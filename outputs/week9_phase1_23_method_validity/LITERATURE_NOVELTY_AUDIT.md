# Literature and novelty audit — boundary-conditioned coverage before margin

Phase 1.23, Part A. Goal: decide what, if anything, is new in `coverage_then_margin_B40` and `early8__coverage_then_margin_B40`. Wording differences do not count as novelty.

**Verification status.**
- ✓ = content checked in this session: abstract or text retrieved.
- (m) = cited from memory of the standard literature; the bibliographic details are well known, but the text was not re-read here.

Nothing below is quoted at length.

## 1. The method, stated neutrally

A finite pool, a GP-classification model whose latent mean is a steep logistic in a known scalar physics coordinate $h$ plus a GP discrepancy (M3), and a budget from 16 to 80 labels. Before B40:
1. Form the interval between the lowest queried positive and the highest queried negative in $h$, padded by 25% (floor 0.05).
2. Among pool points in that interval, maximise rank(model uncertainty) + rank(distance to the nearest queried point, standardised inputs).

From B40 on, use plain probability margin. The practical variant starts active learning after 8 maximin points instead of 16.

Decomposed into ideas:
- **I1:** uncertainty (margin) sampling.
- **I2:** diversity or coverage via distance to already-labelled points.
- **I3:** diversity restricted to a boundary region.
- **I4:** the boundary region defined from revealed labels, not from the model.
- **I5:** region defined in a physics coordinate.
- **I6:** a budget-dependent switch, exploration early and uncertainty late.
- **I7:** a physics-informed prior mean with a GP discrepancy.
- **I8:** a smaller space-filling seed before active learning.

## 2. Close methods, one by one

For each: (1) what it selects; (2) information used; (3) global or boundary-conditioned diversity; (4) whether the boundary region depends on revealed labels; (5) physics prior; (6) whether it addresses a strong prior collapsing uncertainty sampling onto a slab; (7) how ours differs; (8) whether the difference is genuine.

### 2.1 Uncertainty / margin sampling — Lewis & Gale 1994 (m); Scheffer et al. 2001 (m); Settles 2009 survey (m)
1. Selects the point with the smallest $|p-1/2|$ (margin) or maximal entropy.
2. Uses only the model's predictive distribution.
3. No diversity.
4. No explicit region.
5. Model-agnostic.
6. No. The literature documents sampling bias (Dasgupta & Hsu 2008 ✓; Schein & Ungar 2007 ✓), not this specific collapse.
7. Ours equals margin after B40 (it is our control and our late phase).
8. Not different.

### 2.2 Straddle and GP level-set estimation — Bryan et al. 2005 ✓; Gotovos et al. 2013 (LSE) ✓; Bogunovic et al. 2016 (TruVaR) ✓; Mason et al. 2022 ✓
1. Straddle selects $\arg\max\ 1.96\sigma(x)-|\mu(x)-\tau|$. LSE classifies points whose confidence interval excludes $\tau$ and queries the most ambiguous unclassified point. TruVaR greedily shrinks truncated variances over the unclassified set.
2. GP posterior mean and variance; LSE and TruVaR also the set of still-unclassified points.
3. No explicit distance-based diversity. Variance terms push away from queried points implicitly, and TruVaR's set-level variance reduction spreads queries.
4. The unclassified set depends on revealed data through the GP posterior, not directly on label order statistics.
5. No physics prior.
6. No.
7. We use a probability-margin model with a steep physics mean and an explicit distance term, inside an interval computed from label order statistics in $h$.
8. The structure of I3/I4 is shared in spirit: "sample where still ambiguous". The concrete rule differs; the principle does not. Straddle is included as a baseline in Part C.

### 2.3 Reliability / contour learning functions — Echard et al. 2011 (AK-MCS, U) ✓; Bichon et al. 2008 (EFF) ✓; Ranjan et al. 2008 (contour EI) (m); Picheny et al. 2010 (targeted IMSE) ✓; Bect et al. 2012 (m); Chevalier et al. 2014 (SUR) ✓; Cole et al. 2023 (entropy contour) ✓; Marques et al. 2018 (CLoVER) (m); Lyu, Binois & Ludkovski 2021 ✓
1. U selects $\arg\min|\mu|/\sigma$; EFF and contour-EI reward a $\pm\epsilon$ band around the limit state; targeted IMSE and SUR minimise expected variance or misclassification integrated over the region near the threshold.
2. Kriging (GP regression) mean and variance.
3. Targeted IMSE and SUR are **boundary-conditioned coverage by construction**: integrating variance reduction over the target region spreads designs along the contour. U and EFF are not explicitly diverse.
4. The target region is defined by the posterior, not by label order statistics.
5. No physics prior (a prior mean is possible but not the point).
6. No.
7. Ours is a cheap rank-sum heuristic for classification labels, not an integrated criterion; the region comes from labels in $h$.
8. **tIMSE/SUR already implement "spread along the estimated boundary" in a principled way.** Ours is a cruder approximation; the difference lies in cost and model class, not in principle.

### 2.4 Distance-constrained reliability learning functions (a large engineering literature, e.g. the "penalty" and "distance constraint" U-function variants surveyed in the 2023 CMAME search result ✓ at abstract level)
1. U (or a similar score) multiplied or constrained by a distance-to-existing-samples term, to avoid clustered samples near the limit state.
2. Kriging mean and variance plus distances.
3. **Boundary-conditioned diversity** (score concentrated near the limit state, plus a distance penalty).
4. The region comes from the model.
5. No physics prior.
6. The motivation is clustering of samples near the limit state, the same symptom we see. The cause (a steep prior switching off the discrepancy) is not discussed in what we retrieved.
7. Ours defines the region from labels in a physics coordinate and switches the distance term off at B40.
8. **Largely not different in principle.** "Uncertainty near the boundary + distance to existing samples" is established.

### 2.5 Max-min sampling on an estimated decision boundary — Basudhar & Missoum 2008 ✓, 2010 ✓; Lacaze & Missoum 2014 ✓
1. New samples on the current SVM decision boundary that maximise the minimum distance to existing samples. The 2010 version adds a sample to remove a boundary "locking" phenomenon. The 2014 version weights max-min by the input density.
2. SVM boundary estimate plus sample geometry.
3. **Boundary-conditioned max-min: the closest precedent to our I2 + I3.**
4. The boundary is the SVM fitted to revealed labels, so it depends on labels through the model.
5. No physics prior.
6. "Locking", where adaptive samples on the boundary stop changing it, is a related phenomenon, described for SVMs. Its cause there is not the same as ours (A2–A4 of the theory note).
7. Our region is a label-defined interval in a physics coordinate, not the model's zero set. We combine distance with an uncertainty rank, and we switch to margin.
8. **The core idea (spread samples along the estimated boundary) is not new.** The differences are adaptations.

### 2.6 Classification-boundary sequential sampling with exploration — Singh et al. 2017 ✓
1. Combines a Voronoi-cell exploration score with a local-nonlinearity (boundary) exploitation score, balanced by an ε-schedule.
2. Sample geometry plus local model behaviour.
3. Global exploration mixed with boundary exploitation.
4. Region from model or neighbours.
5. No physics prior.
6. No.
7. Ours restricts exploration to the boundary band rather than mixing in global exploration.
8. A modest difference.

### 2.7 Uncertainty + diversity (batch) — Brinker 2003 ✓; Xu et al. 2003 ✓; Nguyen & Smeulders 2004 ✓; Settles & Craven 2008 (information density) ✓; Zhdanov 2019 ✓; Ash et al. 2020 (BADGE) ✓; Citovsky et al. 2021 (Cluster-Margin) ✓
1. Batches that are both uncertain and mutually diverse.
   - Brinker: angle diversity.
   - Xu et al.: cluster the documents **inside the SVM margin** and query cluster representatives.
   - Zhdanov: prefilter the top-β uncertain points, then weighted k-means.
   - Cluster-Margin: diverse sampling across clusters of low-margin points.
   - BADGE: k-means++ on gradient embeddings.
2. Model uncertainty plus embeddings or distances.
3. **Boundary-conditioned** for Xu et al. (margin region), Zhdanov (uncertainty prefilter) and Cluster-Margin (low-margin set); global/embedding-based for Brinker and BADGE.
4. The region is model-defined (margin or uncertainty).
5. No physics prior.
6. They address redundancy within a batch, not a prior-induced collapse across sequential steps.
7. Ours is sequential (batch size 1), uses distance to all queried points (not within-batch diversity), and defines the region from labels in $h$.
8. **"Diversity among uncertain / near-boundary points" is established (Xu et al. 2003 is essentially the same idea for SVMs).** Not new.

### 2.8 Disagreement-based active learning — Cohn, Atlas & Ladner 1994 (CAL) (m); Balcan, Beygelzimer & Langford 2006 (A²) (m); Hanneke 2014 monograph (m)
1. Sample only inside the region of disagreement of hypotheses consistent with the revealed labels.
2. The hypothesis class and the revealed labels.
3. No explicit diversity (CAL samples from the disagreement region according to the data distribution).
4. **Yes: the region is defined by revealed labels.**
5. The hypothesis class can encode prior structure.
6. No.
7. **Key observation:** for the hypothesis class "thresholds in $h$", the disagreement region after separable labels is exactly the gap between the highest queried negative and the lowest queried positive, which is our label-estimated band before padding. Our band is therefore a padded CAL disagreement region for 1D physics thresholds. Inside it we add uncertainty and distance ranks, and we keep using it after separability breaks (then as the overlap interval).
8. **I4 (a label-defined region) is classical.** New is only applying it to a 1D physics-threshold class while *fitting* a richer model (M3) and scoring with that model.

### 2.9 Coverage / typicality in the low-budget regime and switching — Donmez et al. 2007 (DUAL) ✓; Osugi, Kun & Scott 2005 ✓; Hsu & Lin 2015 (ALBL) ✓; Hacohen et al. 2022 (TypiClust) ✓; Yehuda et al. 2022 (ProbCover) ✓; Sener & Savarese 2018 (core-set) (m)
1. DUAL switches from density-weighted to uncertainty sampling as labels accumulate. Osugi et al. randomly explore with an adaptive probability. ALBL learns which strategy to use with a bandit. TypiClust and ProbCover choose typical or covering points at low budget, and Hacohen et al. show a phase transition: typical points at low budget, uncertain points at high budget. Core-set does k-center covering.
2. Data geometry and density; uncertainty later.
3. **Global** coverage or density.
4. No boundary region.
5. No physics prior.
6. They address the unreliability of uncertainty at low budget in general, not a physics-prior slab collapse.
7. Ours restricts coverage to a boundary band and uses a fixed switch (B40), not an adaptive one.
8. **I6 ("explore/cover early, exploit uncertainty late") is established,** with theory (Hacohen et al.). Our fixed B40 switch is a weaker, tuned instance.

### 2.10 Minimax theory for boundary fragments — Castro & Nowak 2008 ✓
1. A grid of lines across the $d-1$ orthogonal coordinates, with 1D probabilistic bisection along the remaining coordinate on each line, then interpolation.
2. Labels only, plus the boundary-fragment structure.
3. **Spread along the boundary (lines over the orthogonal coordinates) × bisection across it.**
4. The bisection intervals depend on revealed labels.
5. The coordinate along which the boundary is a graph is assumed known, analogous to knowing $h$.
6. They remark that practical active learners get side-tracked by the first labels; no slab-collapse analysis.
7. Ours is a finite-pool, model-based, heuristic approximation. There are no fixed lines; spread arises from a distance rank inside the band.
8. **The structural idea behind our rule is minimax-optimal textbook theory.** Our rule is an approximation of it, not an advance on it.

### 2.11 Physics-informed priors in active classification and phase mapping — Vela et al. 2025 (physics-informed GPC prior means) ✓; Kusne et al. 2020 (CAMEO) ✓; Terayama et al. 2019 (phase diagrams by uncertainty sampling) ✓; Dai, Bruss & Glotzer 2020 ✓; Fan et al. 2026 (BALPI: SMOCU, e-straddle) ✓; Kennedy & O'Hagan 2001 (model discrepancy) (m)
1. Vela et al.: a GPC with a CALPHAD / physics prior mean, maximum-entropy acquisition. Terayama, Dai et al.: uncertainty-driven phase-boundary sampling. BALPI: non-myopic Bayesian criteria. CAMEO: physics-informed phase mapping inside closed-loop Bayesian active learning.
2. The model posterior plus a physics prior (Vela, CAMEO).
3. No explicit diversity in Vela, Terayama or Dai, as far as retrieved. CAMEO and BALPI use richer objectives.
4. Model-defined regions.
5. **Yes (I7): prior-mean-plus-discrepancy GPCs exist** (Vela et al. 2025 is structurally close to M3).
6. **No.** Vela et al. report the prior helping in early iterations; none of the retrieved works analyses a steep prior switching off the discrepancy and trapping uncertainty sampling.
7. We diagnose that failure for the steep-logistic-mean + GP-discrepancy class (theory note A2–A4) and counter it with early band coverage.
8. **The model class is not new. The diagnosis appears to be new** (not found), as does its demonstration on SPH data.

### 2.12 Additive-manufacturing regime maps — King et al. 2014 ✓ and Hann et al. 2011 ✓ (normalised enthalpy as the keyhole coordinate); sequential learning for LPBF melt-pool defects (2024/2025, least-confidence + Sobol synthetic sampling) ✓; Phase 1.10 Masinelli maps
1. The physics coordinate (normalised enthalpy threshold ≈ 25–30) predates us. The recent LPBF active-learning work uses least-confidence sampling plus quasi-random exploration.
2. Physics scaling and a model posterior.
3. Global exploration (Sobol).
4. No label-defined region.
5. A physics coordinate is used for regime maps but not as a steep GP prior mean inside active learning, as far as retrieved.
6. No.
7. Ours combines a physics coordinate prior, a discrepancy GP, and early band coverage for keyhole regime maps.
8. **As an application to SPH keyhole regime maps, the combination appears not to have been reported.** That is an application contribution.

## 3. Comparison table

| method | selects | uses | diversity | region from revealed labels | physics prior | addresses prior-induced slab collapse | genuinely different from ours? |
|---|---|---|---|---|---|---|---|
| margin / uncertainty sampling | min $|p-1/2|$ | model posterior | none | no | no | no | no (our control) |
| straddle, LSE, TruVaR | ambiguous points w.r.t. level | GP mean/var | implicit (variance) | via posterior | no | no | principle shared |
| U, EFF, contour EI | near limit state | Kriging mean/var | none | via posterior | no | no | principle shared |
| targeted IMSE, SUR | integrated variance/risk near level | GP posterior | **boundary-conditioned (implicit)** | via posterior | no | no | **principled version of our idea** |
| distance-penalised U variants | near limit state + far from samples | Kriging + distances | **boundary-conditioned** | via posterior | no | symptom only | **not in principle** |
| Basudhar & Missoum max-min | on SVM boundary, max-min distance | SVM + geometry | **boundary-conditioned max-min** | via SVM | no | "locking" (related) | **closest precedent** |
| Singh et al. 2017 | exploration + boundary exploitation | Voronoi + local fit | global + boundary mix | no | no | no | modest |
| Xu et al. 2003; Zhdanov 2019; Cluster-Margin | diverse among uncertain | model + clustering | **boundary-conditioned (model-defined)** | no | no | no | not in principle |
| Brinker 2003; BADGE; core-set | uncertain + diverse / covering | model + embedding | global | no | no | no | band conditioning differs |
| CAL / A² | inside disagreement region | hypotheses + labels | none | **yes** | via hypothesis class | no | **our band = padded CAL region for 1D thresholds in $h$** |
| DUAL, TypiClust, ProbCover, Osugi, ALBL | cover or density early, uncertainty later | geometry, density | global | no | no | low-budget unreliability | switch idea established |
| Castro & Nowak 2008 | lines across $z$ × bisection along $h$ | labels, known graph direction | **spread along boundary** | yes (bisection) | known direction | no | **our rule approximates it** |
| Vela et al. 2025 (physics-informed GPC) | max entropy | physics prior mean + GP | none | no | **yes** | **no (prior reported to help early)** | model class shared; diagnosis not |
| LPBF sequential learning 2024/25 | least confidence + Sobol | RF + quasi-random | global | no | no | no | application differs |

## 4. What is not novel (to be said plainly)

- Uncertainty sampling, margin sampling, straddle-type level-set criteria (I1).
- Diversity by distance to labelled points; max-min sampling (I2).
- Diversity restricted to a boundary or uncertain region (I3): Xu et al. 2003, Basudhar & Missoum 2008/2010, Zhdanov 2019, Cluster-Margin 2021, distance-penalised reliability functions, and implicitly tIMSE/SUR.
- A region defined from revealed labels (I4): disagreement-based active learning since 1994.
- Exploration or coverage early, uncertainty late (I6): DUAL 2007, Hacohen et al. 2022.
- Physics prior mean + GP discrepancy in GP classification (I7): Kennedy–O'Hagan discrepancy, Vela et al. 2025.
- Space-filling initial designs (I8).
- The structural principle "spread along the boundary, bisect across it": Castro & Nowak 2008.

## 5. What might be novel (narrow, and to be tested rather than asserted)

- **N1 (diagnosis, supported by exact lemmas plus SPH diagnostics).** For GP classification with a nearly unregularised logistic mean in a physics coordinate plus a bounded-variance GP discrepancy:
  - while the queried labels are separable in that coordinate, the fitted mean is a near-step at the gap midpoint (A2);
  - the discrepancy posterior mean is forced to near zero (A4);
  - margin sampling degenerates to bisection along the physics coordinate (A1, B1), which by itself never breaks separability (A3).

  We did not find this failure mechanism described for physics-informed GPCs. It is a statement about a model class, not about acquisition in general.
- **N2 (adaptation).** Using the padded disagreement interval of 1D thresholds in the *physics coordinate* as the region for uncertainty + distance sampling, only in the early budget, to break that lock. Each ingredient is known; the specific combination and its motivation by N1 are, as far as we found, not reported. **Only defensible as novel if Part C shows the band conditioning matters,** i.e. beats the same score without the band.
- **N3 (application evidence).** A pre-registered, replicated low-budget gain for SPH keyhole regime maps on untouched partitions of the same 405-simulation population. Internal, not external validation.

## 6. Narrowest defensible novelty claim

> We identify a prior-induced failure mode of margin sampling for GP classifiers with a steep physics-coordinate logistic mean and a GP discrepancy: until the queried labels stop being separable in the physics coordinate, the discrepancy is inert and margin reduces to bisection along that coordinate. We show that a simple, literature-standard remedy — uncertainty-plus-distance sampling restricted to the label-defined disagreement interval in the physics coordinate, used only early — improves low-budget boundary accuracy on SPH keyhole data under pre-registered internal replication.

This is a **diagnosis plus an adaptation of known ideas plus an application result.** It is not a new acquisition principle. Whether it is more than an SPH-specific adaptation is decided by Part C, not by this audit.

**Claims we must not make:** "a novel acquisition function", "a new uncertainty–diversity method", "the first boundary-aware diversity strategy", "theoretically optimal", "physics-informed active learning is new".

## Sources (retrieved in this session)
- [Basudhar & Missoum 2010, SMO](https://link.springer.com/article/10.1007/s00158-010-0511-0); [2008, Computers & Structures](https://www.sciencedirect.com/science/article/abs/pii/S0045794908000515); [Lacaze & Missoum 2014](https://link.springer.com/article/10.1007/s00158-013-1011-9)
- [Singh et al. 2017, SMO](https://link.springer.com/article/10.1007/s00158-016-1584-1)
- [Donmez, Carbonell & Bennett 2007, DUAL](https://www.cs.cmu.edu/~jgc/publication/Dual_Strategy_ECML_2007.pdf)
- [Hacohen, Dekel & Weinshall 2022](https://arxiv.org/abs/2202.02794); [Yehuda et al. 2022, ProbCover](https://arxiv.org/abs/2205.11320)
- [Citovsky et al. 2021, Cluster-Margin](https://arxiv.org/pdf/2107.14263); [Zhdanov 2019](https://arxiv.org/abs/1901.05954); [Ash et al. 2020, BADGE](https://arxiv.org/abs/1906.03671)
- [Brinker 2003](https://www.semanticscholar.org/paper/Incorporating-Diversity-in-Active-Learning-with-Brinker/0ca966cb390b442b10cb76aa3fddee6b613f4f0f); [Xu et al. 2003](https://link.springer.com/chapter/10.1007/3-540-36618-0_28); [Nguyen & Smeulders 2004](https://icml.cc/Conferences/2004/proceedings/papers/94.pdf); [Settles & Craven 2008](https://aclanthology.org/D08-1112/)
- [Bryan et al. 2005, straddle](https://papers.nips.cc/paper/2940-active-learning-for-identifying-function-threshold-boundaries); [Gotovos et al. 2013, LSE](https://www.ijcai.org/Proceedings/13/Papers/202.pdf); [Bogunovic et al. 2016, TruVaR](https://arxiv.org/abs/1610.07379); [Mason et al. 2022](https://arxiv.org/abs/2111.01768)
- [Castro & Nowak, Minimax bounds for active learning](https://rmcastro.win.tue.nl/publications/castro_IT_minimax.pdf)
- [Picheny et al. 2010](https://hal-emse.ccsd.cnrs.fr/emse-00699752); [Chevalier et al. 2014](https://www.tandfonline.com/doi/abs/10.1080/00401706.2013.860918); [Echard et al. 2011, AK-MCS](https://www.sciencedirect.com/science/article/abs/pii/S0167473011000038); [Bichon et al. 2008, EGRA](https://arc.aiaa.org/doi/pdfplus/10.2514/1.34321); [Cole et al. 2023](https://arxiv.org/pdf/2105.11357); [Lyu, Binois & Ludkovski 2021](https://arxiv.org/abs/1807.06712); [distance-constrained Kriging learning function, CMAME 2023](https://www.sciencedirect.com/science/article/pii/S0045782523001597)
- [Dasgupta & Hsu 2008](https://dl.acm.org/doi/abs/10.1145/1390156.1390183); [Mussmann & Liang 2018](https://arxiv.org/abs/1806.06123); [Schein & Ungar 2007](https://link.springer.com/article/10.1007/s10994-007-5019-5); [Osugi, Kun & Scott 2005](https://ieeexplore.ieee.org/document/1565696/); [Hsu & Lin 2015, ALBL](https://ojs.aaai.org/index.php/AAAI/article/view/9597)
- [Vela et al. 2025, physics-informed GPC](https://arxiv.org/abs/2502.11369); [Kusne et al. 2020, CAMEO](https://www.nature.com/articles/s41467-020-19597-w); [Terayama et al. 2019](https://link.aps.org/doi/10.1103/PhysRevMaterials.3.033802); [Dai, Bruss & Glotzer 2020](https://arxiv.org/abs/1803.03296); [Fan et al. 2026, BALPI](https://pubs.rsc.org/en/content/articlelanding/2026/dd/d5dd00459d)
- [King et al. 2014, keyhole-mode LPBF](https://www.osti.gov/biblio/1502044); [LPBF sequential learning 2024/25](https://arxiv.org/html/2411.10822v1)
