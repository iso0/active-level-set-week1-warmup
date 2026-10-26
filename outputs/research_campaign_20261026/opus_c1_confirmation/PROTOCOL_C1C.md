# C1 confirmation (C1C): registered protocol

**Registered** 2026-10-26, before any new result, and frozen in two ways:
- the SHA-256 manifest `freeze/C1C_MANIFEST.json`;
- the registration commit, pushed to `joint-depth-label-dev`.

Every worker of a registered job verifies the manifest before its first unit.

## 0. Status before registration

- No new ID has been run, and no rule below was chosen from new data.
- All checks used old IDs only (results in `repro/`):
  - **EA units:** the recorded EA units `STD r163 f1` and `r197 f5`, L and X, recomputed with the frozen unit code. Every prediction and every paid ID matched bit-exactly (4/4, `REPRO_EA_UNITS.json`).
  - **Startup rules:** `src.rc22_common.startup_task` reproduces the RC22 startups of repeats 35–42 for RAND8 and LOCAL8 (80/80).
    - The check covers the first 8 paid IDs and every path-rule query of the one-class phases: 37 queries in 30 LOCAL8 one-class starts; RAND8 had no one-class start.
    - Result file: `REPRO_STARTUPS_RC22.json`.
  - **Prior scale 1:** the prior-scale control at scale 1 reproduces the recorded EA C1 bit-exactly; scales 0.5 and 2 differ, so the control is active (2/2, `REPRO_PRIOR_SCALE1.json`).
  - **Dry run:** the evaluation and export code was run on old EA data only (EA validation units 163–202 as a stand-in). It reproduces the recorded EA validation decision exactly (early +0.00556, 0.95 saving +2.005, CPU 1.19×), and its exports passed the independent recomputation.
- **Start state:**
  - HEAD = origin = `21a1c045`;
  - EA campaign CLOSED;
  - Astra campaign `astra_joint_local_20261026` ACTIVE, 3 workers, never touched.

## 1. The fixed recipe: C1 + margin, exactly as in EA

This is `src/ea_cand.py` SYSTEMS["C1"], unchanged and frozen. The equations:

**Inputs.**
- x = (P, VX, LS, ST).
- z = log inputs standardised with the candidate pool's mean and SD (public).
- h = standardised (log P − ½ log VX − 3/2 log LS), from pool statistics (`src.rc20_attr.hcol`).

**Depth model** (paid runs with a recorded depth only).
- Response: y = log A, standardised by the mean and SD of the good rows (w ≤ 100).
- Model: y(z) = θ·h(z) + f(z) + ε, with:
  - θ ~ N(0, 3²), integrated, so the covariance gains 9·h hᵀ;
  - f ~ GP(0, s_f² k_{3/2}(z, z′; ℓ_1..ℓ_4)), Matérn-3/2 ARD;
  - ε_i ~ N(0, s_n² w_i), where w_i = 10⁴ for a short record and 1 otherwise.
- Hyperparameters φ = (log s_f², log ℓ_1..4, log s_n²) by MAP:

  φ̂ = argmin_φ [ −log p(y | φ) + ½ Σ_k ((φ_k − m_k)/s_k)² ]

  - prior centres m = (0, 0, 0, 0, 0, log 0.01);
  - prior SDs s = (1.5, 1, 1, 1, 1, 1.5);
  - optimiser: L-BFGS-B within the box bounds of `src.rc18_gp`, from two starts (0, 0, 0, 0, 0, log 0.1) and m; the lower objective is kept.

**Honest stacking.**
- K = 10 folds of the paid set. The predicted depth F of a paid run comes from the model fitted without its fold.
- F of the test and candidate rows comes from the model fitted on all paid runs (`src.ea_diag2.cf_generic`).

**Classifier** (`src.rc22_common.phr_family`, feats = (0,), as HA_LEAN).
- Learned-regularisation Laplace logistic on the standardised [h, F].
- For every (τ_F, τ_h) ∈ {0.5, 1, 2, 4}², a Gaussian-prior logistic is fitted by Laplace. The weights are w_g ∝ the Laplace evidence.
- P(Keyhole | x) = Σ_g w_g σ(m_g(x)), plug-in. Decision threshold 0.5.

**One-class rule.** Until both classes are present among the paid runs with a usable depth:
- the prediction is the paid class rate;
- the next query is the next point of the task's label-free path.

**Selection (margin).** The next query is the unpaid pool point maximising −|P(Keyhole | x) − 0.5|.

**Reference: A = HA_LEAN + margin**, the thesis learner.
- The same, but with a constant-mean depth GP (no trend) under ML-II from one start (`src.rc23_common.run_arm(task, "HA_LEAN")`).
- Classifier, cross-fit, one-class rule and margin are identical.

**Known components.** The parts are known methods:
- GP regression with a linear trend;
- MAP hyperparameters under a fixed log-normal prior;
- stacking;
- Laplace logistic;
- uncertainty sampling.

C1 is an application of known components, not a new method (§7).

## 2. IDs

**Inventory.**
- The highest repeat ID in any recorded unit name is 202.
- Used before: STD repeats 1–202 (RC19–RC24 1–82, EL 83–162, EA 163–202).
- RAND8 / LOCAL8 startups: only repeat 1 (smoke) and repeats 35–42 (RC22).
- K5 startups 1–48 and K4 startups 1–32 (block conditions; not used here).

**New IDs.** None of them was used in any earlier evaluation or selection.

| condition | repeats × folds | learners | clusters | role |
|---|---|---|---|---|
| STD (maximin 8-point startup) | 203–282 × 5 | 400 | 80 | **main validation (verdict set)** |
| subgroup S1 | 203–242 | 200 | 40 | pre-defined, descriptive |
| subgroup S2 | 243–282 | 200 | 40 | pre-defined, descriptive |
| RAND8 (random 8-point startup) | 283–302 × 5 | 100 | 20 | startup robustness |
| LOCAL8 (clustered 8-point startup) | 303–322 × 5 | 100 | 20 | startup robustness |
| prior controls | DEV paths of 123–162 × 5 | 200 | 40 | control only; NOT new validation |

All are new splits or startups of the same 541 runs. They are pool evidence, not external validation.

## 3. Main validation

### 3.1 Arms and runs

Job `c1c-main`, 800 units (`src/c1c_fwd.py`, calling `src/ea_fwd.py` unit_L / unit_X unchanged).

| system | path | role |
|---|---|---|
| C1_own | C1 + margin, own path | PRIMARY |
| A_own | HA_LEAN + margin, own path | reference |
| D_on_A | HA_LEAN selects, previous HA_TREND (ML-II) predicts | strong early control |
| C1_on_A | HA_LEAN selects, C1 predicts | MAP correction against D on identical paid data (C1_on_A − D_on_A) |
| E_on_A | HA_LEAN selects, evidence mixture predicts | secondary, as in EA |
| A_on_C1 | C1's path, HA_LEAN predicts | decomposition only |

- All arms of a learner share the same 8 startup runs (counted), the same test fold and the budget 8..60.
- Each prediction uses only the first b paid runs of its own path.
- Cross predictions reuse the runs already opened on that path, so no extra simulation is counted.

### 3.2 Verdicts

Verdicts apply to the 80 repeats only, on individual learners. The uncertainty is one-sided 95 % t bounds over the 80 repeat clusters, because the folds of one repeat are not independent. Each verdict is also checked with a 10,000-resample cluster bootstrap (seed 2024).

**Unchanged from EA** (`PROTOCOL_EA_VALIDATION.md` §4, code `src.ea_fwd_eval.verdicts`):

| verdict | quantity (C1_own − A_own) | rule |
|---|---|---|
| V-EARLY | ΔBA-AULC B8–B24 | LCB > 0 → EARLY_GAIN_SHOWN; "+PRACTICAL" if mean ≥ 0.003; else NOT_SHOWN |
| V-0.93 | restricted-mean saving RMS_A − RMS_X | LCB > 0 → SAVING_SHOWN, "+PRACTICAL" if mean ≥ 1.0; LCB > −1.0 → NOT_WORSE; else NOT_SHOWN |
| V-0.95 reliability | Δattainment(0.95), Δkept(0.95) | RELIABLE if both LCB ≥ −0.05, else NOT_RELIABLE |
| 0.95 saving status | RMS saving at 0.95 | the V-0.93 statuses |
| LATE | ΔBA-AULC B28–B60 | LOSS_SHOWN if UCB < 0, else NO_LOSS_SHOWN |
| harm limits | ΔLL B8–B60, ΔBrier B8–B60, CPU per decision step | flagged if ΔLL > +0.030, ΔBrier > +0.010, or CPU > 3 × A |

**Ambiguities, resolved here before any result:**

1. **V-0.90.** The 0.90 target gets the V-0.93 statuses (added; EA only reported the 0.90 figures).
2. **LATE_PRESERVED.** This is a non-inferiority statement added beside LATE, which is unchanged.
   - PRESERVED_WITHIN_0.003 if LCB(ΔBA-AULC B28–B60) > −0.003; otherwise PRESERVATION_NOT_SHOWN.
   - The margin 0.003 is the PRACTICAL early threshold.
   - "NO_LOSS_SHOWN" (no loss detected) and "PRESERVED" (a loss larger than 0.003 excluded) are different statements and are reported separately.
3. **Replication.**
   - The early gain replicates if V-EARLY is EARLY_GAIN_SHOWN on the 80 repeats.
   - The 0.95 saving replicates if the 0.95 saving status is SAVING_SHOWN (LCB > 0) on the 80 repeats.
   - RELIABLE alone is not a replication of the saving.
4. **Meaning of RELIABLE.** It is a non-inferiority statement. With one-sided 95 % confidence, C1's rates of attaining and of keeping 0.95 are at most 5 points below A's.
   - It is not superiority.
   - It is not a per-run guarantee: individual runs can still miss or lose 0.95.
5. **Endpoints** (`src.el_eval.endpoints`, unchanged).
   - *First:* the first budget with BA ≥ τ.
   - *Confirmed:* the first b ≤ 56 with BA(b) ≥ τ and BA(b + 4) ≥ τ.
   - *Spend:* b + 4. It includes the 8 startup runs and the 4 confirmation queries.
   - *Attained:* a confirmed b exists.
   - *Kept:* attained and BA(60) ≥ τ. *Lost:* attained and BA(60) < τ.
   - *Above target at B60:* BA(60) ≥ τ, whether or not the target was attained.
   - *Sustained* (the EA definition, `src.ea_cand_eval.sustained`): attained, and BA ≥ τ at every budget from the confirmed b, the starting point, through 60.
6. **Restricted-mean spend.** RMS = mean of min(spend, 61), with a non-attaining learner counted as 61. A difference of two RMS values is the area between the two cumulative attainment curves up to b = 60. It is neither the true cost nor a lower bound on the true difference, and it is never presented as either.
7. **Descriptive savings.** No general saving is built by dropping non-attainers. The following are descriptive and always carry their denominators:
   - the both-attained conditional saving (a selected subset);
   - attainer-only means and medians;
   - the median spend with non-attainers counted as infinity ("not reached by half" when more than half do not attain).
8. **Pooled values** (the 5 folds of a repeat concatenated, with t bounds over clusters) are reported beside the individual values. They decide nothing.
9. **Multiplicity.** Several verdicts are tested, each at one-sided 95 %, without a multiplicity correction. Each verdict speaks only for its own use, and there is no combined winner.
   - A failure in one verdict does not erase a gain shown in another.
   - The early gain is never presented as a 0.95 superiority that was not shown.
10. **No early stop.** All 800 units are completed before any evaluation. No interim result is looked at, the sample size never changes, and no setting is tried.

### 3.3 Reported for the main set and both subgroups

| group | quantities |
|---|---|
| windows (individual, with pooled beside) | BA-AULC B8–B24, B8–B60, B28–B60, each with both recalls (Keyhole recall, conduction recall), log loss and Brier |
| budgets | BA at b = 8 / 12 / 16 / 24 / 40 / 60, with both recalls |
| per target (0.90 / 0.93 / 0.95), per system | attained / kept / lost / above target at B60 / sustained, with denominators; first and confirmed budgets (attainer means); spend (attainer mean and median); median with non-attainers = ∞; RMS; cumulative attainment at b = 16 / 24 / 40 / 60 |
| matched attainment table | both / C1 only / A only / neither, with the both-attained saving (cluster t) |
| saving contrasts | RMS saving with t bounds and bootstrap |
| other | the second-class cost of one-class starts (§4); CPU per decision step |
| pairs | C1_own − A_own, C1_on_A − A_own, D_on_A − A_own, E_on_A − A_own, C1_on_A − D_on_A, C1_own − D_on_A, C1_own − E_on_A, C1_own − A_on_C1, A_on_C1 − A_own, C1_own − C1_on_A |

The subgroups S1 / S2 get the same verdict labels, as descriptive information. Their agreement or disagreement is reported and never overrides the 80-repeat verdict.

### 3.4 Old vs new, side by side

These rows are computed with the same code and never pooled:
- EA DEV (C1 on A's recorded paths, 123–162);
- EA fresh validation (163–202);
- C1C main (203–282), with S1 and S2.

The earlier failures and opposite results stay in the table:
- DEV kept(0.95) −0.055 and the DEV carry-rule failure (late −0.0015);
- the EA K5 per-region geometry warning (−0.049);
- D and E NOT_ADOPTED (EL).

No new geometric split is made.

## 4. Startup robustness

**Startups.** Job `c1c-start`, 400 units: the same unit code, and the audited RC22 startup rules (`src.rc22_common.startup_task`). Neither looks at labels.
- **RAND8:** 8 pool points at random.
- **LOCAL8:** the 8 pool points nearest to one random pool point, a deliberately clustered start that is often one-class.
- Both continue with the greedy farthest-point label-free path.

**Arms.** C1 + margin vs HA_LEAN + margin, plus the same secondary systems.

**One-class starts.** No learner is excluded. The one-class phase is identical for both arms, because both follow the same label-free path until both classes are present (checked). Its queries are counted in every spend. Reported:
- the share of one-class starts;
- the extra queries before both classes are present (mean, median, maximum);
- the mean budget at which both classes are first present.

**Reporting.** Each condition is reported separately with the §3.3 tables and the §3.2 labels. The labels are descriptive, with 20 clusters each. The results are never averaged with the standard startup.

**Startup rule** (fixed now):
- **Early:**
  - STARTUP_CONSISTENT if, in both RAND8 and LOCAL8, the early mean difference is > 0 and no early loss is shown (UCB ≥ 0);
  - otherwise STARTUP_DEPENDENT: the early-use recommendation is then restricted to the standard maximin startup.
- **0.95 saving:**
  - NO_CONTRADICTION if the 0.95 RMS-saving mean is ≥ 0 in both conditions;
  - otherwise STARTUP_DEPENDENT: the 0.95 claim, if replicated, is restricted to the standard startup.
  - With 20 clusters a startup condition can contradict a 0.95 claim, but not confirm it.
- **Also listed:** the conditions with LATE LOSS_SHOWN, and those with an exceeded harm limit.

## 5. Prior-width controls: a control, not candidate selection

**Arms.** Job `c1c-prior`, 200 units (`src/c1c_prior.py`).
- **C1_S05:** every prior SD × 0.5.
- **C1_S2:** every prior SD × 2.
- Everything else is unchanged: prior centres, starts, trend, cross-fit, classifier, one-class rule.
- They run on the recorded HA_LEAN DEV paths of STD 123–162, at every budget 8..60, fixed now.
- The recorded C1, A and D of the same paths are the references.

**Contrasts.** Cross-path, against A, C1 and D:
- early, late and B8–B60;
- LL and Brier;
- attainment, keeping, sustainment and RMS at 0.90 / 0.93 / 0.95 on A's path.

**Rule** (fixed now).
- PRIOR_ROBUST_EARLY if both controls have early ΔBA-AULC vs A with LCB > 0; otherwise PRIOR_SENSITIVE_EARLY, and the early claim is then tied to this prior width.
- |Δ(control − C1)| early < 0.003 is reported as "practically equal".
- Whatever the controls show, neither replaces C1: the better-looking control is never made the candidate.

**Disclosure.**
- The prior centres and SDs were chosen in EA after the full-pool ML-II diagnostics had been seen: log s_f² −1.25; log ℓ (0.07, 0.42, 0.57, 2.56); log s_n² −6.07.
- New random splits of the same 541 runs do not remove this design effect.
- The controls show only how much the result depends on the prior width.
- These DEV paths were reviewed in EA, so this is not independent validation.

## 6. Information rules

**Data**
- One 541-run pool. No model, threshold or selector changes by OLD/NEW.
- No free archive.
- Every opened simulation counts, the startup included. A run's available channels are opened once, and several models using the same opened run is not an extra simulation.
- No oracle depth, full-pool hyperparameter, test label or hard-group membership enters any deployable arm. Labels, exclusions and hard-group definitions are unchanged.

**Scope**
- No physical simulator, paid API, cloud or protected C4 evaluation.
- No simulation is launched and no message is sent.
- If the 0.95 saving does not replicate, no further seeds or variants are run.
- The main recipe and the validation rules are never changed in response to results.

## 7. Pre-defined use decision

| outcome on the 80 main repeats | use statement |
|---|---|
| V-EARLY shown, startup early CONSISTENT, PRIOR_ROBUST_EARLY | C1 + margin is recommended for the early, fixed-small-budget use (B8–B24) in this pool |
| V-EARLY shown, startup early DEPENDENT | as above, but only with the standard maximin startup |
| V-EARLY shown, PRIOR_SENSITIVE_EARLY | as above, with the claim tied to this prior width |
| V-EARLY not shown | the early claim did not replicate; HA_LEAN + margin remains |
| 0.95 saving SHOWN, V-0.95 RELIABLE, startup 0.95 NO_CONTRADICTION | C1 + margin is recommended for the stop-at-0.95 use in this pool |
| 0.95 saving not SHOWN | the 0.95 claim is narrowed to what holds (NOT_WORSE / RELIABLE / neither); the early-use claim is kept if shown; this validation branch is closed, with no further seeds or variants |
| LATE LOSS_SHOWN, or a harm limit exceeded | HA_LEAN + margin is the safer reference for the full-budget / late use |
| LATE_PRESERVED / NO_LOSS_SHOWN only | "late performance preserved within 0.003" / "late loss not shown", never interchanged |
| always | the EA K5 geometry warning stands: HA_LEAN + margin remains the safer reference for extrapolation to an unsampled input region; all claims are pool-only |

**In-pool learner.** C1 + margin becomes the recommended in-pool learner only if all of these hold:
- V-EARLY shown;
- 0.95 saving shown;
- V-0.95 RELIABLE;
- LATE not LOSS_SHOWN;
- harm limits met;
- startup early CONSISTENT and 0.95 NO_CONTRADICTION;
- PRIOR_ROBUST_EARLY.

In that case, HA_LEAN + margin stays the frozen reference and the extrapolation-safe choice. Otherwise:
- HA_LEAN + margin stays the thesis learner;
- C1 + margin is recorded as recommended only for the uses whose verdicts passed.

**Claim boundaries.** A replicated application gain and a methodological novelty are separate claims; only the first can be supported here.

**External-validation plan.** Built from the existing RC24 physical-data proposal, not recreated. It states:
- the runs needed;
- when the models are frozen;
- how new results are opened;
- which comparison tests which claim.

No simulation or message is part of this task.

## 8. Compute and runner

| job | units | estimate |
|---|---|---|
| c1c-main | 800 | ≈ 6.4 worker-h |
| c1c-start | 400 | ≈ 3.2 worker-h |
| c1c-prior | 200 | ≈ 1.1 worker-h |

**Total** ≈ 10.7 worker-hours, or about 3.6 h wall-clock with 3 workers.

**Runner** (`src/c1c_runner.ps1`, a copy of the EA runner; directory `runner/`):
- launched detached through WMI and supervised;
- checkpointed, with O_EXCL unit locks; finished units are never rerun.

**Resources**
- At most 3 single-thread numerical leaves (8 logical CPUs: Astra 3, system 2); memory guard 3072 MB.
- One 48-hour window, 2026-10-26T18:05:16Z – 2026-10-28T18:05:16Z, never reset; closed early when done.
- Coordination only through `C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261026\opus_state.json`, campaign id `opus_c1_confirmation_20261026`.
- Astra's files are read, never written.
- Waiters are bash-only and do no LLM polling.

## 9. Deliverables

**Reports**
- `FINAL_REPORT_C1C.md`: Turkish, one-page result first.
- `DECISION_C1C.md`: the use decision.
- `EXTERNAL_VALIDATION_PLAN_C1C.md`: for Ioan.
- `evaluation/C1C_DECISION.json` and the CSV tables.

**Data and checks**
- `exports/`, each set with `EXPORT_ACCEPTANCE.json`, plus the headline recomputation.
- `COST_BREAKDOWN.json`.
- Freeze check.

**Records**
- Thesis progress log, claims, experiment and decision indexes, attempt ledger.
- Earlier failures are kept, never deleted.
