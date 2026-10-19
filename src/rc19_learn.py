"""RC19 pooled from-scratch learners (regression, region, Keyhole label) on top of the paid-only reveal interface.

Every trajectory starts with the common feature-only startup (first B0 = 8 points of the task's label-free maximin path), which
is PAID and counted; then one query per step. After each query the learner refits on ALL revealed rows (ordinary sequential
updating, as in G3/E1 - not a new method). Learners read only rc19_pool.Reveal arrays (NaN / -1 outside the paid rows) and the
public inputs; source batch is never read. Inference optimisation: for label-free designs (MAXIMIN, RANDOM) the choice does not
depend on the model, so regression fits are made only at the recorded budgets; adaptive designs refit at every step.

Regression models (one GP engine, src/rc18_gp.py; fitting code src.rc18_campaign.fit_model, imported unchanged):
  M0    per-output GP, Matern-3/2 ARD on standardised log inputs, constant mean, homoskedastic, ML-II;
  M0Q   M0 + paid-record quality: a paid run whose record ended before 0.95 x its own planned end gets noise x 1e4;
  SHQ   ARD lengthscales shared by the 8 outputs of the paid runs + Q;
  *H    the same with the public physics coordinate log h = log P - 0.5 log VX - 1.5 log LS added as a 5th standardised input.
Region: {spike log-ratio >= log 2}; selectors MAXIMIN, RANDOM, STRADDLE (1.96 sigma - |mu - tau|), TRUVAR (rc18_gp.truvar_lse,
  fixed beta = 1.96, eta = 0, latent-variance reduction over the unclassified set; falls back to straddle when that set is empty).
Label: G3_MARGIN (Week 18 G3), E1_STRADDLE / E1_MAXIMIN (Week 18 E1: depth GP + depth threshold from revealed pairs), and the
  from-scratch physics-output classifiers PHYSCF_* (cross-fitted) and PHYSMC_* (measured-trained, uncertainty-integrated).
  One-class rule: while the usable paid labels contain one class, every arm follows the label-free path and predicts the paid
  class rate (no threshold or constant learned from hidden data enters; E1's built-in log(111 um) default is never used).
"""
from __future__ import annotations

import time
import warnings

import numpy as np
from scipy.linalg import cho_solve
from scipy.special import expit

import src.rc18_campaign as C
import src.rc18_gp as G
import src.rc19_pool as P

TI = {c: k for k, c in enumerate(P.TARGETS)}
RESP = "vmax_spike_logratio"
TAU = float(np.log(2.0))
PHYS_SETS = {"A": ("log_A_um",), "AT": ("log_A_um", "tmax_T0_K"), "ATS": ("log_A_um", "tmax_T0_K", "vmax_spike_logratio"),
             "ALL": tuple(P.TARGETS)}          # every paid output, L2-regularised (no monitor-informed selection)


def design_inputs(task, model):
    Z = P.zstd(task)
    if model.endswith("H"):
        lx = np.log(task["X"]); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; p = task["pool"]
        Z = np.c_[Z, (h - h[p].mean()) / h[p].std()]
    return Z


def base(model):
    return model[:-1] if model.endswith("H") else model


def startup(task, rev):
    for i in task["path"][:P.B0]:
        rev.reveal(int(i))


def next_on_path(task, rev):
    s = set(rev.order)
    return int(next(int(i) for i in task["path"] if int(i) not in s))


def _f32(a):
    return [None if not np.isfinite(v) else float(np.float32(v)) for v in np.asarray(a, float)]


# ======================================================================================== regression
def run_reg(task, model, acq, bmax, record=None, acq_cols=P.TARGETS, M=None):
    rev = P.Reveal(task, M); Z = design_inputs(task, model); pool, test = task["pool"], task["test"]; ids = task["ids"]
    record = sorted(set(record or range(P.B0, bmax + 1, 4)) | {bmax}); rng = np.random.default_rng([P.SPLIT_SEED, 7, task["repeat"], task["fold"]])
    startup(task, rev); evals = []; t0 = time.time(); fit_s = 0.0
    while True:
        b = rev.queries
        need_fit = acq == "MOIVR" or b in record
        if need_fit:
            t1 = time.time(); fits = C.fit_model(base(model), Z, rev.paid_Y(), rev.paid, list(P.TARGETS), emu=None, short=rev.paid_short()); fit_s += time.time() - t1
        if b in record:
            pr = {}
            for c in P.TARGETS:
                f = fits.get(c)
                if f is None:
                    pr[c] = None; continue
                m, lat, obs = f.predict(test); pr[c] = [_f32(m), _f32(obs)]
            evals.append({"budget": b, "pred": pr, "n_finite_paid": {c: int(np.isfinite(rev.paid_Y()[rev.paid, TI[c]]).sum()) for c in P.TARGETS}})
        if b >= bmax:
            break
        unpaid = np.setdiff1d(pool, rev.paid)
        if acq == "MAXIMIN":
            nxt = next_on_path(task, rev)
        elif acq == "RANDOM":
            nxt = int(rng.choice(unpaid))
        elif acq == "MOIVR":
            sub = [c for c in acq_cols if fits.get(c) is not None and isinstance(fits[c], C.Fitted)]
            if not sub:
                nxt = next_on_path(task, rev)
            else:
                sc = C.mo_ivr({c: fits[c] for c in sub}, sub, Z, rev.paid, unpaid, pool, rev.paid_Y()[:, [TI[c] for c in sub]]); nxt = int(unpaid[int(np.argmax(sc))])
        else:
            raise ValueError(acq)
        rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": acq, "paid": rev.order, "paid_ids": [ids[i] for i in rev.order],
            "test_ids": [ids[i] for i in test], "evals": evals, "seconds": time.time() - t0, "fit_seconds": fit_s, "queries": rev.queries}


def full_reg(task, model, M=None):
    """Offline reference only (never a learner state): every pool row revealed, one fit, test predictions. Used to see the
    attainable accuracy when setting ABSOLUTE target levels before the final freeze."""
    rev = P.Reveal(task, M); Z = design_inputs(task, model); t0 = time.time()
    for i in task["pool"]:
        rev.reveal(int(i))
    fits = C.fit_model(base(model), Z, rev.paid_Y(), rev.paid, list(P.TARGETS), emu=None, short=rev.paid_short())
    pr = {c: (None if fits.get(c) is None else [_f32(x) for x in (fits[c].predict(task["test"])[0], fits[c].predict(task["test"])[2])]) for c in P.TARGETS}
    return {"repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": "FULL_POOL", "test_ids": [task["ids"][i] for i in task["test"]],
            "evals": [{"budget": rev.queries, "pred": pr}], "seconds": time.time() - t0}


# ======================================================================================== region
def run_region(task, model, acq, bmax, M=None):
    rev = P.Reveal(task, M); Z = design_inputs(task, model); pool, test = task["pool"], task["test"]; ids = task["ids"]
    rng = np.random.default_rng([P.SPLIT_SEED, 11, task["repeat"], task["fold"]]); shared = base(model).startswith("SH")
    cols = list(P.TARGETS) if shared else [RESP]; startup(task, rev); evals = []; t0 = time.time(); how = []
    while True:
        b = rev.queries; Yp = rev.paid_Y() if shared else rev.paid_Y()[:, [TI[RESP]]]
        fits = C.fit_model(base(model), Z, Yp, rev.paid, cols, emu=None, short=rev.paid_short()); f = fits.get(RESP)
        if f is not None:
            m, lat, _ = f.predict(test); evals.append({"budget": b, "mean": _f32(m), "lat": _f32(lat)})
        else:
            evals.append({"budget": b, "mean": None, "lat": None})
        if b >= bmax:
            break
        unpaid = np.setdiff1d(pool, rev.paid)
        if acq == "MAXIMIN" or f is None:
            nxt = next_on_path(task, rev); how.append("path")
        elif acq == "RANDOM":
            nxt = int(rng.choice(unpaid)); how.append("random")
        elif acq == "STRADDLE":
            mu, lv, _ = f.predict(unpaid); nxt = int(unpaid[int(np.argmax(G.straddle(mu, lv, TAU)))]); how.append("straddle")
        elif acq == "TRUVAR":
            mu, lv, _ = f.predict(unpaid)
            if isinstance(f, C.Fitted):
                sc, Mset = G.truvar_lse(f.g, Z[unpaid], None, mu, lv, TAU)
            else:
                sc = np.zeros(len(unpaid))
            if np.any(sc > 0):
                nxt = int(unpaid[int(np.argmax(sc))]); how.append("truvar")
            else:
                nxt = int(unpaid[int(np.argmax(G.straddle(mu, lv, TAU)))]); how.append("truvar_fallback_straddle")
        else:
            raise ValueError(acq)
        rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": acq, "paid": rev.order, "paid_ids": [ids[i] for i in rev.order],
            "test_ids": [ids[i] for i in test], "evals": evals, "how": how, "seconds": time.time() - t0, "queries": rev.queries}


# ======================================================================================== Keyhole label
def _loo(g, y):
    """Closed-form leave-one-out predictive mean and observation variance of a fitted rc18_gp.GP at its training rows
    (hyperparameters from the full paid fit)."""
    Kinv = cho_solve(g.c, np.eye(len(g.alpha))); d = np.maximum(np.diag(Kinv), 1e-12)
    return np.asarray(y, float) - g.sd * g.alpha / d, g.sd ** 2 / d


def phys_classifier(Z, rev, feats, rows_eval, variant, rng, S=200):
    """From-scratch physics-output-assisted Keyhole classifier (both variants learn everything from the paid runs only).
    Response model: SHQ (shared lengthscales across the chosen outputs + paid-record quality) on the paid rows.
    PHYSCF (cross-fitted): g = logistic regression (L2, C = 1) on the standardised LEAVE-ONE-OUT predicted outputs of the paid
      rows (every paid row with a label; predicted summaries exist even where a channel is missing); deployed on the predictive
      MEANS at new x, so training and deployment use the same kind of input (predicted summaries).
    PHYSMC (measured, integrated): g trained on the MEASURED outputs of the paid rows that have all of them; deployed as
      P(K|x) = mean over S draws f_s ~ N(mu(x), v_obs(x)) of g(f_s) (response uncertainty propagated; predicted outputs are
      functions of x, not measurements).
    Returns (p_eval, info) or (None, info) when g cannot be fitted (fewer than 2 classes among its training rows)."""
    from sklearn.linear_model import LogisticRegression
    cols = list(feats); Y = rev.paid_Y()[:, [TI[c] for c in cols]]; paid = rev.paid; y = rev.paid_y()
    fits = C.fit_model("SHQ" if len(cols) > 1 else "M0Q", Z, Y, paid, cols, emu=None, short=rev.paid_short())
    if any(fits.get(c) is None or not isinstance(fits[c], C.Fitted) for c in cols):
        return None, {"status": "response_fit_unavailable"}
    mu_e = np.column_stack([fits[c].predict(rows_eval)[0] for c in cols]); v_e = np.column_stack([fits[c].predict(rows_eval)[2] for c in cols])
    if variant == "CF":
        F = np.full((len(paid), len(cols)), np.nan)
        for k, c in enumerate(cols):
            f = fits[c]; L = paid[np.isfinite(Y[paid, k])]; m_loo, _ = _loo(f.g, Y[L, k]); pos = {int(i): j for j, i in enumerate(paid)}
            F[[pos[int(i)] for i in L], k] = m_loo
            miss = ~np.isfinite(F[:, k])
            if miss.any():
                F[miss, k] = f.predict(paid[miss])[0]                     # unpaid channel: predicted summary of that paid run
        yt = y[paid]
    else:
        ok = np.all(np.isfinite(Y[paid]), axis=1); F = Y[paid][ok]; yt = y[paid][ok]
    if len(set(yt.tolist())) < 2:
        return None, {"status": "one_class_in_classifier_rows"}
    mu_f, sd_f = F.mean(0), F.std(0) + 1e-12
    lr = LogisticRegression(C=1.0, max_iter=5000).fit((F - mu_f) / sd_f, yt)
    if variant == "CF":
        p = lr.predict_proba((mu_e - mu_f) / sd_f)[:, 1]
    else:
        D = mu_e[None] + np.sqrt(v_e)[None] * rng.standard_normal((S,) + mu_e.shape)
        p = lr.predict_proba(((D - mu_f) / sd_f).reshape(-1, len(cols)))[:, 1].reshape(S, -1).mean(0)
    return p, {"status": "ok", "n_train": int(len(yt)), "coef": lr.coef_[0].tolist()}


def run_label(task, arm, bmax, M=None):
    import src.week18_engine as E
    rev = P.Reveal(task, M); X = task["X"]; Z = P.zstd(task); pool, test = task["pool"], task["test"]; ids = task["ids"]
    rng = np.random.default_rng([P.SPLIT_SEED, 13, task["repeat"], task["fold"]]); startup(task, rev); evals = []; t0 = time.time(); fails = 0
    while True:
        b = rev.queries; L = rev.paid; y_p = rev.paid_y(); A_p = rev.paid_A()
        usable = np.isfinite(A_p[L]) if (arm.startswith("E1") or arm.startswith("PHYS")) else np.ones(len(L), bool)
        two = len(set(y_p[L][usable].tolist())) == 2; cands = np.setdiff1d(pool, L); p = None; score = None; status = "one_class"
        if two:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tk = {"X": X, "y": y_p, "pool": pool, "prior": np.array([], int), "depth": A_p}
                try:
                    if arm == "G3_MARGIN":
                        f = E.fit_learner(("G3", "mlii"), tk, list(L), None, {"kernel": None, "b0": len(L)})
                        p = np.asarray(E.proba(f, X[test]), float); score = -np.abs(np.asarray(E.proba(f, X[cands]), float) - 0.5); status = "g3"
                    elif arm.startswith("E1"):
                        f = E.fit_learner(("GPR_depth", "mlii"), tk, list(L), None, {"kernel": None, "b0": len(L)})
                        p = np.asarray(E.proba(f, X[test]), float); mc, vc = E.latent(f, X[cands]); score = 1.96 * np.sqrt(vc) - np.abs(mc); status = "e1"
                    elif arm.startswith("PHYS"):
                        variant, rest = arm[4:6], arm.split("_")[1]; feats = PHYS_SETS[rest]
                        pe, info = phys_classifier(Z, rev, feats, np.r_[test, cands], variant, rng)
                        if pe is not None:
                            p = pe[:len(test)]; score = -np.abs(pe[len(test):] - 0.5); status = "phys"
                        else:
                            status = info["status"]
                    else:
                        raise ValueError(arm)
                except Exception as ex:                                       # recorded numerical failure; fallback below
                    fails += 1; status = f"fit_failed:{type(ex).__name__}"
        if p is None:
            p = np.full(len(test), float(np.mean(y_p[L])))                    # paid class rate (no hidden-data threshold)
        evals.append({"budget": b, "p": _f32(p), "status": status})
        if b >= bmax:
            break
        if not two or arm.endswith("MAXIMIN") or score is None:
            nxt = next_on_path(task, rev)
        else:
            nxt = int(cands[int(np.argmax(score))])
        rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": rev.order, "paid_ids": [ids[i] for i in rev.order],
            "test_ids": [ids[i] for i in test], "evals": evals, "fit_failures": fails, "seconds": time.time() - t0, "queries": rev.queries}
