# Week 18 benchmark specification (locked before method work)

Code: `src/week18_tasks.py` (real), `src/week18_twins.py` (S1/S2), `src/week18_engine.py` (AL engine).

## Tasks
| Task | Data | Paid pool / test | Prior (free) | Budgets | Label |
|---|---|---|---|---|---|
| R1_POOLED | OLD ∪ NEW (541; 33.6% KH) | 4 folds (≈ 431) / 1 fold (≈ 110), stratified campaign × class, seed [1818, rep] | — | 16–120 step 8 | POST-HOC/HISTORICAL; confirmation = SPLIT-CONFIRMATION |
| R1_POOLED_STD | 500 standard-settings runs | as R1 | — | as R1 | sensitivity |
| R2_TRANSFER | NEW, Week 11/12 frozen splits | NEW training pool 108 / NEW test 28 | all 405 OLD labels | 16–80 step 4 | POST-HOC |
| R2rev_TRANSFER | OLD, Week 8.5 runs | OLD training pool 324 / test 81 | all 136 NEW labels | 16–120 step 8 | HISTORICAL |
| R3_NEW | NEW frozen splits | 108 / 28 | — | 16–80 step 4 | POST-HOC (continuity) |
| R3_OLD | Week 8.5 runs (depth available) | 324 / 81 | — | 16–120 step 8 | HISTORICAL (continuity) |
| S1 twins | truths T_GP, T_GBT, T_NW, T_QL (fitted to the 541 pooled labels) × input distribution {pooled 433, OLD 324, NEW 108}; T_DEPTH (OLD log-depth GPR) × OLD 324 | pool / test 25% of pool size (≥ 28) + 6,000 dense truth points | — | as the matching real task | SEMI-SYNTHETIC |
| S2 stress | Week 17 cell generator with fresh seed base 1818; NEW-like rare-pocket world; two-campaign world | per cell | per cell | 16–80 / 16–120 | HELD-OUT-SYNTHETIC |
Startup: 8 maximin points of the paid pool (seed = task seed + [2]) + maximin continuation until both classes are
revealed (counting the prior); every paid query counts.

## Blocks (locked)
Real repeats (R1–R3): **DEV 1–8; C1 9–12; C2 13–16; C3 17–20.** Each confirmation block is used at most once
and only after a pushed freeze. Twins/stress: DEV reps 0–7; confirmation round k uses fresh reps 100k–100k+7.

## Hyperparameter treatment of baselines
Per-step ML-II (`mlii`) when the fitted set is ≤ 200 rows; ML-II every 8 paid queries with warm start
(`mlii_k8`) in R2/R2rev (prior + paid ≈ 450–540 rows). G3 with fixed OLD-fitted hyperparameters (Week 15
setting) on R2/R3_NEW. Safeguarded Laplace everywhere; fixed-point error recorded for every fit.

## Baselines reproduced (Phase 2)
G3 + margin; G3 + random; G3 + Candidate B (exact historical selector); LT + margin; M3 + margin; H + margin;
G3(fixed OLD hypers) + margin / random (R2, R3_NEW); GPR-depth + straddle (Week 7 formulation; tasks with depth).

## Metrics (locked)
Real: pooled-per-repeat BA AULC (trapezoid over the budget grid, normalized by the grid width), rare-class
recall at B_max, AUC, Brier, historical q20 mean-fold AULC (R2/R3 NEW and OLD; for POOLED the same construction
on the pooled batch, labelled "pooled-q20", not historical), DC-BD AULC, **queries-to-target (QTT)**: paid queries
for the repeat-pooled BA curve to reach G3 + margin's DEV mean BA at B40 and at B80 (censored at B_max).
Synthetic/semi-synthetic: NSD (τ = 0.1 in the unit twin box / unit box) AULC, ASSD, dense BA, QTT on NSD.
Convergence: fraction of fits with fixed-point error > 1e-6 (must be 0).

## External-validity check (Phase 2)
Kendall/Spearman agreement between baseline rankings on (a) S1 twins, (b) Week 17 held-out cells, and (c) the
real tasks R1–R3 (DEV). If (b) fails to predict (c) while (a) does, earlier synthetic conclusions are re-labelled
accordingly in REPORT.md.
