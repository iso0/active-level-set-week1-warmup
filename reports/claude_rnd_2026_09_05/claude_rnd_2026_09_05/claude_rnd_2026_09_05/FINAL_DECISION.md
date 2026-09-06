# FINAL_DECISION

## A. What is actually wrong with the current active-learning pipeline

Nothing is "wrong" with the acquisition code. Three structural facts make the pipeline insensitive to acquisition changes:

1. **The endpoint has a data-determined ceiling that the incumbent reaches by B60.** With all 324 training labels, M3's Fold-B1-q20 accuracy is 0.8565; the M3-margin curve is 0.846 at B40, 0.856 at B60, 0.861 at B80. Headroom over B41–80 is 0.0005. The historical primary endpoint (AULC 16–80) spends 62% of its weight where no policy can differ. Every published null (|Δ| ≤ 0.0045) is inside the resulting empirical bound (Prop. 4, conditional form: the 324-label ceiling bounds label-free policies late, not selected subsets — see §I′).
2. **The ceiling is 13 label-definition exception cases** (late-onset and transient keyhole episodes concentrated in the old campaigns, depth-marginal conduction cases, and all three KH of the 27-row alternative configuration). They occupy 14% of q20 slots and are unpredictable from (P, VX, LS, ST) by nine model classes, by configuration covariates, and by a censored-depth model. This is a label-provenance/observation-window fact, not an input-resolution law (Prop. 5; falsifiable on the new pool, SATURATION_PREDICTIONS P1–P2).
3. **Under M3 every uncertainty-aware acquisition is margin.** The latent scale is set by a near-unregularised logistic slope (21 per revealed-sd at B16, ≈4 later) and the residual amplitude is capped at 1, so latent variances are nearly constant and small relative to |m|; straddle, EMI, variance gates, residual corrections and p(1−p)-SUR rank as margin (ρ 0.977–0.999). M3 carries no boundary-location uncertainty an acquisition could use.

Two exact results sharpen this beyond M3 (MATHEMATICAL_DEVELOPMENT §9):

- **Prop. 1.** For a deterministic simulator the information a query carries about the pool labelling is exactly its own binary entropy: uncertainty sampling (π = ½) is the information-optimal one-step rule for *any* model with noiseless labels. BALD/joint-entropy set criteria cannot beat margin; only non-entropic losses can.
- **Prop. 2 (leverage identity).** Under any coherent posterior, the one-step reduction of the finite-pool 0-1 set risk from querying x is Σ over reference points whose Bayes decision the outcome would flip, each contributing at most min(π_x, 1−π_x). A set-directed rule can therefore prefer a less uncertain candidate only through more decision flips, and when nothing is flippable every such rule is identically zero (exact saturation). Moment-matched and Laplace-refit look-aheads violate the identity (they credit variance shrinkage without flips): 57–204 of ≈300 candidates per state violate the bound on the development posterior, which is why approximate SURs change paths without improving decisions.

## B. Which candidate methods were tested (old 405 cases; 100 outer runs unless stated)

Models on identical revealed labels (Phase 1.14 paths): threshold-surface probit GP T with nine prior settings; censored-depth level-set model; (label-noise-robust M3 implemented, not completed). Acquisitions, prospective: T-margin; moment-matched GlobalSUR-π (eq. 8); threshold-variance reduction TV (eq. 9); **exact coherent finite-pool 0-1 SUR (XSUR, Prop. 3, Owen's T)**; each evaluated with T and with M3 as the predictive model. Diagnostics: full-label ceilings for nine model classes ± configuration; per-point exception analysis; p-vs-π ranking on saved states; window power analysis; test-label greedy oracle bound (8 runs).

## C. Which were killed and why

| Candidate | Result (AULC 16–40, paired vs control) | Verdict |
|---|---|---|
| T model (any prior) as predictor | −0.016 … −0.045 vs M3 on the same labels; converges only by B32–48 | killed: a rigid physics step is the best early predictor |
| Censored-depth model | −0.019 in every window; ceiling 0.853 ≤ M3 | killed |
| T-SUR-π (moment-matched) | −0.026 (M3 eval), −0.036 (T eval) | killed; non-coherent look-ahead (Prop. 2c) |
| **T-XSUR (exact Bayes-optimal transductive 0-1 rule)** | **−0.028 [−0.041, −0.017] vs M3-margin; −0.025 vs T-margin** | killed — the surprising result: the one-step Bayes-optimal rule for the pool loss loses to margin by 0.03 because its "flippable" reference points (49 per early step vs 19 for the margin choice) lie in sparsely sampled contexts where the 16–40-label posterior is not calibrated; margin trusts the posterior only at the data-anchored boundary |
| T-TV evaluated with T | −0.009 [−0.019, −0.000] | killed as a T-acquisition |
| Repulsion, residual mixtures, PA-TVR, FAST-SUR, exact p(1−p) SUR, physics-refit SUR, monotone propagation | committed Phases 1.15A–1.19B | already closed |

## D. Exactly ONE final challenger

**M3 + TV**: the incumbent predictive model M3, unchanged, with queries selected by the expected threshold-variance reduction computed under a frozen auxiliary threshold-surface posterior (T with c = 7, s_u = 0.41, ℓ_s = (1.7, 30, 30), s_μ = 3, s_β = 1, μ₀ = mean revealed log h; reference set = whole outer training pool).

## E. Exact mathematical definition

Latent g(x) = c(ℓ(x) − τ(z(x))), τ ~ GP with the frozen kernel; Laplace posterior over g at all pool rows with cross-covariance C(u, x). For candidate x with t = m_x/√(1+v_x):

  A_TV(x) = φ(t)² / [Φ(t)(1−Φ(t))(1+v_x)] · Σ_{u∈𝒫} C(u,x)²,  select argmax over unrevealed rows, tie-break smallest row index.

Equivalently A_TV = E_{Y_x}[ Σ_u Var_n(τ_u) − Var_{n+1}(τ_u) ] under the probit moment update; the prediction reported is M3's.

## F. Why it is different from the failed acquisitions

Its ranking is not monotone in margin: top-5 overlap with margin 0.18 in the early window, same top-1 in 4.5% of steps, path Jaccard 0.55 at B40; it weights near-boundary candidates by their covariance leverage over the *boundary location along VX*, which no M3-internal score can express (M3's covariance is amplitude-capped and nearly constant). Unlike repulsion it does not penalise proximity to queried points; unlike SUR/XSUR it does not chase decision flips in uncalibrated regions (its local weight vanishes away from the current boundary, so it is a margin-gated leverage rule). On old data it is the only configuration with a positive early contrast against its own control (+0.0058 [+0.0002, +0.0117] vs M3 on the T-margin path) and a non-negative one against the incumbent (+0.0025 [−0.0032, +0.0080]), with higher B40 q20 KH recall (0.768 vs 0.749). This signal is prior-sensitive: with s_u = 0.2 it is +0.0041 [−0.0016, +0.0103] against its control and −0.0037 [−0.0101, +0.0028] against the incumbent (OLD_DATA_RND_REPORT §7). It is retained as the frozen challenger because it is the only tested acquisition that is neither redundant with margin nor harmful; it is not retained because development supports a gain.

## G. Expected probability that it beats its own margin control

Frozen rule (AULC 16–40, lower 95% bound > 0 and mean ≥ +0.010, KH-recall guard): **≈ 0.12** (range 0.05–0.20). Lower bound > 0 alone: ≈ 0.25. The old-pool estimate fails the rule at both prior settings; the new pool's higher expected ceiling (P1: 0.89) could enlarge the early headroom, which is the only reason the probability is not lower. I state this number rather than a more attractive one because the development evidence does not support more.

## H. Expected probability that it beats M3

The challenger *is* M3 with a different path, so "beats M3" means beating M3-margin (path A): the same ≈ 0.12. No model-side gain is claimed; development shows no model beats M3 at any budget on this benchmark.

## I. What would constitute a methodological contribution if it succeeds

An externally reproduced, blinded demonstration that a boundary-unit leverage term — which Props. 1–2 show is the *only* kind of term that can differ from margin for a deterministic simulator — improves early-window label efficiency, plus the theory that says where and why (early window; leverage along the unresolved context direction; margin-gated to stay calibrated). Together with the negative result that the exact Bayes-optimal transductive rule fails, this would be a principled account of when set-directed acquisition helps on finite pools.

## I′. The result that changes the thesis's direction (found last; not part of the frozen challenger)

A test-label greedy oracle (OLD_DATA_RND_REPORT §7) reaches q20 accuracy 0.93 by B24 with the *right* eight labels — above M3's 324-label ceiling of 0.8565 — and falls back to 0.875 when margin-selected labels are added. The near-boundary endpoint therefore has a training-set *selection sensitivity* of ≈ ±0.1, twenty times any policy contrast ever measured here, and adding labels can *lower* it. The exceptions that set the ceiling are locally clustered (late-onset keyhole of the old campaign), so a training set containing the right cluster members makes a smooth model predict them; the full training set does not, because their conduction neighbours dominate a smooth, global-amplitude likelihood. The headroom that no acquisition can reach without evaluation labels is reachable in principle by a *likelihood* that discounts locally conflicting labels (label-noise-robust or locally nonstationary discrepancy). That model-side test (M3R, implemented, not completed) is the recommended next development step, and prediction P9 (SATURATION_PREDICTIONS) tests the clustering hypothesis on the new pool without any method change.

## J. What contribution remains if it fails

The mechanism: (i) Prop. 1 — margin is exactly information-optimal for deterministic labels; (ii) Prop. 2 — an exact leverage identity characterising all coherent set-directed one-step rules, the non-coherence of moment-matched/Laplace SURs, and an exact Owen-T implementation; (iii) the empirical finding that even the exact Bayes-optimal transductive rule is beaten by margin by 0.03 AULC on a near-boundary endpoint, because expected decision flips are only as real as the posterior's calibration off the data; (iv) the ceiling/exception decomposition and the zero-headroom bound that explain the project's chain of nulls quantitatively; (v) nine falsifiable predictions for the new pool and a blinded protocol that tests them; (vi) the oracle result that the endpoint's selection sensitivity (±0.1) dwarfs policy effects and that exceptions are locally clustered, redirecting the thesis from acquisition design to robust likelihoods. If the new pool's ceiling is > 0.95 (P1 falsified), the thesis gains a stronger statement: the old saturation was campaign/label-specific, and the early-window design becomes the object of a further study.

## Recommendation on how to spend the unseen labels

Run the frozen protocol as written (A, B′, C, D; primary C − A on q20 AULC 16–40), gated by the label-free audit. Report the eight predictions first — they are informative whatever the acquisition contrast does — and the acquisition contrast second.
