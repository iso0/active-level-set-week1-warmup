# FINAL Phase 1.19B report

## Frozen prospective design

Twenty label-independent maximin initial designs were run for exactly four arms on the full 405-point pool and, without retuning, the validated 364-point main configuration. All arms share B16 within repeat. M3 was fitted only to truly queried simulator labels. Provisional monotonic inferences never entered M3 training. The common predeclared horizon is B120.

## Primary finite-pool result

Full-pool balanced-accuracy AULC B16–B120:

- P0: 0.984890
- P1: 0.975267
- P2: 0.971652
- P3: 0.976365

Paired contrasts versus P0:

- P1: -0.009622, 95% CI [-0.012657, -0.006655], Holm p=0
- P2: -0.013237, 95% CI [-0.017733, -0.008987], Holm p=0
- P3: -0.008525, 95% CI [-0.011908, -0.005265], Holm p=0

Primary decision: **MONOTONE_POOL_HARM**.

## Structural safety and label saving

P3's B120 mean wrong-inference rate among inferred labels is 0.7689%, 95% CI [0.7051%, 0.8331%]. However, KH-as-C errors equal 2.466% of the 73 true KH points on average, versus 0.196% of the 332 true C points. This fails the conservative class-direction safety cap despite passing the aggregate cap. Every incorrect inference remains counted in the composite metric and retrospective log. The three known violation pairs are traced in `violation_trajectory_summary.csv`.

Structural decision: **MONOTONE_PROPAGATION_TOO_RISKY**. Label-saving decision: **LABEL_SAVING_NOT_SUPPORTED**. Threshold rows are right-censored; no guaranteed or universal saving is asserted.

## Why the monotone arms lost

P3 reached complete structural coverage using a mean of 86.35 true queries, versus 120 for P0, but its B120 balanced accuracy was 0.986692 versus 0.999172. P3's mean B80 path Jaccard overlap with P0 was 0.693, and the paths first diverged at query 18.45 on average. Thus the order relation resolved many labels cheaply, yet candidate removal and a changed query path plus a small number of hard implication errors reduced the full-horizon recovery curve.

Threshold diagnostics: BA 0.95: P0-P3=-1.80 queries, paired N=20, CI [-4.35,+0.50]; BA 0.97: P0-P3=-3.20 queries, paired N=20, CI [-6.55,-0.05]; BA 0.98: P0-P3=+3.00 queries, paired N=11, CI [+1.00,+4.91]. The apparent positive saving at BA 0.98 is based on only 11 paired attainments, below the frozen 14/20 requirement.

## Boundary diagnostics

- q20: P0=0.9560, P3=0.9347, difference=-0.0213
- q30: P0=0.9663, P3=0.9497, difference=-0.0166

These are secondary. The observed finite-pool harm is also present in the local q20/q30 diagnostics.

## Safe interpretation

This experiment tests the frozen finite simulator pool only. Structural labels are provisional inferences, not guaranteed labels. It does not establish continuous-domain monotonicity, physical causality, or generalization beyond the frozen SPH design.
