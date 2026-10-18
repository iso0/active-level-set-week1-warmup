"""RC18 fix A1 — latent / observation variance contract of the PHYS_DISCOVERY surprise rule (audit; frozen code untouched).

1. hand: a hand-solvable sklearn GP (fixed kernel, 2 training points) in the environment the studies used, to establish what
   GaussianProcessRegressor.predict(return_std=True) returns when the kernel contains a WhiteKernel, with and without
   normalize_y.
2. replay: re-runs the frozen PHYS_DISCOVERY SD_MAXVAR trajectories with the frozen code path, only instrumenting the GP's
   predict() at the surprise step, to recover the pre-observation moments (m, sd, noise) of every paid run. The replay is
   valid only if it reproduces the cached paid path and the logged z exactly; then the corrected z = (y - m) / sd is computed
   on the SAME (old) path and every trigger change is listed. Changes after the first divergence of a corrected path cannot
   be read from this replay: that needs the prospective v1.1 run (src/rc18_phys_discovery_v11.py).
    python -m src.rc18_fix_variance hand | replay
"""
from __future__ import annotations

import gzip
import json
import sys
import time

import numpy as np

import src.rc18_common as RC

OUT = RC.CAMP / "fixes" / "A1_variance_contract"


def hand():
    import sklearn
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    c, ell, s2 = 2.0, 0.7, 0.3
    X = np.array([[0.0], [1.0]]); y = np.array([1.0, -0.5]); xs = np.array([[0.4]])
    def k(a, b):
        d = np.abs(a - b.T) / ell; return c * (1 + np.sqrt(3) * d) * np.exp(-np.sqrt(3) * d)
    res = {"sklearn": sklearn.__version__, "numpy": np.__version__, "kernel": f"{c}*Matern(l={ell}, nu=1.5) + White({s2})", "cases": {}}
    for norm in (False, True):
        g = GaussianProcessRegressor(ConstantKernel(c, "fixed") * Matern(ell, "fixed", nu=1.5) + WhiteKernel(s2, "fixed"),
                                     optimizer=None, normalize_y=norm).fit(X, y)
        m, sd = g.predict(xs, return_std=True)
        if norm:                                               # analytic in standardized units, then back-transformed
            mu, sdv = y.mean(), y.std(); yt = (y - mu) / sdv
        else:
            mu, sdv, yt = 0.0, 1.0, y
        K = k(X, X) + s2 * np.eye(2); ks = k(X, xs); kss = c
        m_a = mu + sdv * float((ks.T @ np.linalg.solve(K, yt)).ravel()[0])
        lat = sdv ** 2 * float((kss - ks.T @ np.linalg.solve(K, ks)).ravel()[0]); noise = sdv ** 2 * s2
        theta_noise = float(g.kernel_.k2.noise_level) * float(np.atleast_1d(getattr(g, "_y_train_std", 1.0))[0]) ** 2   # = exp(theta[-1]) when the white level is free
        res["cases"][f"normalize_y={norm}"] = {
            "predict_mean": float(m[0]), "analytic_mean": m_a,
            "predict_sd^2": float(sd[0] ** 2), "analytic_latent_var": lat, "analytic_observation_var": lat + noise,
            "noise_in_original_units": noise, "frozen_code_noise_term": theta_noise,
            "predict_sd_equals": "observation (latent + noise)" if abs(sd[0] ** 2 - (lat + noise)) < 1e-10 else
                                 ("latent" if abs(sd[0] ** 2 - lat) < 1e-10 else "neither"),
            "frozen_code_denominator_var": float(sd[0] ** 2) + theta_noise}
    ok = all(v["predict_sd_equals"] == "observation (latent + noise)" for v in res["cases"].values())
    res["contract"] = ("In this environment predict(return_std=True) with a WhiteKernel in the fitted kernel returns the OBSERVATION "
                       "predictive SD (latent + white noise); with normalize_y the noise in original units is exp(theta_white) * "
                       "y_train_std^2. The frozen PHYS_DISCOVERY rule computed z = (y - m) / sqrt(sd^2 + noise), i.e. it counted the "
                       "noise twice: denominator variance = latent + 2 * noise. The protocol's formula (y - m) / sqrt(var_prev + noise) "
                       "with var_prev the LATENT variance equals (y - m) / sd." if ok else "UNEXPECTED: see cases")
    res["status"] = "PASS" if ok and all(abs(v["predict_mean"] - v["analytic_mean"]) < 1e-10 for v in res["cases"].values()) else "CHECK"
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "HAND_CHECK.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1)); return res


def replay():
    import src.jdl_phys_al as PAL
    import src.jdl_phys_discovery as PD
    RC.limit_threads(1)
    rec = []                                        # (m, sd, noise) of every return_std predict on ONE row (the surprise step)
    orig_fit = PAL.gp_fit

    class Probe:
        def __init__(self, g):
            self.g = g; self.kernel_ = g.kernel_; self._y_train_std = g._y_train_std
        def predict(self, Z, return_std=False):
            out = self.g.predict(Z, return_std=return_std)
            if return_std and len(Z) == 1:
                noise = float(np.exp(self.g.kernel_.theta[-1])) * float(self.g._y_train_std) ** 2
                rec.append((float(out[0][0]), float(out[1][0]), noise))
            return out

    PD.PAL.gp_fit = lambda Z, y: Probe(orig_fit(Z, y))
    rows, summary = [], {}
    try:
        for pop in ("NEW", "OLD"):
            Tt, qc = PAL.targets(pop), PD.qc_table(pop); y_all = Tt[PD.RESPONSE]
            T = {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}
            for (r, f), t in sorted(T.items()):
                cached = json.loads(gzip.decompress((PD.CACHE / f"{pop}__r{r}_f{f}__SD_MAXVAR.json.gz").read_bytes()))
                rec.clear(); t0 = time.time()
                a = PD.run_traj(t, pop, "SD_MAXVAR", Tt, qc)
                same_path = a["paid"] == cached["paid"]
                log = a["sd_log"]; same_z = len(log) == len(cached["sd_log"]) and all(
                    (x["z"] is None and c["z"] is None) or (x["z"] is not None and c["z"] is not None and abs(x["z"] - c["z"]) <= 1e-9 * max(1, abs(c["z"])))
                    for x, c in zip(log, cached["sd_log"]))
                if len(rec) != len(log):
                    raise RuntimeError(f"probe count {len(rec)} != log length {len(log)} for {pop} r{r} f{f}")
                ids = np.asarray(t["ids"]).astype(str)
                for x, (m, sd, noise) in zip(log, rec):
                    yv = float(y_all.get(x["selected"], np.nan))
                    z_old = x["z"]; z_new = None if not np.isfinite(yv) else (yv - m) / sd
                    if z_old is not None:
                        assert abs(z_old - (yv - m) / np.sqrt(sd ** 2 + noise)) <= 1e-9 * max(1, abs(z_old)), "z reconstruction mismatch"
                    qc_ok = bool(qc.get(x["selected"], False)) and z_new is not None
                    ev_old = x["event"]; ev_new = "QC_EVENT" if not qc_ok else ("SURPRISE" if abs(z_new) >= PD.Z_SURPRISE else "none")
                    rows.append({"pop": pop, "repeat": r, "fold": f, "budget": x["budget"], "selected": x["selected"], "how": x["how"],
                                 "m": m, "sd_observation": sd, "noise": noise, "latent_var": sd ** 2 - noise, "y": yv,
                                 "z_frozen": z_old, "z_corrected": z_new, "event_frozen": ev_old, "event_corrected_same_path": ev_new})
                summary[f"{pop}_r{r}_f{f}"] = {"replay_reproduces_path": same_path, "replay_reproduces_z": same_z, "seconds": round(time.time() - t0, 2),
                                              "surprises_frozen": sum(x["event"] == "SURPRISE" for x in log)}
                print(json.dumps({"pop": pop, "r": r, "f": f, **summary[f"{pop}_r{r}_f{f}"]}), flush=True)
    finally:
        PD.PAL.gp_fit = orig_fit
    import pandas as pd
    D = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True); D.to_csv(OUT / "replay_moments.csv", index=False, lineterminator="\n")
    ch = D[D.event_frozen != D.event_corrected_same_path]
    first = {}
    for (pop, r, f), g in D.groupby(["pop", "repeat", "fold"]):
        c = g[g.event_frozen != g.event_corrected_same_path]
        first[f"{pop}_r{r}_f{f}"] = None if c.empty else int(c.budget.min())
    res = {"all_replays_exact": bool(all(v["replay_reproduces_path"] and v["replay_reproduces_z"] for v in summary.values())),
           "trajectories": summary, "observations": int(len(D)),
           "trigger_changes_same_path": {"total": int(len(ch)), "none_to_SURPRISE": int(((ch.event_frozen == "none") & (ch.event_corrected_same_path == "SURPRISE")).sum()),
                                         "SURPRISE_to_none": int(((ch.event_frozen == "SURPRISE") & (ch.event_corrected_same_path == "none")).sum()),
                                         "by_population": ch.groupby("pop").size().to_dict()},
           "surprises_frozen": D.groupby("pop").apply(lambda g: int((g.event_frozen == "SURPRISE").sum())).to_dict(),
           "surprises_corrected_same_path": D.groupby("pop").apply(lambda g: int((g.event_corrected_same_path == "SURPRISE").sum())).to_dict(),
           "first_trigger_change_budget": first,
           "noise_share_of_observation_var": {"median": float((D.noise / D.sd_observation ** 2).median()), "p10": float((D.noise / D.sd_observation ** 2).quantile(0.1)),
                                              "p90": float((D.noise / D.sd_observation ** 2).quantile(0.9))},
           "z_ratio_corrected_over_frozen": {"median": float((D.z_corrected / D.z_frozen).dropna().median())},
           "scope": "Same-path counterfactual only: after the first changed trigger the corrected rule would choose a different path, whose outcome is measured prospectively by the v1.1 run."}
    (OUT / "REPLAY_RESULT.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "trajectories"}, indent=1, default=str)); return res


if __name__ == "__main__":
    {"hand": hand, "replay": replay}[sys.argv[1]]()
