# Week 15 — Can the true-boundary oracle be approximated without cheating?

Date 2026-10-04. Theory correction `2e52d227`; **pre-result freeze `58da2050`** (pushed before any held-out
or real-data run); results: final commit (see bottom). Evidence tags as in `CLAIM_LEDGER.md`.

## Verdict

# `NO NEW METHOD JUSTIFIED`

The proposed acquisition **EBR-D** fails the frozen success criteria. It is better than margin on the
true boundary in 7 of 16 held-out cells, its mean difference is −0.0095 NSD AULC, and it is catastrophic
(< −0.05) in two cells. Its mechanism reproduces: it acquires far fewer noisy labels. But that does not
translate into better boundaries outside well-specified worlds.

The research did produce four durable results:
1. **A corrected discovery theory** (T_both law).
2. **A decomposition of the oracle headroom.** It is mostly *truth knowledge*, not label peeking.
3. **A measured frontier for legal rules.** Even an exact Bayes look-ahead captures only a fraction of
   that headroom, and only when the model is well specified.
4. **A theorem explaining why perimeter-type look-ahead risks must be normalized** (size bias).

Margin remains the most robust legal refinement rule in physics-like, rough or noise-free regimes.

---

## 1. Corrected Week 14 theory (`THEORY_ERRATA.md`, committed before method work)

- **E15-1.** Under the exchangeable fixed-K model, for every adaptive rule:
  - P(T_both > 0) = 1;
  - P(T_both > t) = [C(K,t) + C(N−K,t)] / C(N,t) for t ≥ 1;
  - E[T_both] = (N+1)/(K+1) + (N+1)/(N−K+1) − 1.

  The proof uses the two ξ-determined continuation sequences, which give disjoint events for t ≥ 1. It
  was verified exactly in rational arithmetic for N < 40, and by simulation of a rule whose continuation
  depends on the first label. Week 14 had stated "the same holds for T_both" after the T_m formula,
  which is wrong as written.
- **E15-2:** H₁₀₈⁽²⁾ = 14.7 (not 11).
- **E15-3:** D4 is tight iff the minority cases are consecutive in the score order.
- **E15-4:** the O1a log-linear implied set contains, but need not equal, the convex-hull closure.
- **E15-5:** Week 13 Prop. 6 needs the t = 0 term set to 1 (erratum only; Week 13 file not edited).

No Week 13/14 empirical result used the erroneous formula.

## 2. The central question and the decisive first experiment

Week 14's true-NSD oracle saw each candidate's *realized* noisy label. An **expectation oracle** knows
the truth and the noise law but not the realization, so it is the best one-step design available to
anyone with a perfect model. On the development generator (σ = 0.5, mean NSD AULC):

| scenario | random | margin | expectation oracle | realized-label oracle |
|---|---:|---:|---:|---:|
| BAL-like | 0.842 | 0.899 | 0.949 | 0.952 |
| OLD-like | 0.798 | 0.835 | 0.909 | 0.909 |
| NEW-like | 0.664 | 0.845 | 0.921 | 0.949 |

Label peeking explains only 0.003 / 0.000 / 0.028; knowing the truth explains 0.05–0.08.
Proposition B4 makes this exact for one step: realized ≥ expectation ≥ Bayes ≥ any legal rule.
The expectation oracle acquires almost no flipped labels (0.2–1%) because it knows where the boundary is.

## 3. The method: Expected Boundary-edge Risk reduction, Dice-normalized (EBR-D)

**Exact definition** (`src/week15_ebr.py`; hyperparameters in `FREEZE.md`):
- Use a uniform reference cloud Z (400 points) with a symmetric kNN graph (k = 8).
- From the Laplace posterior take latent marginals and exact pairwise correlations, and compute for each
  edge P(true crossing) and P(true crossing ≠ predicted crossing) via bivariate-normal orthants
  (Owen's T).
- R_D = Σ P(mismatch) / (Σ P(true crossing) + #predicted crossings).
- Acquisition: choose the unlabelled pool case maximizing R_D(D) − Σ_y p_D(y|c) R_D(D ∪ (c, y)), with a
  full refit for each fantasy label.
- **Ablation VSUR:** the same look-ahead with the expected misclassified latent-sign volume.

**Mathematical motivation** (`THEORY_WEEK15.md`):
- **B1.** The number of mismatched edges equals the cut of the error set (an XOR identity). EBR is
  therefore the expected *perimeter* of the misclassified region, while VSUR (the excursion-set/Vorob'ev
  family) is its expected *volume*.
- **B2.** On a uniform cloud this is a consistent estimator of the nonlocal perimeter. EBR-D estimates
  one minus an r-scale boundary Dice, the soft analogue of NSD.
- **B3 (counterexample).** Take a flat boundary whose location uncertainty exceeds the resolution. The
  unnormalized risk of the plug-in predictor is ≈ 2× that of the constant predictor, so unnormalized EBR
  is rewarded for erasing boundaries. That was exactly its development collapse (NEW-like σ = 1: 0.267
  vs margin 0.747). The Dice normalization removes the incentive, and was the single principled revision.

## 4. Development evidence (before the freeze)

- **EBR-D removed the collapse** (0.669) but was ≤ margin in all 9 development cells (−0.002 to −0.078).
  VSUR, BALD and coverage were also ≤ margin.
- **Oracle alignment.** No legal criterion ranks candidates like the oracle does (Spearman |ρ| ≤ 0.27).
  Choosing the most reliable labels with truth-knowledge gains nothing either.
- **Well-specified 3-D GP world.**
  - Per step: the exact Bayes look-ahead (posterior-sampled NSD) gains +0.0155, versus the oracle's
    +0.0645; EBR-D gains +0.0081; margin −0.0070 (negative).
  - Over paths: EBR-D and exact Bayes are +0.0099 and +0.0097 NSD AULC over margin. ASSD is −0.026
    [−0.065, 0.006] and −0.035 [−0.072, −0.004].

  So model-based boundary look-ahead *can* help when the model is right.
- The pre-stated expectation in `FREEZE.md` was: probably no gain on physics-like noisy families,
  possible gain on well-specified ones.

## 5. Frozen held-out results (16 cells × 8 reps; `heldout/`)

Mean NSD AULC (τ = 0.1):

| cell | random | margin | coverage | BALD | VSUR | EBR-D |
|---|---:|---:|---:|---:|---:|---:|
| gpworld m0 0, 108 | .616 | .623 | .657 | .654 | .644 | .645 |
| gpworld m0 0, 324 | .631 | .639 | .657 | .650 | .643 | .640 |
| gpworld m0 −4, 108 | .093 | .062 | .043 | .051 | .067 | .094 |
| gpworld m0 −4, 324 | .129 | .012 | .014 | .009 | .021 | .036 |
| curvedMono OLD σ0 | .818 | .932 | .917 | .908 | .933 | .918 |
| curvedMono OLD σ.5 | .833 | .905 | .888 | .895 | .907 | .906 |
| curvedMono OLD σ1 | .823 | .836 | .828 | .845 | .847 | .840 |
| curvedMono NEW σ0 | .891 | .959 | .954 | .927 | .958 | .942 |
| curvedMono NEW σ.5 | .769 | .824 | .839 | .724 | .823 | .822 |
| curvedMono NEW σ1 | .477 | .501 | .492 | .499 | .442 | .498 |
| curvedMono NEW σ.5, 324 | .736 | .881 | .868 | .705 | .863 | .880 |
| curvedMono NEW σ1, 324 | .550 | .668 | .678 | .613 | .543 | .638 |
| branin4d σ0 | .829 | .860 | .854 | .847 | .825 | .791 |
| branin4d σ.5 | .662 | .713 | .733 | .713 | .637 | .739 |
| rough σ.5 | .459 | .695 | .668 | .638 | .686 | .662 |
| rough σ1 | .439 | .580 | .552 | .454 | .540 | .488 |
| **average over cells** | .610 | **.668** | .665 | .633 | .649 | .659 |

Average over cells of ASSD / q20 accuracy / BA:

| | random | margin | coverage | BALD | VSUR | EBR-D |
|---|---|---|---|---|---|---|
| ASSD | .222 | .202 | **.186** | .224 | .292 | .198 |
| q20 accuracy | .673 | .683 | .680 | .677 | .685 | .681 |
| BA | .751 | .760 | .760 | .752 | .752 | .756 |

Mean NSD rank (1 = best): margin 2.56, coverage 2.94, EBR-D 3.06, VSUR 3.31, BALD 4.12, random 5.00.

**Frozen criteria** (`heldout/VERDICT.json`):

| criterion | result | detail |
|---|---|---|
| S1 majority of cells | ✗ | 7/16 better NSD, 7/16 better ASSD |
| S2 no catastrophe | ✗ | rough σ1 −0.092; Branin σ0 −0.068 |
| S3 noisy regime | ✗ | mean over noisy cells ≈ −0.004, although margin's flipped share exceeds EBR-D's in most of them |
| S4 noise-free comparable | ✗ | −0.068, −0.018, −0.013 |
| S5 identical startup | ✓ | — |
| S6 pools/imbalance | ✗ | — |
| "useful" regime test | ✗ | gpworld positive in 4/4 cells but CI above 0 in only 1 (needed ≥ 2); noisy group mean negative |

**Unattainable reference.** On two cells the expectation oracle reaches 0.602 (margin 0.399, EBR-D
0.491; curvedMono NEW σ = 1) and 0.40 (all legal ≤ 0.14; gpworld m0 = −4). The headroom is large and
mostly not captured.

**Ablation.** EBR-D − VSUR = +0.010 NSD on average: within the same look-ahead, the boundary target beats
the volume target. VSUR also has the worst ASSD (0.292).

## 6. Failure analysis

1. **Noise-free boundaries.** For deterministic boundaries with a well-fitted model, querying at the
   boundary is near-optimal. EBR-D spends early queries on posterior-uncertain regions away from it
   (Branin σ0: B16–40 deficit −0.138, B40–80 −0.026).
2. **Coherent roughness (rough family).** The label "noise" is spatially coherent and not represented
   by the logistic-GP likelihood. The posterior is confidently wrong in patches, and the model-internal
   risk points to the wrong cases (−0.033, −0.092).
3. **Avoiding noisy labels is not enough** (fig3). EBR-D lowers the flipped-label share in most noisy
   cells, sometimes sharply (0.07 vs 0.37 in curvedMono NEW σ1 pool 324) and sometimes barely (0.078 vs
   0.085), yet NSD does not improve. The oracle's
   gain comes from knowing which cases change the boundary *toward the truth*, which the posterior cannot
   see (development alignment |ρ| ≤ 0.27).
4. **Where it helps.** Only where the model is the data-generating model (gpworld), or the noise is iid
   probit with a moderate fitted amplitude (Branin σ.5, +0.026), and in the external Ti64 replay (§7).
   The gains are small. Two gpworld cells are near-floor for every legal policy.
5. **Historical q20 is not a reliable guide here.** It agrees in sign with the true-boundary contrast in
   10/16 cells (62.5%); BA agrees in 12/16.

**Revision decision.** The brief allowed at most one principled revision after a frozen failure. I made
none. The failure is located in the model's ability to represent where it is wrong (misspecification,
coherent roughness), not in the acquisition formula. The only candidate fix — a calibration-gated hybrid
that uses EBR-D only when posterior checks indicate a well-specified model — would need new held-out
families, and its expected gain is bounded by the small well-specified gains measured here. It is
recorded as SPECULATIVE.

## 7. Real-data secondary replays (descriptive; `real_data/`)

Model: fixed-hyperparameter GPC with historical OLD G3 ML-II hyperparameters. For Masinelli the
hyperparameters come from the other material.

| campaign (tag) | metric | EBR-D − margin AULC [95% CI] |
|---|---|---|
| NEW-136, 20 repeats (POST-HOC) | q20 accuracy | +0.017 [−0.003, 0.036] |
| | pooled BA | −0.006 [−0.032, 0.019] |
| | pooled DC-BD | +0.003 [−0.028, 0.034] |
| OLD, repeats 1–4 (HISTORICAL) | q20 accuracy | −0.007 [−0.021, 0.006] |
| | DC-BD | −0.011 [−0.029, 0.012] |
| Masinelli 316L (EXTERNAL, clean labels) | DC-BD | −0.030 [−0.047, −0.016] |
| | BA | −0.002 |
| Masinelli Ti64 (EXTERNAL, conflicting repeated conditions) | DC-BD | +0.047 [0.015, 0.088] |
| | minority recall | +0.018 [0.004, 0.033] |
| | q20 accuracy | +0.029 |

The Masinelli pattern matches the synthetic mechanism (help with noisy labels, loss with clean ones),
but with 4 repeats on 60 bundles it is a hypothesis, not evidence. One side observation: with the G3-type
model, mean-fold q20 accuracy on NEW reaches 0.70–0.73 for every policy, above the always-Keyhole 0.685
that the Week 12 M3 runs never beat. The model, again, matters more than the acquisition rule.

## 8. Evaluation metric (DC-BD)

**DC-BD** is an importance-weighted r-graph boundary Dice (`src/week15_metric.py`; Proposition M1).
- *What it estimates.* With the true density it estimates the r-scale boundary Dice of a uniform cloud,
  independently of sampling density; the plug-in version with a kNN density estimate is consistent.
- *Development.* Density sensitivity was 5–8× lower than the unweighted version under smooth shifts.
  Correction was incomplete under thin bands (assumption violated).
- *Held-out.* It reduced density sensitivity relative to the unweighted r-graph in every smooth cell.
  It **failed** M-a: in the two-component shape it is more density-sensitive than q20 accuracy (0.276 vs
  0.220), and full BA is the least density-sensitive metric overall. It also failed M-b in one cell, by
  0.002. On rank agreement with −ASSD it is best or near-best in most cells.
- *Conclusion.* No finite-pool metric tested is density-free at these sample sizes. DC-BD is the version
  with a stated estimand, useful as a secondary metric. q20 remains reported for historical continuity.

## 9. What should enter the thesis

- **Discovery chapter.** The corrected D1 with the T_both law.
- **Acquisition headroom chapter.** Replace the Week 14 statement "true headroom exists" with the
  measured decomposition (fig2, Proposition B4):
  - label peeking is small;
  - truth knowledge is large;
  - an exact Bayes look-ahead captures a fraction of it only in well-specified worlds;
  - margin is the most robust legal rule (held-out ranks, fig1).
- **Method chapter (negative result).** Present EBR → EBR-D as a principled, theory-backed attempt,
  with B1–B3, the frozen protocol, its failure and the mechanism (fig3). Present VSUR as evidence that a
  boundary target beats a volume target inside look-ahead.
- **Evaluation chapter.** Add DC-BD (M1) next to the Week 14 density-weighting results; report its
  held-out failure honestly.

**Paper.** A negative-results / evaluation contribution: "True-boundary headroom in active level-set
estimation is real but mostly unattainable: an oracle decomposition and a frozen test of boundary-risk
look-ahead". Venue: TMLR or a workshop on AL evaluation.

## 10. Provenance

- Documents: `THEORY_ERRATA.md`, `THEORY_WEEK15.md`, `FREEZE.md` (incl. deviation D1), `RESEARCH_LOG.md`,
  `NOVELTY_AUDIT.md`, `CLAIM_LEDGER.md`.
- Development outputs: `development/`.
- Held-out outputs: `heldout/` (768 path files, `VERDICT.json`, `METRIC_VERDICT.json`).
- Real-data outputs: `real_data/`.
- Figures: `figures/fig1–fig4`.
- Code: `src/week15_*.py`.
- Tests: `src/tests/test_week15_*.py`.
