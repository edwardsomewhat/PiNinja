"""Artifact preservation — copy built files to archive."""
import os
import shutil


def preserve_artifacts(file_paths: list, source_root: str, archive_dir: str) -> list:
    """Copy built artifacts from source to archive. Returns list of copied paths."""
    os.makedirs(archive_dir, exist_ok=True)
    copied = []

    for rel_path in file_paths:
        src_path = os.path.join(source_root, rel_path)
        if os.path.isfile(src_path):
            dst_path = os.path.join(archive_dir, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)
            copied.append(rel_path)

    return copied
