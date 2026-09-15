# Week 7.1 Notes: Thresholded 4D Hartmann

## Setup

- Fixed-kernel GP classifier, pool `360`, test `800`, initial `12`, budget `16`.
- Reference-set size requested: `1500`.
- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.

## Result

- Best q20: `classifier_uncertainty_repulsion` = `0.412`.
- Best q30: `classifier_uncertainty_repulsion` = `0.446`.
- `classifier_uncertainty_repulsion` q20/q30 = `0.412` / `0.446`.
- `gpc_bernoulli_sur_refit_k15` q20/q30 = `0.450` / `0.479`.
- `gpc_bernoulli_sur_refit_k25` q20/q30 = `0.512` / `0.517`.

## Caveats

- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.
- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.
