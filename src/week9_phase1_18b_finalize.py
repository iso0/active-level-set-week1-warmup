from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from nbclient import NotebookClient
from scipy.stats import binomtest, spearmanr
from sklearn.metrics import pairwise_distances

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_14_m3_margin_acquisition as p14
from src import week9_phase1_18b_prospective_global_gpc_sur_benchmark as engine


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = engine.OUTPUT
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "18_week9_phase1_18b_prospective_global_gpc_sur_benchmark.ipynb"
P0 = "P0_M3_MARGIN"
P1 = "P1_EXACT_FIXED_SUR"
P2 = "P2_PHYSICS_REFIT_SUR"
MODELS = (P0, P1, P2)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bootstrap(values: Sequence[float], key: str) -> tuple[float, float, float, float]:
    v = np.asarray(values, float)
    require(len(v) == 20 and np.isfinite(v).all(), f"bootstrap requires 20 finite blocks: {key}")
    rng = np.random.default_rng(engine.seed_u32("bootstrap", key))
    draws = v[rng.integers(0, len(v), size=(engine.BOOTSTRAP_DRAWS, len(v)))].mean(axis=1)
    return float(v.mean()), float(np.median(v)), float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def summary_ci(values: pd.Series, key: str) -> tuple[float, float, float]:
    mean, _, lo, hi = bootstrap(values.to_numpy(float), key)
    return mean, lo, hi


def collect() -> dict[str, pd.DataFrame]:
    population, specs, _ = engine.load_inputs()
    p0_pred = pd.read_csv(engine.PHASE14 / "new_predictions.csv.gz").assign(model=P0)
    p0_pred = p0_pred[["run_id", "repeat", "fold", "budget", "model", "population_row_index", "truth", "probability", "is_q20", "is_q30"]]
    p0_metrics = []
    p0_fits = pd.read_csv(engine.PHASE14 / "m3_active_fit_diagnostics.csv.gz").rename(columns={"model": "old_model"}).assign(arm=P0)
    p0_queries = pd.read_csv(engine.PHASE14 / "m3_margin_queries.csv.gz").assign(arm=P0)
    p0_paths_frame = pd.read_csv(engine.PHASE14 / "m3_margin_paths.csv.gz").assign(path=P0)
    predictions = [p0_pred]
    metrics: list[dict[str, Any]] = []
    fits = [p0_fits]
    queries = [p0_queries]
    paths = [p0_paths_frame]
    new_path_records: list[dict[str, Any]] = []
    selected, surdiag, candidates, runtimes = [], [], [], []
    for arm in engine.ARMS:
        files = sorted((engine.CHECKPOINTS / arm).glob("*.json.gz"))
        require(len(files) == 100, f"{arm}: {len(files)} checkpoints")
        for file in files:
            payload = engine.read_checkpoint(file)
            require(payload["schema_version"] == engine.CHECKPOINT_SCHEMA_VERSION and payload["complete"], f"bad checkpoint {file}")
            predictions.append(pd.DataFrame(payload["predictions"]))
            metrics.extend(payload["metrics"])
            fits.append(pd.DataFrame(payload["fit_diagnostics"]))
            queries.append(pd.DataFrame(payload["queries"]))
            sel = pd.DataFrame(payload["selected_sur_scores"])
            sel["repeat"] = int(payload["run_id"].split("__r")[1].split("_")[0])
            selected.append(sel)
            surdiag.append(pd.DataFrame(payload["sur_diagnostics"]))
            candidate_frame = pd.DataFrame(payload["candidate_scores"])
            candidate_keep = ["run_id", "budget", "arm", "candidate_population_row_index", "sur_score", "candidate_probability",
                              "current_global_uncertainty", "current_physics_slope", "physics_slope_y0", "physics_slope_y1"]
            candidates.append(candidate_frame[candidate_keep])
            runtimes.append(pd.DataFrame([{"run_id": payload["run_id"], "arm": arm, "run_seconds": payload["run_seconds"]}]))
            for order, index in enumerate(payload["queried_indices"], 1):
                new_path_records.append({"run_id": payload["run_id"], "query_order": order, "population_row_index": int(index), "path": arm, "role": "initial_design" if order <= 16 else "active_query"})
    paths.append(pd.DataFrame(new_path_records))
    pred = pd.concat(predictions, ignore_index=True)
    # Compute the published P0 metrics with the same metric function used by P1/P2.
    for keys, g in p0_pred.groupby(["run_id", "repeat", "fold", "budget", "model"], sort=True):
        run_id, repeat, fold, budget, model = keys
        for subset, flag in (("full81", np.ones(len(g), bool)), ("B1_q20", g.is_q20.to_numpy(bool)), ("B1_q30", g.is_q30.to_numpy(bool))):
            metrics.append({"run_id": run_id, "repeat": repeat, "fold": fold, "budget": budget, "model": model, "subset": subset,
                            **p14.p12.metric_values(g.truth.to_numpy()[flag], g.probability.to_numpy()[flag])})
    result = {
        "population": population,
        "predictions": pred,
        "metrics": pd.DataFrame(metrics),
        "fits": pd.concat(fits, ignore_index=True, sort=False),
        "queries": pd.concat(queries, ignore_index=True, sort=False),
        "paths": pd.concat(paths, ignore_index=True, sort=False),
        "selected": pd.concat(selected, ignore_index=True),
        "surdiag": pd.concat(surdiag, ignore_index=True),
        "candidates": pd.concat(candidates, ignore_index=True),
        "runtime": pd.concat(runtimes, ignore_index=True),
    }
    require(len(result["predictions"]) == 3 * 100 * 65 * 81, "prediction completeness")
    require(len(result["metrics"]) == 3 * 100 * 65 * 3, "metric completeness")
    return result


def aulc_table(metrics: pd.DataFrame, subset: str = "B1_q20") -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    part = metrics[metrics.subset.eq(subset)]
    for keys, g in part.groupby(["run_id", "repeat", "fold", "model"], sort=True):
        run_id, repeat, fold, model = keys
        g = g.sort_values("budget")
        require(g.budget.tolist() == list(engine.BUDGETS), f"AULC grid {keys}")
        rows.append({"run_id": run_id, "repeat": repeat, "fold": fold, "model": model,
                     "subset": subset, "accuracy_AULC_16_80": float(np.trapezoid(g.accuracy, g.budget) / 64)})
    outer = pd.DataFrame(rows)
    repeat = outer.groupby(["repeat", "model"], as_index=False).accuracy_AULC_16_80.mean()
    return outer, repeat


def contrasts(repeat: pd.DataFrame, subset: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = repeat.pivot(index="repeat", columns="model", values="accuracy_AULC_16_80").sort_index()
    rows = []
    for left, right in ((P1, P0), (P2, P0), (P2, P1)):
        values = (wide[left] - wide[right]).to_numpy(float)
        mean, median, lo, hi = bootstrap(values, f"{subset}|{left}-{right}")
        nonzero = values[values != 0]
        p = float(binomtest(int((nonzero > 0).sum()), len(nonzero), .5, alternative="two-sided").pvalue) if len(nonzero) else 1.0
        rows.append({"contrast": f"{left}-{right}", "subset": subset, "mean_difference": mean, "median_difference": median,
                     "ci_lower": lo, "ci_upper": hi, "positive_repeat_blocks": int((values > 0).sum()),
                     "zero_repeat_blocks": int((values == 0).sum()), "negative_repeat_blocks": int((values < 0).sum()),
                     "raw_two_sided_sign_p": p, "bootstrap_draws": engine.BOOTSTRAP_DRAWS})
    primary = pd.DataFrame(rows)
    fam = primary[primary.contrast.isin((f"{P1}-{P0}", f"{P2}-{P0}"))].copy().sort_values("raw_two_sided_sign_p")
    adjusted = []
    running = 0.0
    for rank, r in enumerate(fam.itertuples(index=False), 1):
        adj = min(1.0, (len(fam) - rank + 1) * r.raw_two_sided_sign_p)
        running = max(running, adj)
        adjusted.append({"contrast": r.contrast, "raw_p": r.raw_two_sided_sign_p, "holm_adjusted_p": running,
                         "holm_rank": rank, "family_size": len(fam), "supported_at_0.05": running < .05})
    return primary, pd.DataFrame(adjusted)


def region_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    regions = {"EARLY_B16_24": range(16, 25), "MID_B25_40": range(25, 41), "LATE_B41_80": range(41, 81), "BROAD_B16_40": range(16, 41)}
    rows = []
    for region, budgets in regions.items():
        budgets = list(budgets)
        run_rows = []
        for keys, g in metrics[metrics.subset.eq("B1_q20") & metrics.budget.isin(budgets)].groupby(["run_id", "repeat", "fold", "model"]):
            run_id, repeat, fold, model = keys
            g = g.sort_values("budget")
            require(g.budget.tolist() == budgets, f"region grid {keys}/{region}")
            run_rows.append({"run_id": run_id, "repeat": repeat, "fold": fold, "model": model,
                             "value": float(np.trapezoid(g.accuracy, g.budget) / (budgets[-1] - budgets[0]))})
        repeat = pd.DataFrame(run_rows).groupby(["repeat", "model"], as_index=False).value.mean()
        wide = repeat.pivot(index="repeat", columns="model", values="value").sort_index()
        for left, right in ((P1, P0), (P2, P0), (P2, P1)):
            v = (wide[left] - wide[right]).to_numpy()
            mean, median, lo, hi = bootstrap(v, f"region|{region}|{left}-{right}")
            rows.append({"region": region, "contrast": f"{left}-{right}", "mean_difference": mean, "median_difference": median,
                         "ci_lower": lo, "ci_upper": hi, "positive_repeat_blocks": int((v > 0).sum())})
    return pd.DataFrame(rows)


def checkpoint_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    names = ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive", "brier_score")
    rows = []
    for keys, g in metrics[metrics.budget.isin(engine.CHECKPOINT_BUDGETS)].groupby(["model", "subset", "budget"]):
        model, subset, budget = keys
        for metric in names:
            by_repeat = g.groupby("repeat")[metric].mean().sort_index()
            mean, lo, hi = summary_ci(by_repeat, f"checkpoint|{model}|{subset}|{budget}|{metric}")
            rows.append({"model": model, "subset": subset, "budget": budget, "metric": metric, "mean": mean, "ci_lower": lo, "ci_upper": hi})
    return pd.DataFrame(rows)


def learning_curves(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in metrics.groupby(["model", "subset", "budget"]):
        model, subset, budget = keys
        for metric in ("accuracy", "keyhole_recall", "balanced_accuracy"):
            by_repeat = g.groupby("repeat")[metric].mean().sort_index()
            mean, lo, hi = summary_ci(by_repeat, f"curve|{model}|{subset}|{budget}|{metric}")
            rows.append({"model": model, "subset": subset, "budget": budget, "metric": metric, "mean": mean, "ci_lower": lo, "ci_upper": hi})
    return pd.DataFrame(rows)


def path_diagnostics(paths: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = {(run_id, path): g.sort_values("query_order").population_row_index.astype(int).tolist() for (run_id, path), g in paths.groupby(["run_id", "path"])}
    run_ids = sorted(paths.run_id.unique())
    rows = []
    for run_id in run_ids:
        for left, right in ((P1, P0), (P2, P0), (P2, P1)):
            a, b = lookup[(run_id, left)], lookup[(run_id, right)]
            first = next((order for order, (x, y) in enumerate(zip(a, b), 1) if x != y), None)
            for budget in range(16, 81):
                sa, sb = set(a[:budget]), set(b[:budget])
                rows.append({"run_id": run_id, "comparison": f"{left}-{right}", "budget": budget,
                             "first_divergence_query_order": first, "jaccard": len(sa & sb) / len(sa | sb),
                             "unique_substitutions": len(sa - sb), "identical_prefix": a[:budget] == b[:budget]})
    detail = pd.DataFrame(rows)
    summary = detail.groupby(["comparison", "budget"], as_index=False).agg(
        mean_jaccard=("jaccard", "mean"), median_jaccard=("jaccard", "median"),
        mean_unique_substitutions=("unique_substitutions", "mean"), identical_prefix_fraction=("identical_prefix", "mean"),
        median_first_divergence_query_order=("first_divergence_query_order", "median"))
    return detail, summary


def active_query_diagnostics(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    population, specs, _ = engine.load_inputs()
    labels = population.has_keyhole.astype(int).to_numpy()
    distances = w85.b1_distance(population)
    q20_cut, q30_cut = np.quantile(distances, [.2, .3])
    paths = data["paths"]
    rows = []
    spec_map = {s.run_id: s for s in specs}
    for (run_id, arm), g in paths.groupby(["run_id", "path"]):
        spec = spec_map[run_id]
        indices = g.sort_values("query_order").population_row_index.astype(int).to_numpy()
        scaler = __import__("sklearn.preprocessing", fromlist=["StandardScaler"]).StandardScaler().fit(population.loc[spec.train_indices, engine.FEATURES])
        xs = scaler.transform(population.loc[indices, engine.FEATURES])
        for budget in (24, 40, 60, 80):
            active = indices[16:budget]
            pair = pairwise_distances(xs[:budget])
            tri = pair[np.triu_indices(budget, 1)]
            nearest = [float(np.min(pair[i, :i])) for i in range(16, budget)]
            rows.append({"run_id": run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": arm, "budget": budget,
                         "active_keyhole_fraction": float(labels[active].mean()), "cumulative_revealed_keyhole_fraction": float(labels[indices[:budget]].mean()),
                         "q20_like_query_fraction": float((distances[active] <= q20_cut).mean()), "q30_like_query_fraction": float((distances[active] <= q30_cut).mean()),
                         "mean_B1_distance": float(distances[active].mean()), "mean_nearest_previous_standardized_distance": float(np.mean(nearest)),
                         "mean_pairwise_spread": float(tri.mean())})
    return pd.DataFrame(rows)


def mechanism(candidate_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run_id, budget), g in candidate_scores.groupby(["run_id", "budget"]):
        p1 = g[g.arm.eq(P1)][["candidate_population_row_index", "sur_score"]].rename(columns={"sur_score": "P1"})
        p2 = g[g.arm.eq(P2)][["candidate_population_row_index", "sur_score"]].rename(columns={"sur_score": "P2"})
        common = p1.merge(p2, on="candidate_population_row_index")
        require(len(common) >= 2, f"common candidates {run_id}/B{budget}")
        top1_p1 = int(common.loc[common.P1.idxmax(), "candidate_population_row_index"])
        top1_p2 = int(common.loc[common.P2.idxmax(), "candidate_population_row_index"])
        top5_p1 = set(common.nlargest(5, "P1").candidate_population_row_index)
        top5_p2 = set(common.nlargest(5, "P2").candidate_population_row_index)
        rows.append({"run_id": run_id, "budget": budget, "common_candidate_count": len(common),
                     "score_spearman": float(spearmanr(common.P1, common.P2).statistic), "top1_agreement": top1_p1 == top1_p2,
                     "top5_jaccard": len(top5_p1 & top5_p2) / len(top5_p1 | top5_p2)})
    return pd.DataFrame(rows)


def global_uncertainty_summary(candidate_scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    new = candidate_scores.assign(point_uncertainty=lambda d: d.candidate_probability * (1 - d.candidate_probability))
    new = new.groupby(["run_id", "arm", "budget"], as_index=False).point_uncertainty.mean().rename(columns={"point_uncertainty": "global_uncertainty"})
    historical_path = ROOT / "outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit/candidate_scores_pre_reveal.csv.gz"
    old = pd.read_csv(historical_path, usecols=["run_id", "repeat", "budget", "m3_probability"])
    old["global_uncertainty"] = old.m3_probability * (1 - old.m3_probability)
    old = old.groupby(["run_id", "budget"], as_index=False).global_uncertainty.mean(); old["arm"] = P0
    detail = pd.concat([old[["run_id", "arm", "budget", "global_uncertainty"]], new], ignore_index=True)
    detail["repeat"] = detail.run_id.str.extract(r"__r(\d+)_")[0].astype(int)
    rows = []
    for (arm, budget), g in detail.groupby(["arm", "budget"]):
        values = g.groupby("repeat").global_uncertainty.mean().sort_index()
        mean, lo, hi = summary_ci(values, f"global-uncertainty|{arm}|{budget}")
        rows.append({"arm": arm, "budget": budget, "mean_global_uncertainty": mean, "ci_lower": lo, "ci_upper": hi,
                     "source": "Phase 1.18A published M3-margin snapshots" if arm == P0 else "new prospective path"})
    return detail, pd.DataFrame(rows)


def runtime_summary(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_rows = []
    for r in data["runtime"].itertuples(index=False):
        raw_rows.append({"arm": r.arm, "run_id": r.run_id, "level": "full_sequential_run", "seconds": r.run_seconds})
    for r in data["surdiag"].itertuples(index=False):
        raw_rows.append({"arm": r.arm, "run_id": r.run_id, "budget": r.budget, "level": "candidate_scoring_step", "seconds": r.candidate_scoring_seconds})
    fits = data["fits"][data["fits"].arm.isin((P1, P2)) & data["fits"].current_fit_seconds.notna()]
    for r in fits.itertuples(index=False):
        raw_rows.append({"arm": r.arm, "run_id": r.run_id, "budget": r.budget, "level": "current_M3_fit", "seconds": r.current_fit_seconds})
    raw = pd.DataFrame(raw_rows)
    summary = raw.groupby(["arm", "level"], as_index=False).seconds.agg(mean="mean", median="median", q90=lambda x: x.quantile(.9), count="size")
    return raw, summary


def sample_efficiency(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    detail = []
    for keys, g in metrics[metrics.subset.eq("B1_q20")].groupby(["run_id", "repeat", "fold", "model"]):
        run_id, repeat, fold, model = keys
        g = g.sort_values("budget")
        for threshold in (.80, .82, .84):
            hit = g[g.accuracy.ge(threshold)].budget
            detail.append({"run_id": run_id, "repeat": repeat, "fold": fold, "model": model, "threshold": threshold,
                           "reached": bool(len(hit)), "first_hit_budget": float(hit.iloc[0]) if len(hit) else np.nan})
    detail = pd.DataFrame(detail)
    summary = detail.groupby(["model", "threshold"], as_index=False).agg(n_runs=("run_id", "size"), reached_count=("reached", "sum"),
        reached_fraction=("reached", "mean"), median_first_hit_budget_reached_only=("first_hit_budget", "median"))
    rows, supported = [], False
    for threshold in (.80, .82, .84):
        wide = detail[detail.threshold.eq(threshold)].pivot(index=["run_id", "repeat", "fold"], columns="model", values="first_hit_budget").reset_index()
        for model in (P1, P2):
            common = wide[[P0, model]].notna().all(axis=1)
            pairs = wide[common].copy()
            pairs["difference"] = pairs[model] - pairs[P0]  # negative = fewer labels
            by_repeat = pairs.groupby("repeat").difference.mean().reindex(range(1, 21))
            if by_repeat.notna().all():
                mean, median, lo, hi = bootstrap(by_repeat.to_numpy(), f"threshold|{threshold}|{model}-{P0}")
            else:
                mean = float(pairs.difference.mean()) if len(pairs) else np.nan
                median = float(pairs.difference.median()) if len(pairs) else np.nan
                lo = hi = np.nan
            rows.append({"threshold": threshold, "contrast": f"{model}-{P0}", "sign_convention": "SUR minus Margin; negative means fewer labels",
                         "common_attained_runs": len(pairs), "mean_label_difference": mean, "median_label_difference": median,
                         "ci_lower": lo, "ci_upper": hi})
            p0_attain = float(summary[(summary.model.eq(P0)) & summary.threshold.eq(threshold)].reached_fraction.iloc[0])
            model_attain = float(summary[(summary.model.eq(model)) & summary.threshold.eq(threshold)].reached_fraction.iloc[0])
            supported |= model == P1 and np.isfinite(hi) and hi < 0 and model_attain >= p0_attain
    return summary, pd.DataFrame(rows), {"decision": "LABEL_SAVING_SUPPORTED" if supported else "LABEL_SAVING_NOT_SUPPORTED"}


def decisions(primary: pd.DataFrame, multiplicity: pd.DataFrame, full: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    p1 = primary[primary.contrast.eq(f"{P1}-{P0}")].iloc[0]
    p2p0 = primary[primary.contrast.eq(f"{P2}-{P0}")].iloc[0]
    p2p1 = primary[primary.contrast.eq(f"{P2}-{P1}")].iloc[0]
    holm = bool(multiplicity[multiplicity.contrast.eq(f"{P1}-{P0}")]["supported_at_0.05"].iloc[0])
    gross = full[(full.budget.isin((40, 80))) & full.metric.isin(("accuracy", "keyhole_recall"))]
    # Mean deterioration threshold is a guardrail, not an endpoint.
    pivot = gross.pivot_table(index=["budget", "metric"], columns="model", values="mean")
    catastrophic = bool(((pivot[P1] - pivot[P0]) <= -.05).any())
    if p1.mean_difference > 0 and p1.ci_lower > 0 and holm and not catastrophic:
        main = "GLOBAL_SUR_GAIN_SUPPORTED"
    elif p1.mean_difference > 0:
        main = "GLOBAL_SUR_GAIN_UNRESOLVED"
    elif p1.ci_upper < 0:
        main = "GLOBAL_SUR_HARM"
    else:
        main = "GLOBAL_SUR_NO_GAIN"
    if p2p0.ci_lower > 0 and p2p1.ci_lower > 0:
        secondary = "PHYSICS_REFIT_SUR_ADDS_GAIN"
    elif p2p1.ci_upper < 0 and p2p0.ci_upper < 0:
        secondary = "PHYSICS_REFIT_SUR_HARM"
    else:
        secondary = "PHYSICS_REFIT_SUR_CHANGES_PATH_ONLY"
    return {"decision": main, "catastrophic_fullheldout_degradation": catastrophic}, {"decision": secondary}


def figures(curves: pd.DataFrame, primary: pd.DataFrame, threshold: pd.DataFrame, overlap: pd.DataFrame,
            global_uncertainty: pd.DataFrame, mechanism_df: pd.DataFrame, repeat_q20: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    files = []
    colors = {P0: "#444444", P1: "#0072B2", P2: "#D55E00"}
    def save(name: str) -> None:
        path = FIGURES / name
        plt.tight_layout(); plt.savefig(path, dpi=180, bbox_inches="tight"); plt.close(); files.append(path)
    for metric, name, ylabel in (("accuracy", "01_q20_accuracy_learning_curves.png", "Fold-B1-q20 accuracy"),
                                  ("keyhole_recall", "03_q20_keyhole_recall.png", "Fold-B1-q20 Keyhole recall")):
        fig, ax = plt.subplots(figsize=(8, 4.8))
        g = curves[(curves.subset.eq("B1_q20")) & curves.metric.eq(metric)]
        for model in MODELS:
            m = g[g.model.eq(model)]
            x = m.budget.to_numpy(float); y = m["mean"].to_numpy(float); lo = m.ci_lower.to_numpy(float); hi = m.ci_upper.to_numpy(float)
            ax.plot(x, y, label=model, color=colors[model]); ax.fill_between(x, lo, hi, color=colors[model], alpha=.13)
        ax.set(xlabel="Revealed simulations", ylabel=ylabel); ax.legend(fontsize=8); save(name)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    repeat_wide = repeat_q20.pivot(index="repeat", columns="model", values="accuracy_AULC_16_80")
    labels, means, los, his = [], [], [], []
    for contrast in (f"{P1}-{P0}", f"{P2}-{P0}", f"{P2}-{P1}"):
        r = primary[primary.contrast.eq(contrast)].iloc[0]; labels.append(contrast); means.append(r.mean_difference); los.append(r.ci_lower); his.append(r.ci_upper)
    ax.errorbar(means, range(3), xerr=[np.asarray(means)-np.asarray(los), np.asarray(his)-np.asarray(means)], fmt="o", capsize=4)
    ax.axvline(0, color="black", lw=1); ax.set(yticks=range(3), yticklabels=labels, xlabel="Matched q20 AULC difference"); save("02_paired_q20_aulc_contrasts.png")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for model in MODELS:
        g = threshold[threshold.model.eq(model)]; ax.plot(g.threshold, g.reached_fraction, marker="o", label=model, color=colors[model])
    ax.set(xlabel="q20 accuracy threshold", ylabel="Attainment fraction", ylim=(0, 1.03)); ax.legend(fontsize=8); save("04_sample_efficiency_thresholds.png")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for comparison, g in overlap.groupby("comparison"):
        ax.plot(g.budget, g.mean_jaccard, marker="o", label=comparison)
    ax.set(xlabel="Budget", ylabel="Mean revealed-set Jaccard", ylim=(0, 1.03)); ax.legend(fontsize=8); save("05_path_overlap.png")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for arm, g in global_uncertainty.groupby("arm"):
        ax.plot(g.budget, g.mean_global_uncertainty, marker="o" if arm == P0 else None, label=arm, color=colors[arm])
    ax.set(xlabel="Budget before query", ylabel="Mean candidate-pool p(1-p)"); ax.legend(fontsize=8); save("06_global_sur_evolution.png")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    mechanism_df.groupby("budget").score_spearman.median().plot(ax=axes[0]); axes[0].set(xlabel="Budget", ylabel="Median P1/P2 score Spearman")
    mechanism_df.groupby("budget").top1_agreement.mean().plot(ax=axes[1]); axes[1].set(xlabel="Budget", ylabel="P1/P2 top-1 agreement", ylim=(0, 1))
    save("07_physics_refit_mechanism.png")
    manifest = pd.DataFrame([{"figure": p.name, "sha256": sha256_file(p), "size_bytes": p.stat().st_size} for p in files])
    engine.write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return manifest


def build_notebook() -> None:
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.18B — Prospective finite-pool GPC-SUR\n\nThis notebook reads the frozen artifacts. It does not rerun the expensive 200 prospective trajectories."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_18b_prospective_global_gpc_sur_benchmark'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 1. Three frozen arms\n\nP0 is published M3 probability margin. P1 uses exact enlarged-data Laplace inference while holding the physics mean and Stage-2 kernel fixed. P2 refits only the data-fitted physics mean inside each hypothetical outcome."),
        nbf.v4.new_code_cell("display(Markdown((OUT/'sur_protocol.md').read_text()))"),
        nbf.v4.new_markdown_cell("## 2. Primary q20 result"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'q20_primary_contrasts.csv')); display(Image(filename=str(OUT/'figures'/'01_q20_accuracy_learning_curves.png'))); display(Image(filename=str(OUT/'figures'/'02_paired_q20_aulc_contrasts.png')))"),
        nbf.v4.new_markdown_cell("## 3. Budget regions and B40 Keyhole behavior"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'q20_budget_region_contrasts.csv')); display(pd.read_csv(OUT/'b40_keyhole_diagnostics.csv')); display(Image(filename=str(OUT/'figures'/'03_q20_keyhole_recall.png')))"),
        nbf.v4.new_markdown_cell("## 4. Sample efficiency and paths"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'sample_efficiency_thresholds.csv')); display(pd.read_csv(OUT/'sample_efficiency_contrasts.csv')); display(Image(filename=str(OUT/'figures'/'04_sample_efficiency_thresholds.png'))); display(Image(filename=str(OUT/'figures'/'05_path_overlap.png')))"),
        nbf.v4.new_markdown_cell("## 5. Global uncertainty and physics-refit mechanism"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'sur_numerical_diagnostics.csv')); display(pd.read_csv(OUT/'physics_refit_mechanism.csv')); display(Image(filename=str(OUT/'figures'/'06_global_sur_evolution.png'))); display(Image(filename=str(OUT/'figures'/'07_physics_refit_mechanism.png')))"),
        nbf.v4.new_markdown_cell("## 6. Safe conclusion"),
        nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_18B_ONE_PAGE.md').read_text()))"),
    ]
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Thesis Python", "language": "python", "name": "thesis"}})
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True); nbf.write(nb, NOTEBOOK)
    executed = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=180, kernel_name="thesis", resources={"metadata": {"path": str(ROOT)}}).execute()
    nbf.write(executed, NOTEBOOK)


def write_reports(outputs: dict[str, Any]) -> None:
    primary, region, checkpoints, q30, thresholds, thresh_contrasts, overlap, active, numerical, mechanism_df, runtime, main_dec, phys_dec, label_dec = (outputs[k] for k in ("primary", "region", "checkpoints", "q30", "thresholds", "threshold_contrasts", "overlap", "active", "numerical", "mechanism", "runtime", "main_decision", "physics_decision", "label_decision"))
    aulc = outputs["aulc_summary"].set_index("model").mean_AULC
    p1 = primary[primary.contrast.eq(f"{P1}-{P0}")].iloc[0]; p2 = primary[primary.contrast.eq(f"{P2}-{P0}")].iloc[0]
    p2p1 = primary[primary.contrast.eq(f"{P2}-{P1}")].iloc[0]
    b40 = outputs["b40"]
    fallback = int(numerical.fallback_count.sum()); failures = int(numerical.hypothetical_failures.sum())
    q30p1 = q30[q30.contrast.eq(f"{P1}-{P0}")].iloc[0]
    holm = outputs["multiplicity"].set_index("contrast")
    b40_kh = b40[b40.metric.eq("keyhole_recall")].set_index("model")["mean"]
    b40_ba = b40[b40.metric.eq("balanced_accuracy")].set_index("model")["mean"]
    region_p1 = region[region.contrast.eq(f"{P1}-{P0}")].set_index("region")
    p1p0_b80 = overlap[(overlap.comparison.eq(f"{P1}-{P0}")) & overlap.budget.eq(80)].iloc[0]
    p2p1_b80 = overlap[(overlap.comparison.eq(f"{P2}-{P1}")) & overlap.budget.eq(80)].iloc[0]
    global_u = outputs["global_uncertainty"]
    common_budgets = sorted(set(global_u[global_u.arm.eq(P0)].budget) & set(global_u[global_u.arm.eq(P1)].budget))
    gu = global_u[global_u.budget.isin(common_budgets)].pivot(index="budget", columns="arm", values="mean_global_uncertainty")
    mech_spearman = float(mechanism_df.score_spearman.median()); mech_top1 = float(mechanism_df.top1_agreement.mean()); mech_top5 = float(mechanism_df.top5_jaccard.mean())
    runtime_index = runtime.set_index(["arm", "level"])
    p1_runtime = runtime_index.loc[(P1, "full_sequential_run")]
    p2_runtime = runtime_index.loc[(P2, "full_sequential_run")]
    report = f"""# Final Phase 1.18B report

## Design
All 100 frozen outer runs used the same feature-only B16 design. P0 is the exact published Phase 1.14 M3-margin path. P1 is exact-fixed finite-pool GPC-SUR. P2 refits the revealed-label-fitted physics mean inside each hypothetical outcome while retaining the current Stage-2 kernel.

## Primary q20 AULC

| Arm | Mean AULC |
|---|---:|
| P0 M3 Margin | {aulc[P0]:.9f} |
| P1 exact-fixed SUR | {aulc[P1]:.9f} |
| P2 physics-refit SUR | {aulc[P2]:.9f} |

P1−P0 = **{p1.mean_difference:+.9f}**, repeat-block 95% CI **[{p1.ci_lower:+.9f}, {p1.ci_upper:+.9f}]**. P2−P0 = **{p2.mean_difference:+.9f}**, CI **[{p2.ci_lower:+.9f}, {p2.ci_upper:+.9f}]**. Holm adjustment is reported in `multiplicity_adjustment.csv`.

Primary decision: **{main_dec['decision']}**. Physics-refit decision: **{phys_dec['decision']}**. Label-saving decision: **{label_dec['decision']}**.

## Predeclared secondary checks

- EARLY/MID/LATE P1−P0 q20 contrasts: {region_p1.loc['EARLY_B16_24'].mean_difference:+.6f}, {region_p1.loc['MID_B25_40'].mean_difference:+.6f}, {region_p1.loc['LATE_B41_80'].mean_difference:+.6f}.
- B40 q20 Keyhole recall P0/P1/P2: {b40_kh[P0]:.6f} / {b40_kh[P1]:.6f} / {b40_kh[P2]:.6f}; balanced accuracy: {b40_ba[P0]:.6f} / {b40_ba[P1]:.6f} / {b40_ba[P2]:.6f}.
- q30 AULC P1−P0: {q30p1.mean_difference:+.6f}, CI [{q30p1.ci_lower:+.6f}, {q30p1.ci_upper:+.6f}]. q30 remains secondary.
- B80 revealed-set Jaccard P1/P0: {p1p0_b80.mean_jaccard:.4f}; P2/P1: {p2p1_b80.mean_jaccard:.4f}.
- P1/P2 common-candidate score median Spearman: {mech_spearman:.4f}; top-1 agreement: {mech_top1:.4f}; mean top-5 Jaccard: {mech_top5:.4f}.
- Mean P1−P0 global candidate-pool uncertainty at common checkpoints: {(gu[P1]-gu[P0]).mean():+.6e}.
- Observed median full-run time P1/P2: {p1_runtime['median']:.2f} s / {p2_runtime['median']:.2f} s.

## Mechanism and robustness
There were {failures} failed hypothetical solves and {fallback} deterministic increased-iteration fallbacks. Path divergence, early/mid/late effects, B40 Keyhole recall, q30, full-heldout behavior, threshold attainment, score scale, near ties, and actual runtime are all disclosed in the companion machine-readable tables.

## Claim boundary
This is one finite simulator pool and a one-step probability-uncertainty SUR functional. It is not an exact implementation of a particular random-set SUR paper, does not prove theoretical sample complexity, and does not support universal label savings unless the predeclared threshold analysis says so.
"""
    (OUTPUT / "FINAL_PHASE1_18B_REPORT.md").write_text(report, encoding="utf-8")
    supervisor = f"""# Supervisor one-page — Phase 1.18B

- **Question:** Does global finite-pool predictive-uncertainty reduction beat local M3 probability margin?
- **P0 / P1 / P2 q20 AULC:** {aulc[P0]:.6f} / {aulc[P1]:.6f} / {aulc[P2]:.6f}.
- **Primary P1−P0:** {p1.mean_difference:+.6f}, 95% repeat-block CI [{p1.ci_lower:+.6f}, {p1.ci_upper:+.6f}].
- **Physics-refit P2−P0:** {p2.mean_difference:+.6f}, CI [{p2.ci_lower:+.6f}, {p2.ci_upper:+.6f}].
- **P2−P1:** {p2p1.mean_difference:+.6f}, CI [{p2p1.ci_lower:+.6f}, {p2p1.ci_upper:+.6f}].
- **Holm-adjusted primary p-values:** P1−P0 {holm.loc[f'{P1}-{P0}', 'holm_adjusted_p']:.6g}; P2−P0 {holm.loc[f'{P2}-{P0}', 'holm_adjusted_p']:.6g}.
- **B40 q20 Keyhole recall:** P0/P1/P2 = {b40_kh[P0]:.4f}/{b40_kh[P1]:.4f}/{b40_kh[P2]:.4f}.
- **Decisions:** `{main_dec['decision']}`; `{phys_dec['decision']}`; `{label_dec['decision']}`.
- **Numerics:** {failures} failed hypothetical solves; {fallback} disclosed deterministic retries.
- **Safe interpretation:** the benchmark isolates the acquisition path under the same M3 evaluator. q30, individual budgets, and path diversity cannot override the q20 primary result.
- **Stopping rule:** this closes the planned Week 9 acquisition search unless validation exposes an implementation error.
"""
    (OUTPUT / "SUPERVISOR_PHASE1_18B_ONE_PAGE.md").write_text(supervisor, encoding="utf-8")
    ledger = f"""# Phase 1.18B claim ledger

| Claim | Status | Basis |
|---|---|---|
| Exact-fixed global SUR improves overall q20 AULC over M3 Margin. | {'SUPPORTED' if main_dec['decision']=='GLOBAL_SUR_GAIN_SUPPORTED' else 'NOT SUPPORTED'} | Predeclared paired q20 endpoint and Holm family. |
| Physics refitting adds performance beyond exact-fixed SUR. | {'SUPPORTED' if phys_dec['decision']=='PHYSICS_REFIT_SUR_ADDS_GAIN' else 'NOT SUPPORTED'} | P2−P0 and P2−P1. |
| Physics refitting changes the acquisition path. | QUALIFIED | Score/rank and path diagnostics. |
| SUR saves labels. | {'SUPPORTED' if label_dec['decision']=='LABEL_SAVING_SUPPORTED' else 'NOT SUPPORTED'} | Predeclared thresholds; negative SUR−Margin means fewer labels. |
| q30 can overturn q20. | NOT SUPPORTED | q30 is secondary. |
| This is an exact Menz/random-set SUR implementation. | NOT SUPPORTED | Probability-uncertainty finite-pool functional. |
| SUR or physics-informed acquisition is novel. | NOT TESTED | No novelty claim. |
| ARD lengths are causal importance. | NOT SUPPORTED | Numerical geometry only. |
| Universal active-learning superiority. | NOT SUPPORTED | One frozen simulator pool. |
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger, encoding="utf-8")
    red = f"""# Final red-team report

1. P1 overall q20 AULC effect: {p1.mean_difference:+.9f}.
2. Paired CI excludes zero: {bool(p1.ci_lower > 0 or p1.ci_upper < 0)}; interval [{p1.ci_lower:+.9f}, {p1.ci_upper:+.9f}].
3. Holm survives at 0.05: {bool(holm.loc[f'{P1}-{P0}', 'supported_at_0.05'])}.
4. EARLY/MID/LATE effects: {region_p1.loc['EARLY_B16_24'].mean_difference:+.6f} / {region_p1.loc['MID_B25_40'].mean_difference:+.6f} / {region_p1.loc['LATE_B41_80'].mean_difference:+.6f}.
5. B40 q20 Keyhole recall P1−P0: {b40_kh[P1]-b40_kh[P0]:+.6f}.
6. B40 active-query Keyhole fractions are disclosed in `b40_keyhole_diagnostics.csv`; they are retrospective.
7. B80 P1/P0 Jaccard: {p1p0_b80.mean_jaccard:.4f}; diversity alone is not called beneficial.
8. Mean P1−P0 global p(1-p) difference at common checkpoints: {(gu[P1]-gu[P0]).mean():+.6e}.
9. Whether global uncertainty translates to q20 is adjudicated only by the primary contrast above.
10. Mean near-tied fractions P1/P2: {numerical.groupby('arm').mean_near_tied_fraction.mean()[P1]:.6f}/{numerical.groupby('arm').mean_near_tied_fraction.mean()[P2]:.6f}.
11. Tie break is deterministic smallest population-row index; no candidate was changed post hoc.
12. Threshold results are in `sample_efficiency_contrasts.csv`.
13. Label-saving decision: {label_dec['decision']}.
14. Full-heldout B40/B80 values are in `fullheldout_diagnostics.csv`; catastrophic guardrail: {main_dec['catastrophic_fullheldout_degradation']}.
15. P2−P1 q20 effect: {p2p1.mean_difference:+.6f}, CI [{p2p1.ci_lower:+.6f}, {p2p1.ci_upper:+.6f}].
16. Physics-refit performance decision: {phys_dec['decision']}.
17. P1/P2 score median Spearman {mech_spearman:.4f}, top-1 {mech_top1:.4f}, top-5 Jaccard {mech_top5:.4f}.
18. Median full-run seconds P1/P2: {p1_runtime['median']:.2f}/{p2_runtime['median']:.2f}; cost is disclosed, not extrapolated.
19. Kernel/ARD numerical diagnostics are in `model_fit_diagnostics.csv.gz`; ARD is not interpreted causally.
20. Primary acquisition decision: {main_dec['decision']}.
21. Per the frozen stopping rule, acquisition development stops after this validated benchmark.
22. Narrow claim: see `claim_ledger.md`; no novelty, universal superiority, exact-paper equivalence, or unsupported label saving is claimed.

The audit also attacked future-label leakage, q20/q30/B1 leakage, off-by-one prefixes, candidate-pool drift, P0 reconstruction, hypothetical outcome weighting, P1 parameter drift, P2 kernel drift, FAST fallback, fold pseudo-replication, AULC orientation, and multiplicity. Retrospective B1/query-label diagnostics were computed only after paths were frozen.
"""
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text(red, encoding="utf-8")


def validate(data: dict[str, pd.DataFrame], outputs: dict[str, Any], figures_df: pd.DataFrame) -> dict[str, Any]:
    population, specs, a0 = engine.load_inputs(); paths = data["paths"]; pred = data["predictions"]; metrics = data["metrics"]
    source = (ROOT / "src" / "week9_phase1_18b_prospective_global_gpc_sur_benchmark.py").read_text(encoding="utf-8")
    execution_source = source[source.index("@dataclass"):source.index("def main()")]
    path_map = {(r, p): g.sort_values("query_order").population_row_index.astype(int).tolist() for (r, p), g in paths.groupby(["run_id", "path"])}
    p0_ref = engine.p0_paths(); notebook = nbf.read(NOTEBOOK, as_version=4); code = [c for c in notebook.cells if c.cell_type == "code"]
    primary = outputs["primary"]; mult = outputs["multiplicity"]
    checks = [
        ("exact_parent_sha", subprocess.check_output(["git", "merge-base", "HEAD", engine.START_SHA], cwd=ROOT, text=True).strip() == engine.START_SHA, engine.START_SHA),
        ("population_405_73_332", (len(population), int(population.has_keyhole.sum())) == (405, 73), "405/73/332"),
        ("exact_100_outer_runs", len(specs) == 100, str(len(specs))),
        ("exact_20x5", len(set(s.repeat for s in specs)) == 20 and all(sum(x.repeat == r for x in specs) == 5 for r in range(1, 21)), "20x5"),
        ("same_folds_all_arms", pred.groupby("model").run_id.nunique().eq(100).all(), "100 each"),
        ("same_B16_initialization", all(path_map[(s.run_id, m)][:16] == a0[s.run_id][:16] for s in specs for m in MODELS), "300/300"),
        ("P0_path_exact", all(path_map[(r, P0)] == p0_ref[r] for r in p0_ref), "100/100"),
        ("P0_metric_exact", abs(outputs["aulc_summary"].set_index("model").loc[P0, "mean_AULC"] - .8446231617647059) < 1e-12, "published q20"),
        ("no_duplicate_queries", all(len(v) == len(set(v)) == 80 for v in path_map.values()), "300 paths"),
        ("training_pool_only", all(set(path_map[(s.run_id, m)]).issubset(s.train_indices) for s in specs for m in MODELS), "all"),
        ("heldout_never_queried", all(set(path_map[(s.run_id, m)]).isdisjoint(s.test_indices) for s in specs for m in MODELS), "all"),
        ("no_q20_q30_B1_acquisition", "flags = p17.subset_flags" in source and "score_candidates(fit, x4, logh, labels, revealed, candidates" in source, "flags evaluation-only"),
        ("hypothetical_both_labels", "for outcome in (0, 1)" in source, "y0/y1"),
        ("current_posterior_weighting", "(1.0 - current_p[j]) * u0 + current_p[j] * u1" in source, "exact"),
        ("current_U_uses_complete_Rn", "current_u_global = float(np.mean(current_p * (1.0 - current_p)))" in source, "complete current pool"),
        ("future_U_excludes_candidate", "reference = np.delete(candidates, j)" in source, "remaining pool"),
        ("common_current_U_n", data["candidates"].groupby(["run_id", "budget", "arm"]).current_global_uncertainty.nunique().eq(1).all(), "common over R_n"),
        ("P1_physics_fixed", "physics = current.physics" in source, "exact-fixed"),
        ("P1_physics_numeric_freeze", np.allclose(data["candidates"].query("arm == @P1").current_physics_slope, data["candidates"].query("arm == @P1").physics_slope_y0) and np.allclose(data["candidates"].query("arm == @P1").current_physics_slope, data["candidates"].query("arm == @P1").physics_slope_y1), "all candidates/outcomes"),
        ("P1_scaler_fixed", "current.x_scaler.transform" in source, "fixed"),
        ("P1_P2_kernel_fixed", "FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False" in source, "fixed current kernel"),
        ("P2_physics_refit", "fit_physics_mean(logh, lab, enlarged" in source, "revealed+hypothetical"),
        ("P2_physics_numeric_change", ((data["candidates"].query("arm == @P2").physics_slope_y0 - data["candidates"].query("arm == @P2").current_physics_slope).abs() > 1e-12).any(), "observed"),
        ("normal_actual_next_fit", "p13.fit_hybrid(x4, logh, labels, revealed, train, physics, \"M3\", 100.0)" in source, "normal M3"),
        ("FAST_never_used", "FAST_RANK1" not in execution_source, "absent from execution engine"),
        ("PA_TVR_never_used", "PA-TVR" not in execution_source and "PA_TVR" not in execution_source, "absent from execution engine"),
        ("no_acquisition_tuning", json.loads((OUTPUT / "analysis_specification.json").read_text())["status"] == "FROZEN_BEFORE_NEW_RESULTS", "frozen"),
        ("deterministic_tie_break", "np.lexsort((candidates, -scores))" in source, "smallest index"),
        ("primary_q20_unchanged", set(outputs["q20_outer"].subset) == {"B1_q20"}, "q20"),
        ("repeat_block_inference", all(primary.bootstrap_draws == engine.BOOTSTRAP_DRAWS), "20 blocks"),
        ("bootstrap_at_least_10000", engine.BOOTSTRAP_DRAWS >= 10_000, str(engine.BOOTSTRAP_DRAWS)),
        ("Holm_two_primary", len(mult) == 2 and set(mult.contrast) == {f"{P1}-{P0}", f"{P2}-{P0}"}, "2"),
        ("q30_secondary", len(outputs["q30"]) == 3, "secondary contrasts"),
        ("threshold_sign_explicit", outputs["threshold_contrasts"].sign_convention.str.contains("negative means fewer").all(), "explicit"),
        ("fallback_disclosed", "fallback_count" in data["surdiag"].columns, str(int(data["surdiag"].fallback_count.sum()))),
        ("all_scores_finite", np.isfinite(data["candidates"].sur_score).all(), str(len(data["candidates"]))),
        ("selected_truth_revealed_after", data["queries"].unrevealed_labels_available_to_acquisition.eq(False).all(), "explicit"),
        ("P0_B16_probability_equal", np.allclose(pred[pred.model.eq(P0) & pred.budget.eq(16)].sort_values(["run_id", "population_row_index"]).probability,
                                                   pred[pred.model.eq(P1) & pred.budget.eq(16)].sort_values(["run_id", "population_row_index"]).probability, atol=1e-12, rtol=0), "P0=P1"),
        ("P1_P2_B16_probability_equal", np.allclose(pred[pred.model.eq(P1) & pred.budget.eq(16)].sort_values(["run_id", "population_row_index"]).probability,
                                                      pred[pred.model.eq(P2) & pred.budget.eq(16)].sort_values(["run_id", "population_row_index"]).probability, atol=1e-12, rtol=0), "P1=P2"),
        ("notebook_executed", all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs", []) if o.get("output_type") == "error"], str(len(code))),
        ("figure_hashes", len(figures_df) <= 7 and all(sha256_file(FIGURES / r.figure) == r.sha256 for r in figures_df.itertuples()), str(len(figures_df))),
        ("historical_outputs_unchanged", engine.historical_changes() == [], str(engine.historical_changes())),
        ("no_novelty_claim", "sur is novel" not in (OUTPUT / "FINAL_PHASE1_18B_REPORT.md").read_text().lower(), "safe"),
        ("label_saving_claim_guarded", outputs["label_decision"]["decision"] in {"LABEL_SAVING_SUPPORTED", "LABEL_SAVING_NOT_SUPPORTED"}, outputs["label_decision"]["decision"]),
    ]
    records = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    payload = {"status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL", "check_count": len(records),
               "passed": sum(r["status"] == "PASS" for r in records), "checks": records}
    engine.write_json(OUTPUT / "validation_report.json", payload)
    lines = ["# Phase 1.18B validation", "", f"Status: **{payload['status']}**", f"Checks: **{payload['passed']} / {payload['check_count']} PASS**", "", "| Check | Status | Detail |", "|---|---|---|"] + [f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]
    (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    require(payload["status"] == "PASS", "validation failed")
    return payload


def finalize() -> dict[str, Any]:
    engine.preflight(); data = collect()
    population, specs, a0 = engine.load_inputs()
    path_lookup = {(run_id, path): group.sort_values("query_order").population_row_index.astype(int).tolist()
                   for (run_id, path), group in data["paths"].groupby(["run_id", "path"])}
    engine.write_json(OUTPUT / "initial_design_audit.json", {"status": "PASS", "runs": 100, "size": 16, "feature_only": True,
        "all_arms_identical": all(len({tuple(path_lookup[(s.run_id, model)][:16]) for model in MODELS}) == 1 for s in specs)})
    (OUTPUT / "sur_protocol.md").write_text("# Frozen SUR protocol\n\nFor each unqueried outer-training candidate, both hypothetical labels are integrated with its current M3 probability. The current U_n is the common mean p(1-p) over the complete unqueried pool R_n. Each hypothetical future uncertainty is the mean over the remaining pool R_n minus the candidate. P1 freezes the physics mean, outer-pool scaler, and Stage-2 kernel. P2 refits only the revealed-label-fitted physics mean under each hypothetical outcome and freezes the Stage-2 kernel. The actual next-budget M3 model is normally refit. Ties are resolved by smallest population-row index. No hidden label, held-out label, B1, q20, or q30 enters selection.\n", encoding="utf-8")
    q20_outer, q20_repeat = aulc_table(data["metrics"], "B1_q20"); q30_outer, q30_repeat = aulc_table(data["metrics"], "B1_q30")
    primary, mult = contrasts(q20_repeat, "B1_q20"); q30, _ = contrasts(q30_repeat, "B1_q30")
    region = region_contrasts(data["metrics"]); checkpoints = checkpoint_metrics(data["metrics"]); curves = learning_curves(data["metrics"])
    path_detail, overlap = path_diagnostics(data["paths"]); active = active_query_diagnostics(data)
    mechanism_df = mechanism(data["candidates"]); global_detail, global_summary = global_uncertainty_summary(data["candidates"])
    thresholds, threshold_contrasts, label_dec = sample_efficiency(data["metrics"])
    aulc_summary = q20_repeat.groupby("model", as_index=False).accuracy_AULC_16_80.mean().rename(columns={"accuracy_AULC_16_80": "mean_AULC"})
    full = checkpoints[(checkpoints.subset.eq("full81")) & checkpoints.budget.isin((40, 80))]
    main_dec, phys_dec = decisions(primary, mult, full)
    b40_metrics = checkpoints[(checkpoints.budget.eq(40)) & checkpoints.subset.eq("B1_q20") & checkpoints.metric.isin(("keyhole_recall", "balanced_accuracy"))]
    b40_active = active[active.budget.eq(40)].groupby("arm", as_index=False)[["active_keyhole_fraction", "cumulative_revealed_keyhole_fraction"]].mean().rename(columns={"arm": "model"})
    b40 = b40_metrics.merge(b40_active, on="model", how="left")
    numerical = data["surdiag"].groupby(["arm", "budget"], as_index=False).agg(candidate_count=("candidate_count", "mean"), hypothetical_failures=("hypothetical_failures", "sum"), fallback_count=("fallback_count", "sum"),
        constant_score_events=("constant_score_event", "sum"), median_score_range=("score_range", "median"), median_top1_top2_gap=("top1_top2_gap", "median"), mean_near_tied_fraction=("near_tied_fraction", "mean"), mean_scoring_seconds=("candidate_scoring_seconds", "mean"))
    fit_summary = data["fits"].groupby("arm", as_index=False).agg(
        optimizer_convergence_fraction=("optimizer_converged", "mean"),
        any_length_upper_bound_fraction=("any_length_upper_bound_hit", "mean"),
        any_length_lower_bound_fraction=("any_length_lower_bound_hit", "mean"),
        residual_sd_bound_fraction=("residual_sd_any_bound_hit", "mean"),
        median_posterior_iterations=("posterior_iterations", "median"), median_anisotropy_ratio=("anisotropy_ratio", "median"))
    physics_refit = data["selected"][data["selected"].arm.eq(P2)].copy()
    physics_refit["expected_intercept_change"] = (1 - physics_refit.candidate_probability) * (physics_refit.physics_intercept_y0 - physics_refit.current_physics_intercept) + physics_refit.candidate_probability * (physics_refit.physics_intercept_y1 - physics_refit.current_physics_intercept)
    physics_refit["expected_slope_change"] = (1 - physics_refit.candidate_probability) * (physics_refit.physics_slope_y0 - physics_refit.current_physics_slope) + physics_refit.candidate_probability * (physics_refit.physics_slope_y1 - physics_refit.current_physics_slope)
    runtime_raw, runtime = runtime_summary(data)
    outputs = dict(primary=primary, multiplicity=mult, region=region, checkpoints=checkpoints, curves=curves, q30=q30, thresholds=thresholds,
        threshold_contrasts=threshold_contrasts, label_decision=label_dec, overlap=overlap, active=active, numerical=numerical,
        mechanism=mechanism_df, global_uncertainty=global_summary, runtime=runtime, main_decision=main_dec, physics_decision=phys_dec, aulc_summary=aulc_summary,
        q20_outer=q20_outer, q20_repeat=q20_repeat, b40=b40)
    table_map = {
        "sequential_predictions.csv.gz": data["predictions"], "selected_queries.csv.gz": data["queries"],
        "sur_step_diagnostics.csv.gz": data["selected"],
        "physics_refit_step_diagnostics.csv.gz": physics_refit, "model_fit_diagnostics.csv.gz": data["fits"], "model_fit_summary.csv": fit_summary,
        "path_overlap_detail.csv.gz": path_detail, "path_overlap_summary.csv": overlap, "checkpoint_metrics.csv": checkpoints,
        "learning_curve_summary.csv": curves, "q20_aulc_by_run.csv": q20_outer, "q20_repeat_metrics.csv": q20_repeat,
        "q20_primary_contrasts.csv": primary, "q20_budget_region_contrasts.csv": region, "q30_aulc_contrasts.csv": q30,
        "b40_keyhole_diagnostics.csv": b40, "sample_efficiency_thresholds.csv": thresholds,
        "sample_efficiency_contrasts.csv": threshold_contrasts, "fullheldout_diagnostics.csv": full,
        "active_query_diagnostics.csv": active, "sur_numerical_diagnostics.csv": numerical,
        "multiplicity_adjustment.csv": mult, "physics_refit_mechanism.csv": mechanism_df, "runtime_summary.csv": runtime,
        "runtime_benchmark.csv.gz": runtime_raw, "global_uncertainty_by_run.csv.gz": global_detail,
        "global_uncertainty_summary.csv": global_summary,
        "model_aulc_summary.csv": aulc_summary,
    }
    for name, frame in table_map.items(): engine.write_csv(OUTPUT / name, frame)
    engine.write_json(OUTPUT / "primary_decision.json", main_dec); engine.write_json(OUTPUT / "physics_refit_decision.json", phys_dec); engine.write_json(OUTPUT / "sample_efficiency_decision.json", label_dec)
    figures_df = figures(curves, primary, thresholds, overlap, global_summary, mechanism_df, q20_repeat)
    write_reports(outputs); build_notebook(); validation = validate(data, outputs, figures_df)
    files = [p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name != "run_manifest.json"] + [ROOT / "src" / "week9_phase1_18b_prospective_global_gpc_sur_benchmark.py", Path(__file__), ROOT / "tests" / "test_week9_phase1_18b_prospective_global_gpc_sur_benchmark.py", NOTEBOOK]
    manifest = {"study": "Week 9 Phase 1.18B — Prospective Global GPC-SUR Active-Learning Benchmark", "parent_sha": engine.START_SHA,
        "branch": engine.BRANCH, "decisions": {"primary": main_dec, "physics_refit": phys_dec, "sample_efficiency": label_dec},
        "protocol": {"arms": list(MODELS), "outer_runs": 100, "repeat_blocks": 20, "folds": 5, "budgets": list(engine.BUDGETS), "bootstrap_draws": engine.BOOTSTRAP_DRAWS},
        "validation": validation, "historical_changes": engine.historical_changes(),
        "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p), "size_bytes": p.stat().st_size} for p in sorted(set(files))]}
    engine.write_json(OUTPUT / "run_manifest.json", manifest)
    require(all(sha256_file(ROOT / x["path"]) == x["sha256"] for x in manifest["files"]), "manifest hash mismatch")
    return {"status": "PASS", "validation_checks": validation["check_count"], "decisions": manifest["decisions"], "AULC": aulc_summary.to_dict("records")}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--finalize", action="store_true"); args = parser.parse_args()
    if args.finalize: print(json.dumps(finalize(), indent=2))
    else: parser.error("choose --finalize")


if __name__ == "__main__":
    main()
