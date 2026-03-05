from __future__ import annotations

import json
from pathlib import Path


class RosterStore:
    """
    Stores a small mapping of aliases (e.g. r1, r2) to manifest IDs in a JSON file.
    Path defaults to ~/.neurolab/data/roster.json.
    """

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = Path.home() / ".neurolab" / "data" / "roster.json"
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, str]:
        """Read alias -> manifest_id from JSON. Returns {} if file is missing."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def save(self, entries: dict[str, str]) -> None:
        """Write alias -> manifest_id mapping to JSON."""
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    def get(self, alias: str) -> str | None:
        """Return manifest_id for alias, or None if not in roster."""
        return self.load().get(alias)

    def add(self, alias: str, manifest_id: str) -> None:
        """Add or overwrite alias -> manifest_id and persist."""
        entries = self.load()
        entries[alias] = manifest_id
        self.save(entries)

    def remove(self, alias: str) -> None:
        """Remove alias from roster and persist. No-op if alias not present."""
        entries = self.load()
        entries.pop(alias, None)
        self.save(entries)

    def next_slot(self) -> str:
        """Return first free alias in r1, r2, r3, ..."""
        entries = self.load()
        n = 1
        while f"r{n}" in entries:
            n += 1
        return f"r{n}"
