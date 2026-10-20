"""RC20 acceptance of the sequential-stage code before its freeze (no evaluation metric is computed):
  1. shadow: both candidate arms rerun with every never-paid outcome randomised give the identical path and predictions;
  2. eta variance: the propagated Var(eta) used by eta-straddle equals a Monte-Carlo estimate from independent draws of the
     upstream latent outputs (the variance contract: latent variances only, no observation noise, outputs independent);
  3. consistency: the sequential step function (cand_state) reproduces the Stage 1 construction at the same paid state.
    python -m src.rc20_validate_final
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc20_decisions as DEC
import src.rc20_final as F
from src.rc19_validate import _corrupt, _same

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"


def eta_mc(t, M, cand, b=24, S=4000):
    Z = P.zstd(t); rev = K._rev_with(t, M, list(t["path"][:b])); cands = np.setdiff1d(t["pool"], rev.paid)[:40]; h = A.hcol(t)
    up = "SHQT" if cand.startswith("SHQT") else "SHQ"; use_h = cand.endswith("_H"); L = rev.paid; y = rev.paid_y()[L]; rows = cands
    R = A.cf(Z, rev, A.ATS, up, rows, Hc=h if up == "SHQT" else None)
    xtr, xev = (h[L][:, None], h[rows][:, None]) if use_h else (None, None)
    p, g, mu, sd = A.clf(R["F"], y, R["E"], xtr, xev); eta, var = A.eta_moments(g, mu, sd, R["E"], R["V"], xev)
    rng = np.random.default_rng(3); draws = R["E"][None] + np.sqrt(np.maximum(R["V"], 0))[None] * rng.standard_normal((S,) + R["E"].shape)
    X = draws if xev is None else np.concatenate([draws, np.broadcast_to(xev[None], (S,) + xev.shape)], axis=2)
    e_mc = g.decision_function(((X - mu) / sd).reshape(-1, X.shape[2])).reshape(S, -1)
    rel = np.abs(e_mc.var(0) - var) / np.maximum(var, 1e-12)
    st = A.cand_state(t, rev, Z, cand, cands)
    return {"max_rel_err_var": float(rel.max()), "median_rel_err_var": float(np.median(rel)), "max_abs_err_mean": float(np.max(np.abs(e_mc.mean(0) - eta))),
            "cand_state_matches_direct": float(np.max(np.abs(st["eta_cand"] - eta))), "PASS": bool(np.median(rel) < 0.05 and rel.max() < 0.15 and np.max(np.abs(st["eta_cand"] - eta)) < 1e-9)}


def consistency(t, M, cand):
    Z = P.zstd(t); rev = K._rev_with(t, M, list(t["path"][:20])); cands = np.setdiff1d(t["pool"], rev.paid)
    st = A.cand_state(t, rev, Z, cand, cands); out, _ = A.constructions(t, rev, Z, (cand,))
    return {"max_abs_diff": float(np.max(np.abs(st["p_test"] - out[cand]))), "PASS": bool(np.max(np.abs(st["p_test"] - out[cand])) < 1e-12)}


def main():
    RC.limit_threads(1); M = P.manifest(); t = P.tasks((1,))[0]; res = {"utc": RC.utc(), "cand": DEC.CAND, "shadow": {}}
    for arm in F.CAND_ARMS:
        r1 = F.run_cand(t, arm, 20, M); r2 = F.run_cand(t, arm, 20, _corrupt(M, set(r1["paid_ids"]), 23))
        strip = lambda ev: [{k: v for k, v in e.items() if k != "cpu_s"} for e in ev]
        res["shadow"][arm] = {"identical_path": r1["paid_ids"] == r2["paid_ids"], "identical_predictions": _same(strip(r1["evals"]), strip(r2["evals"])), "seconds": round(r1["seconds"], 1)}
        print(arm, res["shadow"][arm], flush=True)
    res["eta_variance"] = eta_mc(t, M, DEC.CAND); res["consistency"] = consistency(t, M, DEC.CAND)
    res["status"] = "PASS" if all(v["identical_path"] and v["identical_predictions"] for v in res["shadow"].values()) and res["eta_variance"]["PASS"] and res["consistency"]["PASS"] else "FAIL"
    (OUT / "RC20_VALIDATION_FINAL.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
