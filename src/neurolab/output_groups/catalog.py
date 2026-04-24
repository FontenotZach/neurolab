from __future__ import annotations

from collections.abc import Iterable

from neurolab.output_groups.models import OutputGroup


class OutputGroupCatalog:
    def __init__(self, groups: Iterable[OutputGroup] | None = None) -> None:
        self._groups: dict[str, OutputGroup] = {}
        if groups is not None:
            self.add_many(groups)

    def add(self, group: OutputGroup) -> None:
        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id!r}")
        self._groups[group.group_id] = group

    def add_many(self, groups: Iterable[OutputGroup]) -> None:
        incoming: list[OutputGroup] = list(groups)
        incoming_ids = [g.group_id for g in incoming]

        dup_ids: set[str] = set()
        seen: set[str] = set()
        for gid in incoming_ids:
            if gid in seen:
                dup_ids.add(gid)
            seen.add(gid)

        existing_collisions = {gid for gid in incoming_ids if gid in self._groups}

        if dup_ids or existing_collisions:
            details = sorted(dup_ids | existing_collisions)
            raise ValueError(f"Duplicate group_id(s): {details!r}")

        for g in incoming:
            self._groups[g.group_id] = g

    def get(self, group_id: str) -> OutputGroup:
        return self._groups[group_id]

    def maybe_get(self, group_id: str) -> OutputGroup | None:
        return self._groups.get(group_id)

    def list(self) -> list[OutputGroup]:
        return [self._groups[k] for k in sorted(self._groups)]

    def by_type(self, group_type: str) -> list[OutputGroup]:
        return sorted(
            (g for g in self._groups.values() if g.group_type == group_type),
            key=lambda g: g.group_id,
        )

    def roots(self) -> list[OutputGroup]:
        return sorted(
            (g for g in self._groups.values() if g.parent_group_id is None),
            key=lambda g: g.group_id,
        )

    def children_of(self, group_id: str) -> list[OutputGroup]:
        return sorted(
            (g for g in self._groups.values() if g.parent_group_id == group_id),
            key=lambda g: g.group_id,
        )

    def remove(self, group_id: str) -> OutputGroup:
        return self._groups.pop(group_id)

    def clear(self) -> None:
        self._groups.clear()

    def __len__(self) -> int:
        return len(self._groups)

    def __contains__(self, group_id: object) -> bool:
        return isinstance(group_id, str) and group_id in self._groups
