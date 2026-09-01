# Week 9 Phase 1.12 — GPC Kernel Adequacy / Anisotropy Control

## Decision: KERNEL_GAP_CLOSED

## Primary same-path result
All six models received identical frozen A0 prefixes. q20 AULC was H 0.830813, G0 0.813520, G1 0.812822, G2 0.822619, G3 0.826595, and G4 0.812160.
Primary G3-G0: +0.013074 [+0.005624, +0.020216] (16/20 positive repeat blocks).
Key G3-H: -0.004219 [-0.011287, +0.002973]. An interval containing zero is unresolved, not equivalence.
The descriptive best fixed GPC was G3 (0.826595); this ranking is not treated as predeclared winner inference.
The non-deployable repeatwise GPC oracle gave H-oracle -0.000414 [-0.007027, +0.006163].

## Low-data and later checkpoints
At B16 q20 accuracy was H/G0/G3 0.7865/0.7318/0.7235; Keyhole recall was 0.7194/0.4975/0.5251.
At B40 q20 accuracy H/G0/G3 was 0.8359/0.8171/0.8253; at B80 it was 0.8341/0.8329/0.8571.

## q30 robustness
G3-G0 q30 AULC: +0.003559 [-0.004163, +0.010259]. H/G0/G3 q30 AULC: 0.871597/0.866116/0.869675.

## ARD stability
G2: any-length bound 90.3%; B16 anisotropy ratio median 53.39 (IQR 44.99-89.53)
G3: any-length bound 92.3%; B16 anisotropy ratio median 37.82 (IQR 31.37-62.51)
Lengthscales are standardized-space model-geometry diagnostics, not physical units or causal feature importance.

## Safe interpretation
The result is a held-out surrogate comparison on one frozen simulator benchmark. It tests kernel adequacy, not acquisition, external validity, or physical causality.

## Future h + ARD discrepancy GP
Recommendation: **{future}**. This is justified only when G3 materially improves standalone 4D GPC behavior.
