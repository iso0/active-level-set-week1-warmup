# OLD_DATA_RND_REPORT — development results on the 405 cases

All results below are **development evidence**: the 405 labels have been used by this project for a year and by this session repeatedly. Nothing here is confirmatory. Every experiment uses the repository's frozen protocol (100 outer runs = 20 repeats × 5 grouped folds; feature-only maximin B16 design; budgets 16–80; Fold-B1-q20 accuracy; paired repeat-block bootstrap with 10,000 draws). Intervals are two-sided 95%; "(a/b)" = number of the 20 repeat blocks with positive/negative paired difference. Files: `results/`.

## 1. Reproduction and harness

- Phase 1.14 M3-margin trajectory `w85__r01_f01` reproduced exactly (80/80 queries; q20 AULC 0.8920036764705884 vs committed 0.89200368) through the repository's own code (`core.py` wraps `src/week8_5…`, `…1_11…`, `…1_13…`).
- Committed per-budget predictions of Phase 1.13 (M3 on A0) and 1.14 (M3-margin) re-aggregated to window AULCs reproduce the committed contrasts: 16–80 +0.0021 [−0.0012, +0.0057]; 16–40 −0.0016 [−0.0074, +0.0040] (`results/p13_p14_window_aulc.csv`).

## 2. Ceiling and headroom (see RESEARCH_DIAGNOSIS §2–3)

Full-label (324 training labels) q20 ceiling: M3 0.8565; nine other model classes 0.72–0.84; configuration/TE covariates ±0.006; censored-depth model 0.853. M3-margin reaches 0.846 at B40, 0.856 at B60, 0.861 at B80. Headroom to the ceiling: 0.0309 (16–40 mean), 0.0122 (16–80), 0.0005 (41–80). Thirteen persistent exception cases account for the whole q20 ceiling (`results/diag_fulltrain_pointwise.csv`).

## 3. Same-path model contrasts (identical revealed labels: the committed M3-margin P1 paths; 100 runs; `results/samepath_models_metrics.csv.gz`, `results/samepath_T_variants.csv.gz`)

| Model on the P1 path | q20 acc B16 | B24 | B32 | B40 | B80 | AULC 16–40 (Δ vs M3) | AULC 16–80 (Δ vs M3) |
|---|---:|---:|---:|---:|---:|---:|---:|
| M3 (committed) | 0.786 | 0.817 | 0.834 | 0.846 | 0.861 | 0.8260 | 0.8446 |
| T, full-pool ML hyperparameters (c=7, s_u=0.41, ℓ_s=(1.7,30,30), s_β=1) | 0.717 | 0.792 | 0.834 | 0.842 | 0.859 | 0.8035 (−0.0225 [−0.0327, −0.0124]; 6/14) | 0.8339 (−0.0107 [−0.0186, −0.0028]) |
| T, s_u=0.8 | 0.715 | 0.784 | 0.842 | 0.843 | 0.861 | 0.8043 (−0.0217 [−0.0335, −0.0108]) | 0.8354 (−0.0092 [−0.0174, −0.0011]) |
| T, c=4, s_u=0.8 | 0.715 | 0.781 | 0.824 | 0.835 | 0.858 | 0.7936 (−0.0325) | 0.8261 (−0.0185) |
| T, ℓ_s=(1,5,5) | 0.719 | 0.784 | 0.822 | 0.812 | 0.831 | 0.7915 (−0.0346) | 0.8076 (−0.0370) |
| T, tight prior (s_u=0.05, s_β=0.1) | 0.764 | 0.809 | 0.817 | 0.822 | 0.829 | 0.8098 (−0.0163 [−0.0216, −0.0111]) | 0.8200 (−0.0246) |
| T, s_u=0.2, s_β=0.2 | 0.731 | 0.798 | 0.829 | 0.838 | 0.850 | 0.8055 (−0.0205) | 0.8310 (−0.0136) |
| T, c=12, s_u=0.2, s_β=0.3 | 0.727 | 0.781 | 0.820 | 0.840 | 0.858 | 0.7992 (−0.0269) | 0.8333 (−0.0113) |
| T, c=20, s_u=0.1, s_β=0.2 | 0.721 | 0.779 | 0.810 | 0.829 | 0.849 | 0.7924 (−0.0336) | 0.8234 (−0.0212) |
| Censored-depth level set (depth of revealed C points used; D*=100 µm) | 0.777 | 0.804 | 0.814 | 0.835 | 0.843 | 0.8074 (−0.0186 [−0.0257, −0.0113]; 3/17) | 0.8263 (−0.0183 [−0.0239, −0.0125]) |

Verdict: **no boundary-unit posterior and no auxiliary-output model beats M3 at any budget on identical labels.** Every T variant is worse by 0.02–0.07 at B16–B28 and converges to M3 only by B32–B48; the depth model is worse everywhere. The rigid near-hard physics step (M3 at B16 is H with a separable logistic) is the best early predictor on this pool. Model candidates T (all priors) and CDL are **killed**. The M3 label-noise-robust variant (M3R) was implemented (`m3r.py`) but its ML-II fit was too slow to complete on this machine within the session; it is not part of any decision.

## 4. Prospective acquisition replays (100 runs; `results/acq_F7_*`, analysis in `results/acq_F7_analysis.txt`)

Arms start from the shared B16 design. Acquisition posterior: T with full-pool ML hyperparameters. Evaluators: T on its own path, and **M3 on every path** (model held fixed, path varies).

Mean window AULC (q20 accuracy):

| Evaluator @ path | 16–32 | 16–40 | 16–48 | 16–80 |
|---|---:|---:|---:|---:|
| M3 @ committed M3-margin (P1) | 0.8196 | 0.8260 | 0.8314 | 0.8446 |
| M3 @ T-margin | 0.8175 | 0.8227 | 0.8275 | 0.8378 |
| M3 @ T-SUR-π (eq. 8) | 0.7915 | 0.7970 | 0.8008 | 0.8124 |
| M3 @ T-TV (eq. 9) | 0.8212 | 0.8285 | 0.8324 | 0.8405 |
| T @ T-margin | 0.7733 | 0.7918 | 0.8060 | 0.8325 |
| T @ T-SUR-π | 0.7428 | 0.7562 | 0.7682 | 0.7961 |
| T @ T-TV | 0.7616 | 0.7825 | 0.7991 | 0.8304 |
| M3 @ T-XSUR (exact coherent 0-1 SUR, Prop. 3; `results/acq_XSUR_*`) | 0.7938 | 0.7976 | 0.8014 | 0.8144 |
| T @ T-XSUR | 0.7531 | 0.7636 | 0.7736 | 0.8022 |

Paired contrasts (repeat-block bootstrap):

| Contrast | 16–32 | 16–40 | 16–48 | 16–80 |
|---|---|---|---|---|
| T@SUR − T@margin | −0.0304 [−0.0428, −0.0175] (5/15) | −0.0357 [−0.0505, −0.0214] (3/17) | −0.0378 | −0.0365 |
| M3@SUR − M3@T-margin | −0.0260 [−0.0346, −0.0173] (2/18) | −0.0257 [−0.0343, −0.0169] | −0.0267 | −0.0254 |
| T@TV − T@margin | −0.0117 [−0.0218, −0.0022] | −0.0093 [−0.0188, −0.0002] | −0.0069 [−0.0150, +0.0010] | −0.0022 [−0.0066, +0.0021] |
| **M3@TV − M3@T-margin** (same model, same acquisition posterior) | +0.0037 [−0.0030, +0.0109] (12/8) | **+0.0058 [+0.0002, +0.0117] (11/9)** | +0.0049 [+0.0002, +0.0096] (13/7) | +0.0027 [−0.0007, +0.0063] |
| **M3@TV − M3@committed margin (P1)** (the incumbent) | +0.0016 [−0.0051, +0.0078] (11/9) | +0.0025 [−0.0032, +0.0080] (12/8) | +0.0010 [−0.0042, +0.0061] | −0.0041 [−0.0080, −0.0002] (8/12) |
| M3@T-margin − M3@P1 | −0.0021 | −0.0034 [−0.0093, +0.0027] | −0.0039 | −0.0068 [−0.0101, −0.0035] |
| **M3@XSUR − M3@P1** (exact Bayes-optimal transductive rule vs incumbent) | −0.0258 [−0.0383, −0.0140] (4/16) | **−0.0284 [−0.0405, −0.0173] (4/16)** | −0.0299 | −0.0303 [−0.0403, −0.0209] (1/19) |
| M3@XSUR − M3@T-margin | −0.0237 | −0.0250 [−0.0348, −0.0160] (2/18) | −0.0260 | −0.0234 |
| T@XSUR − T@T-margin | −0.0201 | −0.0282 [−0.0430, −0.0146] (5/15) | −0.0324 | −0.0304 |

Ranking novelty of the acquisitions relative to T-margin on the same states (per step; early = B16–39):

| Acquisition | same top-1 as margin | Spearman vs margin | top-5 overlap | selected in physical band | selected KH (retrospective) | path Jaccard vs T-margin B40 / B80 |
|---|---:|---:|---:|---:|---:|---:|
| T-margin | 1 | 1 | 1 | 0.943 (early) / 0.793 (all) | 0.484 / 0.425 | — |
| T-SUR-π | 0.075 | 0.746 | 0.180 | 0.522 / 0.520 | 0.283 / 0.281 | 0.433 / 0.537 |
| T-TV | 0.045 | 0.965 | 0.181 | 0.850 / 0.744 | 0.429 / 0.397 | 0.550 / 0.862 |
| T-XSUR (exact) | 0.077 | 0.781 | 0.207 | 0.510 / 0.591 | 0.260 / 0.308 | 0.435 / 0.661 |

(T-margin vs the committed M3-margin path: Jaccard 0.626 at B40, 0.832 at B80.) q20 KH recall at B40 under M3: P1 0.749, T-margin path 0.734, T-SUR path 0.718, **T-TV path 0.768**.

Exact coherent SUR (XSUR). Because eq. (8) with the moment update (7) is not martingale-coherent (MATHEMATICAL_DEVELOPMENT Prop. 2c), the exact one-step Bayes-optimal rule for the finite-pool latent-set 0-1 risk was implemented with bivariate-normal orthant probabilities (Prop. 3; Owen's T, validated to 2·10⁻¹⁶; flip identity verified numerically) and replayed on all 100 runs. Result: **the exact Bayes-optimal transductive rule is dominated by plain margin by 0.028 AULC (16–40) and by 0.030 (16–80)**; it selects candidates with 49 flippable reference decisions per early step (margin's choice: 19) at p ≈ 0.37, half of them outside the physical band. The flips are model-expected, not real: the 16–40-label posterior is not calibrated in sparsely sampled contexts, so the expected error reduction is realised in the model's own risk and not on held-out near-boundary rows. Margin is robust precisely because it only trusts the posterior at the data-anchored decision boundary.

Mechanism of the moment-matched SUR failure (verified against exact hypothetical refits at one B24 state; approximation error of eq. 7 ≤ 30% of the exact refit reduction): the pool-uniform latent-set risk is dominated by out-of-band candidates with p ≈ 0.25–0.4 under the over-dispersed context prior; a Conduction outcome there removes much pool-wide risk, so SUR spends half of its queries outside the physical band (0.52 vs 0.94 for margin). The endpoint measures accuracy on rows nearest opposite-label neighbours in the dense region, which SUR does not visit. This is an objective/endpoint misalignment, not an implementation error.

## 5. Falsified / killed candidates

| Candidate | Killed by | Evidence |
|---|---|---|
| T as predictive model (any of 9 prior settings) | same-path early accuracy | −0.016 … −0.045 AULC 16–40 vs M3, 1–6/20 positive blocks |
| CDL censored-depth model (auxiliary output) | ceiling and same-path | ceiling 0.853 ≤ M3; −0.019 AULC in every window |
| T-SUR-π (finite-pool latent-set risk) | prospective replay | −0.026 (M3 evaluator), −0.036 (T evaluator), 2–5/20 positive blocks |
| T-TV as an acquisition for the T model | prospective replay | −0.009 [−0.019, −0.000] at 16–40 |
| T-XSUR, exact coherent one-step Bayes-optimal 0-1 rule (Prop. 3) | prospective replay | −0.028 [−0.041, −0.017] vs M3-margin at 16–40; 4/20 positive blocks |
| p-variant SUR (eq. 8 with q=p) | ranking identical in character to SUR-π on inspected states (top candidates out of band); not replayed | — |
| Hard/soft monotone propagation, repulsion, residual mixtures, PA-TVR, FAST-SUR, exact p(1−p) SUR, physics-refit SUR | committed Phases 1.15A–1.19B | see RESEARCH_DIAGNOSIS §1 |

## 6. The single surviving configuration

**M3 as the predictive model, queries chosen by the expected threshold-variance reduction (eq. 9) computed under a frozen auxiliary threshold-surface posterior** ("M3 + TV"). It is the only configuration with a positive early-window contrast against its own same-posterior margin control (+0.0058 [+0.0002, +0.0117] at 16–40) and a non-negative one against the incumbent M3-margin (+0.0025 [−0.0032, +0.0080]); it also raises B40 q20 KH recall (0.768 vs 0.749/0.734), the failure mode recorded in Phase 1.14. Against the frozen success rule of the external protocol (mean ≥ +0.01 and lower bound > 0 on AULC 16–40) it would **fail on the old pool**. Its ranking is distinct from margin (top-5 overlap 0.18, Jaccard 0.55 at B40) for a mechanistic reason (§MATHEMATICAL_DEVELOPMENT R4: leverage along VX where τ is unresolved), and the effect is confined to the window where headroom exists, as the mechanism predicts.

Sensitivity of this result to the auxiliary posterior's prior (s_u = 0.2 instead of 0.41) and the test-label oracle bound on what any acquisition could gain in the early window are reported in §7 (filled in from `results/acq_TIGHT_analysis.txt` and `results/oracle_greedy_metrics.csv.gz`).

## 7. Prior sensitivity of M3 + TV, and the test-label oracle bound

**Prior sensitivity** (`results/acq_TIGHT_analysis.txt`; auxiliary posterior with s_u = 0.2 instead of the full-pool ML value 0.41; 100 runs):

| Contrast (M3 evaluator) | 16–32 | 16–40 | 16–48 | 16–80 |
|---|---|---|---|---|
| TV − T-margin (same posterior) | +0.0038 [−0.0034, +0.0116] | +0.0041 [−0.0016, +0.0103] (11/9) | +0.0028 | +0.0006 |
| TV − committed M3-margin | −0.0020 [−0.0087, +0.0048] | −0.0037 [−0.0101, +0.0028] (9/11) | −0.0059 | −0.0059 [−0.0097, −0.0022] |

With the tighter prior the effect against the same-posterior control is unresolved and the contrast against the incumbent is slightly negative. The M3 + TV signal of §6 is therefore **weak and prior-dependent**; it survives only as the single non-redundant, non-harmful acquisition on this pool, not as a supported gain.

**Exact SUR with the tight prior** (`results/acq_XSURT_analysis.txt`): M3@XSUR − M3@P1 = −0.0111 [−0.0172, −0.0046] at 16–40 (3/17). As the acquisition posterior is concentrated, the exact Bayes-optimal transductive rule approaches margin from below (band rate 0.89, ρ 0.93, flips 11.5 vs 6.9) and never overtakes it.

**Test-label greedy oracle** (`results/oracle_analysis.txt`; 8 runs; at each step B16–B39 the candidate whose *true* label most increases held-out q20 accuracy is queried; margin thereafter). This uses evaluation labels and is a diagnostic upper bound only:

| | 16–32 | 16–40 | 16–48 | 16–80 |
|---|---:|---:|---:|---:|
| oracle | 0.9203 | 0.9249 | 0.9192 | 0.8932 |
| committed M3-margin (same 8 runs) | 0.8199 | 0.8298 | 0.8342 | 0.8483 |
| difference | +0.100 [+0.079, +0.123] | +0.095 [+0.078, +0.114] | +0.085 | +0.045 |

Checkpoints: oracle 0.919 at B20, 0.934 at B24–36, 0.941 at B40, then **0.875 at B48–80 once margin resumes** (margin at the same budgets: 0.809, 0.816–0.868, 0.846, 0.846–0.875). Two facts follow. (i) With the right four to eight labels, M3 scores 0.93 on the near-boundary held-out rows — *above* its 324-label ceiling of 0.8565: the q20 endpoint is dominated by *which* labels are in the training set, with a selection sensitivity of ≈ ±0.1, twenty times the size of any policy contrast measured in this project. (ii) The subsequent decline shows that adding margin-selected labels *lowers* q20 accuracy from the oracle state: some queried labels (the exception cases and their conflicts) actively poison neighbouring predictions under M3's smooth likelihood. The oracle exploits the fact that exceptions are locally clustered (late-onset KH of the old campaign): a training set that contains the right cluster members makes M3 predict the test members of the cluster correctly; the full training set, dominated by their C neighbours, does not. This is not attainable without evaluation labels, but it identifies the only model-side mechanism with large headroom on this benchmark: a likelihood that can *discount* conflicting labels locally (a label-noise-robust or locally nonstationary discrepancy) rather than a different acquisition. The label-noise-robust variant M3R (`code/rnd/m3r.py`) is the recommended follow-up test; it was implemented but its ML-II fit could not be completed within this session.
