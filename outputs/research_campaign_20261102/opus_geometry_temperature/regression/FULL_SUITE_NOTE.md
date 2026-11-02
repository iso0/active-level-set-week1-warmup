# GT regression tests (2026-11-02)

## 1. Registered suite: Weeks 12+ (27 files)

`src/tests`, excluding `test_week1`–`test_week11`. Log: `WEEKS12PLUS_SUITE.log`, run on the final GT tree.

**Result:** 217 passed, 2 skipped, 2 failed.

Both failures are pre-existing. They fail identically on the old base b0e9569f (`OLD_BASE_b0e9569f_two_tests.log`, a git-archive extract of `src` plus the tables these tests read):

1. **`test_week18_twin_truth_frozen.py::test_t_tobit_truth_is_the_frozen_phase2_truth`**
   - θ = [−0.22565, −1.44918, …] against the frozen [−0.251764, −1.189419, …].
   - The code is unchanged since Week 18, so this is a numerical drift, probably from library versions.
   - The frozen reference was NOT changed.
2. **`test_joint_depth_label.py::test_reports_use_full_simulation_ids`**
   - Bare H suffixes on lines 84 and 93 of `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md` (last changed in 599f1025, 2026-10-16).
   - This is unrelated to GT, and the historical ledger lines were NOT rewritten (errata only).

## 2. Full suite (59 files, including the Week 8.5–11 tests that earlier studies did not run)

Log: `FULL_SUITE_all59files.log`.

**Result:** 719 passed, 2 skipped, 40 failed: the 2 above plus 38 tests in Week 8.5 and Week 9 files.

The 38 are historical-integrity checks:
- `git diff` against Week 9 start SHAs ("historical outputs unchanged": thousands of later files);
- the old `tests/` folder layout;
- notebook re-execution and artifact hashes;
- canonical protocol JSON;
- checkpoint folders that are git-ignored.

**Independence check.** The same 38 test IDs were rerun on the IR base commit 0a57d644 (before any GT change), with the worktree temporarily switched to it and then back. All 38 fail there too, and the failing set is identical (`BASE_0a57d644_38_older_tests.log`). They are pre-existing and not caused by GT.

## 3. Side effects of running the legacy suite (disclosed)

- **Three tracked historical files were rewritten by Week 9 tests:**
  - `outputs/week9_phase1_10_external_experimental_validation/source_manifest.json` (one line);
  - `outputs/week9_phase1_8_model_path_decomposition/tables/path_audit_detail.csv` (whitespace / line endings only);
  - `outputs/week9_phase1_9_physics_specificity_control/baseline_gate.json` (whitespace / line endings only).

  They were restored with `git restore --source=HEAD` and never committed.
- **A Week 9 Phase 1.10 test downloaded three public files** of the external Masinelli 2025 dataset (pinned GitHub / Zenodo sources in `src/week9_phase1_10_external_experimental_validation.py`) into the untracked `.cache/external_masinelli/` (about 3.6 MB, 18:45 UTC).
  - They were not committed and are used by nothing in GT.
  - They can be deleted.
