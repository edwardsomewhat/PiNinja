# tests/test_generator.py
import os
import tempfile
import shutil
import yaml
from packager.generator import generate_payload
from packager.spec import TaskSpec, Constraints
from packager.models import ModelRegistry


def make_spec(**overrides):
    defaults = {
        "mission_id": "test-001",
        "goal": "Build auth system",
        "target_dir": "/tmp/test-target",
        "constraints": Constraints(language="python", framework="flask"),
        "model_preferences": {},
        "skills": ["tdd"],
        "context": "Existing SQLAlchemy ORM in place",
    }
    defaults.update(overrides)
    return TaskSpec(**defaults)


def test_generate_creates_payload_directory():
    spec = make_spec()
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)

        # Check top-level structure
        assert os.path.isdir(output_dir)
        assert os.path.isfile(os.path.join(output_dir, "MISSION.md"))
        assert os.path.isfile(os.path.join(output_dir, "endpoints.yaml"))
        assert os.path.isdir(os.path.join(output_dir, "skills"))
        assert os.path.isdir(os.path.join(output_dir, "sub-ninjas"))
    finally:
        shutil.rmtree(output_dir)


def test_mission_md_contains_spec_fields():
    spec = make_spec()
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)
        mission_path = os.path.join(output_dir, "MISSION.md")
        content = open(mission_path).read()

        assert "Build auth system" in content
        assert "/tmp/test-target" in content
        assert "python" in content
        assert "flask" in content
        assert "pytest" in content
        assert "SQLAlchemy" in content
    finally:
        shutil.rmtree(output_dir)


def test_endpoints_yaml_has_all_roles():
    spec = make_spec()
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)
        endpoints_path = os.path.join(output_dir, "endpoints.yaml")
        data = yaml.safe_load(open(endpoints_path))

        for role in ["scout", "coder", "builder", "reviewer", "qa"]:
            assert role in data
            assert "primary" in data[role]
            assert "fallback" in data[role]
    finally:
        shutil.rmtree(output_dir)


def test_sub_ninjas_yaml_created():
    spec = make_spec()
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)
        sub_ninjas = os.path.join(output_dir, "sub-ninjas")

        for role in ["scout", "coder", "builder", "reviewer", "qa"]:
            config_path = os.path.join(sub_ninjas, f"{role}.yaml")
            assert os.path.isfile(config_path)
            config = yaml.safe_load(open(config_path))
            assert config["role"] == role
            assert "model" in config
            assert "prompt" in config
            assert "tools" in config
    finally:
        shutil.rmtree(output_dir)


def test_model_preferences_override_registry():
    spec = make_spec(
        model_preferences={"coder": "ollama://custom/model"}
    )
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)
        endpoints_path = os.path.join(output_dir, "endpoints.yaml")
        data = yaml.safe_load(open(endpoints_path))
        assert data["coder"]["primary"] == "ollama://custom/model"
    finally:
        shutil.rmtree(output_dir)


def test_skills_directory_created():
    spec = make_spec(skills=["tdd", "writing-plans"])
    registry = ModelRegistry()
    output_dir = tempfile.mkdtemp()

    try:
        generate_payload(spec, registry, output_dir)
        skills_dir = os.path.join(output_dir, "skills")

        # Check that skill directories exist (at least stubs)
        contents = os.listdir(skills_dir)
        assert len(contents) > 0
    finally:
        shutil.rmtree(output_dir)
