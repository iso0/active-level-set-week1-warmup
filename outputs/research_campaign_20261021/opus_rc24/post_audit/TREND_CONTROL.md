# Clean trend control on identical paid samples (DEVELOPMENT / diagnostic, 2026-10-22)

**What is compared.**
- Code: `src/rc24p_models.py`, `src/rc24p_trend.py`; units `p-match/`, 200, 0 failed.
- Paths: existing HA_LEAN + margin query paths. Data sets: RC23 std 51–58; RC23 blocks (startups 1–8); RC24 Stage A 59–66; RC24 Stage C 67–74 and blocks (startups 9–16). Stage C data are re-used here post hoc.
- **One architecture, one code path. Only the depth emulator's trend changes:**
  - TR_NONE (≡ HA_LEAN, bit-exact);
  - TR_PHYS (≡ HA_TREND, bit-exact);
  - TR_GEN3: 4 log-input coefficients, each N(0, 3²);
  - TR_GEN15: each N(0, 1.5²), so the prior variance of the trend function, averaged over the pool, equals TR_PHYS's.
- Identical in every arm: the paid set, the depth target and its quality treatment, K = 10 out-of-fold generation, the classifier, the regularisation grid, the normalisation, the budgets and the path.

**What the physics trend can and cannot add.** log h is a fixed linear combination of the log inputs, so TR_PHYS is the special case θ = c · d_h of TR_GEN. The physics trend brings no information that the inputs lack. It is a **structural constraint**: one coefficient in one fixed direction instead of four free ones.

**Matched results.** Paired over the repeats or startups of each data set; budgets 8–60, step 4.

| contrast | metric | RC23 std | Stage A std | Stage C std | RC23 blocks | Stage C blocks |
|---|---|---|---|---|---|---|
| PHYS − NONE | pooled BA, B8–B24 | +0.0069 | +0.0015 | +0.0071 | +0.0118 | +0.0117 |
| GEN15 − NONE | pooled BA, B8–B24 | +0.0065 | +0.0013 | +0.0045 | +0.0111 | +0.0088 |
| PHYS − GEN15 | pooled BA, B8–B24 | +0.0004 | +0.0002 | +0.0026 | +0.0007 | +0.0029 |
| PHYS − NONE | pooled BA, B8–B60 | +0.0010 | −0.0009 | +0.0023 | +0.0106 | +0.0102 |
| PHYS − GEN15 | pooled BA, B8–B60 | +0.0007 | −0.0006 | +0.0010 | **+0.0068** (lower bound +0.0036) | **+0.0096** (+0.0077) |
| PHYS − NONE | per-region / per-learner BA, B8–B60 | +0.0010 | −0.0008 | +0.0022 | **−0.0482** | **−0.0472** |
| PHYS − GEN15 | per-region / per-learner BA, B8–B60 | +0.0006 | −0.0007 | +0.0010 | −0.0236 | −0.0307 |
| PHYS − NONE | learner log loss, B8–B60 | +0.0066 | +0.0052 | +0.0043 | −0.0238 | −0.0235 |
| GEN15 − NONE | learner log loss, B8–B60 | +0.0082 | +0.0054 | +0.0043 | −0.0025 | +0.0021 |

For blocks the "per-region" row is the per-block BA over the two-class blocks. For std it is the per-learner (fold) BA.

**Readings.**
1. **In distribution (std) the trend matters little.** In the late window every trend effect is within ±0.002 BA. In the early window both trends help a little (+0.001 to +0.007). The physics direction adds at most +0.003 over a generic trend with matched prior variance. Every trend costs a little log loss in std (+0.004 to +0.008).
2. **Prior scale is not the issue.** TR_GEN3 and TR_GEN15 are nearly identical everywhere (differences ≤ 0.0006 BA).
3. **Under extrapolation (the five fixed regions) the two metrics disagree.**
   - Pooled BA: the physics direction specifically adds +0.007 / +0.010 over the generic trend.
   - Per-region BA: it loses −0.024 / −0.031 against the generic trend and −0.047 / −0.048 against no trend.
   - The constraint pushes predictions in an unseen region toward the h-only extrapolation. The region's majority class (by h) is predicted more often. Pooled BA rises; within-region minority detection falls.
   - h-only itself shows the extreme of this: pooled +0.016 / +0.017, per region −0.116 / −0.122.
4. **Log loss under extrapolation** improves with the physics direction (−0.024), and hardly with the generic trend.

**Conclusion (DEV).** The physics trend is a useful structural constraint for one question: class-balanced accuracy over all runs when whole regions are unseen. It is not a better within-region classifier. In distribution, a generic trend does as well.

The pre-registered final comparison (`PROTOCOL_RC24P_FINAL.md`) tests this on fresh data, with one new partition.
