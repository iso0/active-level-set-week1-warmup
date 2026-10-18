"""RC18 addendum A3 (exploratory; PROTOCOL_ADDENDUM_A3.md): physics-mediated, cross-campaign Keyhole label model for NEW.

  P(K | x) = E[ g(Y(x)) ],   Y(x) ~ TRSQ predictive distribution of (log A, spike log-ratio, max temperature T0) at x,
  g = logistic regression (C = 1, standardised) on OBSERVED outputs of all OLD runs (historical) + the PAID NEW runs
      (truncated records excluded by the Q rule), refitted at every budget; expectation by 400 Monte Carlo draws
      (independent Gaussian marginals, observation variance; fixed seed per task and budget).
Arms: PHYS_TR_MAXIMIN (frozen label-free path from B0) and PHYS_TR_MARGIN (argmin |P - 0.5| over unpaid pool runs from B8,
after the common 8-point start). Budgets B0-B40 (MAXIMIN) / B8-B40 (MARGIN). Never uses unpaid/test outputs or labels,
short-K or q20 membership. Imports the frozen modules unchanged.
    python -m src.rc18_physlabel work
"""
from __future__ import annotations

import sys
import time

import numpy as np
from sklearn.linear_model import LogisticRegression

import src.rc18_campaign as C
import src.rc18_common as RC

REPEATS = (5, 6, 7, 8)
D = C.OUT / "physlabel"
GF = ["log_A_um", "vmax_spike_logratio", "tmax_T0_K"]
ARMS = ("PHYS_TR_MAXIMIN", "PHYS_TR_MARGIN")
NS = 400


def old_training():
    TO = C.targets("OLD"); import src.jdl_physical_pilot as PP
    import pandas as pd
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); y = W.loc[TO.index].y.to_numpy().astype(int)
    X = TO[GF].to_numpy(float); ok = np.all(np.isfinite(X), axis=1) & ~C.qa_short(np.asarray(TO.index))
    return X[ok], y[ok]


def run(task, arm, Tt, XO, yO, bmax=40):
    ids = np.asarray(task["ids"]).astype(str); Z = C.zstd(task); pool, test = task["pool"], task["test"]; y = np.asarray(task["y"], int)
    cols = C.ALL_T; Y = Tt.reindex(ids)[cols].to_numpy(float); short = C.qa_short(ids)
    e = C.emulator_at(ids); E = {k: e[k].to_numpy(float) for k in e.columns}; gi = [cols.index(c) for c in GF]
    start = 0 if arm.endswith("MAXIMIN") else C.B0
    L = [int(i) for i in task["path"][:start]]; evals = []; t0 = time.time()
    for b in range(start, bmax + 1):
        paid = np.asarray(L, int); fits = C.fit_model("TRSQ", Z, Y, paid, cols, emu=E, short=short)
        okp = paid[np.all(np.isfinite(Y[np.ix_(paid, gi)]), axis=1) & ~short[paid]] if len(paid) else paid
        Xg = np.vstack([XO, Y[np.ix_(okp, gi)]]) if len(okp) else XO; yg = np.r_[yO, y[okp]] if len(okp) else yO
        mu, sd = Xg.mean(0), Xg.std(0) + 1e-12; g = LogisticRegression(C=1.0, max_iter=5000).fit((Xg - mu) / sd, yg)
        def proba(idx):
            rng = np.random.default_rng(81000 + 1000 * task["repeat"] + 10 * task["fold"] + b)
            M = np.zeros((len(idx), len(GF))); V = np.zeros_like(M)
            for j, c in enumerate(GF):
                m, lat, obs = fits[c].predict(np.asarray(idx)); M[:, j] = m; V[:, j] = obs
            S = M[None, :, :] + np.sqrt(V)[None, :, :] * rng.standard_normal((NS, len(idx), len(GF)))
            P = g.predict_proba(((S - mu) / sd).reshape(-1, len(GF)))[:, 1].reshape(NS, len(idx))
            return P.mean(0)
        p = proba(test); evals.append({"budget": b, "p": p.tolist(), "n_paid_used_in_g": int(len(okp))})
        if b == bmax:
            break
        if arm.endswith("MAXIMIN"):
            nxt = int([i for i in task["path"] if i not in set(L)][0])
        else:
            cands = np.setdiff1d(pool, L); pc = proba(cands); nxt = int(cands[int(np.argmin(np.abs(pc - 0.5)))])
        L.append(nxt)
    return {"population": "NEW", "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [ids[i] for i in L],
            "test_ids": [ids[i] for i in test], "evals": evals, "seconds": time.time() - t0}


def work():
    import src.rc18_final as F
    F.check(); RC.limit_threads(1); Tt = C.targets("NEW"); XO, yO = old_training(); U = {}
    for t in C.tasks("NEW", REPEATS):
        for a in ARMS:
            U[f"NEW__r{t['repeat']}_f{t['fold']}__label__{a}"] = (t, a)
    def fn(name):
        t, a = U[name]; return run(t, a, Tt, XO, yO)
    RC.run_units(list(U), fn, D / "units", D / "locks", D / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    {"work": work}[sys.argv[1]]()
