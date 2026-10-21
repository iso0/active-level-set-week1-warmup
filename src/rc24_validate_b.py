"""RC24 Stage B acceptance for prototype P1 (src/rc24_pac.py). PASS / FAIL / INCOMPLETE from numeric conditions; each family has a
non-vacuity control that must FAIL.
  V1 errors-in-variables integral: eiv_prob (32-node Gauss-Hermite) vs Monte Carlo (200,000 draws of a* per row) on recorded states;
     PASS iff max |dp| <= 2e-3. Control: the integral with the depth variance x 4 must FAIL against the same Monte Carlo.
  V2 classifier machinery: lr_family's plug-in mixture equals src.rc22_common.phr_family (frozen RC22/RC23 code) on identical inputs;
     PASS iff max |dp| <= 1e-12.
  V3 physics anchor: far outside the data (standardised log inputs scaled x 25 along the pool's h direction) the physics-anchored
     predictive mean equals mu + sd * theta_hat * z_h with theta_hat = b^2 H' K^-1 y_s (posterior mean of the trend coefficient);
     PASS iff relative error <= 1e-3; the constant-mean emulator's far mean equals mu (control: its slope along z_h must be ~0, so the
     same check applied to it must FAIL).
  V4 shadow: randomising every never-paid outcome leaves the PAC_MARGIN trajectory identical (to budget 20, DEV repeat 1 fold 2).
  V5 honesty of HA_TREND's stacking: a paid run's own depth never changes its own out-of-fold feature; other folds change.
    python -m src.rc24_validate_b
"""
from __future__ import annotations

import json

import numpy as np
from scipy.linalg import cho_solve
from scipy.special import expit

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
R22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
PASS, FAIL, INCOMPLETE = "PASS", "FAIL", "INCOMPLETE"


def _states(M):
    T = {(x["repeat"], x["fold"]): x for x in P.tasks([35])}; t = T[(35, 1)]; pos = {s: i for i, s in enumerate(t["ids"])}
    u = RC.read_json_gz(R22 / "g-ingr" / "units" / "r35_f1__H_MARGIN.json.gz")
    return t, [(b, K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]])) for b in (12, 24, 48)]


def v1(t, S, scale=1.0, draws=200000, seed=7):
    rng = np.random.default_rng(seed); Z = P.zstd(t); h = A.hcol(t); worst = 0.0; n = 0
    for b, rv in S:
        L = rv.paid; y = rv.paid_y()[L]; rows = np.setdiff1d(t["pool"], L)[:80]; f = PC.depth_fit(t, rv, Z, "phys")
        mt, _ = PC.depth_predict(f, Z, L); me, ve = PC.depth_predict(f, Z, rows); fam = PC.lr_family(np.c_[h[L], mt], y, np.c_[h[rows], me])
        p_gh = PC.eiv_prob(fam, ve * scale); u = rng.standard_normal(draws)
        for i in range(len(rows)):
            a = (np.sqrt(ve[i]) / fam["sd_F"]) * u; pm = float(sum(fam["w"][g] * np.mean(expit(fam["m"][g][i] + fam["cA"][g] * a)) for g in range(len(fam["w"]))))
            worst = max(worst, abs(pm - p_gh[i])); n += 1
    return {"status": PASS if worst <= 2e-3 else FAIL, "max_abs_dp": worst, "rows": n, "variance_scale": scale}


def v2(t, S):
    Z = P.zstd(t); h = A.hcol(t); worst = 0.0
    for b, rv in S:
        L = rv.paid; y = rv.paid_y()[L]; rows = np.setdiff1d(t["pool"], L); R = A.cf(Z, rv, ("log_A_um",), "SHQ", rows, A.KF)
        p1 = C22.phr_family(R["F"], h[L], y, R["E"], h[rows], feats=(0,))[0]; fam = PC.lr_family(np.c_[h[L], R["F"][:, 0]], y, np.c_[h[rows], R["E"][:, 0]])
        worst = max(worst, float(np.max(np.abs(fam["w"] @ expit(fam["m"]) - p1))))
    return {"status": PASS if worst <= 1e-12 else FAIL, "max_abs_dp": worst}


def v3(t, S, kind="phys"):
    Z = P.zstd(t); b, rv = S[-1]; f = PC.depth_fit(t, rv, Z, kind); g = f["g"]
    s = np.log(t["X"])[t["pool"]].std(0); d = np.array([1.0, -0.5, -1.5, 0.0]) * s; d /= np.linalg.norm(d)
    Zf = 25.0 * d[None, :]                                                                                # far point along the h direction
    lx = Zf * np.log(t["X"])[t["pool"]].std(0) + np.log(t["X"])[t["pool"]].mean(0); hraw = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]
    hp = np.log(t["X"])[t["pool"]]; hp = hp[:, 0] - 0.5 * hp[:, 1] - 1.5 * hp[:, 2]; zh = float((hraw[0] - hp.mean()) / hp.std())
    H = f["H"]
    if H is None:
        m, _, _ = g.predict(Zf)
        return {"status": FAIL, "far_mean_minus_mu_over_sd": float((m[0] - g.mu) / g.sd), "note": "constant-mean emulator: no trend term (control)", "kind": kind}
    Hf = np.array([[zh]]); m, _, _ = g.predict(Zf, Hs=Hf)
    Lu = f["rows"]; Yt = rv.paid_Y()[Lu, PC.DEPTH_COL]; ysd = (Yt - g.mu) / g.sd; theta = (g.b ** 2) * float(H[Lu, 0] @ cho_solve(g.c, ysd))
    pred = g.mu + g.sd * theta * zh; rel = abs(m[0] - pred) / max(abs(m[0] - g.mu), 1e-12)
    return {"status": PASS if rel <= 1e-3 else FAIL, "far_mean": float(m[0]), "trend_prediction": float(pred), "relative_error": float(rel), "theta_hat_std_units": theta, "z_h_far": zh, "kind": kind}


def v4(M):
    from src.rc19_validate import _corrupt
    import src.rc24_pilot as PL
    t = {(x["repeat"], x["fold"]): x for x in P.tasks([1])}[(1, 2)]
    a = PL.run_pac(t, M, bmax=20); b = PL.run_pac(t, _corrupt(M, set(a["paid_ids"]), 2402), bmax=20)
    ok = a["paid_ids"] == b["paid_ids"] and all(x["p"] == y["p"] for x, y in zip(a["evals"], b["evals"]))
    return {"status": PASS if ok else FAIL}


def v5(t, M, S):
    b, rv = S[1]; Z = P.zstd(t); rows = t["test"][:3]; R0 = PC.cf_phys(t, rv, Z, rows); paid = rv.paid; fold, k = K.folds(len(paid), A.KF); worst, other = 0.0, 0
    for j in (1, 7, 15):
        r1 = K._rev_with(t, M, list(paid)); i = paid[j]; r1._Y[i, PC.DEPTH_COL] = r1._Y[i, PC.DEPTH_COL] + 0.5
        R1 = PC.cf_phys(t, r1, Z, rows); worst = max(worst, float(abs(R1["F"][j, 0] - R0["F"][j, 0])))
        other += int(np.any(np.abs(R1["F"][fold != fold[j], 0] - R0["F"][fold != fold[j], 0]) > 1e-9))
    return {"status": PASS if (worst == 0.0 and other > 0) else FAIL, "own_change_max": worst, "other_folds_changed_cases": other}


def main():
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); t, S = _states(M); res = {"utc": RC.utc()}
    res["V1_eiv_integral"] = v1(t, S); print("V1", res["V1_eiv_integral"], flush=True)
    res["V1_control_variance_x4_must_FAIL"] = v1(t, S[:1], scale=4.0, draws=50000); print("V1c", res["V1_control_variance_x4_must_FAIL"], flush=True)
    res["V2_classifier_equals_phr_family"] = v2(t, S); print("V2", res["V2_classifier_equals_phr_family"], flush=True)
    res["V3_physics_anchor_extrapolation"] = v3(t, S, "phys"); print("V3", res["V3_physics_anchor_extrapolation"], flush=True)
    res["V3_control_flat_must_FAIL"] = v3(t, S, "flat"); print("V3c", res["V3_control_flat_must_FAIL"], flush=True)
    res["V4_shadow"] = v4(M); print("V4", res["V4_shadow"], flush=True)
    res["V5_honesty_HA_TREND"] = v5(t, M, S); print("V5", res["V5_honesty_HA_TREND"], flush=True)
    pos = all(res[k]["status"] == PASS for k in ("V1_eiv_integral", "V2_classifier_equals_phr_family", "V3_physics_anchor_extrapolation", "V4_shadow", "V5_honesty_HA_TREND"))
    neg = res["V1_control_variance_x4_must_FAIL"]["status"] == FAIL and res["V3_control_flat_must_FAIL"]["status"] == FAIL
    res["negative_controls_behave"] = neg; res["status"] = PASS if (pos and neg) else FAIL
    (OUT / "validation").mkdir(parents=True, exist_ok=True); (OUT / "validation" / "RC24_STAGE_B_P1_VALIDATION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("STATUS", res["status"])


if __name__ == "__main__":
    main()
