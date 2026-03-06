"""JSON artifact adapter: format-agnostic parsing of JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from neurolab.adapters.core.base import ArtifactAdapter
from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.core.output import AdapterOutput
from neurolab.data_interface.models import Artifact


class JSONAdapter(ArtifactAdapter):
    """Parses JSON files into AdapterOutput. One file -> one output. Payload is the parsed value."""

    name = "json_adapter"
    priority = 0
    supported_media_types = ["application/json"]

    def can_handle(self, artifact: Artifact) -> bool:
        if artifact.media_type == "application/json":
            return True
        path = artifact.absolute_path or artifact.relative_path or ""
        return path.endswith(".json") if path else False

    def parse(self, artifact: Artifact) -> list[AdapterOutput]:
        if not artifact.absolute_path:
            raise AdapterError("JSONAdapter requires artifact.absolute_path; collectors must set it.")

        path = Path(artifact.absolute_path)
        if not path.exists():
            raise AdapterError(f"JSON file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                # NOTE: loads entire JSON into memory; future: stream for large files
                payload = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise AdapterError(f"Failed to parse JSON {path}: {e}") from e

        root_type = "array" if isinstance(payload, list) else "object" if isinstance(payload, dict) else "other"
        schema = {"root_type": root_type}
        if isinstance(payload, list):
            schema["length"] = len(payload)

        return [
            AdapterOutput(
                artifact_id=artifact.artifact_id,
                adapter_name=self.name,
                adapter_version="1.0",
                dataset_type="tabular",
                schema=schema,
                payload=payload,
            )
        ]
