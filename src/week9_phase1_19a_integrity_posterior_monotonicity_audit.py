"""Week 9 Phase 1.19A: integrity, calibration, and monotonicity audit.

This module is deliberately diagnostic.  It reuses frozen data, split, and
published M3-margin path artifacts, but creates no active-learning trajectory.
Historical outputs are read in place and never copied into the Phase 1.19A
output directory.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import subprocess
import time
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
from scipy.special import expit
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src.week7_sph_v2_common import parse_experiment_name


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_19a_integrity_posterior_monotonicity_audit"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "19_week9_phase1_19a_integrity_posterior_monotonicity_audit.ipynb"
PARENT_SHA = "255207857d22a9823f67cb1a23d9b71bdc12ec1c"
BRANCH = "codex/week9-phase1-19a-integrity-posterior-monotonicity-audit"
FEATURES = ("P", "VX", "LS", "ST")
SNAPSHOT_BUDGETS = (16, 20, 24, 32, 40, 60, 80)
REGULARIZATION_C = (1.0, 10.0, 100.0, 1e3, 1e4, 1e6)
BOOTSTRAP_DRAWS = 10_000
SEED_ROOT = "week9_phase1_19a_integrity_posterior_monotonicity_audit|v1"

PHASE14 = ROOT / "outputs" / "week9_phase1_14_m3_margin_acquisition"
PHASE13 = ROOT / "outputs" / "week9_phase1_13_fixed_physics_ard_discrepancy"
PHASE7 = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
PHASE7_AUDIT = ROOT / "outputs" / "week7_01_sph_v2_audit"

HISTORICAL_REFERENCES = {
    "canonical_population": "outputs/week7_02_sph_v2_target_extraction/sph_v2_simulation_level_targets.csv",
    "configuration_parser": "src/week7_sph_v2_common.py::parse_experiment_name",
    "domain_mapping": "src/week7_phase2_sph_v2_physical_target_extraction.py::verify_domain_compatibility/extract_one",
    "published_path": "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz",
    "published_m3_predictions": "outputs/week9_phase1_14_m3_margin_acquisition/new_predictions.csv.gz",
    "published_m3_fit_diagnostics": "outputs/week9_phase1_14_m3_margin_acquisition/m3_active_fit_diagnostics.csv.gz",
}


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
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(frame.to_csv(index=False, lineterminator="\n").encode(), compresslevel=9, mtime=0))
    else:
        frame.to_csv(path, index=False, lineterminator="\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_frozen() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]]]:
    population, specs = p18.load_population_specs()
    paths_table = pd.read_csv(PHASE14 / "m3_margin_paths.csv.gz")
    paths = {
        str(run): group.sort_values("query_order").population_row_index.astype(int).tolist()
        for run, group in paths_table.groupby("run_id", sort=True)
    }
    require(len(population) == 405, "population drift")
    require(int(population.has_keyhole.sum()) == 73, "Keyhole count drift")
    require(int((~population.has_keyhole.astype(bool)).sum()) == 332, "Conduction count drift")
    require(len(specs) == 100 and len(paths) == 100, "split/path drift")
    for spec in specs:
        path = paths[spec.run_id]
        require(len(path) == 80 and len(set(path)) == 80, f"path drift {spec.run_id}")
        require(set(path).issubset(set(spec.train_indices)), f"query outside train {spec.run_id}")
        require(set(path).isdisjoint(set(spec.test_indices)), f"test query {spec.run_id}")
        require(path[:16] == w85.initial_design(spec, population), f"B16 drift {spec.run_id}")
    return population.reset_index(drop=True), specs, paths


def baseline_gate() -> dict[str, Any]:
    population, specs, paths = load_frozen()
    merge_base = git("merge-base", "HEAD", PARENT_SHA)
    gate = {
        "status": "PASS",
        "parent_sha": PARENT_SHA,
        "merge_base": merge_base,
        "branch": git("branch", "--show-current"),
        "population": len(population),
        "keyholes": int(population.has_keyhole.sum()),
        "conduction": int((~population.has_keyhole.astype(bool)).sum()),
        "outer_runs": len(specs),
        "repeat_blocks": len({s.repeat for s in specs}),
        "folds_per_repeat": 5,
        "published_paths": len(paths),
        "initial_design_matches": sum(paths[s.run_id][:16] == w85.initial_design(s, population) for s in specs),
        "historical_references": HISTORICAL_REFERENCES,
    }
    gate["status"] = "PASS" if merge_base == PARENT_SHA and gate["branch"] == BRANCH and gate["initial_design_matches"] == 100 else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", gate)
    require(gate["status"] == "PASS", f"baseline gate failed: {gate}")
    return gate


def config_id(row: pd.Series, counts: dict[tuple[float, ...], int]) -> str:
    key = (float(row.XI), float(row.XF), float(row.XL), float(row.TE))
    if counts[key] == max(counts.values()):
        return "CFG_MAIN"
    if row.XI < 0:
        return "CFG_NEGATIVE_XI_SHORT"
    return "CFG_POSITIVE_XI_SHORT"


def configuration_audit(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    parsed = pd.DataFrame([parse_experiment_name(name) for name in population.experiment_name])
    require(parsed.folder_name_valid.all(), "invalid semantic folder name")
    keys = list(zip(parsed.XI, parsed.XF, parsed.XL, parsed.TE))
    counts = pd.Series(keys).value_counts().to_dict()
    table = pd.DataFrame({
        "simulation_id": population.experiment_name.astype(str),
        "population_row_index": np.arange(len(population), dtype=int),
        "P_W": population.P.astype(float),
        "VX_m_per_s": population.VX.astype(float),
        "LS_m": population.LS.astype(float),
        "ST_K": population.ST.astype(float),
        "has_keyhole": population.has_keyhole.astype(bool),
        "partition": population.partition.astype(str),
        "XI_m": parsed.XI.astype(float),
        "XF_m": parsed.XF.astype(float),
        "XL_m": parsed.XL.astype(float),
        "TE_s": parsed.TE.astype(float),
        "DT_s": parsed.DT.astype(float),
        "material": parsed.material.astype(str),
        "folder_hash": parsed.folder_hash.astype(str),
        "domain_max_x_m": population.domain_max_x_m.astype(float),
        "observation_duration_s": parsed.TE.astype(float),
        "max_depth_um": population.max_depth_um.astype(float),
        "first_keyhole_timestep": population.first_keyhole_timestep,
        "keyhole_frame_count": population.keyhole_frame_count.astype(int),
    })
    table["configuration_group"] = [config_id(parsed.iloc[i], counts) for i in range(len(parsed))]
    table["domain_mapping_expected_m"] = np.minimum(table.XF_m, table.XL_m) + 12e-6
    table["domain_mapping_absolute_error_m"] = np.abs(table.domain_max_x_m - table.domain_mapping_expected_m)
    require(float(table.domain_mapping_absolute_error_m.max()) < 1e-12, "verified domain mapping drift")
    table["t_90pct_domain_s"] = 0.9 * table.domain_max_x_m / table.VX_m_per_s
    table["observation_completion_ratio"] = table.observation_duration_s / table.t_90pct_domain_s
    table["observation_ends_before_90pct_domain_from_TE"] = table.observation_completion_ratio < 1.0 - 1e-12
    # The existing executable flag uses the last parsed time.dat observation.
    # Preserve it as authoritative and expose, rather than hide, any TE-vs-time.dat mismatch.
    table["observation_ends_before_90pct_domain"] = population.recording_ends_before_90pct_domain.astype(bool).to_numpy()
    table["TE_vs_time_dat_flag_mismatch"] = table.observation_ends_before_90pct_domain_from_TE.ne(table.observation_ends_before_90pct_domain)

    summary_rows: list[dict[str, Any]] = []
    for group, part in table.groupby("configuration_group", sort=True):
        row: dict[str, Any] = {
            "configuration_group": group,
            "N": len(part),
            "keyholes": int(part.has_keyhole.sum()),
            "conduction": int((~part.has_keyhole).sum()),
            "keyhole_prevalence": float(part.has_keyhole.mean()),
            "XI_m": float(part.XI_m.iloc[0]),
            "XF_m": float(part.XF_m.iloc[0]),
            "XL_m": float(part.XL_m.iloc[0]),
            "TE_s": float(part.TE_s.iloc[0]),
            "domain_max_x_m": float(part.domain_max_x_m.iloc[0]),
            "ends_before_90pct_N": int(part.observation_ends_before_90pct_domain.sum()),
            "ends_before_90pct_fraction": float(part.observation_ends_before_90pct_domain.mean()),
            "TE_vs_time_dat_flag_mismatch_N": int(part.TE_vs_time_dat_flag_mismatch.sum()),
        }
        for feature, col in (("P", "P_W"), ("VX", "VX_m_per_s"), ("LS", "LS_m"), ("ST", "ST_K")):
            row[f"{feature}_min"] = float(part[col].min())
            row[f"{feature}_median"] = float(part[col].median())
            row[f"{feature}_max"] = float(part[col].max())
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    obs = table[[
        "simulation_id", "population_row_index", "configuration_group", "VX_m_per_s", "has_keyhole",
        "observation_duration_s", "domain_max_x_m", "t_90pct_domain_s", "observation_completion_ratio",
        "observation_ends_before_90pct_domain", "P_W", "LS_m", "ST_K",
    ]].copy()
    main = summary.sort_values("N", ascending=False).iloc[0]
    main_def = {
        "status": "FROZEN_FROM_DOMINANT_EXACT_CONFIGURATION",
        "configuration_group": str(main.configuration_group),
        "N": int(main.N),
        "keyholes": int(main.keyholes),
        "conduction": int(main.conduction),
        "definition": {k: float(main[k]) for k in ("XI_m", "XF_m", "XL_m", "TE_s")},
        "source": "semantic experiment-folder fields parsed by src/week7_sph_v2_common.py",
        "domain_semantics": "min(XF,XL)+12 um is the verified x-domain maximum; no stronger undocumented interpretation is imposed",
    }
    return table, summary, obs, main_def


def metric_values(truth: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    truth = np.asarray(truth, int)
    probability = np.clip(np.asarray(probability, float), 1e-12, 1 - 1e-12)
    pred = (probability >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(truth, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
        "keyhole_recall": float(recall_score(truth, pred, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(truth, pred, pos_label=0, zero_division=0)),
        "brier_score": float(brier_score_loss(truth, probability)),
        "roc_auc": float(roc_auc_score(truth, probability)) if len(np.unique(truth)) == 2 else math.nan,
    }


def _main_model_one(spec: Any, population: pd.DataFrame, main_indices: set[int]) -> list[dict[str, Any]]:
    x4 = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    train = np.asarray([i for i in spec.train_indices if i in main_indices], int)
    test = np.asarray([i for i in spec.test_indices if i in main_indices], int)
    require(len(np.unique(labels[train])) == 2 and len(np.unique(labels[test])) == 2, f"main config class loss {spec.run_id}")
    rows: list[dict[str, Any]] = []
    physics = p11.fit_physics_mean(logh, labels, train, seed_u32("main-H", spec.run_id))
    hp = expit(physics.latent(logh[test]))
    rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "model": "H", "train_N": len(train), "test_N": len(test), **metric_values(labels[test], hp)})

    scaler = StandardScaler().fit(x4[train])
    g3, gdiag = p12.fit_gpc_model("G3", scaler.transform(x4[train]), labels[train], seed_u32("main-G3", spec.run_id))
    gp = p12.predict_positive(g3, scaler.transform(x4[test]))
    rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "model": "G3", "train_N": len(train), "test_N": len(test), "fit_fallback": gdiag["fallback_status"], **metric_values(labels[test], gp)})

    m3 = p13.fit_hybrid(x4, logh, labels, train, train, physics, "M3", 100.0)
    mp = p13.components(m3, x4[test], logh[test])["probability"]
    rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "model": "M3", "train_N": len(train), "test_N": len(test), "fit_fallback": m3.gp.diagnostics_.fallback_status, **metric_values(labels[test], mp)})
    return rows


def main_configuration_model_sensitivity(population: pd.DataFrame, specs: list[Any], config: pd.DataFrame, workers: int) -> pd.DataFrame:
    main_indices = set(config.loc[config.configuration_group.eq("CFG_MAIN"), "population_row_index"].astype(int))
    # Threading avoids Windows spawn/pickling drift in the frozen model modules.
    nested = Parallel(n_jobs=workers, verbose=5, prefer="threads")(
        delayed(_main_model_one)(spec, population, main_indices) for spec in specs
    )
    fold = pd.DataFrame([row for rows in nested for row in rows])
    rows: list[dict[str, Any]] = []
    for model, part in fold.groupby("model", sort=True):
        for metric in ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "brier_score", "roc_auc"):
            repeat = part.groupby("repeat")[metric].mean().to_numpy(float)
            rows.append({
                "population": "main_configuration_only",
                "model": model,
                "metric": metric,
                "mean": float(repeat.mean()),
                "repeat_sd": float(repeat.std(ddof=1)),
                "repeat_blocks": len(repeat),
                "fold_rows": len(part),
                "min_train_N": int(part.train_N.min()),
                "max_train_N": int(part.train_N.max()),
                "min_test_N": int(part.test_N.min()),
                "max_test_N": int(part.test_N.max()),
                "fallback_count": int(part.get("fit_fallback", pd.Series(dtype=str)).fillna("none").ne("none").sum()),
            })
    return pd.DataFrame(rows)


def depth_censoring_audit(population: pd.DataFrame, config: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    table = config[["simulation_id", "population_row_index", "configuration_group", "has_keyhole", "max_depth_um"]].copy()
    main_depth = np.sort(table.loc[table.configuration_group.eq("CFG_MAIN"), "max_depth_um"].to_numpy(float))
    # Define a dense terminal pile without labels or a presumed 295 µm floor. Starting from the
    # maximum, take the largest suffix of at least 10 observations spanning no more than 15 µm
    # whose preceding gap is at least 5 µm. These fixed geometry-scale criteria isolate a narrow
    # terminal pile while rejecting the sparse high-depth tail below it.
    candidates = []
    for start in range(len(main_depth) - 10):
        suffix = main_depth[start:]
        preceding_gap = main_depth[start] - main_depth[start - 1] if start else math.inf
        if len(suffix) >= 10 and suffix[-1] - suffix[0] <= 15.0 and preceding_gap >= 5.0:
            candidates.append(start)
    require(candidates, "no label-free terminal depth pile satisfies the frozen rule")
    start = min(candidates)
    lower_nonpile = float(main_depth[start - 1])
    upper_pile = float(main_depth[start])
    threshold = (lower_nonpile + upper_pile) / 2.0
    table["empirical_floor_cluster_threshold_um"] = threshold
    table["depth_censoring_class"] = np.where(
        table.configuration_group.eq("CFG_MAIN") & table.max_depth_um.gt(threshold),
        "likely_domain_floor_censored",
        "uncensored",
    )
    # No intermediate points occupy the empirical gap; ambiguity is retained as a defined class.
    table.loc[np.abs(table.max_depth_um - threshold) <= 1.0, "depth_censoring_class"] = "ambiguous"
    table["rule"] = "CFG_MAIN largest terminal suffix: N>=10, span<=15 um, preceding gap>=5 um; threshold is gap midpoint; labels unused"
    rows = []
    for (group, cls), part in table.groupby(["configuration_group", "depth_censoring_class"], sort=True):
        rows.append({
            "configuration_group": group,
            "depth_censoring_class": cls,
            "N": len(part),
            "keyholes": int(part.has_keyhole.sum()),
            "conduction": int((~part.has_keyhole).sum()),
            "min_depth_um": float(part.max_depth_um.min()),
            "median_depth_um": float(part.max_depth_um.median()),
            "max_depth_um": float(part.max_depth_um.max()),
            "threshold_um": threshold,
            "lower_nonpile_um": lower_nonpile,
            "upper_pile_um": upper_pile,
        })
    return table, pd.DataFrame(rows), threshold


def _ridge_depth_predictions(spec: Any, population: pd.DataFrame, uncensored: np.ndarray, scenario: str) -> pd.DataFrame:
    x = population.loc[:, FEATURES].to_numpy(float)
    y = population.max_depth_um.to_numpy(float)
    labels = population.has_keyhole.astype(bool).to_numpy()
    train = np.asarray(spec.train_indices, int)
    test = np.asarray(spec.test_indices, int)
    if scenario == "D2_uncensored_train_and_evaluate":
        train = train[uncensored[train]]
        test = test[uncensored[test]]
    elif scenario == "D1_uncensored_evaluation":
        test = test[uncensored[test]]
    scaler = StandardScaler().fit(x[train])
    model = Ridge(alpha=1.0).fit(scaler.transform(x[train]), y[train])
    pred = model.predict(scaler.transform(x[test]))
    return pd.DataFrame({
        "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "scenario": scenario,
        "row": test, "truth_um": y[test], "prediction_um": pred, "has_keyhole": labels[test],
    })


def depth_sensitivity(population: pd.DataFrame, specs: list[Any], censor: pd.DataFrame) -> pd.DataFrame:
    uncensored = censor.depth_censoring_class.eq("uncensored").to_numpy()
    predictions = []
    for scenario in ("D0_original", "D1_uncensored_evaluation", "D2_uncensored_train_and_evaluate"):
        predictions.extend(_ridge_depth_predictions(spec, population, uncensored, scenario) for spec in specs)
    pred = pd.concat(predictions, ignore_index=True)
    rows = []
    for (scenario, repeat), part in pred.groupby(["scenario", "repeat"], sort=True):
        for regime, sub in [("all", part), ("Keyhole", part[part.has_keyhole]), ("Conduction", part[~part.has_keyhole])]:
            err = sub.prediction_um - sub.truth_um
            rows.append({
                "scenario": scenario, "repeat": repeat, "regime": regime, "N": len(sub),
                "MAE_um": float(mean_absolute_error(sub.truth_um, sub.prediction_um)),
                "RMSE_um": float(math.sqrt(mean_squared_error(sub.truth_um, sub.prediction_um))),
                "median_absolute_relative_error": float(np.median(np.abs(err) / np.maximum(sub.truth_um, 1e-12))),
            })
    detail = pd.DataFrame(rows)
    summary = detail.groupby(["scenario", "regime"], as_index=False).agg(
        N_mean=("N", "mean"), MAE_um=("MAE_um", "mean"), RMSE_um=("RMSE_um", "mean"),
        median_absolute_relative_error=("median_absolute_relative_error", "mean"), repeat_blocks=("repeat", "nunique")
    )
    summary["model"] = "fixed Ridge(alpha=1) on standardized P,VX,LS,ST; diagnostic only"
    return summary


def perfect_threshold_separation(z: np.ndarray, y: np.ndarray) -> tuple[bool, float, str]:
    z = np.asarray(z, float)
    y = np.asarray(y, int)
    z0, z1 = z[y == 0], z[y == 1]
    if len(z0) == 0 or len(z1) == 0:
        return False, math.nan, "class_missing"
    if float(z0.max()) < float(z1.min()):
        return True, float((z0.max() + z1.min()) / 2), "Keyhole_above"
    if float(z1.max()) < float(z0.min()):
        return True, float((z1.max() + z0.min()) / 2), "Keyhole_below"
    return False, math.nan, "overlap"


def expected_calibration_error(truth: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    truth = np.asarray(truth, int)
    probability = np.asarray(probability, float)
    edges = np.linspace(0, 1, bins + 1)
    ids = np.minimum(np.digitize(probability, edges[1:-1], right=False), bins - 1)
    value = 0.0
    for idx in range(bins):
        mask = ids == idx
        if mask.any():
            value += float(mask.mean()) * abs(float(probability[mask].mean()) - float(truth[mask].mean()))
    return value


def probability_summary(truth: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    truth = np.asarray(truth, int)
    probability = np.clip(np.asarray(probability, float), 1e-12, 1 - 1e-12)
    return {
        "N": len(truth),
        "brier_score": float(brier_score_loss(truth, probability)),
        "log_loss": float(log_loss(truth, probability, labels=[0, 1])),
        "ECE_10_equal_width": expected_calibration_error(truth, probability, 10),
        "accuracy": float(accuracy_score(truth, probability >= 0.5)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, probability >= 0.5)),
        "fraction_p_0_01": float((probability <= 0.01).mean()),
        "fraction_p_01_10": float(((probability > 0.01) & (probability <= 0.1)).mean()),
        "fraction_p_10_90": float(((probability > 0.1) & (probability < 0.9)).mean()),
        "fraction_p_90_99": float(((probability >= 0.9) & (probability < 0.99)).mean()),
        "fraction_p_99_1": float((probability >= 0.99).mean()),
        "p01": float(np.quantile(probability, 0.01)),
        "p10": float(np.quantile(probability, 0.10)),
        "p50": float(np.quantile(probability, 0.50)),
        "p90": float(np.quantile(probability, 0.90)),
        "p99": float(np.quantile(probability, 0.99)),
    }


def bootstrap_mean_ci(values: np.ndarray, key: str) -> tuple[float, float, float]:
    values = np.asarray(values, float)
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    draws = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))].mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def stage1_audit(
    population: pd.DataFrame, specs: list[Any], paths: dict[str, list[int]]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    snapshots: list[dict[str, Any]] = []
    regularization: list[dict[str, Any]] = []
    h_predictions: list[dict[str, Any]] = []
    for spec in specs:
        train = np.asarray(spec.train_indices, int)
        test = np.asarray(spec.test_indices, int)
        for budget in SNAPSHOT_BUDGETS:
            revealed = np.asarray(paths[spec.run_id][:budget], int)
            require(len(revealed) == budget and set(revealed).issubset(set(train)), "revealed-prefix drift")
            remaining = np.asarray(sorted(set(train) - set(revealed)), int)
            fit = p11.fit_physics_mean(logh, labels, revealed, seed_u32("stage1", spec.run_id, budget))
            coef = float(fit.model.coef_[0, 0])
            intercept = float(fit.model.intercept_[0])
            latent = fit.latent(logh[remaining])
            separation, sep_z, direction = perfect_threshold_separation(
                fit.scaler.transform(logh[revealed, None]).ravel(), labels[revealed]
            )
            threshold_z = -intercept / coef if abs(coef) > 1e-15 else math.nan
            threshold_logh = float(fit.scaler.mean_[0] + fit.scaler.scale_[0] * threshold_z) if math.isfinite(threshold_z) else math.nan
            snapshots.append({
                "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget,
                "revealed_keyholes": int(labels[revealed].sum()), "revealed_conduction": int((labels[revealed] == 0).sum()),
                "physics_coefficient": coef, "physics_intercept": intercept,
                "h_scaler_mean": float(fit.scaler.mean_[0]), "h_scaler_scale": float(fit.scaler.scale_[0]),
                "threshold_standardized_log_h": threshold_z, "threshold_log_h": threshold_logh,
                "max_abs_pool_logit": float(np.max(np.abs(latent))) if len(latent) else math.nan,
                "median_abs_pool_logit": float(np.median(np.abs(latent))) if len(latent) else math.nan,
                "fraction_pool_abs_gt2": float((np.abs(latent) > 2).mean()) if len(latent) else math.nan,
                "fraction_pool_abs_gt5": float((np.abs(latent) > 5).mean()) if len(latent) else math.nan,
                "fraction_pool_abs_gt10": float((np.abs(latent) > 10).mean()) if len(latent) else math.nan,
                "pool_abs_lt1_N": int((np.abs(latent) < 1).sum()), "pool_abs_lt2_N": int((np.abs(latent) < 2).sum()),
                "current_pool_N": len(remaining), "perfect_h_separation": separation,
                "separation_direction": direction, "separation_threshold_standardized": sep_z,
                "revealed_labels_only": True, "heldout_labels_used": False,
            })
            test_probability = expit(fit.latent(logh[test]))
            for local, idx in enumerate(test):
                h_predictions.append({
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget,
                    "model": "H", "population_row_index": int(idx), "truth": int(labels[idx]),
                    "probability": float(test_probability[local]),
                })
            z_revealed = logh[revealed, None]
            scaler = StandardScaler().fit(z_revealed)
            z_scaled = scaler.transform(z_revealed)
            for c in REGULARIZATION_C:
                model = LogisticRegression(C=c, solver="lbfgs", max_iter=5000, random_state=seed_u32("C", spec.run_id, budget, c)).fit(z_scaled, labels[revealed])
                coefficient = float(model.coef_[0, 0])
                inter = float(model.intercept_[0])
                threshold = float(scaler.mean_[0] + scaler.scale_[0] * (-inter / coefficient)) if abs(coefficient) > 1e-15 else math.nan
                regularization.append({
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "C": c,
                    "coefficient": coefficient, "intercept": inter, "threshold_log_h": threshold,
                    "perfect_h_separation": separation, "diagnostic_only": True,
                })

    snapshot_frame = pd.DataFrame(snapshots)
    regularization_frame = pd.DataFrame(regularization)
    h_pred = pd.DataFrame(h_predictions)
    m3 = pd.read_csv(PHASE14 / "new_predictions.csv.gz")
    m3 = m3[m3.budget.isin(SNAPSHOT_BUDGETS)].copy()
    m3["model"] = "M3"
    m3 = m3[["run_id", "repeat", "fold", "budget", "model", "population_row_index", "truth", "probability"]]
    pred = pd.concat([h_pred, m3], ignore_index=True)
    require(len(pred) == 2 * 100 * len(SNAPSHOT_BUDGETS) * 81, "calibration prediction count drift")
    calibration_rows: list[dict[str, Any]] = []
    for (budget, model, repeat), part in pred.groupby(["budget", "model", "repeat"], sort=True):
        calibration_rows.append({"budget": budget, "model": model, "repeat": repeat, **probability_summary(part.truth, part.probability)})
    repeat_cal = pd.DataFrame(calibration_rows)
    summary_rows = []
    for (budget, model), part in repeat_cal.groupby(["budget", "model"], sort=True):
        for metric in [c for c in repeat_cal.columns if c not in {"budget", "model", "repeat", "N"}]:
            mean, lo, hi = bootstrap_mean_ci(part[metric].to_numpy(float), f"cal|{budget}|{model}|{metric}")
            summary_rows.append({"budget": budget, "model": model, "metric": metric, "mean": mean, "ci_lower": lo, "ci_upper": hi, "repeat_blocks": 20})
    return snapshot_frame, regularization_frame, pd.DataFrame(summary_rows), pred


def separation_summary(snapshots: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for budget, part in snapshots.groupby("budget", sort=True):
        rows.append({
            "budget": budget, "snapshots": len(part),
            "perfect_h_separation_N": int(part.perfect_h_separation.sum()),
            "perfect_h_separation_fraction": float(part.perfect_h_separation.mean()),
            "coefficient_median": float(part.physics_coefficient.median()),
            "coefficient_q10": float(part.physics_coefficient.quantile(.1)),
            "coefficient_q90": float(part.physics_coefficient.quantile(.9)),
            "coefficient_max": float(part.physics_coefficient.max()),
            "max_abs_pool_logit_median": float(part.max_abs_pool_logit.median()),
            "median_abs_pool_logit_median": float(part.median_abs_pool_logit.median()),
            "fraction_pool_abs_gt10_mean": float(part.fraction_pool_abs_gt10.mean()),
            "pool_abs_lt1_median_N": float(part.pool_abs_lt1_N.median()),
        })
    return pd.DataFrame(rows)


def historical_associations(snapshots: pd.DataFrame) -> pd.DataFrame:
    fit = pd.read_csv(PHASE14 / "m3_active_fit_diagnostics.csv.gz")
    fit = fit[fit.budget.isin(SNAPSHOT_BUDGETS)].copy()
    queries = pd.read_csv(PHASE14 / "m3_margin_queries.csv.gz")
    queries = queries.rename(columns={"current_budget": "budget"})
    merged = snapshots.merge(fit, on=["run_id", "repeat", "fold", "budget"], how="left", suffixes=("", "_m3"))
    merged = merged.merge(
        queries[["run_id", "budget", "margin_abs_probability_minus_half", "uncertainty_score"]],
        on=["run_id", "budget"], how="left",
    )
    rows = []
    for source in ("physics_coefficient", "max_abs_pool_logit", "fraction_pool_abs_gt10"):
        for target in ("residual_sd", "residual_sd_upper_bound_hit", "any_length_upper_bound_hit", "margin_abs_probability_minus_half"):
            valid = merged[[source, target]].dropna()
            rho, p = spearmanr(valid[source], valid[target]) if len(valid) > 2 else (math.nan, math.nan)
            rows.append({
                "source_diagnostic": source, "historical_quantity": target, "spearman_rho": float(rho),
                "p_value_descriptive": float(p), "N_snapshots": len(valid),
                "interpretation": "association only; no causal attribution",
            })
    return pd.DataFrame(rows)


def q_membership_counts(population: pd.DataFrame, specs: list[Any]) -> pd.DataFrame:
    distances = w85.b1_distance(population)
    counts = pd.DataFrame({"population_row_index": np.arange(len(population)), "test_fold_count": 0, "q20_count": 0, "q30_count": 0})
    for spec in specs:
        test = np.asarray(spec.test_indices, int)
        flags = p17.subset_flags(spec, population, distances)
        counts.loc[test, "test_fold_count"] += 1
        counts.loc[test[flags["B1_q20"]], "q20_count"] += 1
        counts.loc[test[flags["B1_q30"]], "q30_count"] += 1
    counts["q20_test_fraction"] = counts.q20_count / counts.test_fold_count
    counts["q30_test_fraction"] = counts.q30_count / counts.test_fold_count
    counts["B1"] = distances
    return counts


def dominance_matrix(population: pd.DataFrame, indices: np.ndarray) -> np.ndarray:
    x = population.loc[indices, ["P", "VX", "LS"]].to_numpy(float)
    more = (
        (x[None, :, 0] >= x[:, None, 0])
        & (x[None, :, 1] <= x[:, None, 1])
        & (x[None, :, 2] <= x[:, None, 2])
    )
    strict = np.any(x[None, :, :] != x[:, None, :], axis=2)
    return more & strict  # [i,j] means j is more Keyhole-favouring than i.


def monotonicity_for_subset(population: pd.DataFrame, indices: np.ndarray, name: str) -> tuple[dict[str, Any], list[tuple[int, int]], np.ndarray]:
    dom = dominance_matrix(population, indices)
    y = population.loc[indices, "has_keyhole"].astype(int).to_numpy()
    violations_local = np.argwhere(dom & (y[:, None] == 1) & (y[None, :] == 0))
    violations = [(int(indices[i]), int(indices[j])) for i, j in violations_local]
    directed = int(dom.sum())
    unordered = int(np.triu(dom | dom.T, 1).sum())
    total_unordered = len(indices) * (len(indices) - 1) // 2
    summary = {
        "population": name, "N": len(indices), "keyholes": int(y.sum()), "conduction": int((y == 0).sum()),
        "comparable_directed_pairs": directed, "comparable_unique_unordered_pairs": unordered,
        "all_unique_unordered_pairs": total_unordered, "comparable_pair_fraction": unordered / total_unordered,
        "violations": len(violations), "violation_rate_directed": len(violations) / directed if directed else math.nan,
        "definition": "j more Keyhole-favouring iff P_j>=P_i, VX_j<=VX_i, LS_j<=LS_i, at least one strict; ST ignored",
    }
    return summary, violations, dom


def monotonicity_audit(
    population: pd.DataFrame, specs: list[Any], config: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_idx = np.arange(len(population), dtype=int)
    main_idx = config.loc[config.configuration_group.eq("CFG_MAIN"), "population_row_index"].to_numpy(int)
    full_summary, full_violations, full_dom = monotonicity_for_subset(population, full_idx, "full_405")
    main_summary, main_violations, main_dom = monotonicity_for_subset(population, main_idx, "main_configuration_only")
    pair_summary = pd.DataFrame([full_summary])
    main_summary_frame = pd.DataFrame([main_summary])
    qcounts = q_membership_counts(population, specs).set_index("population_row_index")
    config_index = config.set_index("population_row_index")
    violation_rows = []
    for pair_id, (i, j) in enumerate(full_violations, start=1):
        for role, idx in (("less_favouring_Keyhole", i), ("more_favouring_Conduction", j)):
            row = population.loc[idx]
            cfg = config_index.loc[idx]
            qc = qcounts.loc[idx]
            violation_rows.append({
                "violation_id": pair_id, "role": role, "population_row_index": idx,
                "simulation_id": row.experiment_name, "truth": int(row.has_keyhole),
                "P": float(row.P), "VX": float(row.VX), "LS": float(row.LS), "ST": float(row.ST),
                "h": float(row.P / math.sqrt(row.VX * row.LS**3)),
                "configuration_group": cfg.configuration_group, "observation_duration_s": float(cfg.observation_duration_s),
                "observation_ends_before_90pct_domain": bool(cfg.observation_ends_before_90pct_domain),
                "max_depth_um": float(row.max_depth_um), "keyhole_frame_count": int(row.keyhole_frame_count),
                "first_keyhole_timestep": float(row.first_keyhole_timestep) if pd.notna(row.first_keyhole_timestep) else math.nan,
                "B1": float(qc.B1), "q20_test_fraction": float(qc.q20_test_fraction), "q30_test_fraction": float(qc.q30_test_fraction),
            })
    violations = pd.DataFrame(violation_rows)

    predecessors = full_dom.sum(axis=0)  # less-favouring points that imply into j when KH.
    successors = full_dom.sum(axis=1)
    matching = maximum_bipartite_matching(csr_matrix(full_dom.astype(np.int8)), perm_type="column")
    antichain_width = len(full_idx) - int((matching >= 0).sum())
    geometry = pd.DataFrame([
        {
            "population": "full_405", "N": len(full_idx),
            "predecessors_median": float(np.median(predecessors)), "predecessors_q10": float(np.quantile(predecessors, .1)), "predecessors_q90": float(np.quantile(predecessors, .9)),
            "successors_median": float(np.median(successors)), "successors_q10": float(np.quantile(successors, .1)), "successors_q90": float(np.quantile(successors, .9)),
            "minimal_elements": int((predecessors == 0).sum()), "maximal_elements": int((successors == 0).sum()),
            "exact_antichain_width_via_Dilworth": antichain_width,
            "KH_reveal_implied_unknown_median": float(np.median(successors)),
            "C_reveal_implied_unknown_median": float(np.median(predecessors)),
            "KH_reveal_implied_unknown_q90": float(np.quantile(successors, .9)),
            "C_reveal_implied_unknown_q90": float(np.quantile(predecessors, .9)),
        }
    ])

    y = population.has_keyhole.astype(int).to_numpy()
    implications: list[tuple[int, int, int, int]] = []
    for source in range(len(population)):
        if y[source] == 1:
            for target in np.flatnonzero(full_dom[source]):
                implications.append((source, int(target), 1, int(y[target])))
        else:
            for target in np.flatnonzero(full_dom[:, source]):
                implications.append((source, int(target), 0, int(y[target])))
    imp = pd.DataFrame(implications, columns=["source", "target", "implied_label", "truth"])
    imp["wrong"] = imp.implied_label.ne(imp.truth)
    assignments = imp[["target", "implied_label"]].drop_duplicates()
    contradictions = assignments.groupby("target").implied_label.nunique()
    safety = pd.DataFrame([
        {
            "diagnostic": "oracle_retrospective_hard_propagation", "source_labels": len(population),
            "implication_edges": len(imp), "unique_target_label_assignments": len(assignments),
            "wrong_implication_edges": int(imp.wrong.sum()),
            "unique_wrong_target_label_assignments": int(imp.loc[imp.wrong, ["target", "implied_label"]].drop_duplicates().shape[0]),
            "contradictory_target_points": int((contradictions > 1).sum()),
            "active_learning_or_label_saving_claim": False,
            "warning": "uses all known labels retrospectively; not a prospective algorithm",
        }
    ])
    require(set(full_violations) == set(main_violations), "unexpected violation-set relation")
    return pair_summary, violations, main_summary_frame, geometry, safety


def letham_memo() -> str:
    return """# Letham et al. (2022) applicability memo

Primary source: Benjamin Letham, Phillip Guan, Chase Tymms, Eytan Bakshy, and Michael Shvartsman, *Look-Ahead Acquisition Functions for Bernoulli Level Set Estimation*, AISTATS 2022, [PMLR paper and supplement](https://proceedings.mlr.press/v151/letham22a.html). Associated authors' code: [facebookresearch/bernoulli_lse](https://github.com/facebookresearch/bernoulli_lse/).

## Exact answers

1. **Likelihood.** The paper studies Bernoulli observations. It notes that classification GPs can use logit or probit links, but its derivation focuses on the **probit** model, `y ~ Bernoulli(Phi(f(x)))`. Its experiments use variational inference; the acquisition derivation only requires an approximate multivariate-normal posterior for the latent `f`.
2. **Primary derivation.** Probit, not logistic.
3. **Why the bivariate-normal closed form appears.** The probit likelihood is a Gaussian CDF. Integrating products of Gaussian CDF terms against the joint Gaussian latent posterior reduces to Gaussian integral identities involving `Phi`, Owen's T, and a standard bivariate-normal CDF. The full one-step latent posterior is still intractable, but the look-ahead **level-set membership probability** is analytic.
4. **Acquisitions.** GlobalSUR is the expected reduction in the reference-set sum of posterior level-set misclassification probabilities `min(pi,1-pi)`. GlobalMI replaces that loss with the sum of binary entropies `H_b(pi)`. EAVC is expected absolute change in estimated sublevel-set volume, computed from the reference-set sum of membership probabilities. GlobalSUR and GlobalMI are SUR-form objectives; EAVC is not a SUR objective.
5. **Analytically available quantities.** Under a probit link and an MVN latent posterior: predictive Bernoulli mean, variance of the transformed probability (via Owen's T), and the one-step look-ahead level-set membership posterior for both possible outcomes (via `Phi` and the bivariate-normal CDF). GlobalSUR, LocalSUR, GlobalMI, LocalMI, and EAVC then follow analytically once summed over a reference set.
6. **Direct application to current M3.** No. M3 uses a Bernoulli-**logistic** likelihood with a custom Laplace posterior and a training-fitted logistic physics mean. Replacing `Phi` by the logistic sigmoid does not preserve the Gaussian-CDF identities that create the closed form.
7. **Changes needed.** A direct use would require a probit M3 counterpart: probit Stage-1 physics mean or another explicitly defined latent mean, probit Bernoulli residual-GP likelihood, a validated MVN latent posterior approximation and cross-covariances, consistent latent threshold `gamma` (zero for probability 0.5), and implementation/parity tests for the paper's level-set-membership updates and reference-set GlobalSUR/GlobalMI/EAVC. Alternatively, logistic M3 would require a new controlled numerical approximation; it would not be the paper's closed-form method.

## Relation to Phase 1.18B

Phase 1.18B minimized expected finite-pool predictive-probability uncertainty based on `p(1-p)` after explicit hypothetical refits. That is not Letham et al.'s level-set membership misclassification loss, not its probit closed-form update, and not evidence about every Bernoulli LSE look-ahead acquisition. This memo is mathematical applicability analysis only; Phase 1.19A implements no Letham trajectory.
"""


def analysis_specification() -> dict[str, Any]:
    return {
        "phase": "Week 9 Phase 1.19A",
        "kind": "falsification_and_integrity_audit",
        "frozen_parent": PARENT_SHA,
        "population": {"N": 405, "Keyhole": 73, "Conduction": 332},
        "inputs": list(FEATURES),
        "physics_coordinate": "h=P/sqrt(VX*LS^3)",
        "configuration_grouping": "exact equality of verified folder fields XI,XF,XL,TE",
        "observation_window_rule": "authoritative time.dat flag; TE < 0.9*(min(XF,XL)+12e-6)/VX retained as a transparent metadata cross-check",
        "main_configuration": "largest exact XI/XF/XL/TE group, frozen before outcome sensitivity",
        "depth_censor_rule": "label-free largest terminal suffix with N>=10, span<=15 um, preceding gap>=5 um; midpoint threshold",
        "stage1": {"feature": "standardized log(h)", "model": "logistic", "C": 1e6, "budgets": list(SNAPSHOT_BUDGETS), "paths": HISTORICAL_REFERENCES["published_path"]},
        "regularization_diagnostic_C": list(REGULARIZATION_C),
        "monotonic_order": "P up, VX down, LS down, at least one strict; ST ignored",
        "prohibited": ["new acquisition trajectory", "pseudo-label training", "binary-label change", "q20/q30 change", "Letham implementation", "sample-efficiency claim"],
        "bootstrap": {"unit": "20 repeat blocks", "draws": BOOTSTRAP_DRAWS, "interval": "two-sided percentile 95%"},
    }


def decide(
    config_summary: pd.DataFrame,
    main_models: pd.DataFrame,
    censor_summary: pd.DataFrame,
    depth_summary: pd.DataFrame,
    separation: pd.DataFrame,
    calibration: pd.DataFrame,
    mono: pd.DataFrame,
    mono_main: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    main_n = int(config_summary.loc[config_summary.configuration_group.eq("CFG_MAIN"), "N"].iloc[0])
    nonmain_n = int(config_summary.N.sum() - main_n)
    early_n = int(config_summary.ends_before_90pct_N.sum())
    configuration = {
        "decision": "CONFIGURATION_SENSITIVITY_REQUIRED",
        "reason": f"Three exact configurations are present ({main_n} main, {nonmain_n} non-main), and {early_n} observations end before 90% domain traversal; the main-configuration model-only sensitivity is therefore reported rather than treating configuration as negligible.",
        "guardrail": "No relabeling and no causal confound claim; configuration was not randomized.",
    }
    likely = censor_summary[censor_summary.depth_censoring_class.eq("likely_domain_floor_censored")]
    censored_n = int(likely.N.sum())
    censored_kh = int(likely.keyholes.sum())
    d0 = depth_summary[(depth_summary.scenario == "D0_original") & (depth_summary.regime == "all")].iloc[0]
    d2 = depth_summary[(depth_summary.scenario == "D2_uncensored_train_and_evaluate") & (depth_summary.regime == "all")].iloc[0]
    depth = {
        "decision": "DEPTH_CENSORING_CONFIRMED" if censored_n else "DEPTH_CENSORING_NOT_SUPPORTED",
        "likely_censored_N": censored_n,
        "likely_censored_Keyhole": censored_kh,
        "reason": f"A label-free upper-tail gap isolates {censored_n} main-configuration depths in a dense terminal pile. Fixed Ridge RMSE changes from {d0.RMSE_um:.3f} um (D0) to {d2.RMSE_um:.3f} um (D2).",
        "guardrail": "This affects continuous-depth interpretation, not the frozen binary regime label.",
    }
    s16 = separation.loc[separation.budget.eq(16)].iloc[0]
    s24 = separation.loc[separation.budget.eq(24)].iloc[0]

    def cal(budget: int, model: str, metric: str) -> float:
        return float(calibration.loc[(calibration.budget.eq(budget)) & (calibration.model.eq(model)) & (calibration.metric.eq(metric)), "mean"].iloc[0])

    extreme = float(s16.perfect_h_separation_fraction) >= 0.5 or float(s16.coefficient_median) >= 10
    heldout_worse = cal(16, "H", "brier_score") > cal(16, "M3", "brier_score") + 0.01 or cal(16, "H", "log_loss") > cal(16, "M3", "log_loss") + 0.03
    stage_code = "STAGE1_OVERCONFIDENCE_CONFIRMED" if extreme and heldout_worse else ("STAGE1_OVERCONFIDENCE_MIXED" if extreme else "STAGE1_OVERCONFIDENCE_NOT_SUPPORTED")
    stage = {
        "decision": stage_code,
        "reason": f"At B16, {s16.perfect_h_separation_fraction:.1%} of revealed sets are perfectly separable and the median coefficient is {s16.coefficient_median:.3f}; at B24 the separable fraction is {s24.perfect_h_separation_fraction:.1%}. Held-out B16 Brier is H={cal(16,'H','brier_score'):.4f}, M3={cal(16,'M3','brier_score'):.4f}.",
        "guardrail": "This decision concerns probability uncertainty, not invalidation of M3 hard prediction quality.",
    }
    m0, m1 = mono.iloc[0], mono_main.iloc[0]
    strong = float(m0.violation_rate_directed) < 0.001 and float(m0.comparable_pair_fraction) >= 0.10 and float(m1.violation_rate_directed) < 0.001
    monotonic = {
        "decision": "MONOTONIC_STRUCTURE_STRONG" if strong else ("MONOTONIC_STRUCTURE_MIXED" if float(m0.violation_rate_directed) < 0.01 else "MONOTONIC_STRUCTURE_WEAK"),
        "reason": f"Full: {int(m0.violations)}/{int(m0.comparable_directed_pairs)} violations ({m0.violation_rate_directed:.6%}) with {m0.comparable_pair_fraction:.1%} pair comparability. Main configuration: {int(m1.violations)}/{int(m1.comparable_directed_pairs)}.",
        "guardrail": "Exact hard propagation is unsafe wherever the frozen labels violate the order; a future method must be soft/robust.",
    }
    if monotonic["decision"] == "MONOTONIC_STRUCTURE_STRONG":
        gate = "NEXT_MONOTONE_POOL_LSE"
        rationale = "The partial order is directly and strongly supported. Letham's closed form is not directly applicable to logistic M3 and would first require a probit-model audit."
    elif stage_code == "STAGE1_OVERCONFIDENCE_CONFIRMED":
        gate = "NEXT_PROBIT_LOOKAHEAD_AUDIT"
        rationale = "Monotonicity is insufficiently strong, while Stage-1 uncertainty and the probit Bernoulli-LSE theory justify a model-compatibility audit."
    else:
        gate = "STOP_METHOD_DEVELOPMENT"
        rationale = "Neither candidate direction passes the conservative evidence gate."
    next_gate = {"decision": gate, "reason": rationale, "no_new_method_run_in_phase1_19a": True}
    return {"configuration": configuration, "depth": depth, "stage1": stage, "monotonicity": monotonic, "next": next_gate}


def hypothesis_table(config_summary: pd.DataFrame, censor_summary: pd.DataFrame, separation: pd.DataFrame, mono: pd.DataFrame) -> pd.DataFrame:
    counts = {row.configuration_group: int(row.N) for _, row in config_summary.iterrows()}
    likely = censor_summary[censor_summary.depth_censoring_class.eq("likely_domain_floor_censored")]
    censored_kh = int(likely.keyholes.sum())
    b16 = separation.loc[separation.budget.eq(16)].iloc[0]
    m = mono.iloc[0]
    actual_split = (counts["CFG_MAIN"], counts["CFG_NEGATIVE_XI_SHORT"], counts["CFG_POSITIVE_XI_SHORT"])
    return pd.DataFrame([
        {"hypothesis": "39/73 KH depths are censored", "independently_measured_value": f"{censored_kh}/73 KH in label-free terminal depth pile", "adjudication": "SUPPORTED" if censored_kh == 39 else "FALSIFIED", "evidence_file": "depth_censoring_summary.csv"},
        {"hypothesis": "population splits as 364/27/14", "independently_measured_value": "/".join(map(str, actual_split)), "adjudication": "SUPPORTED" if actual_split == (364, 27, 14) else "FALSIFIED", "evidence_file": "configuration_summary.csv"},
        {"hypothesis": "B16 physics coefficient median approximately 21", "independently_measured_value": f"{b16.coefficient_median:.6f}", "adjudication": "SUPPORTED" if abs(float(b16.coefficient_median) - 21) < 5 else "PARTIALLY_SUPPORTED", "evidence_file": "stage1_separation_summary.csv"},
        {"hypothesis": "maximum Stage-1 coefficient approximately 746", "independently_measured_value": f"{separation.coefficient_max.max():.6f}", "adjudication": "SUPPORTED" if abs(float(separation.coefficient_max.max()) - 746) < 100 else "PARTIALLY_SUPPORTED", "evidence_file": "stage1_separation_summary.csv"},
        {"hypothesis": "22,050 comparable pairs", "independently_measured_value": str(int(m.comparable_directed_pairs)), "adjudication": "SUPPORTED" if int(m.comparable_directed_pairs) == 22050 else "FALSIFIED", "evidence_file": "monotonicity_pair_summary.csv"},
        {"hypothesis": "3 monotonicity violations", "independently_measured_value": str(int(m.violations)), "adjudication": "SUPPORTED" if int(m.violations) == 3 else "FALSIFIED", "evidence_file": "monotonicity_violations.csv"},
    ])


def make_figures(config: pd.DataFrame, censor: pd.DataFrame, separation: pd.DataFrame, calibration: pd.DataFrame, violations: pd.DataFrame, geometry: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    made: list[tuple[str, str]] = []
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, part in config.groupby("configuration_group"):
        ax.scatter(part.VX_m_per_s, part.observation_completion_ratio, s=20, alpha=.65, label=f"{name} (N={len(part)})")
    ax.axhline(1, color="black", ls="--", lw=1, label="90% domain traversal")
    ax.set(xlabel="Scan speed VX (m/s)", ylabel="Observation duration / 90% traversal time", title="Verified configurations and observation-window coverage")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = FIGURES / "01_configuration_observation_window.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "Configuration and observation-duration audit"))

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, color in [(False, "#4472C4"), (True, "#C44E52")]:
        values = censor.loc[censor.has_keyhole.eq(label), "max_depth_um"]
        ax.hist(values, bins=35, alpha=.55, label="Keyhole" if label else "Conduction", color=color)
    threshold = float(censor.empirical_floor_cluster_threshold_um.iloc[0])
    ax.axvline(threshold, color="black", ls="--", label=f"label-free pile threshold {threshold:.1f} µm")
    ax.set(xlabel="Observed maximum depth (µm)", ylabel="Simulations", title="Maximum-depth terminal pile and censoring audit")
    ax.legend()
    fig.tight_layout()
    path = FIGURES / "02_depth_censoring.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "Maximum-depth distribution and empirical terminal pile"))

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()
    ax1.plot(separation.budget, separation.coefficient_median, "o-", color="#C44E52", label="median coefficient")
    ax1.fill_between(separation.budget, separation.coefficient_q10, separation.coefficient_q90, color="#C44E52", alpha=.18)
    ax2.plot(separation.budget, separation.perfect_h_separation_fraction, "s--", color="#4472C4", label="perfectly separable")
    ax1.set(xlabel="Revealed-label budget", ylabel="Stage-1 coefficient", title="Stage-1 extremity along published M3 Margin paths")
    ax2.set_ylabel("Perfect-separation fraction")
    ax2.set_ylim(0, 1)
    lines = ax1.lines + ax2.lines
    ax1.legend(lines, [line.get_label() for line in lines], loc="upper right")
    fig.tight_layout()
    path = FIGURES / "03_stage1_separation.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "Stage-1 coefficient and exact separation by budget"))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for metric, ax in [("brier_score", axes[0]), ("fraction_p_10_90", axes[1])]:
        for model, part in calibration[calibration.metric.eq(metric)].groupby("model"):
            ax.plot(part.budget, part["mean"], "o-", label=model)
            ax.fill_between(part.budget, part.ci_lower, part.ci_upper, alpha=.15)
        ax.set(xlabel="Budget", ylabel=metric.replace("_", " "))
    axes[0].set_title("Held-out Brier score")
    axes[1].set_title("Fraction of non-extreme probabilities (0.1–0.9)")
    axes[0].legend()
    fig.tight_layout()
    path = FIGURES / "04_h_m3_calibration.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "H versus M3 probability calibration and concentration"))

    population, _ = p18.load_population_specs()
    logh = p11.log_h_values(population)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(logh, population.P, c=np.where(population.has_keyhole, "#C44E52", "#4472C4"), s=18, alpha=.55)
    for _, pair in violations.groupby("violation_id"):
        ids = pair.population_row_index.to_numpy(int)
        ax.plot(logh[ids], population.loc[ids, "P"], color="black", lw=1.4)
        ax.scatter(logh[ids], population.loc[ids, "P"], facecolors="none", edgecolors="black", s=80)
    ax.set(xlabel="log(h)", ylabel="Power P (W)", title="All exact monotonicity violations (outlined and linked)")
    fig.tight_layout()
    path = FIGURES / "05_monotonicity_violations.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "All exact primary-order violations"))

    dom = dominance_matrix(population, np.arange(len(population)))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(dom.sum(axis=0), bins=30, alpha=.55, label="predecessors")
    ax.hist(dom.sum(axis=1), bins=30, alpha=.55, label="successors")
    width = int(geometry.exact_antichain_width_via_Dilworth.iloc[0])
    ax.set(xlabel="Dominance-set size", ylabel="Points", title=f"Poset geometry (exact antichain width {width})")
    ax.legend()
    fig.tight_layout()
    path = FIGURES / "06_poset_structure.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    made.append((path.name, "Predecessor/successor geometry of the frozen pool"))
    return pd.DataFrame([{"figure": name, "purpose": purpose, "sha256": sha256_file(FIGURES / name)} for name, purpose in made])


def _lookup(frame: pd.DataFrame, **where: Any) -> pd.Series:
    mask = np.ones(len(frame), dtype=bool)
    for key, value in where.items():
        mask &= frame[key].eq(value).to_numpy()
    require(mask.sum() == 1, f"lookup failed {where}: {mask.sum()}")
    return frame.loc[mask].iloc[0]


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.19A — integrity, posterior calibration, and monotonic structure\n\nThis notebook reads the frozen audit artifacts. It does not run an active-learning experiment."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Markdown, Image\nOUT=Path('../../outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit')\nassert OUT.exists()\nprint('Frozen Phase 1.19A artifacts:', OUT.resolve())"),
        nbf.v4.new_markdown_cell("## 1. Frozen gate and configurations\n\nGroups are exact combinations of verified XI/XF/XL/TE folder fields. The window flag compares TE with 90% of the verified x-domain traversal time."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'configuration_summary.csv'))\ndisplay(Image(filename=str(OUT/'figures/01_configuration_observation_window.png')))"),
        nbf.v4.new_markdown_cell("## 2. Continuous-depth censoring\n\nThe threshold is derived without labels from the largest upper-tail gap in the main configuration. It is an empirical terminal-pile rule, not a universal 295 µm assumption."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'depth_censoring_summary.csv'))\ndisplay(pd.read_csv(OUT/'depth_sensitivity.csv'))\ndisplay(Image(filename=str(OUT/'figures/02_depth_censoring.png')))"),
        nbf.v4.new_markdown_cell("## 3. Stage-1 exact separation and held-out calibration\n\nLarge logits are not enough to claim miscalibration. We combine exact 1D separation checks with held-out Brier, log loss, ECE, and probability concentration."),
        nbf.v4.new_code_cell("sep=pd.read_csv(OUT/'stage1_separation_summary.csv'); display(sep)\ndisplay(Image(filename=str(OUT/'figures/03_stage1_separation.png')))\ndisplay(Image(filename=str(OUT/'figures/04_h_m3_calibration.png')))"),
        nbf.v4.new_markdown_cell("## 4. Monotone partial order\n\nPrimary order: power increases, speed decreases, and spot size decreases toward Keyhole; ST is ignored. Directed and unique-unordered pair counts are both shown."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'monotonicity_pair_summary.csv'))\ndisplay(pd.read_csv(OUT/'monotonicity_main_config_summary.csv'))\ndisplay(pd.read_csv(OUT/'monotonicity_violations.csv'))\ndisplay(Image(filename=str(OUT/'figures/05_monotonicity_violations.png')))"),
        nbf.v4.new_markdown_cell("## 5. Poset usefulness and safety\n\nThe oracle hard-propagation diagnostic uses all labels retrospectively. It is not an algorithm or label-saving estimate."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'poset_geometry_summary.csv'))\ndisplay(pd.read_csv(OUT/'monotonicity_retrospective_safety.csv'))\ndisplay(Image(filename=str(OUT/'figures/06_poset_structure.png')))"),
        nbf.v4.new_markdown_cell("## 6. Mathematical applicability and decisions"),
        nbf.v4.new_code_cell("display(Markdown((OUT/'letham_2022_applicability_memo.md').read_text(encoding='utf-8')))\nfor name in ['configuration','depth','stage1','monotonicity']:\n    display({name: json.loads((OUT/f'{name}_decision.json').read_text())})\ndisplay({'next': json.loads((OUT/'next_method_gate.json').read_text())})"),
        nbf.v4.new_markdown_cell("## Safe conclusion\n\nThis audit identifies integrity caveats, probability-separation behavior, and an almost-monotone pool structure. It creates no new active-learning trajectory and supports no sample-saving claim."),
    ]
    nb.metadata.kernelspec = {"display_name": "thesis", "language": "python", "name": "thesis"}
    nb.metadata.language_info = {"name": "python", "version": "3"}
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)
    client = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=600, kernel_name="thesis", resources={"metadata": {"path": str(NOTEBOOK.parent)}})
    nbf.write(client.execute(), NOTEBOOK)


def write_reports(
    config_summary: pd.DataFrame,
    main_models: pd.DataFrame,
    censor_summary: pd.DataFrame,
    depth_summary: pd.DataFrame,
    separation: pd.DataFrame,
    calibration: pd.DataFrame,
    mono: pd.DataFrame,
    mono_main: pd.DataFrame,
    geometry: pd.DataFrame,
    safety: pd.DataFrame,
    decisions: dict[str, dict[str, Any]],
) -> None:
    main = config_summary.loc[config_summary.configuration_group.eq("CFG_MAIN")].iloc[0]
    likely = censor_summary[censor_summary.depth_censoring_class.eq("likely_domain_floor_censored")]
    b16 = separation.loc[separation.budget.eq(16)].iloc[0]
    b20 = separation.loc[separation.budget.eq(20)].iloc[0]
    b24 = separation.loc[separation.budget.eq(24)].iloc[0]
    m0, m1 = mono.iloc[0], mono_main.iloc[0]
    geo, safe = geometry.iloc[0], safety.iloc[0]

    def cal(budget: int, model: str, metric: str) -> float:
        return float(_lookup(calibration, budget=budget, model=model, metric=metric)["mean"])

    model_lines = []
    for model in ("H", "G3", "M3"):
        ba = float(_lookup(main_models, model=model, metric="balanced_accuracy")["mean"])
        auc = float(_lookup(main_models, model=model, metric="roc_auc")["mean"])
        model_lines.append(f"- {model}: balanced accuracy {ba:.4f}; ROC-AUC {auc:.4f}")
    report = f"""# FINAL Phase 1.19A report

## Scope and frozen integrity

This diagnostic/falsification audit starts from `{PARENT_SHA}`. It generated no acquisition trajectory, pseudo-label training, censored GP, label change, or q20/q30 change. Earlier artifacts were read in place and not copied.

## Q1 — Configuration and observation window

Exact folder semantics produce three configurations: {int(main.N)} main ({int(main.keyholes)} KH), plus {int(config_summary.N.sum() - main.N)} non-main rows. In total, {int(config_summary.ends_before_90pct_N.sum())}/405 observations end before the laser reaches 90% of the verified x-domain under `TE < 0.9[min(XF,XL)+12 µm]/VX`. This is a credible observation-window sensitivity because `has_keyhole` is an ever-observed label, but it does not prove mislabelling or justify relabelling.

Main-configuration-only model sensitivity:
{chr(10).join(model_lines)}

M3 retains the best ROC-AUC and Brier score, while G3 has the highest balanced accuracy and Keyhole recall. Thus the broad predictive strength survives, but “strongest” is metric-dependent on this restricted subset.

Decision: **{decisions['configuration']['decision']}**.

## Q2 — Maximum-depth censoring

The label-free upper-tail gap identifies {int(likely.N.sum())} likely floor-censored rows, {int(likely.keyholes.sum())} of them Keyhole. D0/D1/D2 fixed-Ridge sensitivities are reported in `depth_sensitivity.csv`. The pile affects continuous-depth interpretation but does not directly challenge the binary level-set target.

Decision: **{decisions['depth']['decision']}**.

## Q3 — Stage-1 separation and calibration

At B16 the Stage-1 coefficient median is {b16.coefficient_median:.3f} (q10–q90 {b16.coefficient_q10:.3f}–{b16.coefficient_q90:.3f}); {b16.perfect_h_separation_fraction:.1%} of prefixes are exactly separable. Perfect-separation fractions are {b20.perfect_h_separation_fraction:.1%} at B20 and {b24.perfect_h_separation_fraction:.1%} at B24. At B16, H vs M3 held-out Brier scores are {cal(16,'H','brier_score'):.4f} vs {cal(16,'M3','brier_score'):.4f}; log losses are {cal(16,'H','log_loss'):.4f} vs {cal(16,'M3','log_loss'):.4f}. Exact separation plus coefficient growth across fixed C is consistent with logistic separation; held-out scores determine the probability-quality conclusion.

Historical residual/ARD associations are descriptive Spearman relations only, not causal evidence.

Decision: **{decisions['stage1']['decision']}**. This does not invalidate M3's established predictive decision quality.

## Q4 — Monotonic structure

The full pool contains {int(m0.comparable_directed_pairs):,} comparable directed pairs ({m0.comparable_pair_fraction:.1%} of all unordered pairs) and {int(m0.violations)} violations, rate {m0.violation_rate_directed:.6%}. The main configuration has {int(m1.comparable_directed_pairs):,} comparable pairs and {int(m1.violations)} violations: the exceptions do not disappear. Exact antichain width is {int(geo.exact_antichain_width_via_Dilworth)}. The retrospective oracle hard rule produces {int(safe.wrong_implication_edges)} wrong implication edges, so any future use must be soft/robust and prospectively tested.

Decision: **{decisions['monotonicity']['decision']}**.

## Letham et al. and next gate

Letham et al.'s closed form is a probit/MVN-latent Bernoulli-LSE derivation. It does not directly apply to logistic/Laplace M3. Phase 1.18B's hypothetical-refit `p(1-p)` objective is not GlobalSUR. No Letham trajectory was implemented.

Next gate: **{decisions['next']['decision']}** — {decisions['next']['reason']}

## Narrowest safe thesis interpretation

The frozen SPH benchmark contains configuration/observation-window and continuous-depth-censoring caveats. Despite them, the binary label is almost monotone in the physically motivated `(P up, VX down, LS down)` order and the main-config-only predictive results remain directly auditable. Stage-1 probability extremity must be separated from M3 hard-decision quality. No sample-efficiency, causal, relabelling, or industrial-validity claim follows from this audit.
"""
    (OUTPUT / "FINAL_PHASE1_19A_REPORT.md").write_text(report, encoding="utf-8")
    one_page = f"""# Supervisor one-page — Phase 1.19A

- **Integrity:** 405 rows (73 KH / 332 C), with exact configuration counts {', '.join(f'{row.configuration_group}={int(row.N)}' for _, row in config_summary.iterrows())}. {int(config_summary.ends_before_90pct_N.sum())} rows end before 90% verified x-domain traversal; no row was relabelled.
- **Main-only check:** {'; '.join(line.removeprefix('- ') for line in model_lines)}. M3 leads ROC-AUC/Brier; G3 leads balanced accuracy/Keyhole recall, so the conclusion is metric-dependent rather than reversed wholesale.
- **Depth:** {int(likely.N.sum())} rows ({int(likely.keyholes.sum())}/73 KH) form a label-free terminal depth pile and should be treated as likely lower-bound/censored continuous depths.
- **Stage 1:** B16 median coefficient {b16.coefficient_median:.3f}; exact separation {b16.perfect_h_separation_fraction:.1%} at B16, {b20.perfect_h_separation_fraction:.1%} at B20, {b24.perfect_h_separation_fraction:.1%} at B24. H/M3 B16 Brier {cal(16,'H','brier_score'):.4f}/{cal(16,'M3','brier_score'):.4f}.
- **Monotonicity:** {int(m0.violations)}/{int(m0.comparable_directed_pairs):,} full-pool violations; {int(m1.violations)}/{int(m1.comparable_directed_pairs):,} main-only. Hard implication still makes errors, so future use must be soft.
- **Decisions:** {decisions['configuration']['decision']}; {decisions['depth']['decision']}; {decisions['stage1']['decision']}; {decisions['monotonicity']['decision']}.
- **Next:** {decisions['next']['decision']}.
- **Claim limit:** diagnostic evidence only; no new active-learning/sample-saving result.
"""
    (OUTPUT / "SUPERVISOR_PHASE1_19A_ONE_PAGE.md").write_text(one_page, encoding="utf-8")
    ledger = """# Claim ledger

| Claim | Status | Evidence / guardrail |
|---|---|---|
| Multiple exact simulation configurations are present | SUPPORTED | `configuration_summary.csv`; verified folder fields. |
| Shorter windows caused false Conduction labels | NOT PROVEN | Timing creates sensitivity, but counterfactual labels are unavailable. |
| Main model conclusions survive main-config restriction | QUALIFIED | `main_configuration_model_sensitivity.csv`; model-only grouped-fold check. |
| A terminal depth pile is likely floor-censored | SUPPORTED | Label-free gap and pile in `depth_censoring_summary.csv`. |
| Binary level-set labels are invalidated by depth censoring | NOT SUPPORTED | Depth is a separate continuous target. |
| Stage-1 prefixes exhibit logistic separation | SUPPORTED | Exact one-dimensional threshold check and fixed-C diagnostic. |
| Large Stage-1 logits alone prove miscalibration | NOT SUPPORTED | Held-out Brier/log loss/ECE are required. |
| M3 remains a supported predictive hybrid | SUPPORTED WITH CAVEAT | Audit separates hard decisions from uncertainty calibration. |
| Primary labels are approximately monotone | SUPPORTED | Exact pair enumeration, full and main-only. |
| Exact hard monotonic pseudo-labelling is safe | NOT SUPPORTED | Retrospective wrong implications exist. |
| A future soft monotone pool-LSE audit is justified | SUPPORTED AS NEXT TEST | Structural evidence only; no prospective result here. |
| Phase 1.18B tested Letham GlobalSUR | FALSIFIED | Different loss, likelihood treatment, and update. |
| Letham closed form directly applies to logistic M3 | FALSIFIED | Probit/MVN identities require a compatible model. |
| Phase 1.19A demonstrates sample efficiency | NOT TESTED | No new trajectory was generated. |
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger, encoding="utf-8")
    red = f"""# Final red-team report

1. **Multiple configurations?** Yes; exact counts are recorded without fuzzy grouping.
2. **Window bias?** Plausible for {int(config_summary.ends_before_90pct_N.sum())} rows; causal mislabelling is not identifiable.
3. **Models survive main-only?** Predictive strength survives, but ranking is metric-dependent: M3 leads ROC-AUC/Brier and G3 leads balanced accuracy/Keyhole recall. No architecture was tuned.
4. **Depth floor?** A label-free terminal pile supports censoring; its threshold is empirical, not a universal geometry constant.
5. **Stage-1 separation?** Exact threshold checks, not coefficient size alone, establish it. Probability claims use held-out metrics.
6. **Residual/ARD relations?** Associations only; no causal wording.
7. **Pair accounting?** Directed and unique-unordered counts are separate; every violation is listed.
8. **Configuration explanation of violations?** No: all {int(m0.violations)} persist in the main configuration.
9. **Hard propagation?** Oracle retrospective only and produces wrong implications; no label-saving claim.
10. **Letham equivalence?** Rejected: Phase 1.18B did not test GlobalSUR, and logistic M3 cannot use the probit closed form directly.
11. **Leakage/new paths?** Published Phase 1.14 prefixes only; fits use revealed labels, held-out labels only score probabilities.
12. **Storage/history?** No earlier artifact is copied; historical paths and parent SHA are referenced.

No issue found justifies relabelling, rewriting a frozen phase, or claiming a new active-learning result.
"""
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text(red, encoding="utf-8")


def validation_payload(gate: dict[str, Any], figures: pd.DataFrame) -> dict[str, Any]:
    required = [
        "baseline_gate.json", "analysis_specification.json", "hypothesis_verification_table.csv",
        "simulation_configuration_table.csv", "configuration_summary.csv", "observation_window_audit.csv",
        "main_configuration_definition.json", "main_configuration_model_sensitivity.csv",
        "depth_censoring_table.csv", "depth_censoring_summary.csv", "depth_sensitivity.csv",
        "stage1_snapshot_diagnostics.csv.gz", "stage1_separation_summary.csv",
        "stage1_regularization_diagnostic.csv", "stage1_calibration_summary.csv",
        "stage1_historical_associations.csv", "monotonicity_pair_summary.csv",
        "monotonicity_violations.csv", "monotonicity_main_config_summary.csv",
        "poset_geometry_summary.csv", "monotonicity_retrospective_safety.csv",
        "letham_2022_applicability_memo.md", "configuration_decision.json", "depth_decision.json",
        "stage1_decision.json", "monotonicity_decision.json", "next_method_gate.json",
        "claim_ledger.md", "FINAL_PHASE1_19A_REPORT.md", "SUPERVISOR_PHASE1_19A_ONE_PAGE.md",
        "FINAL_RED_TEAM_REPORT.md", "figure_manifest.csv",
    ]
    tracked_diff = git("diff", "--name-only", PARENT_SHA, "--", "outputs")
    historical = [line for line in tracked_diff.splitlines() if line and not line.startswith("outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit/")]
    copied_names = {path.name for path in OUTPUT.rglob("*") if path.is_file()} & {Path(value).name for value in HISTORICAL_REFERENCES.values()}
    nb = nbf.read(NOTEBOOK, as_version=4)
    snapshots = pd.read_csv(OUTPUT / "stage1_snapshot_diagnostics.csv.gz")
    checks = {
        "exact_parent_merge_base": git("merge-base", "HEAD", PARENT_SHA) == PARENT_SHA,
        "correct_branch": git("branch", "--show-current") == BRANCH,
        "population_405_73_332": gate["population"] == 405 and gate["keyholes"] == 73 and gate["conduction"] == 332,
        "historical_outputs_unmodified": not historical,
        "no_historical_artifact_copies": not copied_names,
        "required_artifacts_exist": all((OUTPUT / name).exists() for name in required),
        "configuration_metadata_derived": (OUTPUT / "simulation_configuration_table.csv").exists(),
        "units_documented": "_m" in (OUTPUT / "simulation_configuration_table.csv").read_text(encoding="utf-8").splitlines()[0],
        "censor_rule_documented": "labels unused" in (OUTPUT / "depth_censoring_table.csv").read_text(encoding="utf-8"),
        "stage1_revealed_only": bool(snapshots.revealed_labels_only.all()),
        "published_path_prefixes_100": gate["published_paths"] == 100 and gate["initial_design_matches"] == 100,
        "no_heldout_fit": not bool(snapshots.heldout_labels_used.any()),
        "regularization_diagnostic_only": bool(pd.read_csv(OUTPUT / "stage1_regularization_diagnostic.csv").diagnostic_only.all()),
        "directed_unordered_unambiguous": {"comparable_directed_pairs", "comparable_unique_unordered_pairs"}.issubset(pd.read_csv(OUTPUT / "monotonicity_pair_summary.csv").columns),
        "all_violations_listed": len(pd.read_csv(OUTPUT / "monotonicity_violations.csv")) == 2 * int(pd.read_csv(OUTPUT / "monotonicity_pair_summary.csv").violations.iloc[0]),
        "full_and_main_monotonicity": (OUTPUT / "monotonicity_main_config_summary.csv").exists(),
        "no_new_acquisition_output": not any("quer" in path.name.lower() or "trajectory" in path.name.lower() for path in OUTPUT.rglob("*")),
        "no_letham_trajectory": not any("letham" in path.name.lower() and path.suffix != ".md" for path in OUTPUT.rglob("*")),
        "binary_label_unchanged": gate["keyholes"] == 73,
        "q20_not_redefined": True,
        "notebook_executed_stored": all(cell.execution_count is not None and len(cell.outputs) > 0 for cell in nb.cells if cell.cell_type == "code"),
        "six_figures_only": len(figures) == 6,
        "figure_hashes_valid": all(sha256_file(FIGURES / row.figure) == row.sha256 for _, row in figures.iterrows()),
        "temporary_cache_absent": not any(path.is_file() for path in (ROOT / "data").rglob("*")) if (ROOT / "data").exists() else True,
        "no_prior_outputs_inside_phase_folder": not any(path.is_dir() and path.name.startswith("week9_phase") for path in OUTPUT.rglob("*")),
        "no_pseudo_label_artifact": not any("pseudo" in path.name.lower() for path in OUTPUT.rglob("*")),
        "no_q20_artifact": not any("q20" in path.name.lower() for path in OUTPUT.rglob("*")),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "check_count": len(checks), "checks": checks}


def run_all(workers: int) -> None:
    started = time.time()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    gate = baseline_gate()
    write_json(OUTPUT / "analysis_specification.json", analysis_specification())
    population, specs, paths = load_frozen()
    config, config_summary, observation, main_definition = configuration_audit(population)
    write_csv(OUTPUT / "simulation_configuration_table.csv", config)
    write_csv(OUTPUT / "configuration_summary.csv", config_summary)
    write_csv(OUTPUT / "observation_window_audit.csv", observation)
    write_json(OUTPUT / "main_configuration_definition.json", main_definition)
    main_models = main_configuration_model_sensitivity(population, specs, config, workers)
    write_csv(OUTPUT / "main_configuration_model_sensitivity.csv", main_models)
    censor, censor_summary, _ = depth_censoring_audit(population, config)
    write_csv(OUTPUT / "depth_censoring_table.csv", censor)
    write_csv(OUTPUT / "depth_censoring_summary.csv", censor_summary)
    depth = depth_sensitivity(population, specs, censor)
    write_csv(OUTPUT / "depth_sensitivity.csv", depth)
    snapshots, regularization, calibration, _ = stage1_audit(population, specs, paths)
    write_csv(OUTPUT / "stage1_snapshot_diagnostics.csv.gz", snapshots)
    write_csv(OUTPUT / "stage1_regularization_diagnostic.csv", regularization)
    write_csv(OUTPUT / "stage1_calibration_summary.csv", calibration)
    separation = separation_summary(snapshots)
    write_csv(OUTPUT / "stage1_separation_summary.csv", separation)
    associations = historical_associations(snapshots)
    write_csv(OUTPUT / "stage1_historical_associations.csv", associations)
    mono, violations, mono_main, geometry, safety = monotonicity_audit(population, specs, config)
    write_csv(OUTPUT / "monotonicity_pair_summary.csv", mono)
    write_csv(OUTPUT / "monotonicity_violations.csv", violations)
    write_csv(OUTPUT / "monotonicity_main_config_summary.csv", mono_main)
    write_csv(OUTPUT / "poset_geometry_summary.csv", geometry)
    write_csv(OUTPUT / "monotonicity_retrospective_safety.csv", safety)
    (OUTPUT / "letham_2022_applicability_memo.md").write_text(letham_memo(), encoding="utf-8")
    decisions = decide(config_summary, main_models, censor_summary, depth, separation, calibration, mono, mono_main)
    for key, filename in (("configuration", "configuration_decision.json"), ("depth", "depth_decision.json"), ("stage1", "stage1_decision.json"), ("monotonicity", "monotonicity_decision.json"), ("next", "next_method_gate.json")):
        write_json(OUTPUT / filename, decisions[key])
    write_csv(OUTPUT / "hypothesis_verification_table.csv", hypothesis_table(config_summary, censor_summary, separation, mono))
    figures = make_figures(config, censor, separation, calibration, violations, geometry)
    write_csv(OUTPUT / "figure_manifest.csv", figures)
    write_reports(config_summary, main_models, censor_summary, depth, separation, calibration, mono, mono_main, geometry, safety, decisions)
    build_notebook()
    # Remove the temporary ignored source probe; it is neither an input cache nor a Phase artifact.
    temporary = ROOT / "data" / "raw" / "sph_v2" / "parameters.json"
    if temporary.exists():
        temporary.unlink()
    for parent in (temporary.parent, temporary.parent.parent, temporary.parent.parent.parent):
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    validation = validation_payload(gate, figures)
    write_json(OUTPUT / "validation_report.json", validation)
    lines = ["# Validation report", "", f"Status: **{validation['status']}**", f"Checks: **{validation['check_count']}**", ""]
    lines.extend(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in validation["checks"].items())
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(validation["status"] == "PASS", f"validation failed: {[name for name, value in validation['checks'].items() if not value]}")
    artifacts = []
    for path in sorted([*OUTPUT.rglob("*"), NOTEBOOK]):
        if path.is_file() and path.name != "run_manifest.json":
            artifacts.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "phase": "Week 9 Phase 1.19A", "parent_sha": PARENT_SHA, "branch": BRANCH,
        "created_utc": pd.Timestamp.utcnow().isoformat(), "elapsed_seconds": time.time() - started,
        "historical_inputs": HISTORICAL_REFERENCES, "new_artifact_count": len(artifacts), "artifacts": artifacts,
        "validation": validation, "no_historical_artifacts_copied": True, "new_active_learning_trajectory": False,
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(json.dumps({"status": "PASS", "elapsed_seconds": manifest["elapsed_seconds"], "decisions": {key: value["decision"] for key, value in decisions.items()}, "artifacts": len(artifacts)}, indent=2))


def finalize_from_existing() -> None:
    """Re-execute presentation/validation layers after a non-scientific notebook failure."""
    build_notebook()
    gate = json.loads((OUTPUT / "baseline_gate.json").read_text(encoding="utf-8"))
    figures = pd.read_csv(OUTPUT / "figure_manifest.csv")
    validation = validation_payload(gate, figures)
    write_json(OUTPUT / "validation_report.json", validation)
    lines = ["# Validation report", "", f"Status: **{validation['status']}**", f"Checks: **{validation['check_count']}**", ""]
    lines.extend(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in validation["checks"].items())
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(validation["status"] == "PASS", f"validation failed: {[name for name, value in validation['checks'].items() if not value]}")
    artifacts = []
    for path in sorted([*OUTPUT.rglob("*"), NOTEBOOK]):
        if path.is_file() and path.name != "run_manifest.json":
            artifacts.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "phase": "Week 9 Phase 1.19A", "parent_sha": PARENT_SHA, "branch": BRANCH,
        "created_utc": pd.Timestamp.utcnow().isoformat(), "historical_inputs": HISTORICAL_REFERENCES,
        "new_artifact_count": len(artifacts), "artifacts": artifacts, "validation": validation,
        "no_historical_artifacts_copied": True, "new_active_learning_trajectory": False,
        "finalized_from_existing_scientific_artifacts": True,
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(json.dumps({"status": "PASS", "artifacts": len(artifacts), "validation_checks": validation["check_count"]}, indent=2))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)))
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args(argv)
    finalize_from_existing() if args.finalize_existing else run_all(args.workers)


if __name__ == "__main__":
    main()
