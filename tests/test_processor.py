# tests/test_processor.py
import json
import os
import tempfile
from processor.parser import parse_intel_packet


def make_intel(overrides=None):
    base = {
        "mission_id": "test-001",
        "status": "PASS",
        "subtasks": [],
        "qc": {"verdict": "PASS", "issues": [], "qa_output": ""},
        "performance": {"by_model": {}, "total_duration_seconds": 0},
        "architecture": {"new_files": [], "new_modules": [], "diagram": ""},
        "graphify": {"new_files": [], "relationships": []},
        "lessons": [],
        "models_used": [],
    }
    if overrides:
        base.update(overrides)
    return base


def test_parse_intel_from_dict():
    data = make_intel()
    packet = parse_intel_packet(data)
    assert packet["mission_id"] == "test-001"
    assert packet["status"] == "PASS"


def test_parse_intel_from_file():
    data = make_intel({"mission_id": "file-test"})
    tmp = tempfile.mktemp(suffix=".json")
    with open(tmp, "w") as f:
        json.dump(data, f)

    try:
        packet = parse_intel_packet(tmp)
        assert packet["mission_id"] == "file-test"
    finally:
        os.unlink(tmp)


def test_parse_intel_rejects_invalid():
    import pytest
    with pytest.raises(ValueError, match="mission_id"):
        parse_intel_packet({"status": "PASS"})
    with pytest.raises(ValueError, match="status"):
        parse_intel_packet({"mission_id": "x"})


def test_parse_intel_normalizes_missing_sections():
    data = {"mission_id": "minimal", "status": "PASS"}
    packet = parse_intel_packet(data)
    assert "subtasks" in packet
    assert "qc" in packet
    assert "performance" in packet
    assert "lessons" in packet
    assert "architecture" in packet
    assert "graphify" in packet


# --- Memory writer ---

def test_memory_writer_extracts_lessons():
    from processor.memory_writer import extract_memory_entries

    packet = make_intel({
        "mission_id": "mem-test",
        "lessons": [
            "Scout found existing auth helpers — reused instead of rewriting",
            "coder failed with: No module named 'jwt'"
        ],
        "models_used": ["qwen3.6:9b", "gpt-oss:20b"],
        "performance": {
            "by_model": {
                "qwen3.6:9b": {"calls": 2, "total_seconds": 6.2, "successes": 2, "failures": 0},
                "gpt-oss:20b": {"calls": 2, "total_seconds": 55.2, "successes": 1, "failures": 1},
            }
        },
        "architecture": {
            "new_modules": ["auth", "middleware"],
        }
    })

    entries = extract_memory_entries(packet)
    assert len(entries) >= 3

    assert any("auth helpers" in e["content"] for e in entries)

    perf_entries = [e for e in entries if e["type"] == "performance"]
    assert len(perf_entries) >= 1
    assert "gpt-oss:20b" in perf_entries[0]["content"]


def test_memory_writer_empty_packet():
    from processor.memory_writer import extract_memory_entries

    packet = make_intel()
    entries = extract_memory_entries(packet)
    assert entries == []


# --- Graphify updater ---

def test_graphify_updater_generates_commands():
    from processor.graphify_updater import generate_graphify_commands

    packet = make_intel({
        "mission_id": "gf-test",
        "graphify": {
            "new_files": [
                {"path": "auth/routes.py", "language": "python"},
                {"path": "auth/middleware.py", "language": "python"},
            ],
            "relationships": [
                {"from": "app.py", "to": "auth/routes.py", "type": "imports"},
            ]
        },
    })

    commands = generate_graphify_commands(packet, target_dir="/tmp/project")
    assert len(commands) >= 2
    assert any("graphify update" in cmd for cmd in commands)
    assert any("auth" in cmd for cmd in commands)


def test_graphify_updater_empty_packet():
    from processor.graphify_updater import generate_graphify_commands

    packet = make_intel()
    commands = generate_graphify_commands(packet)
    assert commands == []


# --- Session archiver ---

def test_session_archiver_generates_summary():
    from processor.session_archiver import generate_session_summary

    packet = make_intel({
        "mission_id": "summary-test",
        "status": "PASS",
        "subtasks": [
            {"id": "A", "agent": "scout", "model": "qwen3.6:9b", "status": "PASS",
             "files": [], "duration_seconds": 3.2,
             "output": "Found existing auth pattern"},
            {"id": "B", "agent": "coder", "model": "gpt-oss:20b", "status": "PASS",
             "files": ["auth/routes.py"], "duration_seconds": 45.2,
             "output": "Created JWT login endpoints"},
        ],
        "models_used": ["qwen3.6:9b", "gpt-oss:20b"],
        "performance": {"total_duration_seconds": 48.4},
        "architecture": {
            "new_files": ["auth/routes.py"],
            "diagram": "  app.py\n    └── auth/routes.py"
        },
        "lessons": ["Scout found reusable pattern"]
    })

    summary = generate_session_summary(packet)
    assert "# Mission: summary-test" in summary
    assert "PASS" in summary
    assert "qwen3.6:9b" in summary
    assert "gpt-oss:20b" in summary
    assert "auth/routes.py" in summary
    assert "48.4s" in summary
    assert "app.py" in summary


# --- CLI ---

def test_processor_cli():
    processor_dir = os.path.expanduser("~/.hermes/shinobi/processor")
    cli_path = os.path.join(processor_dir, "cli.py")

    intel_file = tempfile.mktemp(suffix=".json")
    with open(intel_file, "w") as f:
        json.dump(make_intel({
            "mission_id": "cli-proc-test",
            "lessons": ["Test lesson"],
            "models_used": ["gpt-oss:20b"],
            "performance": {
                "by_model": {
                    "gpt-oss:20b": {"calls": 1, "total_seconds": 30.0, "successes": 1, "failures": 0}
                }
            }
        }), f)

    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, cli_path, intel_file],
            capture_output=True, text=True,
            cwd=processor_dir,
        )
        assert result.returncode == 0
        assert "Test lesson" in result.stdout
    finally:
        os.unlink(intel_file)
