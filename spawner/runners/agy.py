"""agy backend runner — SSH to hq-ai, run agy CLI."""
import re
import os
import time
import tempfile
import subprocess
from .base import Runner
from ..config import SubNinjaConfig
from ..packet import ResultPacket, PacketStatus


class AgyRunner(Runner):
    def run(self, config: SubNinjaConfig, mission_context: str) -> ResultPacket:
        # Parse URI: agy://host
        uri = config.model
        match = re.match(r"agy://(.+)", uri)
        if not match:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model=uri,
                output="",
                errors=[f"Invalid agy URI: {uri}"],
            )

        host = match.group(1)

        # Write prompt to temp file (agy reads from file, avoids SSH quoting hell)
        full_prompt = f"{config.prompt}\n\n## Mission Context\n{mission_context}"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="agy-prompt-"
        ) as f:
            f.write(full_prompt)
            prompt_path = f.name

        start = time.time()

        try:
            cmd = ["ssh", host, "cat", prompt_path, "|", "agy", "-p", "--dangerously-skip-permissions"]
            result = subprocess.run(
                " ".join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,
            )

            output = result.stdout.strip()
            errors = []
            if result.returncode != 0:
                errors.append(result.stderr.strip() or f"Exit code: {result.returncode}")

            elapsed = time.time() - start
            status = PacketStatus.PASS if result.returncode == 0 else PacketStatus.ERROR

            return ResultPacket(
                role=config.role,
                status=status,
                model="agy",
                output=output,
                files_changed=_extract_files_agy(output),
                errors=errors,
                duration_seconds=round(elapsed, 1),
            )

        except subprocess.TimeoutExpired:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model="agy",
                output="",
                errors=["Timeout after 600s"],
            )
        except Exception as e:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model="agy",
                output="",
                errors=[str(e)],
            )
        finally:
            try:
                os.unlink(prompt_path)
            except OSError:
                pass


def _extract_files_agy(output: str) -> list:
    files = []
    for match in re.finditer(r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)`', output):
        files.append(match.group(1))
    seen = set()
    return [f for f in files if not (f in seen or seen.add(f))]
