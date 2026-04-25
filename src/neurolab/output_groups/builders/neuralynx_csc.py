from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_hub.models import HubRecord
from neurolab.output_groups.base import OutputGroupBuilder
from neurolab.output_groups.models import OutputGroup, OutputGroupBuilderDescription, OutputGroupSelectionResult

NEURALYNX_CSC_EXPERIMENT = "neuralynx_csc_experiment"
NEURALYNX_TETRODE = "neuralynx_tetrode"


@dataclass(frozen=True)
class NeuralynxCSCGroupRequest:
    min_csc_files_per_experiment: int = 2
    include_incomplete_tetrodes: bool = False


@dataclass(frozen=True)
class CandidateCSCRecord:
    provenance_id: str
    relative_path: str
    relative_folder: str
    channel_number: int
    hub_order: int


@dataclass(frozen=True)
class TetrodeCandidate:
    tetrode_index: int
    channel_numbers: tuple[int, int, int, int]
    provenance_ids: tuple[str, str, str, str]


class NeuralynxCSCOutputGroupBuilder(OutputGroupBuilder[NeuralynxCSCGroupRequest]):
    builder_name = "neuralynx_csc"
    builder_version = "0.1.0"

    def describe(self) -> OutputGroupBuilderDescription:
        return OutputGroupBuilderDescription(
            builder_name=self.builder_name,
            builder_version=self.builder_version,
            summary=("Detects Neuralynx CSC experiment folders and complete tetrode groups from hub metadata."),
            supported_group_types=(NEURALYNX_CSC_EXPERIMENT, NEURALYNX_TETRODE),
            supported_adapter_names=("neuralynx_ncs",),
            notes=(
                "Metadata-only builder.",
                "Does not load payloads.",
                "Groups CSC outputs by parent relative folder.",
                "Creates nested tetrode groups for complete 4-channel CSC blocks.",
            ),
        )

    def select(self, hub: AnalysisHub, request: NeuralynxCSCGroupRequest) -> OutputGroupSelectionResult:
        candidates = _discover_candidates(hub, request)
        by_folder = _group_candidates_by_folder(candidates)
        valid_folders = {f for f, cs in by_folder.items() if len(cs) >= request.min_csc_files_per_experiment}

        selected: list[str] = []
        for c in sorted(candidates, key=lambda x: x.hub_order):
            if c.relative_folder in valid_folders:
                selected.append(c.provenance_id)

        return OutputGroupSelectionResult(
            builder_name=self.builder_name,
            selected_provenance_ids=tuple(selected),
            total_candidates_seen=len(candidates),
        )

    def build(self, hub: AnalysisHub, request: NeuralynxCSCGroupRequest) -> list[OutputGroup]:
        if request.include_incomplete_tetrodes:
            raise NotImplementedError("include_incomplete_tetrodes=True is not implemented yet.")

        candidates = _discover_candidates(hub, request)
        by_folder_all = _group_candidates_by_folder(candidates)
        by_folder = {folder: cs for folder, cs in by_folder_all.items() if len(cs) >= request.min_csc_files_per_experiment}

        groups: list[OutputGroup] = []

        for relative_folder in sorted(by_folder.keys()):
            folder_candidates = by_folder[relative_folder]
            folder_candidates_sorted = sorted(folder_candidates, key=lambda c: c.channel_number)

            tetrodes = _detect_complete_tetrodes(folder_candidates_sorted)

            experiment_group_id = f"{NEURALYNX_CSC_EXPERIMENT}:{relative_folder}"
            experiment_group = OutputGroup(
                group_id=experiment_group_id,
                group_type=NEURALYNX_CSC_EXPERIMENT,
                member_provenance_ids=tuple(c.provenance_id for c in folder_candidates_sorted),
                parent_group_id=None,
                label=None,
                metadata={
                    "relative_folder": relative_folder,
                    "n_csc_files": len(folder_candidates_sorted),
                    "channel_numbers": [c.channel_number for c in folder_candidates_sorted],
                    "n_complete_tetrodes": len(tetrodes),
                    "builder_name": self.builder_name,
                    "builder_version": self.builder_version,
                },
            )
            groups.append(experiment_group)

            for t in sorted(tetrodes, key=lambda x: x.tetrode_index):
                tetrode_group_id = f"{NEURALYNX_TETRODE}:{relative_folder}:tetrode_{t.tetrode_index:02d}"
                groups.append(
                    OutputGroup(
                        group_id=tetrode_group_id,
                        group_type=NEURALYNX_TETRODE,
                        member_provenance_ids=t.provenance_ids,
                        parent_group_id=experiment_group_id,
                        label=None,
                        metadata={
                            "relative_folder": relative_folder,
                            "tetrode_index": t.tetrode_index,
                            "channel_numbers": list(t.channel_numbers),
                            "complete": True,
                            "builder_name": self.builder_name,
                            "builder_version": self.builder_version,
                        },
                    )
                )

        return groups


def _extract_relative_path(record: HubRecord) -> str | None:
    """
    Pull a relative path string from hub metadata.

    The canonical expected key is `schema["relative_path"]` for metadata-only builders.
    """

    schema = record.schema
    if not isinstance(schema, dict):
        return None

    for key in ("relative_path", "path", "artifact_relative_path", "source_relative_path"):
        val = schema.get(key)
        if isinstance(val, str) and val.strip():
            return val

    return None


def _extract_channel_number(relative_path: str) -> int | None:
    rel_norm = relative_path.replace("\\", "/")
    name = PurePosixPath(rel_norm).name
    if not name.lower().endswith(".ncs"):
        return None

    stem = PurePosixPath(name).stem
    digits = "".join(ch for ch in stem if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _parent_folder(relative_path: str) -> str:
    rel_norm = relative_path.replace("\\", "/")
    p = PurePosixPath(rel_norm)
    parent = str(p.parent)
    if parent in (".", ""):
        return ""
    return parent


def _discover_candidates(hub: AnalysisHub, request: NeuralynxCSCGroupRequest) -> list[CandidateCSCRecord]:
    records = [r for r in hub.list_records() if r.record_kind == "original"]
    out: list[CandidateCSCRecord] = []

    for hub_order, r in enumerate(records):
        rel = _extract_relative_path(r)
        if rel is None:
            continue

        # Filter to Neuralynx .ncs by relative path and channel parsing rule
        ch = _extract_channel_number(rel)
        if ch is None:
            continue

        # Optional adapter-format check (metadata-only)
        fmt = r.schema.get("format") if isinstance(r.schema, dict) else None
        if fmt is not None and fmt != "neuralynx_ncs":
            continue

        folder = _parent_folder(rel)
        out.append(
            CandidateCSCRecord(
                provenance_id=r.provenance_id,
                relative_path=rel.replace("\\", "/"),
                relative_folder=folder,
                channel_number=ch,
                hub_order=hub_order,
            )
        )

    # If duplicates for a channel exist in a folder, keep earliest in hub order for determinism
    deduped: dict[tuple[str, int], CandidateCSCRecord] = {}
    for c in out:
        k = (c.relative_folder, c.channel_number)
        prev = deduped.get(k)
        if prev is None or c.hub_order < prev.hub_order:
            deduped[k] = c

    return sorted(deduped.values(), key=lambda c: c.hub_order)


def _group_candidates_by_folder(
    candidates: list[CandidateCSCRecord],
) -> dict[str, list[CandidateCSCRecord]]:
    out: dict[str, list[CandidateCSCRecord]] = {}
    for c in candidates:
        out.setdefault(c.relative_folder, []).append(c)
    return out


def _detect_complete_tetrodes(candidates: list[CandidateCSCRecord]) -> list[TetrodeCandidate]:
    by_channel: dict[int, CandidateCSCRecord] = {c.channel_number: c for c in candidates}
    channels = sorted(by_channel.keys())
    if not channels:
        return []

    tetrode_candidates: list[TetrodeCandidate] = []

    # Only consider blocks implied by present channels, but require completeness.
    for ch in channels:
        tetrode_index = ((ch - 1) // 4) + 1
        start = (tetrode_index - 1) * 4 + 1
        block = (start, start + 1, start + 2, start + 3)

        if all(b in by_channel for b in block):
            prov_ids = tuple(by_channel[b].provenance_id for b in block)
            tetrode_candidates.append(
                TetrodeCandidate(
                    tetrode_index=tetrode_index,
                    channel_numbers=block,
                    provenance_ids=prov_ids,
                )
            )

    # Deduplicate tetrodes (loop above hits same tetrode up to 4 times)
    unique: dict[int, TetrodeCandidate] = {}
    for t in tetrode_candidates:
        unique[t.tetrode_index] = t

    return [unique[k] for k in sorted(unique.keys())]
