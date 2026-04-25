"""Reference analysis module: sum top-level counts from selected hub payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.ids import compute_parameters_hash
from neurolab.analysis_modules.models import AnalysisModuleDescription, AnalysisRunResult, SelectionResult


def _count_payload(payload: Any) -> int:
    """Count list/tuple/set length, dict top-level keys, else 1."""
    if isinstance(payload, dict):
        return len(payload)
    if isinstance(payload, list | tuple | set | frozenset):
        return len(payload)
    return 1


@dataclass(frozen=True, slots=True)
class PayloadTopLevelCountRequest:
    """If ``adapter_name`` is set, only outputs from that adapter are selected."""

    adapter_name: str | None = None


class PayloadTopLevelCountModule:
    """
    Metadata-only selection, then loads each selected payload and sums top-level counts.

    ``select()`` uses ``include_derived=False`` so only adapter (original) rows are
    candidates. ``hub.get_record`` resolves originals before derived for a given
    ``provenance_id``, which matches this selection set.
    """

    module_name = "payload_top_level_count"
    module_version = "0.1.0"

    @staticmethod
    def request_from_dict(data: Any) -> PayloadTopLevelCountRequest:
        """Build request from CLI JSON (top-level object with optional ``adapter_name``)."""
        if not isinstance(data, dict):
            raise TypeError("request must be a JSON object (dict)")
        an = data.get("adapter_name")
        if an is None or an == "":
            return PayloadTopLevelCountRequest(adapter_name=None)
        return PayloadTopLevelCountRequest(adapter_name=str(an))

    def describe(self) -> AnalysisModuleDescription:
        return AnalysisModuleDescription(
            module_name=self.module_name,
            module_version=self.module_version,
            summary="Selects hub records and sums top-level key/element counts from decoded payloads.",
            supported_dataset_types=(),
            supported_adapter_names=(),
            notes=(
                "Reference module for wiring tests.",
                "select() uses hub metadata only (originals).",
                "run() loads payloads via hub.open_handle(...).load().",
            ),
        )

    def select(self, hub: AnalysisHub, request: PayloadTopLevelCountRequest) -> SelectionResult:
        if request.adapter_name is not None:
            records = hub.find_records(adapter_name=request.adapter_name, include_derived=False)
        else:
            records = hub.list_records(include_derived=False)

        selected = tuple(r.provenance_id for r in records)
        return SelectionResult(
            module_name=self.module_name,
            selected_provenance_ids=selected,
            total_candidates_seen=len(records),
        )

    def run(
        self,
        hub: AnalysisHub,
        request: PayloadTopLevelCountRequest,
        selection: SelectionResult | None = None,
    ) -> AnalysisRunResult:
        if selection is not None and selection.module_name != self.module_name:
            raise ValueError(f"selection.module_name {selection.module_name!r} does not match module.module_name {self.module_name!r}")

        if selection is None:
            selection = self.select(hub, request)

        parameters_hash = compute_parameters_hash(request)
        pids = list(selection.selected_provenance_ids)
        data_hashes = [hub.get_record(pid).data_hash for pid in pids]

        total = 0
        for pid in pids:
            total += _count_payload(hub.open_handle(pid).load())

        input_count = len(pids)
        return AnalysisRunResult(
            module_name=self.module_name,
            module_version=self.module_version,
            result_type="payload_top_level_count",
            input_provenance_ids=pids,
            input_data_hashes=data_hashes,
            parameters_hash=parameters_hash,
            schema={
                "type": "object",
                "fields": {
                    "total_count": "int",
                    "input_count": "int",
                },
                "metric": "top_level_count_sum",
            },
            payload={"total_count": total, "input_count": input_count},
        )
