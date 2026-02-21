from __future__ import annotations

from .collectors import FilesystemCollector
from .models import DataSourceSpec, Manifest

"""
Orchestrator for collecting artifacts from various data sources.
- collect_source is the main entry point, which takes a DataSourceSpec and returns a Manifest
  representing the collection snapshot.
- It selects the appropriate collector based on the source_type of the DataSourceSpec.
- The design allows for easy extension to support additional source types and collectors in the future.
"""


def collect_source(source: DataSourceSpec, *, compute_hash: bool = False) -> Manifest:
    # Implement collection logic based on source_type.
    # Currently only "filesystem" is supported
    if source.source_type == "filesystem":
        collector = FilesystemCollector(compute_hash=compute_hash)
        return collector.collect(source)

    raise ValueError(f"No collector registered for source_type={source.source_type}")
