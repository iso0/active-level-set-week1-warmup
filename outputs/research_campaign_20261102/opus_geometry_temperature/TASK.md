# TASK GT (owner brief of 2026-11-02, Turkish; summary)

**What is tested.** Two open routes that might improve the current C1 + margin method, tested fairly:
1. a geometric Keyhole classifier built from predicted depth and width;
2. whether early temperature helps classification (simulation count) or execution time.

The IR study's interpretations and the thesis records are completed alongside.

**This is an implementation request.** Inspect, register a reasoned protocol, run, validate, report and push the research branch, without waiting for "continue" between routine stages.

**Objectives, in order:**
- early BA-AULC on true labels (total 8–24 simulations);
- total simulations to reach BA targets;
- Keyhole and conduction success separately;
- the cost of extra model complexity and computation.

**Freedom.** The owner's ideas are hypotheses. Question them and propose better formulations. Do not repeat a truly tested approach (show the evidence). Do not count a related but different old experiment as a refutation. Fix the candidates before validation, and never change the success definition after seeing results.

**Data rules.**
- All 541 simulations form one pool.
- Every opened run counts, including the first 8, and missing-channel or short records keep their cost.
- No free archive. No unopened or test outcome reaches a learner.
- Labels and the short-Keyhole definition stay unchanged.
- No new simulation.
- C1 + margin is kept unchanged as the strong reference. Old results must be checked for reuse, and numbers from different protocols are not compared directly.

**Geometry.**
- **Target.** Audit the target before modelling. The IR rule is d / w ≥ 1/2 (physical depth and full width). Three definitions are audited: the active-window maxima, the width at the depth maximum, and the maximum of the simultaneous ratio. The current definition is the reference; the alternatives are limited and physically motivated.
- **Measurements.** Verify that the width is the melt-pool width, not the beam. Use the audited quality rules and show the exclusions. The 97.8 % true-value BA is neither model success nor a ceiling.
- **Approaches.** Compare separate prediction (A, with uncertainty carried to the class probability and the independence or cross-covariance treatment stated) with a direct target g = log(2d/w) with boundary g = 0 (B). The primary threshold is 2; any other threshold is learned from opened data only.
- **Controls.** Limited controls are allowed: the ratio added to C1, and calibration with opened labels, both on honest out-of-fold features. Representation and regularisation effects are separated from new information.
- **Stages.**
  1. acceptance;
  2. DEV on the same opened runs and starts;
  3. the promising candidate's own sequential path;
  4. pre-fixed validation on new splits.

  The first screen uses true BA, never a pool-wide g\* map. The same margin selector first; then straddle around g = 0 and space-filling as limited controls.
- **Full metric list.** BA-AULC B8–B24 and B8–B60; BA at B8, B12, B16, B24, B40, B60; both recalls; probability quality; targets 0.80 / 0.90 / 0.93 / 0.95 with b / b+4 confirmation, spend, non-attainers, median and mean, kept and sustained; short-Keyhole and hard conduction; CPU.

**Early temperature.** Two separate questions:
- (A) predicting an early-temperature summary from opened runs at new settings, added to C1;
- (B) judging a started run from its first part.

Rules for (B):
- no future information;
- known start reference (laser / simulation start); a few fixed physical times;
- causal normalisation; splits at the run level;
- false alarms on conduction; missed early events and short Keyhole shown;
- comparisons: settings / h and C1, + temperature, early depth, early depth + temperature;
- alarm capture, false alarm, warning time and time read, with repeated alarm opportunities;
- no CPU-saving claim without wall-clock records.

Start with a small DEV experiment, and do not start a large campaign without benefit.

**Acceptance.** Before results, register:
- the primaries, the minimum useful differences and the losses accepted;
- the transition and stop rules;
- the code and evaluation versions.

Shadow test (unopened outcomes must not change predictions or paths). Leakage-free learned scales, thresholds and calibrations. Independent recomputation from the exports.

**IR corrections.** A dated addendum on six points: depth / label causality; the scope of "no output adds"; "no saving" without a full sequential test; the true-KE control is not a bound for all methods; the assumptions of transfer cancellation; the first look before registration in the summaries. Investigate the ~300 µm pile-up. Frozen numbers are not changed.

**Close.** One Turkish result report. Update:
- this ledger;
- `docs/thesis_progress_log.md`;
- `CLAIMS_MATRIX.md`;
- the central experiment and decision records;
- IR's missing central links.

Check the two earlier test failures on the old base. Commit and push the research branch, verify the remote SHA, no merge to main. The final message starts with one decision: "C1 korunuyor", "<candidate> geliştirildi ve doğrulandı" or "kanıt tamamlanmadı".

**Limits.** 24 h window from the start. Idle cores may be used, without BLAS × worker oversubscription. Do not touch other studies' areas or processes.
