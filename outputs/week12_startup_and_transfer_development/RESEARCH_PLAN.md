# Week 12: startup and transfer development

Status: **POST-HOC DEVELOPMENT / EXPLORATORY**. Created 2026-10-03, before
Week 12 model/acquisition results. NEW-136 labels are already open. This plan
is a prospective execution specification within development, not a new external
preregistration or confirmation claim.

## A. Audited starting point

- `main` = remote `main` = `d8fa330c1e404e4d36569e094db14625249480af`.
- Only user-owned `.codex/` was untracked; it is excluded from this work.
- OLD-405: 73 Keyhole, 332 non-Keyhole. NEW-136: 124 Keyhole, 12 non-Keyhole.
- 49 Bug-withheld physical outcomes remain outside this analysis.
- Frozen external result remains `INCOMPLETE_FROZEN_STOP` at
  `external__r003_f04`; no completed-subset performance estimate is computed.
- Included labels are recovered from the unique `sim_id,truth` columns of
  previously authorized predictions. Historical probabilities are never read.
- Exact frozen Python/package versions exist in `.venv`; use that interpreter.
- `audit/protected_hashes.json` snapshots Week 11 files, frozen source/specs and
  OLD input data. Recheck before publication. All new outputs remain here.

## B. Mechanism before method design

Enumerate the original 100 feature-only maximin orders to the whole training
pool, verify their first 16 against stored paths/audit, and measure first
two-class discovery. Describe all 12 rare observations in raw inputs/log h,
nearest opposite/same-class distances, OLD-standardized support distances,
rank in each order, marginal associations, and the three failed prefixes.
Do not optimize acquisition or startup parameters in this phase.

## C-D. Small startup study

After the mechanism report, specify at most five rules: original maximin,
physics-stratified geometry, adaptive physics-guided discovery, and uniform
random reference. Any optional fifth rule requires an explicit mechanism.
Record rules/config before benchmarking. No label-dependent preselection.
Charge all queries, show discovery CDF/tails, rare capture and coverage,
paired variation over the 100 original candidate pools. Original designs and
new developmental policies retain distinct identifiers.

## E. OLD to NEW predictive transfer

Fit historical H (log-h logistic), G0 (historical binary isotropic GPC), G3
(historical generic ARD GPC), M3 and an empirical OLD-prior baseline using only
OLD data. All scaling and hyperparameters use OLD only. Save predictions,
physics/residual components, diagnostics before scoring NEW outcomes.
Metrics: accuracy, balanced accuracy, both class recalls, ROC AUC, average
precision for each class, Brier, log loss, fixed q20 accuracy and calibration.
Use paired class-stratified bootstrap of fixed test predictions for descriptive
cohort uncertainty; this does not model training-set or campaign uncertainty.

## F. NEW-only predictive evaluation

Use the same 100 original input-only splits as paired developmental partitions,
not a resumed frozen run. Train each architecture on all 108-109 training rows.
Some test folds may lack negatives; never discard them. Undefined fold AUC/BA
is null. Pool out-of-fold predictions across all five folds within each repeat
for discrimination/class recall. Report repeat spread as conditional partition
variability, not 20 independent campaigns. No model/hyperparameter selection.

## G. NEW-only end-to-end active learning

Specify the final small arm set after D and before acquisition results. Preserve
historical M3, margin, coverage-to-B40, and early8 logic where applicable; any
extension beyond B16 is explicitly a new developmental complete protocol.
Include matching early-start margin to separate initialization from acquisition,
and a paid random baseline. All queries count, including class discovery.
Use original candidate pools, B80 horizon and every integer B16-B80 for the
historical q20 accuracy AULC. Report startup-stage predictions explicitly if
both classes have not yet appeared. Add earlier-budget summaries if valid.
No checkpoint/performance reuse from the incomplete Week 11 attempt.

## q20 and uncertainty policy

Keep the exact Week 11 evaluation-only full-NEW-pool StandardScaler + nearest
opposite-label distance + stable-ID ties + closest ceil(0.2*n_test) definition.
It is an empirical finite-pool boundary proxy, not the true continuous physical
boundary. Evaluator labels/flags are never available to query selection or
training. q20 accuracy remains defined in single-class test subsets; class
metrics that need a missing class are null. Pooled OOF summaries are secondary
to the historical mean-fold q20 accuracy endpoint. q30 is not substituted.
No confirmatory significance/replacement decision will be issued on these data.

## H-I. Interpretation and publication

Explicitly decide whether meaningful separated tests are possible. If yes,
do not pool OLD+NEW without a distinct unresolved question. Complete model and
acquisition interpretations, then use a targeted primary-literature check for
the strongest actual finding. Produce the requested A-N report and Q1-Q12
answers, plots, QC, code/config/provenance, and logical commits pushed to main.
