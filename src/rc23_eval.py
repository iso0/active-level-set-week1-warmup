"""RC23 evaluation (frozen with PROTOCOL_RC23.md before any RC23 outcome). Uses the frozen RC22 metric functions (src.rc22_eval:
learner / fold-pooled metrics, AULC, verdicts, MATERIAL labels) and adds: BA target endpoints for 0.80 / 0.90 / 0.93 / 0.95 (first
budget, b and b + 4 confirmation, spend, censoring, sustained share), paired spend with the observed both-attained difference kept
apart from a restricted score (censored = 61 = the smallest confirmation spend that could follow B60), the pre-registered
non-inferiority rule and the three-way decision rule.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.rc19_eval as EV
import src.rc22_eval as E22

BA_TARGETS = (0.80, 0.90, 0.93, 0.95)
CENSOR_SCORE = 61                     # confirmation needs b and b + 4 measured; a curve unconfirmed by B60 can at best confirm at b = 57 -> 61
DELTA = 0.010                         # acceptable BA-AULC loss for the simplification decision (one-sided 95 % lower bound)
SPEND_THR, SPEND_FRAC, MIN_GOOD_FRAC = 2.0, 6 / 8, 7 / 8


def endpoints(B, by=("arm", "repeat"), targets=BA_TARGETS):
    rows = []
    for key, g in B.groupby(list(by)):
        g = g.sort_values("budget"); cur = dict(zip(g.budget, g.BA))
        for lev in targets:
            base = {**dict(zip(by, key)), "target": f"BA >= {lev:.2f}"}
            if any(not np.isfinite(v) for v in cur.values()):
                rows.append({**base, "defined": False, "first": np.nan, "at_startup": False, "confirmed_b": np.nan, "spend": np.nan, "censored": True, "sustained_share": np.nan}); continue
            e = EV.endpoint(cur, lev, step=4); cb = e["confirmed"]
            sus = float(np.mean([cur[b] >= lev for b in cur if cb is not None and b >= cb])) if cb is not None else np.nan
            rows.append({**base, "defined": True, "first": e["first"], "at_startup": e["first"] == min(cur), "confirmed_b": cb, "spend": e["confirm_spend"],
                         "censored": bool(e["censored"]), "sustained_share": sus})
    return pd.DataFrame(rows)


def attainment_table(E):
    return E.groupby(["target", "arm"]).agg(units=("censored", "size"), defined=("defined", "sum"), attained=("censored", lambda c: int((~c).sum())),
                                            first_median=("first", "median"), at_startup=("at_startup", "sum"), spend_mean_attainers=("spend", "mean"),
                                            spend_median_attainers=("spend", "median"), sustained_share_mean=("sustained_share", "mean")).reset_index()


def spend_pair(E, a, b, target, by="repeat"):
    e = E[(E.target == target) & E.defined]; j = e[e.arm == a].set_index(by)[["spend", "censored"]].join(e[e.arm == b].set_index(by)[["spend", "censored"]], lsuffix="_a", rsuffix="_b", how="inner")
    if not len(j):
        return {"contrast": f"{a} − {b}", "target": target, "verdict": "INCOMPLETE"}
    both = (~j.censored_a) & (~j.censored_b); obs = (j.spend_a - j.spend_b)[both]
    sc = lambda s, c: np.where(c, CENSOR_SCORE, s); d = sc(j.spend_a, j.censored_a) - sc(j.spend_b, j.censored_b); n = len(d); k = math.ceil(SPEND_FRAC * n)
    fewer, more = int((d < 0).sum()), int((d > 0).sum())
    v = ("FEWER SIMULATIONS (DEV)" if (np.mean(d) <= -SPEND_THR and fewer >= k and j.censored_a.sum() <= j.censored_b.sum()) else
         "MORE SIMULATIONS (DEV)" if (np.mean(d) >= SPEND_THR and more >= k and j.censored_a.sum() >= j.censored_b.sum()) else "NO CLEAR DIFFERENCE (DEV)")
    return {"contrast": f"{a} − {b}", "target": target, "units": n, "attained_a": int((~j.censored_a).sum()), "attained_b": int((~j.censored_b).sum()),
            "both_attained": int(both.sum()), "observed_mean_diff_both_attained": float(obs.mean()) if len(obs) else np.nan,
            "restricted_mean_diff(censored=61)": float(np.mean(d)), "fewer/equal/more(restricted)": f"{fewer}/{int((d == 0).sum())}/{more}",
            "per_unit": ";".join(f"{'–' if ca else int(sa)}/{'–' if cb else int(sb)}" for sa, ca, sb, cb in zip(j.spend_a, j.censored_a, j.spend_b, j.censored_b)), "verdict": v}


def noninferiority(T, a, b, metric, delta=DELTA, by="repeat"):
    x = T[T.arm == a].set_index(by)[metric]; y = T[T.arm == b].set_index(by)[metric]; d = (x - y).dropna(); n = len(d)
    m = float(d.mean()); se = float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan; lcb = m - tdist.ppf(0.95, n - 1) * se if n > 1 else np.nan
    return {"contrast": f"{a} − {b}", "metric": metric, "mean": m, "se": se, "lower_95": lcb, "delta": delta, "good": f"{int((d > 0).sum())}/{n}",
            "verdict": "NON-INFERIOR (DEV)" if np.isfinite(lcb) and lcb >= -delta else "NON-INFERIORITY NOT SHOWN"}


def robust_ok(Ts, a, b):
    """Ts: {condition: {window: AULC table}}. OK iff no WORSE BA verdict (margin 0.020) and mean BA-AULC B8-B60 >= -0.010 in every condition."""
    rows, ok = [], True
    for cond, A in Ts.items():
        for w in ("small", "all"):
            r = E22.contrast(A[w], a, b, "BA", 0.020, "higher"); rows.append({"condition": cond, "window": w, **r}); ok = ok and not r["verdict"].startswith("WORSE")
            if w == "all":
                ok = ok and r["mean"] >= -0.010
    return ok, rows


def decide(A_std, E_std, Ts, R="PHR_NRMAP", S="HA_LR", L="HA_LEAN"):
    """Pre-registered three-way decision (PROTOCOL_RC23.md section 6)."""
    out = {}
    for cand in (L, S):
        ni = [noninferiority(A_std[w], cand, R, "BA") for w in ("small", "all")]; sp = spend_pair(E_std, cand, R, "BA >= 0.93")
        rob, rrows = robust_ok({k: {w: v[w] for w in ("small", "all")} for k, v in Ts.items()}, cand, R)
        out[cand] = {"noninferiority": ni, "spend_BA_0.93": sp, "robust": rob, "robust_rows": rrows,
                     "pass": bool(all(x["verdict"].startswith("NON-INFERIOR") for x in ni) and not sp["verdict"].startswith("MORE") and rob)}
    dec = ("D1: the fully lean system is sufficient — HA_LEAN + margin" if out[L]["pass"] else
           "D2: the shared upstream is needed — HA_LR + margin" if out[S]["pass"] else "D3: simplification not robust enough — keep PHR_NRMAP + margin")
    return dec, out
