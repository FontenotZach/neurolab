"""Base interface for artifact adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from neurolab.adapters.core.output import AdapterOutput
from neurolab.data_interface.models import Artifact


class ArtifactAdapter(ABC):
    """
    Base class for artifact adapters.
    Stateless, deterministic, side-effect free (I/O only for reading artifact content).
    Adapters are format-agnostic: care only about type (media_type, extension), not domain semantics.
    """

    name: str = "base_adapter"
    priority: int = 0  # optional safeguard when multiple adapters could match; higher = preferred
    supported_media_types: list[str] | None = None  # optional, for debugging

    @abstractmethod
    def can_handle(self, artifact: Artifact) -> bool:
        """Determine if the adapter can parse this artifact (by media_type/extension only)."""

    @abstractmethod
    def parse(self, artifact: Artifact) -> list[AdapterOutput]:
        """Convert artifact contents into structured output(s). One artifact may yield many outputs."""
