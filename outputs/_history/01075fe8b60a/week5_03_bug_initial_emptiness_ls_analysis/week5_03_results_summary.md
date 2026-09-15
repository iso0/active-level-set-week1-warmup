# Week 5 Experiment 03 results summary

## Scope

This diagnostic describes CSV label sequences, process-input distributions and existing Matérn 3/2 LOO errors. It does not relabel frames, fit a GP, alter the first-observed-Conduction raw-timestep target or make a causal claim.

## Sequence evidence

- Bug-containing simulations: 150 of 241.
- Begin with Initial Emptiness: 0 of 150 (0.0%).
- Strict first-frame Initial Emptiness followed immediately by Bug: 0 of 150 (0.0%).
- All pre-Conduction Bugs remain in the initial empty-like block: 147 of 147 (100.0%).
- Bug after a physical regime appeared: 51 of 150.

## LS and multivariable diagnostic

- Median LS: Bug 66.48 µm; no-Bug 59.86 µm.
- LS-only out-of-fold ROC AUC: 0.5952.
- Four-input out-of-fold ROC AUC: 0.5926.
- Four-input minus LS-only AUC: -0.0026.

## Revised interpretation

Screenshot Bug does not necessarily identify corrupted simulation data. The no-Bug subgroup is an operational sensitivity subset, not a confirmed higher-quality subset. The Phase 2 clean/broad prediction gap is consistent with subgroup or design heterogeneity, different input/target distributions, empty-like duration and unrecorded factors. Broad inclusion remains fixed.

## High-error review

The top 10 clean/no-Bug and top 20 broad Matérn 3/2 LOO cases are preserved without manual removal. Their target quantiles, LS, Bug status, sequence pattern, fold-local nearest-neighbour distance and process-boundary flags are saved in the accompanying CSV files.
