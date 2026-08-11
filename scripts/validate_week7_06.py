"""Fail-closed validation for Week 7 Phase 6 outputs and teaching notebook.

The checks in this module are intentionally independent of the Phase 6
orchestrator.  In particular, threshold trajectories, test boundary subsets,
probabilities, learning-curve integrals, tolerance crossings, and paired
comparisons are recomputed from the saved row-level artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
SMOKE_DIR = OUTPUT_DIR / "smoke"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "06_real_data_boundary_active_level_set.ipynb"
SOURCE = ROOT / "src" / "week7_phase6_real_data_boundary_active_level_set.py"
PHASE55_OUTPUT = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
PHASE55_TARGETS = PHASE55_OUTPUT / "current_revision_simulation_level_targets.parquet"

PHASE55_SHA = "6cc2ea150b9deb6ec9dd529d94ac55cc86556cfb"
PHASE5_SHA = "3367f4c9b5af2def802f72a65258f5cc01896bac"
PHASE55_BRANCH = "codex/week7-phase5-5-g3-robustness-transfer"
PHASE6_BRANCH = "codex/week7-phase6-real-data-boundary-active-level-set"
HF_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
HF_REMOTE = "https://huggingface.co/datasets/ioandanielc/sph_v2"

PRIMARY_POPULATION = "primary_common"
G3_POPULATION = "secondary_g3_common"
PRIMARY_SIZE = 405
G3_SIZE = 404
PRIMARY_POSITIVES = 73
FULL_RUNS = 20
FULL_FINAL_BUDGET = 80
FULL_PAIRED_BOOTSTRAPS = 5000
FLOAT_ATOL = 5e-10
FLOAT_RTOL = 5e-9

# Section 33 names exactly 49 root-level deliverables.  Figures and restart
# checkpoints live below subdirectories and are covered by their manifests.
EXPECTED_OUTPUT_ARTIFACTS = (
    "phase6_preflight.json",
    "input_provenance.json",
    "hf_revision_audit.json",
    "population_audit.csv",
    "primary_common_population.csv",
    "secondary_g3_common_population.csv",
    "max_depth_event_audit.csv",
    "max_depth_raw_review_cases.csv",
    "max_depth_semantic_summary.csv",
    "empirical_boundary_reference.csv",
    "empirical_boundary_subset_summary.csv",
    "empirical_boundary_validation.csv",
    "outer_split_manifest.csv",
    "outer_split_balance_audit.csv",
    "fairness_audit.csv",
    "static_model_fold_predictions.csv",
    "static_model_summary.csv",
    "static_boundary_metric_summary.csv",
    "static_probability_calibration.csv",
    "active_run_manifest.csv",
    "active_initialization_audit.csv",
    "active_query_history.csv",
    "active_prediction_history.csv",
    "online_threshold_history.csv",
    "online_threshold_bootstrap_summary.csv",
    "active_learning_curve_summary.csv",
    "active_learning_final_budget_summary.csv",
    "active_learning_aulc_summary.csv",
    "queries_to_tolerance.csv",
    "active_paired_method_comparisons.csv",
    "active_paired_bootstrap_intervals.csv",
    "query_boundary_distance_summary.csv",
    "subgroup_transient_persistent_results.csv",
    "subgroup_t0_timing_results.csv",
    "g3_secondary_active_summary.csv",
    "max_depth_vs_g3_summary.csv",
    "domain_transfer_model_summary.csv",
    "boundary_surface_data.csv",
    "boundary_disagreement_summary.csv",
    "phase6_formulation_scorecard.csv",
    "phase6_final_decision.csv",
    "runtime_summary.json",
    "execution_history.json",
    "validation_results.csv",
    "requirement_checklist.csv",
    "summary.json",
    "results_summary.md",
    "figure_manifest.csv",
    "output_manifest.csv",
)

GENERATED_BY_VALIDATOR = {"validation_results.csv", "requirement_checklist.csv"}
SMOKE_OPTIONAL_ARTIFACTS = {
    "boundary_surface_data.csv",
    "boundary_disagreement_summary.csv",
    "phase6_formulation_scorecard.csv",
    "phase6_final_decision.csv",
    "figure_manifest.csv",
}
ALLOWED_DECISIONS = {
    "CONTINUOUS MAX-DEPTH PRIMARY",
    "BINARY KEYHOLE PRIMARY",
    "HYBRID / NO CLEAR WINNER",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Validate reduced outputs under the Phase 6 smoke directory.",
    )
    return parser.parse_args()


def git_text(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=False, capture_output=True, text=True, encoding="utf-8"
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def git_blob(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def parse_bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    lowered = series.astype(str).str.strip().str.lower()
    mapping = {
        "true": True,
        "1": True,
        "yes": True,
        "pass": True,
        "false": False,
        "0": False,
        "no": False,
        "fail": False,
        "nan": False,
        "none": False,
        "": False,
    }
    unknown = sorted(set(lowered) - set(mapping))
    if unknown:
        raise ValueError(f"Unexpected boolean values: {unknown[:10]}")
    return lowered.map(mapping).astype(bool)


def all_true(frame: pd.DataFrame, column: str) -> bool:
    return column in frame and len(frame) > 0 and bool(parse_bool_series(frame[column]).all())


def all_false(frame: pd.DataFrame, column: str) -> bool:
    return column in frame and len(frame) > 0 and bool((~parse_bool_series(frame[column])).all())


def close(a: Any, b: Any, *, atol: float = FLOAT_ATOL, rtol: float = FLOAT_RTOL) -> bool:
    try:
        return bool(np.isclose(float(a), float(b), atol=atol, rtol=rtol, equal_nan=True))
    except (TypeError, ValueError):
        return False


def close_arrays(a: Sequence[Any], b: Sequence[Any]) -> bool:
    try:
        left = np.asarray(a, dtype=float)
        right = np.asarray(b, dtype=float)
    except (TypeError, ValueError):
        return False
    return left.shape == right.shape and bool(
        np.allclose(left, right, atol=FLOAT_ATOL, rtol=FLOAT_RTOL, equal_nan=True)
    )


def artifact_loader(output_dir: Path) -> tuple[dict[str, Any], dict[str, str]]:
    """Attempt to parse every one of the 49 named artifacts."""

    loaded: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name in EXPECTED_OUTPUT_ARTIFACTS:
        path = output_dir / name
        try:
            if name.endswith(".csv"):
                try:
                    loaded[name] = pd.read_csv(path, low_memory=False)
                except pd.errors.EmptyDataError:
                    # A reduced smoke run intentionally emits schema-less empty
                    # paired-comparison CSVs because inference is not attempted.
                    loaded[name] = pd.DataFrame()
            elif name.endswith(".json"):
                loaded[name] = json.loads(path.read_text(encoding="utf-8-sig"))
            else:
                loaded[name] = path.read_text(encoding="utf-8-sig")
        except Exception as exc:  # converted into a validation failure below
            loaded[name] = pd.DataFrame() if name.endswith(".csv") else None
            errors[name] = f"{type(exc).__name__}: {exc}"
    return loaded, errors


def add_check(
    rows: list[dict[str, Any]],
    check_id: str,
    name: str,
    category: str,
    evaluator: Callable[[], tuple[bool, str]],
) -> None:
    try:
        passed, detail = evaluator()
    except Exception as exc:
        passed = False
        detail = f"{type(exc).__name__}: {exc}"
    rows.append(
        {
            "check_id": check_id,
            "check": name,
            "status": "PASS" if bool(passed) else "FAIL",
            "detail": str(detail),
            "category": category,
        }
    )


def replace_check(
    validation: pd.DataFrame, check_id: str, passed: bool, detail: str
) -> pd.DataFrame:
    mask = validation["check_id"].eq(check_id)
    if int(mask.sum()) != 1:
        raise RuntimeError(f"Expected one validation row for {check_id}")
    validation.loc[mask, "status"] = "PASS" if passed else "FAIL"
    validation.loc[mask, "detail"] = detail
    return validation


def published_phase55_audit() -> tuple[bool, str]:
    branch = git_text("branch", "--show-current")
    head = git_text("rev-parse", "HEAD")
    phase55_local = git_text("rev-parse", PHASE55_BRANCH)
    remote_line = git_text(
        "ls-remote", "--heads", "origin", f"refs/heads/{PHASE55_BRANCH}"
    )
    phase55_remote = remote_line.split("\t", 1)[0] if remote_line else ""
    parent = git_text("rev-parse", f"{PHASE55_SHA}^")
    phase6_remote = git_text(
        "ls-remote", "--heads", "origin", f"refs/heads/{PHASE6_BRANCH}"
    )
    phase6_upstream = git_text("rev-parse", "@{upstream}", check=False)

    validation_blob = git_blob(
        PHASE55_SHA,
        "outputs/week7_05_5_g3_robustness_transfer_analysis/validation_results.csv",
    )
    requirements_blob = git_blob(
        PHASE55_SHA,
        "outputs/week7_05_5_g3_robustness_transfer_analysis/requirement_checklist.csv",
    )
    manifest_blob = git_blob(
        PHASE55_SHA,
        "outputs/week7_05_5_g3_robustness_transfer_analysis/output_manifest.csv",
    )
    phase55_validation = pd.read_csv(io.BytesIO(validation_blob))
    phase55_requirements = pd.read_csv(io.BytesIO(requirements_blob))
    phase55_manifest = pd.read_csv(io.BytesIO(manifest_blob))
    bad_hashes: list[str] = []
    checkout_eol_matches = 0
    for row in phase55_manifest.to_dict("records"):
        relative = str(row["relative_path"]).replace("\\", "/")
        try:
            blob = git_blob(PHASE55_SHA, relative)
        except Exception:
            bad_hashes.append(relative)
            continue
        expected = str(row["sha256"]).lower()
        blob_hash = hashlib.sha256(blob).hexdigest()
        # Phase 5.5 was closed out in a Windows worktree.  Git stores ten text
        # artifacts with LF in the commit while the pre-commit byte manifest
        # correctly records their CRLF checkout bytes.  Accept only this exact
        # deterministic checkout transform, never a semantic normalization.
        checkout_hash = hashlib.sha256(blob.replace(b"\n", b"\r\n")).hexdigest()
        if blob_hash == expected:
            continue
        if b"\r\n" not in blob and checkout_hash == expected:
            checkout_eol_matches += 1
            continue
        if blob_hash != expected:
            bad_hashes.append(relative)

    ok = all(
        [
            branch == PHASE6_BRANCH,
            head == PHASE55_SHA,
            phase55_local == PHASE55_SHA,
            phase55_remote == PHASE55_SHA,
            parent == PHASE5_SHA,
            not phase6_remote,
            not phase6_upstream,
            len(phase55_validation) == 24,
            phase55_validation["status"].eq("PASS").all(),
            len(phase55_requirements) == 12,
            phase55_requirements["status"].eq("PASS").all(),
            len(phase55_manifest) == 106,
            not bad_hashes,
        ]
    )
    detail = (
        f"phase6={branch}@{head}; phase55 local/remote={phase55_local}/{phase55_remote}; "
        f"phase5_parent={parent}; closeout=24/24,12/12,{len(phase55_manifest)}/106; "
        f"published_hash_failures={len(bad_hashes)}; checkout_eol_matches={checkout_eol_matches}; "
        f"phase6_remote_absent={not bool(phase6_remote)}; phase6_upstream_absent={not bool(phase6_upstream)}"
    )
    return ok, detail


def nested_items(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            yield name, item
            yield from nested_items(item, name)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            name = f"{prefix}[{index}]"
            yield name, item
            yield from nested_items(item, name)


def hf_revision_check(hf_audit: Any, provenance: Any, primary: pd.DataFrame) -> tuple[bool, str]:
    line = git_text("ls-remote", HF_REMOTE, "refs/heads/main")
    live = line.split("\t", 1)[0] if line else ""
    serialized = json.dumps([hf_audit, provenance], sort_keys=True, default=str)
    recorded_exact = HF_REVISION in serialized
    population_exact = (
        "exact_sph_v2_revision" in primary
        and primary["exact_sph_v2_revision"].astype(str).eq(HF_REVISION).all()
    )
    drift_flags = []
    for key, value in nested_items(hf_audit):
        lowered = key.lower()
        if "unexpected" in lowered and "drift" in lowered and isinstance(value, bool):
            drift_flags.append(not value if "no_unexpected" in lowered else value)
    no_drift = not any(drift_flags)
    ok = live == HF_REVISION and recorded_exact and population_exact and no_drift
    return ok, (
        f"live={live}; expected={HF_REVISION}; provenance_recorded={recorded_exact}; "
        f"population_pinned={population_exact}; unexpected_drift_flags={drift_flags}"
    )


def authoritative_population_check(
    population_audit: pd.DataFrame,
    primary: pd.DataFrame,
    secondary: pd.DataFrame,
) -> tuple[bool, str]:
    authority = pd.read_parquet(PHASE55_TARGETS)
    required_primary = {
        "experiment_name", "has_keyhole", "P", "VX", "LS", "ST", "value__max_depth"
    }
    required_secondary = required_primary | {"value__G3"}
    if not required_primary.issubset(primary) or not required_secondary.issubset(secondary):
        missing = sorted((required_primary - set(primary)) | (required_secondary - set(secondary)))
        return False, f"missing population columns={missing}"

    labels = parse_bool_series(primary["has_keyhole"])
    primary_names = set(primary["experiment_name"].astype(str))
    secondary_names = set(secondary["experiment_name"].astype(str))
    audit_names = set(population_audit["experiment_name"].astype(str))
    authority_names = set(authority["experiment_name"].astype(str))
    ready_names = (
        set(population_audit.loc[parse_bool_series(population_audit["primary_ready"]), "experiment_name"].astype(str))
        if "primary_ready" in population_audit
        else set()
    )
    g3_ready_names = (
        set(population_audit.loc[parse_bool_series(population_audit["secondary_g3_ready"]), "experiment_name"].astype(str))
        if "secondary_g3_ready" in population_audit
        else set()
    )
    ok = all(
        [
            len(population_audit) == 407,
            population_audit["experiment_name"].is_unique,
            audit_names == authority_names,
            len(primary) == PRIMARY_SIZE,
            primary["experiment_name"].is_unique,
            len(secondary) == G3_SIZE,
            secondary["experiment_name"].is_unique,
            int(labels.sum()) == PRIMARY_POSITIVES,
            secondary_names.issubset(primary_names),
            ready_names == primary_names,
            g3_ready_names == secondary_names,
        ]
    )
    return ok, (
        f"audit={len(population_audit)}/407; primary={len(primary)}/405 with "
        f"{int(labels.sum())}/73 Keyhole; g3={len(secondary)}/404; "
        f"primary_ready_match={ready_names == primary_names}; g3_ready_match={g3_ready_names == secondary_names}"
    )


def unchanged_target_check(primary: pd.DataFrame, secondary: pd.DataFrame) -> tuple[bool, str]:
    authority = pd.read_parquet(PHASE55_TARGETS).set_index("experiment_name")
    current = primary.set_index("experiment_name")
    g3 = secondary.set_index("experiment_name")
    authority_primary = authority.loc[current.index]
    authority_g3 = authority.loc[g3.index]

    labels_equal = np.array_equal(
        parse_bool_series(current["has_keyhole"]).to_numpy(),
        parse_bool_series(authority_primary["has_keyhole"]).to_numpy(),
    )
    mappings = {
        "P": "P_W",
        "VX": "VX_m_per_s",
        "LS": "LS_m",
        "ST": "ST_K",
        "value__max_depth": "max_depth_um",
    }
    numeric_equal = all(
        close_arrays(current[left], authority_primary[right]) for left, right in mappings.items()
    )
    g3_equal = close_arrays(g3["value__G3"], authority_g3["G3_persistent_depth_um"])
    depth_formula_equal = (
        "depth_formula" in current
        and current["depth_formula"].astype(str).equals(authority_primary["depth_formula"].astype(str))
    )
    t0_equal = (
        "T0_definition" in current
        and current["T0_definition"].astype(str).equals(authority_primary["T0_definition"].astype(str))
    )
    no_label_modification = (
        "source_label_modified" in current and not parse_bool_series(current["source_label_modified"]).any()
    )
    ok = all(
        [labels_equal, numeric_equal, g3_equal, depth_formula_equal, t0_equal, no_label_modification]
    )
    return ok, (
        f"labels={labels_equal}; inputs/max_depth={numeric_equal}; G3={g3_equal}; "
        f"depth_formula={depth_formula_equal}; T0={t0_equal}; source_label_modified={not no_label_modification}"
    )


def exclusion_check(population_audit: pd.DataFrame, primary: pd.DataFrame) -> tuple[bool, str]:
    ready = parse_bool_series(population_audit["primary_ready"])
    excluded = population_audit.loc[~ready]
    reasons_ok = (
        "primary_exclusion_reasons" in excluded
        and excluded["primary_exclusion_reasons"].fillna("").astype(str).str.strip().ne("").all()
    )
    no_silent = (
        "simulation_silently_removed" in population_audit
        and not parse_bool_series(population_audit["simulation_silently_removed"]).any()
    )
    retained = set(primary["experiment_name"].astype(str)) == set(
        population_audit.loc[ready, "experiment_name"].astype(str)
    )
    ok = len(excluded) == 2 and reasons_ok and no_silent and retained
    return ok, (
        f"retained={int(ready.sum())}; excluded_visible={len(excluded)}; "
        f"reasons_complete={reasons_ok}; silent_removal={not no_silent}"
    )


def empirical_boundary_check(
    primary: pd.DataFrame,
    boundary: pd.DataFrame,
    boundary_validation: pd.DataFrame,
) -> tuple[bool, str]:
    required = {
        "experiment_name", "has_keyhole", "P", "VX", "LS", "ST",
        "empirical_boundary_distance", "nearest_opposite_experiment",
    }
    if not required.issubset(set(primary) | set(boundary)):
        return False, f"required columns absent: {sorted(required - (set(primary) | set(boundary)))}"
    ordered = primary.reset_index(drop=True)
    reference = boundary.set_index("experiment_name").loc[ordered["experiment_name"]].reset_index()
    x = ordered[["P", "VX", "LS", "ST"]].to_numpy(float)
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=0)
    scaled = (x - mean) / scale
    labels = parse_bool_series(ordered["has_keyhole"]).to_numpy()
    names = ordered["experiment_name"].astype(str).to_numpy()
    squared = np.sum((scaled[:, None, :] - scaled[None, :, :]) ** 2, axis=2)
    distances = np.sqrt(np.maximum(squared, 0.0))
    distances[labels[:, None] == labels[None, :]] = np.inf
    nearest_index = np.argmin(distances, axis=1)
    expected_distance = distances[np.arange(len(ordered)), nearest_index]
    expected_names = names[nearest_index]
    distance_ok = close_arrays(reference["empirical_boundary_distance"], expected_distance)
    nearest_ok = np.array_equal(
        reference["nearest_opposite_experiment"].astype(str).to_numpy(), expected_names
    )
    forbidden = [
        column for column in boundary.columns
        if any(token in column.lower() for token in ["max_depth", "g3", "prediction", "probability"])
    ]
    validation_ok = (
        len(boundary_validation) > 0
        and "status" in boundary_validation
        and boundary_validation["status"].eq("PASS").all()
    )
    ok = len(boundary) == PRIMARY_SIZE and distance_ok and nearest_ok and not forbidden and validation_ok
    return ok, (
        f"rows={len(boundary)}; distances={distance_ok}; nearest_opposites={nearest_ok}; "
        f"forbidden_columns={forbidden}; validation_pass={validation_ok}"
    )


def split_checks(
    outer: pd.DataFrame, primary: pd.DataFrame, smoke: bool
) -> tuple[tuple[bool, str], tuple[bool, str]]:
    required = {"benchmark_population", "run_id", "role", "experiment_name", "input_tuple_sha256"}
    if not required.issubset(outer):
        missing = sorted(required - set(outer))
        return (False, f"missing={missing}"), (False, f"missing={missing}")
    frame = outer[outer["benchmark_population"].eq(PRIMARY_POPULATION)]
    runs = sorted(frame["run_id"].unique())
    # A smoke artifact may retain the complete deterministic split design or
    # materialize only its two executed folds.  The active manifest below is
    # the authority for how many runs were actually executed.
    expected_runs = len(runs) in {1, 2, FULL_RUNS} if smoke else len(runs) == FULL_RUNS
    disjoint = True
    group_disjoint = True
    complete_roles = True
    details: list[str] = []
    all_names = set(primary["experiment_name"].astype(str))
    for run_id, group in frame.groupby("run_id", sort=True):
        train = group[group["role"].eq("training_pool")]
        test = group[group["role"].eq("untouched_test")]
        train_names = set(train["experiment_name"].astype(str))
        test_names = set(test["experiment_name"].astype(str))
        train_groups = set(train["input_tuple_sha256"].astype(str))
        test_groups = set(test["input_tuple_sha256"].astype(str))
        disjoint &= train_names.isdisjoint(test_names)
        group_disjoint &= train_groups.isdisjoint(test_groups)
        complete_roles &= train_names | test_names == all_names
        details.append(f"{run_id}:{len(train_names)}/{len(test_names)}")

    repeated_coverage = True
    if not smoke and {"repeat", "fold"}.issubset(frame):
        folds = frame[["run_id", "repeat", "fold"]].drop_duplicates()
        repeated_coverage = (
            folds["repeat"].nunique() == 4
            and folds.groupby("repeat")["fold"].nunique().eq(5).all()
        )
        test_rows = frame[frame["role"].eq("untouched_test")]
        repeated_coverage &= test_rows.groupby(["repeat", "experiment_name"]).size().eq(1).all()
        repeated_coverage &= (
            test_rows.groupby("repeat")["experiment_name"].nunique().eq(PRIMARY_SIZE).all()
        )
    design_ok = expected_runs and complete_roles and repeated_coverage
    separation_ok = disjoint and group_disjoint
    return (
        design_ok,
        f"primary_runs={len(runs)}; complete_roles={complete_roles}; repeated_coverage={repeated_coverage}",
    ), (
        separation_ok,
        f"row_disjoint={disjoint}; input-group-disjoint={group_disjoint}; splits={';'.join(details)}",
    )


def choose_higher_threshold(values: Sequence[float], labels: Sequence[int]) -> float:
    values_array = np.asarray(values, dtype=float)
    labels_array = np.asarray(labels, dtype=int)
    if set(np.unique(labels_array)) != {0, 1}:
        raise ValueError("threshold calibration requires both classes")
    unique = np.unique(values_array)
    if len(unique) == 1:
        magnitude = max(abs(float(unique[0])), 1.0)
        thresholds = np.array([unique[0] - magnitude * 1e-12, unique[0] + magnitude * 1e-12])
    else:
        middle = (unique[:-1] + unique[1:]) / 2.0
        magnitude = max(float(np.ptp(unique)), float(np.max(np.abs(unique))), 1.0)
        thresholds = np.concatenate(
            [[unique[0] - magnitude * 1e-12], middle, [unique[-1] + magnitude * 1e-12]]
        )
    predictions = values_array[:, None] > thresholds[None, :]
    positive = labels_array == 1
    negative = labels_array == 0
    sensitivity = predictions[positive].mean(axis=0)
    specificity = (~predictions[negative]).mean(axis=0)
    accuracy = (predictions == labels_array[:, None]).mean(axis=0)
    median = float(np.median(values_array))
    scale = max(float(np.std(values_array)), 1e-12)
    candidates = pd.DataFrame(
        {
            "threshold": thresholds,
            "balanced_accuracy": (sensitivity + specificity) / 2.0,
            "minimum_class_recall": np.minimum(sensitivity, specificity),
            "accuracy": accuracy,
            "distance": np.abs(thresholds - median) / scale,
        }
    ).sort_values(
        ["balanced_accuracy", "minimum_class_recall", "accuracy", "distance", "threshold"],
        ascending=[False, False, False, True, True],
        kind="mergesort",
    )
    return float(candidates.iloc[0]["threshold"])


def static_fold_check(
    static_predictions: pd.DataFrame,
    outer: pd.DataFrame,
    primary: pd.DataFrame,
    smoke: bool,
) -> tuple[bool, str]:
    frame = static_predictions[
        static_predictions.get("benchmark_population", pd.Series(index=static_predictions.index, dtype=str)).eq(
            PRIMARY_POPULATION
        )
    ]
    runs = sorted(frame["run_id"].unique())
    expected_runs = 1 <= len(runs) <= 2 if smoke else len(runs) == FULL_RUNS
    primary_index = primary.set_index("experiment_name")
    exact_test_sets = True
    thresholds_ok = True
    model_coverage = True
    for run_id, run_rows in frame.groupby("run_id", sort=True):
        split = outer[
            outer["benchmark_population"].eq(PRIMARY_POPULATION) & outer["run_id"].eq(run_id)
        ]
        train_names = split.loc[split["role"].eq("training_pool"), "experiment_name"].astype(str)
        test_names = set(split.loc[split["role"].eq("untouched_test"), "experiment_name"].astype(str))
        expected_threshold = choose_higher_threshold(
            primary_index.loc[train_names, "value__max_depth"],
            parse_bool_series(primary_index.loc[train_names, "has_keyhole"]).astype(int),
        )
        formulations = set(run_rows["formulation"].astype(str))
        model_coverage &= formulations == {"binary", "max_depth"}
        for (_, _), model_rows in run_rows.groupby(["formulation", "model"], sort=True):
            exact_test_sets &= set(model_rows["experiment_name"].astype(str)) == test_names
        continuous = run_rows[run_rows["formulation"].eq("max_depth")]
        thresholds_ok &= continuous["training_only_threshold_um"].map(
            lambda value: close(value, expected_threshold)
        ).all()
    ok = expected_runs and exact_test_sets and thresholds_ok and model_coverage
    return ok, (
        f"runs={len(runs)}; test_sets={exact_test_sets}; training_thresholds={thresholds_ok}; "
        f"both_formulations={model_coverage}"
    )


def active_fairness_check(
    fairness: pd.DataFrame,
    run_manifest: pd.DataFrame,
    initialization: pd.DataFrame,
    smoke: bool,
) -> tuple[bool, str]:
    primary_fair = fairness[fairness["benchmark_population"].eq(PRIMARY_POPULATION)]
    primary_runs = run_manifest[run_manifest["benchmark_population"].eq(PRIMARY_POPULATION)]
    executed_run_count = primary_runs["run_id"].nunique()
    executed_runs_ok = (
        1 <= executed_run_count <= 2 if smoke else executed_run_count == FULL_RUNS
    )
    flag_ok = all(
        [
            all_true(primary_fair, "candidate_pool_is_outer_training_only"),
            all_true(primary_fair, "test_set_never_queried"),
            all_false(primary_fair, "test_labels_used_for_fitting"),
            all_false(primary_fair, "test_responses_used_for_fitting"),
            all_false(primary_fair, "hidden_pool_labels_used_for_acquisition"),
            all_false(primary_fair, "hidden_pool_responses_used_for_acquisition"),
            all_false(primary_fair, "empirical_boundary_used_for_acquisition"),
        ]
    )
    shared = True
    methods_per_run: list[int] = []
    for run_id, group in primary_fair.groupby("run_id", sort=True):
        shared &= group["split_sha256"].nunique() == 1 and group["warm_start_sha256"].nunique() == 1
        methods_per_run.append(group["method"].nunique())
    expected_method_count = (
        bool(methods_per_run) and min(methods_per_run) >= 2
        if smoke
        else bool(methods_per_run) and set(methods_per_run) == {8}
    )
    manifests_match = True
    if {"split_sha256", "warm_start_sha256"}.issubset(primary_runs):
        for run_id, group in primary_runs.groupby("run_id", sort=True):
            manifests_match &= group["split_sha256"].nunique() == 1
            manifests_match &= group["warm_start_sha256"].nunique() == 1
    init_ok = (
        len(initialization[initialization["benchmark_population"].eq(PRIMARY_POPULATION)]) > 0
        and all_true(
            initialization[initialization["benchmark_population"].eq(PRIMARY_POPULATION)],
            "same_for_all_methods",
        )
    )
    ok = (
        flag_ok
        and shared
        and expected_method_count
        and manifests_match
        and init_ok
        and executed_runs_ok
    )
    return ok, (
        f"information_flags={flag_ok}; shared_split_warm={shared}; methods/run={methods_per_run}; "
        f"manifest_hashes={manifests_match}; initialization={init_ok}; "
        f"executed_primary_runs={executed_run_count}"
    )


def warm_start_check(
    initialization: pd.DataFrame,
    queries: pd.DataFrame,
) -> tuple[bool, str]:
    consistent = True
    counted = True
    class_counts = True
    checked = 0
    for (population, run_id), init_group in initialization.groupby(
        ["benchmark_population", "run_id"], sort=True
    ):
        effective_values = pd.to_numeric(init_group["effective_warm_start"], errors="coerce").dropna().unique()
        if len(effective_values) != 1:
            consistent = False
            continue
        effective = int(effective_values[0])
        consistent &= effective >= 12
        run_queries = queries[
            queries["benchmark_population"].eq(population) & queries["run_id"].eq(run_id)
        ]
        sequences = []
        for _, method_rows in run_queries.groupby("method", sort=True):
            warm = method_rows[method_rows["query_order"].le(effective)].sort_values("query_order")
            sequences.append(tuple(warm["experiment_name"].astype(str)))
            counted &= len(warm) == effective and list(warm["query_order"].astype(int)) == list(
                range(1, effective + 1)
            )
            labels = pd.to_numeric(warm["revealed_has_keyhole"], errors="coerce").astype(int)
            class_counts &= labels.nunique() == 2
        consistent &= bool(sequences) and len(set(sequences)) == 1
        checked += 1
    init_flags = all(
        [
            all_false(initialization, "hidden_labels_used_to_skip_candidates"),
            all_true(initialization, "sequential_stop_used_revealed_labels_only"),
        ]
    )
    ok = checked > 0 and consistent and counted and class_counts and init_flags
    return ok, (
        f"run_populations={checked}; identical_sequences={consistent}; counted={counted}; "
        f"both_classes={class_counts}; revealed-only-stop={init_flags}"
    )


def query_leakage_check(queries: pd.DataFrame, outer: pd.DataFrame) -> tuple[bool, str]:
    membership_ok = True
    unique_ok = True
    for (population, run_id, method), group in queries.groupby(
        ["benchmark_population", "run_id", "method"], sort=True
    ):
        split = outer[
            outer["benchmark_population"].eq(population) & outer["run_id"].eq(run_id)
        ]
        train_names = set(split.loc[split["role"].eq("training_pool"), "experiment_name"].astype(str))
        test_names = set(split.loc[split["role"].eq("untouched_test"), "experiment_name"].astype(str))
        queried = list(group.sort_values("query_order")["experiment_name"].astype(str))
        membership_ok &= set(queried).issubset(train_names) and set(queried).isdisjoint(test_names)
        unique_ok &= len(queried) == len(set(queried))
    flags_ok = all(
        [
            all_false(queries, "boundary_score_consulted_before_selection"),
            all_false(queries, "hidden_label_consulted_before_selection"),
            all_false(queries, "hidden_physical_response_consulted_before_selection"),
        ]
    )
    known_ok = (
        "known_before_query" in queries
        and queries["known_before_query"].astype(str).eq("P,VX,LS,ST").all()
    )
    ok = len(queries) > 0 and membership_ok and unique_ok and flags_ok and known_ok
    return ok, (
        f"training_pool_only={membership_ok}; unique_queries={unique_ok}; guard_flags={flags_ok}; "
        f"known_before_query={known_ok}"
    )


def threshold_history_check(
    thresholds: pd.DataFrame,
    queries: pd.DataFrame,
) -> tuple[bool, str]:
    scopes = (
        len(thresholds) > 0
        and thresholds["training_scope"].astype(str).eq("queried_only").all()
        and all_false(thresholds, "test_information_used")
        and all_false(thresholds, "unqueried_pool_information_used")
    )
    recomputed = True
    g3_present = False
    max_present = False
    checked = 0
    for row in thresholds.to_dict("records"):
        formulation = str(row["formulation"])
        max_present |= formulation == "max_depth"
        g3_present |= formulation == "g3"
        budget = int(row["budget"])
        selected = queries[
            queries["benchmark_population"].eq(row["benchmark_population"])
            & queries["run_id"].eq(row["run_id"])
            & queries["method"].eq(row["method"])
            & queries["query_order"].le(budget)
        ].sort_values("query_order")
        response_column = "revealed_max_depth_um" if formulation == "max_depth" else "revealed_G3_um"
        if len(selected) != budget or response_column not in selected:
            recomputed = False
            continue
        expected = choose_higher_threshold(
            pd.to_numeric(selected[response_column], errors="coerce"),
            pd.to_numeric(selected["revealed_has_keyhole"], errors="coerce").astype(int),
        )
        recomputed &= close(row["threshold"], expected)
        checked += 1
    ok = scopes and recomputed and max_present and g3_present and checked == len(thresholds)
    return ok, (
        f"rows={len(thresholds)}; queried_only={scopes}; independently_recomputed={recomputed}; "
        f"max_depth={max_present}; G3={g3_present}"
    )


def latent_uncertainty_check(
    curves: pd.DataFrame,
    predictions: pd.DataFrame,
    queries: pd.DataFrame,
) -> tuple[bool, str]:
    continuous_curves = curves[curves["formulation"].isin(["max_depth", "g3"])]
    kernels = continuous_curves.get("kernel", pd.Series(dtype=str)).fillna("").astype(str)
    no_white_kernel = len(kernels) > 0 and not kernels.str.contains("WhiteKernel", case=False).any()
    continuous_predictions = predictions[predictions["formulation"].isin(["max_depth", "g3"])]
    latent_positive = (
        len(continuous_predictions) > 0
        and pd.to_numeric(continuous_predictions["latent_std"], errors="coerce").gt(0).all()
    )
    metadata_ok = True
    selected_active = queries[
        queries["formulation"].isin(["max_depth", "g3"])
        & queries["selection_stage"].eq("active_acquisition")
    ]
    for text in selected_active.get("acquisition_metadata_json", pd.Series(dtype=str)).astype(str):
        metadata = json.loads(text)
        definition = str(metadata.get("acquisition_definition", ""))
        if definition != "minimum_abs_mean_minus_threshold":
            metadata_ok &= "selected_sigma_latent" in metadata
        metadata_ok &= "noise" not in " ".join(metadata).lower()
    source_text = SOURCE.read_text(encoding="utf-8")
    source_ok = "WhiteKernel" not in source_text and "selected_sigma_latent" in source_text
    ok = no_white_kernel and latent_positive and metadata_ok and source_ok
    return ok, (
        f"no_white_kernel={no_white_kernel}; positive_latent_std={latent_positive}; "
        f"acquisition_metadata={metadata_ok}; source_guard={source_ok}"
    )


def probability_checks(
    static_predictions: pd.DataFrame,
    active_predictions: pd.DataFrame,
) -> tuple[tuple[bool, str], tuple[bool, str]]:
    binary_frames = []
    continuous_frames = []
    for source_name, frame in [("static", static_predictions), ("active", active_predictions)]:
        binary = frame[frame["formulation"].eq("binary")].copy()
        binary["source"] = source_name
        binary_frames.append(binary)
        continuous = frame[frame["formulation"].isin(["max_depth", "g3"])].copy()
        if "probability_available" in continuous:
            continuous = continuous[parse_bool_series(continuous["probability_available"])]
        continuous["source"] = source_name
        continuous_frames.append(continuous)

    binary = pd.concat(binary_frames, ignore_index=True)
    probabilities = pd.to_numeric(binary["keyhole_probability"], errors="coerce")
    labels = pd.to_numeric(binary["predicted_keyhole"], errors="coerce").astype(int)
    binary_ok = (
        len(binary) > 0
        and probabilities.notna().all()
        and probabilities.between(0, 1, inclusive="both").all()
        and np.array_equal(labels.to_numpy(), probabilities.ge(0.5).astype(int).to_numpy())
    )

    continuous = pd.concat(continuous_frames, ignore_index=True)
    active_response = continuous.get(
        "predicted_response", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    static_response = continuous.get(
        "predicted_max_depth_um", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    continuous["predicted_response"] = active_response.combine_first(static_response)
    active_sigma = continuous.get(
        "latent_std", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    static_sigma = continuous.get(
        "latent_std_um", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    continuous["latent_std"] = active_sigma.combine_first(static_sigma)
    active_threshold = continuous.get(
        "threshold", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    static_threshold = continuous.get(
        "training_only_threshold_um", pd.Series(np.nan, index=continuous.index, dtype=float)
    )
    continuous["threshold"] = active_threshold.combine_first(static_threshold)
    mu = pd.to_numeric(continuous["predicted_response"], errors="coerce").to_numpy(float)
    sigma = pd.to_numeric(continuous["latent_std"], errors="coerce").to_numpy(float)
    threshold = pd.to_numeric(continuous["threshold"], errors="coerce").to_numpy(float)
    expected = np.clip(norm.cdf((mu - threshold) / np.maximum(sigma, 1e-12)), 1e-12, 1 - 1e-12)
    recorded = pd.to_numeric(continuous["keyhole_probability"], errors="coerce").to_numpy(float)
    predicted = pd.to_numeric(continuous["predicted_keyhole"], errors="coerce").astype(int).to_numpy()
    continuous_ok = (
        len(continuous) > 0
        and np.isfinite(mu).all()
        and np.isfinite(sigma).all()
        and np.isfinite(threshold).all()
        and close_arrays(expected, recorded)
        and np.array_equal(predicted, (mu > threshold).astype(int))
    )
    return (
        binary_ok,
        f"rows={len(binary)}; probabilities_in_range_and_0.5_labels={binary_ok}",
    ), (
        continuous_ok,
        f"rows={len(continuous)}; Gaussian_tail_and_response_threshold={continuous_ok}",
    )


def boundary_prediction_reconciliation(
    predictions: pd.DataFrame,
    curves: pd.DataFrame,
) -> tuple[bool, str]:
    exact_flags = True
    exact_metrics = True
    checked = 0
    keys = ["benchmark_population", "run_id", "method", "budget"]
    for key, group in predictions.groupby(keys, sort=True):
        group = group.copy()
        names = group["experiment_name"].astype(str)
        distances = pd.to_numeric(
            group["empirical_boundary_distance_evaluation_only"], errors="coerce"
        )
        order = pd.DataFrame({"name": names, "distance": distances}, index=group.index).sort_values(
            ["distance", "name"], kind="mergesort"
        )
        curve_match = curves[
            curves["benchmark_population"].eq(key[0])
            & curves["run_id"].eq(key[1])
            & curves["method"].eq(key[2])
            & curves["budget"].eq(key[3])
        ]
        if len(curve_match) != 1:
            exact_metrics = False
            continue
        curve_row = curve_match.iloc[0]
        for q in (20, 30):
            count = int(math.ceil(q / 100.0 * len(group)))
            expected_names = set(order.head(count)["name"])
            flag_column = f"test_q{q}"
            actual_names = set(group.loc[parse_bool_series(group[flag_column]), "experiment_name"].astype(str))
            exact_flags &= actual_names == expected_names and len(actual_names) == count
            mask = names.isin(expected_names).to_numpy()
            labels = pd.to_numeric(group["has_keyhole"], errors="coerce").astype(int).to_numpy()
            predicted = pd.to_numeric(group["predicted_keyhole"], errors="coerce").astype(int).to_numpy()
            expected_error = float(np.mean(labels[mask] != predicted[mask]))
            exact_metrics &= close(curve_row[f"q{q}_error"], expected_error)
        checked += 1
    ok = checked > 0 and exact_flags and exact_metrics
    return ok, (
        f"raw_prediction_checkpoints={checked}; q20/q30_membership={exact_flags}; "
        f"curve_errors={exact_metrics}"
    )


def budget_check(
    run_manifest: pd.DataFrame,
    initialization: pd.DataFrame,
    queries: pd.DataFrame,
    curves: pd.DataFrame,
    smoke: bool,
) -> tuple[bool, str]:
    final_values = pd.to_numeric(run_manifest["final_budget"], errors="coerce").dropna().astype(int).unique()
    expected_final = len(final_values) == 1 and (
        int(final_values[0]) == FULL_FINAL_BUDGET if not smoke else 20 <= int(final_values[0]) <= 30
    )
    final_budget = int(final_values[0]) if len(final_values) == 1 else -1
    contiguous = True
    query_counts = True
    for key, group in curves.groupby(["benchmark_population", "run_id", "method"], sort=True):
        budgets = sorted(pd.to_numeric(group["budget"], errors="coerce").astype(int).tolist())
        init = initialization[
            initialization["benchmark_population"].eq(key[0])
            & initialization["run_id"].eq(key[1])
        ]
        effective = int(pd.to_numeric(init["effective_warm_start"], errors="coerce").dropna().iloc[0])
        contiguous &= budgets == list(range(effective, final_budget + 1))
        method_queries = queries[
            queries["benchmark_population"].eq(key[0])
            & queries["run_id"].eq(key[1])
            & queries["method"].eq(key[2])
        ].sort_values("query_order")
        query_counts &= len(method_queries) == final_budget
        query_counts &= list(method_queries["query_order"].astype(int)) == list(range(1, final_budget + 1))
    ok = expected_final and contiguous and query_counts
    return ok, (
        f"final_budget={final_values.tolist()}; expected_mode={expected_final}; integer_curves={contiguous}; "
        f"query_accounting={query_counts}"
    )


def random_trajectory_check(queries: pd.DataFrame) -> tuple[bool, str]:
    comparisons = [
        (PRIMARY_POPULATION, ["max_depth_random", "binary_random"]),
        (
            G3_POPULATION,
            ["g3_random", "max_depth_g3_common_random", "binary_g3_common_random"],
        ),
    ]
    exact = True
    checked = 0
    for population, methods in comparisons:
        subset = queries[queries["benchmark_population"].eq(population)]
        present = [method for method in methods if method in set(subset["method"].astype(str))]
        if len(present) < 2:
            if population == PRIMARY_POPULATION:
                exact = False
            continue
        for run_id, group in subset[subset["method"].isin(present)].groupby("run_id", sort=True):
            sequences = [
                tuple(
                    group[group["method"].eq(method)]
                    .sort_values("query_order")["experiment_name"]
                    .astype(str)
                )
                for method in present
            ]
            exact &= len(set(sequences)) == 1
            checked += 1
    return checked > 0 and exact, f"matched_random_run_sets={checked}; identical={exact}"


def trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    return float(np.sum(np.diff(x) * (y[:-1] + y[1:]) / 2.0))


def aulc_check(
    aulc: pd.DataFrame,
    curves: pd.DataFrame,
    initialization: pd.DataFrame,
) -> tuple[bool, str]:
    exact = True
    checked = 0
    common_starts = initialization.groupby("benchmark_population")["effective_warm_start"].max().to_dict()
    for row in aulc.to_dict("records"):
        group = curves[
            curves["benchmark_population"].eq(row["benchmark_population"])
            & curves["run_id"].eq(row["run_id"])
            & curves["method"].eq(row["method"])
        ].sort_values("budget")
        if len(group) == 0:
            exact = False
            continue
        available_start = int(group["budget"].min())
        common_start = int(common_starts[row["benchmark_population"]])
        final_budget = int(group["budget"].max())
        common = group[group["budget"].ge(common_start)]
        exact &= int(row["available_start_budget"]) == available_start
        exact &= int(row["common_start_budget"]) == common_start
        exact &= int(row["final_budget"]) == final_budget
        for metric in ["q20_error", "q30_error", "balanced_accuracy"]:
            expected_common = trapezoid(
                common[metric].to_numpy(float), common["budget"].to_numpy(float)
            ) / max(final_budget - common_start, 1)
            expected_warm = trapezoid(
                group[metric].to_numpy(float), group["budget"].to_numpy(float)
            ) / max(final_budget - available_start, 1)
            exact &= close(row[f"common_normalized_aulc__{metric}"], expected_common)
            exact &= close(row[f"warm_relative_normalized_aulc__{metric}"], expected_warm)
        checked += 1
    expected_rows = curves.groupby(["benchmark_population", "run_id", "method"]).ngroups
    ok = checked == expected_rows and exact
    return ok, f"rows={checked}/{expected_rows}; independently_integrated={exact}"


def tolerance_check(tolerance: pd.DataFrame, curves: pd.DataFrame) -> tuple[bool, str]:
    exact = True
    checked = 0
    for row in tolerance.to_dict("records"):
        group = curves[
            curves["benchmark_population"].eq(row["benchmark_population"])
            & curves["run_id"].eq(row["run_id"])
            & curves["method"].eq(row["method"])
        ].sort_values("budget")
        values = pd.to_numeric(group[row["metric"]], errors="coerce")
        target = float(row["target"])
        eligible = values.ge(target) if row["direction"] == "at_least" else values.le(target)
        reached = group[eligible]
        expected_query = int(reached.iloc[0]["budget"]) if len(reached) else math.nan
        recorded_query = pd.to_numeric(pd.Series([row["queries_required"]]), errors="coerce").iloc[0]
        query_ok = (pd.isna(recorded_query) and math.isnan(expected_query)) or close(
            recorded_query, expected_query, atol=0, rtol=0
        )
        expected_status = "reached" if len(reached) else "not reached"
        exact &= query_ok and row["status"] == expected_status and bool(row["no_extrapolation"])
        checked += 1
    groups = curves.groupby(["benchmark_population", "run_id", "method"]).ngroups
    expected_rows = groups * 9
    return checked == expected_rows and exact, (
        f"rows={checked}/{expected_rows}; first_crossings_and_no_extrapolation={exact}"
    )


def paired_check(
    comparisons: pd.DataFrame,
    bootstrap: pd.DataFrame,
    aulc: pd.DataFrame,
    smoke: bool,
) -> tuple[bool, str]:
    if smoke and comparisons.empty and bootstrap.empty:
        return True, "paired inference intentionally omitted from the reduced smoke run"
    primary = aulc[aulc["benchmark_population"].eq(PRIMARY_POPULATION)]
    exact = True
    checked = 0
    for row in comparisons.to_dict("records"):
        a = primary[primary["method"].eq(row["method_a"])].set_index("run_id")
        b = primary[primary["method"].eq(row["method_b"])].set_index("run_id")
        common = sorted(set(a.index) & set(b.index))
        differences = a.loc[common, row["metric"]].to_numpy(float) - b.loc[
            common, row["metric"]
        ].to_numpy(float)
        expected_count = len(common)
        exact &= expected_count > 0
        exact &= int(row["paired_run_count"]) == expected_count
        exact &= close(row["mean_paired_difference_a_minus_b"], np.mean(differences))
        exact &= close(row["median_paired_difference_a_minus_b"], np.median(differences))
        if not smoke:
            exact &= expected_count == FULL_RUNS
        checked += 1
    keys = ["comparison", "method_a", "method_b", "metric"]
    merged = comparisons.merge(bootstrap, on=keys, how="outer", suffixes=("_comparison", "_bootstrap"), indicator=True)
    bootstrap_match = len(merged) > 0 and merged["_merge"].eq("both").all()
    if bootstrap_match:
        resamples = pd.to_numeric(bootstrap["bootstrap_resamples"], errors="coerce")
        bootstrap_match &= resamples.eq(FULL_PAIRED_BOOTSTRAPS).all() if not smoke else resamples.gt(0).all()
        bootstrap_match &= (
            pd.to_numeric(bootstrap["bootstrap_ci_low"], errors="coerce")
            <= pd.to_numeric(bootstrap["bootstrap_median"], errors="coerce")
        ).all()
        bootstrap_match &= (
            pd.to_numeric(bootstrap["bootstrap_median"], errors="coerce")
            <= pd.to_numeric(bootstrap["bootstrap_ci_high"], errors="coerce")
        ).all()
        bootstrap_match &= all_false(bootstrap, "formal_hypothesis_test")
    ok = checked > 0 and exact and bootstrap_match
    return ok, (
        f"comparisons={checked}; matched_run_recompute={exact}; bootstrap_keyed_ordered={bootstrap_match}"
    )


def g3_check(
    secondary: pd.DataFrame,
    g3_summary: pd.DataFrame,
    comparison: pd.DataFrame,
    thresholds: pd.DataFrame,
) -> tuple[bool, str]:
    summary_population_ok = len(g3_summary) > 0 and set(
        g3_summary.get("formulation", pd.Series(dtype=str)).astype(str)
    ) == {"g3"}
    g3_thresholds = thresholds[thresholds["formulation"].eq("g3")]
    comparison_ok = len(comparison) > 0
    serialized = (
        " ".join(map(str, g3_summary.columns))
        + " "
        + g3_summary.astype(str).to_csv(index=False)
        + " "
        + comparison.astype(str).to_csv(index=False)
    ).lower()
    secondary_wording = "secondary" in serialized or summary_population_ok
    ok = (
        len(secondary) == G3_SIZE
        and summary_population_ok
        and len(g3_thresholds) > 0
        and comparison_ok
        and secondary_wording
    )
    return ok, (
        f"population={len(secondary)}/404; summary_population={summary_population_ok}; "
        f"threshold_rows={len(g3_thresholds)}; comparison_rows={len(comparison)}; secondary={secondary_wording}"
    )


def domain_shift_check(domain: pd.DataFrame) -> tuple[bool, str]:
    expected_routes = {
        "all_old_to_new", "new_to_all_old", "old_local_to_new", "old_remote_to_new"
    }
    routes = set(domain.get("route", pd.Series(dtype=str)).astype(str))
    status = domain.get("route_status", pd.Series(dtype=str)).astype(str).str.lower()
    secondary = len(domain) > 0 and status.str.contains("secondary").all()
    tiny_remote = (
        len(domain[domain["route"].eq("old_remote_to_new")]) > 0
        and domain.loc[domain["route"].eq("old_remote_to_new"), "route_status"]
        .astype(str)
        .str.lower()
        .str.contains("tiny|small|caution")
        .all()
    )
    formulations = domain.groupby("route")["formulation"].apply(set).to_dict() if len(domain) else {}
    both = all(formulations.get(route) == {"binary", "max_depth"} for route in expected_routes)
    oracle_guard = all_true(domain, "target_oracle_unavailable_to_valid_method")
    ok = routes == expected_routes and secondary and tiny_remote and both and oracle_guard
    return ok, (
        f"routes={sorted(routes)}; secondary_only={secondary}; tiny-old-remote-caution={tiny_remote}; "
        f"matched_formulations={both}; target_oracle_unavailable={oracle_guard}"
    )


def decision_check(decision: pd.DataFrame, scorecard: pd.DataFrame, results_text: str) -> tuple[bool, str]:
    serialized = decision.astype(str).to_csv(index=False) + "\n" + results_text
    found = [value for value in ALLOWED_DECISIONS if value in serialized]
    no_replacement = not any(
        phrase in serialized.lower()
        for phrase in ["replace ioan", "manual labels replaced"]
    )
    explicit_guards = all(
        [
            all_true(decision, "manual_annotation_remains_reference"),
            all_false(decision, "threshold_is_universal_physical_constant"),
            all_false(decision, "causal_claim"),
        ]
    )
    scorecard_ok = len(scorecard) > 0 and len(decision) == 1
    ok = len(found) == 1 and no_replacement and explicit_guards and scorecard_ok
    return ok, (
        f"decision={found}; scorecard_rows={len(scorecard)}; decision_rows={len(decision)}; "
        f"manual_reference_preserved={no_replacement}; explicit_guards={explicit_guards}"
    )


def notebook_check(smoke: bool) -> tuple[bool, str]:
    if smoke and not NOTEBOOK.is_file():
        return True, "teaching notebook intentionally deferred until after the reduced computational smoke run"
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8-sig"))
    code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
    markdown = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "markdown"]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    execution = [cell.get("execution_count") for cell in code_cells]
    executed = all(value is not None for value in execution)
    sequential = executed and execution == list(range(1, len(code_cells) + 1))
    headings = 0
    for cell in markdown:
        source = cell.get("source", "")
        source_text = "".join(source) if isinstance(source, list) else str(source)
        headings += sum(
            line.lstrip().startswith("## ") for line in source_text.splitlines()
        )
    execution_ok = True if smoke else sequential
    ok = len(code_cells) > 0 and headings >= 25 and not errors and execution_ok
    return ok, (
        f"code_cells={len(code_cells)}; section_headings={headings}; stored_errors={len(errors)}; "
        f"executed={executed}; sequential={sequential}; smoke={smoke}"
    )


def resolve_figure_path(output_dir: Path, value: str) -> Path:
    path = Path(value)
    candidates = [path] if path.is_absolute() else [output_dir / path, ROOT / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def figure_check(figures: pd.DataFrame, output_dir: Path, smoke: bool) -> tuple[bool, str]:
    if smoke and figures.empty:
        return True, "descriptive figures intentionally omitted from the reduced smoke run"
    column = next(
        (name for name in ["figure", "relative_path", "path", "file"] if name in figures), None
    )
    if column is None:
        return False, "figure manifest has no path column"
    valid = []
    for value in figures[column].astype(str):
        path = resolve_figure_path(output_dir, value)
        try:
            with Image.open(path) as image:
                image.verify()
            valid.append(path.stat().st_size > 0)
        except Exception:
            valid.append(False)
    count_ok = len(figures) >= (1 if smoke else 40)
    metadata_column = next(
        (
            name
            for name in [
                "population_units_status_caveat_visible",
                "population_units_method_caveat_in_figure",
            ]
            if name in figures
        ),
        "",
    )
    metadata_ok = bool(metadata_column) and all_true(figures, metadata_column)
    meaningful_ok = (
        all_true(figures, "meaningful_explanatory_figure")
        if "meaningful_explanatory_figure" in figures
        else True
    )
    unique = figures[column].astype(str).is_unique
    ok = count_ok and bool(valid) and all(valid) and metadata_ok and meaningful_ok and unique
    return ok, (
        f"figures={len(figures)}; minimum={1 if smoke else 40}; valid={sum(valid)}/{len(valid)}; "
        f"visible-metadata={metadata_ok}; meaningful={meaningful_ok}; unique={unique}"
    )


def build_manifest(output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "output_manifest.csv" or path.suffix.lower() == ".log":
            continue
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return pd.DataFrame(rows, columns=["relative_path", "size_bytes", "sha256"])


def manifest_check(output_dir: Path, manifest: pd.DataFrame, smoke: bool = False) -> tuple[bool, str]:
    required = {"relative_path", "size_bytes", "sha256"}
    if not required.issubset(manifest):
        return False, f"missing manifest columns={sorted(required - set(manifest))}"
    missing: list[str] = []
    mismatched: list[str] = []
    paths: list[str] = []
    for row in manifest.to_dict("records"):
        relative = str(row["relative_path"]).replace("\\", "/")
        paths.append(relative)
        path = ROOT / Path(relative)
        if not path.is_file():
            missing.append(relative)
            continue
        if path.stat().st_size != int(row["size_bytes"]) or sha256_file(path) != str(row["sha256"]).lower():
            mismatched.append(relative)
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "output_manifest.csv" and path.suffix.lower() != ".log"
    }
    coverage = set(paths) == actual
    unique = len(paths) == len(set(paths))
    expected_covered = all(
        (output_dir / name).relative_to(ROOT).as_posix() in set(paths)
        for name in EXPECTED_OUTPUT_ARTIFACTS
        if name != "output_manifest.csv"
        and (not smoke or name not in SMOKE_OPTIONAL_ARTIFACTS)
    )
    ok = not missing and not mismatched and coverage and unique and expected_covered
    return ok, (
        f"rows={len(manifest)}; missing={len(missing)}; mismatched={len(mismatched)}; "
        f"complete_coverage={coverage}; unique={unique}; named_artifacts_covered={expected_covered}"
    )


def exact_artifact_check(
    output_dir: Path, load_errors: Mapping[str, str], smoke: bool = False
) -> tuple[bool, str]:
    named = {path.name for path in output_dir.iterdir() if path.is_file()}
    expected = set(EXPECTED_OUTPUT_ARTIFACTS) - (SMOKE_OPTIONAL_ARTIFACTS if smoke else set())
    missing = sorted(expected - named)
    extra = sorted(named - expected)
    parse_errors = {name: error for name, error in load_errors.items() if name in expected}
    notebook_loaded = False
    notebook_error = ""
    try:
        json.loads(NOTEBOOK.read_text(encoding="utf-8-sig"))
        notebook_loaded = True
    except Exception as exc:
        notebook_error = f"{type(exc).__name__}: {exc}"
    notebook_ok = notebook_loaded or smoke
    ok = not missing and not extra and not parse_errors and notebook_ok
    return ok, (
        f"named={len(named)}/{len(expected)}; missing={missing}; extra={extra}; "
        f"parse_errors={list(parse_errors)}; notebook_loaded={notebook_loaded}; smoke={smoke}"
        f"{'; '+notebook_error if notebook_error and not smoke else ''}"
    )


def build_validation(loaded: Mapping[str, Any], smoke: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    primary = loaded["primary_common_population.csv"]
    secondary = loaded["secondary_g3_common_population.csv"]
    population_audit = loaded["population_audit.csv"]
    outer = loaded["outer_split_manifest.csv"]
    fairness = loaded["fairness_audit.csv"]
    static_predictions = loaded["static_model_fold_predictions.csv"]
    run_manifest = loaded["active_run_manifest.csv"]
    initialization = loaded["active_initialization_audit.csv"]
    queries = loaded["active_query_history.csv"]
    predictions = loaded["active_prediction_history.csv"]
    thresholds = loaded["online_threshold_history.csv"]
    curves = loaded["active_learning_curve_summary.csv"]
    aulc = loaded["active_learning_aulc_summary.csv"]
    tolerance = loaded["queries_to_tolerance.csv"]
    paired = loaded["active_paired_method_comparisons.csv"]
    paired_bootstrap = loaded["active_paired_bootstrap_intervals.csv"]

    add_check(rows, "V01", "Exact Phase 6 branch and published Phase 5.5 parent", "provenance", published_phase55_audit)
    add_check(
        rows,
        "V02",
        "Exact live and recorded Hugging Face revision with no drift",
        "provenance",
        lambda: hf_revision_check(
            loaded["hf_revision_audit.json"], loaded["input_provenance.json"], primary
        ),
    )
    add_check(
        rows,
        "V03",
        "Exact 407 retained, 405 primary, 404 G3, and 73-positive populations",
        "population",
        lambda: authoritative_population_check(population_audit, primary, secondary),
    )
    add_check(
        rows,
        "V04",
        "Manual labels, inputs, maximum depth, G3, and T0 definitions are unchanged",
        "definition",
        lambda: unchanged_target_check(primary, secondary),
    )
    add_check(
        rows,
        "V05",
        "All unavailable rows remain visible with explicit reasons and no silent exclusion",
        "population",
        lambda: exclusion_check(population_audit, primary),
    )
    add_check(
        rows,
        "V06",
        "Empirical boundary reference independently uses only four inputs and manual labels",
        "boundary",
        lambda: empirical_boundary_check(
            primary,
            loaded["empirical_boundary_reference.csv"],
            loaded["empirical_boundary_validation.csv"],
        ),
    )
    split_design, split_disjoint = split_checks(outer, primary, smoke)
    add_check(rows, "V07", "Repeated held-out primary outer-run design is complete", "split", lambda: split_design)
    add_check(rows, "V08", "Every outer split is row- and physical-input-group-disjoint", "split", lambda: split_disjoint)
    add_check(
        rows,
        "V09",
        "Static Binary and Max-Depth models share held-out rows and training-only thresholds",
        "static",
        lambda: static_fold_check(static_predictions, outer, primary, smoke),
    )
    add_check(
        rows,
        "V10",
        "All active methods share splits and warm starts with fail-closed fairness flags",
        "fairness",
        lambda: active_fairness_check(fairness, run_manifest, initialization, smoke),
    )
    add_check(
        rows,
        "V11",
        "Shared sequential warm starts contain both classes and count every extra reveal",
        "warm_start",
        lambda: warm_start_check(initialization, queries),
    )
    add_check(
        rows,
        "V12",
        "No test row, hidden label, hidden response, or boundary score enters acquisition",
        "leakage",
        lambda: query_leakage_check(queries, outer),
    )
    add_check(
        rows,
        "V13",
        "Max-Depth and G3 thresholds exactly recompute from queried rows only",
        "threshold",
        lambda: threshold_history_check(thresholds, queries),
    )
    add_check(
        rows,
        "V14",
        "Continuous acquisition uses latent uncertainty without a learned nugget",
        "surrogate",
        lambda: latent_uncertainty_check(curves, predictions, queries),
    )
    binary_probability, continuous_probability = probability_checks(static_predictions, predictions)
    add_check(rows, "V15", "Binary probabilities and 0.5 decisions reconcile", "prediction", lambda: binary_probability)
    add_check(
        rows,
        "V16",
        "Continuous Gaussian-tail probabilities and point decisions reconcile",
        "prediction",
        lambda: continuous_probability,
    )
    add_check(
        rows,
        "V17",
        "q20/q30 membership and errors reconcile from raw checkpoint predictions",
        "boundary",
        lambda: boundary_prediction_reconciliation(predictions, curves),
    )
    add_check(
        rows,
        "V18",
        "Integer simulator-query accounting is complete through the final budget",
        "budget",
        lambda: budget_check(run_manifest, initialization, queries, curves, smoke),
    )
    add_check(
        rows,
        "V19",
        "Random query trajectories are shared across formulations",
        "fairness",
        lambda: random_trajectory_check(queries),
    )
    add_check(
        rows,
        "V20",
        "AULC values independently recompute from raw integer-budget curves",
        "summary",
        lambda: aulc_check(aulc, curves, initialization),
    )
    add_check(
        rows,
        "V21",
        "Queries-to-tolerance independently recompute without extrapolation",
        "summary",
        lambda: tolerance_check(tolerance, curves),
    )
    add_check(
        rows,
        "V22",
        "Paired comparisons use matched runs and ordered descriptive bootstrap intervals",
        "summary",
        lambda: paired_check(paired, paired_bootstrap, aulc, smoke),
    )
    add_check(
        rows,
        "V23",
        "G3 is separately documented on the 404-row secondary population",
        "secondary",
        lambda: g3_check(
            secondary,
            loaded["g3_secondary_active_summary.csv"],
            loaded["max_depth_vs_g3_summary.csv"],
            thresholds,
        ),
    )
    add_check(
        rows,
        "V24",
        "Every old/new domain-transfer route remains a secondary stress test",
        "secondary",
        lambda: domain_shift_check(loaded["domain_transfer_model_summary.csv"]),
    )
    add_check(
        rows,
        "V25",
        "Final decision uses one predeclared formulation outcome and preserves manual labels",
        "decision",
        (
            (lambda: (True, "final scientific decision intentionally omitted from smoke"))
            if smoke
            else lambda: decision_check(
                loaded["phase6_final_decision.csv"],
                loaded["phase6_formulation_scorecard.csv"],
                str(loaded["results_summary.md"] or ""),
            )
        ),
    )
    add_check(rows, "V26", "Teaching notebook is explanatory and has zero stored errors", "notebook", lambda: notebook_check(smoke))
    add_check(
        rows,
        "V27",
        "At least 40 meaningful full-run figures exist and validate",
        "figure",
        lambda: figure_check(loaded["figure_manifest.csv"], SMOKE_DIR if smoke else OUTPUT_DIR, smoke),
    )
    # These two are finalized after validator-generated CSVs and the refreshed
    # non-self-referential manifest have been written.
    add_check(rows, "V28", "Exactly 49 named artifacts plus the notebook load successfully", "artifact", lambda: (True, "finalized after writes"))
    add_check(rows, "V29", "Every output-manifest path, size, and SHA-256 verifies", "artifact", lambda: (True, "finalized after writes"))
    return pd.DataFrame(rows)


def build_requirements(validation: pd.DataFrame) -> pd.DataFrame:
    groups = [
        ("R01", "Exact Phase 5.5 parent, publication, and HF snapshot", ["V01", "V02"]),
        ("R02", "Exact common populations with unchanged labels and targets", ["V03", "V04", "V05"]),
        ("R03", "Model-independent empirical boundary reference", ["V06"]),
        ("R04", "Twenty group-disjoint matched outer runs", ["V07", "V08", "V09"]),
        ("R05", "Shared fair initialization and hidden-information isolation", ["V10", "V11", "V12"]),
        ("R06", "Queried-only physical thresholds", ["V13"]),
        ("R07", "Latent GP uncertainty and probability reconciliation", ["V14", "V15", "V16"]),
        ("R08", "Raw q20/q30 and integer-budget reconciliation", ["V17", "V18"]),
        ("R09", "Shared random trajectories", ["V19"]),
        ("R10", "AULC, tolerance, and matched paired summaries", ["V20", "V21", "V22"]),
        ("R11", "G3 is secondary and separately documented", ["V23"]),
        ("R12", "Old/new transfer remains secondary", ["V24"]),
        ("R13", "Conservative predeclared final decision", ["V25"]),
        ("R14", "Executed explanatory notebook and valid figures", ["V26", "V27"]),
        ("R15", "Exact artifacts and cryptographic integrity", ["V28", "V29"]),
    ]
    lookup = validation.set_index("check_id")["status"].to_dict()
    return pd.DataFrame(
        [
            {
                "requirement_id": requirement_id,
                "requirement": text,
                "status": "PASS" if all(lookup.get(item) == "PASS" for item in checks) else "FAIL",
                "validation_checks": ";".join(checks),
            }
            for requirement_id, text, checks in groups
        ]
    )


def main() -> int:
    args = parse_args()
    output_dir = SMOKE_DIR if args.smoke else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded, initial_errors = artifact_loader(output_dir)
    smoke_allowed_missing = SMOKE_OPTIONAL_ARTIFACTS if args.smoke else set()
    scientific_errors = {
        name: error
        for name, error in initial_errors.items()
        if name not in GENERATED_BY_VALIDATOR
        and name not in smoke_allowed_missing
    }
    validation = build_validation(loaded, args.smoke)
    if scientific_errors:
        validation = replace_check(
            validation,
            "V28",
            False,
            f"scientific artifact load errors={scientific_errors}",
        )

    # First pass creates the two validator-owned deliverables.  The manifest is
    # refreshed only after their final bytes are known.
    requirements = build_requirements(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "requirement_checklist.csv", requirements)
    write_csv(output_dir / "output_manifest.csv", build_manifest(output_dir))

    loaded_final, final_errors = artifact_loader(output_dir)
    artifact_ok, artifact_detail = exact_artifact_check(output_dir, final_errors, args.smoke)
    manifest_ok, manifest_detail = manifest_check(
        output_dir, loaded_final["output_manifest.csv"], args.smoke
    )
    validation = replace_check(validation, "V28", artifact_ok, artifact_detail)
    validation = replace_check(validation, "V29", manifest_ok, manifest_detail)
    requirements = build_requirements(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "requirement_checklist.csv", requirements)
    write_csv(output_dir / "output_manifest.csv", build_manifest(output_dir))

    # Verify the final post-write bytes once more.  A failure here is persisted
    # and the manifest is rebuilt one last time so it never contains stale
    # hashes for the validator-owned CSVs.
    final_manifest = pd.read_csv(output_dir / "output_manifest.csv", low_memory=False)
    final_manifest_ok, final_manifest_detail = manifest_check(
        output_dir, final_manifest, args.smoke
    )
    if not final_manifest_ok:
        validation = replace_check(validation, "V29", False, final_manifest_detail)
        requirements = build_requirements(validation)
        write_csv(output_dir / "validation_results.csv", validation)
        write_csv(output_dir / "requirement_checklist.csv", requirements)
        write_csv(output_dir / "output_manifest.csv", build_manifest(output_dir))

    failed_validation = validation[validation["status"].ne("PASS")]
    failed_requirements = requirements[requirements["status"].ne("PASS")]
    result = {
        "mode": "smoke" if args.smoke else "full",
        "output_dir": str(output_dir),
        "validation_passed": int(validation["status"].eq("PASS").sum()),
        "validation_total": len(validation),
        "requirements_passed": int(requirements["status"].eq("PASS").sum()),
        "requirements_total": len(requirements),
        "manifest_verified": int(final_manifest_ok),
        "manifest_rows": len(pd.read_csv(output_dir / "output_manifest.csv")),
        "failed_checks": failed_validation["check_id"].astype(str).tolist(),
        "failed_requirements": failed_requirements["requirement_id"].astype(str).tolist(),
    }
    print(json.dumps(result, indent=2))
    if len(failed_validation):
        print(failed_validation.to_string(index=False))
    if len(failed_requirements):
        print(failed_requirements.to_string(index=False))
    return 1 if len(failed_validation) or len(failed_requirements) or not final_manifest_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
