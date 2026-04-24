"""Persisted analysis result metadata (v1).

Mirrors adapter-results persistence patterns, but for analysis module outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PersistedAnalysisResult:
    """
    Metadata for one stored analysis result.

    ``data_hash`` identifies standardized payload content (computational equivalence).
    ``provenance_id`` identifies lineage (unique directory name).
    """

    provenance_id: str
    data_hash: str
    result_type: str
    module_name: str
    module_version: str
    input_provenance_ids: list[str]
    input_data_hashes: list[str]
    parameters_hash: str
    schema: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "data_hash": self.data_hash,
            "result_type": self.result_type,
            "module": {"name": self.module_name, "version": self.module_version},
            "inputs": [{"provenance_id": pid, "data_hash": dh} for pid, dh in zip(self.input_provenance_ids, self.input_data_hashes, strict=True)],
            "parameters_hash": self.parameters_hash,
            "schema": self.schema,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PersistedAnalysisResult:
        module = d.get("module")
        if not isinstance(module, dict):
            raise TypeError("meta.module must be an object")
        inputs = d.get("inputs")
        if not isinstance(inputs, list):
            raise TypeError("meta.inputs must be a list")
        input_prov: list[str] = []
        input_hash: list[str] = []
        for item in inputs:
            if not isinstance(item, dict):
                raise TypeError("meta.inputs items must be objects")
            input_prov.append(str(item["provenance_id"]))
            input_hash.append(str(item["data_hash"]))

        schema = d.get("schema")
        if schema is None:
            schema = {}
        if not isinstance(schema, dict):
            raise TypeError("meta.schema must be an object")

        return cls(
            provenance_id=str(d["provenance_id"]),
            data_hash=str(d["data_hash"]),
            result_type=str(d["result_type"]),
            module_name=str(module["name"]),
            module_version=str(module["version"]),
            input_provenance_ids=input_prov,
            input_data_hashes=input_hash,
            parameters_hash=str(d["parameters_hash"]),
            schema=dict(schema),
            created_at=str(d.get("created_at", "")),
        )
