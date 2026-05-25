"""OpenRouter backend runner — OpenAI-compatible API with tool-calling."""
import os
import re
import time
import requests
from .base import Runner
from ..config import SubNinjaConfig
from ..packet import ResultPacket, PacketStatus

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class OpenRouterRunner(Runner):
    def run(self, config: SubNinjaConfig, mission_context: str) -> ResultPacket:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model=config.model,
                output="",
                errors=["OPENROUTER_API_KEY environment variable not set"],
            )

        # Parse URI: openrouter://provider/model
        uri = config.model
        match = re.match(r"openrouter://(.+)", uri)
        if not match:
            return ResultPacket(
                role=config.role,
                status=PacketStatus.ERROR,
                model=uri,
                output="",
                errors=[f"Invalid OpenRouter URI: {uri}"],
            )

        model_name = match.group(1)

        system_prompt = f"{config.prompt}\n\n## Mission Context\n{mission_context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "Execute your task. Report what you did, files changed, "
                "and any issues encountered."
            )},
        ]

        tool_defs = _build_tool_defs_openai(config.tools)

        start = time.time()

        try:
            payload = {
                "model": model_name,
                "messages": messages,
            }
            if tool_defs:
                payload["tools"] = tool_defs

            resp = requests.post(
                f"{OPENROUTER_BASE}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()

            output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            elapsed = time.time() - start

            return ResultPacket(
                role=config.role,
                status=PacketStatus.PASS,
                model=model_name,
                output=output,
                files_changed=_extract_files(output),
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


def _build_tool_defs_openai(tool_names: list) -> list:
    """Convert tool names to OpenAI function definitions."""
    tool_map = {
        "read_file": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
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
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        },
    }
    return [tool_map[t] for t in tool_names if t in tool_map]


def _extract_files(output: str) -> list:
    files = []
    for match in re.finditer(r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)`', output):
        files.append(match.group(1))
    seen = set()
    return [f for f in files if not (f in seen or seen.add(f))]
