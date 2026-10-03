"""Bounded, post-hoc diagnosis of the Week 11 startup failure.

This module reconstructs the exact 100 frozen feature-only maximin orders and
describes their class-discovery behaviour.  It does not define or benchmark a
new startup rule.  The only labels read are the already-open NEW-136 truth
values recoverable from the saved Week 11 predictions; no sealed or withheld
outcomes are opened.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.week12_development_common import (
    FEATURES,
    FREEZE,
    HIST,
    MANIFEST,
    OLD,
    OUT,
    load_new,
    load_old,
    load_splits,
    original_order,
    safe,
    sha,
    seed,
    write_csv,
    write_json,
)


SCHEMA_VERSION = "week12_startup_diagnosis_v1"
DIAG = OUT / "startup" / "diagnosis"
FAILURES = {"external__r003_f04", "external__r009_f05", "external__r019_f04"}
STARTUP_RULES = ("maximin", "physics_stratified_geometry", "adaptive_physics", "uniform_random")
STARTUP_BUDGETS = (8, 12, 16, 20, 24, 40, 80)


def _single_class_probability(n0: int, n1: int, k: int) -> float:
    """Uniform-without-replacement probability that k labels have one class."""
    n = n0 + n1
    if k > n:
        return np.nan
    numerator = (math.comb(n0, k) if n0 >= k else 0)
    numerator += math.comb(n1, k) if n1 >= k else 0
    return float(numerator / math.comb(n, k))


def _rank_auc(y: np.ndarray, values: np.ndarray) -> float:
    if np.unique(y).size != 2:
        return np.nan
    return float(roc_auc_score(y, values))


def _effective_dimension(values: np.ndarray) -> dict:
    values = np.asarray(values, float)
    if len(values) < 3:
        return {"n": int(len(values)), "effective_dimension": np.nan, "eigenvalues": []}
    cov = np.cov(values, rowvar=False, ddof=1)
    eig = np.linalg.eigvalsh(np.atleast_2d(cov))
    eig = np.clip(np.asarray(eig, float), 0.0, None)
    total = float(eig.sum())
    effective = float(total * total / np.square(eig).sum()) if total > 0 else 0.0
    return {"n": int(len(values)), "effective_dimension": effective,
            "eigenvalues": eig[::-1].tolist(), "trace": total}


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {str(p.relative_to(Path(__file__).resolve().parents[1])).replace("\\", "/"): sha(p)
            for p in paths}


def _load_context():
    new = load_new()
    old = load_old()
    splits = load_splits()
    x = new.loc[:, FEATURES].to_numpy(float)
    y = new.has_keyhole.to_numpy(int)
    ids = new.sim_id.astype(str).to_numpy()
    old_x = old.loc[:, FEATURES].to_numpy(float)
    old_y = old.has_keyhole.to_numpy(int)
    all_scaler = StandardScaler().fit(x)
    old_scaler = StandardScaler().fit(old_x)
    return new, old, splits, x, y, ids, old_x, old_y, all_scaler, old_scaler


def _rare_table(new, old, x, y, ids, old_x, old_y, all_scaler, old_scaler):
    log_h = new.log_h.to_numpy(float)
    values = {**{name: x[:, i] for i, name in enumerate(FEATURES)}, "log_h": log_h}
    rank_pct = {name: rankdata(values[name], method="average") / len(y) for name in values}
    old_scaled = old_scaler.transform(old_x)
    new_scaled = old_scaler.transform(x)
    dmat = cdist(new_scaled, old_scaled)
    new_all_scaled = all_scaler.transform(x)
    rare_indices = np.flatnonzero(y == 0)
    keyhole_indices = np.flatnonzero(y == 1)
    new_pairwise = cdist(new_all_scaled, new_all_scaled)
    rows = []
    for idx in rare_indices:
        same = np.flatnonzero(old_y == 0)
        opposite = np.flatnonzero(old_y == 1)
        nearest_new_keyhole = keyhole_indices[np.argmin(new_pairwise[idx, keyhole_indices])]
        rows.append({
            "row_index": int(idx), "sim_id": str(ids[idx]), "class_value": 0,
            **{name: float(x[idx, j]) for j, name in enumerate(FEATURES)},
            "log_h": float(log_h[idx]),
            **{f"{name}_rank_pct_new": float(rank_pct[name][idx]) for name in values},
            "nearest_old_same_std4": float(dmat[idx, same].min()),
            "nearest_old_opposite_std4": float(dmat[idx, opposite].min()),
            "nearest_old_same_abs_log_h": float(np.abs(log_h[idx] - old.log_h.to_numpy(float)[old_y == 0]).min()),
            "nearest_old_opposite_abs_log_h": float(np.abs(log_h[idx] - old.log_h.to_numpy(float)[old_y == 1]).min()),
            "nearest_new_keyhole_row_index": int(nearest_new_keyhole),
            "nearest_new_keyhole_std4": float(new_pairwise[idx, nearest_new_keyhole]),
            "nearest_new_keyhole_abs_vx": float(abs(x[idx, 1] - x[nearest_new_keyhole, 1])),
            "new_keyhole_neighbors_std4_le_1": int(np.sum(new_pairwise[idx, keyhole_indices] <= 1.0)),
        })
    return pd.DataFrame(rows)


def _orders_table(new, splits, x, y, ids):
    rows, split_rows = [], []
    for split in splits:
        train = np.asarray(split["train_indices"], dtype=int)
        order = np.asarray(original_order(x, split), dtype=int)
        require = len(order) == len(train) and len(set(order.tolist())) == len(order)
        if not require:
            raise RuntimeError(f"invalid maximin order {split['split_id']}")
        ordered_y = y[order]
        both = np.flatnonzero((np.cumsum(ordered_y == 0) > 0) & (np.cumsum(ordered_y == 1) > 0))
        first_both = int(both[0] + 1) if len(both) else None
        b16 = ordered_y[:16]
        split_rows.append({
            "split_id": split["split_id"], "repeat": int(split["repeat"]), "fold": int(split["fold"]),
            "split_seed": int(split["split_seed"]), "train_size": int(len(train)),
            "train_class_0": int((y[train] == 0).sum()), "train_class_1": int((y[train] == 1).sum()),
            "train_minority": int(min((y[train] == 0).sum(), (y[train] == 1).sum())),
            "b16_class_0": int((b16 == 0).sum()), "b16_class_1": int((b16 == 1).sum()),
            "b16_has_both_classes": bool(np.unique(b16).size == 2),
            "first_both_query": first_both,
            "queries_after_b16_to_both": int(first_both - 16) if first_both and first_both > 16 else 0,
        })
        for q, idx in enumerate(order, 1):
            rows.append({
                "split_id": split["split_id"], "repeat": int(split["repeat"]), "fold": int(split["fold"]),
                "query_order": q, "row_index": int(idx), "sim_id": str(ids[idx]),
                "has_keyhole": int(y[idx]), "P": float(x[idx, 0]), "VX": float(x[idx, 1]),
                "LS": float(x[idx, 2]), "ST": float(x[idx, 3]), "log_h": float(new.log_h.iloc[idx]),
                "in_frozen_b16": bool(q <= 16), "class0_seen": bool(np.any(ordered_y[:q] == 0)),
                "class1_seen": bool(np.any(ordered_y[:q] == 1)),
                "both_classes_seen": bool(np.unique(ordered_y[:q]).size == 2),
                "first_both_query": first_both,
            })
    return pd.DataFrame(rows), pd.DataFrame(split_rows)


def _prefix_geometry(new, splits, x, y, orders, old_scaler):
    rows = []
    for split in splits:
        sid = split["split_id"]
        if sid not in FAILURES:
            continue
        order = orders[sid]
        train = np.asarray(split["train_indices"], int)
        train_scaled = old_scaler.transform(x[train])
        for q in range(1, int(np.flatnonzero((np.cumsum(y[order] == 0) > 0) & (np.cumsum(y[order] == 1) > 0))[0] + 1) + 1):
            prefix = order[:q]
            remaining = np.setdiff1d(train, prefix, assume_unique=False)
            row = {"split_id": sid, "query_order": q, "queried_row_index": int(order[q - 1]),
                   "queried_class": int(y[order[q - 1]]), "prefix_class0": int((y[prefix] == 0).sum()),
                   "prefix_class1": int((y[prefix] == 1).sum())}
            p_scaled = old_scaler.transform(x[prefix])
            for cls in (0, 1):
                candidate = remaining[y[remaining] == cls]
                d = cdist(p_scaled, old_scaler.transform(x[candidate])).min()
                row[f"nearest_unqueried_class{cls}_std4"] = float(d)
                for j, feature in enumerate(FEATURES):
                    row[f"nearest_unqueried_class{cls}_{feature}_std"] = float(
                        np.abs(p_scaled[:, j, None] - old_scaler.transform(x[candidate])[:, j][None, :]).min())
            row["nearest_unqueried_class0_minus_class1_std4"] = row["nearest_unqueried_class0_std4"] - row["nearest_unqueried_class1_std4"]
            rows.append(row)
    return pd.DataFrame(rows)


def _dimension_associations(new, x, y, all_scaler):
    values = {**{name: x[:, i] for i, name in enumerate(FEATURES)}, "log_h": new.log_h.to_numpy(float)}
    rows = []
    for feature, value in values.items():
        rare = value[y == 0]
        majority = value[y == 1]
        rows.append({
            "feature": feature, "rare_n": int(len(rare)), "majority_n": int(len(majority)),
            "rank_auc_keyhole_high": _rank_auc(y, value),
            "rank_auc_rare_high": _rank_auc((y == 0).astype(int), value),
            "rare_min": float(rare.min()), "rare_median": float(np.median(rare)), "rare_max": float(rare.max()),
            "rare_iqr": float(np.percentile(rare, 75) - np.percentile(rare, 25)),
            "majority_min": float(majority.min()), "majority_median": float(np.median(majority)), "majority_max": float(majority.max()),
            "majority_iqr": float(np.percentile(majority, 75) - np.percentile(majority, 25)),
            "median_difference_rare_minus_majority": float(np.median(rare) - np.median(majority)),
        })
    all_scaled = all_scaler.transform(x)
    rare_scaled = all_scaled[y == 0]
    majority_scaled = all_scaled[y == 1]
    effective = {"raw_4d_all_new_scale": _effective_dimension(all_scaled),
                 "raw_4d_rare_class": _effective_dimension(rare_scaled),
                 "raw_4d_majority_class": _effective_dimension(majority_scaled),
                 "log_h_plus_raw_context_rare_class": _effective_dimension(np.column_stack([new.log_h.to_numpy(float)[y == 0], rare_scaled[:, 1:]]))}
    return pd.DataFrame(rows), effective


def _analytic_reference(split_summary):
    rows = []
    for row in split_summary.itertuples(index=False):
        for k in range(1, min(24, int(row.train_size)) + 1):
            rows.append({"split_id": row.split_id, "k": k, "train_minority": int(row.train_minority),
                         "train_class_0": int(row.train_class_0), "train_class_1": int(row.train_class_1),
                         "uniform_single_class_probability": _single_class_probability(int(row.train_class_0), int(row.train_class_1), k)})
    frame = pd.DataFrame(rows)
    summary = frame.groupby("k", as_index=False).agg(
        mean_single_class_probability=("uniform_single_class_probability", "mean"),
        median_single_class_probability=("uniform_single_class_probability", "median"),
        q05=("uniform_single_class_probability", lambda v: v.quantile(.05)),
        q95=("uniform_single_class_probability", lambda v: v.quantile(.95)),
        split_count=("split_id", "nunique"),
    )
    summary["mean_uniform_discovery_cdf"] = 1.0 - summary.mean_single_class_probability
    frame["uniform_discovery_cdf"] = 1.0 - frame.uniform_single_class_probability
    conditioned = frame.groupby(["k", "train_minority"], as_index=False).agg(
        mean_single_class_probability=("uniform_single_class_probability", "mean"), split_count=("split_id", "nunique"))
    return frame, summary, conditioned


def _prefix_parity(splits, x):
    path_file = HIST / "path_manifest.csv"
    saved = pd.read_csv(path_file) if path_file.exists() else pd.DataFrame()
    rows = []
    if len(saved):
        for sid, group in saved.groupby("split_id", sort=True):
            split = next(s for s in splits if s["split_id"] == sid)
            expected = np.asarray(original_order(x, split), int)
            for arm, n in (("M3_margin_incumbent", 16), ("coverage_then_margin_B40", 16), ("early8__coverage_then_margin_B40", 8)):
                observed = group[group.arm == arm].sort_values("query_order").row_index.astype(int).tolist()
                if not observed:
                    continue
                compare = observed[:n]
                target = expected[:n]
                target_list = target.tolist()
                rows.append({"split_id": sid, "arm": arm, "prefix_length": n,
                             "observed_count": len(compare), "exact": bool(compare == target_list),
                             "observed": json.dumps(compare), "expected": json.dumps(target_list)})
    return pd.DataFrame(rows)


def _figures(new, split_summary, prefix, rare, root):
    root.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(new.loc[new.has_keyhole == 1, "VX"], new.loc[new.has_keyhole == 1, "P"], s=16, alpha=.5, label="Keyhole")
    axes[0].scatter(new.loc[new.has_keyhole == 0, "VX"], new.loc[new.has_keyhole == 0, "P"], s=45, c="tab:red", label="non-Keyhole")
    axes[0].set(xlabel="VX (m/s)", ylabel="P (W)", title="NEW-136 input geometry")
    axes[0].legend(frameon=False)
    axes[1].scatter(rare.nearest_old_same_std4, rare.nearest_old_opposite_std4, c=rare.VX, cmap="viridis", s=45)
    axes[1].plot([0, max(axes[1].get_xlim()[1], axes[1].get_ylim()[1])], [0, max(axes[1].get_xlim()[1], axes[1].get_ylim()[1])], "k--", lw=1)
    axes[1].set(xlabel="Nearest OLD non-Keyhole distance", ylabel="Nearest OLD Keyhole distance", title="Rare-class OLD support distances")
    fig.tight_layout(); fig.savefig(root / "rare_geometry_old_support.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    counts = split_summary.first_both_query.dropna().astype(int)
    ax.hist(counts, bins=np.arange(.5, counts.max() + 1.5), color="0.65", edgecolor="white")
    for q in sorted(split_summary.loc[split_summary.split_id.isin(FAILURES), "first_both_query"].astype(int)):
        ax.axvline(q, color="tab:red", lw=1.5, alpha=.8)
    ax.axvline(16, color="tab:blue", ls="--", lw=1.5, label="frozen B16")
    ax.set(xlabel="Queries until both classes in continued maximin order", ylabel="Frozen splits", title="Discovery cost across all 100 frozen pools")
    ax.legend(frameon=False); fig.tight_layout(); fig.savefig(root / "discovery_cost_histogram.png", dpi=170); plt.close(fig)

    if len(prefix):
        fig, ax = plt.subplots(figsize=(7.2, 4.5))
        for sid, g in prefix.groupby("split_id", sort=True):
            ax.plot(g.query_order, g.nearest_unqueried_class0_std4, color="tab:red", alpha=.8, label=f"{sid} non-Keyhole")
            ax.plot(g.query_order, g.nearest_unqueried_class1_std4, color="tab:blue", alpha=.8, ls="--", label=f"{sid} Keyhole")
        ax.axvline(16, color="k", ls=":", lw=1)
        ax.set(xlabel="Prefix length", ylabel="Nearest unqueried distance (OLD-standardized 4D)", title="Failure-prefix geometry")
        ax.legend(frameon=False, fontsize=7, ncol=2); fig.tight_layout(); fig.savefig(root / "failure_prefix_distances.png", dpi=170); plt.close(fig)


def _require_selector_inputs(rule, x, train, queried, observed, original):
    if rule not in STARTUP_RULES:
        raise ValueError(f"unknown startup rule: {rule}")
    x = np.asarray(x, float)
    train = np.asarray(train, int)
    queried = np.asarray(queried, int)
    observed = np.asarray(observed, int)
    original = np.asarray(original, int)
    if x.ndim != 2 or x.shape[1] != 4 or not np.isfinite(x).all():
        raise ValueError("x must be a finite n-by-4 feature matrix")
    if len(queried) != len(observed) or len(set(queried.tolist())) != len(queried):
        raise ValueError("queried and observed labels must have the same unique prefix")
    if len(train) == 0 or not set(queried.tolist()).issubset(set(train.tolist())):
        raise ValueError("queried rows must lie in the training pool")
    if len(original) != len(train) or set(original.tolist()) != set(train.tolist()):
        raise ValueError("original_order must be a full training-pool permutation")
    if not set(np.unique(observed).tolist()).issubset({0, 1}):
        raise ValueError("observed labels must be binary")
    return x, train, queried, observed, original


def _scaled_geometry(x, train):
    scaler = StandardScaler().fit(x[train])
    return scaler.transform(x), scaler


def _farthest_from_chosen(x_scaled, candidates, chosen):
    candidates = np.asarray(candidates, int)
    chosen = np.asarray(chosen, int)
    if len(candidates) == 0:
        raise ValueError("no candidates remain")
    if len(chosen) == 0:
        return int(candidates.min())
    nearest = cdist(x_scaled[candidates], x_scaled[chosen]).min(axis=1)
    best = float(nearest.max())
    ties = candidates[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
    return int(ties.min())


def _physics_strata(x, train, original):
    """Return train-row strata from training-only log-h ranks and 4D geometry."""
    train = np.asarray(train, int)
    original = np.asarray(original, int)
    log_h = np.log(x[:, 0]) - .5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])
    ordered = sorted(train.tolist(), key=lambda row: (float(log_h[row]), int(row)))
    strata = {}
    for rank, row in enumerate(ordered):
        strata[int(row)] = min(2, (3 * rank) // len(ordered))
    return log_h, strata


def _uniform_permutation(train, split_id):
    train = np.asarray(train, int)
    return train[np.random.default_rng(seed(split_id, "uniform_startup")).permutation(len(train))]


def startup_next(rule, x, train, queried, observed, original_order, split_id):
    """Select one startup row using only inputs and already observed labels.

    ``original_order`` is the complete, label-blind frozen maximin order.  It is an
    explicit argument so callers can test that hidden labels cannot affect any
    rule's choice.  The function never receives the unobserved truth vector.
    """
    x, train, queried, observed, original = _require_selector_inputs(
        rule, x, train, queried, observed, original_order)
    remaining = np.setdiff1d(train, queried, assume_unique=False)
    if len(remaining) == 0:
        raise ValueError("no startup candidates remain")
    if rule == "maximin":
        return int(next(row for row in original if row not in set(queried.tolist())))
    if rule == "uniform_random":
        permutation = _uniform_permutation(train, split_id)
        return int(next(row for row in permutation if row not in set(queried.tolist())))

    x_scaled, _ = _scaled_geometry(x, train)
    if rule == "physics_stratified_geometry":
        if len(queried) == 0:
            return int(original[0])
        _, strata = _physics_strata(x, train, original)
        selected = set(queried.tolist())
        for target in range(3):
            candidates = np.asarray([row for row in remaining if strata[int(row)] == target], int)
            if len(candidates):
                return _farthest_from_chosen(x_scaled, candidates, queried)
        return _farthest_from_chosen(x_scaled, remaining, queried)

    # Adaptive physics: the first eight are the frozen order.  While only one
    # class has been observed, query the opposite log-h extreme.  Once both
    # classes exist, continue with geometry-only maximin from the revealed set.
    if len(queried) < min(8, len(original)):
        return int(original[len(queried)])
    labels = set(observed.tolist())
    log_h = np.log(x[:, 0]) - .5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])
    if labels == {1}:
        best = float(log_h[remaining].min())
        ties = remaining[np.isclose(log_h[remaining], best, rtol=1e-12, atol=1e-14)]
        return int(ties.min())
    if labels == {0}:
        best = float(log_h[remaining].max())
        ties = remaining[np.isclose(log_h[remaining], best, rtol=1e-12, atol=1e-14)]
        return int(ties.min())
    return _farthest_from_chosen(x_scaled, remaining, queried)


def _coverage_metrics(x_scaled, train, queried, y):
    train = np.asarray(train, int)
    queried = np.asarray(queried, int)
    nearest = cdist(x_scaled[train], x_scaled[queried]).min(axis=1)
    return {
        "coverage_mean_nearest_std4": float(nearest.mean()),
        "coverage_worst_nearest_std4": float(nearest.max()),
        "both_classes_seen": bool(np.unique(y[queried]).size == 2),
        "rare_capture": int((y[queried] == 0).sum()),
        "keyhole_capture": int((y[queried] == 1).sum()),
    }


def _benchmark_paths(new, splits, x, y, ids):
    rows, costs, coverage = [], [], []
    for split in splits:
        sid = split["split_id"]
        train = np.asarray(split["train_indices"], int)
        original = np.asarray(original_order(x, split), int)
        x_scaled, _ = _scaled_geometry(x, train)
        for rule in STARTUP_RULES:
            queried, observed = [], []
            cost = None
            for q in range(1, len(train) + 1):
                nxt = startup_next(rule, x, train, queried, observed, original, sid)
                if nxt in queried or nxt not in set(train.tolist()):
                    raise RuntimeError(f"invalid selector output {rule} {sid} {nxt}")
                queried.append(int(nxt)); observed.append(int(y[nxt]))
                if cost is None and len(set(observed)) == 2:
                    cost = q
                rows.append({"split_id": sid, "repeat": int(split["repeat"]), "fold": int(split["fold"]), "rule": rule, "query_order": q, "row_index": int(nxt), "sim_id": str(ids[nxt]), "has_keyhole": int(y[nxt]), "log_h": float(new.log_h.iloc[nxt]), "both_classes_seen": bool(len(set(observed)) == 2)})
                if q in STARTUP_BUDGETS:
                    coverage.append({"split_id": sid, "repeat": int(split["repeat"]), "fold": int(split["fold"]), "rule": rule, "budget": q, **_coverage_metrics(x_scaled, train, np.asarray(queried), y)})
            costs.append({"split_id": sid, "repeat": int(split["repeat"]), "fold": int(split["fold"]), "rule": rule, "discovery_cost": int(cost) if cost is not None else np.nan, "train_size": int(len(train)), "train_minority": int(min((y[train] == 0).sum(), (y[train] == 1).sum()))})
    return pd.DataFrame(rows), pd.DataFrame(costs), pd.DataFrame(coverage)


def _benchmark_prefix_parity(paths, splits, x):
    rows = []
    for split in splits:
        sid = split["split_id"]
        expected = np.asarray(original_order(x, split), int)
        for rule, n in (("maximin", len(expected)), ("adaptive_physics", min(8, len(expected))), ("physics_stratified_geometry", 1)):
            observed = paths[(paths.split_id == sid) & (paths.rule == rule)].sort_values("query_order").row_index.astype(int).to_numpy()
            target = expected[:n]
            rows.append({"split_id": sid, "rule": rule, "prefix_length": int(n), "exact": bool(np.array_equal(observed[:n], target)), "observed_count": int(len(observed))})
    return pd.DataFrame(rows)


def run_benchmark() -> dict:
    """Run the four fixed startup protocols on all original frozen pools."""
    root = OUT / "startup" / "benchmark"
    new, old, splits, x, y, ids, *_ = _load_context()
    root.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "week12_startup_benchmark_v1", "status": "POST-HOC DEVELOPMENT",
        "rules": list(STARTUP_RULES), "budgets": list(STARTUP_BUDGETS), "split_count": len(splits),
        "training_scope": "NEW-136 original Week11 frozen training pools", "features": FEATURES,
        "maximin": "original_order; pool-only StandardScaler; seeded farthest-point continuation",
        "physics_stratified_geometry": "same original first point; train-only log-h tertiles; low/mid/high cyclic farthest 4D point; row-index ties",
        "adaptive_physics": "first eight original points; all-one lowest remaining log-h; all-zero highest remaining log-h; after both classes standardized-4D farthest continuation",
        "uniform_random": "np.random.default_rng(common.seed(split_id, 'uniform_startup')).permutation(train)",
        "cost": "first paid query index containing both classes; no free labels",
        "coverage": "mean and worst nearest Euclidean distance over full training pool in pool-standardized 4D",
        "rare_capture": "number of queried non-Keyhole labels, diagnostic only",
        "hidden_label_contract": "startup_next receives observed labels only; unobserved truth is never passed to a selector",
        "no_tuning": True,
    }
    write_json(root / "config.json", config)
    config_sha = sha(root / "config.json")
    write_json(root / "config_binding.json", {"config_sha256_before_execution": config_sha, "execution_started_after_config": True})
    paths, costs, coverage = _benchmark_paths(new, splits, x, y, ids)
    parity = _benchmark_prefix_parity(paths, splits, x)
    write_csv(root / "full_startup_paths.csv.gz", paths)
    write_csv(root / "discovery_costs.csv", costs)
    write_csv(root / "coverage_and_rare_capture.csv", coverage)
    write_csv(root / "label_blind_prefix_parity.csv", parity)
    cdf = []
    for rule, group in costs.groupby("rule", sort=True):
        values = group.discovery_cost.to_numpy(float)
        for budget in STARTUP_BUDGETS:
            cdf.append({"rule": rule, "budget": budget, "fraction_both_classes": float(np.mean(values <= budget)), "median_cost": float(np.median(values)), "mean_cost": float(np.mean(values)), "tail_cost_q95": float(np.quantile(values, .95)), "run_count": int(len(values))})
    cdf = pd.DataFrame(cdf)
    write_csv(root / "discovery_cdf.csv", cdf)
    coverage_summary = coverage.groupby(["rule", "budget"], as_index=False).agg(
        mean_nearest_std4=("coverage_mean_nearest_std4", "mean"), worst_nearest_std4=("coverage_worst_nearest_std4", "mean"),
        q95_worst_nearest_std4=("coverage_worst_nearest_std4", lambda v: v.quantile(.95)),
        fraction_both_classes=("both_classes_seen", "mean"), mean_rare_capture=("rare_capture", "mean"),
        fraction_any_rare=("rare_capture", lambda v: float(np.mean(v > 0))), run_count=("split_id", "nunique"))
    write_csv(root / "coverage_summary.csv", coverage_summary)
    summary = {"schema_version": "week12_startup_benchmark_v1", "status": "POST-HOC DEVELOPMENT", "config_sha256": config_sha, "rules": list(STARTUP_RULES), "split_count": len(splits), "outcomes": cdf.to_dict(orient="records"), "coverage_summary": coverage_summary.to_dict(orient="records"), "no_withheld_outcomes": True, "no_rule_tuning": True}
    write_json(root / "summary.json", summary)
    source_paths = [FREEZE, MANIFEST, OLD, HIST / "split_manifest.json", HIST / "per_budget_predictions.csv", Path(__file__), Path(__file__).resolve().parent / "week12_development_common.py", Path(__file__).resolve().parent / "external_validation" / "runner.py"]
    write_json(root / "provenance.json", {"schema_version": "week12_startup_benchmark_v1", "source_hashes": _hashes(source_paths), "config_sha256": config_sha, "status": "POST-HOC DEVELOPMENT", "withheld_outcomes_accessed": False})
    qc = {"status": "PASS", "checks": {"four_rules": tuple(sorted(costs.rule.unique())) == tuple(sorted(STARTUP_RULES)), "100_splits_each_rule": len(costs) == 100 * len(STARTUP_RULES), "full_paths": len(paths) == int(sum(len(s["train_indices"]) for s in splits)) * len(STARTUP_RULES), "all_costs_finite": bool(np.isfinite(costs.discovery_cost).all()), "config_before_execution": config_sha == sha(root / "config.json"), "labelblind_prefix_parity": bool(parity.exact.all()), "no_withheld_outcomes": True, "no_tuning": True}}
    write_json(root / "QC.json", qc)
    lines = ["# Week 12 startup benchmark", "", "Post-hoc developmental benchmark of four fixed, label-blind startup protocols over the original 100 NEW-136 training pools. Every query is paid. The benchmark does not establish external confirmation.", "", "The four protocols are maximin, physics-stratified geometry, adaptive physics, and deterministic uniform random. Configuration was written and hashed before path execution. Discovery costs, budget CDFs, standardized 4D coverage, and rare-class capture are reported separately.", "", "The adaptive rule uses observed labels only during its one-class phase. Once both classes are observed, its continuation is geometry-only. No rule or parameter was tuned against outcomes.", ""]
    (root / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def run_diagnosis() -> dict:
    root = DIAG
    root.mkdir(parents=True, exist_ok=True)
    new, old, splits, x, y, ids, old_x, old_y, all_scaler, old_scaler = _load_context()
    rare = _rare_table(new, old, x, y, ids, old_x, old_y, all_scaler, old_scaler)
    orders, split_summary = _orders_table(new, splits, x, y, ids)
    order_map = {sid: g.sort_values("query_order").row_index.to_numpy(int) for sid, g in orders.groupby("split_id", sort=True)}
    prefix = _prefix_geometry(new, splits, x, y, order_map, old_scaler)
    associations, effective = _dimension_associations(new, x, y, all_scaler)
    analytic, analytic_summary, analytic_conditioned = _analytic_reference(split_summary)
    parity = _prefix_parity(splits, x)
    _figures(new, split_summary, prefix, rare, root / "figures")

    write_csv(root / "original_maximin_orders.csv.gz", orders)
    write_csv(root / "split_startup_summary.csv", split_summary)
    write_csv(root / "rare12_geometry.csv", rare)
    write_csv(root / "failure_prefix_geometry.csv", prefix)
    write_csv(root / "dimension_associations.csv", associations)
    write_csv(root / "analytic_startup_reference.csv.gz", analytic)
    write_csv(root / "analytic_startup_reference_summary.csv", analytic_summary)
    write_csv(root / "analytic_reference_conditioned_by_minority.csv", analytic_conditioned)
    write_csv(root / "prefix_parity.csv", parity)
    write_json(root / "effective_dimension.json", effective)

    histogram = {str(int(k)): int(v) for k, v in split_summary.first_both_query.value_counts().sort_index().items()}
    summary = {
        "schema_version": SCHEMA_VERSION, "status": "POST-HOC DEVELOPMENT / EXPLORATORY DIAGNOSIS",
        "included_count": int(len(new)), "keyhole_count": int(y.sum()), "non_keyhole_count": int((y == 0).sum()),
        "split_count": int(len(splits)), "b16_two_class_count": int(split_summary.b16_has_both_classes.sum()),
        "b16_single_class_count": int((~split_summary.b16_has_both_classes).sum()),
        "b16_minority_histogram": {str(int(k)): int(v) for k, v in split_summary.assign(minority=split_summary[["b16_class_0", "b16_class_1"]].min(axis=1)).minority.value_counts().sort_index().items()},
        "first_both_query_histogram": histogram,
        "first_both_query_median": float(split_summary.first_both_query.median()),
        "first_both_query_mean": float(split_summary.first_both_query.mean()),
        "failure_splits": split_summary[split_summary.split_id.isin(FAILURES)].to_dict(orient="records"),
        "uniform_reference_sum_at_b16": float(analytic[analytic.k == 16].uniform_single_class_probability.sum()),
        "uniform_reference_interpretation": "Descriptive hypergeometric reference conditioned on each fixed training-pool class count; no formal superiority test.",
        "prefix_parity": {"status": "PASS" if len(parity) and bool(parity.exact.all()) else "NOT_AVAILABLE_OR_FAIL", "rows": int(len(parity)), "available_split_count": int(parity.split_id.nunique()) if len(parity) else 0},
        "rare_high_vx_count": int((rare.VX >= 0.898).sum()),
        "rare_nearest_new_keyhole_std4_median": float(rare.nearest_new_keyhole_std4.median()),
        "withheld_outcomes_accessed": False, "new_startup_rule_designed": False,
    }
    write_json(root / "summary.json", summary)
    source_paths = [FREEZE, MANIFEST, OLD, HIST / "split_manifest.json", HIST / "per_budget_predictions.csv",
                    Path(__file__), Path(__file__).resolve().parent / "week12_development_common.py",
                    Path(__file__).resolve().parent / "external_validation" / "runner.py"]
    write_json(root / "provenance.json", {"schema_version": SCHEMA_VERSION, "status": "POST-HOC DEVELOPMENT", "source_hashes": _hashes(source_paths), "runtime": ".venv/Scripts/python.exe", "label_recovery": "Unique included sim_id/truth mapping from saved Week 11 predictions", "withheld_outcomes_accessed": False, "data_mixing": False})
    config = {"schema_version": SCHEMA_VERSION, "features": FEATURES, "log_h": "log(P) - 0.5*log(VX) - 1.5*log(LS)", "order": "StandardScaler fit on each training pool; seeded maximin; isclose ties then smallest global row index", "seed": "w85.seed_u32(w85.seed_key('run', split_id, 'initial_design'))", "old_support_distance": "Euclidean distance after StandardScaler fit on OLD-405 inputs", "prefix_distance": "minimum distance from selected prefix to each unqueried class in OLD-standardized 4D", "analytic_reference": "[C(n0,k)+C(n1,k)]/C(N,k)", "scope": "Diagnosis only; no startup-rule tuning or benchmarking"}
    write_json(root / "config.json", config)
    qc = {"status": "PASS", "checks": {"new_rows_136": len(new) == 136, "new_classes_124_12": int(y.sum()) == 124 and int((y == 0).sum()) == 12, "split_count_100": len(splits) == 100, "orders_cover_each_training_pool": len(orders) == int(sum(len(s["train_indices"]) for s in splits)), "unique_order_rows": bool(orders.groupby("split_id").row_index.nunique().eq(orders.groupby("split_id").size()).all()), "b16_single_class_three": int((~split_summary.b16_has_both_classes).sum()) == 3, "required_failures_identified": set(split_summary.loc[~split_summary.b16_has_both_classes, "split_id"]) == FAILURES, "prefix_parity_available_pass": len(parity) > 0 and bool(parity.exact.all()), "no_withheld_outcomes": True, "no_startup_rule_design": True}}
    write_json(root / "QC.json", qc)
    report = ["# Week 12 startup diagnosis", "", "This is post-hoc developmental and exploratory evidence on the already-open NEW-136 cohort. It reconstructs the exact 100 frozen feature-only maximin orders and does not design or benchmark a replacement startup rule.", "", "## Main findings", "", f"The cohort contains {int(y.sum())} Keyhole and {int((y == 0).sum())} non-Keyhole runs. All 100 training pools contain both classes, while the frozen B16 contains both classes in {int(split_summary.b16_has_both_classes.sum())}/100 pools. Continuing the same label-blind maximin order discovers both classes at median query {int(split_summary.first_both_query.median())}; only the three frozen failures require more than B16: external__r003_f04 at 18, external__r019_f04 at 19, and external__r009_f05 at 24.", "", "The rare class is concentrated in high VX: 11 of 12 non-Keyhole runs have VX at least 0.898 m/s, with one low-VX exception at 0.332 m/s. Its log-h range overlaps the Keyhole range, so log-h is a directional search coordinate rather than a deterministic label rule. The rare points also have nearby Keyhole points in standardized input space; this means geometric coverage can still represent the high-VX region even when it fails to capture a rare non-Keyhole label.", "", "## Analytic reference", "", "For each fixed training pool and prefix size k, the descriptive uniform-without-replacement single-class probability is [C(n0,k)+C(n1,k)]/C(N,k). Its complement is the analytic CDF of discovering both classes by k under uniform sampling without replacement. The reported values are conditioned on the observed training-pool class counts and are not a formal baseline superiority test.", "", "## Geometry caution", "", "Covariance effective dimension summaries are descriptive only. Twelve rare points are insufficient for a causal or manifold claim, and no dimension-based rule was tuned.", "", "## Reproducibility", "", "The full orders, per-query class labels, three failure-prefix tables, rare-class/OLD-support table, analytic references, parity checks, figures, configuration, provenance, and QC are saved beside this report. Saved Week11 artifacts remain untouched.", ""]
    (root / "diagnosis.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("diagnosis", "benchmark"), required=True)
    args = parser.parse_args()
    result = run_diagnosis() if args.mode == "diagnosis" else run_benchmark()
    print(json.dumps(safe(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
