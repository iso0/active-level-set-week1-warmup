"""Week 18 metrics on engine outputs (BENCHMARK_SPEC.md): real pooled-per-repeat endpoints, twin dense metrics,
queries-to-target, arm contrasts with repeat-level bootstrap, and ranking agreement across task families."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import roc_auc_score

ARM = ["model", "hyper", "rule"]


def arm_name(r):
    return f"{r['model']}|{r['hyper']}|{r['rule']}"


def real_curves(df, y_of):
    """Pooled per (task, repeat, arm, budget): BA, rare recall, AUC, Brier, q20 (mean over folds)."""
    out = []
    for (task, rep, model, hyper, rule, b), g in df.groupby(["task", "repeat", "model", "hyper", "rule", "budget"]):
        y = y_of[task]
        idx = np.concatenate([np.array(r.split(","), int) for r in g.rows]); p = np.concatenate([np.array(r.split(","), float) for r in g.p])
        yy = y[idx]; yh = (p >= .5).astype(int); rare = int(yy.mean() < .5)
        qa = []
        for r in g.itertuples():
            if isinstance(r.q20, str) and r.q20:
                ii = np.array(r.rows.split(","), int); pp = np.array(r.p.split(","), float); qq = np.array(r.q20.split(","), int).astype(bool)
                if qq.any():
                    qa.append(np.mean((pp[qq] >= .5) == y[ii][qq]))
        out.append({"task": task, "repeat": rep, "arm": f"{model}|{hyper}|{rule}", "budget": b, "folds": len(g),
                    "BA": float((np.mean(yh[yy == 1] == 1) + np.mean(yh[yy == 0] == 0)) / 2) if len(set(yy)) == 2 else np.nan,
                    "rare_recall": float(np.mean(yh[yy == rare] == rare)), "AUC": float(roc_auc_score(yy, p)) if len(set(yy)) == 2 else np.nan,
                    "brier": float(np.mean((p - yy) ** 2)), "q20": float(np.mean(qa)) if qa else np.nan})
    return pd.DataFrame(out)


def twin_curves(df):
    keep = ["task", "repeat", "budget", "NSD_0.1", "ASSD", "dense_BA"]
    d = df.copy(); d["arm"] = d.model + "|" + d.hyper + "|" + d.rule
    return d[keep[:2] + ["arm"] + keep[2:]]


def aulc(curves, key):
    def f(g):
        g = g.sort_values("budget"); b = g.budget.to_numpy(float); v = g[key].to_numpy(float)
        return float(np.trapezoid(v, b) / (b.max() - b.min())) if len(b) > 1 else np.nan
    return curves.groupby(["task", "repeat", "arm"]).apply(f, include_groups=False).rename(f"{key}_AULC").reset_index()


def qtt(curves, key, ref_arm, at=(40, 80)):
    """Queries-to-target: first budget at which an arm's per-repeat curve reaches the reference arm's mean value
    (over repeats) at budget `at` (nearest available budget); censored at the largest budget (reported as +inf)."""
    rows = []
    for task, g in curves.groupby("task"):
        r = g[g.arm == ref_arm]
        for a in at:
            bb = r.budget.unique()[np.argmin(np.abs(r.budget.unique() - a))]
            target = r[r.budget == bb][key].mean()
            for (rep, arm), h in g.groupby(["repeat", "arm"]):
                h = h.sort_values("budget"); hit = h[h[key] >= target - 1e-12]
                rows.append({"task": task, "repeat": rep, "arm": arm, "target_at": int(bb), "target": float(target),
                             "qtt": float(hit.budget.iloc[0]) if len(hit) else np.inf})
    return pd.DataFrame(rows)


def contrast(au, key, arm, ref, n=4000, seed=0):
    out = []
    for task, g in au.groupby("task"):
        w = g.pivot_table(index="repeat", columns="arm", values=key)
        if arm not in w or ref not in w:
            continue
        d = (w[arm] - w[ref]).dropna().to_numpy()
        b = np.random.default_rng(seed).choice(d, (n, len(d))).mean(1) if len(d) > 1 else np.array([np.nan])
        out.append({"task": task, "arm": arm, "ref": ref, "metric": key, "mean": float(d.mean()), "lo": float(np.quantile(b, .025)),
                    "hi": float(np.quantile(b, .975)), "repeats": len(d)})
    return pd.DataFrame(out)


def ranking_agreement(levels, families, arms):
    """levels: DataFrame indexed by family with one column per arm (mean metric). Kendall tau between families."""
    out = []
    for i, a in enumerate(families):
        for b in families[i + 1:]:
            x, y = levels.loc[a, arms].to_numpy(float), levels.loc[b, arms].to_numpy(float)
            ok = ~np.isnan(x) & ~np.isnan(y)
            if ok.sum() >= 3:
                out.append({"a": a, "b": b, "kendall": float(kendalltau(x[ok], y[ok]).statistic), "spearman": float(spearmanr(x[ok], y[ok]).statistic), "arms": int(ok.sum())})
    return pd.DataFrame(out)
