# Week 18 claim ledger

Labels: HISTORICAL (OLD data analysed before NEW existed / earlier weeks' frozen results), POST-HOC (NEW or pooled
data analysed after the fact), DEVELOPMENT (Week 18 DEV blocks / DEV reps; exploration), SPLIT-CONFIRMATION (a locked
real confirmation block used once after a pushed freeze), HELD-OUT-SYNTHETIC (fresh-seed stress worlds after a
freeze), SEMI-SYNTHETIC (digital twins fitted to real data; fresh reps after a freeze when used confirmatorily),
THEOREM (proved, known, or derived — status stated). Pointers are relative to `outputs/week18_independent_research/`.

## Re-verified or corrected earlier conclusions
| id | claim | label | evidence |
|---|---|---|---|
| V1 | The NEW "random beats margin" exception (Week 17) is an ML-II × random-design interaction plus seed noise: margin BA AULC ≈ 0.66 under fixed OLD hyperparameters and per-step ML-II with both seed schemes; random gains +0.023–0.026 from ML-II; random − margin = −0.022 / −0.003 (fixed) vs +0.002 / +0.020 (ML-II). | POST-HOC | phase0/ |
| V2 | Week 17 report: mean M3 − G3 over the 12 held-out cells is −0.102, not −0.110. | HISTORICAL (erratum) | ERRATA.md E18-1 |
| V3 | has_keyhole on OLD is the level set {max depth ≥ ≈ 111 µm} to within one run (AUC 1.000). | HISTORICAL | DATA_AUDIT.md §2 |
| V4 | The OLD→NEW "level shift" in log h is a region effect: in the overlap the thresholds agree (20.91 vs 20.94); a NEW campaign offset adds +0.001 nats to the pooled GPC evidence. | POST-HOC | DATA_AUDIT.md §3 |
| V5 | Week 7's depth-GPR result reproduces on the new benchmark: GPR on log max depth + straddle vs G3 + margin, R3_OLD BA AULC +0.021 [0.014, 0.030], queries to G3's B80 level 32 vs 56; R2rev +0.012 [0.007, 0.016]; q20 lower (0.817 vs 0.842). | DEVELOPMENT (HISTORICAL data) | phase2/contrasts_real.csv, qtt_real.csv |
| V6 | Week 17's held-out conclusion "M3 ≪ G3" (−0.10 NSD AULC) does not transfer to the real OLD / POOLED tasks (M3 − G3 = +0.006 / +0.002 BA AULC, DEV); it does on NEW (−0.070). | DEVELOPMENT | phase2/contrasts_real.csv |
| V7 | Real tasks share no ordering of the five common baselines (mean Kendall τ between real tasks 0.00); twins agree with real tasks slightly better (0.22) than the Week 17 cells (0.16). Rankings are task-dependent; no synthetic family validates as a proxy for "the" real ranking. | DEVELOPMENT | phase2/external_validity_*.csv |
| V8 | Random refinement is the worst G3 rule on every real task except NEW-like pools and on every twin except two NEW-like twins. | DEVELOPMENT | phase2/contrasts_*.csv |

## Data decisions
| id | claim | label | evidence |
|---|---|---|---|
| D-1 | Pooling OLD + NEW (541 runs) is legitimate for a flexible 4-D GPC: overlap agreement 94.4%, a NEW offset adds +0.001 nats. In a 1-D log-h model the NEW threshold is higher by +0.17 [0.03, 0.29] overall and +0.01 [−0.14, 0.28] in the overlap: campaign shift vs region effect is **not decidable** (erratum E18-3). POOLED_STD (500) as sensitivity. | POST-HOC | DATA_AUDIT.md §3 + amendment, phase4/astra3_* |
| D-2 | The 49 Bug simulations stay excluded (eligibility unresolved). | — | DATA_AUDIT.md §4 |
| D-3 | NEW continuous outputs are not in the repository (owner decision D1 open); all depth results are OLD-only or partial-depth. | — | RESEARCH_LOG.md |

## Astra Round 3 (outputs/astra_round3/; integrated as hypotheses, THEORY_WEEK18.md last section)
| id | claim | label | evidence |
|---|---|---|---|
| A3-1 | L3, C10 (−1/9), R5 (−1/210), P5 re-derived exactly; D4 rank bound holds on OLD/NEW/POOLED with the log-h order. | THEOREM (independent check) | phase4/astra3_checks.json, astra3_D4_real.csv |
| A3-2 | Week 16's "remaining gap = model information" is replaced by the narrower attribution statement. | HISTORICAL (erratum E18-4) | ERRATA.md |
| A3-3 | Week 16 martingale "max 4.3" = max of state medians (candidate max 7.158); the B24 saturation illustration is not saturated. | HISTORICAL (erratum E18-5) | ERRATA.md |
| A3-4 | "Level shifts, order survives": order survives (AUC 0.99 / 0.86); the level shift is not decidable from the overlap. | POST-HOC | ERRATA E18-3 |

## Theory (status in THEORY_WEEK18.md)
| id | claim | status |
|---|---|---|
| T18-1 | Binary threshold localization needs ⌈log₂(N+1)⌉ queries; censored affine branch 2; censored smooth branch saves only on fine pools. | KNOWN / PROVED / NUMERICALLY CHECKED |
| T18-2 | Pool floor N^{−α/(α+d−1)}; saturation budget N^{(d−1)/(α+d−1)}. Checks: no rule/model headroom at B_max on R1/R2 (held); saturation budget ≈ 40 for N = 108…866 on the T_GP twin, flat in N (nonparametric law refuted for this boundary; index-like). | KNOWN / DERIVED; checks NUMERICALLY CHECKED / SEMI-SYNTHETIC |
| T18-3 | Binary source labels cannot identify a target level shift (only nesting); index structure or continuous source values reduce the target to a 1-D threshold search. | PROVED |
| T18-4 | Information per query: binary probit Fisher information decays as φ(m)²/(Φ(m)Φ(−m)); exact depth carries 1/σ² everywhere. | KNOWN (application PROVED) |
| T18-5 | ML-II under boundary-concentrated designs: shorter length-scales and harmful hyperparameters at b = 40 (twins −0.03…−0.05, real OLD −0.10 BA); amplitude unidentified (at the bound under both designs), not inflated; effects ≤ 0.015 at b ≥ 80. | CONJECTURE partly refuted (NUMERICALLY CHECKED; real part POST-HOC) |

## Method claims (Phase 3 / 5)
| id | claim | label | evidence |
|---|---|---|---|
| M1 | Where every paid simulation reports max depth, GPR on log depth + straddle (E1) beats G3 + margin: R3_OLD +0.0285 [0.010, 0.047] BA AULC and 66% fewer simulations [44, 74] to G3's B80 accuracy; R2rev +0.012 [−0.001, 0.024]. | SPLIT-CONFIRMATION (block C1, freeze fc1afb50) | round_1/ |
| M2 | Same on fresh digital-twin seeds: T_DEPTH +0.082 [0.041, 0.125], T_TOBIT OLD +0.062 [0.028, 0.104] NSD AULC; NEW-like twin +0.009. | SEMI-SYNTHETIC (fresh reps, frozen) | round_1/ |
| M3 | E1's gain is largest at small budgets (R3_OLD BA 0.927 vs 0.863 at B24), as predicted by T18-4 / P-T18-1. | SPLIT-CONFIRMATION (descriptive) | round_1/ |
| M4 | With partial depth (NEW runs without depth) E1 is worse than G3 on POOLED (−0.037 [−0.050, −0.026]); a mixed-likelihood GP (E3) using the label-only rows does not fix it (−0.031). | DEVELOPMENT | phase3/depth2/ |
| M5 | E1 is fragile to stale hyperparameters: ML-II every 8 queries instead of per step turns R2rev +0.012 into −0.081. | DEVELOPMENT | phase3/depth2/ |
| M7 | E1 survives depth stress: no world below −0.03 NSD AULC (worst 25% depth noise −0.018 [−0.077, 0.034]); gains under threshold drift (+0.052) and 30% missing depth (+0.033). | HELD-OUT-SYNTHETIC (round-1 seeds) | round_1/stress_depth_* |
| M8 | For binary labels no Week 18 candidate improves on G3 + margin: G3 on log inputs, nested-start LT and a 25% exploration mixture are all within ±0.011 BA AULC (intervals include 0); at B_max G3 + margin equals its full-pool ceiling on R1/R2. | DEVELOPMENT (paired screening) | phase3/cfa/, phase3/headroom/ |
| M9 | On NEW the label is not a max-depth threshold (AUC 0.891; 7/12 non-Keyhole runs ≥ 111 µm, fast scans). | POST-HOC (descriptive, after D1) | phase1/new_depth*.csv, DATA_AUDIT amendment 2 |
| M10 | With depth for every run, E1 does not improve POOLED (C2 +0.004 [−0.001, 0.009]) and is worse on NEW (C2 −0.022). | SPLIT-CONFIRMATION (block C2, freeze 1d560792) | round_2/ |
| M11 | The OLD improvement replicates in direction but not at the pre-registered size: R3_OLD C2 +0.016 [0.013, 0.020] (bar +0.02); QTT −12% (C1 −66%). | SPLIT-CONFIRMATION (block C2) | round_2/ |
| M6 | q20 (historical) does not improve with E1: R3_OLD −0.003 n.s. (round 1), R2rev −0.024 (round 1), DEV −0.026 / −0.045. | SPLIT-CONFIRMATION + DEVELOPMENT | round_1/, phase2/ |
