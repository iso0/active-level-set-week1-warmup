"""Week 16 item 4 — Astra's discovery theory (eqs. 9-11, §6.4) on the real pools (descriptive).

Tails: the M lowest-log h points of each NEW-136 training pool (rare class = non-Keyhole) and the M
highest-log h points of each OLD-405 Week 8.5 training pool (rare class = Keyhole), M ∈ {5, 10, 15, 20}.
Uses labels only to *describe* enrichment; nothing here selects a method.
"""
from __future__ import annotations

import json
from fractions import Fraction
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

from src.week16_astra import E_T, first_hit_survival, p_T_greater, tail_dominates
from src.week16_real import ROOT, W12, splits, campaigns

OUT = ROOT / "outputs/week16_theory_meets_data/discovery"
MS = (5, 10, 15, 20)


def log_h(df):
    return np.log(df.P) - .5 * np.log(df.VX) - 1.5 * np.log(df.LS)


def enrichment(C, S):
    rows = []
    lh = {k: log_h(C[k]["df"]).to_numpy() for k in ("NEW", "OLD")}
    for s in S + [{"campaign": k, "repeat": 0, "fold": 0, "train": np.arange(len(C[k]["y"]))} for k in ("NEW", "OLD")]:
        camp = s["campaign"]; tr = s["train"]; y = C[camp]["y"][tr]; h = lh[camp][tr]
        rare = 0 if camp == "NEW" else 1
        order = np.argsort(h if camp == "NEW" else -h, kind="stable")
        isr = (y[order] == rare)
        N, r = len(tr), int(isr.sum())
        det_first = int(np.argmax(isr)) + 1
        for M in MS:
            sM = int(isr[:M].sum())
            rows.append({"campaign": camp, "repeat": s["repeat"], "fold": s["fold"], "whole_campaign": s["repeat"] == 0,
                         "N": N, "r": r, "M": M, "s": sM, "tail_rate": sM / M, "pool_rate": r / N, "enriched": sM / M >= r / N,
                         "dominates": tail_dominates(M, sM, N, r) if sM >= 1 else False,
                         "E_D_tail": float(Fraction(M + 1, sM + 1)) if sM >= 1 else np.nan, "E_D_pool": float(Fraction(N + 1, r + 1)),
                         "P_D_tail_gt3": float(first_hit_survival(3, M, sM)) if sM >= 1 else 1.0, "P_D_pool_gt3": float(first_hit_survival(3, N, r)),
                         "deterministic_first_rare_rank": det_first,
                         "E_T_pool": float(E_T(N - r, r)), "P_T_pool_gt8": float(p_T_greater(8, N - r, r)), "P_T_pool_gt16": float(p_T_greater(16, N - r, r))})
    return pd.DataFrame(rows)


def observed_vs_exact(E):
    """Week 12 observed discovery costs (100 NEW pools) against the exact uniform-order law of each pool."""
    d = pd.read_csv(W12 / "startup/benchmark/discovery_costs.csv")
    ex = E[(E.campaign == "NEW") & ~E.whole_campaign & (E.M == 5)][["repeat", "fold", "N", "r", "E_T_pool", "P_T_pool_gt8", "P_T_pool_gt16"]]
    m = d.merge(ex, on=["repeat", "fold"])
    rows = []
    for rule, g in m.groupby("rule"):
        rows.append({"rule": rule, "pools": len(g), "mean_cost": g.discovery_cost.mean(), "se_cost": g.discovery_cost.std(ddof=1) / np.sqrt(len(g)),
                     "share_gt8": float((g.discovery_cost > 8).mean()), "share_gt16": float((g.discovery_cost > 16).mean()), "max_cost": int(g.discovery_cost.max()),
                     "exact_uniform_mean_E_T": g.E_T_pool.mean(), "exact_uniform_P_gt8": g.P_T_pool_gt8.mean(), "exact_uniform_P_gt16": g.P_T_pool_gt16.mean()})
    return pd.DataFrame(rows)


def posterior_at_T():
    """§6.4: stored Week 12 predictions, maximin8 vs adaptive-physics8 startups with the same margin refinement."""
    arms = ("M3_margin__maximin8_continue", "M3_margin__adaptive_physics8")
    P = pd.read_csv(W12 / "active_learning/predictions.csv.gz")
    P = P[P.arm.isin(arms)]
    P["ll"] = -np.log(np.clip(np.where(P.truth == 1, P.probability, 1 - P.probability), 1e-12, 1))
    P["correct"] = ((P.probability >= .5).astype(int) == P.truth)
    rel = P[P.predictor == "historical_M3"].groupby(["split_id", "arm"]).budget.min().rename("T_release").reset_index()
    q = pd.read_csv(W12 / "active_learning/query_paths.csv.gz")
    q = q[q.arm.isin(arms)]
    first16 = q[q.query_order <= 16].groupby(["split_id", "arm"]).row_index.apply(lambda x: tuple(sorted(x))).unstack()
    differs = first16[arms[0]] != first16[arms[1]]
    rows = []
    for (sid, arm), g in P.groupby(["split_id", "arm"]):
        T = int(rel[(rel.split_id == sid) & (rel.arm == arm)].T_release.iloc[0])
        for tag, b in (("at_T", T), ("B16", 16), ("B24", 24), ("B40", 40)):
            h = g[g.budget == b]
            rows.append({"split_id": sid, "arm": arm, "point": tag, "budget": b, "T_release": T, "startups_differ_by_B16": bool(differs.get(sid, False)),
                         "test_logloss": h.ll.mean(), "test_acc": h.correct.mean(),
                         "test_minority_recall": h[h.truth == 0].correct.mean() if (h.truth == 0).any() else np.nan})
    R = pd.DataFrame(rows)
    W = R.pivot_table(index=["split_id", "point", "startups_differ_by_B16"], columns="arm", values=["test_logloss", "test_acc", "test_minority_recall"]).reset_index()
    return R, W


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C = campaigns(); S = splits(C)
    E = enrichment(C, S); E.to_csv(OUT / "tail_enrichment.csv", index=False)
    observed_vs_exact(E).to_csv(OUT / "observed_vs_exact_discovery.csv", index=False)
    R, W = posterior_at_T(); R.to_csv(OUT / "posterior_at_T.csv", index=False)
    W.columns = ["|".join(c).strip("|") for c in W.columns]; W.to_csv(OUT / "posterior_at_T_paired.csv", index=False)


if __name__ == "__main__":
    main()
