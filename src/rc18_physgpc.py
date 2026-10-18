"""RC18 addendum A4 (exploratory; PROTOCOL_ADDENDUM_A4.md): hybrid label model = PHYS_TR prior + NEW-label residual GPC.

At budget b: P_phys(x) = PHYS_TR probability (src/rc18_physlabel.py: TRSQ-predicted outputs + classifier g on OLD observed
outputs and paid NEW outputs, Monte Carlo); latent prior mean m(x) = logit(clip(P_phys, 0.01, 0.99)); a fixed-mean Laplace GP
classifier (Week 17/18 SafeguardedFixedMeanLaplaceGPC, residual kernel M3 = C x Matern3/2-ARD, ML-II) is fitted on the paid NEW
labels with that mean (fold-standardised log inputs); P(K|x) = its predictive probability. b = 0 (no paid labels): P_phys.
Arms: PHYS_GPC_MARGIN (common 8-point start, then argmin |P - 0.5|), PHYS_GPC_MAXIMIN (label-free path from B0).
A GPC fit failure falls back to P_phys at that budget and is recorded. Imports the frozen modules unchanged.
    python -m src.rc18_physgpc work
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
from scipy.special import expit, logit

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_physlabel as PL

REPEATS = (5, 6, 7, 8)
D = C.OUT / "physgpc"
ARMS = ("PHYS_GPC_MARGIN", "PHYS_GPC_MAXIMIN")


def run(task, arm, Tt, XO, yO, bmax=40):
    from sklearn.linear_model import LogisticRegression
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC as GPC
    GPC.FP_TOL = 1e-9
    ids = np.asarray(task["ids"]).astype(str); Z = C.zstd(task); pool, test = task["pool"], task["test"]; y = np.asarray(task["y"], int)
    cols = C.ALL_T; Y = Tt.reindex(ids)[cols].to_numpy(float); short = C.qa_short(ids)
    e = C.emulator_at(ids); E = {k: e[k].to_numpy(float) for k in e.columns}; gi = [cols.index(c) for c in PL.GF]
    start = 0 if arm.endswith("MAXIMIN") else C.B0
    L = [int(i) for i in task["path"][:start]]; evals = []; t0 = time.time(); fails = 0; allidx = np.r_[pool, test]
    for b in range(start, bmax + 1):
        paid = np.asarray(L, int); fits = C.fit_model("TRSQ", Z, Y, paid, cols, emu=E, short=short)
        okp = paid[np.all(np.isfinite(Y[np.ix_(paid, gi)]), axis=1) & ~short[paid]] if len(paid) else paid
        Xg = np.vstack([XO, Y[np.ix_(okp, gi)]]) if len(okp) else XO; yg = np.r_[yO, y[okp]] if len(okp) else yO
        mu, sd = Xg.mean(0), Xg.std(0) + 1e-12; g = LogisticRegression(C=1.0, max_iter=5000).fit((Xg - mu) / sd, yg)
        rng = np.random.default_rng(91000 + 1000 * task["repeat"] + 10 * task["fold"] + b)
        M = np.zeros((len(allidx), len(PL.GF))); V = np.zeros_like(M)
        for j, c in enumerate(PL.GF):
            m_, lat, obs = fits[c].predict(allidx); M[:, j] = m_; V[:, j] = obs
        S = M[None] + np.sqrt(V)[None] * rng.standard_normal((PL.NS, len(allidx), len(PL.GF)))
        Pphys = g.predict_proba(((S - mu) / sd).reshape(-1, len(PL.GF)))[:, 1].reshape(PL.NS, len(allidx)).mean(0)
        pmap = np.full(len(ids), np.nan); pmap[allidx] = Pphys; mlat = logit(np.clip(pmap, 0.01, 0.99))
        status = "prior_only"
        if len(paid):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    gp = GPC(p13.residual_kernel("M3", 100.0), optimize=True).fit(Z[paid], y[paid], mlat[paid])
                    P = lambda idx: gp.predict_proba(Z[idx], mlat[idx])[:, 1]
                    status = "gpc"
            except Exception:
                fails += 1; P = lambda idx: pmap[idx]; status = "gpc_failed_prior_used"
        else:
            P = lambda idx: pmap[idx]
        p = np.asarray(P(np.asarray(test)), float); evals.append({"budget": b, "p": p.tolist(), "status": status})
        if b == bmax:
            break
        if arm.endswith("MAXIMIN"):
            nxt = int([i for i in task["path"] if i not in set(L)][0])
        else:
            cands = np.setdiff1d(pool, L); pc = np.asarray(P(cands), float); nxt = int(cands[int(np.argmin(np.abs(pc - 0.5)))])
        L.append(nxt)
    return {"population": "NEW", "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [ids[i] for i in L],
            "test_ids": [ids[i] for i in test], "evals": evals, "gpc_failures": fails, "seconds": time.time() - t0}


def work():
    import src.rc18_final as F
    F.check(); RC.limit_threads(1); Tt = C.targets("NEW"); XO, yO = PL.old_training(); U = {}
    for t in C.tasks("NEW", REPEATS):
        for a in ARMS:
            U[f"NEW__r{t['repeat']}_f{t['fold']}__label__{a}"] = (t, a)
    def fn(name):
        t, a = U[name]; return run(t, a, Tt, XO, yO)
    RC.run_units(list(U), fn, D / "units", D / "locks", D / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    {"work": work}[sys.argv[1]]()
