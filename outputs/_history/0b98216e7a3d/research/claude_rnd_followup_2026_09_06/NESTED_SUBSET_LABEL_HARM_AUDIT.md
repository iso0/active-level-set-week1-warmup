# NESTED_SUBSET_LABEL_HARM_AUDIT — does "more labels hurt M3" survive without the test-label oracle?

Design (label-blind; development data): 20 outer runs (one fold per repeat). Five nested sequences over each outer training pool, all starting from the shared feature-only B16 maximin design: MAXIMIN (feature-only maximin continued to 324), MARGIN (committed Phase 1.14 M3-margin path to 80, margin continued to 120, maximin fill), RANDOM (3 seeds), BAND (physical-band rows in random order, then the rest; 3 seeds), CAMPAIGN (campaign-balanced round-robin random order; 3 seeds). Sizes 16, 20, …, 120, 160, 200, 260, 324. Models: M3 and M3R(ε = 0.05, fixed hyperparameters). Metrics: q20/q30/full accuracy, BA, KH recall. Script `code/nested_subsets.py`; tables `results/nested_subsets.csv.gz`, `results/nested_summary.csv`, `results/nested_steps_*.csv`; log `results/nested_analysis.txt`.

## M3 mean q20 accuracy by training size

| n | BAND | MARGIN | MAXIMIN | RANDOM | CAMPAIGN |
|---:|---:|---:|---:|---:|---:|
| 16 | 0.815 | 0.815 | 0.815 | 0.815 | 0.815 |
| 40 | 0.845 | 0.835 | 0.821 | 0.831 | 0.819 |
| 80 | 0.859 | 0.862 | 0.838 | 0.828 | 0.837 |
| 100–120 | **0.860** | 0.850–0.859 | 0.835–0.847 | 0.833–0.835 | 0.830–0.838 |
| 160–260 | 0.855–0.858 | 0.850–0.853 | 0.841–0.853 | 0.834–0.845 | 0.830–0.844 |
| 324 (all) | 0.844 | 0.844 | 0.844 | 0.844 | 0.844 |

Full-fold accuracy: BAND 0.970 at n = 80–120 → 0.965 at 324; MARGIN 0.969 → 0.965; the other sequences rise monotonically to 0.965.

## Paired contrasts (repeat-block bootstrap, 20 blocks; "(a/b)" = blocks positive/negative)

| Sequence, model | contrast | q20 | q30 | full | q20 KH recall |
|---|---|---|---|---|---|
| BAND, M3 | n=100 − n=324 | **+0.016 [+0.004, +0.031] (5/0)** | +0.011 [+0.003, +0.021] | +0.0045 [+0.002, +0.008] (7/0) | +0.040 [+0.010, +0.078] |
| BAND, M3 | n=100 − n=200 | +0.003 [−0.002, +0.009] | +0.002 | +0.0008 | +0.009 |
| MARGIN, M3 | n=84 − n=324 | **+0.021 [+0.006, +0.035] (6/0)** | | | |
| MARGIN, M3 | n=120 − n=324 | +0.006 [0.000, +0.018] | | | |
| BAND, M3R(0.05) | n=100 − n=324 | +0.008 [0.000, +0.017] (3/0) | +0.005 | +0.003 | +0.021 |
| MAXIMIN, M3 | n=160 − n=324 | +0.009 [−0.009, +0.027] (5/3) | | | |
| RANDOM, M3 | n=120 − n=324 | −0.011 [−0.044, +0.020] | | | |
| CAMPAIGN, M3 | n=120 − n=324 | −0.014 [−0.031, +0.002] | | | |

## Findings

1. **"More labels can hurt M3" survives in a label-blind form, but with a different mechanism from the oracle's.** For sequences that exhaust the physical band first (BAND, MARGIN), the held-out metrics peak at n ≈ 80–120 and decline when the remaining ≈ 200 far-from-boundary rows are added: q20 −0.016, q30 −0.011, full-fold −0.0045, KH recall −0.04, all with intervals excluding zero and no repeat block in the opposite direction. The decline is concentrated in the last step (n = 200 → 324: rows farthest from the boundary in log h); n = 100 → 200 is neutral.
2. The effect is **not** produced by adding *locally contradictory* labels: it appears when adding far-away, unambiguous rows, and it is absent (curves rise or plateau) for sequences that interleave far rows from the start (RANDOM, CAMPAIGN, MAXIMIN). It is therefore a global-fit property of M3 — the near-unregularised Stage-1 logistic on log h and the amplitude-capped residual are pulled by many far rows — rather than local conflict.
3. The effect is **not unique to q20**: q30, full-fold accuracy and KH recall move together.
4. M3R(ε = 0.05) roughly halves the decline (+0.008 instead of +0.016 for BAND) but does not raise the peak and does not remove it.
5. Magnitude: 0.016–0.021 on q20 — one order of magnitude smaller than the oracle's +0.095 selection sensitivity, and of the same order as the ceiling-to-curve headroom discussed in the previous package.

## Verdict on the previous claim

"Adding margin-selected labels *lowers* q20 from the oracle state (0.941 → 0.875)" — **VALID WITH QUALIFICATION.** The decline after an oracle prefix is mostly regression from an evaluation-selected optimum (ORACLE_MECHANISM_AUDIT: single margin labels have mean V ≈ −0.005 with both signs); a genuine, label-blind, reproducible decline exists but is small (≈0.016 q20) and arises from far-from-boundary labels late in the sequence, not from local contradiction. The word "poison" is withdrawn; the observable statement is: **under M3, the all-label fit is not the best fit; a band-restricted training set of ≈ 100 rows is better on every held-out metric by 0.005–0.04.** Since the external acquisition study never exceeds 80 labels, this affects only the full-label prediction study (UPDATED_SATURATION_PREDICTIONS, P1 note).
