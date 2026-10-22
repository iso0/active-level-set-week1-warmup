# Stacking a trend-anchored auxiliary emulator into an active classifier: a measured combination, and two evaluation pitfalls

*Draft v2 (2026-10-22). It replaces the claims of `PAPER_DRAFT.md` (v1, kept as the RC24 record) wherever they differ. Everything here is DEV evidence on one 541-run simulator pool.*

## Abstract

**Problem.** Pool-based active classification of keyhole vs conduction melting.
- Before a query, the standardised log of h = P/√(VX·LS³) is known. h itself has units W·s^{1/2}·m⁻². Its standardised logarithm z_h equals the standardised log normalised enthalpy under constant material properties.
- Each query returns the label and the simulated melt depth.

**Systems compared.** Under one paid-only contract with margin acquisition and 8–60 simulations, we compare:
- a stacked classifier fed by honest out-of-fold depth predictions (HA_LEAN);
- the same with the depth emulator's mean given a one-basis-function GP trend along z_h (HA_TREND);
- an h-only classifier;
- a control with a generic linear trend in all log inputs, with matched prior variance.

**Results on fresh random splits:**
- The trend improves early balanced accuracy (+0.009) and the pooled simulations to BA 0.93 / 0.95 (−3.3 / −6.5).
- A generic trend does almost as well. The physics direction adds +0.002, not significant.
- The trend worsens probability quality (log loss +0.007, upper bound +0.012) and the maintenance of BA ≥ 0.95.
- A pre-registered rule therefore keeps the stacked classifier without trend.

**Results under geometric extrapolation (unseen regions of the same pool):**
- The trend (and h-only, more strongly) raises the pooled class-balanced accuracy.
- Per region, the effect is partition-dependent (−0.038 / +0.031). The trend trades minority detection in some regions for majority-class accuracy in others.

**Contributions.**
- A measured combination of known components: universal kriging, stacking and uncertainty sampling.
- Two evaluation lessons for active learning on simulation pools:
  - pooled and per-region extrapolation metrics can order models oppositely;
  - "no MORE-simulations verdict" must not be read as spend non-inferiority.

## 1. What is known and what is ours

See `post_audit/ORIGINALITY_AND_LITERATURE.md`.
- **Known:** universal kriging / explicit basis functions; physics mean functions (Ziatdinov et al. 2021, for optimisation); fixed physics prior means in GPCs (Hardcastle et al. 2025); stacking; margin sampling.
- **Ours:** the placement of a one-basis physics trend in the AUXILIARY emulator inside honest stacking, and its evaluation.
- **No claim** of superiority over published methods; none was reimplemented as published.

## 2. Methods

As in `paper/EQUATIONS_AND_ALGORITHM.md`, with the clean trend family of `src/rc24p_models.py`:
- TR_NONE ≡ HA_LEAN and TR_PHYS ≡ HA_TREND, bit-exact;
- TR_GEN: four log-input coefficients, prior N(0, 1.5²) each, which matches the trend-function prior variance of TR_PHYS.

## 3. Theory, with assumptions

See `analysis/PROPOSITIONS_v2_20261022.md`.
- **Trend coefficient (exact).** Var(θ̂) = b⁴q/(1 + b²q)², with q = hᵀK⁻¹h. The coefficient is learned only if q grows. A GP residual that can absorb the h direction keeps q bounded (counterexample in the file). There is therefore no general guarantee that a wrong or absent anchor is harmless.
- **Stacking slope error.** The slope-error mechanism holds only if the stacked coefficients recover the structural ones. This is an assumption, not a result.
- **Errors-in-variables integration** leaves a single fixed configuration's 0.5 decision unchanged. That does not extend to the refitted system.

## 4. Experiments (pre-registered final comparison; `post_audit/final/`)

**Conditions.**
- Fresh random-split repeats 75–82.
- The original five k-means regions with new startups.
- A new k = 4 partition.

The tables are in `FINAL_REPORT_RC24P.md` §3 and §7: BA-AULC pooled and per learner or region, both recalls, log loss, attainment and spend for 0.80–0.95, and minority hits with exact intervals.

**Frozen decision:** HA_LEAN + margin. HA_TREND's log-loss non-inferiority is not shown.

## 5. Limits

- One pool; no external validation.
- The fixed blocks were re-used.
- Minorities of 1–4 runs.
- The hard fast-scan region is unresolved. Its timing statement is corrected in `post_audit/TIMING_CORRECTION.md`.
- Synthetic test blocks were chosen with at least 15 runs of each class, so they do not represent the real heavy-minority blocks.
