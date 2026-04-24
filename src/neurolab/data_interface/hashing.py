from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


def hash_artifact_id(
    *,
    content_hash: str | None,
    relative_path: str | None,
    absolute_path: str | None = None,
    size_bytes: int | None = None,
) -> str:
    """
    Deterministic artifact identity for filesystem artifacts.

    Incorporates ``content_hash`` and a path key: ``relative_path`` when present,
    otherwise the basename of ``absolute_path`` (for single-file sources where
    ``relative_path`` is unset in the model).

    When ``content_hash`` is unavailable (e.g. hashing disabled or failed),
    ``size_bytes`` may be used as a weaker fallback (with a warning).
    """
    path_key = relative_path
    if path_key is None and absolute_path:
        path_key = str(Path(absolute_path).name)

    parts: dict[str, Any] = {}
    if content_hash is not None:
        parts["content_hash"] = content_hash
    else:
        warnings.warn(
            "artifact_id: content_hash unavailable; using size_bytes only (weaker identity). "
            "Keep compute_hash=True on DataSourceSpec for stable artifact_id.",
            UserWarning,
            stacklevel=2,
        )
        if size_bytes is not None:
            parts["size_bytes"] = int(size_bytes)
    if path_key is not None:
        parts["relative_path"] = path_key
    else:
        warnings.warn(
            "artifact_id: no relative_path or basename available; identity may be unstable.",
            UserWarning,
            stacklevel=2,
        )

    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
