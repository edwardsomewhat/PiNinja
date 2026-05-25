# tests/test_packet.py
import json
from spawner.packet import ResultPacket, PacketStatus


def test_packet_creation():
    pkt = ResultPacket(
        role="coder",
        status=PacketStatus.PASS,
        model="ollama://hq-ai:11434/gpt-oss:20b",
        output="Wrote auth/routes.py with JWT middleware",
        files_changed=["auth/routes.py", "auth/middleware.py"],
        errors=[],
        duration_seconds=45.2,
    )
    assert pkt.role == "coder"
    assert pkt.status == PacketStatus.PASS
    assert len(pkt.files_changed) == 2


def test_packet_to_dict():
    pkt = ResultPacket(
        role="scout",
        status=PacketStatus.PASS,
        model="ollama://hq-ai:11434/qwen3.6:9b",
        output="Found existing auth pattern in auth/helpers.py",
        files_changed=[],
        errors=[],
        duration_seconds=12.1,
    )
    d = pkt.to_dict()
    assert d["role"] == "scout"
    assert d["status"] == "PASS"
    assert d["errors"] == []


def test_packet_json_roundtrip():
    pkt = ResultPacket(
        role="qa",
        status=PacketStatus.FLAG,
        model="openrouter://minimax/minimax-m2.5",
        output="Rate limit test fails: expected 429, got 200",
        files_changed=[],
        errors=["Rate limit middleware not applied to /api/v2"],
        duration_seconds=8.3,
    )
    d = pkt.to_dict()
    json_str = json.dumps(d)
    reloaded = json.loads(json_str)
    assert reloaded["status"] == "FLAG"
    assert len(reloaded["errors"]) == 1


def test_packet_status_values():
    assert PacketStatus.PASS == "PASS"
    assert PacketStatus.FLAG == "FLAG"
    assert PacketStatus.REJECT == "REJECT"
    assert PacketStatus.ERROR == "ERROR"
