# RC19B — RC19 continuation: an honest physical-response Keyhole classifier and the spike-duration bottleneck (Opus; frozen before any final run)

**Status:** FROZEN by `final/RC19B_FINAL_MANIFEST.json` (SHA-256 of the code, the data manifest and this protocol), committed and pushed before any final repeat runs.
- Every final worker refuses to start if a frozen hash changed (`src/rc19b_final.check`, called by `src/rc19b_jobs.work` for every `b-final-*` job).
- **The freeze includes the evaluation, report and export code:** `src/rc19b_keyhole_eval.py`, `src/rc19b_duration_eval.py`, `src/rc19b_report.py` (every final table, every pre-declared verdict, the float32 exports and their acceptance check, compute cost) and `src/rc19b_repair.py`, plus the RC19 evaluator `src/rc19_eval.py` they call.
- **Not frozen (presentation only):** `src/rc19b_viewer.py`. Its numbers are refits of the frozen learners and are checked against the recorded predictions on the page itself.
- RC19 itself is not re-labelled: its report, export, figures and viewer were written after its runs (erratum E). Only RC19B is runtime-frozen in this way.

**Owner instruction:** 2026-10-19, "Opus — RC19 continuation: improve the pooled learner and prove where the gain comes from".

**Budget:** this continues the research campaign started 2026-10-18 08:41:20 UTC; deadline 2026-10-20 08:41:20 UTC (unchanged; no later authorisation is recorded). Opus uses 2 threads, Astra keeps her 2 (her study, workspace, code and allocation untouched).

**Evidence label: DEV.** All 541 simulations were inspected in earlier weeks. New splits are new partitions of the same runs; repeats and folds are correlated, not independent physical replications.
- No new simulator jobs, paid cloud, C4, real-data Stage A, main merge or external messages. BA_RISK stays cancelled. C3's decision stands.

## 1. Repairs done first (from caches; no learner refitted)

Dated erratum `opus_pooled/ERRATUM_RC19_20261019.md`; tables in `opus_rc19b/repair/`; ledger row RC19B-REPAIR.
- **A** first qualifying budget and confirmation spend (b + 4) reported separately.
- **B** float32 re-export of every RC19 final prediction (`opus_rc19b/export/`), acceptance PASS on every metric cell.
- **C** RC19's "cross-fitted" PHYSCF is a closed-form leave-one-out with full-fit hyperparameters, an approximation (now ATSAPPROX).
- **D** joint 8-output completion reported for every arm.
- No RC19 verdict changed.

## 2. Questions

- **K1 (primary).** At equal total revealed simulations, does an honestly cross-fitted physical-response classifier (ATSCF) give better Keyhole probabilities than E1 with an honest small-sample probability map (E1CAL)?
- **K2.** Do the temperature and spike-ratio predictions add information beyond predicted depth (ATSCF vs DEPTHCF)?
- **K3.** How much is probability mapping alone (E1CAL vs E1RAW; DEPTHCF vs E1CAL)?
- **K4.** Decision quality: BA, both recalls, confirmation spend to BA ≥ 0.93, censoring.
- **K5.** Honest construction vs RC19's approximation (ATSCF vs ATSAPPROX); continuity of RC19 primary C (ATSAPPROX + margin vs E1 + straddle).
- **D1.** Does the two-part (hurdle) spike-duration model predict duration better than the arm's own duration GP on the same paths?
- **D2.** Does it change joint 8-output completion by B80?
- **D3.** Does bottleneck-aware acquisition (MOIVRB) reduce joint spend relative to SHQ + RANDOM, the RC19 joint leader?

## 3. Information contract (unchanged from RC19, plus cross-fitting rules)

- `src/rc19_pool.Reveal` is the only route from hidden outcomes to a learner. The 8-point label-free maximin startup is paid and counted; one query = one simulation; missing channels and short records keep their cost; refit after every query.
- No OLD/NEW routing, archive pretraining, campaign-specific threshold, acquisition or feature. Batch identity is used only by the evaluator (fast-scan corner diagnostic).
- **Cross-fitting (ATSCF, DEPTHCF, E1CAL):** the paid runs are split by query order, fold of the j-th paid run = j mod K, K = min(CF_K, n). For each fold, the upstream GP fit, its hyperparameters, its shared lengthscales, its normalisation and E1's depth threshold are refitted without that fold. Held-out runs never enter any of this.
- **Calibration map (E1CAL):** logit p = a + c · logit p_E1, MAP with a ~ N(0, 1²), c ~ N(1, 0.5²), fitted on the honest out-of-fold E1 probabilities of the paid runs only.
- Every construction predicts the paid class rate until both classes are revealed; such queries follow the label-free path and are counted.
- **Validation before the freeze** (`RC19B_VALIDATION.json` K = 5, `RC19B_VALIDATION_FINAL.json` K = CF_K):
  - honesty: changing a paid run's own outcomes never changes its own out-of-fold prediction;
  - shadow: randomising every never-paid outcome leaves every final arm's path and predictions identical;
  - recording every construction on a path leaves the path and the arm's own predictions identical;
  - the bottleneck-aware regression arm with the hurdle recorded passes the same shadow test.

## 4. Development stage (seen data; it chooses the design and supports no final claim)

All on the RC19 final repeats 3–10, recomputing constructions on the **same paid prefixes** of existing RC19 trajectories.

**Keyhole, K = 5** (`KEYHOLE_REPLAY.md`):
- T/S beyond depth: ATSCF − DEPTHCF log loss lower in 8/8 on every path set.
- ATSCF − E1CAL: log loss −0.030 to −0.073 (8/8); BA within ±0.004.
- Honest K = 5 is worse than the RC19 approximation in 8/8 repeats.

**Fold-size factor** (mechanism-led one-factor test; `KEYHOLE_REPLAY_K.md`). Label-free paths, ATSCF LL-AULC:

| K | ATSCF LL-AULC |
|---|---|
| 5 | 0.1911 |
| 10 | 0.1870 |
| exact refit-LOO | 0.1863 |
| ATSAPPROX (RC19 approximation) | 0.1772 |

- Larger training folds remove about a third of the gap to the approximation.
- The rest (+0.009, 0/8) comes from refitting hyperparameters and normalisation per fold, which the approximation does not do.

**Rule K** (ledger RC19B-SELECT-RULES, fixed before reading) gives **CF_K = 10**: LOO is lowest, K = 10 is within 0.002, so the cheaper K = 10 is used.

**Duration** (`DURATION_REPLAY.md`):
- No hurdle variant beats the arm's own duration GP in duration R²-AULC:

  | Arm | own GP | QS_RAW | QG3_RAW |
  |---|---|---|---|
  | M0Q + MOIVR | 0.510 | 0.471 | 0.469 |
  | SHQ + MOIVR | 0.534 | 0.490 | 0.487 |
  | SHQ + RANDOM | 0.528 | 0.443 | 0.444 |

  The LOG variants are unstable.
- Joint completion with QS_RAW: SHQ + MOIVR 4/8 (GP 1/8), M0Q + MOIVR 4/8 (GP 5/8), SHQ + RANDOM 1/8 (GP 7/8).
- **Rule V** gives **QS_RAW**: 0.468 vs QG3_RAW 0.467 is within 0.005; joint completions are tied 9 vs 9; QS is preferred over QG3.
- The final therefore tests a hurdle that development does not favour. This is reported as it comes out.

**Descriptive ceiling** (full data, not a learner): an isotonic map from the TRUE spike log-ratio to duration reaches R² 0.59 (20 training runs) to 0.75 (400). Duration is noisy even given the spike strength, so the 0.60 level is near what is achievable around B60–B80.

## 5. Final design (fresh DEV repeats 11–18, never run before this freeze)

**Splits:** seeded random 5-fold partition per repeat (seed [1919, r]), the RC19 rule. 8 repeats × 5 folds; startup and seeds shared by the arms.

### Keyhole: job `b-final-label` (200 trajectories, B8 → B60, every budget recorded)

| arm | probability | acquisition |
|---|---|---|
| E1S → **E1RAW+straddle** and **E1CAL+straddle** (one path) | E1 / E1 + honest map (K = 10) | E1 straddle (1.96 σ − \|μ − u\|) |
| **ATSCF_MARGIN** | logistic on cross-fitted predicted (log A, T0 temperature, spike log-ratio), K = 10 | margin \|p − 0.5\| |
| **DEPTHCF_MARGIN** | logistic on cross-fitted predicted log depth, K = 10 | margin |
| **G3_MARGIN** | Week 18 GP classifier | margin |
| **ATSAPPROX_MARGIN** | RC19 PHYSCF_ATS (approximate LOO) | margin |

At B8, 12, …, 60, every construction is also recorded on each arm's own path. This gives an exploratory matched-path decomposition on fresh repeats.

**PRIMARY (K1):** ATSCF_MARGIN − E1CAL+straddle, **LL-AULC over B8–B60, lower is better, practical margin 0.02 nats**.
- **BETTER (DEV)** iff the mean paired difference ≤ −0.02 and the difference is negative in ≥ 7 of the 8 repeats.
- **WORSE** symmetrically; otherwise **NOT DIFFERENT**.

**Pre-declared secondary contrasts:** same rule, margins BA-AULC 0.02, LL-AULC 0.02, Brier-AULC 0.005.
- ATSCF_MARGIN − E1CAL+straddle
- ATSCF_MARGIN − E1RAW+straddle
- ATSCF_MARGIN − DEPTHCF_MARGIN (K2)
- DEPTHCF_MARGIN − E1CAL+straddle (K3)
- E1CAL+straddle − E1RAW+straddle (K3)
- ATSCF_MARGIN − ATSAPPROX_MARGIN (K5)
- ATSCF_MARGIN − G3_MARGIN
- ATSAPPROX_MARGIN − E1RAW+straddle (RC19 primary-C continuity)

**Also reported (no verdict):**
- BA, sensitivity and specificity curves; AUC.
- BA ≥ 0.93: first qualifying budget, confirmation spend b + 4, censoring at B60, paired spend differences.
- Reliability: calibration slope and intercept, ECE and calibration-in-the-large with SE over repeats; Wilson 95 % reliability bins.
- Fast-scan corner (NEW-batch conduction test runs, evaluator-only): recall and error counts.
- q20 boundary BA, short-K capture, compute seconds.

### Physical outputs: job `b-final-reg` (160 trajectories, B8 → B80, recorded every 4)

**Arms:**
- SHQ + RANDOM (reference; RC19 joint leader)
- M0Q + MOIVR
- SHQ + MOIVR
- SHQ + MOIVRB: MOIVR with output weights w_t = max(0.05, 1 − paid closed-form LOO-R²_t). The weights come from the learner's own paid data; no evaluation residual is used.

Every recorded budget also records the hurdle duration E[D | x] = q(x) · E[D | D > 0, x]:
- q is from the arm's own spike-ratio predictive and a threshold learned from the paid (S, 1[D > 0]) pairs;
- E[D | D > 0, x] is from an M0Q GP on the paid positive durations.

Zeros are kept; missing durations stay missing.

**Pre-declared contrasts** (fixed absolute targets of RC19: log A, KE, laser, temperature 0.85; spike ratio, etot, npart 0.80; spike duration 0.60):
- **D1:** per arm, HURDLE − own GP duration R²-AULC (B8–B80) on the same path. Margin 0.02, ≥ 7/8.
- **D2:** per arm, joint completion by B80 with the hurdle vs with the own GP duration.
  - **IMPROVED** iff ≥ 2 more of 8 repeats complete and none that completed is lost.
  - **WORSE** iff ≥ 2 fewer complete.
  - Otherwise **NO CLEAR CHANGE**.
- **D3:** joint confirmation spend of each arm − SHQ + RANDOM.
  - The arm's own GP duration is the acquisition contrast; the hurdle duration is secondary.
  - Censored = 84 (a lower bound of the true spend). Margin 4 simulations, ≥ 7/8.

**Also reported:**
- joint completion, spend per repeat, ever-qualified and censoring for every arm with both duration predictors;
- per-output completion;
- duration R², cov90, error on true zeros and on positive durations;
- MOIVRB weights.

Per-output savings are never multiplied by eight.

## 6. Outputs

- `report/KEYHOLE_FINAL.md`, `KEYHOLE_FINAL_DECOMPOSITION.md`, `DURATION_FINAL.md`, `COMPUTE_COST.md`, with their CSVs.
- `export_final/` float32 predictions (label; 8 outputs + hurdle) and `paths_final.csv.gz`. `EXPORT_ACCEPTANCE.json` recomputes every metric cell from the exports.
- Viewer: `viewer/single_learner_view.html`.
  - One learner (pre-declared: repeat 11, fold 1, each arm), refitted on its own paid prefix.
  - Grid over log P × log VX at a chosen LS slice with ST fixed; its paid runs and its own fold's held-out runs drawn separately.
  - Refit vs recorded difference shown on the page.
- RC19 view relabelled: `viewer/pooled_boundary_view_RC19_relabelled.html`.
- Narrative: `FINAL_REPORT_RC19B.md`.

## 7. Queue

Persistent runner `src/rc19_runner.ps1` (plan `opus_pooled/runner/PLAN.json`), jobs `b_final_label` and `b_final_reg` after the freeze commit:
- Opus share 2 leaf processes, every one single-threaded.
- Atomic launches under the coordination lock; Astra's processes are detected and never touched.
- The unit protocol (O_EXCL claims, atomic json.gz) records every failure and never retries it.
