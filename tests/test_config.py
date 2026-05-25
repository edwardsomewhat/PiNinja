# tests/test_config.py
import os
import tempfile
import shutil
import yaml
from spawner.config import Payload, SubNinjaConfig, load_payload


def make_payload_dir(base_dir):
    """Create a minimal payload directory structure."""
    os.makedirs(os.path.join(base_dir, "sub-ninjas"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "skills"), exist_ok=True)

    with open(os.path.join(base_dir, "MISSION.md"), "w") as f:
        f.write("# Mission: test-001\n## Goal\nTest mission\n## Target\n**Directory:** `/tmp/test`\n")

    endpoints = {
        "scout": {"primary": "ollama://hq-ai:11434/qwen3.6:9b", "fallback": "openrouter://minimax/minimax-m2.5"},
        "coder": {"primary": "ollama://hq-ai:11434/gpt-oss:20b", "fallback": "openrouter://minimax/minimax-m2.5"},
        "builder": {"primary": "agy://hq-ai", "fallback": "openrouter://minimax/minimax-m2.5"},
        "reviewer": {"primary": "openrouter://minimax/minimax-m2.5", "fallback": "openrouter://minimax/minimax-m2.5"},
        "qa": {"primary": "openrouter://minimax/minimax-m2.5", "fallback": "openrouter://minimax/minimax-m2.5"},
    }
    with open(os.path.join(base_dir, "endpoints.yaml"), "w") as f:
        yaml.dump(endpoints, f)

    for role in ["scout", "coder", "builder", "reviewer", "qa"]:
        config = {
            "role": role,
            "model": "test-model",
            "fallback": "fallback-model",
            "prompt": f"You are a {role}.",
            "tools": ["read_file", "write_file"],
            "mission_id": "test-001",
        }
        with open(os.path.join(base_dir, "sub-ninjas", f"{role}.yaml"), "w") as f:
            yaml.dump(config, f)

    return base_dir


def test_load_payload_reads_all_components():
    tmp = tempfile.mkdtemp()
    try:
        make_payload_dir(tmp)
        payload = load_payload(tmp)

        assert isinstance(payload, Payload)
        assert payload.mission_id == "test-001"
        assert "Test mission" in payload.goal
        assert payload.target_dir == "/tmp/test"

        # Endpoints
        assert payload.endpoints["coder"]["primary"] == "ollama://hq-ai:11434/gpt-oss:20b"

        # Sub-ninjas
        assert len(payload.sub_ninjas) == 5
        scout = payload.get_sub_ninja("scout")
        assert scout.role == "scout"
        assert scout.model == "test-model"
        assert "read_file" in scout.tools
    finally:
        shutil.rmtree(tmp)


def test_load_payload_missing_directory_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_payload("/tmp/nonexistent-payload-xyz")


def test_get_sub_ninja_unknown_role_raises():
    import pytest
    tmp = tempfile.mkdtemp()
    try:
        make_payload_dir(tmp)
        payload = load_payload(tmp)
        with pytest.raises(KeyError, match="diagnostician"):
            payload.get_sub_ninja("diagnostician")
    finally:
        shutil.rmtree(tmp)


def test_sub_ninja_config_fields():
    tmp = tempfile.mkdtemp()
    try:
        make_payload_dir(tmp)
        payload = load_payload(tmp)
        coder = payload.get_sub_ninja("coder")
        assert coder.role == "coder"
        assert coder.model == "test-model"
        assert coder.fallback == "fallback-model"
        assert coder.prompt == "You are a coder."
        assert coder.tools == ["read_file", "write_file"]
        assert coder.mission_id == "test-001"
    finally:
        shutil.rmtree(tmp)
