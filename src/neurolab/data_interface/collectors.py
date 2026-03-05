from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .hashing import hash_file_sha256, hash_manifest_id
from .models import Artifact, DataSourceSpec, Manifest, utc_now


class ArtifactCollector(Protocol):
    """Protocol for artifact collectors."""

    def collect(self, source: DataSourceSpec) -> Manifest: ...


# Extension -> MIME type mapping for basic inference; not meant to be comprehensive.
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


def _infer_media_type(path: Path) -> str | None:
    """Return the MIME type for a file extension, or None if unknown."""
    return _MEDIA_BY_EXT.get(path.suffix.lower())


def _any_pattern_matches(path: Path, patterns: list[str]) -> bool:
    return any(path.match(pat) for pat in patterns)


def _matches_any(path: Path, patterns: list[str] | None) -> bool:
    """Return True if path matches ANY pattern; if patterns is None/empty, True."""
    if not patterns:
        return True
    return _any_pattern_matches(path, patterns)


def _excluded(path: Path, patterns: list[str] | None) -> bool:
    """Return True if path matches ANY exclude pattern; if patterns is None/empty, False."""
    if not patterns:
        return False
    return _any_pattern_matches(path, patterns)


@dataclass
class FilesystemCollector:
    """Collect artifacts from the local filesystem.

    Supports single-file and directory sources with optional recursive traversal
    and include/exclude glob patterns. Gathers metadata (size, mtime, content hash,
    media type) for each discovered file.
    """

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
            manifest_id=hash_manifest_id(artifacts),
            source=source,
            created_at=utc_now(),
            artifacts=artifacts,
            warnings=warnings,
        )
