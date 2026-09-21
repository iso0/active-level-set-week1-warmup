# Repository forensic audit

## Scope and safety

This audit covers every fetched remote head, every local branch tip, the scientific file union, and the current checkout's tracked/untracked/ignored state. It compares Git blobs rather than names alone. It did not open, hash, label, or summarize any genuinely new Ioan batch; no such path was surfaced by status.

## What main already contains

`origin/main` contains 19,471 tracked files at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`. Its 2026-09-14 consolidation manifest records the prior lossless, content-addressed union. All older branch blobs found on main under relocated history/variant paths count as preserved, not missing.

## Branch findings before import

- **ACTIVE_CURRENT_WORK (2)**: `codex/week10-pg-rmbc-internal-replication`, `main`
- **FULLY_IN_MAIN (36)**: `codex/external-masinelli-feasibility-audit`, `codex/thesis-unified-project`, `codex/week5-first-conduction-gp`, `codex/week6-phase2-5-depth-closure`, `codex/week6-phase4-new-outputs-feature-effects`, `codex/week7-phase1-2-sph-v2-audit`, `codex/week7-phase3-new-data-model-stability`, `codex/week7-phase4-new-data-feature-effects-depth-diagnostics`, `codex/week7-phase5-5-g3-robustness-transfer`, `codex/week7-phase5-keyhole-physical-proxy-analysis`, `codex/week7-phase6-real-data-boundary-active-level-set`, `codex/week7-phase7-final-boundary-hybrid-benchmark`, `codex/week8-5-frozen-sample-efficiency-confirmation`, `codex/week8-final-sample-efficiency-thesis-consolidation`, `codex/week9-no-phase-controls-r-and-d`, `codex/week9-phase1-10-closure-diagnostics`, `codex/week9-phase1-10-external-experimental-validation`, `codex/week9-phase1-11-fixed-mean-discrepancy-gp`, `codex/week9-phase1-12-gpc-kernel-adequacy`, `codex/week9-phase1-13-fixed-physics-ard-discrepancy`, `codex/week9-phase1-14-m3-margin-acquisition`, `codex/week9-phase1-15a-physics-residual-signal-audit`, `codex/week9-phase1-16-m3-repulsion-scale-audit`, `codex/week9-phase1-17a-physics-contour-geometry-audit`, `codex/week9-phase1-18a-level-set-acquisition-compatibility-audit`, `codex/week9-phase1-18b-prospective-global-gpc-sur-benchmark`, `codex/week9-phase1-18b0-fast-gpc-sur-update-validation`, `codex/week9-phase1-19a-integrity-posterior-monotonicity-audit`, `codex/week9-phase1-19b-prospective-robust-monotone-pool-lse`, `codex/week9-phase1-20-m3-g3-margin-acquisition`, `codex/week9-phase1-5-h-physics-confirmation`, `codex/week9-phase1-7-physics-ridge-residual-gp`, `codex/week9-phase1-8-model-path-decomposition`, `codex/week9-phase1-9-physics-specificity-control`, `codex/week9-phase1-close-week8-sample-efficiency`, `codex/week9-phase2-temporal-width-dynamics`

Remote branches with scientific blobs absent from old main: **1**.
- `codex/week10-pg-rmbc-internal-replication`: 1530 blobs / 1532 paths; provisional `ACTIVE_CURRENT_WORK`.

## Local findings before import

Untracked scientific artifacts requiring import: **2,361**.
Local branch tips with scientific blobs absent from old main: **2**.
- `codex/thesis-complete-consolidation`: 3915 unique blobs.
- `codex/week10-pg-rmbc-internal-replication`: 1530 unique blobs.

The known local-only sets are the Phase 1.20-1.22 comparator audit and boundary-displacement Gate 1, with their code, tests, reports, manifests, diagnostics, figures, and checkpoints. Their explicit path-level destinations and SHA-256 values are in `LOCAL_VS_GITHUB_AUDIT.csv`.

## Duplicate trees and conflicts

The union contains 1,684 paths with multiple historical blob versions. Authority is not selected by timestamp: the validated main layout remains canonical when every blob is already present; post-main Week 10 work is imported; otherwise the row remains an import/manual-review gate. Historical alternatives remain in content-addressed `_history`/`_variants` locations.

## Recent experiments missing from old main

- Week 10 PG-RMBC internal replication (remote branch).
- Week 10 Phase 1.20-1.22 comparator/provenance audit (local-only tree).
- Week 10 boundary-displacement model Gate 1 and implementation repair (local-only tree).

## Deletion gate

No remote branch is deletion-eligible yet. Eligibility requires import/reconciliation, provenance rows, open-PR exclusion, a PASS validation document, publication to remote main, and a fresh blob-level comparison against remote main.
