"""Filesystem-backed analysis result store (v1)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from neurolab.data_interface.models import utc_now
from neurolab.storage.adapter_results.payload_codec import decode_payload_from_record, encode_payload_to_record
from neurolab.storage.analysis_results.errors import AnalysisResultAlreadyExistsError, AnalysisResultNotFoundError
from neurolab.storage.analysis_results.ids import compute_data_hash, compute_provenance_id
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

META_FILENAME = "meta.json"


def _default_analysis_results_dir() -> Path:
    return Path.home() / ".neurolab" / "data" / "analysis_results"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _is_hex64(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
    except ValueError:
        return False
    return True


class FileAnalysisResultStore:
    """
    Stores analysis results under base_dir / {provenance_id} /.

    Authoritative state is meta.json + payload material in each record directory.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir if base_dir is not None else _default_analysis_results_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_result(
        self,
        *,
        result_type: str,
        module_name: str,
        module_version: str,
        input_provenance_ids: list[str],
        input_data_hashes: list[str],
        parameters_hash: str,
        schema: dict[str, Any],
        payload: Any,
        created_at: str | None = None,
    ) -> PersistedAnalysisResult:
        if len(input_provenance_ids) != len(input_data_hashes):
            raise ValueError("input_provenance_ids and input_data_hashes must have the same length")

        data_hash = compute_data_hash(payload)
        provenance_id = compute_provenance_id(
            module_name=module_name,
            module_version=module_version,
            input_provenance_ids=input_provenance_ids,
            input_data_hashes=input_data_hashes,
            parameters_hash=parameters_hash,
        )

        record_dir = self.base_dir / provenance_id
        meta_path = record_dir / META_FILENAME

        created = created_at if created_at is not None else utc_now().isoformat()

        meta = PersistedAnalysisResult(
            provenance_id=provenance_id,
            data_hash=data_hash,
            result_type=result_type,
            module_name=module_name,
            module_version=module_version,
            input_provenance_ids=list(input_provenance_ids),
            input_data_hashes=list(input_data_hashes),
            parameters_hash=parameters_hash,
            schema=dict(schema),
            created_at=created,
        )

        if meta_path.is_file():
            existing = PersistedAnalysisResult.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
            if self._equivalent(existing, meta):
                # Treat as idempotent save when everything but created_at matches.
                return existing
            raise AnalysisResultAlreadyExistsError(f"Analysis result already exists for provenance_id={provenance_id!r}")

        record_dir.mkdir(parents=True, exist_ok=True)
        encode_payload_to_record(payload, record_dir)
        text = json.dumps(meta.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        _atomic_write_text(meta_path, text)
        return meta

    def load_metadata(self, provenance_id: str) -> PersistedAnalysisResult:
        record_dir = self._record_dir(provenance_id)
        meta_path = record_dir / META_FILENAME
        if not meta_path.is_file():
            raise AnalysisResultNotFoundError(f"No analysis result {provenance_id!r}")
        return PersistedAnalysisResult.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))

    def load_payload(self, provenance_id: str) -> Any:
        record_dir = self._record_dir(provenance_id)
        meta_path = record_dir / META_FILENAME
        if not meta_path.is_file():
            raise AnalysisResultNotFoundError(f"No analysis result {provenance_id!r}")
        return decode_payload_from_record(record_dir)

    def list_metadata(self) -> list[PersistedAnalysisResult]:
        if not self.base_dir.is_dir():
            return []
        out: list[PersistedAnalysisResult] = []
        for p in sorted(self.base_dir.iterdir(), key=lambda x: x.name):
            if not p.is_dir() or not _is_hex64(p.name):
                continue
            meta_path = p / META_FILENAME
            if not meta_path.is_file():
                continue
            out.append(PersistedAnalysisResult.from_dict(json.loads(meta_path.read_text(encoding="utf-8"))))
        out.sort(key=lambda m: m.provenance_id)
        return out

    def delete(self, provenance_id: str) -> None:
        record_dir = self._record_dir(provenance_id)
        if record_dir.is_dir():
            shutil.rmtree(record_dir)

    def _record_dir(self, provenance_id: str) -> Path:
        return self.base_dir / provenance_id

    @staticmethod
    def _equivalent(a: PersistedAnalysisResult, b: PersistedAnalysisResult) -> bool:
        # created_at is intentionally excluded from all identity decisions.
        return (
            a.provenance_id == b.provenance_id
            and a.data_hash == b.data_hash
            and a.result_type == b.result_type
            and a.module_name == b.module_name
            and a.module_version == b.module_version
            and a.input_provenance_ids == b.input_provenance_ids
            and a.input_data_hashes == b.input_data_hashes
            and a.parameters_hash == b.parameters_hash
            and a.schema == b.schema
        )
