"""Vanish protocol — synopsis → preserve → save intel → purge."""
import os
import json
import shutil
from .synopsis import generate_intel_packet
from .archive import preserve_artifacts

ARCHIVE_ROOT = os.path.expanduser("~/.hermes/shinobi/archive")


def vanish(
    result,
    payload_dir: str,
    target_dir: str = None,
    archive_dir: str = None,
    purge: bool = True,
) -> dict:
    """Execute the full vanish protocol.

    1. Generate intel packet (synopsis)
    2. Preserve artifacts to archive
    3. Save intel packet to archive
    4. Purge payload directory (if purge=True)

    Returns the intel packet dict.
    """
    # 1. Synopsis
    intel = generate_intel_packet(result)

    # Determine archive directory
    if archive_dir is None:
        archive_dir = os.path.join(ARCHIVE_ROOT, result.mission_id)
    os.makedirs(archive_dir, exist_ok=True)

    # 2. Preserve artifacts from all sub-agents
    target = target_dir or "/tmp"
    all_files = []
    for pkt in result.packets:
        all_files.extend(pkt.files_changed)

    if all_files:
        preserved = preserve_artifacts(all_files, target, archive_dir)
        intel["artifacts_preserved"] = preserved

    # 3. Save intel packet to archive
    intel_path = os.path.join(archive_dir, "intel.json")
    with open(intel_path, "w") as f:
        json.dump(intel, f, indent=2)
    intel["intel_saved_to"] = intel_path

    # 4. Purge payload directory
    if purge and os.path.isdir(payload_dir):
        shutil.rmtree(payload_dir)
    intel["payload_purged"] = purge

    return intel
