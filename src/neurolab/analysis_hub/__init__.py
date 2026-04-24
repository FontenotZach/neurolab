"""Analysis hub: read-only registry + lazy payload access."""

from __future__ import annotations

from neurolab.analysis_hub.errors import AnalysisHubError, MetadataLoadError, MetadataRecordNotFoundError, PayloadNotFoundError
from neurolab.analysis_hub.filesystem import FileSystemAnalysisHub
from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_hub.models import AnalysisHandle, OutputMetadataRecord, PayloadDescriptor

__all__ = [
    "AnalysisHandle",
    "AnalysisHub",
    "AnalysisHubError",
    "FileSystemAnalysisHub",
    "MetadataLoadError",
    "MetadataRecordNotFoundError",
    "OutputMetadataRecord",
    "PayloadDescriptor",
    "PayloadNotFoundError",
]

