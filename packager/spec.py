"""Task spec schema for Shinobi packager."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Constraints:
    language: Optional[str] = None
    framework: Optional[str] = None
    test_framework: Optional[str] = None


@dataclass
class TaskSpec:
    mission_id: str
    goal: str
    target_dir: str
    constraints: Optional[Constraints] = None
    model_preferences: dict = field(default_factory=dict)
    skills: list = field(default_factory=list)
    context: str = ""


def parse_spec(input_data) -> TaskSpec:
    """Parse a task spec from dict, YAML string, or JSON string."""
    if isinstance(input_data, TaskSpec):
        return input_data

    if isinstance(input_data, str):
        import yaml
        import json
        stripped = input_data.strip()
        if stripped.startswith('{'):
            data = json.loads(stripped)
        else:
            data = yaml.safe_load(stripped)
    else:
        data = input_data

    if not isinstance(data, dict):
        raise ValueError("Input must be a dict, YAML string, or JSON string")

    # Validate required fields
    for field_name in ["mission_id", "goal", "target_dir"]:
        if field_name not in data:
            raise ValueError(f"Missing required field: {field_name}")

    constraints_data = data.get("constraints", {})
    constraints = Constraints(
        language=constraints_data.get("language"),
        framework=constraints_data.get("framework"),
        test_framework=constraints_data.get("test_framework"),
    ) if constraints_data else None

    return TaskSpec(
        mission_id=data["mission_id"],
        goal=data["goal"],
        target_dir=data["target_dir"],
        constraints=constraints,
        model_preferences=data.get("model_preferences", {}),
        skills=data.get("skills", []),
        context=data.get("context", ""),
    )
