# EX metrics addendum: q20, AUC, short-K, counts, J_trained at 0.5 vs π̂, and the POST-HOC frontier

**Status.** **POST-HOC** addendum to `EXPLORATORY_REPORT.md`, computed from the stored EX1/EX2 predictions only.
- **Data:** DEV repeats 5–8, NEW-136 (124 Keyhole / 12 no Keyhole); OLD and POOLED where stored.
- **No new fit:** no model was refitted, no threshold or rule was re-tuned, and no exploratory decision was changed.
- **Run:** queue task T09 (`src/jdl_ex_metrics_addendum.py`, 45 s on one thread, commit `cabdbe57`); the descriptive re-run T10 (`src/jdl_ex_descriptive.py`, commit `3b50def4`).
- **Outputs:** `EX_METRICS_ADDENDUM/` (`metrics_with_counts.csv`, `paired_contrasts.csv`, `J_trained_rule_change_by_simulation.csv`, `POSTHOC_threshold_frontier_B40.csv`) and `POSTHOC_descriptive/`.
- **Uncertainty:** Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), conditional on the stored fits.
- **Standing caveats (markers in this file):**
  - **[C1]** p ≥ π̂ is a heuristic. The paid fraction is not an unbiased prevalence estimate, and the probabilities need not be population-calibrated.
  - **[C2]** "None of the tested models" is not "no discriminator".
  - **[C3]** VX > 0.85 is an explanatory reference from earlier inspection. It is not train-only.
  - **[C4]** J_trained at π̂ was singled out on global BA, which is not a sufficient selection criterion.

## 1. NEW B40, all metrics with counts (mean of repeats 5–8; `metrics_with_counts.csv`)

| Arm | Rule | BA | q20 | Spec | Sens | Short-K | Brier | Log loss | AUC |
|---|---|---|---|---|---|---|---|---|---|
| J (Stage M config) | 0.5 | 0.543 | 0.692 | 0.104 | 0.982 | 0.850 | 0.064 | 0.214 | 0.864 |
| J | π̂ [C1] | 0.878 | 0.592 | 0.917 | 0.839 | 0.025 | 0.064 | 0.214 | 0.864 |
| J_trained | 0.5 | 0.752 | 0.783 | 0.542 | 0.962 | 0.675 | 0.050 | 0.166 | 0.916 |
| J_trained | π̂ [C1, C4] | 0.906 | 0.650 | 0.917 | 0.895 | 0.050 | 0.050 | 0.166 | 0.916 |
| Binary_matched | 0.5 | 0.568 | 0.650 | 0.167 | 0.970 | 0.775 | 0.108 | 0.383 | 0.774 |
| Binary_matched | π̂ | 0.501 | 0.300 | 1.000 | 0.002 | 0.000 | 0.108 | 0.383 | 0.774 |
| ACTIVE_E1 | 0.5 | 0.682 | 0.742 | 0.396 | 0.968 | 0.700 | 0.076 | 0.716 | 0.914 |
| ACTIVE_E1 | π̂ | 0.729 | 0.750 | 0.500 | 0.958 | 0.575 | 0.076 | 0.716 | 0.914 |
| G3 | 0.5 | 0.644 | 0.650 | 0.333 | 0.954 | 0.550 | 0.093 | 0.320 | 0.769 |
| G3 | π̂ | 0.687 | 0.458 | 0.979 | 0.395 | 0.000 | 0.093 | 0.320 | 0.769 |

- **Per-repeat values and confusion counts** (TP/FN/TN/FP, with unique simulations) are in the CSV.
- **Quoted numbers reproduced:** these match the numbers quoted in `EXPLORATORY_REPORT.md`: G3 0.6435 / short-K 0.55; ACTIVE_E1 0.6818 / 0.70; J_trained at 0.5 0.7517 / 0.675; J_trained at π̂ 0.9059 / 0.05. The test `test_ex_addendum_reproduces_the_quoted_numbers` checks this at T17.
- **OLD and POOLED** (stored arms only): J_trained at 0.5 reaches BA 0.925 (OLD) and 0.939 (POOLED) at B40.

## 2. Paired contrasts at NEW B40 (`paired_contrasts.csv`)

| Contrast | BA | Specificity | Sensitivity | Short-K | q20 | Log loss | AUC |
|---|---|---|---|---|---|---|---|
| J_trained π̂ − J_trained 0.5 | +0.154 [0.053, 0.268] | +0.375 | −0.067 | **−0.625** [−0.813, −0.406] | −0.133 | 0 | 0 |
| J_trained 0.5 − ACTIVE_E1 0.5 | +0.070 [−0.018, 0.171] | +0.146 | −0.006 | −0.025 | +0.042 | −0.550 | +0.002 |
| J_trained 0.5 − G3 0.5 | +0.108 [0.035, 0.190] | +0.208 | +0.008 | +0.125 | +0.133 | −0.154 | +0.147 |
| J_trained 0.5 − J 0.5 | +0.209 [0.110, 0.310] | +0.438 | −0.020 | −0.175 | +0.092 | −0.048 | +0.052 |
| J_trained 0.5 − Binary_matched 0.5 | +0.184 [0.100, 0.268] | +0.375 | −0.008 | −0.100 | +0.133 | −0.217 | +0.142 |
| J_trained π̂ − ACTIVE_E1 0.5 | +0.224 [0.104, 0.346] | +0.521 | −0.073 | −0.650 | −0.092 | −0.550 | +0.002 |

- **Same scores, different rule:** the J_trained π̂ − 0.5 contrast changes only the cutoff, so the scores are identical (log loss and AUC differences 0). The whole BA gain is a trade: corner negatives gained against short-K positives lost.

## 3. Which simulations change between J_trained at 0.5 and at π̂ (`J_trained_rule_change_by_simulation.csv`, full IDs)

- **B40: 21 simulations change** in at least one of the four repeats.
  - **8 negatives gained** (18 repeat-instances). All 8 are in the fast-scan corner [C3].
  - **13 positives lost** (33 repeat-instances). 10 are in the corner and 9 are short-K.
  - **Three of the lost positives are outside the corner:**
    - `P-351p157464561_VX-0p813888376043_LS-4p78494456981e-05_ST-349p508071973_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p92725089215e-06_H-bba3700d20`: VX 0.814, lost in 4 of 4 repeats.
    - `P-424p576470605_VX-0p257086791186_LS-4p07840364156e-05_ST-494p332476624_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p87645603291e-05_H-6dae2a1270`: lost in 1 of 4.
    - `P-400p525454977_VX-0p341072284717_LS-4p30678180913e-05_ST-491p080440097_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p41439830182e-05_H-1d3f99112b`: lost in 1 of 4.
- **B16: 22 simulations change.** 10 negatives are gained (31 instances, all in the corner). 12 positives are lost (42 instances; 11 in the corner, 10 short-K).

## 4. Inside vs outside the fast-scan corner (POST-HOC descriptive, `POSTHOC_descriptive/NEW_BA_inside_vs_outside_fast_corner.csv`, B40)

| Arm | BA inside the corner at 0.5 (12 positive / 11 negative per repeat) | BA inside the corner at π̂ |
|---|---|---|
| J_trained | 0.598 | 0.521 |
| ACTIVE_E1 | 0.549 | 0.554 |
| Binary_matched | 0.497 | 0.500 |
| J | 0.463 | 0.510 |
| G3 | 0.453 | 0.500 |

- **Inside the corner:** the hand-computed range of 0.45–0.60 cited in `EXPLORATORY_REPORT.md` is confirmed (0.453–0.598).
- **Outside the corner** there are 112 positives and 1 negative per repeat. BA there is 0.46–0.59 for every arm and rule. At 0.5 every arm misclassifies that single negative in every repeat. It is the early-ended slow scan `P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce`, which has no A.
- **Reference rule:** "no Keyhole iff VX > 0.85" gives BA 0.910 (sensitivity 0.903, specificity 0.917) [C3].
- **AUC per repeat** (`AUC_per_repeat.csv`, mean): J_trained 0.916, ACTIVE_E1 0.914, J 0.864, Binary_matched 0.774, G3 0.769 at B40.

## 5. POST-HOC threshold frontier (`POSTHOC_threshold_frontier_B40.csv`; uses evaluation labels, so it describes and is not a method)

| Arm | BA at 0.5 | Best mean BA over all cutoffs | Cutoff | Specificity / sensitivity there | Short-K there |
|---|---|---|---|---|---|
| J_trained | 0.752 | 0.918 | 0.841 | 0.917 / 0.919 | 0.20 |
| ACTIVE_E1 | 0.682 | 0.918 | 1.000 | 0.917 / 0.919 | 0.30 |
| J | 0.543 | 0.898 | 0.836 | 0.917 / 0.879 | 0.00 |
| G3 | 0.644 | 0.823 | 0.687 | 0.750 / 0.895 | 0.30 |
| Binary_matched | 0.568 | 0.820 | 0.712 | 0.833 / 0.807 | 0.30 |

## 6. Interpretation (HYP)
- **Ranking:** J_trained has the best ranking on NEW (AUC 0.916) and the best BA at 0.5 (0.752). It is a serious complete-system comparator.
- **The π̂ gain is a cutoff trade:** at π̂ its extra BA (+0.154) comes from rejecting 8 corner negatives at the cost of 13 positives, most of them transient short-K cases (short-K sensitivity 0.675 → 0.05) [C1, C4].
- **The frontier is post-hoc:** every model's best label-chosen cutoff reaches BA 0.82–0.92, the same ceiling set by the corner. No tested score separates the corner [C2].
- **Rule question:** choosing a cutoff without evaluation labels is a separate decision-rule question. It is what the frozen finite-batch decision audit was built to study on the V2 posteriors; that audit is currently stopped at T05 (see `../v2_decision_audit/SAFEGUARD_CORRECTION.md`).
