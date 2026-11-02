"""EL study evaluator (PROTOCOL_EL_OBJECTIVES.md sections 3-6, 9). Test outcomes are read ONLY here.

Input: E[(system, condition, cluster, learner)] = (budgets, P[n_budgets x n_test], test_ids), budgets 8..60 at every step.
  STD: cluster = repeat, learner = fold; BLOCK: cluster = startup, learner = held-out region.
Per learner and budget: BA (threshold 0.5; NaN when the test set holds one class), Keyhole recall (class 1), conduction recall
(class 0), log loss (clip 1e-6) and Brier. AULC = mean over the window's budgets (B8_B24: 8..24, B8_B60: 8..60).
Target endpoints (tau = 0.90 / 0.93 / 0.95): first, confirmed (first b <= 56 with BA(b) >= tau and BA(b + 4) >= tau), spend =
confirmed + 4 INCLUDING the 8 startup simulations, attained, maintenance (attainers), kept (attained and BA(60) >= tau), lost.
Restricted-mean spend (horizon 60): mean of min(spend, 61) with a non-attaining learner counted as 61 = 12 + area above the
cumulative attainment curve over b = 12..60; a difference of two of them is the area between the two attainment curves. It is
neither the true cost nor a bound on the true saving.
Uncertainty: per-cluster mean of the per-learner paired difference; one-sided 95 % t bounds over clusters; cluster bootstrap check.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

WIN = {"B8_B24": tuple(range(8, 25)), "B8_B60": tuple(range(8, 61))}
TAUS = (0.90, 0.93, 0.95)
AT_B = (8, 12, 16, 24, 40, 60)
CUM_B = (16, 24, 40, 60)
H = 60; CENS = H + 1


# ======================================================================================== per learner and budget
def learner_rows(E, y_of):
    R = []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        y = y_of.reindex(ids).to_numpy(int); n1 = int((y == 1).sum()); n0 = int((y == 0).sum())
        Pc = np.clip(np.asarray(Pm, float), 1e-6, 1 - 1e-6)
        hat = Pc >= 0.5
        tp = (hat & (y == 1)).sum(1); tn = (~hat & (y == 0)).sum(1)
        ll = -(y * np.log(Pc) + (1 - y) * np.log(1 - Pc)).mean(1); br = ((np.asarray(Pm, float) - y) ** 2).mean(1)
        for j, b in enumerate(bs):
            R.append((sy, cond, c, l, int(b), n1, n0, int(tp[j]), int(tn[j]), float(ll[j]), float(br[j])))
    D = pd.DataFrame(R, columns=["system", "condition", "cluster", "learner", "budget", "n1", "n0", "tp", "tn", "ll", "brier"])
    D["sens"] = np.where(D.n1 > 0, D.tp / D.n1.clip(lower=1), np.nan); D["spec"] = np.where(D.n0 > 0, D.tn / D.n0.clip(lower=1), np.nan)
    D["BA"] = np.where((D.n1 > 0) & (D.n0 > 0), 0.5 * (D.sens + D.spec), np.nan); return D


def pooled_rows(E, y_of):
    """The learners of one cluster concatenated (each test run predicted once, by the learner whose test set holds it)."""
    acc = {}
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        acc.setdefault((sy, cond, c), []).append((np.asarray(bs, int), np.asarray(Pm, float), y_of.reindex(ids).to_numpy(int)))
    R = []
    for (sy, cond, c), parts in acc.items():
        bs = parts[0][0]
        if any(not np.array_equal(p[0], bs) for p in parts):
            raise RuntimeError("budgets differ within a pooled cluster")
        Pm = np.concatenate([p[1] for p in parts], axis=1); y = np.concatenate([p[2] for p in parts]); Pc = np.clip(Pm, 1e-6, 1 - 1e-6); hat = Pc >= 0.5
        n1, n0 = int((y == 1).sum()), int((y == 0).sum()); tp = (hat & (y == 1)).sum(1); tn = (~hat & (y == 0)).sum(1)
        ll = -(y * np.log(Pc) + (1 - y) * np.log(1 - Pc)).mean(1); br = ((Pm - y) ** 2).mean(1)
        for j, b in enumerate(bs):
            R.append((sy, cond, c, int(b), len(parts), n1, n0, int(tp[j]), int(tn[j]), float(ll[j]), float(br[j])))
    G = pd.DataFrame(R, columns=["system", "condition", "cluster", "budget", "learners", "n1", "n0", "tp", "tn", "ll", "brier"])
    G["sens"] = G.tp / G.n1; G["spec"] = G.tn / G.n0; G["BA"] = 0.5 * (G.sens + G.spec); return G


def aulc(T, by, cols=("BA", "sens", "spec", "ll", "brier")):
    out = []
    for w, bs in WIN.items():
        a = T[T.budget.isin(bs)].groupby(list(by))[list(cols)].mean().reset_index(); a["window"] = w; out.append(a)
    return pd.concat(out, ignore_index=True)


def endpoints(T, by):
    out = []
    for key, g in T.groupby(list(by)):
        cur = dict(zip(g.budget.astype(int), g.BA.astype(float))); bs = sorted(cur); defined = all(np.isfinite(cur[b]) for b in bs)
        for tau in TAUS:
            row = dict(zip(by, key)); row["target"] = tau; row["defined"] = defined
            if not defined:
                out.append(row); continue
            first = next((b for b in bs if cur[b] >= tau), None)
            conf = next((b for b in bs if b + 4 in cur and cur[b] >= tau and cur[b + 4] >= tau), None)
            att = conf is not None; spend = conf + 4 if att else None
            row.update({"first": first, "confirmed_b": conf, "spend": spend, "attained": att, "rms": float(spend) if att else float(CENS),
                        "maintenance": float(np.mean([cur[b] >= tau for b in bs if b >= conf])) if att else np.nan,
                        "kept": bool(att and cur[max(bs)] >= tau), "lost": bool(att and cur[max(bs)] < tau)})
            out.append(row)
    return pd.DataFrame(out)


# ======================================================================================== paired statistics over clusters
def tstats(d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d)
    if n < 2:
        return {"n": n, "mean": float(d.mean()) if n else np.nan, "se": np.nan, "lcb": np.nan, "ucb": np.nan, "pos": int((d > 0).sum()), "neg": int((d < 0).sum())}
    m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"n": n, "mean": m, "se": se, "lcb": m - q * se, "ucb": m + q * se, "pos": int((d > 0).sum()), "neg": int((d < 0).sum())}


def boot(d, B=10000, seed=2024):
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    if len(d) < 2:
        return {"boot_lo05": np.nan, "boot_hi95": np.nan}
    rng = np.random.default_rng(seed); m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return {"boot_lo05": float(np.quantile(m, 0.05)), "boot_hi95": float(np.quantile(m, 0.95))}


def cluster_diff(T, x, a, col, sign=1.0, key=("cluster", "learner")):
    """Per learner sign*(col_x - col_a) (NaN pairs dropped), averaged within cluster -> t bounds over clusters (+ bootstrap check)."""
    X = T[T.system == x].set_index(list(key))[col].astype(float); A_ = T[T.system == a].set_index(list(key))[col].astype(float)
    d = (sign * (X - A_)).dropna()
    if not len(d):
        return {"n": 0, "mean": np.nan, "lcb": np.nan, "ucb": np.nan, "learners": 0}
    cm = d.groupby(level=0).mean(); r = tstats(cm.values); r.update(boot(cm.values)); r["learners"] = int(len(d)); return r


def contrast_table(Ai, Ei, x, a):
    """Every registered estimand for X against A on individual learners (Ai: AULC rows; Ei: endpoint rows)."""
    out = {}
    for w in WIN:
        T = Ai[Ai.window == w]
        for col in ("BA", "sens", "spec", "ll", "brier"):
            out[f"d{col}_{w}"] = cluster_diff(T, x, a, col)
    for tau in TAUS:
        T = Ei[(Ei.target == tau) & (Ei.defined == True)].copy()  # noqa: E712
        T["att"] = T.attained.astype(float); T["kp"] = T.kept.astype(float)
        out[f"rms_saving_{tau}"] = cluster_diff(T, x, a, "rms", sign=-1.0)                  # RMS_A - RMS_X  (positive = X needs fewer)
        out[f"d_attain_{tau}"] = cluster_diff(T, x, a, "att"); out[f"d_kept_{tau}"] = cluster_diff(T, x, a, "kp")
        X = T[T.system == x].set_index(["cluster", "learner"]); A_ = T[T.system == a].set_index(["cluster", "learner"]); j = X.join(A_, lsuffix="_x", rsuffix="_a", how="inner")
        ax, aa = j.attained_x.astype(bool), j.attained_a.astype(bool); both = ax & aa
        dd = (j.spend_a.astype(float) - j.spend_x.astype(float))[both]
        cm = dd.groupby(level=0).mean() if len(dd) else pd.Series(dtype=float)
        out[f"attain_table_{tau}"] = {"learners": int(len(j)), "both": int(both.sum()), "x_only": int((ax & ~aa).sum()), "a_only": int((~ax & aa).sum()), "neither": int((~ax & ~aa).sum()),
                                      "both_attained_mean_saving": float(dd.mean()) if len(dd) else np.nan, "both_attained_cluster_t": tstats(cm.values) if len(cm) else None}
        sx = np.where(ax, j.spend_x.astype(float), np.inf); sa = np.where(aa, j.spend_a.astype(float), np.inf)
        out[f"cum_attain_{tau}"] = {int(b): {"x": float(np.mean(sx <= b)), "a": float(np.mean(sa <= b))} for b in CUM_B}
        out[f"median_spend_{tau}"] = {"x": float(np.median(sx)) if np.isfinite(np.median(sx)) else None, "a": float(np.median(sa)) if np.isfinite(np.median(sa)) else None}
    return out


def ba_at(D, x, a):
    out = {}
    for b in AT_B:
        T = D[D.budget == b]; out[int(b)] = {"x": float(T[T.system == x].BA.mean()), "a": float(T[T.system == a].BA.mean()), "diff": cluster_diff(T, x, a, "BA")}
    return out


def summary_by_system(D, Ai, Ei, G=None, Ap=None, Ep=None):
    """Per system: individual means (and pooled means beside) of every registered metric."""
    rows = []
    for sy in sorted(D.system.unique()):
        r = {"system": sy}
        for w in WIN:
            T = Ai[(Ai.window == w) & (Ai.system == sy)]
            for col in ("BA", "sens", "spec", "ll", "brier"):
                r[f"{col}_{w}"] = float(T[col].mean())
            if Ap is not None:
                Tp = Ap[(Ap.window == w) & (Ap.system == sy)]; r[f"pooled_BA_{w}"] = float(Tp.BA.mean())
        for b in AT_B:
            r[f"BA_b{b}"] = float(D[(D.system == sy) & (D.budget == b)].BA.mean())
            if G is not None:
                r[f"pooled_BA_b{b}"] = float(G[(G.system == sy) & (G.budget == b)].BA.mean())
        for tau in TAUS:
            T = Ei[(Ei.system == sy) & (Ei.target == tau) & (Ei.defined == True)]  # noqa: E712
            att = T.attained.astype(bool)
            r[f"attained_{tau}"] = f"{int(att.sum())}/{len(T)}"; r[f"attain_rate_{tau}"] = float(att.mean()) if len(T) else np.nan
            r[f"rms_{tau}"] = float(T.rms.mean()) if len(T) else np.nan
            r[f"spend_mean_attainers_{tau}"] = float(T.spend[att].astype(float).mean()) if att.any() else np.nan
            r[f"first_mean_attainers_{tau}"] = float(T["first"][att].astype(float).mean()) if att.any() else np.nan
            r[f"maintenance_{tau}"] = float(T.maintenance[att].astype(float).mean()) if att.any() else np.nan
            r[f"kept_{tau}"] = f"{int(T.kept.astype(bool).sum())}/{len(T)}"; r[f"lost_{tau}"] = int(T.lost.astype(bool).sum())
            if Ep is not None:
                Tp = Ep[(Ep.system == sy) & (Ep.target == tau) & (Ep.defined == True)]  # noqa: E712
                ap = Tp.attained.astype(bool); r[f"pooled_attained_{tau}"] = f"{int(ap.sum())}/{len(Tp)}"; r[f"pooled_rms_{tau}"] = float(Tp.rms.mean()) if len(Tp) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def decomposition(Ai, Ei):
    """2x2 on identical startups: model effect on each path, path effect for each predictor, interaction."""
    eff = {"model_on_L_path (D-A)": ("D", "A"), "model_on_T_path (B-C)": ("B", "C"), "path_for_L_predictor (C-A)": ("C", "A"),
           "path_for_T_predictor (B-D)": ("B", "D"), "total (B-A)": ("B", "A")}
    out = {}
    for nm, (x, a) in eff.items():
        r = {}
        for w in WIN:
            r[f"dBA_{w}"] = cluster_diff(Ai[Ai.window == w], x, a, "BA"); r[f"dll_{w}"] = cluster_diff(Ai[Ai.window == w], x, a, "ll")
        for tau in (0.93, 0.95):
            T = Ei[(Ei.target == tau) & (Ei.defined == True)]  # noqa: E712
            r[f"rms_saving_{tau}"] = cluster_diff(T, x, a, "rms", sign=-1.0)
        out[nm] = r
    # interaction (B - C) - (D - A) per learner
    r = {}
    for w in WIN:
        T = Ai[Ai.window == w].pivot_table(index=["cluster", "learner"], columns="system", values="BA")
        d = (T["B"] - T["C"]) - (T["D"] - T["A"]); cm = d.dropna().groupby(level=0).mean(); r[f"dBA_{w}"] = {**tstats(cm.values), **boot(cm.values)}
    for tau in (0.93, 0.95):
        T = Ei[(Ei.target == tau) & (Ei.defined == True)].pivot_table(index=["cluster", "learner"], columns="system", values="rms")  # noqa: E712
        d = -((T["B"] - T["C"]) - (T["D"] - T["A"])); cm = d.dropna().groupby(level=0).mean(); r[f"rms_saving_{tau}"] = {**tstats(cm.values), **boot(cm.values)}
    out["interaction ((B-C)-(D-A))"] = r
    return out


def fmt(r, k=4):
    if not isinstance(r, dict) or not np.isfinite(r.get("mean", np.nan)):
        return "–"
    s = f"{r['mean']:+.{k}f}"
    if np.isfinite(r.get("lcb", np.nan)):
        s += f" [{r['lcb']:+.{k}f}, {r['ucb']:+.{k}f}]"
    return s
