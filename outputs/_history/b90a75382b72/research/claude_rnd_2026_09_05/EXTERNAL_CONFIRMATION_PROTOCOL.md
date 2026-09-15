# EXTERNAL_CONFIRMATION_PROTOCOL — frozen external test on the unseen pool

This document, `external_confirmation_protocol.json`, and the code in `code/` are to be committed to Git **before** any new label is read by anyone on the method side. The commit SHA and the SHA-256 of the JSON are then recorded in the JSON's `freeze` block by a second commit. Until that sequence has actually happened the experiment must not be called preregistered.

## 1. Question

Does the frozen challenger (M3 predictive model; queries chosen by expected threshold-variance reduction under a frozen auxiliary threshold-surface posterior, "M3+TV") select expensive labels more efficiently than the incumbent (M3 + probability margin) for recovering the Conduction–Keyhole boundary on an independently generated pool whose labels were withheld during development? Secondary: do the saturation predictions of SATURATION_PREDICTIONS.md hold?

## 2. Architecture: three query paths plus Random, model held fixed

Development showed that no candidate model improves on M3 at any budget on identical labels (OLD_DATA_RND_REPORT §3). The challenger therefore keeps M3 as the predictive model and changes only the acquisition. The crossed design of the brief (A: M3+margin; B: challenger model+margin; C: challenger model+set acquisition; D: Random) collapses because the challenger model *is* M3, so B ≡ A. The mathematical justification: with the model fixed, C − A is exactly the acquisition effect (same evaluator, same posterior at every common prefix), which is the cleanest identification available; a model contrast has no content when the models coincide. To attribute the effect to the variance/leverage term rather than to "an auxiliary posterior's margin", a secondary path B′ is added.

| Path | Model used for prediction | Query policy | Role |
|---|---|---|---|
| A | M3 (Phase 1.13/1.14 code, unchanged) | M3 probability margin `1 − 2|p − ½|` | incumbent |
| B′ | M3 | probability margin of the frozen auxiliary T posterior | secondary control isolating the leverage term |
| C | M3 | expected threshold-variance reduction (MATHEMATICAL_DEVELOPMENT eq. 9) under the frozen T posterior, reference set = whole outer training pool | **challenger** |
| D | M3 | matched Random continuation (feature-independent order; 10 seeded continuations per outer run) | sampling baseline |

Frozen constants: T hyperparameters c = 7.0, s_u = 0.41, ℓ_s = (1.7, 30, 30) in standardised (log VX, log LS, ST), s_μ = 3.0, s_β = 1.0, μ₀ = mean revealed log h; selection argmax with smallest-row-index tie-break; batch size 1; no look-ahead beyond one step; M3 bounds and seeds as in Phase 1.14 (`length_upper = 100`, residual sd ∈ [0.05, 1], Stage-1 C = 10⁶, seed key `shared_physics|run_id|budget`).

Primary contrast: **C − A**. Secondary contrasts: C − B′, B′ − A, each of A/C − D.

## 3. Data flow and blinding

- Inputs manifest (IDs, P, VX, LS, ST, configuration fields) is the only file available to method code.
- Labels live in one CSV read only by `code/label_oracle.py:Oracle`; its SHA-256 is written to the access log at first open. `Oracle.reveal(run_id, ids)` returns labels for explicitly requested IDs in that run's training pool and appends every access to an append-only JSONL log; requests outside the training pool raise and are logged.
- Held-out labels are used only inside `Evaluator`, which computes B1 distances and q20/q30 flags from the full new-pool labels (evaluation-only, exactly as historically) and returns metric values, never labels or flags.
- Depth or other simulator outputs are not used by any path.
- Partitions: `StratifiedGroupKFold`-style label-free grouping is impossible without labels; the frozen rule is **feature-only** grouping by exact input tuple with a seeded random K-fold split (stratification by label is not available before unblinding and is not used). Seeds: `rnd2026|v1|new|outer_split|repeat|rr` (SHA-256 → uint32), repeats 1–20. Splits are generated and committed before labels.
- Initial design: for every outer run the same feature-only maximin 16-point design (repository `w85.initial_design` logic, seed `rnd2026|v1|new|run|<run_id>|initial_design`). If the 16 revealed labels contain one class, all arms continue with a predetermined feature-only maximin sequence until two classes appear (charged to the budget); during that startup all arms report the smoothed-prevalence prediction; if no second class appears by H the run is reported as a non-diverging run and kept.

## 4. Fold, horizon and budget rules (from NEW_POOL_FEASIBILITY_SPEC)

K = largest of {5,4,3,2} with N/K ≥ 85; n_train = N − N/K; H = min(80, ⌊0.8·n_train⌋); if H < 40 the acquisition study is infeasible and only the prediction study runs. Budgets 16 … H, one query per step, all arms evaluated at every budget.

## 5. Endpoints

**Primary endpoint (frozen): Fold-B1-q20 accuracy AULC over budgets 16–40, normalised trapezoid, contrast C − A.**

Justification (old data only; RESEARCH_DIAGNOSIS §2, `results/window_power.csv`): the M3 curve's headroom to its own full-label ceiling averages 0.031 over B16–40 and 0.0005 over B41–80; an early-decaying effect of amplitude 0.02 at B16 is detected with power 0.82 by the 16–40 endpoint versus 0.42 by 16–80 (0.998 by 16–32, which is however too short to include the B32–B40 headroom and is kept as a secondary window). Historical 16–80 AULC is reported as a secondary endpoint for continuity.

Secondary endpoints: q20 AULC 16–32 and 16–H; q30 AULC 16–40; q20 KH-recall AULC 16–40 (non-inferiority guard, margin −0.02); full-fold accuracy at B40 and B H; budget to sustained q20 accuracy ≥ 0.80/0.82/0.84 (three consecutive checkpoints; censored); path Jaccard at B40/H; selected-band rate; the eight saturation predictions.

## 6. Success / failure criteria (frozen)

- **Success**: C − A on the primary endpoint has a paired repeat-block 95% interval with lower bound > 0 **and** point estimate ≥ +0.010, **and** the q20 KH-recall guard is not violated (interval for C − A on KH-recall AULC 16–40 does not lie entirely below −0.02).
- **Practical futility**: upper bound of the C − A interval < +0.010.
- **Harm**: upper bound < 0.
- **Unresolved**: otherwise. No secondary endpoint can promote an unresolved primary result.
- Model-side statements are not made (no challenger model). Random contrasts are reported descriptively.

Old-data expectation for the primary contrast (development, not a promise): +0.0025 [−0.0032, +0.0080] against the committed M3-margin path; +0.0058 [+0.0002, +0.0117] against the same-posterior margin control (B′). Against this rule the challenger fails on the old pool; the external test is its only chance.

## 7. Statistical analysis (frozen)

Unit of inference: the repeat block (K folds retained together). Paired differences of run-level AULCs averaged within blocks; 10,000 block-bootstrap draws with seed `rnd2026|v1|new|bootstrap|<contrast>`; two-sided 95% percentile intervals. Holm adjustment over the secondary confirmatory family {C−A on 16–32, C−A on 16–H, C−B′ on 16–40}. Random arm: 10 continuations per run averaged before pairing. No run, fold or configuration is dropped; non-diverging runs contribute zero differences.

## 8. Order of operations and audit trail

1. Run `code/new_pool_audit.py` on the input-only manifest; commit `new_pool_audit.json` and the gate level.
2. Generate and commit partitions, initial designs, Random orders (`code/run_external.py --prepare`).
3. Commit this document, the JSON, and `code/`; record commit SHA and JSON SHA-256 in the JSON `freeze` block (second commit).
4. Receive the label file into the oracle location; record its SHA-256 (the oracle does this automatically at first open); confirm in writing that no method-side person has inspected it.
5. Run all arms (`code/run_external.py --run`); the oracle log is the audit trail; verify that every revealed ID was in the requesting run's training pool and that the number of reveals per run equals H.
6. Evaluate once, unblind all endpoints together, apply §6, report all contrasts and all eight predictions.
7. No method change, endpoint change or extra arm after step 4.

## 9. Compute

Per outer run and arm: ≈ (H−16) × (M3 fit 0.1 s + T fit 0.02 s + scoring 0.05 s) ≈ 15 s; 20 repeats × K folds × (3 arms + 10 Random continuations) ≈ 1–3 CPU-hours for N ≈ 400.
