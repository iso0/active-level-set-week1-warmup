# RC19B model definitions (version 2 of `opus_pooled/MODEL_DEFINITIONS_RC19.md`; dated 2026-10-19)

Every model learns from the **paid runs only**. Inputs are x = (P, VX, LS, ST); standardised log inputs use the candidate pool's input means and SDs, which are public.

**Changes from version 1:**
- "Cross-fitted PHYSCF" is renamed ATSAPPROX, because it is an approximation.
- New: honest cross-fitting (ATSCF, DEPTHCF), calibrated E1 (E1CAL), the spike-duration hurdle model and bottleneck-aware acquisition (MOIVRB).

## Notation

| symbol | meaning |
|---|---|
| L | paid runs, in query order; n = \|L\| |
| y_i | Keyhole label of a paid run (canonical) |
| A_i | active-window maximum depth (µm); log A is the depth output |
| T_i | T0-window median maximum temperature (K) |
| S_i | spike log-ratio log(p99.9 / median) of the maximum melt velocity in the active window |
| D_i | spike duration (µs): summed hold time of active rows with velocity > 2 × median; 0 = no such row, NaN = undefined |
| Φ | standard normal CDF |
| σ(z) | logistic function |

## Response models (unchanged; `src/rc18_campaign.fit_model`)

- **M0:** one GP per output; Matérn-3/2 ARD kernel on standardised log inputs; constant mean; ML-II hyperparameters; normalised targets.
- **M0Q:** M0 plus record quality. A paid run whose record ended before 0.95 × its own planned end time gets noise × 10⁴.
- **SHQ:** M0Q with ARD lengthscales shared by the chosen outputs. They are fitted jointly on the paid runs that have all of those outputs.

## Keyhole probability constructions (`src/rc19b_keyhole.py`)

**E1RAW (Week 18 E1):**
- a GP on log A gives μ_A(x), σ_A(x);
- a depth threshold u is learned from the paid (log A, y) pairs: the midpoint of the gap if the classes are separable, otherwise a 1-D logistic boundary;
- p(x) = Φ((μ_A(x) − u) / σ_A(x));
- acquisition (straddle): 1.96 σ_A − |μ_A − u|.

**E1CAL (calibrated E1):**
- p_cal = σ(a + c · logit p_E1(x));
- (a, c) is the MAP estimate with prior a ~ N(0, 1²), c ~ N(1, 0.5²), fitted on HONEST out-of-fold E1 probabilities of the paid runs. For each fold the depth GP, its normalisation and the threshold u are refitted without that fold;
- it uses the same path as E1RAW, because straddle does not depend on the map.

**Cross-fitting folds:**
- the j-th paid run is in fold j mod K, with K = min(CF_K, n);
- **CF_K = 10** in the final; 5 in the first development replay; exact LOO (K = n) as a development factor;
- a fold fit with fewer than 3 usable rows for an output returns that fold's training mean for the output (counted in the unit info).

**DEPTHCF and ATSCF (honest physical-response classifiers):**

1. For each fold k, fit the response model (M0Q for one output, SHQ for several) on the paid runs outside fold k. That fit has its own hyperparameters, its own shared lengthscales and its own normalisation. It predicts the outputs of the runs in fold k, giving out-of-fold features F_i.
2. Fit g = L2 logistic regression (C = 1) on the standardised F_i and the paid labels. The standardisation uses the out-of-fold features only.
3. Deploy: refit the same response model on ALL paid runs, predict the feature means at new x, standardise them with step 2's scaling and apply g.

- Features: DEPTHCF uses (log A); ATSCF uses (log A, T, S).
- Acquisition: margin, −|p − 0.5| on the candidates.

**ATSAPPROX (RC19's PHYSCF_ATS, historical control):**
- the same g, but its training features are closed-form leave-one-out predictions of ONE full-data fit;
- the hyperparameters and normalisation are estimated with the held-out run included, so the features are an approximation of cross-fitting;
- it remains deployable: it uses paid runs only and no test information.

**G3 (Week 18):** direct GP classifier on the labels (Laplace, ML-II). Acquisition: margin.

**One-class rule (all constructions):** until both classes are revealed among the usable paid runs, p = the paid class rate, and the next query follows the label-free maximin path. These queries are counted.

## Spike-duration hurdle (`src/rc19b_duration.py`)

E[D | x] = q(x) · m₊(x), where:
- q(x) = P(D > 0 | x);
- m₊(x) = E[D | D > 0, x].

**q(x), variant QS (final):**
- q(x) = Φ((μ_S(x) − c) / √v_S(x));
- (μ_S, v_S) is the arm's own spike-ratio predictive (mean and observation variance);
- c is the threshold learned from the paid (S, 1[D > 0]) pairs (E1-style rule).

**m₊(x), variant RAW (final):** an M0Q GP on the paid positive durations; m₊ = max(μ, 0).

**Development-only variants:**
- QG3: q from a G3 classifier on 1[D > 0];
- LOG: GP on log D, with E[D | +] = exp(μ + v/2) and v clipped at 1.

**Variance:** Var[D | x] = q · E[D² | +] − E[D | x]².

Zeros are kept. Missing (NaN) durations are neither zeros nor training rows; they still cost their query.

## Acquisitions for the physical outputs

- **RANDOM:** a uniform draw from the unpaid candidates (seeded).
- **MOIVR (RC19):** sum over outputs of the integrated variance reduction over the pool, each normalised by the output's paid variance.
- **MOIVRB (RC19B):** MOIVR with output weights w_t = max(0.05, 1 − LOO-R²_t).
  - LOO-R²_t is the closed-form leave-one-out R² of output t's own fitted GP on its paid training rows. It is a paid-data self-assessment; no held-out or evaluation residual is used.
  - Outputs the learner predicts worst (the bottleneck) get more weight.

## Endpoints (unchanged definitions; RC19B reports the spend explicitly)

- **first qualifying budget:** the first recorded b at the level;
- **confirmed pair:** the first b with the level at b and at b + 4;
- **confirmation spend:** b + 4, the total revealed simulations, startup included;
- **censored:** no confirmed pair by the horizon (B60 label, B80 outputs).

**Joint:** all 8 outputs at their fixed absolute R² targets at the same budget.
