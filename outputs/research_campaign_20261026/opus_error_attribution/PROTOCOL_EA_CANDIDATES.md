# EA stage 2: candidate, controls and DEV selection

Registered 2026-10-26, before any evaluation of the candidate.

## 1. Measured problem

From `diagnosis/DIAGNOSIS.md`:
- **HA_TREND's ML-II hyperparameters overfit at small and medium n.** At b = 8 / 12 / 16 / 24 / 40, a hyperparameter is at a bound in 100 / 100 / 95 / 75 / 45 % of the fits. The noise variance collapses to 1e-6 in 80 / 65 / 50 / 35 / 20 %.
- **With well-estimated hyperparameters the trend model is better at every budget.** The evaluator-only D2T oracle gives:

  | | early | late | b = 24 | b = 40 |
  |---|---|---|---|---|
  | D2T − HA_TREND | +0.0031 [+0.0022] | +0.0036 | +0.0056 | +0.0048 |
  | D2T − HA_LEAN | +0.0071 | +0.0020 | | |

  Its mid-budget loss is an estimation artefact.
- **The rest of the early gap** (+0.040 to the true-depth oracle) is an information limit of b paid depths. It is not a target.

## 2. Candidate C1: HA_TREND with MAP hyperparameters under a fixed weak hyperprior

**Depth model** (unchanged from HA_TREND):

  a(x) = θ z_h(x) + g(x) + ε,

with:
- θ ~ N(0, 3²), integrated (kernel term 3² z_h z_h');
- g ~ GP(0, s_f² k_Matérn-3/2(Z, Z'; ℓ_1..4)), where Z are the standardised log inputs;
- ε ~ N(0, s_n² w(q)), w = 1e4 for a short record;
- targets standardised on the good paid rows (`src.rc18_gp.GP`).

**Change.** The hyperparameters φ = (log s_f², log ℓ_1..4, log s_n²) are the posterior mode

  φ̂ = argmin_φ [ NLML(φ) + ½ Σ_k ((φ_k − m_k) / s_k)² ]

under independent normal hyperpriors on the log scale. These are fixed and are not tuned:

| hyperparameter | prior | meaning |
|---|---|---|
| log s_f² | N(0, 1.5²) | residual amplitude of the order of the standardised output scale, wide |
| log ℓ_k | N(0, 1²) | on standardised log inputs: variation on the scale of one input SD; 95 % range 0.14–7.1 |
| log s_n² | N(log 0.01, 1.5²) | noise SD ≈ 10 % of the output SD; 95 % range of the SD 2–50 % |

- Same bounds as `src.rc18_gp`.
- L-BFGS-B from two fixed starts: (0, 0, 0, 0, 0, log 0.1) = HA_TREND's start, and (0, 0, 0, 0, 0, log 0.01) = the prior mean. The lower objective is kept.

**Everything else exactly as HA_TREND:**
- honest K = 10 out-of-fold features (each fold fit has its own MAP);
- full fit at the evaluation rows;
- the HA_LEAN learned-regularisation classifier on [z_h, F];
- margin on the system's own probability;
- the same one-class rule and startup.

**Information used:** paid depths, record-quality flags and paid labels, plus public inputs. Nothing else.

**Learned parameters:**
- φ: 6 values, MAP for every fit;
- θ: integrated;
- the classifier's coefficients (Laplace) and its τ grid weights (evidence).

**Expected mechanism.**
- At b ≤ 24 the prior prevents noise collapse and boundary lengthscales, so depth predictions at unqueried inputs improve. That gives early gain on top of the trend.
- As n grows the likelihood dominates and φ̂ approaches ML-II. HA_TREND's mid-budget loss should then disappear.

**Disclosure.** The prior was chosen after the full-pool ML-II values of the trend GP had been seen (log s_f² −1.25; log ℓ (0.07, 0.42, 0.57, 2.56); log s_n² −6.07).
- The prior centres are generic (0, 0, log 0.01), not those values.
- The full-pool values lie within about 1 prior SD, except ℓ_ST (2.6 SD).
- Validation on new splits of the same pool cannot detect a prior that suits this pool by luck.

**Difference from earlier attempts:**

| earlier attempt | what it did | how C1 differs |
|---|---|---|
| RC20 "MAP lengthscales" (`FINAL_REPORT_RC20.md` §3) | lengthscale-only hyperprior on the constant-mean shared T/S upstream | C1 has priors on amplitude and noise too (the measured failure is noise collapse), uses the trend GP (where D2T shows the headroom) and is judged on BA endpoints. RC20 judged a remedy for coefficient attenuation in LL, with a null result. |
| RC21 residual, Astra local corrections, JDL J, PAC | change the model structure | C1 changes only the estimation of an existing model's hyperparameters |
| EL-2 E | weights two fixed ML-II models by label evidence | C1 fixes the estimation inside one model |

## 3. Mechanism controls

All are on the same paid data.

| control | definition | question |
|---|---|---|
| C1a | HA_LEAN-MAP: the constant-mean depth GP with the same hyperprior and starts | Is the gain specific to the trend model? |
| C1b | HA_TREND with the same two starts and NO prior (ML-II) | Is the gain from more optimiser starts (compute) rather than from the prior? |

**References:**
- A = HA_LEAN, D = HA_TREND, E = the EL-2 evidence mixture, all ML-II and recorded;
- D2T = the evaluator-only oracle (headroom).

## 4. DEV evaluation

- **Matched**: on the recorded HA_LEAN paths. A, D, E and the paid data are identical across systems.
- **Data:**
  - STD repeats 123–162: the EL-2 confirmation paths, DEV now, 40 clusters, 200 learners. They are disjoint from the diagnosis repeats 83–122.
  - K5 startups 33–40 and K4 startups 17–24, as robustness.
- Every budget 8..60.
- **Metrics:** those of `PROTOCOL_EL_OBJECTIVES.md` §4–6, plus "sustained" (attained and BA ≥ τ at EVERY budget from the confirmation to 60), log loss, Brier and CPU per step.

**Code checks before the run:**
- With the prior disabled and the single default start, C1's fit code must reproduce HA_TREND (= recorded D) bit-exactly.
- C1a's code with the prior disabled must reproduce HA_LEAN (= recorded A).

## 5. Rule for carrying a candidate to the forward validation

Fixed now. On DEV STD, individual learners, 40 clusters, the carried candidate X ∈ {C1, C1a} must satisfy:
1. ΔBA-AULC B8–B24 (X − A) with LCB > 0;
2. ΔBA-AULC B8–B24 (X − D) ≥ −0.001, i.e. it keeps the trend's early gain (applied to C1; for C1a, ≥ −0.002);
3. ΔBA-AULC late (B28–B60) (X − A) ≥ 0 as a point estimate, i.e. no late loss.

- If both pass, the larger early gain against A is carried.
- If C1 passes but does not beat C1b early (C1 − C1b ≤ 0), the mechanism is "more starts". C1b is then carried instead, and the claim is narrowed accordingly.
- If neither passes, no new model is validated and the DEV result is reported.

## 6. Forward validation (registered separately before any fresh run)

| condition | fresh IDs | IDs used before |
|---|---|---|
| STD | repeats 163–202 | 1–162 |
| K5 | startups 41–48 | 1–40 |
| K4 | startups 25–32 | 1–24 |

- **Primary system:** "the carried model + margin on its own probabilities", against A.
- **Secondary:**
  - "HA_LEAN selects / carried model predicts" (matched path);
  - D and E against A, for reference.
- **Separate verdicts** for early learning, 0.93 savings and 0.95 reliability. Rules and harm limits are registered before the run.
