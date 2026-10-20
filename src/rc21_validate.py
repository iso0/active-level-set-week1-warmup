"""RC21 numerical acceptance before any scientific comparison (no evaluation metric is computed here):
  1. Laplace mode / evidence: function-space Newton (src.rc21_phr.laplace) equals an independent weight-space Laplace for the
     residual-free configurations; with the residual it is stationary (grad = y - pi - a = 0) and at least as good as a generic
     optimiser of the same objective (the f gap to the optimiser's stopping point is reported, informational);
  2. predictive integral: 64-node Gauss-Hermite equals a 200-node rule and agrees with Monte Carlo;
  3. nesting: PHR_FXMAP (theta = (1, 1, 0), plug-in) equals RC20's SHQ_ATS_H up to the intercept prior (and converges to it,
     to sklearn's solver tolerance, when that prior is widened to N(0, 100^2));
  4. reproduction: rc21 SHQ_ATS_H equals the cached RC20 c-replay SHQ_ATS_H and RC20's cand_state (identical code path);
  5. shadow: randomising every never-paid outcome leaves every RC21 construction identical on a fixed paid prefix;
  6. transverse geometry: Z . d is exactly proportional to z_h, U is orthogonal to d, the basis is orthonormal;
  7. timing: CPU seconds per paid state (single thread).
    python -m src.rc21_validate
"""
from __future__ import annotations

import json
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_attr as RA
import src.rc21_phr as PH
from src.rc19_validate import _corrupt

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"
C20 = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20" / "c-replay" / "units"


def _states(M, tasks, specs):
    for (r, f, arm, b) in specs:
        t = tasks[(r, f)]; u = RC.read_json_gz(B19 / f"r{r}_f{f}__{arm}.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}
        paid = [pos[s] for s in u["paid_ids"]]; yield t, K._rev_with(t, M, paid[:b]), (r, f, arm, b)


def _design(t, rev):
    """Training design of the PHR layer at one state (standardised [z_h, F~]) and the transverse coordinates."""
    Z = P.zstd(t); L = rev.paid; y = rev.paid_y()[L].astype(float); h = A.hcol(t); R = A.cf(Z, rev, A.ATS, "SHQ", t["test"][:5], A.KF)
    X = np.c_[h[L], R["F"]]; H = (X - X.mean(0)) / (X.std(0) + 1e-12); U, d = PH.transverse(t, Z)
    return H, U[L], y


def laplace_checks(M, tasks):
    res = {"weight_space": [], "residual_vs_optimiser": []}
    for t, rev, key in _states(M, tasks, ((11, 1, "ATSCF_MARGIN", 12), (12, 2, "E1S", 24), (13, 4, "G3_MARGIN", 60))):
        H, U, y = _design(t, rev); G = PH.Gram(H, H, U, U); n, p = H.shape
        for tf, th in ((0.5, 4.0), (1.0, 1.0), (4.0, 0.5)):
            mode = PH.laplace(G.K(tf, th, 0.0, None), y); Hb = np.c_[np.ones(n), H]; S = np.r_[PH.V0, th ** 2, np.full(p - 1, tf ** 2)]
            b = np.zeros(p + 1)
            for _ in range(200):                                          # weight-space Newton (independent implementation)
                pi = expit(Hb @ b); g = Hb.T @ (y - pi) - b / S; Hs = Hb.T @ (Hb * (pi * (1 - pi))[:, None]) + np.diag(1 / S)
                st = np.linalg.solve(Hs, g); b = b + st
                if np.max(np.abs(st)) < 1e-12:
                    break
            pi = expit(Hb @ b); W = pi * (1 - pi); fb = Hb @ b
            logZ_w = float(np.sum(y * fb - np.logaddexp(0, fb)) - 0.5 * np.sum(b ** 2 / S)
                           - 0.5 * np.linalg.slogdet(np.eye(p + 1) + np.sqrt(S)[:, None] * (Hb.T @ (Hb * W[:, None])) * np.sqrt(S)[None, :])[1])
            res["weight_space"].append({"state": key, "theta": [tf, th], "max_abs_f_diff": float(np.max(np.abs(fb - mode["f"]))), "abs_logZ_diff": abs(logZ_w - mode["logZ"])})
        for sr, el in ((0.5, 0.75), (2.0, 1.5)):
            Kx = G.K(1.0, 2.0, sr, el); mode = PH.laplace(Kx, y)
            obj = lambda a: -(-0.5 * a @ Kx @ a + float(np.sum(y * (Kx @ a) - np.logaddexp(0, Kx @ a))))
            jac = lambda a: -(Kx @ (y - expit(Kx @ a)) - Kx @ a)
            r = minimize(obj, np.zeros(len(y)), jac=jac, method="L-BFGS-B", options={"maxiter": 20000, "gtol": 1e-12, "ftol": 1e-15})
            res["residual_vs_optimiser"].append({"state": key, "theta": [1.0, 2.0, sr, el], "optimiser_minus_newton_objective": float(-obj(r.x) - mode["obj"]),
                                                 "newton_stationarity_max_abs": float(np.max(np.abs(mode["grad"] - mode["a"]))),
                                                 "max_abs_f_diff": float(np.max(np.abs(Kx @ r.x - mode["f"])))})
    ws = max(max(c["max_abs_f_diff"], c["abs_logZ_diff"]) for c in res["weight_space"])
    ro = max(c["optimiser_minus_newton_objective"] for c in res["residual_vs_optimiser"]); rf = max(c["max_abs_f_diff"] for c in res["residual_vs_optimiser"])
    st = max(c["newton_stationarity_max_abs"] for c in res["residual_vs_optimiser"])
    res["PASS"] = bool(ws < 1e-6 and ro < 1e-8 and st < 1e-6); res["worst"] = {"weight_space": ws, "optimiser_objective_gap": ro, "optimiser_f_gap_informational": rf, "newton_stationarity": st}
    return res


def quadrature_check():
    rng = np.random.default_rng(21); m = rng.normal(0, 3, 40); v = rng.uniform(0, 9, 40)
    x2, w2 = np.polynomial.hermite_e.hermegauss(200); w2 = w2 / w2.sum()
    p64 = expit(m[:, None] + np.sqrt(v)[:, None] * PH._GHX[None, :]) @ PH._GHW; p200 = expit(m[:, None] + np.sqrt(v)[:, None] * x2[None, :]) @ w2
    mc = expit(m[:, None] + np.sqrt(v)[:, None] * rng.standard_normal((40, 400000))).mean(1)
    return {"max_abs_64_vs_200": float(np.max(np.abs(p64 - p200))), "max_abs_64_vs_mc": float(np.max(np.abs(p64 - mc))),
            "PASS": bool(np.max(np.abs(p64 - p200)) < 1e-7 and np.max(np.abs(p64 - mc)) < 3e-3)}


def nesting_and_reproduction(M, tasks):
    import src.rc20_decisions as DEC
    res = {"fxmap_vs_shq_ats_h": [], "wide_intercept": [], "cache": [], "rc20_cand_state": []}
    for t, rev, key in _states(M, tasks, ((11, 1, "ATSCF_MARGIN", 12), (12, 2, "E1S", 24), (13, 4, "G3_MARGIN", 60), (14, 5, "ATSAPPROX_MARGIN", 40))):
        r, f, arm, b = key; Z = P.zstd(t); out, info = RA.state(t, rev, Z, t["test"])
        res["fxmap_vs_shq_ats_h"].append(float(np.max(np.abs(out["PHR_FXMAP"] - out["SHQ_ATS_H"]))))
        # exact optimum of the SHQ_ATS_H objective (1/2 |w|^2 + log loss, free intercept) by tight Newton, vs PHR_FXMAP with a
        # widened intercept prior and vs sklearn (whose lbfgs tolerance is the remaining gap; informational)
        L = rev.paid; y = rev.paid_y()[L].astype(float); h = A.hcol(t); R = A.cf(Z, rev, A.ATS, "SHQ", t["test"], A.KF)
        Xtr = np.c_[R["F"], h[L]]; Xev = np.c_[R["E"], h[t["test"]]]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
        Hb = np.c_[np.ones(len(L)), (Xtr - mu) / sd]; Hv = np.c_[np.ones(len(Xev)), (Xev - mu) / sd]; pen = np.r_[0.0, np.ones(Hb.shape[1] - 1)]; beta = np.zeros(Hb.shape[1])
        for _ in range(500):
            pi = expit(Hb @ beta); g = Hb.T @ (y - pi) - pen * beta; Hs = Hb.T @ (Hb * (pi * (1 - pi))[:, None]) + np.diag(pen + 1e-12); st = np.linalg.solve(Hs, g); beta = beta + st
            if np.max(np.abs(st)) < 1e-13:
                break
        p_exact = expit(Hv @ beta); v0 = PH.V0; PH.V0 = 1e4
        try:
            ph, _ = PH.fit_predict(R["F"], h[L], PH.transverse(t, Z)[0][L], y, R["E"], h[t["test"]], PH.transverse(t, Z)[0][t["test"]])
        finally:
            PH.V0 = v0
        res["wide_intercept"].append(float(np.max(np.abs(ph["PHR_FXMAP"] - p_exact))))
        res.setdefault("sklearn_vs_exact_informational", []).append(float(np.max(np.abs(out["SHQ_ATS_H"] - p_exact))))
        cu = RC.read_json_gz(C20 / f"r{r}_f{f}__{arm}.json.gz"); ref = [e for e in cu["evals"] if e["budget"] == b][0]["p"]["SHQ_ATS_H"]
        res["cache"].append(float(np.max(np.abs(out["SHQ_ATS_H"] - np.asarray(ref, float)))))
        cands = np.setdiff1d(t["pool"], rev.paid); st = A.cand_state(t, rev, Z, DEC.CAND, cands); o3, _ = RA.state(t, rev, Z, np.r_[t["test"], cands], which=("SHQ_ATS_H",))
        res["rc20_cand_state"].append(float(np.max(np.abs(np.r_[st["p_test"], st["p_cand"]] - o3["SHQ_ATS_H"]))))
    res["PASS"] = bool(max(res["fxmap_vs_shq_ats_h"]) < 5e-3 and max(res["wide_intercept"]) < 1e-4 and max(res["cache"]) < 1e-6 and max(res["rc20_cand_state"]) == 0.0)
    return res


def shadow(M, t):
    Z = P.zstd(t); paid = list(t["path"][:20]); r1 = K._rev_with(t, M, paid); o1, _ = RA.state(t, r1, Z, t["test"])
    Mc = _corrupt(M, {t["ids"][i] for i in paid}, 21); r2 = K._rev_with(t, Mc, paid); o2, _ = RA.state(t, r2, Z, t["test"])
    diff = {k: float(np.max(np.abs(o1[k] - o2[k]))) for k in o1}
    return {"max_abs_diff": diff, "PASS": bool(all(v == 0.0 for v in diff.values()))}


def geometry(t):
    Z = P.zstd(t); U, d = PH.transverse(t, Z); h = A.hcol(t); s = np.log(t["X"])[t["pool"]].std(0); B = None
    Q, _ = np.linalg.qr(np.c_[d, np.eye(4)]); B = Q[:, 1:4]
    c = float(np.corrcoef(Z @ d, h)[0, 1])
    return {"corr_Zd_zh": c, "max_abs_Bt_d": float(np.max(np.abs(B.T @ d))), "max_abs_BtB_minus_I": float(np.max(np.abs(B.T @ B - np.eye(3)))),
            "U_change_along_d_max": float(np.max(np.abs((Z + 0.7 * d[None, :]) @ B - U))), "d": d.tolist(), "pool_log_sd": s.tolist(),
            "PASS": bool(abs(c - 1.0) < 1e-12 and np.max(np.abs(B.T @ d)) < 1e-12 and np.max(np.abs(B.T @ B - np.eye(3))) < 1e-12)}


def timing(M, tasks):
    rows = []
    for t, rev, key in _states(M, tasks, ((11, 1, "ATSCF_MARGIN", 8), (11, 1, "ATSCF_MARGIN", 24), (11, 1, "ATSCF_MARGIN", 60), (12, 2, "E1S", 60))):
        Z = P.zstd(t); rows_ = np.r_[t["test"], np.setdiff1d(t["pool"], rev.paid)]
        t0 = time.process_time(); RA.state(t, rev, Z, rows_, which=("SHQ_ATS_H",)); t1 = time.process_time(); RA.state(t, rev, Z, rows_); t2 = time.process_time()
        rows.append({"state": key, "cpu_s_shq_ats_h_only": t1 - t0, "cpu_s_all_constructions": t2 - t1})
    return rows


def main():
    RC.limit_threads(1); M = P.manifest(); tasks = {(x["repeat"], x["fold"]): x for x in P.tasks([11, 12, 13, 14])}; t1 = P.tasks((1,))[0]
    res = {"utc": RC.utc()}
    res["laplace"] = laplace_checks(M, tasks); print("laplace", res["laplace"]["PASS"], res["laplace"]["worst"], flush=True)
    res["quadrature"] = quadrature_check(); print("quadrature", res["quadrature"], flush=True)
    res["nesting_reproduction"] = nesting_and_reproduction(M, tasks); print("nesting", res["nesting_reproduction"], flush=True)
    res["shadow"] = shadow(M, t1); print("shadow", res["shadow"], flush=True)
    res["geometry"] = geometry(t1); print("geometry", res["geometry"]["PASS"], flush=True)
    res["timing"] = timing(M, tasks); print("timing", res["timing"], flush=True)
    res["status"] = "PASS" if all(res[k]["PASS"] for k in ("laplace", "quadrature", "nesting_reproduction", "shadow", "geometry")) else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RC21_VALIDATION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print(res["status"])


if __name__ == "__main__":
    main()
