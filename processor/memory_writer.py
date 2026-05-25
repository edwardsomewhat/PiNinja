"""Extract memory-worthy entries from intel packets."""


def extract_memory_entries(packet: dict) -> list:
    """Extract memory entries from an intel packet.

    Returns list of dicts with: type, content
    """
    entries = []

    # Lessons → memory
    for lesson in packet.get("lessons", []):
        entries.append({
            "type": "lesson",
            "content": f"[{packet['mission_id']}] {lesson}",
        })

    # Model performance patterns
    perf = packet.get("performance", {}).get("by_model", {})
    if perf:
        perf_lines = [f"Mission {packet['mission_id']} model performance:"]
        for model, stats in perf.items():
            calls = stats.get("calls", 0)
            successes = stats.get("successes", 0)
            rate = (successes / calls * 100) if calls > 0 else 0
            perf_lines.append(
                f"  {model}: {successes}/{calls} succeeded "
                f"({rate:.0f}%), {stats.get('total_seconds', 0):.1f}s"
            )
        entries.append({
            "type": "performance",
            "content": "\n".join(perf_lines),
        })

    # Architecture changes worth remembering
    arch = packet.get("architecture", {})
    new_modules = arch.get("new_modules", [])
    if new_modules:
        entries.append({
            "type": "architecture",
            "content": (
                f"[{packet['mission_id']}] New modules created: "
                f"{', '.join(new_modules)}"
            ),
        })

    return entries
