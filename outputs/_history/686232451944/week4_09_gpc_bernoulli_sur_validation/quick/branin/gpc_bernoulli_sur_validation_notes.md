# Week 4 Experiment 09 Notes: Thresholded Branin

## Setup

- Fixed-kernel GP classifier, pool `260`, test `600`, initial `6`, budget `10`.
- Reference-set size requested: `1500`.
- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.

## Result

- Best q20: `gpc_bernoulli_sur_refit_k15` = `0.367`.
- Best q30: `gpc_bernoulli_sur_refit_k15` = `0.283`.
- `classifier_uncertainty_repulsion` q20/q30 = `0.458` / `0.439`.
- `gpc_bernoulli_sur_refit_k15` q20/q30 = `0.367` / `0.283`.
- `gpc_bernoulli_sur_refit_k25` q20/q30 = `0.383` / `0.294`.

## Caveats

- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.
- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.
