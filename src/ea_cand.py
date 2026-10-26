"""EA stage 2 candidates (PROTOCOL_EA_CANDIDATES.md, registered before any evaluation).
  C1   HA_TREND with MAP hyperparameters under a FIXED weak hyperprior (log s_f2 ~ N(0, 1.5^2); log ell_k ~ N(0, 1); log s_n2 ~ N(log 0.01,
       1.5^2)), L-BFGS-B from two fixed starts (HA_TREND's start and the prior mean), lowest objective kept; everything else = HA_TREND
  C1a  the same prior and starts on the constant-mean depth GP (HA_LEAN)            [is the gain specific to the trend?]
  C1b  HA_TREND with the same two starts and NO prior (ML-II)                         [is the gain from more optimiser starts?]
Classifier, honest K = 10 out-of-fold stacking, one-class rule and margin = HA_LEAN / HA_TREND. Paid outcomes and public inputs only.
    python -m src.ea_cand work ea-cand-dev | ea-cand-smoke
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np

import src.ea_diag as DG
import src.ea_diag2 as D2
import src.el_cross as X
import src.rc18_campaign as C18
import src.rc18_common as RC
import src.rc18_gp as G
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_pac as PC

OUT = DG.OUT
EL = RC.ROOT / "outputs" / "research_campaign_20261024" / "opus_early_learning"
PRIOR_M = np.r_[0.0, 0.0, 0.0, 0.0, 0.0, np.log(0.01)]
PRIOR_S = np.r_[1.5, 1.0, 1.0, 1.0, 1.0, 1.5]
START_DEFAULT = np.r_[0.0, 0.0, 0.0, 0.0, 0.0, np.log(0.1)]
STARTS = (START_DEFAULT, PRIOR_M.copy())
SYSTEMS = {"C1": ("phys", True, STARTS), "C1a": ("flat", True, STARTS), "C1b": ("phys", False, STARTS)}
CHECKS = {"chk_trend_noprior_1start": ("phys", False, (START_DEFAULT,)), "chk_flat_noprior_1start": ("flat", False, (START_DEFAULT,))}


class GPMAP(G.GP):
    """src.rc18_gp.GP with an optional independent normal hyperprior on ALL log-hyperparameters (posterior mode instead of ML-II)."""

    def __init__(self, H_cols=0, b=3.0, prior=True):
        super().__init__(H_cols=H_cols, b=b, hyperprior=None); self.use_prior = bool(prior)

    def _nlml(self, th, Z, ys, H, w):
        nl, g = super()._nlml(th, Z, ys, H, w)
        if self.use_prior:
            d = (np.asarray(th, float) - PRIOR_M) / PRIOR_S; nl = nl + 0.5 * float(d @ d); g = g + d / PRIOR_S
        return nl, g


def gp_fit(Zl, Yl, Hl, Wl, kind, prior, starts):
    best = None
    for th0 in starts:
        g = GPMAP(H_cols=1 if kind == "phys" else 0, b=PC.B_TREND, prior=prior).fit(Zl, Yl, H=Hl, w=Wl, theta0=np.asarray(th0, float))
        if best is None or g.opt["nlml"] < best.opt["nlml"]:
            best = g
    return best


def depth_fit_cand(task, rev, Z, kind, rows, prior, starts):
    """= src.rc24_pac.depth_fit (phys / flat) with the fit replaced by gp_fit (prior and starts)."""
    L = rev.paid if rows is None else np.asarray(rows); Y = rev.paid_Y()[:, PC.DEPTH_COL]; W = np.where(rev.paid_short(), C18.W_SHORT, 1.0)
    Lu = L[np.isfinite(Y[L])]
    if (W[Lu] <= 100).sum() < 3:
        return None
    H = A.hcol(task)[:, None] if kind == "phys" else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = gp_fit(Z[Lu], Y[Lu], None if H is None else H[Lu], W[Lu], kind, prior, starts)
    return {"g": g, "H": H, "rows": Lu}


def predict(task, rev, Z, rows, spec):
    kind, prior, starts = spec; L = rev.paid; y_p = rev.paid_y(); y = y_p[L]; A_p = rev.paid_A(); usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        return np.full(len(rows), float(np.mean(y))), True
    h = A.hcol(task)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        F, E = D2.cf_generic(rev, Z, rows, lambda r: depth_fit_cand(task, rev, Z, kind, r, prior, starts), lambda f, idx: PC.depth_predict(f, Z, idx)[0])
        return DG.lin(F, h[L], y, E, h[rows]), False


def dev_path_unit(cond, r, f):
    d = EL / "el-mix-fwd" / "units"
    return RC.read_json_gz(d / (f"STD__r{r}_f{f}.json.gz" if cond == "STD" else f"{cond}__s{r}_b{f}.json.gz"))


def dev_unit(task, u, M, budgets=tuple(range(8, 61)), check_b=(12, 40)):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in u["paid_ids"]]; te = np.asarray(task["test"])
    if [task["ids"][i] for i in te] != list(u["test_ids"]):
        raise RuntimeError("recorded test set differs from the task")
    recA = {e["budget"]: e["p_L"] for e in u["evals"]}; recD = {e["budget"]: e["p_T"] for e in u["evals"]}; ev = []; chk = {}
    for b in budgets:
        rev = K._rev_with(task, M, paid_all[:b]); e = {"budget": b, "p": {}, "cpu_s": {}}
        for nm, spec in SYSTEMS.items():
            t0 = time.process_time(); p, one = predict(task, rev, Z, te, spec); e["p"][nm] = LN._f32(p); e["cpu_s"][nm] = time.process_time() - t0; e["one_class"] = one
        if b in check_b:
            pt, _ = predict(task, rev, Z, te, CHECKS["chk_trend_noprior_1start"]); pf, _ = predict(task, rev, Z, te, CHECKS["chk_flat_noprior_1start"])
            chk[b] = {"trend_noprior_1start_vs_recorded_D": float(np.max(np.abs(np.asarray(LN._f32(pt)) - np.asarray(recD[b], float)))),
                      "flat_noprior_1start_vs_recorded_A": float(np.max(np.abs(np.asarray(LN._f32(pf)) - np.asarray(recA[b], float))))}
        ev.append(e)
    return {"evals": ev, "checks": chk}


def units(job):
    if job == "ea-cand-dev":
        return ([(f"STD__r{r}_f{f}", ("dev", "STD", r, f)) for r in range(123, 163) for f in range(1, 6)]
                + [(f"K5__s{s}_b{b}", ("dev", "K5", s, b)) for s in range(33, 41) for b in range(1, 6)]
                + [(f"K4__s{s}_b{b}", ("dev", "K4", s, b)) for s in range(17, 25) for b in range(1, 5)])
    if job == "ea-cand-smoke":
        return [("STD__r123_f1", ("smoke", "STD", 123, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    T = X.tasks_for({n: (None, v[1], v[2], v[3]) for n, v in S.items()}, M)

    def fn(name):
        kind, c, r, f = S[name]; task = T[(c, r, f)]; u = dev_path_unit(c, r, f)
        res = dev_unit(task, u, M, budgets=(8, 12, 13, 40) if kind == "smoke" else tuple(range(8, 61)))
        return {"condition": c, "repeat": r, "fold": f, "paid_ids": u["paid_ids"][:60], "test_ids": u["test_ids"], **res}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("ea-cand-dev", "ea-cand-smoke")})
