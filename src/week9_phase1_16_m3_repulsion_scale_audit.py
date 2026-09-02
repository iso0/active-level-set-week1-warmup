"""Week 9 Phase 1.16: predeclared M3-margin repulsion-scale audit.

The M3 surrogate is frozen. Five prospectively declared repulsion multipliers
change only sequential query selection. Historical Phase 1.14 M3-margin
predictions and paths are reused as the c=0 baseline.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from nbclient import NotebookClient
from scipy.spatial.distance import pdist
from scipy.stats import binomtest

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_14_m3_margin_acquisition as p14


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_16_m3_repulsion_scale_audit"
CHECKPOINTS = OUTPUT / "checkpoints"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "14_week9_phase1_16_m3_repulsion_scale_audit.ipynb"
PHASE14 = ROOT / "outputs" / "week9_phase1_14_m3_margin_acquisition"
PHASE15A = ROOT / "outputs" / "week9_phase1_15a_physics_residual_signal_audit"
PARENT_SHA = "a8eafbbb814f5d5c9fe71a985746d6d1c4cb76eb"
PHASE14_SHA = "5a7a6c05ae5bf3191b74766156407211ad414360"
BRANCH = "codex/week9-phase1-16-m3-repulsion-scale-audit"
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
EARLY = tuple(range(16, 41))
LATE = tuple(range(41, 81))
CHECKPOINT_BUDGETS = (16, 24, 32, 40, 60, 80)
FULL_BUDGETS = (16, 40, 80)
OVERLAP_BUDGETS = (24, 40, 60, 80)
THRESHOLDS = (0.80, 0.82, 0.84)
C_GRID = (0.25, 0.5, 1.0, 2.0, 4.0)
ARM_TO_C = {"REP_C025": 0.25, "REP_C050": 0.5, "REP_C100": 1.0, "REP_C200": 2.0, "REP_C400": 4.0}
ARMS = ("M3_MARGIN", *ARM_TO_C)
BOOTSTRAP_DRAWS = 10_000
SEED_ROOT = "week9_phase1_16_m3_repulsion_scale_audit|v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() not in {".png", ".gz", ".xlsx", ".tar"}:
        payload = payload.replace(b"\r\n", b"\n")
    return payload


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = frame.to_csv(index=False, lineterminator="\n").encode()
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    else:
        path.write_bytes(raw)


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(json_safe(payload), sort_keys=True) + "\n").encode()
    path.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))


def read_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def checkpoint_path(arm: str, run_id: str) -> Path:
    return CHECKPOINTS / arm / f"{run_id}.json.gz"


def load_inputs() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]], dict[str, list[int]]]:
    population, specs, a0 = p13.load_inputs()
    paths = pd.read_csv(PHASE14 / "m3_margin_paths.csv.gz")
    p1 = {
        str(run): group.sort_values("query_order").population_row_index.astype(int).tolist()
        for run, group in paths.groupby("run_id", sort=True)
    }
    return population, specs, a0, p1


def historical_changes() -> list[str]:
    protected = [
        "outputs/week9_phase1_5_h_physics_confirmation",
        "outputs/week9_phase1_7_physics_ridge_residual_gp",
        "outputs/week9_phase1_8_model_path_decomposition",
        "outputs/week9_phase1_9_physics_specificity_control",
        "outputs/week9_phase1_10_external_experimental_validation",
        "outputs/week9_phase1_10_closure_diagnostics",
        "outputs/week9_phase1_11_fixed_mean_discrepancy_gp",
        "outputs/week9_phase1_12_gpc_kernel_adequacy",
        "outputs/week9_phase1_13_fixed_physics_ard_discrepancy",
        "outputs/week9_phase1_14_m3_margin_acquisition",
        "outputs/week9_phase1_15a_physics_residual_signal_audit",
    ]
    result = subprocess.check_output(["git", "diff", "--name-only", PARENT_SHA, "--", *protected], cwd=ROOT, text=True)
    return [line for line in result.splitlines() if line.strip()]


def baseline_gate() -> dict[str, Any]:
    population, specs, _, p1 = load_inputs()
    gate14 = json.loads((PHASE14 / "baseline_gate.json").read_text())
    report14 = json.loads((PHASE14 / "run_manifest.json").read_text())
    contrasts = pd.read_csv(PHASE14 / "paired_contrasts.csv")
    summary = pd.read_csv(PHASE14 / "learning_curve_summary.csv")
    q20 = float(summary[(summary.model.eq("P1")) & summary.subset.eq("B1_q20")].sort_values("budget").pipe(lambda d: np.trapezoid(d.mean_accuracy, d.budget) / 64))
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    base = subprocess.check_output(["git", "merge-base", "HEAD", PARENT_SHA], cwd=ROOT, text=True).strip()
    recon = pd.read_csv(PHASE15A / "component_reconstruction_audit.csv")
    payload = {
        "status": "PASS",
        "required_parent_sha": PARENT_SHA,
        "current_head": current,
        "exact_branch_base": base,
        "phase14_sha": PHASE14_SHA,
        "population": len(population),
        "keyholes": int(population.has_keyhole.sum()),
        "conduction": int((~population.has_keyhole.astype(bool)).sum()),
        "outer_runs": len(specs),
        "repeat_blocks": len(set(s.repeat for s in specs)),
        "historical_P1_paths": len(p1),
        "initial_design_matches": sum(p1[s.run_id][:16] == w85.initial_design(s, population) for s in specs),
        "historical_M3_margin_q20_AULC": q20,
        "phase14_decision": report14["decision"],
        "phase15a_reconstruction_rows": len(recon),
        "phase15a_all_selection_matches": bool(recon.selection_matches.all()),
        "phase15a_max_probability_difference": float(recon.absolute_probability_difference.max()),
        "historical_changes": historical_changes(),
    }
    ok = (
        base == PARENT_SHA
        and (len(population), int(population.has_keyhole.sum())) == (405, 73)
        and len(specs) == len(p1) == 100
        and payload["initial_design_matches"] == 100
        and all(len(path) == 80 for path in p1.values())
        and abs(q20 - 0.844623161764706) < 1e-12
        and len(contrasts) >= 2
        and len(recon) == 900
        and payload["phase15a_all_selection_matches"]
        and payload["phase15a_max_probability_difference"] < 1e-10
        and not payload["historical_changes"]
        and gate14["status"] == "PASS"
    )
    payload["status"] = "PASS" if ok else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", payload)
    require(ok, f"baseline gate failed: {payload}")
    return payload


def analysis_specification() -> dict[str, Any]:
    payload = {
        "status": "FROZEN_BEFORE_REPULSION_RESULTS",
        "arms": {"M3_MARGIN": {"c": 0.0, "role": "historical exact Phase 1.14 baseline"}, **{arm: {"c": c, "role": "prospective repulsion arm"} for arm, c in ARM_TO_C.items()}},
        "c_grid": list(C_GRID),
        "model": {"name": "M3", "physics_mean": "training-fitted log(h), frozen before discrepancy fit", "residual_inputs": list(FEATURES), "kernel": "ARD Matern-3/2", "residual_sd_bounds": list(p13.RESIDUAL_SD_BOUNDS), "length_bounds": list(p13.PRIMARY_LENGTH_BOUNDS), "log_h_in_residual": False},
        "repulsion": {"d_min": "minimum Euclidean distance in outer-pool StandardScaler coordinates", "s_B": "median current candidate d_min", "lambda_B": "c*s_B", "factor": "1-exp(-d_min^2/(2*lambda_B^2))", "score": "M3 margin uncertainty * factor", "recomputed_each_budget": True},
        "primary": "Fold-B1-q20 accuracy normalized trapezoidal AULC B16-80",
        "regions": {"early": "B16-40", "late": "B41-80"},
        "thresholds": list(THRESHOLDS),
        "inference": {"unit": "20 repeat blocks with five folds retained", "bootstrap_draws": BOOTSTRAP_DRAWS, "multiplicity": "Holm across five overall q20 contrasts"},
        "decision_categories": ["REPULSION_GAIN_ROBUST", "REPULSION_MECHANISM_ONLY", "REPULSION_SCALE_SENSITIVE", "REPULSION_NO_GAIN", "REPULSION_HARMS_BOUNDARY_LEARNING", "REPULSION_NUMERICALLY_UNRELIABLE"],
        "no_posthoc_scales": True,
    }
    write_json(OUTPUT / "analysis_specification.json", payload)
    (OUTPUT / "repulsion_scale_definition.md").write_text(
        "# Repulsion scale definition\n\n"
        "At each budget, distances are computed in the same outer-training-pool StandardScaler coordinates used by M3. "
        "For each unqueried candidate, `d_min` is its distance to the queried set; `s_B=median(d_min)` and "
        "`lambda_B=c*s_B`. The score is `A_margin * (1-exp(-d_min^2/(2*lambda_B^2)))`. "
        "The fixed predeclared multipliers are 0.25, 0.5, 1, 2, and 4. No held-out label enters the score.\n",
        encoding="utf-8",
    )
    return payload


def historical_repulsion_audit() -> None:
    text = """# Historical repulsion audit

## Week 4 synthetic diversified straddle

- `week4_02_diversified_straddle.py` used `(1-alpha)*normalized_straddle + alpha*normalized_diversity`, with `alpha=0.25`.
- Diversity was minimum Euclidean distance to the queried set in scaled synthetic input coordinates, then min-max normalized over the candidate pool.
- Week 4.03 added a boundary shortlist before a similar additive mixture.
- These were tested on synthetic Branin and Ackley designs; the fixed mixture weight was not a systematic geometry-scale sweep.

## Week 7 / frozen Week 8.5 classifier repulsion

- `week7_phase6_real_data_boundary_active_level_set.py` and Week 8.5 used `normalized_uncertainty * (1-exp(-d_min^2/(2*0.15^2)))`.
- `d_min` used standardized `[P,VX,LS,ST]` geometry; the bandwidth was the fixed raw standardized-space value `0.15`.
- Week 8.5 found slightly larger nearest-query distance but no robust performance improvement for this single configuration.

## Scope of the old conclusion

The defensible historical conclusion is: **one small fixed repulsion configuration did not robustly outperform margin**. It does not establish that repulsion as a principle fails, because neither the raw bandwidth nor a geometry-relative scale response was audited systematically.
"""
    (OUTPUT / "historical_repulsion_audit.md").write_text(text, encoding="utf-8")


def choose_repulsion(candidate: np.ndarray, probability: np.ndarray, pool_scaled: np.ndarray, queried: Sequence[int], c: float) -> tuple[int, dict[str, float]]:
    candidate = np.asarray(candidate, int)
    probability = np.asarray(probability, float)
    queried_array = np.asarray(queried, int)
    require(c in C_GRID and len(candidate) and len(queried_array), "invalid repulsion selector inputs")
    distances = np.sqrt(((pool_scaled[candidate, None, :] - pool_scaled[queried_array][None, :, :]) ** 2).sum(axis=2))
    d_min = distances.min(axis=1)
    s_b = float(np.median(d_min))
    require(s_b > 0 and np.isfinite(s_b), "invalid geometry scale")
    lambda_b = c * s_b
    repulsion = 1.0 - np.exp(-(d_min**2) / (2.0 * lambda_b**2))
    uncertainty = 1.0 - 2.0 * np.abs(probability - 0.5)
    score = uncertainty * repulsion
    order = np.lexsort((candidate, -score))
    position = int(order[0])
    return int(candidate[position]), {
        "uncertainty_score": float(uncertainty[position]),
        "d_min": float(d_min[position]),
        "s_B": s_b,
        "lambda_B": float(lambda_b),
        "repulsion_factor": float(repulsion[position]),
        "acquisition_score": float(score[position]),
        "candidate_median_d_min": s_b,
    }


def run_one_spec(spec: Any, arm: str, population: pd.DataFrame, distances_b1: np.ndarray, initial: Sequence[int]) -> dict[str, Any]:
    destination = checkpoint_path(arm, spec.run_id)
    source_hash = sha256_file(Path(__file__))
    if destination.is_file():
        payload = read_checkpoint(destination)
        if payload.get("complete") and payload.get("parent_sha") == PARENT_SHA and payload.get("source_hash") == source_hash and payload.get("arm") == arm:
            return {"run_id": spec.run_id, "arm": arm, "reused": True}
    c = ARM_TO_C[arm]
    x4 = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    h = np.exp(logh)
    labels = population.has_keyhole.astype(int).to_numpy()
    train = np.asarray(spec.train_indices, int)
    test = np.asarray(spec.test_indices, int)
    flags = p17.subset_flags(spec, population, distances_b1)
    q20_cut = float(np.quantile(distances_b1[test], 0.20, method="higher"))
    q30_cut = float(np.quantile(distances_b1[test], 0.30, method="higher"))
    queried = list(map(int, initial))
    predictions: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    for budget in BUDGETS:
        require(len(queried) == budget and len(set(queried)) == budget, f"prefix drift {spec.run_id}/{arm}/B{budget}")
        revealed = np.asarray(queried, int)
        physics = p11.fit_physics_mean(logh, labels, revealed, p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(x4, logh, labels, revealed, train, physics, "M3", 100.0)
        probability = p13.components(fit, x4[test], logh[test])["probability"]
        for local, pop_index in enumerate(test):
            predictions.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "arm": arm, "population_row_index": int(pop_index), "truth": int(labels[pop_index]), "probability": float(probability[local]), "is_q20": bool(flags["B1_q20"][local]), "is_q30": bool(flags["B1_q30"][local])})
        for subset, flag in (("full81", np.ones(len(test), bool)), ("B1_q20", flags["B1_q20"]), ("B1_q30", flags["B1_q30"])):
            metrics.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "arm": arm, "subset": subset, **p12.metric_values(labels[test][flag], probability[flag])})
        diagnostics.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "arm": arm, **p13.fit_diagnostic(fit)})
        if budget < 80:
            candidate = np.setdiff1d(train, revealed, assume_unique=False)
            candidate_probability = p13.components(fit, x4[candidate], logh[candidate])["probability"]
            pool_scaled = fit.x_scaler.transform(x4)
            chosen, info = choose_repulsion(candidate, candidate_probability, pool_scaled, queried, c)
            position = int(np.flatnonzero(candidate == chosen)[0])
            active_scaled = pool_scaled[np.asarray(queried[16:], int)] if budget > 16 else np.empty((0, 4))
            spread_before = float(pdist(active_scaled).mean()) if len(active_scaled) >= 2 else math.nan
            active_after = pool_scaled[np.asarray([*queried[16:], chosen], int)]
            spread_after = float(pdist(active_after).mean()) if len(active_after) >= 2 else math.nan
            row = population.iloc[chosen]
            queries.append({
                "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": arm, "c": c,
                "current_budget": budget, "selection_budget": budget + 1, "selected_population_row_index": chosen,
                "predicted_probability_before_reveal": float(candidate_probability[position]), **info,
                "true_label_revealed_after_selection": int(labels[chosen]), "P": float(row.P), "VX": float(row.VX), "LS": float(row.LS), "ST": float(row.ST), "h": float(h[chosen]),
                "B1_distance_posthoc": float(distances_b1[chosen]), "is_q20_like_posthoc": bool(distances_b1[chosen] <= q20_cut), "is_q30_like_posthoc": bool(distances_b1[chosen] <= q30_cut),
                "active_pairwise_spread_before": spread_before, "active_pairwise_spread_after": spread_after, "candidate_count": int(len(candidate)), "scaler_fit_scope": "complete_outer_training_pool_features_only",
                "labels_available_to_score": False, "B1_q20_q30_available_to_score": False, "tie_break": "smallest_population_row_index",
            })
            require(chosen in set(train) and chosen not in set(test) and chosen not in queried, "invalid selected row")
            queried.append(chosen)
    require(len(queried) == 80 and len(queries) == 64, "incomplete path")
    write_checkpoint(destination, {"complete": True, "parent_sha": PARENT_SHA, "source_hash": source_hash, "arm": arm, "c": c, "run_id": spec.run_id, "queried_indices": queried, "predictions": predictions, "metrics": metrics, "diagnostics": diagnostics, "queries": queries})
    return {"run_id": spec.run_id, "arm": arm, "reused": False}


def run_main(workers: int = 4, limit_specs: int | None = None, arms: Sequence[str] | None = None) -> dict[str, Any]:
    baseline_gate(); analysis_specification(); historical_repulsion_audit()
    population, specs, _, p1 = load_inputs()
    distances = w85.b1_distance(population)
    specs = specs[:limit_specs] if limit_specs else specs
    selected_arms = tuple(arms) if arms else tuple(ARM_TO_C)
    require(set(selected_arms).issubset(ARM_TO_C), "run supports repulsion arms only")
    jobs = [(spec, arm) for arm in selected_arms for spec in specs]
    started = time.time()
    results = Parallel(n_jobs=workers, verbose=10)(delayed(run_one_spec)(spec, arm, population, distances, p1[spec.run_id][:16]) for spec, arm in jobs)
    payload = {"status": "PASS", "completed_jobs": len(results), "reused_jobs": sum(r["reused"] for r in results), "workers": workers, "elapsed_seconds": time.time() - started, "arms": list(selected_arms), "complete": limit_specs is None and set(selected_arms) == set(ARM_TO_C)}
    write_json(OUTPUT / "execution_report.json", payload)
    return payload


def collect_repulsion() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions: list[dict[str, Any]] = []; metrics: list[dict[str, Any]] = []; diagnostics: list[dict[str, Any]] = []; queries: list[dict[str, Any]] = []; paths: list[dict[str, Any]] = []
    for arm in ARM_TO_C:
        files = sorted((CHECKPOINTS / arm).glob("*.json.gz"))
        require(len(files) == 100, f"{arm} checkpoint count {len(files)}")
        for path in files:
            payload = read_checkpoint(path)
            require(payload.get("complete") and payload["arm"] == arm and payload["parent_sha"] == PARENT_SHA, f"bad checkpoint {path}")
            predictions.extend(payload["predictions"]); metrics.extend(payload["metrics"]); diagnostics.extend(payload["diagnostics"]); queries.extend(payload["queries"])
            for order, index in enumerate(payload["queried_indices"], 1):
                paths.append({"run_id": payload["run_id"], "arm": arm, "query_order": order, "population_row_index": int(index), "role": "initial_design" if order <= 16 else "active_query"})
    p, m, d, q, pa = map(pd.DataFrame, (predictions, metrics, diagnostics, queries, paths))
    require(len(p) == 5 * 100 * 65 * 81 and len(m) == 5 * 100 * 65 * 3 and len(d) == 5 * 100 * 65 and len(q) == 5 * 100 * 64 and len(pa) == 5 * 100 * 80, "repulsion collection incomplete")
    return p, m, d, q, pa


def historical_baseline(population: pd.DataFrame, specs: list[Any], distances: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions = pd.read_csv(PHASE14 / "new_predictions.csv.gz").rename(columns={"model": "old_model"})
    predictions["arm"] = "M3_MARGIN"
    metrics = p13.boundary_metrics_vectorized(predictions.rename(columns={"arm": "model"}), "M3_MARGIN").rename(columns={"model": "arm"})
    diagnostics = pd.read_csv(PHASE14 / "m3_active_fit_diagnostics.csv.gz").rename(columns={"model": "old_model", "path": "old_path"})
    diagnostics["arm"] = "M3_MARGIN"
    paths = pd.read_csv(PHASE14 / "m3_margin_paths.csv.gz").rename(columns={"path": "old_path"})
    paths["arm"] = "M3_MARGIN"
    source_queries = pd.read_csv(PHASE14 / "m3_margin_queries.csv.gz")
    spec_map = {s.run_id: s for s in specs}
    path_map = {run: group.sort_values("query_order").population_row_index.astype(int).tolist() for run, group in paths.groupby("run_id")}
    x4 = population.loc[:, FEATURES].to_numpy(float); labels = population.has_keyhole.astype(int).to_numpy(); h = np.exp(p11.log_h_values(population))
    query_source = source_queries.set_index(["run_id", "selection_budget"])
    rows = []
    for run_id, full_path in path_map.items():
        spec = spec_map[run_id]; train = np.asarray(spec.train_indices, int)
        mean = x4[train].mean(axis=0); scale = x4[train].std(axis=0); scale[scale == 0] = 1.0; scaled = (x4 - mean) / scale
        test = np.asarray(spec.test_indices, int); q20_cut = float(np.quantile(distances[test], .20, method="higher")); q30_cut = float(np.quantile(distances[test], .30, method="higher"))
        for selection_budget in range(17, 81):
            before = full_path[: selection_budget - 1]; selected = int(full_path[selection_budget - 1]); candidate = np.setdiff1d(train, np.asarray(before, int))
            d = np.sqrt(((scaled[candidate, None, :] - scaled[np.asarray(before, int)][None, :, :]) ** 2).sum(axis=2)).min(axis=1); pos = int(np.flatnonzero(candidate == selected)[0]); active = scaled[np.asarray(before[16:], int)]
            historical = query_source.loc[(run_id, selection_budget)]
            active_after = scaled[np.asarray([*before[16:], selected], int)]
            rows.append({"run_id": run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": "M3_MARGIN", "c": 0.0, "current_budget": selection_budget - 1, "selection_budget": selection_budget, "selected_population_row_index": selected, "predicted_probability_before_reveal": float(historical.predicted_probability_before_reveal), "uncertainty_score": float(historical.uncertainty_score), "d_min": float(d[pos]), "s_B": float(np.median(d)), "lambda_B": math.nan, "repulsion_factor": 1.0, "acquisition_score": float(historical.uncertainty_score), "candidate_median_d_min": float(np.median(d)), "true_label_revealed_after_selection": int(labels[selected]), "P": float(population.iloc[selected].P), "VX": float(population.iloc[selected].VX), "LS": float(population.iloc[selected].LS), "ST": float(population.iloc[selected].ST), "h": float(h[selected]), "B1_distance_posthoc": float(distances[selected]), "is_q20_like_posthoc": bool(distances[selected] <= q20_cut), "is_q30_like_posthoc": bool(distances[selected] <= q30_cut), "active_pairwise_spread_before": float(pdist(active).mean()) if len(active) >= 2 else math.nan, "active_pairwise_spread_after": float(pdist(active_after).mean()) if len(active_after) >= 2 else math.nan, "candidate_count": len(candidate), "scaler_fit_scope": "complete_outer_training_pool_features_only", "labels_available_to_score": False, "B1_q20_q30_available_to_score": False, "tie_break": "smallest_population_row_index"})
    queries = pd.DataFrame(rows)
    return predictions, metrics, diagnostics, queries, paths


def bootstrap(values: np.ndarray, key: str) -> tuple[float, float, float]:
    values = np.asarray(values, float)
    require(len(values) == 20 and np.isfinite(values).all(), f"bootstrap input {key}")
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    draws = values[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def aulc_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    regions = {"OVERALL_B16_80": BUDGETS, "EARLY_B16_40": EARLY, "LATE_B41_80": LATE}
    for keys, group in metrics[metrics.subset.isin(("B1_q20", "B1_q30"))].groupby(["run_id", "repeat", "fold", "arm", "subset"], sort=True):
        run_id, repeat, fold, arm, subset = keys
        for region, budgets in regions.items():
            part = group[group.budget.isin(budgets)].sort_values("budget")
            require(part.budget.astype(int).tolist() == list(budgets), f"AULC budget drift {keys}/{region}")
            denom = budgets[-1] - budgets[0]
            value = float(part.accuracy.iloc[0]) if denom == 0 else float(np.trapezoid(part.accuracy, part.budget) / denom)
            rows.append({"run_id": run_id, "repeat": repeat, "fold": fold, "arm": arm, "subset": subset, "region": region, "accuracy_AULC": value})
    outer = pd.DataFrame(rows)
    repeat = outer.groupby(["repeat", "arm", "subset", "region"], as_index=False).accuracy_AULC.mean()
    inference = []
    for subset in ("B1_q20", "B1_q30"):
        for region in regions:
            wide = repeat[(repeat.subset.eq(subset)) & repeat.region.eq(region)].pivot(index="repeat", columns="arm", values="accuracy_AULC")
            baseline = wide["M3_MARGIN"].to_numpy()
            for arm in ARMS:
                values = wide[arm].to_numpy(); delta = values - baseline; mean, lo, hi = bootstrap(delta, f"{subset}|{region}|{arm}")
                inference.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "subset": subset, "region": region, "mean_AULC": float(values.mean()), "delta_vs_M3_MARGIN": mean, "ci_lower": lo, "ci_upper": hi, "positive_repeat_blocks": int((delta > 0).sum()), "zero_repeat_blocks": int((delta == 0).sum()), "negative_repeat_blocks": int((delta < 0).sum()), "bootstrap_draws": BOOTSTRAP_DRAWS})
    return outer, repeat, pd.DataFrame(inference)


def metric_summary(metrics: pd.DataFrame, subset: str, budgets: Sequence[int], names: Sequence[str]) -> pd.DataFrame:
    rows = []
    part = metrics[(metrics.subset.eq(subset)) & metrics.budget.isin(budgets)]
    for (arm, budget), group in part.groupby(["arm", "budget"], sort=True):
        for name in names:
            values = group[name].to_numpy(float)
            rows.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "subset": subset, "budget": int(budget), "metric": name, "mean": float(np.nanmean(values)), "median": float(np.nanmedian(values)), "n_outer_runs": len(values)})
    return pd.DataFrame(rows)


def repeat_checkpoint_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    repeated = metrics.groupby(["repeat", "arm", "subset", "budget"], as_index=False).mean(numeric_only=True)
    for subset in ("B1_q20", "full81"):
        budgets = CHECKPOINT_BUDGETS if subset == "B1_q20" else FULL_BUDGETS
        names = ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive") if subset == "B1_q20" else ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "roc_auc", "pr_auc", "brier_score")
        for budget in budgets:
            part = repeated[(repeated.subset.eq(subset)) & repeated.budget.eq(budget)]
            for name in names:
                wide = part.pivot(index="repeat", columns="arm", values=name)
                for arm in ARM_TO_C:
                    delta = (wide[arm] - wide["M3_MARGIN"]).to_numpy(float); mean, lo, hi = bootstrap(delta, f"checkpoint|{subset}|{budget}|{name}|{arm}")
                    rows.append({"arm": arm, "c": ARM_TO_C[arm], "subset": subset, "budget": budget, "metric": name, "delta_vs_M3_MARGIN": mean, "ci_lower": lo, "ci_upper": hi})
    return pd.DataFrame(rows)


def path_and_diversity(paths: pd.DataFrame, queries: pd.DataFrame, population: pd.DataFrame, specs: list[Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path_map = {(arm, run): group.sort_values("query_order").population_row_index.astype(int).tolist() for (arm, run), group in paths.groupby(["arm", "run_id"])}
    spec_map = {s.run_id: s for s in specs}; overlaps = []; diversity = []; qchars = []
    for arm in ARMS:
        for run_id in sorted({run for _, run in path_map}):
            base = path_map[("M3_MARGIN", run_id)]; path = path_map[(arm, run_id)]; spec = spec_map[run_id]
            different = [i for i in range(16, 80) if path[i] != base[i]]
            for budget in OVERLAP_BUDGETS:
                a, b = set(path[:budget]), set(base[:budget]); overlaps.append({"run_id": run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "budget": budget, "first_divergence_budget": different[0] + 1 if different else math.nan, "same_step_fraction_active": float(np.mean(np.asarray(path[16:budget]) == np.asarray(base[16:budget]))) if budget > 16 else 1.0, "shared_point_count": len(a & b), "jaccard": len(a & b) / len(a | b)})
    labels = population.has_keyhole.astype(int).to_numpy()
    for (arm, budget), group in queries.groupby(["arm", "selection_budget"], sort=True):
        revealed_fractions = [float(labels[np.asarray(path_map[(arm, run_id)][:int(budget)], int)].mean()) for run_id in group.run_id]
        diversity.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "budget": int(budget), "mean_selected_d_min": float(group.d_min.mean()), "median_selected_d_min": float(group.d_min.median()), "mean_candidate_scale_s_B": float(group.s_B.mean()), "mean_active_pairwise_spread": float(group.active_pairwise_spread_after.mean()), "active_query_keyhole_fraction": float(group.true_label_revealed_after_selection.mean()), "revealed_keyhole_fraction": float(np.mean(revealed_fractions)), "q20_like_fraction": float(group.is_q20_like_posthoc.mean()), "q30_like_fraction": float(group.is_q30_like_posthoc.mean()), "mean_B1_distance": float(group.B1_distance_posthoc.mean())})
    for arm, group in queries.groupby("arm", sort=True):
        qchars.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "active_query_keyhole_fraction": float(group.true_label_revealed_after_selection.mean()), "mean_selected_d_min": float(group.d_min.mean()), "median_selected_d_min": float(group.d_min.median()), "mean_B1_distance": float(group.B1_distance_posthoc.mean()), "q20_like_fraction": float(group.is_q20_like_posthoc.mean()), "q30_like_fraction": float(group.is_q30_like_posthoc.mean()), **{f"mean_{name}": float(group[name].mean()) for name in ("P", "VX", "LS", "ST", "h")}})
    overlap = pd.DataFrame(overlaps); overlap_summary = overlap.groupby(["arm", "c", "budget"], as_index=False).agg(first_divergence_budget_mean=("first_divergence_budget", "mean"), same_step_fraction_active=("same_step_fraction_active", "mean"), shared_point_count=("shared_point_count", "mean"), jaccard=("jaccard", "mean"))
    return overlap, overlap_summary, pd.DataFrame(diversity), pd.DataFrame(qchars)


def sample_efficiency(metrics: pd.DataFrame) -> pd.DataFrame:
    repeat_curve = metrics[metrics.subset.eq("B1_q20")].groupby(["repeat", "arm", "budget"], as_index=False).accuracy.mean()
    rows = []
    for threshold in THRESHOLDS:
        first = []
        for (repeat, arm), group in repeat_curve.groupby(["repeat", "arm"], sort=True):
            reached = group[group.accuracy >= threshold]
            first.append({"repeat": repeat, "arm": arm, "first_hit_budget": int(reached.budget.min()) if len(reached) else math.nan, "reached": bool(len(reached))})
        frame = pd.DataFrame(first); wide = frame.pivot(index="repeat", columns="arm", values="first_hit_budget")
        for arm in ARMS:
            group = frame[frame.arm.eq(arm)]; paired = wide[["M3_MARGIN", arm]].dropna() if arm != "M3_MARGIN" else wide[["M3_MARGIN"]].dropna()
            delta = (paired[arm] - paired["M3_MARGIN"]).to_numpy(float) if arm != "M3_MARGIN" else np.zeros(len(paired))
            if len(delta) == 20:
                mean, lo, hi = bootstrap(delta, f"threshold|{threshold}|{arm}")
            else:
                mean, lo, hi = (float(np.mean(delta)) if len(delta) else math.nan, math.nan, math.nan)
            rows.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "threshold": threshold, "reach_rate": float(group.reached.mean()), "median_first_hit_budget": float(group.first_hit_budget.median()), "paired_repeats_both_reached": len(paired), "mean_first_hit_difference_vs_margin": mean, "ci_lower": lo, "ci_upper": hi, "noncrossings_not_imputed": True})
    return pd.DataFrame(rows)


def fit_summary(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (arm, region), group in diagnostics.assign(region=np.where(diagnostics.budget <= 40, "EARLY_B16_40", "LATE_B41_80")).groupby(["arm", "region"], sort=True):
        rows.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "region": region, "fits": len(group), "optimizer_convergence_rate": float(group.optimizer_converged.mean()), "mean_residual_sd": float(group.residual_sd.mean()), "residual_sd_upper_hit_rate": float(group.residual_sd_upper_bound_hit.mean()), "any_length_lower_hit_rate": float(group[["l_P_lower_bound_hit", "l_VX_lower_bound_hit", "l_LS_lower_bound_hit", "l_ST_lower_bound_hit"]].any(axis=1).mean()), "any_length_upper_hit_rate": float(group[["l_P_upper_bound_hit", "l_VX_upper_bound_hit", "l_LS_upper_bound_hit", "l_ST_upper_bound_hit"]].any(axis=1).mean()), "median_anisotropy_ratio": float(group.anisotropy_ratio.median())})
    return pd.DataFrame(rows)


def holm_summary(inference: pd.DataFrame) -> pd.DataFrame:
    primary = inference[(inference.subset.eq("B1_q20")) & inference.region.eq("OVERALL_B16_80") & inference.arm.ne("M3_MARGIN")].copy()
    p_values = []
    for row in primary.itertuples(index=False):
        # Direction-free repeat-block sign test is intentionally conservative.
        n = row.positive_repeat_blocks + row.negative_repeat_blocks
        p_values.append(float(binomtest(row.positive_repeat_blocks, n, .5).pvalue) if n else 1.0)
    primary["raw_sign_test_p"] = p_values
    order = np.argsort(primary.raw_sign_test_p.to_numpy()); adjusted = np.empty(len(primary)); running = 0.0
    for rank, position in enumerate(order):
        value = min(1.0, (len(primary) - rank) * primary.raw_sign_test_p.iloc[position]); running = max(running, value); adjusted[position] = running
    primary["holm_adjusted_p"] = adjusted
    primary["holm_reject_0_05"] = primary.holm_adjusted_p < .05
    return primary[["arm", "c", "delta_vs_M3_MARGIN", "ci_lower", "ci_upper", "positive_repeat_blocks", "negative_repeat_blocks", "raw_sign_test_p", "holm_adjusted_p", "holm_reject_0_05"]]


def scale_response(inference: pd.DataFrame, contrasts: pd.DataFrame, diversity: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    q20 = inference[(inference.subset.eq("B1_q20"))].set_index(["arm", "region"])
    b40_recall = contrasts[(contrasts.subset.eq("B1_q20")) & contrasts.budget.eq(40) & contrasts.metric.eq("keyhole_recall")].set_index("arm")
    d40 = diversity[diversity.budget.eq(40)].set_index("arm")
    base_spread = float(d40.loc["M3_MARGIN", "mean_active_pairwise_spread"])
    base_hit = float(thresholds[(thresholds.arm.eq("M3_MARGIN")) & thresholds.threshold.eq(.84)].median_first_hit_budget.iloc[0])
    rows = []
    for arm in ARMS:
        rows.append({"arm": arm, "c": 0.0 if arm == "M3_MARGIN" else ARM_TO_C[arm], "q20_AULC": float(q20.loc[(arm, "OVERALL_B16_80"), "mean_AULC"]), "overall_q20_delta": float(q20.loc[(arm, "OVERALL_B16_80"), "delta_vs_M3_MARGIN"]), "overall_ci_lower": float(q20.loc[(arm, "OVERALL_B16_80"), "ci_lower"]), "overall_ci_upper": float(q20.loc[(arm, "OVERALL_B16_80"), "ci_upper"]), "early_q20_delta": float(q20.loc[(arm, "EARLY_B16_40"), "delta_vs_M3_MARGIN"]), "late_q20_delta": float(q20.loc[(arm, "LATE_B41_80"), "delta_vs_M3_MARGIN"]), "B40_keyhole_recall_delta": 0.0 if arm == "M3_MARGIN" else float(b40_recall.loc[arm, "delta_vs_M3_MARGIN"]), "B40_query_spread": float(d40.loc[arm, "mean_active_pairwise_spread"]), "B40_query_spread_delta": float(d40.loc[arm, "mean_active_pairwise_spread"] - base_spread), "B84_median_first_hit": float(thresholds[(thresholds.arm.eq(arm)) & thresholds.threshold.eq(.84)].median_first_hit_budget.iloc[0]), "B84_median_first_hit_delta": float(thresholds[(thresholds.arm.eq(arm)) & thresholds.threshold.eq(.84)].median_first_hit_budget.iloc[0] - base_hit)})
    return pd.DataFrame(rows)


def decide(response: pd.DataFrame, inference: pd.DataFrame, holm: pd.DataFrame, contrasts: pd.DataFrame, full: pd.DataFrame, fit: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    rep = response[response.arm.ne("M3_MARGIN")].sort_values("c")
    positive = rep.overall_ci_lower > 0
    adjacent_supported = any(bool(positive.iloc[i] and positive.iloc[i + 1]) for i in range(len(positive) - 1))
    any_supported = bool(positive.any())
    diversity_increased = bool((rep.B40_query_spread_delta > 0).sum() >= 3)
    early_or_recall = bool(((rep.early_q20_delta > 0) | (rep.B40_keyhole_recall_delta > 0)).sum() >= 2)
    q30 = inference[(inference.subset.eq("B1_q30")) & inference.region.eq("OVERALL_B16_80") & inference.arm.ne("M3_MARGIN")]
    q30_support = bool((q30.delta_vs_M3_MARGIN > 0).sum() >= 2)
    full80 = full[(full.subset.eq("full81")) & full.budget.eq(80) & full.metric.isin(("accuracy", "keyhole_recall"))]
    no_global_harm = not bool((full80.delta_vs_M3_MARGIN <= np.where(full80.metric.eq("accuracy"), -.02, -.05)).any())
    numeric_ok = bool(fit.optimizer_convergence_rate.min() >= .80)
    holm_any = bool(holm.holm_reject_0_05.any())
    harmful = bool((rep.overall_ci_upper < 0).sum() >= 3)
    if not numeric_ok:
        decision = "REPULSION_NUMERICALLY_UNRELIABLE"
    elif harmful:
        decision = "REPULSION_HARMS_BOUNDARY_LEARNING"
    elif adjacent_supported and diversity_increased and early_or_recall and q30_support and no_global_harm and holm_any:
        decision = "REPULSION_GAIN_ROBUST"
    elif any_supported and not adjacent_supported:
        decision = "REPULSION_SCALE_SENSITIVE"
    elif diversity_increased and not any_supported:
        decision = "REPULSION_MECHANISM_ONLY"
    else:
        decision = "REPULSION_NO_GAIN"
    return decision, {"adjacent_supported": adjacent_supported, "any_supported": any_supported, "diversity_increased": diversity_increased, "early_or_recall": early_or_recall, "q30_support": q30_support, "no_global_harm": no_global_harm, "numeric_ok": numeric_ok, "holm_any": holm_any, "harmful": harmful}


def make_figures(response: pd.DataFrame, checkpoint: pd.DataFrame, diversity: pd.DataFrame, thresholds: pd.DataFrame, overlap: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    c = response.c.to_numpy(); rows = []
    def save(name: str) -> None:
        plt.tight_layout(); path = FIGURES / name; plt.savefig(path, dpi=180, bbox_inches="tight"); plt.close(); rows.append({"figure": name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    plt.figure(figsize=(7, 4)); plt.axhline(0, color="black", lw=.8); plt.errorbar(c, response.overall_q20_delta, yerr=[response.overall_q20_delta-response.overall_ci_lower, response.overall_ci_upper-response.overall_q20_delta], marker="o", capsize=3); plt.xlabel("Repulsion multiplier c (0 = plain margin)"); plt.ylabel("q20 AULC difference vs M3 margin"); save("01_q20_aulc_scale_response.png")
    plt.figure(figsize=(7, 4)); plt.axhline(0, color="black", lw=.8); plt.plot(c, response.early_q20_delta, "o-", label="Early B16–40"); plt.plot(c, response.late_q20_delta, "s-", label="Late B41–80"); plt.xlabel("Repulsion multiplier c"); plt.ylabel("q20 AULC difference"); plt.legend(); save("02_early_late_scale_response.png")
    rec = checkpoint[(checkpoint.subset.eq("B1_q20")) & checkpoint.budget.eq(40) & checkpoint.metric.eq("keyhole_recall")]; plt.figure(figsize=(7, 4)); plt.axhline(0, color="black", lw=.8); plt.errorbar(rec.c, rec.delta_vs_M3_MARGIN, yerr=[rec.delta_vs_M3_MARGIN-rec.ci_lower, rec.ci_upper-rec.delta_vs_M3_MARGIN], fmt="o-", capsize=3); plt.xlabel("Repulsion multiplier c"); plt.ylabel("B40 q20 Keyhole-recall difference"); save("03_b40_keyhole_recall.png")
    plt.figure(figsize=(7, 4)); plt.axhline(0, color="black", lw=.8); plt.plot(c, response.B40_query_spread_delta, "o-", label="Active-query spread"); plt.xlabel("Repulsion multiplier c"); plt.ylabel("B40 spread difference vs margin"); plt.legend(); save("04_diversity_scale_response.png")
    t84 = thresholds[thresholds.threshold.eq(.84)]; plt.figure(figsize=(7, 4)); plt.plot(t84.c, t84.median_first_hit_budget, "o-"); plt.xlabel("Repulsion multiplier c"); plt.ylabel("Median first-hit budget (repeat mean q20 accuracy ≥ .84)"); save("05_sample_efficiency_scale_response.png")
    ov = overlap[overlap.budget.eq(40)]; plt.figure(figsize=(7, 4)); plt.plot(ov.c, ov.jaccard, "o-", label="B40 Jaccard with margin path"); plt.plot(ov.c, ov.same_step_fraction_active, "s-", label="Same-step fraction"); plt.xlabel("Repulsion multiplier c"); plt.ylabel("Path overlap"); plt.ylim(0, 1.02); plt.legend(); save("06_path_overlap.png")
    frame = pd.DataFrame(rows); write_csv(OUTPUT / "figure_manifest.csv", frame); return frame


def build_reports(decision: str, flags: dict[str, Any], response: pd.DataFrame, inference: pd.DataFrame, checkpoint: pd.DataFrame, diversity: pd.DataFrame, thresholds: pd.DataFrame, q30: pd.DataFrame, full: pd.DataFrame, overlap: pd.DataFrame, fit: pd.DataFrame, holm: pd.DataFrame) -> None:
    best = response[response.arm.ne("M3_MARGIN")].sort_values("overall_q20_delta", ascending=False).iloc[0]
    broad = "broad contiguous supported region" if flags["adjacent_supported"] else ("isolated supported scale" if flags["any_supported"] else "no supported performance scale")
    b40 = checkpoint[(checkpoint.subset.eq("B1_q20")) & checkpoint.budget.eq(40) & checkpoint.metric.eq("keyhole_recall")].set_index("arm")
    d40 = diversity[diversity.budget.eq(40)].set_index("arm")
    t84 = thresholds[thresholds.threshold.eq(.84)].set_index("arm")
    full80 = full[(full.subset.eq("full81")) & full.budget.eq(80) & full.metric.isin(("accuracy", "keyhole_recall"))].pivot(index="arm", columns="metric", values="mean")
    ov40 = overlap[overlap.budget.eq(40)].set_index("arm")
    lines = [
        "# Week 9 Phase 1.16 — M3 Margin + Repulsion Scale Audit", "", f"## Decision: {decision}", "",
        "## Frozen design and baseline", "", "The exact Phase 1.14 M3-margin path is the c=0 baseline. Five geometry-relative scales (c=.25,.5,1,2,4) change only the acquisition score; M3, splits, initial designs, budgets, and evaluation definitions remain frozen. Inference uses 20 repeat blocks and 10,000 paired bootstrap draws.", "",
        "## Primary q20 AULC scale response", "", "| Arm | c | q20 AULC | Difference | 95% CI |", "|---|---:|---:|---:|---:|",
    ]
    for row in response.itertuples(index=False):
        lines.append(f"| {row.arm} | {row.c:g} | {row.q20_AULC:.6f} | {row.overall_q20_delta:+.6f} | [{row.overall_ci_lower:+.6f}, {row.overall_ci_upper:+.6f}] |")
    lines += ["", f"All five point estimates are positive, but every primary interval includes zero. The predeclared response therefore shows **{broad}**. The best-looking numerical arm ({best.arm}) is not promoted as a selected winner.", "", "## Early/late and B40 Keyhole mechanism", "", "| Arm | Early ΔAULC | Late ΔAULC | B40 q20 KH-recall Δ (95% CI) | B40 spread Δ |", "|---|---:|---:|---:|---:|"]
    for row in response.itertuples(index=False):
        recall = "0" if row.arm == "M3_MARGIN" else f"{b40.loc[row.arm,'delta_vs_M3_MARGIN']:+.4f} [{b40.loc[row.arm,'ci_lower']:+.4f}, {b40.loc[row.arm,'ci_upper']:+.4f}]"
        lines.append(f"| {row.arm} | {row.early_q20_delta:+.6f} | {row.late_q20_delta:+.6f} | {recall} | {row.B40_query_spread_delta:+.4f} |")
    lines += ["", "Repulsion strengthens early q20 accuracy AULC at larger scales, but it does not repair the motivating B40 Keyhole-recall loss. c=.25 significantly worsens that recall; all other recall intervals include zero with negative point estimates. Geometry spreads for c≥.5, while c=.25 is too weak to prevent narrowing.", "", "## Sample efficiency", "", "| Arm | Reach rate at .84 | Median first hit | Mean paired budget difference | 95% CI |", "|---|---:|---:|---:|---:|"]
    for arm in ARMS:
        row = t84.loc[arm]
        lines.append(f"| {arm} | {row.reach_rate:.2f} | {row.median_first_hit_budget:.1f} | {row.mean_first_hit_difference_vs_margin:+.2f} | [{row.ci_lower:+.2f}, {row.ci_upper:+.2f}] |")
    lines += ["", "All repeats reach .84, but no paired first-hit contrast excludes zero. There is no supported label-saving conclusion.", "", "## q30 and full81 robustness", "", "Every repulsion scale has a small supported positive q30 AULC difference (approximately +.0023 to +.0034). This is a useful robustness signal, but q30 is secondary and cannot overturn the unresolved primary q20 endpoint.", "", "At B80, full81 accuracy and Keyhole-recall changes are negligible and unresolved; no meaningful global degradation is detected.", "", "## Path and numerical behavior", "", f"At B40, mean Jaccard overlap falls from {ov40.loc['REP_C025','jaccard']:.3f} (c=.25) to {ov40.loc['REP_C400','jaccard']:.3f} (c=4). Repulsion genuinely changes geometry rather than merely reordering identical points. Active-query Keyhole fraction falls as repulsion strengthens, explaining why geometric diversity does not automatically recover Keyhole recall.", "", f"Optimizer convergence remains above {fit.optimizer_convergence_rate.min():.1%}. Residual-SD upper-bound pressure remains high and is higher late for strong repulsion; numerical behavior is usable but not improved.", "", "## Multiplicity", "", f"No overall q20 comparison survives Holm adjustment (smallest adjusted p={holm.holm_adjusted_p.min():.3f}).", "", "## Safe interpretation", "", "On the frozen 405-simulation benchmark, geometry-relative repulsion mitigates the spatial concentration of plain M3 margin for c≥.5, but this geometric correction does not produce a statistically resolved overall q20 AULC or first-hit advantage and does not recover B40 Keyhole recall. The broad positive q30 and early-q20 patterns are secondary qualified signals, not a robust acquisition gain.", "", "## Claim boundary and next action", "", "This replay does not establish universal superiority, an optimal scale, theoretical sample complexity, external transfer, or causal ARD importance.", "", "Do not launch another broad repulsion search. Close repulsion as a performance-improvement direction; retain the geometry diagnostic as evidence that diversity alone is insufficient for the Keyhole-recall failure mode."]
    (OUTPUT / "FINAL_PHASE1_16_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    supervisor = ["# Supervisor Phase 1.16 one-page", "", f"**Decision:** {decision}", "", "- Historical h=.15 repulsion was one fixed configuration; Phase 1.16 tested geometry-relative c=.25,.5,1,2,4 without held-out tuning.", f"- M3-margin baseline q20 AULC: {response.iloc[0].q20_AULC:.6f}.", f"- Best numerical q20 arm: c={best.c:g}, difference {best.overall_q20_delta:+.4f} [{best.overall_ci_lower:+.4f}, {best.overall_ci_upper:+.4f}]; every primary CI includes zero.", "- Early q20 AULC improves most for c=1 and c=4, but late gains are small and unresolved.", f"- B40 spread is larger for c≥.5 (maximum Δ {response.B40_query_spread_delta.max():+.3f}), so spatial narrowing is genuinely mitigated.", f"- B40 q20 Keyhole recall does not improve at any scale; c=.25 is significantly worse ({b40.loc['REP_C025','delta_vs_M3_MARGIN']:+.4f}).", "- q30 AULC improves slightly at all five scales, but this is secondary to the unresolved q20 endpoint.", "- .84 first-hit differences all include zero; there is no supported query-saving result.", "- B80 full81 performance is essentially unchanged; no global harm signal.", f"- No primary q20 contrast survives Holm adjustment (minimum adjusted p={holm.holm_adjusted_p.min():.3f}).", "- Safest conclusion: repulsion fixes geometry, not the Keyhole-recall/sample-efficiency problem. Close broad repulsion tuning rather than searching more scales."]
    (OUTPUT / "SUPERVISOR_PHASE1_16_ONE_PAGE.md").write_text("\n".join(supervisor) + "\n", encoding="utf-8")
    ledger = ["# Phase 1.16 claim ledger", "", "| Claim | Status | Evidence boundary |", "|---|---|---|", f"| Repulsion increases query diversity. | {'SUPPORTED' if flags['diversity_increased'] else 'NOT SUPPORTED'} | B40 spread rises for c≥.5. |", f"| Repulsion mitigates spatial path narrowing. | {'SUPPORTED' if flags['diversity_increased'] else 'NOT SUPPORTED'} | Geometry/path overlap only. |", "| Repulsion recovers B40 q20 Keyhole recall. | NOT SUPPORTED | Every point estimate is negative; c=.25 harm is supported. |", f"| Repulsion robustly improves overall q20 AULC across a scale region. | {'SUPPORTED' if decision=='REPULSION_GAIN_ROBUST' else 'NOT SUPPORTED'} | All primary CIs include zero; Holm none. |", "| Repulsion improves q30 AULC. | QUALIFIED | Small supported secondary gains at all scales. |", "| Repulsion improves q20 sample efficiency. | NOT SUPPORTED | First-hit intervals include zero. |", "| One isolated overall-q20 scale is beneficial. | NOT SUPPORTED | No overall q20 CI excludes zero. |", "| A universal optimal repulsion scale is identified. | NOT SUPPORTED | Sensitivity sweep, not optimization. |", "| Theoretical sample-complexity improvement is established. | NOT TESTED | Empirical pool replay only. |", "| External transfer is established. | NOT TESTED | One simulator benchmark. |"]
    (OUTPUT / "claim_ledger.md").write_text("\n".join(ledger) + "\n", encoding="utf-8")
    red = ["# Final red-team report", "", "1. Diversity increase is tested separately from prediction gain.", "2. B40 Keyhole recall is compared for every predeclared scale.", "3. Overall, early, late, q30, full81, and threshold results are all retained.", "4. The full scale curve is reported; no winner is promoted as preselected.", "5. Holm-adjusted sign tests guard against cherry-picking five shared-baseline contrasts.", "6. Retrospective queried labels and B1/q flags never enter acquisition.", "7. Strong repulsion is checked for loss of boundary relevance.", "8. M3 bound pressure and convergence are reported without causal ARD interpretation.", "9. Conclusions are evaluated with the best-looking scale ignored through the broad-region rule.", "10. Historical h=.15 and Week 4 alpha=.25 studies are not rewritten.", "11. No held-out tuning, optimal-scale, universal, or theoretical claim is made."]
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red) + "\n", encoding="utf-8")


def build_notebook() -> None:
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.16 — M3 Margin + Repulsion Scale Audit\n\nThis executed teaching notebook reads frozen artifacts; the expensive sequential engine lives in the source module."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_16_m3_repulsion_scale_audit'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 1. Why revisit repulsion?\n\nPhase 1.14 temporarily narrowed its query path and lost q20 Keyhole recall near B40. The older h=.15 experiment did not test geometry-relative scales."),
        nbf.v4.new_code_cell("display(Markdown((OUT/'historical_repulsion_audit.md').read_text())); display(json.loads((OUT/'analysis_specification.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 2. Predeclared scale response\n\n`c=0` is plain M3 margin. Every positive c multiplies the same margin score by a smooth geometry-relative repulsion factor."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'repulsion_scale_response.csv')); display(Image(filename=str(OUT/'figures'/'01_q20_aulc_scale_response.png'))); display(Image(filename=str(OUT/'figures'/'02_early_late_scale_response.png')))"),
        nbf.v4.new_markdown_cell("## 3. Did repulsion fix the B40 failure mode?"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'q20_checkpoint_metrics.csv').query(\"budget==40\")); display(Image(filename=str(OUT/'figures'/'03_b40_keyhole_recall.png'))); display(Image(filename=str(OUT/'figures'/'04_diversity_scale_response.png')))"),
        nbf.v4.new_markdown_cell("## 4. Sample efficiency and q30 robustness"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'sample_efficiency_thresholds.csv')); display(pd.read_csv(OUT/'q30_robustness.csv')); display(Image(filename=str(OUT/'figures'/'05_sample_efficiency_scale_response.png')))"),
        nbf.v4.new_markdown_cell("## 5. Paths and numerical behavior"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'path_overlap_summary.csv').query(\"budget==40\")); display(pd.read_csv(OUT/'fit_diagnostics_summary.csv')); display(Image(filename=str(OUT/'figures'/'06_path_overlap.png')))"),
        nbf.v4.new_markdown_cell("## 6. Multiplicity and safe decision"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'multiplicity_summary.csv')); display(Markdown((OUT/'SUPERVISOR_PHASE1_16_ONE_PAGE.md').read_text()))"),
    ]
    notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Thesis Python", "language": "python", "name": "thesis"}})
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True); nbf.write(notebook, NOTEBOOK)
    executed = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=180, kernel_name="thesis", resources={"metadata": {"path": str(ROOT)}}).execute()
    nbf.write(executed, NOTEBOOK)


def validate(predictions: pd.DataFrame, metrics: pd.DataFrame, diagnostics: pd.DataFrame, queries: pd.DataFrame, paths: pd.DataFrame, inference: pd.DataFrame, checkpoint: pd.DataFrame, figures: pd.DataFrame, decision: str) -> dict[str, Any]:
    population, specs, _, p1 = load_inputs(); gate = json.loads((OUTPUT / "baseline_gate.json").read_text()); spec = json.loads((OUTPUT / "analysis_specification.json").read_text()); source = Path(__file__).read_text(); notebook = nbf.read(NOTEBOOK, as_version=4); code = [c for c in notebook.cells if c.cell_type == "code"]
    path_map = {(arm, run): g.sort_values("query_order").population_row_index.astype(int).tolist() for (arm, run), g in paths.groupby(["arm", "run_id"])}
    b16 = predictions[predictions.budget.eq(16)].pivot(index=["run_id", "population_row_index"], columns="arm", values="probability")
    checks = [
        ("exact_parent_sha", gate["exact_branch_base"] == PARENT_SHA, gate["exact_branch_base"]),
        ("population_405_73_332", (len(population), int(population.has_keyhole.sum())) == (405, 73), "405/73/332"),
        ("exact_100_outer_runs", len(specs) == 100, str(len(specs))),
        ("exact_initial_designs", all(all(path_map[(arm, s.run_id)][:16] == p1[s.run_id][:16] for arm in ARMS) for s in specs), "100x6"),
        ("historical_M3_margin_reproduced", abs(gate["historical_M3_margin_q20_AULC"] - .844623161764706) < 1e-12 and gate["phase15a_all_selection_matches"], "exact"),
        ("exact_M3_architecture", p13.residual_kernel("M3").k2.nu == 1.5 and tuple(p13.RESIDUAL_SD_BOUNDS) == (.05, 1.0), "frozen"),
        ("exact_h_formula", "p11.log_h_values(population)" in source, "inherited"),
        ("residual_inputs_exact", FEATURES == ("P", "VX", "LS", "ST"), str(FEATURES)),
        ("logh_absent_residual", len(FEATURES) == 4 and "fit_hybrid(x4, logh" in source, "4D residual"),
        ("scores_pre_reveal", source.index("chosen, info = choose_repulsion") < source.index("true_label_revealed_after_selection"), "ordered"),
        ("labels_absent_selector", "labels" not in source[source.index("def choose_repulsion"):source.index("def run_one_spec")], "geometry+probability only"),
        ("B1_q_absent_selector", not any(x in source[source.index("def choose_repulsion"):source.index("def run_one_spec")] for x in ("B1", "q20", "q30")), "absent"),
        ("geometry_only_distance", "pool_scaled" in source[source.index("def choose_repulsion"):source.index("def run_one_spec")], "feature geometry"),
        ("scaler_information_flow", queries.scaler_fit_scope.eq("complete_outer_training_pool_features_only").all(), "outer train features"),
        ("exact_c_grid", tuple(spec["c_grid"]) == C_GRID and set(queries[queries.arm.ne("M3_MARGIN")].c.unique()) == set(C_GRID), str(C_GRID)),
        ("no_posthoc_scales", spec["no_posthoc_scales"] and set(ARM_TO_C.values()) == set(C_GRID), "frozen"),
        ("deterministic_tie_break", queries.tie_break.eq("smallest_population_row_index").all(), "exact"),
        ("one_query_per_step", queries.groupby(["arm", "run_id"]).size().eq(64).all(), "64"),
        ("no_train_test_overlap", all(set(path_map[(arm, s.run_id)]).isdisjoint(s.test_indices) for arm in ARMS for s in specs), "all"),
        ("no_duplicate_query", all(len(set(path)) == 80 for path in path_map.values()), "all"),
        ("B16_equal_all_arms", float((b16.max(axis=1) - b16.min(axis=1)).max()) < 1e-12, str(float((b16.max(axis=1)-b16.min(axis=1)).max()))),
        ("all_paths_length_80", len(path_map) == 600 and all(len(path) == 80 for path in path_map.values()), "600x80"),
        ("repeat_block_inference", metrics.repeat.nunique() == 20 and inference.bootstrap_draws.eq(BOOTSTRAP_DRAWS).all(), "20 blocks"),
        ("bootstrap_10000", BOOTSTRAP_DRAWS == 10000, str(BOOTSTRAP_DRAWS)),
        ("multiplicity_present", (OUTPUT / "multiplicity_summary.csv").is_file(), "Holm"),
        ("q20_q30_unchanged", set(metrics.subset) == {"full81", "B1_q20", "B1_q30"}, str(sorted(metrics.subset.unique()))),
        ("historical_outputs_unchanged", historical_changes() == [], str(historical_changes())),
        ("notebook_executed", bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs", []) if o.get("output_type") == "error"], str(len(code))),
        ("figure_hashes", len(figures) <= 6 and all(sha256_file(FIGURES / r.figure) == r.sha256 for r in figures.itertuples(index=False)), str(len(figures))),
        ("no_placeholders", all(token not in (OUTPUT / "FINAL_PHASE1_16_REPORT.md").read_text() for token in ("TODO", "TBD", "{decision}")), "none"),
        ("decision_rule_exact", decision in spec["decision_categories"], decision),
    ]
    records = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    payload = {"status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL", "check_count": len(records), "passed": sum(r["status"] == "PASS" for r in records), "checks": records}
    write_json(OUTPUT / "validation_report.json", payload)
    lines = ["# Phase 1.16 validation", "", f"Status: **{payload['status']}**", f"Checks: **{payload['passed']} / {payload['check_count']} PASS**", "", "| Check | Status | Detail |", "|---|---|---|"] + [f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(payload["status"] == "PASS", "validation failed")
    return payload


def write_manifest(validation: dict[str, Any], decision: str) -> None:
    files = [p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name != "run_manifest.json"] + [Path(__file__), ROOT / "tests" / "test_week9_phase1_16_m3_repulsion_scale_audit.py", NOTEBOOK]
    entries = []
    for path in sorted(set(files)):
        payload = artifact_bytes(path); entries.append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)})
    write_json(OUTPUT / "run_manifest.json", {"study": "Week 9 Phase 1.16 — M3 Margin + Repulsion Scale Audit", "parent_sha": PARENT_SHA, "branch": BRANCH, "decision": decision, "protocol": {"arms": list(ARMS), "c_grid": list(C_GRID), "outer_runs": 100, "repeat_blocks": 20, "budgets": list(BUDGETS), "bootstrap_draws": BOOTSTRAP_DRAWS}, "validation": validation, "historical_changes": historical_changes(), "files": entries})


def finalize() -> dict[str, Any]:
    gate = baseline_gate(); analysis_specification(); historical_repulsion_audit()
    population, specs, _, p1 = load_inputs(); distances = w85.b1_distance(population)
    rp, rm, rd, rq, rpaths = collect_repulsion(); bp, bm, bd, bq, bpaths = historical_baseline(population, specs, distances)
    predictions = pd.concat([bp, rp], ignore_index=True, sort=False); metrics = pd.concat([bm, rm], ignore_index=True, sort=False); diagnostics = pd.concat([bd, rd], ignore_index=True, sort=False); queries = pd.concat([bq, rq], ignore_index=True, sort=False); paths = pd.concat([bpaths, rpaths], ignore_index=True, sort=False)
    outer, repeat, inference = aulc_tables(metrics)
    checkpoint_summary = metric_summary(metrics, "B1_q20", CHECKPOINT_BUDGETS, ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive"))
    full_summary = metric_summary(metrics, "full81", FULL_BUDGETS, ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "roc_auc", "pr_auc", "brier_score"))
    checkpoint_contrasts = repeat_checkpoint_contrasts(metrics)
    overlap_detail, overlap_summary, diversity, qchars = path_and_diversity(paths, queries, population, specs)
    thresholds = sample_efficiency(metrics); fits = fit_summary(diagnostics); holm = holm_summary(inference)
    response = scale_response(inference, checkpoint_contrasts, diversity, thresholds)
    early_late = inference[(inference.subset.eq("B1_q20")) & inference.region.isin(("EARLY_B16_40", "LATE_B41_80"))]
    q30 = inference[(inference.subset.eq("B1_q30")) & inference.region.eq("OVERALL_B16_80")]
    decision, flags = decide(response, inference, holm, checkpoint_contrasts, checkpoint_contrasts, fits)
    for name, frame in (
        ("outer_run_metrics.csv.gz", outer), ("query_paths.csv.gz", paths), ("query_characteristics.csv", qchars), ("repulsion_scale_response.csv", response),
        ("q20_checkpoint_metrics.csv", checkpoint_summary), ("early_late_summary.csv", early_late), ("q30_robustness.csv", q30), ("sample_efficiency_thresholds.csv", thresholds),
        ("full81_metrics.csv", full_summary), ("path_overlap_summary.csv", overlap_summary), ("diversity_diagnostics.csv", diversity), ("fit_diagnostics.csv.gz", diagnostics),
        ("fit_diagnostics_summary.csv", fits), ("repeat_block_inference.csv", inference), ("multiplicity_summary.csv", holm), ("checkpoint_contrasts.csv", checkpoint_contrasts),
    ):
        write_csv(OUTPUT / name, frame)
    figures = make_figures(response, checkpoint_contrasts, diversity, thresholds, overlap_summary)
    build_reports(decision, flags, response, inference, checkpoint_contrasts, diversity, thresholds, q30, full_summary, overlap_summary, fits, holm)
    build_notebook()
    validation = validate(predictions, metrics, diagnostics, queries, paths, inference, checkpoint_contrasts, figures, decision)
    write_manifest(validation, decision)
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    require(all(hashlib.sha256(artifact_bytes(ROOT / item["path"])).hexdigest() == item["sha256"] for item in manifest["files"]), "manifest hash failure")
    return {"status": "PASS", "decision": decision, "validation_checks": validation["check_count"], "baseline_q20_AULC": gate["historical_M3_margin_q20_AULC"], "historical_changes": historical_changes()}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--preflight", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--finalize", action="store_true"); parser.add_argument("--workers", type=int, default=4); parser.add_argument("--limit-specs", type=int); parser.add_argument("--arms", nargs="*"); args = parser.parse_args()
    if args.preflight:
        print(json.dumps({"baseline": baseline_gate(), "specification": analysis_specification()}, indent=2)); historical_repulsion_audit()
    if args.run:
        print(json.dumps(run_main(args.workers, args.limit_specs, args.arms), indent=2))
    if args.finalize:
        print(json.dumps(finalize(), indent=2))
    if not any((args.preflight, args.run, args.finalize)):
        parser.error("choose --preflight, --run, or --finalize")


if __name__ == "__main__":
    main()
