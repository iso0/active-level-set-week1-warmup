# RC24 synthetic test families: verdicts on the pre-registered hypotheses S1–S5

Source: `S-TEST.md`, `s-test_contrasts.csv` and `S5_corner_query_share.csv`. 640 units, 0 failed.

- Each world gives one learner per split.
- Metric: BA-AULC B8–B60, mean over 10 seeds (± standard error, number of positive seeds).
- Δ = HA_TREND − HA_LEAN unless stated otherwise.

| ID | registered rule | result | verdict |
|---|---|---|---|
| S1 | block split: Δ > 0 in ≥ 7/10 seeds, in BOTH T1 and T2 | T1 +0.025 ± 0.009 (7/10); T2 +0.015 ± 0.008 (6/10) | **NOT SUPPORTED as registered**: both means are positive, but T2 has 6/10 positive seeds |
| S2 | T3 and T4, std and block: Δ ≥ −0.010 | T3 std −0.006, block +0.016; T4 std −0.006, block +0.000 | **SUPPORTED** |
| S3 | T5, std: HONLY − HA_LEAN ≥ −0.005 | −0.0002 | **SUPPORTED** (an irrelevant auxiliary output buys nothing) |
| S4 | T6 and T7, std: \|Δ\| ≤ 0.010 | T6 −0.002; T7 +0.012 ± 0.003 (9/10) | **NOT SUPPORTED**: the anchor helped more than expected in the balanced, noisy family |
| S5 | T8: corner query share per arm (reported only) | pool share 0.051; std 0.048–0.065; block 0.054–0.079 | margin does **not** over-sample a synthetic aleatoric box that does not lie on the decision boundary |

## Readings

- **Anchor strength.**
  - Where depth is anchored on the physics coordinate (T1, T2, T3), the anchor gives positive extrapolation gains of +0.015 to +0.025.
  - It costs little when the anchor is wrong or useless: S2.
  - This replicates the direction of the real-pool Stage C result. Under the registered count rule, it is only partial support.
- **h-only in the synthetic worlds.** h-only loses heavily wherever depth carries information that h does not: T3 (−0.14), T8 (−0.07 to −0.13). In the real pool, depth is mostly explained by h. That is why h-only is so strong there.
- **The real-data corner over-sampling (45 %) is not a generic margin property.** S5 shows that a randomly-labelled box which does not straddle the model's boundary is not attracted. Proposition P4's condition (p̂ → 1/2 on the region) is essential. The real corner lies on the boundary.
- **PAC (structural) against HA_TREND** is mixed: blocks −0.018 to −0.022 in T1–T3, +0.021 in T4. The structural composite is not a uniform improvement, consistent with its closure.
