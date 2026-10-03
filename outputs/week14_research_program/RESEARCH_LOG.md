# Week 14 research log

Start: 2026-10-04, `main` = `6bd75f8cbc3ffaea84238d5c61db9e52619a91f2` (remote verified equal).
Evidence tags used throughout: THEOREM/EXACT, CONTROLLED SYNTHETIC, HISTORICAL OLD, POST-HOC NEW,
EXTERNAL/PUBLIC, SPECULATIVE.

## Stage A — reconstruction and literature (2026-10-04)

- Re-read Week 13 report/theory/design and code (authored in the previous session).
- Re-read Phase 1.19A/B (monotonicity). Key pre-NEW facts: on OLD the order
  (P up, VX down, LS down; ST ignored) has 3 violations in 22,050 comparable pairs; 22 minimal and
  11 maximal elements on the full 405 pool; Dilworth width 93. Phase 1.19B: hard monotone
  *propagation for in-domain pool labelling* lowered BA AULC (-0.0085) — monotone structure did
  not help acquisition where M3 is already near-perfect. Any new use of order must be different
  in kind (discovery certificates; transfer/generalization under shift) and must not be re-sold as
  in-domain label saving.
- Found the external Masinelli et al. (2025) Ti64 / 316L bundles (P, VX, label; LS constant) in the
  retained Phase 1.10 OOF files: a small genuinely external/public 2-D benchmark.
- Literature anchors found so far: Tao (PODS 2018, 2021) active monotone classification,
  O(w log(n/w)) probes; Dasarathy, Nowak & Zhu (COLT 2015) S^2 cut-edge active learning;
  Riihimaki & Vehtari (AISTATS 2010) monotone GP classification; Hvarfner et al. piBO (prior decay);
  Jiang et al. (ICML 2017) active-search hardness; He & Carbonell (2007) rare category detection
  with compactness assumptions; Bentley et al. (JACM 1978) expected number of maxima;
  Brynjarsdottir & O'Hagan (2014) model discrepancy.

## Integrity commitments for this week

- NEW-136 labels are **not** inspected for any new monotonicity/discovery/model question before the
  Week 14 freeze commit. Label-free NEW quantities (pool geometry, Pareto fronts) are allowed.
- Methods are selected on synthetic development families and OLD (historical) only.

## Stage A/B — theory and first development experiments (2026-10-04)

- Wrote THEORY.md: D1 (exchangeability no-free-lunch), D2 (sharp geometric certificate, minimax
  cost in [(N(2r)+1)/2, N(r)]), D3 (Pareto-front certificate, minimax Θ(|Min|+|Max|)), D4, D5 (hedge),
  O1 (dominance = exponent-robust order), I1 (LOO front fraction), E1 (linear metrics = precision
  thresholds; KNOWN via ROC iso-performance lines), E2 (cut-edge recovery limit), H1/H2 (headroom).
  Property tests: src/tests/test_week14_discovery_theory.py (6 pass).
- Study 1 development smoke (20 reps/cell, 6 families x d{2,4,6} x n{108,324} x prevalence x design):
  monotone families: FRONT mean T_both ~2.1, SCORE ~2.1, MAXI ~5.4, RAND ~14.5. Non-monotone compact
  families (islands, slab): RAND best on average (14.4); MAXI 18.8; FRONT 25; SCORE 40.
  -> farthest-first is *worse than random* when rare islands sit in the density bulk (periphery bias;
  consistent with the coreset/outlier observation of Yehuda et al. 2022). HEDGE(MAXI,FRONT,SCORE) inherits
  this; a hedge must include RAND to keep the D5 guarantee relative to random.
- Monotone GPC (virtual derivative observations, Laplace) implemented and tested (3 tests pass:
  sklearn parity without virtual points, finite-difference covariance, enforced monotone mean).
- Study 2 smoke (2 reps): physics-mean models (H, M3) best in-domain, worst under shift in all three
  families (reproduces Week 12/13). MG/GRC helped only in the monotone twoRegime target40 setting;
  no help or harm in stShift (order O3 violated). 20-rep development run launched.
- Study 3 (metric study, 30 reps): density-induced rank reversal occurs for *every* finite-pool metric
  (q20 accuracy, BA, BER, BEF1, all graphs): equal-geometry left/right errors swap rank when the
  evaluation density moves (Gabriel BER 0.27 vs 0.93 and back). r-graph is most extreme (p^2 weighting).
  q20 accuracy and BER are blind to spurious islands far from the boundary; BEF1 penalizes them.
- Study 3b: length^(d-1)-weighted cut-edge metrics (wBER/wBEF1) cut the density sensitivity ~3x
  (Gabriel |left-right| 0.62 -> 0.15-0.24; truth 0.03) without harming uniform designs; residual bias
  remains under strongly anisotropic density. PARTIAL fix, recorded as such.

## Stage B decisions and Stage C freeze (2026-10-04)

- Study 2 development (20 reps): MG rejected (minimum-slope misspecification; see DEVELOPMENT_DESIGN.md);
  closure override never below GR in BA across 12 cells -> confirmatory candidate G3C (order O3).
- Study 4 (descriptive): greedy oracle on *evaluation-pool* BA exceeds the full-pool "ceiling" by
  0.03-0.09 BA, so the full-pool reference is not a ceiling; but that oracle's true-boundary NSD is not
  higher than margin's (evaluation-set overfitting). Replace-one sensitivity bounds (Prop. H1) are
  numerically vacuous for these GPCs (mean-swap bound 0.03-0.47, max-swap bound > 1).
- Week 13 source restored byte-identical; the new weighted metric lives in src/week14_metrics.py.
- Freeze committed before any held-out family or Week 14 real-data check is executed.
