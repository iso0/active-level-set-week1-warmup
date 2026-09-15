"""Dataset pins, population loading, input-tuple hashing, ledger/registry access.

The frozen 405-simulation population lives in ``data/population.csv`` (a
byte-identical copy of the archive's ``primary_common_population.csv``).
Target extraction (T0 window, max depth, G3/R3) is deliberately NOT ported: it
lives in the archive (``week7_phase2`` + ``week6_phase1``/``phase3_5``) and its
output is frozen in the population file.  Network access (Hugging Face) happens
only inside ``download_pinned_file`` / ``load_partition_labels`` and is never
required at import.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from alse.config import DATA_DIR, POPULATION_CSV
from alse.io import require, strict_bool

# --- pins ------------------------------------------------------------------
# frozen: week7_sph_v2_common.py::WEEK6_REPO_ID / WEEK6_REVISION (Weeks 5-6 dataset)
SPH_DATASET_REPO = "ioandanielc/sph_dataset"
SPH_DATASET_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
# frozen: week7_sph_v2_common.py::SPH_V2_REPO_ID / SPH_V2_REVISION (audit pin, Phases 1-5)
SPH_V2_REPO = "ioandanielc/sph_v2"
SPH_V2_REVISION_AUDIT = "d69dac5bda8b622bc0de316b112815c6056c06ec"
# frozen: week7_phase6_real_data_boundary_active_level_set.py::EXPECTED_HF_REVISION (final pin, 5.5+)
SPH_V2_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
# frozen: outputs/week7_06_real_data_boundary_active_level_set/output_manifest.csv
# (sha256 of primary_common_population.csv after CRLF->LF normalisation; the data pin)
POPULATION_SHA256_LF = "d31391e256c7b07f0ee4544baf65a6aeb80df21c7cba2cbf8cd2a2b24524ccbe"

# --- schema constants ------------------------------------------------------
# frozen: week7_phase6_real_data_boundary_active_level_set.py::FEATURE_COLUMNS / FEATURE_UNITS
# (== week7_sph_v2_common.py::FEATURE_UNITS; LS is the Gaussian spot RADIUS in metres.
# Week 6 phase 4 and Week 7 phases 3/4 modelled LS in micrometres -- not the population.)
FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}
# frozen: week7_sph_v2_common.py::PARTITIONS / PARTITION_ORDER (== week7_phase6::LABEL_FILES)
PARTITIONS: dict[str, str] = {
    "new-data": "labels_partition_1_new-data.csv",
    "old-data-local": "labels_partition_2_old-data-local.csv",
    "old-data-remote-clean": "labels_partition_3_old-data-remote-clean.csv",
}
LABEL_FILES = PARTITIONS
PARTITION_ORDER = list(PARTITIONS)
# frozen: week7_sph_v2_common.py::PHYSICAL_LABELS / TECHNICAL_LABELS
PHYSICAL_LABELS = {"Forming Phase", "Conduction", "Keyhole"}
TECHNICAL_LABELS = {
    "Initial Emptiness",
    "Scanning Stopped",
    "Solidifying Stopped",
    "Screenshot Bug",
    "Unsure",
}
# frozen: week7_sph_v2_common.py::load_partition_labels (``expected`` ledger schema)
LEDGER_COLUMNS = [
    "name", "hash", "P", "VX", "LS", "ST", "bug_free", "correctly_finished",
    "timestep", "label_1", "label_2", "label_final",
]
# frozen: week7_sph_v2_common.py::FOLDER_KEYS / FOLDER_PATTERN
FOLDER_KEYS = ["P", "VX", "LS", "ST", "M", "XI", "XF", "XL", "TE", "DT", "H"]
FOLDER_PATTERN = re.compile(
    r"^P-(?P<P>[^_]+)_VX-(?P<VX>[^_]+)_LS-(?P<LS>[^_]+)_"
    r"ST-(?P<ST>[^_]+)_M-(?P<M>[^_]+)_XI-(?P<XI>[^_]+)_"
    r"XF-(?P<XF>[^_]+)_XL-(?P<XL>[^_]+)_TE-(?P<TE>[^_]+)_"
    r"DT-(?P<DT>[^_]+)_H-(?P<H>[^_]+)$"
)
_NUMERIC_FOLDER_KEYS = ["P", "VX", "LS", "ST", "XI", "XF", "XL", "TE", "DT"]

# frozen: week7_phase6_real_data_boundary_active_level_set.py::load_population_tables
# (strict-bool and numeric column lists; has_conduction added, already boolean in the file)
POPULATION_BOOL_COLUMNS = [
    "has_keyhole",
    "has_conduction",
    "physical_target_extraction_success",
    "ready__max_depth",
    "ready__G3",
    "source_label_modified",
    "simulation_silently_removed",
]
POPULATION_NUMERIC_COLUMNS = FEATURE_COLUMNS + ["value__max_depth", "value__G3"]
POPULATION_ROWS = 405
POPULATION_KEYHOLE = 73
INPUT_MATCH_ATOL = 1e-14  # frozen: week7_phase1::build_experiment_registry value_checks


# --- experiment names ------------------------------------------------------


# frozen: week7_sph_v2_common.py::decode_number
def decode_number(value: Any) -> float:
    """Decode the repository's ``101p25`` -> 101.25 / ``-0p0002`` -> -0.0002 encoding.

    Numbers pass through as float; ``None``/NaN/blank give NaN.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return math.nan
    return float(text.replace("p", "."))


# frozen: week7_sph_v2_common.py::parse_experiment_name
def parse_experiment_name(name: str) -> dict[str, Any]:
    """Parse one ``sph_v2`` folder name ``P-.._VX-.._LS-.._ST-.._M-.._XI-.._XF-.._XL-.._TE-.._DT-.._H-..``.

    Returns ``experiment_name``, ``folder_name_valid``, the nine decoded
    numbers, ``material`` and ``folder_hash`` (NaN / '' when the name is invalid).
    """
    match = FOLDER_PATTERN.fullmatch(str(name))
    if not match:
        return {
            "experiment_name": str(name),
            "folder_name_valid": False,
            **{key: math.nan for key in _NUMERIC_FOLDER_KEYS},
            "material": "",
            "folder_hash": "",
        }
    values = match.groupdict()
    return {
        "experiment_name": str(name),
        "folder_name_valid": True,
        **{key: decode_number(values[key]) for key in _NUMERIC_FOLDER_KEYS},
        "material": values["M"],
        "folder_hash": values["H"],
    }


# --- hashing and population ------------------------------------------------


# frozen: week7_phase6_real_data_boundary_active_level_set.py::input_tuple_hash
def input_tuple_hash(frame: pd.DataFrame) -> pd.Series:
    """sha256 of ``'%.17g'``-formatted ``P|VX|LS|ST`` (the group key of every split)."""

    def one(row: pd.Series) -> str:
        text = "|".join(f"{float(row[col]):.17g}" for col in FEATURE_COLUMNS)
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    return frame.apply(one, axis=1)


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::load_population (checks)
# and week7_phase6_real_data_boundary_active_level_set.py::load_population_tables (typing, flags)
def load_population(path: Path = POPULATION_CSV) -> pd.DataFrame:
    """Load the frozen 405-row primary population in its frozen row order.

    Requires 405 rows, 73 ``has_keyhole``, unique ``experiment_name``, finite
    features and no modified / silently-removed source rows; boolean columns
    are parsed strictly, feature and target columns coerced to float.
    """
    frame = pd.read_csv(Path(path), low_memory=False)
    for column in POPULATION_BOOL_COLUMNS:
        if column in frame.columns:
            frame[column] = strict_bool(frame[column])
    for column in POPULATION_NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    require(len(frame) == POPULATION_ROWS, f"Frozen primary population must contain {POPULATION_ROWS} rows")
    require(int(frame["has_keyhole"].sum()) == POPULATION_KEYHOLE, "Frozen population must contain 73 Keyhole labels")
    require(frame["experiment_name"].is_unique, "Experiment names must be unique")
    require(bool(frame[FEATURE_COLUMNS].notna().all(axis=None)), "Population features must be finite")
    if "source_label_modified" in frame.columns:
        require(not frame["source_label_modified"].any(), "A source label was marked modified")
    if "simulation_silently_removed" in frame.columns:
        require(not frame["simulation_silently_removed"].any(), "A simulation was marked silently removed")
    return frame.reset_index(drop=True)


# --- pinned downloads (network) --------------------------------------------


def raw_dir(revision: str = SPH_V2_REVISION) -> Path:
    """Local cache ``data/raw/sph_v2/<revision>`` (gitignored; the archive's ``RAW_ROOT`` layout)."""
    return DATA_DIR / "raw" / "sph_v2" / revision


# frozen: week7_sph_v2_common.py::download_pinned_file
def download_pinned_file(
    filename: str,
    revision: str = SPH_V2_REVISION,
    local_dir: Path | None = None,
    *,
    repo: str = SPH_V2_REPO,
    force: bool = False,
) -> Path:
    """Download one dataset file at an exact revision (needs network).

    ``hf_hub_download(repo_type='dataset', revision=<pin>, local_dir=<cache>)``;
    ``local_dir`` defaults to :func:`raw_dir` of the revision.
    """
    from huggingface_hub import hf_hub_download  # network optional; never at import

    target = Path(local_dir) if local_dir is not None else raw_dir(revision)
    target.mkdir(parents=True, exist_ok=True)
    return Path(
        hf_hub_download(
            repo_id=repo,
            repo_type="dataset",
            revision=revision,
            filename=filename,
            local_dir=target,
            force_download=force,
        )
    )


# frozen: week7_sph_v2_common.py::load_partition_labels (offline half)
def read_partition_ledgers(paths: dict[str, Path]) -> pd.DataFrame:
    """Combine the three partition ledgers (``paths`` maps partition -> csv).

    Exact schema check, then ``partition_number`` (1..3), ``partition``,
    ``partition_label_file``, ``frame_row_in_partition`` inserted at the front,
    ``P/VX/LS/ST_numeric`` decoded, ``experiment_name = name``.
    """
    frames: list[pd.DataFrame] = []
    for number, (partition, filename) in enumerate(PARTITIONS.items(), start=1):
        frame = pd.read_csv(paths[partition])
        if frame.columns.tolist() != LEDGER_COLUMNS:
            raise RuntimeError(f"{filename}: unexpected label schema {frame.columns.tolist()}")
        frame.insert(0, "partition_number", number)
        frame.insert(1, "partition", partition)
        frame.insert(2, "partition_label_file", filename)
        frame.insert(3, "frame_row_in_partition", np.arange(len(frame), dtype=int))
        for feature in FEATURE_COLUMNS:
            frame[f"{feature}_numeric"] = frame[feature].map(decode_number)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined["experiment_name"] = combined["name"].astype(str)
    return combined


# frozen: week7_sph_v2_common.py::load_partition_labels
def load_partition_labels(revision: str = SPH_V2_REVISION, local_dir: Path | None = None) -> pd.DataFrame:
    """Download (pinned) and combine the three partition ledgers (needs network)."""
    paths = {
        partition: download_pinned_file(filename, revision, local_dir)
        for partition, filename in PARTITIONS.items()
    }
    return read_partition_ledgers(paths)


# --- per-experiment registry ------------------------------------------------


# frozen: week7_phase1_sph_v2_dataset_shift_audit.py::collapsed
def collapsed(values: Sequence[str]) -> list[str]:
    """Run-length collapse of a label sequence (consecutive duplicates removed)."""
    return [value for index, value in enumerate(values) if index == 0 or value != values[index - 1]]


# frozen: week7_phase1_sph_v2_dataset_shift_audit.py::keyhole_segments
def keyhole_segments(values: Sequence[str]) -> list[tuple[int, int]]:
    """Inclusive ``(start, end)`` frame indices of maximal ``Keyhole`` runs."""
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values):
        if value == "Keyhole" and start is None:
            start = index
        if value != "Keyhole" and start is not None:
            segments.append((start, index - 1))
            start = None
    if start is not None:
        segments.append((start, len(values) - 1))
    return segments


# frozen: week7_phase1_sph_v2_dataset_shift_audit.py::sequence_audit (label flags)
# and ::build_experiment_registry (inputs; sorted by partition, experiment_name)
def experiment_registry(labels: pd.DataFrame) -> pd.DataFrame:
    """Per-experiment inputs and manual-label summary from the frame ledgers.

    ``labels`` needs ``partition``, ``experiment_name`` (or ``name``),
    ``timestep``, ``label_final``; optional ``frame_row_in_partition`` (default:
    row order) and ``P/VX/LS/ST_numeric`` (ledger cross-check).  Frames are
    ordered by ``(timestep, frame_row_in_partition)``; ``has_keyhole`` =
    any(label_final == 'Keyhole'), ``has_conduction`` likewise, keyhole fraction
    = Keyhole frames / physical-label frames, transient = last physical frame is
    not Keyhole, persistent = it is.  P/VX/LS/ST are decoded from the folder
    name (the archive read parameters.json and verified both at atol 1e-14).
    Rows sorted by (partition, experiment_name); ``input_tuple_sha256`` added.
    """
    frame = labels.copy()
    if "experiment_name" not in frame.columns:
        frame["experiment_name"] = frame["name"].astype(str)
    if "frame_row_in_partition" not in frame.columns:
        frame["frame_row_in_partition"] = np.arange(len(frame), dtype=int)
    frame["timestep"] = pd.to_numeric(frame["timestep"], errors="coerce")
    ledger_inputs = all(f"{feature}_numeric" in frame.columns for feature in FEATURE_COLUMNS)
    rows: list[dict[str, Any]] = []
    for (partition, name), subset in frame.groupby(["partition", "experiment_name"], sort=True):
        ordered = subset.sort_values(["timestep", "frame_row_in_partition"], kind="stable").reset_index(drop=True)
        values = ordered["label_final"].astype(str).tolist()
        compressed = collapsed(values)
        is_physical = ordered["label_final"].isin(PHYSICAL_LABELS).to_numpy()
        physical_values = [value for value, keep in zip(values, is_physical) if keep]
        segments = keyhole_segments(values)
        keyhole_positions = np.flatnonzero(ordered["label_final"].eq("Keyhole").to_numpy())
        conduction_positions = np.flatnonzero(ordered["label_final"].eq("Conduction").to_numpy())
        relevant_count = len(physical_values)
        last_physical = physical_values[-1] if physical_values else None
        parsed = parse_experiment_name(name)
        row: dict[str, Any] = {
            "partition": partition,
            "experiment_name": str(name),
            "folder_name_valid": parsed["folder_name_valid"],
            **{feature: parsed[feature] for feature in FEATURE_COLUMNS},
            "material": parsed["material"],
            "folder_hash": parsed["folder_hash"],
            "labelled_frame_count": len(ordered),
            "distinct_label_count": int(ordered["label_final"].nunique()),
            "label_change_count": max(0, len(compressed) - 1),
            "collapsed_label_sequence": " -> ".join(compressed),
            "collapsed_physical_sequence": " -> ".join(collapsed(physical_values)) if physical_values else "",
            "first_physical_label": physical_values[0] if physical_values else "",
            "last_physical_label": last_physical if last_physical is not None else "",
            "has_conduction": bool(len(conduction_positions)),
            "has_keyhole": bool(len(keyhole_positions)),
            "first_conduction_frame_index": int(conduction_positions[0]) if len(conduction_positions) else np.nan,
            "first_conduction_timestep": int(ordered.loc[conduction_positions[0], "timestep"]) if len(conduction_positions) else np.nan,
            "first_keyhole_frame_index": int(keyhole_positions[0]) if len(keyhole_positions) else np.nan,
            "first_keyhole_timestep": int(ordered.loc[keyhole_positions[0], "timestep"]) if len(keyhole_positions) else np.nan,
            "last_keyhole_frame_index": int(keyhole_positions[-1]) if len(keyhole_positions) else np.nan,
            "last_keyhole_timestep": int(ordered.loc[keyhole_positions[-1], "timestep"]) if len(keyhole_positions) else np.nan,
            "keyhole_frame_count": len(keyhole_positions),
            "relevant_physical_frame_count": relevant_count,
            "keyhole_fraction_of_relevant_physical_frames": len(keyhole_positions) / relevant_count if relevant_count else np.nan,
            "keyhole_segment_count": len(segments),
            "maximum_keyhole_segment_frames": max((end - start + 1 for start, end in segments), default=0),
            "keyhole_transient_by_sequence": bool(len(keyhole_positions) and last_physical is not None and last_physical != "Keyhole"),
            "keyhole_persistent_to_last_physical_frame": bool(len(keyhole_positions) and last_physical is not None and last_physical == "Keyhole"),
            "repeated_keyhole_episodes": len(segments) > 1,
            "label_sequence_sha256": hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest(),
        }
        if ledger_inputs:
            row["inputs_match_partition_ledger"] = all(
                bool(np.isclose(parsed[feature], float(ordered[f"{feature}_numeric"].iloc[0]), rtol=0.0, atol=INPUT_MATCH_ATOL))
                for feature in FEATURE_COLUMNS
            )
        rows.append(row)
    registry = pd.DataFrame(rows).sort_values(["partition", "experiment_name"], kind="stable").reset_index(drop=True)
    registry["input_tuple_sha256"] = input_tuple_hash(registry) if len(registry) else pd.Series(dtype=str)
    return registry
