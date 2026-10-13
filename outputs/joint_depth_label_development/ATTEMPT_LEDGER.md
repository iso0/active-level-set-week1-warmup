# Joint depth-label study — attempt ledger

Branch `joint-depth-label-dev` (worktree `.claude/worktrees/joint-depth-label-dev`) from `e2bcf97a`; main is unchanged. Every execution that fits, validates or evaluates is listed, including failed and repaired runs.

**Caps:**
- Stage M: 360 checkpoint fit requests.
- Threads: at most 4 CPU threads in total (J fits use 2 BLAS threads; E1/G3 use a thread-pool limit of 2).
- Memory: at most 8 GiB.
- Not authorized: Stage A, C4, simulator or cloud jobs.

| # | UTC | What ran | Comparative fits | Outputs | Notes |
|---|---|---|---:|---|---|
| S0 | 2026-10-13 | Worktree created at the pinned baseline `e2bcf97a`; the owner-supplied Astra package was copied verbatim to `outputs/astra_week20_method_development/` | 0 | package copy | All 10 SHA-256 values in `DELIVERY_VALIDATION.json` match. Astra's `__pycache__` was not copied. |
| V0 | 2026-10-13 | `run_checks.py` with the **unchanged reference**, in this environment (Python 3.14.4, NumPy 2.5.1, SciPy 1.18.0) | 0 (26 synthetic fits) | `validation/reference_checks_reproduced.json` | PASS, 26 checks. Values match the delivered record to about 1e-15. |
| V1 | 2026-10-13 | Port `src/jdl_model.py` (version `jdl-port-1.0`) | 0 | — | Independent of the reference in three places: a GPML-style Newton mode, Genz BVNU for the bivariate normal CDF, and erfcx plus an inverted Mills series for the probit terms. |
| V2a | 2026-10-13 | `python -m src.jdl_validation`, run 1 | 0 (synthetic) | — | **FAIL** in one check only, the importance-sampling reference for the tractable case. It drew from the prior and kept only 163 effective draws, so it could not test anything. All other checks passed. |
| V2b | 2026-10-13 | Validation design repaired: exact rejection sampling (Albert–Chib), Genz quasi-Monte Carlo orthant probabilities and elliptical slice sampling, run 2 | 0 | — | Crashed: the frozen `multivariate_normal` object does not accept `maxpts`. Fixed by calling the function form. |
| V2c | 2026-10-13 | Run 3 | 0 | — | **FAIL**: slice sampling vs orthant probabilities differed by 0.0169, against a fixed tolerance of 0.015 on a short chain (11k samples). |
| V2d | 2026-10-13 | Run 4: chain lengthened to 405k iterations; tolerance set to 4 batch-means standard errors + 1e-3 | 0 | `validation/validation_results.json`, `validation/astra_checks_{reference,port}.json` | **PASS, 21 checks.** Laplace vs exact on the 6-label four-input case: maximum probability error 0.040, mean 0.016 (reported as a limitation). No model, prior or scientific case changed in V2a–d; only the validation's reference methods changed. |
| C4-D | 2026-10-13 | C4 audit and draft, before any Stage M result | 0 | `C4_STABILITY_DRAFT.md`, `c4_audit.json` | Repeats 21–24 collide for OLD (used in Week 9 Phase 1.20). The draft proposes a new seed namespace. Not frozen, not executed. |
| P0 | 2026-10-13 | `python -m src.jdl_stage_m paths`: feature-only maximin paths to B80 for 30 task-folds; prefix composition; task inventory | 0 | `stage_m/paths.csv`, `path_verification_NEW_vs_week19.csv`, `prefix_composition.csv`, `task_inventory.csv` | NEW paths are identical to the saved Week 19 paths (10/10). There is no one-class prefix: NEW B16 prefixes have 1–3 negatives. |
| M0 | 2026-10-13 | `python -m src.jdl_stage_m manifest` | 0 | `STUDY_MANIFEST.json` | Population counts verified (NEW 136 = 124/12, OLD 405 = 73/332, POOLED 541 = 197/344). Committed and pushed before any comparative fit. |
