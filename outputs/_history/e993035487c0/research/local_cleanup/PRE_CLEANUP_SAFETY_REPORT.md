# Pre-cleanup safety report

## Decision

**STOP BEFORE DELETION.** The mandatory stop conditions are active. No worktree, clone, file, cache, ref, or Git object has been removed.

## Inventory summary

- Registered worktrees: **35**
- Physically present Git checkouts/worktrees: **5**
- Prunable stale registrations: **30**
- Standalone duplicate clones found: **0**
- Selected canonical checkout: `C:\Users\ozgur\Documents\thesis`
- Measured Git-checkout/worktree usage: **8.059 GiB**
- Proven-safe physical deletion now: **0 GiB**
- Physical linked-worktree space pending explicit review/preservation: **5.973 GiB**

## KEEP list

- `C:\Users\ozgur\Documents\thesis` — **KEEP_CANONICAL**: Selected stable canonical checkout; it is dirty and must remain untouched.
- `C:\Users\ozgur\Documents\thesis-week4-chronology-restructure` — **KEEP_UNCERTAIN**: Clean and remotely reachable, but its named remote branch no longer exists and ignored pycache files remain.
- `C:\Users\ozgur\Documents\thesis-week5-first-conduction-gp` — **KEEP_UNCERTAIN**: Contains an ignored virtual environment and a locally unique 17,421,654-byte final-labels_all.csv.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark` — **KEEP_UNCERTAIN**: Contains 200 ignored checkpoint files (413,133,685 bytes).
- `C:\Users\ozgur\Documents\thesis-week9-phase1-19a-integrity-posterior-monotonicity-audit` — **KEEP_UNCERTAIN**: Latest Phase 1.19B checkout; only runtime caches were identified, but canonical consolidation has not occurred.

## Metadata-only safe list

- `C:\Users\ozgur\Documents\thesis-external-masinelli-feasibility-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week6-melt-pool-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-comprehensive-presentation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase3-new-data-model-stability` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase4-new-data-feature-effects-depth-diagnostics` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase5-5-g3-robustness-transfer` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase5-keyhole-physical-proxy-analysis` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase6-real-data-boundary-active-level-set` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-phase7-final-boundary-hybrid-benchmark` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week7-sph-v2-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week8-5-frozen-sample-efficiency-confirmation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week8-definitive-sample-efficiency-presentation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week8-final-sample-efficiency-thesis-consolidation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-10-closure-diagnostics` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-10-external-experimental-validation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-11-fixed-mean-discrepancy-gp-clean` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-12-gpc-kernel-adequacy` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-13-fixed-physics-ard-discrepancy-clean` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-14-m3-margin-acquisition` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-15a-physics-residual-signal-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-16-m3-repulsion-scale-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-17a-physics-contour-geometry-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-18a-level-set-acquisition-compatibility-audit` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-18b0-fast-gpc-sur-update-validation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-5-h-physics-confirmation` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-7-physics-ridge-residual-gp` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-8-model-path-decomposition` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-9-physics-specificity-control` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase1-close-week8` — stale metadata only; path absent.
- `C:\Users\ozgur\Documents\thesis-week9-phase2-temporal-width-dynamics` — stale metadata only; path absent.

These 30 entries have no filesystem path. `git worktree prune` would remove registry metadata only, but it has not been run because the global deletion stop is active.

## Mandatory warnings

1. Canonical `main` is dirty: `outputs/week2_acquisition_comparison/week2_slide_notes.md` is modified; five thesis files are untracked.
2. Week 5 contains a locally unique ignored 17.4 MB dataset CSV.
3. Phase 18B contains 394 MiB of ignored checkpoints.
4. The latest Phase 1.19B checkout is separate from the dirty canonical checkout.
5. `git fsck --full --no-reflogs` exits 0 but reports dangling scientific commit `27035c8` and eight dangling blobs. Do not run garbage collection or expiry.
6. Non-repository `Documents\Codex` (0.77 GiB) and `codex-temp-week8-figure-audit` montage files were observed and intentionally left outside the deletion plan.

## Required decision before cleanup

The user must decide whether to preserve the Week 5 CSV, Phase 18B checkpoints, latest Phase 1.19B checkout, and dangling commit in explicit archival locations/refs before any physical worktree removal.
