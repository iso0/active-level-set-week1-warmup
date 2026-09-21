# Consolidation validation

## Verdict: PASS

The complete-consolidation candidate satisfies the deletion gate. The machine-readable result is [`CONSOLIDATION_VALIDATION.json`](CONSOLIDATION_VALIDATION.json), produced by [`src/tools/validate_complete_consolidation.py`](../../src/tools/validate_complete_consolidation.py).

| Gate | Evidence | Result |
|---|---|---|
| 1. Every initial remote branch audited | 38 rows in `REMOTE_BRANCH_AUDIT.csv` | PASS |
| 2. Every local scientific artifact classified | 23,419 local audit records; 2,361 local-only scientific artifacts have explicit manifest destinations | PASS |
| 3. Every unique remote branch reconciled | PG-RMBC branch imported at exact paths and ancestry merged | PASS |
| 4. Every partial branch reconciled | No `PARTIALLY_IN_MAIN` branch remained; all 38 initial tips are ancestors of the candidate | PASS |
| 5. Latest Week 10 work present | PG-RMBC, Phase 1.20–1.22 comparator audit, and boundary-displacement Gate 1 present | PASS |
| 6. Track A authoritative files present | Six files under `docs/trackA_freeze/`; pinned hashes verified | PASS |
| 7. Negative-result reports present | register plus phase reports, including PG-RMBC and boundary Gate 1 | PASS |
| 8. Phase 2 width reports present | Phase 2.1R predictive and Phase 2.2 acquisition reports present | PASS |
| 9. Current-method tests present and executable | 30/30 Week 10 and 16/16 selected M3/control tests passed | PASS |
| 10. Protocol hashes/manifests | prior 19,327-file consolidation PASS; local-import SHA-256s; Week 10 run manifests and protocol sidecars verified | PASS with two documented pre-existing Phase 2 exceptions |
| 11. No new Ioan data accessed | no new batch path was opened or summarized; freeze flag is false | PASS |
| 12. No secret/private/raw-data contamination | forbidden-name and high-confidence secret scans clean; no added file ≥100 MiB | PASS |

## Content and ancestry findings

- Old `main` already preserved every scientific blob from 36 historical phase branches through the earlier content-addressed union.
- `codex/week10-pg-rmbc-internal-replication` was the only initial remote branch with scientific blobs absent from old `main`: 1,530 blobs across 1,532 paths (1,530 added and 2 modified). Its actual commit is a parent of the consolidation history.
- The local worktree contained 2,361 untracked scientific artifacts: 2,035 Phase 1.20–1.22 comparator-audit files and 326 boundary-displacement Gate 1 files. All were imported with SHA-256 verification.
- The candidate deletes no path from old `main`.
- Every initial remote tip is reachable from the candidate history, and every remote branch has a provenance row.

## Preserved exceptions

Two pre-existing Week 9 Phase 2 frozen-manifest mismatches remain explicitly recorded in [`outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md`](../../outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md). Available Git bytes were retained; the consolidation does not pretend to repair source history.

The broad historical test suite is not wholly green: 474 passed and 36 failed for the classified legacy assumptions in [`TEST_VALIDATION_LOG.md`](TEST_VALIDATION_LOG.md). Current-method acceptance suites pass. This is not a scientific-result failure and is not concealed as an all-tests-pass claim.

No branch deletion may occur until this candidate is first published and verified on remote `main`.
