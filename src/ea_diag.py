"""EA study, stage 1 diagnostics (PROTOCOL_EA_HYPOTHESES.md, registered in d4dc329d before any EA computation).

On the RECORDED HA_LEAN margin paths of the EL-1 forward stage (STD repeats 83-122, K5 startups 25-32, K4 startups 9-16) and, at each
budget b, the SAME first b paid runs, the rung ladder (classifier = HA_LEAN learned-regularisation Laplace logistic unless stated;
a = log active maximum depth; F = honest K = 10 out-of-fold emulator means; E = full-fit emulator mean):
  deployable   R0_L (F_L / E_L, = recorded A)  R0_T (F_T / E_T, = recorded D)  R1a_L (in-sample E_L at paid / E_L)
               R1b_L (measured paid a; missing -> in-sample E_L / E_L)
  ORACLE (evaluator-only diagnostics, NOT methods, no query saving, no universal ceiling)
               R2_L, R2_T (R0 classifiers, TRUE test depth)   R3u (unlimited-data emulator predictions both sides)
               R3 (true a both sides)   R4 (R3 + the three log-input directions orthogonal to h, own prior scale)
               R5 (R3 + residual GP over (z_h, a), the RC21 grid)   R6 / R6u (large-n: trained on every pool run of the task)
"Unlimited-data emulator": the HA_LEAN depth GP (src.rc24_pac.depth_fit flat = the HA_LEAN emulator, same code path) fitted in 20
folds over the whole pool; every run is predicted by the fold model that excludes it (job ea-unlimited, run once).
Oracle rungs are evaluated only on test rows with a recorded depth (the one run without A is excluded from every rung's BA there).
    python -m src.ea_diag work ea-unlimited | ea-diag | ea-smoke
"""
from __future__ import annotations

import json
import sys
import time
import warnings

import numpy as np
from scipy.special import expit

import src.el_cross as X
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution"
EL = RC.ROOT / "outputs" / "research_campaign_20261024" / "opus_early_learning"
BUDS = tuple(range(8, 25)) + tuple(range(28, 61, 4))
UNL_FOLDS = 20; UNL_SEED = 26102026
RUNGS = ("R0_L", "R0_T", "R1a_L", "R1b_L", "R2_L", "R2_T", "R3u", "R3", "R4", "R5")
DCOL = PC.DEPTH_COL


# ======================================================================================== classifier families
def _plugin_mix(Ktt_list, Kte_list, kss_list, y, logprior):
    y = np.asarray(y, float); logw = np.empty(len(Ktt_list)); Pm = np.empty((len(Ktt_list), Kte_list[0].shape[0]))
    for g, (Ktt, Kte, kss) in enumerate(zip(Ktt_list, Kte_list, kss_list)):
        mode = PH.laplace(Ktt, y); m, _, _ = PH.predictive(mode, Kte, kss, plugin=True); Pm[g] = expit(m); logw[g] = mode["logZ"] + logprior[g]
    w = np.exp(logw - logw.max()); w /= w.sum(); return w @ Pm, w


def lin_u(htr, atr, Utr, y, hev, aev, Uev):
    """R4: learned-regularisation logistic on [z_h, a, U] (standardised on the training rows), tau_h, tau_F, tau_U in {0.5,1,2,4}^3."""
    Xtr = np.c_[htr, atr, Utr]; Xev = np.c_[hev, aev, Uev]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Ht, He = (Xtr - mu) / sd, (Xev - mu) / sd
    hh_t = np.outer(Ht[:, 0], Ht[:, 0]); aa_t = np.outer(Ht[:, 1], Ht[:, 1]); uu_t = Ht[:, 2:] @ Ht[:, 2:].T
    hh_e = np.outer(He[:, 0], Ht[:, 0]); aa_e = np.outer(He[:, 1], Ht[:, 1]); uu_e = He[:, 2:] @ Ht[:, 2:].T
    Kt, Ke, ks, lp = [], [], [], []
    for tf in PH.TAU_F:
        for th in PH.TAU_H:
            for tu in PH.TAU_F:
                Kt.append(PH.V0 + th ** 2 * hh_t + tf ** 2 * aa_t + tu ** 2 * uu_t); Ke.append(PH.V0 + th ** 2 * hh_e + tf ** 2 * aa_e + tu ** 2 * uu_e)
                ks.append(PH.V0 + th ** 2 * He[:, 0] ** 2 + tf ** 2 * He[:, 1] ** 2 + tu ** 2 * np.sum(He[:, 2:] ** 2, 1)); lp.append(0.0)
    return _plugin_mix(Kt, Ke, ks, y, np.asarray(lp))[0]


def res_ha(htr, atr, y, hev, aev):
    """R5: [z_h, a] linear terms + residual r(z_h, a) ~ GP(0, sr^2 RBF_ell) on the standardised 2-D features; RC21 grid and prior
    (P(sr = 0) = 1/2; 1/6 each for sr in {0.5, 1, 2}; ell uniform on {0.75, 1.5}); plug-in mixture over the posterior weights."""
    Xtr = np.c_[htr, atr]; Xev = np.c_[hev, aev]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Ht, He = (Xtr - mu) / sd, (Xev - mu) / sd
    Gt = PH.Gram(Ht, Ht, Ht, Ht); Ge = PH.Gram(He, Ht, He, Ht); Kt, Ke, ks, lp = [], [], [], []
    for (tf, th, sr, el, lpr) in PH.grid():
        Kt.append(Gt.K(tf, th, sr, el)); Ke.append(Ge.K(tf, th, sr, el))
        ks.append(PH.V0 + th ** 2 * He[:, 0] ** 2 + tf ** 2 * He[:, 1] ** 2 + (sr ** 2 if sr > 0 else 0.0)); lp.append(lpr)
    return _plugin_mix(Kt, Ke, ks, y, np.asarray(lp))[0]


def lin(Ftr, htr, y, Fev, hev):
    return C22.phr_family(np.asarray(Ftr, float).reshape(-1, 1), htr, y, np.asarray(Fev, float).reshape(-1, 1), hev, feats=(0,))[0]


# ======================================================================================== unlimited-data emulator (evaluator-only)
def unlimited(M):
    """Every run's log-depth prediction from the HA_LEAN depth GP fitted on all OTHER folds of a 20-fold partition of the pool."""
    ids = M.index.to_numpy(str); Xall = M[list(P.INPUTS)].to_numpy(float); n = len(ids)
    task = {"repeat": 0, "fold": 0, "ids": ids, "X": Xall, "pool": np.arange(n), "test": np.arange(0), "path": np.arange(n)}
    Z = P.zstd(task); fold = np.empty(n, int); fold[np.random.default_rng(UNL_SEED).permutation(n)] = np.arange(n) % UNL_FOLDS
    pred = np.full(n, np.nan); var = np.full(n, np.nan); log = []
    for j in range(UNL_FOLDS):
        tr = np.flatnonzero(fold != j); te = np.flatnonzero(fold == j); t0 = time.process_time()
        rev = K._rev_with(task, M, tr); f = PC.depth_fit(task, rev, Z, "flat")
        m, v = PC.depth_predict(f, Z, te); pred[te] = m; var[te] = v
        log.append({"fold": j, "n_train": int(len(tr)), "cpu_s": time.process_time() - t0})
    a = M.log_A_um.to_numpy(float); ok = np.isfinite(a)
    return {"ids": ids.tolist(), "pred": pred.tolist(), "latent_var": var.tolist(), "fold": fold.tolist(), "seed": UNL_SEED, "folds": UNL_FOLDS, "log": log,
            "rmse_all": float(np.sqrt(np.mean((pred[ok] - a[ok]) ** 2)))}


# ======================================================================================== one learner on its recorded path
def path_unit(cond, r, f):
    d = EL / "el-fwd" / "units"
    return RC.read_json_gz(d / (f"STD__r{r}_f{f}__L.json.gz" if cond == "STD" else f"{cond}__s{r}_b{f}__L.json.gz"))


def learner(task, unit, M, U, budgets=BUDS):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in unit["paid_ids"]]; te = np.asarray(task["test"])
    if [task["ids"][i] for i in te] != list(unit["test_ids"]):
        raise RuntimeError("recorded test set differs from the task")
    a_all = M.reindex(list(task["ids"])).log_A_um.to_numpy(float); u_all = U.reindex(list(task["ids"])).to_numpy(float)
    h = A.hcol(task); Uperp, _ = PH.transverse(task, Z); recA = {e["budget"]: e["p"]["HA_LEAN"] for e in unit["evals"]}; recD = {e["budget"]: e["p"]["HA_TREND"] for e in unit["cross"]["evals"]}
    ok_te = np.isfinite(a_all[te]); out = []; chkA = chkD = 0.0
    for b in budgets:
        t0 = time.process_time(); paid = paid_all[:b]; rev = K._rev_with(task, M, paid); L = rev.paid; y_p = rev.paid_y(); y = y_p[L]; A_p = rev.paid_A()
        usable = np.isfinite(A_p[L]); one = len(set(y_p[L][usable].tolist())) < 2; e = {"budget": b, "one_class": bool(one)}
        if one:
            c = np.full(len(te), float(np.mean(y))); e["p"] = {k: LN._f32(c) for k in RUNGS}; e["E_L"] = None; e["E_T"] = None
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                rows = np.r_[te, L]; R1 = A.cf(Z, rev, C23.DEPTH, "SHQ", rows, A.KF); FL = R1["F"][:, 0]; EL_te = R1["E"][:len(te), 0]; EL_paid = R1["E"][len(te):, 0]
                R2 = PC.cf_phys(task, rev, Z, te); FT = R2["F"][:, 0]; ET_te = R2["E"][:, 0]
                a_paid = np.where(np.isfinite(a_all[L]), a_all[L], EL_paid); a_te = np.where(ok_te, a_all[te], EL_te)   # missing test depth: excluded later
                p = {"R0_L": lin(FL, h[L], y, EL_te, h[te]), "R0_T": lin(FT, h[L], y, ET_te, h[te]), "R1a_L": lin(EL_paid, h[L], y, EL_te, h[te]),
                     "R1b_L": lin(a_paid, h[L], y, EL_te, h[te]), "R2_L": lin(FL, h[L], y, a_te, h[te]), "R2_T": lin(FT, h[L], y, a_te, h[te]),
                     "R3u": lin(u_all[L], h[L], y, u_all[te], h[te]), "R3": lin(a_paid, h[L], y, a_te, h[te]),
                     "R4": lin_u(h[L], a_paid, Uperp[L], y, h[te], a_te, Uperp[te]), "R5": res_ha(h[L], a_paid, y, h[te], a_te)}
            chkA = max(chkA, float(np.max(np.abs(LN._f32(p["R0_L"]) - np.asarray(recA[b], float))))); chkD = max(chkD, float(np.max(np.abs(LN._f32(p["R0_T"]) - np.asarray(recD[b], float)))))
            e["p"] = {k: LN._f32(v) for k, v in p.items()}; e["E_L"] = LN._f32(EL_te); e["E_T"] = LN._f32(ET_te)
        e["cpu_s"] = time.process_time() - t0; out.append(e)
    # large-n references (every pool run of the task with a recorded depth; evaluator-only)
    pool = np.asarray(task["pool"]); pk = pool[np.isfinite(a_all[pool])]; yk = M.reindex(list(task["ids"])).y.to_numpy(int)[pk]; a_te = np.where(ok_te, a_all[te], np.nanmean(a_all[pk]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        R6 = {"R6_lin": LN._f32(lin(a_all[pk], h[pk], yk, a_te, h[te])), "R6_res": LN._f32(res_ha(h[pk], a_all[pk], yk, h[te], a_te)),
              "R6u": LN._f32(lin(u_all[pk], h[pk], yk, u_all[te], h[te]))}
    return {"evals": out, "R6": R6, "test_has_depth": ok_te.tolist(), "check_R0_L_vs_recorded_A_maxabs": chkA, "check_R0_T_vs_recorded_D_maxabs": chkD}


def units(job):
    if job == "ea-unlimited":
        return [("UNLIMITED", ("unl",))]
    if job == "ea-diag":
        return ([(f"STD__r{r}_f{f}", ("diag", "STD", r, f)) for r in range(83, 123) for f in range(1, 6)]
                + [(f"K5__s{s}_b{b}", ("diag", "K5", s, b)) for s in range(25, 33) for b in range(1, 6)]
                + [(f"K4__s{s}_b{b}", ("diag", "K4", s, b)) for s in range(9, 17) for b in range(1, 5)])
    if job == "ea-smoke":
        return [("STD__r83_f1", ("smoke", "STD", 83, 1))]
    raise ValueError(job)


def load_unlimited():
    import pandas as pd
    u = RC.read_json_gz(OUT / "ea-unlimited" / "units" / "UNLIMITED.json.gz"); return pd.Series(u["pred"], index=u["ids"], dtype=float)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    if job == "ea-unlimited":
        def fn(name):
            return unlimited(M)
    else:
        U = load_unlimited(); T = X.tasks_for({n: (None, v[1], v[2], v[3]) for n, v in S.items()}, M)

        def fn(name):
            kind, c, r, f = S[name]; task = T[(c, r, f)]; u = path_unit(c, r, f)
            res = learner(task, u, M, U, budgets=(8, 9, 12) if kind == "smoke" else BUDS)
            return {"condition": c, "repeat": r, "fold": f, "paid_ids": u["paid_ids"][:60], "test_ids": u["test_ids"], **res}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("ea-unlimited", "ea-diag", "ea-smoke")})
