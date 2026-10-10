# Reporting corrections to the Week 19 DEV pilot (2026-10-10)

These corrections change **wording only**. They follow from the post-hoc review in [REVIEW.md](REVIEW.md), which uses no new fits.

**What is unchanged:**
- every number and the verdict (ADVANCE, exploratory);
- `pilot_manifest.json`, `decision.json` and the saved predictions;
- all tables under `tables/`.

Each corrected passage is marked *[corrected]*, *[updated]* or *[added]* in place.

## Corrections

### RC-1. Late-negative attribution

**Location:** `PILOT_REPORT.md` §1 item 7 (also `docs/thesis_progress_log.md`, 2026-10-10 entry).

**Original:** "The gain does not come from the late negative."

**Corrected:** "Its own held-out classification is unchanged in both arms, so it contributes no direct improvement; its influence through training remains unresolved." It is isolated at only two checkpoints. There, the ACTIVE arm's threshold was higher and three classifications changed.

**Basis:**
- `late_negative_fold_summary.csv`;
- `late_negative_paid_response_differences.csv`;
- `late_negative_isolation_by_checkpoint.csv`.

### RC-2. Mechanism of the specificity gain

**Location:** `PILOT_REPORT.md` §1 item 7.

**Original:** "ACTIVE_E1's five fewer false positives fall on four fast-scan negatives whose own A equals their whole-record maximum. The improvement therefore comes from a different fitted response surface."

**Corrected:** the 12 B40 changes decompose into a mean change and a threshold change, with an interaction.
- Of the five removed false positives, one flips with the mean alone, one with the threshold alone and three only with both.
- Four of those five lie in the two folds where WHOLE_E1's threshold root fell outside the paid depth range.

**Basis:**
- `B40_classification_changes.csv`;
- `B40_four_cell_diagnostic.csv`;
- `B40_fold_thresholds.csv`.

### RC-3. Oracle-response conclusion

**Location:** `PILOT_REPORT.md` §1 item 7.

**Original:** "Classifying the observed response with the same learned threshold gives the same BA as the GP prediction (0.728 vs 0.730; 0.628 vs 0.632). Regression error is not the bottleneck."

**Corrected:** on identical cases and thresholds, 12/272 (WHOLE) and 8/270 (ACTIVE) B40 classifications differ in both directions.
- "0.728 vs 0.730" compared 135 with 136 runs; on the same 135 runs the GP gives 0.753.
- At B16 and B80 the observed response classifies better for WHOLE.
- The pilot does not show that regression is not a bottleneck.

**Basis:**
- `oracle_vs_GP_same_cohort.csv`;
- `oracle_vs_GP_discordant_B40.csv`.

### RC-4. Oracle column in §4

**Location:** `PILOT_REPORT.md` §4.

**Original:** "The target matters. Predicting the response well gains nothing beyond the GP: the oracle column matches the learned column."

**Corrected:** the table does not separate response-prediction error from target and threshold effects; similar aggregate BA conceals cancelling errors. A cohort note was added under the table.

**Basis:** as RC-3.

### RC-5. H1 threshold range

**Location:** `PILOT_REPORT.md` §2.

**Original:** "…the logistic root stays near 100–130 µm."

**Corrected:** WHOLE_E1's threshold stayed between 22.5 and 130.3 µm in the 23 checkpoints with the late negative paid. Where its response is the only difference between arms, the threshold was lower with its whole-record value (86.0 vs 117.1 µm; 104.0 vs 119.6 µm).

**Basis:** `late_negative_isolation_by_checkpoint.csv`.

### RC-6. Matched-pair wording

**Location:** `IOAN_SUMMARY.md` §2 (template in `src/week19_pilot_reports.py`).

**Original:** "The matched fast-scan pair differs only in its labels."

**Corrected:** "Similar inputs and depth trajectories, opposite recorded labels; the morphology difference has not been established."

**Basis:** owner instruction; the images had not been compared when the sentence was written.

### RC-7. Case 1 image timing

**Location:** `IOAN_SUMMARY.md`, case list (note added).

**Original:** case 1's question refers to "the startup peak (115.6 µm at 0.427 ms)", with images linked at frame 82.

**Corrected (note added):** frame 82 is 0.18 µs after the maximum, after a sharp drop (114.3 → 89.1 µm between frames 81 and 82). The near-peak frame 81 is not among the linked images.

**Basis:** `../../week19_temporal_regime_audit/tables/frame_level_map.csv.gz`.

### RC-8. Image statement

**Location:** `IOAN_SUMMARY.md`, "What would help most".

**Original:** "Some late frames are tiny image files (under 1 kB) and may be nearly empty. We have not viewed any images."

**Corrected:** the images were checked for usability: 22 usable, 6 nearly empty, 1 blank and 1 unclear. The check made no morphology judgement.

**Basis:** `../ioan_gallery/image_inventory.csv`.

### RC-9. Pinned audit report (erratum only, not edited)

**Location:** `../../week19_temporal_regime_audit/REPORT.md` §0 item 6. This file is pinned at `f3206f29`, so it was left as it is.

**Original:** "The only difference is that 16 frames (about 76 µs) around the startup peak are labelled Keyhole in the positive and Conduction/Forming in the negative."

**Read as:** "Similar inputs and depth trajectories, opposite recorded labels; the morphology difference has not been established."

**Basis:** as RC-6.

## Commit messages

The commit message of `de065db9` does not contain the corrected statements. No history was rewritten.
