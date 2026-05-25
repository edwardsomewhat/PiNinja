"""Dispatcher — orchestrates sub-agent execution in sequence."""
from dataclasses import dataclass, field
from .config import load_payload
from .packet import ResultPacket, PacketStatus
from .runners.fallback import FallbackRunner
from .diagnostician import Diagnostician

EXECUTION_ORDER = ["scout", "coder", "builder", "reviewer", "qa"]
MAX_RETRIES = 3


@dataclass
class MissionResult:
    mission_id: str
    packets: list = field(default_factory=list)
    recovery: dict = field(default_factory=dict)

    def all_passed(self) -> bool:
        return all(p.status == PacketStatus.PASS for p in self.packets)

    def has_errors(self) -> bool:
        return any(p.status == PacketStatus.ERROR for p in self.packets)

    def failed(self) -> bool:
        return any(
            p.status in (PacketStatus.REJECT, PacketStatus.ERROR)
            for p in self.packets
        )

    def summary(self) -> str:
        lines = [f"Mission: {self.mission_id}"]
        status = "PASSED" if self.all_passed() else "FAILED"
        lines.append(f"Result: {status}")
        lines.append("")
        for pkt in self.packets:
            flag = "✓" if pkt.status == PacketStatus.PASS else "✗"
            lines.append(
                f"  {flag} {pkt.role}: {pkt.status.value} "
                f"({pkt.duration_seconds:.1f}s) — {pkt.model}"
            )
            if pkt.errors:
                for err in pkt.errors:
                    lines.append(f"    Error: {err}")
            if pkt.files_changed:
                lines.append(
                    f"    Files: {', '.join(pkt.files_changed)}"
                )
        return "\n".join(lines)


class Dispatcher:
    """Loads a payload and executes sub-agents with retry and fallback."""

    def __init__(self, payload_dir: str, all_api: bool = False):
        self.payload_dir = payload_dir
        self.payload = load_payload(payload_dir)
        self.all_api = all_api

    def run(self) -> MissionResult:
        """Execute all sub-agents in order with retry and fallback."""
        result = MissionResult(mission_id=self.payload.mission_id)
        mission_context = self.payload.mission_md_raw
        recovery = {"attempts": 0, "diagnosticians_spawned": 0, "diagnoses": []}

        for role in EXECUTION_ORDER:
            if role not in self.payload.sub_ninjas:
                continue

            config = self.payload.sub_ninjas[role]
            packet = self._run_with_retry(config, mission_context, recovery)
            result.packets.append(packet)

            if packet.status in (PacketStatus.REJECT, PacketStatus.ERROR):
                if packet.status == PacketStatus.REJECT or recovery["attempts"] >= MAX_RETRIES:
                    break

        result.recovery = recovery
        return result

    def _run_with_retry(self, config, mission_context, recovery) -> ResultPacket:
        """Run a sub-agent with up to MAX_RETRIES attempts."""
        runner = FallbackRunner()

        # All-API mode: force OpenRouter fallback
        if self.all_api and config.fallback:
            config.model = config.fallback

        for attempt in range(1, MAX_RETRIES + 1):
            packet = runner.run(config, mission_context)

            if packet.status == PacketStatus.PASS:
                return packet

            # REJECT means the code is wrong — don't retry
            if packet.status == PacketStatus.REJECT:
                return packet

            # ERROR means infrastructure issue — retry
            recovery["attempts"] += 1

            if attempt < MAX_RETRIES:
                # Spawn Diagnostician
                diag = Diagnostician()
                diagnosis = diag.diagnose(packet, mission_context)
                recovery["diagnosticians_spawned"] += 1
                recovery["diagnoses"].append({
                    "failed_agent": config.role,
                    "attempt": attempt,
                    "error": (
                        packet.errors[0]
                        if packet.errors
                        else "Unknown error"
                    ),
                    "diagnosis": diagnosis.output,
                })

        return packet  # All retries exhausted

    def run_and_vanish(
        self,
        target_dir: str = None,
        archive_dir: str = None,
        purge: bool = True,
    ) -> dict:
        """Run the mission and execute vanish protocol. Returns intel packet."""
        result = self.run()
        from vanish.engine import vanish as do_vanish

        return do_vanish(
            result,
            self.payload_dir,
            target_dir=target_dir,
            archive_dir=archive_dir,
            purge=purge,
        )
