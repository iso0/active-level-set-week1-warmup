# Supervisor Phase 2.1 — one page

## The control Ioan asked for
Phase 2 tested width dynamics against the scalar physics coordinate `h`. It never ran the control an
engineer actually cares about: the baseline is the **four process parameters you dial on the machine**,
`[P, VX, LS, ST]`. Phase 2.1 runs exactly that comparison, with the width definition, population and
folds all held fixed.

* **Baseline** `4d_only` = `[P, VX, LS, ST]`
* **Challenger** `4d_plus_width_dynamics` = `[P, VX, LS, ST]` + the eight Phase 2 temporal width features
* Width is transverse **ΔY = Ymax − Ymin**, reused byte-for-byte from Phase 2 commit `da913797d14b`.
  ΔX (longitudinal length) is not used anywhere in this phase.

## Data
350 of 405 simulations have a usable transverse-width trace (70 Keyhole,
280 Conduction). Every model — baseline included — is trained and scored on that
same subset, so the comparison is paired. Trace loss is **not** random: usable simulations sit at higher
laser power (standardized mean difference +0.55),
so all numbers below are conditional on a trace existing.

## Headline numbers (q20 boundary band, 100 frozen grouped folds)

| model | features | bal. acc | accuracy | Keyhole recall | ROC-AUC | PR-AUC | Brier | full-set bal. acc |
|---|---|---|---|---|---|---|---|---|
| h only | 1 | 0.8210 | 0.8405 | 0.7305 | 0.9060 | 0.8069 | 0.1216 | 0.9293 |
| static width | 3 | 0.5099 | 0.6143 | 0.0198 | 0.5404 | 0.4837 | 0.2677 | 0.4986 |
| width dynamics only | 8 | 0.5054 | 0.6098 | 0.0150 | 0.4972 | 0.4460 | 0.2755 | 0.5021 |
| 4d only | 4 | 0.8109 | 0.8366 | 0.6920 | 0.9073 | 0.8135 | 0.1205 | 0.9204 |
| 4d plus static width | 7 | 0.7999 | 0.8261 | 0.6764 | 0.8998 | 0.8058 | 0.1255 | 0.9126 |
| 4d plus width shape only | 7 | 0.8312 | 0.8503 | 0.7424 | 0.9217 | 0.8282 | 0.1118 | 0.9246 |
| 4d plus width dynamics | 12 | 0.8144 | 0.8385 | 0.7021 | 0.9065 | 0.8177 | 0.1184 | 0.9188 |
| h plus width dynamics | 9 | 0.8009 | 0.8294 | 0.6676 | 0.9076 | 0.8270 | 0.1204 | 0.9110 |

## The primary contrast: 4d_plus_width_dynamics − 4d_only

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
| accuracy | higher is better | +0.0020 [-0.0040, +0.0085] | 0.5659 | 1.0000 | **NO DETECTABLE DIFFERENCE** |
| balanced accuracy | higher is better | +0.0035 [-0.0037, +0.0112] | 0.4004 | 1.0000 | **NO DETECTABLE DIFFERENCE** |
| keyhole recall | higher is better | +0.0101 [-0.0020, +0.0251] | 0.1961 | 1.0000 | **NO DETECTABLE DIFFERENCE** |
| brier score | lower is better | -0.0021 [-0.0050, +0.0010] | 0.1913 | 1.0000 | **NO DETECTABLE DIFFERENCE** |
| pr auc | higher is better | +0.0042 [-0.0026, +0.0106] | 0.2473 | 1.0000 | **NO DETECTABLE DIFFERENCE** |
| roc auc | higher is better | -0.0008 [-0.0112, +0.0085] | 0.8707 | 1.0000 | **NO DETECTABLE DIFFERENCE** |

**Hard classification: NOT SUPPORTED. Ranking / probability: NOT SUPPORTED.
Overall: NO ADDED VALUE BEYOND THE 4D PROCESS INPUTS.**

Every one of the six predeclared metrics has a 95% interval that contains zero, and the largest effect
(Keyhole recall, +0.0101) is smaller than the spread between repeat blocks. This is
not a small-but-real gain that more data would sharpen; on the primary evaluation region it is nothing.

The picture across held-out regions is *not* perfectly uniform, so it is worth being precise:

| evaluation region | balanced accuracy | ROC-AUC | Brier (lower better) | metrics with a nominal effect |
|---|---|---|---|---|
| q20 | +0.0035 [-0.0037, +0.0112] | -0.0008 [-0.0112, +0.0085] | -0.0021 [-0.0050, +0.0010] | none |
| q30 | +0.0049 [-0.0002, +0.0105] | +0.0022 [-0.0064, +0.0092] | -0.0046 [-0.0067, -0.0026] | brier_score, keyhole_recall, pr_auc |
| full | -0.0015 [-0.0049, +0.0021] | -0.0009 [-0.0031, +0.0009] | -0.0009 [-0.0016, -0.0001] | brier_score |

Read that carefully. On **q20** — the boundary band this project uses for its claims — nothing moves.
Away from the boundary, small *probability-quality* effects do appear at a nominal (unadjusted) reading:
Brier improves by 0.0046 on q30 and by 0.0009 on the full set, and q30 PR-AUC moves +0.0104.

Hard classification is a different story: 1 of the 9 hard-decision region/metric combinations has a bootstrap interval excluding zero — q30 keyhole recall +0.0105 [+0.0011, +0.0212] (sign-flip p=0.088, Holm p=0.351). None of them survives the Holm adjustment, and none of them is on q20.

Three reasons not to promote any of this. Each effect is at or below the spread of the metric itself
across repeat blocks (q30 Brier SD ≈ 0.0033, q30 PR-AUC SD ≈ 0.0156). The intervals are unadjusted for the six
metrics × three regions being inspected, and **nothing anywhere survives the Holm adjustment** — every
Holm-adjusted p for this contrast is 1.00 on q20. And the effects live away from the
boundary band, which is precisely the region where a level-set method has the least to gain. The claim
ledger therefore logs region stability as QUALIFIED, and the headline verdict stays the q20 one.

## An honest secondary finding: the shape subset, not the full block

The predeclared sensitivity `4d_plus_width_shape_only` — the same 4D inputs plus only the **three shape**
features (width_gain_20_um, width_gain_40_um, time_to_50pct_max_width_tau), dropping the five robust-derivative features — does improve on
`4d_only`, on every metric, in the same direction:

| metric | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|
| accuracy | +0.0137 [+0.0046, +0.0227] | 0.0083 | 0.0083 | **IMPROVES** |
| balanced accuracy | +0.0203 [+0.0094, +0.0313] | 0.0019 | 0.0038 | **IMPROVES** |
| keyhole recall | +0.0505 [+0.0319, +0.0706] | 0.0002 | 0.0006 | **IMPROVES** |
| brier score | -0.0087 [-0.0097, -0.0075] | 0.0000 | 0.0003 | **IMPROVES** |
| pr auc | +0.0147 [+0.0114, +0.0182] | 0.0000 | 0.0003 | **IMPROVES** |
| roc auc | +0.0144 [+0.0115, +0.0171] | 0.0000 | 0.0003 | **IMPROVES** |

Two things stop this from being the headline. First, it is a secondary sensitivity, not the control that
was asked for. Second, it is best read as a *dimensionality* result rather than new physics: adding three
partly-informative columns helps, and adding five mostly-uninformative derivative columns on top of them
cancels the gain. Phase 2 saw the same pattern against the `h` baseline, so the effect at least
replicates across two different baselines rather than being a one-off. It is logged as
**SUPPORTED** and is a candidate for a dedicated ablation, not a conclusion.

## Why the answer comes out this way
Temporal width is a *consequence* of the process parameters, not an independent measurement of the melt
pool. Regressing each width feature on `[P, VX, LS, ST]` gives a median R² of
0.58: most of what the width trace knows, the inputs already knew.

| width feature | R² explained by 4D inputs | Spearman ρ with label (raw) | Spearman ρ (residual) |
|---|---|---|---|
| width gain 40 um | 0.857 | +0.104 | -0.224 |
| robust max positive dWdt um per ms | 0.705 | -0.159 | -0.079 |
| width gain 20 um | 0.686 | +0.083 | -0.178 |
| robust early dWdt 40 um per ms | 0.652 | -0.011 | -0.072 |
| time to 50pct max width tau | 0.510 | +0.170 | -0.068 |
| robust early dWdt 20 um per ms | 0.489 | +0.073 | -0.142 |
| robust median positive dWdt um per ms | 0.209 | -0.184 | +0.035 |
| robust time of max dWdt tau | 0.035 | -0.021 | -0.157 |

Inside the fitted challenger the decision is still carried by the inputs: the largest process-input weight
is `P`
(+2.568), the largest width weight is
`width gain 40 um`
(+0.743,
sign stable in 100% of folds).

Width dynamics on its own is close to useless as a classifier
(q20 balanced accuracy 0.505), which is consistent with Phase 2.

## Secondary contrasts

| contrast | metric | mean difference [95% CI] | sign-flip p |
|---|---|---|---|
| h_plus_width_dynamics - h_only | roc auc | +0.0016 [-0.0067, +0.0094] | 0.7105 |
| h_plus_width_dynamics - h_only | pr auc | +0.0202 [+0.0113, +0.0289] | 0.0004 |
| h_plus_width_dynamics - h_only | balanced accuracy | -0.0201 [-0.0288, -0.0113] | 0.0003 |
| h_plus_width_dynamics - h_only | keyhole recall | -0.0629 [-0.0780, -0.0487] | 0.0000 |
| h_plus_width_dynamics - h_only | brier score | -0.0011 [-0.0040, +0.0019] | 0.4489 |
| 4d_plus_width_shape_only - 4d_only | roc auc | +0.0144 [+0.0115, +0.0171] | 0.0000 |
| 4d_plus_width_shape_only - 4d_only | pr auc | +0.0147 [+0.0114, +0.0182] | 0.0000 |
| 4d_plus_width_shape_only - 4d_only | balanced accuracy | +0.0203 [+0.0094, +0.0313] | 0.0019 |
| 4d_plus_width_shape_only - 4d_only | keyhole recall | +0.0505 [+0.0319, +0.0706] | 0.0002 |
| 4d_plus_width_shape_only - 4d_only | brier score | -0.0087 [-0.0097, -0.0075] | 0.0000 |
| 4d_plus_static_width - 4d_only | roc auc | -0.0075 [-0.0109, -0.0045] | 0.0001 |
| 4d_plus_static_width - 4d_only | pr auc | -0.0077 [-0.0108, -0.0049] | 0.0000 |
| 4d_plus_static_width - 4d_only | balanced accuracy | -0.0110 [-0.0207, -0.0012] | 0.0482 |
| 4d_plus_static_width - 4d_only | keyhole recall | -0.0156 [-0.0353, +0.0031] | 0.1533 |
| 4d_plus_static_width - 4d_only | brier score | +0.0050 [+0.0035, +0.0066] | 0.0000 |
| width_dynamics_only - 4d_only | roc auc | -0.4101 [-0.4225, -0.3981] | 0.0000 |
| width_dynamics_only - 4d_only | pr auc | -0.3675 [-0.3815, -0.3533] | 0.0000 |
| width_dynamics_only - 4d_only | balanced accuracy | -0.3055 [-0.3146, -0.2962] | 0.0000 |
| width_dynamics_only - 4d_only | keyhole recall | -0.6769 [-0.6968, -0.6579] | 0.0000 |
| width_dynamics_only - 4d_only | brier score | +0.1550 [+0.1507, +0.1594] | 0.0000 |
| 4d_only - h_only | roc auc | +0.0013 [-0.0022, +0.0050] | 0.4892 |
| 4d_only - h_only | pr auc | +0.0066 [+0.0017, +0.0118] | 0.0189 |
| 4d_only - h_only | balanced accuracy | -0.0101 [-0.0183, -0.0022] | 0.0239 |
| 4d_only - h_only | keyhole recall | -0.0386 [-0.0521, -0.0240] | 0.0002 |
| 4d_only - h_only | brier score | -0.0011 [-0.0028, +0.0007] | 0.2647 |

## What we are NOT claiming
No monitoring-hardware claim, no early-warning rule, no result for the 55 simulations without a
usable trace, and no re-derivation of width — the extraction is inherited, not re-run.

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
