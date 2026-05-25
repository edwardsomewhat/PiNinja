# tests/test_integration.py
import os
import tempfile
import shutil
import json
import subprocess
import sys
import yaml

PACKAGER_DIR = os.path.expanduser("~/.hermes/shinobi/packager")
CLI_PATH = os.path.join(PACKAGER_DIR, "cli.py")

FULL_SPEC = {
    "mission_id": "integration-001",
    "goal": "Build user authentication with JWT tokens",
    "target_dir": "/tmp/sovereign-auth",
    "constraints": {
        "language": "python",
        "framework": "flask",
        "test_framework": "pytest"
    },
    "model_preferences": {
        "coder": "ollama://hq-ai:11434/gpt-oss:20b"
    },
    "skills": ["tdd"],
    "context": (
        "Existing codebase uses Flask blueprints for route organization. "
        "User model exists with email and password_hash fields. "
        "SQLAlchemy session via flask_sqlalchemy."
    )
}


def test_full_pipeline():
    output_dir = tempfile.mkdtemp()

    try:
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--output", output_dir],
            input=json.dumps(FULL_SPEC),
            capture_output=True,
            text=True,
            cwd=PACKAGER_DIR,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify MISSION.md
        mission = open(os.path.join(output_dir, "MISSION.md")).read()
        assert "# Mission: integration-001" in mission
        assert "Build user authentication with JWT tokens" in mission
        assert "flask" in mission
        assert "SQLAlchemy" in mission
        assert "blueprints" in mission

        # Verify endpoints.yaml
        endpoints = yaml.safe_load(open(os.path.join(output_dir, "endpoints.yaml")))
        assert endpoints["coder"]["primary"] == "ollama://hq-ai:11434/gpt-oss:20b"
        assert endpoints["coder"]["fallback"] == "openrouter://minimax/minimax-m2.5"
        assert endpoints["scout"]["primary"] == "ollama://hq-ai:11434/qwen3.6:9b"

        # Verify sub-ninjas
        sub_ninjas_dir = os.path.join(output_dir, "sub-ninjas")
        for role in ["scout", "coder", "builder", "reviewer", "qa"]:
            config = yaml.safe_load(
                open(os.path.join(sub_ninjas_dir, f"{role}.yaml"))
            )
            assert config["role"] == role
            assert config["model"]
            assert config["tools"]

        # Verify skills/
        skills_dir = os.path.join(output_dir, "skills")
        assert os.path.isdir(skills_dir)

        # Verify vanishing instructions in MISSION.md
        assert "Vanish" in mission

        print(f"Payload verified at: {output_dir}")
    finally:
        shutil.rmtree(output_dir)
