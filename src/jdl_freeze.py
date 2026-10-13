"""Freeze step for the joint depth-label study: feature-only paths, C4 audit and STUDY_MANIFEST.json (before any
comparative fit).  Nothing here fits a model.

Steps: python -m src.jdl_stage_m paths  |  python -m src.jdl_stage_m manifest
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

import src.jdl_model as JM
from src.jdl_stage_m import (ARMS, ASTRA, BASELINE_COMMIT, BUDGETS, CAPS, FAST_VX, OUT, PATH_LEN, PILOT, POPS, REPEATS, ROOT, SM, VARIANTS, Z_REF_UM,
                             _git, build_tasks, inputs_table, make_paths, sha256, shortk, verify_new_paths)

CODE = ["src/jdl_model.py", "src/jdl_validation.py", "src/jdl_stage_m.py", "src/jdl_evaluate.py", "src/jdl_freeze.py", "src/week19_dev_pilot.py",
        "src/week18_engine.py", "src/week18_tasks.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py",
        "src/week12_development_common.py", "src/external_validation/analysis.py"]


def write_paths():
    SM.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks()
    paths = make_paths(tasks)
    paths.to_csv(SM / "paths.csv", index=False, lineterminator="\n")
    ver = verify_new_paths(paths); ver.to_csv(SM / "path_verification_NEW_vs_week19.csv", index=False, lineterminator="\n")
    if not ver.identical_to_week19_saved_path.all():
        raise SystemExit("NEW paths do not reproduce the saved Week 19 paths")
    comp = []
    for t in tasks:
        for b in BUDGETS:
            L = t["path"][:b]
            comp.append({"population": t["population"], "repeat": t["repeat"], "fold": t["fold"], "budget": b, "n_paid": len(L),
                         "n_pos": int(t["y"][L].sum()), "n_neg": int((t["y"][L] == 0).sum()), "n_missing_A": int((~np.isfinite(t["A"][L])).sum()),
                         "one_class_prefix": bool(len(set(t["y"][L].tolist())) < 2)})
    pd.DataFrame(comp).to_csv(SM / "prefix_composition.csv", index=False, lineterminator="\n")
    inv = []
    for t in tasks:
        inv.append({"population": t["population"], "repeat": t["repeat"], "fold": t["fold"], "seed": json.dumps(t["seed"]), "n_pool": len(t["pool"]), "n_test": len(t["test"]),
                    "n_q20": int(t["q20"].sum()), "split_sha256": hashlib.sha256((",".join(map(str, t["pool"])) + "|" + ",".join(map(str, t["test"]))).encode()).hexdigest()[:16],
                    "train_test_disjoint": len(np.intersect1d(t["pool"], t["test"])) == 0, "path_in_pool": bool(np.isin(t["path"], t["pool"]).all())})
    pd.DataFrame(inv).to_csv(SM / "task_inventory.csv", index=False, lineterminator="\n")
    print(pd.DataFrame(comp).groupby(["population", "budget"])[["n_pos", "n_neg", "one_class_prefix"]].agg(["min", "max", "sum"]).to_string())
    print(ver.to_string())


def c4_audit():
    found = sorted({str(p.parent.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "outputs").rglob("*")
                    if p.is_file() and any(f"r{k}_" in p.name or f"r{k:03d}" in p.name for k in range(21, 25))})
    return {"question": "were repeats / seeds 21-24 used before?",
            "OLD": {"construction": "src.week8_5_frozen_sample_efficiency_confirmation.build_splits: StratifiedGroupKFold(5, shuffle) with seed_u32('outer_split|repeat|NN')",
                    "repeats_21_24": "USED: Week 9 Phase 1.20 confirmation used repeats 21-60 of this generator; Phase 1.21 used 61-120",
                    "evidence": found, "phase1_21_report": "outputs/week9_phase1_21_simplification_replication/FINAL_PHASE1_21_REPORT.md (section 3)"},
            "NEW": {"construction": "Week 11 owner-approved label-free group-fold certificate (outputs/week11_external_prelabel_freeze_final/EXTERNAL_BATCH_FREEZE.json), 20 seeds",
                    "repeats_21_24": "not generated"},
            "POOLED": {"construction": "src.week18_tasks.pooled_tasks: campaign x label stratified shuffle with default_rng([1818, rep]), rep in 1..20",
                       "repeats_21_24": "not generated"},
            "conclusion": "collision for OLD; a common C4 block of repeats 21-24 is not appropriate. Proposed: new seed namespace 'C4|<population>|repeat|k', k = 1..4 (C4_STABILITY_DRAFT.md)"}


def hypotheses():
    return {
        "SM-H1_primary": "NEW, B40, BA (pooled per repeat, mean of repeats 1-2): J > Binary_matched. Direction from the evidence that ACTIVE A carries canonical-label information on NEW (Week 20 C3: ACTIVE - WHOLE +0.044 [+0.023, +0.067]; ACTIVE ranks NEW labels better than G3: AUC +0.095). Magnitude unknown: the fixed positive depth coupling and fixed priors can also hurt (Astra adverse case).",
        "SM-H2_specificity": "NEW B40 specificity, J vs Binary_matched: no directional expectation (fast-scan negatives share depths with fast-scan positives; whether the centered discrepancy represents them under the fixed prior is unknown).",
        "SM-H3_log_loss": "NEW B40 log loss: J <= Binary_matched (direction from the better ACTIVE Brier scores on DEV and C3). Magnitude unknown.",
        "SM-H4_OLD": "OLD, B16 and B40 BA: J > Binary_matched. Direction: OLD labels are almost a threshold on A (Week 19 audit: A separates OLD labels with AUC about 0.9999), and the threshold prior is centred at 111 um, near the OLD reference threshold. Magnitude unknown.",
        "SM-H5_POOLED": "POOLED, J vs Binary_matched: no directional expectation (one global threshold plus a smooth discrepancy must absorb the OLD/NEW shift).",
        "SM-H6_ablations": "NEW B40 BA: J >= J_no_delta (the discrepancy is needed to represent fast-scan exceptions). J vs J_fixed_theta: no directional expectation. Magnitudes unknown.",
        "SM-H7_systems": "J vs G3 and J vs ACTIVE_E1: complete-system comparisons with different hyperparameter treatments; no directional expectation.",
        "SM-H8_theta": "Posterior theta SD at B40 is below the prior SD 0.35 in every population (labels inform theta). The theta-conditioning diagnostic changes probabilities by a magnitude that is unknown.",
        "SM-H9_numerics": "Every J-family fit is accepted by the gradient criterion (2e-6) and all leakage controls pass.",
        "thresholds": "+0.01 BA = practical improvement threshold; -0.01 BA = practical deterioration threshold. These are decision thresholds, not forecasts or equivalence margins.",
        "null_result_reading": "a failed screen means that an incremental benefit was not demonstrated for this model, prior and budget; it does not mean depth contains no label information.",
    }


def write_manifest():
    tasks = build_tasks()
    paths = pd.read_csv(SM / "paths.csv")
    inp = inputs_table()
    sk = sorted(shortk(inp))
    val = json.loads((OUT / "validation/validation_results.json").read_text(encoding="utf-8"))
    dv = json.loads((ASTRA / "DELIVERY_VALIDATION.json").read_text(encoding="utf-8"))
    pkg = {p.name: sha256(p) for p in sorted(ASTRA.iterdir()) if p.is_file()}
    pops = {}
    for pop in POPS:
        ts = [t for t in tasks if t["population"] == pop]
        y = ts[0]["y"]; A = ts[0]["A"]
        pops[pop] = {"task": POPS[pop], "n": int(len(y)), "positives": int(y.sum()), "negatives": int((y == 0).sum()),
                     "A_available": int(np.isfinite(A).sum()), "A_missing_ids": [str(s) for s in ts[0]["ids"][~np.isfinite(A)]],
                     "fast_scans_VX_gt_0.85": int((ts[0]["VX"] > FAST_VX).sum()), "early_end_records": int(ts[0]["early_end"].sum())}
    expected = {"NEW": (136, 124, 12), "OLD": (405, 73, 332), "POOLED": (541, 197, 344)}
    counts_ok = all((pops[p]["n"], pops[p]["positives"], pops[p]["negatives"]) == expected[p] for p in POPS)
    man = {
        "study": "joint depth-label GP development — Stage M (model value on identical feature-only paths)",
        "status": "FROZEN BEFORE ANY COMPARATIVE FIT. DEV development on previously inspected simulations; not confirmation. Stage A and C4 are not executed under this request.",
        "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "baseline_commit": BASELINE_COMMIT, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "parent_commit": _git("rev-parse", "HEAD"),
        "source_package": {"location": "outputs/astra_week20_method_development (verbatim copy of the owner-supplied package)", "sha256": pkg,
                           "matches_delivery_validation": all(pkg.get(k) == v for k, v in dv["sha256"].items()),
                           "role": "reference code = initial numerical specification; design text = hypotheses"},
        "data_contract": {"inputs": ["P", "VX", "LS (laser spot radius)", "ST"], "label": "canonical Y = any observed manually labelled Keyhole frame (pilot_inputs.has_keyhole)",
                          "response": "existing ACTIVE A (A_um, Week 19 audit; startup included; 90 %-of-derived-exit cutoff); z = log(A_um / 111) for valid positive A; missing A keeps its label and query cost",
                          "z_reference_um": Z_REF_UM, "populations": pops, "population_counts_verified": counts_ok,
                          "exclusions": "the 49 Bug-withheld NEW entries are outside NEW-136 and stay excluded; no label, exclusion or q20 change",
                          "identifiers": "full simulation IDs everywhere (H suffixes are not unique)"},
        "splits": {"NEW": "src.week18_tasks R3_NEW = week12 original_splits.json (identical to the Week 19 pilot)", "OLD": "src.week18_tasks R3_OLD (Week 8.5 split manifest)",
                   "POOLED": "src.week18_tasks R1_POOLED (campaign x label stratified, default_rng([1818, rep]))", "repeats": list(REPEATS), "folds": 5,
                   "split_sha256": {f"{t['population']}_r{t['repeat']}_f{t['fold']}": hashlib.sha256((",".join(map(str, t["pool"])) + "|" + ",".join(map(str, t["test"]))).encode()).hexdigest()[:16] for t in tasks}},
        "paths": {"routine": "src.week13_synthetic_al.maximin_order on the raw inputs of the fold's training pool (StandardScaler inside), rng = task seed + [2]",
                  "task_seeds": {"NEW": "[1820, repeat, fold]", "OLD": "[1822, repeat, fold]", "POOLED": "[1818, repeat, fold]"}, "length": PATH_LEN, "prefixes": list(BUDGETS),
                  "NEW_identical_to_week19_saved_paths": bool(pd.read_csv(SM / "path_verification_NEW_vs_week19.csv").identical_to_week19_saved_path.all()),
                  "sha256_by_task": {f"{p}_r{r}_f{f}": hashlib.sha256("\n".join(g.sort_values("query_index").sim_id).encode()).hexdigest() for (p, r, f), g in paths.groupby(["population", "repeat", "fold"])},
                  "paths_csv_sha256": sha256(SM / "paths.csv"), "prefix_composition_csv_sha256": sha256(SM / "prefix_composition.csv"),
                  "no_extension": "prefixes are never extended to obtain a class composition; one-class prefixes are kept"},
        "transformations": {"J_family": "log of the four raw inputs, standardized with the mean/sd of the fold's feature-only training pool (ddof 0); the discrepancy is centred on that fixed standardized pool",
                            "ACTIVE_E1": "frozen: StandardScaler on log(pool X); log A standardized on paid finite responses", "G3": "frozen Week 17/18 G3 transformations"},
        "priors_J": {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(JM.STAGE_M_CONFIG).items()},
        "variants": {k: {"config_changes": v[0], "use_response": v[1]} for k, v in VARIANTS.items()},
        "arms": list(ARMS),
        "baseline_declared_behaviour": {"source": "src.week19_dev_pilot.fit_one (frozen shared-path implementation of Week 19)",
                                        "ACTIVE_E1": "single-class usable pairs -> unavailable; logistic slope <= 0 -> failed_nonpositive_slope; non-positive response -> failed; otherwise predictions",
                                        "G3": "single-class paid labels -> unavailable; Laplace fixed-point error > 1e-6 or fallback -> failed_convergence; otherwise predictions",
                                        "no_reseeding_no_extra_startup_no_silent_exclusion": True},
        "task_counts": {"checkpoints": len(tasks) * len(BUDGETS), "fit_requests": len(tasks) * len(BUDGETS) * len(ARMS), "cap": CAPS},
        "numerical_limits": {"J_newton_max_iterations": JM.NEWTON_MAX_ITER, "J_newton_gradient_tolerance": JM.NEWTON_GRAD_TOL, "J_gradient_acceptance": JM.GRADIENT_ACCEPT,
                             "J_line_search_min_step": 1e-10, "E1": "sklearn GPR L-BFGS-B, 0 restarts; logistic C=1e6, max_iter 5000", "G3": "frozen safeguarded Laplace (FP_TOL 1e-9), one L-BFGS-B start",
                             "threads": "J fits: 2 BLAS threads; E1/G3: threadpool limit 2; at most 4 threads in total"},
        "evaluation": {"pooling": "per repeat over the five test folds (every simulation once); headline = mean of the two repeats",
                       "metrics": ["BA at p >= 0.5", "q20 accuracy: unchanged membership, mean over folds with q20 points", "specificity", "sensitivity",
                                   "short-K sensitivity", "Brier", "log loss (p clipped to [1e-12, 1-1e-12])", "AUC"],
                       "short_K": {"definition": "NEW positives with 0 < K/(F+C+K) < 0.10 (frac_K_FCK; not K/(K+C))", "unique_simulations": len(sk),
                                   "membership_sha256": hashlib.sha256("\n".join(sk).encode()).hexdigest(), "OLD": "not defined (NaN)", "POOLED": "the same NEW simulations"},
                       "contrasts": "paired on identical tasks, restricted to the common available cohort; per-repeat values reported",
                       "uncertainty": "simulation-cluster bootstrap (2000 draws, seed 20261013): class-stratified multiplicities per simulation shared across repeats, budgets and arms; conditional on the stored fits",
                       "populations_reported_separately": True, "no_pooled_significance_claim": True},
        "primary_contrast": "NEW, B40, BA: J - Binary_matched",
        "hypotheses": hypotheses(),
        "decision_rule": "Recommend Stage A iff numerical/leakage checks pass AND, on NEW at B40 (mean over repeats 1-2), J - Binary_matched BA >= +0.01, specificity(J) >= specificity(Binary_matched) and log loss(J) <= log loss(Binary_matched). q20, short-K and OLD/POOLED regressions are reported explicitly. A pragmatic development screen, not confirmation.",
        "mechanism_diagnostics_predeclared": ["FP/FN by full ID per arm; strata: NEW negatives, fast scans (VX > 0.85), short-K, incomplete support (A missing or recording ends early)",
                                              "theta posterior per fit; delta, response, latent margin, uncertainty and cross-covariances at test points",
                                              "Astra theta-conditioning diagnostic vs J_fixed_theta refit",
                                              "oracle-response diagnostic (held-out A, NOT deployable) for J and ACTIVE_E1 on the same simulations",
                                              "ranking (AUC) vs probability scores (log loss, Brier) vs decisions (BA); reliability bins with counts",
                                              "Laplace approximation error by elliptical slice sampling for J at NEW repeat 1, folds 1-5, B40"],
        "validation": {"status": val["status"], "n_checks": len(val["checks"]), "results_sha256": sha256(OUT / "validation/validation_results.json")},
        "C4": {"draft": "C4_STABILITY_DRAFT.md (written before Stage M results)", "audit": c4_audit()},
        "not_authorized_here": ["Stage A execution", "C4 execution or scoring", "simulator or cloud jobs", "label/exclusion/q20 changes", "q30"],
        "code_sha256": {c: sha256(ROOT / c) for c in CODE},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "STUDY_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    (OUT / "c4_audit.json").write_text(json.dumps(man["C4"]["audit"], indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("task_counts", "primary_contrast")}, indent=1), "counts ok:", counts_ok, "package ok:", man["source_package"]["matches_delivery_validation"])
    return man
