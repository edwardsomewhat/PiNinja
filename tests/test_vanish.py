# tests/test_vanish.py
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import yaml
from spawner.packet import ResultPacket, PacketStatus
from spawner.dispatcher import MissionResult, Dispatcher
from vanish.synopsis import generate_intel_packet


def test_generate_intel_packet_all_pass():
    packets = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="qwen3.6:9b",
                     output="Found auth pattern", files_changed=[],
                     errors=[], duration_seconds=3.2),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="gpt-oss:20b",
                     output="Wrote auth/routes.py",
                     files_changed=["auth/routes.py", "auth/middleware.py"],
                     errors=[], duration_seconds=45.2),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="agy",
                     output="Deployed container", files_changed=["docker-compose.yml"],
                     errors=[], duration_seconds=22.1),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="minimax-m2.5",
                     output="LGTM", files_changed=[],
                     errors=[], duration_seconds=5.0),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="minimax-m2.5",
                     output="All tests pass", files_changed=[],
                     errors=[], duration_seconds=8.3),
    ]
    result = MissionResult(mission_id="test-001", packets=packets)
    packet = generate_intel_packet(result)

    assert packet["mission_id"] == "test-001"
    assert packet["status"] == "PASS"
    assert len(packet["subtasks"]) == 5
    assert packet["subtasks"][0]["agent"] == "scout"
    assert packet["subtasks"][1]["agent"] == "coder"
    assert packet["subtasks"][1]["files"] == ["auth/routes.py", "auth/middleware.py"]
    assert set(packet["models_used"]) == {"qwen3.6:9b", "gpt-oss:20b", "agy", "minimax-m2.5"}
    total_seconds = 3.2 + 45.2 + 22.1 + 5.0 + 8.3
    assert packet["duration_seconds"] == round(total_seconds, 1)
    assert "qc" in packet
    assert packet["qc"]["verdict"] == "PASS"
    assert packet["qc"]["issues"] == []


def test_generate_intel_packet_with_failures():
    packets = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="qwen3.6:9b",
                     output="Found pattern", files_changed=[],
                     errors=[], duration_seconds=3.0),
        ResultPacket(role="coder", status=PacketStatus.REJECT, model="gpt-oss:20b",
                     output="Failed", files_changed=[],
                     errors=["SyntaxError: invalid syntax at line 42"],
                     duration_seconds=10.0),
    ]
    result = MissionResult(mission_id="test-002", packets=packets)
    packet = generate_intel_packet(result)

    assert packet["status"] == "FAILED"
    assert packet["qc"]["verdict"] == "REJECT"
    assert len(packet["qc"]["issues"]) == 1
    assert "SyntaxError" in packet["qc"]["issues"][0]


def test_generate_intel_packet_with_lesson():
    packets = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="qwen3.6:9b",
                     output="Found existing auth pattern in helpers.py",
                     files_changed=[], errors=[], duration_seconds=3.0),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="gpt-oss:20b",
                     output="Reused scout findings",
                     files_changed=["auth/routes.py"],
                     errors=[], duration_seconds=30.0),
    ]
    result = MissionResult(mission_id="test-003", packets=packets)
    packet = generate_intel_packet(result)

    assert len(packet["lessons"]) > 0
    assert any("scout" in lesson.lower() for lesson in packet["lessons"])


# --- Enriched intel packet tests ---

def test_enriched_intel_packet_has_forensic_data():
    packets = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="qwen3.6:9b",
                     output="Found existing auth in helpers.py — pattern: decorator-based",
                     files_changed=[], errors=[], duration_seconds=3.2),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="gpt-oss:20b",
                     output="Created auth/routes.py with JWT login/logout endpoints",
                     files_changed=["auth/routes.py", "auth/middleware.py"],
                     errors=[], duration_seconds=45.2),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="agy",
                     output="Deployed Flask app with auth blueprint",
                     files_changed=["docker-compose.yml"],
                     errors=[], duration_seconds=22.1),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="minimax-m2.5",
                     output="LGTM, clean code, type hints present",
                     files_changed=[], errors=[], duration_seconds=5.0),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="minimax-m2.5",
                     output="All 12 tests pass. No regressions detected.",
                     files_changed=[], errors=[], duration_seconds=8.3),
    ]
    result = MissionResult(mission_id="enriched-001", packets=packets)
    packet = generate_intel_packet(result, target_dir="/tmp/auth-build")

    # Forensic output in each subtask
    assert "decorator-based" in packet["subtasks"][0]["output"]
    assert "JWT login" in packet["subtasks"][1]["output"]
    assert "12 tests" in packet["subtasks"][4]["output"]

    # Performance by model
    perf = packet["performance"]
    assert "by_model" in perf
    assert perf["by_model"]["qwen3.6:9b"]["calls"] == 1
    assert perf["by_model"]["gpt-oss:20b"]["calls"] == 1
    assert perf["by_model"]["gpt-oss:20b"]["successes"] == 1

    # Architecture
    arch = packet["architecture"]
    assert "auth/routes.py" in arch["new_files"]
    assert "auth" in arch["new_modules"]
    assert len(arch["diagram"]) > 0

    # Graphify
    gf = packet["graphify"]
    assert len(gf["new_files"]) >= 2
    paths = [f["path"] for f in gf["new_files"]]
    assert "auth/routes.py" in paths

    # Target
    assert packet["target"]["directory"] == "/tmp/auth-build"

    # QC output
    assert "12 tests" in packet["qc"]["qa_output"]

    # Recovery (empty for success)
    assert packet["recovery"]["attempts"] == 0


# --- Archive tests ---

def test_preserve_artifacts_copies_files():
    from vanish.archive import preserve_artifacts

    src = tempfile.mkdtemp()
    dst = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(src, "auth"), exist_ok=True)
        with open(os.path.join(src, "auth", "routes.py"), "w") as f:
            f.write("def login(): pass")
        with open(os.path.join(src, "config.py"), "w") as f:
            f.write("DEBUG = True")

        files = ["auth/routes.py", "config.py"]
        copied = preserve_artifacts(files, src, dst)

        assert len(copied) == 2
        assert os.path.isfile(os.path.join(dst, "auth", "routes.py"))
        assert os.path.isfile(os.path.join(dst, "config.py"))
    finally:
        shutil.rmtree(src)
        shutil.rmtree(dst)


def test_preserve_artifacts_missing_files():
    from vanish.archive import preserve_artifacts

    src = tempfile.mkdtemp()
    dst = tempfile.mkdtemp()
    try:
        files = ["nonexistent.py"]
        copied = preserve_artifacts(files, src, dst)
        assert len(copied) == 0
    finally:
        shutil.rmtree(src)
        shutil.rmtree(dst)


def test_preserve_empty_list():
    from vanish.archive import preserve_artifacts

    copied = preserve_artifacts([], "/tmp/src", "/tmp/dst")
    assert copied == []


# --- Engine tests ---

def test_vanish_full_cycle():
    from vanish.engine import vanish

    payload_dir = tempfile.mkdtemp()
    target_dir = tempfile.mkdtemp()
    archive_dir = tempfile.mkdtemp()

    try:
        with open(os.path.join(payload_dir, "MISSION.md"), "w") as f:
            f.write("# Mission: v-test\n## Goal\nVanish test")

        os.makedirs(os.path.join(target_dir, "src"), exist_ok=True)
        with open(os.path.join(target_dir, "src", "main.py"), "w") as f:
            f.write("print('hello')")

        result = MissionResult(
            mission_id="v-test",
            packets=[
                ResultPacket(role="scout", status=PacketStatus.PASS, model="qwen3.6:9b",
                             output="Found src/main.py", files_changed=[],
                             errors=[], duration_seconds=1.0),
                ResultPacket(role="coder", status=PacketStatus.PASS, model="gpt-oss:20b",
                             output="Wrote src/main.py",
                             files_changed=["src/main.py"],
                             errors=[], duration_seconds=10.0),
            ]
        )

        intel = vanish(result, payload_dir, target_dir, archive_dir, purge=True)

        assert intel["mission_id"] == "v-test"
        assert intel["status"] == "PASS"
        assert not os.path.isdir(payload_dir)

    finally:
        for d in [payload_dir, target_dir, archive_dir]:
            if os.path.isdir(d):
                shutil.rmtree(d)


def test_vanish_no_purge():
    from vanish.engine import vanish

    payload_dir = tempfile.mkdtemp()
    target_dir = tempfile.mkdtemp()
    archive_dir = tempfile.mkdtemp()

    try:
        with open(os.path.join(payload_dir, "MISSION.md"), "w") as f:
            f.write("# Mission: keep-test")

        result = MissionResult(
            mission_id="keep-test",
            packets=[
                ResultPacket(role="scout", status=PacketStatus.PASS, model="test",
                             output="OK", files_changed=[], errors=[],
                             duration_seconds=1.0),
            ]
        )

        vanish(result, payload_dir, target_dir, archive_dir, purge=False)
        assert os.path.isdir(payload_dir)

    finally:
        for d in [payload_dir, target_dir, archive_dir]:
            if os.path.isdir(d):
                shutil.rmtree(d)


def test_vanish_saves_intel_json():
    from vanish.engine import vanish
    import json

    payload_dir = tempfile.mkdtemp()
    target_dir = tempfile.mkdtemp()
    archive_dir = tempfile.mkdtemp()

    try:
        with open(os.path.join(payload_dir, "MISSION.md"), "w") as f:
            f.write("# Mission: intel-test")

        result = MissionResult(
            mission_id="intel-test",
            packets=[
                ResultPacket(role="qa", status=PacketStatus.PASS, model="minimax-m2.5",
                             output="OK", files_changed=[], errors=[],
                             duration_seconds=1.0),
            ]
        )

        intel = vanish(result, payload_dir, target_dir, archive_dir, purge=True)
        assert "intel_saved_to" in intel
        saved_path = intel["intel_saved_to"]
        assert os.path.isfile(saved_path)

        with open(saved_path) as f:
            loaded = json.load(f)
        assert loaded["mission_id"] == "intel-test"

    finally:
        for d in [payload_dir, target_dir, archive_dir]:
            if os.path.isdir(d):
                shutil.rmtree(d)


# --- Dispatcher integration ---

def _make_minimal_payload(base_dir):
    os.makedirs(os.path.join(base_dir, "sub-ninjas"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "skills"), exist_ok=True)
    with open(os.path.join(base_dir, "MISSION.md"), "w") as f:
        f.write("# Mission: disp-test\n## Goal\nTest\n## Target\n**Directory:** `/tmp/disp`\n")
    endpoints = {
        "scout": {"primary": "test", "fallback": "fb"},
        "coder": {"primary": "test", "fallback": "fb"},
        "builder": {"primary": "test", "fallback": "fb"},
        "reviewer": {"primary": "test", "fallback": "fb"},
        "qa": {"primary": "test", "fallback": "fb"},
    }
    with open(os.path.join(base_dir, "endpoints.yaml"), "w") as f:
        yaml.dump(endpoints, f)
    for role in ["scout", "coder", "builder", "reviewer", "qa"]:
        with open(os.path.join(base_dir, "sub-ninjas", f"{role}.yaml"), "w") as f:
            yaml.dump({"role": role, "model": "test", "fallback": "fb",
                       "prompt": f"Agent {role}", "tools": ["read_file"],
                       "mission_id": "disp-test"}, f)
    return base_dir


@patch("spawner.dispatcher.FallbackRunner")
def test_dispatcher_with_vanish(mock_fb_class):
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="t", output="OK"),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="t", output="OK"),
    ]
    mock_fb_class.return_value = mock_fb

    tmp = tempfile.mkdtemp()
    archive_dir = tempfile.mkdtemp()
    try:
        _make_minimal_payload(tmp)
        dispatcher = Dispatcher(tmp)
        intel = dispatcher.run_and_vanish(
            target_dir=tmp,
            archive_dir=archive_dir,
        )

        assert intel["mission_id"] == "disp-test"
        assert intel["status"] == "PASS"
        assert not os.path.isdir(tmp)
    finally:
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        if os.path.isdir(archive_dir):
            shutil.rmtree(archive_dir)
