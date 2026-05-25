"""Intel packet parser — read and validate packet JSON."""
import json
import os

REQUIRED_FIELDS = ["mission_id", "status"]
DEFAULT_SECTIONS = {
    "subtasks": [],
    "qc": {"verdict": "PASS", "issues": [], "qa_output": ""},
    "performance": {
        "by_model": {},
        "total_duration_seconds": 0,
        "fallbacks_used": 0,
    },
    "architecture": {
        "new_files": [],
        "modified_files": [],
        "new_modules": [],
        "dependencies_added": [],
        "diagram": "",
    },
    "graphify": {"new_files": [], "relationships": []},
    "lessons": [],
    "models_used": [],
    "target": {},
    "recovery": {
        "attempts": 0,
        "diagnosticians_spawned": 0,
        "diagnoses": [],
    },
}


def parse_intel_packet(source) -> dict:
    """Parse an intel packet from a dict, JSON string, or file path."""
    if isinstance(source, dict):
        data = source
    elif isinstance(source, str):
        if os.path.isfile(source):
            with open(source) as f:
                data = json.load(f)
        else:
            data = json.loads(source)
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Fill in defaults for missing sections
    for key, default in DEFAULT_SECTIONS.items():
        if key not in data:
            data[key] = default

    return data
