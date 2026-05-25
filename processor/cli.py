#!/usr/bin/env python3
"""Processor CLI — read intel packet, produce memory/graphify/session outputs."""
import sys
import os

# Allow running as both `python -m processor.cli` and `python cli.py`
if __name__ == "__main__" and __package__ is None:
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _parent)
    __package__ = "processor"

from .parser import parse_intel_packet
from .memory_writer import extract_memory_entries
from .graphify_updater import generate_graphify_commands
from .session_archiver import generate_session_summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m processor.cli <intel.json> [--target-dir DIR]")
        sys.exit(1)

    intel_path = sys.argv[1]
    target_dir = "."

    # Parse optional args
    args = sys.argv[2:]
    while args:
        if args[0] == "--target-dir" and len(args) > 1:
            target_dir = args[1]
            args = args[2:]
        else:
            args = args[1:]

    packet = parse_intel_packet(intel_path)

    # Memory
    print("=== MEMORY ENTRIES ===")
    for entry in extract_memory_entries(packet):
        print(f"[{entry['type']}] {entry['content']}")
        print()

    # Graphify
    print("=== GRAPHIFY COMMANDS ===")
    for cmd in generate_graphify_commands(packet, target_dir):
        print(f"  $ {cmd}")

    # Session summary
    print()
    print("=== SESSION SUMMARY ===")
    print(generate_session_summary(packet))


if __name__ == "__main__":
    main()
