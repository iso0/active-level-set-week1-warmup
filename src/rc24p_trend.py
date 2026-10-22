"""RC24 post-audit, DEVELOPMENT / diagnostic: the clean trend family evaluated on identical paid samples (p-match units, existing DEV
HA_LEAN + margin paths, step-4 budgets). Metric code: src.rc24p_audit (frozen with the final comparison; imported, not edited).
    python -m src.rc24p_trend
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc24p_audit as AU

CONS = ("TR_NONE", "TR_PHYS", "TR_GEN3", "TR_GEN15", "HONLY_LR")
PAIRS = (("TR_PHYS", "TR_NONE"), ("TR_GEN15", "TR_NONE"), ("TR_GEN3", "TR_NONE"), ("TR_PHYS", "TR_GEN15"), ("TR_PHYS", "TR_GEN3"), ("HONLY_LR", "TR_NONE"))
W4 = {"B8_B24": range(8, 25, 4), "B8_B60": range(8, 61, 4)}


def main():
    M = P.manifest(); U = EV.load_units(AU.OUT / "p-match"); rows, regs = [], []
    for src in sorted({u["source"] for u in U}):
        E = {}
        for u in U:
            if u["source"] != src:
                continue
            bs = np.array([e["budget"] for e in u["evals"]], int)
            for c in CONS:
                E[(c, u["repeat"], u["fold"])] = (bs, np.array([np.asarray(e["p"][c], float) for e in u["evals"]]), np.asarray(u["test_ids"], str))
        D = AU.rows_from(E, M.y); G = AU.pooled(D)
        for w, bs in W4.items():
            Ap = G[G.budget.isin(list(bs))].groupby(["arm", "repeat"]).BA.mean().unstack(0)
            Ri = D[D.budget.isin(list(bs))].groupby(["arm", "repeat", "fold"]).BA.mean().dropna().groupby(["arm", "repeat"]).mean().unstack(0)
            Ll = D[D.budget.isin(list(bs))].groupby(["arm", "repeat"]).ll.mean().unstack(0)
            for a, b in PAIRS:
                for lab, T in (("pooled_BA", Ap), ("per_learner_BA_defined", Ri), ("learner_logloss", Ll)):
                    d = (T[a] - T[b]).dropna(); n = len(d); se = d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan; q = tdist.ppf(0.95, n - 1) if n > 1 else np.nan
                    rows.append({"source": src, "window": w, "metric": lab, "contrast": f"{a} − {b}", "n": n, "mean": d.mean(), "lcb": d.mean() - q * se, "ucb": d.mean() + q * se, "pos": int((d > 0).sum())})
            if "block" in src:
                pb = D[D.budget.isin(list(bs))].groupby(["arm", "fold"])[["BA", "sens", "spec"]].mean().reset_index(); pb["source"] = src; pb["window"] = w; regs.append(pb)
    R = pd.DataFrame(rows); R.to_csv(AU.AUD / "trend_control_contrasts.csv", index=False)
    pd.concat(regs).to_csv(AU.AUD / "trend_control_per_block.csv", index=False)
    print(R[R.window == "B8_B60"].pivot_table(index=["source", "contrast"], columns="metric", values="mean").round(4).to_string())
    print(R[(R.window == "B8_B24") & (R.metric == "pooled_BA")].pivot_table(index="source", columns="contrast", values="mean").round(4).to_string())
    return R


if __name__ == "__main__":
    main()
