# Week 4 Experiment 09 Slide Notes

## Question

Does fixed-kernel GP-classifier Bernoulli SUR refit generalize beyond the promising Week 4 Experiment 08 seed-0 result?

## Setup

- Fixed GP classifier, no optimized kernel.
- Baselines: random, margin, entropy, uncertainty repulsion.
- SUR shortlists: k15 and k25 by default.
- Primary metrics: q20 and q30 near-boundary error.

## Results

- branin: best q20 `classifier_uncertainty_repulsion` = `0.256`, best q30 `classifier_uncertainty_repulsion` = `0.190`.
- hartmann4: best q20 `gpc_bernoulli_sur_refit_k25` = `0.373`, best q30 `gpc_bernoulli_sur_refit_k25` = `0.315`.
- ackley: best q20 `classifier_entropy` = `0.421`, best q30 `classifier_entropy` = `0.380`.

## Message

Do not overclaim: SUR is acquisition-expensive and should be kept only if five-seed q20/q30 gains justify the runtime.
