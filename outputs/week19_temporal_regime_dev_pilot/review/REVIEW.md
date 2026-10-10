# Review of the Week 19 DEV pilot: classification changes, late negative, oracle check, images

**Status.** Post-hoc reporting review of the completed pilot (commit `de065db9`), written 2026-10-10. It uses the saved predictions, thresholds and oracle diagnostics only.
- **No new modelling:** no learner fit, seed, repeat, threshold tuning, relabelling or exclusion.
- **Nothing changed:** the manifest, `decision.json`, the saved predictions and every numerical output are byte-identical (`experimental_files_unchanged.csv`).
- **Verdict unchanged:** ADVANCE, exploratory DEV gate.
- **Reading the numbers:** every quantity here is an algorithmic diagnostic of the existing fits, never a deployable candidate or a physical intervention.
- **Corrections:** the wording corrections that follow from this review are listed in [REPORTING_CORRECTIONS.md](REPORTING_CORRECTIONS.md).

**Convention.** For both E1 arms the class is 1 exactly when the margin m = μ − log u ≥ 0.
- μ is the predicted *absolute* log depth (oracle file `predicted_log_depth`, which equals the learned `latent_mean` + log u; the latent mean alone is threshold-relative).
- log u is the fold's learned log-threshold.
- Between arms, Δm = (μ_A − μ_W) − (log u_A − log u_W).

All identities hold to 2e-15 (`B40_margin_identities.csv`).

## 1. Every B40 WHOLE → ACTIVE classification change

12 of 272 held-out B40 predictions change:
- 5 false positives become true negatives;
- 5 true positives are lost;
- 2 false negatives are corrected.

Full rows, with full IDs, log-scale values and all four cells: `B40_classification_changes.csv`. Δμ and −Δlog u are in log µm and sum to Δm.

| Run | Rep/fold | Label | Observed whole / A (µm) | Predicted depth W → A (µm) | Threshold u W → A (µm) | Δμ | −Δlog u | Change | Flips with |
|---|---|---:|---|---|---|---:|---:|---|---|
| H-210d3fce7d | 1/2 | 0 | 98.7 / 98.7 | 116.1 → 100.0 | 86.0 → 117.1 | -0.149 | -0.309 | FP→TN | threshold alone |
| H-ce04be44b1 | 1/2 | 0 | 87.3 / 87.3 | 120.1 → 106.9 | 86.0 → 117.1 | -0.117 | -0.309 | FP→TN | only both together |
| H-3172b413b1 | 1/3 | 0 | 90.8 / 90.8 | 108.8 → 86.5 | 91.4 → 103.0 | -0.229 | -0.120 | FP→TN | mean alone |
| H-3172b413b1 | 2/2 | 0 | 90.8 / 90.8 | 128.3 → 93.1 | 73.0 → 97.2 | -0.321 | -0.287 | FP→TN | only both together |
| H-be08daa72c | 2/2 | 0 | 107.3 / 107.3 | 100.0 → 95.1 | 73.0 → 97.2 | -0.049 | -0.287 | FP→TN | only both together |
| H-6dae2a1270 | 2/1 | 1 | 119.3 / 119.3 | 109.4 → 117.8 | 110.6 → 115.1 | +0.074 | -0.040 | FN→TP | mean alone |
| H-85317ef64f | 2/1 | 1 | 119.2 / 119.2 | 107.3 → 118.0 | 110.6 → 115.1 | +0.095 | -0.040 | FN→TP | mean alone |
| H-349225d53c | 1/2 | 1 | 88.8 / 79.0 | 129.5 → 112.0 | 86.0 → 117.1 | -0.145 | -0.309 | TP→FN | only both together |
| H-5a876064ac | 1/4 | 1 | 123.3 / 123.3 | 182.4 → 119.9 | 127.0 → 125.1 | -0.419 | +0.014 | TP→FN | mean alone |
| H-8827d7eb9a | 1/4 | 1 | 119.4 / 119.4 | 150.9 → 110.1 | 127.0 → 125.1 | -0.315 | +0.014 | TP→FN | mean alone |
| H-349225d53c | 2/5 | 1 | 88.8 / 79.0 | 125.8 → 89.0 | 116.3 → 119.1 | -0.346 | -0.024 | TP→FN | mean alone |
| H-6ca7f366ce | 2/5 | 1 | 111.3 / 111.3 | 132.2 → 116.0 | 116.3 → 119.1 | -0.130 | -0.024 | TP→FN | mean alone |

**Four-cell diagnostic** (`B40_four_cell_diagnostic.csv`). Each cell pairs one arm's saved means with one arm's saved thresholds. The two mixed cells combine a mean for one target with a threshold learned for the other, so they are algorithmic decompositions only; no hybrid is proposed or selected.

| Mean from | Threshold from | BA | TN of 24 | TP of 248 | Short-K of 20 | q20 | Changes vs WHOLE as fitted |
|---|---|---:|---:|---:|---:|---:|---:|
| WHOLE | WHOLE | 0.632 | 7 | 241 | 13 | 0.683 | 0 |
| ACTIVE | WHOLE | 0.669 | 9 | 239 | 12 | 0.717 | 8 |
| WHOLE | ACTIVE | 0.651 | 8 | 240 | 12 | 0.667 | 2 |
| ACTIVE | ACTIVE | 0.730 | 12 | 238 | 12 | 0.750 | 12 |

**What the decomposition shows.**
- **Neither change alone reproduces the gain.**
  - ACTIVE means with WHOLE thresholds: BA 0.669.
  - WHOLE means with ACTIVE thresholds: 0.651.
  - Both together: 0.730, against 0.632 for WHOLE as fitted.
  - The joint gain (+0.098) exceeds the sum of the single-change gains (+0.038 and +0.019).
- **The removed false positives.** Of the 5:
  - 1 flips with the mean change alone;
  - 1 with the threshold change alone;
  - 3 only with both.

  Four of the five lie in repeat 1 fold 2 and repeat 2 fold 2. There, WHOLE_E1's B40 threshold was low (86.0, 73.0 µm, with the logistic root outside the paid depth range), while ACTIVE_E1's was 117.1, 97.2 µm.
- **The positive changes.** Of the 7, 6 flip with the mean change alone. The ACTIVE GP predicts lower depths for several fast-scan short-K positives.
- **Correction.** The earlier sentence "the improvement comes from a different fitted response surface" is withdrawn. The gain combines a change in predicted means and a change in learned thresholds, with an interaction.

## 2. The late negative H-f4fc937e86

**Its own held-out prediction is unchanged.** It is held out in repeat 1 fold 1 and repeat 2 fold 4, and is classified identically by both arms there:
- repeat 1: no Keyhole;
- repeat 2: Keyhole.

That is not evidence about its effect on other predictions. In the folds where it is paid, its training response changes from 312.0 µm (whole) to 110.8 µm (A). Other paid responses change as well:

| Rep/fold | Late negative's paid position | Held out here | Paid runs whose response differs at B40 | u W → A (µm) | WHOLE root outside paid range | B40 changes (to correct / to wrong) |
|---|---:|---|---|---|---|---|
| 1/1 | — | yes | H-349225d53c (88.8→79.0) | 107.1 → 104.4 | no | 0 (0 / 0) |
| 1/2 | 21 | no | H-f4fc937e86 (312.0→110.8) | 86.0 → 117.1 | yes | 3 (2 / 1) |
| 1/3 | 2 | no | H-f4fc937e86 (312.0→110.8), H-349225d53c (88.8→79.0), H-6f28bdc6c9 (88.5→79.4) | 91.4 → 103.0 | no | 1 (1 / 0) |
| 1/4 | 8 | no | H-349225d53c (88.8→79.0), H-f4fc937e86 (312.0→110.8) | 127.0 → 125.1 | no | 2 (0 / 2) |
| 1/5 | 2 | no | H-f4fc937e86 (312.0→110.8), H-349225d53c (88.8→79.0), H-6f28bdc6c9 (88.5→79.4) | 115.9 → 116.5 | no | 0 (0 / 0) |
| 2/1 | 6 | no | H-f4fc937e86 (312.0→110.8), H-349225d53c (88.8→79.0) | 110.6 → 115.1 | no | 2 (2 / 0) |
| 2/2 | 2 | no | H-f4fc937e86 (312.0→110.8), H-349225d53c (88.8→79.0) | 73.0 → 97.2 | yes | 2 (2 / 0) |
| 2/3 | 8 | no | H-349225d53c (88.8→79.0), H-f4fc937e86 (312.0→110.8), H-6f28bdc6c9 (88.5→79.4), H-c698d0e5ac (312.0→297.0) | 105.0 → 107.8 | no | 0 (0 / 0) |
| 2/4 | — | yes | H-349225d53c (88.8→79.0), H-c698d0e5ac (312.0→297.0) | 109.9 → 108.7 | no | 0 (0 / 0) |
| 2/5 | 6 | no | H-f4fc937e86 (312.0→110.8), H-bba3700d20 (312.0→142.2) | 116.3 → 119.1 | no | 2 (0 / 2) |

**What can be established without an isolated refit** (`late_negative_isolation_by_checkpoint.csv`):

- **Isolated checkpoints.** In 2 checkpoints the two arms' paid training data differ *only* in the late negative's response (B16 repeat 2 fold 5; B40 repeat 1 fold 2). The fitting procedure is deterministic (fixed start, no restarts), so these differences follow from that single response:
  - B16 repeat 2 fold 5: the threshold moved 104.0 → 119.6 µm, and 3 test classifications changed (H-349225d53c TP→FN, H-6f28bdc6c9 FP→TN, H-210d3fce7d FP→TN).
  - B40 repeat 1 fold 2: the threshold moved 86.0 → 117.1 µm, and 3 test classifications changed (H-349225d53c TP→FN, H-210d3fce7d FP→TN, H-ce04be44b1 FP→TN).
- **Determinism control.** In 1 checkpoint (B16 repeat 1 fold 2) the paid data are identical in both arms. The thresholds there are identical and no classification changes.
- **Confounded checkpoints.** At every other checkpoint, other paid responses differ as well (1–5 runs among H-349225d53c, H-6f28bdc6c9, H-c698d0e5ac, H-bba3700d20, and the A-unavailable H-e7dbd8e5ce at B80). The late negative's share there cannot be separated without an isolated refit, which is not authorized here.
- **Direction.** On these label-blind paths its 312 µm response *lowers* WHOLE_E1's threshold where it is isolated. It does not pull it up as in the historical adaptive runs.

**Supported statement.** Its own held-out classification contributes no direct improvement. Its influence through training remains unresolved.

It is isolated at only 2 checkpoints. There, replacing its 312.0 µm response by 110.8 µm raised the learned threshold (by 15.6, 31.1 µm) and changed three classifications each: two false positives removed and one true positive lost.

## 3. Observed response versus GP on identical cases

**Setup.**
- **Cohort:** each arm's available-response cohort (WHOLE: 136 runs × 2 repeats; ACTIVE: 135 × 2, without the A-unavailable H-e7dbd8e5ce).
- **Threshold:** the same training threshold for both classifications.
- **Benchmark:** the benchmark itself keeps all 136 runs; nothing in `metrics.csv` changes.

At B40 the observed response and the GP disagree on 12 of 272 WHOLE and 8 of 270 ACTIVE predictions, in both directions and in both classes. The case list is in `oracle_vs_GP_discordant_B40.csv`, and the counts for all budgets are in `oracle_vs_GP_same_cohort.csv`:

| Budget | Arm | Class | Predictions | Both correct | GP right, observed wrong | GP wrong, observed right | Both wrong |
|---:|---|---|---:|---:|---:|---:|---:|
| 40 | WHOLE | positives | 248 | 236 | 5 | 3 | 4 |
| 40 | WHOLE | negatives | 24 | 5 | 2 | 2 | 15 |
| 40 | ACTIVE | positives | 248 | 236 | 2 | 1 | 9 |
| 40 | ACTIVE | negatives | 22 | 9 | 3 | 2 | 8 |

| Budget | Arm | GP (learned threshold) | Observed response, same threshold (ORACLE, NOT DEPLOYABLE) | Difference |
|---:|---|---:|---:|---:|
| 16 | ACTIVE | 0.622 | 0.672 | +0.049 |
| 16 | WHOLE | 0.558 | 0.598 | +0.040 |
| 40 | ACTIVE | 0.753 | 0.728 | -0.025 |
| 40 | WHOLE | 0.632 | 0.628 | -0.004 |
| 80 | ACTIVE | 0.705 | 0.711 | +0.006 |
| 80 | WHOLE | 0.653 | 0.711 | +0.058 |

**Interpretation.**
- **At B40 the similar BA hides cancelling errors.** For WHOLE, GP-only and observed-only correct cases nearly cancel.
- **The earlier ACTIVE comparison used different cohorts.** It compared 0.730 (136 runs) with 0.728 (135 runs). On the same 135 runs the GP gives 0.753.
- **At B16 and B80 the observed response classifies better** for WHOLE, and at B16 for ACTIVE.

**Scoped conclusion.** In this pilot, B40 aggregate BA does not separate regression error from target and threshold effects. The pilot does not show that regression is not a bottleneck.

## 4. Image package for Ioan

The package uses the 30 already-linked native images (`../ioan_gallery/`):
- **Provenance:** downloaded once at the pinned NEW revision (no local copy existed) and verified by LFS SHA-256.
- **Usability:** 22 usable, 6 nearly empty, 1 blank, 1 unclear; none missing or unreadable. 5 images are byte-identical to another image in the set.

Case notes:
- **H-f4fc937e86 (G2, the late-window maximum):** no usable image. All six of its late-frame images are blank, nearly empty, or content only at the image border.
- **H-349225d53c (G1):** at its last Keyhole frame (364) the front and side views are nearly empty, and the monitored melt depth at that frame is 0.0 µm.
- **H-b302fc6cbd (G5):** its linked frame 82 is 0.18 µs after the run's depth maximum, and after a sharp drop (114.3 µm at frame 81 → 89.1 µm at frame 82). The near-peak frame 81 is not among the 30 images.

The gallery shows no recorded labels or predictions; those are in `../ioan_gallery/KEY.md`.

## 5. Checks

All review checks pass (`REVIEW_CHECKS.csv`):
- the margin identities hold;
- each arm's four-cell corner reproduces its B40 metrics in `metrics.csv` exactly;
- the joins are one-to-one;
- the oracle labels recompute exactly;
- every experimental file is unchanged;
- the Week 18 engine was never imported;
- the 30 images are verified;
- the brief's word limit is met.
