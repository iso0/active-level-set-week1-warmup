# Week 12 startup diagnosis

This is post-hoc developmental and exploratory evidence on the already-open NEW-136 cohort. It reconstructs the exact 100 frozen feature-only maximin orders and does not design or benchmark a replacement startup rule.

## Main findings

The cohort contains 124 Keyhole and 12 non-Keyhole runs. All 100 training pools contain both classes, while the frozen B16 contains both classes in 97/100 pools. Continuing the same label-blind maximin order discovers both classes at median query 4; only the three frozen failures require more than B16: external__r003_f04 at 18, external__r019_f04 at 19, and external__r009_f05 at 24.

The rare class is concentrated in high VX: 11 of 12 non-Keyhole runs have VX at least 0.898 m/s, with one low-VX exception at 0.332 m/s. Its log-h range overlaps the Keyhole range, so log-h is a directional search coordinate rather than a deterministic label rule. The rare points also have nearby Keyhole points in standardized input space; this means geometric coverage can still represent the high-VX region even when it fails to capture a rare non-Keyhole label.

## Analytic reference

For each fixed training pool and prefix size k, the descriptive uniform-without-replacement single-class probability is [C(n0,k)+C(n1,k)]/C(N,k). Its complement is the analytic CDF of discovering both classes by k under uniform sampling without replacement. The reported values are conditioned on the observed training-pool class counts and are not a formal baseline superiority test.

## Geometry caution

Covariance effective dimension summaries are descriptive only. Twelve rare points are insufficient for a causal or manifold claim, and no dimension-based rule was tuned.

## Reproducibility

The full orders, per-query class labels, three failure-prefix tables, rare-class/OLD-support table, analytic references, parity checks, figures, configuration, provenance, and QC are saved beside this report. Saved Week11 artifacts remain untouched.
