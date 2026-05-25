"""Result packet — structured output from each sub-agent run."""
from dataclasses import dataclass, field, asdict
from enum import Enum


class PacketStatus(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    REJECT = "REJECT"
    ERROR = "ERROR"


@dataclass
class ResultPacket:
    role: str
    status: PacketStatus
    model: str
    output: str
    files_changed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d
