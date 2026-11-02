"""GT acceptance G1 (PROTOCOL_GT.md section 5): V2 shadow tests (matched and own path), V3 GEO_A depth GP = C1's depth GP, V6 linearity
identity at fixed hyperparameters, V7 Monte-Carlo check of the probit probabilities. V1 (data layer), V4/V5 (in every G2 unit) and V8
(evaluator) are checked elsewhere. Writes acceptance/ACCEPTANCE_G1.json.
    python -m src.gt_accept run
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

import src.ea_cand as CA
import src.el_cross as X
import src.gt_data as GD
import src.gt_dev as DV
import src.gt_geo as GG
import src.gt_own as OW
import src.rc18_campaign as C18
import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc24_pac as PC

OUT = DV.OUT / "acceptance"


def shadow(task, keep_rows, M, seed):
    """Copies of the hidden tables with every row outside keep_rows replaced by noise (labels, depth, targets, quality, geometry, temperature)."""
    rng = np.random.default_rng(seed); ids = [str(s) for s in task["ids"]]; keep = {ids[i] for i in keep_rows}; oth = [s for s in ids if s not in keep]
    Ms = M.copy(); Ms.loc[oth, "y"] = rng.integers(0, 2, len(oth)); Ms.loc[oth, "short_record"] = rng.random(len(oth)) < 0.5
    for c in ("A_um",) + tuple(P.TARGETS):
        Ms.loc[oth, c] = Ms.loc[oth, c].to_numpy(float) * rng.uniform(0.3, 3.0, len(oth))
    R = GD.runs().copy()
    for c in ("W_A_um", "W_atA_um", "R3inst"):
        R.loc[oth, c] = R.loc[oth, c].to_numpy(float) * rng.uniform(0.3, 3.0, len(oth))
    for c in ("g1", "g2", "g3"):
        R.loc[oth, c] = rng.normal(0, 2, len(oth))
    E = dict(GD.early()); Tm = E["Tmax"].copy(); pos = {str(s): i for i, s in enumerate(E["ids"])}
    for s in oth:
        Tm[pos[s], :] = rng.uniform(0, 6000, Tm.shape[1])
    E["Tmax"] = Tm
    return Ms, R, E


def same(a, b):
    return all(np.array_equal(np.asarray(a[k], float), np.asarray(b[k], float), equal_nan=True) for k in a) and set(a) == set(b)


def v2_matched(T, M, keys):
    res = []
    for key in keys:
        task = T[key]; uX = DV.recorded(*key); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in uX["paid_ids"][:60]]
        base = DV.dev_unit(task, uX, M, GG.Hidden(task), budgets=tuple(range(8, 21)))
        Ms, R, E = shadow(task, paid, M, 11); sh = DV.dev_unit(task, uX, Ms, GG.Hidden(task, R, E), budgets=tuple(range(8, 21)))
        per = {s: bool(all(np.array_equal(np.asarray(a["p"][s], float), np.asarray(b["p"][s], float), equal_nan=True) for a, b in zip(base["evals"], sh["evals"])))
               for s in base["evals"][0]["p"]}
        # ORACLE_T reads the true test temperature by design (evaluator-only diagnostic): it must CHANGE (positive control of the test)
        ok = all(v for s, v in per.items() if s != "ORACLE_T") and not per.get("ORACLE_T", False)
        res.append({"task": list(key), "identical": bool(ok), "budgets": "8-20", "identical_by_system": per,
                    "note": "every method identical; ORACLE_T (evaluator-only, reads test truth) changes = positive control"})
    return res


def v2_own(T, M, key, systems=("GEO_A1", "GEO_B1")):
    res = []
    for system in systems:
        for sel in OW.SELECTORS:
            task = T[key]; hid = GG.Hidden(task); base = OW.own_geo(task, M, hid, system, sel, bmax=20)
            Ms, R, E = shadow(task, base["paid"], M, 12); sh = OW.own_geo(task, Ms, GG.Hidden(task, R, E), system, sel, bmax=20)
            ok = base["paid"] == sh["paid"] and all(same(a["p"], b["p"]) for a, b in zip(base["evals"], sh["evals"]))
            res.append({"task": list(key), "system": system, "selector": sel, "identical_path_and_predictions": bool(ok), "bmax": 20})
    return res


def v3(T, M, key, b=20):
    task = T[key]; uX = DV.recorded(*key); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in uX["paid_ids"][:b]]
    rev = K._rev_with(task, M, paid); Z = P.zstd(task); te = np.asarray(task["test"])
    f1 = GG.fit_y(task, rev, Z, rev.paid_Y()[:, PC.DEPTH_COL]); f2 = CA.depth_fit_cand(task, rev, Z, "phys", None, True, CA.STARTS)
    return float(np.max(np.abs(GG.pred(f1, Z, te)[0] - PC.depth_predict(f2, Z, te)[0])))


def v6(T, M, key, b=30):
    """Fixed hyperparameters: GP mean of g = log 2 + mean(log d) - mean(log w) (same rows, same weights, same theta)."""
    task = T[key]; uX = DV.recorded(*key); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in uX["paid_ids"][:b]]
    rev = K._rev_with(task, M, paid); Z = P.zstd(task); te = np.asarray(task["test"]); hid = GG.Hidden(task)
    d = rev.paid_Y()[:, PC.DEPTH_COL]; w = hid.paid(rev, "logW1"); L = rev.paid; Lu = L[np.isfinite(d[L]) & np.isfinite(w[L])]
    g = GG.LOG2 + d - w; H = A.hcol(task)[:, None]; W = np.where(rev.paid_short(), C18.W_SHORT, 1.0)
    fd = CA.gp_fit(Z[Lu], d[Lu], H[Lu], W[Lu], "phys", True, CA.STARTS); th = fd.theta.copy()
    out = {}
    for nm, y in (("d", d), ("w", w), ("g", g)):
        gp = CA.GPMAP(H_cols=1, b=PC.B_TREND, prior=True).fit(Z[Lu], y[Lu], H=H[Lu], w=W[Lu], theta0=th, optimize=False)
        out[nm] = gp.predict(Z[te], Hs=H[te])[0]
    return float(np.max(np.abs(out["g"] - (GG.LOG2 + out["d"] - out["w"]))))


def v7(T, M, key, b=20, draws=100000):
    task = T[key]; uX = DV.recorded(*key); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in uX["paid_ids"][:b]]
    rev = K._rev_with(task, M, paid); Z = P.zstd(task); te = np.asarray(task["test"])[:20]; hid = GG.Hidden(task); rng = np.random.default_rng(5)
    fd = GG.fit_y(task, rev, Z, rev.paid_Y()[:, PC.DEPTH_COL]); fw = GG.fit_y(task, rev, Z, hid.paid(rev, "logW1"))
    Pp, m, vl, vo = GG.geo_from_fits(fd, fw, "A", Z, te); md, _, od = GG.pred(fd, Z, te); mw, _, ow = GG.pred(fw, Z, te)
    dd = md[None, :] + np.sqrt(od)[None, :] * rng.standard_normal((draws, len(te))); ww = mw[None, :] + np.sqrt(ow)[None, :] * rng.standard_normal((draws, len(te)))
    mc = (np.exp(dd) / np.exp(ww) >= 0.5).mean(0)
    return float(np.max(np.abs(mc - Pp)))


def run():
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); t0 = time.time()
    keys = [("STD", 163, 1), ("STD", 170, 3), ("K5", 41, 2), ("K4", 25, 3)]
    T = X.tasks_for({f"k{i}": (None,) + k for i, k in enumerate(keys)}, M)
    R = {"utc": RC.utc(), "V2_matched": v2_matched(T, M, keys), "V2_own": v2_own(T, M, ("STD", 163, 1)),
         "V3_depth_gp_max_abs": v3(T, M, ("STD", 163, 1)), "V6_linearity_max_abs": v6(T, M, ("STD", 170, 3)), "V7_mc_max_abs": v7(T, M, ("STD", 163, 1))}
    R["PASS"] = {"V2": bool(all(r["identical"] for r in R["V2_matched"]) and all(r["identical_path_and_predictions"] for r in R["V2_own"])),
                 "V3": bool(R["V3_depth_gp_max_abs"] <= 1e-12), "V6": bool(R["V6_linearity_max_abs"] <= 1e-10), "V7": bool(R["V7_mc_max_abs"] <= 3e-3)}
    R["seconds"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "ACCEPTANCE_G1.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: R[k] for k in ("PASS", "V3_depth_gp_max_abs", "V6_linearity_max_abs", "V7_mc_max_abs", "seconds")}), flush=True)


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
