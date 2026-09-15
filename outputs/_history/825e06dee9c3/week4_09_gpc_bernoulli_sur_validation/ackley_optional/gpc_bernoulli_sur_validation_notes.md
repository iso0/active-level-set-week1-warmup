# Week 4 Experiment 09 Notes: Thresholded 4D Ackley

## Setup

- Fixed-kernel GP classifier, pool `4000`, test `10000`, initial `12`, budget `80`.
- Reference-set size requested: `1500`.
- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.

## Result

- Best q20: `classifier_entropy` = `0.421`.
- Best q30: `classifier_entropy` = `0.380`.
- `classifier_uncertainty_repulsion` q20/q30 = `0.422` / `0.381`.
- `gpc_bernoulli_sur_refit_k15` q20/q30 = `0.428` / `0.385`.
- `gpc_bernoulli_sur_refit_k25` q20/q30 = `0.426` / `0.395`.

## Caveats

- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.
- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.
