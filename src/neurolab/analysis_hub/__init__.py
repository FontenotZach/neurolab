"""Analysis hub: read-only registry + lazy payload access."""

from __future__ import annotations

from neurolab.analysis_hub.errors import AnalysisHubError, MetadataLoadError, MetadataRecordNotFoundError, PayloadNotFoundError
from neurolab.analysis_hub.filesystem import FileSystemAnalysisHub
from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_hub.models import AnalysisHandle, HubRecord, OutputMetadataRecord, PayloadDescriptor, RecordKind
from neurolab.analysis_hub.record_mapping import hub_record_from_adapter_output, hub_record_from_analysis_result

__all__ = [
    "AnalysisHandle",
    "AnalysisHub",
    "AnalysisHubError",
    "FileSystemAnalysisHub",
    "HubRecord",
    "MetadataLoadError",
    "MetadataRecordNotFoundError",
    "OutputMetadataRecord",
    "PayloadDescriptor",
    "PayloadNotFoundError",
    "RecordKind",
    "hub_record_from_adapter_output",
    "hub_record_from_analysis_result",
]
