from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurolab.output_groups.catalog import OutputGroupCatalog
from neurolab.output_groups.models import OutputGroup


class FileOutputGroupCatalogStore:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)
        self._catalog_path = self.root_dir / "output_groups" / "catalog.json"

    def save(self, catalog: OutputGroupCatalog) -> None:
        self._catalog_path.parent.mkdir(parents=True, exist_ok=True)

        groups = catalog.list()
        body = {
            "schema_version": 1,
            "groups": [_serialize_group(g) for g in groups],
        }
        text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

        tmp = self._catalog_path.with_name(self._catalog_path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self._catalog_path)

    def load(self) -> OutputGroupCatalog:
        if not self._catalog_path.is_file():
            return OutputGroupCatalog()

        raw = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("catalog.json must contain a JSON object")

        schema_version = raw.get("schema_version")
        if schema_version != 1:
            raise ValueError(f"Unsupported schema_version: {schema_version!r}")

        groups_raw = raw.get("groups")
        if not isinstance(groups_raw, list):
            raise ValueError("'groups' must be a list")

        groups: list[OutputGroup] = [_deserialize_group(d) for d in groups_raw]
        return OutputGroupCatalog(groups)

    def exists(self) -> bool:
        return self._catalog_path.is_file()

    def delete(self) -> None:
        try:
            self._catalog_path.unlink()
        except FileNotFoundError:
            return


def _serialize_group(group: OutputGroup) -> dict[str, Any]:
    return {
        "group_id": group.group_id,
        "group_type": group.group_type,
        "member_provenance_ids": list(group.member_provenance_ids),
        "parent_group_id": group.parent_group_id,
        "label": group.label,
        "metadata": group.metadata,
    }


def _deserialize_group(raw: Any) -> OutputGroup:
    if not isinstance(raw, dict):
        raise ValueError("Each group must be a JSON object")

    required = ("group_id", "group_type", "member_provenance_ids", "parent_group_id", "label", "metadata")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"Group missing required field(s): {missing!r}")

    member_ids = raw["member_provenance_ids"]
    if not isinstance(member_ids, list) or not all(isinstance(x, str) for x in member_ids):
        raise ValueError("'member_provenance_ids' must be a list of strings")

    metadata = raw["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("'metadata' must be an object")

    parent = raw["parent_group_id"]
    if parent is not None and not isinstance(parent, str):
        raise ValueError("'parent_group_id' must be a string or null")

    label = raw["label"]
    if label is not None and not isinstance(label, str):
        raise ValueError("'label' must be a string or null")

    group_id = raw["group_id"]
    group_type = raw["group_type"]
    if not isinstance(group_id, str) or not isinstance(group_type, str):
        raise ValueError("'group_id' and 'group_type' must be strings")

    return OutputGroup(
        group_id=group_id,
        group_type=group_type,
        member_provenance_ids=tuple(member_ids),
        parent_group_id=parent,
        label=label,
        metadata=dict(metadata),
    )
