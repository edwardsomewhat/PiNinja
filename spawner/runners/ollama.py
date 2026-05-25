"""Ollama backend runner — REST API with native tool-calling."""
import re
import time
import requests
from .base import Runner
from ..config import SubNinjaConfig
from ..packet import ResultPacket, PacketStatus


class OllamaRunner(Runner):
    def run(self, config: SubNinjaConfig, mission_context: str) -> ResultPacket:
        # Parse model URI: ollama://host:port/model
        uri = config.model
        match = re.match(r"ollama://([^:/]+)(?::(\d+))?/(.+)", uri)
        if not match:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model=uri,
                output="",
                errors=[f"Invalid Ollama URI: {uri}"],
            )

        host = match.group(1)
        port = match.group(2) or "11434"
        model_name = match.group(3)
        base_url = f"http://{host}:{port}"

        # Build system prompt with mission context
        system_prompt = f"{config.prompt}\n\n## Mission Context\n{mission_context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "Execute your task. Report what you did, files changed, "
                "and any issues encountered."
            )},
        ]

        tool_defs = _build_tool_defs(config.tools)

        start = time.time()

        try:
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {"num_ctx": 32768},
            }
            if tool_defs:
                payload["tools"] = tool_defs

            resp = requests.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()

            output = data.get("message", {}).get("content", "")
            elapsed = time.time() - start
            files = _extract_files(output)

            return ResultPacket(
                role=config.role,
                status=PacketStatus.PASS,
                model=model_name,
                output=output,
                files_changed=files,
                errors=[],
                duration_seconds=round(elapsed, 1),
            )

        except Exception as e:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model=model_name,
                output="",
                errors=[str(e)],
            )


def _build_tool_defs(tool_names: list) -> list:
    """Convert tool names to Ollama function tool definitions."""
    tool_map = {
        "read_file": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        "write_file": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        "patch": {
            "type": "function",
            "function": {
                "name": "patch",
                "description": "Apply a patch to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"},
                    },
                    "required": ["path", "old_string", "new_string"],
                },
            },
        },
        "search_files": {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search file contents or find files by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "path": {"type": "string"},
                    },
                    "required": ["pattern"],
                },
            },
        },
        "terminal": {
            "type": "function",
            "function": {
                "name": "terminal",
                "description": "Run a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                    },
                    "required": ["command"],
                },
            },
        },
    }
    return [tool_map[t] for t in tool_names if t in tool_map]


def _extract_files(output: str) -> list:
    """Extract file paths from agent output."""
    files = []
    for match in re.finditer(r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)`', output):
        files.append(match.group(1))
    # Deduplicate while preserving order
    seen = set()
    return [f for f in files if not (f in seen or seen.add(f))]
