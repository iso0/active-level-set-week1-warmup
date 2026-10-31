"""IR parts B and C (PROTOCOL_IR.md sections 4-5) on the RECORDED C1-selected paths (identical paid prefixes; no new query):
learnability of every physical output and the depth-model screen (co-output candidates LMC_q / CHAIN_q for q in {W, KE, T}, controls
SUM2 / ICM_W, evaluator-only diagnostics ORACLE_CHAIN_q). Paid outcomes and public inputs only, except the ORACLE rows.
    python -m src.ir_screen validate            acceptance V2 (shadow), V4 (CHAIN), V5 (C1 reproduction), V6 (g* frozen)
    python -m src.ir_screen work ir-screen       units (3 single-thread workers in parallel, O_EXCL unit locks)
    python -m src.ir_screen timing              one unit, all budgets, wall time
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd

import src.ea_cand as EC
import src.el_cross as X
import src.ir_data as IRD
import src.ir_gp as LG
import src.rc18_campaign as C18
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc24_pac as PC

OUT = IRD.OUT
EA = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "exports"
BUDGETS = (8, 12, 16, 20, 24, 32, 40, 60)
KF = 10
COL = {"W": None, "KE": "log_ke_T0_nJ", "T": "tmax_T0_K", "SPK": "vmax_spike_logratio", "LAS": "laser_T0_W", "ETOT": "log_etot_T0_J", "NPART": "log_npart_T0"}
CO = ("W", "KE", "T")                                   # co-outputs of the candidates
LEARN = ("W", "KE", "T", "SPK", "LAS", "ETOT", "NPART")  # part B outputs besides depth


# ======================================================================================== data access (paid only unless ORACLE)
def paid_q(task, rev, q):
    if q == "W":
        return IRD.paid_W(task, rev)
    return rev.paid_Y()[:, LN.TI[COL[q]]]


def true_q(task, M, q):
    """Evaluator only (ORACLE diagnostics)."""
    if q == "W":
        return IRD.all_W(task)
    return M[COL[q]].reindex(list(task["ids"])).to_numpy(float)


def weights(rev):
    return np.where(rev.paid_short(), C18.W_SHORT, 1.0)


def depth_vec(rev):
    return rev.paid_Y()[:, PC.DEPTH_COL]


# ======================================================================================== models
def r0(task, rev, Z, te):
    f = EC.depth_fit_cand(task, rev, Z, "phys", None, True, EC.STARTS)
    if f is None:
        return None
    m, lat, obs = f["g"].predict(Z[te], Hs=f["H"][te]); return m, lat, obs - lat


def gp_q(Z, v, hb, w, rows):
    """C1-style GP (h trend b = 3, Matern 3/2 ARD, C1 MAP prior, 2 starts) on rows with finite v; None if < 3 good rows."""
    rows = np.asarray(rows, int); rows = rows[np.isfinite(v[rows])]
    if (w[rows] <= 100).sum() < 3:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return EC.gp_fit(Z[rows], v[rows], hb[rows][:, None], w[rows], "phys", True, EC.STARTS)


def gp_q_pred(g, Z, hb, idx, fallback):
    if g is None:
        return np.full(len(idx), fallback), np.full(len(idx), np.nan), np.full(len(idx), np.nan)
    m, lat, obs = g.predict(Z[idx], Hs=hb[idx][:, None]); return m, lat, obs - lat


def qhat_oof(Z, v, hb, w, L, Kf=KF):
    """Honest K-fold out-of-fold q-hat at the paid rows L (fold of the j-th paid run = j mod K)."""
    fold, k = K.folds(len(L), Kf); out = np.full(len(L), np.nan)
    for j in range(k):
        tr = L[fold != j]; g = gp_q(Z, v, hb, w, tr); fin = v[tr][np.isfinite(v[tr])]
        out[fold == j] = gp_q_pred(g, Z, hb, L[fold == j], float(fin.mean()) if len(fin) else 0.0)[0]
    return out


def depth_basis_fit(Z, yd, w, Lu, Hm):
    """Depth GP with basis columns Hm (each coefficient ~ N(0, 3^2), integrated), C1's MAP prior and two starts."""
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for th0 in EC.STARTS:
            g = EC.GPMAP(H_cols=Hm.shape[1], b=PC.B_TREND, prior=True).fit(Z[Lu], yd[Lu], H=Hm[Lu], w=w[Lu], theta0=np.asarray(th0, float))
            if best is None or g.opt["nlml"] < best.opt["nlml"]:
                best = g
    return best


def chain(Z, yd, w, hb, L, te, qpaid_basis, qtest_basis):
    """CHAIN depth model given the basis values at the paid rows (L order) and the test rows; standardised by the paid values."""
    Lu = L[np.isfinite(yd[L])]
    if (w[Lu] <= 100).sum() < 3:
        return None
    mu, sd = float(np.nanmean(qpaid_basis)), float(np.nanstd(qpaid_basis))
    sd = sd if sd > 1e-12 else 1.0
    s = np.zeros(len(Z)); s[L] = (qpaid_basis - mu) / sd; s_te = (qtest_basis - mu) / sd
    Hm = np.c_[hb, s]; g = depth_basis_fit(Z, yd, w, Lu, Hm)
    m, lat, obs = g.predict(Z[te], Hs=np.c_[hb[te], s_te]); return m, lat, obs - lat


def lmc_fit_pred(Z, ys, ws, hb, te, n_out, tied=False):
    d = Z.shape[1]
    if (np.isfinite(ys[0]) & (ws[0] <= 100)).sum() < 3:
        return None
    m = LG.LMC(n_out=n_out, R=2, tied=tied).fit(Z, ys, ws, hb=hb, starts=LG.starts_lmc(d, n_out=n_out, tied=tied))
    mu, lat = m.predict(Z[te], 0, hb[te]); return mu, lat, np.full(len(te), m.noise_var(0)), m.opt


def state(task, rev, Z, te, M, which=None, learn=True):
    """All part B / C predictions at one paid state. Returns {name: (mean, latent var, noise var)} on the test rows."""
    L = rev.paid; yd = depth_vec(rev); w = weights(rev); hb = A.hcol(task); out = {}; info = {}
    want = set(which) if which is not None else None

    def need(nm):
        return want is None or nm in want
    if need("R0"):
        r = r0(task, rev, Z, te)
        if r is not None:
            out["R0"] = r
    qv = {q: paid_q(task, rev, q) for q in LEARN}
    gfull = {}
    for q in LEARN:
        if not (learn or (q in CO and (need(f"CHAIN_{q}") or need(f"ORACLE_CHAIN_{q}")))):
            continue
        g = gp_q(Z, qv[q], hb, w, L); gfull[q] = g
        fin = qv[q][L][np.isfinite(qv[q][L])]
        if learn:
            out[f"LEARN_{q}"] = gp_q_pred(g, Z, hb, te, float(fin.mean()) if len(fin) else np.nan)
    for q in CO:
        if need(f"CHAIN_{q}"):
            qo = qhat_oof(Z, qv[q], hb, w, L); fin = qv[q][L][np.isfinite(qv[q][L])]
            qt = gp_q_pred(gfull.get(q), Z, hb, te, float(fin.mean()) if len(fin) else 0.0)[0]
            r = chain(Z, yd, w, hb, L, te, qo, qt)
            if r is not None:
                out[f"CHAIN_{q}"] = r
        if need(f"ORACLE_CHAIN_{q}"):
            tq = true_q(task, M, q); qo = qhat_oof(Z, qv[q], hb, w, L)
            qp = np.where(np.isfinite(tq[L]), tq[L], qo)                       # true q at paid rows; OOF q-hat where the truth is missing
            fin = qv[q][L][np.isfinite(qv[q][L])]; qh = gp_q_pred(gfull.get(q) if q in gfull else gp_q(Z, qv[q], hb, w, L), Z, hb, te, float(fin.mean()) if len(fin) else 0.0)[0]
            qt = np.where(np.isfinite(tq[te]), tq[te], qh)
            r = chain(Z, yd, w, hb, L, te, qp, qt)
            if r is not None:
                out[f"ORACLE_CHAIN_{q}"] = r
        if need(f"LMC_{q}"):
            r = lmc_fit_pred(Z, [yd, qv[q]], [w, w], hb, te, 2)
            if r is not None:
                out[f"LMC_{q}"] = r[:3]; info[f"LMC_{q}"] = r[3]
    if need("SUM2"):
        r = lmc_fit_pred(Z, [yd], [w], hb, te, 1)
        if r is not None:
            out["SUM2"] = r[:3]; info["SUM2"] = r[3]
    if need("ICM_W"):
        r = lmc_fit_pred(Z, [yd, qv["W"]], [w, w], hb, te, 2, tied=True)
        if r is not None:
            out["ICM_W"] = r[:3]; info["ICM_W"] = r[3]
    return out, info


# ======================================================================================== recorded paths and units
_PATHS = {}


def recorded_path(cond, cl, l):
    src = {"STD": "validation_std", "K5": "validation_k5", "K4": "validation_k4"}[cond]
    if src not in _PATHS:
        _PATHS[src] = pd.read_csv(EA / src / "paths.csv.gz")
    T = _PATHS[src]; T = T[(T.path == "C1-selected") & (T.condition == cond) & (T.cluster == cl) & (T.learner == l)].sort_values("query")
    if len(T) != 60:
        raise RuntimeError(f"recorded C1 path {cond} {cl} {l}: {len(T)} queries")
    return T.sim_id.astype(str).tolist()


def units(job):
    if job == "ir-screen":
        return ([(f"STD__r{r}_f{f}", ("STD", r, f)) for r in range(163, 203) for f in range(1, 6)]
                + [(f"K5__s{s}_b{b}", ("K5", s, b)) for s in range(41, 49) for b in range(1, 6)]
                + [(f"K4__s{s}_b{b}", ("K4", s, b)) for s in range(25, 33) for b in range(1, 5)])
    if job == "ir-screen-reduced":
        return [u for u in units("ir-screen") if not (u[1][0] == "STD" and u[1][1] >= 183)]
    raise ValueError(job)


def unit_eval(task, M, paid_ids, budgets=BUDGETS):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_rows = [pos[s] for s in paid_ids]; te = np.asarray(task["test"]); ev = []
    for b in budgets:
        rev = K._rev_with(task, M, paid_rows[:b]); t0 = time.process_time(); out, info = state(task, rev, Z, te, M)
        ev.append({"budget": b, "cpu_s": time.process_time() - t0,
                   "pred": {k: [LN._f32(v[0]), LN._f32(v[1]), LN._f32(v[2])] for k, v in out.items()},
                   "opt": {k: {kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv) for kk, vv in v.items()} for k, v in info.items()}})
    return ev


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    T = X.tasks_for({n: (None, v[0], v[1], v[2]) for n, v in S.items()}, M)

    def fn(name):
        c, r, f = S[name]; task = T[(c, r, f)]; ids = recorded_path(c, r, f)
        return {"condition": c, "cluster": r, "learner": f, "paid_ids": ids, "test_ids": [task["ids"][i] for i in task["test"]], "evals": unit_eval(task, M, ids)}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


def timing():
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); T = X.tasks_for({"u": (None, "STD", 163, 1)}, M); task = T[("STD", 163, 1)]
    ids = recorded_path("STD", 163, 1); t0 = time.time(); ev = unit_eval(task, M, ids); wall = time.time() - t0
    per_b = {e["budget"]: round(e["cpu_s"], 2) for e in ev}; n_units = len(units("ir-screen"))
    res = {"unit": "STD r163 f1", "wall_s": round(wall, 1), "cpu_s_per_budget": per_b, "projected_worker_hours_full": round(wall * n_units / 3600, 2),
           "projected_worker_hours_reduced": round(wall * len(units("ir-screen-reduced")) / 3600, 2), "models": sorted(ev[-1]["pred"])}
    (OUT / "screen_timing.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1)); return res


# ======================================================================================== acceptance V2 / V4 / V5 / V6
def gstar():
    """V6: the frozen evaluator map g*(log h, log A): L2 logistic (C = 1) on standardised features, all good records, true values."""
    from sklearn.linear_model import LogisticRegression
    M = P.manifest(); lx = np.log(M[list(P.INPUTS)].to_numpy(float)); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; a = M.log_A_um.to_numpy(float)
    good = (~M.short_record.astype(bool).to_numpy()) & np.isfinite(a); Xf = np.c_[h, a][good]; mu, sd = Xf.mean(0), Xf.std(0)
    lr = LogisticRegression(C=1.0, max_iter=5000).fit((Xf - mu) / sd, M.y.to_numpy(int)[good])
    p = lr.predict_proba((Xf - mu) / sd)[:, 1]; y = M.y.to_numpy(int)[good]; hat = p >= 0.5
    return {"mu": mu.tolist(), "sd": sd.tolist(), "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0]), "n": int(good.sum()),
            "BA_true_depth": float(0.5 * (hat[y == 1].mean() + (~hat[y == 0]).mean()))}


def validate():
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); res = {"checks": {}, "info": {}}
    T = X.tasks_for({"a": (None, "STD", 163, 1), "b": (None, "K5", 41, 1), "c": (None, "STD", 170, 3), "d": (None, "K4", 25, 2)}, M)
    # V6
    g = gstar(); (OUT / "GSTAR_FROZEN.json").write_text(json.dumps(g, indent=1), encoding="utf-8"); res["info"]["gstar"] = g; res["checks"]["V6_gstar_frozen"] = True
    # V5: C1 pipeline on the recorded path reproduces the recorded C1_own probabilities
    z = np.load(EA / "validation_std" / "predictions_f32.npz"); keys = [str(k) for k in z["keys"]]; ix = {k: i for i, k in enumerate(keys)}; worst = 0.0
    for (c, r, f) in (("STD", 163, 1), ("STD", 170, 3)):
        task = T[(c, r, f)]; Z = P.zstd(task); ids = recorded_path(c, r, f); pos = {s: i for i, s in enumerate(task["ids"])}; i = ix[f"C1_own|{c}|{r}|{f}"]
        if list(z[f"test_ids_{i}"].astype(str)) != [task["ids"][j] for j in task["test"]]:
            raise RuntimeError("recorded test set differs")
        for b in (12, 40):
            rev = K._rev_with(task, M, [pos[s] for s in ids[:b]]); p, _ = EC.predict(task, rev, Z, np.asarray(task["test"]), EC.SYSTEMS["C1"])
            worst = max(worst, float(np.max(np.abs(np.asarray(LN._f32(p), float) - np.asarray(z[f"pred_{i}"], float)[b - 8]))))
    res["info"]["V5_max_abs_dp"] = worst; res["checks"]["V5_C1_reproduces_recorded_1e-6"] = worst <= 1e-6
    # V4: CHAIN with a zero basis column equals R0 exactly; own q never changes own OOF q-hat
    task = T[("STD", 163, 1)]; Z = P.zstd(task); ids = recorded_path("STD", 163, 1); pos = {s: i for i, s in enumerate(task["ids"])}
    rev = K._rev_with(task, M, [pos[s] for s in ids[:20]]); te = np.asarray(task["test"]); L = rev.paid; yd = depth_vec(rev); w = weights(rev); hb = A.hcol(task)
    m0 = r0(task, rev, Z, te); Lu = L[np.isfinite(yd[L])]; g0 = depth_basis_fit(Z, yd, w, Lu, np.c_[hb, np.zeros(len(Z))])
    mz = g0.predict(Z[te], Hs=np.c_[hb[te], np.zeros(len(te))])[0]; res["info"]["V4_zero_basis_max_abs"] = float(np.max(np.abs(mz - m0[0])))
    res["checks"]["V4_zero_basis_equals_R0_1e-10"] = res["info"]["V4_zero_basis_max_abs"] <= 1e-10
    qv = paid_q(task, rev, "KE"); base = qhat_oof(Z, qv, hb, w, L); fold, k = K.folds(len(L), KF); own_ok = True
    for j in (0, 3, 7):
        q2 = qv.copy(); q2[L[j]] += 5.0; alt = qhat_oof(Z, q2, hb, w, L)
        own_ok &= bool(abs(alt[j] - base[j]) == 0.0) and bool(np.any(np.abs(alt - base) > 0))
    res["checks"]["V4_own_q_never_changes_own_oof"] = own_ok
    # V2: shadow test - permuting W / KE / T of every unpaid row leaves every prediction identical
    rng = np.random.default_rng(5); te_all = np.setdiff1d(np.arange(len(task["ids"])), L)
    names = [s for s in task["ids"]]; unpaid_ids = [names[i] for i in te_all]
    out1, _ = state(task, rev, Z, te, M, which=["R0", "LMC_W", "LMC_KE", "LMC_T", "CHAIN_W", "CHAIN_KE", "CHAIN_T", "SUM2", "ICM_W"], learn=True)
    M2 = M.copy(); perm = rng.permutation(len(unpaid_ids))
    for c in ("log_ke_T0_nJ", "tmax_T0_K", "vmax_spike_logratio", "laser_T0_W", "log_etot_T0_J", "log_npart_T0", "A_um", "log_A_um", "y"):
        M2.loc[unpaid_ids, c] = M.loc[unpaid_ids, c].to_numpy()[perm]
    Wsave = IRD.geometry().copy(); Gp = Wsave.copy(); Gp.loc[unpaid_ids, "W_A_um"] = Wsave.loc[unpaid_ids, "W_A_um"].to_numpy()[perm]; IRD._W = Gp
    try:
        rev2 = K._rev_with(task, M2, [pos[s] for s in ids[:20]])
        out2, _ = state(task, rev2, Z, te, M2, which=["R0", "LMC_W", "LMC_KE", "LMC_T", "CHAIN_W", "CHAIN_KE", "CHAIN_T", "SUM2", "ICM_W"], learn=True)
    finally:
        IRD._W = Wsave
    dmax = max(float(np.max(np.abs(np.asarray(out1[k][j]) - np.asarray(out2[k][j])))) for k in out1 for j in range(2))
    res["info"]["V2_shadow_max_abs"] = dmax; res["info"]["V2_models"] = sorted(out1); res["checks"]["V2_shadow_identical"] = dmax == 0.0
    res["status"] = "PASS" if all(res["checks"].values()) else "FAIL"
    (OUT / "ACCEPTANCE_V2_V4_V5_V6.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(json.dumps(res, indent=1, default=float)); return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "work":
        work(sys.argv[2])
    elif cmd == "validate":
        validate()
    elif cmd == "timing":
        timing()
