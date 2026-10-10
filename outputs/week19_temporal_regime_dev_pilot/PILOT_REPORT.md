# Week 19 DEV pilot: active-window E1 target on shared paid paths (R3_NEW)

**Status.**
- **POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE.** The pilot uses DEV repeats 1–2 only; C3 (repeats 17–20) is unused.
- P3 and the morphology fallback were not started.
- No label, eligibility decision or historical output was changed.

**Specification.** The pilot implements P0–P2 of Astra's `OPUS_IMPLEMENTATION_REQUEST.md` (`../astra_week19_rnd/`, stored verbatim), with the owner's changes of 2026-10-10:
- **Primary decision.** Balanced accuracy (BA) at B40, ACTIVE_E1 minus WHOLE_E1. The gate also requires no mean specificity decline and no short-K sensitivity loss greater than 0.05 against either comparator.
- **Co-endpoint.** q20 is reported alongside, not used as the gate.
- **Prediction.** A falsifiable prediction was frozen before any fit.
- **Additions.** A descriptive table that fits no model, a summary for Ioan, and a `timestep × DT` audit.

Astra's statements are treated as hypotheses; every number Astra reported was re-derived (P0).

**Evidence labels.**
- **OBS**: table values.
- **PRED**: pilot predictions.
- **POST-HOC**: targets or analyses motivated by the observed NEW labels.
- **HYP**: interpretation.

**Run.**
- `python -m src.week19_dev_pilot p0|p1|p2`
- `python -m src.week19_pilot_reports all`

## Verdict

**ADVANCE, as an exploratory DEV gate under the owner-modified rule.** All eight gate conditions hold at B40 (`decision.json`). Two hold by a narrow margin:
- the paired 95 % lower bound of ΔBA is **+0.013**;
- the short-K sensitivity loss against WHOLE_E1 is **exactly the allowed 0.05**: 12/20 vs 13/20 predictions. The comparison is evaluated in exact arithmetic.

**q20 co-endpoint.** q20 did not deteriorate (+0.067), but its interval includes 0, so **no boundary improvement is claimed**.

**What ADVANCE means here.** The active-window target A has earned a place in the next step; this is **not** a confirmed improvement. Confirmation would need a newly frozen protocol on data not used here, and the owner's decision.

## 1. Answer in brief

1. **Provenance holds (P0, OBS).** 10 checks pass and 2 are information only (`tables/P0_CHECKS.csv`).
   - Populations: OLD 405/73 positive, NEW 136/124.
   - Labels agree across four sources, joined by full name.
   - Exactly one A is unavailable (`H-e7dbd8e5ce`), and two K/(K+C) ratios are undefined.
   - Astra's paired-cohort AUC, BA and confusion values, the A oracle at 142.2322 µm (114/10/11/0, short-K 1/10), the threshold-pull summary and the registry counts all reproduce within 1e-10.
   - The fold-table maximum u is **309.619080770828 µm**. The audit report's "309.3 µm" is the final-budget maximum.
   - WHOLE target: equals the Week 18 E1 response exactly.
   - Target-contract arithmetic: exact to 4e-16.
   - **Historical paid-query logs do not exist**, so historical acquisition timing is unavailable and the causal threshold-pull claim stays unresolved.
2. **All 90 fits succeeded (P1).** There were no unavailable checkpoints and no failures. The run took 4.5 s, with peak memory 0.25 GiB and 2 threads. Every arm saw the same label-blind maximin path, with the first 80 IDs saved before fitting.
3. **Primary endpoint (PRED, POST-HOC).** BA at B40:

   | Arm | BA |
   |---|---:|
   | ACTIVE_E1 | **0.730** |
   | WHOLE_E1 | 0.632 |
   | G3 | 0.618 |

   - **ΔBA = +0.098 [+0.013, +0.185].**
   - Per repeat it is +0.113 and +0.083; each repeat's own interval includes 0.
4. **Safeguards at B40.**

   | Measure | ACTIVE_E1 | WHOLE_E1 | G3 |
   |---|---:|---:|---:|
   | Specificity (correct of 24 negative predictions) | **12/24** | 7/24 | 7/24 |
   | Short-K sensitivity | 12/20 | 13/20 | 8/20 |
   | Sensitivity, all positives | 0.960 | 0.972 | 0.944 |
5. **Budget dependence.** ΔBA is +0.052 [−0.006, +0.115] at B16 and +0.034 [−0.112, +0.165] at B80. The advantage is concentrated at the primary checkpoint.
6. **Prediction versus outcome** (§2).
   - Threshold pull removed: **untestable**, because WHOLE_E1 shows no pull on the shared paths.
   - Moves toward G3: **falsified as stated**, because ACTIVE_E1 overshoots G3.
   - Fast-scan ambiguity remains: **supported**.

   The overall prediction is **not supported as stated**.
7. **Where the gain comes from (PRED/HYP, §4–5).** The gain does not come from the late negative.
   - The late negative's own prediction is unchanged (1 of 2 called Keyhole in both arms).
   - ACTIVE_E1's five fewer false positives fall on four fast-scan negatives whose own A *equals* their whole-record maximum. The improvement therefore comes from a different fitted response surface.
   - A is easier to predict: log RMSE 0.082 vs 0.178.
   - Classifying the *observed* response with the same learned threshold gives the same BA as the GP prediction (0.728 vs 0.730; 0.628 vs 0.632). Regression error is not the bottleneck.
   - The learned threshold costs BA against the fixed OLD u_ref in both arms (u_ref gives 0.780 and 0.717). This is a diagnostic only.
8. **Descriptive table (OBS, no fits; `tables/descriptive_whole_vs_A_by_label.csv`).**
   - **NEW overall:** A ranks the labels far better than the whole-record maximum (AUC 0.978 vs 0.889, paired cohort).
   - **NEW fast scans (VX > 0.85, exploratory):** both are weak (0.773 vs 0.705), and relabelling by K/(K+C) ≥ 5 % or ≥ 10 % does not help (0.62–0.76).
   - **OLD fast scans:** separate almost perfectly (0.999).
9. **`timestep × DT` (`TIMESTEP_DT_USAGE_AUDIT.md`).** No earlier week used it as physical time.
   - **Wording only:** Week 18's "time-step rule".
   - **Caveat:** Week 5 regressed raw iteration counts and said so.
   - Nothing was rewritten.

## 2. Prediction versus outcome (frozen in `pilot_manifest.json` before any fit)

**Prediction:** *"ACTIVE_E1 removes the late-negative threshold pull and moves toward G3 on NEW; the fast-scan ambiguity remains."*

| Component | Frozen test | Outcome | Result |
|---|---|---|---|
| **H1** pull removed | WHOLE u ≥ 200 µm in ≥ 1 fit with the late negative paid, and ACTIVE u < 200 µm in all such fits | The late negative was paid in 23/30 checkpoints per arm. Max u was 130.3 µm (WHOLE) and 125.1 µm (ACTIVE). No fit reached 200 µm in either arm. | **UNTESTABLE** (no pull on shared paths) |
| **H2** toward G3 | BA(A) − BA(W) > 0 **and** \|A − G3\| < \|W − G3\| at B40 | +0.098 > 0, but \|0.730 − 0.618\| = 0.112 > \|0.632 − 0.618\| = 0.014 | **FALSIFIED as stated** (A exceeds G3 rather than approaching it) |
| **H3** fast-scan ambiguity remains | ACTIVE errs on the 4 unresolved fast-scan negatives in ≥ 50 % of 8 predictions, and short-K gain ≤ 0.05 | Wrong in 6/8 (0.75); short-K gain −0.05 | **SUPPORTED** |

**H1 was known before the real run.** The E1 learned threshold depends only on the paid (depth, label) pairs, not on the GP. The stub dry run (no GP fits, `ATTEMPT_LEDGER.md`, attempt 0) therefore revealed these thresholds before P1. The manifest had already been frozen, and nothing in it was changed.

**What H1 implies (HYP).** The historical pull (u up to 309.6 µm in 13 of 32 folds) does not arise from the late negative's presence alone. On space-filling paths, several shallow negatives are paid alongside it and the logistic root stays near 100–130 µm. The pull appears to need the composition produced by adaptive acquisition. Without acquisition logs this remains unresolved.

## 3. Results at B40

Mean over repeats 1–2. Brackets are the paired conditional bootstrap 95 % interval (2000 draws, seed 191026, simulations resampled within label strata).

| Metric | WHOLE_E1 | ACTIVE_E1 | G3 |
|---|---|---|---|
| **BA (primary)** | 0.632 [0.530, 0.742] | **0.730 [0.597, 0.857]** | 0.618 [0.547, 0.688] |
| specificity (12 negatives) | 0.292 [0.083, 0.500] | 0.500 [0.250, 0.750] | 0.292 [0.167, 0.417] |
| sensitivity (124 positives) | 0.972 [0.940, 0.996] | 0.960 [0.927, 0.988] | 0.944 [0.903, 0.984] |
| short-K sensitivity (10) | 0.650 [0.357, 0.929] | 0.600 [0.357, 0.833] | 0.400 [0.100, 0.727] |
| q20 accuracy (co-endpoint) | 0.683 [0.538, 0.809] | 0.750 [0.614, 0.874] | 0.633 [0.478, 0.766] |
| AUC | 0.821 [0.725, 0.910] | 0.893 [0.789, 0.972] | 0.819 [0.735, 0.894] |
| Brier | 0.077 | 0.070 | 0.091 |
| response RMSE (log) | 0.178 | 0.082 | — |

| Contrast at B40 | ΔBA | Δq20 | Δspecificity | Δshort-K |
|---|---|---|---|---|
| **ACTIVE − WHOLE** | **+0.098 [+0.013, +0.185]** | +0.067 [−0.009, +0.148] | +0.208 [+0.042, +0.375] | −0.050 [−0.273, +0.182] |
| ACTIVE − G3 | +0.112 [−0.009, +0.212] | +0.117 [+0.018, +0.237] | +0.208 [−0.042, +0.417] | +0.200 [−0.056, +0.500] |
| WHOLE − G3 | +0.014 [−0.092, +0.116] | +0.050 [−0.046, +0.153] | 0.000 [−0.208, +0.208] | +0.250 [0.000, +0.539] |

**Per-repeat BA.**

| Arm | Repeat 1 | Repeat 2 |
|---|---:|---:|
| ACTIVE_E1 | 0.767 | 0.692 |
| WHOLE_E1 | 0.655 | 0.609 |
| G3 | 0.597 | 0.638 |

The B16 and B80 rows are in `tables/metrics.csv` (`figures/pilot_fig2_metrics_by_budget.png`).

**Bootstrap draws.** No draw was undefined. In 49 of 2000 draws, a fold's q20 points were not resampled; that fold was skipped, as under the Week 18 rule (`tables/bootstrap_undefined_draws.csv`).

## 4. Calibration versus response prediction (diagnostics, not candidates)

These are the two diagnostics the spec requires, at B40 (BA / specificity):

| Arm | Learned threshold (deployable) | Fixed u_ref on the same latent | Observed response vs learned u (**ORACLE RESPONSE — NOT DEPLOYABLE**) |
|---|---|---|---|
| WHOLE_E1 | 0.632 / 0.292 | 0.717 / 0.458 | 0.628 / 0.292 |
| ACTIVE_E1 | 0.730 / 0.500 | 0.780 / 0.583 | 0.728 / 0.500 (H-e7dbd8e5ce unscored) |

**HYP.**
- **The target matters.** Predicting the response well gains nothing beyond the GP: the oracle column matches the learned column.
- **The threshold matters.** The threshold learned from 3–7 paid negatives at B40 costs about 0.05–0.09 BA relative to the OLD-derived u_ref, in both arms. u_ref is reported only as a diagnostic, so this is not a recommendation.

## 5. Which simulations moved (B40, 2 repeats)

**Negatives** (`tables/negatives_12_predictions.csv`). The table counts Keyhole calls out of 2:

| Negative | VX | Whole / A (µm) | WHOLE | ACTIVE | G3 |
|---|---:|---|---:|---:|---:|
| H-e7dbd8e5ce (A unavailable) | 0.332 | 145.0 / — | 2 | 2 | 2 |
| H-2e066980ca (unresolved) | 0.899 | 115.1 / 115.1 | 2 | 2 | 2 |
| H-1d4ea0f649 (unresolved) | 0.904 | 111.6 / 111.6 | 2 | 2 | 1 |
| H-29cf03a279 (Forming peak) | 0.912 | 131.2 / 131.2 | 2 | 2 | 2 |
| H-be08daa72c | 0.919 | 107.3 / 107.3 | 1 | **0** | 1 |
| H-f4fc937e86 (late negative) | 0.954 | 312.0 / 110.8 | 1 | 1 | 2 |
| H-b302fc6cbd (unresolved) | 0.960 | 115.6 / 115.6 | 0 | 0 | 1 |
| H-6f28bdc6c9 | 0.961 | 88.5 / 79.4 | 0 | 0 | 1 |
| H-ce04be44b1 | 0.965 | 87.3 / 87.3 | 2 | **1** | 2 |
| H-b2eec677b1 (unresolved) | 0.970 | 118.8 / 118.8 | 2 | 2 | 1 |
| H-210d3fce7d | 0.978 | 98.7 / 98.7 | 1 | **0** | 1 |
| H-3172b413b1 | 0.980 | 90.8 / 90.8 | 2 | **0** | 1 |

**Positives.** ACTIVE_E1 loses 5 positive predictions that WHOLE_E1 gets right and gains 2.
- **Losses:** H-349225d53c (both repeats; its Keyhole frames all lie after the 90 % cutoff), and the short-K positives H-5a876064ac, H-6ca7f366ce and H-8827d7eb9a.
- **Gains:** the short-K positives H-6dae2a1270 and H-85317ef64f.

Details: `tables/named_case_predictions.csv`, `tables/evaluation.csv`.

## 6. Thresholds on the shared paths

All 60 E1 fits used the existing rule: 55 logistic, 5 midpoint.
- Near-zero slopes: none.
- Roots outside the paid depth range: 6, all at B16/B40 with 1–3 negative pairs.
- The engine's 111 µm single-class fallback was never reached.

Learned u at B40 ranges 73.0–127.0 µm (WHOLE) and 97.2–125.1 µm (ACTIVE); see `figures/pilot_fig1_learned_thresholds.png`.

## 7. Checks, failures and resources

**P1/P2 checks.** All 13 pass (`tables/P1_CHECKS.csv`):
- train/test are disjoint and the five folds partition the 136;
- the 80-ID paths are unique, lie inside the pool and are identical across arms;
- the leakage guard holds: the learner receives labels and responses of the paid prefix only;
- q20 flags and test rows are identical to the Week 18 cache;
- each simulation has exactly one prediction per series;
- missing targets are accounted for;
- probabilities and variances are finite;
- the E1 threshold replicates;
- resources stay within the caps, and the manifest predates and is unchanged by the fits;
- labels, pinned inputs, tracked historical outputs and the C3 inventory are unchanged;
- the bootstrap design is as specified.

**Fit numerics.**
- **G3:** all 30 L-BFGS-B runs converged; maximum Laplace fixed-point error 6.9e-10 (rule: ≤ 1e-6); no initial-kernel fallback.
- **E1:** no `ConvergenceWarning`. 50 of 60 fits have a hyperparameter at a bound:
  - ST length scale at its upper bound 100 in 30 fits;
  - P length scale at 100 in 14;
  - noise at its lower bound 1e-6 in 23.

  A hyperparameter at a bound is a property of the optimum, not a convergence failure, so these are recorded as diagnostics (Week 18 practice). The pre-specified L-BFGS-B sensitivity check finds no non-converged B40 fit, so it would leave the verdict unchanged.

**C3 inventory.** 40 files: Week 12 checkpoints `dev__r017…r020`, written before the Week 18 block reservation. No Week 18 C3 cache exists. Unchanged.

## 8. What this pilot does not show

- **Not an acquisition comparison.** All arms saw the same label-blind path. The historical E1/G3 used adaptive acquisition, and the threshold pull appears only there.
- **The target choice is post-hoc and label-informed.** A was proposed after the Week 19 audit had looked at all NEW labels, including the runs held out here. The 0.9 window constant predates Week 19, but that does not make this target selection prospective. The DEV estimate is therefore optimistic.
- **Small denominators.**
  - Specificity rests on 12 negatives, so it moves in steps of 1/24.
  - Short-K moves in steps of 1/20.
  - The short-K gate passed at its limit.
- **Narrow uncertainty.** The bootstrap is conditional on these fitted models and two historical split repeats. It carries no refitting, independent-fold or external uncertainty, and each repeat's own interval includes 0.
- **Budget-specific.** The advantage is clear only at B40, the pre-chosen primary checkpoint.
- **Known failures persist.** The A-unavailable negative and the four unresolved fast-scan negatives remain misclassified, and H-349225d53c is lost.

## 9. Files

| File | Content |
|---|---|
| `pilot_manifest.json` | Frozen before any fit (sha256 `a94ad88b…41b0`; commit `c88f92c9`): prediction H1–H3, decision rule, failure rules, caps, seeds, folds, code hashes. |
| `decision.json` | Verdict, gate conditions, counts, margins and hypothesis outcomes. |
| `ATTEMPT_LEDGER.md` | Every execution, including the stub dry run. |
| `tables/P0_*`, `pilot_inputs.csv` | Provenance, reproduction and the input contract. |
| `tables/paid_paths.csv`, `fit_diagnostics.csv`, `predictions.csv`, `oracle_response_diagnostics.csv`, `evaluation.csv`, `metrics.csv` | P1/P2 outputs, with the fields of the spec. |
| `tables/negatives_12_predictions.csv`, `named_case_predictions.csv`, `bootstrap_undefined_draws.csv`, `P1_*` | Case summaries and checks. |
| `tables/descriptive_whole_vs_A_by_label.csv` | The descriptive table (item 3). |
| `IOAN_SUMMARY.md`, `tables/ioan_cases.csv`, `tables/ioan_case_frames.csv`, `figures/ioan_*` | One-page summary for Ioan; six cases with verified image links. |
| `TIMESTEP_DT_USAGE_AUDIT.md`, `tables/timestep_dt_*.csv` | The `timestep × DT` audit (item 6). |
| `figures/pilot_fig1_learned_thresholds.png`, `figures/pilot_fig2_metrics_by_budget.png` | Pilot figures. |
