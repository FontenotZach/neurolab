from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .hashing import hash_file_sha256
from .models import Artifact, DataSourceSpec, Manifest, utc_now

"""
Protocol for artifact collectors.
"""


class ArtifactCollector(Protocol):
    def collect(self, source: DataSourceSpec) -> Manifest: ...


# Simple extension -> media (MIME) type mapping; used for basic inference but can be overridden
#   by user-provided metadata.
# Note: this is not meant to be comprehensive, just cover common cases. For more robust inference,
#    users can provide explicit media types in metadata or use custom collectors.
_MEDIA_BY_EXT: dict[str, str] = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".parquet": "application/parquet",
    ".feather": "application/vnd.apache.arrow.file",
    ".arrow": "application/vnd.apache.arrow.file",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".sqlite": "application/x-sqlite3",
    ".db": "application/x-sqlite3",
    ".pkl": "application/octet-stream",
    ".pickle": "application/octet-stream",
    ".zip": "application/zip",
    ".gz": "application/gzip",
    ".tar": "application/x-tar",
}

"""
Helper function to infer media type from file extension. Returns None if unknown. 
    This is used in the FilesystemCollector to populate the media_type field of Artifacts.
"""


def _infer_media_type(path: Path) -> str | None:
    return _MEDIA_BY_EXT.get(path.suffix.lower())


"""
Helper function to check if a path matches ANY of the provided glob patterns. 
    If patterns is None or empty, it returns True (i.e., no filtering). 
    This is used in the FilesystemCollector to apply include_globs rules.
"""


def _matches_any(path: Path, patterns: list[str] | None) -> bool:
    """Return True if path matches ANY pattern; if patterns is None/empty, True."""
    if not patterns:
        return True
    # Path.match supports glob-style patterns; use both basename and full path.
    # Most useful patterns: "**/*.csv", "*.json", etc.
    s = path.as_posix()
    for pat in patterns:
        if path.match(pat) or Path(s).match(pat):
            return True
    return False


"""
Return True if path matches ANY exclude pattern; if patterns is None/empty, False.
"""


def _excluded(path: Path, patterns: list[str] | None) -> bool:
    """Return True if path matches ANY exclude pattern."""
    if not patterns:
        return False
    s = path.as_posix()
    for pat in patterns:
        if path.match(pat) or Path(s).match(pat):
            return True
    return False


"""
Helper function to get mtime as timezone-aware UTC datetime. Returns None if stat fails 
    (e.g., due to permissions issues). This is used in the FilesystemCollector to populate
    the mtime field of Artifacts.
"""


def _mtime_utc(path: Path) -> datetime | None:
    """Return timezone-aware UTC mtime (or None if stat fails)."""
    st = path.stat()
    return datetime.fromtimestamp(st.st_mtime, tz=UTC)


"""
FilesystemCollector is a simple implementation of ArtifactCollector that collects artifacts 
    from the local filesystem. It supports both single-file and directory sources, 
    with optional recursive traversal and include/exclude glob patterns. For each collected
    file, it gathers metadata such as size, mtime, content hash (optional), and media type 
    (inferred from extension). Any warnings encountered during collection are included in 
    the resulting Manifest.
- compute_hash: Whether to compute a content hash for each file (default: True).
- source.uri: The filesystem path to collect from (can be a file or directory).
- source.include_globs: Optional list of glob patterns to include (e.g., ["**/*.csv"]).
- source.exclude_globs: Optional list of glob patterns to exclude (e.g., ["**/__pycache__/**"]).
- source.recursive: Whether to search directories recursively (default: True).
- source.hints: Optional dictionary for additional discovery hints
"""


@dataclass
class FilesystemCollector:
    def collect(self, source: DataSourceSpec) -> Manifest:
        if source.source_type != "filesystem":
            raise ValueError(f"FilesystemCollector cannot handle source_type={source.source_type}")

        root = Path(source.uri).expanduser()
        warnings: list[str] = []
        artifacts: list[Artifact] = []

        def try_add_file(p: Path, base_root: Path | None) -> None:
            # Apply include/exclude rules
            if _excluded(p, source.exclude_globs):
                return
            if not _matches_any(p, source.include_globs):
                return

            try:
                st = p.stat()
                size_bytes = st.st_size
                mtime = datetime.fromtimestamp(st.st_mtime, tz=UTC)
            except Exception as e:
                warnings.append(f"stat failed for {p}: {e}")
                return

            content_hash: str | None = None
            if source.compute_hash:
                try:
                    content_hash = hash_file_sha256(p)
                except Exception as e:
                    warnings.append(f"hash failed for {p}: {e}")

            rel_path: str | None
            abs_path = str(p.resolve())
            if base_root is not None:
                try:
                    rel_path = str(p.resolve().relative_to(base_root.resolve()))
                except Exception:
                    # Fallback (should be rare)
                    rel_path = str(p.name)
            else:
                rel_path = None  # single-file sources don't need a relative path

            artifacts.append(
                Artifact(
                    artifact_id=str(uuid4()),
                    source_uri=source.uri,
                    artifact_type="file",
                    relative_path=rel_path,
                    absolute_path=abs_path,
                    size_bytes=size_bytes,
                    mtime=mtime,
                    content_hash=content_hash,
                    media_type=_infer_media_type(p),
                    tags={},
                )
            )

        # Case 1: source points to a file
        if root.is_file():
            try_add_file(root, base_root=None)

        # Case 2: source points to a directory
        elif root.is_dir():
            # Walk files
            try:
                if source.recursive:
                    iterator = root.rglob("*")
                else:
                    iterator = root.glob("*")
            except Exception as e:
                warnings.append(f"failed to list directory {root}: {e}")
                iterator = []

            for p in iterator:
                # skip directories/symlinks-to-dirs etc; only collect regular files
                try:
                    if p.is_file():
                        try_add_file(p, base_root=root)
                except Exception as e:
                    warnings.append(f"failed to inspect path {p}: {e}")

        else:
            warnings.append(f"source uri does not exist or is not accessible: {root}")

        artifacts.sort(key=lambda a: a.relative_path or "")

        return Manifest(
            manifest_id=str(uuid4()),
            source=source,
            created_at=utc_now(),
            artifacts=artifacts,
            warnings=warnings,
        )
