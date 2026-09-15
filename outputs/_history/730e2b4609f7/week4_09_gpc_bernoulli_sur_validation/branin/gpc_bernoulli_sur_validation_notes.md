# Week 4 Experiment 09 Notes: Thresholded Branin

## Setup

- Fixed-kernel GP classifier, pool `1500`, test `4000`, initial `6`, budget `50`.
- Reference-set size requested: `1500`.
- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.

## Result

- Best q20: `classifier_uncertainty_repulsion` = `0.256`.
- Best q30: `classifier_uncertainty_repulsion` = `0.190`.
- `classifier_uncertainty_repulsion` q20/q30 = `0.256` / `0.190`.
- `gpc_bernoulli_sur_refit_k15` q20/q30 = `0.266` / `0.202`.
- `gpc_bernoulli_sur_refit_k25` q20/q30 = `0.286` / `0.217`.

## Caveats

- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.
- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.
