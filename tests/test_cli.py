# tests/test_cli.py
import os
import sys
import tempfile
import shutil
import json
import subprocess

PACKAGER_DIR = os.path.expanduser("~/.hermes/shinobi/packager")
CLI_PATH = os.path.join(PACKAGER_DIR, "cli.py")


def test_cli_accepts_json_stdin():
    """Packager reads task spec from stdin as JSON."""
    output_dir = tempfile.mkdtemp()
    spec = {
        "mission_id": "cli-test-001",
        "goal": "CLI test mission",
        "target_dir": "/tmp/cli-test"
    }

    try:
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--output", output_dir],
            input=json.dumps(spec),
            capture_output=True,
            text=True,
            cwd=PACKAGER_DIR,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert os.path.isfile(os.path.join(output_dir, "MISSION.md"))
        assert os.path.isfile(os.path.join(output_dir, "endpoints.yaml"))
    finally:
        shutil.rmtree(output_dir)


def test_cli_accepts_file_argument():
    """Packager reads task spec from a file."""
    output_dir = tempfile.mkdtemp()
    spec_file = tempfile.mktemp(suffix=".json")
    spec = {
        "mission_id": "file-test-001",
        "goal": "File test mission",
        "target_dir": "/tmp/file-test"
    }
    with open(spec_file, "w") as f:
        json.dump(spec, f)

    try:
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--output", output_dir, spec_file],
            capture_output=True,
            text=True,
            cwd=PACKAGER_DIR,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        content = open(os.path.join(output_dir, "MISSION.md")).read()
        assert "File test mission" in content
    finally:
        shutil.rmtree(output_dir)
        os.unlink(spec_file)


def test_cli_requires_mission_id():
    """Packager fails when required fields are missing."""
    output_dir = tempfile.mkdtemp()
    spec = {"goal": "no mission id", "target_dir": "/tmp"}

    try:
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--output", output_dir],
            input=json.dumps(spec),
            capture_output=True,
            text=True,
            cwd=PACKAGER_DIR,
        )
        assert result.returncode != 0
    finally:
        shutil.rmtree(output_dir)
