"""Payload loader — reads a deployed payload directory into structured objects."""
import os
import yaml
from dataclasses import dataclass, field


@dataclass
class SubNinjaConfig:
    role: str
    model: str
    fallback: str
    prompt: str
    tools: list
    mission_id: str


@dataclass
class Payload:
    mission_id: str
    goal: str
    target_dir: str
    endpoints: dict
    sub_ninjas: dict           # role → SubNinjaConfig
    mission_md_raw: str = ""   # Full MISSION.md text

    def get_sub_ninja(self, role: str) -> SubNinjaConfig:
        if role not in self.sub_ninjas:
            raise KeyError(f"Unknown sub-ninja role: {role}")
        return self.sub_ninjas[role]


def load_payload(payload_dir: str) -> Payload:
    """Load a Shinobi payload directory into a Payload object."""
    if not os.path.isdir(payload_dir):
        raise FileNotFoundError(f"Payload directory not found: {payload_dir}")

    # Load MISSION.md
    mission_path = os.path.join(payload_dir, "MISSION.md")
    with open(mission_path) as f:
        mission_raw = f.read()

    # Parse mission fields
    mission_id = ""
    goal = ""
    target_dir = ""

    in_goal = False
    goal_lines = []
    for line in mission_raw.split("\n"):
        if line.startswith("# Mission:"):
            mission_id = line.split(":", 1)[1].strip()
        elif line.startswith("## Goal"):
            in_goal = True
            continue
        elif in_goal and line.strip():
            if line.startswith("##") or line.startswith("#"):
                in_goal = False
            else:
                goal_lines.append(line.strip())
        elif "**Directory:**" in line and "`" in line:
            target_dir = line.split("`")[1]
    goal = " ".join(goal_lines)

    # Load endpoints.yaml
    endpoints_path = os.path.join(payload_dir, "endpoints.yaml")
    with open(endpoints_path) as f:
        endpoints = yaml.safe_load(f) or {}

    # Load sub-ninjas
    sub_ninjas = {}
    sub_dir = os.path.join(payload_dir, "sub-ninjas")
    for filename in sorted(os.listdir(sub_dir)):
        if filename.endswith(".yaml"):
            with open(os.path.join(sub_dir, filename)) as f:
                data = yaml.safe_load(f)
            role = data["role"]
            sub_ninjas[role] = SubNinjaConfig(
                role=role,
                model=data["model"],
                fallback=data.get("fallback", ""),
                prompt=data.get("prompt", ""),
                tools=data.get("tools", []),
                mission_id=data.get("mission_id", ""),
            )

    return Payload(
        mission_id=mission_id,
        goal=goal,
        target_dir=target_dir,
        endpoints=endpoints,
        sub_ninjas=sub_ninjas,
        mission_md_raw=mission_raw,
    )
