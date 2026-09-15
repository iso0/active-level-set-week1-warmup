# FINAL Phase 1.19A report

## Scope and frozen integrity

This diagnostic/falsification audit starts from `255207857d22a9823f67cb1a23d9b71bdc12ec1c`. It generated no acquisition trajectory, pseudo-label training, censored GP, label change, or q20/q30 change. Earlier artifacts were read in place and not copied.

## Q1 — Configuration and observation window

Exact folder semantics produce three configurations: 364 main (70 KH), plus 41 non-main rows. In total, 167/405 observations end before the laser reaches 90% of the verified x-domain under `TE < 0.9[min(XF,XL)+12 µm]/VX`. This is a credible observation-window sensitivity because `has_keyhole` is an ever-observed label, but it does not prove mislabelling or justify relabelling.

Main-configuration-only model sensitivity:
- H: balanced accuracy 0.9348; ROC-AUC 0.9914
- G3: balanced accuracy 0.9532; ROC-AUC 0.9923
- M3: balanced accuracy 0.9456; ROC-AUC 0.9947

M3 retains the best ROC-AUC and Brier score, while G3 has the highest balanced accuracy and Keyhole recall. Thus the broad predictive strength survives, but “strongest” is metric-dependent on this restricted subset.

Decision: **CONFIGURATION_SENSITIVITY_REQUIRED**.

## Q2 — Maximum-depth censoring

The label-free upper-tail gap identifies 39 likely floor-censored rows, 39 of them Keyhole. D0/D1/D2 fixed-Ridge sensitivities are reported in `depth_sensitivity.csv`. The pile affects continuous-depth interpretation but does not directly challenge the binary level-set target.

Decision: **DEPTH_CENSORING_CONFIRMED**.

## Q3 — Stage-1 separation and calibration

At B16 the Stage-1 coefficient median is 20.978 (q10–q90 2.904–80.252); 55.0% of prefixes are exactly separable. Perfect-separation fractions are 39.0% at B20 and 9.0% at B24. At B16, H vs M3 held-out Brier scores are 0.0483 vs 0.0489; log losses are 0.3744 vs 0.3826. Exact separation plus coefficient growth across fixed C is consistent with logistic separation; held-out scores determine the probability-quality conclusion.

Historical residual/ARD associations are descriptive Spearman relations only, not causal evidence.

Decision: **STAGE1_OVERCONFIDENCE_MIXED**. This does not invalidate M3's established predictive decision quality.

## Q4 — Monotonic structure

The full pool contains 22,050 comparable directed pairs (27.0% of all unordered pairs) and 3 violations, rate 0.013605%. The main configuration has 19,491 comparable pairs and 3 violations: the exceptions do not disappear. Exact antichain width is 93. The retrospective oracle hard rule produces 6 wrong implication edges, so any future use must be soft/robust and prospectively tested.

Decision: **MONOTONIC_STRUCTURE_STRONG**.

## Letham et al. and next gate

Letham et al.'s closed form is a probit/MVN-latent Bernoulli-LSE derivation. It does not directly apply to logistic/Laplace M3. Phase 1.18B's hypothetical-refit `p(1-p)` objective is not GlobalSUR. No Letham trajectory was implemented.

Next gate: **NEXT_MONOTONE_POOL_LSE** — The partial order is directly and strongly supported. Letham's closed form is not directly applicable to logistic M3 and would first require a probit-model audit.

## Narrowest safe thesis interpretation

The frozen SPH benchmark contains configuration/observation-window and continuous-depth-censoring caveats. Despite them, the binary label is almost monotone in the physically motivated `(P up, VX down, LS down)` order and the main-config-only predictive results remain directly auditable. Stage-1 probability extremity must be separated from M3 hard-decision quality. No sample-efficiency, causal, relabelling, or industrial-validity claim follows from this audit.
