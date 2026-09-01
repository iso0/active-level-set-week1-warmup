# Minimum future experiment: Masinelli 2025 Level A gate

## Objective

Test one question before attempting any active-learning replay: does the fixed physics coordinate `log h` organize an independent experimental Conduction–Keyhole boundary at least as well as a comparably simple unconstrained process-parameter baseline?

This is a transfer test, not an exact replication and not experimental proof of the simulator.

## Frozen sources

- Paper: DOI [`10.1016/j.addma.2025.104677`](https://doi.org/10.1016/j.addma.2025.104677).
- Code/metadata: GitHub commit [`50ccb1bab03c626cb9f83d9c4f44182f58dda439`](https://github.com/GiulioMa/LPBF-SmartAM-Optical-Data/tree/50ccb1bab03c626cb9f83d9c4f44182f58dda439).
- Rows: `Microscopy_1.xlsx` joined to `experiment_parameters_ref.xlsx` on `(material, cube, local line)`.
- Do not use optical features or Zenodo raw signals in this first experiment.

## Population and target

Analyze alloys separately.

| Alloy | Rows | Unique `(P,VX)` groups | Binary target |
|---|---:|---:|---|
| Ti-6Al-4V | 60 | 38 | `C=0`; `T/CT/TK/K=1` (26/34) |
| 316L | 60 | 38 | `C=0`; `T/CT/TK/K=1` (37/23) |

The ten optical tracks inside a bundle are not independent labels. Exact repeated `(P,VX)` conditions are one grouping unit. Keep the raw mode code for a fixed transition-exclusion sensitivity; do not select the mapping from model performance.

## Features and models

All physical calculations use SI units: `P` in W, `VX` in m/s, and `r0=25e-6 m`.

1. **M0: generic process trend.** L2-regularized logistic regression on training-standardized `[log P, log VX]`. This is the smallest Phase-1.9-aligned specificity control because its two slopes are free.
2. **M1: physics coordinate.** Logistic regression on training-standardized `log h`, where `log h = log P - 0.5 log VX - 1.5 log r0`.
3. **M2: standard flexible baseline (secondary).** A small 2D GPC on training-standardized `[P,VX]` with one frozen kernel definition and no result-driven tuning.

Do not fit the Phase 1.7 physics-ridge residual GP in the first run. Gate it on evidence that M1 is useful and that repeated-fold fits are numerically stable.

Because `r0` is constant, M1 tests the fixed `P^1 VX^-1/2` direction only. It cannot validate the `r0^-3/2` exponent.

## Splitting and information flow

- Primary: fixed repeated grouped cross-validation within each alloy, grouping exact `(P,VX)` so duplicates never cross train/test. Use five outer folds only if every fold retains both classes; otherwise use the smallest deterministic grouped stratification that does.
- Secondary stress test: leave one cuboid pair (`A&B`, `C&D`, `E&F`) out. Interpret cautiously because `E&F` has constant power.
- Fit standardizers, models, and probability threshold on training data only.
- Use threshold 0.5 for the primary hard decision; if a calibrated threshold is added, learn it only inside nested training folds.
- Never use the paper's held-out labels for feature choice, kernel choice, transition mapping, or material-constant selection.
- Resample exact-condition groups for uncertainty; do not treat 60 rows or ten tracks per bundle as independent physical designs.

## Endpoints

Primary endpoint per alloy: paired difference `M1 - M0` in held-out ROC-AUC, with a condition-group bootstrap interval.

Secondary: PR-AUC, balanced accuracy, Keyhole recall, Conduction recall, Brier score, FN and FP. Report raw modes and performance on the fixed non-transition subset as a sensitivity, not a replacement target.

Do not import thesis B1/q20 as a primary endpoint. With only 38 unique conditions and two input dimensions, a q20 subset would be tiny and definition-sensitive. If a boundary diagnostic is later needed, predeclare a process-space nearest-opposite-label score on training-standardized `(P,VX)` and report it only as secondary.

## Decision gate

- **Advance to Level B / physics-ridge prototype:** `log h` has stable directional discrimination in Ti64, and preferably 316L, without a material increase in Brier score relative to M0.
- **Stop at static transfer result:** `log h` discriminates but the flexible or generic baseline is clearly better.
- **Do not advance:** estimates are unstable to grouping/transition handling or `log h` lacks discrimination in Ti64.

Expected cost: seconds to minutes on a laptop; no raw-signal download and no large experiment.

## Deferred Level B design

If the Level A gate passes, reconstruct the four 20-condition finite pools (`Ti64 A&B`, `Ti64 C&D`, `316L A&B`, `316L C&D`). Use each of the three power blocks as a shared label-free initial design, compare policies on the same metallographic hidden-pool labels, and count individual bundle labels rather than claiming the authors' block policy is identical to thesis margin sampling. The external query-path endpoint should be full-pool probabilistic/classification AULC; q20/B1 must not be imported automatically.

## Leakage and fairness locks

- External material constants are covariates, not labels, but their sources and phase/temperature conventions must be frozen before outcomes are inspected.
- Acquisition may not see hidden pool labels.
- Optical post-process features are excluded from process-parameter baselines.
- Identical condition repeats stay grouped.
- No universal `h` or `Ke` threshold is fitted or claimed.
- Report Ti64 and 316L separately before any pooled or normalized comparison.
