# RC18 protocol addendum A3 — physics-mediated cross-campaign Keyhole label model (registered before it runs; exploratory)

**Registered:** 2026-10-18 ~11:06 UTC, before any A3 run. At registration the final primary result was known; the final label arm (G3, E1, TR_E1) had not been read.

**Motivation.** A descriptive inspection (`inspection/LABEL_INSPECTION.json`, observed outputs, evaluator level) compared two classifiers trained on all OLD runs and applied to NEW:

| Classifier trained on OLD | NEW AUC | NEW BA | specificity | fast corner (VX > 0.85) AUC |
|---|---|---|---|---|
| observed outputs (log A, spike log-ratio, temperature T0) | 0.97 | 0.72 | 0.45 | 0.70 |
| x only (the Week 17 x → label transfer) | 0.84 | 0.49 | 0 | 0.50 |

So the map outputs → label transfers much better between campaigns than the map x → label. A3 tests whether this survives when NEW outputs are **predicted** from x by TRSQ, as a learner must do.

**Model** (`src/rc18_physlabel.py`; imports the frozen modules unchanged):
- **Probability:** P(K | x) = E[g(Y(x))], where Y(x) are TRSQ's predictive marginals (observation variance) of log A, spike log-ratio and temperature T0. The expectation uses 400 Monte Carlo draws.
- **Classifier g:** logistic regression (C = 1, standardised), trained at every budget on the observed outputs and labels of all OLD runs plus the paid NEW runs. Truncated records are excluded by the Q rule.

**Arms:**
- **PHYS_TR_MAXIMIN:** the label-free path from B0.
- **PHYS_TR_MARGIN:** argmin |P − 0.5| from B8, after the common 8-point start.

Budgets run to B40 on the NEW final tasks (repeats 5–8).

**Endpoints (exploratory):** BA at p ≥ 0.5, sensitivity, specificity, q20, short-K captured/total, Brier, log loss and AUC, at B0 (MAXIMIN arm), B8, B16, B24 and B40. Also BA-AULC over B8–B40, set beside the final label arm (G3_MARGIN, ACTIVE_E1_STRADDLE, TR_E1_STRADDLE and the MAXIMIN controls) on the same tasks. The label and the short-K definition are unchanged.
