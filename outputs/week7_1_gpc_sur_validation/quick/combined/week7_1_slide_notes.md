# Week 7.1 Slide Notes

## Question

Does fixed-kernel GP-classifier Bernoulli SUR refit generalize beyond the promising Week 7 seed-0 result?

## Setup

- Fixed GP classifier, no optimized kernel.
- Baselines: random, margin, entropy, uncertainty repulsion.
- SUR shortlists: k15 and k25 by default.
- Primary metrics: q20 and q30 near-boundary error.

## Results

- branin: best q20 `gpc_bernoulli_sur_refit_k15` = `0.367`, best q30 `gpc_bernoulli_sur_refit_k15` = `0.283`.
- hartmann4: best q20 `classifier_uncertainty_repulsion` = `0.412`, best q30 `classifier_uncertainty_repulsion` = `0.446`.

## Message

Do not overclaim: SUR is acquisition-expensive and should be kept only if five-seed q20/q30 gains justify the runtime.
