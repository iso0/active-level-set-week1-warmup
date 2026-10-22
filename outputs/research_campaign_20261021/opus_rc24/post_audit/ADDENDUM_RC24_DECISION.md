# Dated addendum (2026-10-22) to the RC24 Stage C decision

The pre-registered RC24 decision "HA_TREND + margin: CONFIRMED (DEV-confirm)" (`stage_c/STAGE_C_DECISION.json`, frozen at e82d2845) is **kept as recorded**. No threshold, region or criterion of RC24 is changed after the fact.

This addendum states what that decision did and did not establish. Every number below was recomputed independently from the exported float32 predictions (`src/rc24p_audit.py`; no unit file or RC22 metric code is used). It agrees with the RC24 tables and with the owner's independent check.

## 1. What CONFIRMED validated

The registered criterion had three parts, all on **fold-pooled** curves:

| part | result |
|---|---|
| STD (repeats 67–74): non-inferiority in both windows | HA_TREND − HA_LEAN +0.0034 (lower bound −0.0011) and +0.0007 (−0.0013) |
| spend to BA ≥ 0.95 "not MORE" | met as worded |
| BLOCK pooled BA-AULC B8–B60 | +0.0112, lower bound +0.0080, 8/8 startups |

## 2. What it did NOT validate

### 2.1 Geometry

The Stage C "block seeds 9–16" were **new startups on the same five k-means regions** (partition seed 2222) used in RC22 and RC23. They are not new geometry and not independent data. The RC24 wording "fresh geometry-block seeds" is withdrawn.

### 2.2 Pooled vs per-region

| BA-AULC, BLOCK | HA_LEAN | HA_TREND | h-only |
|---|---|---|---|
| pooled, B8–B60 | 0.9274 | 0.9386 | 0.9468 |
| per-region mean (4 two-class blocks), B8–B60 | **0.7225** | 0.6893 | 0.6268 |
| per-region mean, B8–B24 | 0.6687 | **0.6827** | 0.6381 |

What each evaluation answers:
- **Pooled** asks: if every region is extrapolated once and all runs are counted together, what is the class-balanced error over the whole pool? Each region's MAJORITY class dominates, because a region contributes almost only its majority class to the totals.
- **Per region** asks: inside a region the learner has never sampled, can it find BOTH classes? This is what matters when exploring a new process window for its rare regime.

They are different questions. RC24 reported only the first.

### 2.3 Where the pooled gain comes from

Additive split of the pooled B8–B60 difference HA_TREND − HA_LEAN over blocks and classes: dBA = −Σ_b (dFN_b / n₁ + dFP_b / n₀) / 2. The rows sum to +0.0112.

| block | Keyhole / conduction runs | Keyhole term | conduction term |
|---|---|---|---|
| 1 | 1 / 148 | −0.0006 | +0.0012 |
| 2 | 84 / 4 | +0.0021 | −0.0005 |
| 3 | 0 / 91 | 0 | +0.0001 |
| 4 | 101 / 17 | +0.0014 | −0.0018 |
| 5 | 11 / 84 | +0.0006 | **+0.0087** |

**78 % of the pooled gain is majority-class conduction in block 5.**

### 2.4 Per-block behaviour

AULC values are B8–B60. Hit counts are summed over the 8 startups at B60, with exact 95 % intervals. Minority counts of 1–4 runs are anecdotal: the same single run is predicted 8 times.

| block | HA_LEAN | HA_TREND | h-only |
|---|---|---|---|
| 1, minority Keyhole (1 run) | recall AULC 0.632; B60 8/8 | 0.410; B60 2/8 | 0.059; B60 0/8 |
| 2, minority conduction (4 runs) | spec AULC 0.208; B60 7/32 [0.09, 0.40] | 0.121; B60 5/32 [0.05, 0.33] | 0.020; B60 0/32 |
| 3 (one class, 91 conduction) | BA undefined; conduction recall 0.999 | 1.000 | 1.000 |
| 4, minority conduction (17 runs) | spec AULC 0.423; B60 74/136 [0.46, 0.63] | 0.352; B60 64/136 [0.38, 0.56] | 0.329; B60 56/136 |
| 5 (11 Keyhole / 84 conduction) | BA AULC 0.798 | **0.845** | 0.833 |

Paired per-block wins of HA_LEAN over HA_TREND (B8–B60, 8 startups each):
- block 1: 6/8;
- block 2: 5/8;
- block 4: 8/8 (+0.033);
- block 5: HA_TREND wins 8/8 (+0.047).

**Budgets.** In B8–B24, HA_TREND is better than HA_LEAN in block 1 (0.753 vs 0.663) and block 5. The losses in blocks 1, 2 and 4 grow later.

**Hard group** (B60, evaluator-only):
- the specificity on the 12 NEW conduction runs falls from 0.260 to 0.135;
- local BA falls from 0.624 to 0.568.

### 2.5 Spend

| target | HA_TREND − HA_LEAN (pooled, STD) |
|---|---|
| BA ≥ 0.80 | equal (8/8 vs 8/8, 12.0 each) |
| BA ≥ 0.90 | −0.5 (8 both-attained, upper bound +0.12) |
| BA ≥ 0.93 | −0.75 (upper bound +1.14) |
| BA ≥ 0.95 | 7/8 vs 8/8 attainers; means 31.86 vs 31.38 among attainers; both-attained (7 pairs) +1.0, **upper bound +9.3**; held at B60 6/8 vs 8/8; lower-bound imputation +4.1 |

- RC24's "PASS" for spend meant only that a "MORE SIMULATIONS" verdict was not reached. **"Worsening not shown" is not "not worse".**
- At BA ≥ 0.95, non-inferiority of spend was NOT SHOWN.
- The value 61 assigned to a non-attaining curve is the earliest confirmation that could follow B60. It is a lower bound, not a cost.

### 2.6 Physics specificity

The RC24 control PAC_GEN changed the training scheme (structural, integrated) as well as the trend direction. The clean control (`post_audit/TREND_CONTROL.md`) holds everything fixed except the trend. Matched DEV paths:
- In the early window (B8–B24), a **generic** log-input trend gives most of the gain of the physics trend. Physics minus generic: +0.000 to +0.003.
- In the blocks over B8–B60, the physics direction adds pooled BA (+0.007 / +0.010 over generic) but **loses per-region BA** (−0.024 / −0.031). It moves the model toward h-only behaviour.

## 3. The corrected criteria applied retrospectively to Stage C (information only; not pre-registered)

Applying `src/rc24p_eval.py::decide` to the Stage C units (with the fixed blocks standing in for both partitions):
- **STD:** BA PASS / PASS; LL PASS; spend at BA ≥ 0.93 PASS; spend at BA ≥ 0.95 NOT_SHOWN.
- **BLOCK:** pooled PASS; per-region FAIL (−0.033, lower bound −0.066).
- **Rule outcome:** HA_LEAN + margin.

This is NOT a decision. The pre-registered final comparison on fresh data (`PROTOCOL_RC24P_FINAL.md`) decides.

## 4. Narrowed RC24 claims

| claim | change |
|---|---|
| C94 | "better under geometric extrapolation" → "better in the POOLED block metric on the same five regions, driven by majority-class conduction in one region; worse per region; minority detection lower in three of four two-class regions" |
| C95 | "specific to the physics direction" → withdrawn for the early window; holds only for the pooled block metric, where it trades off against per-region discrimination |
| C97 (HT_PHYS) | its block statement is narrowed in the same way (pooled only) |
| paper draft and FINAL_REPORT_RC24 | references to "dimensionless h" and to "fresh geometry" are corrected in their dated v2 versions; the originals are kept |
