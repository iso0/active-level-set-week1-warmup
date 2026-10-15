# V2 model report: does uncertain depth–label sharing (V2 EP mixture) improve canonical-label BA over its binary counterpart?

**Status.** Development work on DEV repeats 1–2 of previously inspected simulations; not confirmation.
- **Freeze:** `v2_model_comparison/V2_MANIFEST.json`, commit `44b7f0cd`, written 2026-10-14 22:15:56 UTC before any comparison fit.
- **Validation:** commit `05f628dc`.
- **Results:** commit `006ca9f5`. These came from queue tasks T01–T04, run by the continuation runner on one thread.
- **Evidence labels:** **PRED** = held-out predictions; **OBS** = logs and tables; **POST-HOC** = added after the results were seen; **HYP** = interpretation.
- **Unchanged decisions:** Stage M (screen failed), C3 (not confirmed), and the marked errata of 2026-10-14 (ledger row ERR). C4 and real-data Stage A are not authorized.
- **Standing caveats** (markers used in this report):
  - **[C1]** The paid-prevalence cutoff p ≥ π̂ is a heuristic. The paid fraction is not an unbiased estimate of the target prevalence, and the probabilities need not be population-calibrated.
  - **[C2]** "No tested model resolves the corner" means that none of the tested models did, not that no discriminator exists.
  - **[C3]** VX > 0.85 is an explanatory reference from earlier inspection. Only the evaluator uses it.

## 1. What was run

### Model and validation
- **Model (Astra's V2).**
  - Equation: h = ρ f + √(1 − ρ²) g − θ + δ, with ρ ∈ {0, 0.5, 1} and a prior of 1/3 each. The response is z = log(A/111 µm) | f ~ N(f, 0.03²), and Y | h ~ Bernoulli(Φ(h/0.15)). Priors are the Stage M priors.
  - Inference:
    - Each component uses damped parallel EP: damping 0.5; tolerance 1e-8 on three consecutive updates; at most 200 iterations.
    - If any component fails, the whole mixture is refitted with Laplace (accepted at gradient ≤ 2e-6).
    - Prediction is p = Σ_k w_k Φ(μ_k / √(τ² + V_k)).
- **Port validation (T01, `validation/V2_VALIDATION.json`).** **PASS**, 17/17 hard checks, using 144 component solves and 16 sampling chains. The port:
  - reproduces Astra's checks and her delivered references;
  - matches her sparse case and her ESS reference;
  - shows zero synthetic leakage;
  - refits the whole mixture on an induced failure.
  - On real NEW checkpoints it also passes:
    - parity;
    - the binary limits;
    - invariance to corrupted unpaid or test outcomes;
    - batch invariance;
    - keeping a label when its response is missing;
    - an induced fallback;
    - the covariance and acquisition identities.

### Design and arms
- **Design.** NEW-136 (124 Keyhole / 12 no Keyhole; canonical any-observed-Keyhole label; full simulation IDs).
  - Splits: repeats 1–2 × folds 1–5.
  - Paths: the saved Week 19 feature-only maximin prefixes, cut at B16 and B40.
  - Inputs: log P, VX, LS radius and ST, standardized on the fold's feature-only pool.
  - Response: the existing ACTIVE A; a missing A is never imputed.
- **Arms** (the frozen definitions are in `V2_MANIFEST.json`):

| Arm | Source |
|---|---|
| V2_EP_mixture | new fit |
| rho1_EP | the mixture's ρ = 1 EP component (exact reuse) |
| Binary_V2_EP | new fit without the response; the three masses must stay at 1/3 |
| V1_Laplace, Binary_V1_Laplace, ACTIVE_E1, G3 | exact Stage M reuse after prefix, scaler, configuration, response-use and implementation checks |
| J_trained | EX2's trained response prior; a complete-system control |
| VX_stump | vx-stump-1.0: one cut on standardized log VX learned from the paid labels |

- **Accounting (OBS, `RUN_STATE.json`).**
  - 180 / 180 top-level requests, all with status `ok`.
  - Component attempts: 144 for validation + 140 for the comparison = 284, within the cap of 300.
  - No failure and no Laplace fallback.
  - 80 Stage M reuses verified. All 20 rho1_EP checkpoints reused the mixture's ρ = 1 EP component.
  - Post-fit exports of the V2_EP_mixture and Binary_V2_EP posteriors were written for the cached-posterior decision audit; they changed no fit or metric.
- **Uncertainty.** Class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), shared by all arms, both repeats and both budgets. It is conditional on the stored fits and splits.

## 2. Decision (frozen screen; `v2_model_comparison/V2_DECISION.json`): **SCREEN NOT PASSED**

Astra's development screen calls V2 promising only if three conditions all hold at NEW B40, cutoff 0.5:

| Criterion (V2_EP_mixture − Binary_V2_EP) | Result | Holds? |
|---|---|---|
| BA ≥ +0.01 | **−0.002** [−0.006, 0.000]; per repeat −0.004 and 0.000 | **no** |
| Specificity not lower | 0.000 (0.125 vs 0.125) | yes |
| Log loss not worse | −0.040 [−0.065, −0.013] | yes |

- **Trade-offs at B40, 0.5 (always reported):**
  - Sensitivity −0.004 and q20 −0.017.
  - Short-K sensitivity −0.05 (0.80 vs 0.85).
  - AUC +0.067 [0.023, 0.125] and Brier −0.009 [−0.015, −0.004].
- **At B16** (not part of the screen): BA +0.006 [0.000, 0.014], log loss −0.058 [−0.077, −0.038], AUC +0.148 [0.072, 0.233].

## 3. Results (PRED; pooled per repeat, mean of repeats 1–2; `v2_model_comparison/metrics_per_repeat.csv`)

### NEW B40, cutoff 0.5
Counts are means per repeat (124 positives, 12 negatives).

| Arm | BA | Sens | Spec | q20 | Short-K | Brier | Log loss | AUC | TP | FN | TN | FP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V2_EP_mixture | 0.554 | 0.984 | 0.125 | 0.667 | 0.80 | 0.066 | 0.219 | 0.868 | 122.0 | 2.0 | 1.5 | 10.5 |
| rho1_EP | 0.554 | 0.984 | 0.125 | 0.667 | 0.80 | 0.066 | 0.218 | 0.869 | 122.0 | 2.0 | 1.5 | 10.5 |
| Binary_V2_EP | 0.556 | 0.988 | 0.125 | 0.683 | 0.85 | 0.075 | 0.259 | 0.801 | 122.5 | 1.5 | 1.5 | 10.5 |
| V1_Laplace | 0.552 | 0.980 | 0.125 | 0.650 | 0.75 | 0.063 | 0.212 | 0.873 | 121.5 | 2.5 | 1.5 | 10.5 |
| Binary_V1_Laplace | 0.546 | 0.968 | 0.125 | 0.600 | 0.70 | 0.108 | 0.384 | 0.800 | 120.0 | 4.0 | 1.5 | 10.5 |
| ACTIVE_E1 | 0.730 | 0.960 | 0.500 | 0.750 | 0.60 | 0.070 | 0.799 | 0.893 | 119.0 | 5.0 | 6.0 | 6.0 |
| G3 | 0.618 | 0.944 | 0.292 | 0.633 | 0.40 | 0.091 | 0.307 | 0.819 | 117.0 | 7.0 | 3.5 | 8.5 |
| J_trained | 0.707 | 0.956 | 0.458 | 0.717 | 0.60 | 0.053 | 0.171 | 0.918 | 118.5 | 5.5 | 5.5 | 6.5 |
| VX_stump | 0.851 | 0.911 | 0.792 | 0.717 | 0.10 | 0.082 | 0.271 | 0.818 | 113.0 | 11.0 | 9.5 | 2.5 |

- **Per repeat (OBS):**
  - V2 BA is 0.617 in repeat 1 (TN 3, FP 9) and 0.492 in repeat 2 (TN 0, FP 12). In repeat 2 it rejects none of the 12 negatives.
  - Binary V2 is 0.621 and 0.492.

### NEW B16, cutoff 0.5 (BA / specificity / log loss / AUC)

| Arm | BA | Spec | Log loss | AUC |
|---|---|---|---|---|
| V2_EP_mixture | 0.600 | 0.208 | 0.258 | 0.797 |
| rho1_EP | 0.579 | 0.167 | 0.247 | 0.820 |
| Binary_V2_EP | 0.594 | 0.208 | 0.316 | 0.649 |
| V1_Laplace | 0.581 | 0.167 | 0.242 | 0.847 |
| Binary_V1_Laplace | 0.588 | 0.208 | 0.453 | 0.637 |
| ACTIVE_E1 | 0.611 | 0.250 | 1.048 | 0.842 |
| G3 | 0.624 | 0.292 | 0.402 | 0.704 |
| J_trained | 0.673 | 0.375 | 0.161 | 0.934 |
| VX_stump | 0.791 | 0.667 | 0.291 | 0.711 |

### Paired contrasts at B40 (simulation-cluster bootstrap; `v2_model_comparison/contrasts.csv`)

| Family | Contrast | BA at 0.5 | Other |
|---|---|---|---|
| mechanism | rho1_EP − V1_Laplace (EP vs Laplace, same model) | +0.002 [−0.060, +0.063] | log loss +0.006 [−0.001, +0.012]; AUC −0.005 |
| mechanism | V2_EP_mixture − rho1_EP (uncertain vs forced sharing) | 0.000 [0.000, 0.000] | log loss +0.001; identical decisions |
| system | V2 − J_trained | −0.153 [−0.276, −0.040] | specificity −0.333; short-K +0.20 |
| system | V2 − ACTIVE_E1 | −0.175 [−0.302, −0.051] | specificity −0.375; log loss −0.580 |
| system | V2 − G3 | −0.063 [−0.134, +0.003] | sensitivity +0.040; short-K +0.40 |
| system | V2 − VX_stump | −0.297 [−0.401, −0.187] | specificity −0.667; short-K +0.70 |
| descriptive | Binary_V2_EP − Binary_V1_Laplace | +0.010 [0.002, 0.022] | log loss −0.125 |
| descriptive | J_trained − Binary_V2_EP | +0.151 [0.038, 0.274] | short-K −0.25 |
| descriptive | J_trained − ACTIVE_E1 | −0.023 [−0.093, +0.042] | log loss −0.629 |
| descriptive | VX_stump − G3 | +0.234 [0.151, 0.313] | short-K −0.30 |

### Mixture masses (OBS, `component_masses_and_moments.csv`, mean over the 20 checkpoints)

| Budget | ρ = 0 | ρ = 0.5 | ρ = 1 |
|---|---|---|---|
| B16 | 0.024 | 0.241 | 0.735 |
| B40 | 0.001 | 0.050 | 0.949 |

Binary V2 masses stay at exactly 1/3, as required.

### Secondary rule p ≥ π̂ (paid positive fraction; a heuristic [C1], not part of the screen)
- **B40 BA:**
  - V2 0.878 (sensitivity 0.839, specificity 0.917, short-K 0.00); rho1_EP 0.880.
  - V1_Laplace 0.870; Binary V2 0.785; J_trained 0.906.
- **Contrast:** V2 − Binary V2 at π̂ is +0.093 [0.024, 0.194]. The gain comes with short-K sensitivity of 0: transient positives are lost.

### Fast-scan corner (VX > 0.85 m/s; an evaluator-only description, never a model input)
B40 counts are summed over both repeats: 24 positive and 22 negative cases in the corner (`fast_scan_corner_errors.csv`).

| Arm (0.5) | TP | FN | TN | FP |
|---|---|---|---|---|
| V2_EP_mixture | 20 | 4 | 3 | 19 |
| Binary_V2_EP | 21 | 3 | 3 | 19 |
| J_trained | 13 | 11 | 11 | 11 |
| ACTIVE_E1 | 14 | 10 | 12 | 10 |
| G3 | 10 | 14 | 7 | 15 |
| VX_stump | 2 | 22 | 19 | 3 |

- **At π̂:** V2 and J_trained label the whole corner negative (0 / 24 / 22 / 0).
- **Outside the corner:** every arm at 0.5 classifies all 224 positive cases correctly. Every arm misclassifies the one negative case in both repeats: the early-ended slow scan `P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce`, which has no A (V2 p = 0.989 at B40).

## 4. Interpretation (HYP)

1. **Depth helps probabilities, not the 0.5 decision.** With the response, V2's probabilities are better than Binary V2's: log loss −0.040, Brier −0.009, AUC +0.067 at B40. The 0.5 decisions do not change (BA −0.002). This repeats the V1 Stage M pattern on NEW.
   - With 124 positives and 12 negatives, the V1 and V2 arms (with or without the response) reject on average only 1.5 of 12 negatives at B40 at 0.5.
   - The binding constraint is the decision rule and the corner, not how depth is shared.
2. **The mixture collapses to forced sharing.** At B40 the mixture puts 0.95 of its mass on ρ = 1, so V2 equals rho1_EP to the decision.
   - "Uncertain sharing" neither protects nor hurts here: on NEW the paid responses favour full sharing.
   - EP vs Laplace on the same model changes BA by +0.002 (interval ±0.06). The inference method is not the bottleneck.
3. **The cutoff dominates.** Moving it from 0.5 to π̂ raises V2's BA by +0.32. That only re-states the rule question [C1]: the gain comes from rejecting the corner, at the cost of short-K detection.
   - The finite-batch decision audit was frozen to study this rule on the same exported posteriors. At the time of writing it was stopped at T05 (see `v2_decision_audit/SAFEGUARD_CORRECTION.md`, addendum 1.1.1).
   - **Update 2026-10-15** (see `v2_decision_audit/DECISION_AUDIT_REPORT.md`):
     - The audit ran in the owner-authorized recovery. Its frozen outcome is **PRIMARY_UNAVAILABLE**: only 11 of 20 checkpoints met the frozen QMC acceptance.
     - Under the registered amendment A1 (one more ladder level, criterion unchanged; AMENDED), the finite-batch rule at NEW B40 gives BA 0.858, sensitivity 0.798, specificity 0.917, short-K 0.00.
     - Its decisions equal the posterior-mean-π rule, and it does not exceed π̂ (0.878).
4. **The complete-system controls beat V2 at 0.5 by 0.15–0.30 BA,** almost entirely through corner specificity.
   - The controls are J_trained, ACTIVE_E1 and VX_stump.
   - They differ from V2 in more than one factor (a trained response prior; one learned VX cut), so these are not attributions.
   - VX_stump's advantage costs short-K sensitivity (0.10). [C3]
5. **No tested model resolves the corner** [C2].

## 4a. EX3: V2 with the EX2-trained response prior (EXPLORATORY; DEV repeats 5–8; separate manifest)

**Run.** `exploratory/EX3_V2_with_trained_response_prior/EX3_MANIFEST.json` was frozen at 22:27:09 UTC before any EX3 fit. The fits ran as queue T13–T14 (commit `74c5ae0d`): 40 fits, all `ok`, no fallback.

| NEW, cutoff 0.5 | BA B16 | BA B40 | Spec B40 | Short-K B40 | Log loss B40 | AUC B40 |
|---|---|---|---|---|---|---|
| V2_trained | 0.569 | 0.684 | 0.396 | 0.750 | 0.183 | 0.903 |
| rho1_trained_EP | 0.568 | 0.725 | 0.479 | 0.750 | 0.181 | 0.907 |
| J_trained (stored EX2) | 0.618 | 0.752 | 0.542 | 0.675 | 0.166 | 0.916 |
| Binary_V2_EP | 0.513 | 0.541 | 0.104 | 0.825 | 0.269 | 0.778 |

**Prospective hypotheses:**
- **EX3-P1 (supported):** the median B40 posterior mass on ρ = 1 should be ≥ 0.8. It is 0.889; the mean masses for ρ = 0 / 0.5 / 1 are 0.015 / 0.120 / 0.865.
- **EX3-P2 (falsified):** the hypothesis was |BA(V2_trained) − BA(rho1_trained_EP)| < 0.01. The difference is −0.042 [−0.094, 0.000] (per repeat 0, −0.083, −0.083, 0).
  - The cause is specificity −0.083: the residual mass on ρ < 1 returns some corner negatives to "Keyhole".

**Further contrasts at B40:**
- V2_trained − Binary_V2_EP: +0.143 [0.081, 0.206].
- V2_trained − J_trained: −0.068 [−0.142, −0.007].

**HYP.**
- Once the response prior is trained, depth sharing does add BA over the binary model at 0.5. In the untrained V2 comparison (DEV 1–2) it did not.
- Uncertainty over the coupling ρ costs a little against forced sharing; it does not help.
- None of this is confirmatory: these are inspected repeats, chosen after EX2.

## 5. Limitations
- **Data:** development data, two repeats of previously inspected simulations, and 12 negatives. Specificity moves in steps of 1/12 per repeat. The bootstrap is conditional on the fits and splits, and repeated predictions of a simulation are not independent cases.
- **Screen:** +0.01 is a practical threshold, not a forecast or a significance test.
- **Budgets:** results cover B16 and B40 only. B80 and acquisition were not studied.

## 6. Files
`v2_model_comparison/`:
- `V2_MANIFEST.json`, `V2_DECISION.json`, `RUN_STATE.json`
- `metrics_per_repeat.csv`, `contrasts.csv`, `component_masses_and_moments.csv`
- `fast_scan_corner_errors.csv`, `paid_negatives.csv`, `heldout_negative_predictions.csv`
- `fit_log.csv`, `predictions_all.csv.gz`
- `validation/V2_VALIDATION.json`

Code: `src/jdl_v2_model.py`, `src/jdl_v2_comparison.py`, `src/jdl_v2_evaluate.py`, `src/jdl_v2_export.py`, `src/jdl_vx_stump.py`, `src/jdl_v2_validation.py`. Their hashes are in the manifest.
