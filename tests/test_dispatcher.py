# tests/test_dispatcher.py
import os
import tempfile
import shutil
import yaml
from unittest.mock import patch, MagicMock
from spawner.dispatcher import Dispatcher, MissionResult
from spawner.packet import PacketStatus, ResultPacket


def make_minimal_payload(base_dir):
    """Minimal payload for dispatcher tests."""
    os.makedirs(os.path.join(base_dir, "sub-ninjas"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "skills"), exist_ok=True)

    with open(os.path.join(base_dir, "MISSION.md"), "w") as f:
        f.write("# Mission: disp-test\n## Goal\nTest dispatch\n## Target\n**Directory:** `/tmp/disp`\n")

    endpoints = {
        "scout": {"primary": "ollama://hq-ai:11434/qwen3.6:9b", "fallback": "fb"},
        "coder": {"primary": "ollama://hq-ai:11434/gpt-oss:20b", "fallback": "fb"},
        "builder": {"primary": "agy://hq-ai", "fallback": "fb"},
        "reviewer": {"primary": "openrouter://minimax/minimax-m2.5", "fallback": "fb"},
        "qa": {"primary": "openrouter://minimax/minimax-m2.5", "fallback": "fb"},
    }
    with open(os.path.join(base_dir, "endpoints.yaml"), "w") as f:
        yaml.dump(endpoints, f)

    for role in ["scout", "coder", "builder", "reviewer", "qa"]:
        config = {
            "role": role, "model": "test-model",
            "fallback": "fb", "prompt": f"Agent {role}",
            "tools": ["read_file"], "mission_id": "disp-test",
        }
        with open(os.path.join(base_dir, "sub-ninjas", f"{role}.yaml"), "w") as f:
            yaml.dump(config, f)

    return base_dir


@patch("spawner.dispatcher.FallbackRunner")
def test_dispatcher_runs_all_agents_in_order(mock_fb_class):
    mock_fb = MagicMock()
    # 5 PASS responses — one per agent
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="test", output="OK"),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="test", output="OK"),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="test", output="OK"),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="test", output="OK"),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="test", output="OK"),
    ]
    mock_fb_class.return_value = mock_fb

    tmp = tempfile.mkdtemp()
    try:
        make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp)
        result = dispatcher.run()

        assert isinstance(result, MissionResult)
        assert result.mission_id == "disp-test"
        assert len(result.packets) == 5
        assert result.all_passed()

        roles = [p.role for p in result.packets]
        assert roles == ["scout", "coder", "builder", "reviewer", "qa"]
        assert mock_fb.run.call_count == 5
    finally:
        shutil.rmtree(tmp)


@patch("spawner.dispatcher.FallbackRunner")
def test_dispatcher_stops_on_reject(mock_fb_class):
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="coder", status=PacketStatus.REJECT, model="t",
                     output="Bad code", errors=["Syntax error"]),
    ]
    mock_fb_class.return_value = mock_fb

    tmp = tempfile.mkdtemp()
    try:
        make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp)
        result = dispatcher.run()

        assert not result.all_passed()
        assert len(result.packets) == 2
        assert result.packets[-1].status == PacketStatus.REJECT
    finally:
        shutil.rmtree(tmp)


def test_mission_result_methods():
    result = MissionResult(
        mission_id="test",
        packets=[
            ResultPacket(role="scout", status=PacketStatus.PASS, model="t", output=""),
            ResultPacket(role="coder", status=PacketStatus.PASS, model="t", output=""),
            ResultPacket(role="qa", status=PacketStatus.FLAG, model="t",
                         output="", errors=["minor"]),
        ],
    )
    assert not result.all_passed()
    assert result.has_errors() is False
    summary = result.summary()
    assert "FAILED" in summary
    assert "test" in summary


# --- Phase 5: All-API mode ---

@patch("spawner.dispatcher.FallbackRunner")
def test_dispatcher_all_api_mode(mock_fb_class):
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="minimax-m2.5", output="OK"),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="minimax-m2.5", output="OK"),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="minimax-m2.5", output="OK"),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="minimax-m2.5", output="OK"),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="minimax-m2.5", output="OK"),
    ]
    mock_fb_class.return_value = mock_fb

    tmp = tempfile.mkdtemp()
    try:
        make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp, all_api=True)
        result = dispatcher.run()

        assert result.all_passed()
        for pkt in result.packets:
            assert "minimax" in pkt.model or "openrouter" in pkt.model.lower()
    finally:
        shutil.rmtree(tmp)


# --- Phase 6: Retry loop ---

@patch("spawner.dispatcher.FallbackRunner")
@patch("spawner.dispatcher.Diagnostician")
def test_dispatcher_retries_on_error(mock_diag_class, mock_fb_class):
    # Coder fails 2x, succeeds on 3rd try
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="t", output="OK"),
        # Coder failures
        ResultPacket(role="coder", status=PacketStatus.ERROR, model="t",
                     output="", errors=["Connection refused"]),
        ResultPacket(role="coder", status=PacketStatus.ERROR, model="t",
                     output="", errors=["Connection refused"]),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="t",
                     output="Done"),
        # Rest pass
        ResultPacket(role="builder", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="t", output="OK"),
    ]
    mock_fb_class.return_value = mock_fb

    mock_diag = MagicMock()
    mock_diag.diagnose.return_value = ResultPacket(
        role="diagnostician", status=PacketStatus.PASS, model="qwen3.6:9b",
        output="Primary unreachable — use fallback",
    )
    mock_diag_class.return_value = mock_diag

    tmp = tempfile.mkdtemp()
    try:
        make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp)
        result = dispatcher.run()

        assert result.all_passed()
        assert mock_diag.diagnose.call_count == 2
        assert result.recovery["attempts"] == 2
        assert len(result.recovery["diagnoses"]) == 2
    finally:
        shutil.rmtree(tmp)


@patch("spawner.dispatcher.FallbackRunner")
def test_dispatcher_escalates_after_max_retries(mock_fb_class):
    # Coder fails all 3 attempts
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="coder", status=PacketStatus.ERROR, model="t",
                     output="", errors=["Persistent"]),
        ResultPacket(role="coder", status=PacketStatus.ERROR, model="t",
                     output="", errors=["Persistent"]),
        ResultPacket(role="coder", status=PacketStatus.ERROR, model="t",
                     output="", errors=["Persistent"]),
    ]
    mock_fb_class.return_value = mock_fb

    tmp = tempfile.mkdtemp()
    try:
        make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp)
        result = dispatcher.run()

        assert not result.all_passed()
        assert len(result.packets) == 2  # Scout PASS + Coder final ERROR
        assert result.recovery["attempts"] == 3
    finally:
        shutil.rmtree(tmp)
