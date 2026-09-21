# Test validation log

Date: 2026-09-21. Environment: Windows, Python 3.14.4.

## Acceptance suites

| Scope | Command | Result | Interpretation |
|---|---|---|---|
| Current Week 10 work | `python -m pytest -q src/tests/test_week10_trackA_pg_rmbc.py src/tests/test_week10_trackA_boundary_displacement_gate1.py src/tests/test_week10_trackA_phase121_comparator_audit.py` | **30 passed**, 1 warning | Current imported source, policies, diagnostics, frozen decisions, and local-only studies are executable. |
| M3 and live control core behavior | `python -m pytest -q src/tests/test_week9_phase1_13_fixed_physics_ard_discrepancy.py src/tests/test_week9_phase1_14_m3_margin_acquisition.py -k "not historical and not notebook"` | **16 passed**, 4 deselected, 1 warning | Current model/control imports, specifications, information flow, predictions, query paths, paired inference, regions, and sensitivity checks pass. |
| Prior consolidated manifest | `python -m src.tools.validate_project_consolidation` | **PASS** | 19,327 preserved files, 18,559 unique blobs, 148,839 source records, 366 Python files, 86 notebooks, and Phase 1.20 freeze references validated. |
| Complete-consolidation gate | `python -m src.tools.validate_complete_consolidation --write` | **PASS** | Branch ancestry, union/import manifests, Week 10 manifests, freeze hashes, navigation, size, deletion, and secret-name/content gates pass. |

Warnings were library deprecation warnings, not assertion failures.

## Broad historical suite

`python -m pytest -q src/tests` produced **474 passed and 36 failed**. This broad suite is not used as a false all-green claim. The failures fall into preserved historical-test assumptions:

- tests that compare the canonical consolidated repository against an old phase `STARTING_SHA` and expect no later paths;
- manifests that refer to former top-level `tests/...` paths after the lossless consolidation placed test files under `src/tests/...`;
- intentionally untracked phase checkpoints absent from Git;
- frozen historical artifact hashes already documented as legacy exceptions;
- a notebook re-execution test requiring a `python3` Jupyter kernel not installed in this runtime.

The broad run also caused test-side effects: it refreshed three old generated files and downloaded the public Masinelli cache. The three tracked files were restored byte-for-byte from the index. The cache was moved out of the worktree to the local pre-deletion safety area; it is not committed. These files are unrelated to genuinely new Ioan data.

The failures do not alter current scientific results, but they remain visible technical debt. Historical tests should eventually be split into branch-snapshot tests and canonical-tree tests; this consolidation does not rewrite their frozen assertions or regenerate old results.
