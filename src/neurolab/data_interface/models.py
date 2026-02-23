"""
Data Interface Layer - Artifact Collection Models (MVP)

RULES:
- This layer only DISCOVERS artifacts; it does not parse schemas or load dataframes.
- Keep models serializable with to_dict()/from_dict().
- Use UTC timezone-aware datetimes.
- Do not add fields beyond what is defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


"""
DataSourceSpec defines the parameters for discovering artifacts from a data source.
- uri: The URI of the data source (e.g., file path, database connection string).
- source_type: The type of data source (currently only "filesystem" is supported).
- include_globs: Optional list of glob patterns to include (e.g., ["*.csv"]).
- exclude_globs: Optional list of glob patterns to exclude (e.g., ["*.tmp"]).
- recursive: Whether to search directories recursively (default: True).
- hints: Optional dictionary for additional discovery hints (e.g., {"follow_symlinks": True}).
"""


@dataclass(frozen=True)
class DataSourceSpec:
    uri: str
    source_type: Literal["filesystem"] = "filesystem"
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None
    compute_hash: bool = True
    recursive: bool = True
    hints: dict[str, Any] = field(default_factory=dict)

    """to_dict serializes the DataSourceSpec instance to a dictionary."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "source_type": self.source_type,
            "include_globs": self.include_globs,
            "exclude_globs": self.exclude_globs,
            "recursive": self.recursive,
            "hints": self.hints,
        }

    """from_dict validates the input dictionary and constructs a DataSourceSpec instance."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DataSourceSpec:
        if not isinstance(d, dict):
            raise TypeError("Input must be a dictionary")
        if "uri" not in d:
            raise ValueError("Missing required field: uri")

        source_type = d.get("source_type", "filesystem")
        if source_type not in ("filesystem",):
            raise ValueError(f"Invalid source_type: {source_type}")

        return cls(
            uri=d["uri"],
            source_type=source_type,
            include_globs=d.get("include_globs"),
            exclude_globs=d.get("exclude_globs"),
            recursive=d.get("recursive", True),
            hints=d.get("hints", {}),
        )


"""
Artifact represents a discovered artifact from a data source.
- source_uri: The original URI where the artifact was discovered.
- artifact_type: The type of artifact (e.g., "file", "db_table").
- relative_path: The path of the artifact relative to the data source root (if applicable).
- absolute_path: The absolute path of the artifact (if applicable).
- size_bytes: The size of the artifact in bytes (if applicable).
- mtime: The last modified time of the artifact (if applicable).
- content_hash: A hash of the artifact's content for change detection (if applicable).
- media_type: The media type of the artifact (e.g., "text/csv", "application/json") (if applicable).
- artifact_id: A unique identifier for the artifact (defaults to a UUID).
- tags: Optional dictionary of tags for additional metadata.
"""


@dataclass(frozen=True)
class Artifact:
    source_uri: str
    artifact_type: Literal["file", "db_table"]
    relative_path: str | None
    absolute_path: str | None
    size_bytes: int | None
    mtime: datetime | None
    content_hash: str | None
    media_type: str | None

    # TODO: Diff identity currently uses `relative_path` for filesystem artifacts.
    # When adding non-filesystem collectors (e.g., database, API, S3),
    # introduce a generalized `identity_key` field or method so diffing
    # does not depend on filesystem-specific structure.

    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    tags: dict[str, str] = field(default_factory=dict)

    """to_dict serializes the Artifact instance to a dictionary."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source_uri": self.source_uri,
            "artifact_type": self.artifact_type,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "size_bytes": self.size_bytes,
            "mtime": self.mtime.isoformat() if self.mtime else None,
            "content_hash": self.content_hash,
            "media_type": self.media_type,
            "tags": self.tags,
        }

    """from_dict validates the input dictionary and constructs an Artifact instance."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Artifact:
        if not isinstance(d, dict):
            raise TypeError("Input must be a dictionary")
        if "artifact_id" not in d:
            raise ValueError("Missing required field: artifact_id")
        if "source_uri" not in d:
            raise ValueError("Missing required field: source_uri")
        if "artifact_type" not in d:
            raise ValueError("Missing required field: artifact_type")

        artifact_type = d["artifact_type"]
        if artifact_type not in ("file", "db_table"):
            raise ValueError(f"Invalid artifact_type: {artifact_type}")

        mtime_iso = d.get("mtime")
        mtime = datetime.fromisoformat(mtime_iso) if mtime_iso else None
        if mtime and mtime.tzinfo is None:
            raise ValueError("mtime must be timezone-aware")

        return cls(
            artifact_id=d["artifact_id"],
            source_uri=d["source_uri"],
            artifact_type=artifact_type,
            relative_path=d.get("relative_path"),
            absolute_path=d.get("absolute_path"),
            size_bytes=d.get("size_bytes"),
            mtime=mtime,
            content_hash=d.get("content_hash"),
            media_type=d.get("media_type"),
            tags=dict(d.get("tags", {})),
        )


"""
Manifest represents the result of an artifact discovery process.
- manifest_id: A unique identifier for the manifest (defaults to a UUID).
- source: The DataSourceSpec that was used for discovery.
- created_at: The timestamp when the manifest was created (in UTC).
- artifacts: A list of discovered Artifact instances.
- warnings: Optional list of warning messages encountered during discovery.
"""


@dataclass(frozen=True)
class Manifest:
    manifest_id: str
    source: DataSourceSpec
    created_at: datetime
    artifacts: list[Artifact]
    warnings: list[str] = field(default_factory=list)

    """artifact_count returns the number of artifacts in the manifest."""

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    """to_dict serializes the Manifest instance to a dictionary."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source": self.source.to_dict(),
            "created_at": self.created_at.isoformat(),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "warnings": self.warnings,
        }

    """from_dict validates the input dictionary and constructs a Manifest instance."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Manifest:
        if not isinstance(d, dict):
            raise TypeError("Input must be a dictionary")
        if "manifest_id" not in d:
            raise ValueError("Missing required field: manifest_id")
        if "source" not in d:
            raise ValueError("Missing required field: source")
        if "created_at" not in d:
            raise ValueError("Missing required field: created_at")
        if "artifacts" not in d:
            raise ValueError("Missing required field: artifacts")

        source = DataSourceSpec.from_dict(d["source"])
        created_at = datetime.fromisoformat(d["created_at"])
        if created_at and created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        artifacts = [Artifact.from_dict(artifact) for artifact in d["artifacts"]]

        return cls(
            manifest_id=d["manifest_id"],
            source=source,
            created_at=created_at,
            artifacts=artifacts,
            warnings=d.get("warnings", []),
        )
