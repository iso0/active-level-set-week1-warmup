# FINAL METHOD REPORT — PG-RMBC

Project: `week10-pg-rmbc-internal-replication`  
Study type: **predeclared internal replication on the same frozen 405 simulations**  
Method name: Physics-Guided Robust Monotone Boundary Coverage (provisional; no novelty claim)  
Classification: **NO_CLEAR_IMPROVEMENT**  
Final decision: **KEEP_PHASE121_CANDIDATE_B**

## Primary result

Candidate B q20 accuracy AULC B16–B40: **0.838023**.  
Full PG-RMBC: **0.835421**.  
Paired P4−P1: **-0.002602 [-0.006295, +0.001074]**, positive repeats 24/60, sign-flip p=0.173398, Holm p=0.189678.

B40 q20 Keyhole-recall difference: **-0.003086** (guardrail ≥−0.03).  
B80 full81 accuracy difference: **-0.000329** (guardrail ≥−0.01).  
Safety/leakage audit: **PASS**.

## Answers to the eight frozen questions

1. **Does h initialization beat inherited feature-space initialization?** P2−P1 is -0.011565 [-0.016307, -0.006773] on the primary endpoint. Mean effective seed sizes were P1=8.00 and P2=2.00. This is the predeclared initialization ablation.
2. **Does soft monotone leverage improve Phase 1.21 coverage?** P3−P1 is -0.002888 [-0.006156, +0.000392]. On the frozen primary rule this is classified **UNRESOLVED**.
3. **Does the adaptive physics-to-M3 switch help?** The requested five arms do not separately identify a pure switch effect. P4 changes initialization and the RMBC acquisition jointly, while P3 fixes the switch at B40 under a different seed. The only valid statement is the algebraic adaptive/interaction remainder below. P4 switching behavior: 300/300 runs switched; median B10.0.
4. **Does full PG-RMBC clearly beat Candidate B?** **NO_CLEAR_IMPROVEMENT** under the pre-frozen +0.005 material-effect and interval rules.
5. **Where does the gain come from?** Algebraically on primary AULC: total P4−P1=-0.002602; initialization P2−P1=-0.011565; monotone-acquisition P3−P1=-0.002888; remaining adaptive/interaction=+0.011850. These are additive contrasts, not causal percentages.
6. **Keyhole-recall safety?** Maintained under the frozen B40 and B80 guardrails.
7. **Did monotonicity help as a soft query prior?** **UNRESOLVED** for the direct P3−P1 ablation. Regardless of outcome, no monotone inference entered training or candidate eligibility.
8. **Which one policy is frozen for genuinely new Ioan data?** `P1_PHASE121_CANDIDATE_B`. No further tuning is authorized after this experiment.

## Mechanism diagnostics

P4 h-separable fractions were B16: 0.053, B20: 0.047, B24: 0.043, B32: 0.037, B40: 0.010. Selected-query U/C/M and G-count distributions are in `monotone_leverage_diagnostics.csv`; path overlaps against Candidate B are in `query_path_overlap.csv`; q20 FP/FN trajectories are in `error_decomposition.csv`. The monotonicity-disagreement score is diagnostic only and never entered acquisition.

- The h-maximin seed contained both classes after exactly 2 true queries in all 300 P2 runs and all 300 P4 runs. The inherited Phase 1.21 seed used 8 in every P1/P3 run; P0 used 16.
- P4 switched in all 300 runs, at mean budget 11.33, median B10, range B7–B45. This explains why only 5.3% of P4 runs remained h-separable at B16.
- Across P4 queries selected by RMBC itself, mean selected `U=0.432`, `C=2.140`, `M=5.485`, `G_KH=5.762`, and `G_C=7.561`. Median `M`, `G_KH`, and `G_C` were all zero, so large leverage was concentrated in a minority of selections rather than being uniformly available.
- From query orders B16–B40, 74.5% of P4 selections lay inside the currently estimated band. P4/P1 query-set Jaccard was 0.239 at B24, 0.373 at B32, 0.484 at B40, and 0.821 at B80.
- At B40, Candidate B averaged 0.937 q20 false positives and 1.620 false negatives per outer run; P4 averaged 0.910 and 1.643. The small FP improvement did not compensate for the earlier accuracy/recall deficit created by the two-point seed.
- The diagnostic M3 monotonicity-disagreement score at P4 RMBC-selected queries had mean `2.1e-17` and median zero. There is no evidence here that PG-RMBC naturally concentrated on posterior order-disagreement regions; this remains a future hypothesis, not an acquisition component.

## Secondary endpoints: P4 minus Candidate B

| Endpoint | Mean paired difference | 95% interval |
|---|---:|---:|
| q20 accuracy AULC B16–B80 | -0.001039 | [-0.003370, +0.001138] |
| q20 balanced-accuracy AULC B16–B40 | -0.004146 | [-0.008037, -0.000244] |
| q20 balanced-accuracy AULC B16–B80 | -0.001172 | [-0.003567, +0.001142] |
| q20 Keyhole-recall AULC B16–B40 | -0.009513 | [-0.018400, -0.000701] |
| q20 Keyhole-recall AULC B16–B80 | -0.002126 | [-0.006751, +0.002495] |
| q30 accuracy AULC B16–B40 | -0.001536 | [-0.004750, +0.001581] |
| q30 accuracy AULC B16–B80 | -0.000809 | [-0.002709, +0.001034] |
| full81 accuracy AULC B16–B80 | -0.000341 | [-0.001011, +0.000309] |

The early balanced-accuracy and Keyhole-recall intervals are below zero even though the predeclared B40 and B80 safety guardrails pass. This reinforces the decision not to replace Candidate B.

## Descriptive sample-efficiency crossings

Relative to Candidate B's mean q20 accuracy at its B24/B32/B40 checkpoints, P4 first crossed the same levels at B26/B34/B39: respectively 2 more, 2 more, and 1 fewer query on these non-monotone mean curves. P2 required B31/B39/B49. These are descriptive crossings only and are not simulator-saving claims.

The sample-efficiency table reports first mean-curve crossings of Candidate B's B24/B32/B40 q20 accuracy. These are descriptive finite-pool comparisons, not guaranteed simulator savings.

## Scientific interpretation and boundaries

The strongest allowed interpretation is conditional on the decision above: a physics-guided strategy using monotone structure only as a soft query prior was prospectively tested on the frozen SPH benchmark. This is not external validation. It establishes neither universal monotonicity, theoretical sample-complexity improvement, guaranteed savings, exact physical-boundary geometry, industrial safety, nor novelty relative to the literature. External evidence must come from Ioan's genuinely new simulations under a separately frozen blind protocol.

## Final required decision

**KEEP_PHASE121_CANDIDATE_B**
