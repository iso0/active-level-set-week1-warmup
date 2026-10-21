"""RC22 evaluation (frozen with PROTOCOL_RC22.md before any RC22 outcome): metrics for individual learners (one fold / block)
and for fold-pooled curves (the 5 learners of one repeat / seed pooled, as in RC19-RC21), AULC windows, paired contrasts with
the RC20/RC21 verdict rules, target attainment, the matched-state ingredient / scale / ranking analyses, the acquisition audit and
the two pre-registered decision rules (SELECTOR, SIMPLE). Test outcomes are read here only (evaluator side).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.special import logit
from scipy.stats import spearmanr

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
EB = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21" / "e-final" / "units"
WIN = {"small": tuple(range(8, 25)), "all": tuple(range(8, 61))}
TARGETS = (("BA", 0.93, "higher"), ("BA", 0.95, "higher"), ("log_loss", 0.20, "lower"))
PRIMARY_TARGET = "BA >= 0.93"
MIN_GOOD_FRAC, SPEND_THR, SPEND_FRAC = 7 / 8, 2.0, 6 / 8
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330)).to_numpy()                   # evaluator-only geometric diagnostic (RC21 definition)


# ======================================================================================== per-learner records
def learner_rows(units, M, tasks=None, key="p", cons_map=None):
    """One row per (arm, repeat, fold, budget) with the learner's own test predictions (+ y, batch, q20, corner flags)."""
    y_all = M.y; batch = M.source_batch; corner = pd.Series(CORNER(M), index=M.index); rows = []
    for u in units:
        ids = u["test_ids"]; y = y_all.reindex(ids).to_numpy(int); nb = (batch.reindex(ids) == "NEW").to_numpy(); cr = corner.reindex(ids).to_numpy(bool)
        q20 = None
        if tasks is not None and (u["repeat"], u["fold"]) in tasks:
            t = tasks[(u["repeat"], u["fold"])]
            if list(np.asarray(t["ids"])[t["test"]]) == list(ids):           # q20 only from the task whose test set this is
                q20 = np.asarray(t["q20"], bool)
        for e in u["evals"]:
            for c, arm in (cons_map(u) if cons_map else [(list(e[key].keys())[0], u["arm"])]):
                p = np.asarray([np.nan if v is None else v for v in e[key][c]], float)
                rows.append({"arm": arm, "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], "p": p, "y": y, "new": nb, "corner": cr, "q20": q20, "ids": ids})
    return rows


def _m(p, y, new=None, corner=None, q20=None):
    p = np.clip(p, 1e-6, 1 - 1e-6); hat = p >= 0.5; n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    sens = float(np.mean(hat[y == 1])) if n1 else np.nan; spec = float(np.mean(~hat[y == 0])) if n0 else np.nan
    r = {"n1": n1, "n0": n0, "sensitivity": sens, "specificity": spec, "BA": 0.5 * (sens + spec) if (n1 and n0) else np.nan,
         "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), "brier": float(np.mean((p - y) ** 2))}
    if new is not None:
        c = new & (y == 0); r["spec_NEW"] = float(np.mean(~hat[c])) if c.any() else np.nan; r["corner_cond_errors"] = int(np.sum(hat & corner & (y == 0))) if corner is not None else np.nan
        r["corner_cond_n"] = int(np.sum(corner & (y == 0))) if corner is not None else np.nan
        k = corner & (y == 1); r["corner_key_errors"] = int(np.sum(~hat & k)) if corner is not None else np.nan
    if q20 is not None and q20.any():
        s1 = np.mean(hat[q20 & (y == 1)]) if (q20 & (y == 1)).any() else np.nan; s0 = np.mean(~hat[q20 & (y == 0)]) if (q20 & (y == 0)).any() else np.nan
        r["q20_BA"] = 0.5 * (s1 + s0)
    return r


def learner_metrics(rows):
    return pd.DataFrame([{k: r[k] for k in ("arm", "repeat", "fold", "budget")} | _m(r["p"], r["y"], r["new"], r["corner"], r["q20"]) for r in rows])


def pooled_metrics(rows, n_learners=5):
    """Fold-pooled curve of one repeat: the 5 learners' out-of-fold test predictions pooled (RC19 convention)."""
    acc = {}
    for r in rows:
        acc.setdefault((r["arm"], r["repeat"], r["budget"]), []).append(r)
    out = []
    for (arm, rep, b), rs in acc.items():
        cat = lambda k: np.concatenate([x[k] for x in rs]); q = [x["q20"] for x in rs]
        m = _m(cat("p"), cat("y"), cat("new"), cat("corner"), np.concatenate(q) if all(v is not None for v in q) else None)
        if len(rs) != n_learners:
            m["BA"] = np.nan
        out.append({"arm": arm, "repeat": rep, "budget": b, "learners": len(rs), **m})
    return pd.DataFrame(out).sort_values(["arm", "repeat", "budget"]).reset_index(drop=True)


def aulc(B, window, cols=("BA", "log_loss", "brier", "sensitivity", "specificity", "q20_BA", "spec_NEW"), by=("arm", "repeat")):
    cols = [c for c in cols if c in B]
    return B[B.budget.isin(WIN[window] if isinstance(window, str) else window)].groupby(list(by))[cols].mean().reset_index()


# ======================================================================================== verdicts
def verdict(d, margin, direction):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d); m = float(d.mean()) if n else np.nan
    good = (d < 0) if direction == "lower" else (d > 0); bad = (d > 0) if direction == "lower" else (d < 0); k = math.ceil(MIN_GOOD_FRAC * n)
    if n == 0:
        return "INCOMPLETE", m, 0, 0
    if (m <= -margin if direction == "lower" else m >= margin) and good.sum() >= k:
        return "BETTER (DEV)", m, int(good.sum()), n
    if (m >= margin if direction == "lower" else m <= -margin) and bad.sum() >= k:
        return "WORSE (DEV)", m, int(good.sum()), n
    return "NOT DIFFERENT (DEV)", m, int(good.sum()), n


def contrast(T, a, b, metric, margin, direction, by="repeat"):
    x = T[T.arm == a].set_index(by)[metric]; y = T[T.arm == b].set_index(by)[metric]; d = (x - y).dropna()
    v, m, g, n = verdict(d.values, margin, direction)
    return {"contrast": f"{a} − {b}", "metric": metric, "direction": direction, "margin": margin, "mean": m,
            "se": float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else np.nan, "min": float(d.min()) if len(d) else np.nan,
            "max": float(d.max()) if len(d) else np.nan, "good": f"{g}/{n}", "verdict": v}


def material(T, a, b, metric, lower):
    """Matched-path label (RC20 / RC21): MATERIAL iff |mean| >= 0.010 in the good direction and good in >= 7/8."""
    x = T[T.arm == a].set_index("repeat")[metric]; y = T[T.arm == b].set_index("repeat")[metric]; d = (x - y).dropna(); n = len(d); m = float(d.mean())
    good = (d < 0) if lower else (d > 0); bad = (d > 0) if lower else (d < 0); k = math.ceil(MIN_GOOD_FRAC * n)
    lab = "MATERIAL" if ((m <= -0.010 if lower else m >= 0.010) and good.sum() >= k) else ("MATERIAL HARM" if ((m >= 0.010 if lower else m <= -0.010) and bad.sum() >= k) else "NOT MATERIAL")
    return {"contrast": f"{a} − {b}", "metric": metric, "mean": m, "se": float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan, "good": f"{int(good.sum())}/{n}", "label": lab}


# ======================================================================================== attainment
def endpoints(B, by=("arm", "repeat")):
    rows = []
    for key, g in B.groupby(list(by)):
        for met, lev, dirn in TARGETS:
            cur = dict(zip(g.budget, g[met] if dirn == "higher" else -g[met]))
            if any(not np.isfinite(v) for v in cur.values()):
                rows.append({**dict(zip(by, key)), "target": f"{met} {'>=' if dirn == 'higher' else '<='} {lev}", "first": np.nan, "confirmed_b": np.nan, "spend": np.nan,
                             "censored": True, "defined": False}); continue
            e = EV.endpoint(cur, lev if dirn == "higher" else -lev, step=4)
            rows.append({**dict(zip(by, key)), "target": f"{met} {'>=' if dirn == 'higher' else '<='} {lev}", "first": e["first"], "confirmed_b": e["confirmed"],
                         "spend": e["confirm_spend"], "censored": bool(e["censored"]), "defined": True})
    return pd.DataFrame(rows)


def spend_pair(E, a, b, target, horizon=60, by="repeat"):
    e = E[E.target == target]; j = e[e.arm == a].set_index(by)[["spend", "censored"]].join(e[e.arm == b].set_index(by)[["spend", "censored"]], lsuffix="_a", rsuffix="_b", how="inner")
    if not len(j):
        return {"contrast": f"{a} − {b}", "target": target, "verdict": "INCOMPLETE"}
    imp = lambda s, c: np.where(c, horizon + 4, s); d = imp(j.spend_a, j.censored_a) - imp(j.spend_b, j.censored_b); n = len(d); k = math.ceil(SPEND_FRAC * n)
    fewer = int((d < 0).sum()); more = int((d > 0).sum())
    v = ("FEWER SIMULATIONS (DEV)" if (np.mean(d) <= -SPEND_THR and fewer >= k and j.censored_a.sum() <= j.censored_b.sum()) else
         "MORE SIMULATIONS (DEV)" if (np.mean(d) >= SPEND_THR and more >= k and j.censored_a.sum() >= j.censored_b.sum()) else "NO CLEAR DIFFERENCE (DEV)")
    return {"contrast": f"{a} − {b}", "target": target, "restricted_mean_difference(censored=64)": float(np.mean(d)), "fewer/equal/more": f"{fewer}/{int((d == 0).sum())}/{more}",
            "censored_a/b": f"{int(j.censored_a.sum())}/{int(j.censored_b.sum())}", "per_unit": ";".join(f"{'–' if ca else int(sa)}/{'–' if cb else int(sb)}" for sa, ca, sb, cb in
                                                                                             zip(j.spend_a, j.censored_a, j.spend_b, j.censored_b)), "verdict": v}


def learner_attainment(LB, target="BA >= 0.93"):
    """Individual learners (one fold each): confirmed own-fold BA target; censored at B60 (never a fictional completion budget)."""
    E = endpoints(LB, by=("arm", "repeat", "fold")); e = E[E.target == target]
    return e.groupby("arm").agg(learners=("censored", "size"), defined=("defined", "sum"), attained=("censored", lambda c: int((~c).sum())),
                                spend_mean_attainers=("spend", "mean"), spend_median_attainers=("spend", "median")).reset_index(), E


# ======================================================================================== matched-state analyses (g-ingr)
def scale_ranking(units, a="SHQ_ATS_H", b="PHR_NRMAP", extra=("SHQ_ATS_H_RECAL", "HA_LR", "HONLY_LR")):
    """Per state: logit(b) on logit(a) over candidates (slope, intercept, R^2), sign disagreements, margin-rank agreement."""
    rows = []
    for u in units:
        for e in u["evals"]:
            if "cand" not in e:
                continue
            c = e["cand"]; la = logit(np.clip(np.asarray(c[f"p:{a}"], float), 1e-6, 1 - 1e-6))
            for other in (b,) + tuple(extra):
                lb = logit(np.clip(np.asarray(c[f"p:{other}"], float), 1e-6, 1 - 1e-6)); X = np.c_[np.ones_like(la), la]; beta = np.linalg.lstsq(X, lb, rcond=None)[0]
                res = lb - X @ beta; r2 = 1 - res.var() / lb.var() if lb.var() > 0 else np.nan
                ma, mb = -np.abs(la), -np.abs(lb); ta, tb = np.argsort(-ma, kind="stable"), np.argsort(-mb, kind="stable")
                rows.append({"path": u["path_of"], "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], "pair": f"{other} vs {a}", "slope": float(beta[1]),
                             "intercept": float(beta[0]), "R2": float(r2), "sign_disagree": float(np.mean(np.sign(la) != np.sign(lb))),
                             "spearman_margin": float(spearmanr(ma, mb).correlation), "top1_same": bool(ta[0] == tb[0]), "top5_jaccard": len(set(ta[:5]) & set(tb[:5])) / len(set(ta[:5]) | set(tb[:5]))})
    return pd.DataFrame(rows)


def audit(units, M):
    """Selector audit on matched states: collapse, distinctness from margin (REF) and eta-straddle (H), corner diagnostic."""
    corner = pd.Series(CORNER(M), index=M.index); rows = []
    for u in units:
        ids = None
        for e in u["evals"]:
            if "cand" not in e:
                continue
            c = e["cand"]; pr = np.asarray(c["p:PHR_NRMAP"], float); marg = -np.abs(pr - 0.5); hp = -(np.clip(pr, 1e-12, 1) * np.log(np.clip(pr, 1e-12, 1)) + np.clip(1 - pr, 1e-12, 1) * np.log(np.clip(1 - pr, 1e-12, 1)))
            eta = np.asarray(c["eta_straddle_H"], float); cand_ids = None
            for sel in ("bald_lap", "bald_grid"):
                s = np.asarray(c[sel], float); t1 = int(np.argmax(s))
                rows.append({"path": u["path_of"], "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], "selector": sel, "max_score": float(s.max()),
                             "max_entropy": float(hp.max()), "ratio_max": float(s.max() / hp.max()) if hp.max() > 0 else np.nan, "frac_below_1e-6": float(np.mean(s < 1e-6)),
                             "spearman_vs_margin": float(spearmanr(s, marg).correlation), "spearman_vs_eta_straddle_H": float(spearmanr(s, eta).correlation),
                             "top1_same_as_margin": bool(t1 == int(np.argmax(marg))), "top1_same_as_eta_straddle_H": bool(t1 == int(np.argmax(eta))),
                             "p_ref_at_top1": float(pr[t1]), "p_ref_at_margin_top1": float(pr[int(np.argmax(marg))]),
                             "corner_top1": bool(corner.iloc[c["cand_rows"][t1]]), "corner_margin_top1": bool(corner.iloc[c["cand_rows"][int(np.argmax(marg))]])})
    return pd.DataFrame(rows)


SELECTOR_ORDER = ("BALD_LAP", "BALD_GRID")
SIMPLE_ORDER = ("HONLY_LR", "HA_LR", "SHQ_ATS_H_RECAL")


def decide_selector(AU, numerics_pass, timing_extra_s):
    """Pre-registered rule (PROTOCOL_RC22.md section 5): first selector in SELECTOR_ORDER passing every criterion, else None."""
    res = {}
    for sel in SELECTOR_ORDER:
        a = AU[AU.selector == sel.lower()]
        crit = {"numerics": bool(numerics_pass), "median_ratio_max_ge_0.05": bool(a.ratio_max.median() >= 0.05),
                "states_with_max_below_1e-6_lt_10pct": bool(np.mean(a.max_score < 1e-6) < 0.10),
                "top1_differs_from_margin_ge_25pct": bool(1 - a.top1_same_as_margin.mean() >= 0.25), "median_spearman_vs_margin_lt_0.95": bool(a.spearman_vs_margin.median() < 0.95),
                "top1_differs_from_eta_straddle_ge_25pct": bool(1 - a.top1_same_as_eta_straddle_H.mean() >= 0.25), "extra_cpu_le_0.5s": bool(timing_extra_s <= 0.5)}
        res[sel] = {"criteria": crit, "pass": bool(all(crit.values())), "summary": {"median_ratio_max": float(a.ratio_max.median()), "top1_differs_from_margin": float(1 - a.top1_same_as_margin.mean()),
                                                                                 "median_spearman_vs_margin": float(a.spearman_vs_margin.median()),
                                                                                 "top1_differs_from_eta_straddle": float(1 - a.top1_same_as_eta_straddle_H.mean())}}
    chosen = next((s for s in SELECTOR_ORDER if res[s]["pass"]), None)
    return chosen, res


def decide_simple(A_small):
    """Pre-registered rule: first construction in SIMPLE_ORDER with BA-AULC B8-B24 >= REF - 0.003 and LL-AULC <= REF + 0.003 (matched)."""
    res = {}
    ref = A_small[A_small.arm == "PHR_NRMAP"].set_index("repeat")
    for c in SIMPLE_ORDER:
        x = A_small[A_small.arm == c].set_index("repeat"); dba = float((x.BA - ref.BA).mean()); dll = float((x.log_loss - ref.log_loss).mean())
        res[c] = {"dBA_B8_B24": dba, "dLL_B8_B24": dll, "equivalent": bool(dba >= -0.003 and dll <= 0.003)}
    return next((c for c in SIMPLE_ORDER if res[c]["equivalent"]), None), res
