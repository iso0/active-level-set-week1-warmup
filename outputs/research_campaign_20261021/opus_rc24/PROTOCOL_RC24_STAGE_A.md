# RC24 Stage A protocol: strong comparisons for the RC23 learner

Registered 2026-10-21, before any Stage A outcome. Fresh repeats 59–66 have never been run.

Every rule below is implemented in frozen code:
- `src/rc24_models.py` (constructions);
- `src/rc24_jobs.py` (units);
- `src/rc24_eval.py` (metrics, decisions);
- `src/rc24_correction.py` (explicit-status rules).

The freeze manifest is `freeze/RC24_STAGE_A_MANIFEST.json`. Workers refuse to run if any listed file has changed.

## 1. Programme frame

- **Owner instruction:** 2026-10-21, about 20:30 UTC (RC24).
- **Window:** one 48-hour window, from t0 = 2026-10-21T20:32:31Z to deadline 2026-10-23T20:32:31Z. It is not restarted between stages.
- **CPU authorisation:** all local cores. It is recorded in the coordination record `POOL_PLAN.json` under `capacity_history`.
- **Host:** i5-10300H, 4 physical / 8 logical cores, 31.8 GB RAM.
- **Worker layout:** fixed by the timing trial (`timing/TIMING.json`).
  - The 8-repetition workload gave these rates (workloads per minute):

    | layout | rate |
    |---|---|
    | 1 × 1 | 18.9 |
    | 2 × 1 | 34.7 |
    | 4 × 1 | 56.2 |
    | 6 × 1 | **63.7** |
    | 8 × 1 | 61.4 |
    | 4 × 2 | 51.6 |
    | 2 × 4 | 28.8 |

  - The chosen layout is **6 workers with 1 BLAS/OpenMP thread each**.
- **Queue:** `src/rc24_runner.ps1`, a copy of the RC23 runner. It has a numeric capacity rule: total leaf processes ≤ the coordination capacity of 8. It is detached through `src/rc24_start_runner.ps1` and supervised by `src/rc24_supervisor.ps1`. Units are checkpointed atomically and claimed with O_EXCL locks.
- **Not in scope:** paid cloud, physical simulator jobs, C4, real-data Stage A, main merge, external messages, and Astra's files.

## 2. Before Stage A: correction of the RC23 decision rule (done, dated 2026-10-21)

The defect is in `src/rc23_eval.py::decide`. It accepted the failing verdict "NON-INFERIORITY NOT SHOWN" (string prefix), an INCOMPLETE spend, and missing robustness conditions.

The frozen file is not edited. The correction is in `src/rc24_correction.py`: explicit PASS / FAIL / INCOMPLETE statuses computed from numbers.

**Recomputation from the saved RC23 tables (no GP refit):**
- D1 is reproduced. 26 recorded numbers were checked; the maximum difference is 4e-17.
- HA_LEAN and HA_LR both PASS every component.

**Negative controls:**
- Under the old rule, four synthetic failing or incomplete inputs reach D1: failing non-inferiority, n = 1, missing spend, and a missing condition.
- Under the corrected rule, none of them reaches D1.
- On real data, HA_LEAN − HONLY_LR B8–B24 non-inferiority has a lower bound of −0.0117. The corrected rule marks it FAIL; the old prefix test accepted that component.
- Output: `correction/RC24_DECISION_CORRECTION.json`.

**Direct witness** (`correction/RC24_PHR_NRMAP_WITNESS.json`). On a recorded state (repeat 35, fold 1, budget 24), a channel is removed from every paid run:
- PHR_NRMAP raises `ValueError` ("array must not contain infs or NaNs") for T absent, S absent and both absent.
- On the control state, PHR_NRMAP is finite.
- HA_LEAN and HONLY_LR are unchanged bit for bit.
- HA_LR is recorded separately: it stays finite but changes by up to 0.44.

The erratum is `../opus_rc23/ERRATUM_RC23_20261021.md`.

## 3. Data and information contract (unchanged from RC19–RC23)

- **Pool:** one pool of 541 runs. OLD/NEW is provenance only: it never routes a model and is never a feature.
- **Splits:** seeded 5-fold splits [1919, r].
- **Startup:** the 8-point label-free maximin startup is paid and counted. The one-class rule applies.
- **Budgets:** 8 to 60, one query per step. Existing outputs of a simulation carry one purchase cost.
- **Information:** learning, normalisation of outcomes, feature selection, calibration and acquisition use only paid outcomes (`src.rc19_pool.Reveal`). Public inputs x = (P, VX, LS, ST) may be standardised on the candidate pool, as in `rc19_pool.zstd`. Test outcomes, region, short-K and q20 memberships are evaluator-only.

## 4. Arms (own query; fresh repeats 59–66 × 5 folds = 40 tasks each)

| arm | model | acquisition |
|---|---|---|
| HA_LEAN_MARGIN (reference, RC23 D1) | learned-regularisation Laplace classifier on [z_h, honest CF predicted log depth]; depth-only SHQ upstream | margin −\|p − 0.5\| |
| HONLY_MARGIN | the same classifier on z_h only | margin |
| M3_MARGIN | faithful historical M3 (below) | margin |
| E1S | Week 18 E1: depth GP + depth threshold from the paid depth–label pairs; the probability reported is E1CAL (paid-only honest calibration map); E1RAW is recorded too | straddle on E1's depth latent (unchanged RC19B/RC22 code, K = 10) |
| G3_MARGIN | Week 18 G3 direct ARD GP classifier | margin |
| HA_LEAN_STRADDLE | HA_LEAN probabilities | straddle 1.96 s − \|η\| (below) |

**M3 (faithful).** M3 is ported verbatim from sibling repository commit 25520785 (Phase 1.11 / 1.13).

- **Physics mean:** logistic regression with C = 1e6 on log h standardised on the paid rows. It is frozen per state.
- **Residual:** Laplace GPC on StandardScaler(raw P, VX, LS, ST), fitted on the task's candidate-pool inputs. Historically this was the outer training pool, also public.
- **Kernel and fit:**
  - ConstantKernel(0.09, (0.05², 1.0²)) × Matérn-3/2 ARD, lengthscales initialised at 1 with bounds (0.01, 100);
  - L-BFGS-B, no restart;
  - Williams–Barber predictive.
- **Parity:** acceptance T1 shows bit-identical probabilities against the historical code run unchanged (8 states, max |Δp| = 0).
- **Disclosed historical properties, not corrected in M3:**
  - The h mean is practically unregularised. The B8 slope is 29.3 on standardised log h at repeat 35 fold 1.
  - The residual amplitude is capped at SD ≤ 1, and the B8 SD sits at its lower bound 0.05.
- **Corrected control:** M3_C1 is M3 with C = 1. It is a renamed control in the matched evaluation only, never called M3. h-only does not replace M3.

**HA_LEAN straddle (defined before results).**
- **Latent score:** η(x) = logit p̄(x), where p̄ is the HA_LEAN probability. The boundary is η = 0, exactly HA_LEAN's decision boundary.
- **Uncertainty:**

  s²(x) = Σ_g w_g [v_g(x) + σ²(x) E_g[w_A²]] + Σ_g w_g (m_g − m̄)²

  It has three separated sources:
  - Laplace classifier variance given the plug-in feature, v_g;
  - depth-predictive uncertainty propagated through the depth coefficient. Only the excess over the honest out-of-fold error level is used: σ² = max(0, v_A + q − mse_oof) / sd_F². The in-distribution part was already absorbed by the reduced-form classifier, so it is not counted twice;
  - the spread of the grid configurations.
- **Exactness:** the formula is exact for a Gaussian feature.
- **Monte Carlo validation (T2):** 360 rows; median relative variance error 0.5 %, maximum 2.3 %. The depth term is up to 86 % of the variance. The deliberately doubled variance FAILs.
- **Discriminability audit:**
  - the share of steps whose straddle choice differs from the margin choice on the same state;
  - the share with a numerically indistinguishable top-2 gap (≤ 1e-9 × score range).
  - A straddle arm that only reproduces margin, or that chooses between numerically identical candidates, is not counted as a success.

**Matched (cross-path) evaluation (a-match).**
- On each of the 6 × 40 own paths, every construction is evaluated at the path's paid prefixes, budgets 8–60 step 4: HA_LEAN, HONLY_LR, M3, M3_C1, E1RAW, E1CAL and G3.
- Same paid samples means same information; it does not mean the same path.

## 5. Metrics and pre-registered decisions (src/rc24_eval.py)

**Primary metrics.**
- Fold-pooled BA-AULC over B8–B24 and B8–B60, paired by repeat (n = 8).
- Sensitivity and specificity AULC.
- BA targets 0.80 / 0.90 / 0.93 / 0.95: first budget, confirmation at b and b + 4, sustained share, censoring, and the paired spend. The observed both-attained difference is kept apart from the restricted score (censored = 61).
- Individual-learner metrics are reported separately.

**Secondary metrics.**
- Log loss, Brier score, AUC, q20 BA, compute (CPU per step).
- The hard group (evaluator-only): recall on the 10 NEW short-Keyhole originals, specificity on the 12 NEW conduction runs, the hard-group BA, and pooled short-K recall (22 runs).
- The oracle-threshold BA, as a non-deployable calibration diagnostic.

**Verdict and status rules.**
- **BA verdict:** margin 0.020 in the good direction in ≥ 7/8 repeats → BETTER / WORSE / NOT DIFFERENT (RC22 rule).
- **Non-inferiority:** one-sided 95 % t lower bound ≥ −0.010 → PASS / FAIL / INCOMPLETE (corrected rule).
- **Spend:** FEWER / MORE when the mean is ≥ 2 sims, in ≥ 6/8 repeats, with no extra censoring.

**Q1 — Is h alone sufficient?** "H-ONLY SUFFICIENT" requires all of the following:
- HONLY_MARGIN − HA_LEAN_MARGIN non-inferiority PASS in both windows;
- spend to BA ≥ 0.95 PASS (not MORE, complete);
- HONLY attains BA ≥ 0.95 in at least (HA_LEAN's attainers − 1) repeats.

Otherwise the answer is NOT SUFFICIENT, or INCOMPLETE if a component is incomplete.

**Q2 — Are M3 or E1 similar or better?** For M3_MARGIN and for E1S (E1CAL), each against HA_LEAN_MARGIN:
- BETTER: a BETTER BA verdict in a window and no WORSE in the other;
- WORSE: any WORSE verdict;
- SIMILAR: non-inferiority PASS in both windows;
- otherwise: NON-INFERIORITY NOT SHOWN.

The same labels are reported for G3_MARGIN.

**Q3 — Margin vs straddle on HA_LEAN.** HA_LEAN_STRADDLE gets the same Q2-type label against HA_LEAN_MARGIN, together with the discriminability audit.

**Q4 — Model, path or calibration?** For each comparator X, a 2 × 2 table over model {X, HA_LEAN} × path {X's own path, HA_LEAN's path} on the matched matrix (BA-AULC on the step-4 grid). It reports:
- the total own-query difference;
- model effects on each path;
- path effects for each model;
- the interaction (model effect on X's path − model effect on HA_LEAN's path).

Calibration is reported on the same predictions:
- AUC, which is threshold-free;
- the oracle-threshold BA minus BA at 0.5, a non-deployable diagnostic;
- E1RAW vs E1CAL, the paid-only calibration map on the same path.

**Hard region (§4 of the instruction).**
- Values at B60 and B40, per arm and per construction on the matched matrix.
- Check of the owner's figures on the RC23 h-std records (repeats 51–58).

Nothing is changed after outcomes. Thresholds, margins, windows, targets and memberships are fixed here.

## 6. What Stage A does not claim

- Stage A is DEV evidence on one simulator pool.
- No stopping rule is claimed.
- A NOT DIFFERENT verdict is not equivalence.
- M3_C1 and the oracle-threshold BA are controls and diagnostics, not candidates.
