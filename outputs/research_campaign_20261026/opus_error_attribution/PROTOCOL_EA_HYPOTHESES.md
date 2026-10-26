# EA study, stage 1: hypotheses and diagnostic design

Registered 2026-10-26, before any EA computation.

## 0. Known before registration (from the records; not re-run)

**Full-pool, evaluator-only, 5-fold CV** (`opus_rc21/diagnostics/DESIGN_DIAGNOSTICS.md`):

| model | BA | LL | NEW-conduction recall |
|---|---|---|---|
| oracle log A alone | 0.978 | 0.072 | 0.909 |
| h only | 0.948 | – | 0 |
| ARD GPC on the 4 log inputs | 0.969 | – | 0.455 |

In the same study, h and T/S add nothing to the oracle A. These numbers hold at about 387 training runs, not at active-learning budgets.

**Training-feature noise** (RC20 `FINAL_REPORT_RC20.md` §3):
- Honest out-of-fold depth features differ from in-sample approximations by 0.54 / 0.42 / 0.22 feature-SD at B12 / B16 / B24.
- The classifier coefficients are attenuated.
- The remedies tried (fold deployment, MAP lengthscales) gave nothing.

**Older JDL model, NEW population** (`joint_depth_label_development/MECHANISM_REPORT.md`):
- Fast-scan negatives get depth predictions that are too deep.
- The held-out true A separates them only partly.

**EL study:**
- HA_TREND's early gain is a prediction effect, concentrated at b ≤ 16.
- There is no reliable single-learner saving to BA 0.95.
- Current reference A = HA_LEAN + margin. Its individual BA is about 0.957 at B60.

## 1. Hypotheses: which stage limits progress?

| | hypothesis | measured signature |
|---|---|---|
| H-A | The **depth emulator** cannot predict depth well enough from few observations. | Replacing the emulator's depth by the true depth (R2, R3) closes most of the gap. R3u vs R3 then splits the gap: the part recovered by the "unlimited-data emulator" (R3u) is a data limitation; the part only the true depth recovers means the depth is not predictable from the inputs with this emulator family even with all other runs. |
| H-B | Even with the **true depth**, the h + depth classifier family does not explain the label well enough. | A flexible family on the same (z_h, true depth) inputs (R5) beats the linear family (R3) materially, or R3 stays far below its large-n value (R6). |
| H-C | **Compressing** the four inputs into (h, depth) loses label information. | Adding the three log-input directions orthogonal to h to the true-depth classifier (R4) beats R3 materially. |
| H-D | A **combination** of the above, or a **label / time-window mismatch**. | No single step dominates. Or the residual errors of R3–R5 concentrate on records whose label and depth may refer to different time windows: short records, early-ending records, short-Keyhole originals (evaluator-only descriptors). |

None of these is assumed. Different labels at similar inputs are not read as "unlearnable", "random" or "label error".

## 2. Rungs

All rungs use the SAME recorded HA_LEAN margin paths and, at budget b, the SAME first b paid runs.

**Notation:**
- **Classifier:** the HA_LEAN learned-regularisation Laplace logistic (`src.rc22_common.phr_family`, grid τ_F, τ_h ∈ {0.5, 1, 2, 4}), unless stated.
- **a:** log active maximum depth.
- **F:** honest K = 10 out-of-fold emulator means at the paid runs.
- **E:** full-fit emulator mean.

**Deployable (paid information only):**

| rung | train feature | test feature | note |
|---|---|---|---|
| R0_L | F_L | E_L | current HA_LEAN; must equal the recorded A exactly |
| R0_T | F_T | E_T | HA_TREND; must equal the recorded D exactly |
| R1a_L | in-sample full-fit means E_L at the paid runs | E_L | approximate stacking (cf. RC19 ATSAPPROX) |
| R1b_L | the measured paid depths a (for short records and the missing-A run, the in-sample emulator mean) | E_L | plug-in |

**Evaluator-only oracle diagnostics.** These use unopened true outcomes. They are NOT methods, give no query saving and set no universal ceiling.

| rung | train feature | test feature | note |
|---|---|---|---|
| R2_L, R2_T | R0_L / R0_T classifier | TRUE test depth | |
| R3u | "unlimited-data emulator" predictions at the paid runs | same, at the test runs | the emulator is the HA_LEAN depth GP (same code path) fitted in 20 folds on the whole pool; each run is predicted by the fold model that excludes it |
| R3 | true paid depth | true test depth | |
| R4 | R3 + the three standardised log-input directions orthogonal to h (U, `src.rc21_phr.transverse`) | same | linear terms with their own prior scale τ_U ∈ {0.5, 1, 2, 4} |
| R5 | as R3 | as R3 | the same features plus a residual r(z_h, a) ~ GP(0, σ_r² RBF_ℓ) on the 2-D (standardised) feature space; the RC21 grid σ_r ∈ {0, 0.5, 1, 2}, ℓ ∈ {0.75, 1.5}, P(σ_r = 0) = 1/2 |
| R6 | R3 and R5 trained on all pool runs of the task (about 433, true depth) | the task's test set | large-n reference |
| R6u | the same with unlimited-emulator predictions | | |

Rungs R1b, R3, R4, R5 and R6 are computed only on test rows with a true depth. The one run without A is excluded from every oracle comparison, and all rungs are compared on the same common rows.

## 3. Analyses

All are pre-declared. The primary unit is the individual learner, with pooled values beside.

1. **BA by budget for every rung.**
   - Early window B8–B24 (every budget), late window B28–B60 (every 4).
   - Decomposition of the R3 − R0_L gap into:
     - test-time emulation, R2_L − R0_L;
     - training features, R3 − R2_L;
     - the part attainable from the inputs, R3u − R0_L, and the rest, R3 − R3u.
   - Representation: R4 − R3. Family: R5 − R3. Finite labels: R6 − R3.
2. **Error types.** False Keyhole (predicted K, true conduction) and missed Keyhole, separately, per rung and window.
3. **Per-example transitions** on identical (learner, budget, test run) triples:
   - which rung first fixes an R0_L error;
   - which errors no rung fixes;
   - which correct R0_L calls a rung breaks;
   - all by class and window.
4. **Emulator depth error** E − a by budget: bias and RMSE, fast-scan corner (RC21 definition, evaluator-only) vs the rest, HA_LEAN vs HA_TREND. Also the unlimited-data emulator's error by region.
5. **Pairs similar in (z_h, true a) with opposite labels** on the full pool:
   - count and location;
   - evaluator-only descriptors: record quality, early end, short-K, frac_K_FCK, raw inputs, batch as provenance only.
6. **Controls:**
   - geometric blocks (K5, K4 paths);
   - the short-Keyhole and NEW-conduction hard group (RC24 definition), reported as strata.

**Data:** the recorded HA_LEAN paths of the EL-1 forward stage, all DEV:
- STD repeats 83–122: 40 clusters, 200 learners;
- K5 startups 25–32: 40 learners;
- K4 startups 9–16: 32 learners.

## 4. From diagnosis to design

The dominant stage in a window is the rung step that carries the largest share of the R0_L → R5 BA gap (and of the false- / missed-Keyhole errors), read separately for the early and the late window.

The development target follows it:

| dominant stage | development target |
|---|---|
| H-A data limitation (R3u − R0_L large) | the depth emulator's data efficiency |
| H-A non-identifiability (R3 − R3u large, R3u − R0_L small) | not emulator capacity; the classification / probability layer or the selector, to be justified separately |
| H-B / H-C | the classification layer |
| H-D | the stated mismatch |

Candidates, their equations, information use, learned parameters, mechanism and controls are registered in a separate protocol BEFORE they are evaluated. The selector stays margin unless a new measured defect of margin is shown first on the same paid data.

## 5. Information rules for any candidate

No oracle quantity, test label or hard-group membership enters any candidate's training, selector, weights or stopping.
