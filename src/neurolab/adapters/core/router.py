"""Selects appropriate adapters for artifacts and returns list of outputs."""

from __future__ import annotations

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.core.registry import get_adapters
from neurolab.data_interface.models import Artifact


class AdapterRouter:
    """Selects the first matching adapter per artifact and returns its parse outputs."""

    def route(self, artifact: Artifact) -> list[AdapterOutput]:
        """
        For each registered adapter (by priority), if it can_handle the artifact,
        instantiate, parse, and return the list of outputs. If none match, return [].
        """
        for adapter_cls in get_adapters():
            adapter = adapter_cls()
            if adapter.can_handle(artifact):
                return adapter.parse(artifact)
        return []
