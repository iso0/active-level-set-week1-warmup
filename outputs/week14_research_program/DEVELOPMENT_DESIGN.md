# Week 14 development design and decisions (before any confirmatory/held-out run)

All development used synthetic families and OLD (historical) facts only. NEW-136 labels were not
inspected for any Week 14 question before the freeze commit; only label-free NEW pool geometry
(front sizes 6/9 for O3) was computed.

## Study 1 — discovery

Development families: mono, mono_noise, mono_tworegime, islands, bump, slab; d ∈ {2,4,6}; pools 108/324;
prevalence 3/8/15%; designs uniform/skewed/clustered; 20 reps (smoke). Strategies were defined by
theory before running (RAND, MAXI, SCORE, FRONT, ADAPT8, HEDGE = MAXI+FRONT+SCORE).

Findings that changed the candidate set:
- Under monotone labels FRONT and SCORE discover both classes in ~2 queries on average.
- Under compact non-monotone islands, farthest-first is worse than random (periphery bias), and the
  hedge without RAND inherits that. **Decision:** add HEDGE_FR = interleave(FRONT, RAND), the
  smallest hedge with a guarantee relative to random (Prop. D5). No numeric parameter was tuned.

## Study 2 — how physics should enter the model

Development families: twoRegime (monotone, NEW-like oblique boundary), bump (Week 13 non-monotone),
stShift (monotone in O4, violates O3). Settings transfer / target40 / target80 / indomain80; 20 reps.
Candidates: H, M3, G3, GR, GRS (physics feature), MG (monotone GPC, ν ∈ {0.03, 0.1, 0.3}, O3/O4),
GRC (closure override, O3/O4).

Findings:
- Physics-mean models (H, M3) are best in-domain and worst under shift in all three families.
- **MG is rejected.** It raised minority recall but lowered majority recall and BA in several shifted
  cells (twoRegime target80 BA 0.693 vs GR 0.799). Mechanism check: the same bias appears without
  label noise (σ = 0: BA 0.842 vs 0.860) and disappears with a looser probit scale, whereas MG helps
  on a balanced monotone toy (0.911 → 0.947). Interpretation: probit virtual derivative observations
  with a small scale impose an effective *minimum slope* (strict monotonicity), which is wrong where the
  latent saturates (deep inside a regime). Recorded as a negative result; not a confirmatory candidate.
- **GRC (dominance-closure override at prediction time) was never worse than GR in BA** across the 12
  development cells (gains +0.015 to +0.038 in shifted small-sample cells, ≈0 in-domain) and strongly
  reduced ASSD; one NSD decrease (stShift transfer). O4 did not help consistently even where it is true.
  **Decision:** confirmatory candidate = closure override on the historical G3 base (G3C), order O3
  (the pre-NEW OLD-validated order), CLOSURE_P = (0.001, 0.999). G3S (physics as an extra coordinate) is
  kept as a comparator; MG and O4 are not.

## Study 3 — metrics

Development: curved 2-D/4-D boundary, densities uniform / dense-left / dense-right, noise 0 / 0.02.
- All finite-pool metrics, including q20 accuracy and BER/BEF1, are density-weighted: equal-geometry
  left/right errors swap rank with the evaluation density.
- Length^(d−1)-weighted Gabriel metrics (wBER, wBEF1) reduced the density sensitivity ~3×.
  **Decision:** confirmatory candidates wBER/wBEF1 (Gabriel, power d−1), compared against q20 accuracy,
  q20 BA, full BA, BER, BEF1 (Gabriel and kNN-5).

## Study 4 — headroom (descriptive)

Greedy oracle on evaluation-pool BA and greedy oracle on dense-truth NSD (Week 13 generator).
No method is selected from Study 4.
