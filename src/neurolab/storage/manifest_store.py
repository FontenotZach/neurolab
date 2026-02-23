from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from neurolab.data_interface.models import Manifest


class ManifestStore(Protocol):
    def save(self, manifest: Manifest) -> None: ...
    def load(self, manifest_id: str) -> Manifest: ...
    def list(self) -> list[str]: ...


class FileManifestStore:
    """
    Stores manifests locally as JSON files under ~/.neurolab/data/manifests/.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir if base_dir is not None else Path.home() / ".neurolab" / "data" / "manifests"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, manifest_id: str) -> Path:
        return self.base_dir / f"{manifest_id}.json"

    def save(self, manifest: Manifest) -> None:
        path = self._path(manifest.manifest_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def load(self, manifest_id: str) -> Manifest:
        path = self._path(manifest_id)
        if not path.exists():
            raise FileNotFoundError(f"Manifest {manifest_id} not found")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return Manifest.from_dict(data)

    def list(self) -> list[str]:
        return [p.stem for p in self.base_dir.glob("*.json") if p.is_file()]

    def delete(self, manifest_id: str) -> None:
        path = self._path(manifest_id)
        if not path.exists():
            raise FileNotFoundError(f"Manifest {manifest_id} not found")
        path.unlink()
