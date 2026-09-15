from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed, parallel_config
from scipy.stats import spearmanr

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_14_m3_margin_acquisition as p14


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_18b_prospective_global_gpc_sur_benchmark"
CHECKPOINTS = OUTPUT / "checkpoints"
PHASE14 = ROOT / "outputs" / "week9_phase1_14_m3_margin_acquisition"
START_SHA = "1e34b4759037d5f3d107781791524853a406a526"
BRANCH = "codex/week9-phase1-18b-prospective-global-gpc-sur-benchmark"
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
CHECKPOINT_BUDGETS = (16, 24, 32, 40, 60, 80)
ARMS = ("P1_EXACT_FIXED_SUR", "P2_PHYSICS_REFIT_SUR")
CHECKPOINT_SCHEMA_VERSION = 3
BOOTSTRAP_DRAWS = 20_000
NEAR_TIE_RELATIVE_TOLERANCE = 1e-6
SEED_ROOT = "week9_phase1_18b_prospective_global_gpc_sur_benchmark|v1"


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


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
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
    if path.suffix == ".gz":
        raw = frame.to_csv(index=False, lineterminator="\n").encode()
        path.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))
    else:
        frame.to_csv(path, index=False, lineterminator="\n")


def checkpoint_path(arm: str, run_id: str) -> Path:
    return CHECKPOINTS / arm / f"{run_id}.json.gz"


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(json_safe(payload), sort_keys=True) + "\n").encode(), compresslevel=6, mtime=0))


def read_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def load_inputs() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]]]:
    return p14.load_inputs()


def p0_paths() -> dict[str, list[int]]:
    frame = pd.read_csv(PHASE14 / "m3_margin_paths.csv.gz")
    return {run_id: group.sort_values("query_order").population_row_index.astype(int).tolist() for run_id, group in frame.groupby("run_id")}


def historical_changes() -> list[str]:
    protected = [p.as_posix() for p in (ROOT / "outputs").glob("week9_phase1_*") if p.name != OUTPUT.name]
    if not protected:
        return []
    out = subprocess.check_output(["git", "diff", "--name-only", START_SHA, "--", *protected], cwd=ROOT, text=True)
    return [line for line in out.splitlines() if line.strip()]


def preflight() -> dict[str, Any]:
    population, specs, a0 = load_inputs()
    paths = p0_paths()
    p0_outer = pd.read_csv(PHASE14 / "outer_run_metrics.csv.gz")
    q20 = float(p0_outer[(p0_outer.model.eq("P1")) & p0_outer.subset.eq("B1_q20")].accuracy_AULC_16_80.mean())
    common16 = sum(paths[s.run_id][:16] == a0[s.run_id][:16] == w85.initial_design(s, population) for s in specs)
    payload = {
        "status": "PASS",
        "start_sha": START_SHA,
        "population": len(population),
        "keyholes": int(population.has_keyhole.sum()),
        "conduction": int((~population.has_keyhole.astype(bool)).sum()),
        "outer_runs": len(specs),
        "repeat_blocks": len(set(s.repeat for s in specs)),
        "p0_complete_paths": len(paths),
        "p0_paths_length_80": sum(len(v) == 80 for v in paths.values()),
        "initial_design_matches": common16,
        "published_P0_q20_AULC": q20,
        "historical_changes": historical_changes(),
    }
    ok = (len(population), int(population.has_keyhole.sum()), len(specs), len(paths), common16) == (405, 73, 100, 100, 100)
    ok &= abs(q20 - 0.8446231617647059) < 1e-12 and not payload["historical_changes"]
    payload["status"] = "PASS" if ok else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", payload)
    require(ok, f"preflight failed: {payload}")
    write_json(OUTPUT / "analysis_specification.json", {
        "status": "FROZEN_BEFORE_NEW_RESULTS",
        "arms": {"P0": "published Phase 1.14 M3 probability-margin", "P1": "exact enlarged-data Laplace with physics/scaler/kernel fixed", "P2": "physics mean refit per outcome; scaler and current Stage-2 kernel fixed"},
        "uncertainty": "U_n is mean p(1-p) over the complete current unqueried pool R_n; hypothetical U_(n+1) is over R_n minus candidate x",
        "candidate_reference_rule": "literal predeclared formula: common current U_n for every candidate; future uncertainty uses the remaining pool after x is queried",
        "tie_break": "maximum SUR score, then smallest population-row index",
        "near_tie_tolerance": "max(1e-14, 1e-6 * max(max_abs_score, score_range))",
        "failure_fallback": "retry identical fixed-kernel Laplace solve with max_iter_predict=300; never FAST_RANK1",
        "primary_endpoint": "Fold-B1-q20 accuracy normalized trapezoidal AULC B16-B80",
        "primary_family": ["P1-P0", "P2-P0"],
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "regions": {"EARLY": [16, 24], "MID": [25, 40], "LATE": [41, 80], "BROAD_EARLY": [16, 40]},
        "thresholds": [0.80, 0.82, 0.84],
        "catastrophic_fullheldout_guardrail": "at B40 or B80, mean P1-P0 full81 accuracy or Keyhole recall <= -0.05",
        "label_saving_guardrail": "a paired first-hit CI must be entirely below zero and P1 attainment fraction must not be below P0",
        "retrospective_query_diagnostics": "q20-like/q30-like mean global 20th/30th percentile of label-free B1 distance; never used for selection",
        "evaluation_only": ["B1", "q20", "q30", "held-out labels"],
    })
    return payload


@dataclass
class Hypothetical:
    probability: np.ndarray
    seconds: float
    fallback: bool
    posterior_iterations: int
    intercept: float
    slope: float


def hypothetical_update(current: Any, x4: np.ndarray, logh: np.ndarray, labels: np.ndarray,
                        revealed: np.ndarray, candidate: int, outcome: int, arm: str,
                        reference: np.ndarray, run_id: str, budget: int) -> Hypothetical:
    lab = labels.copy()
    lab[candidate] = outcome
    enlarged = np.append(revealed, candidate)
    if arm == "P1_EXACT_FIXED_SUR":
        physics = current.physics
    elif arm == "P2_PHYSICS_REFIT_SUR":
        physics = p11.fit_physics_mean(logh, lab, enlarged, seed_u32("physics_refit", run_id, budget, candidate, outcome))
    else:
        raise ValueError(arm)
    started = time.perf_counter()
    fallback = False
    try:
        gp = p11.FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False, max_iter_predict=100).fit(
            current.x_scaler.transform(x4[enlarged]), lab[enlarged], physics.latent(logh[enlarged]))
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "hypothetical kernel drift")
        require(gp.diagnostics_.posterior_iterations < 100, "Laplace iteration limit")
    except Exception:
        fallback = True
        gp = p11.FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False, max_iter_predict=300).fit(
            current.x_scaler.transform(x4[enlarged]), lab[enlarged], physics.latent(logh[enlarged]))
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "fallback kernel drift")
    probability = gp.predict_proba(current.x_scaler.transform(x4[reference]), physics.latent(logh[reference]))[:, 1]
    return Hypothetical(probability, time.perf_counter() - started, fallback, int(gp.diagnostics_.posterior_iterations),
                        float(physics.model.intercept_[0]), float(physics.model.coef_[0, 0]))


def score_candidates(current: Any, x4: np.ndarray, logh: np.ndarray, labels: np.ndarray,
                     revealed: np.ndarray, candidates: np.ndarray, arm: str, run_id: str, budget: int) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
    comp = p13.components(current, x4[candidates], logh[candidates])
    current_p = np.asarray(comp["probability"], float)
    latent_mean = np.asarray(comp["final_latent"], float)
    latent_var = np.asarray(comp["latent_variance"], float)
    records: list[dict[str, Any]] = []
    failures = fallbacks = 0
    started = time.perf_counter()
    current_intercept = float(current.physics.model.intercept_[0])
    current_slope = float(current.physics.model.coef_[0, 0])
    current_u_global = float(np.mean(current_p * (1.0 - current_p)))
    for j, candidate in enumerate(candidates):
        reference = np.delete(candidates, j)
        outcomes: dict[int, Hypothetical] = {}
        for outcome in (0, 1):
            try:
                outcomes[outcome] = hypothetical_update(current, x4, logh, labels, revealed, int(candidate), outcome, arm, reference, run_id, budget)
                fallbacks += int(outcomes[outcome].fallback)
            except Exception:
                failures += 1
        if len(outcomes) != 2:
            score = np.nan
            u0 = u1 = expected = np.nan
            i0 = i1 = s0 = s1 = np.nan
            it0 = it1 = 0
            seconds = np.nan
        else:
            u0 = float(np.mean(outcomes[0].probability * (1.0 - outcomes[0].probability)))
            u1 = float(np.mean(outcomes[1].probability * (1.0 - outcomes[1].probability)))
            expected = (1.0 - current_p[j]) * u0 + current_p[j] * u1
            score = current_u_global - expected
            i0, i1 = outcomes[0].intercept, outcomes[1].intercept
            s0, s1 = outcomes[0].slope, outcomes[1].slope
            it0, it1 = outcomes[0].posterior_iterations, outcomes[1].posterior_iterations
            seconds = outcomes[0].seconds + outcomes[1].seconds
        records.append({
            "run_id": run_id, "budget": budget, "arm": arm,
            "candidate_population_row_index": int(candidate), "candidate_probability": float(current_p[j]),
            "candidate_latent_mean": float(latent_mean[j]), "candidate_latent_variance": float(latent_var[j]),
            "current_global_uncertainty": current_u_global, "future_uncertainty_y0": u0,
            "future_uncertainty_y1": u1, "expected_future_uncertainty": expected, "sur_score": score,
            "current_physics_intercept": current_intercept, "current_physics_slope": current_slope,
            "physics_intercept_y0": i0, "physics_intercept_y1": i1, "physics_slope_y0": s0, "physics_slope_y1": s1,
            "posterior_iterations_y0": it0, "posterior_iterations_y1": it1, "candidate_scoring_seconds": seconds,
        })
    scores = np.asarray([r["sur_score"] for r in records], float)
    require(np.isfinite(scores).all(), f"nonfinite SUR scores {run_id}/B{budget}/{arm}")
    order = np.lexsort((candidates, -scores))
    chosen = int(candidates[order[0]])
    max_abs = float(np.max(np.abs(scores)))
    score_range = float(np.ptp(scores))
    tolerance = max(1e-14, NEAR_TIE_RELATIVE_TOLERANCE * max(max_abs, score_range))
    sorted_scores = scores[order]
    diagnostic = {
        "run_id": run_id, "budget": budget, "arm": arm, "candidate_count": len(candidates),
        "hypothetical_failures": failures, "fallback_count": fallbacks, "nonfinite_scores": int((~np.isfinite(scores)).sum()),
        "constant_score_event": bool(score_range <= tolerance), "score_min": float(scores.min()), "score_max": float(scores.max()),
        "score_range": score_range, "top1_top2_gap": float(sorted_scores[0] - sorted_scores[1]),
        "near_tie_tolerance": tolerance, "near_tied_fraction": float(np.mean(sorted_scores[0] - scores <= tolerance)),
        "candidate_scoring_seconds": time.perf_counter() - started,
    }
    return chosen, records, diagnostic


def run_one(spec: Any, initial_path: Sequence[int], population: pd.DataFrame, distances: np.ndarray, arm: str) -> dict[str, Any]:
    destination = checkpoint_path(arm, spec.run_id)
    if destination.is_file():
        try:
            payload = read_checkpoint(destination)
            if payload.get("complete") and payload.get("arm") == arm and payload.get("schema_version") == CHECKPOINT_SCHEMA_VERSION:
                return {"run_id": spec.run_id, "arm": arm, "reused": True}
        except (OSError, EOFError, json.JSONDecodeError):
            pass  # interrupted local checkpoint: deterministically recompute it
    x4 = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    train, test = np.asarray(spec.train_indices, int), np.asarray(spec.test_indices, int)
    flags = p17.subset_flags(spec, population, distances)
    queried = list(map(int, initial_path[:16]))
    predictions: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    fits: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    selected_scores: list[dict[str, Any]] = []
    candidate_scores: list[dict[str, Any]] = []
    sur_diagnostics: list[dict[str, Any]] = []
    run_started = time.perf_counter()
    for budget in BUDGETS:
        require(len(queried) == budget and len(set(queried)) == budget, f"prefix error {spec.run_id}/B{budget}")
        revealed = np.asarray(queried, int)
        fit_started = time.perf_counter()
        physics = p11.fit_physics_mean(logh, labels, revealed, p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(x4, logh, labels, revealed, train, physics, "M3", 100.0)
        fit_seconds = time.perf_counter() - fit_started
        test_probability = p13.components(fit, x4[test], logh[test])["probability"]
        for local, pop_index in enumerate(test):
            predictions.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget,
                                "model": arm, "population_row_index": int(pop_index), "truth": int(labels[pop_index]),
                                "probability": float(test_probability[local]), "is_q20": bool(flags["B1_q20"][local]),
                                "is_q30": bool(flags["B1_q30"][local])})
        for subset, flag in (("full81", np.ones(len(test), bool)), ("B1_q20", flags["B1_q20"]), ("B1_q30", flags["B1_q30"])):
            metrics.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget,
                            "model": arm, "subset": subset, **p12.metric_values(labels[test][flag], test_probability[flag])})
        fits.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "arm": arm,
                     "current_fit_seconds": fit_seconds, **p13.fit_diagnostic(fit)})
        if budget < 80:
            candidates = np.setdiff1d(train, revealed)
            chosen, candidate_records, diagnostic = score_candidates(fit, x4, logh, labels, revealed, candidates, arm, spec.run_id, budget)
            candidate_scores.extend(candidate_records)
            selected = next(r for r in candidate_records if r["candidate_population_row_index"] == chosen)
            selected_scores.append(selected)
            sur_diagnostics.append(diagnostic)
            queries.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": arm,
                            "current_budget": budget, "selection_budget": budget + 1, "selected_population_row_index": chosen,
                            "true_label_revealed_after_selection": int(labels[chosen]), "P": float(population.iloc[chosen].P),
                            "VX": float(population.iloc[chosen].VX), "LS": float(population.iloc[chosen].LS), "ST": float(population.iloc[chosen].ST),
                            "log_h": float(logh[chosen]), "B1_distance_posthoc": float(distances[chosen]),
                            "test_rows_available_to_acquisition": False, "unrevealed_labels_available_to_acquisition": False,
                            "B1_q20_q30_available_to_acquisition": False, "tie_break": "smallest_population_row_index"})
            queried.append(chosen)
    require(len(queried) == 80 and len(set(queried)) == 80, f"incomplete trajectory {spec.run_id}/{arm}")
    write_checkpoint(destination, {"complete": True, "schema_version": CHECKPOINT_SCHEMA_VERSION, "arm": arm, "run_id": spec.run_id, "queried_indices": queried,
                                   "predictions": predictions, "metrics": metrics, "fit_diagnostics": fits, "queries": queries,
                                   "selected_sur_scores": selected_scores, "candidate_scores": candidate_scores, "sur_diagnostics": sur_diagnostics,
                                   "run_seconds": time.perf_counter() - run_started})
    return {"run_id": spec.run_id, "arm": arm, "reused": False}


def run_benchmark(workers: int, limit_specs: int | None = None, arms: Sequence[str] = ARMS) -> dict[str, Any]:
    preflight()
    population, specs, a0 = load_inputs()
    distances = w85.b1_distance(population)
    if limit_specs:
        specs = specs[:limit_specs]
    jobs = [(spec, arm) for spec in specs for arm in arms]
    started = time.time()
    with parallel_config(backend="loky", inner_max_num_threads=1):
        results = Parallel(n_jobs=workers, verbose=10)(delayed(run_one)(spec, a0[spec.run_id], population, distances, arm) for spec, arm in jobs)
    payload = {"status": "PASS", "jobs": len(results), "reused": sum(r["reused"] for r in results), "workers": workers,
               "elapsed_seconds": time.time() - started, "complete": limit_specs is None and set(arms) == set(ARMS)}
    write_json(OUTPUT / "execution_report.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit-specs", type=int)
    parser.add_argument("--arms", nargs="*", choices=ARMS, default=list(ARMS))
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.run:
        print(json.dumps(run_benchmark(args.workers, args.limit_specs, args.arms), indent=2))
    if not args.preflight and not args.run:
        parser.error("choose --preflight or --run")


if __name__ == "__main__":
    main()
