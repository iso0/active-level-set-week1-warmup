"""V2 numerical acceptance, run before the V2 comparison manifest is frozen and before any V2 comparison fit.

1. Astra's `reference_checks.py`, unchanged, rerun in a scratch copy of his sources; every numeric leaf of the new
   NUMERICAL_REFERENCES.json is compared with the delivered file.
2. The same unchanged checks with this repository's port (`src.jdl_v2_model`) injected as `joint_model_v2`.
3. AMENDMENT_01 reproduced without unpickling anything: the original V1 one-negative case (V1 Laplace, fixed-rho=1 EP,
   V2), Astra's elliptical-slice reference chains, a synthetic unpaid-outcome corruption check on a regenerated world
   (with comparison to his stored record) and the induced whole-mixture fallback (his code and the port).
4. Real four-input NEW paid prefixes (Stage M paths, fold-pool scaler and reference pool): port-vs-standalone parity,
   rho=1 Laplace = immutable V1, rho=0 = binary limit, binary masses at their prior, unpaid-outcome corruption,
   prediction-batch invariance, missing responses, induced fallback, covariance identities, acquisition identities and
   an EP-vs-elliptical-slice comparison of every component on one checkpoint (diagnostic; EP is not exact).

Tolerances are fixed in TOL below before the first run.  Component solves are counted toward the V2 study's
300-attempt allowance; sampling chains are counted separately.

Step: python -m src.jdl_v2_validation      (one BLAS thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import contextlib
import hashlib
import importlib
import io
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[1]
ASTRA = ROOT / "outputs" / "astra_joint_model_v2"
OUT = ROOT / "outputs" / "joint_depth_label_development" / "v2_model_comparison"
VAL = OUT / "validation"
ASTRA_SOURCES = ("joint_model_v2.py", "v1_reference.py", "reference_checks.py", "run_controlled.py", "controlled_worlds.py",
                 "supplemental_diagnostics.py", "SELECTION_RECORD_V2.json")
ASTRA_MODULES = ("joint_model_v2", "v1_reference", "reference_checks", "run_controlled", "controlled_worlds", "supplemental_diagnostics")
TOL = {"astra_rerun_vs_delivered": 1e-9, "port_vs_astra_ep": 1e-7, "port_vs_astra_laplace": 1e-6, "port_vs_delivered_references": 1e-6,
       "rho1_laplace_vs_v1": 2e-7, "identity": 1e-9, "batch": 1e-12, "ess_mcse_multiple": 4.0}
COUNT = {"component_solves": 0, "sampling_chains": 0}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, obj


def compare_numeric(a, b, skip=("seconds", "source_sha256")):
    """Max absolute difference over matching numeric leaves; exact match required for non-numeric leaves."""
    la, lb = dict(leaves(a)), dict(leaves(b))
    worst, mism = 0.0, []
    for k, va in la.items():
        if any(s in k for s in skip):
            continue
        if k not in lb:
            mism.append(f"missing {k}"); continue
        vb = lb[k]
        if isinstance(va, bool) or isinstance(vb, bool) or not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            if va != vb:
                mism.append(f"{k}: {va!r} != {vb!r}")
        elif va is not None and vb is not None:
            worst = max(worst, abs(float(va) - float(vb)))
    return worst, mism


def scratch_copy(tag):
    d = VAL / f"astra_{tag}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in ASTRA_SOURCES:
        shutil.copy2(ASTRA / f, d / f)
    return d


@contextlib.contextmanager
def astra_import(d, port=False):
    """Import Astra's modules from directory d (optionally with the port standing in for joint_model_v2)."""
    for m in ASTRA_MODULES:
        sys.modules.pop(m, None)
    sys.path.insert(0, str(d))
    try:
        if port:
            import src.jdl_v2_model as P
            sys.modules["joint_model_v2"] = P
        mods = {m: importlib.import_module(m) for m in ASTRA_MODULES}
        yield mods
    finally:
        sys.path.remove(str(d))
        for m in ASTRA_MODULES:
            sys.modules.pop(m, None)


def run_reference_checks(d, port):
    with astra_import(d, port) as M:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            M["reference_checks"].run()
    rec = json.loads((d / "NUMERICAL_REFERENCES.json").read_text(encoding="utf-8"))
    COUNT["component_solves"] += int(rec.get("correctness_component_solves", 0))
    return rec


# ======================================================================================== step 3: supplemental
def supplemental(adir, res):
    import src.jdl_v2_model as P
    delivered = json.loads((ASTRA / "SUPPLEMENTAL_DIAGNOSTICS.json").read_text(encoding="utf-8"))
    with astra_import(adir) as M:
        V, V1, CW, SD = M["joint_model_v2"], M["v1_reference"], M["controlled_worlds"], M["supplemental_diagnostics"]
        X = np.linspace(-1, 1, 61)[:, None]; paid = np.arange(0, 61, 5)
        yp = np.ones(13, dtype=int); yp[-2] = 0
        z = .55 * X[:, 0] + .3; xp, zp = X[paid], z[paid]; c = V1.Config()
        v1 = V1.JointDepthLabelGP(X, c).fit(xp, yp, zp); COUNT["component_solves"] += 1
        a_ep = V.JointModelV2(X, c, rhos=(1.,)).fit(xp, yp, zp); a_mix = V.JointModelV2(X, c).fit(xp, yp, zp)
        p_ep = P.JointModelV2(X, c, rhos=(1.,)).fit(xp, yp, zp); p_mix = P.JointModelV2(X, c).fit(xp, yp, zp)
        COUNT["component_solves"] += a_ep.solve_count + a_mix.solve_count + p_ep.solve_count + p_mix.solve_count
        at = xp[-2:-1]
        probs = {"V1_Laplace": float(v1.predict_proba(at)[0]), "rho1_EP_astra": float(a_ep.predict_proba(at)[0]), "V2_astra": float(a_mix.predict_proba(at)[0]),
                 "rho1_EP_port": float(p_ep.predict_proba(at)[0]), "V2_port": float(p_mix.predict_proba(at)[0])}
        dp = delivered["V1_sparse_case"]["probabilities"]
        res["supplemental"]["sparse_case"] = {"probabilities": probs, "delivered": dp,
                                              "astra_rerun_max_diff": max(abs(probs["V1_Laplace"] - dp["V1_Laplace"]), abs(probs["rho1_EP_astra"] - dp["rho1_EP"]), abs(probs["V2_astra"] - dp["V2_EP_mixture"])),
                                              "port_max_diff": max(abs(probs["rho1_EP_port"] - dp["rho1_EP"]), abs(probs["V2_port"] - dp["V2_EP_mixture"])),
                                              "port_weights": p_mix.weights.tolist(), "astra_weights": a_mix.weights.tolist()}
        # elliptical-slice reference of the fixed V1 (rho=1) posterior, Astra's sampler and seeds
        m, K = a_ep.components[0].hp_prior
        chains = []
        for seed in (4301, 4302, 4303, 4304):
            s, _ = SD.ess_chain(m, K, yp, c.probit_scale, seed); chains.append(s); COUNT["sampling_chains"] += 1
        chains = np.array(chains)
        pp = ndtr(chains[:, :, -2] / c.probit_scale)
        mcse = float(pp.reshape(4, 32, 250).mean(2).ravel().std(ddof=1) / np.sqrt(128))
        ref = delivered["V1_sparse_case"]["reference"]
        res["supplemental"]["ess_reference"] = {"probability_mean": float(pp.mean()), "batch_MCSE": mcse, "probability_split_Rhat": float(SD.rhat(pp[:, :, None])[0]),
                                                "maximum_latent_split_Rhat": float(np.max(SD.rhat(chains))), "delivered_probability_mean": ref["probability_mean"],
                                                "delivered_batch_MCSE": ref["batch_MCSE"], "abs_diff_vs_delivered": abs(float(pp.mean()) - ref["probability_mean"]),
                                                "port_rho1_EP_error_vs_reference": abs(probs["rho1_EP_port"] - float(pp.mean())),
                                                "V1_Laplace_error_vs_reference": abs(probs["V1_Laplace"] - float(pp.mean())),
                                                "samples_sha256": hashlib.sha256(chains.tobytes()).hexdigest()}
        # synthetic unpaid-outcome corruption, regenerated world (no pickle); compare with Astra's stored record
        w = CW.make_world("informative_depth", 1301); prefix = w["path"][:16]; xr = w["X"][w["pool"]]
        cand = np.array([i for i in w["pool"] if i not in prefix])
        out = {}
        for name, Mod in (("astra", V), ("port", P)):
            orig = Mod.JointModelV2(xr, CW.config()).fit(w["X"][prefix], w["y"][prefix], w["z"][prefix])
            wc = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in w.items()}
            bad = np.ones(len(wc["y"]), bool); bad[prefix] = False
            wc["y"][bad] = 1 - wc["y"][bad]; wc["z"][bad] = 12345.
            rep = Mod.JointModelV2(xr, CW.config()).fit(wc["X"][prefix], wc["y"][prefix], wc["z"][prefix])
            COUNT["component_solves"] += orig.solve_count + rep.solve_count
            out[name] = {"max_probability_change": float(np.max(np.abs(orig.predict_proba(w["X"]) - rep.predict_proba(w["X"])))),
                         "max_acquisition_change": float(np.max(np.abs(orig.acquisition(w["X"][cand])["score"] - rep.acquisition(w["X"][cand])["score"]))),
                         "test_probabilities": orig.predict_proba(w["X"][w["test"]])}
        stored = json.loads((ASTRA / "records" / "static_informative_depth_1301_B16_V2_EP_mixture.json").read_text(encoding="utf-8"))
        sp = np.array(stored["predictions"], float)
        res["supplemental"]["synthetic_leakage"] = {"astra": {k: v for k, v in out["astra"].items() if k != "test_probabilities"},
                                                    "port": {k: v for k, v in out["port"].items() if k != "test_probabilities"},
                                                    "astra_rerun_vs_stored_record_max_diff": float(np.max(np.abs(out["astra"]["test_probabilities"] - sp))),
                                                    "port_vs_stored_record_max_diff": float(np.max(np.abs(out["port"]["test_probabilities"] - sp)))}
        # induced whole-mixture fallback: Astra's (all EP calls fail) and the port's (EP fails at rho = 0.5 only)
        saved = V.infer_probit

        def forced(m_, K_, y_, tau_, method):
            if method == "ep":
                raise RuntimeError("Injected EP failure for policy test")
            return saved(m_, K_, y_, tau_, method)
        V.infer_probit = forced
        try:
            a_fb = V.JointModelV2(X, c).fit(xp, yp, zp)
        finally:
            V.infer_probit = saved
        p_fb = P.JointModelV2(X, c).fit(xp, yp, zp, _inject_failure=0.5)
        COUNT["component_solves"] += a_fb.solve_count + p_fb.solve_count
        res["supplemental"]["induced_fallback"] = {
            "astra": {"fallback": a_fb.diagnostics["fallback"], "components": len(a_fb.components), "methods": [q["method"] for q in a_fb.diagnostics["components"]], "weights": a_fb.weights.tolist()},
            "port": {"fallback": p_fb.diagnostics["fallback"], "components": len(p_fb.components), "methods": [q["method"] for q in p_fb.diagnostics["components"]],
                     "weights": p_fb.weights.tolist(), "failures": p_fb.diagnostics["failures"], "solve_count": p_fb.solve_count},
            "laplace_mixture_port_vs_astra_max_prob_diff": float(np.max(np.abs(a_fb.predict_proba(X) - p_fb.predict_proba(X))))}


# ======================================================================================== step 4: real 4D prefixes
def real_data(adir, res):
    import src.jdl_model as JM
    import src.jdl_stage_m as SMM
    import src.jdl_v2_model as P
    import pandas as pd
    cfg = JM.STAGE_M_CONFIG
    tasks = SMM.build_tasks()
    paths = pd.read_csv(SMM.SM / "paths.csv")
    pick = {("NEW", 1, 1, 16), ("NEW", 1, 1, 40), ("NEW", 2, 3, 40)}

    def prep(t, b):
        g = paths[(paths.population == t["population"]) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
        std, _ = SMM.standardizer(t)
        paid = SMM.Oracle(t).reveal(t["path"][:b])
        cand = np.array([i for i in t["pool"] if i not in set(t["path"][:b].tolist())])[:6]
        return std, paid, std(t["X"][t["pool"]]), std(t["X"][t["test"]]), std(t["X"][cand])

    rows = []
    with astra_import(adir) as M:
        V, V1 = M["joint_model_v2"], M["v1_reference"]
        for t in tasks:
            for b in (16, 40):
                if (t["population"], t["repeat"], t["fold"], b) not in pick:
                    continue
                std, paid, xr, xt, xc = prep(t, b)
                Xp, yp, zp = std(paid.X), paid.y.astype(float), paid.z
                r = {"checkpoint": f"NEW_r{t['repeat']}_f{t['fold']}_B{b}", "n_paid": len(yp), "n_negative": int((yp == 0).sum()), "n_response": int(np.isfinite(zp).sum())}
                fits = {}
                for name, Mod in (("astra", V), ("port", P)):
                    fits[name] = {"mix": Mod.JointModelV2(xr, cfg).fit(Xp, yp, zp), "bin": Mod.JointModelV2(xr, cfg).fit(Xp, yp, zp, use_response=False),
                                  "rho1": Mod.JointModelV2(xr, cfg, rhos=(1.,)).fit(Xp, yp, zp)}
                    COUNT["component_solves"] += sum(f.solve_count for f in fits[name].values())
                a, p = fits["astra"], fits["port"]
                d = {}
                for arm in ("mix", "bin", "rho1"):
                    d[f"{arm}_prob"] = float(np.max(np.abs(a[arm].predict_proba(xt) - p[arm].predict_proba(xt))))
                    d[f"{arm}_weights"] = float(np.max(np.abs(a[arm].weights - p[arm].weights)))
                    d[f"{arm}_log_evidence"] = float(np.max(np.abs(np.array(a[arm].diagnostics["log_evidence"]) - np.array(p[arm].diagnostics["log_evidence"]))))
                qa, qp = a["mix"].component_posteriors(xt), p["mix"].component_posteriors(xt)
                d["mix_component_h_mean"] = float(max(np.max(np.abs(x["h_mean"] - y["h_mean"])) for x, y in zip(qa, qp)))
                d["mix_component_h_cov"] = float(max(np.max(np.abs(x["h_cov"] - y["h_cov"])) for x, y in zip(qa, qp)))
                d["mix_component_f_h_cov"] = float(max(np.max(np.abs(x["f_h_cov"] - y["f_h_cov"])) for x, y in zip(qa, qp)))
                d["mix_theta"] = float(max(abs(x["theta_mean"] - y["theta_mean"]) + abs(x["theta_var"] - y["theta_var"]) for x, y in zip(qa, qp)))
                d["mix_interval"] = float(np.max(np.abs(a["mix"].probability_interval(xt) - p["mix"].probability_interval(xt))))
                aq_a, aq_p = a["mix"].acquisition(xc, x_integrate=xr), p["mix"].acquisition(xc, x_integrate=xr)
                d["mix_acquisition"] = float(np.max(np.abs(aq_a["score"] - aq_p["score"])))
                r["parity_max_abs_diff"] = d
                r["ep_iterations_port"] = [q.get("iterations") for q in p["mix"].diagnostics["components"]]
                r["weights_port"] = p["mix"].weights.tolist(); r["log_evidence_port"] = p["mix"].diagnostics["log_evidence"]
                # rho = 1 Laplace endpoint vs immutable V1 (Astra's code) and the repository V1 port
                lap = P.JointModelV2(xr, cfg, rhos=(1.,), inference="laplace").fit(Xp, yp, zp)
                v1a = V1.JointDepthLabelGP(xr, cfg).fit(Xp, yp, zp)
                v1p = JM.JointDepthLabelGP(xr, cfg).fit(Xp, yp, zp)
                COUNT["component_solves"] += lap.solve_count + 2
                r["rho1_laplace_vs_V1"] = {"astra_v1": float(np.max(np.abs(lap.predict_proba(xt) - v1a.predict_proba(xt)))),
                                           "port_v1": float(np.max(np.abs(lap.predict_proba(xt) - v1p.predict_proba(xt)))),
                                           "rho1_EP_minus_rho1_Laplace_max_abs": float(np.max(np.abs(p["rho1"].predict_proba(xt) - lap.predict_proba(xt))))}
                # rho = 0 binary limit, binary masses, rho = 0 ignores depth values
                r0 = P.JointModelV2(xr, cfg, rhos=(0.,)).fit(Xp, yp, zp)
                r0z = P.JointModelV2(xr, cfg, rhos=(0.,)).fit(Xp, yp, np.where(np.isfinite(zp), zp + 2.0, np.nan))
                COUNT["component_solves"] += r0.solve_count + r0z.solve_count
                r["binary_limits"] = {"rho0_vs_binaryV2": float(np.max(np.abs(r0.predict_proba(xt) - p["bin"].predict_proba(xt)))),
                                      "rho0_depth_shift_change": float(np.max(np.abs(r0.predict_proba(xt) - r0z.predict_proba(xt)))),
                                      "binary_masses_minus_prior": float(np.max(np.abs(p["bin"].weights - 1 / 3))), "binary_solves": p["bin"].solve_count}
                # unpaid / test outcome corruption before paid extraction
                tc = dict(t); paid_rows = set(t["path"][:b].tolist())
                other = np.array([i for i in range(len(t["y"])) if i not in paid_rows])
                tc["y"] = t["y"].copy(); tc["y"][other] = 1 - tc["y"][other]
                tc["A"] = t["A"].copy(); tc["A"][other] = np.where(np.isfinite(tc["A"][other]), 7.0 * tc["A"][other], 250.0)
                paid_c = SMM.Oracle(tc).reveal(t["path"][:b])
                same_paid = bool(np.array_equal(paid_c.y, paid.y) and np.array_equal(np.nan_to_num(paid_c.z, nan=-9), np.nan_to_num(paid.z, nan=-9)))
                pc = P.JointModelV2(xr, cfg).fit(std(paid_c.X), paid_c.y.astype(float), paid_c.z); COUNT["component_solves"] += pc.solve_count
                r["corruption"] = {"paid_arrays_identical": same_paid, "probability_change": float(np.max(np.abs(pc.predict_proba(xt) - p["mix"].predict_proba(xt)))),
                                   "acquisition_change": float(np.max(np.abs(pc.acquisition(xc, x_integrate=xr)["score"] - aq_p["score"])))}
                # prediction-batch invariance and a fixed reference pool
                whole = p["mix"].predict_proba(xt)
                pieces = np.concatenate([p["mix"].predict_proba(xt[:5]), p["mix"].predict_proba(xt[5:17]), p["mix"].predict_proba(xt[17:])])
                r["batch"] = {"max_diff": float(np.max(np.abs(whole - pieces))), "reference_pool_unchanged": bool(np.array_equal(p["mix"].x_ref, xr))}
                # missing response: drop one available response, label and cost retained
                zm = zp.copy(); k = int(np.flatnonzero(np.isfinite(zm))[0]); zm[k] = np.nan
                pm = P.JointModelV2(xr, cfg).fit(Xp, yp, zm); COUNT["component_solves"] += pm.solve_count
                r["missing_response"] = {"n_paid": pm.diagnostics["n_paid"], "n_response": pm.diagnostics["n_response"], "expected_n_response": int(np.isfinite(zp).sum()) - 1}
                # induced fallback on the real prefix
                fb = P.JointModelV2(xr, cfg).fit(Xp, yp, zp, _inject_failure=0.5); COUNT["component_solves"] += fb.solve_count
                r["induced_fallback"] = {"fallback": fb.diagnostics["fallback"], "methods": [q["method"] for q in fb.diagnostics["components"]], "n_components": len(fb.components),
                                         "weights": fb.weights.tolist(), "max_prob_diff_vs_EP": float(np.max(np.abs(fb.predict_proba(xt) - whole)))}
                # covariance identities
                full = p["mix"].component_posteriors(xt, full=True)
                r["covariance"] = {"joint_identity": float(max(max(np.max(np.abs(q["H"] @ q["joint_mean"] - q["h_mean"])), np.max(np.abs(q["H"] @ q["joint_cov"] @ q["H"].T - q["h_cov"]))) for q in full))}
                post = p["mix"].posterior(xt)
                manual = sum(w * (q["h_cov"] + np.outer(q["h_mean"] - post["h_mean"], q["h_mean"] - post["h_mean"])) for w, q in zip(p["mix"].weights, full))
                r["covariance"]["mixture_within_plus_between"] = float(np.max(np.abs(post["h_cov"] - manual)))
                prior_K = [P.Component(xr, cfg, rho) for rho in P.RHOS]
                for cp in prior_K:
                    cp.xp = Xp
                Ks = [cp.prior_h(xt)[1] for cp in prior_K]
                r["covariance"]["unconditioned_h_prior_equal_across_rho"] = float(max(np.max(np.abs(Ks[0] - Kk)) for Kk in Ks[1:]))
                # acquisition identities (label-only route and the mixture-versus-average distinction)
                la = p["mix"].acquisition(xc[:3], x_integrate=xr, observe_response=False)
                qs = p["mix"].component_posteriors(np.vstack([xr, xc[:3]]))
                ni, tau2 = len(xr), cfg.probit_scale ** 2
                direct = []
                for j in range(3):
                    jj = ni + j; ids = np.r_[np.arange(ni), jj]
                    E1n, E0n, qq, pp = 0.0, 0.0, 0.0, 0.0
                    for wk, q in zip(p["mix"].weights, qs):
                        mm = q["h_mean"][ids]; C = q["h_cov"][np.ix_(ids, ids)]
                        den = np.sqrt(tau2 + np.diag(C)); aa = mm / den
                        Jk = JM.phi2(aa[:-1], aa[-1], C[:-1, -1] / (den[:-1] * den[-1]))
                        qk = ndtr(aa[-1]); pk = ndtr(aa[:-1])
                        E1n = E1n + wk * Jk; E0n = E0n + wk * (pk - Jk); qq += wk * qk; pp = pp + wk * pk
                    E1, E0 = E1n / qq, E0n / (1 - qq)                            # E[pi_i | Y_j = 1], E[pi_i | Y_j = 0] with mass updates
                    direct.append(float(np.mean(qq * (E1 - pp) ** 2 + (1 - qq) * (E0 - pp) ** 2)))
                comp_avg = []
                for k_, wk in enumerate(p["mix"].weights):
                    single = P.JointModelV2(xr, cfg, rhos=(P.RHOS[k_],)); single.components = [p["mix"].components[k_]]; single.weights = np.array([1.0])
                    single.use_response = True
                    comp_avg.append(wk * single.acquisition(xc[:3], x_integrate=xr)["score"])
                full_acq = p["mix"].acquisition(xc[:3], x_integrate=xr)
                fine = p["mix"].acquisition(xc[:3], x_integrate=xr, gh_order=31, cdf_order=64)
                total = float(p["mix"].integrated_probability_variance(xr).mean())
                r["acquisition"] = {"label_only_closed_form_vs_direct": float(np.max(np.abs(la["score"] - np.array(direct)))),
                                    "mixture_minus_weighted_component_average": (full_acq["score"] - np.sum(comp_avg, axis=0)).tolist(),
                                    "nonnegative_and_bounded": bool(np.min(full_acq["score"]) >= 0 and np.max(full_acq["score"]) <= total + 1e-7),
                                    "quadrature_15_48_vs_31_64": float(np.max(np.abs(fine["score"] - full_acq["score"])))}
                if (t["repeat"], t["fold"], b) == (1, 1, 16):
                    r["ep_vs_ess"] = ess_components(p["mix"], xt, cfg, M["supplemental_diagnostics"])
                rows.append(r)
    res["real_data"] = rows
    # missing responses present in a real paid prefix (NEW, Stage M paths)
    miss = []
    for t in tasks:
        g = paths[(paths.population == t["population"]) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}; pth = g.sim_id.map(pos).to_numpy(int)
        for b in (16, 40):
            pr = SMM.Oracle(t).reveal(pth[:b])
            if np.isnan(pr.z).any():
                miss.append({"task": f"{t['population']}_r{t['repeat']}_f{t['fold']}_B{b}", "n_paid": len(pr.y), "n_missing_response": int(np.isnan(pr.z).sum()),
                             "labels_of_missing": pr.y[np.isnan(pr.z)].tolist(), "ids_of_missing": [pr.ids[i] for i in np.flatnonzero(np.isnan(pr.z))]})
    res["paid_prefixes_with_missing_response"] = miss


def ess_components(model, xt, cfg, SD):
    """Elliptical-slice reference for each component's paid-latent posterior (Astra's sampler), test probabilities
    propagated through the exact Gaussian conditional; compared with the EP component probabilities."""
    out = []
    tau = cfg.probit_scale
    for k, cp in enumerate(model.components):
        m, K = cp.hp_prior
        mh, ch = cp.prior_h(xt)
        _, chp = cp.prior_h(xt, cp.xp)
        G = np.linalg.solve(K, chp.T).T
        vt = np.maximum(np.diag(ch) - np.einsum("ij,ij->i", G, chp), 0)
        chains = []
        for seed in (4401, 4402, 4403, 4404):
            s, _ = SD.ess_chain(m, K, cp.yp, tau, seed); chains.append(s); COUNT["sampling_chains"] += 1
        hs = np.concatenate(chains)                                            # (32000, n_paid)
        mt = mh[None, :] + (hs - m[None, :]) @ G.T
        pt = ndtr(mt / np.sqrt(tau ** 2 + vt[None, :]))                        # per-draw test probabilities
        batches = pt.reshape(4, 32, 250, -1).mean(2).reshape(128, -1)
        p_ess, mcse = pt.mean(0), batches.std(0, ddof=1) / np.sqrt(128)
        p_ep = ndtr(cp.posterior(xt)["h_mean"] / np.sqrt(tau ** 2 + np.maximum(np.diag(cp.posterior(xt)["h_cov"]), 0)))
        out.append({"rho": cp.rho, "max_abs_EP_minus_ESS": float(np.max(np.abs(p_ep - p_ess))), "mean_abs_EP_minus_ESS": float(np.mean(np.abs(p_ep - p_ess))),
                    "max_MCSE": float(mcse.max()), "decision_changes_at_0.5": int(np.sum((p_ep >= 0.5) != (p_ess >= 0.5))),
                    "paid_latent_split_Rhat_max": float(np.max(SD.rhat(np.array(chains))))})
    return out


def main():
    t0 = time.time()
    VAL.mkdir(parents=True, exist_ok=True)
    import src.jdl_v2_model as P
    res = {"version": P.VERSION, "tolerances_fixed_before_run": TOL, "supplemental": {},
           "port_sha256": sha(ROOT / "src" / "jdl_v2_model.py"), "astra_sources_sha256": {f: sha(ASTRA / f) for f in ASTRA_SOURCES}}
    delivered = json.loads((ASTRA / "NUMERICAL_REFERENCES.json").read_text(encoding="utf-8"))
    d1 = scratch_copy("reference_rerun")
    ref = run_reference_checks(d1, port=False)
    worst, mism = compare_numeric(delivered, ref)
    res["astra_reference_rerun"] = {"status": ref["status"], "checks_passed": sum(v["passed"] for v in ref["checks"].values()), "n_checks": len(ref["checks"]),
                                    "max_numeric_diff_vs_delivered": worst, "non_numeric_mismatches": mism}
    d2 = scratch_copy("port_run")
    rp = run_reference_checks(d2, port=True)
    worst2, mism2 = compare_numeric(delivered, rp)
    res["port_under_astra_checks"] = {"status": rp["status"], "checks_passed": sum(v["passed"] for v in rp["checks"].values()), "n_checks": len(rp["checks"]),
                                      "max_numeric_diff_vs_delivered": worst2, "non_numeric_mismatches": mism2,
                                      "scalar_threshold": rp["diagnostics"]["scalar_threshold"], "two_label_reference": {k: rp["diagnostics"]["two_label_reference"][k] for k in ("probability_max_error", "joint_covariance_max_error", "weight_max_error", "EP_selected", "reference_selected")},
                                      "single_label_paired_reference": {k: rp["diagnostics"]["single_label_paired_reference"][k] for k in ("probability_error", "score_max_error", "EP_selected", "reference_selected")}}
    supplemental(d1, res)
    real_data(d1, res)
    # ---------------------------------------------------------------------------------------------- verdict
    s, rd = res["supplemental"], res["real_data"]
    hard = {
        "astra_checks_reproduced": res["astra_reference_rerun"]["status"] == "PASS" and res["astra_reference_rerun"]["max_numeric_diff_vs_delivered"] <= TOL["astra_rerun_vs_delivered"] and not res["astra_reference_rerun"]["non_numeric_mismatches"],
        "port_passes_astra_checks": rp["status"] == "PASS",
        "port_matches_delivered_references": worst2 <= TOL["port_vs_delivered_references"] and not mism2,
        "sparse_case_reproduced": s["sparse_case"]["astra_rerun_max_diff"] <= TOL["astra_rerun_vs_delivered"] and s["sparse_case"]["port_max_diff"] <= TOL["port_vs_astra_ep"],
        "ess_reference_reproduced": s["ess_reference"]["abs_diff_vs_delivered"] <= TOL["ess_mcse_multiple"] * s["ess_reference"]["delivered_batch_MCSE"],
        "synthetic_leakage_zero": all(s["synthetic_leakage"][k][m] == 0.0 for k in ("astra", "port") for m in ("max_probability_change", "max_acquisition_change")),
        "synthetic_record_reproduced": s["synthetic_leakage"]["astra_rerun_vs_stored_record_max_diff"] <= TOL["astra_rerun_vs_delivered"] and s["synthetic_leakage"]["port_vs_stored_record_max_diff"] <= TOL["port_vs_astra_ep"],
        "induced_fallback_whole_mixture": all(s["induced_fallback"][k]["fallback"] and s["induced_fallback"][k]["components"] == 3 and set(s["induced_fallback"][k]["methods"]) == {"laplace"} for k in ("astra", "port")),
        "real_parity": all(max(v for k, v in r["parity_max_abs_diff"].items()) <= TOL["port_vs_astra_ep"] for r in rd),
        "real_rho1_laplace_is_V1": all(r["rho1_laplace_vs_V1"]["astra_v1"] <= TOL["rho1_laplace_vs_v1"] and r["rho1_laplace_vs_V1"]["port_v1"] <= TOL["rho1_laplace_vs_v1"] for r in rd),
        "real_binary_limits": all(r["binary_limits"]["rho0_vs_binaryV2"] <= TOL["identity"] and r["binary_limits"]["rho0_depth_shift_change"] <= TOL["identity"] and r["binary_limits"]["binary_masses_minus_prior"] <= 1e-12 for r in rd),
        "real_corruption_invariance": all(r["corruption"]["paid_arrays_identical"] and r["corruption"]["probability_change"] == 0.0 and r["corruption"]["acquisition_change"] == 0.0 for r in rd),
        "real_batch_invariance": all(r["batch"]["max_diff"] <= TOL["batch"] and r["batch"]["reference_pool_unchanged"] for r in rd),
        "real_missing_response_keeps_label": all(r["missing_response"]["n_paid"] == r["n_paid"] and r["missing_response"]["n_response"] == r["missing_response"]["expected_n_response"] for r in rd),
        "real_induced_fallback": all(r["induced_fallback"]["fallback"] and r["induced_fallback"]["n_components"] == 3 and set(r["induced_fallback"]["methods"]) == {"laplace"} for r in rd),
        "real_covariance_identities": all(max(r["covariance"].values()) <= TOL["identity"] for r in rd),
        "real_acquisition_identities": all(r["acquisition"]["label_only_closed_form_vs_direct"] <= TOL["identity"] and r["acquisition"]["nonnegative_and_bounded"] for r in rd),
    }
    res["hard_checks"] = hard
    res["status"] = "PASS" if all(hard.values()) else "FAIL"
    res["counts"] = dict(COUNT)
    res["seconds"] = time.time() - t0
    (VAL / "V2_VALIDATION.json").write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o)), encoding="utf-8")
    print(json.dumps({"status": res["status"], "hard_checks": hard, "counts": res["counts"], "seconds": res["seconds"]}, indent=1))
    return res


if __name__ == "__main__":
    main()
