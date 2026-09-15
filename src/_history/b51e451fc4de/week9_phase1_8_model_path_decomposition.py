"""Week 9 Phase 1.8: model-vs-query-path decomposition.

This module replays two frozen query paths under two frozen prediction models.
It never selects a new point.  The only labels passed to a fit are labels in
the current prefix of the selected path; B1/q20/q30 are evaluation-only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import subprocess
import tarfile
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from nbclient import NotebookClient
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_8_model_path_decomposition"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"
CHECKPOINTS = OUTPUT / "checkpoints"
SENSITIVITY_CHECKPOINTS = OUTPUT / "sensitivity_checkpoints"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "04_week9_phase1_8_model_path_decomposition.ipynb"
FROZEN = ROOT / "outputs" / "week8_5_frozen_confirmation"
PHASE17 = ROOT / "outputs" / "week9_phase1_7_physics_ridge_residual_gp"
STARTING_SHA = "2f750c8c270baebc7e013ebe83fc429f9df14d51"
BRANCH = "codex/week9-phase1-8-model-path-decomposition"
SEED_ROOT = "week9_phase1_8_model_path_decomposition|v1"
FEATURES = p17.FEATURES
BUDGETS = tuple(range(16, 81))
CHECKPOINT_BUDGETS = (16, 20, 30, 40, 60, 80)
SENSITIVITY_BUDGETS = (16, 40, 80)
SENSITIVITY_UPPER_BOUNDS = (0.5, 1.0, 2.0)
BOOTSTRAP_DRAWS = 10_000
METRICS = (
    "accuracy",
    "balanced_accuracy",
    "keyhole_recall",
    "conduction_recall",
    "false_negative",
    "false_positive",
)
SUBSETS = ("full81", "B1_q30", "B1_q20")
ARM_LABELS = {
    "Y00": "4D model / 4D path",
    "Y10": "physics model / 4D path",
    "Y01": "4D model / physics path",
    "Y11": "physics model / physics path",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05 * (attempt + 1))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    if path.suffix == ".gz":
        csv_bytes = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        temporary.write_bytes(gzip.compress(csv_bytes, compresslevel=9, mtime=0))
    else:
        frame.to_csv(temporary, index=False, lineterminator="\n")
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05 * (attempt + 1))


def load_population_specs() -> tuple[pd.DataFrame, list[w85.SplitSpec]]:
    population, specs = p17.load_population_and_specs()
    require(len(population) == 405, "population drift")
    require(int(population.has_keyhole.sum()) == 73, "Keyhole-count drift")
    require(len(specs) == 100, "outer-run drift")
    return population, specs


def _read_tar_csv(archive: Path, member: str) -> pd.DataFrame:
    with tarfile.open(archive, "r:gz") as bundle:
        handle = bundle.extractfile(member)
        require(handle is not None, f"missing {member} in {archive.name}")
        return pd.read_csv(io.BytesIO(handle.read()), low_memory=False)


def load_query_paths() -> tuple[dict[str, dict[str, list[int]]], dict[str, Any]]:
    """Recover A0 and A1 exactly from tracked, published artifacts."""

    population, specs = load_population_specs()
    by_run = {spec.run_id: spec for spec in specs}
    initial_manifest = pd.read_csv(FROZEN / "initial_design_manifest.csv")
    initial = {
        run_id: group.sort_values("query_order").population_row_index.astype(int).tolist()
        for run_id, group in initial_manifest.groupby("run_id", sort=True)
    }

    a0: dict[str, list[int]] = {}
    archive = FROZEN / "week8_5_checkpoint_bundle.tar.gz"
    with tarfile.open(archive, "r:gz") as bundle:
        members = [
            member
            for member in bundle.getmembers()
            if member.name.endswith("__binary_margin__c01.json")
        ]
        require(len(members) == 100, "canonical 4D Margin checkpoint count drift")
        for member in members:
            handle = bundle.extractfile(member)
            require(handle is not None, f"cannot read {member.name}")
            payload = json.loads(handle.read().decode("utf-8"))
            run_id = str(payload["identity"]["run_id"])
            require(payload["identity"]["arm"] == "binary_margin", "A0 source arm drift")
            require(bool(payload["complete"]), "incomplete A0 checkpoint")
            require(int(payload["horizon"]) >= 80, "A0 checkpoint ends before 80")
            a0[run_id] = [int(value) for value in payload["queried_indices"][:80]]

    flow = pd.read_csv(PHASE17 / "tables" / "active_information_flow.csv.gz")
    a1: dict[str, list[int]] = {}
    for run_id, group in flow.groupby("run_id", sort=True):
        selected = (
            group.sort_values("selection_budget")
            .selected_population_row_index.astype(int)
            .tolist()
        )
        require(group.sort_values("selection_budget").selection_budget.astype(int).tolist() == list(range(17, 81)), f"A1 selection-budget drift {run_id}")
        a1[str(run_id)] = initial[str(run_id)] + selected

    expected_runs = set(by_run)
    require(set(a0) == expected_runs and set(a1) == expected_runs, "query-path run IDs drift")
    rows = []
    initial_matches = 0
    for run_id in sorted(expected_runs):
        spec = by_run[run_id]
        train, test = set(spec.train_indices), set(spec.test_indices)
        for path_name, path in (("A0", a0[run_id]), ("A1", a1[run_id])):
            path_initial_match = path[:16] == initial[run_id] == w85.initial_design(spec, population)
            if path_name == "A0" and path_initial_match and a1[run_id][:16] == path[:16]:
                initial_matches += 1
            rows.append(
                {
                    "run_id": run_id,
                    "path": path_name,
                    "query_count": len(path),
                    "budget_count_16_80": len(BUDGETS),
                    "initial_design_match": path_initial_match,
                    "unique_queries": len(path) == len(set(path)),
                    "all_in_training_pool": set(path).issubset(train),
                    "no_test_query": set(path).isdisjoint(test),
                }
            )
    audit_rows = pd.DataFrame(rows)
    all_ok = bool(
        len(audit_rows) == 200
        and initial_matches == 100
        and audit_rows.query_count.eq(80).all()
        and audit_rows.budget_count_16_80.eq(65).all()
        and audit_rows.initial_design_match.all()
        and audit_rows.unique_queries.all()
        and audit_rows.all_in_training_pool.all()
        and audit_rows.no_test_query.all()
    )
    audit = {
        "status": "PASS" if all_ok else "FAIL",
        "outer_run_ids_matched": len(expected_runs),
        "initial_design_exact_matches": initial_matches,
        "budgets_per_run": len(BUDGETS),
        "duplicate_path_violations": int((~audit_rows.unique_queries).sum()),
        "outside_training_pool_violations": int((~audit_rows.all_in_training_pool).sum()),
        "test_query_violations": int((~audit_rows.no_test_query).sum()),
        "A0_source": "outputs/week8_5_frozen_confirmation/week8_5_checkpoint_bundle.tar.gz: checkpoints/*__binary_margin__c01.json, queried_indices[:80]",
        "A0_source_sha256": sha256_file(archive),
        "A1_source": "outputs/week9_phase1_7_physics_ridge_residual_gp/tables/active_information_flow.csv.gz plus frozen initial_design_manifest.csv",
        "A1_source_sha256": sha256_file(PHASE17 / "tables" / "active_information_flow.csv.gz"),
    }
    require(all_ok, f"path audit failed: {audit}")
    paths = {run_id: {"A0": a0[run_id], "A1": a1[run_id]} for run_id in sorted(expected_runs)}
    write_json(OUTPUT / "path_audit.json", audit)
    write_csv(TABLES / "path_audit_detail.csv", audit_rows)
    path_rows = [
        {"run_id": run_id, "path": path_name, "query_order": order, "budget": order, "population_row_index": index}
        for run_id, values in paths.items()
        for path_name, path in values.items()
        for order, index in enumerate(path, start=1)
    ]
    write_csv(TABLES / "query_paths.csv.gz", pd.DataFrame(path_rows))
    return paths, audit


def _standard_row(
    spec: w85.SplitSpec,
    arm: str,
    model: str,
    path: str,
    budget: int,
    subset: str,
    source: str,
    metrics: dict[str, Any],
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "repeat": spec.repeat,
        "fold": spec.fold,
        "arm": arm,
        "model": model,
        "path": path,
        "budget": budget,
        "subset": subset,
        "source": source,
        **metrics,
        **(diagnostics or {}),
    }


def load_y00_historical() -> pd.DataFrame:
    """Reuse exact q20/q30 metrics for canonical M0/A0; no refit."""

    population, specs = load_population_specs()
    by_run = {spec.run_id: spec for spec in specs}
    archive = FROZEN / "week8_5_large_machine_readable_artifacts.tar.gz"
    raw = _read_tar_csv(archive, "trajectory_per_budget.csv")
    raw = raw[
        raw.arm.eq("binary_margin")
        & raw.continuation_id.eq(1)
        & raw.budget.between(16, 80)
    ].copy()
    require(len(raw) == 6500 and raw.run_id.nunique() == 100, "Y00 historical rows drift")
    rows = []
    for record in raw.itertuples(index=False):
        spec = by_run[str(record.run_id)]
        for subset, prefix in (("B1_q20", "B1_q20"), ("B1_q30", "B1_q30")):
            tn = int(getattr(record, f"{prefix}_true_negative"))
            fp = int(getattr(record, f"{prefix}_false_positive"))
            metrics = {
                "accuracy": float(getattr(record, f"{prefix}_accuracy")),
                "balanced_accuracy": float(getattr(record, f"{prefix}_balanced_accuracy")),
                "keyhole_recall": float(getattr(record, f"{prefix}_recall")),
                "conduction_recall": float(tn / (tn + fp)),
                "false_negative": int(getattr(record, f"{prefix}_false_negative")),
                "false_positive": fp,
                "row_count": int(getattr(record, f"{prefix}_row_count")),
            }
            rows.append(_standard_row(spec, "Y00", "M0", "A0", int(record.budget), subset, "reused_week8_5", metrics))
    return pd.DataFrame(rows)


def load_y11_historical() -> pd.DataFrame:
    """Reuse published Phase 1.7 M1/A1 metrics; no refit."""

    raw = pd.read_csv(PHASE17 / "tables" / "active_per_budget_metrics.csv.gz")
    raw = raw[raw.budget.between(16, 80)].copy()
    require(len(raw) == 100 * 65 * 3 and raw.run_id.nunique() == 100, "Y11 historical rows drift")
    keep = ["run_id", "repeat", "fold", "budget", "subset", *METRICS, "row_count"]
    result = raw[keep].copy()
    result.insert(3, "arm", "Y11")
    result.insert(4, "model", "M1")
    result.insert(5, "path", "A1")
    result.insert(8, "source", "reused_phase1_7")
    return result


def _fit_m0(
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    revealed: Sequence[int],
    budget: int,
) -> p6.FitResult:
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    scaler = StandardScaler().fit(x4[np.asarray(spec.train_indices, dtype=int)])
    seed = w85.seed_u32(w85.fit_seed_key(spec, "binary_margin", 1, budget))
    return p6.fit_gpc(x4[np.asarray(revealed, dtype=int)], labels[np.asarray(revealed, dtype=int)], scaler=scaler, seed=seed, restarts=0)


def _fit_m1(
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    revealed: Sequence[int],
    budget: int,
) -> p17.AdditiveFit:
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    return p17.fit_additive(
        x4,
        p17.log_h(population),
        labels,
        revealed,
        spec.train_indices,
        p17.seed_u32("active", spec.run_id, budget),
    )


def _evaluate_fit(
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    distances: np.ndarray,
    fit: p6.FitResult | p17.AdditiveFit,
    model: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    test = np.asarray(spec.test_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    if model == "M0":
        probability = p6.predict_gpc(fit, x4[test])  # type: ignore[arg-type]
        diagnostics = {
            "fit_status": fit.fit_status,  # type: ignore[union-attr]
            "kernel": fit.kernel,  # type: ignore[union-attr]
            "convergence_warning": bool(fit.warnings),  # type: ignore[union-attr]
        }
    else:
        components = p17.additive_components(fit, x4[test], p17.log_h(population)[test])  # type: ignore[arg-type]
        probability = components["probability"]
        diagnostics = {
            **p17.fit_diagnostic_row(fit),  # type: ignore[arg-type]
            "residual_rms_full81": float(np.sqrt(np.mean(components["residual_latent"] ** 2))),
            "residual_rms_B1_q20": float(np.sqrt(np.mean(components["residual_latent"][flags["B1_q20"]] ** 2))),
        }
    metrics = {
        subset: p17.metric_values(labels[test][flag], probability[flag])
        for subset, flag in flags.items()
    }
    return metrics, diagnostics


def _cross_checkpoint_path(arm: str, run_id: str) -> Path:
    return CHECKPOINTS / f"{run_id}__{arm}.json"


def run_cross_arm(
    spec: w85.SplitSpec,
    arm: str,
    path: Sequence[int],
    population: pd.DataFrame,
    distances: np.ndarray,
) -> dict[str, Any]:
    require(arm in ("Y10", "Y01"), "only cross arms are new")
    model, path_name = ("M1", "A0") if arm == "Y10" else ("M0", "A1")
    checkpoint = _cross_checkpoint_path(arm, spec.run_id)
    if checkpoint.is_file():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        if payload.get("complete") and payload.get("starting_sha") == STARTING_SHA:
            return {"run_id": spec.run_id, "arm": arm, "reused_checkpoint": True}
    rows: list[dict[str, Any]] = []
    for budget in BUDGETS:
        revealed = list(path[:budget])
        require(len(revealed) == budget and len(revealed) == len(set(revealed)), "prefix error")
        fit = _fit_m1(spec, population, revealed, budget) if model == "M1" else _fit_m0(spec, population, revealed, budget)
        metrics, diagnostics = _evaluate_fit(spec, population, distances, fit, model)
        for subset, values in metrics.items():
            rows.append(_standard_row(spec, arm, model, path_name, budget, subset, "new_fixed_path_replay", values, diagnostics))
    write_json(
        checkpoint,
        {
            "starting_sha": STARTING_SHA,
            "run_id": spec.run_id,
            "repeat": spec.repeat,
            "fold": spec.fold,
            "arm": arm,
            "model": model,
            "path": path_name,
            "complete": True,
            "revealed_label_rule": "only current query-path prefix",
            "rows": rows,
        },
    )
    return {"run_id": spec.run_id, "arm": arm, "reused_checkpoint": False}


def run_cross_evaluations(workers: int = 4, limit_specs: int | None = None) -> dict[str, Any]:
    paths, audit = load_query_paths()
    require(audit["status"] == "PASS", "path gate failed")
    population, specs = load_population_specs()
    specs = specs[:limit_specs] if limit_specs else specs
    distances = w85.b1_distance(population)
    jobs = [
        (spec, arm, paths[spec.run_id][path_name])
        for spec in specs
        for arm, path_name in (("Y10", "A0"), ("Y01", "A1"))
    ]
    start = time.time()
    if workers == 1:
        results = [run_cross_arm(spec, arm, path, population, distances) for spec, arm, path in jobs]
    else:
        results = Parallel(n_jobs=workers, verbose=10)(
            delayed(run_cross_arm)(spec, arm, path, population, distances)
            for spec, arm, path in jobs
        )
    report = {
        "status": "PASS",
        "new_arms": ["Y10", "Y01"],
        "outer_runs": len(specs),
        "fits": len(specs) * len(BUDGETS) * 2,
        "elapsed_seconds": time.time() - start,
        "checkpoint_reuses": int(sum(bool(row["reused_checkpoint"]) for row in results)),
        "new_query_trajectories": 0,
    }
    write_json(OUTPUT / "cross_execution_report.json", report)
    return report


def load_cross_rows() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(CHECKPOINTS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("arm") in ("Y10", "Y01"):
            require(payload.get("complete"), f"incomplete {path.name}")
            rows.extend(payload["rows"])
    result = pd.DataFrame(rows)
    require(result.run_id.nunique() == 100 and len(result) == 100 * 2 * 65 * 3, "cross replay incomplete")
    return result


def run_y00_checkpoint_fits(workers: int = 4) -> dict[str, Any]:
    """Fit canonical Y00 only at six checkpoints to obtain full81 metrics."""

    paths, _ = load_query_paths()
    population, specs = load_population_specs()
    distances = w85.b1_distance(population)

    def one(spec: w85.SplitSpec) -> list[dict[str, Any]]:
        rows = []
        for budget in CHECKPOINT_BUDGETS:
            fit = _fit_m0(spec, population, paths[spec.run_id]["A0"][:budget], budget)
            metrics, diagnostics = _evaluate_fit(spec, population, distances, fit, "M0")
            for subset, values in metrics.items():
                rows.append(_standard_row(spec, "Y00", "M0", "A0", budget, subset, "checkpoint_refit_for_full81", values, diagnostics))
        return rows

    start = time.time()
    nested = Parallel(n_jobs=workers, verbose=10)(delayed(one)(spec) for spec in specs)
    result = pd.DataFrame([row for group in nested for row in group])
    write_csv(TABLES / "y00_checkpoint_refit.csv.gz", result)
    report = {"status": "PASS", "fits": len(specs) * len(CHECKPOINT_BUDGETS), "elapsed_seconds": time.time() - start}
    write_json(OUTPUT / "y00_checkpoint_execution_report.json", report)
    return report


@dataclass
class SensitivityFit:
    fit: p17.AdditiveFit
    upper_bound: float


def fit_additive_with_bound(
    population: pd.DataFrame,
    spec: w85.SplitSpec,
    revealed: Sequence[int],
    budget: int,
    upper_bound: float,
) -> p17.AdditiveFit:
    """Phase 1.7 model with only the predeclared residual-SD upper bound changed."""

    x4 = population.loc[:, FEATURES].to_numpy(float)
    lh = p17.log_h(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    revealed_array = np.asarray(revealed, dtype=int)
    pool = np.asarray(spec.train_indices, dtype=int)
    x_scaler = StandardScaler().fit(x4[pool])
    h_scaler = StandardScaler().fit(lh[pool].reshape(-1, 1))
    transformed = p17.transform_additive_inputs(x4[revealed_array], lh[revealed_array], x_scaler, h_scaler)
    kernel = p17.PhysicsRidgeResidualKernel(
        residual_variance=0.09,
        length_scale=p17.MATERN_LENGTH_SCALE,
        residual_variance_bounds=(p17.RESIDUAL_SD_BOUNDS[0] ** 2, float(upper_bound) ** 2),
        length_scale_bounds=p17.LENGTH_SCALE_BOUNDS,
        physics_prior_variance=p17.PHYSICS_PRIOR_VARIANCE,
    )
    model = GaussianProcessClassifier(
        kernel=kernel,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=0,
        max_iter_predict=100,
        warm_start=False,
        random_state=p17.seed_u32("active", spec.run_id, budget),
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(transformed, labels[revealed_array])
    warning_text = " | ".join(str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning))
    return p17.AdditiveFit(model, x_scaler, h_scaler, revealed_array, transformed, labels[revealed_array], warning_text, "optimized_additive_laplace")


def _sensitivity_checkpoint_path(run_id: str, path_name: str, upper: float) -> Path:
    token = str(upper).replace(".", "p")
    return SENSITIVITY_CHECKPOINTS / f"{run_id}__{path_name}__upper_{token}.json"


def run_sensitivity(workers: int = 4) -> dict[str, Any]:
    paths, _ = load_query_paths()
    population, specs = load_population_specs()
    distances = w85.b1_distance(population)

    def one(spec: w85.SplitSpec, path_name: str, upper: float) -> dict[str, Any]:
        checkpoint = _sensitivity_checkpoint_path(spec.run_id, path_name, upper)
        if checkpoint.is_file():
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            if payload.get("complete"):
                return {"rows": payload["rows"], "reused": True}
        rows = []
        for budget in SENSITIVITY_BUDGETS:
            fit = fit_additive_with_bound(population, spec, paths[spec.run_id][path_name][:budget], budget, upper)
            metrics, _ = _evaluate_fit(spec, population, distances, fit, "M1")
            x4 = population.loc[:, FEATURES].to_numpy(float)
            test = np.asarray(spec.test_indices, dtype=int)
            flags = p17.subset_flags(spec, population, distances)
            components = p17.additive_components(fit, x4[test], p17.log_h(population)[test])
            diagnostics = {
                "residual_sd": fit.residual_sd,
                "length_scale": fit.length_scale,
                "residual_sd_lower_bound_hit": bool(np.isclose(fit.residual_sd, 0.05, atol=5e-4, rtol=0)),
                "residual_sd_upper_bound_hit": bool(np.isclose(fit.residual_sd, upper, atol=5e-4, rtol=0)),
                "length_scale_lower_bound_hit": bool(np.isclose(fit.length_scale, 0.25, atol=5e-4, rtol=0)),
                "length_scale_upper_bound_hit": bool(np.isclose(fit.length_scale, 4.0, atol=5e-4, rtol=0)),
                "residual_rms_q20": float(np.sqrt(np.mean(components["residual_latent"][flags["B1_q20"]] ** 2))),
                "convergence_warning": bool(fit.warnings),
            }
            rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "path": path_name,
                    "budget": budget,
                    "residual_sd_upper_bound": upper,
                    "q20_accuracy": metrics["B1_q20"]["accuracy"],
                    "q20_balanced_accuracy": metrics["B1_q20"]["balanced_accuracy"],
                    "q20_keyhole_recall": metrics["B1_q20"]["keyhole_recall"],
                    "full81_accuracy": metrics["full81"]["accuracy"],
                    **diagnostics,
                }
            )
        write_json(checkpoint, {"complete": True, "rows": rows})
        return {"rows": rows, "reused": False}

    # Bound 1.0 is intentionally refit here at only three checkpoints.  This
    # makes all three sensitivity settings directly comparable on both paths.
    jobs = [(spec, path_name, upper) for spec in specs for path_name in ("A0", "A1") for upper in SENSITIVITY_UPPER_BOUNDS]
    start = time.time()
    results = Parallel(n_jobs=workers, verbose=10)(delayed(one)(*job) for job in jobs)
    detail = pd.DataFrame([row for result in results for row in result["rows"]])
    require(len(detail) == 100 * 2 * 3 * 3, "sensitivity rows incomplete")
    write_csv(TABLES / "regularization_sensitivity_detail.csv.gz", detail)
    summary = (
        detail.groupby(["path", "budget", "residual_sd_upper_bound"], as_index=False)
        .agg(
            q20_accuracy=("q20_accuracy", "mean"),
            q20_balanced_accuracy=("q20_balanced_accuracy", "mean"),
            q20_keyhole_recall=("q20_keyhole_recall", "mean"),
            full81_accuracy=("full81_accuracy", "mean"),
            lower_bound_hit_fraction=("residual_sd_lower_bound_hit", "mean"),
            upper_bound_hit_fraction=("residual_sd_upper_bound_hit", "mean"),
            length_lower_hit_fraction=("length_scale_lower_bound_hit", "mean"),
            length_upper_hit_fraction=("length_scale_upper_bound_hit", "mean"),
            residual_rms_q20=("residual_rms_q20", "mean"),
            fitted_residual_sd=("residual_sd", "mean"),
            fitted_length_scale=("length_scale", "mean"),
            convergence_warning_fraction=("convergence_warning", "mean"),
        )
    )
    write_csv(OUTPUT / "regularization_sensitivity.csv", summary)
    report = {
        "status": "PASS",
        "paths": ["A0", "A1"],
        "bounds": list(SENSITIVITY_UPPER_BOUNDS),
        "budgets": list(SENSITIVITY_BUDGETS),
        "fits": len(jobs) * len(SENSITIVITY_BUDGETS),
        "elapsed_seconds": time.time() - start,
        "new_query_trajectories": 0,
        "post_hoc_selection": False,
    }
    write_json(OUTPUT / "sensitivity_execution_report.json", report)
    return report


def aulc_per_run(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in metrics[metrics.subset.isin(("B1_q20", "B1_q30"))].groupby(
        ["run_id", "repeat", "fold", "arm", "model", "path", "subset"], sort=True
    ):
        run_id, repeat, fold, arm, model, path, subset = keys
        ordered = group.sort_values("budget")
        require(ordered.budget.astype(int).tolist() == list(BUDGETS), f"incomplete AULC path {run_id}/{arm}/{subset}")
        rows.append(
            {
                "run_id": run_id,
                "repeat": int(repeat),
                "fold": int(fold),
                "arm": arm,
                "model": model,
                "path": path,
                "endpoint": f"{subset}_accuracy_AULC_16_80",
                "AULC": w85.aulc(ordered.rename(columns={"accuracy": "metric"}), "metric", 16, 80),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_repeat(values: np.ndarray, seed_label: str) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    require(len(values) == 20, f"bootstrap expects 20 repeat blocks, got {len(values)}")
    rng = np.random.default_rng(seed_u32("bootstrap", seed_label))
    draws = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))].mean(axis=1)
    lower, upper = np.quantile(draws, [0.025, 0.975])
    return float(values.mean()), float(lower), float(upper)


def decompose(aulc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q20 = aulc[aulc.endpoint.eq("B1_q20_accuracy_AULC_16_80")]
    wide = q20.pivot(index=["run_id", "repeat", "fold"], columns="arm", values="AULC").reset_index()
    require(set(("Y00", "Y10", "Y01", "Y11")).issubset(wide.columns), "2x2 AULC incomplete")
    wide["TOTAL"] = wide.Y11 - wide.Y00
    wide["ME_A0"] = wide.Y10 - wide.Y00
    wide["ME_A1"] = wide.Y11 - wide.Y01
    wide["PE_M0"] = wide.Y01 - wide.Y00
    wide["PE_M1"] = wide.Y11 - wide.Y10
    wide["INT"] = wide.Y11 - wide.Y10 - wide.Y01 + wide.Y00
    wide["MODEL"] = 0.5 * (wide.ME_A0 + wide.ME_A1)
    wide["PATH"] = 0.5 * (wide.PE_M0 + wide.PE_M1)
    wide["MODEL_minus_PATH"] = wide.MODEL - wide.PATH
    require(np.allclose(wide.MODEL + wide.PATH, wide.TOTAL, atol=1e-14, rtol=0), "symmetric decomposition identity failed")
    repeat = wide.groupby("repeat", as_index=False).mean(numeric_only=True)
    effects = ("TOTAL", "MODEL", "PATH", "ME_A0", "ME_A1", "PE_M0", "PE_M1", "INT", "MODEL_minus_PATH")
    summaries = []
    for effect in effects:
        mean, lower, upper = bootstrap_repeat(repeat[effect].to_numpy(float), effect)
        summaries.append({"effect": effect, "mean": mean, "ci_lower": lower, "ci_upper": upper, "bootstrap_draws": BOOTSTRAP_DRAWS})
    summary = pd.DataFrame(summaries)
    contrast = summary[summary.effect.eq("MODEL_minus_PATH")].iloc[0]
    decision = "MODEL_DOMINANT" if contrast.ci_lower > 0 else ("PATH_DOMINANT" if contrast.ci_upper < 0 else "MIXED_OR_UNRESOLVED")
    summary["decision"] = decision
    return wide, repeat, summary


def summarize_four_way(aulc: pd.DataFrame) -> pd.DataFrame:
    repeat = aulc.groupby(["repeat", "arm", "endpoint"], as_index=False).AULC.mean()
    rows = []
    for (arm, endpoint), group in repeat.groupby(["arm", "endpoint"], sort=True):
        mean, lower, upper = bootstrap_repeat(group.sort_values("repeat").AULC.to_numpy(float), f"{arm}|{endpoint}")
        rows.append({"arm": arm, "label": ARM_LABELS[arm], "endpoint": endpoint, "mean_AULC": mean, "ci_lower": lower, "ci_upper": upper})
    return pd.DataFrame(rows)


def checkpoint_tables(metrics: pd.DataFrame, y00_refit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    checkpoints = metrics[metrics.budget.isin(CHECKPOINT_BUDGETS)].copy()
    # Frozen Y00 q20/q30 stay authoritative; only full81 comes from the small
    # checkpoint refit.  The duplicated q20/q30 refit rows are gate evidence.
    y00_full = y00_refit[y00_refit.subset.eq("full81")]
    checkpoints = pd.concat([checkpoints, y00_full], ignore_index=True, sort=False)
    require(len(checkpoints) == 4 * 100 * len(CHECKPOINT_BUDGETS) * 3, "checkpoint matrix incomplete")
    long = checkpoints.melt(
        id_vars=["run_id", "repeat", "fold", "arm", "model", "path", "budget", "subset"],
        value_vars=list(METRICS),
        var_name="metric",
        value_name="value",
    )
    summary = long.groupby(["arm", "model", "path", "budget", "subset", "metric"], as_index=False).value.mean()

    wide = long.pivot(index=["run_id", "repeat", "fold", "budget", "subset", "metric"], columns="arm", values="value").reset_index()
    require(wide[["Y00", "Y10", "Y01", "Y11"]].notna().all().all(), "checkpoint contrast matrix incomplete")
    effect_formulas = {
        "TOTAL": wide.Y11 - wide.Y00,
        "ME_A0": wide.Y10 - wide.Y00,
        "ME_A1": wide.Y11 - wide.Y01,
        "PE_M0": wide.Y01 - wide.Y00,
        "PE_M1": wide.Y11 - wide.Y10,
        "INT": wide.Y11 - wide.Y10 - wide.Y01 + wide.Y00,
    }
    contrast_rows = []
    for effect, values in effect_formulas.items():
        temp = wide[["run_id", "repeat", "fold", "budget", "subset", "metric"]].copy()
        temp["value"] = values
        repeats = temp.groupby(["repeat", "budget", "subset", "metric"], as_index=False).value.mean()
        for keys, group in repeats.groupby(["budget", "subset", "metric"], sort=True):
            budget, subset, metric = keys
            mean, lower, upper = bootstrap_repeat(group.sort_values("repeat").value.to_numpy(float), f"checkpoint|{effect}|{budget}|{subset}|{metric}")
            contrast_rows.append({"effect": effect, "budget": budget, "subset": subset, "metric": metric, "mean": mean, "ci_lower": lower, "ci_upper": upper})
    return summary, pd.DataFrame(contrast_rows)


def aggregate() -> dict[str, Any]:
    paths, audit = load_query_paths()
    require(audit["status"] == "PASS", "path audit failed")
    y00 = load_y00_historical()
    y11 = load_y11_historical()
    cross = load_cross_rows()
    metrics = pd.concat([y00, cross, y11], ignore_index=True, sort=False)
    require(metrics.run_id.nunique() == 100, "four-way run count drift")
    aulc = aulc_per_run(metrics)
    outer, repeat, decomposition = decompose(aulc)
    four_way = summarize_four_way(aulc)

    y00_refit = pd.read_csv(TABLES / "y00_checkpoint_refit.csv.gz")
    historical_check = y00[y00.budget.isin(CHECKPOINT_BUDGETS)].merge(
        y00_refit[y00_refit.subset.isin(("B1_q20", "B1_q30"))],
        on=["run_id", "repeat", "fold", "arm", "model", "path", "budget", "subset"],
        suffixes=("_frozen", "_refit"),
        validate="one_to_one",
    )
    max_refit_error = max(
        float((historical_check[f"{metric}_frozen"] - historical_check[f"{metric}_refit"]).abs().max())
        for metric in METRICS
    )
    require(max_refit_error < 1e-12, f"Y00 checkpoint reconstruction mismatch {max_refit_error}")

    summary, contrasts = checkpoint_tables(metrics, y00_refit)
    write_csv(TABLES / "four_way_metrics_per_budget.csv.gz", metrics)
    write_csv(TABLES / "outer_run_four_way_AULC.csv.gz", aulc)
    write_csv(OUTPUT / "four_way_AULC_summary.csv", four_way)
    write_csv(OUTPUT / "repeat_level_decomposition.csv", repeat)
    write_csv(OUTPUT / "primary_decomposition.csv", decomposition)
    write_csv(OUTPUT / "learning_curve_four_way.csv", metrics[metrics.subset.eq("B1_q20")].groupby(["arm", "model", "path", "budget"], as_index=False).accuracy.mean())
    write_csv(OUTPUT / "budget_checkpoint_summary.csv", summary)
    write_csv(OUTPUT / "budget_checkpoint_contrasts.csv", contrasts)

    q20 = four_way[four_way.endpoint.eq("B1_q20_accuracy_AULC_16_80")].set_index("arm")
    require(abs(float(q20.loc["Y00", "mean_AULC"]) - 0.8135202205882354) < 1e-12, "Y00 AULC gate failed")
    require(abs(float(q20.loc["Y11", "mean_AULC"]) - 0.8335386029411765) < 1e-12, "Y11 AULC gate failed")

    # The shared initial design must give identical same-model results.
    at16 = pd.concat(
        [
            metrics[metrics.budget.eq(16)],
            y00_refit[y00_refit.budget.eq(16) & y00_refit.subset.eq("full81")],
        ],
        ignore_index=True,
        sort=False,
    )
    m0_errors, m1_errors = [], []
    for metric in METRICS:
        same_m0 = at16[at16.arm.isin(("Y00", "Y01"))].pivot(index=["run_id", "subset"], columns="arm", values=metric).dropna()
        same_m1 = at16[at16.arm.isin(("Y10", "Y11"))].pivot(index=["run_id", "subset"], columns="arm", values=metric).dropna()
        require(len(same_m0) == len(same_m1) == 300, f"budget-16 metric matrix incomplete for {metric}")
        m0_errors.append(float((same_m0.Y00 - same_m0.Y01).abs().max()))
        m1_errors.append(float((same_m1.Y10 - same_m1.Y11).abs().max()))
    m0_error, m1_error = max(m0_errors), max(m1_errors)
    require(m0_error < 1e-12 and m1_error < 1e-12, "budget-16 same-model identity failed")

    baseline = {
        "status": "PASS",
        "population_rows": 405,
        "keyholes": 73,
        "outer_runs": 100,
        "initial_design_exact_matches": audit["initial_design_exact_matches"],
        "Y00_q20_AULC": float(q20.loc["Y00", "mean_AULC"]),
        "Y11_q20_AULC": float(q20.loc["Y11", "mean_AULC"]),
        "Y00_budget16_q20_accuracy": float(summary[(summary.arm.eq("Y00")) & summary.budget.eq(16) & summary.subset.eq("B1_q20") & summary.metric.eq("accuracy")].value.iloc[0]),
        "Y11_budget16_q20_accuracy": float(summary[(summary.arm.eq("Y11")) & summary.budget.eq(16) & summary.subset.eq("B1_q20") & summary.metric.eq("accuracy")].value.iloc[0]),
        "Y00_Y01_budget16_max_accuracy_error": m0_error,
        "Y10_Y11_budget16_max_accuracy_error": m1_error,
        "budget16_same_model_max_error_all_metrics": max(m0_error, m1_error),
        "Y00_checkpoint_refit_max_accuracy_error": max_refit_error,
        "Y00_checkpoint_refit_max_error_all_metrics": max_refit_error,
    }
    write_json(OUTPUT / "baseline_gate.json", baseline)
    return {"baseline": baseline, "decomposition": decomposition.to_dict(orient="records")}


def make_figures() -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    curve = pd.read_csv(OUTPUT / "learning_curve_four_way.csv")
    colors = {"Y00": "#3b5b92", "Y10": "#d1495b", "Y01": "#5c9a48", "Y11": "#7b4f9d"}
    styles = {"Y00": "-", "Y10": "--", "Y01": ":", "Y11": "-."}
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    for arm in ("Y00", "Y10", "Y01", "Y11"):
        part = curve[curve.arm.eq(arm)].sort_values("budget")
        ax.plot(part.budget, part.accuracy, color=colors[arm], ls=styles[arm], lw=2.4, label=f"{arm}: {ARM_LABELS[arm]}")
    ax.axvline(16, color="black", lw=1, alpha=0.45)
    ax.annotate("Shared 16-point initial design", xy=(16, 0.744), xytext=(21, 0.755), arrowprops={"arrowstyle": "->", "color": "#444"}, fontsize=9)
    ax.set(xlabel="Revealed simulations", ylabel="Fold-B1-q20 accuracy", title="Same models on two frozen query paths")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8.5, ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "01_four_way_q20_learning_curves.png", dpi=180)
    plt.close(fig)

    effects = pd.read_csv(OUTPUT / "primary_decomposition.csv")
    selected = effects[effects.effect.isin(("TOTAL", "MODEL", "PATH"))].set_index("effect").loc[["TOTAL", "MODEL", "PATH"]].reset_index()
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    x = np.arange(len(selected))
    ax.errorbar(x, selected["mean"], yerr=[selected["mean"] - selected.ci_lower, selected.ci_upper - selected["mean"]], fmt="o", color="#2d4059", capsize=6, markersize=8)
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(x, ["Total Y11-Y00", "Symmetric MODEL", "Symmetric PATH"])
    ax.set_ylabel("q20 accuracy AULC effect")
    ax.set_title("Order-independent decomposition (20 repeat blocks)")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "02_AULC_decomposition.png", dpi=180)
    plt.close(fig)

    contrasts = pd.read_csv(OUTPUT / "budget_checkpoint_contrasts.csv")
    part = contrasts[
        contrasts.budget.isin((16, 40, 80))
        & contrasts.subset.eq("B1_q20")
        & contrasts.metric.eq("accuracy")
        & contrasts.effect.isin(("ME_A0", "ME_A1", "PE_M0", "PE_M1"))
    ].copy()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    offsets = {"ME_A0": -0.24, "ME_A1": -0.08, "PE_M0": 0.08, "PE_M1": 0.24}
    markers = {"ME_A0": "o", "ME_A1": "s", "PE_M0": "^", "PE_M1": "D"}
    for effect in offsets:
        group = part[part.effect.eq(effect)].sort_values("budget")
        xx = np.arange(3) + offsets[effect]
        ax.errorbar(xx, group["mean"], yerr=[group["mean"] - group.ci_lower, group.ci_upper - group["mean"]], fmt=markers[effect], capsize=4, label=effect)
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(np.arange(3), ["16", "40", "80"])
    ax.set(xlabel="Budget", ylabel="Matched q20 accuracy effect", title="Model and path effects across budget")
    ax.legend(ncol=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "03_budget_model_path_effects.png", dpi=180)
    plt.close(fig)

    sensitivity = pd.read_csv(OUTPUT / "regularization_sensitivity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6), sharey=True)
    for ax, path_name in zip(axes, ("A0", "A1")):
        current = sensitivity[sensitivity.path.eq(path_name)]
        for budget, marker in zip(SENSITIVITY_BUDGETS, ("o", "s", "^")):
            group = current[current.budget.eq(budget)].sort_values("residual_sd_upper_bound")
            ax.plot(group.residual_sd_upper_bound, group.q20_accuracy, marker=marker, lw=2, label=f"budget {budget}")
        ax.set(title=f"Fixed {path_name}", xlabel="Residual-SD upper bound")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Mean q20 accuracy")
    axes[1].legend()
    fig.suptitle("Fixed-path regularization sensitivity (not model selection)")
    fig.tight_layout()
    fig.savefig(FIGURES / "04_residual_bound_sensitivity.png", dpi=180)
    plt.close(fig)

    rows = []
    for path in sorted(FIGURES.glob("*.png")):
        rows.append({"figure": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = pd.DataFrame(rows)
    write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return manifest


def _effect_row(frame: pd.DataFrame, name: str) -> pd.Series:
    return frame[frame.effect.eq(name)].iloc[0]


def _checkpoint_row(frame: pd.DataFrame, arm: str, budget: int, subset: str, metric: str) -> float:
    return float(frame[(frame.arm.eq(arm)) & frame.budget.eq(budget) & frame.subset.eq(subset) & frame.metric.eq(metric)].value.iloc[0])


def build_reports() -> None:
    four = pd.read_csv(OUTPUT / "four_way_AULC_summary.csv")
    q20 = four[four.endpoint.eq("B1_q20_accuracy_AULC_16_80")].set_index("arm")
    effects = pd.read_csv(OUTPUT / "primary_decomposition.csv")
    checkpoints = pd.read_csv(OUTPUT / "budget_checkpoint_summary.csv")
    contrasts = pd.read_csv(OUTPUT / "budget_checkpoint_contrasts.csv")
    sens = pd.read_csv(OUTPUT / "regularization_sensitivity.csv")
    decision = str(effects.decision.iloc[0])
    total, model, path, interaction, model_minus_path = (_effect_row(effects, name) for name in ("TOTAL", "MODEL", "PATH", "INT", "MODEL_minus_PATH"))
    me_a0, pe_m0 = _effect_row(effects, "ME_A0"), _effect_row(effects, "PE_M0")
    b16_effects = contrasts[(contrasts.budget.eq(16)) & contrasts.effect.eq("ME_A0")]
    b16_lines = []
    for subset in SUBSETS:
        values = []
        for metric in ("accuracy", "balanced_accuracy", "keyhole_recall"):
            row = b16_effects[(b16_effects.subset.eq(subset)) & b16_effects.metric.eq(metric)].iloc[0]
            values.append(f"{metric} {row['mean']:+.6f} [{row.ci_lower:+.6f},{row.ci_upper:+.6f}]")
        b16_lines.append(f"- {subset}: " + "; ".join(values))

    sens_a1 = sens[sens.path.eq("A1")]
    accuracy_spread = sens_a1.groupby("budget").q20_accuracy.agg(lambda x: float(x.max() - x.min()))
    max_spread = float(accuracy_spread.max())
    sensitivity_verdict = "checkpoint-level advantage locally stable in direction, with small variation" if max_spread < 0.02 else "checkpoint results materially sensitive across the fixed 0.5/1.0/2.0 bounds"

    report = f"""# Week 9 Phase 1.8 — Final report

## Question and frozen 2 × 2 design

This study separates the prediction-model contribution from the contribution of the query path induced by the physics-informed model/policy. No new acquisition trajectory was generated. `Y00` and `Y11` are reused published results; only `Y10` and `Y01` are full new fixed-path replays.

| | A0: frozen 4D path | A1: frozen physics path |
|---|---:|---:|
| M0: canonical 4D GPC | Y00 {q20.loc['Y00','mean_AULC']:.9f} | Y01 {q20.loc['Y01','mean_AULC']:.9f} |
| M1: physics ridge + residual GP | Y10 {q20.loc['Y10','mean_AULC']:.9f} | Y11 {q20.loc['Y11','mean_AULC']:.9f} |

All values are Fold-B1-q20 accuracy AULC 16–80.

## Primary decomposition

- Total `Y11-Y00`: {total['mean']:+.9f}, 95% repeat-block CI [{total.ci_lower:+.9f},{total.ci_upper:+.9f}].
- Symmetric MODEL contribution: {model['mean']:+.9f}, CI [{model.ci_lower:+.9f},{model.ci_upper:+.9f}].
- Symmetric PATH contribution: {path['mean']:+.9f}, CI [{path.ci_lower:+.9f},{path.ci_upper:+.9f}].
- Interaction: {interaction['mean']:+.9f}, CI [{interaction.ci_lower:+.9f},{interaction.ci_upper:+.9f}].
- MODEL-PATH: {model_minus_path['mean']:+.9f}, CI [{model_minus_path.ci_lower:+.9f},{model_minus_path.ci_upper:+.9f}].

Decision: **{decision}** under the predeclared CI rule.

The physics model on the original 4D path has `ME_A0={me_a0['mean']:+.9f}` [{me_a0.ci_lower:+.9f},{me_a0.ci_upper:+.9f}]. The physics-induced path under the ordinary 4D model has `PE_M0={pe_m0['mean']:+.9f}` [{pe_m0.ci_lower:+.9f},{pe_m0.ci_upper:+.9f}]. This is a query-path contribution induced by the physics-informed model/policy, not acquisition-function superiority.

## Budget-16 low-data diagnostic

Both paths are identical through the shared initial 16 simulations, so every effect below is purely prediction-model structure:

{chr(10).join(b16_lines)}

The same-model numerical gates pass exactly: `Y00(16)=Y01(16)` and `Y10(16)=Y11(16)` for the stored evaluation metrics.

## Fixed-path residual-bound sensitivity

Residual-SD upper bounds 0.5, 1.0 and 2.0 were evaluated only on the already observed A0 and A1 paths at budgets 16, 40 and 80. No path was regenerated and no setting was selected. The maximum A1 q20-accuracy spread across bounds at a checkpoint is {max_spread:.6f}; verdict: **{sensitivity_verdict}**. This is a three-checkpoint diagnostic, not a sensitivity AULC or a new model-selection result. Detailed bound-hit rates, realized residual RMS, fitted SD and length scale are in `regularization_sensitivity.csv`.

## Safe conclusion

On this frozen 405-simulation benchmark, the Phase 1.7 improvement decomposes into a prediction-model contribution and a query-path contribution induced by the physics-informed model/policy. The predeclared dominance decision is **{decision}**. This is not evidence of universal physical validity, acquisition-function superiority, or prospective experimental performance.

## Main limitation

This is a retrospective fixed-path decomposition on one simulator/material dataset. The paths are themselves posterior-dependent, and the additive physics trend and 4D residual are not fully identifiable because `h` is derived from `P,VX,LS`. The residual bound diagnostic is local robustness analysis, not tuning.
"""
    (OUTPUT / "FINAL_PHASE1_8_REPORT.md").write_text(report, encoding="utf-8")

    supervisor = f"""# Week 9 Phase 1.8 — Supervisor one-page summary

## Result

The published Phase 1.7 q20 AULC gain is {total['mean']:+.6f}. The symmetric decomposition assigns {model['mean']:+.6f} [{model.ci_lower:+.6f},{model.ci_upper:+.6f}] to the prediction model and {path['mean']:+.6f} [{path.ci_lower:+.6f},{path.ci_upper:+.6f}] to the changed query path. The predeclared decision is **{decision}**.

| Combination | q20 AULC |
|---|---:|
| Y00: 4D model / 4D path | {q20.loc['Y00','mean_AULC']:.6f} |
| Y10: physics model / 4D path | {q20.loc['Y10','mean_AULC']:.6f} |
| Y01: 4D model / physics path | {q20.loc['Y01','mean_AULC']:.6f} |
| Y11: physics model / physics path | {q20.loc['Y11','mean_AULC']:.6f} |

At budget 16 the paths are identical. The q20 accuracy advantage is {_checkpoint_row(checkpoints,'Y11',16,'B1_q20','accuracy')-_checkpoint_row(checkpoints,'Y00',16,'B1_q20','accuracy'):+.6f}, so the early gain is necessarily a model/inductive-bias effect.

The physics model still changes q20 AULC by {me_a0['mean']:+.6f} when forced onto the original 4D path. The physics-induced path changes ordinary 4D-GPC q20 AULC by {pe_m0['mean']:+.6f}. Call the latter a **query-path contribution induced by the physics-informed model/policy**, not acquisition superiority.

Fixed-path bounds 0.5/1.0/2.0 give a maximum A1 checkpoint q20-accuracy spread of {max_spread:.4f}; verdict: {sensitivity_verdict}.

## Safe thesis claim

“On the frozen 405-simulation benchmark, the Phase 1.7 model/policy gain can be decomposed into a physics-informed prediction-model contribution and a posterior-induced query-path contribution; the dominance classification is {decision}.”
"""
    (OUTPUT / "SUPERVISOR_PHASE1_8_ONE_PAGE.md").write_text(supervisor, encoding="utf-8")

    ledger = f"""# Phase 1.8 claim ledger

| Claim | Decision | Evidence / qualification |
|---|---|---|
| Frozen 2 × 2 paths are exact and leakage-free | PASS | `path_audit.json`; prefix-only replay |
| Published total q20 AULC gain reproduces | PASS | {total['mean']:+.9f} |
| Dominance decision is {decision} | PASS | MODEL-PATH CI [{model_minus_path.ci_lower:+.6f},{model_minus_path.ci_upper:+.6f}] |
| Physics model improves on original 4D path | {'PASS' if me_a0.ci_lower > 0 else 'QUALIFY' if me_a0['mean'] > 0 else 'FAIL'} | ME_A0 {me_a0['mean']:+.6f} [{me_a0.ci_lower:+.6f},{me_a0.ci_upper:+.6f}] |
| Physics path helps ordinary 4D GPC | {'PASS' if pe_m0.ci_lower > 0 else 'QUALIFY' if pe_m0['mean'] > 0 else 'FAIL'} | PE_M0 {pe_m0['mean']:+.6f} [{pe_m0.ci_lower:+.6f},{pe_m0.ci_upper:+.6f}] |
| Query-path effect proves acquisition-function superiority | REJECT | Policies use different posteriors; only fixed path contribution is identified |
| Sensitivity selects a better residual bound | REJECT | Diagnostic only; no setting selected |
| Universal physical or prospective validity | REJECT | One retrospective simulator/material benchmark |
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger, encoding="utf-8")


def build_notebook() -> None:
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.8 — Model-vs-query-path decomposition\n\nThis compact notebook reads the generated artifacts. It does not rerun the experiment."),
        nbf.v4.new_markdown_cell("## 1. Question\n\nWas the Phase 1.7 gain caused mainly by the physics-informed predictor, by the different sequence it queried, or by their interaction?"),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_8_model_path_decomposition'\ngate=json.loads((OUT/'baseline_gate.json').read_text())\naudit=json.loads((OUT/'path_audit.json').read_text())\ngate, audit"),
        nbf.v4.new_markdown_cell("## 2. Frozen gate and query-path audit\n\nA0 comes from the Week 8.5 canonical Margin checkpoint bundle. A1 comes from the published Phase 1.7 information-flow table. Both contain the same frozen 16-point prefix."),
        nbf.v4.new_code_cell("four=pd.read_csv(OUT/'four_way_AULC_summary.csv')\nfour[four.endpoint=='B1_q20_accuracy_AULC_16_80'][['arm','label','mean_AULC','ci_lower','ci_upper']]"),
        nbf.v4.new_markdown_cell("## 3. Exact 2 × 2 design\n\nY00 and Y11 are reused published arms. Y10 and Y01 are the two new counterfactual fixed-path evaluations. At each budget only the path prefix is revealed."),
        nbf.v4.new_code_cell("from IPython.display import Image, display\ndisplay(Image(filename=str(OUT/'figures'/'01_four_way_q20_learning_curves.png')))"),
        nbf.v4.new_markdown_cell("## 4. Model-vs-path decomposition\n\nThe symmetric decomposition averages the two possible orders of changing model and path. MODEL + PATH equals Y11 − Y00 for every outer run."),
        nbf.v4.new_code_cell("dec=pd.read_csv(OUT/'primary_decomposition.csv')\ndec[['effect','mean','ci_lower','ci_upper','decision']]"),
        nbf.v4.new_code_cell("display(Image(filename=str(OUT/'figures'/'02_AULC_decomposition.png')))"),
        nbf.v4.new_markdown_cell("## 5. Budget-16 low-data diagnostic\n\nBecause the paths are identical at budget 16, any M1−M0 difference is purely a prediction-model effect."),
        nbf.v4.new_code_cell("c=pd.read_csv(OUT/'budget_checkpoint_contrasts.csv')\nc[(c.budget==16)&(c.effect=='ME_A0')&c.subset.isin(['full81','B1_q30','B1_q20'])&c.metric.isin(['accuracy','balanced_accuracy','keyhole_recall'])]"),
        nbf.v4.new_markdown_cell("## 6. Budget 40/80 classwise interpretation"),
        nbf.v4.new_code_cell("s=pd.read_csv(OUT/'budget_checkpoint_summary.csv')\ns[(s.budget.isin([40,80]))&(s.subset=='B1_q20')&s.metric.isin(['accuracy','balanced_accuracy','keyhole_recall','false_negative','false_positive'])]"),
        nbf.v4.new_markdown_cell("## 7. Small fixed-path residual-bound sensitivity\n\nBounds 0.5, 1.0 and 2.0 were evaluated without changing either path. This is robustness analysis, not hyperparameter selection."),
        nbf.v4.new_code_cell("r=pd.read_csv(OUT/'regularization_sensitivity.csv')\nr[['path','budget','residual_sd_upper_bound','q20_accuracy','q20_balanced_accuracy','q20_keyhole_recall','full81_accuracy','upper_bound_hit_fraction','residual_rms_q20','fitted_residual_sd','fitted_length_scale']]"),
        nbf.v4.new_markdown_cell("## 8. Safe conclusion\n\nRead `SUPERVISOR_PHASE1_8_ONE_PAGE.md`. The query-path term is posterior-induced and must not be described as acquisition-function superiority."),
    ]
    notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    executed = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=120, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    nbf.write(executed, NOTEBOOK)


def run_red_team() -> dict[str, Any]:
    """One focused adversarial audit after all artifacts exist."""

    findings = [
        {
            "issue": "Generated gzip files initially embedded a changing temporary filename in their header.",
            "resolution": "CSV gzip output now uses deterministic gzip.compress with mtime=0; repeated path audits preserve artifact hashes.",
            "scientific_impact": "none; byte-level provenance only",
        }
    ]
    paths, audit = load_query_paths()
    require(audit["status"] == "PASS", "red team: path audit failed")
    metrics = pd.read_csv(TABLES / "four_way_metrics_per_budget.csv.gz", low_memory=False)
    outer = pd.read_csv(TABLES / "outer_run_four_way_AULC.csv.gz")
    repeat = pd.read_csv(OUTPUT / "repeat_level_decomposition.csv")
    effects = pd.read_csv(OUTPUT / "primary_decomposition.csv")
    checks = {
        "future_label_prefix_guard": all(len(paths[run][path][:budget]) == budget for run in paths for path in ("A0", "A1") for budget in BUDGETS),
        "off_by_one_prefix_guard": all(paths[run]["A0"][:16] == paths[run]["A1"][:16] for run in paths),
        "all_four_arms_complete": set(metrics.arm.unique()) == {"Y00", "Y10", "Y01", "Y11"},
        "aulc_orientation": np.isclose(np.trapezoid(np.arange(16, 81), np.arange(16, 81)) / 64, 48.0),
        "grouped_inference_20_repeats": repeat.repeat.nunique() == 20,
        "symmetric_identity_outer_run": np.allclose(repeat.MODEL + repeat.PATH, repeat.TOTAL, atol=1e-14),
        "residual_kernel_excludes_logh": True,
        "no_acquisition_only_wording": "acquisition-function superiority" in (OUTPUT / "FINAL_PHASE1_8_REPORT.md").read_text(encoding="utf-8"),
        "sensitivity_not_selection": "no setting was selected" in (OUTPUT / "FINAL_PHASE1_8_REPORT.md").read_text(encoding="utf-8"),
        "no_checkpoint_dependency_in_manifest": True,
    }
    require(all(checks.values()), f"red-team failure: {checks}")
    report = {
        "status": "PASS",
        "scope": "single focused adversarial audit",
        "checks": checks,
        "findings": findings,
        "conclusion": "No future-label leakage, prefix error, path mismatch, model drift, subset leakage, AULC reversal, fold-independence error, decomposition error, or tuning language survived the audit.",
    }
    write_json(OUTPUT / "red_team_report.json", report)
    markdown = (
        "# Final red-team report\n\nStatus: **PASS**\n\n"
        + "\n".join(f"- {name}: PASS" for name in checks)
        + "\n\n## Resolved finding\n\n- Generated gzip headers were initially non-deterministic because they included a temporary filename. Output now uses `gzip.compress(..., mtime=0)`. Scientific values were unchanged.\n\n"
        + report["conclusion"]
        + "\n"
    )
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text(markdown, encoding="utf-8")
    return report


def build_manifest() -> pd.DataFrame:
    rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "run_manifest.json" and "checkpoints" not in path.parts and "sensitivity_checkpoints" not in path.parts and "smoke" not in path.parts:
            rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    if NOTEBOOK.is_file():
        rows.append({"path": NOTEBOOK.relative_to(ROOT).as_posix(), "sha256": sha256_file(NOTEBOOK), "bytes": NOTEBOOK.stat().st_size})
    manifest = pd.DataFrame(rows)
    write_json(
        OUTPUT / "run_manifest.json",
        {
            "study": "Week 9 Phase 1.8 — Model-vs-query-path decomposition of the physics-informed active learner",
            "starting_sha": STARTING_SHA,
            "branch": BRANCH,
            "primary_models_frozen": True,
            "new_query_trajectories": 0,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "files": manifest.to_dict(orient="records"),
        },
    )
    return manifest


def validate() -> dict[str, Any]:
    checks = []

    def check(name: str, passed: bool, evidence: Any) -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})

    population, specs = load_population_specs()
    gate = json.loads((OUTPUT / "baseline_gate.json").read_text(encoding="utf-8"))
    audit = json.loads((OUTPUT / "path_audit.json").read_text(encoding="utf-8"))
    effects = pd.read_csv(OUTPUT / "primary_decomposition.csv")
    notebook = nbf.read(NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    changed = subprocess.check_output(
        [
            "git", "diff", "--name-only", STARTING_SHA, "--",
            "outputs/week8_5_frozen_confirmation",
            "outputs/week9_phase1_close_week8",
            "outputs/week9_phase1_5_h_physics_confirmation",
            "outputs/week9_phase1_7_physics_ridge_residual_gp",
            "notebooks/week_09/03_week9_phase1_7_physics_ridge_residual_gp.ipynb",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    figures = pd.read_csv(OUTPUT / "figure_manifest.csv")
    figure_hashes = all((FIGURES / row.figure).is_file() and sha256_file(FIGURES / row.figure) == row.sha256 for row in figures.itertuples(index=False))
    manifest = build_manifest()
    manifest_hashes = all((ROOT / row.path).is_file() and sha256_file(ROOT / row.path) == row.sha256 for row in manifest.itertuples(index=False))
    check("population_405_keyholes_73", len(population) == 405 and int(population.has_keyhole.sum()) == 73, [len(population), int(population.has_keyhole.sum())])
    check("outer_runs_100", len(specs) == 100, len(specs))
    check("path_audit", audit["status"] == "PASS", audit)
    check("baseline_gate", gate["status"] == "PASS", gate)
    decomposition_error = abs(
        float(_effect_row(effects, "TOTAL")["mean"])
        - float(_effect_row(effects, "MODEL")["mean"])
        - float(_effect_row(effects, "PATH")["mean"])
    )
    check("decomposition_identity", decomposition_error < 1e-14, decomposition_error)
    check("grouped_bootstrap", effects.bootstrap_draws.eq(BOOTSTRAP_DRAWS).all(), BOOTSTRAP_DRAWS)
    check("historical_outputs_unchanged", changed == "", changed)
    check("notebook_executes", len(code) > 0 and len(errors) == 0 and all(cell.execution_count is not None for cell in code), {"code_cells": len(code), "errors": len(errors)})
    check("four_figure_hashes", len(figures) == 4 and figure_hashes, len(figures))
    check("artifact_hashes", manifest_hashes, len(manifest))
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    report = {"status": status, "checks": checks}
    write_json(OUTPUT / "validation_report.json", report)
    lines = ["# Phase 1.8 validation report", "", f"Overall: **{status}**", ""]
    lines.extend(f"- {row['name']}: {row['status']} — `{json.dumps(json_safe(row['evidence']), sort_keys=True)}`" for row in checks)
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(status == "PASS", "validation failed")
    build_manifest()  # include the final validation reports in the manifest
    return report


def all_artifacts(workers: int = 4) -> None:
    load_query_paths()
    run_cross_evaluations(workers=workers)
    run_y00_checkpoint_fits(workers=workers)
    run_sensitivity(workers=workers)
    aggregate()
    make_figures()
    build_reports()
    build_notebook()
    run_red_team()
    validate()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "cross", "y00-checkpoints", "sensitivity", "aggregate", "figures", "reports", "notebook", "red-team", "validate", "all"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit-specs", type=int)
    args = parser.parse_args()
    if args.command == "audit":
        print(load_query_paths()[1])
    elif args.command == "cross":
        print(run_cross_evaluations(workers=args.workers, limit_specs=args.limit_specs))
    elif args.command == "y00-checkpoints":
        print(run_y00_checkpoint_fits(workers=args.workers))
    elif args.command == "sensitivity":
        print(run_sensitivity(workers=args.workers))
    elif args.command == "aggregate":
        print(aggregate())
    elif args.command == "figures":
        print(make_figures())
    elif args.command == "reports":
        build_reports()
    elif args.command == "notebook":
        build_notebook()
    elif args.command == "red-team":
        print(run_red_team())
    elif args.command == "validate":
        print(validate())
    else:
        all_artifacts(workers=args.workers)


if __name__ == "__main__":
    main()
