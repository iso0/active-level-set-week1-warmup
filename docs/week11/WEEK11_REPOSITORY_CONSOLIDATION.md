# Week 11 repository consolidation checkpoint

Status: **LOCAL MAIN CONSOLIDATED; HISTORICAL PRESERVATION PASS; PUBLICATION PENDING**

This record was created before changing any branch, remote ref, worktree, or stash. The machine-readable companion is `outputs/week11_repository_consolidation/PRE_CONSOLIDATION_SNAPSHOT.json`. It records the exact local and cached remote refs, ahead/behind relationships, registered worktrees and their visible status, stashes, the four Week 11 commits, and the tracked external-validation freeze hash.

## Intended canonical history

At the pre-change snapshot, local `main` and cached `origin/main` were both `5ae71520073435ff4d312c9b1bc99683c8a3eb4a`. The intended Week 11 tip was `e0adbc28b6368ee6366c6dcd7d500632c7b5f8f1`, four commits ahead of that checkpoint:

1. `30efdd6df3b0ffd4bd7ccc4fcdc60a7693c6b09d` — arrival audit.
2. `1bfb965e512e50d5d12e8ac4184a5472f307a92b` — Bug annotation audit.
3. `2f3c0ea834d1bdc5d5ddc0a014eb726f31a00d03` — pre-label design with custody gates.
4. `e0adbc28b6368ee6366c6dcd7d500632c7b5f8f1` — owner-authorized blinded seal.

The accepted ancestry audit found 53 local heads. Every local head except the Week 11 line is already an ancestor of `main`; the Week 11 line contributes exactly the four commits above. The Week 11 diff adds 248 paths: 230 under `outputs/`, 10 under `docs/`, and 8 under `src/`. No existing path is modified or deleted by this four-commit range.

The cached remote view contains three live branch heads: `main` and `codex/pre-new-data-readiness` at `5ae71520073435ff4d312c9b1bc99683c8a3eb4a`, and `codex/week11-new-data-arrival-audit` at `30efdd6df3b0ffd4bd7ccc4fcdc60a7693c6b09d`. This is a local snapshot and does not claim a fresh network fetch.

After the snapshot, local `main` was fast-forwarded to `e0adbc28b6368ee6366c6dcd7d500632c7b5f8f1`. A non-oracle preflight with the repository `.venv` passed at that commit: the freeze remained unchanged with 136 included runs, 49 withheld runs, 20 repeats by 5 folds, and minimum training size 108. Publication of the consolidated local main is a separate root-owned step.

## Preservation gate

The primary checkout was clean except for the user-owned untracked `.codex/` directory before this record was added. One historical Week 9 worktree contains untracked notebooks, outputs, source files, and a project-path note. The worktree remains untouched.

The preservation audit established that 745 of those untracked files, totalling 37,058,993 bytes, are byte-identical to the same tracked paths at the consolidated tip and its source manifest. The 504-byte `00_AKTIF_PROJE_YOLU.md` safety note was copied byte-for-byte to `outputs/_history/583da71538c8/00_AKTIF_PROJE_YOLU.md`.

Stash `583da71538c8ddc7c0bb36133e0bb953e1405ca9` contains 16 unique historical artifacts absent from the consolidated tree: one notebook and 15 Phase 1.20 output files, totalling 709,792 bytes. Their exact third-parent Git blob bytes were archived beneath `outputs/_history/583da71538c8/` at their original relative paths. `HISTORICAL_ARTIFACT_MANIFEST.json` records each original path, Git blob, SHA-256, size, destination, and the classification **ARCHIVED HISTORICAL VARIANT NOT ACTIVE**. Every archived copy was verified byte-for-byte against its source blob. The second stash has 163 absent paths but no unique content requiring another archive.

Registered worktrees whose administrative entries point to missing directories are recorded as unavailable/prunable. This record does not remove, detach, or repair any worktree. Both existing stashes are preserved.

## Frozen external-validation binding

The tracked freeze file `outputs/week11_external_prelabel_freeze_final/EXTERNAL_BATCH_FREEZE.json` has SHA-256 `856219763ec41ba22eb13ebb5c23e2137fb3d6eb884de71a44f96d80debe1eee`, matching its tracked sidecar. Its Git blob is `f99cac57a2e187c20bea89bff44ca1ef2ca6ab6e`. The freeze file was read only to verify these hashes. No frozen source or output was changed; no oracle was accessed and no model or validation execution occurred.

## Gate result

Snapshot readiness is **PASS** and historical-artifact preservation is **PASS**. Local `main` contains the complete four-commit Week 11 line. Publication and any later ref cleanup remain root-owned operations; this record does not perform them.

The forward policy is that `main` is the single canonical development branch. Future logical thesis units are committed directly to `main`. An exceptional branch requires a documented reason. Historical variants remain archived evidence and must not replace the current scientific reports.
