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
- Held-out (frozen): EBR-D better than margin in 7/16 cells; mean -0.0095 NSD AULC; S1-S4, S6 fail; verdict
  NO NEW METHOD JUSTIFIED. Ablation: EBR-D beats VSUR by +0.010. Oracle references: 0.602 vs margin 0.399;
  0.40 vs <= 0.14 for every legal rule.
- DC-BD held-out: improves on the unweighted r-graph in every smooth cell; fails M-a (vs q20 accuracy in the
  two-component shape) and M-b (one cell by 0.002).
- Real-data replays (descriptive): NEW and OLD no resolved difference; Masinelli Ti64 EBR-D better (DC-BD +0.047),
  316L worse (-0.030). No revision attempted (reasons in report §6).
