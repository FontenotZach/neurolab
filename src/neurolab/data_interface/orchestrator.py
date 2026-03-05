from __future__ import annotations

from .collectors import FilesystemCollector
from .models import DataSourceSpec, Manifest


def collect_source(source: DataSourceSpec) -> Manifest:
    """Select the appropriate collector and return a Manifest for the given source."""
    if source.source_type == "filesystem":
        collector = FilesystemCollector()
        return collector.collect(source)

    raise ValueError(f"No collector registered for source_type={source.source_type}")
