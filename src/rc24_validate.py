"""RC24 Stage A numerical acceptance (no evaluation metric). Every test returns PASS / FAIL / INCOMPLETE from numeric conditions,
and each test family includes a deliberately wrong input that must FAIL (non-vacuity) or an unreachable input that must be
INCOMPLETE.
  T1 M3 parity: the RC24 port (src.rc24_models.m3_fit_predict) against the HISTORICAL code executed unchanged in the sibling
     repository (read-only; src.week9_phase1_11 fit_physics_mean + src.week9_phase1_13 fit_hybrid / components, model "M3",
     upper 100) on recorded paid states; PASS iff max |dp| <= 1e-9. Negative controls: the port with C = 1e5 must FAIL; a
     missing sibling path must give INCOMPLETE.
  T2 straddle moments: analytic (eta, s^2) of src.rc24_models.ha_lean_moments against Monte Carlo (S = 40,000 draws: grid
     configuration g ~ w, standardised depth feature ~ N(F_bar, sigma2), latent ~ N(m_g, v_g) recomputed exactly at the drawn
     feature with the configuration's Laplace mode); PASS iff median relative error of the variance <= 3 % and max <= 10 % and
     |mean error| <= 0.05 sd. Negative control: the analytic variance x 2 must FAIL.
  T3 reproduction: HA_LEAN_MARGIN and HONLY_MARGIN (src.rc23_common.run_arm, unchanged) reproduce the RC23 h-std units of
     repeat 51 fold 1 bit for bit.
  T4 shadow: randomising every never-paid outcome leaves the M3_MARGIN, G3_MARGIN and HA_LEAN_STRADDLE trajectories identical
     (paid-only information), to budget 20 on DEV repeat 1 fold 2.
    python -m src.rc24_validate
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc21_phr as PH
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_jobs as J
import src.rc24_models as MD

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
R22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
SIB = Path(r"C:\Users\ozgur\Documents\thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark")
PASS, FAIL, INCOMPLETE = "PASS", "FAIL", "INCOMPLETE"

HIST = r'''
import sys, json, numpy as np
sys.path.insert(0, ".")
import src.week9_phase1_11_fixed_mean_discrepancy_gp as p11
import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13
d = np.load(sys.argv[1]); out = {}
for k in sorted({n.split("__")[0] for n in d.files}):
    x4, logh, lab, rev, pool, rows = (d[f"{k}__{n}"] for n in ("x4", "logh", "lab", "rev", "pool", "rows"))
    phys = p11.fit_physics_mean(logh, lab, rev, 0)
    fit = p13.fit_hybrid(x4, logh, lab, rev, pool, phys, "M3", 100.0)
    out[k] = p13.components(fit, x4[rows], logh[rows])["probability"].tolist()
print(json.dumps(out))
'''


def _states():
    M = P.manifest(); C22.set_manifest(M); T = {(x["repeat"], x["fold"]): x for x in P.tasks([35, 43])}; S = []
    for (r, f), unit in (((35, 1), R22 / "g-ingr" / "units" / "r35_f1__H_MARGIN.json.gz"), ((43, 2), R22 / "g-acq" / "units" / "r43_f2__A5_SIMPLE.json.gz")):
        t = T[(r, f)]; pos = {s: i for i, s in enumerate(t["ids"])}; u = RC.read_json_gz(unit)
        for b in (10, 16, 30, 60):
            S.append((f"r{r}f{f}b{b}", t, K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]])))
    return M, S


def t1_m3_parity(M, S, sib=SIB, C=1e6):
    arrs, mine = {}, {}
    for k, t, rv in S:
        L = rv.paid; y = rv.paid_y()[L]
        if len(set(y.tolist())) < 2:
            continue
        lab = np.zeros(len(t["ids"]), int); lab[L] = y; rows = np.asarray(t["test"]); X4 = t["X"]; logh = MD.log_h_raw(X4)
        arrs.update({f"{k}__x4": X4, f"{k}__logh": logh, f"{k}__lab": lab, f"{k}__rev": np.asarray(L), f"{k}__pool": np.asarray(t["pool"]), f"{k}__rows": rows})
        mine[k] = MD.m3_fit_predict(X4, logh, y, L, t["pool"], rows, C=C)[0]
    if not Path(sib).is_dir():
        return {"status": INCOMPLETE, "reason": f"sibling repository not found: {sib}"}
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "m3_inputs.npz"; np.savez(f, **arrs)
        r = subprocess.run([sys.executable, "-c", HIST, str(f)], cwd=str(sib), capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        return {"status": INCOMPLETE, "reason": "historical code failed", "stderr": r.stderr[-1500:]}
    hist = json.loads(r.stdout.strip().splitlines()[-1]); d = {k: float(np.max(np.abs(np.asarray(hist[k]) - mine[k]))) for k in mine}
    mx = max(d.values()) if d else np.nan
    return {"status": PASS if (d and mx <= 1e-9) else FAIL, "max_abs_dp": mx, "per_state": d, "states": len(d), "sibling_head": _git_head(sib), "C_port": C}


def _git_head(p):
    try:
        return subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return None


def t2_straddle_mc(M, S, n_rows=60, draws=40000, scale=1.0, seed=24):
    rng = np.random.default_rng(seed); rows_out = []
    for k, t, rv in S:
        Z = P.zstd(t); rows = np.r_[t["test"], np.setdiff1d(t["pool"], rv.paid)]; mom = MD.ha_lean_moments(t, rv, Z, rows)
        if mom["one_class"]:
            continue
        Htr, Hev, yf = mom["_H"]; Gtt = PH.Gram(Htr, Htr, np.zeros((len(Htr), 1)), np.zeros((len(Htr), 1)))
        cfg = [(tf, th) for tf in PH.TAU_F for th in PH.TAU_H]; modes = [PH.laplace(Gtt.K(tf, th, 0.0, None), yf) for tf, th in cfg]
        pick = rng.choice(len(rows), size=min(n_rows, len(rows)), replace=False)
        for i in pick:
            g = rng.choice(len(cfg), size=draws, p=mom["w"]); Fd = Hev[i, 1] + np.sqrt(mom["sig2"][i]) * rng.standard_normal(draws); f = np.empty(draws)
            for gi in np.unique(g):
                sel = g == gi; tf, th = cfg[gi]; Hx = np.c_[np.full(sel.sum(), Hev[i, 0]), Fd[sel]]
                Gx = PH.Gram(Hx, Htr, np.zeros((len(Hx), 1)), np.zeros((len(Htr), 1))); kss = PH.V0 + th ** 2 * Hx[:, 0] ** 2 + tf ** 2 * Hx[:, 1] ** 2
                m, v, _ = PH.predictive(modes[gi], Gx.K(tf, th, 0.0, None), kss, plugin=True); f[sel] = m + np.sqrt(v) * rng.standard_normal(sel.sum())
            mbar = float(mom["w"] @ mom["m"][:, i]); s2 = float(mom["s2"][i]) * scale
            rows_out.append({"state": k, "row": int(rows[i]), "mc_var": float(f.var()), "an_var": s2, "rel_err_var": abs(f.var() - s2) / s2, "mean_err_sd": abs(f.mean() - mbar) / np.sqrt(s2),
                             "sig2": float(mom["sig2"][i]), "depth_share_of_var": float(mom["sig2"][i] * (mom["w"] @ mom["Ew2"]) / s2) if s2 > 0 else 0.0})
    if not rows_out:
        return {"status": INCOMPLETE, "reason": "no two-class state"}
    re = np.array([r["rel_err_var"] for r in rows_out]); me = np.array([r["mean_err_sd"] for r in rows_out])
    ok = np.median(re) <= 0.03 and re.max() <= 0.10 and me.max() <= 0.05
    return {"status": PASS if ok else FAIL, "rows": len(rows_out), "median_rel_err_var": float(np.median(re)), "max_rel_err_var": float(re.max()), "max_mean_err_sd": float(me.max()),
            "rows_with_excess_depth_variance": int(sum(r["sig2"] > 0 for r in rows_out)), "max_depth_share_of_var": float(max(r["depth_share_of_var"] for r in rows_out)), "scale_tested": scale}


def t3_reproduction(M):
    T = {(x["repeat"], x["fold"]): x for x in P.tasks([51])}; res = {}
    for arm, cons in (("HA_LEAN_MARGIN", "HA_LEAN"), ("HONLY_MARGIN", "HONLY_LR")):
        ref = RC.read_json_gz(R23 / "h-std" / "units" / f"STD__r51_f1__{cons}.json.gz"); u = J.run_own(T[(51, 1)], arm, M)
        res[arm] = bool(u["paid_ids"] == ref["paid_ids"] and all(a["p"][cons] == b["p"][cons] for a, b in zip(u["evals"], ref["evals"])))
    return {"status": PASS if all(res.values()) else FAIL, **res}


def t4_shadow(M):
    from src.rc19_validate import _corrupt
    T = {(x["repeat"], x["fold"]): x for x in P.tasks([1])}; t = T[(1, 2)]; res = {}
    for arm in ("M3_MARGIN", "G3_MARGIN", "HA_LEAN_STRADDLE"):
        a = J.run_own(t, arm, M, bmax=20); b = J.run_own(t, arm, _corrupt(M, set(a["paid_ids"]), 2401), bmax=20)
        res[arm] = bool(a["paid_ids"] == b["paid_ids"] and all(x["p"] == y["p"] for x, y in zip(a["evals"], b["evals"])))
    return {"status": PASS if all(res.values()) else FAIL, **res}


def main():
    RC.limit_threads(1); M, S = _states(); res = {"utc": RC.utc()}
    res["T1_m3_parity"] = t1_m3_parity(M, S); print("T1", {k: v for k, v in res["T1_m3_parity"].items() if k != "per_state"}, flush=True)
    res["T1_negative_C1e5_must_FAIL"] = {k: v for k, v in t1_m3_parity(M, S, C=1e5).items() if k != "per_state"}; print("T1neg", res["T1_negative_C1e5_must_FAIL"], flush=True)
    res["T1_missing_sibling_must_be_INCOMPLETE"] = t1_m3_parity(M, S[:1], sib=Path(r"C:\does\not\exist")); print("T1inc", res["T1_missing_sibling_must_be_INCOMPLETE"], flush=True)
    S2 = [s for s in S if s[0].endswith(("b16", "b30", "b60"))]
    res["T2_straddle_mc"] = t2_straddle_mc(M, S2); print("T2", res["T2_straddle_mc"], flush=True)
    res["T2_negative_variance_x2_must_FAIL"] = t2_straddle_mc(M, S2[:2], n_rows=20, draws=20000, scale=2.0); print("T2neg", res["T2_negative_variance_x2_must_FAIL"], flush=True)
    res["T3_reproduction"] = t3_reproduction(M); print("T3", res["T3_reproduction"], flush=True)
    res["T4_shadow"] = t4_shadow(M); print("T4", res["T4_shadow"], flush=True)
    neg_ok = (res["T1_negative_C1e5_must_FAIL"]["status"] == FAIL and res["T1_missing_sibling_must_be_INCOMPLETE"]["status"] == INCOMPLETE
              and res["T2_negative_variance_x2_must_FAIL"]["status"] == FAIL)
    pos_ok = all(res[k]["status"] == PASS for k in ("T1_m3_parity", "T2_straddle_mc", "T3_reproduction", "T4_shadow"))
    res["negative_controls_behave"] = neg_ok
    res["status"] = PASS if (pos_ok and neg_ok) else (INCOMPLETE if any(res[k]["status"] == INCOMPLETE for k in ("T1_m3_parity", "T2_straddle_mc")) else FAIL)
    (OUT / "validation").mkdir(parents=True, exist_ok=True); (OUT / "validation" / "RC24_STAGE_A_VALIDATION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("STATUS", res["status"])


if __name__ == "__main__":
    main()
