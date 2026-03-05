from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from neurolab.data_interface.models import Manifest


class ManifestStore(Protocol):
    """
    Protocol for persisting and retrieving manifests.
    Implementations must support save, load, list, and delete.
    """

    def save(self, manifest: Manifest) -> None:
        """Persist a manifest. Overwrites if manifest_id already exists."""
        ...

    def load(self, manifest_id: str) -> Manifest:
        """Load a manifest by ID. Raises FileNotFoundError if not found."""
        ...

    def list(self) -> list[str]:
        """Return the list of stored manifest IDs."""
        ...

    def delete(self, manifest_id: str) -> None:
        """Remove a manifest by ID. Raises FileNotFoundError if not found."""
        ...


class FileManifestStore:
    """
    Stores manifests locally as JSON files under ~/.neurolab/data/manifests/.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize store; base_dir defaults to ~/.neurolab/data/manifests."""
        self.base_dir = base_dir if base_dir is not None else Path.home() / ".neurolab" / "data" / "manifests"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, manifest_id: str) -> Path:
        """Return the filesystem path for a given manifest_id."""
        return self.base_dir / f"{manifest_id}.json"

    def _resolve_id(self, manifest_id: str) -> str:
        """Resolve a full or prefix manifest ID to the unique full ID.

        Raises FileNotFoundError if no match, ValueError if ambiguous.
        """
        if self._path(manifest_id).exists():
            return manifest_id

        matches = [p.stem for p in self.base_dir.glob(f"{manifest_id}*.json") if p.is_file()]

        if len(matches) == 0:
            raise FileNotFoundError(f"Manifest {manifest_id} not found")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous prefix '{manifest_id}' matches {len(matches)} manifests — use more characters")
        return matches[0]

    def save(self, manifest: Manifest) -> None:
        """Persist manifest as JSON; overwrites existing file for same manifest_id."""
        path = self._path(manifest.manifest_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def load(self, manifest_id: str) -> Manifest:
        """Load manifest by ID or unique prefix; raises FileNotFoundError if not found."""
        resolved = self._resolve_id(manifest_id)
        path = self._path(resolved)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return Manifest.from_dict(data)

    def list(self) -> list[str]:
        """Return manifest IDs for all stored manifests."""
        return [p.stem for p in self.base_dir.glob("*.json") if p.is_file()]

    def delete(self, manifest_id: str) -> None:
        """Remove manifest file by ID or unique prefix; raises FileNotFoundError if not found."""
        resolved = self._resolve_id(manifest_id)
        self._path(resolved).unlink()
