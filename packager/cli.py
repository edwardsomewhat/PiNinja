#!/usr/bin/env python3
"""Shinobi Packager CLI — assemble deployable Shinobi payloads."""
import sys
import argparse

# Allow running as both `python -m packager.cli` and `python cli.py`
if __name__ == "__main__" and __package__ is None:
    import os
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _parent)
    __package__ = "packager"

from .spec import parse_spec
from .models import ModelRegistry
from .generator import generate_payload


def main():
    parser = argparse.ArgumentParser(
        description="Shinobi Packager — assemble deployable Shinobi payloads"
    )
    parser.add_argument(
        "spec_file",
        nargs="?",
        help="Path to task spec file (JSON or YAML). If omitted, reads from stdin."
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for the Shinobi payload"
    )
    args = parser.parse_args()

    # Read spec
    if args.spec_file:
        with open(args.spec_file) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("Error: no input provided", file=sys.stderr)
        sys.exit(1)

    # Parse and generate
    try:
        spec = parse_spec(raw)
        registry = ModelRegistry()
        generate_payload(spec, registry, args.output)
        print(f"Shinobi payload generated: {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
