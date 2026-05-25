"""Generate human-readable mission summary from intel packets."""


def generate_session_summary(packet: dict) -> str:
    """Generate a markdown session summary from an intel packet."""
    lines = []

    lines.append(f"# Mission: {packet['mission_id']}")
    lines.append(f"**Status:** {packet['status']}")
    lines.append(f"**Duration:** {packet.get('performance', {}).get('total_duration_seconds', 0):.1f}s")
    lines.append("")

    # Models used
    models = packet.get("models_used", [])
    if models:
        lines.append("## Models Used")
        for m in models:
            lines.append(f"- {m}")
        lines.append("")

    # Subtask summary
    subtasks = packet.get("subtasks", [])
    if subtasks:
        lines.append("## Subtasks")
        for st in subtasks:
            status_icon = "✓" if st["status"] == "PASS" else "✗"
            lines.append(
                f"- **{st['id']}: {st['agent']}** ({st['model']}) "
                f"— {status_icon} {st['status']} ({st['duration_seconds']:.1f}s)"
            )
            if st.get("errors"):
                for err in st["errors"]:
                    lines.append(f"  - Error: {err}")
            if st.get("files"):
                lines.append(f"  - Files: {', '.join(st['files'])}")
        lines.append("")

    # Architecture diagram
    arch = packet.get("architecture", {})
    diagram = arch.get("diagram", "")
    if diagram:
        lines.append("## Architecture")
        lines.append("```")
        lines.append(diagram)
        lines.append("```")
        lines.append("")

    # New files
    new_files = arch.get("new_files", [])
    if new_files:
        lines.append("## Files Changed")
        for f in new_files:
            lines.append(f"- `{f}`")
        lines.append("")

    # QC
    qc = packet.get("qc", {})
    lines.append("## QC")
    lines.append(f"- Verdict: **{qc.get('verdict', 'N/A')}**")
    issues = qc.get("issues", [])
    if issues:
        for issue in issues:
            lines.append(f"- Issue: {issue}")
    lines.append("")

    # Lessons
    lessons = packet.get("lessons", [])
    if lessons:
        lines.append("## Lessons Learned")
        for lesson in lessons:
            lines.append(f"- {lesson}")
        lines.append("")

    # Performance
    perf = packet.get("performance", {}).get("by_model", {})
    if perf:
        lines.append("## Performance")
        for model, stats in perf.items():
            calls = stats.get("calls", 0)
            successes = stats.get("successes", 0)
            lines.append(
                f"- **{model}**: {successes}/{calls} succeeded, "
                f"{stats.get('total_seconds', 0):.1f}s"
            )

    return "\n".join(lines)
