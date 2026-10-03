# Week 13 — What the thesis has actually found, and the strongest defensible contribution

Date: 2026-10-03. Author of this analysis: Claude (Opus 5.5), working on `main` at `3c77769e`.

> **Türkçe özet.** Tezdeki asıl sorun yanlış edinim fonksiyonu değil. Sorunu üç ayrı
> mekanizma oluşturuyor: (1) nadir sınıfın bulunması (keşif), (2) değerlendirme metriğinin
> sınıf oranına bağımlılığı, (3) fizik öncülünün kampanya kaymasında "çapalanması".
> Bunların üçü de mevcut veride kesin olarak gösterilebiliyor ve kontrollü sentetik deneylerle
> genellenebiliyor. Önerilen tez/makale çerçevesi şu: *"Sonlu havuzlarda nadir-rejim aktif
> düzey-kümesi kestirimi: keşif maliyeti, edinim payı (headroom) ve sınıf oranından bağımsız sınır
> değerlendirmesi."* Yeni bir edinim fonksiyonu önerilmiyor; yeni olan şey, edinim
> karşılaştırmalarının neden ayırt edici olamadığını açıklayan ve ölçen bir çerçeve.

## 0. Evidence categories used in this report

| Category | Content | Allowed interpretation |
|---|---|---|
| HISTORICAL / FROZEN | OLD-405 Track A (Phases 1.13–1.21, Week 8.5) | Internal evidence on one campaign |
| FROZEN EXTERNAL ATTEMPT | Week 11 `INCOMPLETE_FROZEN_STOP` | No effect estimate. **Untouched here.** |
| POST-HOC DEVELOPMENT | Week 12 NEW-136 runs | Development data |
| **EXPLORATORY (new, this week)** | Re-analysis of *already retained* Week 8.5 / Week 12 predictions, query paths and labels; four bounded M3 refits for mechanism checks | Descriptive mechanisms. No new method selected on NEW. |
| **CONTROLLED METHODOLOGICAL (new)** | Synthetic generator with a known boundary (2,880 AL paths + 320 transfer fits + displaced-boundary family) | Evidence about mechanisms, **not** validation on SPH |

Nothing in this week used the 49 Bug-withheld outcomes, resumed the Week 11 run, changed q20, or
reported a new primary endpoint. q20 accuracy is reported everywhere it was reported before;
alternative metrics are added beside it and are motivated (Section G) before being applied.

---

## Internal research diagnosis (Step 23 of the brief)

1. **Original question.** Can the Conduction–Keyhole level set in [P, VX, LS, ST] be estimated with
   fewer SPH runs by choosing runs actively?
2. **What Weeks 8–12 established.** (a) On OLD, uncertainty sampling beats random clearly
   (Week 8.5: +0.0373 q20 AULC, 20/20 repeats). (b) The physics coordinate log h is an excellent
   global ordering on OLD (AUC 0.991; free exponents reproduce h). (c) M3 is a good in-domain model.
   (d) Beyond margin, *every* acquisition refinement gives ≤ +0.007. (e) On NEW, the B16 startup can
   fail, M3 does not transfer better than generic GPs, and no protocol beats always-Keyhole on q20.
3. **What failed.** The hope that a better acquisition function (or a physics-informed one) would
   produce a material, transferable gain; and the hope that NEW-136 could confirm Candidate B.
4. **What survived.** Margin ≫ random on OLD; physics ordering; adaptive startup removes the
   discovery tail; M3 > H everywhere.
5. **Central unresolved problem.** Not "which acquisition", but *why acquisition comparisons
   could not be decisive*. This week answers that question quantitatively.
6. **Top three contributions from existing data.** (i) An end-to-end decomposition of active
   level-set cost into discovery, model ceiling and acquisition headroom, with discovery
   certificates. (ii) A demonstration, with exact identities, that band accuracy (q20) is
   prevalence-confounded, plus a pair-based boundary metric validated against true surface
   distances. (iii) A mechanism for physics-prior failure under campaign shift ("ordering
   transfers, local level does not"), reproduced synthetically.
7. **Recommended.** All three, as one evaluation-methodology contribution with an LPBF case study.
8. **Smallest analyses needed.** Done this week (Sections D–I).

---

## A. Project reconstruction (Weeks 8–12)

- **Week 8 / 8.5.** Binary GPC margin vs random under a frozen protocol on OLD: +0.0373 q20 AULC
  [+0.030, +0.044], 20/20 repeats. Repulsion added nothing. This is the strongest acquisition
  result in the thesis, and it is a *margin vs random* result.
- **Week 9 Phase 1.** Physics coordinate h, H model, then M3 (H mean + 4-D ARD Matérn discrepancy,
  residual sd ≤ 1). Many acquisition attempts (repulsion, SUR, monotone LSE, residual, PA-TVR,
  CCM...) gave negligible or negative gains over M3 margin. Phase 1.21 replicated Candidate B
  (+0.0067) and Candidate A (+0.0032) on untouched OLD repeats, below the +0.01 threshold.
- **Week 10.** PG-RMBC and boundary-displacement Gate 1 failed to beat Candidate B. Track A frozen.
- **Week 11.** NEW campaign (185 → 136 included, 124/12). Frozen external run STOPPED at a
  single-class B16 (`external__r003_f04`). Remains `INCOMPLETE_FROZEN_STOP`.
- **Week 12.** Post-hoc: startup diagnosis; adaptive startup; strict OLD→NEW transfer
  (G0/G3 > M3 > H); NEW-only CV; 800 complete paid AL paths; nothing beats always-Keyhole on q20.

The decisive structural fact that was present all along but never used as an argument
(Phase 1.21 report, §1): **the OLD all-label M3 reference q20 accuracy is 0.8551 and margin's AULC
is 0.8411, so the entire B16–B80 headroom over margin was 0.014.** The preregistered replacement
threshold (+0.01) demanded 71% of the total achievable improvement. Candidate B captured 48% of it.
Margin at B80 (0.8559) already equals the all-label model. The acquisition search was a search
inside a 0.014-wide window.

## B. Failure diagnosis — why the external/acquisition story did not materialise

Three independent mechanisms, each now quantified.

**B1. Discovery (startup) is a different geometric problem on NEW.** Proposition 4
(`THEORY.md`): a design whose fill distance is below the largest "rare-pure" radius ρ* is
*guaranteed* to contain a rare case. On OLD pools, ρ* (median 2.45) exceeds the B16 fill distance
(1.91) in 100/100 pools — discovery was certified. On NEW pools, ρ* (1.38) is below it (1.83);
the certificate arrives only at a median B28 and holds by B16 in 1/100 pools. The certificate is
never violated (fig1). The frozen B16 rule was safe on OLD *for a geometric reason* that did not
carry over. The fill distance decays as b^−0.49 (effective dimension ≈ 2), so geometric discovery
of small rare islands is slow; a physics *ordering* (Prop. 5) is dimension-free, which is why the
adaptive log-h rule removes the tail.

**B2. The primary metric cannot reward boundary learning under the NEW prevalence.**
Proposition 1: for any band S, acc(ŷ) − acc(always-majority) = (correct − wrong minority
calls)/|S|. A model beats the trivial predictor on q20 iff its rare-class calls are more than 50%
precise — independent of prevalence. All NEW protocols have rare-call precision < 0.5 in the band
(margin16: 2.34 correct vs 2.79 wrong per fold), hence none beats always-Keyhole. On OLD the same
quantity is 4.62 vs 1.18. This is not a weakness of the methods relative to each other; it is
what band accuracy measures.

**B3. On NEW the bottleneck is information, not acquisition.** Margin had already labelled 8.5 of
the ≈9.6 rare cases in each training pool by B40 (random: 4.1; fig3). Thereafter every policy only
adds Keyhole cases. Yet held-out rare recall stays ≈0.25. With ~9 rare examples the model, not the
query rule, limits performance. Between-protocol differences on every metric, including
the new boundary metrics, are within noise (Section D2).

## C. Strongest surviving scientific findings

1. **Margin ≫ random when the model can use the information** (OLD Week 8.5; all 24 synthetic
   cells on true-boundary NSD, +0.04 to +0.16 for the generic GPC).
2. **Acquisition refinements beyond margin have almost no headroom** in small finite pools: OLD
   headroom 0.014; synthetic margin captures 37–94% of ceiling-minus-random headroom; the
   coverage rule (Candidate B analogue) is never better than margin in the synthetic study.
3. **A better predictive model leaves less acquisition headroom.** In the synthetic study the
   physics-mean model P has higher random-acquisition quality and *smaller* margin gains in every
   BAL/OLD cell (e.g. OLD/324: NSD gain +0.160 for G vs +0.050 for P; fig6). "Better model ≠ better
   acquisition" is not a paradox: acquisition value is bounded by what the prior has not already
   learned.
4. **Rare-regime cold start has a clean geometric explanation** (B1).
5. **q20 accuracy is prevalence-confounded in a precise sense** (B2, Prop. 2, Section G).
6. **Physics priors transfer ordering but not local level** (Section H): log h keeps AUC 0.857 on
   NEW, but the NEW boundary is oblique to the h contours (≈ a VX threshold, BA 0.918), and M3
   anchors to the OLD trend.

## D. New analyses performed (methods, results, QC)

All code is in `src/week13_*.py`; outputs in this directory.

### D1. q20 band composition and hubness (`real_data/`)
Recomputed the historical q20 band per split. Majority share in q20: **0.611 OLD, 0.685 NEW**.
Nearest-opposite hubness: each NEW rare case is the nearest opposite of 10.3 Keyhole cases
(max 47); on OLD 47/73 Keyhole cases are never selected.

### D2. Re-scoring all 800 Week 12 paths (1.59 M retained predictions) under more metrics
Pipeline QC: the recomputed mean-fold q20 AULCs reproduce Week 12 exactly (e.g. margin16
0.670234, Candidate B 0.672878, random16 0.681328; contrasts +0.002643, +0.011094).

| Protocol | q20 acc | full BA | Gabriel BEF1 | BER |
|---|---:|---:|---:|---:|
| always-Keyhole | **0.685** | 0.500 | 0.000 | 0.000 |
| random16 | 0.681 | 0.584 | 0.152 | 0.112 |
| margin16 | 0.670 | 0.594 | 0.141 | 0.107 |
| Candidate B | 0.673 | 0.597 | 0.143 | 0.106 |
| margin8 / adaptive8 | 0.662 | 0.602 | 0.151 | 0.120 |

Every protocol beats always-Keyhole by ≈ +0.14 BEF1 (19–20/20 repeats) and +0.09 full BA, yet
loses on q20 accuracy. Between protocols nothing is resolved under any metric (e.g. Candidate B
− margin16 BEF1 +0.0015 [−0.015, +0.015]; random16 − margin16 BEF1 +0.011 [−0.019, +0.040]).
**I am not claiming the new metric rescues margin or Candidate B on NEW; it does not.** What it
shows is that the protocols do recover part of the boundary, which q20 accuracy scores as worse
than doing nothing.

### D3. OLD Week 8.5 decomposition (extracted unchanged from the archived tarball)
Margin vs random on OLD: correct rare calls 4.62 vs 4.10, wrong 1.18 vs 1.29 (both sides improve);
q20 BA 0.791 vs 0.743. Margin's labelled Keyhole share 0.40 vs pool 0.18.

### D4. Theory checks (`theory_checks/`)
Prop. 4 certificate on 100 NEW + 100 OLD pools (never violated); Prop. 5 bound (valid, loose:
23.4 vs 9.0); Prop. 6 analytic uniform discovery (10.6 vs empirical 11.3); Prop. 7 anchoring
bound on 101 M3 fits (never violated; certifies 46/188 NEW-only rare misses).

### D5. Synthetic study (`synthetic/`, design frozen in `synthetic/DESIGN.md` before the full run)
Generator: physics score s(u) + a localized corner deviation (the physics law is locally wrong at
high P / small LS / high VX), OLD box (18% class 1) and NEW corner box (≈9% class 0), observed
labels with boundary noise (σ ∈ {0.5, 1}); the estimand is the noise-free level set. 2,880 paths:
3 scenarios × 2 σ × 2 pool sizes × 4 policies × 2 models × 30 independent replicates; oracle
fixed hyperparameters. True-boundary metrics: NSD (surface Dice) at τ ∈ {0.05, 0.1, 0.2}, ASSD.

### D6. Displaced-boundary family
Predictors with the exact boundary shape but displaced level, 25 offsets × 30 evaluation pools ×
12 cells.

### D7. Synthetic transfer study (`synthetic_transfer/`)
OLD-trained H, M3-analogue (σ² ≤ 1), M3-analogue (σ² ≤ 1000) and G3-analogue, all through the
*same* historical `FixedMeanLaplaceGPC` L-BFGS code path, scored on NEW-like data, for corner
deviation A ∈ {0, 0.75, 1.5, 3}, 20 replicates.

### D8. One real-data mechanism counterfactual (EXPLORATORY, post-hoc)
OLD-trained M3 with the residual-variance cap relaxed from 1 to 1000, scored once on NEW. Not a
method proposal, not tuned.

QC: 7 new unit tests (`src/tests/test_week13_propositions.py`) pass (Gabriel definition and
connectivity, prevalence-free constant values, Props. 1, 2, 4, 7). Protected Week 11/12 artifacts
were read only.

## E. Methodological insight (synthetic + real)

**In finite-pool active level-set estimation, the measurable value of an acquisition rule is
bounded by headroom = (model ceiling − discovery-and-random baseline), and that headroom shrinks
when (i) the pool is small relative to the budget, (ii) the rare class is exhausted early, or
(iii) the prior model is already good. Under severe imbalance, accuracy-type endpoints further
compress or invert what remains.**

Evidence: OLD headroom 0.014 (real); rare exhaustion by B40 on NEW (real) and in synthetic NEW
(margin 92–96% of pool rare labelled by B40); synthetic headroom smaller for the better model in
all BAL/OLD cells; the q20 dynamic range in the synthetic NEW cell is only 0.11 *for the
Bayes-optimal boundary* (0.700 vs constant 0.589).

The general recommendation for anyone benchmarking acquisition rules on small scientific pools:
**report the full-pool model ceiling, the random baseline and the trivial predictor before
comparing acquisition rules**, and count discovery queries in the budget.

## F. Mathematical insight

See `THEORY.md` for statements and proofs. Seven elementary results:

- **Prop. 1 (trivial-baseline identity).** Band accuracy minus majority = (C − W)/|S|.
- **Prop. 2 (metric-disagreement window).** Accuracy and BA rank two predictors oppositely exactly
  when the marginal precision ρ of the extra minority calls lies in (π, ½). Verified on NEW:
  full pool π = 0.088, ρ = 0.279 ⇒ accuracy favours random (−0.0036) and BA favours margin
  (+0.0098). q20: π = 0.315, ρ = 0.298 < π ⇒ both favour random. This fully explains "random looks
  competitive".
- **Remark 3 (hubness).**
- **Prop. 4 (geometric discovery certificate)** with the (ρ*)^−d scaling.
- **Prop. 5 (score-ordered discovery, dimension-free).**
- **Prop. 6 (uniform discovery, exact).**
- **Prop. 7 (anchoring bound for fixed-mean Laplace GPC).** μ(x) − m(x) = Σ k(x, x_i)(y_i − π̂_i),
  so a rare prediction requires m(x) < σ² S₀(x). A capped σ² makes points certifiably unreachable.
  An honest partial mechanism (24% of NEW-only misses).

Props. 2 and 4 are the strongest for the thesis: short, exact, and each explains a specific,
previously puzzling observation.

## G. Metric assessment

**Historical comparability:** q20 accuracy remains the primary historical endpoint and is reported
unchanged. **Evaluation validity:** under the NEW prevalence, q20 accuracy (i) has a trivial
baseline at 0.685 that no protocol beats, (ii) rewards fewer rare calls whenever their precision
is below ½ (Prop. 1), (iii) can rank opposite to balanced metrics (Prop. 2), and (iv) inherits
majority weighting through nearest-opposite hubness.

**Proposed complement (not a replacement): Gabriel boundary-edge metrics.** On the Gabriel graph
of the evaluation pool, the true cut set E* consists of edges whose endpoints have different labels
(the true level set crosses each). BER = fraction of E* resolved correctly at both ends; BEF1 =
F1 between E* and the predicted cut set (penalises spurious boundaries anywhere). Properties:
parameter-free graph (contains the MST, connected); a constant predictor scores exactly 0
whatever the prevalence; it is a point-cloud analogue of the boundary-F1 / normalized surface
distance used in segmentation (Csurka et al. 2013; Nikolov et al. 2018; *Metrics Reloaded*), and
graph cuts of point clouds converge to perimeters (García Trillos & Slepčev 2016), which motivates
cut edges as a discrete boundary.

**Synthetic validation against true surface distance (fig5, `synthetic/metric_validity_spearman.csv`):**
- The constant-majority predictor beats 12% (q20 acc) and 13% (full acc) of all AL predictors in
  the NEW-like scenario (up to 22–26% at σ = 1), 0% under BEF1/BER/BA/NSD; ≈0% in BAL.
- Spearman correlation with true NSD: in NEW-like cells BEF1 averages 0.55 vs q20 accuracy 0.38;
  in BAL and OLD cells full accuracy is as good as or better than BEF1 (0.55/0.61 vs 0.49/0.56).
  BEF1 is the most consistent across regimes, never the worst; q20 accuracy is never the best.
- **Displaced-boundary family (honest nuance):** for predictors with the correct shape, q20 accuracy
  peaks at the true level (δ = 0). Balanced metrics peak slightly on the minority side under label
  noise; BEF1 is least biased (argmax |δ| ≤ 0.5). But q20 accuracy ranks *no boundary at all*
  (δ = +1.5 in NEW, NSD 0.006) above *a boundary displaced 1.5 into the minority* (NSD 0.128):
  0.589 vs 0.550. BEF1 ranks them 0.004 vs 0.306, consistent with the true geometry.
- **Attenuation:** finite boundary metrics are scored against noisy observed labels, so even the
  Bayes boundary has BER ≈ 0.35 at σ = 1. Their absolute values are not boundary errors;
  comparisons are meaningful.

**Conclusion.** q20 accuracy is adequate for OLD-like prevalence and for comparisons within one
campaign whose band is near-balanced. It is not a valid boundary-recovery endpoint for NEW-like
imbalance. For the thesis: keep q20 accuracy as the historical primary, and add q20 BA, full BA,
rare recall and BEF1 as pre-declared secondary endpoints for any *future* comparison. No historical
conclusion is re-labelled.

## H. Model-transfer analysis — why M3 did not transfer

1. **The physics ordering transfers; the boundary orientation does not.** OLD: log h AUC 0.991, free
   exponent ratios (VX/P −0.52, LS/P −1.44) reproduce h. NEW: log h AUC 0.857, free ratios unstable
   (VX/P −2.1), and a single VX threshold (0.899) gives BA 0.918 versus 0.852 for the best log h
   threshold. The 50%-level of log h moves only +0.14 (bootstrap intervals overlap), so it is not a
   simple level shift: the NEW boundary is oblique to the h contours in the high-P/small-LS corner
   (fig4).
2. **OLD contained almost no evidence there.** Only 45 OLD cases fall in NEW's P–LS range, 43
   Keyhole and 2 non-Keyhole — both at VX 0.95–0.98, i.e. exactly on the NEW side of the VX
   threshold.
3. **M3 subordinates that local evidence to the global trend.** The OLD-fitted M3 discrepancy is
   effectively one-dimensional (ℓ = [100, 0.63, 100, 100], σ² = 1 at its cap); G3 learns
   σ² ≈ 380 with ℓ ≈ [7.6, 7.0, 8.4, 100], a smooth large-amplitude surface able to represent the
   P×VX corner.
4. **The cap is a minor part.** Relaxing it (exploratory, once): BA 0.579 → 0.617, rare 2 → 3 of 12,
   learned σ² only 1.9 — still far below G3 (0.700). The main effect is the anchoring of a globally
   correct trend into a region where the source campaign had too few contradicting cases.
5. **Synthetic reproduction (fig7).** With the physics law holding in the target region (A = 0)
   the physics models dominate (NSD 0.93–0.94 vs 0.65 for G3). With a local deviation
   (A = 1.5) the ranking reverses: BA G3 0.786 > uncapped M3 0.658 > capped M3 0.620 > H 0.539 —
   the same order and similar values as real OLD→NEW (0.70 > 0.62 > 0.58 > 0.50). The synthetic
   M3 also learns a VX-only discrepancy (ℓ_VX ≈ 5, others ≈ 65–70).
6. **Substrate temperature is not the explanation.** The Keyhole number of Gan et al. (2021)
   includes (T_l − T₀); h omits it. With T_l(Ti-6Al-4V) ≈ 1928 K, the factor can move log h by at
   most 0.13 across both campaigns and by 0.012 between NEW classes on average — too small.

**Design rule (supported synthetically, consistent with real):** a physics-informed mean helps
when the target region lies where the source data confirm the law, and hurts when the target
region is where the law is locally wrong and sparsely represented in the source. Use physics as an
ordering (for discovery and ranking) and let a flexible model own the local level.

## I. Acquisition analysis

- **Margin vs random.** Real: OLD +0.037 (with both rare-call precision and recall improving).
  NEW q20 accuracy favours random because margin's extra rare calls are 28–30% precise
  (Prop. 2). Synthetic: margin beats random on NSD in every cell, and on q20 accuracy whenever the
  model is adequate.
- **Random's competitiveness on NEW** = metric pathology (Prop. 1–2) + rare exhaustion + weak
  rare-class model. It is not evidence that random is a good acquisition rule.
- **Coverage / Candidate B.** Synthetic coverage-then-margin is never better than margin
  (generic model: −0.005 to −0.056 NSD in 9 of 12 cells; physics model: ≈ 0). The real NEW
  decomposition (+0.0026 = −0.0082 early margin + 0.0108 coverage) and the OLD +0.0067 are within
  the 0.014 OLD headroom. A plausible but **untested** mechanism for its OLD gain: at small
  budgets M3's hyperparameters are re-learned on few labels, and coverage diversifies those early
  labels. The synthetic study fixed hyperparameters and therefore could not show that effect.
  Candidate B remains a historical frozen challenger, unconfirmed.
- **Candidate A vs B coherence.** Both are dominated by early-phase effects inside the same tiny
  window; they do not tell a general story.

## J. Publication options (at most three)

**Option 1 (recommended) — Methodology paper: "Why acquisition comparisons fail in rare-regime
finite pools: discovery certificates, headroom and prevalence-invariant boundary evaluation for
active level-set estimation", with LPBF/SPH as the case study.**
- *Claim:* in small finite pools, measured acquisition value is bounded by headroom and distorted by
  band accuracy under imbalance; discovery must be certified or counted. Provides Props. 1, 2, 4,
  5, 7 and a pair-based boundary metric.
- *Evidence:* exact identities verified on real data; 2,880-path synthetic study with a known
  boundary; OLD/NEW case study (with the frozen STOP honestly reported).
- *Missing:* a second public benchmark (e.g. a standard LSE test function and one public tabular
  imbalanced dataset) to show generality; NSD for real data is impossible (unknown boundary).
- *Novelty risk:* moderate. AL-evaluation pitfalls (Lüth et al. 2023; Ji et al. 2023), margin's
  dominance (Bahri et al. 2022), AL sampling bias (Farquhar et al. 2021), rare-category detection
  (He & Carbonell 2007) and segmentation boundary metrics exist. The *combination* for level-set
  estimation, the exact disagreement window and the discovery certificate appear new in this
  form, but this targeted search does not exclude prior statements of Props. 1–2.
- *Venue:* TMLR, or a workshop at AISTATS/ICML (data-centric ML, AI for science); a journal such
  as *Machine Learning: Science and Technology* or *Statistical Analysis and Data Mining*.
- *Work:* 2–4 weeks (one extra benchmark, polishing proofs, writing).

**Option 2 — Physics priors under campaign shift: "Ordering transfers, level does not".**
- *Claim:* a physics-informed GP mean with a discrepancy learned on the source campaign anchors
  predictions where the source is uninformative; generic GPs transfer better there; proved partial
  bound (Prop. 7) plus the synthetic crossover (fig7) and the LPBF case.
- *Missing:* a second physical system or literature dataset; a principled alternative tested
  prospectively (only synthetically supportable now).
- *Risk:* the real evidence rests on 12 rare cases. *Venue:* *Integrating Materials and Manufacturing
  Innovation*, *Additive Manufacturing* (short communication), or a UQ venue (SIAM/ASA JUQ is
  probably too demanding). *Work:* 3–5 weeks.

**Option 3 — Application/negative-results paper for the AM community:** the preregistered OLD
programme, the frozen STOP and its geometric cause, startup rules and the transfer findings.
Lower ML novelty, high integrity value. *Venue:* *Additive Manufacturing Letters*, *JOM*, or a
negative-results track. *Work:* 2 weeks.

## K. Recommended thesis story (chapter level)

1. **Introduction.** Active level-set estimation for expensive deterministic simulators; the
   keyhole boundary.
2. **Background.** GP classification, LSE, finite-pool AL, physics scaling (h and Ke).
3. **Synthetic foundations (Weeks 1–4).** Short.
4. **The SPH campaigns and the physics coordinate.** OLD/NEW data, h, M3 construction.
5. **Acquisition on OLD (Weeks 8–10).** Margin ≫ random; the refinement zoo; Candidate B; then
   the headroom argument (0.014 window; +0.01 = 71%). Negative results framed as headroom-limited,
   not as failed creativity.
6. **The prospective attempt (Week 11).** Frozen protocol, STOP, why STOP was correct.
7. **Diagnosis: three mechanisms.** (a) Discovery certificates (Props. 4–6, fig1); (b) metric
   identities (Props. 1–2, Remark 3, fig2); (c) rare exhaustion and information limits (fig3).
8. **Evaluation of boundary recovery.** Boundary-edge metrics, synthetic validation against NSD
   (fig5), displaced-boundary family, recommendation.
9. **Physics priors under campaign shift.** Week 12 transfer, orientation shift (fig4), anchoring
   bound (Prop. 7), synthetic crossover (fig7), design rule.
10. **Acquisition headroom in a controlled study.** fig6: better model ⇒ less headroom; coverage
    vs margin.
11. **Discussion and limitations.** Development vs confirmation; 12 rare cases; synthetic ≠ SPH;
    what a future campaign would need (pre-declared endpoints from Ch. 8; startup with a certificate
    or physics ordering).

## L. Exact next actions

1. **Read and challenge `THEORY.md`.** Ask me (or Codex) to turn Props. 1, 2, 4, 7 into thesis-style
   LaTeX with full proofs and to check the literature for prior statements of Props. 1–2.
2. **Add one public benchmark** to the synthetic study for generality: e.g. Branin/Hartmann-type
   level sets with the same imbalance/pool factors (the repository's Week 1–3 code can be reused),
   using the same frozen analysis.
3. **Optional mechanism test for Candidate B:** repeat the synthetic study with hyperparameters
   re-learned at each budget (as M3 does), to test the "coverage stabilises early hyperparameters"
   hypothesis. Pre-register it first.
4. **Write Chapters 7–10** from this report and the figures in `figures/`.
5. **Do not** run further acquisition searches on OLD or NEW, do not reopen Week 11, and do not
   promote BEF1 to a historical primary endpoint.

## Limitations

- NEW has 12 rare cases; all real-data contrasts are conditional on one campaign; the 20 repeats are
  not independent.
- Synthetic results depend on the generator (smooth physics law + one localized deviation +
  iid boundary noise) and on oracle hyperparameters in the AL study.
- Boundary-edge metrics are attenuated by label noise and noisy with few rare cases.
- The M3 counterfactual (D8) and the level-shift summaries are post-hoc and descriptive.
- Literature checks were targeted, not systematic.

## References (checked this week)

- Gan et al. 2021, *Universal scaling laws of keyhole stability and porosity in 3D printing of metals*, Nat. Commun. 12:2379 — https://www.nature.com/articles/s41467-021-22704-0
- Gotovos et al. 2013, *Active learning for level set estimation*, IJCAI — https://www.ijcai.org/Proceedings/13/Papers/202.pdf
- Letham et al. 2022, *Look-ahead acquisition functions for Bernoulli level set estimation*, AISTATS — https://arxiv.org/pdf/2203.09751
- Bahri et al. 2022, *Is margin all you need?* — https://arxiv.org/abs/2210.03822
- Farquhar, Gal & Rainforth 2021, *On statistical bias in active learning*, ICLR — https://arxiv.org/pdf/2101.11665
- He & Carbonell 2007, *Nearest-neighbor-based active learning for rare category detection*, NeurIPS — https://mlanthology.org/neurips/2007/he2007neurips-nearestneighborbased/
- Csurka et al. 2013, *What is a good evaluation measure for semantic segmentation?*, BMVC — https://www.bmva-archive.org.uk/bmvc/2013/Papers/paper0032/abstract0032.pdf
- Maier-Hein et al., *Metrics Reloaded* — https://arxiv.org/pdf/2206.01653
- García Trillos & Slepčev 2016, *Continuum limit of total variation on point clouds* — https://arxiv.org/abs/1403.6355
- Lorena et al. 2019, *How complex is your classification problem?* — https://arxiv.org/pdf/1808.03591
- Week 12 literature record: Barata et al. 2021; Chandra et al. 2021; Zhao et al. 2021 (`outputs/week12_.../interpretation/TARGETED_LITERATURE.md`).
