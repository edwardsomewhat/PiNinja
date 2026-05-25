# tests/test_spec.py
import pytest
from packager.spec import TaskSpec, parse_spec

VALID_SPEC = {
    "mission_id": "test-mission-001",
    "goal": "Build a user authentication system",
    "target_dir": "/tmp/shinobi-test",
    "constraints": {
        "language": "python",
        "framework": "flask",
        "test_framework": "pytest"
    },
    "model_preferences": {
        "coder": "ollama://hq-ai:11434/gpt-oss:20b"
    },
    "skills": ["tdd", "code-review"],
    "context": "Existing project uses SQLAlchemy for ORM"
}


def test_parse_spec_returns_taskspec():
    spec = parse_spec(VALID_SPEC)
    assert isinstance(spec, TaskSpec)
    assert spec.mission_id == "test-mission-001"
    assert spec.goal == "Build a user authentication system"
    assert spec.target_dir == "/tmp/shinobi-test"
    assert spec.constraints.language == "python"
    assert spec.model_preferences["coder"] == "ollama://hq-ai:11434/gpt-oss:20b"
    assert "tdd" in spec.skills


def test_parse_spec_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="mission_id"):
        parse_spec({"goal": "foo", "target_dir": "/tmp"})
    with pytest.raises(ValueError, match="goal"):
        parse_spec({"mission_id": "m1", "target_dir": "/tmp"})
    with pytest.raises(ValueError, match="target_dir"):
        parse_spec({"mission_id": "m1", "goal": "foo"})


def test_parse_spec_defaults_empty_fields():
    spec = parse_spec({
        "mission_id": "m1",
        "goal": "test",
        "target_dir": "/tmp"
    })
    assert spec.constraints is None
    assert spec.model_preferences == {}
    assert spec.skills == []
    assert spec.context == ""


def test_parse_spec_from_yaml_string():
    yaml_str = """
mission_id: yaml-mission
goal: Test YAML parsing
target_dir: /tmp/yaml-test
"""
    spec = parse_spec(yaml_str)
    assert spec.mission_id == "yaml-mission"


def test_parse_spec_from_json_string():
    import json
    json_str = json.dumps({
        "mission_id": "json-mission",
        "goal": "Test JSON parsing",
        "target_dir": "/tmp/json-test"
    })
    spec = parse_spec(json_str)
    assert spec.mission_id == "json-mission"
