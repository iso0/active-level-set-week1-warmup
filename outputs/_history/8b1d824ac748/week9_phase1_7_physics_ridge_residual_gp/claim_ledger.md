# Phase 1.7 claim ledger

| Claim | Decision | Evidence |
|---|---|---|
| The implementation is an additive latent physics trend plus 4D residual GP, not a 5D GPC | PASS | custom additive kernel; component-decomposition tests |
| Frozen baseline and information-flow contracts are preserved | PASS | `baseline_gate.json`; `active_information_flow.csv.gz` |
| The additive model/policy improves primary q20 AULC versus 4D Margin | PASS | Δ=+0.020018, CI [+0.014071,+0.026264], predeclared rule |
| It improves q30 AULC | PASS as secondary | Δ=+0.010941, CI [+0.005966,+0.015978] |
| The residual genuinely recovers some h-trend Keyhole misses | QUALIFY | budget-40 recovery/worsening counts; effect is small |
| It clearly improves over the Phase 1.5 h-only model/policy | QUALIFY | Δ=+0.001801, CI [-0.002183,+0.005598] includes zero |
| The residual amplitude is learned freely and remains small naturally | REJECT | amplitude is learned within a cap and often reaches the upper bound |
| The physics and residual components are uniquely identifiable | REJECT | h is deterministic in three 4D inputs; the cap imposes dominance |
| The result proves acquisition-only superiority | REJECT | model and acquisition policy both differ; advantage starts at shared budget 16 |
| The result transfers across materials or validates industrial safety | REJECT | one retrospective simulator/material population |
