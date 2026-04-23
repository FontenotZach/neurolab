"""Orchestrates processing of an entire manifest through the adapter layer."""

from __future__ import annotations

from dataclasses import dataclass

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.core.router import AdapterRouter
from neurolab.data_interface.models import Artifact, Manifest


@dataclass
class AdapterPipelineResult:
    """Result of processing a manifest: outputs from adapters and artifacts no adapter handled."""

    outputs: list[AdapterOutput]
    skipped_artifacts: list[Artifact]


class AdapterPipeline:
    """Processes all artifacts in a manifest through adapters."""

    def __init__(self) -> None:
        self.router = AdapterRouter()

    def process_manifest(self, manifest: Manifest) -> AdapterPipelineResult:
        """
        Process each artifact in deterministic order (by relative_path).
        Collect adapter outputs and record artifacts that no adapter matched.
        """
        outputs: list[AdapterOutput] = []
        skipped_artifacts: list[Artifact] = []

        sorted_artifacts = sorted(
            manifest.artifacts,
            key=lambda a: a.relative_path or "",
        )

        for artifact in sorted_artifacts:
            result = self.router.route(artifact)
            if result:
                outputs.extend(result)
            else:
                skipped_artifacts.append(artifact)

        return AdapterPipelineResult(outputs=outputs, skipped_artifacts=skipped_artifacts)
