"""V2 model comparison: NEW only, DEV repeats 1-2, five folds, B16/B40, the saved Week 19 feature-only maximin
prefixes (= Stage M NEW paths).  No acquisition, startup extension, reseeding or monitor-based candidate filtering.

Arms (nine; 9 x 20 = 180 top-level checkpoint requests counted before exact reuse)
  V2_EP_mixture      new   src.jdl_v2_model.JointModelV2, rho in {0, .5, 1}, EP, fixed reference priors
  rho1_EP            reuse the mixture's rho = 1 EP component when it was fitted by EP; otherwise a separate fixed-rho=1 fit
                           (a component produced by the whole-mixture Laplace fallback is never used as the EP control)
  Binary_V2_EP       new   same model without the continuous likelihood (one shared EP solve; masses stay at 1/3)
  V1_Laplace         reuse Stage M arm J (immutable jdl-port-1.0; identical paths, scaler, priors, target, missingness)
  Binary_V1_Laplace  reuse Stage M arm Binary_matched
  ACTIVE_E1          reuse Stage M arm ACTIVE_E1 (frozen Week 18 implementation through the Week 19 fit_one)
  G3                 reuse Stage M arm G3
  J_trained          new   EX2's rule exactly (src.jdl_ex2.trained_config: paid-response-only ML-II of the response prior)
  VX_stump           new   src.jdl_vx_stump: depth-one classifier on the fold-pool-standardized log VX, paid labels only

Steps: python -m src.jdl_v2_comparison manifest | run | evaluate       (one BLAS thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

import src.jdl_model as JM
import src.jdl_stage_m as SMM
import src.jdl_v2_model as V2
import src.jdl_vx_stump as VS

OUT = SMM.OUT / "v2_model_comparison"
CACHE = SMM.OUT / "_cache" / "v2"
STATE = OUT / "RUN_STATE.json"
MANIFEST = OUT / "V2_MANIFEST.json"
VALIDATION = OUT / "validation" / "V2_VALIDATION.json"
CFG = JM.STAGE_M_CONFIG
POP, REPEATS, BUDGETS = "NEW", (1, 2), (16, 40)
ARMS = ("V2_EP_mixture", "rho1_EP", "Binary_V2_EP", "V1_Laplace", "Binary_V1_Laplace", "ACTIVE_E1", "G3", "J_trained", "VX_stump")
REUSED = {"V1_Laplace": "J", "Binary_V1_Laplace": "Binary_matched", "ACTIVE_E1": "ACTIVE_E1", "G3": "G3"}
PROBABILISTIC = ("V2_EP_mixture", "rho1_EP", "Binary_V2_EP", "V1_Laplace", "Binary_V1_Laplace", "ACTIVE_E1", "G3", "J_trained")
CAPS = {"top_level_requests": 180, "component_attempts_including_validation_and_fallback": 300}
CONTRASTS = {
    "primary": [("V2_EP_mixture", "Binary_V2_EP")],
    "mechanism": [("rho1_EP", "V1_Laplace"), ("V2_EP_mixture", "rho1_EP")],
    "system": [("V2_EP_mixture", "J_trained"), ("V2_EP_mixture", "ACTIVE_E1"), ("V2_EP_mixture", "G3"), ("V2_EP_mixture", "VX_stump")],
    "descriptive": [("Binary_V2_EP", "Binary_V1_Laplace"), ("J_trained", "Binary_V2_EP"), ("J_trained", "ACTIVE_E1"), ("VX_stump", "G3")],
}
CODE = ["src/jdl_v2_model.py", "src/jdl_v2_comparison.py", "src/jdl_v2_evaluate.py", "src/jdl_vx_stump.py", "src/jdl_v2_validation.py", "src/jdl_model.py", "src/jdl_stage_m.py",
        "src/jdl_evaluate.py", "src/jdl_ex2.py", "src/jdl_ex1.py", "src/week19_dev_pilot.py", "src/week18_tasks.py", "src/week18_engine.py"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(path, obj):
    """Atomic write (temporary file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_default), encoding="utf-8")
    os.replace(tmp, path)


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


# ======================================================================================== manifest
def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8")) if VALIDATION.exists() else None
    if not val or val.get("status") != "PASS":
        raise SystemExit("V2 numerical validation must PASS before the comparison manifest is frozen")
    sm = json.loads((SMM.OUT / "STUDY_MANIFEST.json").read_text(encoding="utf-8"))
    inv = pd.read_csv(SMM.SM / "task_inventory.csv")
    inv = inv[(inv.population == POP) & inv.repeat.isin(REPEATS)]
    man = {
        "study": "V2 joint depth-label model comparison (separate from the frozen V1 Stage M; Stage M and C3 decisions unchanged)",
        "status": "FROZEN BEFORE ANY V2 COMPARISON FIT", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "parent_commit": SMM._git("rev-parse", "HEAD"), "baseline_reviewed": "2b22c13df41ee0179d5999ff07a98c0aa36814ca",
        "source_package": {"directory": "outputs/astra_joint_model_v2", "handoff": "OPUS_V2_IMPLEMENTATION_REQUEST.md",
                           "intake": "v2_model_comparison/intake/PACKAGE_INTAKE.json", "expansion": "Astra's seven-arm design plus two system controls (J_trained, VX_stump), prospectively; Astra's 140/180/200 fit caps are replaced by the caps below"},
        "data": {"population": "NEW-136 (124 Keyhole / 12 no Keyhole), canonical any-observed-Keyhole label, all 49 exclusions preserved, full simulation IDs",
                 "inputs": "P, VX, LS radius, ST only (log of each, standardized on the feature-only fold training pool, ddof 0)",
                 "response": "existing ACTIVE A (startup retained, 90 % of derived exit), z = log(A / 111 um); unavailable or nonpositive A is missing (never imputed); a missing response keeps its label and its query",
                 "repeats": list(REPEATS), "folds": [1, 2, 3, 4, 5], "budgets": list(BUDGETS),
                 "paths": "exactly the saved Week 19 feature-only maximin prefixes = stage_m/paths.csv NEW rows (verified identical to Week 19, 10/10)",
                 "path_sha256_by_task": {k: v for k, v in sm["paths"]["sha256_by_task"].items() if k.startswith("NEW_r1") or k.startswith("NEW_r2")},
                 "split_sha256_by_task": {f"NEW_r{r.repeat}_f{r.fold}": r.split_sha256 for r in inv.itertuples()},
                 "paid_interface": "src.jdl_stage_m.Oracle reveals only the paid rows (Y, z); the learner never receives unpaid or held-out outcomes",
                 "reference_pool": "the fixed feature-only fold training pool; delta is centred there; test rows are never candidates; the pool is never recentred on the paid subset or the prediction batch",
                 "no": ["adaptive acquisitions", "startup extension", "reseeding", "monitor-based candidate filtering", "held-out monitors or subgroup metadata in training"]},
        "priors_V2": {"f_sd": CFG.f_amplitude, "g_sd": CFG.f_amplitude, "delta_sd": CFG.discrepancy_amplitude, "theta_mean": CFG.threshold_mean,
                      "theta_sd": CFG.threshold_sd, "sigma_z": CFG.response_noise_sd, "tau": CFG.probit_scale, "kernel": "Matern-3/2",
                      "lengthscales": list(CFG.f_lengthscale), "delta_lengthscales": list(CFG.discrepancy_lengthscale), "jitter": CFG.jitter,
                      "rho_support": list(V2.RHOS), "rho_prior": [1 / 3] * 3, "nothing_trained": True},
        "inference_V2": {"method": "probit EP per component", "sites_initialised_at": 0, "updates": "parallel", "damping": V2.EP_DAMPING,
                         "stop": f"{V2.EP_CONSECUTIVE} consecutive relative natural-parameter changes < {V2.EP_TOL}", "max_iterations": V2.EP_MAX_ITER,
                         "evidence": "EP approximate label evidence including site constants; the identical response evidence cancels between components",
                         "fallback": f"if EP fails in ANY component, EVERY component is refitted by Laplace (accept: finite objective, whitened gradient inf-norm <= {V2.LAPLACE_ACCEPT}); a failing fallback marks that checkpoint failed; no component is dropped; tau, delta, tolerances are never changed; no second seed",
                         "prediction": "mixture of component probit probabilities; within- and between-component covariance retained",
                         "known_approximation_errors": "preserved as recorded by Astra (scalar EP 0.000583 vs Laplace 0.017007; two-label 0.00338/0.000579/0.000210; V1 sparse negative Laplace 0.674 / EP 0.721 / ESS 0.732) and measured on one real prefix in the validation (EP vs elliptical slice)"},
        "arms": {
            "V2_EP_mixture": "new fit", "rho1_EP": "the mixture's rho=1 EP component (exact reuse; same paths/preprocessing/target/priors/EP implementation); a separate fixed-rho=1 EP fit if the mixture fell back to Laplace; a Laplace-fallback rho=1 component is flagged as not an EP control",
            "Binary_V2_EP": "new fit, continuous likelihood removed only; one EP solve shared by the three components; masses must equal 1/3; nothing learned from depth",
            "V1_Laplace": "exact reuse of Stage M J predictions after verifying path prefix hash, scaler, config, use_response and implementation hash",
            "Binary_V1_Laplace": "exact reuse of Stage M Binary_matched predictions (same verification)", "ACTIVE_E1": "exact reuse of Stage M ACTIVE_E1 predictions (frozen implementation, prefix hash verified)",
            "G3": "exact reuse of Stage M G3 predictions (frozen implementation, prefix hash verified)",
            "J_trained": "new fit with EX2's trained_config exactly (sklearn ML-II on paid responses only: amplitude in [0.032, 10], four lengthscales in [0.05, 20], noise fixed 0.03, zero mean, 0 restarts); theta, delta, tau priors unchanged. A complete-system control, not a capacity-matched attribution control",
            "VX_stump": f"new fit, {VS.RULE_VERSION}: cut and orientation learned from the paid labels on standardized log VX (rule in src/jdl_vx_stump.py); class-weighted smoothed leaf scores are not population-calibrated probabilities"},
        "endpoints": {
            "primary": "NEW B40 BA at cutoff 0.5 (pooled per repeat, mean of repeats 1-2), V2_EP_mixture minus Binary_V2_EP, paired by split and budget",
            "mechanism": ["rho1_EP minus V1_Laplace (inference, same model)", "V2_EP_mixture minus rho1_EP (uncertain sharing vs forced sharing)"],
            "system": ["V2 minus J_trained", "V2 minus ACTIVE_E1", "V2 minus G3", "V2 minus VX_stump"],
            "descriptive": ["Binary_V2_EP minus Binary_V1_Laplace", "J_trained minus Binary_V2_EP", "J_trained minus ACTIVE_E1", "VX_stump minus G3"],
            "metrics": ["BA", "q20 (unchanged, fold-mean)", "specificity", "sensitivity", "short-K sensitivity (the existing 10 NEW short-K simulations, unique cases)", "Brier", "log loss", "AUC"],
            "budgets": "B16 and B40", "confusion_counts": "TP/FN/TN/FP and unique simulations reported with every rate",
            "secondary_rule": "for probabilistic arms (all except VX_stump) the previously declared paid-prevalence rule p >= pi_hat (share of positives among the checkpoint's paid labels; train-only; no threshold fitted from evaluation labels). A train-only cutoff is a heuristic, not necessarily an unbiased prevalence estimate or a Bayes-optimal rule",
            "fast_scan_corner": "errors inside VX > 0.85 m/s are reported as evaluation-only description (the cut is used by the evaluator only and never by a model)"},
        "uncertainty": {"bootstrap": "class-stratified simulation-cluster resampling (src.jdl_evaluate.boot_weights: 2000 draws, seed 20261013), multiplicities shared by both repeats, both budgets and all arms; conditional on the stored fits and these splits; repeated predictions of a simulation are not additional independent cases"},
        "screen": {"rule": "Astra's development screen: V2 is promising for further model work only if NEW B40 mean BA(V2) - BA(Binary_V2) >= +0.01, specificity(V2) >= specificity(Binary_V2) and log loss(V2) <= log loss(Binary_V2). +0.01 is a practical effect threshold, not a forecast or a significance test",
                   "always_reported": "intervals, case counts, q20 and short-K trade-offs, whether or not the screen passes; no success criterion is added after the results"},
        "expectations": {"identities": "Binary_V2_EP masses equal 1/3 exactly; rho1_EP equals the mixture's rho=1 component; no numeric performance forecast (Astra: V2 may withdraw harmful sharing and may lose efficiency where depth is informative)"},
        "accounting": {**CAPS, "planned_component_attempts": {"validation": int(val["counts"]["component_solves"]), "V2_EP_mixture": 60, "Binary_V2_EP": 20, "rho1_EP": "0 if reused (up to 20 if fallbacks force separate fits)",
                                                                "J_trained": "20 ML-II + 20 Laplace", "VX_stump": 20, "reused_arms": 0},
                       "rule": "failures and fallbacks are counted; if a genuine numerical need would exceed the caps, a prospective amendment is written before any further computation"},
        "validation": {"file": "v2_model_comparison/validation/V2_VALIDATION.json", "sha256": sha(VALIDATION), "status": val["status"]},
        "threads": "one BLAS thread; the four-thread total across all local jobs is respected (the run starts only when a temporal worker thread has freed)",
        "not_authorized": ["real-data Stage A", "C4", "simulator or cloud jobs", "label changes"],
        "code_sha256": {c: sha(SMM.ROOT / c) for c in CODE}}
    save_json(MANIFEST, man)
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "parent_commit")}, indent=1))


# ======================================================================================== run
def _committed(path):
    return bool(SMM._git("log", "--format=%H", "--", str(path.relative_to(SMM.ROOT)).replace("\\", "/")))


def _state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"top_level_requests": 0, "component_attempts": {"validation": 0, "comparison": 0}, "failures": [], "fallbacks": [], "reuse_verified": 0, "pending": None, "by_arm": {a: 0 for a in ARMS}}


def _mixture_record(model, xt, xp_paid, y_paid):
    """Per-checkpoint mechanism log of a V2 mixture."""
    qs = model.component_posteriors(xt)
    post = model.posterior(xt)
    comp = []
    for k, (cp, q) in enumerate(zip(model.components, qs)):
        comp.append({"rho": cp.rho, "weight": float(model.weights[k]), "log_evidence": float(model.diagnostics["log_evidence"][k]),
                     **{f"inf_{a}": v for a, v in model.diagnostics["components"][k].items()},
                     "theta_mean": q["theta_mean"], "theta_sd": float(np.sqrt(max(q["theta_var"], 0))),
                     "test_mean_f": float(np.mean(q["f_mean"])), "test_mean_h": float(np.mean(q["h_mean"])),
                     "test_mean_f_h_cov_diag": float(np.mean(np.diag(q["f_h_cov"]))), "test_mean_abs_delta": float(np.mean(np.abs(q["delta_mean"])))})
    pp = model.predict_proba(xp_paid)
    paid_post = model.posterior(xp_paid)
    neg = np.flatnonzero(np.asarray(y_paid) == 0)
    return {"components": comp, "fallback": bool(model.diagnostics["fallback"]), "failures": model.diagnostics["failures"],
            "solve_count": int(model.solve_count), "theta_mixture_mean": float(post["theta_mean"]), "theta_mixture_sd": float(np.sqrt(max(post["theta_var"], 0))),
            "test_mean_between_component_h_var": float(np.mean(post["h_between_component_var"])),
            "paid_negatives": [{"index_in_prefix": int(i), "p": float(pp[i]), "h_mean": float(paid_post["h_mean"][i]), "h_sd": float(np.sqrt(max(paid_post["h_cov"][i, i], 0)))} for i in neg]}


def run():
    if not MANIFEST.exists() or not _committed(MANIFEST):
        raise SystemExit("commit the V2 manifest before any comparison fit")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if sha(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} differs from the frozen manifest")
    import src.jdl_ex2 as EX2
    state = _state()
    if state["pending"]:
        raise SystemExit(f"unfinished request {state['pending']}: a recovery decision must be recorded first")
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    state["component_attempts"]["validation"] = int(val["counts"]["component_solves"])
    tasks = [t for t in SMM.build_tasks() if t["population"] == POP]
    paths = pd.read_csv(SMM.SM / "paths.csv")
    fl = pd.read_csv(SMM.SM / "fit_log.csv"); fl = fl[fl.population == POP]
    pr = pd.read_csv(SMM.SM / "predictions_all.csv.gz"); pr = pr[pr.population == POP]
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for t in tasks:
        g = paths[(paths.population == POP) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != man["data"]["path_sha256_by_task"][f"NEW_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit("path differs from the frozen manifest")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
        if not np.allclose(t["X"][:, 1], t["VX"]):
            raise SystemExit("input column order: X[:, 1] is not VX")
        std, sc = SMM.standardizer(t)
        xr, xt = std(t["X"][t["pool"]]), std(t["X"][t["test"]])
        test_ids = [str(t["ids"][i]) for i in t["test"]]
        for b in BUDGETS:
            paid = SMM.Oracle(t).reveal(t["path"][:b])
            prefix = hashlib.sha256("\n".join(paid.ids).encode()).hexdigest()
            Xp, yp, zp = std(paid.X), paid.y.astype(float), paid.z
            pi_hat = float(np.mean(paid.y))
            base = {"population": POP, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "prefix_sha256": prefix, "pi_hat": pi_hat,
                    "n_paid": len(yp), "n_neg_paid": int((yp == 0).sum()), "n_response": int(np.isfinite(zp).sum()),
                    "missing_response_ids": [paid.ids[i] for i in np.flatnonzero(~np.isfinite(zp))], "scaler": sc}
            mix = None
            for arm in ARMS:
                cf = CACHE / f"NEW__r{t['repeat']}_f{t['fold']}__B{b}__{arm}.json.gz"
                if cf.exists():
                    if arm == "V2_EP_mixture":
                        mix = None                                              # the rho1 arm reads the cached component instead
                    continue
                state["top_level_requests"] += 1; state["by_arm"][arm] += 1
                if state["top_level_requests"] > CAPS["top_level_requests"]:
                    raise SystemExit("top-level request cap reached")
                state["pending"] = cf.name; save_json(STATE, state)
                rec, preds = dict(base, arm=arm), []
                tf = time.time()
                try:
                    if arm == "V2_EP_mixture":
                        mix = V2.JointModelV2(xr, CFG).fit(Xp, yp, zp)
                        state["component_attempts"]["comparison"] += mix.solve_count
                        rec["mechanism"] = _mixture_record(mix, xt, Xp, yp)
                        if mix.diagnostics["fallback"]:
                            state["fallbacks"].append(cf.name)
                        p_all = mix.predict_proba(xt); post = mix.posterior(xt); iv = mix.probability_interval(xt)
                        qs = mix.component_posteriors(xt)
                        for j, sid in enumerate(test_ids):
                            row = {"sim_id": sid, "p": float(p_all[j]), "h_mean": float(post["h_mean"][j]), "h_var": float(post["h_cov"][j, j]),
                                   "h_between_var": float(post["h_between_component_var"][j]), "f_mean": float(post["f_mean"][j]), "f_var": float(post["f_cov"][j, j]),
                                   "pi_lo90": float(iv[0, j]), "pi_hi90": float(iv[1, j])}
                            for r_, q in zip(V2.RHOS, qs):
                                hv = max(q["h_cov"][j, j], 0.0)
                                row.update({f"p_rho_{r_}": float(ndtr(q["h_mean"][j] / np.sqrt(CFG.probit_scale ** 2 + hv))), f"h_mean_rho_{r_}": float(q["h_mean"][j]),
                                            f"h_var_rho_{r_}": float(hv), f"f_mean_rho_{r_}": float(q["f_mean"][j])})
                            preds.append(row)
                        rec["status"] = "ok"
                    elif arm == "rho1_EP":
                        mf = CACHE / f"NEW__r{t['repeat']}_f{t['fold']}__B{b}__V2_EP_mixture.json.gz"
                        mrec = json.loads(gzip.decompress(mf.read_bytes())) if mf.exists() else None
                        if mrec and mrec["fit"]["status"] == "ok" and not mrec["fit"]["mechanism"]["fallback"]:
                            comp = next(c_ for c_ in mrec["fit"]["mechanism"]["components"] if c_["rho"] == 1.0)
                            rec.update({"status": "ok", "reused_from": "V2_EP_mixture rho=1 EP component (exact; same fit)", "method": "ep", "ep_control": True,
                                        "component_attempts": 0, "theta_mean": comp["theta_mean"], "theta_sd": comp["theta_sd"],
                                        "inf": {k_[4:]: v_ for k_, v_ in comp.items() if k_.startswith("inf_")}})
                            for row in mrec["predictions"]:
                                preds.append({"sim_id": row["sim_id"], "p": row["p_rho_1.0"], "h_mean": row["h_mean_rho_1.0"], "h_var": row["h_var_rho_1.0"], "f_mean": row["f_mean_rho_1.0"]})
                        else:
                            sep = V2.JointModelV2(xr, CFG, rhos=(1.0,)).fit(Xp, yp, zp)
                            state["component_attempts"]["comparison"] += sep.solve_count
                            q = sep.component_posteriors(xt)[0]
                            p1 = sep.predict_proba(xt)
                            meth = sep.diagnostics["components"][0]["method"]
                            rec.update({"status": "ok", "reused_from": None, "method": meth, "component_attempts": sep.solve_count,
                                        "ep_control": meth == "ep", "theta_mean": q["theta_mean"], "theta_sd": float(np.sqrt(max(q["theta_var"], 0))),
                                        "inf": sep.diagnostics["components"][0], "fallback": bool(sep.diagnostics["fallback"])})
                            for j, sid in enumerate(test_ids):
                                preds.append({"sim_id": sid, "p": float(p1[j]), "h_mean": float(q["h_mean"][j]), "h_var": float(q["h_cov"][j, j]), "f_mean": float(q["f_mean"][j])})
                    elif arm == "Binary_V2_EP":
                        bm = V2.JointModelV2(xr, CFG).fit(Xp, yp, zp, use_response=False)
                        state["component_attempts"]["comparison"] += bm.solve_count
                        if np.max(np.abs(bm.weights - 1 / 3)) > 1e-12:
                            raise RuntimeError("Binary V2 masses moved from the prior")
                        rec["mechanism"] = _mixture_record(bm, xt, Xp, yp)
                        if bm.diagnostics["fallback"]:
                            state["fallbacks"].append(cf.name)
                        pb = bm.predict_proba(xt); post = bm.posterior(xt)
                        for j, sid in enumerate(test_ids):
                            preds.append({"sim_id": sid, "p": float(pb[j]), "h_mean": float(post["h_mean"][j]), "h_var": float(post["h_cov"][j, j])})
                        rec["status"] = "ok"
                    elif arm in REUSED:
                        src_arm = REUSED[arm]
                        r = fl[(fl.repeat == t["repeat"]) & (fl.fold == t["fold"]) & (fl.budget == b) & (fl.arm == src_arm)]
                        if len(r) != 1 or r.iloc[0].prefix_sha256 != prefix:
                            raise RuntimeError("reuse refused: paid prefix differs")
                        chk = {"prefix_sha256": True, "status": str(r.iloc[0].status)}
                        if src_arm in ("J", "Binary_matched"):
                            cfg_ok = json.loads(r.iloc[0].config) == json.loads(json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in CFG.__dict__.items()}))
                            sc_ok = json.loads(r.iloc[0].scaler) == json.loads(json.dumps(sc))
                            ur_ok = bool(r.iloc[0].use_response) == (src_arm == "J")
                            if not (cfg_ok and sc_ok and ur_ok):
                                raise RuntimeError("reuse refused: config, scaler or response use differs")
                            chk.update({"config": cfg_ok, "scaler": sc_ok, "use_response": ur_ok, "implementation_sha256": man["code_sha256"]["src/jdl_model.py"]})
                        g2 = pr[(pr.repeat == t["repeat"]) & (pr.fold == t["fold"]) & (pr.budget == b) & (pr.arm == src_arm)].set_index("sim_id")
                        for sid in test_ids:
                            row = g2.loc[sid]
                            preds.append({"sim_id": sid, "p": float(row.p) if row.prediction_status == "ok" else float("nan"), "prediction_status": row.prediction_status})
                        rec.update({"status": "ok", "reused_from": f"stage_m {src_arm}", "reuse_checks": chk, "component_attempts": 0})
                        state["reuse_verified"] += 1
                    elif arm == "J_trained":
                        cfg_t, info = EX2.trained_config(Xp, zp)
                        m = JM.JointDepthLabelGP(xr, cfg_t).fit(Xp, yp.astype(int), zp)
                        state["component_attempts"]["comparison"] += 2
                        q = m.marginals(xt)
                        rec.update({"status": "ok", **{k: (list(v) if isinstance(v, tuple) else v) for k, v in info.items()}, "solver_status": m.diagnostics["solver_status"],
                                    "gradient_inf": m.diagnostics["gradient_inf"], "theta_mean": q["theta_mean"], "component_attempts": 2})
                        for j, sid in enumerate(test_ids):
                            preds.append({"sim_id": sid, "p": float(q["p"][j]), "f_mean": float(q["f_mean"][j]), "h_mean": float(q["h_mean"][j]), "h_var": float(q["h_var"][j])})
                    elif arm == "VX_stump":
                        model = VS.fit_stump(Xp[:, 1], yp.astype(int))
                        state["component_attempts"]["comparison"] += 1
                        ps = VS.predict_stump(model, xt[:, 1])
                        rec.update({"status": "ok", "stump": model, "component_attempts": 1,
                                    "cut_in_VX_m_s": float(np.exp(model["cut"] * sc["sd"][1] + sc["mean"][1])) if model["type"] == "split" else None})
                        for j, sid in enumerate(test_ids):
                            preds.append({"sim_id": sid, "p": float(ps[j])})
                except V2.NUMERICAL_ERRORS + (ValueError,) as ex:
                    rec.update({"status": "failed", "error": f"{type(ex).__name__}: {ex}"[:300]})
                    state["failures"].append(cf.name)
                rec["seconds"] = time.time() - tf
                for p_ in preds:
                    p_.update({"population": POP, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "arm": arm})
                cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=_default).encode()))
                state["pending"] = None
                total = state["component_attempts"]["validation"] + state["component_attempts"]["comparison"]
                if total > CAPS["component_attempts_including_validation_and_fallback"]:
                    save_json(STATE, state)
                    raise SystemExit("component-attempt cap reached; a prospective amendment is required before more computation")
                save_json(STATE, state)
                print(f"r{t['repeat']} f{t['fold']} B{b} {arm:18s} {rec['status']}", flush=True)
    import scipy
    import sklearn
    state["environment"] = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__,
                            "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
    state["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); state["elapsed_s_this_session"] = time.time() - t0
    save_json(STATE, state)
    print(json.dumps({k: state[k] for k in ("top_level_requests", "component_attempts", "failures", "fallbacks", "reuse_verified")}, indent=1))


def load():
    fits, preds = [], []
    for f in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        fits.append(r["fit"]); preds += r["predictions"]
    return fits, pd.DataFrame(preds)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    if step == "manifest":
        write_manifest()
    elif step == "run":
        run()
    elif step == "evaluate":
        from src.jdl_v2_evaluate import main
        main()
