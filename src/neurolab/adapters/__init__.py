"""Adapter layer: route manifest artifacts through format adapters to structured outputs."""

import neurolab.adapters.implementations  # noqa: F401 -- register adapters at import time
from neurolab.adapters.core.base import ArtifactAdapter
from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipeline, AdapterPipelineResult

__all__ = [
    "AdapterOutput",
    "AdapterPipeline",
    "AdapterPipelineResult",
    "ArtifactAdapter",
]
