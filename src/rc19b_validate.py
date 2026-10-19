"""RC19B acceptance checks before any queue (no evaluation):
  1. cross-fit honesty: changing a paid run's OWN outcomes (label, depth, T, S) must not change its out-of-fold prediction
     (ATSCF / DEPTHCF features and E1's out-of-fold probability), while it may change other folds' predictions;
  2. shadow test: every new adaptive arm rerun with all never-paid outcomes randomised gives the identical path and predictions;
  3. calibration map sanity: identity data give (a, c) close to (0, 1).
    python -m src.rc19b_validate
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
from src.rc19_validate import _corrupt, _same


def honesty(M, t):
    Z = P.zstd(t); rev = K._rev_with(t, M, t["path"][:24]); paid = rev.paid; fold, k = K.folds(len(paid)); out = {"K": int(k)}
    rows = np.r_[t["test"][:5]]
    F0, _, _ = K.cf_features(Z, rev, K.ATS, rows); p0 = K.e1_oof(t["X"], rev)
    worst_self = 0.0; changed_other = 0
    for j in (0, 3, 11):                                                       # three paid runs in different folds
        i = int(paid[j]); r2 = K._rev_with(t, M, t["path"][:24])
        r2._Y[i] = r2._Y[i] + np.array([0.5 if np.isfinite(v) else 0.0 for v in r2._Y[i]]); r2._A[i] = r2._A[i] * 1.6; r2._y[i] = 1 - r2._y[i]
        F1, _, _ = K.cf_features(Z, r2, K.ATS, rows); p1 = K.e1_oof(t["X"], r2)
        worst_self = max(worst_self, float(np.max(np.abs(F1[j] - F0[j]))), abs(float(p1[j] - p0[j])))
        changed_other += int(np.any(np.abs(F1[fold != fold[j]] - F0[fold != fold[j]]) > 1e-9))
    out["own_outcome_changes_own_oof_prediction_max"] = worst_self; out["other_folds_changed_in_cases"] = changed_other
    out["PASS"] = bool(worst_self == 0.0 and changed_other > 0)
    return out


def main():
    RC.limit_threads(1); M = P.manifest(); t = P.tasks((1,))[0]; res = {"utc": RC.utc(), "honesty": honesty(M, t), "shadow": {}}
    for arm in ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN"):
        r1 = K.run_adaptive(t, arm, 20, M=M); r2 = K.run_adaptive(t, arm, 20, M=_corrupt(M, set(r1["paid_ids"]), 11))
        res["shadow"][arm] = {"identical_path": r1["paid_ids"] == r2["paid_ids"], "identical_predictions": _same(r1["evals"], r2["evals"]), "seconds": round(r1["seconds"], 1)}
        print(arm, res["shadow"][arm], flush=True)
    rng = np.random.default_rng(3); z = rng.normal(0, 2, 400); y = (rng.random(400) < 1 / (1 + np.exp(-z))).astype(int)
    a, c = K.calib_map(1 / (1 + np.exp(-z)), y); res["calibration_identity_recovery"] = {"a": float(a), "c": float(c), "ok": bool(abs(a) < 0.3 and abs(c - 1) < 0.3)}
    res["status"] = "PASS" if res["honesty"]["PASS"] and all(v["identical_path"] and v["identical_predictions"] for v in res["shadow"].values()) and res["calibration_identity_recovery"]["ok"] else "FAIL"
    K_OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"; K_OUT.mkdir(parents=True, exist_ok=True)
    (K_OUT / "RC19B_VALIDATION.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
