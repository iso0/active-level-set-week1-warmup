# Week 15 research log

- 2026-10-04: theory audit; T_both law corrected and three smaller errors fixed (commit 2e52d227).
- Expectation-oracle decomposition (Week 13 generator): attainable-with-truth headroom 0.050/0.074/0.076
  NSD AULC over margin; label peeking only 0.003/0.000/0.028.
- EBR (unnormalized expected error-set perimeter) implemented with exact bivariate-normal edge
  probabilities; development: ≈ margin without noise, catastrophic in NEW-like σ = 1 (size bias, Prop. B3).
- One principled revision: EBR-D (Dice-normalized). Development: no catastrophe but ≤ margin in all 9 cells.
- Oracle alignment: no legal criterion (margin, BALD, VSUR, EBR-D) correlates with the oracle's
  per-candidate gain; even a truth-informed "label reliability" criterion gains nothing.
- Well-specified GP world: exact Bayes look-ahead and EBR-D both ≈ +0.01 NSD AULC over margin and lower ASSD.
- DC-BD metric developed (importance-weighted r-graph boundary Dice); development: 5-8x lower density
  sensitivity than the unweighted version under smooth density shifts; incomplete under thin bands.
- Freeze written (FREEZE.md) before any held-out or real-data run.
