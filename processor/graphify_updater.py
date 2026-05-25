"""Generate graphify CLI commands from intel packets."""


def generate_graphify_commands(
    packet: dict, target_dir: str = "."
) -> list:
    """Generate graphify CLI commands from an intel packet."""
    commands = []

    gf = packet.get("graphify", {})
    arch = packet.get("architecture", {})

    new_files = gf.get("new_files", []) or []
    if not new_files and arch.get("new_files"):
        new_files = [{"path": f} for f in arch["new_files"]]

    if new_files:
        paths = " ".join(
            f'"{f["path"]}"' for f in new_files[:20]
        )
        commands.append(f"graphify update {target_dir} --files {paths}")

    relationships = gf.get("relationships", [])
    for rel in relationships[:50]:
        from_path = rel.get("from", "")
        to_path = rel.get("to", "")
        rel_type = rel.get("type", "related")
        if from_path and to_path:
            commands.append(
                f'graphify relate "{from_path}" "{to_path}" --type {rel_type}'
            )

    return commands
