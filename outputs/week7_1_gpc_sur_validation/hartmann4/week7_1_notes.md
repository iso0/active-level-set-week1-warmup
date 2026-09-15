# Week 7.1 Notes: Thresholded 4D Hartmann

## Setup

- Fixed-kernel GP classifier, pool `4000`, test `10000`, initial `12`, budget `80`.
- Reference-set size requested: `1500`.
- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.

## Result

- Best q20: `gpc_bernoulli_sur_refit_k25` = `0.373`.
- Best q30: `gpc_bernoulli_sur_refit_k25` = `0.315`.
- `classifier_uncertainty_repulsion` q20/q30 = `0.385` / `0.326`.
- `gpc_bernoulli_sur_refit_k15` q20/q30 = `0.375` / `0.316`.
- `gpc_bernoulli_sur_refit_k25` q20/q30 = `0.373` / `0.315`.

## Caveats

- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.
- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.
