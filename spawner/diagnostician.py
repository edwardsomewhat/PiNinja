"""On-the-fly diagnostic agent spawning."""

DIAGNOSTICIAN_PROMPT = """You are a Shinobi Diagnostician. Your job: figure out what went wrong.

A sub-agent failed. Analyze the error and provide:
1. Root cause (what actually broke)
2. Suggested fix (what to change)
3. Whether to retry the original agent or escalate

Be concise. This is triage, not a full solution."""

DEFAULT_MODEL = "ollama://hq-ai:11434/qwen3.6:9b"


class Diagnostician:
    """Creates and runs diagnostic agents on-the-fly when sub-agents fail."""

    def __init__(self, primary_model: str = DEFAULT_MODEL):
        self.primary_model = primary_model

    def build_config(self, failed_packet, mission_context: str):
        from .config import SubNinjaConfig

        prompt = (
            f"{DIAGNOSTICIAN_PROMPT}\n\n"
            f"## Failed Agent: {failed_packet.role}\n"
            f"## Error Output:\n{failed_packet.output}\n\n"
            f"## Errors:\n" + "\n".join(f"- {e}" for e in failed_packet.errors) + "\n\n"
            f"## Files Changed:\n" + "\n".join(f"- {f}" for f in failed_packet.files_changed)
        )

        return SubNinjaConfig(
            role="diagnostician",
            model=self.primary_model,
            fallback="",
            prompt=prompt,
            tools=["read_file", "search_files"],
            mission_id="diagnostic",
        )

    def diagnose(self, failed_packet, mission_context: str):
        from .runners.base import get_runner

        config = self.build_config(failed_packet, mission_context)
        runner = get_runner(config.model)
        return runner.run(config, mission_context)
