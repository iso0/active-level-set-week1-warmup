"""RC19B Keyhole workstream: honest cross-fitted physical-response classifiers and a calibrated E1, on the RC19 paid-only contract.

Probability constructions at one paid state (all learned from the paid runs only; inputs x = (P, VX, LS, ST)):
  E1RAW   frozen Week 18 E1: GP on log depth + depth threshold u from the revealed (depth, label) pairs;
          p = Phi((mu_A - u) / sigma_A).
  E1CAL   E1RAW passed through a small-sample probability map fitted on HONEST out-of-fold E1 predictions of the paid runs:
          logit p_cal = a + c * logit p_E1, MAP with a Gaussian prior centred on the identity (a ~ N(0, 1^2), c ~ N(1, 0.5^2)).
          Out-of-fold = for each of K folds of the paid set, E1's depth GP, its normalisation AND its threshold are refitted
          without that fold. A training fold with one class predicts its class rate (no full-data constant).
  DEPTHCF depth-only classifier: g = L2 logistic (C = 1) on standardised K-fold cross-fitted predicted log depth.
  ATSCF   physical-response classifier: the same g on cross-fitted predicted (log A, temperature T0, spike log-ratio).
          Cross-fitting: for each fold the upstream response model (SHQ: lengthscales shared by the chosen outputs + paid-record
          quality; per-output GP normalisation) is refitted on the paid runs OUTSIDE the fold and predicts the fold. The deployed
          model is the same construction refitted on all paid runs; g's feature scaling uses the out-of-fold features only.
  ATSAPPROX the RC19 PHYSCF_ATS construction (closed-form leave-one-out with the FULL-fit hyperparameters and normalisation):
          an approximation of cross-fitting, kept as the historical control.
  G3      frozen Week 18 direct GP classifier (reference).
Folds: K = min(5, number of paid runs); fold of the j-th paid run (in query order) = j mod K (frozen rule). Fold fits with
fewer than 3 usable rows for an output fall back to that fold's training mean for the output (counted). Every construction
uses the one-class rule of RC19 (paid class rate until both classes are revealed).
"""
from __future__ import annotations

import time
import warnings

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

import src.rc18_campaign as C
import src.rc19_learn as LN
import src.rc19_pool as P

KMAX = 5
ATS = ("log_A_um", "tmax_T0_K", "vmax_spike_logratio")
DEPTH = ("log_A_um",)
CAL_PRIOR = (1.0, 0.5)                       # prior SD of intercept a and of slope c around the identity map


def folds(n, k=KMAX):
    """k = None means exact leave-one-out (k = n): every held-out run gets its own refit on the other n - 1 runs."""
    k = int(n if k is None else min(k, n)); return np.arange(n) % k, k


# ======================================================================================== cross-fitted response features
def cf_features(Z, rev, feats, rows_eval, K=KMAX):
    """Honest K-fold out-of-fold predicted features for the paid runs + full-fit predictions at rows_eval."""
    cols = list(feats); paid = rev.paid; Yall = rev.paid_Y()[:, [LN.TI[c] for c in cols]]; short = rev.paid_short()
    model = "SHQ" if len(cols) > 1 else "M0Q"; fold, k = folds(len(paid), K); F = np.full((len(paid), len(cols)), np.nan); fb = 0
    for j in range(k):
        tr, te = paid[fold != j], paid[fold == j]
        Ytr = np.full_like(Yall, np.nan); Ytr[tr] = Yall[tr]                   # the fold's outcomes never enter its fit
        fits = C.fit_model(model, Z, Ytr, tr, cols, emu=None, short=short)
        for kk, c in enumerate(cols):
            f = fits.get(c)
            if f is None:
                v = Yall[tr, kk]; v = v[np.isfinite(v)]; F[fold == j, kk] = float(np.mean(v)) if len(v) else 0.0; fb += 1
            else:
                F[fold == j, kk] = f.predict(te)[0]
    full = C.fit_model(model, Z, Yall, paid, cols, emu=None, short=short)
    E = np.column_stack([(full[c].predict(rows_eval)[0] if full.get(c) is not None else np.full(len(rows_eval), np.nanmean(Yall[paid, kk])))
                         for kk, c in enumerate(cols)])
    return F, E, {"K": k, "fold_fallbacks": fb}


def cf_classifier(Z, rev, feats, rows_eval, K=KMAX):
    from sklearn.linear_model import LogisticRegression
    F, E, info = cf_features(Z, rev, feats, rows_eval, K); y = rev.paid_y()[rev.paid]
    if len(set(y.tolist())) < 2:
        return None, {**info, "status": "one_class"}
    mu, sd = F.mean(0), F.std(0) + 1e-12; g = LogisticRegression(C=1.0, max_iter=5000).fit((F - mu) / sd, y)
    return g.predict_proba((E - mu) / sd)[:, 1], {**info, "status": "ok", "coef": g.coef_[0].tolist()}


# ======================================================================================== E1 and its calibrated version
def _e1_fit(X, rev, rows):
    import src.week18_engine as E
    y_p = rev.paid_y(); A_p = rev.paid_A(); tk = {"X": X, "y": y_p, "pool": rev._pool_idx, "prior": np.array([], int), "depth": A_p}
    return E.fit_learner(("GPR_depth", "mlii"), tk, list(rows), None, {"kernel": None, "b0": len(rows)})


def e1_oof(X, rev, K=KMAX):
    """Honest out-of-fold E1 probabilities of the paid runs (depth GP, normalisation and threshold refitted per fold)."""
    import src.week18_engine as E
    paid = rev.paid; y = rev.paid_y(); A = rev.paid_A(); usable = paid[np.isfinite(A[paid])]; fold, k = folds(len(paid), K); p = np.full(len(paid), np.nan)
    for j in range(k):
        tr = paid[fold != j]; tr_u = tr[np.isfinite(A[tr])]; te_pos = np.flatnonzero(fold == j)
        if len(set(y[tr_u].tolist())) < 2 or len(tr_u) < 3:
            p[te_pos] = float(np.mean(y[tr])) if len(tr) else 0.5; continue
        f = _e1_fit(X, rev, tr_u); p[te_pos] = np.asarray(E.proba(f, X[paid[te_pos]]), float)
    return p


def calib_map(p_oof, y):
    z = logit(np.clip(p_oof, 1e-4, 1 - 1e-4)); sa, sc = CAL_PRIOR

    def nll(th):
        a, c = th; s = a + c * z; ll = y * s - np.logaddexp(0, s)
        return -np.sum(ll) + 0.5 * (a / sa) ** 2 + 0.5 * ((c - 1) / sc) ** 2
    r = minimize(nll, np.array([0.0, 1.0]), method="L-BFGS-B")
    return r.x


def e1_constructions(X, rev, rows_eval, cands, K=KMAX):
    """E1RAW and E1CAL at rows_eval, plus E1's straddle score on the candidates (the straddle path does not depend on the map)."""
    import src.week18_engine as E
    paid = rev.paid; A = rev.paid_A(); usable = paid[np.isfinite(A[paid])]
    f = _e1_fit(X, rev, usable); p_raw = np.asarray(E.proba(f, X[rows_eval]), float)
    mc, vc = E.latent(f, X[cands]); score = 1.96 * np.sqrt(vc) - np.abs(mc)
    po = e1_oof(X, rev, K); y = rev.paid_y()[paid]; a, c = calib_map(po, y)
    p_cal = expit(a + c * logit(np.clip(p_raw, 1e-4, 1 - 1e-4)))
    return p_raw, p_cal, score, {"cal_a": float(a), "cal_c": float(c)}


# ======================================================================================== one paid state -> every construction
def constructions(task, rev, Z, which, rng):
    import src.week18_engine as E
    X = task["X"]; test = task["test"]; cands = np.setdiff1d(task["pool"], rev.paid); rows = np.r_[test, cands]; nt = len(test)
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; usable = np.isfinite(A_p[L]); out, info, scores = {}, {}, {}
    two_all = len(set(y_p[L].tolist())) == 2; two_u = len(set(y_p[L][usable].tolist())) == 2
    rate = float(np.mean(y_p[L]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if "E1RAW" in which or "E1CAL" in which:
            if two_u:
                pr, pc, sc, inf = e1_constructions(X, rev, rows, cands); out["E1RAW"], out["E1CAL"] = pr[:nt], pc[:nt]; scores["E1"] = sc; info["E1CAL"] = inf
            else:
                out["E1RAW"] = out["E1CAL"] = np.full(nt, rate)
        for nm, feats in (("DEPTHCF", DEPTH), ("ATSCF", ATS)):
            if nm in which:
                if two_u:
                    pe, inf = cf_classifier(Z, rev, feats, rows)
                    if pe is not None:
                        out[nm] = pe[:nt]; scores[nm] = -np.abs(pe[nt:] - 0.5); info[nm] = inf
                    else:
                        out[nm] = np.full(nt, rate); info[nm] = inf
                else:
                    out[nm] = np.full(nt, rate)
        if "ATSAPPROX" in which:
            if two_u:
                pe, inf = LN.phys_classifier(Z, rev, ATS, rows, "CF", rng)
                out["ATSAPPROX"] = pe[:nt] if pe is not None else np.full(nt, rate)
                if pe is not None:
                    scores["ATSAPPROX"] = -np.abs(pe[nt:] - 0.5)
            else:
                out["ATSAPPROX"] = np.full(nt, rate)
        if "G3" in which:
            if two_all:
                tk = {"X": X, "y": y_p, "pool": task["pool"], "prior": np.array([], int), "depth": A_p}
                f = E.fit_learner(("G3", "mlii"), tk, list(L), None, {"kernel": None, "b0": len(L)})
                out["G3"] = np.asarray(E.proba(f, X[test]), float); scores["G3"] = -np.abs(np.asarray(E.proba(f, X[cands]), float) - 0.5)
            else:
                out["G3"] = np.full(nt, rate)
    return out, scores, info, cands


def _rev_with(task, M, paid_rows):
    rev = P.Reveal(task, M); rev._pool_idx = task["pool"]
    for i in paid_rows:
        rev.reveal(int(i))
    return rev


# ======================================================================================== matched-path replay (development)
REPLAY_WHICH = ("E1RAW", "E1CAL", "DEPTHCF", "ATSCF", "ATSAPPROX", "G3")


def replay_unit(task, unit, M, budgets):
    """Every construction on the SAME paid prefixes of an existing RC19 trajectory (identical outcomes and budgets)."""
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    rng = np.random.default_rng([P.SPLIT_SEED, 17, task["repeat"], task["fold"]]); evals = []; t0 = time.time(); tc = {}
    for b in budgets:
        rev = _rev_with(task, M, paid[:b]); t1 = time.time()
        out, _, info, _ = constructions(task, rev, Z, REPLAY_WHICH, rng)
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}, "info": info}); tc[b] = time.time() - t1
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(budgets)], "test_ids": unit["test_ids"],
            "evals": evals, "seconds": time.time() - t0, "seconds_per_budget": tc}


def replay_k_unit(task, unit, M, budgets, Ks=(10, None)):
    """Fold-size factor on the same paid prefixes: ATSCF / DEPTHCF / E1CAL with K = 10 and exact refit-LOO (K = None)."""
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; X = task["X"]; test = task["test"]; evals = []; t0 = time.time(); tc = {}
    for b in budgets:
        rev = _rev_with(task, M, paid[:b]); y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; two_u = len(set(y_p[L][np.isfinite(A_p[L])].tolist())) == 2
        rate = float(np.mean(y_p[L])); out = {}; t1 = time.time(); cands = np.setdiff1d(task["pool"], L)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for K in Ks:
                tag = "LOO" if K is None else str(K)
                if not two_u:
                    out[f"ATSCF{tag}"] = out[f"DEPTHCF{tag}"] = out[f"E1CAL{tag}"] = np.full(len(test), rate); continue
                for nm, feats in (("ATSCF", ATS), ("DEPTHCF", DEPTH)):
                    pe, _ = cf_classifier(Z, rev, feats, test, K); out[f"{nm}{tag}"] = pe if pe is not None else np.full(len(test), rate)
                _, pc, _, _ = e1_constructions(X, rev, test, cands, K); out[f"E1CAL{tag}"] = pc
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}}); tc[b] = time.time() - t1
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(budgets)], "test_ids": unit["test_ids"],
            "evals": evals, "seconds": time.time() - t0, "seconds_per_budget": tc}


# ======================================================================================== adaptive trajectories (final)
ADAPTIVE = {"E1S": ("E1RAW", "E1CAL"), "ATSCF_MARGIN": ("ATSCF",), "DEPTHCF_MARGIN": ("DEPTHCF",), "G3_MARGIN": ("G3",), "ATSAPPROX_MARGIN": ("ATSAPPROX",)}
SCORE_OF = {"E1S": "E1", "ATSCF_MARGIN": "ATSCF", "DEPTHCF_MARGIN": "DEPTHCF", "G3_MARGIN": "G3", "ATSAPPROX_MARGIN": "ATSAPPROX"}


def run_adaptive(task, arm, bmax, M=None):
    """One adaptive trajectory: the arm's own acquisition on its own probability construction (E1S records E1RAW and E1CAL on
    E1's straddle path, which does not depend on the probability map)."""
    M = P.manifest() if M is None else M; rev = _rev_with(task, M, []); Z = P.zstd(task); LN.startup(task, rev)
    rng = np.random.default_rng([P.SPLIT_SEED, 19, task["repeat"], task["fold"]]); evals = []; t0 = time.time(); which = ADAPTIVE[arm]
    while True:
        b = rev.queries; out, scores, info, cands = constructions(task, rev, Z, which, rng)
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}, "info": info})
        if b >= bmax:
            break
        sc = scores.get(SCORE_OF[arm])
        nxt = LN.next_on_path(task, rev) if sc is None else int(cands[int(np.argmax(sc))])
        rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order],
            "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals, "seconds": time.time() - t0, "queries": rev.queries}
