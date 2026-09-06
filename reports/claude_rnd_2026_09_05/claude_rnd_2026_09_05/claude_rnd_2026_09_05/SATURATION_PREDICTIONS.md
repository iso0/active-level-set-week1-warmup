# SATURATION_PREDICTIONS — pre-declared numerical predictions for the unseen pool

These predictions are derived from the old 405 cases only and are frozen before any new label is inspected. They test the mechanism of RESEARCH_DIAGNOSIS §2–5: (i) the near-boundary endpoint has a data-determined ceiling produced by a small set of label-definition exception cases; (ii) M3-margin reaches that ceiling once ≈40% of the physical-band candidates have been queried; (iii) after that, model-uncertain candidates vanish while band candidates remain, and boundary-seeking policies coincide; (iv) the only window in which acquisition can act is the early one. Each prediction states its derivation, a numerical threshold, and the outcome that would falsify the mechanism.

Notation for the new pool: N = pool size; K folds and outer runs as fixed by NEW_POOL_FEASIBILITY_SPEC; n_b = number of physical-band rows (log h ∈ [20.3621, 21.2533], band frozen from old labels) in an outer training pool; B_q(f) = the budget at which a policy has queried a fraction f of the n_b band rows.

## P1 — Full-label ceiling of the near-boundary endpoint

Derivation. Old pool: full-label M3 q20 accuracy 0.8565 (100 folds); q20-slot error concentrated in 13 exception rows. Split by campaign: q20-slot error 0.113 within the single-campaign `new-data` partition (164 rows, 63 KH, 0 late-onset KH) versus 0.202 in `old-data-local` (8 of 9 late-onset KH) and 0.130 in `old-data-remote-clean`. Ceiling = 1 − exception-slot share.

Prediction. On the new pool, with K-fold full-label M3 (train on all other folds), the Fold-B1-q20 accuracy ceiling lies in **[0.85, 0.93]**; the point prediction for a single-campaign supervisor-labelled pool is **0.89** (the new-data partition value 1 − 0.113 = 0.887).

Falsification. Ceiling > 0.95: the exception mechanism does not transfer (labels of near-boundary cases are predictable from inputs on the new pool) — the old ceiling was a property of the old campaigns/annotation, and the early-window headroom on the new pool is larger than assumed. Ceiling < 0.83: exceptions are at least as frequent in a single-campaign pool, so the old-campaign attribution in RESEARCH_DIAGNOSIS §3 is wrong (label-definition sensitivity is generic).

## P2 — Where the exceptions are

Derivation. Old exceptions: late/transient-onset KH episodes and depth-marginal C rows; if the new pool retains per-frame label sequences and depth extraction, the same diagnostic can be run.

Prediction. Among new-pool rows misclassified by full-label M3 in ≥50% of folds, **≥ 60%** will be either (a) KH with sequence Conduction→Keyhole or with ≤ 20 KH frames, or (b) C with max depth within ±15 µm of the depth separator fitted on the new pool.

Falsification. < 40%: the exception structure is not label-definition-driven; a different mechanism (e.g. true fine-scale boundary structure) dominates.

## P3 — Saturation budget of M3-margin

Derivation. Old pool: gap to the full-label ceiling 0.0100 at B40 after 23.5 band queries (38.6% of the 60.75 band candidates available at B16), 0.0053 at B48 (≈30 band queries, 49%), 0.0000 at B60 (41 queries, 67%). Margin selects a band row in 94% of early steps.

Prediction. The M3-margin q20 curve on the new pool will be within **0.010** of the new-pool full-label ceiling at the budget where **40% (±10%)** of the band candidates have been queried, and within 0.005 at 50%. For n_b ≈ 60 this is B ≈ 40 and B ≈ 46; in general B_sat ≈ 16 + 0.4·n_b (assuming ≥ 85% of early queries land in the band, itself a prediction).

Falsification. Gap still > 0.02 at 60% band-queried: the pool is not saturated by band exhaustion; either the new pool has richer within-band structure (resolution not the limit) or the ceiling estimate is wrong.

## P4 — Collapse of model-uncertain candidates while band candidates remain

Derivation. Old pool (saved M3-margin states): candidates with 0.2 < p < 0.8 fall from 25.9 (B16) to 16.5 (B40), 1.3 (B60, 67% band queried), 0.1 (B80); band candidates remaining 60.8 → 37.3 → 20.4 → 8.3.

Prediction. Under M3-margin on the new pool, the mean number of candidates with 0.2 < p < 0.8 falls below **2** when the band-queried fraction reaches **65% (±10%)**, while at that point **≥ 25%** of the band candidates remain unqueried.

Falsification. Uncertain candidates remain > 5 at 75% band-queried: M3's posterior does not collapse on the new pool (a differently structured boundary), and the "converged model" explanation fails. Uncertain candidates < 2 already at 40%: earlier saturation; the early window is even shorter.

## P5 — Late-window equivalence of boundary-seeking policies

Derivation. Old pool: M3-margin vs M3-on-A0 q20 difference at B60–80 is +0.002 … +0.007 (both paths query the band); paths of T-margin/T-TV/M3-margin overlap 0.83–0.86 by B80. Random is excluded (binary GPC Random is still 0.02 below margin at B160 in Week 8.5).

Prediction. Any two policies that place ≥ 70% of their queries in the physical band will have mean q20 accuracy within **0.010** of each other over B60–B80 on the new pool, whatever their early-window difference.

Falsification. A late-window difference > 0.02 between two band-seeking policies: late headroom exists on the new pool, contradicting the zero-late-headroom bound, and 16–80 would have been the right primary window.

## P6 — Early-window confinement of any acquisition effect

Derivation. Old pool: all published and new acquisition contrasts against margin are confined to B16–B48 (M3+TV vs M3+T-margin: +0.0058 at 16–40, +0.0027 at 16–80 with the late part ≈ 0).

Prediction. For the frozen challenger (M3 + TV) versus M3-margin, the q20 accuracy difference averaged over B48–B80 will be within **±0.006**; the difference over B16–B40 will be at least as large in absolute value as the difference over B41–B80.

Falsification. |late difference| > 0.012 with the same sign as the early difference: the effect is not early-confined; the headroom model is wrong for the new pool.

## P7 — Ranking collapse under M3 transfers

Derivation. Under M3, straddle/EMI/variance-gate rankings correlate 0.977–0.999 with margin because the latent scale is set by the Stage-1 slope and the residual amplitude is capped.

Prediction. On new-pool M3 states at B16–B40, the Spearman correlation between M3 probability margin and M3 straddle (1.96σ−|μ|) will exceed **0.99** (median over states), and the number of candidates with 0.2 < π < 0.8 (π = Φ(m/√v)) will be ≤ 40% of the number with 0.2 < p < 0.8.

Falsification. Median ρ < 0.95: M3's latent variance is informative on the new pool; uncertainty-aware M3 acquisitions are no longer redundant there and should be re-examined.

## P8 — Full-label smooth models on the new pool

Prediction. The nine model classes of RESEARCH_DIAGNOSIS §2 will rank with M3 within the top two by full-label q20 accuracy, and the spread between M3 and a wide-bounded ARD GPC will be ≤ 0.03.

Falsification. A flexible model beats M3 by > 0.03: M3 bias exists on the new pool; the model-side conclusion ("M3 is near-optimal") is old-pool-specific.

## P9 — Selection sensitivity of the endpoint and clustering of exceptions

Derivation. Old pool: a test-label greedy oracle (queries at B16–B39 chosen with evaluation labels; diagnostic only) reaches q20 AULC 16–40 of 0.925 versus 0.830 for M3-margin (+0.095 [+0.078, +0.114], 8 runs) and 0.93 at B24, above the 324-label ceiling; the gain exists because the exception cases are locally clustered so that including the right training members flips held-out exceptions.

Prediction. On the new pool the same oracle diagnostic (run after unblinding, evaluation-only) will gain **≥ +0.05** AULC 16–40 over M3-margin if exception clusters exist (as in the old campaigns) and **≤ +0.02** if the new pool's exceptions are isolated label noise. The point prediction for a single-campaign supervisor-labelled pool is +0.03 (fewer, less clustered exceptions).

Falsification. Oracle gain > +0.08 with a full-label ceiling > 0.93: exceptions are numerous *and* clustered on the new pool, contradicting P1's premise that they are campaign-specific. Oracle gain < +0.01: the endpoint on the new pool has no selection sensitivity, and the model-side (robust-likelihood) direction of FINAL_DECISION §I′ has no headroom there.

## How the thresholds were chosen

Every numerical threshold above is either (a) the old-pool value with a margin of one to two old-pool standard errors (P1, P3, P4, P6), or (b) a value with a clear mechanistic dichotomy (P2, P5, P7, P8). The intervals were widened once for the uncertainty of transferring to a pool of unknown size; they were not touched after any new label. Thresholds are also recorded in `external_confirmation_protocol.json` under `predictions` with their SHA-256-committed text.
