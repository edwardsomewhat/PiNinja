"""Payload generator — produces the Shinobi payload directory."""
import os
import shutil
import yaml
from datetime import datetime, timezone
from .spec import TaskSpec
from .models import ModelRegistry

SUB_NINJA_TOOLS = {
    "scout": ["read_file", "search_files", "web_search", "web_extract", "graphify"],
    "coder": ["read_file", "write_file", "patch", "search_files", "terminal"],
    "builder": ["terminal", "write_file", "patch", "read_file"],
    "reviewer": ["read_file", "search_files", "patch"],
    "qa": ["read_file", "terminal", "search_files"],
}

SUB_NINJA_PROMPTS = {
    "scout": (
        "You are a Shinobi Scout. Your job: find existing patterns, conventions, "
        "and reusable code in the target codebase before coding begins. "
        "Read the MISSION.md, explore the codebase, run graphify to map "
        "file relationships, and report what exists. Include a structured "
        "graphify report showing file imports and dependencies."
    ),
    "coder": (
        "You are a Shinobi Coder. Your job: write production-quality code "
        "following the plan and tests. Use TDD. Follow conventions found by the Scout. "
        "Write clean, well-documented, type-hinted Python."
    ),
    "builder": (
        "You are a Shinobi Builder. Your job: Docker, deploy, wire things up. "
        "Run builds, manage infrastructure, and verify deployments work."
    ),
    "reviewer": (
        "You are a Shinobi Reviewer. Your job: inline code review. "
        "Check every change for correctness, style, edge cases, and security. "
        "Flag issues before they compound."
    ),
    "qa": (
        "You are a Shinobi QA. Your job: final verification. "
        "Run the test suite, check outputs, verify against acceptance criteria. "
        "Produce a PASS/FLAG/REJECT verdict."
    ),
}

MISSION_MD_TEMPLATE = """# Mission: {mission_id}

> **Generated:** {generated_at}
> **Lead Shinobi:** Deploy to target, execute, report, vanish.

## Goal

{goal}

## Target

**Directory:** `{target_dir}`

## Constraints

{constraints_section}

## Acceptance Criteria

{acceptance_section}

## Context

{context}

## Skills

{skills_section}

## Execution Order

1. **Scout** explores the codebase for existing patterns
2. **Coder** writes the code (TDD)
3. **Builder** deploys and wires up
4. **Reviewer** inline QC after each step
5. **QA** final verification

## Vanish Protocol

After QA passes: produce intel packet (JSON), deliver to Pi Ninja, self-destruct.
"""


def _format_constraints(constraints) -> str:
    if constraints is None:
        return "- No specific constraints"
    lines = []
    if constraints.language:
        lines.append(f"- **Language:** {constraints.language}")
    if constraints.framework:
        lines.append(f"- **Framework:** {constraints.framework}")
    if constraints.test_framework:
        lines.append(f"- **Test Framework:** {constraints.test_framework}")
    return "\n".join(lines) if lines else "- No specific constraints"


def _format_skills(skills: list) -> str:
    if not skills:
        return "None specified"
    return "\n".join(f"- {s}" for s in skills)


def generate_payload(spec: TaskSpec, registry: ModelRegistry, output_dir: str):
    """Generate a complete Shinobi payload directory."""
    os.makedirs(output_dir, exist_ok=True)

    # Apply model preferences as overrides
    for role, model in spec.model_preferences.items():
        registry.override(role, model)

    # 1. MISSION.md
    mission_content = MISSION_MD_TEMPLATE.format(
        mission_id=spec.mission_id,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        goal=spec.goal,
        target_dir=spec.target_dir,
        constraints_section=_format_constraints(spec.constraints),
        acceptance_section="- Tests pass (pytest)\n- No regressions",
        context=spec.context or "No additional context",
        skills_section=_format_skills(spec.skills),
    )
    with open(os.path.join(output_dir, "MISSION.md"), "w") as f:
        f.write(mission_content)

    # 2. endpoints.yaml
    endpoints = registry.to_endpoints_dict()
    for role_config in endpoints.values():
        role_config.setdefault("timeout", "30s")
    with open(os.path.join(output_dir, "endpoints.yaml"), "w") as f:
        yaml.dump(endpoints, f, default_flow_style=False, sort_keys=False)

    # 3. skills/ — copy referenced skills
    skills_dir = os.path.join(output_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)
    _copy_skills(spec.skills, skills_dir)

    # 4. sub-ninjas/
    sub_ninjas_dir = os.path.join(output_dir, "sub-ninjas")
    os.makedirs(sub_ninjas_dir, exist_ok=True)
    _generate_sub_ninja_configs(spec, registry, sub_ninjas_dir)

    return output_dir


def _copy_skills(skill_names: list, target_dir: str):
    """Copy referenced skills from Hermes skills directory into payload."""
    skills_source = os.path.expanduser("~/.hermes/skills")

    for name in skill_names:
        found = False
        if os.path.isdir(skills_source):
            for root, dirs, files in os.walk(skills_source):
                if os.path.basename(root) == name:
                    dest = os.path.join(target_dir, name)
                    if not os.path.exists(dest):
                        shutil.copytree(root, dest)
                    found = True
                    break

        if not found:
            os.makedirs(os.path.join(target_dir, name), exist_ok=True)
            print(f"Warning: skill '{name}' not found locally, created stub")


def _generate_sub_ninja_configs(
    spec: TaskSpec, registry: ModelRegistry, output_dir: str
):
    """Generate sub-ninja YAML configs for each role."""
    for role in ["scout", "coder", "builder", "reviewer", "qa"]:
        endpoint = registry.get_endpoint(role)
        config = {
            "role": role,
            "model": endpoint.primary,
            "fallback": endpoint.fallback,
            "prompt": SUB_NINJA_PROMPTS.get(role, ""),
            "tools": SUB_NINJA_TOOLS.get(role, []),
            "mission_id": spec.mission_id,
        }
        config_path = os.path.join(output_dir, f"{role}.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
