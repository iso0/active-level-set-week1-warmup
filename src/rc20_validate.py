"""RC20 numerical acceptance before any scientific comparison (no evaluation metric is computed here):
  1. reproduction: on cached RC19B final paths, SHQ_ATS equals the cached ATSCF and M0Q_A the cached DEPTHCF (K = 10);
  2. honesty: changing a paid run's OWN outcomes never changes its own out-of-fold feature (M0Q, SHQ, SHQT, SHQM) while it may
     change other folds' features; the FD fold models never use their own fold;
  3. shadow: randomising every never-paid outcome leaves every construction identical on a fixed paid prefix;
  4. log h: equals week18_engine.logh (LS = Gaussian spot radius in m) up to the public pool standardisation.
    python -m src.rc20_validate
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
from src.rc19_validate import _corrupt

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"


def reproduction(M, tasks):
    worst = {}
    for (r, f, arm) in ((11, 1, "E1S"), (12, 3, "ATSCF_MARGIN"), (13, 5, "DEPTHCF_MARGIN")):
        t = tasks[(r, f)]; u = RC.read_json_gz(B19 / f"r{r}_f{f}__{arm}.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}; paid = [pos[s] for s in u["paid_ids"]]
        cache = {e["budget"]: e["p_all"] for e in u["evals"] if "p_all" in e}; Z = P.zstd(t)
        for b in (12, 24, 48):
            rev = K._rev_with(t, M, paid[:b]); out, _ = A.constructions(t, rev, Z, ("SHQ_ATS", "M0Q_A"))
            for mine, theirs in (("SHQ_ATS", "ATSCF"), ("M0Q_A", "DEPTHCF")):
                ref = np.asarray([np.nan if v is None else v for v in cache[b][theirs]], float)
                worst[mine] = max(worst.get(mine, 0.0), float(np.nanmax(np.abs(out[mine] - ref))))
    return {"max_abs_diff": worst, "PASS": bool(all(v < 1e-6 for v in worst.values()))}


def honesty(M, t):
    Z = P.zstd(t); h = A.hcol(t); rev = K._rev_with(t, M, t["path"][:24]); paid = rev.paid; fold, k = K.folds(len(paid), A.KF); res = {"K": int(k)}
    for model in ("M0Q", "SHQ", "SHQT", "SHQM"):
        R0 = A.cf(Z, rev, A.ATS, model, t["test"][:5], Hc=h if model == "SHQT" else None, fold_eval=True); worst_self = 0.0; other = 0; fe_self = 0.0
        for j in (0, 3, 11):
            i = int(paid[j]); r2 = K._rev_with(t, M, t["path"][:24])
            r2._Y[i] = r2._Y[i] + np.array([0.5 if np.isfinite(v) else 0.0 for v in r2._Y[i]]); r2._A[i] = r2._A[i] * 1.6; r2._y[i] = 1 - r2._y[i]
            R1 = A.cf(Z, r2, A.ATS, model, t["test"][:5], Hc=h if model == "SHQT" else None, fold_eval=True)
            worst_self = max(worst_self, float(np.nanmax(np.abs(R1["F"][j] - R0["F"][j]))))
            other += int(np.any(np.abs(R1["F"][fold != fold[j]] - R0["F"][fold != fold[j]]) > 1e-9))
            fe_self = max(fe_self, float(np.nanmax(np.abs(R1["FE"][fold[j]] - R0["FE"][fold[j]]))))   # fold model of j's own fold
        res[model] = {"own_outcome_changes_own_oof_feature_max": worst_self, "other_folds_changed_in_cases": other,
                      "own_fold_model_changes_max": fe_self, "PASS": bool(worst_self == 0.0 and other > 0 and fe_self == 0.0)}
    res["PASS"] = bool(all(v["PASS"] for v in res.values() if isinstance(v, dict)))
    return res


def shadow(M, t):
    Z = P.zstd(t); paid = list(t["path"][:20]); r1 = K._rev_with(t, M, paid); o1, _ = A.constructions(t, r1, Z, A.ATTR, remedy=("FD", "MAP"))
    Mc = _corrupt(M, {t["ids"][i] for i in paid}, 17); r2 = K._rev_with(t, Mc, paid); o2, _ = A.constructions(t, r2, Z, A.ATTR, remedy=("FD", "MAP"))
    diff = {k: float(np.max(np.abs(o1[k] - o2[k]))) for k in o1}
    return {"max_abs_diff": diff, "PASS": bool(all(v == 0.0 for v in diff.values()))}


def logh_check(t):
    import src.week18_engine as E
    h = A.hcol(t); ref = E.logh(t["X"]); p = t["pool"]; ref_s = (ref - ref[p].mean()) / ref[p].std()
    LS = t["X"][:, 2]
    return {"max_abs_diff_vs_week18_logh_standardised": float(np.max(np.abs(h - ref_s))), "LS_range_m": [float(LS.min()), float(LS.max())],
            "convention": "LS = Gaussian laser spot radius in metres (claims C20); h = P / sqrt(VX LS^3) in W s^0.5 m^-2; log h standardised on the pool",
            "PASS": bool(np.max(np.abs(h - ref_s)) < 1e-9 and 1e-5 < LS.min() and LS.max() < 1e-3)}


def main():
    RC.limit_threads(1); M = P.manifest(); tasks = {(x["repeat"], x["fold"]): x for x in P.tasks([11, 12, 13])}; t1 = P.tasks((1,))[0]
    res = {"utc": RC.utc(), "reproduction": reproduction(M, tasks)}; print("reproduction", res["reproduction"], flush=True)
    res["honesty"] = honesty(M, t1); print("honesty", res["honesty"]["PASS"], flush=True)
    res["shadow"] = shadow(M, t1); print("shadow", res["shadow"]["PASS"], flush=True)
    res["logh"] = logh_check(t1)
    res["status"] = "PASS" if all(res[k]["PASS"] for k in ("reproduction", "honesty", "shadow", "logh")) else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RC20_VALIDATION.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
