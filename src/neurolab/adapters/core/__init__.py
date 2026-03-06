"""Adapter infrastructure and interfaces."""

from neurolab.adapters.core.base import ArtifactAdapter
from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.core.registry import get_adapters, register_adapter
from neurolab.adapters.core.router import AdapterRouter

__all__ = [
    "AdapterOutput",
    "AdapterRouter",
    "ArtifactAdapter",
    "get_adapters",
    "register_adapter",
]
