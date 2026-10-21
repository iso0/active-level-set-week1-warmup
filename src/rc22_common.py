"""RC22 shared machinery (robustness, ingredients, acquisition) for the frozen reference learner PHR_NRMAP + margin.

Everything is learned from public inputs x = (P, VX, LS, ST) and PAID outcomes only (src.rc19_pool.Reveal); test outcomes are
evaluator-only. Frozen RC21 code is called unchanged (src.rc20_attr.cf / clf, src.rc21_phr.laplace / predictive / Gram).

Tasks
  standard   rc19_pool.tasks(repeats): seeded 5-fold splits of the 541-run pool, 8-point label-free maximin startup.
  startup    the same splits with another lawful public-feature-only 8-point startup (labels never read):
               RAND8  8 pool points drawn uniformly at random (rng [2222, repeat, fold, 1]);
               LOCAL8 the 8 pool points nearest (standardised log inputs) to one random pool point (rng [2222, repeat, fold, 2]),
                      a deliberately clustered start that is often one-class; class discovery is then counted.
             After the startup the label-free continuation is greedy farthest-point order from the paid set (one-class rule).
  block      geometry-blocked tasks: k-means (k = 5, n_init 20, seed 2222) on the standardised log inputs of all 541 runs (public);
             block b is the test set (withheld from fitting AND querying), the other 4 blocks are the pool; startup and
             continuation as standard (maximin order of the pool, rng [2222, seed, b + 1, 3]). Evaluator q20 as RC19.
Constructions (one honest SHQ upstream fit per state, K = 10)
  SHQ_ATS_H  RC20 classifier (L2 logistic C = 1 on out-of-fold (log A, T, S) + exact log h)
  PHR_NRMAP  RC21B reference: same features, regularisation strengths (tau_F, tau_h on {0.5, 1, 2, 4}) averaged by Laplace marginal
             likelihood, plug-in sigma(m) per configuration; computed here on the 16 residual-free configurations only, which is
             exactly the RC21 PHR_NRMAP (validated)
  HA_LR      the same learned-regularisation classifier on exact log h + predicted log A only
  HONLY_LR   the same on exact log h only (no emulator output; tau_h grid only)
  SHQ_ATS_H_RECAL  SHQ_ATS_H with a paid-only scalar logit recalibration logit p' = a + c logit p; (a, c) by MAP (prior a ~ N(0, 1),
             c ~ N(1, 0.5^2), the E1CAL map of RC19B) on HONEST 5-fold out-of-fold predictions of the COMPLETE pipeline (upstream CF,
             normalisation and classifier refitted without the fold); fallback identity when < 12 paid runs or < 3 of either class.
Selectors
  margin     -|p - 0.5| on the arm's own construction (RC19 convention)
  BALD_GRID  partial disagreement of the PHR_NRMAP mixture: H(sum_g w_g p_g) - sum_g w_g H(p_g), p_g = sigma(m_g)
  BALD_LAP   classifier-weight information (Houlsby et al. 2011): H(pbar) - sum_g w_g E_{f~N(m_g, v_g)} H(sigma(f)),
             pbar = sum_g w_g E sigma(f); v_g = Laplace latent variance of configuration g GIVEN the plug-in emulator features
             (upstream emulator uncertainty is NOT included); the reported probabilities stay PHR_NRMAP
  coverage   a fixed label-free schedule: every 5th query after the startup (query numbers 13, 18, ..., 58) is the candidate farthest
             (standardised log inputs) from all paid runs
  MAXIMIN    every query farthest-point (label-free design reference)
"""
from __future__ import annotations

import time
import warnings

import numpy as np
from scipy.special import expit, logit

import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_phr as PH

SEED = 2222
COVERAGE_EVERY = 5
ATS_T, ATS_S = LN.TI["tmax_T0_K"], LN.TI["vmax_spike_logratio"]
CAL_MIN_N, CAL_MIN_CLASS, CAL_K = 12, 3, 5


# ======================================================================================== tasks
def _z_all(X):
    lx = np.log(X); return (lx - lx.mean(0)) / lx.std(0)


def farthest_continuation(Z, start, pool):
    """start (list of rows) followed by the greedy farthest-point order of the remaining pool rows (ties: lowest row)."""
    start = [int(i) for i in start]; rest = np.setdiff1d(pool, start); order = list(start)
    d = np.min(np.linalg.norm(Z[rest][:, None, :] - Z[start][None, :, :], axis=2), axis=1)
    while len(rest):
        j = int(np.argmax(d)); r = int(rest[j]); order.append(r)
        rest = np.delete(rest, j); d = np.delete(d, j)
        if len(rest):
            d = np.minimum(d, np.linalg.norm(Z[rest] - Z[r], axis=1))
    return np.asarray(order, int)


def startup_task(task, kind):
    """Same split, another public-feature-only startup; labels are never read."""
    t = dict(task); Z = P.zstd(task); pool = task["pool"]
    if kind == "STD":
        return t
    if kind == "RAND8":
        start = np.random.default_rng([SEED, task["repeat"], task["fold"], 1]).choice(pool, P.B0, replace=False)
    elif kind == "LOCAL8":
        c = int(np.random.default_rng([SEED, task["repeat"], task["fold"], 2]).choice(pool))
        start = pool[np.argsort(np.linalg.norm(Z[pool] - Z[c], axis=1), kind="stable")[:P.B0]]
    else:
        raise ValueError(kind)
    t["path"] = farthest_continuation(Z, start, pool); t["startup"] = kind; return t


def blocks(M=None, k=5):
    from sklearn.cluster import KMeans
    M = P.manifest() if M is None else M; X = M[list(P.INPUTS)].to_numpy(float)
    return KMeans(n_clusters=k, n_init=20, random_state=SEED).fit_predict(_z_all(X))


def block_tasks(seeds, M=None):
    from src.external_validation.analysis import boundary_flags
    from src.week13_synthetic_al import maximin_order
    M = P.manifest() if M is None else M; ids = M.index.to_numpy(str); X = M[list(P.INPUTS)].to_numpy(float); lab = blocks(M); out = []
    for s in seeds:
        for b in range(lab.max() + 1):
            test = np.flatnonzero(lab == b); pool = np.flatnonzero(lab != b)
            order = maximin_order(X[pool], np.random.default_rng([SEED, s, b + 1, 3])); path = pool[order]
            q20 = boundary_flags(X, M.y.to_numpy(int), test, ids, "entire_evaluation_batch")[20]
            out.append({"repeat": int(s), "fold": b + 1, "ids": ids, "X": X, "pool": pool, "test": test, "path": path, "q20": q20, "block": b, "startup": "STD"})
    return out


def startup(task, rev):
    for i in task["path"][:P.B0]:
        rev.reveal(int(i))


# ======================================================================================== constructions
def phr_family(Ftr, htr, y, Fev, hev, feats=(0, 1, 2)):
    """Learned-regularisation classifier on [z_h, F[:, feats]] over the residual-free grid; plug-in mixture + per-config moments."""
    feats = list(feats); Xtr = np.c_[htr, Ftr[:, feats]] if feats else htr[:, None]; Xev = np.c_[hev, Fev[:, feats]] if feats else hev[:, None]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr, Hev = (Xtr - mu) / sd, (Xev - mu) / sd; y = np.asarray(y, float)
    Utr, Uev = np.zeros((len(Htr), 1)), np.zeros((len(Hev), 1)); Gtt = PH.Gram(Htr, Htr, Utr, Utr); Get = PH.Gram(Hev, Htr, Uev, Utr)
    kss_h = Hev[:, 0] ** 2; kss_F = np.sum(Hev[:, 1:] ** 2, 1); cfg = [(tf, th) for tf in (PH.TAU_F if feats else (1.0,)) for th in PH.TAU_H]
    logw = np.empty(len(cfg)); Mm = np.empty((len(cfg), len(Hev))); Vv = np.empty_like(Mm)
    for g, (tf, th) in enumerate(cfg):
        mode = PH.laplace(Gtt.K(tf, th, 0.0, None), y); kss = PH.V0 + th ** 2 * kss_h + tf ** 2 * kss_F
        Mm[g], Vv[g], _ = PH.predictive(mode, Get.K(tf, th, 0.0, None), kss, plugin=True); logw[g] = mode["logZ"]
    w = np.exp(logw - logw.max()); w /= w.sum()
    return w @ expit(Mm), {"w": w, "m": Mm, "v": Vv, "cfg": cfg}


def _hb(p):
    p = np.clip(p, 1e-12, 1 - 1e-12); return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def bald_scores(fam):
    """Partial (grid) and classifier-weight (Laplace) mutual information per evaluation row."""
    w, Mm, Vv = fam["w"], fam["m"], fam["v"]; pg = expit(Mm)
    grid = _hb(w @ pg) - w @ _hb(pg)
    F = Mm[:, :, None] + np.sqrt(np.maximum(Vv, 0.0))[:, :, None] * PH._GHX[None, None, :]; S = expit(F)
    q = S @ PH._GHW; e = _hb(S) @ PH._GHW
    lap = _hb(w @ q) - w @ e
    return np.maximum(grid, 0.0), np.maximum(lap, 0.0), w @ q


def state(task, rev, Z, rows, which=("SHQ_ATS_H", "PHR_NRMAP"), want_bald=False, want_eta=False):
    """Probabilities at `rows` for the requested constructions (+ selector scores); paid outcomes only."""
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        return {k: np.full(len(rows), float(np.mean(y))) for k in which}, {"one_class": True}
    h = A.hcol(task); out = {}; info = {"one_class": False}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        R = A.cf(Z, rev, A.ATS, "SHQ", rows, A.KF); info["K"] = R["K"]; info["fallbacks"] = R["fallbacks"]
        if {"SHQ_ATS_H", "SHQ_ATS_H_RECAL"} & set(which) or want_eta:
            p, g, mu, sd = A.clf(R["F"], y, R["E"], h[L][:, None], h[rows][:, None]); out["SHQ_ATS_H"] = p
            if want_eta:
                eta, var = A.eta_moments(g, mu, sd, R["E"], R["V"], h[rows][:, None]); info["eta_straddle_H"] = 1.96 * np.sqrt(np.maximum(var, 0)) - np.abs(eta)
        if "PHR_NRMAP" in which or want_bald:
            out["PHR_NRMAP"], fam = phr_family(R["F"], h[L], y, R["E"], h[rows]); info["phr_w"] = fam["w"].tolist()
            if want_bald:
                info["bald_grid"], info["bald_lap"], info["p_integrated"] = bald_scores(fam)
        if "HA_LR" in which:
            out["HA_LR"] = phr_family(R["F"], h[L], y, R["E"], h[rows], feats=(0,))[0]
        if "HONLY_LR" in which:
            out["HONLY_LR"] = phr_family(R["F"], h[L], y, R["E"], h[rows], feats=())[0]
    if "SHQ_ATS_H_RECAL" in which:
        a, c, cinfo = recal_map(task, rev, Z); info["recal"] = cinfo
        out["SHQ_ATS_H_RECAL"] = expit(a + c * logit(np.clip(out["SHQ_ATS_H"], 1e-4, 1 - 1e-4)))
    return {k: out[k] for k in which}, info


def recal_map(task, rev, Z):
    """Paid-only scalar logit recalibration of SHQ_ATS_H from honest out-of-fold predictions of the complete pipeline."""
    L = rev.paid; y = rev.paid_y()[L]; n = len(L)
    if n < CAL_MIN_N or min(int((y == 1).sum()), int((y == 0).sum())) < CAL_MIN_CLASS:
        return 0.0, 1.0, {"fallback": True, "n": n}
    fold = np.arange(n) % CAL_K; p = np.full(n, np.nan)
    for j in range(CAL_K):
        r2 = subrev(task, rev, [int(i) for i in L[fold != j]])
        o, _ = state(task, r2, Z, L[fold == j], which=("SHQ_ATS_H",)); p[fold == j] = o["SHQ_ATS_H"]
    a, c = K.calib_map(p, y)
    return float(a), float(c), {"fallback": False, "n": n, "a": float(a), "c": float(c), "p_oof": [float(v) for v in p]}


def subrev(task, rev, sub):
    """A Reveal holding only the paid runs `sub`, with exactly the values the learner sees in `rev` (masked channels stay masked)."""
    r2 = K._rev_with(task, _MANIFEST[0], sub); s = np.asarray(sub, int)
    r2._y[s] = rev._y[s]; r2._A[s] = rev._A[s]; r2._Y[s] = rev._Y[s]; r2._short[s] = rev._short[s]
    return r2


_MANIFEST = [None]


def set_manifest(M):
    _MANIFEST[0] = M


# ======================================================================================== trajectories
def _farthest(Z, rev, cands):
    paid = rev.paid; d = np.min(np.linalg.norm(Z[cands][:, None, :] - Z[paid][None, :, :], axis=2), axis=1)
    return int(cands[int(np.argmax(d))])


def run_phys(task, own, selector, coverage, M, bmax=60, record=("SHQ_ATS_H", "PHR_NRMAP")):
    """One adaptive trajectory: own construction, selector in {margin, BALD_GRID, BALD_LAP, MAXIMIN}, coverage None or every-k."""
    set_manifest(M); rev = K._rev_with(task, M, []); Z = P.zstd(task); startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    which = tuple(dict.fromkeys(list(record) + [own])); bald = selector in ("BALD_GRID", "BALD_LAP")
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        out, info = state(task, rev, Z, np.r_[task["test"], cands], which=which, want_bald=bald)
        e = {"budget": b, "p": {own: LN._f32(out[own][:nt])}, "p_all": {k: LN._f32(v[:nt]) for k, v in out.items()},
             "info": {k: v for k, v in info.items() if k in ("one_class", "K", "fallbacks", "phr_w", "recal")}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        q = b + 1
        if info["one_class"]:
            nxt = LN.next_on_path(task, rev); how = "path"
        elif selector == "MAXIMIN" or (coverage and q > P.B0 and (q - P.B0) % coverage == 0):
            nxt = _farthest(Z, rev, cands); how = "coverage" if selector != "MAXIMIN" else "maximin"
        else:
            if selector == "margin":
                sc = -np.abs(out[own][nt:] - 0.5)
            else:
                sc = np.asarray(info["bald_grid" if selector == "BALD_GRID" else "bald_lap"][nt:])
            k = int(np.argmax(sc)); nxt = int(cands[k]); how = selector
            e["sel"] = {"score": float(sc[k]), "p_own": float(out[own][nt + k])}
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "block": task.get("block"), "construction": own, "selector": selector,
            "coverage": coverage, "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def run_e1s(task, M, bmax=60):
    """E1RAW / E1CAL + straddle with the task's own startup: the loop of rc19b_keyhole.run_adaptive (K = 10) unchanged."""
    rev = K._rev_with(task, M, []); Z = P.zstd(task); startup(task, rev); which = K.ADAPTIVE["E1S"]
    rng = np.random.default_rng([P.SPLIT_SEED, 19, task["repeat"], task["fold"]]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; t1 = time.process_time()
        out, scores, info, cands = K.constructions(task, rev, Z, which, rng, K=10)
        e = {"budget": b, "p": {k: LN._f32(out[k]) for k in which}, "info": info}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        sc = scores.get("E1"); nxt = LN.next_on_path(task, rev) if sc is None else int(cands[int(np.argmax(sc))])
        e["cpu_s"] = time.process_time() - t1; e["how"] = "path" if sc is None else "straddle"; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "block": task.get("block"), "arm": "E1S", "K": "10", "record_all": False,
            "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}
