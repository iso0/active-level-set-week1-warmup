# PROTOCOL GT: geometric Keyhole classifier and early temperature

Registered on 2026-11-02 before any learner, classifier or label-association number of this study is computed. The registration commit is pushed first.

Every rule below is fixed now. A change after any result is recorded as a dated amendment with its reason. Errata only: no earlier output is overwritten.

The owner's brief is in `TASK.md`. The C1 reference is `src/ea_cand.py` SYSTEMS["C1"] with the margin path of `src/ea_fwd.py` `unit_X`; both are unchanged.

## 0. What is already known, and what was looked at before this registration (ledger row GT-PRE)

**Earlier results that bear on the questions.** None of them answers this study's questions. None is counted as a refutation.

| source | what was tested | relation to this study |
|---|---|---|
| Week 6 Phase 3.5 (`src/week6_phase3_5_regime_target_design.py`) | Aspect-ratio summaries (T0 median, global maximum, interior q95, persistent maximum R3) with a 12 µm width guard; R3 recommended as a continuous target, with persistent depth G3 as a companion | Definitions and quality rule only. No classifier, no learning from inputs. |
| Week 7 Phase 5 (`outputs/week7_05_keyhole_physical_proxy_analysis/`) | TRUE-value label proxies on 165 runs: G3 AUC 1.000, max depth 0.9998, R3 0.9986, T0 aspect ratio 0.961, T0 width 0.54; G3 carried | Measured values, not predictions. Not an active-learning comparison. |
| RC20 C45, RC22 | Late-window (T0) maximum temperature as a classifier feature: it lowered log loss beyond predicted depth, but added nothing after log h + depth | T0 is the last 20 % of the active window. It is not an early, causal window. |
| IR (0a57d644) | True W/D ≤ 2 (W = active maximum width): BA 0.978. Oracle [h, D]: BA 0.976. Width alone: AUC 0.64. LMC / CHAIN co-output DEPTH models failed the screen. IR F3: maximum temperature rises before the first K frame (−28 µs). IR F4: early-window temperature AUC 0.97 vs h alone 0.99. | IR used width to improve the DEPTH prediction. Here geometry is the CLASSIFIER itself, through a fixed physical boundary. IR's F3 aligns runs on the first K frame, which a running system cannot know. IR's F4 window starts at the first active row and ends at a cutoff that is known only afterwards. Neither is a causal early test. |

**Looked at today, 2026-11-02 between 17:45 and 18:15 UTC, before this registration** (scratchpad, label-free unless stated):

- **R2 true-value rule** (label-related; the only label look): A / W_atA ≥ 1/2 gives BA 0.974 (sensitivity 1.000, specificity 0.948, 540 runs). It was computed next to IR's R1 (0.977).
- **Width:**
  - no pile-up (one run has W_A ≥ 295 µm, maximum 303.7 µm);
  - W_A / (2·LS) has median 1.54, and corr(log W_A, log 2·LS) = 0.26, so width is not the beam diameter.
- **Data layer (`src/gt_data.py`, run 18:10 UTC):**
  - depth reproduces the pooled A_um exactly on 540 runs; one run has a bounds/time mismatch;
  - the maximum-temperature file exists for 485 runs (55 missing, 1 unusable);
  - the depth maximum and the width maximum lie a median 0.35 ms apart (IQR 0.16–0.62 ms);
  - W_atA / W_A has median 0.954;
  - R3inst / (A / W_A) has median 1.08, and R3inst / (A / W_atA) has median 1.01;
  - the 99th percentile of the instantaneous ratio is 0.995 of its maximum, so the maximum is not a single-row spike;
  - 134 runs have active rows ≥ 295 µm, with a median depth of 300.2 µm on those rows (IQR 300.05–300.39).
- **Timeline peek on 3 runs** (rows every 0.018 µs; frames every 8.5–11 µs):
  - melt onset at 0.30–0.37 ms;
  - first C/K frame at 0.54–0.66 ms;
  - first K frame at 0.65–0.74 ms;
  - the 41 runs with TE = 1.25 ms melt from about 0.002 ms.
- **The C1 reference levels** published in C1C (STD 203–282):
  - BA 0.957 at B60;
  - 0.90 reached by 400/400 learners;
  - 0.95 reached by 335/400, mean spend 22.3.

## 1. Questions

- **QG1.** Does a classifier built from PREDICTED melt-pool geometry with the fixed physical boundary d / w = 1/2 learn Keyhole vs conduction at fewer total simulations than C1 + margin?
- **QG2.** Is the direct ratio target (B) easier to classify with than separate depth and width predictions (A)?
- **QG3.** Does any gain come from the model or from the query path?
- **QG4** (controls). Does a label-calibrated geometric score, or the predicted ratio added to C1, change the answer? Representation and regularisation are separated from new information.
- **QT-A.** Does an early-temperature summary, learned from opened runs and predicted at new settings, add to C1? This is a claim about simulation COUNT.
- **QT-B.** Can the first part of a started run predict its label, and does temperature add beyond the known settings and the early depth? This is a claim about execution TIME.
- **QIR.** Dated corrections of IR's interpretations, and the ~300 µm depth pile-up.

### Mathematical notes that frame QG1–QG4

1. **The boundary.** d / w = 1/2 is a semicircular cross-section, depth equal to half the width. W/D thresholds in the literature range from 1.5 to 2.75 (IR `LITERATURE.md`). The primary threshold is 2: g = log(2d/w) and the boundary is g = 0. d and w are physical depth and FULL width in µm. They are not C1's standardised log-depth feature.
2. **A vs B are linear rewrites at fixed hyperparameters.**
   - For a fixed kernel, trend prior and noise structure, the GP posterior mean is linear in the targets.
   - A GP on g = log 2 + log d − log w would then return exactly log 2 + m_d − m_w.
   - B can differ from A only through separately learned hyperparameters (MAP lengthscales, signal and noise variances) and through its variance.
   - "B is easier" can only mean that the ratio's input dependence is smoother or less noisy relative to its spread, because common factors cancel. Acceptance check V6 verifies the identity numerically.
3. **A's decision ignores the cross-covariance.**
   - P(Keyhole) ≥ 0.5 depends only on the sign of m_d − m_w + log 2.
   - The cross-covariance of the two predictions changes only the probability scale (log loss) and the margin ranking.
   - A assumes independent posteriors for d and w. This is stated; the errors are probably positively correlated, so A's probabilities are too moderate. A joint model is not a candidate: IR's LMC gave no depth gain, and the 0.5 decision is invariant.
4. **Label use.** A fixed physical threshold uses no labels. The geometric classifiers A and B ignore every paid label, so they need no one-class rule. Labels enter only in the controls CAL and C1_G.

## 2. Data contract, IDs, window, resources

**The pool.** One pool of 541 runs (405 OLD + 136 NEW; provenance only), behind `src.rc19_pool.Reveal`:
- every opened run counts, including the 8 startup runs; a run with missing channels or a short record keeps its cost;
- unopened and test outcomes never reach a learner: the width, ratio and temperature reveals are paid-only accessors, NaN elsewhere;
- labels (has_keyhole, manual morphology), short-Keyhole (pooled rule), q20 and the source batch are unchanged;
- no new simulation.

**DEV** (recorded C1 + margin own paths of the EA validation; IR's screen set; no longer fresh):
- STD 163–202 × 5 folds (200 learners);
- K5 startups 41–48 × 5 blocks (40);
- K4 startups 25–32 × 4 blocks (32).

Source: `outputs/research_campaign_20261026/opus_error_attribution/ea-fwd/units/*__X.json.gz`.

**Fresh validation** (never used; FR ID_INVENTORY):
- STD 383–462 (80 repeats × 5 folds = 400 learners);
- K5 49–56 (40);
- K4 33–40 (32).

These are new splits of the same pool. They are not external physical validation.

**Window:** 2026-11-02T17:45:00Z to 2026-11-03T17:45:00Z (24 h). The study closes early when done. No earlier campaign's window is reused.

**Resources:**
- at most 6 single-thread workers (4 physical / 8 logical cores, no other study running); BLAS and OpenMP threads = 1 in every worker;
- coordination only through `C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261102\opus_state.json`;
- queues use `src.rc18_common.run_units` (unit checkpoints, locks, failed records; a restart repeats the same command); STATUS and logs are kept in `runner/`.

## 3. Measurement definitions and quality rules (`src/gt_data.py`; data frozen with this registration)

| symbol | definition |
|---|---|
| d = A | active-window maximum of max(0, −z_min) over valid bounds rows (C1's depth target) |
| w1 = W_A | active-window maximum of the y-extent of the melt bounds (IR's definition) |
| w2 = W_atA | width at the row of the active depth maximum |
| R3inst | maximum over active valid rows with w(t) ≥ 12 µm of d(t)/w(t) |

- R3inst is the simultaneous ratio, closest to an "any Keyhole event" label. The 12 µm guard is the audited Week 6 denominator guard, three 4 µm particle spacings.
- **Targets:**
  - g1 = log(2A / W_A) is the reference: IR's rule, a ratio of two maxima that do NOT occur at the same time;
  - g2 = log(2A / W_atA) is simultaneous at the deepest row;
  - g3 = log(2·R3inst).
- **Quality rules are the audited ones, never chosen from results:**
  - valid bounds rows: finite, non-sentinel, ordered (Week 19);
  - active window (Week 19);
  - frame-time mapping through iter.dat (Week 19);
  - a channel is used only if its row count equals time.dat (IR);
  - short records (< 95 % of the planned end) get the RC18 noise weight 1e4, as in C1;
  - runs without a value keep their cost and are left out of that GP only.
- **Early features** (causal): only rows with time ≤ t are used, on a 25 µs grid from 0.300 to 2.100 ms after the simulation start t = 0, which is known beforehand:
  - Dmax(t), the running maximum depth; Dnow(t), the median depth over the last 10 µs;
  - Tmax(t), the running maximum of maximum-temperature_melt; Tnow(t), its median over the last 10 µs;
  - ifrac(t), the solver iteration at t over the last iteration (compute proxy).
  - No whole-run mean, standard deviation, future maximum, active-window end, first-K time or label enters a feature.
- **Primary decision times:** t_c ∈ {0.50, 0.75, 1.00} ms after the start, about 24 %, 36 % and 48 % of the planned 2.1 ms.
  - They were fixed with knowledge of IR's descriptive timeline and the 3-run peek (§0).
  - The full 25 µs grid is evaluated as well, so no single t_c carries the conclusion.

## 4. Systems

All GPs reuse C1's engine unchanged: `src.ea_cand.gp_fit`, i.e. GPMAP with Matérn-3/2 ARD on the standardised log inputs, the physics trend θ·z_h with θ ~ N(0, 3²) integrated, the weak MAP hyperprior, two starts and the RC18 quality weights. Only the target changes. The trend and the prior are kept for three reasons:
- the normalised-enthalpy scaling drives depth, width and their ratio alike;
- the prior corrects the small-n ML-II collapse found in EA, a property of n ≤ 60 fits rather than of the target;
- no new engine is written.

| system | definition | uses labels? |
|---|---|---|
| C1 (reference) | recorded C1 + margin (DEV); `ea_fwd.unit_X` unchanged (validation) | yes |
| GEO_A1 | separate GPs on log d (= C1's depth GP) and log W_A; P = Φ((m_d − m_w + log 2) / √(v_d + v_w)), observation predictive variances, independence assumed | no |
| GEO_A2 | as GEO_A1 with log W_atA | no |
| GEO_B1 / GEO_B2 / GEO_B3 | one GP on g1 / g2 / g3; P = Φ(m_g / √v_g), observation predictive variance | no |
| CAL_B1 (control) | 1-D Bayesian logistic (the C1 classifier family with one feature) on s = m_g/√v_g from GEO_B1; training s = honest K = 10 out-of-fold; the threshold and scale are learned from paid labels only | yes |
| C1_G (control) | C1's classifier with ĝ1 added as a separately shrunk feature (`src.ea_diag.lin_u`, τ_U ∈ {0.5, 1, 2, 4}); training ĝ1 and depth are honest K = 10 out-of-fold | yes |
| C1_T (QT-A) | C1's classifier with predicted Tmax(0.75 ms) as a separately shrunk feature (lin_u); temperature GP = C1's engine on paid Tmax(0.75); honest out-of-fold | yes |
| ORACLE_T (diagnostic) | as C1_T with the TRUE Tmax(0.75) at paid and test rows; evaluator-only, never a method | yes |

Notes on the systems:
- The observation variance is used because the label belongs to the observed run.
- lin_u with a zero extra feature reduces exactly to C1's classifier, so C1_G and C1_T are nested in C1. A gain from ĝ1 would be representation or regularisation (ĝ1 = log 2 + log d − log w is a rewrite of geometry): it is reported as such, never as "new information".
- **One-class rule:** C1, CAL_B1, C1_G and C1_T return the paid class rate and follow the label-free path while the paid usable labels hold one class, as C1 does. GEO_A and GEO_B never need it.
- **GP fallback:** if fewer than 3 good rows exist, the system falls back to the label-free path. Its predictions are then the GP-free class rate for label systems and 0.5 for GEO.

**Selectors (G3).**
- margin: argmin |P − 0.5|;
- straddle: argmax 1.96 σ_lat − |m| on the g scale, where σ_lat is the latent predictive SD (Bryan et al. 2005);
- space-filling: the next run of the task's label-free maximin path.

## 5. Stages and rules (fixed now)

### G1. Acceptance and honesty (before any DEV number is read)

| check | rule |
|---|---|
| V1 | depth A equals the pooled A_um on every run (done: 0.0) |
| V2 | **shadow test:** every unpaid and test label, depth, width, ratio and temperature is replaced by noise in the hidden tables; the predictions and the query path of every system are bitwise identical (2 STD learners, 1 K5, 1 K4; budgets 8–20; plus 2 own paths per selector) |
| V3 | GEO_A's depth GP is C1's full-fit depth GP (the mean at test rows equals `PC.depth_predict` of `CA.depth_fit_cand` to 1e-12) |
| V4 | C1 recomputed at b = 12 and 40 reproduces the recorded C1 predictions on every DEV learner (max \|Δ\| ≤ 1e-6, float32): the reuse check |
| V5 | the recorded C1 paths start with the task's 8 startup runs; the GEO own paths start with the same 8 |
| V6 | linearity identity: with one fixed hyperparameter vector, GP(g) mean = log 2 + GP(log d) mean − GP(log w) mean to 1e-10 |
| V7 | Φ-probabilities match a 10⁵-draw Monte-Carlo estimate to 3e-3 |
| V8 | the evaluator (`src/gt_eval.py`) reproduces `src.el_eval.endpoints` exactly at τ ∈ {0.90, 0.93, 0.95} on the recorded C1 rows |

### G2. DEV matched comparison (same opened runs, same startups, every budget 8–60)

- Every system of §4 is computed on the recorded C1 paid prefixes. The reference is the recorded C1.
- **Selection.** One geometric system, GEO\*, is chosen: the GEO_A / GEO_B variant with the largest STD mean ΔBA-AULC B8–B24 against C1. If two lie within 0.0005, B8–B60 decides.
- **"Promising" rule.** The geometry line goes on to G3 only if GEO\*'s STD mean ΔBA-AULC B8–B24 ≥ −0.003. This is within C1's practical margin, so a path effect could still give a gain.
  - Otherwise: GEOMETRY STOP. No G3, no G4.
- **Controls.** C1_G is carried to G3 as a second candidate only if its STD ΔBA-AULC B8–B24 ≥ +0.005 with one-sided 95 % LCB > 0. CAL_B1 is descriptive.
- **QT-A.** C1_T is carried to an own-path test only if its STD ΔBA-AULC B8–B24 ≥ +0.005 with LCB > 0. Otherwise TEMPERATURE-A STOP: no time-model campaign.

### G3. DEV own path (only if promising)

- GEO\* + margin runs its own path on the 272 DEV tasks with the same startups.
- C1 predictions are computed on the GEO\* paths, for the 2×2 decomposition: model effect on each path, path effect for each model, interaction.
- GEO\* + straddle and GEO\* + space-filling run their own paths as limited selector controls.
- **Transition to G4.** GEO\*·S is the selector with the best own-path STD ΔBA-AULC B8–B24 against C1_own. It goes to fresh validation only if both conditions hold:
  1. either (a) ΔBA-AULC B8–B24 ≥ +0.005 with LCB > 0, or (b) the restricted-mean spend saving at 0.95 ≥ +1.0 with LCB > 0 and ΔBA-AULC B8–B24 LCB > −0.003;
  2. the DEV harm limits hold:
     - late ΔBA-AULC B28–B60 LCB ≥ −0.005;
     - per-region block ΔBA-AULC B8–B60 LCB ≥ −0.02 in K5 and K4 (EA warning rule);
     - Δ log loss B8–B60 ≤ +0.030.
- Otherwise: GEOMETRY STOP.
- The same rule applies to C1_G if it was carried.
- The code, the system and the selector are frozen and pushed before any G4 unit runs.

### G4. Fresh validation (frozen code, fresh IDs of §2)

- GEO\*·S own path runs against C1 + margin (`ea_fwd.unit_X` unchanged). GEO\* on the C1 path is computed as a secondary model-effect contrast.
- **Verdicts.** The rules of `src.ea_fwd_eval.verdicts` apply unchanged, with clusters = repeats and one-sided 95 % t bounds:
  - V_EARLY (B8–B24);
  - savings 0.90 / 0.93 / 0.95;
  - V_095 RELIABLE;
  - LATE;
  - harm: LL ≤ +0.030, Brier ≤ +0.010, CPU ≤ 3×.
- C1C's LATE_PRESERVED applies: LCB(B28–B60) > −0.003.
- The block warning applies: per-region LCB < −0.02.

### Final decision (one of three)

- **"ADAY GELİŞTİRİLDİ VE DOĞRULANDI"** requires both:
  1. G4 shows either V_EARLY = EARLY_GAIN_SHOWN+PRACTICAL, or 0.95 saving SAVING_SHOWN+PRACTICAL with early LCB > −0.003;
  2. G4 passes LATE_PRESERVED, V_095 RELIABLE, LL_ok, Brier_ok and CPU_ok, with no block warning.
- **"C1 KORUNUYOR"** applies after a registered DEV stop, after a G4 without these, or when a harm limit fails.
- **"KANIT TAMAMLANMADI"** applies only if a registered stage cannot finish in the window, or if an acceptance check fails and cannot be repaired without changing a registered rule.

### QT-B. Early evaluation of a started run (run-level, separate from the learner)

**Population.** Runs with bounds and maximum temperature: 485 of 541. Exclusions are listed by batch and label.

**Split.** A seeded split stratified by label (`numpy.random.default_rng([20261102, 7])`):
- DEV half: development, with 5 × 10-fold run-level CV;
- VAL half: opened only if temperature passes the benefit rule below.

Frames of one run never sit on both sides of a split.

**Models.** L2-logistic (C = 1, features standardised on the training folds only), at each grid time:

| model | features |
|---|---|
| S | z_h, the settings |
| S+T | adds Tmax, Tnow (kK) |
| S+D | adds log1p Dmax, log1p Dnow |
| S+D+T | all of the above |
| C1p (reference) | C1's classifier on [z_h, D̂], with D̂ from C1's depth GP fitted on the training runs only (inner honest K = 10 out-of-fold) |

C1p is "C1 with large training sets": the prediction before the run starts.

**TB-INFO.** Held-out log loss, AUC and BA at t_c ∈ {0.50, 0.75, 1.00} ms.
- Reported by stratum: all runs; Keyhole with the first K frame ≤ t_c (already happened) vs > t_c (future event); short-Keyhole; NEW conduction; the 20 % of runs closest to the boundary (smallest \|p_S − 0.5\|); TE = 1.25 runs.
- Contrasts:
  - S+D+T vs S+D (temperature beyond early depth), PRIMARY;
  - S+T vs S (beyond settings);
  - S+D vs S.
- Paired run-level bootstrap, 2,000 draws.

**TB-TIME** (alarm, every 25 µs grid time up to the planned end TE).
- A run alarms at the first grid time with P_t ≥ π_hi.
- π_hi is chosen inside each training fold by nested 5-fold CV, so that the per-run false-alarm rate over ALL grid times of conduction runs is ≤ 0.05 (secondary: 0.02).
- Reported:
  - capture (Keyhole runs alarmed);
  - false alarm (conduction runs alarmed at any time);
  - warning time (first K frame − alarm; negative = after onset);
  - time read: t_alarm / TE for alarmed runs, 1 otherwise; iteration share as a compute proxy;
  - the static S alarm, which decides without simulating.
- No wall-clock records exist, so no CPU saving is claimed. Only the fraction of physical simulation time and of solver iterations is reported, with the assumption that cost is proportional to them.

**Benefit rule (DEV → VAL).** Temperature has an extra benefit if either holds:
- (i) Δ log loss (S+D+T − S+D) ≤ −0.010 with a bootstrap upper bound < 0 at ≥ 2 of the 3 primary times;
- (ii) at FAR ≤ 0.05 for both models, the mean time read over all DEV runs is lower by ≥ 0.03 for S+D+T vs S+D, with the bootstrap interval excluding 0 and capture not lower by more than 0.02.

If neither holds: TEMPERATURE-B: NO EXTRA BENEFIT, the VAL half stays closed, and no time-model campaign starts. The S+D (early-depth) time figures then stay DEV-level descriptive.

## 6. Metrics (every system, every stage)

- **Windows:** BA-AULC B8–B24, B8–B60, B28–B60 (late).
- **BA at budgets:** B8, B12, B16, B24, B40, B60.
- **Recalls:** Keyhole recall (sensitivity) and conduction recall (specificity), in the same windows.
- **Probability quality:** log loss (clip 1e-6) and Brier.
- **Targets τ ∈ {0.80, 0.90, 0.93, 0.95}:**
  - first b with BA ≥ τ;
  - confirmed b, the first b ≤ 56 with BA(b) ≥ τ and BA(b+4) ≥ τ;
  - spend = confirmed b + 4, including the 8 startup runs and the 4 confirmation runs;
  - attained (count / denominator and rate);
  - spend mean and median among attainers, with denominators;
  - median spend over all learners with non-attainers = ∞;
  - restricted-mean spend, 61-capped. It is flagged as neither the true cost nor a bound;
  - kept: BA(60) ≥ τ;
  - sustained: BA ≥ τ at every budget from the confirmed b to 60.
- **No conditional mean of attainers is presented as an overall saving.**
- **Subgroups** (evaluator only), over B8–B24 and B24–B60:
  - short-Keyhole recall (pooled rule; NEW original);
  - NEW conduction specificity (EA hard group);
  - the corner (VX > 0.85, P > 330);
  - ceiling Keyhole (A ≥ 295 µm), Keyhole below the ceiling, and conduction;
  - the per-learner Δ against the paid share of ceiling runs (descriptive).
- **CPU:** process seconds per decision.
- **Uncertainty:** per-cluster mean of per-learner paired differences, one-sided 95 % t bounds, with a cluster bootstrap check. Repeats, folds and time frames are not new physical data.

## 7. Exports and independent recomputation

- `exports/`: predictions (float32) and query IDs for every system and stage.
- `src/gt_recompute.py`: separate code with no `el_eval` import. It recomputes BA, the AULC windows and the headline contrasts from the exports. Acceptance: max \|Δ\| ≤ 1e-9.

## 8. Why these sizes

- **+0.003 BA (PRACTICAL).**
  - A test fold holds about 108 runs. One misclassified run changes BA by 0.5 / n_class, about 0.009.
  - +0.003 is one error fewer in about every third learner-budget. C1's own established early gain over HA_LEAN was +0.005.
  - Below +0.003, a new model family is not worth its complexity.
- **+0.005** is required at DEV transitions, as a margin for regression to the mean after selection among 5 variants.
- **1 simulation** is the smallest unit of cost, so a saving counts as practical at ≥ 1.0.
- **Late −0.003** is C1C's non-inferiority margin. DEV allows −0.005.
- **The −0.02 block rule** is EA's warning rule.
- **QT-B:** 0.010 nats per run and 3 % of a run, about 63 µs of 2.1 ms, are the smallest differences that would change how a simulation is run.

## 9. IR corrections, depth ceiling, tests and records

- **IR addendum.** A dated addendum (`IR_ADDENDUM_20261102.md` in the IR folder) qualifies:
  - "depth carries all label information": not causal and not universal; labels are manual morphology annotations, and the ceiling censors depth;
  - "no output adds information": limited to the tried features, models and practical limits;
  - "no simulation saving": the full own-path comparison was not run;
  - the true-KE control is no upper bound for all methods;
  - the assumptions of the transfer-cancellation result (isotopic data, ICM / separable kernel, noise structure);
  - the first look before registration, to be repeated in the summaries.
- Dated pointer lines are added to IR's Turkish and English reports. Frozen numbers are not changed.
- **Ceiling.**
  - Local parameter files and audited sources are searched. Run folders hold only `frames.csv` and monitors, and Week 19 notes that the z-extent is not in the folder parameters read so far.
  - Internal evidence is reported: the plateau level, its spread, durations and batches.
  - If the domain floor cannot be verified, it stays a HYPOTHESIS.
  - The geometric results are checked by ceiling subgroup; the main sample is never changed.
- **Regression tests.**
  - The full suite runs on the final commit.
  - Both earlier failures are rerun on the old base b0e9569f (`git archive` extract), and "pre-existing" is claimed only if they fail there.
  - Failures caused by this study are fixed. Unrelated ones are reported, and no frozen scientific reference is changed to make a test pass.
- **Records.**
  - this study's ledger;
  - `docs/thesis_progress_log.md`;
  - `outputs/joint_depth_label_development/CLAIMS_MATRIX.md`;
  - `docs/alse/claims.md`, `decisions.md` and `experiments.md`;
  - the central ATTEMPT_LEDGER;
  - IR's missing central links: IR has no progress-log, claims or decision rows yet.
- **Findings** are recorded as positive, negative and untested, separately.
