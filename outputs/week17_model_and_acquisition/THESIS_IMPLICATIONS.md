# Week 17 — implications for the thesis

## What the thesis can now state firmly
1. **Why M3 failed (mechanism, with evidence).** The historical M3 couples a near-unregularized physics
   logistic (C = 1e6) — which separates the early revealed labels and saturates (|m| up to ≈ 50) — with a
   discrepancy GP whose amplitude is capped at sd 1. The cap binds in essentially every fit, so labels that
   contradict the physics prior cannot move the boundary; under a logistic likelihood they are absorbed as
   label noise. Between campaigns the physics *level* moved (log-h threshold 20.69 → 20.82) and the physics
   *direction* weakened (NEW is VX-dominated). On the held-out worlds this structure costs 0.10–0.16 NSD AULC
   whenever physics is not exactly right.
2. **Regularizing the physics mean alone is not the fix.** C = 1 repairs calibration (log loss 0.69 → 0.25 at
   small NEW budgets) but lowers BA/rare recall; "regularize and uncap" recovers most of M3's loss but stays
   below G3 (held-out −0.022; NEW CV BA 0.651 vs 0.693).
3. **A principled learned-strength physics trend (LT) is useful but not robust.** It improves boundary
   recovery when physics is right or under strong imbalance (+0.03 to +0.05 NSD AULC) and gives the best
   calibrated latent-sign probabilities, but loses up to 0.046 under localized label noise and up to 0.02 when
   physics is useless or misleading; ML-II does not reliably switch an unhelpful trend off at these budgets.
   G3 remains the established generic model; LT is a defensible *option when the physics direction is
   trusted*, not a replacement.
4. **A better model does not unlock model-aware acquisition.** On held-out worlds and OLD, coherent one-step
   EER/SUR (PEER) loses to margin under every model (−0.03 to −0.15), and most under the better model. Its value function is
   uninformative about true value (ρ ≈ 0), and it chases far-field epistemic uncertainty. Margin captures
   9–17% of the truth-oracle's one-step headroom; the remainder is not visible in any model's posterior.
5. **Candidate-B-like coverage ≈ margin** in every model on held-out worlds and on OLD (exact historical
   selector). On NEW, Candidate B, PEER *and random* all beat margin by 0.01–0.03 BA AULC under G3/LT —
   an exploration effect in a discovery-limited pool (≈ 9 rare points in one VX pocket), not a better
   acquisition formula. The thesis should present margin as the control and NEW's exploration effect as a
   documented, post-hoc caveat about rare-pocket discovery.
6. **Numerical integrity.** Historical M3 fits were often not at the Laplace mode (C = 1e6 saturation stalls
   the undamped Newton); a safeguarded refit changes no historical conclusion (≤ 0.0025 q20/BA).

## Suggested chapter placement
- Methods: one paragraph on Laplace mode finding (safeguarded Newton) and an appendix table (Phase 0).
- Models chapter: M3's failure mechanism (saturation, capped discrepancy, level/direction shift) with the
  override and transfer-decomposition figures; LT as the principled alternative and its held-out profile.
- Acquisition chapter: margin as the endpoint; the oracle headroom decomposition across models; why coherent
  one-step EER/SUR fails here (volume objective vs boundary target; ρ ≈ 0).
- Discussion: the bottleneck is information the posterior does not contain (truth knowledge), not the
  acquisition formula and not M3's numerics.

## Stop doing
- Further acquisition-formula search (Weeks 9, 15–17 all point the same way).
- Tuning physics-mean regularization or residual caps of M3.
- Re-running historical analyses for the Laplace convergence issue (no conclusion depends on it).

## One possible final follow-up (optional)
A frozen, small study of LT with a nested multi-start ML-II (one start at the G3 optimum) — the only
diagnosed, fixable LT weakness — on the same held-out worlds. It could at most turn LT into a robust
"never worse than G3" option; it would not change the acquisition conclusion.
