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

## Stage D — confirmatory results (after freeze 3278f7dc)

- C1 discovery (held-out): P1, P2, P3a, P3b, P4 all hold. FRONT cost is dimension-free on the monotone
  held-out family (2.0 at d = 2, 4, 6) while MAXI grows (4.0 -> 6.3); MAXI is best on Branin/Hartmann
  (peripheral compact basins); RAND/HEDGE_FR best on twoislands_skew at d >= 4.
- C2 transfer (held-out): P5a and P5b FAIL (G3C below G3 in twoRegimeST: BA -0.016 at target80, NSD
  -0.075), P5c holds (curvedMono), P6a/P6b hold. Risk asymmetry: worst cell G3C - G3 = -0.016 BA, whereas
  M3 - G3 reaches -0.19 and H - G3 -0.26.
- C3 metrics: P7a holds (wBER less density-sensitive than BER in every cell; 6-D reduction small), P7b
  fails in 3/12 cells (uniform/clustered sphere; two of them by < 0.002).
- R1 (POST-HOC NEW) FAILS: FRONT needs > 16 queries in 9/100 NEW pools (max 21). NEW labels violate O3
  far more than OLD: 75 violating pairs on the full 136, of which 64 come from one non-Keyhole case
  (P 423 W, VX 0.332 m/s, LS 42 um, ST 473 K) in the highest-energy-density corner; the remaining 11 are
  near-front boundary violations that defeat the min-front certificate in 9 pools. SCORE (log-h extremes)
  has max 7 and the three-way HEDGE (MAXI+FRONT+SCORE) max 14 on NEW; HEDGE_FR max 37.
- R2 (EXTERNAL Masinelli) holds strongly: FRONT mean 2.0-2.5 (max 8) vs RAND 8.4-16.4 and MAXI up to 35.
- R7: Prop. I1 — 75% of NEW rare cases (9/12) and 64% of OLD rare cases are dominated by another rare case.
- R3-R5 real models: G3C helps within-material on Masinelli (+0.016/+0.020 at n = 10), neutral on
  transfers, +0.006 OLD in-domain, -0.023 NEW-only (closure errors 11% of implied labels). Removing the
  anomalous NEW case from training only (sensitivity) makes G3C worse (-0.051): the harm is not a single
  label; NEW's labels genuinely violate O3 near the extreme-VX boundary.
- R6: weighted metrics on Week 12 NEW paths resolve no protocol difference.
- Study 4b/4c: a true-NSD oracle beats margin by +0.05/+0.07/+0.10 NSD (BAL/OLD/NEW-like) by avoiding
  noisy near-boundary labels (flipped acquired labels <= 2.3% vs 8-17%). Study 5 (development): BALD does
  not capture this headroom (NEW-like NSD 0.734 vs margin 0.825 at sigma 0.5). Not pursued further.
- Wrote LITERATURE_NOVELTY_AUDIT, COUNTEREXAMPLES, CLAIM_LEDGER, WEEK14_MASTER_REPORT, THESIS_INTEGRATION.
