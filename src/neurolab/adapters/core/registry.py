"""Adapter registry: stores adapter classes; router instantiates when needed."""

from __future__ import annotations

from neurolab.adapters.core.base import ArtifactAdapter

_ADAPTERS: list[type[ArtifactAdapter]] = []


def register_adapter(adapter_cls: type[ArtifactAdapter]) -> None:
    """Register an adapter class. Router will instantiate when needed."""
    _ADAPTERS.append(adapter_cls)


def get_adapters() -> list[type[ArtifactAdapter]]:
    """Return registered adapter classes, sorted by priority descending (safeguard)."""
    return sorted(_ADAPTERS, key=lambda c: getattr(c, "priority", 0), reverse=True)
