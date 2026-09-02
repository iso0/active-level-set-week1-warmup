# Week 9 Phase 1.14 — M3-margin active acquisition

## Decision: LATE_ACQUISITION_GAIN_ONLY

## Clean primary comparison
P0 M3-on-A0 q20 AULC: 0.842490809.
P1 M3-margin q20 AULC: 0.844623162.
P1-P0: +0.002132 [-0.001167, +0.005621], repeats +/0/- = 12/0/8.
The evaluator/model is M3 in both arms; only the revealed-label path changes.

## Early and late
Early B16-40: -0.001556 [-0.007525, +0.004106].
Late B41-80: +0.004510 [+0.000120, +0.009020].

## q20 checkpoints
B16 P0/P1 accuracy 0.7859/0.7859; balanced accuracy 0.7719/0.7719; KH recall 0.7221/0.7221; C recall 0.8217/0.8217.
B40 P0/P1 accuracy 0.8494/0.8465; balanced accuracy 0.8363/0.8271; KH recall 0.7724/0.7487; C recall 0.9001/0.9054.
B80 P0/P1 accuracy 0.8576/0.8612; balanced accuracy 0.8321/0.8359; KH recall 0.7327/0.7383; C recall 0.9314/0.9336.

## Sample efficiency
- 0.80: P0: reached 20/20, median B17; P1: reached 20/20, median B17 (non-crossings censored).
- 0.82: P0: reached 20/20, median B18; P1: reached 20/20, median B18 (non-crossings censored).
- 0.84: P0: reached 20/20, median B24; P1: reached 20/20, median B26 (non-crossings censored).

## Path behavior
Median first divergence: B17; median A0/P1 Jaccard B40/B80: 0.600/0.702.
P1 queried-Keyhole fraction: 0.420; same-step query disagreement with A0: 0.981.

## Robustness
q30 P1-P0: +0.003588 [+0.001194, +0.006091].
At B40, q20 Keyhole recall changes by -0.0237; the late positive AULC result must not hide this early recall cost.
At B80 full81 P0/P1 accuracy 0.9685/0.9691, KH recall 0.8755/0.8775, Brier 0.0274/0.0263.
P1 all-budget residual-SD upper-hit 72.0%; any-length upper-hit 79.4%; convergence 95.5%.
L100/L1000 sensitivity: median B80 path Jaccard 1.000, mean q20 AULC delta +0.0004, L1000 convergence 96.0%.

## Safe interpretation
Severe global degradation: False; acquisition numerically unstable under the predeclared rule: False.
Further physics/residual-aware acquisition work is qualified as a follow-up: the late-region gain coexists with unresolved overall gain and a B40 Keyhole-recall cost.
This is pool-based active-learning replay on one deterministic simulator dataset. It does not establish universal acquisition superiority, theoretical sample complexity, external transfer, or causal ARD importance.
