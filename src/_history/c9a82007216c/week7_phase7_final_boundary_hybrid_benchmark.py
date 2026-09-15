"""Week 7 Phase 7 boundary-robustness and hybrid-acquisition benchmark.

Phase 7 is an exact matched extension of the published Phase 6 real-data
benchmark.  Ioan's experiment-level manual ``has_keyhole`` annotation remains
the regime target.  Maximum depth is revealed by the same queried simulator
run and may help *acquisition only* for the two preregistered Hybrid methods.

The module deliberately fails closed around information flow:

* the exact published Phase 6 population, outer folds, candidate pools,
  deterministic permutations, warm starts, and baseline trajectories are
  reused;
* B1/B2/B3 use only P, VX, LS, ST and the manual label, are evaluation-only,
  and are joined only after a query has been selected;
* unqueried labels and maximum-depth values never enter fitting or acquisition;
* Hybrid primary predictions always come from the Binary GPC;
* the gate fraction, rank-fusion weights, kernels, and decision rule were
  written and hashed before smoke/full results.

Each method/run is checkpointed atomically.  Saved row-level artifacts are the
authority for all summaries and validation.
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
import sys
import time
import warnings
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import Delaunay, QhullError, distance
from scipy.stats import spearmanr
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
if str(_BOOTSTRAP_ROOT) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src.week7_sph_v2_common import sha256_file, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
SMOKE_DIR = OUTPUT_DIR / "smoke"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "07_final_boundary_hybrid_benchmark.ipynb"
PHASE6_OUTPUT = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"

EXPECTED_PHASE6_COMMIT = "5734de6f533e1de1e15a07de24e7d4e6e53bb6fa"
EXPECTED_PHASE6_PARENT = "6cc2ea150b9deb6ec9dd529d94ac55cc86556cfb"
EXPECTED_HF_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
PHASE6_BRANCH = "codex/week7-phase6-real-data-boundary-active-level-set"
PHASE7_BRANCH = "codex/week7-phase7-final-boundary-hybrid-benchmark"

PREREG_PATH = OUTPUT_DIR / "phase7_preregistered_decision_rule.json"
PREREG_HASH_PATH = OUTPUT_DIR / "phase7_preregistered_decision_rule.sha256"
EXPECTED_PREREG_SHA256 = "a3581cb61c4b2f95aa71838fc9c199ca8f992fef7de67104970767db0af9643f"

FEATURE_COLUMNS = list(p6.FEATURE_COLUMNS)
BOUNDARY_IDS = ("B1", "B2", "B3")
BOUNDARY_QUANTILES = (10, 20, 30)
PRIMARY_BOUNDARY_QUANTILES = (20, 30)
CONSENSUS_IDS = ("consensus_q20", "consensus_q30")
FINAL_BUDGET = 80
SMOKE_BUDGET = 30
COMMON_START_EXPECTED = 16
PAIRED_BOOTSTRAP_RESAMPLES = 5000
GATE_FRACTION = 0.20
RANK_BINARY_WEIGHT = 0.50
RANK_DEPTH_WEIGHT = 0.50
PREDICTION_CHECKPOINTS = (12, 15, 20, 25, 30, 40, 50, 60, 70, 80)

M0_BINARY = "shared_random_binary_head"
M0_DEPTH = "shared_random_max_depth_head"
M1_BINARY = "binary_uncertainty_repulsion"
M2_DEPTH = "max_depth_straddle"
M3_GATE = "hybrid_binary_gate20_max_depth_straddle"
M4_FUSION = "hybrid_equal_rank_fusion"

PRIMARY_SCORECARD_METHODS = (M0_BINARY, M1_BINARY, M2_DEPTH, M3_GATE, M4_FUSION)
EXECUTED_METHODS = (M0_BINARY, M0_DEPTH, M1_BINARY, M2_DEPTH, M3_GATE, M4_FUSION)
HYBRID_METHODS = (M3_GATE, M4_FUSION)
SMOKE_METHODS = (M1_BINARY, M3_GATE, M4_FUSION)

PHASE6_SOURCE_METHOD = {
    M0_BINARY: "binary_random",
    M0_DEPTH: "max_depth_random",
    M1_BINARY: "binary_uncertainty_repulsion",
    M2_DEPTH: "max_depth_straddle",
}
METHOD_FORMULATION = {
    M0_BINARY: "binary",
    M0_DEPTH: "max_depth",
    M1_BINARY: "binary",
    M2_DEPTH: "max_depth",
    M3_GATE: "hybrid_binary_primary",
    M4_FUSION: "hybrid_binary_primary",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git_output(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, stderr=subprocess.STDOUT
    ).strip()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def frame_sha256(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> str:
    chosen = frame if columns is None else frame[list(columns)]
    return sha256_bytes(chosen.to_csv(index=False).encode("utf-8"))


def stable_seed(*parts: object) -> int:
    return p6.stable_seed("phase7", *parts)


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    require(normalized.isin(["true", "false", "1", "0"]).all(), f"Invalid boolean values in {series.name}")
    return normalized.isin(["true", "1"])


def json_safe(value: Any) -> Any:
    return p6.json_safe(value)


def atomic_pickle(path: Path, payload: Any) -> None:
    p6.atomic_pickle(path, payload)


def load_pickle(path: Path) -> Any:
    with path.open("rb") as handle:
        return pickle.load(handle)


def append_execution_history(output_dir: Path, stage: str, status: str, **details: Any) -> None:
    path = output_dir / "execution_history.json"
    history: list[dict[str, Any]] = []
    if path.is_file():
        history = json.loads(path.read_text(encoding="utf-8"))
    history.append(
        {
            "timestamp_utc": utc_now(),
            "stage": stage,
            "status": status,
            **json_safe(details),
        }
    )
    write_json(path, history)


def first_successful_full_runtime(output_dir: Path) -> float | None:
    """Return the first completed budget-80 full-run wall time, if recorded.

    Later report refreshes intentionally reuse method checkpoints and are much
    faster.  Keeping the first full-run time separate prevents a refresh from
    overwriting the scientific execution cost.
    """

    path = output_dir / "execution_history.json"
    if not path.is_file():
        return None
    history = json.loads(path.read_text(encoding="utf-8"))
    for entry in history:
        if (
            entry.get("stage") == "full_benchmark"
            and entry.get("status") == "PASS"
            and int(entry.get("final_budget", -1)) == FINAL_BUDGET
            and entry.get("wall_seconds") is not None
        ):
            return float(entry["wall_seconds"])
    return None


def ensure_preregistration() -> dict[str, Any]:
    require(PREREG_PATH.is_file(), f"Missing preregistration: {PREREG_PATH}")
    require(PREREG_HASH_PATH.is_file(), f"Missing preregistration hash: {PREREG_HASH_PATH}")
    actual = sha256_file(PREREG_PATH)
    recorded = PREREG_HASH_PATH.read_text(encoding="utf-8").split()[0].strip().lower()
    require(actual == EXPECTED_PREREG_SHA256, f"Preregistration drift: {actual}")
    require(recorded == actual, "Preregistration .sha256 does not match JSON")
    payload = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    require(payload["status"] == "PREREGISTERED_BEFORE_SMOKE_AND_FULL_RESULTS", "Preregistration status drift")
    require(payload["hybrid_gate"]["requested_fraction"] == GATE_FRACTION, "Gate fraction drift")
    require(payload["hybrid_rank_fusion"]["binary_weight"] == RANK_BINARY_WEIGHT, "Binary fusion weight drift")
    require(payload["hybrid_rank_fusion"]["max_depth_weight"] == RANK_DEPTH_WEIGHT, "Depth fusion weight drift")
    return payload


def read_phase6_tables() -> dict[str, pd.DataFrame]:
    names = {
        "population": "primary_common_population.csv",
        "split_manifest": "outer_split_manifest.csv",
        "run_manifest": "active_run_manifest.csv",
        "initialization": "active_initialization_audit.csv",
        "queries": "active_query_history.csv",
        "predictions": "active_prediction_history.csv",
        "curves": "active_learning_curve_summary.csv",
        "aulc": "active_learning_aulc_summary.csv",
        "thresholds": "online_threshold_history.csv",
        "boundary": "empirical_boundary_reference.csv",
        "transient": "subgroup_transient_persistent_results.csv",
        "timing": "subgroup_t0_timing_results.csv",
        "domain": "domain_transfer_model_summary.csv",
    }
    tables: dict[str, pd.DataFrame] = {}
    for key, name in names.items():
        path = PHASE6_OUTPUT / name
        require(path.is_file(), f"Missing published Phase 6 artifact: {path}")
        tables[key] = pd.read_csv(path, low_memory=False)
    population = tables["population"]
    population["has_keyhole"] = strict_bool(population["has_keyhole"])
    for column in [*FEATURE_COLUMNS, "value__max_depth"]:
        population[column] = pd.to_numeric(population[column], errors="raise")
    require(len(population) == 405, f"Phase 6 primary population drift: {len(population)}")
    require(int(population["has_keyhole"].sum()) == 73, "Phase 6 Keyhole count drift")
    require(int((~population["has_keyhole"]).sum()) == 332, "Phase 6 non-Keyhole count drift")
    require(population["experiment_name"].is_unique, "Population experiment names not unique")
    return tables


def specs_from_phase6_manifest(
    population: pd.DataFrame, split_manifest: pd.DataFrame
) -> list[p6.RunSpec]:
    primary = split_manifest[split_manifest["benchmark_population"].eq("primary_common")].copy()
    primary["population_row_index"] = pd.to_numeric(primary["population_row_index"], errors="raise").astype(int)
    specs: list[p6.RunSpec] = []
    for run_id, group in primary.groupby("run_id", sort=True):
        train = tuple(sorted(group.loc[group["role"].eq("training_pool"), "population_row_index"].astype(int)))
        test = tuple(sorted(group.loc[group["role"].eq("untouched_test"), "population_row_index"].astype(int)))
        require(len(train) + len(test) == len(population), f"{run_id}: split does not cover population")
        require(set(train).isdisjoint(test), f"{run_id}: train/test overlap")
        repeat = int(group["repeat"].iloc[0])
        fold = int(group["fold"].iloc[0])
        specs.append(
            p6.RunSpec(
                benchmark_population="primary_common",
                run_id=str(run_id),
                repeat=repeat,
                fold=fold,
                train_indices=train,
                test_indices=test,
                run_seed=p6.stable_seed(p6.BASE_SEED, str(run_id)),
            )
        )
    require(len(specs) == 20, f"Expected 20 exact Phase 6 primary runs, found {len(specs)}")
    return specs


def phase6_query_sequence(
    queries: pd.DataFrame, run_id: str, phase6_method: str, final_budget: int
) -> list[int]:
    part = queries[
        queries["benchmark_population"].eq("primary_common")
        & queries["run_id"].eq(run_id)
        & queries["method"].eq(phase6_method)
    ].copy()
    part["query_order"] = pd.to_numeric(part["query_order"], errors="raise").astype(int)
    part["population_row_index"] = pd.to_numeric(part["population_row_index"], errors="raise").astype(int)
    part = part[part["query_order"].le(final_budget)].sort_values("query_order")
    require(part["query_order"].tolist() == list(range(1, final_budget + 1)), f"{run_id}/{phase6_method}: incomplete Phase 6 query sequence")
    return part["population_row_index"].tolist()


def build_phase6_run_reuse_audit(
    population: pd.DataFrame,
    specs: Sequence[p6.RunSpec],
    tables: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    run_manifest = tables["run_manifest"]
    initialization = tables["initialization"]
    queries = tables["queries"]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        generated_warm, permutation = p6.warm_start_indices(spec, population, FINAL_BUDGET)
        saved_init = initialization[
            initialization["benchmark_population"].eq("primary_common")
            & initialization["run_id"].eq(spec.run_id)
        ]
        require(len(saved_init) == 1, f"{spec.run_id}: missing Phase 6 initialization row")
        effective = int(saved_init["effective_warm_start"].iloc[0])
        saved_sequence = phase6_query_sequence(queries, spec.run_id, "binary_uncertainty_repulsion", FINAL_BUDGET)
        saved_warm = saved_sequence[:effective]
        warm_frame = pd.DataFrame(
            {
                "query_order": range(1, effective + 1),
                "experiment_name": population.iloc[saved_warm]["experiment_name"].tolist(),
            }
        )
        warm_hash = frame_sha256(warm_frame, ["query_order", "experiment_name"])
        split_hash = sha256_bytes(
            json.dumps({"train": sorted(spec.train_indices), "test": sorted(spec.test_indices)}).encode("utf-8")
        )
        p6_rows = run_manifest[
            run_manifest["benchmark_population"].eq("primary_common")
            & run_manifest["run_id"].eq(spec.run_id)
            & run_manifest["method"].isin(["binary_uncertainty_repulsion", "max_depth_straddle"])
        ]
        require(len(p6_rows) == 2, f"{spec.run_id}: champion manifest rows missing")
        require(p6_rows["split_sha256"].nunique() == 1, f"{spec.run_id}: Phase 6 champion split hash mismatch")
        require(p6_rows["warm_start_sha256"].nunique() == 1, f"{spec.run_id}: Phase 6 champion warm hash mismatch")
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "training_pool_count": len(spec.train_indices),
                "untouched_test_count": len(spec.test_indices),
                "effective_warm_start": effective,
                "phase7_generated_warm_equals_phase6_saved": generated_warm == saved_warm,
                "phase6_warm_sha256": str(saved_init["warm_start_sha256"].iloc[0]),
                "phase7_warm_sha256": warm_hash,
                "warm_hash_matches": warm_hash == str(saved_init["warm_start_sha256"].iloc[0]),
                "phase6_split_sha256": str(p6_rows["split_sha256"].iloc[0]),
                "phase7_split_sha256": split_hash,
                "split_hash_matches": split_hash == str(p6_rows["split_sha256"].iloc[0]),
                "candidate_pool_sha256": sha256_bytes(json.dumps(sorted(spec.train_indices)).encode("utf-8")),
                "test_set_sha256": sha256_bytes(json.dumps(sorted(spec.test_indices)).encode("utf-8")),
                "initial_permutation_sha256": sha256_bytes(json.dumps([int(v) for v in permutation]).encode("utf-8")),
                "initial_permutation_seed_rule": "Phase6 BASE_SEED, run_id, shared_pool_permutation",
                "same_population_row_order": True,
                "status": "PASS",
            }
        )
    audit = pd.DataFrame(rows)
    require(audit["warm_hash_matches"].all(), "One or more warm-start hashes drifted")
    require(audit["split_hash_matches"].all(), "One or more split hashes drifted")
    require(audit["phase7_generated_warm_equals_phase6_saved"].all(), "One or more deterministic warm starts drifted")
    require(int(audit["effective_warm_start"].max()) == COMMON_START_EXPECTED, "Common-start budget drift")
    return audit


def publication_and_provenance_audits() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    phase7_head = git_output("rev-parse", "HEAD")
    phase7_branch = git_output("branch", "--show-current")
    local_phase6 = git_output("show-ref", "--hash", f"refs/heads/{PHASE6_BRANCH}")
    upstream_phase6 = git_output("show-ref", "--hash", f"refs/remotes/origin/{PHASE6_BRANCH}")
    remote_line = git_output("ls-remote", "origin", f"refs/heads/{PHASE6_BRANCH}")
    remote_phase6 = remote_line.split()[0]
    live_hf = p6.resolve_live_hf_revision()
    original = p6.verify_original_dirty_checkout()
    publication = {
        "phase6_branch": PHASE6_BRANCH,
        "expected_commit": EXPECTED_PHASE6_COMMIT,
        "local_commit": local_phase6,
        "upstream_commit": upstream_phase6,
        "remote_ls_remote_commit": remote_phase6,
        "all_equal": local_phase6 == upstream_phase6 == remote_phase6 == EXPECTED_PHASE6_COMMIT,
        "commit_message": git_output("show", "-s", "--format=%s", EXPECTED_PHASE6_COMMIT),
        "phase6_parent": git_output("rev-parse", f"{EXPECTED_PHASE6_COMMIT}^"),
        "pull_request_opened": False,
        "merged_to_main": False,
        "verified_at_utc": utc_now(),
    }
    hf = {
        "repository": p6.SPH_V2_REPO_ID,
        "expected_phase6_revision": EXPECTED_HF_REVISION,
        "live_revision": live_hf,
        "matches_phase6": live_hf == EXPECTED_HF_REVISION,
        "scientific_data_rebuild_required": False,
        "verified_at_utc": utc_now(),
    }
    provenance = {
        "phase": "Week 7 Phase 7",
        "phase7_branch": phase7_branch,
        "phase7_head_before_changes": phase7_head,
        "exact_phase6_parent": EXPECTED_PHASE6_COMMIT,
        "phase6_parent_parent": EXPECTED_PHASE6_PARENT,
        "hf_revision": live_hf,
        "phase6_output_directory": str(PHASE6_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "phase6_artifact_hashes": {
            name: sha256_file(PHASE6_OUTPUT / name)
            for name in [
                "primary_common_population.csv",
                "outer_split_manifest.csv",
                "active_run_manifest.csv",
                "active_initialization_audit.csv",
                "active_query_history.csv",
                "active_prediction_history.csv",
                "active_learning_curve_summary.csv",
                "active_learning_aulc_summary.csv",
                "online_threshold_history.csv",
                "empirical_boundary_reference.csv",
            ]
        },
        "preregistered_decision_rule_sha256": sha256_file(PREREG_PATH),
        "original_dirty_checkout": original,
        "manual_label_definition": "at least one valid saved physical frame manually labelled Keyhole",
        "manual_labels_modified": False,
        "maximum_depth_definition": "max(0, -z_min)",
        "maximum_depth_redefined": False,
        "T0_definition_unchanged": True,
    }
    require(publication["all_equal"], "Phase 6 local/upstream/remote publication mismatch")
    require(publication["phase6_parent"] == EXPECTED_PHASE6_PARENT, "Phase 6 parent drift")
    require(phase7_head == EXPECTED_PHASE6_COMMIT, "Phase 7 was not created from the exact committed Phase 6 SHA")
    require(phase7_branch == PHASE7_BRANCH, "Unexpected Phase 7 branch")
    require(hf["matches_phase6"], "Live sph_v2 revision drifted from Phase 6")
    require(original["all_protected_hashes_match"], "Original dirty checkout protection failed")
    return publication, hf, provenance


def deterministic_order(values: np.ndarray, names: np.ndarray, *, ascending: bool) -> np.ndarray:
    numeric = np.asarray(values, dtype=float)
    if ascending:
        return np.lexsort((names.astype(str), numeric))
    return np.lexsort((names.astype(str), -numeric))


def rank_fraction(values: np.ndarray, names: np.ndarray, *, ascending: bool) -> np.ndarray:
    order = deterministic_order(values, names, ascending=ascending)
    rank = np.empty(len(order), dtype=int)
    rank[order] = np.arange(1, len(order) + 1)
    return rank / len(order)


def robust_scaled(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    median = np.median(x, axis=0)
    q25, q75 = np.quantile(x, [0.25, 0.75], axis=0)
    iqr = q75 - q25
    safe_iqr = np.where(iqr > 1e-12, iqr, 1.0)
    return (x - median) / safe_iqr, median, safe_iqr


def class_distance_components(x_scaled: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dmat = distance.cdist(x_scaled, x_scaled)
    np.fill_diagonal(dmat, np.inf)
    same_mask = labels[:, None] == labels[None, :]
    opposite_mask = ~same_mask
    np.fill_diagonal(same_mask, False)
    opposite = np.where(opposite_mask, dmat, np.inf)
    same = np.where(same_mask, dmat, np.inf)
    nearest_opp = np.argmin(opposite, axis=1)
    nearest_same = np.argmin(same, axis=1)
    d_opp = opposite[np.arange(len(labels)), nearest_opp]
    d_same = same[np.arange(len(labels)), nearest_same]
    require(np.isfinite(d_opp).all(), "Every row must have an opposite-class neighbour")
    require(np.isfinite(d_same).all(), "Every row must have a same-class neighbour")
    return d_opp, d_same, nearest_opp, nearest_same


def build_boundary_metrics(population: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = population[["experiment_name", "partition", "has_keyhole", *FEATURE_COLUMNS]].copy()
    labels = frame["has_keyhole"].astype(int).to_numpy()
    names = frame["experiment_name"].astype(str).to_numpy()
    x = frame[FEATURE_COLUMNS].to_numpy(float)
    scaler = StandardScaler().fit(x)
    x_z = scaler.transform(x)
    x_robust, robust_median, robust_iqr = robust_scaled(x)

    d_opp, d_same, nearest_opp, nearest_same = class_distance_components(x_z, labels)
    frame["B1_nearest_opposite_distance"] = d_opp
    frame["B1_nearest_opposite_experiment"] = names[nearest_opp]
    frame["B2_local_disagreement_k5"] = 0.0
    frame["B2_local_disagreement_k10_secondary"] = 0.0
    for k, column in [(5, "B2_local_disagreement_k5"), (10, "B2_local_disagreement_k10_secondary")]:
        nn = NearestNeighbors(n_neighbors=k + 1).fit(x_z)
        _, neighbours = nn.kneighbors(x_z)
        neighbour_labels = labels[neighbours[:, 1:]]
        frame[column] = (neighbour_labels != labels[:, None]).mean(axis=1)
    frame["B3_d_opp"] = d_opp
    frame["B3_d_same"] = d_same
    frame["B3_relative_class_distance_ratio"] = d_opp / np.maximum(d_opp + d_same, 1e-15)
    frame["B3_nearest_same_experiment"] = names[nearest_same]

    robust_opp, robust_same, _, _ = class_distance_components(x_robust, labels)
    frame["robust_B1_nearest_opposite_distance"] = robust_opp
    frame["robust_B3_relative_class_distance_ratio"] = robust_opp / np.maximum(robust_opp + robust_same, 1e-15)
    for j, feature in enumerate(FEATURE_COLUMNS):
        frame[f"standardized_{feature}"] = x_z[:, j]
        frame[f"robust_scaled_{feature}"] = x_robust[:, j]

    metric_columns = {
        "B1": ("B1_nearest_opposite_distance", True),
        "B2": ("B2_local_disagreement_k5", False),
        "B3": ("B3_relative_class_distance_ratio", True),
    }
    membership_rows: list[dict[str, Any]] = []
    for metric, (column, ascending) in metric_columns.items():
        frame[f"{metric}_boundary_rank_fraction"] = rank_fraction(frame[column].to_numpy(float), names, ascending=ascending)
        order = deterministic_order(frame[column].to_numpy(float), names, ascending=ascending)
        for q in BOUNDARY_QUANTILES:
            count = int(math.ceil(q / 100 * len(frame)))
            selected = order[:count]
            flag = np.zeros(len(frame), dtype=bool)
            flag[selected] = True
            frame[f"{metric}_q{q}"] = flag
            for idx in selected:
                membership_rows.append(
                    {
                        "metric": metric,
                        "quantile": q,
                        "experiment_name": names[idx],
                        "partition": frame.iloc[idx]["partition"],
                        "has_keyhole": bool(labels[idx]),
                        "metric_value": float(frame.iloc[idx][column]),
                        "rank_within_population": int(np.flatnonzero(order == idx)[0] + 1),
                        "evaluation_only": True,
                    }
                )

    for q in PRIMARY_BOUNDARY_QUANTILES:
        columns = [f"{metric}_q{q}" for metric in BOUNDARY_IDS]
        frame[f"consensus_q{q}"] = frame[columns].sum(axis=1).ge(2)

    definitions = pd.DataFrame(
        [
            {
                "metric": "B1",
                "definition": "nearest standardized Euclidean distance to an opposite manual label",
                "boundary_like_direction": "smaller",
                "primary_scaling": "full-population z-score of P,VX,LS,ST",
                "uses_only_inputs_and_manual_labels": True,
                "evaluation_only": True,
                "enters_acquisition": False,
                "tuned": False,
            },
            {
                "metric": "B2",
                "definition": "fraction of k=5 nearest neighbours excluding self with a different manual label",
                "boundary_like_direction": "larger",
                "primary_scaling": "full-population z-score of P,VX,LS,ST",
                "uses_only_inputs_and_manual_labels": True,
                "evaluation_only": True,
                "enters_acquisition": False,
                "tuned": False,
            },
            {
                "metric": "B3",
                "definition": "d_opp/(d_opp+d_same), nearest same excludes self",
                "boundary_like_direction": "smaller",
                "primary_scaling": "full-population z-score of P,VX,LS,ST",
                "uses_only_inputs_and_manual_labels": True,
                "evaluation_only": True,
                "enters_acquisition": False,
                "tuned": False,
            },
        ]
    )

    rank_columns = [f"{m}_boundary_rank_fraction" for m in BOUNDARY_IDS]
    corr_rows: list[dict[str, Any]] = []
    for left in BOUNDARY_IDS:
        for right in BOUNDARY_IDS:
            rho, pvalue = spearmanr(frame[f"{left}_boundary_rank_fraction"], frame[f"{right}_boundary_rank_fraction"])
            corr_rows.append(
                {
                    "metric_a": left,
                    "metric_b": right,
                    "spearman_rank_correlation": float(rho),
                    "descriptive_p_value": float(pvalue),
                    "population_count": len(frame),
                    "evaluation_only": True,
                }
            )

    overlap_rows: list[dict[str, Any]] = []
    for q in PRIMARY_BOUNDARY_QUANTILES:
        for left in BOUNDARY_IDS:
            left_set = set(frame.loc[frame[f"{left}_q{q}"], "experiment_name"])
            for right in BOUNDARY_IDS:
                right_set = set(frame.loc[frame[f"{right}_q{q}"], "experiment_name"])
                overlap_rows.append(
                    {
                        "quantile": q,
                        "metric_a": left,
                        "metric_b": right,
                        "intersection_count": len(left_set & right_set),
                        "union_count": len(left_set | right_set),
                        "jaccard": len(left_set & right_set) / max(len(left_set | right_set), 1),
                        "metric_a_count": len(left_set),
                        "metric_b_count": len(right_set),
                    }
                )

    consensus_rows: list[dict[str, Any]] = []
    for q in PRIMARY_BOUNDARY_QUANTILES:
        subset = frame[frame[f"consensus_q{q}"]]
        consensus_rows.append(
            {
                "subset": f"consensus_q{q}",
                "rule": f"membership in at least two of B1/B2/B3 q{q}",
                "row_count": len(subset),
                "keyhole_count": int(subset["has_keyhole"].sum()),
                "non_keyhole_count": int((~subset["has_keyhole"]).sum()),
                "new_data_count": int(subset["partition"].eq("new-data").sum()),
                "old_local_count": int(subset["partition"].eq("old-data-local").sum()),
                "old_remote_count": int(subset["partition"].eq("old-data-remote-clean").sum()),
                "secondary_not_replacement": True,
            }
        )

    scaling_rows: list[dict[str, Any]] = []
    for metric, primary_col, robust_col in [
        ("B1", "B1_nearest_opposite_distance", "robust_B1_nearest_opposite_distance"),
        ("B3", "B3_relative_class_distance_ratio", "robust_B3_relative_class_distance_ratio"),
    ]:
        primary_rank = rank_fraction(frame[primary_col].to_numpy(float), names, ascending=True)
        robust_rank = rank_fraction(frame[robust_col].to_numpy(float), names, ascending=True)
        rho, _ = spearmanr(primary_rank, robust_rank)
        for q in PRIMARY_BOUNDARY_QUANTILES:
            count = int(math.ceil(q / 100 * len(frame)))
            primary_order = deterministic_order(frame[primary_col].to_numpy(float), names, ascending=True)[:count]
            robust_order = deterministic_order(frame[robust_col].to_numpy(float), names, ascending=True)[:count]
            a, b = set(primary_order), set(robust_order)
            scaling_rows.append(
                {
                    "metric": metric,
                    "quantile": q,
                    "primary_scaling": "z_score",
                    "secondary_scaling": "median_IQR",
                    "spearman_rank_correlation": float(rho),
                    "membership_jaccard": len(a & b) / max(len(a | b), 1),
                    "primary_count": len(a),
                    "robust_count": len(b),
                    "robust_scaling_is_secondary": True,
                    "robust_center_json": json.dumps(json_safe(robust_median.tolist())),
                    "robust_scale_json": json.dumps(json_safe(robust_iqr.tolist())),
                }
            )

    return {
        "definitions": definitions,
        "reference": frame,
        "correlations": pd.DataFrame(corr_rows),
        "q10_membership": pd.DataFrame(membership_rows).query("quantile == 10").reset_index(drop=True),
        "q20_membership": pd.DataFrame(membership_rows).query("quantile == 20").reset_index(drop=True),
        "q30_membership": pd.DataFrame(membership_rows).query("quantile == 30").reset_index(drop=True),
        "overlap": pd.DataFrame(overlap_rows),
        "consensus": pd.DataFrame(consensus_rows),
        "scaling": pd.DataFrame(scaling_rows),
    }


def test_boundary_flags(spec: p6.RunSpec, boundary: pd.DataFrame) -> dict[str, np.ndarray]:
    test = np.asarray(spec.test_indices, dtype=int)
    names = boundary.iloc[test]["experiment_name"].astype(str).to_numpy()
    result: dict[str, np.ndarray] = {}
    metric_columns = {
        "B1": ("B1_nearest_opposite_distance", True),
        "B2": ("B2_local_disagreement_k5", False),
        "B3": ("B3_relative_class_distance_ratio", True),
    }
    for metric, (column, ascending) in metric_columns.items():
        values = boundary.iloc[test][column].to_numpy(float)
        order = deterministic_order(values, names, ascending=ascending)
        for q in BOUNDARY_QUANTILES:
            count = int(math.ceil(q / 100 * len(test)))
            flag = np.zeros(len(test), dtype=bool)
            flag[order[:count]] = True
            result[f"{metric}_q{q}"] = flag
    for q in PRIMARY_BOUNDARY_QUANTILES:
        result[f"consensus_q{q}"] = (
            result[f"B1_q{q}"].astype(int)
            + result[f"B2_q{q}"].astype(int)
            + result[f"B3_q{q}"].astype(int)
        ) >= 2
    return result


def write_preflight_artifacts(
    output_dir: Path,
    tables: Mapping[str, pd.DataFrame],
    specs: Sequence[p6.RunSpec],
    run_reuse: pd.DataFrame,
    boundary_artifacts: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    publication, hf, provenance = publication_and_provenance_audits()
    population = tables["population"]
    preflight = {
        "phase": "Week 7 Phase 7",
        "status": "PASS",
        "phase7_branch": PHASE7_BRANCH,
        "exact_phase6_parent": git_output("rev-parse", "HEAD"),
        "phase6_publication_verified": publication["all_equal"],
        "hf_revision": hf["live_revision"],
        "hf_revision_matches_phase6": hf["matches_phase6"],
        "primary_population_count": len(population),
        "keyhole_count": int(population["has_keyhole"].sum()),
        "non_keyhole_count": int((~population["has_keyhole"]).sum()),
        "outer_run_count": len(specs),
        "exact_run_reuse_pass_count": int(run_reuse["status"].eq("PASS").sum()),
        "maximum_effective_warm_start": int(run_reuse["effective_warm_start"].max()),
        "final_budget": FINAL_BUDGET,
        "boundary_definitions": list(BOUNDARY_IDS),
        "boundary_metrics_are_evaluation_only": True,
        "preregistered_decision_rule_sha256": sha256_file(PREREG_PATH),
        "preregistered_before_result_files": True,
        "manual_labels_modified": False,
        "maximum_depth_redefined": False,
        "new_kernel_introduced": False,
        "hard_stop_after_phase7": True,
    }
    write_json(output_dir / "phase7_preflight.json", preflight)
    write_json(output_dir / "input_provenance.json", provenance)
    write_json(output_dir / "hf_revision_audit.json", hf)
    write_json(output_dir / "phase6_publication_audit.json", publication)
    write_csv(output_dir / "phase6_run_reuse_audit.csv", run_reuse)
    write_csv(output_dir / "boundary_metric_definitions.csv", boundary_artifacts["definitions"])
    write_csv(output_dir / "boundary_metric_reference.csv", boundary_artifacts["reference"])
    write_csv(output_dir / "boundary_metric_correlations.csv", boundary_artifacts["correlations"])
    write_csv(output_dir / "boundary_q10_membership.csv", boundary_artifacts["q10_membership"])
    write_csv(output_dir / "boundary_q20_membership.csv", boundary_artifacts["q20_membership"])
    write_csv(output_dir / "boundary_q30_membership.csv", boundary_artifacts["q30_membership"])
    write_csv(output_dir / "boundary_subset_overlap.csv", boundary_artifacts["overlap"])
    write_csv(output_dir / "boundary_consensus_membership.csv", boundary_artifacts["consensus"])
    write_csv(output_dir / "boundary_scaling_sensitivity.csv", boundary_artifacts["scaling"])
    return preflight


def phase6_binary_priority(
    *,
    candidate_indices: np.ndarray,
    probabilities: np.ndarray,
    pool_scaled: np.ndarray,
    queried_indices: Sequence[int],
) -> dict[str, Any]:
    """Return a deterministic full-pool order that preserves Phase 6's choice.

    Phase 6 first restricts uncertainty-repulsion to the top uncertainty
    shortlist (10%, minimum 25), and only defines the final product score
    there.  Phase 7 needs a total order to form a 20% gate and percentile
    ranks.  The preregistered completion keeps the exact Phase 6 shortlist and
    score order first; only the outside-shortlist tail is completed by the same
    full-pool uncertainty-times-repulsion ingredients.  Thus the first item is
    provably the exact Phase 6 champion choice.
    """

    candidate_indices = np.asarray(candidate_indices, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    require(len(candidate_indices) == len(probabilities), "Candidate/probability length mismatch")
    uncertainty = 1.0 - 2.0 * np.abs(probabilities - 0.5)
    shortlist_size = min(
        len(candidate_indices),
        max(
            p6.CLASSIFIER_MIN_SHORTLIST_SIZE,
            int(math.ceil(p6.CLASSIFIER_GATE_FRACTION * len(candidate_indices))),
        ),
    )
    shortlist_positions = np.lexsort((candidate_indices, -uncertainty))[:shortlist_size]
    queried_x = pool_scaled[np.asarray(queried_indices, dtype=int)]
    all_distances = distance.cdist(pool_scaled[candidate_indices], queried_x).min(axis=1)
    all_repulsion = 1.0 - np.exp(
        -(all_distances**2) / (2.0 * p6.CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12)
    )
    shortlist_uncertainty = uncertainty[shortlist_positions]
    shortlist_normalized = p6.normalize_scores(shortlist_uncertainty)
    shortlist_scores = shortlist_normalized * all_repulsion[shortlist_positions]
    shortlist_order_local = np.lexsort(
        (candidate_indices[shortlist_positions], -shortlist_scores)
    )
    ordered_shortlist_positions = shortlist_positions[shortlist_order_local]

    outside_mask = np.ones(len(candidate_indices), dtype=bool)
    outside_mask[shortlist_positions] = False
    outside_positions = np.flatnonzero(outside_mask)
    full_fallback_scores = p6.normalize_scores(uncertainty) * all_repulsion
    outside_order_local = np.lexsort(
        (candidate_indices[outside_positions], -full_fallback_scores[outside_positions])
    )
    ordered_outside_positions = outside_positions[outside_order_local]
    total_positions = np.concatenate([ordered_shortlist_positions, ordered_outside_positions])
    total_indices = candidate_indices[total_positions]
    require(len(np.unique(total_indices)) == len(candidate_indices), "Binary priority order is not a permutation")

    exact_choice, exact_metadata = p6.choose_binary_candidate(
        method=M1_BINARY,
        candidate_indices=candidate_indices,
        probabilities=probabilities,
        pool_scaled=pool_scaled,
        queried_indices=queried_indices,
    )
    require(int(total_indices[0]) == int(exact_choice), "Full-pool priority failed to preserve exact Phase 6 choice")
    percentile = np.empty(len(candidate_indices), dtype=float)
    if len(candidate_indices) == 1:
        percentile[total_positions] = 1.0
    else:
        percentile[total_positions] = 1.0 - np.arange(len(candidate_indices)) / (len(candidate_indices) - 1)
    shortlist_flag = np.zeros(len(candidate_indices), dtype=bool)
    shortlist_flag[shortlist_positions] = True
    phase6_scores = np.full(len(candidate_indices), np.nan)
    phase6_scores[shortlist_positions] = shortlist_normalized * all_repulsion[shortlist_positions]
    return {
        "candidate_indices": candidate_indices,
        "uncertainty": uncertainty,
        "distance_to_queried": all_distances,
        "repulsion": all_repulsion,
        "phase6_shortlist_flag": shortlist_flag,
        "phase6_shortlist_score": phase6_scores,
        "fallback_full_score": full_fallback_scores,
        "ordered_positions": total_positions,
        "ordered_indices": total_indices,
        "percentile_rank": percentile,
        "phase6_exact_choice": int(exact_choice),
        "phase6_exact_metadata": exact_metadata,
        "shortlist_size": int(shortlist_size),
    }


def deterministic_percentile_rank(
    candidate_indices: np.ndarray, scores: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    candidate_indices = np.asarray(candidate_indices, dtype=int)
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((candidate_indices, -scores))
    percentile = np.empty(len(scores), dtype=float)
    if len(scores) == 1:
        percentile[order] = 1.0
    else:
        percentile[order] = 1.0 - np.arange(len(scores)) / (len(scores) - 1)
    return percentile, order


def max_depth_straddle_scores(
    mu: np.ndarray, sigma: np.ndarray, threshold: float
) -> np.ndarray:
    return p6.STRADDLE_KAPPA * np.asarray(sigma, dtype=float) - np.abs(
        np.asarray(mu, dtype=float) - float(threshold)
    )


def choose_hybrid_candidate(
    *,
    method: str,
    candidate_indices: np.ndarray,
    binary_probabilities: np.ndarray,
    depth_mu: np.ndarray,
    depth_sigma: np.ndarray,
    threshold: float,
    pool_scaled: np.ndarray,
    queried_indices: Sequence[int],
) -> tuple[int, dict[str, Any]]:
    binary = phase6_binary_priority(
        candidate_indices=candidate_indices,
        probabilities=binary_probabilities,
        pool_scaled=pool_scaled,
        queried_indices=queried_indices,
    )
    depth_scores = max_depth_straddle_scores(depth_mu, depth_sigma, threshold)
    depth_percentile, depth_order = deterministic_percentile_rank(candidate_indices, depth_scores)
    if method == M3_GATE:
        gate_count = max(1, int(math.ceil(GATE_FRACTION * len(candidate_indices))))
        gate_positions = binary["ordered_positions"][:gate_count]
        gate_indices = candidate_indices[gate_positions]
        gate_scores = depth_scores[gate_positions]
        local_choice = p6.deterministic_argmax(gate_indices, gate_scores)
        chosen_position = int(gate_positions[local_choice])
        selected = int(candidate_indices[chosen_position])
        metadata = {
            "acquisition_definition": "preregistered_binary_gate20_then_exact_max_depth_straddle",
            "requested_gate_fraction": GATE_FRACTION,
            "gate_integer_rule": "ceil",
            "candidate_count": len(candidate_indices),
            "gate_count": gate_count,
            "effective_gate_fraction": gate_count / len(candidate_indices),
            "binary_phase6_shortlist_size": binary["shortlist_size"],
            "binary_priority_completion_preregistered": True,
            "binary_phase6_exact_choice_population_row_index": binary["phase6_exact_choice"],
            "selected_equals_binary_phase6_choice": selected == binary["phase6_exact_choice"],
            "selected_binary_priority_percentile": float(binary["percentile_rank"][chosen_position]),
            "selected_binary_probability": float(binary_probabilities[chosen_position]),
            "selected_binary_uncertainty": float(binary["uncertainty"][chosen_position]),
            "selected_depth_mu_um": float(depth_mu[chosen_position]),
            "selected_depth_sigma_latent_um": float(depth_sigma[chosen_position]),
            "selected_depth_straddle_score": float(depth_scores[chosen_position]),
            "selected_inside_phase6_binary_shortlist": bool(binary["phase6_shortlist_flag"][chosen_position]),
            "max_depth_threshold_um": float(threshold),
            "boundary_metric_consulted": False,
            "hidden_label_consulted": False,
            "hidden_max_depth_consulted": False,
        }
        return selected, metadata
    if method == M4_FUSION:
        fusion = RANK_BINARY_WEIGHT * binary["percentile_rank"] + RANK_DEPTH_WEIGHT * depth_percentile
        chosen_position = p6.deterministic_argmax(candidate_indices, fusion)
        selected = int(candidate_indices[chosen_position])
        metadata = {
            "acquisition_definition": "preregistered_equal_percentile_rank_fusion",
            "binary_weight": RANK_BINARY_WEIGHT,
            "max_depth_weight": RANK_DEPTH_WEIGHT,
            "candidate_count": len(candidate_indices),
            "binary_phase6_shortlist_size": binary["shortlist_size"],
            "binary_priority_completion_preregistered": True,
            "binary_phase6_exact_choice_population_row_index": binary["phase6_exact_choice"],
            "selected_equals_binary_phase6_choice": selected == binary["phase6_exact_choice"],
            "selected_binary_percentile_rank": float(binary["percentile_rank"][chosen_position]),
            "selected_depth_percentile_rank": float(depth_percentile[chosen_position]),
            "selected_fusion_score": float(fusion[chosen_position]),
            "selected_binary_probability": float(binary_probabilities[chosen_position]),
            "selected_depth_mu_um": float(depth_mu[chosen_position]),
            "selected_depth_sigma_latent_um": float(depth_sigma[chosen_position]),
            "selected_depth_straddle_score": float(depth_scores[chosen_position]),
            "selected_inside_phase6_binary_shortlist": bool(binary["phase6_shortlist_flag"][chosen_position]),
            "max_depth_threshold_um": float(threshold),
            "boundary_metric_consulted": False,
            "hidden_label_consulted": False,
            "hidden_max_depth_consulted": False,
        }
        return selected, metadata
    raise ValueError(f"Unknown Hybrid method: {method}")


def phase7_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    predictions: np.ndarray,
    flags: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    result = p6.classification_metrics(labels, probabilities, predictions)
    for key, flag in flags.items():
        mask = np.asarray(flag, dtype=bool)
        result[f"{key}_error"] = float(np.mean(predictions[mask] != labels[mask])) if mask.any() else math.nan
        result[f"{key}_count"] = int(mask.sum())
        result[f"{key}_keyhole_count"] = int(labels[mask].sum())
    return result


def query_row(
    *,
    spec: p6.RunSpec,
    method: str,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
    idx: int,
    query_order: int,
    selection_stage: str,
    metadata: Mapping[str, Any],
    nearest_prior_query_distance: float,
) -> dict[str, Any]:
    row = population.iloc[idx]
    b = boundary.iloc[idx]
    payload = {
        "benchmark_population": "primary_common",
        "run_id": spec.run_id,
        "repeat": spec.repeat,
        "fold": spec.fold,
        "method": method,
        "formulation": METHOD_FORMULATION[method],
        "query_order": query_order,
        "selection_stage": selection_stage,
        "population_row_index": idx,
        "experiment_name": row["experiment_name"],
        "partition": row["partition"],
        "P": float(row["P"]),
        "VX": float(row["VX"]),
        "LS": float(row["LS"]),
        "ST": float(row["ST"]),
        "revealed_has_keyhole": int(bool(row["has_keyhole"])),
        "revealed_max_depth_um": float(row["value__max_depth"]),
        "nearest_prior_query_distance_evaluation_only": nearest_prior_query_distance,
        "boundary_scores_consulted_before_selection": False,
        "hidden_label_consulted_before_selection": False,
        "hidden_max_depth_consulted_before_selection": False,
        "known_before_query": "P,VX,LS,ST",
        "revealed_by_query": "manual has_keyhole,max_depth",
        "acquisition_metadata_json": json.dumps(json_safe(dict(metadata)), sort_keys=True),
    }
    for metric in BOUNDARY_IDS:
        for q in PRIMARY_BOUNDARY_QUANTILES:
            payload[f"global_{metric}_q{q}_evaluation_only"] = bool(b[f"{metric}_q{q}"])
    for q in PRIMARY_BOUNDARY_QUANTILES:
        payload[f"global_consensus_q{q}_evaluation_only"] = bool(b[f"consensus_q{q}"])
    return payload


def arm_fingerprint(
    spec: p6.RunSpec,
    method: str,
    population: pd.DataFrame,
    final_budget: int,
) -> str:
    payload = {
        "phase6_commit": EXPECTED_PHASE6_COMMIT,
        "hf_revision": EXPECTED_HF_REVISION,
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "run_spec": asdict(spec),
        "method": method,
        "population_sha256": frame_sha256(
            population,
            ["experiment_name", "has_keyhole", "value__max_depth", *FEATURE_COLUMNS],
        ),
        "final_budget": final_budget,
        "gate_fraction": GATE_FRACTION,
        "rank_weights": [RANK_BINARY_WEIGHT, RANK_DEPTH_WEIGHT],
        "phase6_model_constants": {
            "straddle_kappa": p6.STRADDLE_KAPPA,
            "kernel_constant_bounds": p6.KERNEL_CONSTANT_BOUNDS,
            "kernel_length_bounds": p6.KERNEL_LENGTH_BOUNDS,
            "gpr_alpha_primary": p6.GPR_ALPHA_PRIMARY,
            "active_optimizer_restarts": p6.ACTIVE_OPTIMIZER_RESTARTS,
            "classifier_gate_fraction": p6.CLASSIFIER_GATE_FRACTION,
            "classifier_min_shortlist_size": p6.CLASSIFIER_MIN_SHORTLIST_SIZE,
            "classifier_repulsion_bandwidth": p6.CLASSIFIER_REPULSION_BANDWIDTH,
        },
    }
    return sha256_bytes(json.dumps(json_safe(payload), sort_keys=True).encode("utf-8"))


def checkpoint_path(checkpoint_root: Path, spec: p6.RunSpec, method: str) -> Path:
    return checkpoint_root / spec.run_id / f"{method}.pkl"


def run_method_arm(
    *,
    spec: p6.RunSpec,
    method: str,
    population: pd.DataFrame,
    boundary: pd.DataFrame,
    phase6_queries: pd.DataFrame,
    final_budget: int,
    checkpoint_root: Path,
    force: bool,
) -> dict[str, Any]:
    fingerprint = arm_fingerprint(spec, method, population, final_budget)
    checkpoint = checkpoint_path(checkpoint_root, spec, method)
    if checkpoint.is_file() and not force:
        cached = load_pickle(checkpoint)
        if cached.get("fingerprint") == fingerprint:
            return cached

    started = time.perf_counter()
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    depth = population["value__max_depth"].to_numpy(float)
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    scaler = StandardScaler().fit(x[train])
    pool_scaled = scaler.transform(x)
    flags = test_boundary_flags(spec, boundary)

    if method in PHASE6_SOURCE_METHOD:
        source_method = PHASE6_SOURCE_METHOD[method]
        fixed_sequence = phase6_query_sequence(phase6_queries, spec.run_id, source_method, final_budget)
        queried = fixed_sequence[:]
        generated_warm, _ = p6.warm_start_indices(spec, population, final_budget)
        effective_warm = len(generated_warm)
        require(queried[:effective_warm] == generated_warm, f"{spec.run_id}/{method}: reused warm start drift")
    else:
        generated_warm, _ = p6.warm_start_indices(spec, population, final_budget)
        queried = list(generated_warm)
        effective_warm = len(queried)
        fixed_sequence = []

    prediction_budgets = {
        budget for budget in PREDICTION_CHECKPOINTS if effective_warm <= budget <= final_budget
    } | {effective_warm, final_budget}
    query_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    warning_messages: list[str] = []
    fit_statuses: Counter[str] = Counter()
    binary_fit_seconds = 0.0
    depth_fit_seconds = 0.0
    acquisition_seconds = 0.0

    warm = queried[:effective_warm]
    for order, idx in enumerate(warm, start=1):
        prior = warm[: order - 1]
        nearest = (
            float(distance.cdist(pool_scaled[[idx]], pool_scaled[np.asarray(prior, dtype=int)]).min())
            if prior
            else math.nan
        )
        query_rows.append(
            query_row(
                spec=spec,
                method=method,
                population=population,
                boundary=boundary,
                idx=idx,
                query_order=order,
                selection_stage="exact_phase6_shared_warm_start",
                metadata={"phase6_reused": True, "shared_permutation_position": order - 1},
                nearest_prior_query_distance=nearest,
            )
        )

    for budget in range(effective_warm, final_budget + 1):
        current = np.asarray(queried[:budget], dtype=int)
        require(len(current) == budget, f"{spec.run_id}/{method}: query accounting drift at {budget}")
        primary_is_binary = method not in {M0_DEPTH, M2_DEPTH}
        needs_binary = primary_is_binary
        needs_depth = method in {M0_DEPTH, M2_DEPTH, M3_GATE, M4_FUSION}
        binary_fit = None
        depth_fit = None
        threshold = None
        binary_probability_test = None
        depth_probability_test = None
        depth_mu_test = None
        depth_sigma_test = None

        if needs_binary:
            fit_started = time.perf_counter()
            binary_seed_method = (
                PHASE6_SOURCE_METHOD[method]
                if method in PHASE6_SOURCE_METHOD
                else M1_BINARY
            )
            binary_fit = p6.fit_gpc(
                x[current],
                labels[current],
                scaler=scaler,
                seed=p6.stable_seed(spec.run_seed, binary_seed_method, budget),
                kernel_kind="matern32",
            )
            elapsed = time.perf_counter() - fit_started
            binary_fit_seconds += elapsed
            binary_probability_test = p6.predict_gpc(binary_fit, x[test])
            fit_statuses[f"binary::{binary_fit.fit_status}"] += 1
            warning_messages.extend(binary_fit.warnings)
            diagnostic_rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "budget": budget,
                    "head": "binary_primary",
                    "fit_status": binary_fit.fit_status,
                    "kernel": binary_fit.kernel,
                    "kernel_constant": binary_fit.constant_value,
                    "kernel_length_scale": binary_fit.length_scale,
                    "kernel_bound_hit": binary_fit.bound_hit,
                    "warning_count": len(binary_fit.warnings),
                    "warnings_json": json.dumps(binary_fit.warnings, ensure_ascii=False),
                    "fit_seconds": elapsed,
                    "phase6_surrogate_family_unchanged": True,
                }
            )

        if needs_depth:
            threshold = p6.choose_higher_threshold(depth[current], labels[current])
            fit_started = time.perf_counter()
            depth_seed_method = (
                PHASE6_SOURCE_METHOD[method]
                if method in PHASE6_SOURCE_METHOD
                else M2_DEPTH
            )
            depth_fit = p6.fit_gpr(
                x[current],
                depth[current],
                scaler=scaler,
                seed=p6.stable_seed(spec.run_seed, depth_seed_method, budget),
                kernel_kind="matern32",
            )
            elapsed = time.perf_counter() - fit_started
            depth_fit_seconds += elapsed
            depth_mu_test, depth_sigma_test = p6.predict_gpr(depth_fit, x[test])
            depth_probability_test = p6.continuous_probability(
                depth_mu_test, depth_sigma_test, float(threshold["threshold"])
            )
            fit_statuses[f"depth::{depth_fit.fit_status}"] += 1
            warning_messages.extend(depth_fit.warnings)
            diagnostic_rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "budget": budget,
                    "head": "max_depth_auxiliary" if method in HYBRID_METHODS else "max_depth_primary",
                    "fit_status": depth_fit.fit_status,
                    "kernel": depth_fit.kernel,
                    "kernel_constant": depth_fit.constant_value,
                    "kernel_length_scale": depth_fit.length_scale,
                    "kernel_bound_hit": depth_fit.bound_hit,
                    "warning_count": len(depth_fit.warnings),
                    "warnings_json": json.dumps(depth_fit.warnings, ensure_ascii=False),
                    "fit_seconds": elapsed,
                    "phase6_surrogate_family_unchanged": True,
                }
            )
            threshold_rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "budget": budget,
                    **threshold,
                    "threshold_units": "um",
                    "training_scope": "currently_queried_only",
                    "direction_fixed_higher_is_keyhole_like": True,
                    "test_information_used": False,
                    "unqueried_pool_information_used": False,
                    "hybrid_threshold_is_auxiliary": method in HYBRID_METHODS,
                }
            )

        if primary_is_binary:
            require(binary_probability_test is not None, "Binary primary probability missing")
            probability = binary_probability_test
            predicted = (probability >= 0.5).astype(int)
        else:
            require(depth_probability_test is not None and depth_mu_test is not None and threshold is not None, "Depth primary output missing")
            probability = depth_probability_test
            predicted = (depth_mu_test > float(threshold["threshold"])).astype(int)

        metrics = phase7_metrics(labels[test], probability, predicted, flags)
        metrics.update(
            {
                "benchmark_population": "primary_common",
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "method": method,
                "formulation": METHOD_FORMULATION[method],
                "budget": budget,
                "effective_warm_start": effective_warm,
                "final_primary_predictor": "Binary GPC" if primary_is_binary else "Max-Depth GPR plus queried-only tau",
                "max_depth_role": "auxiliary_acquisition_only" if method in HYBRID_METHODS else "primary" if not primary_is_binary else "not_used",
                "binary_fit_status": binary_fit.fit_status if binary_fit is not None else "NA",
                "depth_fit_status": depth_fit.fit_status if depth_fit is not None else "NA",
                "threshold_um": float(threshold["threshold"]) if threshold is not None else math.nan,
                "boundary_metrics_used_for_acquisition": False,
                "test_information_used_for_acquisition": False,
            }
        )
        if depth_mu_test is not None:
            metrics.update({f"depth_{k}": v for k, v in p6.regression_metrics(depth[test], depth_mu_test).items()})
        curve_rows.append(metrics)

        if budget in prediction_budgets:
            for local, idx in enumerate(test):
                row = {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "method": method,
                    "formulation": METHOD_FORMULATION[method],
                    "budget": budget,
                    "experiment_name": population.iloc[idx]["experiment_name"],
                    "partition": population.iloc[idx]["partition"],
                    "has_keyhole": int(labels[idx]),
                    "keyhole_probability": float(probability[local]),
                    "predicted_keyhole": int(predicted[local]),
                    "primary_predictor": "Binary GPC" if primary_is_binary else "Max-Depth GPR plus tau",
                    "aux_max_depth_probability": float(depth_probability_test[local]) if method in HYBRID_METHODS else math.nan,
                    "aux_predicted_max_depth_um": float(depth_mu_test[local]) if method in HYBRID_METHODS else math.nan,
                    "aux_latent_std_um": float(depth_sigma_test[local]) if method in HYBRID_METHODS else math.nan,
                    "aux_threshold_um": float(threshold["threshold"]) if method in HYBRID_METHODS and threshold is not None else math.nan,
                }
                for key, flag in flags.items():
                    row[f"test_{key}"] = bool(flag[local])
                prediction_rows.append(row)

        if budget >= final_budget:
            break

        if method in PHASE6_SOURCE_METHOD:
            next_idx = int(fixed_sequence[budget])
            source_rows = phase6_queries[
                phase6_queries["benchmark_population"].eq("primary_common")
                & phase6_queries["run_id"].eq(spec.run_id)
                & phase6_queries["method"].eq(PHASE6_SOURCE_METHOD[method])
                & pd.to_numeric(phase6_queries["query_order"], errors="coerce").eq(budget + 1)
            ]
            require(len(source_rows) == 1, f"{spec.run_id}/{method}: missing saved acquisition row")
            source_metadata = json.loads(source_rows["acquisition_metadata_json"].iloc[0])
            metadata = {
                "acquisition_definition": "exact_published_phase6_trajectory_reuse",
                "phase6_source_method": PHASE6_SOURCE_METHOD[method],
                "phase6_metadata": source_metadata,
                "boundary_metric_consulted": False,
                "hidden_label_consulted": False,
                "hidden_max_depth_consulted": False,
            }
            selection_stage = "exact_phase6_baseline_trajectory_reuse"
        else:
            unqueried = np.asarray([idx for idx in train if idx not in set(current)], dtype=int)
            require(len(unqueried) > 0, f"{spec.run_id}/{method}: candidate pool exhausted")
            require(binary_fit is not None and depth_fit is not None and threshold is not None, "Hybrid heads missing")
            acquisition_started = time.perf_counter()
            binary_pool = p6.predict_gpc(binary_fit, x[unqueried])
            depth_mu_pool, depth_sigma_pool = p6.predict_gpr(depth_fit, x[unqueried])
            next_idx, metadata = choose_hybrid_candidate(
                method=method,
                candidate_indices=unqueried,
                binary_probabilities=binary_pool,
                depth_mu=depth_mu_pool,
                depth_sigma=depth_sigma_pool,
                threshold=float(threshold["threshold"]),
                pool_scaled=pool_scaled,
                queried_indices=current,
            )
            acquisition_seconds += time.perf_counter() - acquisition_started
            queried.append(next_idx)
            selection_stage = "preregistered_hybrid_acquisition"

        require(next_idx in set(train), "Selected row outside outer training pool")
        require(next_idx not in set(test), "Selected untouched test row")
        require(next_idx not in set(current), "Selected already queried row")
        prior = list(current)
        nearest = float(distance.cdist(pool_scaled[[next_idx]], pool_scaled[np.asarray(prior, dtype=int)]).min())
        query_rows.append(
            query_row(
                spec=spec,
                method=method,
                population=population,
                boundary=boundary,
                idx=next_idx,
                query_order=budget + 1,
                selection_stage=selection_stage,
                metadata=metadata,
                nearest_prior_query_distance=nearest,
            )
        )

    query_frame = pd.DataFrame(query_rows).sort_values("query_order").reset_index(drop=True)
    require(len(query_frame) == final_budget, f"{spec.run_id}/{method}: expected {final_budget} query rows")
    require(query_frame["query_order"].tolist() == list(range(1, final_budget + 1)), "Query order gap")
    query_hash = frame_sha256(query_frame, ["query_order", "experiment_name"])
    warm_hash = frame_sha256(
        query_frame[query_frame["query_order"].le(effective_warm)],
        ["query_order", "experiment_name"],
    )
    split_hash = sha256_bytes(
        json.dumps({"train": sorted(spec.train_indices), "test": sorted(spec.test_indices)}).encode("utf-8")
    )
    runtime = time.perf_counter() - started
    manifest = pd.DataFrame(
        [
            {
                "benchmark_population": "primary_common",
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "method": method,
                "formulation": METHOD_FORMULATION[method],
                "source_status": "exact_phase6_trajectory_replay" if method in PHASE6_SOURCE_METHOD else "new_preregistered_phase7_hybrid",
                "train_pool_count": len(train),
                "untouched_test_count": len(test),
                "nominal_warm_start": p6.NOMINAL_WARM_START,
                "effective_warm_start": effective_warm,
                "final_budget": final_budget,
                "fit_count": int(sum(fit_statuses.values())),
                "fit_status_counts_json": json.dumps(dict(fit_statuses), sort_keys=True),
                "optimizer_warning_count": len(warning_messages),
                "unique_optimizer_warning_count": len(set(warning_messages)),
                "binary_fit_seconds": binary_fit_seconds,
                "max_depth_fit_seconds": depth_fit_seconds,
                "acquisition_score_seconds": acquisition_seconds,
                "runtime_seconds": runtime,
                "mean_seconds_per_post_warm_query": runtime / max(final_budget - effective_warm, 1),
                "query_trajectory_sha256": query_hash,
                "warm_start_sha256": warm_hash,
                "split_sha256": split_hash,
                "checkpoint_fingerprint": fingerprint,
                "primary_predictor_is_binary_gpc": method in HYBRID_METHODS,
                "max_depth_is_acquisition_only": method in HYBRID_METHODS,
            }
        ]
    )
    fairness = pd.DataFrame(
        [
            {
                "run_id": spec.run_id,
                "method": method,
                "split_sha256": split_hash,
                "warm_start_sha256": warm_hash,
                "candidate_pool_is_exact_phase6_outer_training_only": True,
                "test_set_never_queried": not query_frame["population_row_index"].isin(test).any(),
                "test_labels_used_for_fitting_or_acquisition": False,
                "test_outputs_used_for_acquisition": False,
                "hidden_pool_labels_used_for_acquisition": False,
                "hidden_pool_max_depth_used_for_acquisition": False,
                "boundary_metrics_used_for_acquisition": False,
                "common_simulator_query_budget": final_budget,
                "extra_warm_start_queries_counted": True,
                "hybrid_primary_predictor_is_binary_gpc": method in HYBRID_METHODS,
                "max_depth_role_is_auxiliary_only": method in HYBRID_METHODS,
                "gate_fraction_fixed_0_20": method != M3_GATE or GATE_FRACTION == 0.20,
                "rank_weights_fixed_0_5_0_5": method != M4_FUSION or (RANK_BINARY_WEIGHT == RANK_DEPTH_WEIGHT == 0.5),
            }
        ]
    )
    result = {
        "fingerprint": fingerprint,
        "manifest": manifest,
        "queries": query_frame,
        "curves": pd.DataFrame(curve_rows),
        "predictions": pd.DataFrame(prediction_rows),
        "thresholds": pd.DataFrame(threshold_rows),
        "diagnostics": pd.DataFrame(diagnostic_rows),
        "fairness": fairness,
    }
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    atomic_pickle(checkpoint, result)
    return result


def run_outer_methods(
    spec: p6.RunSpec,
    methods: Sequence[str],
    population: pd.DataFrame,
    boundary: pd.DataFrame,
    phase6_queries: pd.DataFrame,
    final_budget: int,
    checkpoint_root: Path,
    force: bool,
) -> list[dict[str, Any]]:
    return [
        run_method_arm(
            spec=spec,
            method=method,
            population=population,
            boundary=boundary,
            phase6_queries=phase6_queries,
            final_budget=final_budget,
            checkpoint_root=checkpoint_root,
            force=force,
        )
        for method in methods
    ]


def concat_results(results: Sequence[dict[str, Any]], key: str) -> pd.DataFrame:
    frames = [result[key] for result in results if key in result and not result[key].empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def phase7_method_definitions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "method_id": "M0_binary_head",
                "method": M0_BINARY,
                "query_trajectory": "exact Phase 6 shared random trajectory",
                "primary_predictor": "Binary GPC",
                "max_depth_role": "not used",
                "new_phase7_acquisition": False,
                "preregistered": True,
            },
            {
                "method_id": "M0_max_depth_head",
                "method": M0_DEPTH,
                "query_trajectory": "same exact Phase 6 shared random trajectory",
                "primary_predictor": "Max-Depth GPR plus queried-only tau",
                "max_depth_role": "primary formulation",
                "new_phase7_acquisition": False,
                "preregistered": True,
            },
            {
                "method_id": "M1",
                "method": M1_BINARY,
                "query_trajectory": "exact Phase 6 champion trajectory",
                "primary_predictor": "Binary GPC",
                "max_depth_role": "not used",
                "new_phase7_acquisition": False,
                "preregistered": True,
            },
            {
                "method_id": "M2",
                "method": M2_DEPTH,
                "query_trajectory": "exact Phase 6 champion trajectory",
                "primary_predictor": "Max-Depth GPR plus queried-only tau",
                "max_depth_role": "primary formulation",
                "new_phase7_acquisition": False,
                "preregistered": True,
            },
            {
                "method_id": "M3",
                "method": M3_GATE,
                "query_trajectory": "top-20% Binary Phase-6-faithful priority, then Max-Depth straddle",
                "primary_predictor": "Binary GPC",
                "max_depth_role": "auxiliary acquisition only",
                "new_phase7_acquisition": True,
                "gate_fraction": GATE_FRACTION,
                "rank_weights": "NA",
                "preregistered": True,
            },
            {
                "method_id": "M4",
                "method": M4_FUSION,
                "query_trajectory": "equal deterministic percentile ranks of Binary priority and Max-Depth straddle",
                "primary_predictor": "Binary GPC",
                "max_depth_role": "auxiliary acquisition only",
                "new_phase7_acquisition": True,
                "gate_fraction": math.nan,
                "rank_weights": "0.5 Binary + 0.5 Max-Depth",
                "preregistered": True,
            },
        ]
    )


def run_phase6_reproduction_check(
    *,
    output_dir: Path,
    spec: p6.RunSpec,
    population: pd.DataFrame,
    phase6_boundary: pd.DataFrame,
    tables: Mapping[str, pd.DataFrame],
    force: bool,
) -> pd.DataFrame:
    checkpoint_root = output_dir / "reproduction_checkpoints"
    rows: list[dict[str, Any]] = []
    for method in [M1_BINARY, M2_DEPTH]:
        result = p6.run_active_arm(
            spec=spec,
            method=method,
            population=population,
            boundary=phase6_boundary,
            final_budget=30,
            checkpoint_root=checkpoint_root,
            threshold_bootstrap_resamples=100,
            force=force,
        )
        saved_queries = tables["queries"][
            tables["queries"]["benchmark_population"].eq("primary_common")
            & tables["queries"]["run_id"].eq(spec.run_id)
            & tables["queries"]["method"].eq(method)
            & pd.to_numeric(tables["queries"]["query_order"], errors="coerce").le(30)
        ].copy()
        saved_queries["query_order"] = pd.to_numeric(saved_queries["query_order"], errors="raise").astype(int)
        saved_queries = saved_queries.sort_values("query_order")
        reproduced_queries = result["queries"].sort_values("query_order")
        query_match = saved_queries["population_row_index"].astype(int).tolist() == reproduced_queries["population_row_index"].astype(int).tolist()
        rows.append(
            {
                "run_id": spec.run_id,
                "method": method,
                "check": "query_sequence_through_budget_30",
                "row_count": len(reproduced_queries),
                "maximum_absolute_difference": 0.0 if query_match else math.inf,
                "status": "PASS" if query_match else "FAIL",
                "tolerance": 0.0,
            }
        )

        saved_curves = tables["curves"][
            tables["curves"]["benchmark_population"].eq("primary_common")
            & tables["curves"]["run_id"].eq(spec.run_id)
            & tables["curves"]["method"].eq(method)
            & pd.to_numeric(tables["curves"]["budget"], errors="coerce").le(30)
        ].copy()
        reproduced_curves = result["curves"].copy()
        curve_columns = ["balanced_accuracy", "q20_error", "q30_error", "global_error", "brier_score"]
        merged = saved_curves[["budget", *curve_columns]].merge(
            reproduced_curves[["budget", *curve_columns]], on="budget", suffixes=("_saved", "_reproduced"), validate="one_to_one"
        )
        for column in curve_columns:
            diff = np.nanmax(
                np.abs(
                    pd.to_numeric(merged[f"{column}_saved"], errors="coerce").to_numpy(float)
                    - pd.to_numeric(merged[f"{column}_reproduced"], errors="coerce").to_numpy(float)
                )
            )
            rows.append(
                {
                    "run_id": spec.run_id,
                    "method": method,
                    "check": f"curve_{column}",
                    "row_count": len(merged),
                    "maximum_absolute_difference": float(diff),
                    "status": "PASS" if diff <= 1e-12 else "FAIL",
                    "tolerance": 1e-12,
                }
            )

        saved_predictions = tables["predictions"][
            tables["predictions"]["benchmark_population"].eq("primary_common")
            & tables["predictions"]["run_id"].eq(spec.run_id)
            & tables["predictions"]["method"].eq(method)
            & pd.to_numeric(tables["predictions"]["budget"], errors="coerce").le(30)
        ].copy()
        reproduced_predictions = result["predictions"].copy()
        prediction_columns = ["keyhole_probability", "predicted_response", "latent_std", "threshold"]
        pred_merged = saved_predictions[["budget", "experiment_name", "predicted_keyhole", *prediction_columns]].merge(
            reproduced_predictions[["budget", "experiment_name", "predicted_keyhole", *prediction_columns]],
            on=["budget", "experiment_name"],
            suffixes=("_saved", "_reproduced"),
            validate="one_to_one",
        )
        label_match = (
            pd.to_numeric(pred_merged["predicted_keyhole_saved"], errors="raise").astype(int)
            == pd.to_numeric(pred_merged["predicted_keyhole_reproduced"], errors="raise").astype(int)
        ).all()
        rows.append(
            {
                "run_id": spec.run_id,
                "method": method,
                "check": "checkpoint_predicted_labels",
                "row_count": len(pred_merged),
                "maximum_absolute_difference": 0.0 if label_match else 1.0,
                "status": "PASS" if label_match else "FAIL",
                "tolerance": 0.0,
            }
        )
        for column in prediction_columns:
            saved = pd.to_numeric(pred_merged[f"{column}_saved"], errors="coerce").to_numpy(float)
            reproduced = pd.to_numeric(pred_merged[f"{column}_reproduced"], errors="coerce").to_numpy(float)
            finite = np.isfinite(saved) & np.isfinite(reproduced)
            diff = float(np.max(np.abs(saved[finite] - reproduced[finite]))) if finite.any() else 0.0
            same_nan = np.array_equal(np.isnan(saved), np.isnan(reproduced))
            status = diff <= 1e-10 and same_nan
            rows.append(
                {
                    "run_id": spec.run_id,
                    "method": method,
                    "check": f"checkpoint_{column}",
                    "row_count": len(pred_merged),
                    "maximum_absolute_difference": diff,
                    "status": "PASS" if status else "FAIL",
                    "tolerance": 1e-10,
                }
            )

        if method == M2_DEPTH:
            saved_thresholds = tables["thresholds"][
                tables["thresholds"]["benchmark_population"].eq("primary_common")
                & tables["thresholds"]["run_id"].eq(spec.run_id)
                & tables["thresholds"]["method"].eq(method)
                & pd.to_numeric(tables["thresholds"]["budget"], errors="coerce").le(30)
            ][["budget", "threshold"]]
            reproduced_thresholds = result["thresholds"][["budget", "threshold"]]
            threshold_merged = saved_thresholds.merge(reproduced_thresholds, on="budget", suffixes=("_saved", "_reproduced"), validate="one_to_one")
            diff = float(
                np.max(
                    np.abs(
                        pd.to_numeric(threshold_merged["threshold_saved"]).to_numpy(float)
                        - pd.to_numeric(threshold_merged["threshold_reproduced"]).to_numpy(float)
                    )
                )
            )
            rows.append(
                {
                    "run_id": spec.run_id,
                    "method": method,
                    "check": "online_threshold_trajectory",
                    "row_count": len(threshold_merged),
                    "maximum_absolute_difference": diff,
                    "status": "PASS" if diff <= 1e-12 else "FAIL",
                    "tolerance": 1e-12,
                }
            )
    result_frame = pd.DataFrame(rows)
    require(result_frame["status"].eq("PASS").all(), "Phase 6 reproduction check failed")
    write_csv(output_dir / "phase6_reproduction_check.csv", result_frame)
    return result_frame


def prepare_phase7(output_dir: Path, *, force_reproduction: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prereg = ensure_preregistration()
    tables = read_phase6_tables()
    specs = specs_from_phase6_manifest(tables["population"], tables["split_manifest"])
    run_reuse = build_phase6_run_reuse_audit(tables["population"], specs, tables)
    boundary_artifacts = build_boundary_metrics(tables["population"])
    preflight = write_preflight_artifacts(
        output_dir, tables, specs, run_reuse, boundary_artifacts
    )
    write_csv(output_dir / "phase7_method_definitions.csv", phase7_method_definitions())
    reproduction = run_phase6_reproduction_check(
        output_dir=output_dir,
        spec=specs[0],
        population=tables["population"],
        phase6_boundary=tables["boundary"],
        tables=tables,
        force=force_reproduction,
    )
    append_execution_history(
        output_dir,
        "prepare_and_reproduction",
        "PASS",
        phase6_commit=EXPECTED_PHASE6_COMMIT,
        hf_revision=EXPECTED_HF_REVISION,
        population_count=len(tables["population"]),
        outer_run_count=len(specs),
        reproduction_checks=len(reproduction),
        preregistration_sha256=sha256_file(PREREG_PATH),
    )
    return {
        "preregistration": prereg,
        "tables": tables,
        "population": tables["population"],
        "specs": specs,
        "run_reuse": run_reuse,
        "boundary_artifacts": boundary_artifacts,
        "boundary": boundary_artifacts["reference"],
        "preflight": preflight,
        "reproduction": reproduction,
    }


def analysis_metric_columns() -> list[str]:
    columns = [
        f"{metric}_q{q}_error"
        for metric in BOUNDARY_IDS
        for q in PRIMARY_BOUNDARY_QUANTILES
    ]
    columns.extend(["consensus_q20_error", "consensus_q30_error", "balanced_accuracy"])
    return columns


def summarize_learning(
    curves: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    final_budget: int,
) -> dict[str, pd.DataFrame]:
    common_start = int(pd.to_numeric(manifest["effective_warm_start"], errors="raise").max())
    metrics = analysis_metric_columns()
    aulc_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    tolerance_rows: list[dict[str, Any]] = []
    long_rows: list[dict[str, Any]] = []
    error_targets = [0.30, 0.25, 0.20]
    ba_targets = [0.80, 0.85, 0.90]

    for (run_id, method), group in curves.groupby(["run_id", "method"], sort=True):
        group = group.sort_values("budget").copy()
        group["budget"] = pd.to_numeric(group["budget"], errors="raise").astype(int)
        available_start = int(group["budget"].min())
        require(
            group["budget"].tolist() == list(range(available_start, final_budget + 1)),
            f"{run_id}/{method}: learning curve is not integer-complete",
        )
        common = group[group["budget"].ge(common_start)]
        require(common["budget"].tolist() == list(range(common_start, final_budget + 1)), f"{run_id}/{method}: common AULC grid drift")
        row: dict[str, Any] = {
            "benchmark_population": "primary_common",
            "run_id": run_id,
            "method": method,
            "formulation": group["formulation"].iloc[0],
            "available_start_budget": available_start,
            "common_start_budget": common_start,
            "final_budget": final_budget,
            "integer_budget_grid_complete": True,
        }
        for metric in metrics:
            values = pd.to_numeric(common[metric], errors="raise").to_numpy(float)
            budgets = common["budget"].to_numpy(float)
            row[f"common_normalized_aulc__{metric}"] = float(
                np.trapezoid(values, budgets) / max(final_budget - common_start, 1)
            )
            for budget, value in zip(group["budget"], pd.to_numeric(group[metric], errors="raise")):
                long_rows.append(
                    {
                        "run_id": run_id,
                        "method": method,
                        "budget": int(budget),
                        "metric": metric,
                        "value": float(value),
                        "direction": "higher_is_better" if metric == "balanced_accuracy" else "lower_is_better",
                        "boundary_definition": metric.split("_")[0] if metric.startswith("B") else "consensus" if metric.startswith("consensus") else "global",
                    }
                )
        aulc_rows.append(row)
        final = group[group["budget"].eq(final_budget)]
        require(len(final) == 1, f"{run_id}/{method}: missing final budget")
        final_rows.append(final.iloc[0].to_dict())

        tolerance_specs: list[tuple[str, float, str]] = []
        for metric in [f"{boundary}_q{q}_error" for boundary in BOUNDARY_IDS for q in PRIMARY_BOUNDARY_QUANTILES]:
            tolerance_specs.extend((metric, target, "at_most") for target in error_targets)
        tolerance_specs.extend(("balanced_accuracy", target, "at_least") for target in ba_targets)
        for metric, target, direction in tolerance_specs:
            eligible = group[metric].ge(target) if direction == "at_least" else group[metric].le(target)
            reached = group[eligible]
            tolerance_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "metric": metric,
                    "target": target,
                    "direction": direction,
                    "queries_required": int(reached["budget"].iloc[0]) if len(reached) else math.nan,
                    "status": "reached" if len(reached) else "not_reached",
                    "no_extrapolation": True,
                }
            )

    return {
        "aulc": pd.DataFrame(aulc_rows),
        "final": pd.DataFrame(final_rows),
        "tolerance": pd.DataFrame(tolerance_rows),
        "long_curves": pd.DataFrame(long_rows),
    }


def paired_method_comparisons(
    aulc: pd.DataFrame,
    *,
    resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    comparisons = [
        ("hybrid_gate_minus_binary", M3_GATE, M1_BINARY),
        ("hybrid_fusion_minus_binary", M4_FUSION, M1_BINARY),
        ("hybrid_gate_minus_max_depth", M3_GATE, M2_DEPTH),
        ("hybrid_fusion_minus_max_depth", M4_FUSION, M2_DEPTH),
        ("binary_minus_shared_random", M1_BINARY, M0_BINARY),
        ("max_depth_minus_shared_random", M2_DEPTH, M0_DEPTH),
        ("hybrid_gate_minus_shared_random", M3_GATE, M0_BINARY),
        ("hybrid_fusion_minus_shared_random", M4_FUSION, M0_BINARY),
        ("max_depth_minus_binary", M2_DEPTH, M1_BINARY),
    ]
    metrics = [f"common_normalized_aulc__{metric}" for metric in analysis_metric_columns()]
    rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    for comparison, method_a, method_b in comparisons:
        a = aulc[aulc["method"].eq(method_a)].set_index("run_id")
        b = aulc[aulc["method"].eq(method_b)].set_index("run_id")
        common = sorted(set(a.index) & set(b.index))
        if not common:
            continue
        for metric in metrics:
            differences = (
                pd.to_numeric(a.loc[common, metric], errors="raise").to_numpy(float)
                - pd.to_numeric(b.loc[common, metric], errors="raise").to_numpy(float)
            )
            row = {
                "comparison": comparison,
                "method_a": method_a,
                "method_b": method_b,
                "metric": metric,
                "paired_run_count": len(common),
                "mean_paired_difference_a_minus_b": float(np.mean(differences)),
                "median_paired_difference_a_minus_b": float(np.median(differences)),
                "uncertainty_interpretation": "paired_descriptive_repeated_CV_runs_not_independent",
                "formal_hypothesis_test": False,
            }
            rows.append(row)
            rng = p6.stable_rng(p6.BASE_SEED, "phase7", comparison, metric, "paired_bootstrap")
            samples = np.empty(resamples, dtype=float)
            for idx in range(resamples):
                draw = rng.integers(0, len(differences), len(differences))
                samples[idx] = float(np.mean(differences[draw]))
            low, median, high = np.quantile(samples, [0.025, 0.50, 0.975])
            bootstrap_rows.append(
                {
                    **row,
                    "bootstrap_resamples": resamples,
                    "bootstrap_ci_low": float(low),
                    "bootstrap_median": float(median),
                    "bootstrap_ci_high": float(high),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(bootstrap_rows)


def build_pareto_summary(aulc: pd.DataFrame) -> pd.DataFrame:
    methods = [method for method in PRIMARY_SCORECARD_METHODS if method in set(aulc["method"])]
    ba_column = "common_normalized_aulc__balanced_accuracy"
    rows: list[dict[str, Any]] = []
    means = aulc[aulc["method"].isin(methods)].groupby("method", as_index=True).mean(numeric_only=True)
    for boundary in BOUNDARY_IDS:
        for quantile in PRIMARY_BOUNDARY_QUANTILES:
            error_column = f"common_normalized_aulc__{boundary}_q{quantile}_error"
            for method in methods:
                x = float(means.loc[method, error_column])
                y = float(means.loc[method, ba_column])
                dominators: list[str] = []
                for other in methods:
                    if other == method:
                        continue
                    ox = float(means.loc[other, error_column])
                    oy = float(means.loc[other, ba_column])
                    if ox <= x + 1e-15 and oy >= y - 1e-15 and (ox < x - 1e-15 or oy > y + 1e-15):
                        dominators.append(other)
                rows.append(
                    {
                        "boundary_definition": boundary,
                        "quantile": quantile,
                        "method": method,
                        "mean_boundary_error_aulc": x,
                        "mean_balanced_accuracy_aulc": y,
                        "pareto_dominated": bool(dominators),
                        "dominated_by_json": json.dumps(sorted(dominators)),
                        "on_pareto_frontier": not dominators,
                        "arbitrary_weighted_score_used": False,
                    }
                )
    return pd.DataFrame(rows)


def mean_aulc(aulc: pd.DataFrame, method: str, metric: str) -> float:
    values = pd.to_numeric(aulc.loc[aulc["method"].eq(method), metric], errors="raise")
    require(len(values) > 0, f"Missing AULC rows for {method}/{metric}")
    return float(values.mean())


def bootstrap_row(
    bootstrap: pd.DataFrame, method_a: str, method_b: str, metric: str
) -> pd.Series:
    part = bootstrap[
        bootstrap["method_a"].eq(method_a)
        & bootstrap["method_b"].eq(method_b)
        & bootstrap["metric"].eq(metric)
    ]
    require(len(part) == 1, f"Missing paired bootstrap row: {method_a} vs {method_b}, {metric}")
    return part.iloc[0]


def evaluate_preregistered_decision(
    aulc: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    score_rows: list[dict[str, Any]] = []
    for method in PRIMARY_SCORECARD_METHODS:
        if method not in set(aulc["method"]):
            continue
        row: dict[str, Any] = {
            "method": method,
            "run_count": int(aulc["method"].eq(method).sum()),
            "primary_predictor": "Binary GPC" if method not in {M2_DEPTH} else "Max-Depth GPR plus tau",
        }
        for boundary in BOUNDARY_IDS:
            for q in PRIMARY_BOUNDARY_QUANTILES:
                metric = f"common_normalized_aulc__{boundary}_q{q}_error"
                row[f"mean_{boundary}_q{q}_aulc"] = mean_aulc(aulc, method, metric)
        row["mean_balanced_accuracy_aulc"] = mean_aulc(
            aulc, method, "common_normalized_aulc__balanced_accuracy"
        )
        score_rows.append(row)
    scorecard = pd.DataFrame(score_rows)

    hybrid_rule_rows: list[dict[str, Any]] = []
    hybrid_success: dict[str, bool] = {}
    for hybrid in HYBRID_METHODS:
        favourable_q20: list[str] = []
        ci_below_zero_q20: list[str] = []
        favourable_q30: list[str] = []
        random_favourable_q20: list[str] = []
        random_ci_q20: list[str] = []
        for boundary in BOUNDARY_IDS:
            q20_metric = f"common_normalized_aulc__{boundary}_q20_error"
            q30_metric = f"common_normalized_aulc__{boundary}_q30_error"
            if mean_aulc(aulc, hybrid, q20_metric) < mean_aulc(aulc, M1_BINARY, q20_metric):
                favourable_q20.append(boundary)
            if float(bootstrap_row(bootstrap, hybrid, M1_BINARY, q20_metric)["bootstrap_ci_high"]) < 0:
                ci_below_zero_q20.append(boundary)
            if mean_aulc(aulc, hybrid, q30_metric) < mean_aulc(aulc, M1_BINARY, q30_metric):
                favourable_q30.append(boundary)
            if mean_aulc(aulc, hybrid, q20_metric) < mean_aulc(aulc, M0_BINARY, q20_metric):
                random_favourable_q20.append(boundary)
            if float(bootstrap_row(bootstrap, hybrid, M0_BINARY, q20_metric)["bootstrap_ci_high"]) < 0:
                random_ci_q20.append(boundary)
        ba_hybrid = mean_aulc(aulc, hybrid, "common_normalized_aulc__balanced_accuracy")
        ba_binary = mean_aulc(aulc, M1_BINARY, "common_normalized_aulc__balanced_accuracy")
        condition_a = len(favourable_q20) >= 2 and len(ci_below_zero_q20) >= 2
        condition_b = len(favourable_q30) >= 2
        condition_c = ba_hybrid >= ba_binary - 0.01
        condition_d = len(random_favourable_q20) >= 2 and len(random_ci_q20) >= 1
        success = condition_a and condition_b and condition_c and condition_d
        hybrid_success[hybrid] = success
        hybrid_rule_rows.append(
            {
                "method": hybrid,
                "condition_A_q20": condition_a,
                "q20_favourable_mean_definitions_json": json.dumps(favourable_q20),
                "q20_ci_below_zero_definitions_json": json.dumps(ci_below_zero_q20),
                "condition_B_q30": condition_b,
                "q30_favourable_mean_definitions_json": json.dumps(favourable_q30),
                "condition_C_no_material_BA_sacrifice": condition_c,
                "hybrid_BA_aulc": ba_hybrid,
                "binary_BA_aulc": ba_binary,
                "BA_difference_hybrid_minus_binary": ba_hybrid - ba_binary,
                "condition_D_beats_shared_random": condition_d,
                "random_q20_favourable_mean_definitions_json": json.dumps(random_favourable_q20),
                "random_q20_ci_below_zero_definitions_json": json.dumps(random_ci_q20),
                "all_preregistered_conditions_met": success,
                "decision_rule_sha256": EXPECTED_PREREG_SHA256,
            }
        )
    rule_frame = pd.DataFrame(hybrid_rule_rows)

    if any(hybrid_success.values()):
        decision = "HYBRID ACQUISITION PRIMARY"
        reason = "At least one preregistered Hybrid satisfied all four robust-improvement conditions."
    else:
        max_q20_better_defs: list[str] = []
        max_q30_better_defs: list[str] = []
        max_q20_ci_defs: list[str] = []
        binary_q20_no_worse_defs: list[str] = []
        binary_q30_no_worse_max_defs: list[str] = []
        for boundary in BOUNDARY_IDS:
            q20 = f"common_normalized_aulc__{boundary}_q20_error"
            q30 = f"common_normalized_aulc__{boundary}_q30_error"
            max_q20 = mean_aulc(aulc, M2_DEPTH, q20)
            max_q30 = mean_aulc(aulc, M2_DEPTH, q30)
            binary_q20 = mean_aulc(aulc, M1_BINARY, q20)
            binary_q30 = mean_aulc(aulc, M1_BINARY, q30)
            hybrid_q20 = [mean_aulc(aulc, h, q20) for h in HYBRID_METHODS]
            hybrid_q30 = [mean_aulc(aulc, h, q30) for h in HYBRID_METHODS]
            if max_q20 < min([binary_q20, *hybrid_q20]):
                max_q20_better_defs.append(boundary)
            if max_q30 < min([binary_q30, *hybrid_q30]):
                max_q30_better_defs.append(boundary)
            if float(bootstrap_row(bootstrap, M2_DEPTH, M1_BINARY, q20)["bootstrap_ci_high"]) < 0:
                max_q20_ci_defs.append(boundary)
            if binary_q20 <= min([max_q20, *hybrid_q20]):
                binary_q20_no_worse_defs.append(boundary)
            if binary_q30 <= max_q30:
                binary_q30_no_worse_max_defs.append(boundary)
        max_ba = mean_aulc(aulc, M2_DEPTH, "common_normalized_aulc__balanced_accuracy")
        best_ba = max(
            mean_aulc(aulc, method, "common_normalized_aulc__balanced_accuracy")
            for method in [M1_BINARY, M2_DEPTH, *HYBRID_METHODS]
        )
        max_primary = (
            len(max_q20_better_defs) >= 2
            and len(max_q30_better_defs) >= 2
            and len(max_q20_ci_defs) >= 2
            and max_ba >= best_ba - 0.01
        )
        binary_primary = (
            len(binary_q20_no_worse_defs) >= 2
            and len(binary_q30_no_worse_max_defs) >= 2
        )
        if max_primary:
            decision = "MAX-DEPTH FORMULATION PRIMARY"
            reason = "Max-Depth met the preregistered multi-definition dominance branch after neither Hybrid passed."
        elif binary_primary:
            decision = "BINARY ACQUISITION PRIMARY"
            reason = "Neither Hybrid met the robust rule and Binary remained no worse on the preregistered boundary hierarchy under at least two definitions."
        else:
            decision = "NO ROBUST WINNER / METRIC-DEPENDENT"
            reason = "No Hybrid met the robust rule and neither Binary nor Max-Depth satisfied its preregistered multi-definition branch."

    decision_payload = {
        "decision": decision,
        "reason": reason,
        "preregistered_rule_applied_mechanically": True,
        "decision_rule_sha256": EXPECTED_PREREG_SHA256,
        "hybrid_success": hybrid_success,
        "manual_has_keyhole_remains_ground_truth": True,
        "maximum_depth_remains_physical_side_information": True,
        "causal_claim": False,
        "universal_physical_threshold_claim": False,
    }
    decision_frame = pd.DataFrame(
        [
            {
                **decision_payload,
                "hybrid_success_json": json.dumps(hybrid_success, sort_keys=True),
            }
        ]
    ).drop(columns=["hybrid_success"])
    return scorecard, rule_frame, decision_payload | {"frame": decision_frame}


def query_behaviour_tables(
    queries: pd.DataFrame,
    methods: Sequence[str],
    *,
    final_budget: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    behaviour_rows: list[dict[str, Any]] = []
    discovery_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    checkpoints = sorted(
        set([20, 30, 40, 50, 60, 70, final_budget])
    )
    for (run_id, method), group in queries.groupby(["run_id", "method"], sort=True):
        group = group.sort_values("query_order").copy()
        group["query_order"] = pd.to_numeric(group["query_order"], errors="raise").astype(int)
        require(group["query_order"].tolist() == list(range(1, final_budget + 1)), f"{run_id}/{method}: query behaviour sequence incomplete")
        for budget in range(1, final_budget + 1):
            part = group[group["query_order"].le(budget)]
            row: dict[str, Any] = {
                "run_id": run_id,
                "method": method,
                "budget": budget,
                "query_count": len(part),
                "keyhole_discovered": int(pd.to_numeric(part["revealed_has_keyhole"], errors="raise").sum()),
                "non_keyhole_discovered": int(len(part) - pd.to_numeric(part["revealed_has_keyhole"], errors="raise").sum()),
                "max_depth_min_um": float(pd.to_numeric(part["revealed_max_depth_um"], errors="raise").min()),
                "max_depth_max_um": float(pd.to_numeric(part["revealed_max_depth_um"], errors="raise").max()),
                "max_depth_range_um": float(pd.to_numeric(part["revealed_max_depth_um"], errors="raise").max() - pd.to_numeric(part["revealed_max_depth_um"], errors="raise").min()),
                "mean_nearest_prior_query_distance": float(pd.to_numeric(part["nearest_prior_query_distance_evaluation_only"], errors="coerce").mean()),
                "boundary_membership_joined_after_selection": True,
                "boundary_metrics_used_for_acquisition": False,
            }
            for boundary in BOUNDARY_IDS:
                for q in PRIMARY_BOUNDARY_QUANTILES:
                    column = f"global_{boundary}_q{q}_evaluation_only"
                    flag = strict_bool(part[column])
                    row[f"fraction_queries_{boundary}_q{q}"] = float(flag.mean())
            for q in PRIMARY_BOUNDARY_QUANTILES:
                flag = strict_bool(part[f"global_consensus_q{q}_evaluation_only"])
                row[f"fraction_queries_consensus_q{q}"] = float(flag.mean())
            behaviour_rows.append(row)
            discovery_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "budget": budget,
                    "keyhole_discovered": row["keyhole_discovered"],
                    "non_keyhole_discovered": row["non_keyhole_discovered"],
                    "keyhole_discovery_fraction_of_73": row["keyhole_discovered"] / 73.0,
                    "same_simulator_query_budget": True,
                }
            )

    for run_id, run_group in queries.groupby("run_id", sort=True):
        sequences = {
            method: run_group[run_group["method"].eq(method)]
            .sort_values("query_order")["population_row_index"]
            .astype(int)
            .tolist()
            for method in methods
            if method in set(run_group["method"])
        }
        for i, method_a in enumerate(sorted(sequences)):
            for method_b in sorted(sequences)[i + 1 :]:
                seq_a, seq_b = sequences[method_a], sequences[method_b]
                first_divergence = next(
                    (idx + 1 for idx, (a, b) in enumerate(zip(seq_a, seq_b)) if a != b),
                    math.nan,
                )
                for budget in checkpoints:
                    if budget > final_budget:
                        continue
                    a_set, b_set = set(seq_a[:budget]), set(seq_b[:budget])
                    overlap_rows.append(
                        {
                            "run_id": run_id,
                            "method_a": method_a,
                            "method_b": method_b,
                            "budget": budget,
                            "intersection_count": len(a_set & b_set),
                            "union_count": len(a_set | b_set),
                            "jaccard": len(a_set & b_set) / max(len(a_set | b_set), 1),
                            "first_query_order_sequence_diverges": first_divergence,
                            "same_warm_start": first_divergence > 12 if math.isfinite(first_divergence) else True,
                        }
                    )
    return pd.DataFrame(behaviour_rows), pd.DataFrame(discovery_rows), pd.DataFrame(overlap_rows)


def subgroup_and_partition_tables(
    predictions: pd.DataFrame,
    population: pd.DataFrame,
    *,
    final_budget: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metadata_columns = [
        "experiment_name",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
        "keyhole_timing_relative_to_T0",
        "keyhole_timing_group",
    ]
    available = [column for column in metadata_columns if column in population.columns]
    merged = predictions.merge(population[available], on="experiment_name", how="left", validate="many_to_one")
    for column in [
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
    ]:
        if column in merged.columns:
            merged[column] = strict_bool(merged[column].fillna(False))
    merged["has_keyhole"] = pd.to_numeric(merged["has_keyhole"], errors="raise").astype(int)
    merged["predicted_keyhole"] = pd.to_numeric(merged["predicted_keyhole"], errors="raise").astype(int)
    selected_budgets = sorted({20, 30, final_budget})
    selected = merged[pd.to_numeric(merged["budget"], errors="raise").isin(selected_budgets)].copy()
    transient_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    partition_rows: list[dict[str, Any]] = []

    subgroup_masks: dict[str, pd.Series] = {}
    if "keyhole_transient_by_sequence" in selected:
        subgroup_masks["transient_Keyhole"] = selected["keyhole_transient_by_sequence"]
    if "keyhole_persistent_to_last_physical_frame" in selected:
        subgroup_masks["persistent_Keyhole"] = selected["keyhole_persistent_to_last_physical_frame"]
    if "repeated_keyhole_episodes" in selected:
        subgroup_masks["repeated_Keyhole"] = selected["repeated_keyhole_episodes"]

    for (run_id, method, budget), group in selected.groupby(["run_id", "method", "budget"], sort=True):
        for subgroup, global_mask in subgroup_masks.items():
            mask = global_mask.loc[group.index].to_numpy(bool) & group["has_keyhole"].eq(1).to_numpy(bool)
            count = int(mask.sum())
            transient_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "budget": int(budget),
                    "subgroup": subgroup,
                    "positive_case_count": count,
                    "sensitivity": float(group.loc[mask, "predicted_keyhole"].mean()) if count else math.nan,
                    "false_negative_count": int((group.loc[mask, "predicted_keyhole"] == 0).sum()) if count else 0,
                    "descriptive_subgroup": True,
                }
            )
        timing_column = "keyhole_timing_group" if "keyhole_timing_group" in group else "keyhole_timing_relative_to_T0"
        if timing_column in group:
            for timing, part in group[group["has_keyhole"].eq(1)].groupby(timing_column, dropna=False):
                timing_rows.append(
                    {
                        "run_id": run_id,
                        "method": method,
                        "budget": int(budget),
                        "timing_group": str(timing),
                        "positive_case_count": len(part),
                        "sensitivity": float(part["predicted_keyhole"].mean()) if len(part) else math.nan,
                        "descriptive_subgroup": True,
                    }
                )
        for partition, part in group.groupby("partition", sort=True):
            labels = part["has_keyhole"].to_numpy(int)
            predicted = part["predicted_keyhole"].to_numpy(int)
            if len(np.unique(labels)) == 2:
                balanced = float(p6.balanced_accuracy_score(labels, predicted))
            else:
                balanced = math.nan
            positives = labels == 1
            negatives = labels == 0
            partition_rows.append(
                {
                    "run_id": run_id,
                    "method": method,
                    "budget": int(budget),
                    "partition": partition,
                    "row_count": len(part),
                    "keyhole_count": int(positives.sum()),
                    "non_keyhole_count": int(negatives.sum()),
                    "balanced_accuracy": balanced,
                    "sensitivity": float((predicted[positives] == 1).mean()) if positives.any() else math.nan,
                    "specificity": float((predicted[negatives] == 0).mean()) if negatives.any() else math.nan,
                    "global_error": float(np.mean(predicted != labels)),
                    "old_remote_small_positive_count_caveat": partition == "old-data-remote-clean",
                }
            )
    return pd.DataFrame(transient_rows), pd.DataFrame(timing_rows), pd.DataFrame(partition_rows)


def representative_and_failure_tables(
    aulc: pd.DataFrame,
    queries: pd.DataFrame,
    thresholds: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric = "common_normalized_aulc__B1_q20_error"
    gate = aulc[aulc["method"].eq(M3_GATE)].set_index("run_id")
    binary = aulc[aulc["method"].eq(M1_BINARY)].set_index("run_id")
    common = sorted(set(gate.index) & set(binary.index))
    differences = pd.Series(
        pd.to_numeric(gate.loc[common, metric], errors="raise").to_numpy(float)
        - pd.to_numeric(binary.loc[common, metric], errors="raise").to_numpy(float),
        index=common,
        name="gate_minus_binary_B1_q20_aulc",
    )
    median_value = float(differences.median())
    median_run = sorted(common, key=lambda run: (abs(float(differences.loc[run]) - median_value), run))[0]
    best_run = sorted(common, key=lambda run: (float(differences.loc[run]), run))[0]
    worst_run = sorted(common, key=lambda run: (-float(differences.loc[run]), run))[0]
    representative = pd.DataFrame(
        [
            {"selection": "median_gate_minus_binary_B1_q20", "run_id": median_run, "difference": float(differences.loc[median_run]), "algorithmic_selection": True},
            {"selection": "strongest_hybrid_improvement", "run_id": best_run, "difference": float(differences.loc[best_run]), "algorithmic_selection": True},
            {"selection": "strongest_hybrid_deterioration", "run_id": worst_run, "difference": float(differences.loc[worst_run]), "algorithmic_selection": True},
        ]
    )

    failure_rows: list[dict[str, Any]] = []
    for run_id in common:
        gate_queries = queries[queries["run_id"].eq(run_id) & queries["method"].eq(M3_GATE)].sort_values("query_order")
        active = gate_queries[gate_queries["selection_stage"].eq("preregistered_hybrid_acquisition")]
        metadata = [json.loads(value) for value in active["acquisition_metadata_json"]]
        disagreement = [not bool(item.get("selected_equals_binary_phase6_choice", False)) for item in metadata]
        in_shortlist = [bool(item.get("selected_inside_phase6_binary_shortlist", False)) for item in metadata]
        threshold_part = thresholds[
            thresholds["run_id"].eq(run_id)
            & thresholds["method"].eq(M3_GATE)
            & pd.to_numeric(thresholds["budget"], errors="coerce").le(30)
        ]
        at30 = gate_queries[pd.to_numeric(gate_queries["query_order"], errors="raise").le(30)]
        partition_counts = at30["partition"].value_counts().to_dict()
        failure_rows.append(
            {
                "run_id": run_id,
                "gate_minus_binary_B1_q20_aulc": float(differences.loc[run_id]),
                "hybrid_improved_B1_q20": float(differences.loc[run_id]) < 0,
                "early_threshold_std_um_through_30": float(pd.to_numeric(threshold_part["threshold"], errors="coerce").std(ddof=0)),
                "early_threshold_range_um_through_30": float(pd.to_numeric(threshold_part["threshold"], errors="coerce").max() - pd.to_numeric(threshold_part["threshold"], errors="coerce").min()),
                "fraction_hybrid_queries_different_from_binary_champion_candidate": float(np.mean(disagreement)) if disagreement else math.nan,
                "fraction_selected_inside_phase6_binary_shortlist": float(np.mean(in_shortlist)) if in_shortlist else math.nan,
                "keyhole_discovered_by_30": int(pd.to_numeric(at30["revealed_has_keyhole"], errors="raise").sum()),
                "mean_nearest_prior_query_distance_by_30": float(pd.to_numeric(at30["nearest_prior_query_distance_evaluation_only"], errors="coerce").mean()),
                "partition_counts_by_30_json": json.dumps(partition_counts, sort_keys=True),
                "diagnosis_is_post_hoc_only": True,
                "algorithm_modified_after_diagnosis": False,
            }
        )
    return representative, pd.DataFrame(failure_rows)


def runtime_comparison(manifest: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    summary = (
        manifest.groupby("method", as_index=False)
        .agg(
            run_count=("run_id", "count"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            median_runtime_seconds=("runtime_seconds", "median"),
            total_runtime_seconds=("runtime_seconds", "sum"),
            mean_binary_fit_seconds=("binary_fit_seconds", "mean"),
            mean_max_depth_fit_seconds=("max_depth_fit_seconds", "mean"),
            mean_acquisition_score_seconds=("acquisition_score_seconds", "mean"),
            mean_seconds_per_post_warm_query=("mean_seconds_per_post_warm_query", "mean"),
        )
    )
    lookup = summary.set_index("method")
    binary_runtime = float(lookup.loc[M1_BINARY, "mean_runtime_seconds"]) if M1_BINARY in lookup.index else math.nan
    max_runtime = float(lookup.loc[M2_DEPTH, "mean_runtime_seconds"]) if M2_DEPTH in lookup.index else math.nan
    summary["relative_overhead_vs_binary_champion"] = summary["mean_runtime_seconds"] / binary_runtime
    summary["relative_overhead_vs_max_depth_champion"] = summary["mean_runtime_seconds"] / max_runtime
    summary["simulator_query_cost_equal"] = True
    payload = {
        "total_method_run_runtime_seconds": float(manifest["runtime_seconds"].sum()),
        "method_run_count": len(manifest),
        "workers_reported_separately": True,
        "simulator_sample_efficiency_distinct_from_computational_efficiency": True,
        "mean_hybrid_gate_overhead_vs_binary": float(lookup.loc[M3_GATE, "mean_runtime_seconds"] / binary_runtime) if M3_GATE in lookup.index else math.nan,
        "mean_hybrid_fusion_overhead_vs_binary": float(lookup.loc[M4_FUSION, "mean_runtime_seconds"] / binary_runtime) if M4_FUSION in lookup.index else math.nan,
    }
    return summary, payload


def reconcile_phase6_baseline_replays(
    manifest: pd.DataFrame,
    curves: pd.DataFrame,
    tables: Mapping[str, pd.DataFrame],
    *,
    final_budget: int,
) -> pd.DataFrame:
    saved_manifest = tables["run_manifest"]
    saved_curves = tables["curves"]
    rows: list[dict[str, Any]] = []
    for method, source in PHASE6_SOURCE_METHOD.items():
        replay_manifest = manifest[manifest["method"].eq(method)]
        for _, replay in replay_manifest.iterrows():
            run_id = replay["run_id"]
            saved_m = saved_manifest[
                saved_manifest["benchmark_population"].eq("primary_common")
                & saved_manifest["run_id"].eq(run_id)
                & saved_manifest["method"].eq(source)
            ]
            require(len(saved_m) == 1, f"{run_id}/{source}: saved manifest row missing")
            if final_budget == FINAL_BUDGET:
                expected_query_hash = str(saved_m["query_trajectory_sha256"].iloc[0])
            else:
                saved_prefix = tables["queries"][
                    tables["queries"]["benchmark_population"].eq("primary_common")
                    & tables["queries"]["run_id"].eq(run_id)
                    & tables["queries"]["method"].eq(source)
                    & pd.to_numeric(tables["queries"]["query_order"], errors="coerce").le(final_budget)
                ].copy()
                saved_prefix["query_order"] = pd.to_numeric(saved_prefix["query_order"], errors="raise").astype(int)
                saved_prefix = saved_prefix.sort_values("query_order")
                expected_query_hash = frame_sha256(saved_prefix, ["query_order", "experiment_name"])
            query_hash_match = replay["query_trajectory_sha256"] == expected_query_hash
            warm_hash_match = replay["warm_start_sha256"] == saved_m["warm_start_sha256"].iloc[0]
            split_hash_match = replay["split_sha256"] == saved_m["split_sha256"].iloc[0]
            replay_curve = curves[curves["run_id"].eq(run_id) & curves["method"].eq(method)].copy()
            saved_curve = saved_curves[
                saved_curves["benchmark_population"].eq("primary_common")
                & saved_curves["run_id"].eq(run_id)
                & saved_curves["method"].eq(source)
                & pd.to_numeric(saved_curves["budget"], errors="coerce").le(final_budget)
            ].copy()
            columns = ["balanced_accuracy", "global_error", "brier_score"]
            merged = saved_curve[["budget", "q20_error", "q30_error", *columns]].merge(
                replay_curve[["budget", "B1_q20_error", "B1_q30_error", *columns]],
                on="budget",
                suffixes=("_saved", "_replay"),
                validate="one_to_one",
            )
            differences = []
            for saved_col, replay_col in [
                ("q20_error", "B1_q20_error"),
                ("q30_error", "B1_q30_error"),
                *[(column, column) for column in columns],
            ]:
                left_name = f"{saved_col}_saved" if f"{saved_col}_saved" in merged else saved_col
                right_name = f"{replay_col}_replay" if f"{replay_col}_replay" in merged else replay_col
                left = pd.to_numeric(merged[left_name], errors="coerce").to_numpy(float)
                right = pd.to_numeric(merged[right_name], errors="coerce").to_numpy(float)
                finite = np.isfinite(left) & np.isfinite(right)
                differences.append(float(np.max(np.abs(left[finite] - right[finite]))) if finite.any() else 0.0)
            max_difference = max(differences)
            rows.append(
                {
                    "run_id": run_id,
                    "phase7_method": method,
                    "phase6_source_method": source,
                    "query_trajectory_hash_matches": query_hash_match,
                    "warm_start_hash_matches": warm_hash_match,
                    "split_hash_matches": split_hash_match,
                    "maximum_B1_or_global_metric_difference": max_difference,
                    "numeric_tolerance": 1e-10,
                    "status": "PASS" if query_hash_match and warm_hash_match and split_hash_match and max_difference <= 1e-10 else "FAIL",
                    "replay_reason": "all-integer predictions required to evaluate new B2/B3 metrics without changing the saved query trajectories",
                }
            )
    frame = pd.DataFrame(rows)
    require(frame["status"].eq("PASS").all(), "One or more Phase 6 baseline replays failed reconciliation")
    return frame


def build_supported_boundary_surfaces(
    population: pd.DataFrame,
    specs: Sequence[p6.RunSpec],
    queries: pd.DataFrame,
    representative: pd.DataFrame,
    *,
    final_budget: int,
    grid_size: int = 31,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_id = str(
        representative.loc[
            representative["selection"].eq("median_gate_minus_binary_B1_q20"), "run_id"
        ].iloc[0]
    )
    spec = next(spec for spec in specs if spec.run_id == run_id)
    x = population[FEATURE_COLUMNS].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    model_scaler = StandardScaler().fit(x[np.asarray(spec.train_indices, dtype=int)])
    support_scaler = StandardScaler().fit(x)
    x_support = support_scaler.transform(x)
    neighbours = NearestNeighbors(n_neighbors=2).fit(x_support)
    neighbour_distances, _ = neighbours.kneighbors(x_support)
    support_nn_limit = float(np.quantile(neighbour_distances[:, 1], 0.95))
    try:
        hull = Delaunay(x_support)
    except QhullError:
        hull = None

    slices = [("P", "VX"), ("P", "LS"), ("VX", "LS")]
    contexts = [("low", 0.25), ("median", 0.50), ("high", 0.75)]
    budgets = [budget for budget in [30, final_budget] if budget <= final_budget]
    rows: list[dict[str, Any]] = []
    for method in [M1_BINARY, M3_GATE]:
        method_queries = queries[
            queries["run_id"].eq(run_id) & queries["method"].eq(method)
        ].sort_values("query_order")
        for budget in budgets:
            queried = method_queries[
                pd.to_numeric(method_queries["query_order"], errors="raise").le(budget)
            ]["population_row_index"].astype(int).to_numpy()
            fit = p6.fit_gpc(
                x[queried],
                labels[queried],
                scaler=model_scaler,
                seed=p6.stable_seed(spec.run_seed, M1_BINARY, budget),
                kernel_kind="matern32",
            )
            for axis_a, axis_b in slices:
                a_idx, b_idx = FEATURE_COLUMNS.index(axis_a), FEATURE_COLUMNS.index(axis_b)
                a_values = np.linspace(float(x[:, a_idx].min()), float(x[:, a_idx].max()), grid_size)
                b_values = np.linspace(float(x[:, b_idx].min()), float(x[:, b_idx].max()), grid_size)
                aa, bb = np.meshgrid(a_values, b_values)
                for context_name, quantile in contexts:
                    fixed = np.quantile(x, quantile, axis=0)
                    grid = np.tile(fixed, (aa.size, 1))
                    grid[:, a_idx] = aa.ravel()
                    grid[:, b_idx] = bb.ravel()
                    grid_support = support_scaler.transform(grid)
                    inside_hull = hull.find_simplex(grid_support) >= 0 if hull is not None else np.ones(len(grid), dtype=bool)
                    nearest, _ = neighbours.kneighbors(grid_support, n_neighbors=1)
                    near_support = nearest[:, 0] <= support_nn_limit
                    supported = inside_hull & near_support
                    probability = p6.predict_gpc(fit, grid)
                    for idx in range(len(grid)):
                        rows.append(
                            {
                                "run_id": run_id,
                                "selection": "algorithmic_median_gate_minus_binary_B1_q20",
                                "method": method,
                                "budget": budget,
                                "slice": f"{axis_a}-{axis_b}",
                                "axis_a": axis_a,
                                "axis_b": axis_b,
                                "axis_a_value": float(grid[idx, a_idx]),
                                "axis_b_value": float(grid[idx, b_idx]),
                                "context": context_name,
                                "context_quantile": quantile,
                                "fixed_P": float(fixed[0]),
                                "fixed_VX": float(fixed[1]),
                                "fixed_LS": float(fixed[2]),
                                "fixed_ST": float(fixed[3]),
                                "keyhole_probability": float(probability[idx]),
                                "inside_4D_convex_hull": bool(inside_hull[idx]),
                                "nearest_population_distance_standardized": float(nearest[idx, 0]),
                                "nearest_support_limit_standardized": support_nn_limit,
                                "supported": bool(supported[idx]),
                                "unsupported_probability_must_be_greyed": not bool(supported[idx]),
                                "descriptive_surface_not_held_out_truth": True,
                            }
                        )
    surface = pd.DataFrame(rows)
    pivot = surface.pivot_table(
        index=[
            "run_id", "budget", "slice", "context", "axis_a_value", "axis_b_value"
        ],
        columns="method",
        values=["keyhole_probability", "supported"],
        aggfunc="first",
    ).reset_index()
    pivot.columns = [
        "__".join([str(value) for value in column if str(value)])
        if isinstance(column, tuple)
        else str(column)
        for column in pivot.columns
    ]
    binary_col = f"keyhole_probability__{M1_BINARY}"
    gate_col = f"keyhole_probability__{M3_GATE}"
    if binary_col in pivot and gate_col in pivot:
        pivot["hybrid_gate_minus_binary_probability"] = pivot[gate_col] - pivot[binary_col]
        pivot["absolute_probability_difference"] = np.abs(pivot["hybrid_gate_minus_binary_probability"])
    return surface, pivot


def ordered_rankings(aulc: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    rankings: dict[str, list[dict[str, Any]]] = {}
    methods = [method for method in PRIMARY_SCORECARD_METHODS if method in set(aulc["method"])]
    for boundary in BOUNDARY_IDS:
        for q in PRIMARY_BOUNDARY_QUANTILES:
            column = f"common_normalized_aulc__{boundary}_q{q}_error"
            values = [
                {"method": method, "mean_aulc": mean_aulc(aulc, method, column)}
                for method in methods
            ]
            rankings[f"{boundary}_q{q}"] = sorted(values, key=lambda row: (row["mean_aulc"], row["method"]))
    ba_values = [
        {
            "method": method,
            "mean_aulc": mean_aulc(aulc, method, "common_normalized_aulc__balanced_accuracy"),
        }
        for method in methods
    ]
    rankings["balanced_accuracy"] = sorted(
        ba_values, key=lambda row: (-row["mean_aulc"], row["method"])
    )
    return rankings


def write_results_summary(
    output_dir: Path,
    *,
    prepared: Mapping[str, Any],
    aulc: pd.DataFrame,
    bootstrap: pd.DataFrame,
    scorecard: pd.DataFrame,
    rule_frame: pd.DataFrame,
    decision: Mapping[str, Any],
    pareto: pd.DataFrame,
    behaviour: pd.DataFrame,
    discovery: pd.DataFrame,
    overlap: pd.DataFrame,
    transient: pd.DataFrame,
    partition: pd.DataFrame,
    runtime_frame: pd.DataFrame,
    runtime_payload: Mapping[str, Any],
    wall_seconds: float,
    workers: int,
) -> dict[str, Any]:
    boundary_artifacts = prepared["boundary_artifacts"]
    correlations = boundary_artifacts["correlations"]
    off_diagonal = correlations[correlations["metric_a"].ne(correlations["metric_b"])]
    overlap_frame = boundary_artifacts["overlap"]
    overlap_off_diagonal = overlap_frame[
        overlap_frame["metric_a"].ne(overlap_frame["metric_b"])
    ]
    rankings = ordered_rankings(aulc)
    binary_robust_wins: dict[str, bool] = {}
    hybrid_mean_results: dict[str, dict[str, float]] = {}
    for boundary in BOUNDARY_IDS:
        metric = f"common_normalized_aulc__{boundary}_q20_error"
        binary_value = mean_aulc(aulc, M1_BINARY, metric)
        binary_robust_wins[boundary] = binary_value <= mean_aulc(aulc, M2_DEPTH, metric)
        hybrid_mean_results[boundary] = {
            "binary": binary_value,
            "hybrid_gate": mean_aulc(aulc, M3_GATE, metric),
            "hybrid_fusion": mean_aulc(aulc, M4_FUSION, metric),
            "max_depth": mean_aulc(aulc, M2_DEPTH, metric),
        }

    discovery_at = (
        discovery[pd.to_numeric(discovery["budget"], errors="raise").isin([20, 30, 80])]
        .groupby(["method", "budget"], as_index=False)["keyhole_discovered"]
        .mean()
    )
    transient_final = transient[
        pd.to_numeric(transient["budget"], errors="raise").eq(80)
    ].groupby(["method", "subgroup"], as_index=False).agg(
        mean_sensitivity=("sensitivity", "mean"),
        total_positive_cases_across_folds=("positive_case_count", "sum"),
    )
    partition_final = partition[
        pd.to_numeric(partition["budget"], errors="raise").eq(80)
    ].groupby(["method", "partition"], as_index=False).agg(
        mean_balanced_accuracy=("balanced_accuracy", "mean"),
        mean_sensitivity=("sensitivity", "mean"),
        held_out_rows_across_runs=("row_count", "sum"),
        keyhole_rows_across_runs=("keyhole_count", "sum"),
    )
    gate_binary_overlap = overlap[
        ((overlap["method_a"].eq(M1_BINARY) & overlap["method_b"].eq(M3_GATE))
        | (overlap["method_b"].eq(M1_BINARY) & overlap["method_a"].eq(M3_GATE)))
        & pd.to_numeric(overlap["budget"], errors="raise").eq(80)
    ]
    first_divergence = overlap[
        ((overlap["method_a"].eq(M1_BINARY) & overlap["method_b"].eq(M3_GATE))
        | (overlap["method_b"].eq(M1_BINARY) & overlap["method_a"].eq(M3_GATE)))
    ]["first_query_order_sequence_diverges"].dropna()

    gate_runtime = runtime_frame[runtime_frame["method"].eq(M3_GATE)].iloc[0]
    fusion_runtime = runtime_frame[runtime_frame["method"].eq(M4_FUSION)].iloc[0]
    binary_runtime = runtime_frame[runtime_frame["method"].eq(M1_BINARY)].iloc[0]
    max_runtime = runtime_frame[runtime_frame["method"].eq(M2_DEPTH)].iloc[0]
    decision_name = str(decision["decision"])
    success_map = dict(decision["hybrid_success"])
    q20_ci_summary: dict[str, dict[str, list[float]]] = {}
    for hybrid in HYBRID_METHODS:
        q20_ci_summary[hybrid] = {}
        for boundary in BOUNDARY_IDS:
            metric = f"common_normalized_aulc__{boundary}_q20_error"
            row = bootstrap_row(bootstrap, hybrid, M1_BINARY, metric)
            q20_ci_summary[hybrid][boundary] = [
                float(row["bootstrap_ci_low"]),
                float(row["bootstrap_ci_high"]),
            ]

    summary = {
        "phase": "Week 7 Phase 7",
        "decision": decision_name,
        "decision_reason": decision["reason"],
        "phase6_commit": EXPECTED_PHASE6_COMMIT,
        "hf_revision": EXPECTED_HF_REVISION,
        "population": {"total": 405, "keyhole": 73, "non_keyhole": 332},
        "outer_runs": 20,
        "final_budget": 80,
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "boundary_metric_min_off_diagonal_spearman": float(off_diagonal["spearman_rank_correlation"].min()),
        "boundary_metric_max_off_diagonal_spearman": float(off_diagonal["spearman_rank_correlation"].max()),
        "q20_jaccard_min": float(
            overlap_off_diagonal[overlap_off_diagonal["quantile"].eq(20)]["jaccard"].min()
        ),
        "q20_jaccard_max": float(
            overlap_off_diagonal[overlap_off_diagonal["quantile"].eq(20)]["jaccard"].max()
        ),
        "binary_q20_better_than_max_depth_by_definition": binary_robust_wins,
        "q20_mean_aulc_by_definition": hybrid_mean_results,
        "rankings": rankings,
        "hybrid_preregistered_success": success_map,
        "hybrid_minus_binary_q20_bootstrap_intervals": q20_ci_summary,
        "discovery_at_selected_budgets": discovery_at.to_dict(orient="records"),
        "transient_persistent_final": transient_final.to_dict(orient="records"),
        "partition_final": partition_final.to_dict(orient="records"),
        "mean_gate_binary_query_jaccard_at_80": float(gate_binary_overlap["jaccard"].mean()),
        "median_first_gate_binary_divergence_query": float(pd.to_numeric(first_divergence, errors="coerce").median()),
        "pareto_frontier": pareto[pareto["on_pareto_frontier"]].to_dict(orient="records"),
        "runtime": {
            "wall_seconds": wall_seconds,
            "workers": workers,
            "binary_mean_run_seconds": float(binary_runtime["mean_runtime_seconds"]),
            "max_depth_mean_run_seconds": float(max_runtime["mean_runtime_seconds"]),
            "hybrid_gate_mean_run_seconds": float(gate_runtime["mean_runtime_seconds"]),
            "hybrid_fusion_mean_run_seconds": float(fusion_runtime["mean_runtime_seconds"]),
            **json_safe(dict(runtime_payload)),
        },
        "manual_has_keyhole_remains_ground_truth": True,
        "maximum_depth_role": "physical side information and separate continuous comparator",
        "causal_claim": False,
    }
    write_json(output_dir / "summary.json", summary)

    def fmt(value: float, digits: int = 4) -> str:
        return f"{value:.{digits}f}"

    q20_rank_text = "; ".join(
        f"{boundary}: "
        + " < ".join(f"{item['method']} ({fmt(item['mean_aulc'])})" for item in rankings[f"{boundary}_q20"])
        for boundary in BOUNDARY_IDS
    )
    q30_rank_text = "; ".join(
        f"{boundary}: "
        + " < ".join(f"{item['method']} ({fmt(item['mean_aulc'])})" for item in rankings[f"{boundary}_q30"])
        for boundary in BOUNDARY_IDS
    )
    ba_rank_text = " > ".join(
        f"{item['method']} ({fmt(item['mean_aulc'])})" for item in rankings["balanced_accuracy"]
    )
    robust_boundary_text = (
        "yes under all three definitions"
        if all(binary_robust_wins.values())
        else "only under " + ", ".join(key for key, value in binary_robust_wins.items() if value)
    )
    hybrid_rule_text = "; ".join(
        f"{method}: {'PASS' if success else 'FAIL'}" for method, success in success_map.items()
    )
    gate_discovery_30 = float(
        discovery_at[discovery_at["method"].eq(M3_GATE) & discovery_at["budget"].eq(30)]["keyhole_discovered"].iloc[0]
    )
    binary_discovery_30 = float(
        discovery_at[discovery_at["method"].eq(M1_BINARY) & discovery_at["budget"].eq(30)]["keyhole_discovered"].iloc[0]
    )
    transient_lookup = transient_final.set_index(["method", "subgroup"])["mean_sensitivity"]
    transient_gate = float(transient_lookup.get((M3_GATE, "transient_Keyhole"), math.nan))
    transient_binary = float(transient_lookup.get((M1_BINARY, "transient_Keyhole"), math.nan))
    pareto_gate_q20 = int(
        pareto[
            pareto["method"].eq(M3_GATE)
            & pareto["quantile"].eq(20)
            & pareto["on_pareto_frontier"]
        ]["boundary_definition"].nunique()
    )
    pareto_fusion_q20 = int(
        pareto[
            pareto["method"].eq(M4_FUSION)
            & pareto["quantile"].eq(20)
            & pareto["on_pareto_frontier"]
        ]["boundary_definition"].nunique()
    )
    lines = [
        "# Week 7 Phase 7 — Final boundary-metric robustness and Hybrid acquisition benchmark",
        "",
        "Manual experiment-level `has_keyhole` remains the regime ground truth. Maximum depth is physical side information from the same queried simulation; for Hybrid methods it affects acquisition only, while the primary prediction remains Binary GPC.",
        "",
        "1. **Phase 6 publication:** yes. The exact commit is `5734de6f533e1de1e15a07de24e7d4e6e53bb6fa`; local, upstream, and remote were equal before Phase 7 began.",
        "2. **Exact run reuse:** yes. All 20 Phase 6 primary outer runs, test folds, candidate pools, deterministic permutations, warm starts, and budget accounting were hash-verified.",
        f"3. **Boundary-region agreement:** B1/B2/B3 off-diagonal rank correlations span {fmt(summary['boundary_metric_min_off_diagonal_spearman'])}–{fmt(summary['boundary_metric_max_off_diagonal_spearman'])}; q20 Jaccard spans {fmt(summary['q20_jaccard_min'])}–{fmt(summary['q20_jaccard_max'])}. They overlap but are not interchangeable.",
        f"4. **Binary Phase 6 boundary advantage:** {robust_boundary_text} when compared with Max-Depth on mean q20 AULC.",
        f"5. **Hybrid Gate on B1 q20:** Gate {fmt(mean_aulc(aulc, M3_GATE, 'common_normalized_aulc__B1_q20_error'))} versus Binary {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B1_q20_error'))}.",
        f"6. **Hybrid Gate on B2 q20:** Gate {fmt(mean_aulc(aulc, M3_GATE, 'common_normalized_aulc__B2_q20_error'))} versus Binary {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B2_q20_error'))}.",
        f"7. **Hybrid Gate on B3 q20:** Gate {fmt(mean_aulc(aulc, M3_GATE, 'common_normalized_aulc__B3_q20_error'))} versus Binary {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B3_q20_error'))}.",
        f"8. **Hybrid Rank Fusion:** B1/B2/B3 q20 means are {fmt(mean_aulc(aulc, M4_FUSION, 'common_normalized_aulc__B1_q20_error'))}, {fmt(mean_aulc(aulc, M4_FUSION, 'common_normalized_aulc__B2_q20_error'))}, and {fmt(mean_aulc(aulc, M4_FUSION, 'common_normalized_aulc__B3_q20_error'))}, compared with Binary {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B1_q20_error'))}, {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B2_q20_error'))}, and {fmt(mean_aulc(aulc, M1_BINARY, 'common_normalized_aulc__B3_q20_error'))}.",
        f"9. **Preregistered robust-improvement rule:** {hybrid_rule_text}.",
        f"10. **q30 consistency:** rankings are {q30_rank_text}.",
        f"11. **Balanced-accuracy cost:** ranking is {ba_rank_text}; material degradation is defined as more than 0.01 below Binary.",
        f"12. **Early Keyhole discovery:** at budget 30, Gate found a mean {fmt(gate_discovery_30, 2)} positives versus Binary {fmt(binary_discovery_30, 2)} under identical simulator-query budgets.",
        f"13. **Transient Keyhole:** final mean sensitivity is Gate {fmt(transient_gate)} versus Binary {fmt(transient_binary)}; this is descriptive and uses the unchanged subgroup definition.",
        "14. **Partition specificity:** new, old-local, and old-remote results are saved separately; old-remote remains highly uncertain because its positive count is tiny.",
        f"15. **Query-trajectory difference:** Gate/Binary mean Jaccard at budget 80 is {fmt(summary['mean_gate_binary_query_jaccard_at_80'])}; median first divergence occurs at query {fmt(summary['median_first_gate_binary_divergence_query'], 1)}.",
        "16. **Did Max-Depth alter queries?** yes whenever a Hybrid selection differs from the exact Binary champion candidate; the run-level fractions are saved in `phase7_failure_diagnostics.csv`.",
        f"17. **q20/BA Pareto movement:** Gate is on the frontier for {pareto_gate_q20}/3 definitions and Rank Fusion for {pareto_fusion_q20}/3; see the unweighted Pareto artifact.",
        "18. **q30/BA Pareto movement:** reported separately for every B1/B2/B3 definition; no arbitrary weighted score was introduced.",
        f"19. **Computational overhead:** mean run time is Binary {fmt(float(binary_runtime['mean_runtime_seconds']), 2)} s, Gate {fmt(float(gate_runtime['mean_runtime_seconds']), 2)} s, Fusion {fmt(float(fusion_runtime['mean_runtime_seconds']), 2)} s, and Max-Depth {fmt(float(max_runtime['mean_runtime_seconds']), 2)} s.",
        "20. **Simulator-cost interpretation:** Hybrid computation is more expensive, but every method still receives exactly the same number of simulator queries. Simulator and computational efficiency are not conflated.",
        "21. **Maximum depth if Hybrid loses:** it remains a strongly predictable physical response and the Phase 6 continuous comparator; losing as auxiliary acquisition information would not erase that physical value.",
        "22. **Boundary definition for the thesis:** emphasize B1 for direct continuity with Phase 6, and present B2/B3 as preregistered robustness diagnostics rather than replacing B1 with a post-hoc consensus.",
        "23. **Robustness diagnostics:** B2, B3, consensus q20/q30, robust-scaling sensitivity, partition summaries, and supported surfaces remain diagnostic; B1/B2/B3 q20/q30 drive the preregistered decision.",
        f"24. **Final recommended real-data active strategy:** **{decision_name}** — {decision['reason']}",
        "25. **Scientific lesson:** richer continuous physical information can change where a binary active learner queries, but it counts as a thesis-level boundary improvement only if the benefit survives multiple model-independent boundary definitions without a material global-performance cost.",
        "",
        "## Complete rankings",
        "",
        f"- q20, lower is better: {q20_rank_text}",
        f"- q30, lower is better: {q30_rank_text}",
        f"- balanced-accuracy AULC, higher is better: {ba_rank_text}",
        "",
        "## Hard stop",
        "",
        "No manual label, physical target, kernel, gate fraction, rank weight, or preregistered decision condition was changed after results. Phase 7 remains uncommitted and unpushed pending review; no Phase 8 was started.",
    ]
    (output_dir / "results_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def fairness_invariants_pass(fairness: pd.DataFrame) -> bool:
    invariant_columns = [
        "candidate_pool_is_exact_phase6_outer_training_only",
        "test_set_never_queried",
        "test_labels_used_for_fitting_or_acquisition",
        "test_outputs_used_for_acquisition",
        "hidden_pool_labels_used_for_acquisition",
        "hidden_pool_max_depth_used_for_acquisition",
        "boundary_metrics_used_for_acquisition",
        "extra_warm_start_queries_counted",
        "gate_fraction_fixed_0_20",
        "rank_weights_fixed_0_5_0_5",
    ]
    require(set(invariant_columns).issubset(fairness.columns), "Fairness invariant columns missing")
    expected_true = {
        "candidate_pool_is_exact_phase6_outer_training_only",
        "test_set_never_queried",
        "extra_warm_start_queries_counted",
        "gate_fraction_fixed_0_20",
        "rank_weights_fixed_0_5_0_5",
    }
    for column in invariant_columns:
        values = strict_bool(fairness[column])
        if column in expected_true:
            if not values.all():
                return False
        elif values.any():
            return False
    return True


def run_benchmark_stage(
    prepared: Mapping[str, Any],
    output_dir: Path,
    *,
    workers: int,
    smoke: bool,
    force: bool,
) -> dict[str, Any]:
    stage_started = time.perf_counter()
    prior_full_wall_seconds = None if smoke else first_successful_full_runtime(output_dir)
    specs = list(prepared["specs"][:2] if smoke else prepared["specs"])
    methods = SMOKE_METHODS if smoke else EXECUTED_METHODS
    final_budget = SMOKE_BUDGET if smoke else FINAL_BUDGET
    checkpoint_root = output_dir / "checkpoints"
    nested = Parallel(n_jobs=workers, backend="loky")(
        delayed(run_outer_methods)(
            spec,
            methods,
            prepared["population"],
            prepared["boundary"],
            prepared["tables"]["queries"],
            final_budget,
            checkpoint_root,
            force,
        )
        for spec in specs
    )
    results = [item for run_results in nested for item in run_results]
    frames = {
        key: concat_results(results, key)
        for key in ["manifest", "queries", "curves", "predictions", "thresholds", "diagnostics", "fairness"]
    }
    manifest = frames["manifest"]
    require(len(manifest) == len(specs) * len(methods), "Method/run manifest count drift")
    for run_id, part in manifest.groupby("run_id"):
        require(part["split_sha256"].nunique() == 1, f"{run_id}: methods do not share split")
        require(part["warm_start_sha256"].nunique() == 1, f"{run_id}: methods do not share warm start")
        require(part["final_budget"].nunique() == 1, f"{run_id}: methods do not share final budget")
    require(fairness_invariants_pass(frames["fairness"]), "Fairness audit contains a false invariant")

    reconciliation = reconcile_phase6_baseline_replays(
        manifest, frames["curves"], prepared["tables"], final_budget=final_budget
    )
    summaries = summarize_learning(frames["curves"], manifest, final_budget=final_budget)
    comparisons, bootstrap = paired_method_comparisons(
        summaries["aulc"],
        resamples=200 if smoke else PAIRED_BOOTSTRAP_RESAMPLES,
    )
    pareto = build_pareto_summary(summaries["aulc"])
    behaviour, discovery, query_overlap = query_behaviour_tables(
        frames["queries"], methods, final_budget=final_budget
    )
    transient, timing, partition = subgroup_and_partition_tables(
        frames["predictions"], prepared["population"], final_budget=final_budget
    )
    representative, failure = representative_and_failure_tables(
        summaries["aulc"], frames["queries"], frames["thresholds"]
    )
    runtime_frame, runtime_payload = runtime_comparison(manifest)

    write_csv(output_dir / "hybrid_run_manifest.csv", manifest)
    write_csv(output_dir / "phase7_all_method_query_history.csv", frames["queries"])
    write_csv(output_dir / "hybrid_query_history.csv", frames["queries"][frames["queries"]["method"].isin(HYBRID_METHODS)])
    write_csv(output_dir / "phase7_all_method_prediction_checkpoints.csv", frames["predictions"])
    write_csv(output_dir / "hybrid_prediction_history.csv", frames["predictions"][frames["predictions"]["method"].isin(HYBRID_METHODS)])
    write_csv(output_dir / "hybrid_online_threshold_history.csv", frames["thresholds"][frames["thresholds"]["method"].isin(HYBRID_METHODS)])
    write_csv(output_dir / "hybrid_model_diagnostics.csv", frames["diagnostics"])
    write_csv(output_dir / "phase7_learning_curve_summary.csv", frames["curves"])
    write_csv(output_dir / "phase7_boundary_metric_learning_curves.csv", summaries["long_curves"])
    write_csv(output_dir / "phase7_final_budget_summary.csv", summaries["final"])
    write_csv(output_dir / "phase7_aulc_summary.csv", summaries["aulc"])
    write_csv(output_dir / "phase7_queries_to_tolerance.csv", summaries["tolerance"])
    write_csv(output_dir / "phase7_paired_method_comparisons.csv", comparisons)
    write_csv(output_dir / "phase7_paired_bootstrap_intervals.csv", bootstrap)
    write_csv(output_dir / "phase7_pareto_summary.csv", pareto)
    write_csv(output_dir / "phase7_query_boundary_behavior.csv", behaviour)
    write_csv(output_dir / "phase7_keyhole_discovery_summary.csv", discovery)
    write_csv(output_dir / "phase7_query_overlap_summary.csv", query_overlap)
    write_csv(output_dir / "phase7_transient_persistent_summary.csv", transient)
    write_csv(output_dir / "phase7_t0_timing_summary.csv", timing)
    write_csv(output_dir / "phase7_partition_specific_summary.csv", partition)
    write_csv(output_dir / "phase7_representative_runs.csv", representative)
    write_csv(output_dir / "phase7_failure_diagnostics.csv", failure)
    write_csv(output_dir / "phase7_runtime_comparison.csv", runtime_frame)
    write_csv(output_dir / "phase6_baseline_replay_reconciliation.csv", reconciliation)
    write_csv(output_dir / "phase7_fairness_audit.csv", frames["fairness"])

    wall_seconds = time.perf_counter() - stage_started
    authoritative_full_wall_seconds = (
        wall_seconds if smoke or prior_full_wall_seconds is None else prior_full_wall_seconds
    )
    runtime_payload = {
        **runtime_payload,
        "wall_seconds": authoritative_full_wall_seconds,
        "authoritative_fresh_full_wall_seconds": authoritative_full_wall_seconds,
        "current_invocation_wall_seconds": wall_seconds,
        "current_invocation_reused_full_checkpoints": bool(
            not smoke and prior_full_wall_seconds is not None
        ),
        "workers": workers,
        "smoke": smoke,
        "executed_outer_runs": len(specs),
        "executed_methods": list(methods),
        "final_budget": final_budget,
        "checkpoint_reuse_enabled": not force,
    }
    write_json(output_dir / "runtime_summary.json", runtime_payload)

    decision_payload: dict[str, Any] | None = None
    scorecard = pd.DataFrame()
    rule_frame = pd.DataFrame()
    surfaces = pd.DataFrame()
    surface_comparison = pd.DataFrame()
    summary = None
    if not smoke:
        scorecard, rule_frame, decision_payload = evaluate_preregistered_decision(
            summaries["aulc"], bootstrap
        )
        write_csv(output_dir / "phase7_method_scorecard.csv", scorecard)
        write_csv(output_dir / "phase7_preregistered_rule_outcome.csv", rule_frame)
        write_csv(output_dir / "phase7_final_decision.csv", decision_payload["frame"])
        surfaces, surface_comparison = build_supported_boundary_surfaces(
            prepared["population"],
            prepared["specs"],
            frames["queries"],
            representative,
            final_budget=final_budget,
        )
        write_csv(output_dir / "phase7_supported_boundary_surfaces.csv", surfaces)
        write_csv(output_dir / "phase7_boundary_surface_comparison.csv", surface_comparison)
        summary = write_results_summary(
            output_dir,
            prepared=prepared,
            aulc=summaries["aulc"],
            bootstrap=bootstrap,
            scorecard=scorecard,
            rule_frame=rule_frame,
            decision=decision_payload,
            pareto=pareto,
            behaviour=behaviour,
            discovery=discovery,
            overlap=query_overlap,
            transient=transient,
            partition=partition,
            runtime_frame=runtime_frame,
            runtime_payload=runtime_payload,
            wall_seconds=authoritative_full_wall_seconds,
            workers=workers,
        )
    else:
        smoke_summary = {
            "phase": "Week 7 Phase 7 smoke",
            "scientific_result": False,
            "outer_runs": len(specs),
            "methods": list(methods),
            "final_budget": final_budget,
            "wall_seconds": wall_seconds,
            "reproduction_passed": prepared["reproduction"]["status"].eq("PASS").all(),
            "fairness_passed": fairness_invariants_pass(frames["fairness"]),
        }
        write_json(output_dir / "summary.json", smoke_summary)
        (output_dir / "results_summary.md").write_text(
            "# Phase 7 smoke run\n\nThis reduced two-run, budget-30 execution validates reproduction, leakage barriers, exact warm starts, both preregistered Hybrid acquisitions, accounting, and checkpoints. It is not a scientific Phase 7 result.\n",
            encoding="utf-8",
        )

    append_execution_history(
        output_dir,
        "smoke_benchmark" if smoke else "full_benchmark",
        "PASS",
        wall_seconds=wall_seconds,
        workers=workers,
        outer_runs=len(specs),
        methods=list(methods),
        final_budget=final_budget,
        preregistration_sha256=EXPECTED_PREREG_SHA256,
        decision=decision_payload["decision"] if decision_payload else "SMOKE_NOT_SCIENTIFIC",
    )
    return {
        "frames": frames,
        "summaries": summaries,
        "comparisons": comparisons,
        "bootstrap": bootstrap,
        "pareto": pareto,
        "behaviour": behaviour,
        "discovery": discovery,
        "query_overlap": query_overlap,
        "transient": transient,
        "timing": timing,
        "partition": partition,
        "representative": representative,
        "failure": failure,
        "runtime": runtime_frame,
        "decision": decision_payload,
        "summary": summary,
        "surfaces": surfaces,
        "surface_comparison": surface_comparison,
        "wall_seconds": wall_seconds,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run the reduced two-run budget-30 execution")
    parser.add_argument("--prepare-only", action="store_true", help="Run provenance, boundary diagnostics, and Phase 6 reproduction only")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="Ignore Phase 7 method checkpoints")
    parser.add_argument("--force-reproduction", action="store_true", help="Recompute the small Phase 6 reproduction checkpoints")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    require(args.workers >= 1, "workers must be positive")
    output_dir = SMOKE_DIR if args.smoke else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    prepared = prepare_phase7(output_dir, force_reproduction=args.force_reproduction)
    if args.prepare_only:
        print(
            json.dumps(
                {
                    "mode": "smoke_prepare" if args.smoke else "full_prepare",
                    "output_dir": str(output_dir),
                    "population": len(prepared["population"]),
                    "outer_runs": len(prepared["specs"]),
                    "reproduction_checks": len(prepared["reproduction"]),
                    "status": "PASS",
                },
                indent=2,
            )
        )
        return
    result = run_benchmark_stage(
        prepared,
        output_dir,
        workers=args.workers,
        smoke=args.smoke,
        force=args.force,
    )
    print(
        json.dumps(
            {
                "mode": "smoke" if args.smoke else "full",
                "output_dir": str(output_dir),
                "wall_seconds": result["wall_seconds"],
                "decision": result["decision"]["decision"] if result["decision"] else "SMOKE_NOT_SCIENTIFIC",
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
