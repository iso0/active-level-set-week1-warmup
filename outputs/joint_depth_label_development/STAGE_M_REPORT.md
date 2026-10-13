# Stage M report — does paid ACTIVE depth add canonical-label information to a matched binary model?

**Status.** Development on DEV repeats 1–2 of previously inspected simulations; not confirmation.
- **Freeze:** `STUDY_MANIFEST.json`, commit `0c0ce614`, written before any comparative fit.
- **Results:** commit `23acbaa3`.
- **Evidence labels:** **PRED** = held-out predictions; **OBS** = logs and tables; **POST-HOC** = added after the results were seen; **HYP** = interpretation.

## 1. What was run

- **Model.** The port `src/jdl_model.py` of Astra's joint depth–label GP:
  - h = f − θ + δ, with z = log(A/111) | f ~ N(f, 0.03²) and Y | h ~ Bernoulli(Φ(h/0.15)).
  - Fixed priors: Matérn-3/2 kernels with response SD 0.60 and discrepancy SD 0.35; both use lengthscales (1.5, 1.5, 1.5, 1.5) on log inputs standardized over the fold's feature-only pool. θ ~ N(0, 0.35²).
  - The discrepancy is centred on that fixed pool.
- **Validation** before any fit (`validation/validation_results.json`, 21 checks, PASS):
  - The port reproduces all 26 of Astra's checks and their documented limitations.
  - It matches the reference in four dimensions to about 1e-11, for the posterior, probabilities and acquisition.
  - Further checks passed: covariance reconstruction, batch invariance, centering, one-class data, missing response, gradient acceptance, corruption of every unpaid or test outcome, and refit-from-prior.
  - On a small case it was compared with exact orthant probabilities, rejection sampling and slice sampling. The Laplace step's probability error there is at most 0.040 (mean 0.016).
- **Paths (OBS).** Feature-only maximin orders to B80, with prefixes at B16 and B40.
  - NEW reproduces the saved Week 19 paths exactly (10/10).
  - OLD and POOLED use the same routine with their task seeds plus [2].
  - No prefix is one-class: NEW B16 prefixes contain 1–3 negatives.
- **Arms.** J; J_fixed_theta (θ ≡ 0); J_no_delta (δ ≡ 0); Binary_matched (no continuous likelihood, identical priors, centering and link); ACTIVE_E1; G3.
  - ACTIVE_E1 and G3 are the frozen implementations with paid-only ML-II, run through the Week 19 `fit_one`.
- **Scale.** 360 fit requests, all `ok`. The 240 J-family fits all converged and passed the gradient criterion (maximum whitened gradient 9.7e-12).

## 2. Decision (frozen screen; `stage_m/STAGE_M_DECISION.json`): **SCREEN FAILED — Stage A is not recommended**

| NEW, B40 (mean of repeats 1–2) | J − Binary_matched | Per repeat | Criterion | Result |
|---|---|---|---|---|
| BA | **+0.006** [−0.052, +0.065] | −0.034, +0.046 | ≥ +0.01 | **fails** |
| Specificity | 0.000 [−0.125, +0.125] | −0.083, +0.083 | ≥ 0 | passes |
| Log loss | **−0.172** [−0.203, −0.130] | −0.175, −0.168 | ≤ 0 | passes |
| Numerical and leakage checks | all pass | | required | passes |

- **The failure is a precision and decision-rule failure** (details in `MECHANISM_REPORT.md`).
- **It is not a numerical failure:** every fit converged, and the Laplace error against slice sampling changes at most 1 decision per fold.
- **It is not an adverse trade-off:** specificity is equal and log loss is clearly better.
  - The BA difference cannot be resolved with 12 NEW negatives: one negative is worth 0.042 BA per repeat, and the interval spans ±0.06.
  - J ranks NEW cases better than Binary_matched (AUC +0.074 [+0.020, +0.142]) and scores them better (log loss −0.17, Brier −0.045).
  - At the 0.5 decision threshold, however, J and Binary_matched both label almost every NEW negative positive (specificity 0.125 for both).
- **Prior restriction (HYP):** the smooth, fixed discrepancy prior does not separate the fast-scan negatives from fast-scan positives with similar depth.
- **What the null means:** an incremental BA benefit at B40 was not demonstrated for this model, prior and budget. It does **not** mean that depth carries no label information. The ranking and probability gains show that it does.

## 3. Results (PRED; pooled per repeat, mean of repeats 1–2; `stage_m/metrics_per_repeat.csv`, `metrics_per_fold.csv`, `predictions_all.csv.gz`)

### NEW (136 simulations: 124 positive, 12 negative)

| B | Arm | BA | q20 | Spec. | Sens. | Short-K | Brier | Log loss | AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | J | 0.581 | 0.733 | 0.167 | 0.996 | 1.00 | 0.067 | 0.242 | 0.847 |
| 16 | J_fixed_theta | 0.579 | 0.700 | 0.167 | 0.992 | 1.00 | 0.066 | 0.240 | 0.852 |
| 16 | J_no_delta | 0.556 | 0.683 | 0.125 | 0.988 | 0.95 | 0.062 | 0.221 | 0.856 |
| 16 | Binary_matched | 0.588 | 0.667 | 0.208 | 0.968 | 0.90 | 0.136 | 0.453 | 0.637 |
| 16 | ACTIVE_E1 | 0.611 | 0.717 | 0.250 | 0.972 | 0.80 | 0.078 | 1.048 | 0.840 |
| 16 | G3 | 0.624 | 0.667 | 0.292 | 0.956 | 0.80 | 0.115 | 0.402 | 0.704 |
| 40 | **J** | **0.552** | 0.650 | 0.125 | 0.980 | 0.75 | 0.063 | **0.212** | 0.873 |
| 40 | J_fixed_theta | 0.552 | 0.650 | 0.125 | 0.980 | 0.75 | 0.062 | 0.208 | 0.878 |
| 40 | J_no_delta | 0.575 | 0.683 | 0.167 | 0.984 | 0.80 | 0.061 | 0.211 | 0.876 |
| 40 | **Binary_matched** | **0.546** | 0.600 | 0.125 | 0.968 | 0.70 | 0.108 | 0.384 | 0.800 |
| 40 | ACTIVE_E1 | **0.730** | 0.750 | 0.500 | 0.960 | 0.60 | 0.070 | 0.799 | **0.893** |
| 40 | G3 | 0.618 | 0.633 | 0.292 | 0.944 | 0.40 | 0.091 | 0.307 | 0.819 |

- **Short-K:** the 10 existing NEW positives with 0 < K/(F+C+K) < 0.10 (membership hash in the manifest), counted as unique simulations.

### OLD (405: 73 positive, 332 negative) and POOLED (541: 197 positive, 344 negative)

| Population | B | J | J_fixed_theta | J_no_delta | Binary_matched | ACTIVE_E1 | G3 |
|---|---|---:|---:|---:|---:|---:|---:|
| OLD BA | 16 | 0.896 | 0.918 | 0.893 | 0.829 | 0.908 | 0.819 |
| OLD BA | 40 | 0.927 | 0.933 | 0.943 | 0.870 | 0.942 | 0.907 |
| OLD log loss | 40 | 0.182 | 0.174 | 0.157 | 0.348 | 0.205 | 0.210 |
| OLD q20 | 40 | 0.800 | 0.794 | 0.818 | 0.747 | 0.806 | 0.794 |
| POOLED BA | 16 | 0.932 | 0.933 | 0.934 | 0.916 | 0.921 | 0.899 |
| POOLED BA | 40 | 0.948 | 0.949 | 0.949 | 0.935 | 0.940 | 0.940 |
| POOLED log loss | 40 | 0.176 | 0.169 | 0.161 | 0.341 | 0.301 | 0.226 |
| POOLED specificity | 40 | 0.936 | 0.936 | 0.933 | 0.949 | 0.927 | 0.942 |

### Paired contrasts (simulation-cluster bootstrap, conditional on the stored fits; `stage_m/paired_contrasts.csv`)

| Contrast (BA) | NEW B16 | NEW B40 | OLD B16 | OLD B40 | POOLED B16 | POOLED B40 |
|---|---|---|---|---|---|---|
| **J − Binary_matched** (continuous likelihood, fixed prior) | −0.007 [−0.109, +0.071] | **+0.006** [−0.052, +0.065] | **+0.067** [+0.036, +0.100] | **+0.057** [+0.028, +0.089] | +0.016 [+0.002, +0.031] | +0.013 [+0.001, +0.025] |
| J − J_fixed_theta | +0.002 | 0.000 | −0.022 [−0.044, −0.003] | −0.006 | −0.002 | −0.001 |
| J − J_no_delta | +0.025 [0.000, +0.069] | −0.023 [−0.087, +0.042] | +0.003 | −0.016 [−0.031, −0.002] | −0.002 | −0.001 |
| J − ACTIVE_E1 (complete systems) | −0.030 | **−0.177** [−0.307, −0.056] | −0.012 | −0.015 [−0.043, +0.013] | +0.010 [−0.003, +0.024] | +0.008 [−0.005, +0.021] |
| J − G3 (complete systems) | −0.042 | −0.065 [−0.134, −0.003] | +0.077 [+0.040, +0.111] | +0.021 [−0.008, +0.050] | +0.032 [+0.014, +0.052] | +0.007 [−0.005, +0.019] |

- **Attribution vs system comparison.** J − Binary_matched attributes the effect of the continuous likelihood under the fixed prior. J − ACTIVE_E1 and J − G3 compare complete systems that also differ in hyperparameter treatment (paid-only ML-II for E1 and G3; fixed priors for J).
- **Populations are reported separately.** They overlap (POOLED contains NEW and OLD), so no pooled significance claim is made.
- **Other metrics, NEW B40, J − Binary_matched:** q20 +0.050 [−0.033, +0.145]; short-K +0.05 [−0.13, +0.25]; AUC +0.074 [+0.020, +0.142]; Brier −0.045.
- **OLD and POOLED regressions.**
  - POOLED: J pays a small specificity cost against Binary_matched, −0.013 [−0.025, −0.002] at B40 and −0.019 at B16, while gaining sensitivity.
  - OLD: J's BA is below ACTIVE_E1 by −0.015 [−0.043, +0.013] at B40.
  - No J − Binary_matched BA contrast falls below the −0.01 practical deterioration threshold in any population.

## 4. Hypotheses (directional, frozen; `STUDY_MANIFEST.json`)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| SM-H1 NEW B40 BA: J > Binary_matched | **direction only, not established** | +0.006 [−0.052, +0.065]; repeats −0.034 / +0.046 |
| SM-H2 NEW specificity | no expectation | 0.000 (both 0.125) |
| SM-H3 NEW log loss: J ≤ Binary_matched | **supported** | −0.172 [−0.203, −0.130] |
| SM-H4 OLD BA: J > Binary_matched at B16 and B40 | **supported** | +0.067 [+0.036, +0.100]; +0.057 [+0.028, +0.089] |
| SM-H5 POOLED | no expectation | +0.016 / +0.013 BA; −0.019 / −0.013 specificity |
| SM-H6 NEW B40 BA: J ≥ J_no_delta | **falsified (point estimate)** | −0.023 [−0.087, +0.042]; at B16 +0.025 |
| SM-H7 J vs G3, J vs ACTIVE_E1 | no expectation | NEW: J below both in BA, above both in log loss; OLD: J below ACTIVE_E1 (−0.015), above G3 |
| SM-H8 θ posterior SD < 0.35 at B40 everywhere | **supported** | 0.147–0.207 (NEW 0.155, OLD 0.172, POOLED 0.158) |
| SM-H9 numerics and leakage | **supported** | 240/240 J-family fits accepted (gradient ≤ 1e-11); corruption and leakage controls pass |

## 5. Interpretation (HYP)

1. **Continuous depth helps.** It helps decisively on OLD, where the label is nearly a depth threshold: +0.06 to +0.07 BA, and J nearly matches ACTIVE_E1. It helps marginally on POOLED. On NEW it improves ranking and probability quality (AUC, log loss, Brier) but not balanced accuracy at p ≥ 0.5.
2. **The NEW BA gap is a decision-rule problem as much as a model problem.**
   - About 91 % of NEW runs are positive, so a fixed probit model with a proper prior is calibrated to that rate. Its well-ranked negatives therefore still sit above 0.5.
   - ACTIVE_E1 classifies by a depth threshold rather than a calibrated probability. It reaches the best NEW BA (0.730), with the worst log loss (0.799).
   - POST-HOC (`MECHANISM_REPORT.md`): moving J's threshold to the paid-label prevalence, a train-only rule, raises its NEW B40 BA to 0.870. This is now tested prospectively in `exploratory/`.
3. **θ and δ.** Under the fixed priors, the threshold flexibility (J_fixed_theta) and the discrepancy (J_no_delta) change NEW results only within noise. The discrepancy does not carve out the fast-scan negatives.

## 6. Limitations
- **Data:** two repeats and 12 NEW negatives. The bootstrap is conditional on the stored fits and these splits.
- **Model:** fixed hyperparameters, whose four-input lengthscale (1.5) is an engineering prior, not a fitted value. It is a Laplace approximation (error measured in `MECHANISM_REPORT.md`).
- **Selection of A:** A was defined after the NEW labels had been inspected.
- **Scope:** q20 is an evaluation subset, not the physical boundary. No query-saving claim is possible from identical feature-only paths.
