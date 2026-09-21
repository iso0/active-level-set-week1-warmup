# Thesis project map

## Five-minute orientation

This repository now carries the complete scientific record through the latest Week 10 Track A work. `main` is the canonical tree. Phase branches are historical provenance, not alternative authoritative repositories.

| Period | Purpose | Canonical entry point | Status |
|---|---|---|---|
| Weeks 1–4 | Synthetic active level-set warm-up, metrics, GPC and SUR studies | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Historical foundations |
| Weeks 5–6 | First SPH audits, target construction, response modelling and feature studies | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Preserved evidence |
| Week 7 | `sph_v2`, new-data model stability, physical-proxy and boundary benchmarks | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Preserved evidence |
| Week 8 / 8.5 | Sample-efficiency benchmark and frozen confirmation | [`outputs/week8_5_frozen_sample_efficiency_confirmation/`](../outputs/week8_5_frozen_sample_efficiency_confirmation/) | Superseded as control naming; historically authoritative |
| Week 9 Phase 1 | M3 construction, controls, acquisition audits, Candidate B and closure work | [`docs/AUTHORITATIVE_RESULTS_INDEX.md`](AUTHORITATIVE_RESULTS_INDEX.md) | Source of frozen Track A |
| Week 9 Phase 2 | Width dynamics, predictive association and failed acquisition use | [`outputs/week9_phase2_1r_simple_width_change_control/`](../outputs/week9_phase2_1r_simple_width_change_control/) | Predictive proof of concept; not an acquisition success |
| Week 10 | PG-RMBC replication, comparator audit and boundary-displacement Gate 1 | [`outputs/week10_trackA_pg_rmbc/`](../outputs/week10_trackA_pg_rmbc/), [`outputs/week10_trackA_phase120_122_audit/`](../outputs/week10_trackA_phase120_122_audit/), [`outputs/week10_trackA_boundary_displacement_gate1/`](../outputs/week10_trackA_boundary_displacement_gate1/) | Track A closed/frozen |
| Consolidation | Complete branch/local audit and canonical-tree validation | [`docs/consolidation/`](consolidation/) | Repository authority record |
| Track B | Observable-signal versus hidden-state preparation | [`docs/trackB/`](trackB/) | Inventory and preregistration planning only |

## Current decisions

1. M3 is the predictive model: a trend in `log h` plus a 4D ARD Matérn-3/2 GP discrepancy.
2. M3 probability margin with frozen B16 initialization remains the live control.
3. `early8__coverage_then_margin_B40` is the frozen external challenger. Its internally replicated q20 accuracy-AULC gain over M3 margin is approximately `+0.006708`, below the predeclared `+0.01` replacement threshold.
4. `coverage_then_margin_B40` is the same-B16 attribution companion.
5. `historical_binary_A0_live` remains a historical comparator and must not be relabelled as the current control.
6. PG-RMBC did not beat Candidate B. Boundary-displacement M1 gained only about `+0.000004` over M0 and did not beat generic M2; Gate 2 was not earned.
7. Internal Track A method development is closed. The next Track A event is execution of the frozen external protocol on genuinely new, eligible, label-blinded data.
8. Track B is a separate observability/hidden-state question, not another acquisition-function search.

## Authority and provenance

- Exact result-to-code/report/protocol links: [`AUTHORITATIVE_RESULTS_INDEX.md`](AUTHORITATIVE_RESULTS_INDEX.md)
- Track A implementation and decision freeze: [`trackA_freeze/`](trackA_freeze/)
- Historical and duplicate-tree interpretation: [`ARCHIVAL_MAP.md`](ARCHIVAL_MAP.md)
- Branch and local-file evidence: [`consolidation/REPOSITORY_FORENSIC_AUDIT.md`](consolidation/REPOSITORY_FORENSIC_AUDIT.md)
- Source-tree consolidation manifest: [`outputs/project_consolidation/source_manifest.json.gz`](../outputs/project_consolidation/source_manifest.json.gz)
- Known preserved source-package issues: [`outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md`](../outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md)

The repository does not contain or claim analysis of a genuinely new Ioan batch in this consolidation.
