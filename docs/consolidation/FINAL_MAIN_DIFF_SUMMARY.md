# Final candidate-versus-old-main diff summary

Comparison base: remote `main` at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`.

## Counts

The consolidation candidate changes **3,927 paths** relative to old `main`: **3,923 added**, **4 modified**, and **0 deleted**. By top-level location this is 3,885 under `outputs/`, 33 under `docs/`, 8 under `src/`, and `README.md`.

The four modified paths are:

- `README.md`
- `docs/PROJECT_INDEX.md`
- `docs/thesis_progress_log.md`
- `outputs/project_consolidation/validation.json`

No scientific file from old `main` is deleted.

## Branch-only work added

`codex/week10-pg-rmbc-internal-replication` contributed 1,532 branch paths absent by content from old `main`: 1,530 additions and 2 modified documentation paths, representing 1,530 absent scientific blobs. The branch tip `a380aeb07f6328d8365273835c09a452b4e33d8b` is retained as an actual ancestor through merge commit `b3fb6a1cc7a03777c03c209ea2a3a728c76fcd66`.

## Local-only work added

The original local worktree contributed **2,361** untracked scientific artifacts, all hash-verified in `LOCAL_IMPORT_MANIFEST.csv`:

- 2,035 Phase 1.20–1.22 comparator/provenance audit artifacts;
- 326 boundary-displacement Gate 1 artifacts.

These include 4 source/test files and 2,357 output/report/protocol/diagnostic/figure/checkpoint files.

## Scientific code and tests

Six current scientific/test files were added:

- PG-RMBC implementation and test;
- Phase 1.21 comparator-audit implementation and test;
- boundary-displacement Gate 1 implementation and test.

Two repository-forensics/validation tools were also added or updated. No existing scientific implementation on old `main` was overwritten.

## Documentation added or changed

- complete remote/local/file-union/provenance audits;
- definitive Track A freeze and external-validation protocol;
- canonical README, project map, result index, and archival map;
- Track B signal inventory and bounded association-screen preparation;
- validation, consistency, and test-evidence reports;
- append-only thesis progress update.

## Deliberately not imported

- virtual environments, Python/pytest caches, notebook checkpoints, and machine/runtime files;
- the test-generated public Masinelli download cache, which was moved to the local safety area after testing and is not a thesis result;
- credentials or secret-bearing files (none detected);
- raw/private/external data (none selected for import);
- any genuinely new Ioan batch (none accessed or inventoried by content).

The largest newly added Git file is below 100 MiB. Existing Git LFS policy therefore did not need to change.

## Review verdict

The diff consists of the two missing Week 10 evidence families, PG-RMBC branch history/content, the Track A/Track B freeze material, and repository-forensics/navigation records. There is no unexpected scientific deletion. The candidate is eligible for publication to `main`, followed by remote-branch deletion only after remote-main verification.
