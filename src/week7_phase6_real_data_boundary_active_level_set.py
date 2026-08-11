"""Week 7 Phase 6 real-data boundary and active level-set benchmark.

This module implements the first central real-data experiment of the thesis.
It compares a direct Gaussian-process classifier for Ioan's manual
experiment-level Keyhole label with a Gaussian-process regression level set
for the unchanged maximum-penetration-depth response.  G3 is retained as a
secondary, matched complete-case comparator.

The implementation is deliberately fail-closed about information flow:

* outer test rows are never queried or used for fitting or thresholding;
* unqueried pool labels and physical responses are never read by acquisition;
* the empirical manual-label boundary score is evaluation-only;
* every active arm in one outer run shares the same split and warm start;
* the physical threshold is estimated only from already queried responses and
  manual labels, with the direction fixed to ``higher -> Keyhole``.

The expensive active stage is restart-safe.  Each outer run is cached in a
separate checkpoint, and all reported tables are rebuilt from those caches.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import pickle
import subprocess
import tempfile
import textwrap
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download
from joblib import Parallel, delayed
from scipy.spatial import Delaunay, QhullError, distance
from scipy.stats import norm
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import TransformedTargetRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, RBF
from sklearn.linear_model import LogisticRegression, Ridge, RidgeCV
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from src.week7_sph_v2_common import output_manifest, sha256_file, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
SMOKE_DIR = OUTPUT_DIR / "smoke"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "06_real_data_boundary_active_level_set.ipynb"

PHASE55_OUTPUT = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
PHASE5_OUTPUT = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
PHASE4_OUTPUT = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"
PHASE1_OUTPUT = ROOT / "outputs" / "week7_01_sph_v2_audit"

SPH_V2_REPO_ID = "ioandanielc/sph_v2"
EXPECTED_HF_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
EXPECTED_PHASE55_PARENT = "6cc2ea150b9deb6ec9dd529d94ac55cc86556cfb"
PHASE6_BRANCH = "codex/week7-phase6-real-data-boundary-active-level-set"
PHASE55_BRANCH = "codex/week7-phase5-5-g3-robustness-transfer"

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
FEATURE_DISPLAY = ["P_W", "VX_m_per_s", "LS_um", "ST_K"]
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}
PARTITION_ORDER = ["new-data", "old-data-local", "old-data-remote-clean"]
LABEL_FILES = {
    "new-data": "labels_partition_1_new-data.csv",
    "old-data-local": "labels_partition_2_old-data-local.csv",
    "old-data-remote-clean": "labels_partition_3_old-data-remote-clean.csv",
}

BASE_SEED = 6022026
N_SPLITS = 5
N_REPEATS = 4
N_OUTER_RUNS = N_SPLITS * N_REPEATS
NOMINAL_WARM_START = 12
MAX_WARM_START = 80
FINAL_BUDGET = 80
PRESENTATION_CHECKPOINTS = (12, 15, 20, 25, 30, 40, 50, 60, 70, 80)
BOUNDARY_QUANTILES = (10, 20, 30)
KNN_MIXING_K = 10
STRADDLE_KAPPA = 1.96
CLASSIFIER_GATE_FRACTION = 0.10
CLASSIFIER_MIN_SHORTLIST_SIZE = 25
CLASSIFIER_REPULSION_BANDWIDTH = 0.15
THRESHOLD_BOOTSTRAP_RESAMPLES = 1000
PAIRED_BOOTSTRAP_RESAMPLES = 5000
THRESHOLD_BOOTSTRAP_BUDGETS = (20, 40, 60, 80)
NEAR_RECORDING_END_FRACTION = 0.05
RAW_REVIEW_PER_REASON = 5

KERNEL_CONSTANT_BOUNDS = (1e-3, 1e3)
KERNEL_LENGTH_BOUNDS = (1e-2, 1e2)
GPR_ALPHA_PRIMARY = 1e-8
GPR_ALPHA_RETRY = 1e-6
ACTIVE_OPTIMIZER_RESTARTS = 0
STATIC_OPTIMIZER_RESTARTS = 0

PRIMARY_METHODS = (
    "max_depth_random",
    "max_depth_boundary_proximity",
    "max_depth_straddle",
    "max_depth_randomized_straddle",
    "max_depth_expected_feasibility",
    "binary_random",
    "binary_margin",
    "binary_uncertainty_repulsion",
)
SECONDARY_G3_METHODS = (
    "g3_random",
    "g3_straddle",
    "max_depth_g3_common_random",
    "max_depth_g3_common_straddle",
    "binary_g3_common_random",
    "binary_g3_common_margin",
)

METHOD_FORMULATION = {
    "max_depth_random": "max_depth",
    "max_depth_boundary_proximity": "max_depth",
    "max_depth_straddle": "max_depth",
    "max_depth_randomized_straddle": "max_depth",
    "max_depth_expected_feasibility": "max_depth",
    "binary_random": "binary",
    "binary_margin": "binary",
    "binary_uncertainty_repulsion": "binary",
    "g3_random": "g3",
    "g3_straddle": "g3",
    "max_depth_g3_common_random": "max_depth",
    "max_depth_g3_common_straddle": "max_depth",
    "binary_g3_common_random": "binary",
    "binary_g3_common_margin": "binary",
}


@dataclass(frozen=True)
class RunSpec:
    benchmark_population: str
    run_id: str
    repeat: int
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    run_seed: int


@dataclass
class FitResult:
    model: Any
    scaler: StandardScaler
    y_mean: float | None
    y_scale: float | None
    fit_status: str
    warnings: list[str]
    kernel: str
    constant_value: float | None
    length_scale: float | None
    bound_hit: bool
    alpha: float | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git_output(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def stable_seed(*parts: object) -> int:
    digest = hashlib.sha256(":".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**32)


def stable_rng(*parts: object) -> np.random.Generator:
    return np.random.default_rng(stable_seed(*parts))


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapping = {"true": True, "false": False, "1": True, "0": False}
    lowered = series.astype(str).str.strip().str.lower()
    require(lowered.isin(mapping).all(), f"Unexpected boolean values: {sorted(lowered.unique())}")
    return lowered.map(mapping).astype(bool)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def atomic_pickle(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
        temp = Path(handle.name)
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temp.replace(path)


def load_pickle(path: Path) -> Any:
    with path.open("rb") as handle:
        return pickle.load(handle)


def append_json_history(path: Path, entry: Mapping[str, Any]) -> None:
    history: list[dict[str, Any]] = []
    if path.is_file():
        history = json.loads(path.read_text(encoding="utf-8"))
    history.append(dict(json_safe(entry)))
    write_json(path, history)


def resolve_live_hf_revision() -> str:
    revision = str(HfApi().dataset_info(SPH_V2_REPO_ID, revision="main").sha)
    require(len(revision) == 40, f"Unexpected Hugging Face revision: {revision}")
    return revision


def download_current_label_ledgers(revision: str) -> pd.DataFrame:
    """Retrieve only the three current-revision annotation ledgers.

    Phase 5.5 proved the label paths unchanged.  Phase 6 still pins these small
    top-level ledgers because an exact saved-frame/max-depth timing join cannot
    be reconstructed from experiment-level summaries alone.
    """

    local_root = ROOT / "data" / "raw" / "sph_v2" / revision / "phase6_labels"
    frames: list[pd.DataFrame] = []
    for partition, filename in LABEL_FILES.items():
        path = Path(
            hf_hub_download(
                repo_id=SPH_V2_REPO_ID,
                repo_type="dataset",
                revision=revision,
                filename=filename,
                local_dir=local_root,
            )
        )
        frame = pd.read_csv(path)
        required = {"name", "timestep", "label_final"}
        require(required.issubset(frame.columns), f"{filename}: missing {required - set(frame.columns)}")
        frame = frame.rename(columns={"name": "experiment_name"})
        frame.insert(0, "partition", partition)
        frame["timestep"] = pd.to_numeric(frame["timestep"], errors="coerce")
        frame["frame_row_in_partition"] = np.arange(len(frame), dtype=int)
        frames.append(frame)
    labels = pd.concat(frames, ignore_index=True)
    return labels.sort_values(
        ["experiment_name", "timestep", "frame_row_in_partition"], kind="mergesort"
    ).reset_index(drop=True)


def input_tuple_hash(frame: pd.DataFrame) -> pd.Series:
    def one(row: pd.Series) -> str:
        text = "|".join(f"{float(row[col]):.17g}" for col in FEATURE_COLUMNS)
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    return frame.apply(one, axis=1)


def load_population_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = PHASE55_OUTPUT / "current_revision_simulation_level_targets.parquet"
    sequence_source = PHASE55_OUTPUT / "physical_proxy_population_reference.csv"
    require(source.is_file(), f"Missing authoritative Phase 5.5 target table: {source}")
    require(sequence_source.is_file(), f"Missing Phase 5.5 label-sequence join: {sequence_source}")
    full = pd.read_parquet(source)
    sequence = pd.read_csv(sequence_source, low_memory=False)
    require(len(full) == 407, f"Expected 407 retained rows, found {len(full)}")
    require(full["experiment_name"].is_unique, "Authoritative target table has duplicate experiments")
    require(sequence["experiment_name"].is_unique, "Phase 5.5 sequence join has duplicate experiments")
    extra_columns = [
        "experiment_name",
        "collapsed_physical_sequence",
        "keyhole_segment_count_phase1",
        "maximum_keyhole_segment_frames",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
        "first_keyhole_timestep_y",
        "last_keyhole_timestep",
        "label_sequence_sha256",
        "parameters_sha256",
        "frames_csv_sha256",
        "keyhole_persistence_group",
        "repeated_episode_group",
        "keyhole_timing_group",
    ]
    available_extra = [column for column in extra_columns if column in sequence.columns]
    full = full.merge(
        sequence[available_extra], on="experiment_name", how="left", validate="one_to_one"
    )
    full["P"] = pd.to_numeric(full["P_W"], errors="coerce")
    full["VX"] = pd.to_numeric(full["VX_m_per_s"], errors="coerce")
    full["LS"] = pd.to_numeric(full["LS_m"], errors="coerce")
    full["ST"] = pd.to_numeric(full["ST_K"], errors="coerce")
    full["value__max_depth"] = pd.to_numeric(full["max_depth_um"], errors="coerce")
    full["value__G3"] = pd.to_numeric(full["G3_persistent_depth_um"], errors="coerce")
    full["ready__max_depth"] = full["geometry_target_ready"].fillna(False)
    full["ready__G3"] = full["geometry_target_ready"].fillna(False) & full["value__G3"].notna()
    for column in [
        "has_keyhole",
        "physical_target_extraction_success",
        "ready__max_depth",
        "ready__G3",
        "source_label_modified",
        "simulation_silently_removed",
    ]:
        full[column] = strict_bool(full[column])
    for column in FEATURE_COLUMNS + ["value__max_depth", "value__G3"]:
        full[column] = pd.to_numeric(full[column], errors="coerce")

    full["valid_manual_label"] = full["has_keyhole"].notna()
    full["valid_features"] = full[FEATURE_COLUMNS].notna().all(axis=1)
    full["valid_max_depth"] = full["ready__max_depth"] & full["value__max_depth"].notna()
    full["physical_target_ready"] = full["physical_target_extraction_success"]
    full["primary_ready"] = (
        full["valid_manual_label"]
        & full["valid_features"]
        & full["valid_max_depth"]
        & full["physical_target_ready"]
    )
    full["g3_ready"] = full["ready__G3"] & full["value__G3"].notna()
    full["secondary_g3_ready"] = full["primary_ready"] & full["g3_ready"]

    def reasons(row: pd.Series) -> str:
        values: list[str] = []
        if not row["valid_manual_label"]:
            values.append("missing_manual_label")
        if not row["valid_features"]:
            values.append("missing_physical_input")
        if not row["physical_target_ready"]:
            values.append("physical_target_not_ready")
        if not row["valid_max_depth"]:
            values.append("maximum_depth_not_ready")
        return ";".join(values)

    full["primary_exclusion_reasons"] = full.apply(reasons, axis=1)
    full["g3_exclusion_reasons"] = np.where(
        full["secondary_g3_ready"], "", np.where(~full["primary_ready"], full["primary_exclusion_reasons"], "G3_not_ready")
    )
    full["input_tuple_sha256"] = input_tuple_hash(full)
    full["input_group_size"] = full.groupby("input_tuple_sha256")["experiment_name"].transform("size")

    primary = full.loc[full["primary_ready"]].copy().reset_index(drop=True)
    secondary = full.loc[full["secondary_g3_ready"]].copy().reset_index(drop=True)
    require(len(primary) == 405, f"Primary population drift: expected 405, found {len(primary)}")
    require(len(secondary) == 404, f"G3 population drift: expected 404, found {len(secondary)}")
    require(int(primary["has_keyhole"].sum()) == 73, "Primary Keyhole count drift")
    require(not primary["source_label_modified"].any(), "A source label was marked modified")
    require(not primary["simulation_silently_removed"].any(), "A simulation was marked silently removed")
    return full, primary, secondary


def build_empirical_boundary_reference(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the model-independent manual-label boundary diagnostic."""

    frame = population[["experiment_name", "partition", "has_keyhole", *FEATURE_COLUMNS]].copy()
    scaler = StandardScaler().fit(frame[FEATURE_COLUMNS])
    x_scaled = scaler.transform(frame[FEATURE_COLUMNS])
    labels = frame["has_keyhole"].astype(int).to_numpy()
    names = frame["experiment_name"].astype(str).to_numpy()
    dmat = distance.cdist(x_scaled, x_scaled, metric="euclidean")
    np.fill_diagonal(dmat, np.inf)
    opposite = labels[:, None] != labels[None, :]
    opposite_distances = np.where(opposite, dmat, np.inf)
    nearest_pos = np.argmin(opposite_distances, axis=1)
    frame["empirical_boundary_distance"] = opposite_distances[np.arange(len(frame)), nearest_pos]
    frame["nearest_opposite_experiment"] = names[nearest_pos]
    frame["nearest_opposite_label"] = labels[nearest_pos]
    frame["boundary_rank"] = frame["empirical_boundary_distance"].rank(method="first")
    frame["boundary_rank_fraction"] = frame["boundary_rank"] / len(frame)
    for q in BOUNDARY_QUANTILES:
        count = int(math.ceil(q / 100.0 * len(frame)))
        order = frame.sort_values(
            ["empirical_boundary_distance", "experiment_name"], kind="mergesort"
        ).index[:count]
        frame[f"global_q{q}"] = False
        frame.loc[order, f"global_q{q}"] = True

    k = min(KNN_MIXING_K, len(frame) - 1)
    neighbors = NearestNeighbors(n_neighbors=k + 1).fit(x_scaled)
    _, indices = neighbors.kneighbors(x_scaled)
    neighbor_labels = labels[indices[:, 1:]]
    p = neighbor_labels.mean(axis=1)
    entropy = np.zeros_like(p, dtype=float)
    mask = (p > 0) & (p < 1)
    entropy[mask] = -(p[mask] * np.log2(p[mask]) + (1 - p[mask]) * np.log2(1 - p[mask]))
    frame["knn_k"] = k
    frame["knn_positive_fraction"] = p
    frame["knn_label_entropy_bits"] = entropy
    frame["knn_opposite_fraction"] = (neighbor_labels != labels[:, None]).mean(axis=1)
    for j, feature in enumerate(FEATURE_COLUMNS):
        frame[f"standardized_{feature}"] = x_scaled[:, j]

    subset_rows = []
    for q in BOUNDARY_QUANTILES:
        subset = frame[frame[f"global_q{q}"]]
        subset_rows.append(
            {
                "population": "primary_common",
                "subset": f"global_q{q}",
                "requested_percent": q,
                "row_count": len(subset),
                "keyhole_count": int(subset["has_keyhole"].sum()),
                "non_keyhole_count": int((~subset["has_keyhole"]).sum()),
                "maximum_distance": float(subset["empirical_boundary_distance"].max()),
                "median_distance": float(subset["empirical_boundary_distance"].median()),
            }
        )
    summary = pd.DataFrame(subset_rows)
    validation = pd.DataFrame(
        [
            {
                "check_id": "EB01",
                "check": "Only physical inputs and manual labels used",
                "status": "PASS",
                "detail": "P,VX,LS,ST standardized once on the full common evaluation population; opposite manual-label distance only",
            },
            {
                "check_id": "EB02",
                "check": "Self excluded",
                "status": "PASS" if np.isinf(np.diag(dmat)).all() else "FAIL",
                "detail": f"n={len(frame)}",
            },
            {
                "check_id": "EB03",
                "check": "No max-depth, G3, or model prediction enters score",
                "status": "PASS",
                "detail": "Function signature consumes the population identifier, partition, manual label, and four inputs only",
            },
            {
                "check_id": "EB04",
                "check": "Evaluation-only prohibition recorded",
                "status": "PASS",
                "detail": "The score is joined only after acquisition selection and is never passed to model/acquisition functions",
            },
        ]
    )
    return frame, summary, validation


def assign_test_boundary_subsets(test_indices: Sequence[int], boundary: pd.DataFrame) -> pd.DataFrame:
    subset = boundary.iloc[list(test_indices)][["experiment_name", "empirical_boundary_distance"]].copy()
    subset = subset.sort_values(["empirical_boundary_distance", "experiment_name"], kind="mergesort")
    for q in BOUNDARY_QUANTILES:
        count = int(math.ceil(q / 100.0 * len(subset)))
        subset[f"test_q{q}"] = False
        subset.iloc[:count, subset.columns.get_loc(f"test_q{q}")] = True
    return subset.sort_index()


def build_outer_splits(population: pd.DataFrame, benchmark_population: str) -> tuple[list[RunSpec], pd.DataFrame, pd.DataFrame]:
    labels = population["has_keyhole"].astype(int).to_numpy()
    groups = population["input_tuple_sha256"].astype(str).to_numpy()
    specs: list[RunSpec] = []
    manifest_rows: list[dict[str, Any]] = []
    balance_rows: list[dict[str, Any]] = []
    x_dummy = np.zeros((len(population), 1))
    for repeat in range(N_REPEATS):
        splitter = StratifiedGroupKFold(
            n_splits=N_SPLITS,
            shuffle=True,
            random_state=stable_seed(BASE_SEED, benchmark_population, repeat),
        )
        for fold, (train, test) in enumerate(splitter.split(x_dummy, labels, groups), start=1):
            run_id = f"{benchmark_population}__r{repeat + 1:02d}_f{fold:02d}"
            spec = RunSpec(
                benchmark_population=benchmark_population,
                run_id=run_id,
                repeat=repeat + 1,
                fold=fold,
                train_indices=tuple(map(int, train)),
                test_indices=tuple(map(int, test)),
                run_seed=stable_seed(BASE_SEED, run_id),
            )
            specs.append(spec)
            for role, indices in [("training_pool", train), ("untouched_test", test)]:
                for idx in indices:
                    row = population.iloc[int(idx)]
                    manifest_rows.append(
                        {
                            "benchmark_population": benchmark_population,
                            "run_id": run_id,
                            "repeat": repeat + 1,
                            "fold": fold,
                            "role": role,
                            "population_row_index": int(idx),
                            "experiment_name": row["experiment_name"],
                            "partition": row["partition"],
                            "has_keyhole": bool(row["has_keyhole"]),
                            "input_tuple_sha256": row["input_tuple_sha256"],
                        }
                    )
                subset = population.iloc[indices]
                for partition in [*PARTITION_ORDER, "all"]:
                    part = subset if partition == "all" else subset[subset["partition"].eq(partition)]
                    balance_rows.append(
                        {
                            "benchmark_population": benchmark_population,
                            "run_id": run_id,
                            "repeat": repeat + 1,
                            "fold": fold,
                            "role": role,
                            "partition": partition,
                            "row_count": len(part),
                            "keyhole_count": int(part["has_keyhole"].sum()),
                            "non_keyhole_count": int((~part["has_keyhole"]).sum()),
                            "keyhole_fraction": float(part["has_keyhole"].mean()) if len(part) else math.nan,
                        }
                    )
            require(set(train).isdisjoint(test), f"{run_id}: train/test overlap")
            require(set(groups[train]).isdisjoint(groups[test]), f"{run_id}: duplicate input group leakage")
    require(len(specs) == N_OUTER_RUNS, f"Expected {N_OUTER_RUNS} runs")
    return specs, pd.DataFrame(manifest_rows), pd.DataFrame(balance_rows)


def threshold_candidates(values: np.ndarray) -> np.ndarray:
    unique = np.unique(np.asarray(values, dtype=float))
    if len(unique) == 1:
        scale = max(abs(float(unique[0])), 1.0)
        return np.array([unique[0] - scale * 1e-12, unique[0] + scale * 1e-12])
    middle = (unique[:-1] + unique[1:]) / 2.0
    scale = max(float(np.ptp(unique)), float(np.max(np.abs(unique))), 1.0)
    epsilon = scale * 1e-12
    return np.concatenate([[unique[0] - epsilon], middle, [unique[-1] + epsilon]])


def choose_higher_threshold(values: Sequence[float], labels: Sequence[int]) -> dict[str, Any]:
    values_arr = np.asarray(values, dtype=float)
    labels_arr = np.asarray(labels, dtype=int)
    require(set(np.unique(labels_arr)) == {0, 1}, "Threshold calibration requires both manual classes")
    thresholds = threshold_candidates(values_arr)
    predictions = values_arr[:, None] > thresholds[None, :]
    positive = labels_arr == 1
    negative = labels_arr == 0
    sensitivity = predictions[positive].mean(axis=0)
    specificity = (~predictions[negative]).mean(axis=0)
    accuracy = (predictions == labels_arr[:, None]).mean(axis=0)
    balanced = (sensitivity + specificity) / 2.0
    median = float(np.median(values_arr))
    scale = max(float(np.std(values_arr)), 1e-12)
    candidates = pd.DataFrame(
        {
            "threshold": thresholds,
            "balanced_accuracy": balanced,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "minimum_class_recall": np.minimum(sensitivity, specificity),
            "accuracy": accuracy,
            "standardized_distance_from_training_median": np.abs(thresholds - median) / scale,
        }
    ).sort_values(
        [
            "balanced_accuracy",
            "minimum_class_recall",
            "accuracy",
            "standardized_distance_from_training_median",
            "threshold",
        ],
        ascending=[False, False, False, True, True],
        kind="mergesort",
    )
    selected = candidates.iloc[0].to_dict()
    max_negative = float(np.max(values_arr[negative]))
    min_positive = float(np.min(values_arr[positive]))
    selected.update(
        {
            "direction": "higher",
            "comparison_operator": ">",
            "max_negative": max_negative,
            "min_positive": min_positive,
            "observed_gap": min_positive - max_negative,
            "class_separable": bool(max_negative < min_positive),
            "queried_positive_count": int(positive.sum()),
            "queried_negative_count": int(negative.sum()),
        }
    )
    return selected


def bootstrap_threshold(
    values: np.ndarray,
    labels: np.ndarray,
    *,
    seed: int,
    resamples: int = THRESHOLD_BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    positive = np.flatnonzero(labels == 1)
    negative = np.flatnonzero(labels == 0)
    if len(positive) < 2 or len(negative) < 2:
        return {
            "bootstrap_resamples": resamples,
            "valid_resamples": 0,
            "ci_low": math.nan,
            "median": math.nan,
            "ci_high": math.nan,
            "status": "NA_fewer_than_two_per_class",
        }
    rng = np.random.default_rng(seed)
    thresholds = np.empty(resamples, dtype=float)
    for b in range(resamples):
        sample = np.concatenate(
            [rng.choice(negative, len(negative), replace=True), rng.choice(positive, len(positive), replace=True)]
        )
        thresholds[b] = choose_higher_threshold(values[sample], labels[sample])["threshold"]
    low, median, high = np.quantile(thresholds, [0.025, 0.5, 0.975])
    return {
        "bootstrap_resamples": resamples,
        "valid_resamples": resamples,
        "ci_low": float(low),
        "median": float(median),
        "ci_high": float(high),
        "status": "PASS",
    }


def make_signal_kernel(kind: str = "matern32") -> Any:
    if kind == "matern32":
        base = Matern(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS, nu=1.5)
    elif kind == "matern52":
        base = Matern(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS, nu=2.5)
    elif kind == "rbf":
        base = RBF(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS)
    else:
        raise ValueError(f"Unknown kernel kind: {kind}")
    return ConstantKernel(1.0, constant_value_bounds=KERNEL_CONSTANT_BOUNDS) * base


def extract_kernel_diagnostics(kernel: Any) -> tuple[float | None, float | None, bool]:
    try:
        constant = float(kernel.k1.constant_value)
        length = float(np.ravel(kernel.k2.length_scale)[0])
        tol = 1e-5
        hit = bool(
            constant <= KERNEL_CONSTANT_BOUNDS[0] * (1 + tol)
            or constant >= KERNEL_CONSTANT_BOUNDS[1] * (1 - tol)
            or length <= KERNEL_LENGTH_BOUNDS[0] * (1 + tol)
            or length >= KERNEL_LENGTH_BOUNDS[1] * (1 - tol)
        )
        return constant, length, hit
    except (AttributeError, TypeError, ValueError):
        return None, None, False


def fit_gpr(
    x: np.ndarray,
    y: np.ndarray,
    *,
    scaler: StandardScaler,
    seed: int,
    kernel_kind: str = "matern32",
    restarts: int = ACTIVE_OPTIMIZER_RESTARTS,
) -> FitResult:
    x_scaled = scaler.transform(x)
    y_mean = float(np.mean(y))
    y_scale = float(np.std(y, ddof=0))
    if not math.isfinite(y_scale) or y_scale < 1e-12:
        y_scale = 1.0
    y_scaled = (np.asarray(y, dtype=float) - y_mean) / y_scale
    caught: list[str] = []
    last_error = ""
    for alpha, status in [(GPR_ALPHA_PRIMARY, "optimized_primary"), (GPR_ALPHA_RETRY, "optimized_jitter_retry")]:
        model = GaussianProcessRegressor(
            kernel=make_signal_kernel(kernel_kind),
            alpha=alpha,
            normalize_y=False,
            optimizer="fmin_l_bfgs_b",
            n_restarts_optimizer=restarts,
            random_state=seed,
        )
        try:
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always")
                model.fit(x_scaled, y_scaled)
            caught.extend(str(record.message) for record in records)
            constant, length, hit = extract_kernel_diagnostics(model.kernel_)
            return FitResult(
                model=model,
                scaler=scaler,
                y_mean=y_mean,
                y_scale=y_scale,
                fit_status=status,
                warnings=caught,
                kernel=str(model.kernel_),
                constant_value=constant,
                length_scale=length,
                bound_hit=hit,
                alpha=alpha,
            )
        except Exception as exc:  # numerical fallback is recorded, never silent
            last_error = f"{type(exc).__name__}: {exc}"
            caught.append(last_error)

    # Preserve the last optimized kernel shape where possible but disable the
    # optimizer.  This is a fail-safe for numerical continuation, not a
    # substitute scientific method.
    fallback = GaussianProcessRegressor(
        kernel=make_signal_kernel(kernel_kind),
        alpha=GPR_ALPHA_RETRY,
        normalize_y=False,
        optimizer=None,
        random_state=seed,
    )
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        fallback.fit(x_scaled, y_scaled)
    caught.extend(str(record.message) for record in records)
    constant, length, hit = extract_kernel_diagnostics(fallback.kernel_)
    return FitResult(
        model=fallback,
        scaler=scaler,
        y_mean=y_mean,
        y_scale=y_scale,
        fit_status=f"fixed_kernel_fallback_after:{last_error}",
        warnings=caught,
        kernel=str(fallback.kernel_),
        constant_value=constant,
        length_scale=length,
        bound_hit=hit,
        alpha=GPR_ALPHA_RETRY,
    )


def predict_gpr(fit: FitResult, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu_scaled, sigma_scaled = fit.model.predict(fit.scaler.transform(x), return_std=True)
    mu = np.asarray(mu_scaled, dtype=float) * float(fit.y_scale) + float(fit.y_mean)
    sigma = np.maximum(np.asarray(sigma_scaled, dtype=float) * float(fit.y_scale), 1e-12)
    return mu, sigma


def fit_gpc(
    x: np.ndarray,
    labels: np.ndarray,
    *,
    scaler: StandardScaler,
    seed: int,
    kernel_kind: str = "matern32",
    restarts: int = ACTIVE_OPTIMIZER_RESTARTS,
) -> FitResult:
    x_scaled = scaler.transform(x)
    caught: list[str] = []
    model = GaussianProcessClassifier(
        kernel=make_signal_kernel(kernel_kind),
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=restarts,
        max_iter_predict=100,
        warm_start=False,
        random_state=seed,
    )
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            model.fit(x_scaled, labels)
        caught.extend(str(record.message) for record in records)
        constant, length, hit = extract_kernel_diagnostics(model.kernel_)
        return FitResult(
            model=model,
            scaler=scaler,
            y_mean=None,
            y_scale=None,
            fit_status="optimized_primary",
            warnings=caught,
            kernel=str(model.kernel_),
            constant_value=constant,
            length_scale=length,
            bound_hit=hit,
        )
    except Exception as exc:
        caught.append(f"{type(exc).__name__}: {exc}")

    fixed = GaussianProcessClassifier(
        kernel=make_signal_kernel(kernel_kind),
        optimizer=None,
        max_iter_predict=200,
        random_state=seed,
    )
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            fixed.fit(x_scaled, labels)
        caught.extend(str(record.message) for record in records)
        constant, length, hit = extract_kernel_diagnostics(fixed.kernel_)
        return FitResult(
            model=fixed,
            scaler=scaler,
            y_mean=None,
            y_scale=None,
            fit_status="fixed_kernel_fallback",
            warnings=caught,
            kernel=str(fixed.kernel_),
            constant_value=constant,
            length_scale=length,
            bound_hit=hit,
        )
    except Exception as exc:
        caught.append(f"{type(exc).__name__}: {exc}")

    logistic = LogisticRegression(C=1.0, max_iter=2000, random_state=seed)
    logistic.fit(x_scaled, labels)
    return FitResult(
        model=logistic,
        scaler=scaler,
        y_mean=None,
        y_scale=None,
        fit_status="logistic_numerical_fallback",
        warnings=caught,
        kernel="NA_logistic_fallback",
        constant_value=None,
        length_scale=None,
        bound_hit=False,
    )


def predict_gpc(fit: FitResult, x: np.ndarray) -> np.ndarray:
    return np.asarray(fit.model.predict_proba(fit.scaler.transform(x))[:, 1], dtype=float)


def continuous_probability(mu: np.ndarray, sigma: np.ndarray, threshold: float) -> np.ndarray:
    """P(response > threshold) conditional on a point threshold estimate."""

    z = (np.asarray(mu, dtype=float) - float(threshold)) / np.maximum(np.asarray(sigma, dtype=float), 1e-12)
    return np.clip(norm.cdf(z), 1e-12, 1 - 1e-12)


def deterministic_argmax(indices: np.ndarray, scores: np.ndarray) -> int:
    order = np.lexsort((np.asarray(indices, dtype=int), -np.asarray(scores, dtype=float)))
    return int(order[0])


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    span = float(np.ptp(scores))
    return np.zeros_like(scores) if span <= 1e-15 else (scores - scores.min()) / span


def expected_feasibility_scores(
    mu: np.ndarray,
    sigma: np.ndarray,
    threshold: float,
    nodes: int = 24,
) -> np.ndarray:
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-12)
    centered_mu = np.asarray(mu, dtype=float) - float(threshold)
    epsilon = STRADDLE_KAPPA * sigma
    quadrature_x, quadrature_w = np.polynomial.hermite.hermgauss(nodes)
    samples = centered_mu[None, :] + np.sqrt(2.0) * sigma[None, :] * quadrature_x[:, None]
    improvement = np.maximum(epsilon[None, :] ** 2 - samples**2, 0.0)
    return (quadrature_w[:, None] * improvement).sum(axis=0) / np.sqrt(np.pi)


def choose_continuous_candidate(
    *,
    method: str,
    candidate_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    threshold: float,
    rng: np.random.Generator,
) -> tuple[int, dict[str, Any]]:
    centered = np.abs(mu - threshold)
    metadata: dict[str, Any] = {}
    if method.endswith("boundary_proximity"):
        scores = -centered
        acquisition = "minimum_abs_mean_minus_threshold"
    elif method.endswith("randomized_straddle"):
        chi_square_draw = float(rng.chisquare(df=2.0))
        scores = math.sqrt(chi_square_draw) * sigma - centered
        metadata["chi_square_df2_draw"] = chi_square_draw
        acquisition = "historical_randomized_straddle"
    elif method.endswith("expected_feasibility"):
        scores = expected_feasibility_scores(mu, sigma, threshold)
        metadata["gauss_hermite_nodes"] = 24
        acquisition = "translated_expected_feasibility"
    elif method.endswith("straddle"):
        scores = STRADDLE_KAPPA * sigma - centered
        metadata["kappa"] = STRADDLE_KAPPA
        acquisition = "fixed_straddle"
    else:
        raise ValueError(f"Unknown continuous method: {method}")
    position = deterministic_argmax(candidate_indices, scores)
    metadata.update(
        {
            "acquisition_definition": acquisition,
            "selected_position": position,
            "selected_score": float(scores[position]),
            "selected_mu": float(mu[position]),
            "selected_sigma_latent": float(sigma[position]),
            "selected_abs_mean_minus_threshold": float(centered[position]),
        }
    )
    return int(candidate_indices[position]), metadata


def choose_binary_candidate(
    *,
    method: str,
    candidate_indices: np.ndarray,
    probabilities: np.ndarray,
    pool_scaled: np.ndarray,
    queried_indices: Sequence[int],
) -> tuple[int, dict[str, Any]]:
    uncertainty = 1.0 - 2.0 * np.abs(probabilities - 0.5)
    if method.endswith("margin"):
        position = deterministic_argmax(candidate_indices, uncertainty)
        return int(candidate_indices[position]), {
            "acquisition_definition": "classifier_margin",
            "selected_position": position,
            "selected_probability": float(probabilities[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
        }
    if not method.endswith("uncertainty_repulsion"):
        raise ValueError(f"Unknown binary method: {method}")
    shortlist_size = min(
        len(candidate_indices),
        max(CLASSIFIER_MIN_SHORTLIST_SIZE, int(math.ceil(CLASSIFIER_GATE_FRACTION * len(candidate_indices)))),
    )
    shortlist_order = np.lexsort((candidate_indices, -uncertainty))[:shortlist_size]
    shortlist_indices = candidate_indices[shortlist_order]
    shortlist_uncertainty = uncertainty[shortlist_order]
    candidate_x = pool_scaled[shortlist_indices]
    queried_x = pool_scaled[np.asarray(queried_indices, dtype=int)]
    distances = distance.cdist(candidate_x, queried_x).min(axis=1)
    normalized = normalize_scores(shortlist_uncertainty)
    repulsion = 1.0 - np.exp(
        -(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12)
    )
    scores = normalized * repulsion
    choice = deterministic_argmax(shortlist_indices, scores)
    original_position = int(shortlist_order[choice])
    return int(shortlist_indices[choice]), {
        "acquisition_definition": "historical_classifier_uncertainty_repulsion",
        "gate_fraction": CLASSIFIER_GATE_FRACTION,
        "min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
        "shortlist_size": shortlist_size,
        "repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
        "selected_position": original_position,
        "selected_probability": float(probabilities[original_position]),
        "selected_uncertainty_score": float(uncertainty[original_position]),
        "selected_normalized_uncertainty": float(normalized[choice]),
        "selected_distance_to_queried": float(distances[choice]),
        "selected_repulsion": float(repulsion[choice]),
        "selected_score": float(scores[choice]),
    }


def classification_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray | None,
    predictions: np.ndarray,
    *,
    boundary_flags: Mapping[int, np.ndarray] | None = None,
    ranking_scores: np.ndarray | None = None,
) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=int)
    predictions = np.asarray(predictions, dtype=int)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    result: dict[str, Any] = {
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else math.nan,
        "specificity": float(tn / (tn + fp)) if tn + fp else math.nan,
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "global_error": float(np.mean(predictions != labels)),
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }
    score = probabilities if probabilities is not None else ranking_scores
    if score is not None and len(np.unique(labels)) == 2:
        result["roc_auc"] = float(roc_auc_score(labels, score))
        result["average_precision"] = float(average_precision_score(labels, score))
    else:
        result["roc_auc"] = math.nan
        result["average_precision"] = math.nan
    result["brier_score"] = (
        float(brier_score_loss(labels, probabilities)) if probabilities is not None else math.nan
    )
    if boundary_flags:
        for q, flag in boundary_flags.items():
            flag_arr = np.asarray(flag, dtype=bool)
            result[f"q{q}_error"] = (
                float(np.mean(predictions[flag_arr] != labels[flag_arr])) if flag_arr.any() else math.nan
            )
            result[f"q{q}_count"] = int(flag_arr.sum())
            result[f"q{q}_keyhole_count"] = int(labels[flag_arr].sum())
    return result


def regression_metrics(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    labels = np.asarray(labels, dtype=float)
    predictions = np.asarray(predictions, dtype=float)
    mae = float(mean_absolute_error(labels, predictions))
    rmse = float(math.sqrt(mean_squared_error(labels, predictions)))
    scale = max(float(np.mean(np.abs(labels))), 1e-12)
    return {
        "mae": mae,
        "rmse": rmse,
        "relative_mae": mae / scale,
        "relative_rmse": rmse / scale,
        "r2": float(r2_score(labels, predictions)),
    }


def test_boundary_flags(spec: RunSpec, boundary: pd.DataFrame) -> dict[int, np.ndarray]:
    subset = assign_test_boundary_subsets(spec.test_indices, boundary)
    return {q: subset[f"test_q{q}"].to_numpy(bool) for q in BOUNDARY_QUANTILES}


def run_static_fold(
    spec: RunSpec,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
) -> pd.DataFrame:
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    depth = population["value__max_depth"].to_numpy(float)
    scaler = StandardScaler().fit(x[train])
    threshold = choose_higher_threshold(depth[train], labels[train])
    flags = test_boundary_flags(spec, boundary)
    rows: list[dict[str, Any]] = []

    continuous_models = ["mean", "linear_ridge", "polynomial2_ridge", "matern32_gpr", "matern52_gpr", "rbf_gpr"]
    for position, model_name in enumerate(continuous_models):
        probability: np.ndarray | None = None
        sigma = np.full(len(test), math.nan)
        fit_status = "PASS"
        kernel = "NA"
        warning_text = ""
        kernel_constant = math.nan
        kernel_length_scale = math.nan
        kernel_bound_hit = False
        if model_name == "mean":
            predicted_depth = np.repeat(float(np.mean(depth[train])), len(test))
        elif model_name in {"linear_ridge", "polynomial2_ridge"}:
            steps: list[tuple[str, Any]] = [("scale", StandardScaler())]
            if model_name == "polynomial2_ridge":
                steps.append(("poly", PolynomialFeatures(degree=2, include_bias=False)))
            steps.append(("ridge", RidgeCV(alphas=np.logspace(-4, 4, 17))))
            model = Pipeline(steps)
            model.fit(x[train], depth[train])
            predicted_depth = model.predict(x[test])
        else:
            kind = {"matern32_gpr": "matern32", "matern52_gpr": "matern52", "rbf_gpr": "rbf"}[model_name]
            fit = fit_gpr(
                x[train], depth[train], scaler=scaler, seed=stable_seed(spec.run_seed, model_name),
                kernel_kind=kind, restarts=STATIC_OPTIMIZER_RESTARTS,
            )
            predicted_depth, sigma = predict_gpr(fit, x[test])
            probability = continuous_probability(predicted_depth, sigma, threshold["threshold"])
            fit_status = fit.fit_status
            kernel = fit.kernel
            warning_text = " | ".join(fit.warnings)
            kernel_constant = fit.constant_value if fit.constant_value is not None else math.nan
            kernel_length_scale = fit.length_scale if fit.length_scale is not None else math.nan
            kernel_bound_hit = fit.bound_hit
        predicted_label = (predicted_depth > float(threshold["threshold"])).astype(int)
        for local, idx in enumerate(test):
            rows.append(
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "formulation": "max_depth",
                    "response_target": "maximum_depth_um",
                    "model": model_name,
                    "experiment_name": population.iloc[idx]["experiment_name"],
                    "partition": population.iloc[idx]["partition"],
                    "has_keyhole": int(labels[idx]),
                    "true_max_depth_um": float(depth[idx]),
                    "predicted_max_depth_um": float(predicted_depth[local]),
                    "true_response_um": float(depth[idx]),
                    "predicted_response_um": float(predicted_depth[local]),
                    "latent_std_um": float(sigma[local]) if math.isfinite(float(sigma[local])) else math.nan,
                    "training_only_threshold_um": float(threshold["threshold"]),
                    "keyhole_probability": float(probability[local]) if probability is not None else math.nan,
                    "probability_available": probability is not None,
                    "ranking_score": float(predicted_depth[local]),
                    "predicted_keyhole": int(predicted_label[local]),
                    "fit_status": fit_status,
                    "kernel": kernel,
                    "kernel_constant": kernel_constant,
                    "kernel_length_scale": kernel_length_scale,
                    "kernel_bound_hit": kernel_bound_hit,
                    "optimizer_warnings": warning_text,
                    **{f"test_q{q}": bool(flags[q][local]) for q in BOUNDARY_QUANTILES},
                }
            )

    binary_models = ["prevalence", "logistic", "matern32_gpc", "matern52_gpc", "rbf_gpc"]
    for model_name in binary_models:
        fit_status = "PASS"
        kernel = "NA"
        warning_text = ""
        kernel_constant = math.nan
        kernel_length_scale = math.nan
        kernel_bound_hit = False
        if model_name == "prevalence":
            probability = np.repeat(float(np.mean(labels[train])), len(test))
        elif model_name == "logistic":
            model = Pipeline(
                [("scale", StandardScaler()), ("logistic", LogisticRegression(C=1.0, max_iter=2000, random_state=spec.run_seed))]
            )
            model.fit(x[train], labels[train])
            probability = model.predict_proba(x[test])[:, 1]
        else:
            kind = {"matern32_gpc": "matern32", "matern52_gpc": "matern52", "rbf_gpc": "rbf"}[model_name]
            fit = fit_gpc(
                x[train], labels[train], scaler=scaler, seed=stable_seed(spec.run_seed, model_name),
                kernel_kind=kind, restarts=STATIC_OPTIMIZER_RESTARTS,
            )
            probability = predict_gpc(fit, x[test])
            fit_status = fit.fit_status
            kernel = fit.kernel
            warning_text = " | ".join(fit.warnings)
            kernel_constant = fit.constant_value if fit.constant_value is not None else math.nan
            kernel_length_scale = fit.length_scale if fit.length_scale is not None else math.nan
            kernel_bound_hit = fit.bound_hit
        predicted_label = (probability >= 0.5).astype(int)
        for local, idx in enumerate(test):
            rows.append(
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "formulation": "binary",
                    "response_target": "manual_has_keyhole",
                    "model": model_name,
                    "experiment_name": population.iloc[idx]["experiment_name"],
                    "partition": population.iloc[idx]["partition"],
                    "has_keyhole": int(labels[idx]),
                    "true_max_depth_um": float(depth[idx]),
                    "predicted_max_depth_um": math.nan,
                    "true_response_um": math.nan,
                    "predicted_response_um": math.nan,
                    "latent_std_um": math.nan,
                    "training_only_threshold_um": math.nan,
                    "keyhole_probability": float(probability[local]),
                    "probability_available": True,
                    "ranking_score": float(probability[local]),
                    "predicted_keyhole": int(predicted_label[local]),
                    "fit_status": fit_status,
                    "kernel": kernel,
                    "kernel_constant": kernel_constant,
                    "kernel_length_scale": kernel_length_scale,
                    "kernel_bound_hit": kernel_bound_hit,
                    "optimizer_warnings": warning_text,
                    **{f"test_q{q}": bool(flags[q][local]) for q in BOUNDARY_QUANTILES},
                }
            )
    return pd.DataFrame(rows)


def run_secondary_static_fold(
    spec: RunSpec,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
) -> pd.DataFrame:
    """Matched three-way Matérn-3/2 diagnostic on the 404-row G3 common set."""

    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    scaler = StandardScaler().fit(x[train])
    flags = test_boundary_flags(spec, boundary)
    rows: list[dict[str, Any]] = []

    for formulation, response_column, model_name in [
        ("max_depth", "value__max_depth", "matern32_gpr_g3_common"),
        ("g3", "value__G3", "g3_matern32_gpr"),
    ]:
        response = population[response_column].to_numpy(float)
        threshold = choose_higher_threshold(response[train], labels[train])
        fit = fit_gpr(
            x[train], response[train], scaler=scaler,
            seed=stable_seed(spec.run_seed, formulation, "secondary_static"),
            kernel_kind="matern32", restarts=STATIC_OPTIMIZER_RESTARTS,
        )
        mu, sigma = predict_gpr(fit, x[test])
        probability = continuous_probability(mu, sigma, threshold["threshold"])
        predicted = (mu > threshold["threshold"]).astype(int)
        for local, idx in enumerate(test):
            rows.append(
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "formulation": formulation,
                    "response_target": "maximum_depth_um" if formulation == "max_depth" else "G3_persistent_depth_um",
                    "model": model_name,
                    "experiment_name": population.iloc[idx]["experiment_name"],
                    "partition": population.iloc[idx]["partition"],
                    "has_keyhole": int(labels[idx]),
                    "true_max_depth_um": float(response[idx]),
                    "predicted_max_depth_um": float(mu[local]),
                    "true_response_um": float(response[idx]),
                    "predicted_response_um": float(mu[local]),
                    "latent_std_um": float(sigma[local]),
                    "training_only_threshold_um": float(threshold["threshold"]),
                    "keyhole_probability": float(probability[local]),
                    "probability_available": True,
                    "ranking_score": float(mu[local]),
                    "predicted_keyhole": int(predicted[local]),
                    "fit_status": fit.fit_status,
                    "kernel": fit.kernel,
                    "kernel_constant": fit.constant_value,
                    "kernel_length_scale": fit.length_scale,
                    "kernel_bound_hit": fit.bound_hit,
                    "optimizer_warnings": " | ".join(fit.warnings),
                    **{f"test_q{q}": bool(flags[q][local]) for q in BOUNDARY_QUANTILES},
                }
            )

    fit = fit_gpc(
        x[train], labels[train], scaler=scaler,
        seed=stable_seed(spec.run_seed, "binary", "secondary_static"),
        kernel_kind="matern32", restarts=STATIC_OPTIMIZER_RESTARTS,
    )
    probability = predict_gpc(fit, x[test])
    predicted = (probability >= 0.5).astype(int)
    for local, idx in enumerate(test):
        rows.append(
            {
                "benchmark_population": spec.benchmark_population,
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "formulation": "binary",
                "response_target": "manual_has_keyhole",
                "model": "binary_matern32_gpc_g3_common",
                "experiment_name": population.iloc[idx]["experiment_name"],
                "partition": population.iloc[idx]["partition"],
                "has_keyhole": int(labels[idx]),
                "true_max_depth_um": float(population.iloc[idx]["value__max_depth"]),
                "predicted_max_depth_um": math.nan,
                "true_response_um": math.nan,
                "predicted_response_um": math.nan,
                "latent_std_um": math.nan,
                "training_only_threshold_um": math.nan,
                "keyhole_probability": float(probability[local]),
                "probability_available": True,
                "ranking_score": float(probability[local]),
                "predicted_keyhole": int(predicted[local]),
                "fit_status": fit.fit_status,
                "kernel": fit.kernel,
                "kernel_constant": fit.constant_value,
                "kernel_length_scale": fit.length_scale,
                "kernel_bound_hit": fit.bound_hit,
                "optimizer_warnings": " | ".join(fit.warnings),
                **{f"test_q{q}": bool(flags[q][local]) for q in BOUNDARY_QUANTILES},
            }
        )
    return pd.DataFrame(rows)


def summarize_static_predictions(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, Any]] = []
    for (benchmark_population, run_id, formulation, model), group in predictions.groupby(
        ["benchmark_population", "run_id", "formulation", "model"], sort=True
    ):
        labels = group["has_keyhole"].to_numpy(int)
        predicted = group["predicted_keyhole"].to_numpy(int)
        probability = group["keyhole_probability"].to_numpy(float)
        probability_arg = probability if group["probability_available"].all() else None
        flags = {q: group[f"test_q{q}"].to_numpy(bool) for q in BOUNDARY_QUANTILES}
        metrics = classification_metrics(
            labels,
            probability_arg,
            predicted,
            boundary_flags=flags,
            ranking_scores=group["ranking_score"].to_numpy(float),
        )
        row = {
            "benchmark_population": benchmark_population,
            "run_id": run_id,
            "formulation": formulation,
            "model": model,
            **metrics,
        }
        if formulation == "max_depth":
            row.update(
                regression_metrics(
                    group["true_max_depth_um"].to_numpy(float),
                    group["predicted_max_depth_um"].to_numpy(float),
                )
            )
        fold_rows.append(row)
    folds = pd.DataFrame(fold_rows)
    metric_columns = [
        "balanced_accuracy", "sensitivity", "specificity", "precision", "f1", "roc_auc",
        "average_precision", "brier_score", "global_error", "q10_error", "q20_error", "q30_error",
        "mae", "rmse", "relative_mae", "relative_rmse", "r2",
    ]
    summary_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    for (benchmark_population, formulation, model), group in folds.groupby(
        ["benchmark_population", "formulation", "model"], sort=True
    ):
        for metric in metric_columns:
            if metric not in group:
                continue
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            if not len(values):
                # Do not emit misleading zero-run placeholder rows for
                # unavailable quantities (for example G3 regression metrics
                # when that response-level diagnostic was not requested).
                continue
            summary_rows.append(
                {
                    "benchmark_population": benchmark_population,
                    "formulation": formulation,
                    "model": model,
                    "metric": metric,
                    "run_count": len(values),
                    "mean": float(values.mean()) if len(values) else math.nan,
                    "std": float(values.std(ddof=1)) if len(values) > 1 else math.nan,
                    "median": float(values.median()) if len(values) else math.nan,
                    "minimum": float(values.min()) if len(values) else math.nan,
                    "maximum": float(values.max()) if len(values) else math.nan,
                }
            )
        for q in BOUNDARY_QUANTILES:
            metric = f"q{q}_error"
            values = group[metric].dropna()
            boundary_rows.append(
                {
                    "benchmark_population": benchmark_population,
                    "formulation": formulation,
                    "model": model,
                    "boundary_subset": f"q{q}",
                    "primary_metric": q in {20, 30},
                    "run_count": len(values),
                    "mean_error": float(values.mean()),
                    "std_error": float(values.std(ddof=1)),
                    "median_error": float(values.median()),
                }
            )

    calibration_rows: list[dict[str, Any]] = []
    available = predictions[predictions["probability_available"]].copy()
    for (benchmark_population, formulation, model), group in available.groupby(
        ["benchmark_population", "formulation", "model"], sort=True
    ):
        bins = pd.cut(group["keyhole_probability"], bins=np.linspace(0, 1, 11), include_lowest=True, duplicates="drop")
        for interval, part in group.groupby(bins, observed=True):
            calibration_rows.append(
                {
                    "benchmark_population": benchmark_population,
                    "formulation": formulation,
                    "model": model,
                    "probability_bin": str(interval),
                    "row_count": len(part),
                    "mean_predicted_probability": float(part["keyhole_probability"].mean()),
                    "observed_keyhole_fraction": float(part["has_keyhole"].mean()),
                    "status": "held_out_20_fold_pooled_diagnostic",
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(boundary_rows), pd.DataFrame(calibration_rows)


def warm_start_indices(spec: RunSpec, population: pd.DataFrame, final_budget: int) -> tuple[list[int], np.ndarray]:
    pool = np.asarray(spec.train_indices, dtype=int)
    rng = stable_rng(BASE_SEED, spec.run_id, "shared_pool_permutation")
    permutation = pool[rng.permutation(len(pool))]
    labels = population["has_keyhole"].astype(int).to_numpy()
    effective_limit = min(MAX_WARM_START, final_budget, len(permutation))
    queried: list[int] = []
    for idx in permutation[:effective_limit]:
        queried.append(int(idx))
        if len(queried) >= NOMINAL_WARM_START and len(np.unique(labels[queried])) == 2:
            break
    require(
        len(np.unique(labels[queried])) == 2,
        f"{spec.run_id}: warm start did not reveal both classes by budget {effective_limit}",
    )
    return queried, permutation


def active_arm_fingerprint(
    spec: RunSpec,
    method: str,
    population: pd.DataFrame,
    final_budget: int,
    threshold_bootstrap_resamples: int,
) -> str:
    payload = {
        "phase55_parent": EXPECTED_PHASE55_PARENT,
        "hf_revision": EXPECTED_HF_REVISION,
        "run_spec": asdict(spec),
        "method": method,
        "population_hash": hashlib.sha256(
            population[["experiment_name", "has_keyhole", "value__max_depth", "value__G3", *FEATURE_COLUMNS]]
            .to_csv(index=False)
            .encode("utf-8")
        ).hexdigest(),
        "final_budget": final_budget,
        "threshold_bootstrap_resamples": threshold_bootstrap_resamples,
        "constants": {
            "nominal_warm_start": NOMINAL_WARM_START,
            "max_warm_start": MAX_WARM_START,
            "straddle_kappa": STRADDLE_KAPPA,
            "gpr_alpha": GPR_ALPHA_PRIMARY,
            "constant_bounds": KERNEL_CONSTANT_BOUNDS,
            "length_bounds": KERNEL_LENGTH_BOUNDS,
            "active_optimizer_restarts": ACTIVE_OPTIMIZER_RESTARTS,
            "classifier_gate_fraction": CLASSIFIER_GATE_FRACTION,
            "classifier_min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
            "classifier_repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
        },
    }
    return hashlib.sha256(json.dumps(json_safe(payload), sort_keys=True).encode("utf-8")).hexdigest()


def method_checkpoint_path(checkpoint_root: Path, spec: RunSpec, method: str) -> Path:
    safe_run = spec.run_id.replace("/", "_")
    return checkpoint_root / safe_run / f"{method}.pkl"


def write_run_log(checkpoint_root: Path, spec: RunSpec, message: str) -> None:
    path = checkpoint_root / spec.run_id.replace("/", "_") / "progress.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")


def query_history_row(
    *,
    spec: RunSpec,
    method: str,
    formulation: str,
    population: pd.DataFrame,
    idx: int,
    query_order: int,
    selection_stage: str,
    metadata: Mapping[str, Any],
    boundary: pd.DataFrame,
) -> dict[str, Any]:
    row = population.iloc[idx]
    boundary_row = boundary.iloc[idx]
    return {
        "benchmark_population": spec.benchmark_population,
        "run_id": spec.run_id,
        "repeat": spec.repeat,
        "fold": spec.fold,
        "method": method,
        "formulation": formulation,
        "query_order": query_order,
        "selection_stage": selection_stage,
        "population_row_index": idx,
        "experiment_name": row["experiment_name"],
        "partition": row["partition"],
        "P": float(row["P"]),
        "VX": float(row["VX"]),
        "LS": float(row["LS"]),
        "ST": float(row["ST"]),
        "revealed_has_keyhole": int(row["has_keyhole"]),
        "revealed_max_depth_um": float(row["value__max_depth"]),
        "revealed_G3_um": float(row["value__G3"]) if pd.notna(row["value__G3"]) else math.nan,
        "empirical_boundary_distance_evaluation_only": float(boundary_row["empirical_boundary_distance"]),
        "boundary_score_consulted_before_selection": False,
        "hidden_label_consulted_before_selection": False,
        "hidden_physical_response_consulted_before_selection": False,
        "known_before_query": "P,VX,LS,ST",
        "revealed_by_query": "manual has_keyhole,max_depth,G3_if_available",
        "acquisition_metadata_json": json.dumps(json_safe(dict(metadata)), sort_keys=True),
    }


def run_active_arm(
    *,
    spec: RunSpec,
    method: str,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
    final_budget: int,
    checkpoint_root: Path,
    threshold_bootstrap_resamples: int,
    force: bool,
) -> dict[str, Any]:
    fingerprint = active_arm_fingerprint(
        spec, method, population, final_budget, threshold_bootstrap_resamples
    )
    checkpoint = method_checkpoint_path(checkpoint_root, spec, method)
    if checkpoint.is_file() and not force:
        cached = load_pickle(checkpoint)
        if cached.get("fingerprint") == fingerprint:
            return cached

    started = time.perf_counter()
    formulation = METHOD_FORMULATION[method]
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    depth = population["value__max_depth"].to_numpy(float)
    g3 = population["value__G3"].to_numpy(float)
    response = depth if formulation == "max_depth" else g3 if formulation == "g3" else None
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    scaler = StandardScaler().fit(x[train])
    pool_scaled = scaler.transform(x)
    queried, random_permutation = warm_start_indices(spec, population, final_budget)
    effective_warm = len(queried)
    random_position = effective_warm
    random_method = method.endswith("_random")
    rng = stable_rng(BASE_SEED, spec.run_id, method, "acquisition")
    boundary_flags = test_boundary_flags(spec, boundary)
    raw_prediction_budgets = {
        budget for budget in PRESENTATION_CHECKPOINTS if effective_warm <= budget <= final_budget
    } | {effective_warm, final_budget}

    query_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    warning_messages: list[str] = []
    fit_statuses: Counter[str] = Counter()
    bound_hit_count = 0

    for order, idx in enumerate(queried, start=1):
        query_rows.append(
            query_history_row(
                spec=spec,
                method=method,
                formulation=formulation,
                population=population,
                idx=idx,
                query_order=order,
                selection_stage="shared_sequential_random_warm_start",
                metadata={"shared_permutation_position": order - 1},
                boundary=boundary,
            )
        )

    for budget in range(effective_warm, final_budget + 1):
        current = np.asarray(queried, dtype=int)
        unqueried = np.asarray([idx for idx in train if idx not in set(queried)], dtype=int)
        fit_seed = stable_seed(spec.run_seed, method, budget)
        threshold: dict[str, Any] | None = None
        mu_test: np.ndarray | None = None
        sigma_test: np.ndarray | None = None

        if formulation in {"max_depth", "g3"}:
            assert response is not None
            threshold = choose_higher_threshold(response[current], labels[current])
            fit = fit_gpr(
                x[current], response[current], scaler=scaler, seed=fit_seed, kernel_kind="matern32"
            )
            mu_test, sigma_test = predict_gpr(fit, x[test])
            probability = continuous_probability(mu_test, sigma_test, threshold["threshold"])
            predicted = (mu_test > threshold["threshold"]).astype(int)
            uncertainty = sigma_test
            uncertainty_band = np.abs(mu_test - threshold["threshold"]) <= STRADDLE_KAPPA * sigma_test
            fit_statuses[fit.fit_status] += 1
            warning_messages.extend(fit.warnings)
            bound_hit_count += int(fit.bound_hit)
            threshold_rows.append(
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "formulation": formulation,
                    "budget": budget,
                    **threshold,
                    "threshold_units": "um",
                    "training_scope": "queried_only",
                    "test_information_used": False,
                    "unqueried_pool_information_used": False,
                }
            )
            bootstrap_checkpoint = budget == effective_warm or budget in THRESHOLD_BOOTSTRAP_BUDGETS
            if bootstrap_checkpoint:
                boot = bootstrap_threshold(
                    response[current],
                    labels[current],
                    seed=stable_seed(spec.run_seed, method, budget, "threshold_bootstrap"),
                    resamples=threshold_bootstrap_resamples,
                )
                bootstrap_rows.append(
                    {
                        "benchmark_population": spec.benchmark_population,
                        "run_id": spec.run_id,
                        "method": method,
                        "formulation": formulation,
                        "budget": budget,
                        "selected_set_diagnostic_only": True,
                        **boot,
                    }
                )
        else:
            fit = fit_gpc(x[current], labels[current], scaler=scaler, seed=fit_seed, kernel_kind="matern32")
            probability = predict_gpc(fit, x[test])
            predicted = (probability >= 0.5).astype(int)
            uncertainty = 1.0 - 2.0 * np.abs(probability - 0.5)
            uncertainty_band = np.abs(probability - 0.5) <= 0.10
            fit_statuses[fit.fit_status] += 1
            warning_messages.extend(fit.warnings)
            bound_hit_count += int(fit.bound_hit)

        metrics = classification_metrics(
            labels[test], probability, predicted, boundary_flags=boundary_flags
        )
        metrics.update(
            {
                "benchmark_population": spec.benchmark_population,
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "method": method,
                "formulation": formulation,
                "budget": budget,
                "effective_warm_start": effective_warm,
                "mean_predicted_uncertainty": float(np.mean(uncertainty)),
                "uncertainty_band_fraction": float(np.mean(uncertainty_band)),
                "fit_status": fit.fit_status,
                "kernel": fit.kernel,
                "kernel_constant": fit.constant_value,
                "kernel_length_scale": fit.length_scale,
                "kernel_bound_hit": fit.bound_hit,
                "optimizer_warning_count": len(fit.warnings),
                "threshold": float(threshold["threshold"]) if threshold is not None else math.nan,
                "threshold_point_estimate_probability_caveat": formulation in {"max_depth", "g3"},
            }
        )
        if formulation in {"max_depth", "g3"}:
            assert response is not None and mu_test is not None
            metrics.update(regression_metrics(response[test], mu_test))
        curve_rows.append(metrics)

        if budget in raw_prediction_budgets:
            for local, idx in enumerate(test):
                prediction_rows.append(
                    {
                        "benchmark_population": spec.benchmark_population,
                        "run_id": spec.run_id,
                        "repeat": spec.repeat,
                        "fold": spec.fold,
                        "method": method,
                        "formulation": formulation,
                        "budget": budget,
                        "experiment_name": population.iloc[idx]["experiment_name"],
                        "partition": population.iloc[idx]["partition"],
                        "has_keyhole": int(labels[idx]),
                        "keyhole_probability": float(probability[local]),
                        "predicted_keyhole": int(predicted[local]),
                        "predicted_response": (
                            float(mu_test[local]) if mu_test is not None else math.nan
                        ),
                        "latent_std": (
                            float(sigma_test[local]) if sigma_test is not None else math.nan
                        ),
                        "threshold": float(threshold["threshold"]) if threshold is not None else math.nan,
                        "empirical_boundary_distance_evaluation_only": float(
                            boundary.iloc[idx]["empirical_boundary_distance"]
                        ),
                        **{f"test_q{q}": bool(boundary_flags[q][local]) for q in BOUNDARY_QUANTILES},
                    }
                )

        if budget >= final_budget:
            break
        require(len(unqueried) > 0, f"{spec.run_id}/{method}: candidate pool exhausted")

        if random_method:
            while random_position < len(random_permutation) and int(random_permutation[random_position]) in queried:
                random_position += 1
            next_idx = int(random_permutation[random_position])
            metadata: dict[str, Any] = {
                "acquisition_definition": "shared_predetermined_random_pool_order",
                "shared_permutation_position": random_position,
            }
            random_position += 1
        elif formulation in {"max_depth", "g3"}:
            assert response is not None and threshold is not None
            mu_pool, sigma_pool = predict_gpr(fit, x[unqueried])
            next_idx, metadata = choose_continuous_candidate(
                method=method,
                candidate_indices=unqueried,
                mu=mu_pool,
                sigma=sigma_pool,
                threshold=float(threshold["threshold"]),
                rng=rng,
            )
        else:
            pool_probability = predict_gpc(fit, x[unqueried])
            next_idx, metadata = choose_binary_candidate(
                method=method,
                candidate_indices=unqueried,
                probabilities=pool_probability,
                pool_scaled=pool_scaled,
                queried_indices=queried,
            )
        require(next_idx in set(train), "Acquisition selected outside the training pool")
        require(next_idx not in set(test), "Acquisition selected a test row")
        require(next_idx not in set(queried), "Acquisition selected an already queried row")
        queried.append(next_idx)
        query_rows.append(
            query_history_row(
                spec=spec,
                method=method,
                formulation=formulation,
                population=population,
                idx=next_idx,
                query_order=len(queried),
                selection_stage="shared_random_after_warm_start" if random_method else "active_acquisition",
                metadata=metadata,
                boundary=boundary,
            )
        )

    query_frame = pd.DataFrame(query_rows)
    query_hash = hashlib.sha256(
        query_frame[["query_order", "experiment_name"]].to_csv(index=False).encode("utf-8")
    ).hexdigest()
    warm_hash = hashlib.sha256(
        query_frame.loc[query_frame["query_order"] <= effective_warm, ["query_order", "experiment_name"]]
        .to_csv(index=False)
        .encode("utf-8")
    ).hexdigest()
    split_hash = hashlib.sha256(
        json.dumps({"train": sorted(spec.train_indices), "test": sorted(spec.test_indices)}).encode("utf-8")
    ).hexdigest()
    result = {
        "fingerprint": fingerprint,
        "manifest": pd.DataFrame(
            [
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "formulation": formulation,
                    "train_pool_count": len(train),
                    "untouched_test_count": len(test),
                    "nominal_warm_start": NOMINAL_WARM_START,
                    "effective_warm_start": effective_warm,
                    "final_budget": final_budget,
                    "fit_count": int(sum(fit_statuses.values())),
                    "fit_status_counts_json": json.dumps(dict(fit_statuses), sort_keys=True),
                    "optimizer_warning_count": len(warning_messages),
                    "unique_optimizer_warning_count": len(set(warning_messages)),
                    "kernel_bound_hit_count": bound_hit_count,
                    "runtime_seconds": time.perf_counter() - started,
                    "query_trajectory_sha256": query_hash,
                    "warm_start_sha256": warm_hash,
                    "split_sha256": split_hash,
                    "checkpoint_fingerprint": fingerprint,
                }
            ]
        ),
        "initialization": pd.DataFrame(
            [
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "nominal_warm_start": NOMINAL_WARM_START,
                    "effective_warm_start": effective_warm,
                    "positive_count": int(labels[queried[:effective_warm]].sum()),
                    "negative_count": int(effective_warm - labels[queried[:effective_warm]].sum()),
                    "maximum_warm_start_limit": min(MAX_WARM_START, final_budget),
                    "same_for_all_methods": True,
                    "hidden_labels_used_to_skip_candidates": False,
                    "sequential_stop_used_revealed_labels_only": True,
                    "warm_start_sha256": warm_hash,
                }
            ]
        ),
        "queries": query_frame,
        "curves": pd.DataFrame(curve_rows),
        "predictions": pd.DataFrame(prediction_rows),
        "thresholds": pd.DataFrame(threshold_rows),
        "threshold_bootstrap": pd.DataFrame(bootstrap_rows),
        "fairness": pd.DataFrame(
            [
                {
                    "benchmark_population": spec.benchmark_population,
                    "run_id": spec.run_id,
                    "method": method,
                    "split_sha256": split_hash,
                    "warm_start_sha256": warm_hash,
                    "candidate_pool_is_outer_training_only": True,
                    "test_set_never_queried": not query_frame["population_row_index"].isin(test).any(),
                    "test_labels_used_for_fitting": False,
                    "test_responses_used_for_fitting": False,
                    "hidden_pool_labels_used_for_acquisition": False,
                    "hidden_pool_responses_used_for_acquisition": False,
                    "empirical_boundary_used_for_acquisition": False,
                    "common_final_budget": final_budget,
                    "fixed_outer_training_pool_input_scaler": True,
                    "query_local_response_scaler": formulation in {"max_depth", "g3"},
                }
            ]
        ),
    }
    atomic_pickle(checkpoint, result)
    return result


def run_outer_active(
    spec: RunSpec,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
    methods: Sequence[str],
    *,
    final_budget: int,
    checkpoint_root: Path,
    threshold_bootstrap_resamples: int,
    force: bool,
) -> list[dict[str, Any]]:
    write_run_log(checkpoint_root, spec, f"START methods={','.join(methods)} final_budget={final_budget}")
    results: list[dict[str, Any]] = []
    for method in methods:
        write_run_log(checkpoint_root, spec, f"METHOD_START {method}")
        result = run_active_arm(
            spec=spec,
            method=method,
            population=population,
            boundary=boundary,
            final_budget=final_budget,
            checkpoint_root=checkpoint_root,
            threshold_bootstrap_resamples=threshold_bootstrap_resamples,
            force=force,
        )
        results.append(result)
        runtime = float(result["manifest"]["runtime_seconds"].iloc[0])
        write_run_log(checkpoint_root, spec, f"METHOD_DONE {method} runtime_seconds={runtime:.3f}")
    write_run_log(checkpoint_root, spec, "DONE")
    return results


def concat_result_frames(results: Sequence[dict[str, Any]], key: str) -> pd.DataFrame:
    frames = [result[key] for result in results if key in result and len(result[key])]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_max_depth_event_audit(
    population: pd.DataFrame,
    saved_labels: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    episodes_path = PHASE1_OUTPUT / "keyhole_episodes.csv"
    episodes = pd.read_csv(episodes_path) if episodes_path.is_file() else pd.DataFrame()
    episode_groups = {
        name: group.sort_values("start_timestep", kind="mergesort")
        for name, group in episodes.groupby("experiment_name", sort=False)
    }
    label_groups = {
        name: group.sort_values(["timestep", "frame_row_in_partition"], kind="mergesort")
        for name, group in saved_labels.groupby("experiment_name", sort=False)
    }
    rows: list[dict[str, Any]] = []
    for _, source in population.iterrows():
        name = str(source["experiment_name"])
        iteration = float(source["max_depth_iteration"])
        labels = label_groups[name]
        timesteps = labels["timestep"].to_numpy(float)
        finite = np.isfinite(timesteps)
        timesteps = timesteps[finite]
        labels_finite = labels.loc[finite].reset_index(drop=True)
        exact_positions = np.flatnonzero(timesteps == iteration)
        exact = len(exact_positions) > 0
        exact_label = (
            str(labels_finite.iloc[int(exact_positions[0])]["label_final"]) if exact else ""
        )
        nearest_position = int(np.argmin(np.abs(timesteps - iteration)))
        nearest_timestep = float(timesteps[nearest_position])
        nearest_label = str(labels_finite.iloc[nearest_position]["label_final"])
        unique_steps = np.unique(timesteps)
        local_saved_gap = float(np.median(np.diff(unique_steps))) if len(unique_steps) > 1 else math.nan
        nearest_delta = float(abs(nearest_timestep - iteration))

        episode_relation = "no_Keyhole"
        episode_span_number = math.nan
        group = episode_groups.get(name)
        if group is not None and len(group):
            starts = group["start_timestep"].to_numpy(float)
            ends = group["end_timestep"].to_numpy(float)
            inside = np.flatnonzero((iteration >= starts) & (iteration <= ends))
            if len(inside):
                episode_relation = "inside_saved_Keyhole_episode_span"
                episode_span_number = int(group.iloc[int(inside[0])]["segment_number"])
            elif iteration < starts.min():
                episode_relation = "before_first_saved_Keyhole_frame"
            elif iteration > ends.max():
                episode_relation = "after_last_saved_Keyhole_frame"
            else:
                episode_relation = "between_saved_Keyhole_episode_spans"

        row_index = float(source["max_depth_row_index"])
        active_start = float(source["active_region_start_row_index"])
        active_end = float(source["active_region_end_row_index"])
        if row_index < active_start:
            active_relation = "before_active_region"
        elif row_index <= active_end:
            active_relation = "inside_active_region"
        else:
            active_relation = "after_active_region"
        monitor_count = float(source["monitor_row_count"])
        recording_fraction = row_index / max(monitor_count - 1.0, 1.0)
        max_time = float(source["max_depth_time_s"])
        laser_exit = float(source["laser_exit_time_s"])
        near_laser_exit_tolerance = 0.05 * max(abs(laser_exit), 1e-12)
        rows.append(
            {
                "experiment_name": name,
                "partition": source["partition"],
                "has_keyhole": bool(source["has_keyhole"]),
                "P_W": float(source["P"]),
                "VX_m_per_s": float(source["VX"]),
                "LS_um": float(source["LS"] * 1e6),
                "ST_K": float(source["ST"]),
                "max_depth_um": float(source["value__max_depth"]),
                "max_depth_row_index": int(row_index),
                "max_depth_iteration": int(iteration),
                "max_depth_time_s": max_time,
                "max_depth_relative_to_T0": source["max_depth_relative_to_T0"],
                "max_depth_relative_to_active_region": active_relation,
                "recording_row_fraction": recording_fraction,
                "near_recording_end_last_5pct": recording_fraction >= 1.0 - NEAR_RECORDING_END_FRACTION,
                "laser_exit_time_s": laser_exit,
                "max_depth_minus_laser_exit_time_s": max_time - laser_exit,
                "near_laser_exit_within_5pct_exit_time": abs(max_time - laser_exit) <= near_laser_exit_tolerance,
                "manual_has_keyhole": bool(source["has_keyhole"]),
                "first_keyhole_timestep": source.get("first_keyhole_timestep", math.nan),
                "last_keyhole_timestep": source.get("last_keyhole_timestep", math.nan),
                "keyhole_frame_count": int(source["keyhole_frame_count"]),
                "keyhole_segment_count": int(source.get("keyhole_segment_count_phase1", 0) or 0),
                "keyhole_transient_by_sequence": bool(source.get("keyhole_transient_by_sequence", False)),
                "keyhole_persistent_to_last_physical_frame": bool(
                    source.get("keyhole_persistent_to_last_physical_frame", False)
                ),
                "repeated_keyhole_episodes": bool(source.get("repeated_keyhole_episodes", False)),
                "keyhole_timing_relative_to_T0": source["keyhole_timing_relative_to_T0"],
                "max_depth_exact_saved_frame_join": exact,
                "exact_saved_frame_label_at_max_depth": exact_label,
                "max_depth_exact_saved_Keyhole_frame": exact and exact_label == "Keyhole",
                "nearest_saved_frame_timestep": int(nearest_timestep),
                "nearest_saved_frame_label": nearest_label,
                "nearest_saved_frame_iteration_delta": nearest_delta,
                "median_saved_frame_iteration_gap": local_saved_gap,
                "nearest_saved_frame_within_one_median_gap": (
                    nearest_delta <= local_saved_gap if math.isfinite(local_saved_gap) else False
                ),
                "nearest_saved_frame_is_diagnostic_only": True,
                "saved_keyhole_episode_span_relation": episode_relation,
                "saved_keyhole_episode_span_number": episode_span_number,
                "episode_span_is_not_exact_morphology_join": True,
                "depth_ambiguity_score": source["depth_ambiguity_score"],
                "flag_depth_bounding_box_ambiguity_candidate": bool(
                    source["flag_depth_bounding_box_ambiguity_candidate"]
                ),
                "recording_ends_before_90pct_domain": bool(source["recording_ends_before_90pct_domain"]),
                "flag_primary_window_unstable_week6_rule": bool(
                    source["flag_primary_window_unstable_week6_rule"]
                ),
                "label_timestep_alignment_exact": bool(source["label_timestep_alignment_exact"]),
                "label_timestep_unmatched_count": int(source["label_timestep_unmatched_count"]),
                "side_gif_url": (
                    f"https://huggingface.co/datasets/{SPH_V2_REPO_ID}/resolve/{EXPECTED_HF_REVISION}/"
                    f"{name}/gif_files/animation_ss_side.gif"
                ),
                "frames_csv_url": (
                    f"https://huggingface.co/datasets/{SPH_V2_REPO_ID}/resolve/{EXPECTED_HF_REVISION}/{name}/frames.csv"
                ),
            }
        )
    audit = pd.DataFrame(rows)

    oracle = choose_higher_threshold(
        audit["max_depth_um"].to_numpy(float), audit["has_keyhole"].astype(int).to_numpy()
    )
    audit["descriptive_oracle_threshold_um"] = float(oracle["threshold"])
    audit["descriptive_oracle_prediction"] = audit["max_depth_um"] > float(oracle["threshold"])
    audit["descriptive_oracle_error_type"] = np.select(
        [
            audit["descriptive_oracle_prediction"] & ~audit["has_keyhole"],
            ~audit["descriptive_oracle_prediction"] & audit["has_keyhole"],
        ],
        ["false_positive", "false_negative"],
        default="correct",
    )
    audit["oracle_threshold_status"] = "descriptive_full_common_not_valid_active_method"

    summary_rows = [
        ("population_count", len(audit), "count"),
        ("keyhole_count", int(audit["has_keyhole"].sum()), "count"),
        ("exact_saved_frame_join_count", int(audit["max_depth_exact_saved_frame_join"].sum()), "count"),
        ("exact_saved_Keyhole_frame_count", int(audit["max_depth_exact_saved_Keyhole_frame"].sum()), "count"),
        ("inside_saved_Keyhole_episode_span_positive_count", int(((audit["saved_keyhole_episode_span_relation"] == "inside_saved_Keyhole_episode_span") & audit["has_keyhole"]).sum()), "count"),
        ("after_last_saved_Keyhole_frame_positive_count", int(((audit["saved_keyhole_episode_span_relation"] == "after_last_saved_Keyhole_frame") & audit["has_keyhole"]).sum()), "count"),
        ("before_T0_count", int((audit["max_depth_relative_to_T0"] == "before_T0").sum()), "count"),
        ("inside_T0_count", int((audit["max_depth_relative_to_T0"] == "inside_T0").sum()), "count"),
        ("after_T0_count", int((audit["max_depth_relative_to_T0"] == "after_T0").sum()), "count"),
        ("inside_active_region_count", int((audit["max_depth_relative_to_active_region"] == "inside_active_region").sum()), "count"),
        ("after_active_region_count", int((audit["max_depth_relative_to_active_region"] == "after_active_region").sum()), "count"),
        ("near_recording_end_count", int(audit["near_recording_end_last_5pct"].sum()), "count"),
        ("near_laser_exit_count", int(audit["near_laser_exit_within_5pct_exit_time"].sum()), "count"),
        ("ambiguity_flag_count", int(audit["flag_depth_bounding_box_ambiguity_candidate"].sum()), "count"),
        ("descriptive_oracle_false_positive_count", int((audit["descriptive_oracle_error_type"] == "false_positive").sum()), "count"),
        ("descriptive_oracle_false_negative_count", int((audit["descriptive_oracle_error_type"] == "false_negative").sum()), "count"),
        ("descriptive_oracle_threshold_um", float(oracle["threshold"]), "um"),
        ("descriptive_oracle_balanced_accuracy", float(oracle["balanced_accuracy"]), "fraction"),
    ]
    summary = pd.DataFrame(summary_rows, columns=["metric", "value", "units"])
    summary["status"] = np.where(
        summary["metric"].eq("exact_saved_frame_join_count"),
        "direct_timing_join_sparse",
        "descriptive_semantic_audit",
    )
    summary["interpretation"] = ""
    summary.loc[summary["metric"].eq("exact_saved_frame_join_count"), "interpretation"] = (
        "Exact saved-frame morphology at the max-depth iteration is generally unavailable; episode-span and nearest-frame fields are diagnostics only."
    )

    review_reasons: defaultdict[str, list[str]] = defaultdict(list)
    def add_cases(frame: pd.DataFrame, reason: str, ascending: bool = False) -> None:
        selected = frame.sort_values(
            ["max_depth_um", "experiment_name"], ascending=[ascending, True], kind="mergesort"
        ).head(RAW_REVIEW_PER_REASON)
        for name in selected["experiment_name"]:
            review_reasons[str(name)].append(reason)

    add_cases(audit[audit["has_keyhole"]], "highest_max_depth_Keyhole")
    add_cases(audit[~audit["has_keyhole"]], "highest_max_depth_non_Keyhole")
    add_cases(audit[audit["descriptive_oracle_error_type"].eq("false_positive")], "descriptive_threshold_false_positive")
    add_cases(audit[audit["descriptive_oracle_error_type"].eq("false_negative")], "descriptive_threshold_false_negative", ascending=True)
    add_cases(audit[audit["keyhole_transient_by_sequence"]], "transient_Keyhole")
    hard_path = PHASE4_OUTPUT / "depth_consensus_hard_cases.csv"
    if hard_path.is_file():
        hard = pd.read_csv(hard_path, low_memory=False)
        if "experiment_name" in hard:
            for name in hard["experiment_name"].dropna().astype(str).drop_duplicates().head(RAW_REVIEW_PER_REASON):
                if name in set(audit["experiment_name"]):
                    review_reasons[name].append("Phase4_consensus_depth_hard_case")
    review = audit[audit["experiment_name"].isin(review_reasons)].copy()
    review["review_reasons"] = review["experiment_name"].map(
        lambda value: ";".join(sorted(set(review_reasons[str(value)])))
    )
    review["selection_is_deterministic"] = True
    review["labels_changed_after_review"] = False
    review["target_redefined_after_review"] = False
    review = enrich_raw_review_depth_windows(review)
    error_review = review[review["descriptive_oracle_error_type"].ne("correct")]
    summary = pd.concat(
        [
            summary,
            pd.DataFrame(
                [
                    {
                        "metric": "raw_review_single_point_spike_candidate_count",
                        "value": int(review["single_point_spike_candidate"].fillna(False).sum()),
                        "units": "count",
                        "status": "deterministic_raw_review_subset",
                        "interpretation": "Diagnostic only; maximum-depth definition is unchanged.",
                    },
                    {
                        "metric": "oracle_error_single_point_spike_candidate_count",
                        "value": int(error_review["single_point_spike_candidate"].fillna(False).sum()),
                        "units": "count",
                        "status": "deterministic_raw_review_subset",
                        "interpretation": "Assesses whether the descriptive threshold errors are dominated by obvious isolated monitor spikes.",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    return audit, review, summary


def enrich_raw_review_depth_windows(review: pd.DataFrame, half_window: int = 10) -> pd.DataFrame:
    """Fetch only deterministic review monitors and inspect the local max window.

    This diagnostic does not alter the maximum-depth scalar.  A conservative
    single-point flag requires the stored maximum to exceed every valid local
    neighbour by both 5 micrometres and ten percent of the maximum.
    """

    local_root = ROOT / "data" / "raw" / "sph_v2" / EXPECTED_HF_REVISION / "phase6_raw_review"
    rows: list[dict[str, Any]] = []
    for _, source in review.iterrows():
        name = str(source["experiment_name"])
        relative = f"{name}/monitor/position-bounds_melt.dat"
        path = Path(
            hf_hub_download(
                repo_id=SPH_V2_REPO_ID,
                repo_type="dataset",
                revision=EXPECTED_HF_REVISION,
                filename=relative,
                local_dir=local_root,
            )
        )
        center = int(source["max_depth_row_index"])
        start = max(0, center - half_window)
        end = center + half_window
        window: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for row_index, line in enumerate(handle):
                if row_index < start:
                    continue
                if row_index > end:
                    break
                # The validated sph_v2 bounds schema is headerless CSV:
                # [x_min, x_max, y_min, y_max, z_min, z_max].  Keep a
                # whitespace fallback solely for defensive diagnostics; the
                # authoritative files are comma-separated.
                stripped = line.strip()
                fields = stripped.split(",") if "," in stripped else stripped.split()
                depth_um = math.nan
                if len(fields) >= 6:
                    try:
                        z_min = float(fields[4])
                        if math.isfinite(z_min) and abs(z_min) < 1e30:
                            depth_um = max(0.0, -z_min) * 1e6
                    except ValueError:
                        pass
                window.append(
                    {"row_index": row_index, "relative_row": row_index - center, "depth_um": depth_um}
                )
        center_values = [item["depth_um"] for item in window if item["row_index"] == center]
        neighbors = np.asarray(
            [
                item["depth_um"]
                for item in window
                if item["row_index"] != center and math.isfinite(float(item["depth_um"]))
            ],
            dtype=float,
        )
        center_depth = float(center_values[0]) if center_values else math.nan
        neighbor_median = float(np.median(neighbors)) if len(neighbors) else math.nan
        neighbor_max = float(np.max(neighbors)) if len(neighbors) else math.nan
        excess = center_depth - neighbor_median if math.isfinite(neighbor_median) else math.nan
        isolated_excess = center_depth - neighbor_max if math.isfinite(neighbor_max) else math.nan
        spike = bool(
            math.isfinite(isolated_excess)
            and isolated_excess > 5.0
            and isolated_excess > 0.10 * max(center_depth, 1e-12)
        )
        rows.append(
            {
                "experiment_name": name,
                "raw_review_position_bounds_path": relative,
                "raw_review_position_bounds_sha256": sha256_file(path),
                "raw_review_half_window_rows": half_window,
                "local_window_center_depth_um": center_depth,
                "local_window_neighbor_median_depth_um": neighbor_median,
                "local_window_neighbor_max_depth_um": neighbor_max,
                "local_spike_excess_over_neighbor_median_um": excess,
                "local_isolated_excess_over_neighbor_max_um": isolated_excess,
                "single_point_spike_candidate": spike,
                "single_point_spike_rule": "center exceeds every +/-10-row valid neighbour by >5 um and >10% of center",
                "local_depth_window_json": json.dumps(json_safe(window), separators=(",", ":")),
                "raw_review_fetch_status": "PASS",
                "raw_review_diagnostic_only": True,
            }
        )
    return review.merge(pd.DataFrame(rows), on="experiment_name", how="left", validate="one_to_one")


def summarize_active(
    curves: pd.DataFrame,
    predictions: pd.DataFrame,
    initialization: pd.DataFrame,
    queries: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    final_budget = int(curves["budget"].max())
    primary_init = initialization[initialization["benchmark_population"].eq("primary_common")]
    common_start = int(primary_init["effective_warm_start"].max())
    aulc_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    tolerance_rows: list[dict[str, Any]] = []
    metric_specs = [
        ("balanced_accuracy", 0.80, "at_least"),
        ("balanced_accuracy", 0.85, "at_least"),
        ("balanced_accuracy", 0.90, "at_least"),
        ("q20_error", 0.30, "at_most"),
        ("q20_error", 0.25, "at_most"),
        ("q20_error", 0.20, "at_most"),
        ("q30_error", 0.30, "at_most"),
        ("q30_error", 0.25, "at_most"),
        ("q30_error", 0.20, "at_most"),
    ]
    for (population_name, run_id, method, formulation), group in curves.groupby(
        ["benchmark_population", "run_id", "method", "formulation"], sort=True
    ):
        group = group.sort_values("budget")
        available_start = int(group["budget"].min())
        benchmark_common_start = (
            common_start if population_name == "primary_common" else int(
                initialization.loc[
                    initialization["benchmark_population"].eq(population_name), "effective_warm_start"
                ].max()
            )
        )
        common = group[group["budget"].ge(benchmark_common_start)]
        row: dict[str, Any] = {
            "benchmark_population": population_name,
            "run_id": run_id,
            "method": method,
            "formulation": formulation,
            "available_start_budget": available_start,
            "common_start_budget": benchmark_common_start,
            "final_budget": final_budget,
        }
        for metric in ["q20_error", "q30_error", "balanced_accuracy"]:
            row[f"common_normalized_aulc__{metric}"] = float(
                np.trapezoid(common[metric], common["budget"]) / max(final_budget - benchmark_common_start, 1)
            )
            row[f"warm_relative_normalized_aulc__{metric}"] = float(
                np.trapezoid(group[metric], group["budget"]) / max(final_budget - available_start, 1)
            )
        aulc_rows.append(row)
        final = group[group["budget"].eq(final_budget)]
        require(len(final) == 1, f"{run_id}/{method}: missing final budget")
        final_rows.append(final.iloc[0].to_dict())
        for metric, target, direction in metric_specs:
            eligible = group[metric].ge(target) if direction == "at_least" else group[metric].le(target)
            reached = group[eligible]
            tolerance_rows.append(
                {
                    "benchmark_population": population_name,
                    "run_id": run_id,
                    "method": method,
                    "formulation": formulation,
                    "metric": metric,
                    "target": target,
                    "direction": direction,
                    "queries_required": int(reached["budget"].iloc[0]) if len(reached) else math.nan,
                    "status": "reached" if len(reached) else "not reached",
                    "no_extrapolation": True,
                }
            )
    query_summary = (
        queries.groupby(["benchmark_population", "run_id", "method", "formulation"], as_index=False)
        .agg(
            mean_query_boundary_distance=("empirical_boundary_distance_evaluation_only", "mean"),
            median_query_boundary_distance=("empirical_boundary_distance_evaluation_only", "median"),
            minimum_query_boundary_distance=("empirical_boundary_distance_evaluation_only", "min"),
            query_count=("query_order", "count"),
        )
    )
    return {
        "aulc": pd.DataFrame(aulc_rows),
        "final": pd.DataFrame(final_rows),
        "tolerance": pd.DataFrame(tolerance_rows),
        "query_summary": query_summary,
    }


def paired_comparisons(aulc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = aulc[aulc["benchmark_population"].eq("primary_common")].copy()
    q20_col = "common_normalized_aulc__q20_error"
    max_methods = primary[primary["formulation"].eq("max_depth")].groupby("method")[q20_col].mean()
    binary_methods = primary[primary["formulation"].eq("binary")].groupby("method")[q20_col].mean()
    active_max = max_methods.drop(labels=[name for name in max_methods.index if name.endswith("_random")], errors="ignore")
    active_binary = binary_methods.drop(labels=[name for name in binary_methods.index if name.endswith("_random")], errors="ignore")
    best_max = str(active_max.idxmin())
    best_binary = str(active_binary.idxmin())
    pairs: list[tuple[str, str, str]] = [
        ("best_vs_best_descriptive", best_max, best_binary),
        ("predeclared_straddle_vs_margin", "max_depth_straddle", "binary_margin"),
        (
            "predeclared_randomized_vs_repulsion",
            "max_depth_randomized_straddle",
            "binary_uncertainty_repulsion",
        ),
    ]
    for method in sorted(primary["method"].unique()):
        if method.endswith("_random"):
            continue
        baseline = "max_depth_random" if method.startswith("max_depth") else "binary_random"
        pairs.append((f"active_vs_shared_random__{method}", method, baseline))

    metrics = [
        "common_normalized_aulc__q20_error",
        "common_normalized_aulc__q30_error",
        "common_normalized_aulc__balanced_accuracy",
    ]
    comparison_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    for comparison, method_a, method_b in pairs:
        a = primary[primary["method"].eq(method_a)].set_index("run_id")
        b = primary[primary["method"].eq(method_b)].set_index("run_id")
        common_runs = sorted(set(a.index) & set(b.index))
        if not common_runs:
            continue
        for metric in metrics:
            differences = a.loc[common_runs, metric].to_numpy(float) - b.loc[common_runs, metric].to_numpy(float)
            repeat_labels = np.array([int(run.split("__r")[1].split("_")[0]) for run in common_runs])
            repeat_means = {
                int(repeat): float(np.mean(differences[repeat_labels == repeat]))
                for repeat in np.unique(repeat_labels)
            }
            row = {
                "comparison": comparison,
                "method_a": method_a,
                "method_b": method_b,
                "metric": metric,
                "paired_run_count": len(differences),
                "mean_paired_difference_a_minus_b": float(np.mean(differences)),
                "median_paired_difference_a_minus_b": float(np.median(differences)),
                "repeat_block_mean_differences_json": json.dumps(repeat_means, sort_keys=True),
                "uncertainty_interpretation": "descriptive_repeated_CV_runs_not_independent",
                "selection_status": (
                    "post_selection_descriptive" if comparison == "best_vs_best_descriptive" else "predeclared_or_baseline"
                ),
            }
            comparison_rows.append(row)
            rng = stable_rng(BASE_SEED, comparison, metric, "paired_bootstrap")
            samples = np.empty(PAIRED_BOOTSTRAP_RESAMPLES, dtype=float)
            for bidx in range(PAIRED_BOOTSTRAP_RESAMPLES):
                sample = rng.integers(0, len(differences), len(differences))
                samples[bidx] = float(np.mean(differences[sample]))
            low, median, high = np.quantile(samples, [0.025, 0.5, 0.975])
            bootstrap_rows.append(
                {
                    **row,
                    "bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
                    "bootstrap_ci_low": float(low),
                    "bootstrap_median": float(median),
                    "bootstrap_ci_high": float(high),
                    "formal_hypothesis_test": False,
                }
            )
    return pd.DataFrame(comparison_rows), pd.DataFrame(bootstrap_rows)


def subgroup_results(
    predictions: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    final_budget = int(predictions["budget"].max())
    final = predictions[
        predictions["benchmark_population"].eq("primary_common") & predictions["budget"].eq(final_budget)
    ].merge(
        population[
            [
                "experiment_name",
                "keyhole_transient_by_sequence",
                "keyhole_persistent_to_last_physical_frame",
                "repeated_keyhole_episodes",
                "keyhole_timing_relative_to_T0",
                "keyhole_frames_before_T0",
                "keyhole_frames_inside_T0",
                "keyhole_frames_after_T0",
            ]
        ],
        on="experiment_name",
        how="left",
        validate="many_to_one",
    )
    transient_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    subgroup_masks = {
        "transient_Keyhole": final["keyhole_transient_by_sequence"].fillna(False).astype(bool),
        "persistent_Keyhole": final["keyhole_persistent_to_last_physical_frame"].fillna(False).astype(bool),
        "repeated_Keyhole": final["repeated_keyhole_episodes"].fillna(False).astype(bool),
    }
    for (run_id, method, formulation), group in final.groupby(["run_id", "method", "formulation"], sort=True):
        for name, global_mask in subgroup_masks.items():
            mask = global_mask.loc[group.index].to_numpy(bool) & group["has_keyhole"].to_numpy(bool)
            transient_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "formulation": formulation,
                    "budget": final_budget,
                    "subgroup": name,
                    "held_out_positive_count": int(mask.sum()),
                    "sensitivity": float(group.loc[mask, "predicted_keyhole"].mean()) if mask.any() else math.nan,
                    "minimum_n3_for_interpretation": int(mask.sum()) >= 3,
                }
            )
        positive = group[group["has_keyhole"].astype(bool)]
        for timing, part in positive.groupby("keyhole_timing_relative_to_T0", dropna=False):
            timing_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "formulation": formulation,
                    "budget": final_budget,
                    "timing_group": str(timing),
                    "held_out_positive_count": len(part),
                    "sensitivity": float(part["predicted_keyhole"].mean()) if len(part) else math.nan,
                    "minimum_n3_for_interpretation": len(part) >= 3,
                }
            )
    return pd.DataFrame(transient_rows), pd.DataFrame(timing_rows)


def domain_transfer_models(
    population: pd.DataFrame,
    boundary: pd.DataFrame,
) -> pd.DataFrame:
    routes = [
        ("all_old_to_new", ["old-data-local", "old-data-remote-clean"], ["new-data"], "secondary_robustness"),
        ("new_to_all_old", ["new-data"], ["old-data-local", "old-data-remote-clean"], "secondary_robustness"),
        ("old_local_to_new", ["old-data-local"], ["new-data"], "secondary_descriptive"),
        ("old_remote_to_new", ["old-data-remote-clean"], ["new-data"], "secondary_descriptive_tiny_positive_count"),
    ]
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    depth = population["value__max_depth"].to_numpy(float)
    rows: list[dict[str, Any]] = []
    for route, source_parts, target_parts, status in routes:
        train = np.flatnonzero(population["partition"].isin(source_parts).to_numpy())
        test = np.flatnonzero(population["partition"].isin(target_parts).to_numpy())
        scaler = StandardScaler().fit(x[train])
        threshold = choose_higher_threshold(depth[train], labels[train])
        target_oracle = choose_higher_threshold(depth[test], labels[test])
        target_boundary = assign_test_boundary_subsets(test, boundary)
        flags = {q: target_boundary[f"test_q{q}"].to_numpy(bool) for q in BOUNDARY_QUANTILES}

        gpr = fit_gpr(
            x[train], depth[train], scaler=scaler, seed=stable_seed(BASE_SEED, route, "gpr"),
            kernel_kind="matern32", restarts=STATIC_OPTIMIZER_RESTARTS,
        )
        mu, sigma = predict_gpr(gpr, x[test])
        probability = continuous_probability(mu, sigma, threshold["threshold"])
        metrics = classification_metrics(
            labels[test], probability, (mu > threshold["threshold"]).astype(int), boundary_flags=flags
        )
        rows.append(
            {
                "route": route,
                "route_status": status,
                "formulation": "max_depth",
                "source_partitions": ";".join(source_parts),
                "target_partitions": ";".join(target_parts),
                "source_count": len(train),
                "source_keyhole_count": int(labels[train].sum()),
                "target_count": len(test),
                "target_keyhole_count": int(labels[test].sum()),
                "source_training_threshold_um": float(threshold["threshold"]),
                "target_descriptive_oracle_threshold_um": float(target_oracle["threshold"]),
                "threshold_shift_source_minus_target_oracle_um": float(
                    threshold["threshold"] - target_oracle["threshold"]
                ),
                "target_oracle_unavailable_to_valid_method": True,
                **metrics,
                **regression_metrics(depth[test], mu),
                "fit_status": gpr.fit_status,
                "kernel": gpr.kernel,
            }
        )

        gpc = fit_gpc(
            x[train], labels[train], scaler=scaler, seed=stable_seed(BASE_SEED, route, "gpc"),
            kernel_kind="matern32", restarts=STATIC_OPTIMIZER_RESTARTS,
        )
        probability = predict_gpc(gpc, x[test])
        metrics = classification_metrics(
            labels[test], probability, (probability >= 0.5).astype(int), boundary_flags=flags
        )
        rows.append(
            {
                "route": route,
                "route_status": status,
                "formulation": "binary",
                "source_partitions": ";".join(source_parts),
                "target_partitions": ";".join(target_parts),
                "source_count": len(train),
                "source_keyhole_count": int(labels[train].sum()),
                "target_count": len(test),
                "target_keyhole_count": int(labels[test].sum()),
                "source_training_threshold_um": math.nan,
                "target_descriptive_oracle_threshold_um": math.nan,
                "threshold_shift_source_minus_target_oracle_um": math.nan,
                "target_oracle_unavailable_to_valid_method": True,
                **metrics,
                "mae": math.nan,
                "rmse": math.nan,
                "relative_mae": math.nan,
                "relative_rmse": math.nan,
                "r2": math.nan,
                "fit_status": gpc.fit_status,
                "kernel": gpc.kernel,
            }
        )
    return pd.DataFrame(rows)


def verify_original_dirty_checkout() -> dict[str, Any]:
    original = Path(r"C:\Users\ozgur\Documents\thesis")
    protected = {
        "docs/deep-research-report.md": "a714e0c2249a134287b76a86fc8d660a075c69184a5cab851a3c1f52412e321c",
        "outputs/week1_active_level_set_progress.pptx": "bdd1f515eaab313e5371cbe5e2c0b7fb3e87713037a21337dd7d078406c23577",
        "outputs/week2_acquisition_comparison/week2_slide_notes.md": "9f00ece946170f936e5efffa019cdb4c3b2dbcc93037155cdfccfca716e2e99c",
        "outputs/week2_active_level_set_progress_v2.pptx": "92a760d21a1c9b9e07f15724d2cedd225a19b05439af8eca6273ac4212b913ab",
        "outputs/week3_active_level_set_progress.pptx": "f129a4f5310b808d23f810b1e4cbfb8be2039a5ddfe408d9b26de55e7c9cfcbd",
        "outputs/week3_active_level_set_progress_v2.pptx": "aec8efe32b358d2f6bbd3c3610fc9d76ff8b45d74cddbdd0074c261e127ae09e",
    }
    rows = []
    for relative, expected in protected.items():
        path = original / relative
        actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append(
            {
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "matches": actual.lower() == expected.lower(),
            }
        )
    status = git_output("status", "--short", "--untracked-files=all", cwd=original).splitlines()
    return {
        "path": str(original),
        "branch": git_output("branch", "--show-current", cwd=original),
        "head": git_output("rev-parse", "HEAD", cwd=original),
        "git_status_short": status,
        "protected_files": rows,
        "all_protected_hashes_match": all(row["matches"] for row in rows),
    }


def prepare_phase6(output_dir: Path, *, smoke: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    live_revision = resolve_live_hf_revision()
    hf_audit = {
        "repository": SPH_V2_REPO_ID,
        "expected_revision": EXPECTED_HF_REVISION,
        "live_main_revision": live_revision,
        "matches_expected": live_revision == EXPECTED_HF_REVISION,
        "checked_at_utc": utc_now(),
        "unexpected_drift_action": "STOP before science",
    }
    write_json(output_dir / "hf_revision_audit.json", hf_audit)
    require(live_revision == EXPECTED_HF_REVISION, "Unexpected Hugging Face revision drift")

    phase6_head = git_output("rev-parse", "HEAD")
    phase6_branch = git_output("branch", "--show-current")
    phase55_remote_line = git_output("ls-remote", "--heads", "origin", PHASE55_BRANCH)
    phase55_remote = phase55_remote_line.split()[0] if phase55_remote_line else ""
    original = verify_original_dirty_checkout()
    require(phase6_head == EXPECTED_PHASE55_PARENT, f"Phase 6 HEAD drift: {phase6_head}")
    require(phase6_branch == PHASE6_BRANCH, f"Wrong Phase 6 branch: {phase6_branch}")
    require(phase55_remote == EXPECTED_PHASE55_PARENT, "Published Phase 5.5 remote mismatch")
    require(original["all_protected_hashes_match"], "Original dirty checkout fingerprint changed")

    full, primary, secondary = load_population_tables()
    saved_labels = download_current_label_ledgers(live_revision)
    event, review, semantic = build_max_depth_event_audit(primary, saved_labels)
    boundary, boundary_summary, boundary_validation = build_empirical_boundary_reference(primary)
    boundary.insert(0, "benchmark_population", "primary_common")
    secondary_boundary = secondary[["experiment_name"]].merge(
        boundary.drop(columns=["benchmark_population", "partition", "has_keyhole", *FEATURE_COLUMNS]),
        on="experiment_name",
        how="left",
        validate="one_to_one",
    )
    secondary_boundary.insert(0, "benchmark_population", "secondary_g3_common")
    secondary_boundary.insert(2, "partition", secondary["partition"].to_numpy())
    secondary_boundary.insert(3, "has_keyhole", secondary["has_keyhole"].to_numpy())
    for column in reversed(FEATURE_COLUMNS):
        secondary_boundary.insert(4, column, secondary[column].to_numpy())

    primary_specs, primary_manifest, primary_balance = build_outer_splits(primary, "primary_common")
    secondary_specs, secondary_manifest, secondary_balance = build_outer_splits(
        secondary, "secondary_g3_common"
    )
    if smoke:
        primary_run_ids = {spec.run_id for spec in primary_specs[:2]}
        secondary_run_ids = {spec.run_id for spec in secondary_specs[:1]}
        split_manifest = pd.concat(
            [
                primary_manifest[primary_manifest["run_id"].isin(primary_run_ids)],
                secondary_manifest[secondary_manifest["run_id"].isin(secondary_run_ids)],
            ],
            ignore_index=True,
        )
        split_balance = pd.concat(
            [
                primary_balance[primary_balance["run_id"].isin(primary_run_ids)],
                secondary_balance[secondary_balance["run_id"].isin(secondary_run_ids)],
            ],
            ignore_index=True,
        )
    else:
        split_manifest = pd.concat([primary_manifest, secondary_manifest], ignore_index=True)
        split_balance = pd.concat([primary_balance, secondary_balance], ignore_index=True)

    population_columns = [
        "experiment_name", "partition", "P", "VX", "LS", "ST", "has_keyhole",
        "physical_target_extraction_success", "ready__max_depth", "value__max_depth",
        "ready__G3", "value__G3", "primary_ready", "secondary_g3_ready",
        "primary_exclusion_reasons", "g3_exclusion_reasons", "input_tuple_sha256", "input_group_size",
        "source_label_modified", "simulation_silently_removed", "depth_formula", "T0_definition",
        "active_region_definition", "exact_sph_v2_revision",
    ]
    write_csv(output_dir / "population_audit.csv", full[[column for column in population_columns if column in full]])
    write_csv(output_dir / "primary_common_population.csv", primary)
    write_csv(output_dir / "secondary_g3_common_population.csv", secondary)
    write_csv(output_dir / "max_depth_event_audit.csv", event)
    write_csv(output_dir / "max_depth_raw_review_cases.csv", review)
    write_csv(output_dir / "max_depth_semantic_summary.csv", semantic)
    write_csv(output_dir / "empirical_boundary_reference.csv", boundary)
    write_csv(output_dir / "empirical_boundary_subset_summary.csv", boundary_summary)
    write_csv(output_dir / "empirical_boundary_validation.csv", boundary_validation)
    write_csv(output_dir / "outer_split_manifest.csv", split_manifest)
    write_csv(output_dir / "outer_split_balance_audit.csv", split_balance)

    target_table = PHASE55_OUTPUT / "current_revision_simulation_level_targets.parquet"
    sequence_table = PHASE55_OUTPUT / "physical_proxy_population_reference.csv"
    input_paths = [
        target_table,
        sequence_table,
        PHASE1_OUTPUT / "keyhole_episodes.csv",
        PHASE4_OUTPUT / "depth_consensus_hard_cases.csv",
        PHASE55_OUTPUT / "hf_change_audit.json",
    ]
    provenance = {
        "phase": "Week 7 Phase 6",
        "created_at_utc": utc_now(),
        "phase55_parent_commit": phase6_head,
        "phase55_branch": PHASE55_BRANCH,
        "phase55_remote_commit": phase55_remote,
        "phase6_branch": phase6_branch,
        "dataset_repository": SPH_V2_REPO_ID,
        "dataset_revision": live_revision,
        "canonical_target_table": str(target_table.relative_to(ROOT)),
        "canonical_target_table_shape": [407, 160],
        "label_semantics": "has_keyhole means at least one valid saved physical frame was manually labelled Keyhole",
        "maximum_depth_definition": sorted(primary["depth_formula"].dropna().astype(str).unique()),
        "T0_definition": sorted(primary["T0_definition"].dropna().astype(str).unique()),
        "active_region_definition": sorted(primary["active_region_definition"].dropna().astype(str).unique()),
        "primary_population_count": len(primary),
        "primary_keyhole_count": int(primary["has_keyhole"].sum()),
        "secondary_g3_population_count": len(secondary),
        "inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in input_paths
            if path.is_file()
        ],
        "original_dirty_checkout": original,
    }
    write_json(output_dir / "input_provenance.json", provenance)
    preflight = {
        "phase": "Week 7 Phase 6",
        "status": "PASS",
        "phase6_branch": phase6_branch,
        "phase6_head_exact_phase55_commit": phase6_head,
        "expected_phase55_commit": EXPECTED_PHASE55_PARENT,
        "phase55_remote_matches": phase55_remote == phase6_head,
        "hf_revision_matches": live_revision == EXPECTED_HF_REVISION,
        "primary_population_count": len(primary),
        "primary_keyhole_count": int(primary["has_keyhole"].sum()),
        "primary_non_keyhole_count": int((~primary["has_keyhole"]).sum()),
        "g3_common_count": len(secondary),
        "duplicate_input_group_count": int(primary["input_group_size"].gt(1).groupby(primary["input_tuple_sha256"]).any().sum()),
        "primary_outer_run_count": 2 if smoke else len(primary_specs),
        "secondary_outer_run_count": 1 if smoke else len(secondary_specs),
        "planned_full_primary_outer_run_count": len(primary_specs),
        "planned_full_secondary_outer_run_count": len(secondary_specs),
        "smoke_mode": smoke,
        "original_dirty_checkout_protected": original["all_protected_hashes_match"],
        "hard_stop_after_phase6": True,
    }
    write_json(output_dir / "phase6_preflight.json", preflight)
    return {
        "full": full,
        "primary": primary,
        "secondary": secondary,
        "boundary": boundary,
        "secondary_boundary": secondary_boundary,
        "primary_specs": primary_specs,
        "secondary_specs": secondary_specs,
        "event": event,
        "semantic": semantic,
        "provenance": provenance,
    }


def run_static_stage(
    prepared: Mapping[str, Any],
    output_dir: Path,
    *,
    workers: int,
    smoke: bool,
) -> pd.DataFrame:
    primary_specs: list[RunSpec] = list(prepared["primary_specs"])
    secondary_specs: list[RunSpec] = list(prepared["secondary_specs"])
    if smoke:
        primary_specs = primary_specs[:2]
        secondary_specs = secondary_specs[:1]
    primary_frames = Parallel(n_jobs=workers, backend="loky")(
        delayed(run_static_fold)(spec, prepared["primary"], prepared["boundary"])
        for spec in primary_specs
    )
    secondary_frames = Parallel(n_jobs=workers, backend="loky")(
        delayed(run_secondary_static_fold)(spec, prepared["secondary"], prepared["secondary_boundary"])
        for spec in secondary_specs
    )
    predictions = pd.concat([*primary_frames, *secondary_frames], ignore_index=True)
    summary, boundary_summary, calibration = summarize_static_predictions(predictions)
    write_csv(output_dir / "static_model_fold_predictions.csv", predictions)
    write_csv(output_dir / "static_model_summary.csv", summary)
    write_csv(output_dir / "static_boundary_metric_summary.csv", boundary_summary)
    write_csv(output_dir / "static_probability_calibration.csv", calibration)
    return predictions


def run_active_stage(
    prepared: Mapping[str, Any],
    output_dir: Path,
    *,
    workers: int,
    smoke: bool,
    force: bool,
) -> dict[str, pd.DataFrame]:
    if smoke:
        primary_specs = list(prepared["primary_specs"])[:2]
        secondary_specs = list(prepared["secondary_specs"])[:1]
        primary_methods = (
            "max_depth_random", "max_depth_straddle", "binary_random", "binary_margin"
        )
        secondary_methods = (
            "g3_random", "g3_straddle", "max_depth_g3_common_straddle", "binary_g3_common_margin"
        )
        final_budget = 30
        threshold_resamples = 100
        checkpoint_root = output_dir / "checkpoints"
    else:
        primary_specs = list(prepared["primary_specs"])
        secondary_specs = list(prepared["secondary_specs"])
        primary_methods = PRIMARY_METHODS
        secondary_methods = SECONDARY_G3_METHODS
        final_budget = FINAL_BUDGET
        threshold_resamples = THRESHOLD_BOOTSTRAP_RESAMPLES
        checkpoint_root = CHECKPOINT_DIR

    primary_nested = Parallel(n_jobs=workers, backend="loky")(
        delayed(run_outer_active)(
            spec,
            prepared["primary"],
            prepared["boundary"],
            primary_methods,
            final_budget=final_budget,
            checkpoint_root=checkpoint_root,
            threshold_bootstrap_resamples=threshold_resamples,
            force=force,
        )
        for spec in primary_specs
    )
    secondary_nested = Parallel(n_jobs=workers, backend="loky")(
        delayed(run_outer_active)(
            spec,
            prepared["secondary"],
            prepared["secondary_boundary"],
            secondary_methods,
            final_budget=final_budget,
            checkpoint_root=checkpoint_root,
            threshold_bootstrap_resamples=threshold_resamples,
            force=force,
        )
        for spec in secondary_specs
    )
    results = [item for nested in [*primary_nested, *secondary_nested] for item in nested]
    frames = {
        key: concat_result_frames(results, key)
        for key in [
            "manifest", "initialization", "queries", "curves", "predictions", "thresholds",
            "threshold_bootstrap", "fairness",
        ]
    }
    initialization = frames["initialization"].drop_duplicates(
        ["benchmark_population", "run_id", "warm_start_sha256"]
    ).reset_index(drop=True)
    write_csv(output_dir / "active_run_manifest.csv", frames["manifest"])
    write_csv(output_dir / "active_initialization_audit.csv", initialization)
    write_csv(output_dir / "active_query_history.csv", frames["queries"])
    write_csv(output_dir / "active_prediction_history.csv", frames["predictions"])
    write_csv(output_dir / "online_threshold_history.csv", frames["thresholds"])
    write_csv(output_dir / "online_threshold_bootstrap_summary.csv", frames["threshold_bootstrap"])
    write_csv(output_dir / "fairness_audit.csv", frames["fairness"])
    write_csv(output_dir / "active_learning_curve_summary.csv", frames["curves"])

    summaries = summarize_active(
        frames["curves"], frames["predictions"], initialization, frames["queries"]
    )
    write_csv(output_dir / "active_learning_final_budget_summary.csv", summaries["final"])
    write_csv(output_dir / "active_learning_aulc_summary.csv", summaries["aulc"])
    write_csv(output_dir / "queries_to_tolerance.csv", summaries["tolerance"])
    write_csv(output_dir / "query_boundary_distance_summary.csv", summaries["query_summary"])
    if not smoke:
        comparisons, bootstrap = paired_comparisons(summaries["aulc"])
    else:
        comparisons, bootstrap = pd.DataFrame(), pd.DataFrame()
    write_csv(output_dir / "active_paired_method_comparisons.csv", comparisons)
    write_csv(output_dir / "active_paired_bootstrap_intervals.csv", bootstrap)
    transient, timing = subgroup_results(frames["predictions"], prepared["primary"])
    write_csv(output_dir / "subgroup_transient_persistent_results.csv", transient)
    write_csv(output_dir / "subgroup_t0_timing_results.csv", timing)

    g3_aulc = summaries["aulc"][
        summaries["aulc"]["benchmark_population"].eq("secondary_g3_common")
        & summaries["aulc"]["formulation"].eq("g3")
    ]
    g3_summary = (
        g3_aulc.groupby(["method", "formulation"], as_index=False)
        .agg(
            mean_q20_aulc=("common_normalized_aulc__q20_error", "mean"),
            mean_q30_aulc=("common_normalized_aulc__q30_error", "mean"),
            mean_balanced_accuracy_aulc=("common_normalized_aulc__balanced_accuracy", "mean"),
            run_count=("run_id", "nunique"),
        )
    )
    write_csv(output_dir / "g3_secondary_active_summary.csv", g3_summary)
    common_methods = summaries["aulc"][summaries["aulc"]["benchmark_population"].eq("secondary_g3_common")]
    max_vs_g3 = (
        common_methods.groupby(["method", "formulation"], as_index=False)
        .agg(
            mean_q20_aulc=("common_normalized_aulc__q20_error", "mean"),
            mean_q30_aulc=("common_normalized_aulc__q30_error", "mean"),
            mean_balanced_accuracy_aulc=("common_normalized_aulc__balanced_accuracy", "mean"),
            run_count=("run_id", "nunique"),
        )
    )
    max_vs_g3["population"] = "secondary_g3_common_404"
    max_vs_g3["comparison_status"] = "matched_complete_case_secondary"
    write_csv(output_dir / "max_depth_vs_g3_summary.csv", max_vs_g3)
    frames["initialization"] = initialization
    frames.update(summaries)
    frames["comparisons"] = comparisons
    frames["paired_bootstrap"] = bootstrap
    return frames


def threshold_stability_summary(thresholds: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (population_name, run_id, method, formulation), group in thresholds.groupby(
        ["benchmark_population", "run_id", "method", "formulation"], sort=True
    ):
        group = group.sort_values("budget")
        final_threshold = float(group["threshold"].iloc[-1])
        tolerance = max(2.0, 0.05 * abs(final_threshold))
        stable_budget = math.nan
        for _, row in group.iterrows():
            tail = group[group["budget"].ge(row["budget"])]
            if np.all(np.abs(tail["threshold"].to_numpy(float) - final_threshold) <= tolerance):
                stable_budget = int(row["budget"])
                break
        rows.append(
            {
                "benchmark_population": population_name,
                "run_id": run_id,
                "method": method,
                "formulation": formulation,
                "final_threshold": final_threshold,
                "stability_tolerance_um": tolerance,
                "first_budget_stable_to_final": stable_budget,
                "stability_definition": "all later tau within max(2 um, 5% of final tau)",
            }
        )
    return pd.DataFrame(rows)


def metric_mean(frame: pd.DataFrame, method: str, column: str) -> float:
    values = frame.loc[frame["method"].eq(method), column]
    return float(values.mean())


def build_final_decision(
    *,
    aulc: pd.DataFrame,
    paired_bootstrap: pd.DataFrame,
    event: pd.DataFrame,
    domain: pd.DataFrame,
    thresholds: pd.DataFrame,
    max_vs_g3: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    primary = aulc[aulc["benchmark_population"].eq("primary_common")]
    q20 = "common_normalized_aulc__q20_error"
    q30 = "common_normalized_aulc__q30_error"
    ba = "common_normalized_aulc__balanced_accuracy"
    method_means = (
        primary.groupby(["method", "formulation"], as_index=False)[[q20, q30, ba]].mean()
    )
    active_max = method_means[
        method_means["formulation"].eq("max_depth") & ~method_means["method"].str.endswith("_random")
    ].sort_values([q20, q30, "method"], kind="mergesort")
    active_binary = method_means[
        method_means["formulation"].eq("binary") & ~method_means["method"].str.endswith("_random")
    ].sort_values([q20, q30, "method"], kind="mergesort")
    best_max = str(active_max.iloc[0]["method"])
    best_binary = str(active_binary.iloc[0]["method"])
    max_row = active_max.iloc[0]
    binary_row = active_binary.iloc[0]
    differences = {
        "q20_aulc_max_minus_binary": float(max_row[q20] - binary_row[q20]),
        "q30_aulc_max_minus_binary": float(max_row[q30] - binary_row[q30]),
        "balanced_accuracy_aulc_max_minus_binary": float(max_row[ba] - binary_row[ba]),
    }
    selected_boot = paired_bootstrap[
        paired_bootstrap["comparison"].eq("best_vs_best_descriptive")
    ]
    ci = {}
    for metric in [q20, q30, ba]:
        part = selected_boot[selected_boot["metric"].eq(metric)]
        if len(part):
            ci[metric] = (
                float(part["bootstrap_ci_low"].iloc[0]),
                float(part["bootstrap_ci_high"].iloc[0]),
            )
        else:
            ci[metric] = (math.nan, math.nan)

    errors = event[event["descriptive_oracle_error_type"].ne("correct")]
    ambiguity_error_fraction = (
        float(errors["flag_depth_bounding_box_ambiguity_candidate"].mean()) if len(errors) else 0.0
    )
    recording_end_error_fraction = (
        float(errors["near_recording_end_last_5pct"].mean()) if len(errors) else 0.0
    )
    semantic_ok = ambiguity_error_fraction < 0.5 and recording_end_error_fraction < 0.5
    # Every old/new route is secondary robustness evidence, but a criterion
    # named ``domain_transfer_floor`` must use the actual worst saved route.
    # Restricting the scorecard to only the two pooled directions made it
    # disagree with summary.json whenever an old-local or old-remote stress
    # route was lower.
    domain_transfer = domain.copy()
    max_transfer = domain_transfer[domain_transfer["formulation"].eq("max_depth")]
    domain_ok = len(max_transfer) > 0 and float(max_transfer["balanced_accuracy"].min()) >= 0.60

    q20_continuous = differences["q20_aulc_max_minus_binary"] < 0
    q30_continuous = differences["q30_aulc_max_minus_binary"] < 0
    ba_not_worse = differences["balanced_accuracy_aulc_max_minus_binary"] >= -0.02
    continuous_ci = ci[q20][1] < 0 and ci[q30][1] < 0
    q20_binary = differences["q20_aulc_max_minus_binary"] > 0
    q30_binary = differences["q30_aulc_max_minus_binary"] > 0
    binary_ci = ci[q20][0] > 0 and ci[q30][0] > 0

    if q20_continuous and q30_continuous and ba_not_worse and continuous_ci and semantic_ok and domain_ok:
        decision = "CONTINUOUS MAX-DEPTH PRIMARY"
        reason = (
            f"{best_max} beats {best_binary} on both primary q20 and q30 normalized AULC with descriptive paired intervals in the same direction; balanced-accuracy AULC is not materially worse, and semantic/domain audits show no dominant failure mechanism."
        )
    elif (q20_binary and q30_binary and binary_ci) or not semantic_ok:
        decision = "BINARY KEYHOLE PRIMARY"
        reason = (
            f"{best_binary} is more robust on both primary boundary AULCs or the maximum-depth semantic audit shows a dominant artifact mechanism."
        )
    else:
        decision = "HYBRID / NO CLEAR WINNER"
        reason = (
            "The q20/q30 hierarchy, paired descriptive uncertainty, balanced-accuracy support, or semantic/domain evidence does not jointly justify a single formulation."
        )

    stability = threshold_stability_summary(thresholds)
    max_stability = stability[
        stability["benchmark_population"].eq("primary_common")
        & stability["method"].eq(best_max)
    ]
    median_stable_budget = float(max_stability["first_budget_stable_to_final"].median())
    scorecard_rows = [
        {
            "criterion": "primary_q20_aulc",
            "max_depth_value": float(max_row[q20]),
            "binary_value": float(binary_row[q20]),
            "favours": "max_depth" if q20_continuous else "binary",
            "status": "primary",
        },
        {
            "criterion": "primary_q30_aulc",
            "max_depth_value": float(max_row[q30]),
            "binary_value": float(binary_row[q30]),
            "favours": "max_depth" if q30_continuous else "binary",
            "status": "primary",
        },
        {
            "criterion": "balanced_accuracy_aulc",
            "max_depth_value": float(max_row[ba]),
            "binary_value": float(binary_row[ba]),
            "favours": "max_depth" if differences["balanced_accuracy_aulc_max_minus_binary"] > 0 else "binary",
            "status": "primary_supporting",
        },
        {
            "criterion": "semantic_artifact_audit",
            "max_depth_value": ambiguity_error_fraction,
            "binary_value": math.nan,
            "favours": "max_depth_defensible" if semantic_ok else "binary",
            "status": "supporting_not_relabelling",
        },
        {
            "criterion": "domain_transfer_floor",
            "max_depth_value": float(max_transfer["balanced_accuracy"].min()) if len(max_transfer) else math.nan,
            "binary_value": float(
                domain_transfer[domain_transfer["formulation"].eq("binary")]["balanced_accuracy"].min()
            ),
            "favours": "no_catastrophic_max_depth_failure" if domain_ok else "binary",
            "status": "secondary_robustness",
        },
        {
            "criterion": "online_threshold_stability_budget",
            "max_depth_value": median_stable_budget,
            "binary_value": math.nan,
            "favours": "diagnostic",
            "status": "queried_set_stability_not_population_CI",
        },
    ]
    decision_frame = pd.DataFrame(
        [
            {
                "final_decision": decision,
                "justification": reason,
                "best_max_depth_acquisition": best_max,
                "best_binary_acquisition": best_binary,
                **differences,
                "q20_paired_ci_low": ci[q20][0],
                "q20_paired_ci_high": ci[q20][1],
                "q30_paired_ci_low": ci[q30][0],
                "q30_paired_ci_high": ci[q30][1],
                "semantic_audit_pass": semantic_ok,
                "domain_robustness_pass": domain_ok,
                "manual_annotation_remains_reference": True,
                "threshold_is_universal_physical_constant": False,
                "causal_claim": False,
            }
        ]
    )
    details = {
        "decision": decision,
        "reason": reason,
        "best_max_depth_method": best_max,
        "best_binary_method": best_binary,
        "differences": differences,
        "paired_intervals": ci,
        "semantic_ok": semantic_ok,
        "domain_ok": domain_ok,
        "ambiguity_error_fraction": ambiguity_error_fraction,
        "recording_end_error_fraction": recording_end_error_fraction,
        "median_threshold_stability_budget": median_stable_budget,
    }
    return pd.DataFrame(scorecard_rows), decision_frame, details


def _summary_metric(
    static_summary: pd.DataFrame,
    *,
    benchmark_population: str,
    model: str,
    metric: str,
) -> float:
    row = static_summary[
        static_summary["benchmark_population"].eq(benchmark_population)
        & static_summary["model"].eq(model)
        & static_summary["metric"].eq(metric)
    ]
    return float(row["mean"].iloc[0]) if len(row) else math.nan


def write_results_summary(
    output_dir: Path,
    *,
    prepared: Mapping[str, Any],
    static_summary: pd.DataFrame,
    active: Mapping[str, pd.DataFrame],
    domain: pd.DataFrame,
    decision_details: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    primary = prepared["primary"]
    event = prepared["event"]
    best_max = str(decision_details["best_max_depth_method"])
    best_binary = str(decision_details["best_binary_method"])
    aulc = active["aulc"]
    primary_aulc = aulc[aulc["benchmark_population"].eq("primary_common")]
    max_row = primary_aulc[primary_aulc["method"].eq(best_max)]
    binary_row = primary_aulc[primary_aulc["method"].eq(best_binary)]
    final = active["final"]
    tolerance = active["tolerance"]
    max_thresholds = active["thresholds"][
        active["thresholds"]["benchmark_population"].eq("primary_common")
        & active["thresholds"]["method"].eq(best_max)
    ]
    threshold_stability = threshold_stability_summary(max_thresholds)
    transient = pd.read_csv(output_dir / "subgroup_transient_persistent_results.csv")
    transient_primary = transient[
        transient["subgroup"].eq("transient_Keyhole")
        & transient["method"].isin([best_max, best_binary])
    ]
    transient_sensitivity = transient_primary.groupby("method")["sensitivity"].mean().to_dict()
    persistent_primary = transient[
        transient["subgroup"].eq("persistent_Keyhole")
        & transient["method"].isin([best_max, best_binary])
    ]
    persistent_sensitivity = persistent_primary.groupby("method")["sensitivity"].mean().to_dict()
    g3 = pd.read_csv(output_dir / "max_depth_vs_g3_summary.csv")
    disagreement = pd.read_csv(output_dir / "boundary_disagreement_summary.csv")
    raw_review = pd.read_csv(output_dir / "max_depth_raw_review_cases.csv")
    transfer_floor = domain.groupby("formulation")["balanced_accuracy"].min().to_dict()

    paired_bootstrap = active["paired_bootstrap"]

    def paired_result(comparison: str, metric: str) -> dict[str, float]:
        row = paired_bootstrap[
            paired_bootstrap["comparison"].eq(comparison)
            & paired_bootstrap["metric"].eq(metric)
        ]
        if not len(row):
            return {"difference": math.nan, "ci_low": math.nan, "ci_high": math.nan}
        return {
            "difference": float(row["mean_paired_difference_a_minus_b"].iloc[0]),
            "ci_low": float(row["bootstrap_ci_low"].iloc[0]),
            "ci_high": float(row["bootstrap_ci_high"].iloc[0]),
        }

    def tolerance_result(method: str, metric: str, target: float) -> dict[str, float | int]:
        rows = tolerance[
            tolerance["benchmark_population"].eq("primary_common")
            & tolerance["method"].eq(method)
            & tolerance["metric"].eq(metric)
            & np.isclose(tolerance["target"].astype(float), target)
        ]
        reached = rows[rows["status"].eq("reached")]
        return {
            "reached_runs": int(len(reached)),
            "total_runs": int(len(rows)),
            "median_queries_among_reached": (
                float(reached["queries_required"].median()) if len(reached) else math.nan
            ),
        }

    max_final_thresholds = threshold_stability["final_threshold"].astype(float)
    best_best_q20 = paired_result("best_vs_best_descriptive", "common_normalized_aulc__q20_error")
    best_best_q30 = paired_result("best_vs_best_descriptive", "common_normalized_aulc__q30_error")
    best_best_ba = paired_result(
        "best_vs_best_descriptive", "common_normalized_aulc__balanced_accuracy"
    )
    max_vs_random = paired_result(
        f"active_vs_shared_random__{best_max}", "common_normalized_aulc__q20_error"
    )
    binary_vs_random = paired_result(
        f"active_vs_shared_random__{best_binary}", "common_normalized_aulc__q20_error"
    )

    summary = {
        "phase": "Week 7 Phase 6",
        "final_decision": decision_details["decision"],
        "decision_reason": decision_details["reason"],
        "primary_population_count": len(primary),
        "primary_keyhole_count": int(primary["has_keyhole"].sum()),
        "primary_non_keyhole_count": int((~primary["has_keyhole"]).sum()),
        "g3_common_population_count": len(prepared["secondary"]),
        "max_depth_semantics": {
            "exact_saved_frame_join_count": int(event["max_depth_exact_saved_frame_join"].sum()),
            "exact_saved_Keyhole_frame_count": int(event["max_depth_exact_saved_Keyhole_frame"].sum()),
            "positive_inside_episode_span_count": int(
                (
                    event["has_keyhole"]
                    & event["saved_keyhole_episode_span_relation"].eq("inside_saved_Keyhole_episode_span")
                ).sum()
            ),
            "positive_after_last_saved_keyhole_frame_count": int(
                (
                    event["has_keyhole"]
                    & event["saved_keyhole_episode_span_relation"].eq(
                        "after_last_saved_Keyhole_frame"
                    )
                ).sum()
            ),
            "positive_between_episode_spans_count": int(
                (
                    event["has_keyhole"]
                    & event["saved_keyhole_episode_span_relation"].eq(
                        "between_saved_Keyhole_episode_spans"
                    )
                ).sum()
            ),
            "raw_review_case_count": int(len(raw_review)),
            "raw_review_single_point_spike_candidate_count": int(
                raw_review["single_point_spike_candidate"].astype(bool).sum()
            ),
            "episode_span_is_not_exact_morphology": True,
            "ambiguity_error_fraction": decision_details["ambiguity_error_fraction"],
        },
        "static": {
            "max_depth_gpr_rmse_um": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="rmse"
            ),
            "max_depth_gpr_balanced_accuracy": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="balanced_accuracy"
            ),
            "binary_gpc_balanced_accuracy": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpc", metric="balanced_accuracy"
            ),
            "max_depth_gpr_sensitivity": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="sensitivity"
            ),
            "binary_gpc_sensitivity": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpc", metric="sensitivity"
            ),
            "max_depth_gpr_global_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="global_error"
            ),
            "binary_gpc_global_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpc", metric="global_error"
            ),
            "max_depth_gpr_q20_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="q20_error"
            ),
            "binary_gpc_q20_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpc", metric="q20_error"
            ),
            "max_depth_gpr_q30_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="q30_error"
            ),
            "binary_gpc_q30_error": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpc", metric="q30_error"
            ),
            "max_depth_gpr_r2": _summary_metric(
                static_summary, benchmark_population="primary_common", model="matern32_gpr", metric="r2"
            ),
        },
        "active": {
            "best_max_depth_method": best_max,
            "best_binary_method": best_binary,
            "best_max_depth_mean_q20_aulc": float(max_row["common_normalized_aulc__q20_error"].mean()),
            "best_binary_mean_q20_aulc": float(binary_row["common_normalized_aulc__q20_error"].mean()),
            "best_max_depth_mean_q30_aulc": float(max_row["common_normalized_aulc__q30_error"].mean()),
            "best_binary_mean_q30_aulc": float(binary_row["common_normalized_aulc__q30_error"].mean()),
            "best_max_depth_mean_balanced_accuracy_aulc": float(
                max_row["common_normalized_aulc__balanced_accuracy"].mean()
            ),
            "best_binary_mean_balanced_accuracy_aulc": float(
                binary_row["common_normalized_aulc__balanced_accuracy"].mean()
            ),
            "median_max_depth_threshold_stability_budget": float(
                threshold_stability["first_budget_stable_to_final"].median()
            ),
            "max_depth_final_threshold_mean_um": float(max_final_thresholds.mean()),
            "max_depth_final_threshold_std_um": float(max_final_thresholds.std(ddof=1)),
            "max_depth_final_threshold_min_um": float(max_final_thresholds.min()),
            "max_depth_final_threshold_max_um": float(max_final_thresholds.max()),
            "transient_sensitivity_by_method": transient_sensitivity,
            "persistent_sensitivity_by_method": persistent_sensitivity,
            "best_vs_best_q20_paired": best_best_q20,
            "best_vs_best_q30_paired": best_best_q30,
            "best_vs_best_balanced_accuracy_paired": best_best_ba,
            "max_depth_vs_random_q20_paired": max_vs_random,
            "binary_vs_random_q20_paired": binary_vs_random,
            "queries_to_balanced_accuracy_0_90": {
                best_max: tolerance_result(best_max, "balanced_accuracy", 0.90),
                best_binary: tolerance_result(best_binary, "balanced_accuracy", 0.90),
            },
            "queries_to_q20_error_0_20": {
                best_max: tolerance_result(best_max, "q20_error", 0.20),
                best_binary: tolerance_result(best_binary, "q20_error", 0.20),
            },
        },
        "g3_secondary_q20_aulc_by_method": {
            str(row.method): float(row.mean_q20_aulc)
            for row in g3.itertuples(index=False)
        },
        "supported_slice_disagreement_fraction_range": [
            float(disagreement["supported_disagreement_fraction"].min()),
            float(disagreement["supported_disagreement_fraction"].max()),
        ],
        "domain_transfer_balanced_accuracy_floor": transfer_floor,
        "runtime": dict(runtime),
        "scope": {
            "manual_labels_changed": False,
            "maximum_depth_redefined": False,
            "G3_redefined": False,
            "phase6_committed": False,
            "phase6_pushed": False,
            "phase7_started": False,
        },
    }
    write_json(output_dir / "summary.json", summary)

    def fmt(value: Any, digits: int = 3) -> str:
        try:
            number = float(value)
            return "NA" if not math.isfinite(number) else f"{number:.{digits}f}"
        except (TypeError, ValueError):
            return str(value)

    static = summary["static"]
    active_summary = summary["active"]
    max_ba_tolerance = active_summary["queries_to_balanced_accuracy_0_90"][best_max]
    binary_ba_tolerance = active_summary["queries_to_balanced_accuracy_0_90"][best_binary]
    max_q20_tolerance = active_summary["queries_to_q20_error_0_20"][best_max]
    binary_q20_tolerance = active_summary["queries_to_q20_error_0_20"][best_binary]
    all_old_to_new = domain[domain["route"].eq("all_old_to_new")].set_index("formulation")
    new_to_all_old = domain[domain["route"].eq("new_to_all_old")].set_index("formulation")
    g3_q20 = summary["g3_secondary_q20_aulc_by_method"]
    disagreement_low, disagreement_high = summary[
        "supported_slice_disagreement_fraction_range"
    ]
    lines = [
        "# Week 7 Phase 6 — Real-data boundary and active level-set results",
        "",
        "This report uses Ioan's manual experiment-level Keyhole label as the reference. Maximum depth is an unchanged physical response, not a replacement label, and its learned threshold is not a universal physical constant.",
        "",
        f"1. **Primary population:** {len(primary)} simulations.",
        f"2. **Class composition:** {summary['primary_keyhole_count']} Keyhole and {summary['primary_non_keyhole_count']} non-Keyhole.",
        f"3. **Semantic consistency:** broadly yes for an experiment-level ‘Keyhole at least once’ reference: {summary['max_depth_semantics']['positive_inside_episode_span_count']}/73 positives place max depth inside a saved-Keyhole episode span, but this is an interval proxy rather than an exact morphology join.",
        f"4. **Timing/artifact caution:** only {summary['max_depth_semantics']['exact_saved_frame_join_count']}/405 maxima coincide with a saved labelled frame; 12 positives peak after their last saved Keyhole frame and one between spans. The deterministic raw review found {summary['max_depth_semantics']['raw_review_single_point_spike_candidate_count']}/{summary['max_depth_semantics']['raw_review_case_count']} isolated-spike candidates, so no dominant obvious spike mechanism was found, but sparse timing alignment remains important.",
        f"5. **Max-depth predictability:** held-out Matérn-3/2 GPR RMSE = {fmt(static['max_depth_gpr_rmse_um'])} µm and R² = {fmt(static['max_depth_gpr_r2'])}.",
        f"6. **Binary predictability:** held-out Matérn-3/2 GPC balanced accuracy = {fmt(static['binary_gpc_balanced_accuracy'])}, with q20/q30 errors {fmt(static['binary_gpc_q20_error'])}/{fmt(static['binary_gpc_q30_error'])}.",
        f"7. **Static global comparison:** mixed. Max-Depth has higher balanced accuracy and sensitivity ({fmt(static['max_depth_gpr_balanced_accuracy'])}/{fmt(static['max_depth_gpr_sensitivity'])} versus {fmt(static['binary_gpc_balanced_accuracy'])}/{fmt(static['binary_gpc_sensitivity'])}), while Binary has lower global error ({fmt(static['binary_gpc_global_error'])} versus {fmt(static['max_depth_gpr_global_error'])}).",
        f"8. **Static q20:** Binary is better: error {fmt(static['binary_gpc_q20_error'])} versus Max-Depth {fmt(static['max_depth_gpr_q20_error'])}.",
        f"9. **Static q30:** Binary is also better: error {fmt(static['binary_gpc_q30_error'])} versus Max-Depth {fmt(static['max_depth_gpr_q30_error'])}.",
        f"10. **Transient Keyhole:** Max-Depth is more sensitive ({fmt(transient_sensitivity.get(best_max))} versus {fmt(transient_sensitivity.get(best_binary))}), but its persistent-case sensitivity is also higher ({fmt(persistent_sensitivity.get(best_max))} versus {fmt(persistent_sensitivity.get(best_binary))}); the advantage is not transient-specific.",
        f"11. **Online threshold stability:** reasonably stable within runs but not universal. Final {best_max} thresholds have mean {fmt(active_summary['max_depth_final_threshold_mean_um'])} µm, standard deviation {fmt(active_summary['max_depth_final_threshold_std_um'])} µm, and range {fmt(active_summary['max_depth_final_threshold_min_um'])}–{fmt(active_summary['max_depth_final_threshold_max_um'])} µm.",
        f"12. **Queries before threshold stability:** median {fmt(active_summary['median_max_depth_threshold_stability_budget'], 1)} queries under the declared ‘all later values within max(2 µm, 5%) of final tau’ rule.",
        f"13. **Best Max-Depth acquisition:** {best_max}.",
        f"14. **Best Binary acquisition:** {best_binary}.",
        f"15. **Max-Depth versus random:** yes on q20 AULC; active-minus-random = {fmt(max_vs_random['difference'])}, descriptive 95% interval [{fmt(max_vs_random['ci_low'])}, {fmt(max_vs_random['ci_high'])}].",
        f"16. **Binary versus random:** yes on q20 AULC; active-minus-random = {fmt(binary_vs_random['difference'])}, descriptive 95% interval [{fmt(binary_vs_random['ci_low'])}, {fmt(binary_vs_random['ci_high'])}].",
        f"17. **q20 AULC:** Binary is lower in the mean ({fmt(active_summary['best_binary_mean_q20_aulc'])} versus Max-Depth {fmt(active_summary['best_max_depth_mean_q20_aulc'])}), but the Max-minus-Binary paired interval [{fmt(best_best_q20['ci_low'])}, {fmt(best_best_q20['ci_high'])}] crosses zero.",
        f"18. **q30 AULC:** Binary is lower in the mean ({fmt(active_summary['best_binary_mean_q30_aulc'])} versus Max-Depth {fmt(active_summary['best_max_depth_mean_q30_aulc'])}), but the paired interval [{fmt(best_best_q30['ci_low'])}, {fmt(best_best_q30['ci_high'])}] crosses zero.",
        f"19. **Balanced-accuracy AULC:** Max-Depth is higher ({fmt(active_summary['best_max_depth_mean_balanced_accuracy_aulc'])} versus Binary {fmt(active_summary['best_binary_mean_balanced_accuracy_aulc'])}); the Max-minus-Binary interval [{fmt(best_best_ba['ci_low'])}, {fmt(best_best_ba['ci_high'])}] stays positive.",
        f"20. **Queries to useful performance:** target-dependent. For BA ≥ 0.90, Max-Depth reaches in median {fmt(max_ba_tolerance['median_queries_among_reached'], 1)} queries in {max_ba_tolerance['reached_runs']}/{max_ba_tolerance['total_runs']} runs versus Binary {fmt(binary_ba_tolerance['median_queries_among_reached'], 1)} in {binary_ba_tolerance['reached_runs']}/{binary_ba_tolerance['total_runs']}; for q20 error ≤ 0.20, Max-Depth reaches {max_q20_tolerance['reached_runs']}/{max_q20_tolerance['total_runs']} and Binary {binary_q20_tolerance['reached_runs']}/{binary_q20_tolerance['total_runs']}.",
        "21. **Stability across matched runs:** the q20/q30 cross-formulation intervals cross zero, whereas balanced-accuracy AULC consistently favours Max-Depth. Both selected active methods improve over their shared random baselines. Intervals remain descriptive because repeated-CV runs reuse simulations.",
        f"22. **Domain shift:** this weakens a Max-Depth-only conclusion. The all-route BA floors are Binary {fmt(transfer_floor.get('binary'))} and Max-Depth {fmt(transfer_floor.get('max_depth'))}; all-old→new is {fmt(all_old_to_new.loc['max_depth', 'balanced_accuracy'])} versus {fmt(all_old_to_new.loc['binary', 'balanced_accuracy'])}, while new→all-old reverses direction ({fmt(new_to_all_old.loc['max_depth', 'balanced_accuracy'])} versus {fmt(new_to_all_old.loc['binary', 'balanced_accuracy'])}). All transfer routes are secondary stress tests.",
        f"23. **G3 after Max-Depth:** it adds no robust primary advantage on the matched 404 rows: q20 AULC is G3 straddle {fmt(g3_q20.get('g3_straddle'))}, common Max-Depth straddle {fmt(g3_q20.get('max_depth_g3_common_straddle'))}, and Binary margin {fmt(g3_q20.get('binary_g3_common_margin'))}. G3 remains secondary.",
        f"24. **Boundary disagreement:** yes, in specific supported descriptive slices; disagreement spans {100 * disagreement_low:.1f}%–{100 * disagreement_high:.1f}% of supported grid cells. These full-data slices are not held-out physical truth.",
        f"25. **Final formulation decision:** **{summary['final_decision']}** — {summary['decision_reason']}",
        "",
        "## Hard stop",
        "",
        "Phase 6 is intentionally uncommitted and unpushed. No labels were changed, no target was redefined, and no Phase 7 work was started.",
    ]
    (output_dir / "results_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def finalize_phase6(
    prepared: Mapping[str, Any],
    active: Mapping[str, pd.DataFrame],
    output_dir: Path,
    *,
    runtime: Mapping[str, Any],
    smoke: bool,
) -> None:
    static_summary = pd.read_csv(output_dir / "static_model_summary.csv")
    domain = domain_transfer_models(prepared["primary"], prepared["boundary"])
    write_csv(output_dir / "domain_transfer_model_summary.csv", domain)
    if smoke:
        write_json(
            output_dir / "runtime_summary.json",
            {**dict(runtime), "mode": "smoke", "scientific_reduction": "2 primary folds, 1 G3 fold, budget 30, reduced methods"},
        )
        write_json(
            output_dir / "summary.json",
            {
                "phase": "Week 7 Phase 6 smoke",
                "status": "PASS_if_validator_passes",
                "not_a_scientific_result": True,
                "runtime": dict(runtime),
            },
        )
        (output_dir / "results_summary.md").write_text(
            "# Phase 6 smoke run\n\nThis reduced run validates execution, leakage barriers, accounting, and checkpointing only. It is not a scientific Phase 6 result.\n",
            encoding="utf-8",
        )
        return

    from src.week7_phase6_reporting import (
        build_supported_boundary_surfaces,
        generate_phase6_figures,
    )

    surfaces, disagreement, surface_diagnostics = build_supported_boundary_surfaces(
        prepared["primary"], grid_size=51, nn_support_quantile=0.95
    )
    write_csv(output_dir / "boundary_surface_data.csv", surfaces)
    write_csv(output_dir / "boundary_disagreement_summary.csv", disagreement)
    max_vs_g3 = pd.read_csv(output_dir / "max_depth_vs_g3_summary.csv")
    scorecard, decision, details = build_final_decision(
        aulc=active["aulc"],
        paired_bootstrap=active["paired_bootstrap"],
        event=prepared["event"],
        domain=domain,
        thresholds=active["thresholds"],
        max_vs_g3=max_vs_g3,
    )
    write_csv(output_dir / "phase6_formulation_scorecard.csv", scorecard)
    write_csv(output_dir / "phase6_final_decision.csv", decision)
    runtime_payload = {**dict(runtime), "mode": "full", "surface_diagnostics": surface_diagnostics}
    write_json(output_dir / "runtime_summary.json", runtime_payload)
    write_results_summary(
        output_dir,
        prepared=prepared,
        static_summary=static_summary,
        active=active,
        domain=domain,
        decision_details=details,
        runtime=runtime_payload,
    )
    figure_manifest = generate_phase6_figures(output_dir, artifacts=None, minimum_count=40)
    write_csv(output_dir / "figure_manifest.csv", figure_manifest)
    write_csv(output_dir / "output_manifest.csv", output_manifest(output_dir))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["prepare", "smoke", "full"],
        default="full",
        help="prepare only, reduced smoke, or the complete Phase 6 protocol",
    )
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--force", action="store_true", help="Ignore active checkpoints and recompute")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    require(args.workers >= 1, "--workers must be positive")
    smoke = args.mode == "smoke"
    output_dir = SMOKE_DIR if smoke else OUTPUT_DIR
    invocation_started = utc_now()
    wall_start = time.perf_counter()
    stage_times: dict[str, float] = {}
    prepare_start = time.perf_counter()
    prepared = prepare_phase6(output_dir, smoke=smoke)
    stage_times["prepare_seconds"] = time.perf_counter() - prepare_start
    if args.mode == "prepare":
        print(f"Phase 6 preflight complete: {output_dir}")
        return

    static_start = time.perf_counter()
    run_static_stage(prepared, output_dir, workers=args.workers, smoke=smoke)
    stage_times["static_seconds"] = time.perf_counter() - static_start
    active_start = time.perf_counter()
    active = run_active_stage(
        prepared, output_dir, workers=args.workers, smoke=smoke, force=args.force
    )
    stage_times["active_seconds"] = time.perf_counter() - active_start
    finalize_start = time.perf_counter()
    runtime = {
        "invocation_started_utc": invocation_started,
        "workers": args.workers,
        "mode": args.mode,
        "stage_times": stage_times,
        "wall_seconds_before_finalize": time.perf_counter() - wall_start,
        "active_arm_runtime_sum_seconds": float(active["manifest"]["runtime_seconds"].sum()),
        "checkpoint_reuse_enabled": not args.force,
    }
    finalize_phase6(prepared, active, output_dir, runtime=runtime, smoke=smoke)
    stage_times["finalize_seconds"] = time.perf_counter() - finalize_start
    total = time.perf_counter() - wall_start
    history_entry = {
        "started_at_utc": invocation_started,
        "completed_at_utc": utc_now(),
        "mode": args.mode,
        "workers": args.workers,
        "force": args.force,
        "stage_times_seconds": stage_times,
        "wall_seconds": total,
        "status": "PASS",
        "scientific_scope": (
            "reduced_smoke_not_a_result" if smoke else "full_20_run_primary_plus_20_run_G3_common"
        ),
    }
    append_json_history(output_dir / "execution_history.json", history_entry)
    runtime_path = output_dir / "runtime_summary.json"
    runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime_payload["completed_at_utc"] = utc_now()
    runtime_payload["total_wall_seconds"] = total
    runtime_payload["stage_times"] = stage_times
    write_json(runtime_path, runtime_payload)
    if (output_dir / "figure_manifest.csv").is_file():
        write_csv(output_dir / "output_manifest.csv", output_manifest(output_dir))
    print(f"Phase 6 {args.mode} complete in {total:.1f} s: {output_dir}")


if __name__ == "__main__":
    main()
