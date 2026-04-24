"""Filesystem-backed AdapterResultStore (v1)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.data_interface.models import Artifact, Manifest, utc_now
from neurolab.storage.adapter_results.errors import StoredOutputNotFound
from neurolab.storage.adapter_results.ids import (
    artifact_key_for_provenance,
    compute_data_hash,
    compute_provenance_id,
    schema_fingerprint,
)
from neurolab.storage.adapter_results.models import (
    META_SCHEMA_V2,
    PAYLOAD_FORMAT_V1,
    PRIMARY_PAYLOAD_REL_PATH,
    PersistedAdapterOutput,
)
from neurolab.storage.adapter_results.payload_codec import (
    collect_row_count_and_shapes,
    decode_payload_from_record,
    encode_payload_to_record,
)


def _is_hex64(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
    except ValueError:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _artifact_for_output(manifest: Manifest, output: AdapterOutput) -> Artifact:
    for a in manifest.artifacts:
        if a.artifact_id == output.artifact_id:
            return a
    raise ValueError(f"No artifact with artifact_id={output.artifact_id!r} in manifest")


INDEX_FILENAME = "index.json"
META_FILENAME = "meta.json"


class FileAdapterResultStore:
    """
    Stores adapter outputs under base_dir / {manifest_id} / {provenance_id} /.

    Authoritative state is meta.json + payload material in each record directory.
    index.json is derived and must not be treated as source of truth.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir if base_dir is not None else Path.home() / ".neurolab" / "data" / "adapter_outputs"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_pipeline_result(self, manifest: Manifest, result: AdapterPipelineResult) -> list[PersistedAdapterOutput]:
        manifest_dir = self.base_dir / manifest.manifest_id
        manifest_dir.mkdir(parents=True, exist_ok=True)

        records: list[PersistedAdapterOutput] = []
        expected_ids: set[str] = set()

        for ordinal, out in enumerate(result.outputs):
            art = _artifact_for_output(manifest, out)
            ak = artifact_key_for_provenance(art)
            sf = schema_fingerprint(out.schema)
            prov = compute_provenance_id(
                manifest_id=manifest.manifest_id,
                artifact_key=ak,
                raw_content_hash=art.content_hash,
                adapter_name=out.adapter_name,
                adapter_version=out.adapter_version,
                adapter_config_hash=out.adapter_config_hash,
                schema_fingerprint=sf,
                pipeline_ordinal=ordinal,
            )
            data_h = compute_data_hash(out.payload)
            expected_ids.add(prov)
            meta = self._save_output_record(
                manifest=manifest,
                pipeline_ordinal=ordinal,
                provenance_id=prov,
                data_hash=data_h,
                schema_fp=sf,
                source_artifact=art,
                output=out,
                manifest_dir=manifest_dir,
            )
            records.append(meta)

        self._remove_orphans(manifest_dir, expected_ids)
        self._regenerate_index(manifest_dir)
        return records

    def _save_output_record(
        self,
        *,
        manifest: Manifest,
        pipeline_ordinal: int,
        provenance_id: str,
        data_hash: str,
        schema_fp: str,
        source_artifact: Artifact,
        output: AdapterOutput,
        manifest_dir: Path,
    ) -> PersistedAdapterOutput:
        record_dir = manifest_dir / provenance_id
        record_dir.mkdir(parents=True, exist_ok=True)

        encode_payload_to_record(output.payload, record_dir)

        row_count, shape_summary = collect_row_count_and_shapes(output.payload)

        persisted = PersistedAdapterOutput(
            meta_schema_version=META_SCHEMA_V2,
            provenance_id=provenance_id,
            data_hash=data_hash,
            manifest_id=manifest.manifest_id,
            artifact_id=output.artifact_id,
            raw_content_hash=source_artifact.content_hash,
            adapter_name=output.adapter_name,
            adapter_version=output.adapter_version,
            adapter_config_hash=output.adapter_config_hash,
            schema_fingerprint=schema_fp,
            dataset_type=output.dataset_type,
            pipeline_ordinal=pipeline_ordinal,
            schema=dict(output.schema),
            payload_format=PAYLOAD_FORMAT_V1,
            payload_path=PRIMARY_PAYLOAD_REL_PATH,
            created_at=utc_now().isoformat(),
            row_count=row_count,
            shape_summary=shape_summary,
        )

        meta_text = json.dumps(persisted.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        _atomic_write_text(record_dir / META_FILENAME, meta_text)

        return persisted

    def _remove_orphans(self, manifest_dir: Path, expected_ids: set[str]) -> None:
        for p in list(manifest_dir.iterdir()):
            if p.name.endswith(".staging"):
                shutil.rmtree(p, ignore_errors=True)
                continue
            if p.name == INDEX_FILENAME:
                continue
            if p.is_dir() and _is_hex64(p.name) and p.name not in expected_ids:
                shutil.rmtree(p, ignore_errors=True)

    def _regenerate_index(self, manifest_dir: Path) -> None:
        entries: list[dict[str, Any]] = []
        for p in sorted(manifest_dir.iterdir(), key=lambda x: x.name):
            if not p.is_dir() or not _is_hex64(p.name):
                continue
            meta_path = p / META_FILENAME
            if not meta_path.is_file():
                continue
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            po = PersistedAdapterOutput.from_dict(data)
            entries.append(
                {
                    "provenance_id": po.provenance_id,
                    "data_hash": po.data_hash,
                    "pipeline_ordinal": po.pipeline_ordinal,
                    "artifact_id": po.artifact_id,
                    "adapter_name": po.adapter_name,
                    "adapter_version": po.adapter_version,
                    "dataset_type": po.dataset_type,
                }
            )
        entries.sort(key=lambda e: int(e["pipeline_ordinal"]))
        text = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        _atomic_write_text(manifest_dir / INDEX_FILENAME, text)

    def list_outputs(self, manifest_id: str) -> list[PersistedAdapterOutput]:
        manifest_dir = self.base_dir / manifest_id
        if not manifest_dir.is_dir():
            return []
        out: list[PersistedAdapterOutput] = []
        for p in manifest_dir.iterdir():
            if not p.is_dir() or not _is_hex64(p.name):
                continue
            meta_path = p / META_FILENAME
            if not meta_path.is_file():
                continue
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            out.append(PersistedAdapterOutput.from_dict(data))
        out.sort(key=lambda m: m.pipeline_ordinal)
        return out

    def load_metadata(self, manifest_id: str, provenance_id: str) -> PersistedAdapterOutput:
        record_dir = self._record_dir(manifest_id, provenance_id)
        meta_path = record_dir / META_FILENAME
        if not meta_path.is_file():
            raise StoredOutputNotFound(f"No stored output {provenance_id!r} for manifest {manifest_id!r}")
        return PersistedAdapterOutput.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))

    def load_payload(self, manifest_id: str, provenance_id: str) -> Any:
        record_dir = self._record_dir(manifest_id, provenance_id)
        if not (record_dir / META_FILENAME).is_file():
            raise StoredOutputNotFound(f"No stored output {provenance_id!r} for manifest {manifest_id!r}")
        return decode_payload_from_record(record_dir)

    def _record_dir(self, manifest_id: str, provenance_id: str) -> Path:
        return self.base_dir / manifest_id / provenance_id

    def delete_manifest_outputs(self, manifest_id: str) -> None:
        manifest_dir = self.base_dir / manifest_id
        if manifest_dir.is_dir():
            shutil.rmtree(manifest_dir)
