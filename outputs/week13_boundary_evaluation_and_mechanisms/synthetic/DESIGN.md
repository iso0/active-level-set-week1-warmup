# Week 13 synthetic study — design fixed before the full run

Evidence category: **CONTROLLED METHODOLOGICAL EVIDENCE** (synthetic, known boundary).
It is not real-data validation and makes no claim about the SPH simulator.

Written 2026-10-03 after a 48-path smoke test on replicate 0 / pool 108 only
(used to check that code runs and that labels are not trivially separable).
No parameter below was changed after looking at full-run results.

## Generator (src/week13_synthetic.py)

- u in [0,1]^4 with roles (log P, log VX, log LS, ST).
- Physics score s(u) = 2.2 u1 - 0.8 u2 - 1.2 u3 (spread of log h over the OLD box).
- Latent f(u) = 4 (s(u) - c) - A * bump(u), bump centred at high P / high VX / small LS,
  sharp along VX (scale 0.12), broad along P and LS (0.35), absent in ST.
- A = 1.5, c = 0.818 calibrated so the OLD-like box has 18% class 1; the NEW-like corner
  box (u1 >= 0.8, u3 <= 0.2, ST range doubled) then has about 9% class 0, 98% of which is
  created by the bump (the physics law is locally wrong there).
- Observed labels y = 1[f + sigma * eps > 0], eps iid N(0,1) per case; sigma in {0.5, 1.0}.
  sigma = 0.5 was chosen because the OLD-like full-pool q20 accuracy (~0.82) is close to the
  real OLD all-label M3 value (0.855). The **estimand is the noise-free level set {f = 0}**.

## Factors

scenario {BAL 50/50 whole box, OLD, NEW} x sigma {0.5, 1.0} x pool {108, 324}
(independent evaluation pool of 136 / 405) x policy {random, margin, coverage, maximin}
x model {G zero-mean GPC, P physics trend + GPC discrepancy with variance capped at 1}
x 30 independent replicates = 2,880 paths. Kernel hyperparameters are oracle values fitted once
per (scenario, sigma) on 500 labelled cases and then held fixed, so that acquisition is not
confounded with hyperparameter learning.

Startup: 8 maximin points, maximin continuation until both classes are observed; every query
counts toward B80; before discovery the predictor is the constant observed class.

## Metrics

Finite evaluation pool (observed labels): q20 accuracy (historical construction), q20 balanced
accuracy, full balanced accuracy, minority recall, Gabriel boundary-edge BER / BEBA / BEF1.
Dense truth (20,000 uniform points, noise-free labels): NSD at tau in {0.05, 0.1, 0.2}
(surface Dice), ASSD, dense balanced accuracy. Reference rows: constant majority and
full-pool ceiling for each replicate/model.

## Pre-specified questions

- **H1 metric validity.** Within each scenario/sigma/pool cell, the Spearman correlation across
  all (path, dense budget) predictors between each finite metric and NSD_0.1 (and -ASSD).
  Expectation: q20 accuracy degrades in the imbalanced NEW cell relative to BAL; boundary-edge
  metrics do not.
- **H2 constant predictor.** Where does constant-majority rank under each finite metric?
- **H3 acquisition headroom.** AULC B16-B80 of NSD_0.1 and q20 accuracy: ceiling minus random
  versus margin minus random, by pool size; does the q20 ranking of margin vs random
  disagree with the NSD ranking in NEW?
- **H4 model versus acquisition.** Is the acquisition gain (margin - random, NSD AULC) larger for
  the better predictive model?
- **H5 rare exhaustion.** Labelled minority / pool minority at B16, B40, B80 by policy.

Inference: replicate is the independent unit; paired differences across the 30 replicates with
percentile bootstrap intervals. No multiplicity adjustment; results are descriptive of the
generator, not of SPH.
