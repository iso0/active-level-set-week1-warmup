# Meeting summary for Ioan: last research step before writing (2026-10-29)

**Bottom line.** C1 + margin stays the learner. A last, pre-registered attempt to combine C1 with HA_LEAN through a simple trust rule learned only from paid simulations did not pass its development rule. No fresh test was run and nothing changes in the method. The thesis can move to writing.

**Question.** C1 is strong early, but on held-out geometric regions (K5 blocks) HA_LEAN is clearly better. Can a learner exploit this using only the simulations it has opened?

## What we did

All of this is in-pool DEV evidence on the same 541 runs. No new simulations were opened.

1. **Gain area first, with the rule fixed beforehand.** On identical paid data, we measured where the two models disagree.
   - An oracle that picks the right model at every disagreement would add +0.049 BA-AULC on geometric blocks.
   - Most errors, however, are made by both models (85 % of C1's error on the blocks, 87 % on standard splits). No convex combination can fix those.
   - A label-informed diagnostic showed that +0.021 of the room is predictable from features. It uses other learners' test labels, so it is not a method.
2. **One candidate, GATE.**
   - It is p = w(x)·p_C1 + (1 − w(x))·p_HA_LEAN, with w = σ(a + c · log relative distance to the paid set).
   - (a, c) are a MAP estimate from nested, spatially blocked out-of-fold predictions of both full pipelines on the paid runs. A held-out run's label and outputs never enter its own prediction.
   - The rule falls back to pure C1 below 16 simulations.
   - Checks passed:
     - w = 1 reproduces C1 + margin exactly, and w = 0 reproduces HA_LEAN + margin exactly;
     - a shadow test changing unopened labels and outputs left everything identical.
   - Controls: a fixed 50/50 average, and the strong alternative D_on_A (HA_TREND on HA_LEAN's path).
3. **DEV model effect on recorded paths.** The rule needed at least +0.010 on the geometric blocks with a lower bound above zero, and it failed.

   | GATE − C1 | value |
   |---|---|
   | geometric blocks | +0.0045 [−0.0016, +0.0106] |
   | K5 | +0.022 |
   | K4 | −0.013 (a loss) |
   | standard splits, early | +0.0002 (kept) |
   | standard splits, late | +0.0009 |

   The fixed average did better than GATE on the blocks.

## Why it cannot work this way

On its paid runs, C1 extrapolates better than HA_LEAN in every design: blocked out-of-fold log loss favours C1 by 0.05–0.07. So the learned gate trusts C1 more the farther a point is from the data.
- In a block design the test region is never opened.
- C1's physics trend holds within and between the paid regions, but fails in some K5 regions (and holds in K4).
- The information that would say "switch to HA_LEAN here" lies only in unopened runs.

This is an information limit, consistent with the earlier finding that the bottleneck is depth at unqueried inputs. It is not a tuning problem.

## Decision and wording for the thesis

**Decision**
- C1 + margin stays the recommended in-pool learner.
- HA_LEAN + margin stays the frozen reference. It is safer only for K5-type extrapolation; on K4 it is clearly worse, and pooled over both designs there is no difference.
- GATE is not adopted for any use.

**Claims we will not make**
- external validity;
- a solution of C1's K5 weakness;
- guaranteed 0.95 keeping or safe stopping.

**Bookkeeping**
- Fresh IDs remain unused: STD 383+, K5 49+, K4 33+.
- Astra's parallel finite-pool assurance study (a fixed-model audit, recorded from its own report) did not pass its practical assurance gate.

**Files.** All under `outputs/research_campaign_20261029/opus_final_robustness/`:
- `FINAL_REPORT_FR.md` (Turkish);
- `dev/DEV_RESULT.md`;
- `gain/GAIN_AREA.json`.
