# Active level-set estimation for SPH keyhole prediction

This repository is the authoritative Week 1–10 record for the MSc thesis project. It preserves current methods, negative experiments, historical variants, protocols, tests, reports, and reproducibility evidence on `main`.

## Current scientific state

- **Predictive model:** M3 — a physics-informed logistic trend in `log h`, with `h = P / sqrt(VX * LS^3)`, plus a four-dimensional ARD Matérn-3/2 GP discrepancy over `[P, VX, LS, ST]`.
- **Live active-learning control:** M3 probability margin with frozen B16 initialization.
- **Frozen external challenger:** `early8__coverage_then_margin_B40` (Phase 1.21 Candidate B).
- **Same-B16 attribution control:** `coverage_then_margin_B40`.
- **Historical comparator:** `historical_binary_A0_live`; it is not the live control.
- **Track A status:** frozen. Candidate B is internally replicated, remains below the predeclared `+0.01` replacement threshold, and is not externally validated.
- **Track B status:** observability/hidden-state inventory and association-screen plan only; no new-data analysis or acquisition development has been run.

Start here:

- [Five-minute project map](docs/THESIS_PROJECT_MAP.md)
- [Authoritative results index](docs/AUTHORITATIVE_RESULTS_INDEX.md)
- [Track A final state](docs/trackA_freeze/TRACK_A_FINAL_STATE.md)
- [Frozen method specification](docs/trackA_freeze/FROZEN_METHOD_SPEC.md)
- [External-validation protocol](docs/trackA_freeze/EXTERNAL_VALIDATION_PROTOCOL.md)
- [Track B problem definition](docs/trackB/TRACK_B_PROBLEM_DEFINITION.md)
- [Repository forensic audit](docs/consolidation/REPOSITORY_FORENSIC_AUDIT.md)
- [Complete phase index](docs/PROJECT_INDEX.md)

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | Models, experiment drivers, forensic tools, and tests |
| `notebooks/` | Preserved notebooks and notebook variants |
| `outputs/` | Scientific outputs, figures, reports, protocols, and run manifests |
| `docs/trackA_freeze/` | Definitive Track A method and validation freeze |
| `docs/trackB/` | Evidence-limited observability/hidden-state preparation |
| `docs/consolidation/` | Branch/file/local audits, provenance, and validation records |
| `docs/phases/` | Week/phase-specific navigation |
| `data/` | Repository-approved inputs; raw/private/new external data are excluded |

Historical alternatives with distinct content are retained under explicit experiment paths and, where needed, `_history/` or `_variants/`. A negative result is evidence, not clutter.

Two unrelated studies are both historically named “Phase 1.20”: [M3 + G3 margin](docs/phases/week9_phase1_20_m3_g3_margin_acquisition.md) and [the acquisition-search/CCM study](docs/phases/week9_phase1_20_acquisition_search.md). Their endpoints and conclusions must not be mixed.

See [known legacy issues](outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md) before interpreting preserved source-package manifest discrepancies.
