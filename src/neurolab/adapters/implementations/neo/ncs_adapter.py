"""Neuralynx .ncs artifact adapter using Neo's NeuralynxRawIO (directory-based, metadata-driven)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

# Neo is a dependency; import at module level for clear failure if missing
from neo.rawio import NeuralynxRawIO

from neurolab.adapters.core.base import ArtifactAdapter
from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.core.output import AdapterOutput
from neurolab.data_interface.models import Artifact


class NCSAdapter(ArtifactAdapter):
    """
    Parses Neuralynx .ncs datasets via Neo. Uses the directory containing the artifact;
    discovers the first valid signal stream and returns one channel's timeseries.
    No filename-based channel detection (e.g. no CSC number parsing).
    """

    name = "ncs_adapter"
    priority = 0
    supported_media_types = ["application/x-neuralynx-ncs"]

    def can_handle(self, artifact: Artifact) -> bool:
        if artifact.media_type == "application/x-neuralynx-ncs":
            return True
        path = artifact.absolute_path or artifact.relative_path or ""
        return path.endswith(".ncs") if path else False

    def parse(self, artifact: Artifact) -> list[AdapterOutput]:
        if not artifact.absolute_path:
            raise AdapterError("NCSAdapter requires artifact.absolute_path; collectors must set it.")

        path = Path(artifact.absolute_path)
        dirname = path.parent
        if not dirname.exists():
            raise AdapterError(f"Neuralynx directory not found: {dirname}")

        try:
            reader = NeuralynxRawIO(dirname=str(dirname))
            reader.parse_header()
        except Exception as e:
            raise AdapterError(f"Failed to open or parse Neuralynx directory {dirname}: {e}") from e

        ch_table = reader.header["signal_channels"]
        stream_table = reader.header["signal_streams"]

        signal = None
        fs = 0.0
        n_samples = 0
        stream_index_used = None

        n_streams = reader.signal_streams_count()
        for stream_index in range(n_streams):
            n_samp = int(reader.get_signal_size(block_index=0, seg_index=0, stream_index=stream_index))
            if n_samp <= 0:
                continue
            try:
                fs = float(reader.get_signal_sampling_rate(stream_index))
            except TypeError:
                fs = float(reader.get_signal_sampling_rate(stream_index=stream_index))

            sig = reader.get_analogsignal_chunk(
                block_index=0,
                seg_index=0,
                i_start=0,
                i_stop=n_samp,
                stream_index=stream_index,
                channel_indexes=[0],
            )
            if sig.size > 0:
                signal = sig
                n_samples = n_samp
                stream_index_used = stream_index
                break

        if signal is None:
            raise AdapterError("No valid Neuralynx signal stream detected")

        signal_1d = np.ravel(signal.astype(np.float64))
        payload = {"signal": signal_1d}

        schema = {
            "format": "neuralynx_ncs",
            "sampling_rate": fs,
            "n_samples": n_samples,
            "units": "uV",
            "source": "neo.rawio.NeuralynxRawIO",
        }
        if stream_index_used is not None and stream_table is not None and ch_table is not None:
            try:
                stream_id = stream_table["id"][stream_index_used]
                mask = ch_table["stream_id"] == stream_id
                if np.any(mask):
                    names = ch_table["name"][mask].astype(str)
                    if len(names) > 0:
                        schema["channel_name"] = str(names[0])
            except (IndexError, KeyError, TypeError):
                pass

        return [
            AdapterOutput(
                artifact_id=artifact.artifact_id,
                adapter_name=self.name,
                adapter_version="1.0",
                dataset_type="timeseries",
                schema=schema,
                payload=payload,
            )
        ]
