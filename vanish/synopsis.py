"""Intel packet generation from MissionResult."""
import os
from datetime import datetime, timezone
from collections import defaultdict
from spawner.packet import PacketStatus
from spawner.dispatcher import MissionResult


def generate_intel_packet(
    result: MissionResult, target_dir: str = None
) -> dict:
    """Generate a rich, forensic-level intel packet from a MissionResult."""

    # Overall status
    status = "PASS" if result.all_passed() else "FAILED"

    # Subtasks with full forensic output
    subtasks = _build_subtasks(result)

    # Models used (deduplicated, preserving order)
    seen = set()
    models_used = []
    for pkt in result.packets:
        if pkt.model not in seen:
            models_used.append(pkt.model)
            seen.add(pkt.model)

    # Performance by model
    performance = _build_performance(result)

    # Architecture
    architecture = _build_architecture(result)

    # Graphify data
    graphify = _build_graphify(result)

    # QC section
    qc = _build_qc(result)

    # Recovery history
    recovery = _build_recovery(result)

    # Target info
    target = _build_target(target_dir)

    # Lessons
    lessons = _extract_lessons(result)

    return {
        "mission_id": result.mission_id,
        "status": status,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        ),
        "target": target,
        "subtasks": subtasks,
        "recovery": recovery,
        "performance": performance,
        "qc": qc,
        "architecture": architecture,
        "graphify": graphify,
        "duration_seconds": performance["total_duration_seconds"],
        "models_used": models_used,
        "lessons": lessons,
    }


def _build_subtasks(result: MissionResult) -> list:
    subtasks = []
    for i, pkt in enumerate(result.packets):
        subtasks.append({
            "id": chr(65 + i),
            "agent": pkt.role,
            "model": pkt.model,
            "status": pkt.status.value,
            "files": pkt.files_changed,
            "errors": pkt.errors,
            "duration_seconds": pkt.duration_seconds,
            "output": pkt.output,  # Full raw output
        })
    return subtasks


def _build_performance(result: MissionResult) -> dict:
    by_model = defaultdict(lambda: {
        "calls": 0, "total_seconds": 0.0, "successes": 0, "failures": 0
    })
    total = 0.0

    for pkt in result.packets:
        stats = by_model[pkt.model]
        stats["calls"] += 1
        stats["total_seconds"] += pkt.duration_seconds
        if pkt.status == PacketStatus.PASS:
            stats["successes"] += 1
        elif pkt.status in (PacketStatus.REJECT, PacketStatus.ERROR):
            stats["failures"] += 1
        total += pkt.duration_seconds

    # Round all values
    for model in by_model:
        by_model[model]["total_seconds"] = round(
            by_model[model]["total_seconds"], 1
        )

    return {
        "total_duration_seconds": round(total, 1),
        "by_model": dict(by_model),
        "fallbacks_used": 0,  # Stub — Phase 5
    }


def _build_architecture(result: MissionResult) -> dict:
    all_files = []
    for pkt in result.packets:
        all_files.extend(pkt.files_changed)

    # Deduplicate
    seen = set()
    new_files = [f for f in all_files if not (f in seen or seen.add(f))]

    # Extract module names (first directory component)
    modules = set()
    for f in new_files:
        parts = f.split("/")
        if len(parts) > 1:
            modules.add(parts[0])

    # Generate ASCII diagram
    diagram = _generate_architecture_diagram(new_files)

    return {
        "new_files": new_files,
        "modified_files": [],  # Stub — Phase 6
        "new_modules": sorted(modules),
        "dependencies_added": [],  # Stub — Phase 6
        "diagram": diagram,
    }


def _generate_architecture_diagram(files: list) -> str:
    """Generate a simple ASCII tree diagram from file paths."""
    if not files:
        return "(no files changed)"

    # Build a tree structure
    tree = {}
    for f in sorted(files):
        parts = f.split("/")
        node = tree
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[parts[-1]] = None

    lines = []
    _render_tree(tree, lines, "")
    return "\n".join(lines)


def _render_tree(node: dict, lines: list, prefix: str):
    """Recursively render a tree to ASCII."""
    items = list(node.items())
    for i, (name, children) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}")
        if children is not None and isinstance(children, dict):
            new_prefix = prefix + ("    " if is_last else "│   ")
            _render_tree(children, lines, new_prefix)


def _build_graphify(result: MissionResult) -> dict:
    """Build graphify-compatible data from changed files."""
    new_files = []
    for pkt in result.packets:
        for f in pkt.files_changed:
            # Detect language from extension
            ext = f.rsplit(".", 1)[-1] if "." in f else "unknown"
            lang_map = {
                "py": "python", "js": "javascript", "ts": "typescript",
                "yaml": "yaml", "yml": "yaml", "json": "json",
                "md": "markdown", "toml": "toml", "sh": "bash",
            }
            language = lang_map.get(ext, ext)

            entry = {
                "path": f,
                "language": language,
            }

            # Basic import/export detection from agent output
            if pkt.output:
                if "import" in pkt.output.lower():
                    entry["imports"] = _extract_imports(pkt.output)
                if "def " in pkt.output or "class " in pkt.output:
                    entry["exports"] = _extract_exports(pkt.output)

            new_files.append(entry)

    # Deduplicate by path
    seen = set()
    unique = []
    for f in new_files:
        if f["path"] not in seen:
            unique.append(f)
            seen.add(f["path"])

    # Build relationships
    relationships = _build_relationships(unique)

    return {
        "new_files": unique,
        "relationships": relationships,
    }


def _extract_imports(output: str) -> list:
    """Extract import statements from agent output."""
    imports = []
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)
    return imports[:20]


def _extract_exports(output: str) -> list:
    """Extract function/class definitions from agent output."""
    exports = []
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("def ") or line.startswith("class "):
            name = line.split("(")[0].replace("def ", "").replace("class ", "")
            exports.append(name.strip())
    return exports[:20]


def _build_relationships(graphify_files: list) -> list:
    """Build relationship entries from graphify file data."""
    rels = []
    for gf in graphify_files:
        imports = gf.get("imports", [])
        for imp in imports:
            # Extract module name from import statement
            if imp.startswith("from "):
                module = imp.split(" from ")[-1].split(" import")[0].strip()
            elif imp.startswith("import "):
                module = imp.replace("import ", "").split(" as ")[0].strip()
            else:
                continue
            rels.append({
                "from": gf["path"],
                "to": module.replace(".", "/") + ".py",
                "type": "imports",
            })
    return rels[:50]


def _build_qc(result: MissionResult) -> dict:
    qa_pkt = next((p for p in result.packets if p.role == "qa"), None)
    review_pkt = next(
        (p for p in result.packets if p.role == "reviewer"), None
    )

    all_issues = []
    for pkt in result.packets:
        all_issues.extend(pkt.errors)

    qc_verdict = "PASS"
    if result.failed():
        last_pkt = result.packets[-1]
        if last_pkt.status == PacketStatus.REJECT:
            qc_verdict = "REJECT"
        elif last_pkt.status == PacketStatus.ERROR:
            qc_verdict = "ERROR"
        else:
            qc_verdict = "FLAG"

    return {
        "model": (
            qa_pkt.model
            if qa_pkt
            else (review_pkt.model if review_pkt else "unknown")
        ),
        "verdict": qc_verdict,
        "issues": all_issues,
        "qa_output": qa_pkt.output if qa_pkt else "",
    }


def _build_recovery(result: MissionResult) -> dict:
    if result.recovery:
        return result.recovery
    return {
        "attempts": 0,
        "diagnosticians_spawned": 0,
        "diagnoses": [],
    }


def _build_target(target_dir: str = None) -> dict:
    import socket
    return {
        "directory": target_dir or "/tmp",
        "hostname": socket.gethostname(),
    }


def _extract_lessons(result: MissionResult) -> list:
    """Extract lessons learned from the mission result."""
    lessons = []

    for pkt in result.packets:
        if pkt.role == "scout" and pkt.status == PacketStatus.PASS:
            output_lower = pkt.output.lower()
            if "found" in output_lower or "existing" in output_lower:
                lessons.append(
                    f"Scout identified reusable patterns: {pkt.output[:120]}"
                )

    for pkt in result.packets:
        if pkt.errors and pkt.status in (
            PacketStatus.REJECT,
            PacketStatus.ERROR,
        ):
            lessons.append(f"{pkt.role} failed with: {pkt.errors[0][:120]}")

    return lessons[:5]
