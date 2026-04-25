"""In-memory registry of analysis module instances (lookup by ``module_name``)."""

from __future__ import annotations

from typing import Any

from neurolab.analysis_modules.base import AnalysisModule

_registry: dict[str, AnalysisModule[Any]] = {}


def register_analysis_module(module: AnalysisModule[Any]) -> None:
    """
    Register ``module`` under ``module.module_name``.

    Idempotent when the same ``module_version`` is registered again. If the name
    is already taken with a different ``module_version``, raises ``ValueError``.
    """
    name = module.module_name
    existing = _registry.get(name)
    if existing is not None and existing.module_version != module.module_version:
        raise ValueError(
            f"Analysis module {name!r} is already registered with version {existing.module_version!r}; "
            f"cannot register version {module.module_version!r}"
        )
    _registry[name] = module


def get_analysis_module(name: str) -> AnalysisModule[Any]:
    """Return the registered module instance for ``name``."""
    if name not in _registry:
        known = ", ".join(sorted(_registry.keys())) if _registry else "(none)"
        raise KeyError(f"Unknown analysis module {name!r}. Available: {known}")
    return _registry[name]


def list_analysis_modules() -> list[AnalysisModule[Any]]:
    """All registered modules, sorted by ``module_name`` (deterministic)."""
    return sorted(_registry.values(), key=lambda m: m.module_name)


def clear_registry() -> None:
    """Remove all registrations (intended for tests)."""
    _registry.clear()


__all__ = [
    "clear_registry",
    "get_analysis_module",
    "list_analysis_modules",
    "register_analysis_module",
]
