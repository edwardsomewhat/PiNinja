"""Fallback runner — tries primary, then falls back on failure."""
from .base import Runner, get_runner
from ..packet import ResultPacket, PacketStatus
from ..config import SubNinjaConfig


class FallbackRunner(Runner):
    """Runner that tries primary, then falls back to secondary on failure."""

    def run(
        self, config: SubNinjaConfig, mission_context: str
    ) -> ResultPacket:
        # Try primary
        primary_runner = get_runner(config.model)
        result = primary_runner.run(config, mission_context)

        if result.status == PacketStatus.PASS:
            return result

        # Primary failed — try fallback
        if not config.fallback:
            result.errors.append("No fallback configured")
            return result

        fallback_runner = get_runner(config.fallback)
        fallback_result = fallback_runner.run(config, mission_context)

        # Annotate that fallback was used
        fallback_result.errors.insert(
            0,
            f"Fallback used after primary ({config.model}) failed",
        )
        return fallback_result
