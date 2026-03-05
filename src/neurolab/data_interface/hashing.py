from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurolab.data_interface.models import Artifact


def hash_file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute the SHA-256 hash of a file's contents.
    Reads the file in chunks (default 1 MiB) to support large files without loading
    the entire file into memory. Returns the hex digest.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_manifest_id(artifacts: list[Artifact]) -> str:
    """
    Compute a deterministic manifest ID from the discovered artifacts.
    Same set of artifacts (content identity only) always yields the same ID.
    Uses only content_hash and size_bytes; paths and mtime are ignored.
    """

    def canonical_entry(a: Artifact) -> dict:
        return {
            "content_hash": a.content_hash,
            "size_bytes": a.size_bytes,
        }

    sorted_artifacts = sorted(
        artifacts,
        key=lambda a: (a.content_hash or "", a.size_bytes or 0),
    )
    payload = [canonical_entry(a) for a in sorted_artifacts]
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
