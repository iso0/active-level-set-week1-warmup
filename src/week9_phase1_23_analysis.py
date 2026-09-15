"""Week 9 Phase 1.23 — pre-registered analysis of the synthetic stress test.

Implements PHASE1_23_SYNTHETIC_PROTOCOL.json: per-function paired differences, bootstrap CIs over
functions, sign-flip tests, Holm over the 80 primary tests, the five-way classification, the overall
verdict rules, the theory predictions P1-P10, the validity map and post-hoc mechanism summaries.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_23_grid as grid
from src import week9_phase1_23_synthetic as syn

OUT = syn.OUTPUT
DRAWS = 10_000
EQ = 0.005
A, B = "coverage_then_margin_B40", "early8__coverage_then_margin_B40"
GUD, E8M, RND, STR = "global_unc_div_then_margin_B40", "early8__margin", "random", "straddle"
WINDOWS = {"16-80": (16, 80), "16-40": (16, 40), "41-80": (41, 80)}
SHIFT_STRONG = [c.cell_id for c in grid.CORE if c.family == "shift" and c.amplitude >= 0.3]
F1 = [c.cell_id for c in grid.CORE if c.family == "shift" and c.amplitude == 0.1]
CORE_IDS = [c.cell_id for c in grid.CORE]
SENS_IDS = [c.cell_id for c in grid.SENSITIVITY]
CELL = {c.cell_id: c for c in grid.CELLS}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, steps = [], []
    for path in sorted(syn.CHECKPOINTS.glob("*/*/f*.json.gz")):
        pay = json.loads(gzip.decompress(path.read_bytes()))
        key = {"cell": pay["cell"], "index": pay["index"], "policy": pay["policy"]}
        rows += [{**key, **m} for m in pay["metrics"]]
        steps += [{**key, "seed_size": pay["seed_size"], **s} for s in pay["steps"]]
    return pd.DataFrame(rows), pd.DataFrame(steps)


def aulc_table(metrics: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (cell, index, policy), g in metrics.groupby(["cell", "index", "policy"]):
        g = g.set_index("budget").sort_index()
        rec = {"cell": cell, "index": index, "policy": policy}
        for m in ("acc_q20", "acc_global", "acc_q30", "bacc_global"):
            for w, (lo, hi) in WINDOWS.items():
                s = g.loc[lo:hi, m]
                rec[f"{m}|{w}"] = float(np.trapezoid(s.to_numpy(), s.index.to_numpy()) / (hi - lo))
        rec["error_depth_q95|B40"] = float(g.loc[40, "error_depth_q95"])
        rec["error_depth_q95|B80"] = float(g.loc[80, "error_depth_q95"])
        rec["acc_global|B80"] = float(g.loc[80, "acc_global"])
        out.append(rec)
    return pd.DataFrame(out)


def paired(diff: np.ndarray, key: str) -> dict:
    diff = np.asarray(diff, float)
    rng = np.random.default_rng(p13.seed_u32("phase1_23-boot", key))
    boot = diff[rng.integers(0, len(diff), size=(DRAWS, len(diff)))].mean(axis=1)
    rng = np.random.default_rng(p13.seed_u32("phase1_23-flip", key))
    null = (rng.choice((-1.0, 1.0), size=(DRAWS, len(diff))) * np.abs(diff)).mean(axis=1)
    return {"n": int(len(diff)), "mean": float(diff.mean()), "sd": float(diff.std(ddof=1)),
            "ci_low": float(np.quantile(boot, 0.025)), "ci_high": float(np.quantile(boot, 0.975)),
            "ci90_low": float(np.quantile(boot, 0.05)), "ci90_high": float(np.quantile(boot, 0.95)),
            "p": float((np.sum(np.abs(null) >= abs(diff.mean())) + 1) / (DRAWS + 1)),
            "positive_share": float((diff > 0).mean())}


def holm(ps: dict[str, float]) -> dict[str, float]:
    out, running = {}, 0.0
    ordered = sorted(ps.items(), key=lambda kv: kv[1])
    for rank, (k, p) in enumerate(ordered):
        running = max(running, (len(ordered) - rank) * p)
        out[k] = min(1.0, running)
    return out


def classify(r: dict, p_key: str) -> str:
    p = r[p_key]
    if p < 0.05 and r["ci_low"] > 0:
        return "HELPS_MATERIAL" if r["mean"] >= EQ else "HELPS_SMALL"
    if p < 0.05 and r["ci_high"] < 0:
        return "HURTS"
    if r["ci90_low"] >= -EQ and r["ci90_high"] <= EQ:
        return "EQUIVALENT"
    return "INCONCLUSIVE"


CONTRASTS = {  # name -> (candidate, reference)
    "A-margin": (A, "margin"), "B-margin": (B, "margin"),
    "A-global_unc_div": (A, GUD), "B-early8_margin": (B, E8M), "early8_margin-margin": (E8M, "margin"),
    "global_unc_div-margin": (GUD, "margin"), "A-random": (A, RND), "margin-random": ("margin", RND),
    "straddle-margin": (STR, "margin"), "B-A": (B, A),
}
ENDPOINTS = ["acc_q20|16-80", "acc_q20|16-40", "acc_global|16-80", "acc_global|16-40", "acc_q20|41-80",
             "acc_q30|16-80", "bacc_global|16-80", "error_depth_q95|B40", "error_depth_q95|B80", "acc_global|B80"]


def contrasts(aulc: pd.DataFrame) -> pd.DataFrame:
    wide = aulc.set_index(["cell", "index", "policy"])
    rows = []
    for cell in CORE_IDS + SENS_IDS:
        sub = wide.loc[cell]
        policies = set(sub.index.get_level_values("policy"))
        for name, (cand, ref) in CONTRASTS.items():
            if cand not in policies or ref not in policies:
                continue
            a, b = sub.xs(cand, level="policy"), sub.xs(ref, level="policy")
            common = a.index.intersection(b.index)
            for ep in ENDPOINTS:
                r = paired((a.loc[common, ep] - b.loc[common, ep]).to_numpy(), f"{cell}|{name}|{ep}")
                rows.append({"cell": cell, "family": grid.family_of(cell), "contrast": name, "endpoint": ep, **r})
    frame = pd.DataFrame(rows)
    primary = frame[frame.cell.isin(CORE_IDS) & frame.contrast.isin(["A-margin", "B-margin"])
                    & frame.endpoint.isin(["acc_q20|16-80", "acc_q20|16-40"])]
    assert len(primary) == 80, len(primary)
    adjusted = holm({i: p for i, p in primary.p.items()})
    frame["holm_p"] = frame.index.map(adjusted)
    frame["class"] = [classify(r, "holm_p") if pd.notna(r["holm_p"]) else classify(r, "p") for r in frame.to_dict("records")]
    frame["class_basis"] = np.where(frame.holm_p.notna(), "Holm over 80 primary tests", "unadjusted")
    return frame


def get(frame: pd.DataFrame, cell: str, contrast: str, endpoint: str) -> dict:
    row = frame[(frame.cell == cell) & (frame.contrast == contrast) & (frame.endpoint == endpoint)]
    return row.iloc[0].to_dict() if len(row) else {}


def verdicts(frame: pd.DataFrame) -> dict:
    q40 = "acc_q20|16-40"
    helps = [c for c in SHIFT_STRONG if get(frame, c, "A-margin", q40)["class"].startswith("HELPS")]
    bad = [(c, ep) for c in F1 + ["F7_exact"] for ep in ("acc_q20|16-40", "acc_q20|16-80")
           if get(frame, c, "A-margin", ep)["class"] == "HURTS" and get(frame, c, "A-margin", ep)["mean"] <= -EQ]
    band = [c for c in SHIFT_STRONG if get(frame, c, "A-global_unc_div", q40)["ci_low"] > 0]
    a_verdict = ("A_GENERALISES_IN_PREDICTED_REGION" if len(helps) >= 4 and not bad
                 else "A_SPH_SPECIFIC" if len(helps) <= 1 else "A_MIXED")
    b_helps = [c for c in SHIFT_STRONG if get(frame, c, "B-margin", q40)["class"].startswith("HELPS")]
    return {"A_verdict": a_verdict, "A_helps_cells_among_8_strong_shift": helps,
            "A_material_hurt_in_F1_or_F7": bad,
            "band_verdict": "BAND_CONDITIONING_MATTERS" if len(band) >= 4 else "BAND_CONDITIONING_NOT_SHOWN",
            "band_ci_positive_cells": band, "B_helps_cells_among_8_strong_shift (descriptive)": b_helps}


def predictions(frame: pd.DataFrame) -> dict:
    q40, q80, q41 = "acc_q20|16-40", "acc_q20|16-80", "acc_q20|41-80"
    out = {}
    exact = ["F7_exact", "SENS_prev0.5_exact", "SENS_pool1000_exact"]
    cls = {(c, k): get(frame, c, k, q40)["class"] for c in exact for k in ("A-margin", "B-margin")}
    out["P1"] = {"classes": {f"{c}|{k}": v for (c, k), v in cls.items()},
                 "supported": all(v in ("EQUIVALENT", "HURTS") for v in cls.values())}
    f1 = {c: get(frame, c, "A-margin", q40)["class"] for c in F1}
    out["P2"] = {"A_classes": f1, "B_classes": {c: get(frame, c, "B-margin", q40)["class"] for c in F1},
                 "supported": all(v != "HELPS_MATERIAL" for v in f1.values())}
    means = {c: get(frame, c, "A-margin", q40)["mean"] for c in SHIFT_STRONG}
    by = lambda pred: float(np.mean([m for c, m in means.items() if pred(CELL[c])]))
    out["P3"] = {"means": means, "positive_cells": int(sum(m > 0 for m in means.values())),
                 "mean_a0.6": by(lambda c: c.amplitude == 0.6), "mean_a0.3": by(lambda c: c.amplitude == 0.3),
                 "mean_d3": by(lambda c: c.het_dim == 3), "mean_d1": by(lambda c: c.het_dim == 1),
                 "mean_l0.5": by(lambda c: c.length == 0.5), "mean_l0.2": by(lambda c: c.length == 0.2)}
    out["P3"]["supported"] = bool(out["P3"]["positive_cells"] >= 5 and out["P3"]["mean_a0.6"] > out["P3"]["mean_a0.3"]
                                  and out["P3"]["mean_d3"] > out["P3"]["mean_d1"])
    helping = [c for c in CORE_IDS if get(frame, c, "A-margin", q40)["class"].startswith("HELPS")]
    p4 = {c: (abs(get(frame, c, "A-margin", q41)["mean"]), abs(get(frame, c, "A-margin", q40)["mean"])) for c in helping}
    out["P4"] = {"cells_where_A_helps": {c: {"abs_41_80": v[0], "abs_16_40": v[1]} for c, v in p4.items()},
                 "supported": bool(p4) and all(v[0] < v[1] for v in p4.values())}
    p5 = {c: get(frame, c, "A-global_unc_div", q40)["mean"] for c in ("F6_rot60", "F6_rot90")}
    out["P5"] = {"A_minus_global_unc_div": p5, "A_minus_margin_descriptive":
                 {c: get(frame, c, "A-margin", q40)["mean"] for c in ("F6_rot30", "F6_rot60", "F6_rot90")},
                 "supported": all(v <= 0 for v in p5.values())}
    p6 = {c: get(frame, c, "A-margin", q40)["class"] for c in ("F5_islands_k3", "F5_islands_k8")}
    out["P6"] = {"classes": p6, "supported": all(v == "EQUIVALENT" for v in p6.values())}
    p7 = get(frame, "F4_fold_a0.6", "A-margin", q40)["mean"]
    out["P7"] = {"A_minus_margin_fold_a0.6": p7, "supported": p7 >= 0, "note": "weak prediction"}
    p8 = {c: get(frame, c, "A-global_unc_div", q40)["mean"] for c in SHIFT_STRONG}
    out["P8"] = {"means": p8, "positive_cells": int(sum(v > 0 for v in p8.values())),
                 "supported": sum(v > 0 for v in p8.values()) >= 5}
    e8 = {c: get(frame, c, "early8_margin-margin", q40)["mean"] for c in CORE_IDS}
    agree = {c: bool(np.sign(get(frame, c, "B-early8_margin", q40)["mean"]) == np.sign(get(frame, c, "A-margin", q40)["mean"]))
             for c in CORE_IDS}
    out["P9"] = {"early8_margin_minus_margin_positive_cells": int(sum(v > 0 for v in e8.values())),
                 "sign_agreement_cells": int(sum(agree.values())), "cells": len(CORE_IDS),
                 "supported": sum(v > 0 for v in e8.values()) >= 2 * len(CORE_IDS) / 3
                 and sum(agree.values()) >= 2 * len(CORE_IDS) / 3}
    s = get(frame, "F7_exact", "straddle-margin", q40)
    out["P10"] = {"straddle_minus_margin_F7": {k: s[k] for k in ("mean", "ci90_low", "ci90_high")},
                  "supported": s["ci90_low"] >= -EQ and s["ci90_high"] <= EQ}
    return out


def best_threshold_error(h: np.ndarray, y: np.ndarray) -> float:
    o = np.argsort(h)
    ys = y[o]
    pos_below = np.concatenate([[0], np.cumsum(ys)])
    neg_above = (1 - ys).sum() - np.concatenate([[0], np.cumsum(1 - ys)])
    return float((pos_below + neg_above).min() / len(y))


def validity_map(aulc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    wide = aulc.set_index(["cell", "index", "policy"])
    rows = []
    for cell in CORE_IDS:
        c = CELL[cell]
        for index in range(c.n_functions):
            truth = syn.load_truth(c, index, syn.CHECKPOINTS)
            rec = {"cell": cell, "family": grid.family_of(cell), "index": index,
                   "best_1d_threshold_error": best_threshold_error(truth.test_h, truth.test_y),
                   "amplitude": c.amplitude, "length": c.length, "het_dim": c.het_dim, "shift": c.family == "shift"}
            for name, (cand, ref) in (("A-margin", (A, "margin")), ("B-margin", (B, "margin")),
                                      ("A-global_unc_div", (A, GUD))):
                for ep in ("acc_q20|16-40", "acc_q20|16-80", "acc_global|16-40"):
                    rec[f"{name}|{ep}"] = wide.loc[(cell, index, cand), ep] - wide.loc[(cell, index, ref), ep]
            rows.append(rec)
    per_function = pd.DataFrame(rows)
    per_function["quintile"] = pd.qcut(per_function.best_1d_threshold_error.rank(method="first"), 5, labels=False)
    bins = []
    for q, g in per_function.groupby("quintile"):
        for col in ("A-margin|acc_q20|16-40", "B-margin|acc_q20|16-40", "A-margin|acc_q20|16-80",
                    "A-global_unc_div|acc_q20|16-40", "A-margin|acc_global|16-40"):
            r = paired(g[col].to_numpy(), f"validity|{q}|{col}")
            bins.append({"quintile": int(q), "error_low": g.best_1d_threshold_error.min(),
                         "error_high": g.best_1d_threshold_error.max(), "contrast": col, **r})
    shift = per_function[per_function["shift"]]
    X = np.column_stack([np.ones(len(shift)), shift.amplitude, (shift.length == 0.2).astype(float),
                         (shift.het_dim == 3).astype(float)])
    ols = {}
    for col in ("A-margin|acc_q20|16-40", "A-margin|acc_q20|16-80", "B-margin|acc_q20|16-40"):
        y = shift[col].to_numpy()
        xtx_inv = np.linalg.inv(X.T @ X)
        beta = xtx_inv @ X.T @ y
        resid = y - X @ beta
        lever = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
        meat = X.T @ (X * (resid / (1 - lever))[:, None] ** 2)
        se = np.sqrt(np.diag(xtx_inv @ meat @ xtx_inv))
        ols[col] = {name: {"coef": float(b), "hc3_se": float(s)} for name, b, s in
                    zip(("intercept", "amplitude", "length_0.2", "het_dim_3"), beta, se)}
    return per_function, pd.DataFrame(bins), ols


def mechanism(steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cell, policy), g in steps.groupby(["cell", "policy"]):
        early = g[(g.budget >= 16) & (g.budget < 40)]
        late = g[g.budget >= 40]
        rec = {"cell": cell, "policy": policy,
               "chosen_in_band_B16_39": float(early.chosen_in_band.mean()),
               "differs_from_margin_B16_39": float((early.chosen != early.margin_choice).mean()),
               "differs_from_margin_B40_79": float((late.chosen != late.margin_choice).mean()),
               "band_fraction_B16_39": float(early.band_fraction.mean()),
               "residual_sd_B16": float(g[g.budget == 16].residual_sd.mean()),
               "residual_sd_B40": float(g[g.budget == 40].residual_sd.mean()),
               "seed_size_mean": float(g.drop_duplicates("index").seed_size.mean())}
        for b in (16, 20, 24, 28, 32, 40):
            rec[f"separable_B{b}"] = float(g[g.budget == b].separable.mean())
        rows.append(rec)
    return pd.DataFrame(rows)


def main() -> dict:
    protocol = json.loads((OUT / "PHASE1_23_SYNTHETIC_PROTOCOL.json").read_text(encoding="utf-8"))
    metrics, steps = load()
    expected = len(grid.jobs())
    found = metrics.groupby(["cell", "index", "policy"]).ngroups
    assert found == expected, f"{found} trajectories, expected {expected}"
    aulc = aulc_table(metrics)
    frame = contrasts(aulc)
    per_function, bins, ols = validity_map(aulc)
    mech = mechanism(steps)
    result = {"protocol_frozen_at": protocol["frozen_at_utc"], "trajectories": found,
              "verdicts": verdicts(frame), "predictions": predictions(frame), "ols_shift_family_hc3": ols,
              "seed_size_distribution_early8": steps[steps.policy.str.startswith("early8")].drop_duplicates(
                  ["cell", "index", "policy"]).seed_size.value_counts().sort_index().to_dict()}
    metrics.to_csv(OUT / "synthetic_metrics_by_budget.csv.gz", index=False)
    aulc.to_csv(OUT / "synthetic_aulc_per_function.csv", index=False)
    frame.to_csv(OUT / "synthetic_contrasts.csv", index=False)
    per_function.to_csv(OUT / "synthetic_validity_per_function.csv", index=False)
    bins.to_csv(OUT / "synthetic_validity_bins.csv", index=False)
    mech.to_csv(OUT / "synthetic_mechanism.csv", index=False)
    (OUT / "SYNTHETIC_RESULT.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, default=str))
