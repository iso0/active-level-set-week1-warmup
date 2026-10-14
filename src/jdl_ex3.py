"""Exploratory EX3 - does uncertain coupling (V2) add anything once the response prior is trained on paid depths?

Mechanism (from EX2 and the V2 design).  EX2 showed that a paid-only ML-II response prior removes most of J's
fast-scan depth over-prediction (NEW B40 specificity at 0.5: 0.104 -> 0.542).  The negatives that remain wrong at 0.5
are fast scans whose depth is above the 111 um reference, i.e. places where the depth-label bridge itself points the
wrong way.  V2 can move posterior mass away from rho = 1 when the paid labels contradict the bridge, but its coupling
is global: on NEW the paid positives (mostly deep slow scans) agree with the bridge, so the mass should stay near
rho = 1 and the mixture should behave like the fixed-coupling model.

Data: NEW only, DEV repeats 5-8 (the EX1/EX2 repeats; never the frozen V2 repeats 1-2), five folds, B16/B40, the EX1
feature-only maximin paths.  Model: V2 (src.jdl_v2_model, EP) with f and g sharing the response kernel that EX2's
ML-II learned on the PAID responses of the same checkpoint (amplitude and four lengthscales read from EX2's fit log -
exact reuse, no new hyperparameter fit); delta, theta, tau and the rho prior fixed.  Controls: J_trained (EX2,
Laplace, rho fixed at 1, same trained prior; stored predictions), the mixture's own rho = 1 EP component, and
Binary_V2_EP with the fixed reference prior (new fits).  Caveat: with a depth-trained k_f the rho = 0 component is no
longer capacity-matched to a depth-free classifier.

Steps: python -m src.jdl_ex3 manifest | run | evaluate       (one BLAS thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import src.jdl_model as JM
import src.jdl_stage_m as SMM
import src.jdl_v2_model as V2
from src.jdl_ex1 import EX as EX1_DIR, REPEATS, build_tasks_r
from src.jdl_ex2 import EX as EX2_DIR

EX = SMM.OUT / "exploratory" / "EX3_V2_with_trained_response_prior"
CACHE = SMM.OUT / "_cache" / "ex3"
CAP_COMPONENT_SOLVES = 200
PREDICTIONS = {
    "EX3-P1_mechanism": "NEW, B40: the median (over the 20 checkpoints) posterior mass of V2_trained on rho = 1 is >= 0.8. Falsified if it is below 0.8.",
    "EX3-P2_consequence": "NEW, B40, p >= 0.5: |BA(V2_trained) - BA(rho1_trained_EP)| < 0.01 (uncertain global coupling adds nothing once the response prior is trained). Falsified if the absolute difference is >= 0.01.",
    "EX3-P3_inference": "NEW, B40: rho1_trained_EP vs J_trained (EP vs Laplace with the same trained prior): no directional expectation; reported.",
    "EX3-P4_reference": "Binary_V2_EP (fixed prior, no depth) at 0.5 is reported as the depth-free reference; no expectation.",
}


def trained_hypers():
    f = pd.read_csv(EX2_DIR / "fit_log.csv")
    f = f[f.population == "NEW"]
    return {(int(r.repeat), int(r.fold), int(r.budget)): (float(r.f_amplitude), tuple(json.loads(r.f_lengthscale))) for r in f.itertuples()}


def write_manifest():
    EX.mkdir(parents=True, exist_ok=True)
    hp = trained_hypers()
    paths = pd.read_csv(EX1_DIR / "paths.csv")
    sha_by = {f"NEW_r{r}_f{f}": hashlib.sha256("\n".join(g.sort_values("query_index").sim_id).encode()).hexdigest()
              for (r, f), g in paths[paths.population == "NEW"].groupby(["repeat", "fold"])}
    man = {"idea": "EX3 V2 coupling mixture with the EX2-trained response prior", "status": "EXPLORATORY, frozen before any EX3 fit; separate from the frozen V2 comparison (DEV 1-2)",
           "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "mechanism": __doc__.split("Mechanism")[1].split("Data:")[0].strip(" .\n"), "data": {"population": "NEW", "repeats": list(REPEATS), "folds": [1, 2, 3, 4, 5], "budgets": list(SMM.BUDGETS),
           "paths": "exploratory/EX1_ba_aligned_decision_rule/paths.csv", "path_sha256_by_task": sha_by},
           "trained_part": "f and g share k_f with EX2's paid-only ML-II amplitude and lengthscales for the same checkpoint (read from EX2 fit_log.csv; no refit); delta 0.35, theta 0.35, tau 0.15, sigma_z 0.03, rho prior 1/3 each unchanged",
           "arms": {"V2_trained": "new EP mixture fits", "rho1_trained_EP": "the V2_trained rho=1 EP component (exact reuse; separate EP fit only after a whole-mixture fallback)",
                    "J_trained": "EX2 stored predictions (Laplace, rho = 1, same trained prior)", "Binary_V2_EP": "new EP fits with the fixed reference prior, no continuous likelihood"},
           "predictions": PREDICTIONS, "outcomes": "BA, specificity, sensitivity, short-K sensitivity, q20, log loss, AUC at p >= 0.5; component masses; paired class-stratified simulation-cluster bootstrap",
           "bounded_plan": {"checkpoints": 40, "component_solves": "120 (V2_trained) + 40 (Binary_V2_EP)", "cap_including_fallback": CAP_COMPONENT_SOLVES, "runs": "one; no tuning, all outcomes preserved"},
           "trained_hyperparameters_sha256": hashlib.sha256(json.dumps(sorted((str(k), v) for k, v in hp.items())).encode()).hexdigest(),
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in ("src/jdl_ex3.py", "src/jdl_v2_model.py", "src/jdl_model.py", "src/jdl_stage_m.py", "src/jdl_ex1.py", "src/jdl_ex2.py")}}
    (EX / "EX3_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "bounded_plan")}, indent=1))


def run():
    man_p = EX / "EX3_MANIFEST.json"
    if not man_p.exists() or not SMM._git("log", "--format=%H", "--", str(man_p.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the EX3 manifest first")
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the EX3 freeze")
    hp = trained_hypers()
    tasks = [t for t in build_tasks_r() if t["population"] == "NEW"]
    paths = pd.read_csv(EX1_DIR / "paths.csv")
    CACHE.mkdir(parents=True, exist_ok=True)
    solves, t0 = 0, time.time()
    for t in tasks:
        g = paths[(paths.population == "NEW") & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != man["data"]["path_sha256_by_task"][f"NEW_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit("path differs from the EX3 manifest")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
        std, _ = SMM.standardizer(t)
        xr, xt = std(t["X"][t["pool"]]), std(t["X"][t["test"]])
        test_ids = [str(t["ids"][i]) for i in t["test"]]
        for b in SMM.BUDGETS:
            cf = CACHE / f"NEW__r{t['repeat']}_f{t['fold']}__B{b}.json.gz"
            if cf.exists():
                continue
            paid = SMM.Oracle(t).reveal(t["path"][:b])
            Xp, yp, zp = std(paid.X), paid.y.astype(float), paid.z
            amp, ell = hp[(t["repeat"], t["fold"], b)]
            cfg = replace(JM.STAGE_M_CONFIG, f_amplitude=amp, f_lengthscale=ell)
            rec = {"repeat": t["repeat"], "fold": t["fold"], "budget": b, "f_amplitude": amp, "f_lengthscale": list(ell), "pi_hat": float(np.mean(paid.y))}
            preds = []
            try:
                mix = V2.JointModelV2(xr, cfg).fit(Xp, yp, zp); solves += mix.solve_count
                bm = V2.JointModelV2(xr, JM.STAGE_M_CONFIG).fit(Xp, yp, zp, use_response=False); solves += bm.solve_count
                pm, pc, pb = mix.predict_proba(xt), mix.component_probabilities(xt), bm.predict_proba(xt)
                if mix.diagnostics["fallback"]:
                    sep = V2.JointModelV2(xr, cfg, rhos=(1.0,)).fit(Xp, yp, zp); solves += sep.solve_count
                    p1, r1_method = sep.predict_proba(xt), sep.diagnostics["components"][0]["method"]
                else:
                    p1, r1_method = pc[list(V2.RHOS).index(1.0)], "ep (mixture component)"
                rec.update({"status": "ok", "weights": mix.weights.tolist(), "log_evidence": mix.diagnostics["log_evidence"], "fallback": mix.diagnostics["fallback"],
                            "components": mix.diagnostics["components"], "binary_weights": bm.weights.tolist(), "rho1_method": r1_method})
                for j, sid in enumerate(test_ids):
                    preds += [{"repeat": t["repeat"], "fold": t["fold"], "budget": b, "sim_id": sid, "arm": a, "p": float(v[j]), "prediction_status": "ok", "pi_hat": rec["pi_hat"]}
                              for a, v in (("V2_trained", pm), ("rho1_trained_EP", p1), ("Binary_V2_EP", pb))]
            except V2.NUMERICAL_ERRORS as ex:
                rec.update({"status": "failed", "error": f"{type(ex).__name__}: {ex}"[:300]})
            cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=float).encode()))
            if solves > CAP_COMPONENT_SOLVES:
                raise SystemExit("EX3 component-solve cap reached")
            print(t["repeat"], t["fold"], b, rec["status"], np.round(rec.get("weights", []), 3), flush=True)
    print(f"EX3 component solves this session: {solves}, {time.time() - t0:.1f}s")


def evaluate():
    from src.jdl_evaluate import boot_weights
    from src.jdl_ex_metrics_addendum import frame
    from src.jdl_v2_evaluate import METRICS, wmetrics_thr
    fits, preds = [], []
    for f in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes())); fits.append(r["fit"]); preds += r["predictions"]
    pr = pd.DataFrame(preds)
    jt = pd.read_csv(EX2_DIR / "predictions_all.csv.gz"); jt = jt[(jt.population == "NEW") & (jt.arm == "J_trained")]
    pr = pd.concat([pr, jt[["repeat", "fold", "budget", "sim_id", "arm", "p", "prediction_status", "pi_hat"]]], ignore_index=True)
    tasks = build_tasks_r()
    F = frame("NEW", tasks); ids, y, sk = F["ids"], F["y"], F["shortk"]
    W = boot_weights(y)
    pos = {s: i for i, s in enumerate(ids)}
    rows, store = [], {}
    for arm in ("V2_trained", "rho1_trained_EP", "J_trained", "Binary_V2_EP"):
        for b in SMM.BUDGETS:
            for rep in REPEATS:
                g = pr[(pr.arm == arm) & (pr.repeat == rep) & (pr.budget == b)]
                p = np.full(len(ids), np.nan); p[g.sim_id.map(pos).to_numpy(int)] = g.p.astype(float).to_numpy()
                m, cnt, _ = wmetrics_thr(p, np.isfinite(p), y, sk, F["q20"][rep], F["fold"][rep], W, np.full(len(ids), 0.5))
                store[(arm, b, rep)] = p
                rows.append({"arm": arm, "budget": b, "repeat": rep, **{k: float(v[0]) for k, v in m.items()}, **cnt})
    mt = pd.DataFrame(rows)
    crow = []
    for a1, a2 in (("V2_trained", "rho1_trained_EP"), ("rho1_trained_EP", "J_trained"), ("V2_trained", "J_trained"), ("V2_trained", "Binary_V2_EP"), ("J_trained", "Binary_V2_EP")):
        for b in SMM.BUDGETS:
            per = {k: [] for k in METRICS}
            for rep in REPEATS:
                p1, p2 = store[(a1, b, rep)], store[(a2, b, rep)]; c = np.isfinite(p1) & np.isfinite(p2)
                m1, _, _ = wmetrics_thr(p1, c, y, sk, F["q20"][rep], F["fold"][rep], W, np.full(len(ids), 0.5))
                m2, _, _ = wmetrics_thr(p2, c, y, sk, F["q20"][rep], F["fold"][rep], W, np.full(len(ids), 0.5))
                for k in METRICS:
                    per[k].append(m1[k] - m2[k])
            for k in METRICS:
                d = np.nanmean(np.vstack(per[k]), axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
                crow.append({"arm": a1, "ref": a2, "budget": b, "metric": k, "estimate": float(d[0]), "per_repeat": json.dumps([round(float(x[0]), 4) for x in per[k]]),
                             "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi)})
    ct = pd.DataFrame(crow)
    w40 = np.array([f["weights"] for f in fits if f["budget"] == 40 and f["status"] == "ok"])
    d = ct[(ct.arm == "V2_trained") & (ct.ref == "rho1_trained_EP") & (ct.budget == 40) & (ct.metric == "BA")].iloc[0]
    res = {"EX3-P1_mechanism": {"median_mass_rho1_B40": float(np.median(w40[:, 2])), "mean_masses_B40": w40.mean(0).tolist(), "supported": bool(np.median(w40[:, 2]) >= 0.8)},
           "EX3-P2_consequence": {"BA_difference": float(d.estimate), "interval": [float(d.cluster_bootstrap_lo), float(d.cluster_bootstrap_hi)], "supported": bool(abs(d.estimate) < 0.01)},
           "fits": len(fits), "statuses": pd.Series([f["status"] for f in fits]).value_counts().to_dict(), "fallbacks": int(sum(bool(f.get("fallback")) for f in fits))}
    EX.mkdir(parents=True, exist_ok=True)
    mt.to_csv(EX / "metrics_per_repeat.csv", index=False, lineterminator="\n"); ct.to_csv(EX / "contrasts.csv", index=False, lineterminator="\n")
    pr.to_csv(EX / "predictions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(fits).to_csv(EX / "fit_log.csv", index=False, lineterminator="\n")
    (EX / "EX3_RESULTS.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mt.groupby(["budget", "arm"])[list(METRICS) + ["TP", "FN", "TN", "FP"]].mean().round(3).to_string())
    print(ct[ct.metric.isin(["BA", "specificity", "shortK_sensitivity"])].round(4).to_string())
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    {"manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
