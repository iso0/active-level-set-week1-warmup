# Week 9 Phase 2.1 claim ledger

Primary question: **does `4d_plus_width_dynamics` beat `4d_only` at predicting `has_keyhole`?**

| claim | status | guardrail |
|---|---|---|
| PRIMARY — the full 8-feature width-dynamics block added to [P, VX, LS, ST] improves hard classification | NOT SUPPORTED | q20 balanced accuracy / Keyhole recall / accuracy; 95% repeat-block CI, Holm-adjusted over six predeclared metrics |
| PRIMARY — the same block improves ranking / probability quality | NOT SUPPORTED | q20 ROC-AUC / PR-AUC / Brier; read separately from the hard metrics |
| The primary verdict is stable across evaluation regions (q20, q30, full) | QUALIFIED | q20: nominal effect on none; q30: nominal effect on brier_score, keyhole_recall, pr_auc; full: nominal effect on brier_score |
| Temporal width dynamics alone can classify the regime | NOT SUPPORTED | width_dynamics_only q20 balanced accuracy = 0.505 (chance = 0.500) |
| SECONDARY — a 3-feature width-SHAPE subset added to [P, VX, LS, ST] improves prediction | SUPPORTED | predeclared sensitivity, not the primary claim; q20 BA +0.0203 [+0.0094, +0.0313], consistent on q20/q30/full and mirrors the Phase 2 h-baseline pattern |
| The five robust-derivative features are what neutralises the shape signal | QUALIFIED | inference by subtraction (shape-only helps, shape+derivatives does not); no separate derivative-ablation experiment was run |
| Static width levels added to [P, VX, LS, ST] help | NOT SUPPORTED | 4d+static − 4d q20 BA = -0.0110 [-0.0207, -0.0012] (degrades) |
| Width dynamics is largely redundant with the 4D inputs that generated it | SUPPORTED | median R² of a width feature on [P, VX, LS, ST] = 0.58 |
| Transverse width features are marginally associated with the regime | SUPPORTED | largest absolute Cliff's delta = 0.266 (robust_median_positive_dWdt_um_per_ms); marginal, not incremental |
| Phase 2's published model numbers are reproduced exactly by this pipeline | SUPPORTED | phase2_reproduction_gate.csv: every reproduced mean matches to <1e-9 |
| The four raw process inputs outperform the scalar physics coordinate h | NOT SUPPORTED | 4d_only − h_only q20 BA = -0.0101 [-0.0183, -0.0022] |
| Results generalise to simulations with no usable width trace | NOT SUPPORTED | every model is scored only on the usable subset; trace loss is structured in P |
| This phase says anything about in-process monitoring hardware | NOT SUPPORTED | SPH monitor traces only; no camera, no prospective experiment |

## Status vocabulary
- **SUPPORTED** — the 95% repeat-block interval excludes zero in the favourable direction.
- **QUALIFIED / INCREMENTAL** — the effect appears on some metrics but not others, or is directionally
  present with an interval that touches zero.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
- **DESCRIPTIVE ONLY** — a marginal or exploratory observation with no held-out predictive backing.

## Canonical numbers
- Canonical population: 405 simulations, 73 Keyhole
- Usable transverse-width traces: 350/405 (70 Keyhole, 280 Conduction)
- Structured trace loss in P (standardized mean difference, usable − missing): +0.546
- q20 balanced accuracy — 4d_only 0.8109, width_dynamics_only 0.5054, 4d_plus_width_dynamics 0.8144
- q20 Keyhole recall — 4d_only 0.6920, 4d_plus_width_dynamics 0.7021
- q20 ROC-AUC — 4d_only 0.9073, 4d_plus_width_dynamics 0.9065
- q20 PR-AUC — 4d_only 0.8135, 4d_plus_width_dynamics 0.8177
- q20 Brier — 4d_only 0.1205, 4d_plus_width_dynamics 0.1184
- PRIMARY contrast (4d_plus_width_dynamics − 4d_only, q20): BA +0.0035 [-0.0037, +0.0112], recall +0.0101 [-0.0020, +0.0251], accuracy +0.0020 [-0.0040, +0.0085], ROC -0.0008 [-0.0112, +0.0085], PR +0.0042 [-0.0026, +0.0106], Brier -0.0021 [-0.0050, +0.0010]
- PRIMARY contrast on the full held-out set: BA -0.0015 [-0.0049, +0.0021], ROC -0.0009 [-0.0031, +0.0009]
- SECONDARY (4d_plus_width_shape_only − 4d_only, q20): BA +0.0203 [+0.0094, +0.0313], ROC +0.0144 [+0.0115, +0.0171], PR +0.0147 [+0.0114, +0.0182] — SUPPORTED
- Secondary (4d_plus_static_width − 4d_only, q20): BA -0.0110 [-0.0207, -0.0012] (degrades)
- Phase 2 reproduction (h_plus_width_dynamics − h_only, q20): BA -0.0201 [-0.0288, -0.0113], PR-AUC +0.0202 [+0.0113, +0.0289]
- Context (4d_only − h_only, q20): BA -0.0101 [-0.0183, -0.0022]
- Median R² of a width-dynamics feature regressed on [P, VX, LS, ST]: 0.581
- Phase 2.1 verdict — hard decision: NOT SUPPORTED; ranking/probability: NOT SUPPORTED; overall: NO ADDED VALUE BEYOND THE 4D PROCESS INPUTS
