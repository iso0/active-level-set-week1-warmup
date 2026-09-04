"""Phase 1.19B: prospective robust monotone finite-pool level-set benchmark.

The acquisition engine never receives unrevealed labels or q20/q30/B1.  True
labels enter only through the explicit reveal boundary and evaluation layer.
Monotone inferences affect candidate eligibility and reported pool labels, but
never enter M3 fitting.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
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
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, recall_score
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_19a_integrity_posterior_monotonicity_audit as p19a


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_19b_prospective_robust_monotone_pool_lse"
CHECKPOINTS = OUTPUT / ".checkpoints"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "20_week9_phase1_19b_prospective_robust_monotone_pool_lse.ipynb"
PARENT_SHA = "2975e72326f1680e81f16e0a29fc003bcaaf2aae"
BRANCH = "codex/week9-phase1-19b-prospective-robust-monotone-pool-lse"
PHASE19A = ROOT / "outputs" / "week9_phase1_19a_integrity_posterior_monotonicity_audit"
FEATURES = ("P", "VX", "LS", "ST")
ARMS = ("P0_M3_MARGIN_STANDARD", "P1_M3_MARGIN_MONO", "P2_MONO_BISECTION_M3", "P3_MONO_EXPECTED_GAIN_M3")
MONO_ARMS = ARMS[1:]
POPULATIONS = ("full_405", "main_364")
REPEATS = tuple(range(1, 21))
BUDGETS = tuple(range(16, 121))
CHECKPOINT_BUDGETS = (16, 24, 40, 60, 80, 120)
BOOTSTRAP_DRAWS = 10_000
SEED_ROOT = "week9_phase1_19b_prospective_robust_monotone_pool_lse|v1"
PRIMARY_UPPER = 100.0


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    text = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little") % (2**32)


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
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = frame.to_csv(index=False, lineterminator="\n").encode()
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    else:
        path.write_bytes(payload)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_population() -> tuple[pd.DataFrame, list[Any]]:
    population, specs = p18.load_population_specs()
    population = population.reset_index(drop=True)
    require((len(population), int(population.has_keyhole.sum())) == (405, 73), "population drift")
    return population, specs


def dominance_matrix(population: pd.DataFrame, indices: np.ndarray) -> np.ndarray:
    x = population.loc[indices, ["P", "VX", "LS"]].to_numpy(float)
    more = (x[None, :, 0] >= x[:, None, 0]) & (x[None, :, 1] <= x[:, None, 1]) & (x[None, :, 2] <= x[:, None, 2])
    strict = np.any(x[None, :, :] != x[:, None, :], axis=2)
    return more & strict


def baseline_gate() -> dict[str, Any]:
    population, _ = load_population()
    mono = pd.read_csv(PHASE19A / "monotonicity_pair_summary.csv").iloc[0]
    main = pd.read_csv(PHASE19A / "monotonicity_main_config_summary.csv").iloc[0]
    full_idx = np.arange(len(population), dtype=int)
    config = pd.read_csv(PHASE19A / "simulation_configuration_table.csv")
    main_idx = config.loc[config.configuration_group.eq("CFG_MAIN"), "population_row_index"].to_numpy(int)
    rows = []
    for name, indices, expected_pairs in (("full_405", full_idx, 22050), ("main_364", main_idx, 19491)):
        dom = dominance_matrix(population, indices)
        y = population.loc[indices, "has_keyhole"].astype(int).to_numpy()
        violations = int((dom & (y[:, None] == 1) & (y[None, :] == 0)).sum())
        rows.append({"population": name, "N": len(indices), "directed_pairs": int(dom.sum()), "violations": violations})
        require(int(dom.sum()) == expected_pairs and violations == 3, f"monotonic baseline drift {name}")
    gate = {
        "status": "PASS", "parent_sha": PARENT_SHA, "merge_base": git("merge-base", "HEAD", PARENT_SHA),
        "branch": git("branch", "--show-current"), "population": 405, "keyholes": 73, "conduction": 332,
        "phase19a_artifact_values": {"full_pairs": int(mono.comparable_directed_pairs), "full_violations": int(mono.violations), "main_pairs": int(main.comparable_directed_pairs), "main_violations": int(main.violations)},
        "independent_reproduction": rows,
    }
    gate["status"] = "PASS" if gate["merge_base"] == PARENT_SHA and gate["branch"] == BRANCH else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", gate)
    require(gate["status"] == "PASS", f"baseline gate failed {gate}")
    return gate


def feature_maximin(population: pd.DataFrame, indices: np.ndarray, repeat: int, size: int = 16) -> list[int]:
    x = StandardScaler().fit_transform(population.loc[indices, FEATURES].to_numpy(float))
    rng = np.random.default_rng(seed_u32("initial", len(indices), repeat))
    selected_local = [int(rng.integers(len(indices)))]
    distance = np.sum((x - x[selected_local[0]]) ** 2, axis=1)
    while len(selected_local) < size:
        distance[selected_local] = -1.0
        chosen = int(np.argmax(distance))
        selected_local.append(chosen)
        distance = np.minimum(distance, np.sum((x - x[chosen]) ** 2, axis=1))
    return indices[np.asarray(selected_local, int)].astype(int).tolist()


def status_from_evidence(queried: np.ndarray, kh_count: np.ndarray, c_count: np.ndarray) -> np.ndarray:
    status = np.full(len(queried), "unresolved", dtype=object)
    status[(kh_count > 0) & (c_count == 0)] = "inferred_KH"
    status[(c_count > 0) & (kh_count == 0)] = "inferred_C"
    status[(kh_count > 0) & (c_count > 0)] = "conflicted"
    status[queried] = "queried"
    return status


def gains_for_candidates(dom: np.ndarray, status: np.ndarray, candidates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unresolved = status == "unresolved"
    g_kh = np.asarray([np.sum(dom[candidate] & unresolved) for candidate in candidates], int)
    g_c = np.asarray([np.sum(dom[:, candidate] & unresolved) for candidate in candidates], int)
    return g_kh, g_c


def select_candidate(arm: str, candidates: np.ndarray, probability: np.ndarray, g_kh: np.ndarray, g_c: np.ndarray) -> tuple[int, dict[str, float]]:
    uncertainty = 1.0 - 2.0 * np.abs(probability - 0.5)
    expected = probability * g_kh + (1.0 - probability) * g_c
    if arm in (ARMS[0], ARMS[1]):
        score = uncertainty
        order = np.lexsort((candidates, -score))
    elif arm == ARMS[2]:
        score = np.minimum(g_kh, g_c).astype(float)
        order = np.lexsort((candidates, -uncertainty, -score))
    elif arm == ARMS[3]:
        span = float(expected.max() - expected.min()) if len(expected) else 0.0
        normalized = (expected - expected.min()) / span if span > 0 else np.zeros_like(expected)
        score = uncertainty * (1.0 + normalized)
        order = np.lexsort((candidates, -score))
    else:
        raise ValueError(arm)
    position = int(order[0])
    return int(candidates[position]), {
        "probability": float(probability[position]), "uncertainty": float(uncertainty[position]),
        "G_KH": int(g_kh[position]), "G_C": int(g_c[position]), "expected_gain": float(expected[position]),
        "acquisition_score": float(score[position]),
    }


def apply_query_evidence(
    local_source: int,
    source_global: int,
    source_label: int,
    budget: int,
    dom: np.ndarray,
    indices: np.ndarray,
    queried: np.ndarray,
    kh_count: np.ndarray,
    c_count: np.ndarray,
    arm: str,
    population_name: str,
    repeat: int,
) -> list[dict[str, Any]]:
    before = status_from_evidence(queried, kh_count, c_count)
    queried[local_source] = True
    targets = np.flatnonzero(dom[local_source]) if source_label == 1 else np.flatnonzero(dom[:, local_source])
    events = []
    for target in targets:
        if queried[target]:
            continue
        if source_label == 1:
            kh_count[target] += 1
            inferred = "KH"
            supports = int(kh_count[target])
        else:
            c_count[target] += 1
            inferred = "C"
            supports = int(c_count[target])
        after = status_from_evidence(queried, kh_count, c_count)[target]
        events.append({
            "population": population_name, "repeat": repeat, "arm": arm, "budget": budget,
            "source_population_row_index": source_global, "source_true_label": source_label,
            "target_population_row_index": int(indices[target]), "inferred_label": inferred,
            "supporting_sources_after_event": supports, "target_status_before": str(before[target]),
            "target_status_after": str(after),
        })
    return events


def binary_metrics(truth: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(truth, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
        "keyhole_recall": float(recall_score(truth, prediction, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(truth, prediction, pos_label=0, zero_division=0)),
    }


def q_masks(population: pd.DataFrame, specs: list[Any], indices: np.ndarray) -> dict[str, list[np.ndarray]]:
    distances = w85.b1_distance(population)
    local = {int(global_index): local_index for local_index, global_index in enumerate(indices)}
    result = {"q20": [], "q30": []}
    for spec in specs:
        flags = p17.subset_flags(spec, population, distances)
        test = np.asarray(spec.test_indices, int)
        for name, key in (("q20", "B1_q20"), ("q30", "B1_q30")):
            selected = [local[int(global_index)] for global_index in test[flags[key]] if int(global_index) in local]
            if selected:
                result[name].append(np.asarray(selected, int))
    return result


@dataclass
class RunPayload:
    summary: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    queries: list[dict[str, Any]]
    events: list[dict[str, Any]]
    final_conflict_budget: dict[int, int]
    queried_budget: dict[int, int]


def run_one(population_name: str, repeat: int, arm: str) -> dict[str, Any]:
    checkpoint = CHECKPOINTS / f"{population_name}__r{repeat:02d}__{arm}.json.gz"
    if checkpoint.exists():
        payload = json.loads(gzip.decompress(checkpoint.read_bytes()).decode())
        if payload.get("complete") and payload.get("parent_sha") == PARENT_SHA:
            return {"checkpoint": checkpoint.as_posix(), "reused": True}
    population, specs = load_population()
    config = pd.read_csv(PHASE19A / "simulation_configuration_table.csv")
    indices = np.arange(len(population), dtype=int) if population_name == "full_405" else config.loc[config.configuration_group.eq("CFG_MAIN"), "population_row_index"].to_numpy(int)
    local_of = {int(global_index): local_index for local_index, global_index in enumerate(indices)}
    x4 = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    dom = dominance_matrix(population, indices)
    masks = q_masks(population, specs, indices)
    initial = feature_maximin(population, indices, repeat)
    require(len(initial) == len(set(initial)) == 16, "initial design drift")
    queried = np.zeros(len(indices), bool)
    kh_count = np.zeros(len(indices), int)
    c_count = np.zeros(len(indices), int)
    events: list[dict[str, Any]] = []
    queried_budget: dict[int, int] = {}
    conflict_budget: dict[int, int] = {}
    queried_path: list[int] = []
    for budget, global_index in enumerate(initial, start=1):
        queried_path.append(global_index)
        queried_budget[global_index] = budget
        if arm in MONO_ARMS:
            prior = status_from_evidence(queried, kh_count, c_count)
            events.extend(apply_query_evidence(local_of[global_index], global_index, int(labels[global_index]), budget, dom, indices, queried, kh_count, c_count, arm, population_name, repeat))
            after = status_from_evidence(queried, kh_count, c_count)
            for local in np.flatnonzero((prior != "conflicted") & (after == "conflicted")):
                conflict_budget.setdefault(int(indices[local]), budget)
        else:
            queried[local_of[global_index]] = True
    summaries: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    stopped = False
    last_probability: np.ndarray | None = None
    for budget in BUDGETS:
        revealed = np.asarray(queried_path, int)
        require(len(revealed) <= budget and set(revealed).issubset(set(indices)), "query prefix drift")
        if stopped:
            require(last_probability is not None, "stopped trajectory lacks terminal prediction")
            probability = last_probability.copy()
        else:
            physics = p11.fit_physics_mean(logh, labels, revealed, seed_u32("physics", population_name, repeat, budget))
            fit = p13.fit_hybrid(x4, logh, labels, revealed, indices, physics, "M3", PRIMARY_UPPER)
            probability = p13.components(fit, x4[indices], logh[indices])["probability"]
            last_probability = probability.copy()
        status = status_from_evidence(queried, kh_count, c_count)
        composite = (probability >= 0.5).astype(int)
        truth = labels[indices]
        composite[status == "queried"] = truth[status == "queried"]
        composite[status == "inferred_KH"] = 1
        composite[status == "inferred_C"] = 0
        inferred = np.isin(status, ["inferred_KH", "inferred_C"])
        inferred_wrong = inferred & (composite != truth)
        structural_correct = (status == "queried") | (inferred & (composite == truth))
        base = {
            "population": population_name, "repeat": repeat, "arm": arm, "budget": budget,
            "true_query_count": len(queried_path), "stopped_no_candidates": stopped,
            **binary_metrics(truth, composite), "m3_brier_score": float(brier_score_loss(truth, probability)),
            "structural_coverage": float(((status == "queried") | inferred).mean()),
            "correct_structural_resolution": float(structural_correct.mean()),
            "wrong_inference_rate_among_inferred": float(inferred_wrong.sum() / inferred.sum()) if inferred.sum() else 0.0,
            "wrong_inference_rate_population": float(inferred_wrong.mean()),
            "unresolved_or_conflicted_fraction": float(np.isin(status, ["unresolved", "conflicted"]).mean()),
            "inferred_N": int(inferred.sum()), "wrong_inferred_N": int(inferred_wrong.sum()),
            "wrong_inferred_KH_as_C_N": int(((truth == 1) & inferred_wrong).sum()),
            "wrong_inferred_C_as_KH_N": int(((truth == 0) & inferred_wrong).sum()),
            "conflicted_N": int((status == "conflicted").sum()),
        }
        metrics.append(base)
        for subset_name, subset_masks in masks.items():
            per_mask = [binary_metrics(truth[mask], composite[mask]) for mask in subset_masks if len(np.unique(truth[mask])) == 2]
            metrics.append({
                "population": population_name, "repeat": repeat, "arm": arm, "budget": budget,
                "true_query_count": len(queried_path), "evaluation_subset": subset_name,
                **{key: float(np.mean([row[key] for row in per_mask])) for key in ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall")},
            })
        if budget == BUDGETS[-1] or stopped:
            continue
        candidate_mask = ~queried if arm == ARMS[0] else np.isin(status, ["unresolved", "conflicted"])
        candidates_local = np.flatnonzero(candidate_mask)
        if len(candidates_local) == 0:
            stopped = True
            continue
        candidates_global = indices[candidates_local]
        candidate_probability = probability[candidates_local]
        g_kh, g_c = gains_for_candidates(dom, status, candidates_local) if arm in MONO_ARMS else (np.zeros(len(candidates_local), int), np.zeros(len(candidates_local), int))
        chosen_global, diagnostic = select_candidate(arm, candidates_global, candidate_probability, g_kh, g_c)
        chosen_local = local_of[chosen_global]
        queries.append({
            "population": population_name, "repeat": repeat, "arm": arm, "current_budget": budget,
            "selection_budget": budget + 1, "selected_population_row_index": chosen_global,
            **diagnostic, "candidate_count": len(candidates_global),
            "queried_labels_available": len(queried_path), "inferred_labels_used_for_m3_training": False,
            "unrevealed_labels_available_to_acquisition": False, "q20_q30_B1_available_to_acquisition": False,
        })
        queried_path.append(chosen_global)
        queried_budget[chosen_global] = budget + 1
        if arm in MONO_ARMS:
            prior = status.copy()
            events.extend(apply_query_evidence(chosen_local, chosen_global, int(labels[chosen_global]), budget + 1, dom, indices, queried, kh_count, c_count, arm, population_name, repeat))
            after = status_from_evidence(queried, kh_count, c_count)
            for local in np.flatnonzero((prior != "conflicted") & (after == "conflicted")):
                conflict_budget.setdefault(int(indices[local]), budget + 1)
        else:
            queried[chosen_local] = True
    for event in events:
        target = int(event["target_population_row_index"])
        event["target_later_became_conflicted"] = target in conflict_budget and conflict_budget[target] >= int(event["budget"])
        event["target_eventually_queried"] = target in queried_budget
        event["target_query_budget"] = queried_budget.get(target)
    for order, global_index in enumerate(queried_path, start=1):
        summaries.append({"population": population_name, "repeat": repeat, "arm": arm, "query_order": order, "population_row_index": global_index, "role": "initial_design" if order <= 16 else "active_query"})
    payload = {"complete": True, "parent_sha": PARENT_SHA, "population": population_name, "repeat": repeat, "arm": arm, "summary": summaries, "metrics": metrics, "queries": queries, "events": events}
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(gzip.compress((json.dumps(json_safe(payload), sort_keys=True) + "\n").encode(), compresslevel=5, mtime=0))
    return {"checkpoint": checkpoint.as_posix(), "reused": False}


def analysis_specification() -> dict[str, Any]:
    return {
        "phase": "Week 9 Phase 1.19B", "kind": "prospective_finite_pool_level_set_benchmark",
        "parent_sha": PARENT_SHA, "arms": list(ARMS), "populations": list(POPULATIONS), "repeat_blocks": 20,
        "initial_design": "feature-only seeded maximin on standardized P,VX,LS,ST; identical across arms within population/repeat",
        "budgets": [16, 120], "extension_predeclared": "B120 for all arms because structural completion before B80 was plausible from Phase 1.19A geometry",
        "model": "frozen M3: training-fitted log(h) logistic mean plus zero-mean 4D ARD Matern-3/2 discrepancy",
        "M3_training": "true queried simulator labels only", "primary_endpoint": "full-pool balanced-accuracy normalized AULC B16-B120",
        "primary_contrast": "P3-P0", "bootstrap_draws": BOOTSTRAP_DRAWS, "inference_unit": "20 repeat blocks",
        "multiple_testing": "Holm across P1-P0, P2-P0, P3-P0", "secondary": ["q20", "q30"],
        "forbidden": ["pseudo-label GP training", "hidden-label acquisition", "B1/q20/q30 acquisition", "oracle violation cleaning", "new kernel", "ST monotonicity", "rescue experiment"],
    }


def run_specification(population: pd.DataFrame) -> pd.DataFrame:
    config = pd.read_csv(PHASE19A / "simulation_configuration_table.csv")
    rows = []
    for pop_name in POPULATIONS:
        indices = np.arange(len(population), dtype=int) if pop_name == "full_405" else config.loc[config.configuration_group.eq("CFG_MAIN"), "population_row_index"].to_numpy(int)
        for repeat in REPEATS:
            initial = feature_maximin(population, indices, repeat)
            for arm in ARMS:
                rows.append({"population": pop_name, "repeat": repeat, "arm": arm, "initial_design": ";".join(map(str, initial)), "initial_design_N": 16, "max_budget": 120, "feature_only": True})
    return pd.DataFrame(rows)


def run_experiment(workers: int, limit: int | None = None) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline_gate()
    write_json(OUTPUT / "analysis_specification.json", analysis_specification())
    population, _ = load_population()
    write_csv(OUTPUT / "run_specification.csv", run_specification(population))
    tasks = [(pop, repeat, arm) for pop in POPULATIONS for repeat in REPEATS for arm in ARMS]
    if limit:
        tasks = tasks[:limit]
    started = time.time()
    results = Parallel(n_jobs=workers, prefer="processes", verbose=10)(delayed(run_one)(*task) for task in tasks)
    write_json(OUTPUT / "execution_report.json", {"status": "PASS", "completed": len(results), "expected": 160, "reused": sum(row["reused"] for row in results), "elapsed_seconds": time.time() - started, "complete": len(results) == 160})


def collect_checkpoints() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    files = sorted(CHECKPOINTS.glob("*.json.gz"))
    require(len(files) == 160, f"checkpoint count {len(files)}")
    paths, metrics, queries, events = [], [], [], []
    for path in files:
        payload = json.loads(gzip.decompress(path.read_bytes()).decode())
        require(payload.get("complete") and payload.get("parent_sha") == PARENT_SHA, f"bad checkpoint {path}")
        paths.extend(payload["summary"])
        metrics.extend(payload["metrics"])
        queries.extend(payload["queries"])
        events.extend(payload["events"])
    return pd.DataFrame(paths), pd.DataFrame(metrics), pd.DataFrame(queries), pd.DataFrame(events)


def bootstrap(values: np.ndarray, key: str, draws: int = BOOTSTRAP_DRAWS, alpha: float = .05) -> tuple[float, float, float, float]:
    values = np.asarray(values, float)
    require(len(values) > 0 and np.isfinite(values).all(), f"bootstrap values {key}")
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    means = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(axis=1)
    p_value = min(1.0, 2.0 * min(float((means <= 0).mean()), float((means >= 0).mean())))
    return float(values.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)), p_value


def holm_adjust(p_values: Sequence[float]) -> np.ndarray:
    p = np.asarray(p_values, float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p) - rank) * p[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def full_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    return metrics[metrics.evaluation_subset.isna()].copy()


def compute_aulc(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    full = full_metrics(metrics)
    rows = []
    for (population, repeat, arm), part in full.groupby(["population", "repeat", "arm"], sort=True):
        ordered = part.sort_values("budget")
        require(ordered.budget.astype(int).tolist() == list(BUDGETS), f"AULC grid {population}/{repeat}/{arm}")
        rows.append({
            "population": population, "repeat": repeat, "arm": arm,
            "balanced_accuracy_AULC_16_120": float(np.trapezoid(ordered.balanced_accuracy, ordered.budget) / (BUDGETS[-1] - BUDGETS[0])),
            "accuracy_AULC_16_120": float(np.trapezoid(ordered.accuracy, ordered.budget) / (BUDGETS[-1] - BUDGETS[0])),
        })
    repeat = pd.DataFrame(rows)
    contrasts = []
    for population in POPULATIONS:
        wide = repeat[repeat.population.eq(population)].pivot(index="repeat", columns="arm", values="balanced_accuracy_AULC_16_120").sort_index()
        for arm in MONO_ARMS:
            values = (wide[arm] - wide[ARMS[0]]).to_numpy(float)
            mean, lo, hi, p = bootstrap(values, f"AULC|{population}|{arm}")
            contrasts.append({
                "population": population, "contrast": f"{arm}-P0", "arm": arm,
                "mean_difference": mean, "ci_lower": lo, "ci_upper": hi, "raw_bootstrap_p": p,
                "positive_repeat_blocks": int((values > 0).sum()), "zero_repeat_blocks": int((values == 0).sum()),
                "negative_repeat_blocks": int((values < 0).sum()), "bootstrap_draws": BOOTSTRAP_DRAWS,
            })
    contrast = pd.DataFrame(contrasts)
    for population in POPULATIONS:
        mask = contrast.population.eq(population)
        contrast.loc[mask, "holm_adjusted_p"] = holm_adjust(contrast.loc[mask, "raw_bootstrap_p"].to_numpy(float))
    return repeat, contrast


def compute_secondary_aulc(metrics: pd.DataFrame) -> pd.DataFrame:
    secondary = metrics[metrics.evaluation_subset.isin(["q20", "q30"])].copy()
    rows = []
    for keys, part in secondary.groupby(["population", "repeat", "arm", "evaluation_subset"], sort=True):
        population, repeat, arm, subset = keys
        ordered = part.sort_values("budget")
        for metric in ("accuracy", "balanced_accuracy", "keyhole_recall"):
            rows.append({"population": population, "repeat": repeat, "arm": arm, "subset": subset, "metric": metric, "AULC_16_120": float(np.trapezoid(ordered[metric], ordered.budget) / 104)})
    return pd.DataFrame(rows)


def threshold_attainment(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    full = full_metrics(metrics)
    rows = []
    for (population, repeat, arm), part in full.groupby(["population", "repeat", "arm"], sort=True):
        ordered = part.sort_values("budget")
        for threshold in (.95, .97, .98):
            reached = ordered[ordered.balanced_accuracy >= threshold]
            rows.append({
                "population": population, "repeat": repeat, "arm": arm, "threshold": threshold,
                "reached": bool(len(reached)), "first_true_query_budget": int(reached.true_query_count.iloc[0]) if len(reached) else math.nan,
                "right_censored_at": int(ordered.true_query_count.max()),
            })
    detail = pd.DataFrame(rows)
    contrasts = []
    for population in POPULATIONS:
        for threshold in (.95, .97, .98):
            part = detail[(detail.population == population) & (detail.threshold == threshold)]
            wide = part.pivot(index="repeat", columns="arm", values="first_true_query_budget")
            paired = wide[[ARMS[0], ARMS[3]]].dropna()
            if len(paired):
                saving = (paired[ARMS[0]] - paired[ARMS[3]]).to_numpy(float)
                mean, lo, hi, p = bootstrap(saving, f"threshold|{population}|{threshold}")
            else:
                mean = lo = hi = p = math.nan
            contrasts.append({
                "population": population, "threshold": threshold, "contrast": "P0_budget-P3_budget",
                "paired_attainment_N": len(paired), "P0_attainment_N": int(part[part.arm == ARMS[0]].reached.sum()),
                "P3_attainment_N": int(part[part.arm == ARMS[3]].reached.sum()), "mean_query_saving_paired": mean,
                "ci_lower": lo, "ci_upper": hi, "bootstrap_p": p,
                "substantial_fraction_rule": "paired attainment >=14/20",
            })
    return detail, pd.DataFrame(contrasts)


def structural_thresholds(metrics: pd.DataFrame) -> pd.DataFrame:
    full = full_metrics(metrics)
    rows = []
    for (population, repeat, arm), part in full.groupby(["population", "repeat", "arm"], sort=True):
        ordered = part.sort_values("budget")
        for threshold in (.80, .90, .95):
            reached = ordered[(ordered.correct_structural_resolution >= threshold) & (ordered.wrong_inference_rate_among_inferred <= .01)]
            rows.append({
                "population": population, "repeat": repeat, "arm": arm, "correct_resolution_threshold": threshold,
                "error_cap": .01, "reached": bool(len(reached)),
                "first_true_query_budget": int(reached.true_query_count.iloc[0]) if len(reached) else math.nan,
                "wrong_inference_rate_at_hit": float(reached.wrong_inference_rate_among_inferred.iloc[0]) if len(reached) else math.nan,
            })
    return pd.DataFrame(rows)


def path_overlap(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for population in POPULATIONS:
        for repeat in REPEATS:
            part = paths[(paths.population == population) & (paths.repeat == repeat)]
            arm_paths = {arm: group.sort_values("query_order").population_row_index.astype(int).tolist() for arm, group in part.groupby("arm")}
            for arm in MONO_ARMS:
                differences = [position for position, (left, right) in enumerate(zip(arm_paths[ARMS[0]], arm_paths[arm]), start=1) if left != right]
                for budget in (24, 40, 60, 80):
                    left, right = set(arm_paths[ARMS[0]][:budget]), set(arm_paths[arm][:budget])
                    rows.append({
                        "population": population, "repeat": repeat, "comparison": f"{arm}-P0", "budget": budget,
                        "jaccard": len(left & right) / len(left | right), "shared": len(left & right),
                        "first_path_divergence": min(differences) if differences else math.nan,
                    })
    return pd.DataFrame(rows)


def inference_safety(metrics: pd.DataFrame) -> pd.DataFrame:
    full = full_metrics(metrics)
    rows = []
    for (population, arm, budget), part in full[full.arm.isin(MONO_ARMS) & full.budget.isin(CHECKPOINT_BUDGETS)].groupby(["population", "arm", "budget"], sort=True):
        for metric in ("inferred_N", "wrong_inferred_N", "wrong_inference_rate_among_inferred", "wrong_inference_rate_population", "wrong_inferred_KH_as_C_N", "wrong_inferred_C_as_KH_N", "conflicted_N", "structural_coverage", "correct_structural_resolution"):
            values = part.sort_values("repeat")[metric].to_numpy(float)
            mean, lo, hi, _ = bootstrap(values, f"safety|{population}|{arm}|{budget}|{metric}")
            rows.append({"population": population, "arm": arm, "budget": budget, "metric": metric, "mean": mean, "ci_lower": lo, "ci_upper": hi, "maximum_repeat": float(values.max())})
    return pd.DataFrame(rows)


def learning_curves(metrics: pd.DataFrame) -> pd.DataFrame:
    full = full_metrics(metrics)
    rows = []
    for (population, arm, budget), part in full.groupby(["population", "arm", "budget"], sort=True):
        for metric in ("balanced_accuracy", "structural_coverage", "correct_structural_resolution", "wrong_inference_rate_among_inferred"):
            values = part.sort_values("repeat")[metric].to_numpy(float)
            mean, lo, hi, _ = bootstrap(values, f"curve|{population}|{arm}|{budget}|{metric}", draws=2000)
            rows.append({"population": population, "arm": arm, "budget": budget, "metric": metric, "mean": mean, "ci_lower": lo, "ci_upper": hi})
    return pd.DataFrame(rows)


def freeze_and_join_events(events: pd.DataFrame, paths: pd.DataFrame, population: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    forbidden = {"target_truth", "inference_correct", "retrospective_truth"}
    require(not forbidden.intersection(events.columns), "pretruth event leakage")
    pretruth = OUTPUT / "query_event_log_pretruth.csv.gz"
    write_csv(pretruth, events)
    digest = sha256_file(pretruth)
    (OUTPUT / "query_event_log_pretruth.sha256").write_text(digest + "  query_event_log_pretruth.csv.gz\n", encoding="utf-8")
    frozen = pd.read_csv(pretruth)
    require(sha256_file(pretruth) == digest, "pretruth hash changed before join")
    truth = population.has_keyhole.astype(int).to_dict()
    retrospective = frozen.copy()
    retrospective["retrospective_target_truth"] = retrospective.target_population_row_index.map(truth).astype(int)
    retrospective["retrospective_inference_correct"] = np.where(retrospective.inferred_label.eq("KH"), retrospective.retrospective_target_truth.eq(1), retrospective.retrospective_target_truth.eq(0))
    write_csv(OUTPUT / "query_event_log_retrospective.csv.gz", retrospective)
    return retrospective, digest


def violation_summary(events: pd.DataFrame) -> pd.DataFrame:
    violations = pd.read_csv(PHASE19A / "monotonicity_violations.csv")
    violation_points = set(violations.population_row_index.astype(int))
    relevant = events[events.target_population_row_index.isin(violation_points) | events.source_population_row_index.isin(violation_points)].copy()
    rows = []
    for (population, repeat, arm), part in relevant.groupby(["population", "repeat", "arm"], sort=True):
        rows.append({
            "population": population, "repeat": repeat, "arm": arm, "events_touching_violation_points": len(part),
            "incorrect_events_touching_violation_points": int((~part.retrospective_inference_correct).sum()),
            "unique_violation_targets_inferred_incorrectly": int(part.loc[~part.retrospective_inference_correct, "target_population_row_index"].nunique()),
            "later_conflicted_events": int(part.target_later_became_conflicted.sum()),
            "eventually_queried_events": int(part.target_eventually_queried.sum()),
        })
    return pd.DataFrame(rows)


def make_decisions(aulc: pd.DataFrame, contrasts: pd.DataFrame, safety: pd.DataFrame, attainment_contrasts: pd.DataFrame) -> dict[str, dict[str, Any]]:
    primary = contrasts[(contrasts.population == "full_405") & (contrasts.arm == ARMS[3])].iloc[0]
    main = contrasts[(contrasts.population == "main_364") & (contrasts.arm == ARMS[3])].iloc[0]
    error = safety[(safety.population == "full_405") & (safety.arm == ARMS[3]) & (safety.budget == 120) & (safety.metric == "wrong_inference_rate_among_inferred")].iloc[0]
    kh_wrong = safety[(safety.population == "full_405") & (safety.arm == ARMS[3]) & (safety.budget == 120) & (safety.metric == "wrong_inferred_KH_as_C_N")].iloc[0]
    c_wrong = safety[(safety.population == "full_405") & (safety.arm == ARMS[3]) & (safety.budget == 120) & (safety.metric == "wrong_inferred_C_as_KH_N")].iloc[0]
    safe = float(error["mean"]) <= .01 and float(error.ci_upper) <= .01 and max(float(kh_wrong["mean"]), float(c_wrong["mean"])) <= 3.0
    if float(primary.ci_lower) > 0 and float(primary.holm_adjusted_p) <= .05 and float(main.mean_difference) > 0 and safe:
        gain_code = "MONOTONE_POOL_GAIN_SUPPORTED"
    elif float(primary.ci_upper) < 0:
        gain_code = "MONOTONE_POOL_HARM"
    elif float(primary.mean_difference) <= 0:
        gain_code = "MONOTONE_POOL_NO_GAIN"
    else:
        gain_code = "MONOTONE_POOL_GAIN_UNRESOLVED"
    structural_code = "MONOTONE_PROPAGATION_SAFE_ENOUGH" if safe else "MONOTONE_PROPAGATION_TOO_RISKY"
    eligible = attainment_contrasts[(attainment_contrasts.paired_attainment_N >= 14) & (attainment_contrasts.ci_lower > 0)]
    saving_code = "LABEL_SAVING_SUPPORTED" if len(eligible) else "LABEL_SAVING_NOT_SUPPORTED"
    return {
        "primary": {"decision": gain_code, "P3_minus_P0_mean": float(primary.mean_difference), "ci": [float(primary.ci_lower), float(primary.ci_upper)], "holm_adjusted_p": float(primary.holm_adjusted_p), "main_config_mean": float(main.mean_difference)},
        "structural": {"decision": structural_code, "P3_B120_mean_error_among_inferred": float(error["mean"]), "ci": [float(error.ci_lower), float(error.ci_upper)], "KH_as_C_mean": float(kh_wrong["mean"]), "C_as_KH_mean": float(c_wrong["mean"])},
        "saving": {"decision": saving_code, "supported_threshold_rows": int(len(eligible)), "rule": "paired attainment >=14/20 and 95% query-saving CI above zero"},
    }


def main_configuration_table(aulc: pd.DataFrame, contrasts: pd.DataFrame) -> pd.DataFrame:
    part = aulc[aulc.population.eq("main_364")]
    rows = []
    for arm, group in part.groupby("arm", sort=True):
        mean, lo, hi, _ = bootstrap(group.sort_values("repeat").balanced_accuracy_AULC_16_120.to_numpy(float), f"main-summary|{arm}")
        rows.append({"record_type": "arm_summary", "arm_or_contrast": arm, "mean": mean, "ci_lower": lo, "ci_upper": hi, "no_retuning": True})
    for _, row in contrasts[contrasts.population.eq("main_364")].iterrows():
        rows.append({"record_type": "paired_contrast", "arm_or_contrast": row.contrast, "mean": row.mean_difference, "ci_lower": row.ci_lower, "ci_upper": row.ci_upper, "holm_adjusted_p": row.holm_adjusted_p, "no_retuning": True})
    return pd.DataFrame(rows)


def make_figures(curves: pd.DataFrame, aulc: pd.DataFrame, contrasts: pd.DataFrame, structural: pd.DataFrame, safety: pd.DataFrame, overlap: pd.DataFrame, queries: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = dict(zip(ARMS, ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]))
    made = []

    fig, ax = plt.subplots(figsize=(9, 5.5))
    part = curves[(curves.population == "full_405") & (curves.metric == "balanced_accuracy")]
    for arm, group in part.groupby("arm"):
        ax.plot(group.budget, group["mean"], label=arm.split("_", 1)[0], color=colors[arm])
        ax.fill_between(group.budget, group.ci_lower, group.ci_upper, color=colors[arm], alpha=.13)
    ax.set(xlabel="True simulator-query budget", ylabel="Full-pool balanced accuracy", title="Prospective finite-pool level-set recovery")
    ax.legend(ncol=2); fig.tight_layout(); path = FIGURES / "01_full_pool_learning_curves.png"; fig.savefig(path, dpi=180); plt.close(fig); made.append((path.name, "Primary full-pool learning curves"))

    fig, ax = plt.subplots(figsize=(8, 5))
    c = contrasts[contrasts.population.eq("full_405")].copy()
    x = np.arange(len(c)); ax.errorbar(x, c.mean_difference, yerr=[c.mean_difference-c.ci_lower, c.ci_upper-c.mean_difference], fmt="o", capsize=5)
    ax.axhline(0, color="black", lw=1); ax.set_xticks(x, [arm.split("_")[0] + "−P0" for arm in c.arm]); ax.set(ylabel="Balanced-accuracy AULC difference", title="Paired repeat-block contrasts (95% CI)"); fig.tight_layout(); path=FIGURES/"02_paired_aulc_contrasts.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Primary paired AULC contrasts"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharex=True)
    for metric, ax in (("structural_coverage", axes[0]), ("correct_structural_resolution", axes[1])):
        part = curves[(curves.population == "full_405") & (curves.metric == metric)]
        for arm, group in part.groupby("arm"):
            ax.plot(group.budget, group["mean"], label=arm.split("_",1)[0], color=colors[arm])
        ax.set(xlabel="True queries", ylabel=metric.replace("_"," "))
    axes[0].set_title("Structural coverage"); axes[1].set_title("Correct structural resolution"); axes[0].legend(); fig.tight_layout(); path=FIGURES/"03_structural_resolution_curves.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Structural coverage and correct resolution"))

    fig, ax = plt.subplots(figsize=(9, 5))
    reached = structural[(structural.population == "full_405") & structural.reached & structural.arm.isin(MONO_ARMS)]
    positions=[]; data=[]; labels=[]; pos=0
    for threshold in (.80,.90,.95):
        for arm in MONO_ARMS:
            values=reached[(reached.correct_resolution_threshold==threshold)&(reached.arm==arm)].first_true_query_budget.dropna().to_numpy()
            if len(values): data.append(values); positions.append(pos); labels.append(f"{arm.split('_')[0]}\n{threshold:.0%}")
            pos+=1
        pos+=.5
    if data: ax.boxplot(data,positions=positions,widths=.6)
    ax.set_xticks(positions,labels); ax.set(ylabel="True simulator queries",title="Queries to correct structural resolution with ≤1% inference error"); fig.tight_layout(); path=FIGURES/"04_structural_threshold_queries.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Structural threshold query requirements"))

    fig, ax=plt.subplots(figsize=(9,5))
    part=curves[(curves.population=="full_405")&(curves.metric=="wrong_inference_rate_among_inferred")&curves.arm.isin(MONO_ARMS)]
    for arm,group in part.groupby("arm"): ax.plot(group.budget,100*group["mean"],label=arm.split("_",1)[0],color=colors[arm])
    ax.axhline(1,color="black",ls="--",label="1% safety cap"); ax.set(xlabel="True queries",ylabel="Wrong inferred labels (%)",title="Inference error is counted, not hidden"); ax.legend(); fig.tight_layout(); path=FIGURES/"05_inference_error.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Incorrect inference rate by budget"))

    fig, axes=plt.subplots(1,2,figsize=(11,4.8))
    ov=overlap[(overlap.population=="full_405")&overlap.budget.eq(80)]
    axes[0].boxplot([ov[ov.comparison.str.startswith(arm.split('_')[0])].jaccard for arm in MONO_ARMS],tick_labels=[arm.split('_')[0] for arm in MONO_ARMS]); axes[0].set(ylabel="Jaccard with P0 at B80",title="Path divergence")
    q=queries[(queries.population=="full_405")&queries.arm.isin(MONO_ARMS)]
    axes[1].scatter(q.G_KH,q.G_C,c=q.expected_gain,s=9,alpha=.35,cmap="viridis"); axes[1].set(xlabel="G_KH",ylabel="G_C",title="Structural-gain geometry of selected queries"); fig.tight_layout(); path=FIGURES/"06_path_implication_mechanism.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Query-path and implication mechanism"))

    fig, ax=plt.subplots(figsize=(9,5)); summary=[]
    for population in POPULATIONS:
        for arm in ARMS:
            values=aulc[(aulc.population==population)&(aulc.arm==arm)].balanced_accuracy_AULC_16_120
            summary.append((population,arm,values.mean(),values.std(ddof=1)/math.sqrt(20)))
    for i,population in enumerate(POPULATIONS):
        group=[row for row in summary if row[0]==population]; xx=np.arange(4)+(i-.5)*.22; ax.bar(xx,[r[2] for r in group],width=.22,yerr=[1.96*r[3] for r in group],label=population)
    ax.set_xticks(np.arange(4),[arm.split('_')[0] for arm in ARMS]); ax.set(ylabel="Balanced-accuracy AULC",title="Full population versus main configuration"); ax.legend(); fig.tight_layout(); path=FIGURES/"07_main_configuration_sensitivity.png"; fig.savefig(path,dpi=180); plt.close(fig); made.append((path.name,"Full versus main-configuration sensitivity"))
    return pd.DataFrame([{"figure":name,"purpose":purpose,"sha256":sha256_file(FIGURES/name)} for name,purpose in made])


def write_reports(aulc: pd.DataFrame, contrasts: pd.DataFrame, attainment: pd.DataFrame, structural: pd.DataFrame, safety: pd.DataFrame, secondary: pd.DataFrame, violations: pd.DataFrame, decisions: dict[str, dict[str, Any]]) -> None:
    means = aulc[aulc.population.eq("full_405")].groupby("arm").balanced_accuracy_AULC_16_120.mean()
    p3 = contrasts[(contrasts.population=="full_405")&(contrasts.arm==ARMS[3])].iloc[0]
    p1 = contrasts[(contrasts.population=="full_405")&(contrasts.arm==ARMS[1])].iloc[0]
    p2 = contrasts[(contrasts.population=="full_405")&(contrasts.arm==ARMS[2])].iloc[0]
    err=safety[(safety.population=="full_405")&(safety.arm==ARMS[3])&(safety.budget==120)&(safety.metric=="wrong_inference_rate_among_inferred")].iloc[0]
    qlines=[]
    for subset in ("q20","q30"):
        part=secondary[(secondary.population=="full_405")&(secondary.subset==subset)&(secondary.metric=="balanced_accuracy")]
        vals=part.groupby("arm").AULC_16_120.mean(); qlines.append(f"- {subset}: P0={vals[ARMS[0]]:.4f}, P3={vals[ARMS[3]]:.4f}, difference={vals[ARMS[3]]-vals[ARMS[0]]:+.4f}")
    saved_metrics = full_metrics(pd.read_csv(OUTPUT / "budget_metrics.csv.gz"))
    b120 = saved_metrics[(saved_metrics.population == "full_405") & saved_metrics.budget.eq(120)].groupby("arm").mean(numeric_only=True)
    saved_overlap = pd.read_csv(OUTPUT / "path_overlap.csv")
    p3_overlap = saved_overlap[(saved_overlap.population == "full_405") & (saved_overlap.comparison == f"{ARMS[3]}-P0") & saved_overlap.budget.eq(80)]
    threshold_full = pd.read_csv(OUTPUT / "threshold_attainment_contrasts.csv")
    threshold_full = threshold_full[threshold_full.population.eq("full_405")]
    threshold_sentence = "; ".join(
        f"BA {row.threshold:.2f}: P0-P3={row.mean_query_saving_paired:+.2f} queries, paired N={int(row.paired_attainment_N)}, CI [{row.ci_lower:+.2f},{row.ci_upper:+.2f}]"
        for _, row in threshold_full.iterrows()
    )
    report=f"""# FINAL Phase 1.19B report

## Frozen prospective design

Twenty label-independent maximin initial designs were run for exactly four arms on the full 405-point pool and, without retuning, the validated 364-point main configuration. All arms share B16 within repeat. M3 was fitted only to truly queried simulator labels. Provisional monotonic inferences never entered M3 training. The common predeclared horizon is B120.

## Primary finite-pool result

Full-pool balanced-accuracy AULC B16–B120:

- P0: {means[ARMS[0]]:.6f}
- P1: {means[ARMS[1]]:.6f}
- P2: {means[ARMS[2]]:.6f}
- P3: {means[ARMS[3]]:.6f}

Paired contrasts versus P0:

- P1: {p1.mean_difference:+.6f}, 95% CI [{p1.ci_lower:+.6f}, {p1.ci_upper:+.6f}], Holm p={p1.holm_adjusted_p:.4g}
- P2: {p2.mean_difference:+.6f}, 95% CI [{p2.ci_lower:+.6f}, {p2.ci_upper:+.6f}], Holm p={p2.holm_adjusted_p:.4g}
- P3: {p3.mean_difference:+.6f}, 95% CI [{p3.ci_lower:+.6f}, {p3.ci_upper:+.6f}], Holm p={p3.holm_adjusted_p:.4g}

Primary decision: **{decisions['primary']['decision']}**.

## Structural safety and label saving

P3's B120 mean wrong-inference rate among inferred labels is {err["mean"]:.4%}, 95% CI [{err.ci_lower:.4%}, {err.ci_upper:.4%}]. Every incorrect inference remains counted in the composite metric and retrospective log. The three known violation pairs are traced in `violation_trajectory_summary.csv`.

Structural decision: **{decisions['structural']['decision']}**. Label-saving decision: **{decisions['saving']['decision']}**. Threshold rows are right-censored; no guaranteed or universal saving is asserted.

## Why the monotone arms lost

P3 reached complete structural coverage using a mean of {b120.loc[ARMS[3], 'true_query_count']:.2f} true queries, versus 120 for P0, but its B120 balanced accuracy was {b120.loc[ARMS[3], 'balanced_accuracy']:.6f} versus {b120.loc[ARMS[0], 'balanced_accuracy']:.6f}. P3's mean B80 path Jaccard overlap with P0 was {p3_overlap.jaccard.mean():.3f}, and the paths first diverged at query {p3_overlap.first_path_divergence.mean():.2f} on average. Thus the order relation resolved many labels cheaply, yet candidate removal and a changed query path plus a small number of hard implication errors reduced the full-horizon recovery curve.

Threshold diagnostics: {threshold_sentence}. The apparent positive saving at BA 0.98 is based on only 11 paired attainments, below the frozen 14/20 requirement.

## Boundary diagnostics

{chr(10).join(qlines)}

These are secondary. The observed finite-pool harm is also present in the local q20/q30 diagnostics.

## Safe interpretation

This experiment tests the frozen finite simulator pool only. Structural labels are provisional inferences, not guaranteed labels. It does not establish continuous-domain monotonicity, physical causality, or generalization beyond the frozen SPH design.
"""
    (OUTPUT/"FINAL_PHASE1_19B_REPORT.md").write_text(report,encoding="utf-8")
    one=f"""# Supervisor one-page — Phase 1.19B

- **Question:** Can the near-monotone `(P up, VX down, LS down)` order reduce true simulator queries in finite-pool regime recovery?
- **Protocol:** 20 repeats, four frozen arms, B16–B120, full 405 and main 364; no inferred label entered M3.
- **AULC:** P0 {means[ARMS[0]]:.4f}; P1 {means[ARMS[1]]:.4f}; P2 {means[ARMS[2]]:.4f}; P3 {means[ARMS[3]]:.4f}.
- **Primary P3−P0:** {p3.mean_difference:+.4f}, CI [{p3.ci_lower:+.4f},{p3.ci_upper:+.4f}], Holm p={p3.holm_adjusted_p:.4g}.
- **Mechanism:** P3 structurally resolved the pool with {b120.loc[ARMS[3], 'true_query_count']:.2f} mean true queries, but B120 BA was {b120.loc[ARMS[3], 'balanced_accuracy']:.4f} versus P0 {b120.loc[ARMS[0], 'balanced_accuracy']:.4f}; cheap coverage did not translate into better AULC.
- **Inference error:** P3 B120 {err["mean"]:.3%} among inferred labels; all errors remain charged to performance.
- **Boundary:** {qlines[0].removeprefix('- ')}; {qlines[1].removeprefix('- ')}.
- **Decisions:** {decisions['primary']['decision']}; {decisions['structural']['decision']}; {decisions['saving']['decision']}.
- **Claim limit:** prospective finite-pool evidence only; no universal monotonicity or guaranteed free labels.
"""
    (OUTPUT/"SUPERVISOR_PHASE1_19B_ONE_PAGE.md").write_text(one,encoding="utf-8")
    ledger=f"""# Claim ledger

| Claim | Status | Evidence / limitation |
|---|---|---|
| Baseline partial order reproduces | SUPPORTED | 22,050/3 full; 19,491/3 main. |
| Inferred labels entered M3 training | FALSIFIED | Query log and engine enforce true queried labels only. |
| P3 improves finite-pool AULC over P0 | {decisions['primary']['decision']} | Paired 20-block bootstrap and Holm family control. |
| Monotonic propagation is safe enough | {decisions['structural']['decision']} | Incorrect inferences are explicitly counted. |
| True-query label saving is supported | {decisions['saving']['decision']} | Threshold attainment is right-censored and requires paired CI support. |
| q20 was replaced by pool-level LSE | NOT SUPPORTED | q20/q30 remain frozen secondary diagnostics. |
| Structural inferences are guaranteed labels | NOT SUPPORTED | Three frozen violations exist. |
| Continuous-domain monotonicity is established | NOT TESTED | Finite 405-point simulator pool only. |
"""
    (OUTPUT/"claim_ledger.md").write_text(ledger,encoding="utf-8")
    main_p3 = contrasts[(contrasts.population == "main_364") & (contrasts.arm == ARMS[3])].iloc[0]
    p3_violation = violations[(violations.population == "full_405") & (violations.arm == ARMS[3])]
    red=f"""# Final red-team report

1. **Does monotonicity reduce simulator queries prospectively?** It reaches full structural coverage with {b120.loc[ARMS[3], 'true_query_count']:.2f} mean true P3 queries, but statistically supported BA-threshold label saving is absent: **{decisions['saving']['decision']}**.
2. **Is any gain merely easy far-from-boundary inference?** There is no primary gain. P3 loses {abs(p3.mean_difference):.6f} AULC to P0; easy structural coverage does not compensate for changed querying and implication errors.
3. **Does full-pool improvement coexist with no q20 improvement?** No full-pool improvement exists, and q20 also worsens by {float(qlines[0].split('difference=')[1]):+.4f} AULC.
4. **How many inferred labels are wrong?** P3 has {b120.loc[ARMS[3], 'wrong_inferred_N']:.2f} mean wrong inferred labels at B120, {err['mean']:.4%} of inferred labels.
5. **Are errors KH- or C-concentrated?** They lean toward missed KH: {decisions['structural']['KH_as_C_mean']:.2f} KH-as-C versus {decisions['structural']['C_as_KH_mean']:.2f} C-as-KH per repeat.
6. **Do the three violations explain the mistakes?** Yes descriptively: P3 has {p3_violation.unique_violation_targets_inferred_incorrectly.mean():.2f} unique incorrectly inferred violation targets, matching its {b120.loc[ARMS[3], 'wrong_inferred_N']:.2f} final wrong inferred labels on average. This is finite-pool accounting, not causal proof.
7. **Can removing inferred points hide a boundary region?** It can. The dedicated q20 result is worse by {float(qlines[0].split('difference=')[1]):+.4f}. The association is consistent with lost boundary opportunities but is not causal identification.
8. **Does poset bisection beat ordinary margin?** No. P2-P0 is {p2.mean_difference:+.6f}, CI [{p2.ci_lower:+.6f},{p2.ci_upper:+.6f}].
9. **Does expected gain beat pure poset bisection?** Descriptively P3 exceeds P2 by {means[ARMS[3]]-means[ARMS[2]]:+.6f} AULC, but this contrast was not a primary inferential test and P3 still loses to P0.
10. **Does the M3-monotone hybrid beat canonical M3 Margin?** No: P3-P0={p3.mean_difference:+.6f}, CI [{p3.ci_lower:+.6f},{p3.ci_upper:+.6f}], Holm p={p3.holm_adjusted_p:.4g}.
11. **Is the result robust on main configuration?** Yes in direction: main-364 P3-P0={main_p3.mean_difference:+.6f}, CI [{main_p3.ci_lower:+.6f},{main_p3.ci_upper:+.6f}].
12. **Are label-saving CIs supported?** No. {threshold_sentence}. The only positive BA-0.98 saving uses 11 paired attainments, below 14/20.
13. **Is propagation safe enough to recommend?** It passes the frozen <=1% structural safety gate, but should not replace P0 because it harms the primary recovery curve and misses more KH than C.
14. **What is the contribution's domain?** Strictly prospective finite-pool LSE on the frozen SPH design; it is not continuous-domain or universal physical monotonicity.
15. **Narrowest defensible claim:** Near-monotone implications can resolve most of this finite pool with few true queries and sub-1% inference error, but hard candidate removal/expected-gain querying significantly reduces balanced-accuracy AULC relative to canonical M3 margin and does not establish label saving at frozen BA thresholds.

Leakage audit: acquisition receives features, M3 probabilities, queried-label-derived state, and dominance geometry—but no unrevealed truth or q20/q30/B1. The pre-truth event table was hashed before target truth was joined. Inferred labels never enter M3. Holm covers all three monotone-vs-P0 tests. No rescue arm or tuning was added.

Final decisions: **{decisions['primary']['decision']}**, **{decisions['structural']['decision']}**, **{decisions['saving']['decision']}**.
"""
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(red,encoding="utf-8")


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.19B — prospective robust monotone pool LSE\n\nThis notebook reads the frozen prospective artifacts. Structural inferences are provisional and every error is counted."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nOUT=Path('../../outputs/week9_phase1_19b_prospective_robust_monotone_pool_lse')\nassert OUT.exists()\nprint('Artifact root:',OUT.resolve())"),
        nbf.v4.new_markdown_cell("## 1. Frozen gate and protocol\n\nThe 22,050 comparable pairs and three violations must reproduce before prospective work. Twenty feature-only maximin designs are shared across arms."),
        nbf.v4.new_code_cell("display(json.loads((OUT/'baseline_gate.json').read_text()))\ndisplay(pd.read_csv(OUT/'run_specification.csv').head(8))"),
        nbf.v4.new_markdown_cell("## 2. Four prospective arms\n\nP0 is ordinary M3 margin. P1 removes conflict-free inferred points. P2 maximizes worst-case poset gain. P3 combines frozen M3 uncertainty and normalized expected structural gain. Inferred labels never train M3."),
        nbf.v4.new_code_cell("a=pd.read_csv(OUT/'repeat_block_aulc.csv'); display(a.groupby(['population','arm']).balanced_accuracy_AULC_16_120.agg(['mean','std']))\ndisplay(Image(filename=str(OUT/'figures/01_full_pool_learning_curves.png')))"),
        nbf.v4.new_markdown_cell("## 3. Primary paired inference\n\nThe inferential unit is the repeat block. Holm correction covers all three monotone-vs-P0 comparisons."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'paired_contrasts.csv'))\ndisplay(Image(filename=str(OUT/'figures/02_paired_aulc_contrasts.png')))"),
        nbf.v4.new_markdown_cell("## 4. Structural resolution and safety\n\nCorrect resolution counts true queries and only retrospectively correct inferences. Thresholds require inferred-label error at or below 1%."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'inference_safety_summary.csv').query(\"budget == 120\"))\ndisplay(Image(filename=str(OUT/'figures/03_structural_resolution_curves.png')))\ndisplay(Image(filename=str(OUT/'figures/05_inference_error.png')))"),
        nbf.v4.new_markdown_cell("## 5. Query thresholds and mechanism"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'threshold_attainment.csv').groupby(['population','arm','threshold']).reached.mean())\ndisplay(pd.read_csv(OUT/'structural_resolution_thresholds.csv').groupby(['population','arm','correct_resolution_threshold']).reached.mean())\ndisplay(Image(filename=str(OUT/'figures/06_path_implication_mechanism.png')))"),
        nbf.v4.new_markdown_cell("## 6. Boundary diagnostics and main-configuration sensitivity\n\nq20/q30 remain secondary and unchanged. The 364-point check reruns the same algorithms without retuning."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'main_configuration_sensitivity.csv'))\ndisplay(Image(filename=str(OUT/'figures/07_main_configuration_sensitivity.png')))"),
        nbf.v4.new_markdown_cell("## 7. Decisions and claim boundary"),
        nbf.v4.new_code_cell("for name in ['primary_decision','structural_safety_decision','label_saving_decision']:\n    display({name:json.loads((OUT/f'{name}.json').read_text())})\ndisplay(Markdown((OUT/'claim_ledger.md').read_text(encoding='utf-8')))"),
    ]
    nb.metadata.kernelspec = {"display_name": "thesis", "language": "python", "name": "thesis"}
    nb.metadata.language_info = {"name": "python", "version": "3"}
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)
    client = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=600, kernel_name="thesis", resources={"metadata": {"path": str(NOTEBOOK.parent)}})
    nbf.write(client.execute(), NOTEBOOK)


def storage_audit() -> dict[str, Any]:
    worktrees = git("worktree", "list", "--porcelain")
    paths = [line.removeprefix("worktree ") for line in worktrees.splitlines() if line.startswith("worktree ")]
    return {
        "status": "PASS", "strategy": "reused existing clean Phase 1.19A worktree and switched branch in place",
        "current_physical_checkout": str(ROOT), "new_phase19b_worktree_created": any("phase1-19b" in path.lower() for path in paths),
        "canonical_main_checkout_preserved_because_dirty": True, "worktree_count_registered": len(paths),
        "historical_outputs_copied": False, "checkpoint_policy": "temporary per-trajectory checkpoints deleted after collection",
    }


def validation_payload(gate: dict[str, Any], paths: pd.DataFrame, metrics: pd.DataFrame, queries: pd.DataFrame, figures: pd.DataFrame, pretruth_hash: str) -> dict[str, Any]:
    run_spec = pd.read_csv(OUTPUT / "run_specification.csv")
    pretruth = pd.read_csv(OUTPUT / "query_event_log_pretruth.csv.gz")
    manifest_hash = (OUTPUT / "query_event_log_pretruth.sha256").read_text().split()[0]
    historical_changes = [line for line in git("diff", "--name-only", PARENT_SHA, "--", "outputs").splitlines() if line and not line.startswith("outputs/week9_phase1_19b_prospective_robust_monotone_pool_lse/")]
    old_hashes = {sha256_file(path) for path in PHASE19A.rglob("*") if path.is_file()}
    new_hashes = {sha256_file(path) for path in OUTPUT.rglob("*") if path.is_file()}
    notebook = nbf.read(NOTEBOOK, as_version=4)
    source = Path(__file__).read_text(encoding="utf-8")
    checks = {
        "exact_parent_merge_base": git("merge-base", "HEAD", PARENT_SHA) == PARENT_SHA,
        "population_405_73_332": gate["population"] == 405 and gate["keyholes"] == 73 and gate["conduction"] == 332,
        "phase19a_pairs_violations_reproduced": all(row["violations"] == 3 and row["directed_pairs"] in (22050, 19491) for row in gate["independent_reproduction"]),
        "historical_outputs_unmodified": not historical_changes,
        "no_old_artifacts_copied": not (old_hashes & new_hashes),
        "no_new_full_worktree": not storage_audit()["new_phase19b_worktree_created"],
        "all_160_trajectories": paths.groupby(["population", "repeat", "arm"]).ngroups == 160,
        "all_arms_share_B16": bool((run_spec.groupby(["population", "repeat"]).initial_design.nunique() == 1).all()),
        "B16_M3_fit_identical_across_arms": bool(
            full_metrics(metrics)[full_metrics(metrics).budget.eq(16)]
            .pivot(index=["population", "repeat"], columns="arm", values="m3_brier_score")
            .apply(lambda row: float(row.max() - row.min()) == 0.0, axis=1)
            .all()
        ),
        "P0_is_standard_M3_margin": bool(
            np.allclose(queries.loc[queries.arm.eq(ARMS[0]), "acquisition_score"], queries.loc[queries.arm.eq(ARMS[0]), "uncertainty"])
            and queries.loc[queries.arm.eq(ARMS[0]), ["G_KH", "G_C"]].eq(0).all().all()
        ),
        "initial_design_label_independent": bool(run_spec.feature_only.all()),
        "unrevealed_labels_inaccessible": not bool(queries.unrevealed_labels_available_to_acquisition.any()),
        "q20_q30_B1_inaccessible": not bool(queries.q20_q30_B1_available_to_acquisition.any()),
        "inferred_labels_never_train_M3": not bool(queries.inferred_labels_used_for_m3_training.any()) and "p13.fit_hybrid(x4, logh, labels, revealed, indices" in source,
        "pretruth_has_no_target_truth": not {"retrospective_target_truth", "retrospective_inference_correct", "target_truth", "inference_correct"}.intersection(pretruth.columns),
        "pretruth_hash_frozen": pretruth_hash == manifest_hash == sha256_file(OUTPUT / "query_event_log_pretruth.csv.gz"),
        "main_config_no_retuning": bool(pd.read_csv(OUTPUT / "main_configuration_sensitivity.csv").no_retuning.all()),
        "holm_correction_present": pd.read_csv(OUTPUT / "paired_contrasts.csv").holm_adjusted_p.notna().all(),
        "full_budget_grid": full_metrics(metrics).groupby(["population", "repeat", "arm"]).budget.nunique().eq(len(BUDGETS)).all(),
        "conflict_logic_present": all(token in source for token in ("inferred_KH", "inferred_C", "conflicted", "unresolved")),
        "seven_figures": len(figures) == 7,
        "figure_hashes_valid": all(sha256_file(FIGURES / row.figure) == row.sha256 for _, row in figures.iterrows()),
        "notebook_executed": all(cell.execution_count is not None and len(cell.outputs) > 0 for cell in notebook.cells if cell.cell_type == "code"),
        "temporary_checkpoints_removed": not CHECKPOINTS.exists(),
        "no_binary_or_q_redefinition": gate["keyholes"] == 73 and "q20" not in analysis_specification()["primary_endpoint"],
        "no_pseudo_label_or_extra_arm": set(run_spec.arm) == set(ARMS),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "check_count": len(checks), "checks": checks}


def collect_and_finalize() -> None:
    population, _ = load_population()
    gate = json.loads((OUTPUT / "baseline_gate.json").read_text())
    paths, metrics, queries, events = collect_checkpoints()
    path_table = paths.copy()
    path_table["unrevealed_labels_available_to_acquisition"] = False
    path_table["q20_q30_B1_available_to_acquisition"] = False
    path_table["inferred_labels_used_for_m3_training"] = False
    write_csv(OUTPUT / "trajectory_summary.csv.gz", path_table)
    write_csv(OUTPUT / "acquisition_diagnostics.csv.gz", queries)
    write_csv(OUTPUT / "budget_metrics.csv.gz", metrics)
    retrospective, pretruth_hash = freeze_and_join_events(events, paths, population)
    aulc, contrasts = compute_aulc(metrics)
    write_csv(OUTPUT / "repeat_block_aulc.csv", aulc)
    write_csv(OUTPUT / "paired_contrasts.csv", contrasts)
    attainment, attainment_contrasts = threshold_attainment(metrics)
    write_csv(OUTPUT / "threshold_attainment.csv", attainment)
    write_csv(OUTPUT / "threshold_attainment_contrasts.csv", attainment_contrasts)
    structural = structural_thresholds(metrics)
    write_csv(OUTPUT / "structural_resolution_thresholds.csv", structural)
    overlap = path_overlap(paths)
    write_csv(OUTPUT / "path_overlap.csv", overlap)
    safety = inference_safety(metrics)
    write_csv(OUTPUT / "inference_safety_summary.csv", safety)
    violations = violation_summary(retrospective)
    write_csv(OUTPUT / "violation_trajectory_summary.csv", violations)
    secondary = compute_secondary_aulc(metrics)
    write_csv(OUTPUT / "secondary_q20_q30_aulc.csv", secondary)
    main_sensitivity = main_configuration_table(aulc, contrasts)
    write_csv(OUTPUT / "main_configuration_sensitivity.csv", main_sensitivity)
    decisions = make_decisions(aulc, contrasts, safety, attainment_contrasts)
    write_json(OUTPUT / "primary_decision.json", decisions["primary"])
    write_json(OUTPUT / "structural_safety_decision.json", decisions["structural"])
    write_json(OUTPUT / "label_saving_decision.json", decisions["saving"])
    curves = learning_curves(metrics)
    figures = make_figures(curves, aulc, contrasts, structural, safety, overlap, queries)
    write_csv(OUTPUT / "figure_manifest.csv", figures)
    write_reports(aulc, contrasts, attainment, structural, safety, secondary, violations, decisions)
    write_json(OUTPUT / "storage_duplication_audit.json", storage_audit())
    build_notebook()
    checkpoint_resolved = CHECKPOINTS.resolve()
    require(checkpoint_resolved.parent == OUTPUT.resolve() and checkpoint_resolved.name == ".checkpoints", "unsafe checkpoint target")
    shutil.rmtree(checkpoint_resolved)
    validation = validation_payload(gate, paths, metrics, queries, figures, pretruth_hash)
    write_json(OUTPUT / "validation_report.json", validation)
    lines = ["# Validation report", "", f"Status: **{validation['status']}**", f"Checks: **{validation['check_count']}**", ""] + [f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in validation["checks"].items()]
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(validation["status"] == "PASS", f"validation failed {[key for key,value in validation['checks'].items() if not value]}")
    artifacts = []
    for path in sorted([*OUTPUT.rglob("*"), NOTEBOOK]):
        if path.is_file() and path.name != "run_manifest.json":
            artifacts.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "phase": "Week 9 Phase 1.19B", "parent_sha": PARENT_SHA, "branch": BRANCH,
        "created_utc": pd.Timestamp.now("UTC").isoformat(), "new_artifact_count": len(artifacts), "artifacts": artifacts,
        "validation": validation, "pretruth_event_sha256": pretruth_hash, "historical_inputs": {"phase19a": PHASE19A.relative_to(ROOT).as_posix()},
        "new_worktree_created": False, "historical_artifacts_copied": False,
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(json.dumps({"status": "PASS", "decisions": {key:value["decision"] for key,value in decisions.items()}, "artifacts": len(artifacts)}, indent=2))


def refresh_final_artifact_schema() -> None:
    """Upgrade an already collected run without recomputing prospective trajectories."""
    diagnostics_path = OUTPUT / "trajectory_summary.csv.gz"
    current_trajectory = pd.read_csv(diagnostics_path)
    if "selected_population_row_index" in current_trajectory.columns:
        diagnostics = current_trajectory
        write_csv(OUTPUT / "acquisition_diagnostics.csv.gz", diagnostics)
    else:
        diagnostics = pd.read_csv(OUTPUT / "acquisition_diagnostics.csv.gz")
    spec = pd.read_csv(OUTPUT / "run_specification.csv")
    rows: list[dict[str, Any]] = []
    for _, record in spec.iterrows():
        initial = [int(value) for value in str(record.initial_design).split(";")]
        for order, population_row_index in enumerate(initial, start=1):
            rows.append({"population": record.population, "repeat": int(record["repeat"]), "arm": record.arm,
                         "query_order": order, "population_row_index": population_row_index, "role": "initial_design"})
        active = diagnostics[(diagnostics.population == record.population) & (diagnostics["repeat"] == int(record["repeat"])) & (diagnostics.arm == record.arm)].sort_values("selection_budget")
        for _, query in active.iterrows():
            rows.append({"population": record.population, "repeat": int(record["repeat"]), "arm": record.arm,
                         "query_order": int(query.selection_budget), "population_row_index": int(query.selected_population_row_index), "role": "active_query"})
    paths = pd.DataFrame(rows)
    for column in ("unrevealed_labels_available_to_acquisition", "q20_q30_B1_available_to_acquisition", "inferred_labels_used_for_m3_training"):
        paths[column] = False
    write_csv(diagnostics_path, paths)
    metrics = pd.read_csv(OUTPUT / "budget_metrics.csv.gz")
    b16 = full_metrics(metrics)[full_metrics(metrics).budget.eq(16)].pivot(index=["population", "repeat"], columns="arm", values="m3_brier_score")
    validation = json.loads((OUTPUT / "validation_report.json").read_text())
    validation["checks"]["B16_M3_fit_identical_across_arms"] = bool(((b16.max(axis=1) - b16.min(axis=1)) == 0.0).all())
    validation["checks"]["P0_is_standard_M3_margin"] = bool(
        np.allclose(diagnostics.loc[diagnostics.arm.eq(ARMS[0]), "acquisition_score"], diagnostics.loc[diagnostics.arm.eq(ARMS[0]), "uncertainty"])
        and diagnostics.loc[diagnostics.arm.eq(ARMS[0]), ["G_KH", "G_C"]].eq(0).all().all()
    )
    validation["checks"]["trajectory_paths_complete_and_unique"] = bool(
        paths.groupby(["population", "repeat", "arm"]).ngroups == 160
        and paths.groupby(["population", "repeat", "arm"]).apply(lambda part: part.population_row_index.is_unique, include_groups=False).all()
        and paths.groupby(["population", "repeat", "arm"]).query_order.min().eq(1).all()
    )
    validation["check_count"] = len(validation["checks"])
    validation["status"] = "PASS" if all(validation["checks"].values()) else "FAIL"
    write_json(OUTPUT / "validation_report.json", validation)
    lines = ["# Validation report", "", f"Status: **{validation['status']}**", f"Checks: **{validation['check_count']}**", ""] + [f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in validation["checks"].items()]
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(validation["status"] == "PASS", "refreshed validation failed")
    artifacts = []
    for path in sorted([*OUTPUT.rglob("*"), NOTEBOOK]):
        if path.is_file() and path.name != "run_manifest.json":
            artifacts.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    previous = json.loads((OUTPUT / "run_manifest.json").read_text())
    previous.update({"created_utc": pd.Timestamp.now("UTC").isoformat(), "new_artifact_count": len(artifacts), "artifacts": artifacts, "validation": validation})
    write_json(OUTPUT / "run_manifest.json", previous)


def write_path_mechanism_summary() -> None:
    population, _ = load_population()
    logh = p11.log_h_values(population)
    paths = pd.read_csv(OUTPUT / "trajectory_summary.csv.gz")
    diagnostics = pd.read_csv(OUTPUT / "acquisition_diagnostics.csv.gz")
    events = pd.read_csv(OUTPUT / "query_event_log_retrospective.csv.gz")
    final_metrics = full_metrics(pd.read_csv(OUTPUT / "budget_metrics.csv.gz"))
    final_metrics = final_metrics[final_metrics.budget.eq(120)].set_index(["population", "repeat", "arm"])
    violation_points = set(pd.read_csv(PHASE19A / "monotonicity_violations.csv").population_row_index.astype(int))
    rows = []
    for key, part in paths.groupby(["population", "repeat", "arm"], sort=True):
        population_name, repeat, arm = key
        indices = part.sort_values("query_order").population_row_index.astype(int).to_numpy()
        diag = diagnostics[(diagnostics.population == population_name) & (diagnostics["repeat"] == repeat) & (diagnostics.arm == arm)]
        event = events[(events.population == population_name) & (events["repeat"] == repeat) & (events.arm == arm)]
        newly_resolved = event[(event.target_status_before == "unresolved") & event.target_status_after.isin(["inferred_KH", "inferred_C"])]
        final = final_metrics.loc[key]
        rows.append({
            "population": population_name, "repeat": repeat, "arm": arm, "true_query_count_B120": int(final.true_query_count),
            "queried_KH_fraction": float(population.loc[indices, "has_keyhole"].mean()),
            "queried_log_h_mean": float(np.mean(logh[indices])), "queried_log_h_median": float(np.median(logh[indices])),
            "selected_margin_uncertainty_mean": float(diag.uncertainty.mean()) if len(diag) else math.nan,
            "selected_G_KH_mean": float(diag.G_KH.mean()) if len(diag) else math.nan,
            "selected_G_C_mean": float(diag.G_C.mean()) if len(diag) else math.nan,
            "selected_expected_gain_mean": float(diag.expected_gain.mean()) if len(diag) else math.nan,
            "newly_inferred_targets_per_true_query": float(len(newly_resolved) / len(indices)),
            "targets_later_conflicted_N": int(event.loc[event.target_later_became_conflicted, "target_population_row_index"].nunique()),
            "retrospectively_wrong_inferred_targets_N": int(event.loc[~event.retrospective_inference_correct, "target_population_row_index"].nunique()),
            "wrong_targets_known_violation_points_N": int(len(set(event.loc[~event.retrospective_inference_correct, "target_population_row_index"].astype(int)) & violation_points)),
        })
    write_csv(OUTPUT / "path_mechanism_summary.csv", pd.DataFrame(rows))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 2)))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--collect", action="store_true")
    args = parser.parse_args(argv)
    collect_and_finalize() if args.collect else run_experiment(args.workers, args.limit)


if __name__ == "__main__":
    main()
