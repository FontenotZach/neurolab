"""CSV artifact adapter: format-agnostic tabular parsing."""

from __future__ import annotations

import csv
from pathlib import Path

from neurolab.adapters.core.base import ArtifactAdapter
from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.core.output import AdapterOutput
from neurolab.data_interface.models import Artifact


class CSVAdapter(ArtifactAdapter):
    """Parses CSV files into tabular AdapterOutput. One file -> one output."""

    name = "csv_adapter"
    priority = 0
    supported_media_types = ["text/csv"]

    def can_handle(self, artifact: Artifact) -> bool:
        if artifact.media_type == "text/csv":
            return True
        path = artifact.absolute_path or artifact.relative_path or ""
        return path.endswith(".csv") if path else False

    def parse(self, artifact: Artifact) -> list[AdapterOutput]:
        if not artifact.absolute_path:
            raise AdapterError("CSVAdapter requires artifact.absolute_path; collectors must set it.")

        path = Path(artifact.absolute_path)
        if not path.exists():
            raise AdapterError(f"CSV file not found: {path}")

        try:
            with path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # NOTE: loads entire CSV into memory; future: stream, Arrow, or chunked parsing
                rows = list(reader)
                fieldnames = reader.fieldnames or []
        except (csv.Error, OSError) as e:
            raise AdapterError(f"Failed to parse CSV {path}: {e}") from e

        schema = {"columns": list(fieldnames)}

        return [
            AdapterOutput(
                artifact_id=artifact.artifact_id,
                adapter_name=self.name,
                adapter_version="1.0",
                dataset_type="tabular",
                schema=schema,
                payload=rows,
            )
        ]
