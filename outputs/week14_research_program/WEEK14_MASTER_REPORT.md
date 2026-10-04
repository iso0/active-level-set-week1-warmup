# Week 14 master report — structure-certified active level-set estimation in rare-regime finite pools

Date 2026-10-04. Start `6bd75f8c`; **pre-result freeze `3278f7dc`** (pushed before any held-out or Week 14
real-data run); results commit: see the final section. Evidence tags as in `CLAIM_LEDGER.md`.

## Executive answer

### 1. What did you discover?

**Discovering the rare regime is a question of structure, and the structure that transfers in LPBF
is the physics ordering, not the physics level.**

- *Theorem.* Without an assumption linking labels to features, no query rule (adaptive, geometric,
  physics-guided) can beat — or lose to — random sampling in discovering the rare class (D1). Each
  structural assumption gives a sharp, label-blind certificate with a matching minimax lower bound:
  the pool's covering number for geometric rare islands (D2), the Pareto-front size for monotone
  labels (D3), and the rank error for a score (D4). A round-robin hedge is within a factor J of the
  best of them (D5).
- *Frozen held-out benchmark.* Every pre-registered discovery prediction held. Under monotone labels
  the order certificate costs 2.0 queries at d = 2, 4, 6, while maximin grows from 4.0 to 6.3 with
  dimension and random needs ~15. Under compact non-monotone rare islands, maximin can be *worse than
  random*.
- *Real data.* On OLD-405 (historical) and on the external Masinelli Ti64/316L data, the order
  certificate discovers both regimes in 2–2.5 queries on average (max 8; random 8–16; maximin up to 35).
  On NEW-136 (post-hoc) the order certificate fails because NEW's labels violate the order: 64 of 75
  violations come from one implausible non-Keyhole case. The rank of log h alone still discovers both
  regimes within 7 queries in all 100 NEW pools — the frozen geometric B16 rule stopped in one of them.
  This turns Week 13's diagnosis "the ordering transfers, the level does not" into an operational rule
  with a guarantee.

Two evaluation results accompany this:

- **Every finite-pool boundary metric is density-weighted.** This includes q20 accuracy, BA and the
  cut-edge metrics. Two predictors with identical geometric error swap rank when only the sampling
  density of the evaluation campaign changes.
- **Finite-pool metrics cannot identify acquisition headroom on the true boundary.** An oracle that
  maximizes the finite metric does *worse* than margin on the true boundary. An oracle on the true
  objective beats margin by +0.05 to +0.10 NSD, by avoiding noisy near-boundary labels.

For the model, the physics encoding shows a clear **risk asymmetry**:
- Physics as a fixed mean (M3) or as the only predictor (H) is best in-domain but loses up to −0.19 /
  −0.26 BA under shift (held-out synthetic) and −0.12 BA on real OLD→NEW.
- Physics as an order constraint (dominance closure) has a worst case of −0.023 BA. It helps where the
  order holds, but it is not safe where a campaign's labels violate it, as on NEW.

### 2. Did we obtain a genuinely new method, theorem or framework?

**PARTIALLY.**

- *Yes:* an assumption-explicit discovery theory with sharp minimax characterizations (D1–D3),
  validated on a frozen held-out benchmark and three real campaigns. Also two evaluation findings
  (density-weighting rank reversal; non-identifiability of acquisition headroom from finite-pool
  metrics) that we did not find stated in the active-learning benchmarking literature.
- *No:* a new model or acquisition rule that improves across settings. The order-aware model
  (closure override) failed two of its pre-registered predictions and hurt on NEW-only. The monotone
  GP and BALD were rejected with mechanisms. The mathematics is modest in depth: the value lies in
  sharpness, assumption clarity and the empirical tests, not in technical difficulty.

### 3. What survived attempts to falsify it?

- D1–D5: property tests; not violated on any held-out pool (P1, P3a).
- The dimension-free versus dimension-dependent discovery prediction (P2).
- Maximin worse than random for bulk rare islands (P4, held-out).
- The order certificate on OLD and on external data (R2).
- The physics-level failure under shift (P6; real OLD→NEW and NEW-only).
- G3C gains in valid-order shifted cells (P5c).
- Density sensitivity of all finite metrics, and its reduction by length weighting (P7a).
- The headroom identifiability gap (descriptive; consistent across three scenarios).

### 4. What failed?

- **Pre-registered P5a/P5b.** G3C ≥ G3 in every held-out cell failed: twoRegimeST BA −0.016 (n.s.),
  NSD −0.075 (significant).
- **P7b.** Weighted BEF1 ≥ q20 accuracy in rank agreement with ASSD failed in 3/12 cells.
- **R1.** The order certificate ≤ 16 queries on NEW failed: 9/100 pools exceeded 16, max 21.
- **Order-closure on NEW-only:** BA −0.023; −0.051 when the anomalous case is removed from training,
  because the case is then implied wrong in test folds and boundary violations remain.
- **Monotone GPC with probit virtual derivatives:** it imposes a minimum slope, which is harmful in
  saturated, imbalanced regimes.
- **BALD:** it does not realize the true-objective headroom (worse than margin in the NEW-like cell).
- **Stability bound H1:** numerically vacuous for GPCs.
- **The frozen HEDGE_FR (front + random)** has max 37 on NEW, worse than the three-way hedge (14).

### 5. What is actually novel? (see `LITERATURE_NOVELTY_AUDIT.md`)

Plausibly new, with moderate confidence:
- the sharp geometric discovery certificate and minimax covering characterization (D2);
- the cut-edge recall interpretation as a density-weighted tolerance boundary recall for finite-pool
  evaluation (E2);
- the demonstrated density-induced rank reversal of AL boundary metrics;
- the finite-metric versus true-objective oracle contrast.

Elementary or known:
- D1 (folklore);
- D3's fact (poset theory; Tao 2018/2021 treat monotone *learning*);
- D5 (portfolio construction);
- E1 (ROC iso-performance lines, Provost & Fawcett 2001);
- closure inference (dominance-based rough sets);
- margin acquiring noisy boundary labels (arXiv 2608.13601);
- BALD.

The searches were targeted, not systematic.

### 6. What should go into Burak's MSc thesis?

A chapter **"Structure, not acquisition: discovery, transfer and evaluation in rare-regime finite
pools"** containing:
- D1–D5 with proofs;
- fig1, fig2 (discovery by dimension; real campaigns);
- the risk-asymmetry result (fig3);
- the order-violation diagnostic on NEW (fig6);
- the evaluation chapter extension with E1, E2, density weighting (fig4) and headroom
  identifiability (fig5).

Week 13's Props. 1–2 become a corollary of E1. Detailed plan: `THESIS_INTEGRATION.md`.

### 7. What could support a paper?

**(a) Methodology paper:** "Assumption-explicit cold-start discovery for active level-set estimation"
— D1–D5 + held-out benchmark + three real campaigns, including the honest NEW failure. Venue: TMLR or
an AISTATS/UAI workshop; the theory is too light for a main-track theory venue.

**(b) Evaluation note:** "Finite-pool boundary metrics are density-weighted and cannot identify
acquisition headroom" — E2, C3, C7–C8, synthetic studies. Venue: a data-centric ML / benchmarking
workshop, or a journal note.

**(c) Application paper for AM:** physics-as-order versus physics-as-level under campaign shift,
with the order-violation audit of NEW and the Masinelli external check. Venue: *Additive Manufacturing
Letters* or *Integrating Materials and Manufacturing Innovation*.

### 8. What claims must NOT be made?

- That NEW validates any Week 14 method (all NEW results are post-hoc).
- That closure override is safe in general.
- That the weighted metric fixes density dependence or should replace q20.
- That acquisition does not matter (true-objective headroom exists synthetically).
- That the NEW anomaly is a mislabel.
- That the theorems are deep, or new beyond the audit's statements.
- That Week 13's 0.014 is a ceiling.

---

## A. Methods

### A1. Theory
`THEORY.md`: D1–D5 (discovery), O1 (exponent-robust order), O2 (heuristic), I1 (LOO front
fraction), E1 (linear metrics = precision thresholds), E2 (cut-edge limit), H1/H2 (headroom), L (ledger
not decomposition). Tests: `src/tests/test_week14_discovery_theory.py` (D1 exchangeability law by
simulation, D2 sharpness construction, D3 fronts and lower-bound labellings, D5 hedge, harmonic-number
front sizes), `src/tests/test_week14_methods.py`, `src/tests/test_week14_monotone_gp.py`.

### A2. Studies (code `src/week14_*.py`)

| Study | Purpose | Development | Frozen held-out / real |
|---|---|---|---|
| 1 Discovery | strategies RAND, MAXI, SCORE, FRONT, ADAPT8, HEDGE, HEDGE_FR | 6 families × d{2,4,6} × n{108,324} × π × design, 20 reps | C1: 5 held-out families, 100 reps; R1/R2 on NEW/OLD/Masinelli |
| 2 Physics in the model | H, M3, G3, G3S, G3C, GR, GRC (MG rejected) | 3 families × 4 settings, 20 reps | C2: 3 held-out families × 4 settings, 30 reps; R3–R5 |
| 3 Metrics | q20, BA, BER/BEF1/wBER/wBEF1 (Gabriel, kNN, r-graph) vs NSD/ASSD | curved boundary, 2-D/4-D, 3 densities | C3: sphere (3-D, 6-D), two-component (3-D), 4 densities, 30 reps; R6 |
| 4 Headroom | random, margin, finite-metric oracle, true-NSD oracle, swap sensitivity | Week 13 generator | descriptive |
| 5 Noise-aware acquisition | margin vs BALD | 3 scenarios × σ{0,0.5,1}, 12 reps | not frozen (negative at development) |

Integrity:
- The freeze was committed and pushed before held-out/real runs.
- One deviation (D1: a missing seed-index entry that crashed C1 before any output) is recorded in
  `DEVIATIONS.md`.
- No reps were removed; 12 single-class metric pools are recorded as skipped.
- NEW labels were not inspected for any Week 14 question before the freeze.
- The 49 withheld outcomes were not used.
- Week 13 sources are byte-identical; protected Week 11/12 hashes verified.

## B. Results

### B1. Discovery (C1, held-out; `benchmarks/C1_discovery_verdict.json`)
Mean T_both by family (all cells):

| family | RAND | MAXI | FRONT | SCORE | HEDGE | HEDGE_FR |
|---|---:|---:|---:|---:|---:|---:|
| mono_curved (monotone) | 14.8 | 5.3 | **2.0** | 2.0 | 2.9 | 2.5 |
| rotated_mono (order partly wrong) | 14.3 | 5.4 | **4.0** | 9.0 | 4.1 | 5.3 |
| Branin (non-monotone, 3 basins) | 14.8 | **9.4** | 10.8 | 23.4 | 9.5 | 12.1 |
| Hartmann (non-monotone) | 14.2 | **10.2** | 14.1 | 19.9 | 12.4 | 13.9 |
| two islands (non-monotone) | **14.6** | 16.9 | 19.2 | 30.8 | 19.2 | 14.6 |

P1–P4 all true. In the monotone family FRONT stays at 2.0 for d = 2, 4, 6 whereas MAXI rises 4.0 → 6.3
(fig1) — the D2/D3 contrast.

### B2. Discovery on real campaigns (R1, R2; fig2)

| campaign | RAND mean / max | MAXI | FRONT | SCORE (log h) | HEDGE |
|---|---|---|---|---|---|
| OLD (100 pools, historical) | 5.7 / 24 | 2.9 / 7 | **2.0 / 2** | 2.0 / 2 | 3.4 / 4 |
| NEW (100 pools, post-hoc) | 9.7 / 47 | 5.6 / 30 | 5.3 / 21 | **2.9 / 7** | 4.2 / 14 |
| Masinelli Ti64, K = 1–3 (external) | 11.7 / 35 | 4.2 / 35 | **2.3 / 8** | 2.4 / 26 | 3.1 / 13 |
| Masinelli 316L, K = 1–3 (external) | 11.9 / 38 | 2.8 / 18 | **2.0 / 2** | 2.0 / 2 | 2.6 / 4 |

NEW order violations: 75 pairs on the full cohort, 64 from one case (fig6); mean 47.8 per training
pool versus 1.9 on OLD.

### B3. Physics in the model (C2 held-out; R3–R5 real; fig3)

G3C − G3 balanced accuracy (95% paired bootstrap):
- curvedMono: +0.023 [0.008, 0.041] (target40), +0.010 [0.000, 0.019] (target80), +0.003 (transfer).
- hartmannDev: +0.028 [0.011, 0.047], +0.017, +0.010 [0.002, 0.021].
- twoRegimeST: −0.004, −0.016 [−0.044, 0.012], −0.005.
- In-domain: ≈0 everywhere.

M3 − G3:
- −0.10 (curvedMono transfer), −0.19 / −0.12 / −0.19 (twoRegimeST target40 / target80 / transfer),
  and +0.03 in-domain (hartmannDev).

Real (BA):

| setting | H | M3 | G3 | G3S | G3C |
|---|---:|---:|---:|---:|---:|
| OLD→NEW (post-hoc) | 0.500 | 0.579 | 0.700 | 0.500 | 0.700 |
| NEW-only, 100 partitions (post-hoc) | 0.528 | 0.609 | 0.707 | 0.707 | 0.684 |
| OLD in-domain, 100 splits (historical) | 0.922 | 0.934 | 0.932 | 0.923 | 0.938 |
| Ti64 → 316L (external) | 0.838 | 0.838 | 0.865 | 0.865 | 0.865 |
| 316L → Ti64 (external) | 0.838 | 0.838 | 0.838 | 0.838 | 0.838 |
| Ti64 within, n = 10 (external) | 0.895 | 0.894 | 0.871 | 0.886 | 0.891 |
| 316L within, n = 10 (external) | 0.939 | 0.939 | 0.905 | 0.918 | 0.921 |

On Masinelli the physics direction is genuinely valid (Phase 1.10), and H/M3 are strongest
within-material — consistent with the asymmetry (physics-as-level wins when the level holds).

### B4. Metrics (C3 held-out; fig4)

Density sensitivity |side A − side B| for equal-geometry errors:

| configuration | q20 accuracy | BER | wBER | NSD |
|---|---:|---:|---:|---:|
| sphere 3-D | 0.30 | 0.50 | 0.20 | 0.003 |
| two-component 3-D | 0.28 | 0.47 | 0.14 | 0.04 |
| sphere 6-D | 0.28 | 0.51 | 0.40 | 0.008 |

Rank agreement with −ASSD: wBEF1 exceeds q20 accuracy by 0.02–0.16 in side-concentrated designs, and
ties or loses in 3 uniform/clustered cells. On NEW (R6) weighted and unweighted cut-edge metrics agree
that no Week 12 protocol differs resolvably (random16 − margin16 wBEF1 +0.006 [−0.020, 0.033]).

### B5. Headroom (Study 4; fig5)

| | BAL | OLD | NEW |
|---|---:|---:|---:|
| Mean NSD over B16–B80: random | 0.84 | 0.80 | 0.66 |
| margin | 0.90 | 0.84 | 0.85 |
| finite-metric oracle | 0.874 | 0.795 | 0.815 |
| true-NSD oracle | 0.95 | 0.91 | 0.95 |
| Flipped labels among acquired: margin | 17% | 8% | 10% |
| true-NSD oracle | 2.3% | 0.8% | 0.8% |

The finite-metric oracle exceeds the full-pool ceiling on its own metric (BA 0.95 vs 0.86 NEW-like).

## C. Limitations

- Synthetic generators encode chosen mechanisms (smooth laws, a localized deviation, iid boundary
  noise). The held-out families differ from development but are still authored by us.
- Oracle hyperparameters were fixed in Studies 4–5.
- Real-data contrasts rest on few rare cases (12 NEW; Masinelli 60 bundles per material, minority
  subsampled for discovery).
- NEW is post-hoc throughout.
- Masinelli is 2-D with constant spot size and a transition-inclusive morphology label, not the SPH
  target.
- The literature audit is targeted.
- The true-objective headroom is measured with a cheating oracle; no realizable method captured it.

## D. Provenance

- Freeze `3278f7dc` (pushed).
- Deviation log `DEVIATIONS.md`.
- Development decisions `DEVELOPMENT_DESIGN.md`.
- Chronology `RESEARCH_LOG.md`.
- Counterexamples `COUNTEREXAMPLES.md`.
- Novelty `LITERATURE_NOVELTY_AUDIT.md`.
- Claims `CLAIM_LEDGER.md`.
- Thesis plan `THESIS_INTEGRATION.md`.
- Machine-readable results: `synthetic/`, `benchmarks/`, `real_data/`.
- Figures: `figures/`.
