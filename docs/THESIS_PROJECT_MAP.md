# Thesis project map

## Five-minute orientation

The record now includes Week 11 intake, the frozen external attempt that stopped at a single-class B16, and a separately marked post-hoc initialization audit. `main` is the sole canonical development branch. Original scientific commits and historical artifacts remain preserved; redundant branch names were removed after ancestry/content verification.

| Period | Purpose | Canonical entry point | Status |
|---|---|---|---|
| Weeks 1–4 | Synthetic active level-set warm-up, metrics, GPC and SUR studies | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Historical foundations |
| Weeks 5–6 | First SPH audits, target construction, response modelling and feature studies | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Preserved evidence |
| Week 7 | `sph_v2`, new-data model stability, physical-proxy and boundary benchmarks | [`docs/PROJECT_INDEX.md`](PROJECT_INDEX.md) | Preserved evidence |
| Week 8 / 8.5 | Sample-efficiency benchmark and frozen confirmation | [`outputs/week8_5_frozen_confirmation/`](../outputs/week8_5_frozen_confirmation/) | Superseded as control naming; historically authoritative |
| Week 9 Phase 1 | M3 construction, controls, acquisition audits, Candidate B and closure work | [`docs/AUTHORITATIVE_RESULTS_INDEX.md`](AUTHORITATIVE_RESULTS_INDEX.md) | Source of frozen Track A |
| Week 9 Phase 2 | Width dynamics, predictive association and failed acquisition use | [`outputs/week9_phase2_1r_simple_width_change_control/`](../outputs/week9_phase2_1r_simple_width_change_control/) | Predictive proof of concept; not an acquisition success |
| Week 10 | PG-RMBC replication, comparator audit and boundary-displacement Gate 1 | [`outputs/week10_trackA_pg_rmbc/`](../outputs/week10_trackA_pg_rmbc/), [`outputs/week10_trackA_phase120_122_audit/`](../outputs/week10_trackA_phase120_122_audit/), [`outputs/week10_trackA_boundary_displacement_gate1/`](../outputs/week10_trackA_boundary_displacement_gate1/) | Track A closed/frozen |
| Week 11 | Frozen external STOP and separate startup diagnosis | [`Week 11 synthesis`](week11/WEEK11_THESIS_DECISIVE_STAGE_REPORT.md), [`confirmatory report`](../outputs/week11_external_execution_record/CONFIRMATORY_STOP_REPORT.md), [`QC`](../outputs/week11_external_execution_record/QC_VALIDATION.json) | Incomplete frozen experiment; no confirmatory effect estimate |
| Week 13 | Exploratory re-analysis and controlled synthetic study: discovery certificates, metric identities, acquisition headroom, physics-prior transfer | [`Week 13 report`](../outputs/week13_boundary_evaluation_and_mechanisms/WEEK13_RESEARCH_REPORT.md), [`THEORY.md`](../outputs/week13_boundary_evaluation_and_mechanisms/THEORY.md) | Exploratory + controlled methodological evidence; no new acquisition method, q20 unchanged |
| Week 14 | Structure-certified discovery theory, physics-as-order vs level, density-weighted evaluation, headroom identifiability; frozen held-out benchmark + OLD/NEW/Masinelli checks | [`Week 14 master report`](../outputs/week14_research_program/WEEK14_MASTER_REPORT.md), [`THEORY`](../outputs/week14_research_program/THEORY.md), [`freeze`](../outputs/week14_research_program/CONFIRMATORY_BENCHMARK_FREEZE.md) | Theory + controlled synthetic (frozen held-out) + historical/external/post-hoc real checks; partial: no universally better method |
| Week 15 | Theory correction (T_both law); oracle-headroom decomposition; frozen test of a boundary-risk look-ahead (EBR-D) and of a density-corrected boundary Dice | [`Week 15 report`](../outputs/week15_boundary_acquisition/WEEK15_REPORT.md), [`freeze`](../outputs/week15_boundary_acquisition/FREEZE.md), [`theory`](../outputs/week15_boundary_acquisition/THEORY_WEEK15.md) | Verdict NO NEW METHOD JUSTIFIED; margin remains the robust legal rule |
| Week 16 | Astra query-value theory checked exactly and confronted with our models and data: PEER (exact one-step Hamming value), headroom decomposition, decoys, joint vs marginal calibration, discovery enrichment; Laplace erratum E16-1 | [`Week 16 report`](../outputs/week16_theory_meets_data/WEEK16_REPORT.md), [`predictions`](../outputs/week16_theory_meets_data/PREDICTIONS.md), [`theory`](../outputs/week16_theory_meets_data/THEORY_WEEK16.md), [`erratum`](../outputs/week16_theory_meets_data/ERRATUM_LAPLACE.md) | Descriptive/theory; P2, P5 hold, P1, P3, P4 rejected; no method claim; Week 15 gpworld m0 = −4 numbers withdrawn |
| Week 17 | Last model-development study: Laplace audit of G3/M3, diagnosis of M3's failure (saturating C = 1e6 physics mean, capped discrepancy, level/direction shift), learned-strength physics-trend GP (LT) vs G3/M3/H, decisive held-out synthetic + real NEW/OLD AL | [`Week 17 report`](../outputs/week17_model_and_acquisition/WEEK17_REPORT.md), [`freeze`](../outputs/week17_model_and_acquisition/PREDICTIONS_AND_FREEZE.md), [`model spec`](../outputs/week17_model_and_acquisition/MODEL_SPEC.md), [`integrity`](../outputs/week17_model_and_acquisition/ERRATA_OR_INTEGRITY_AUDIT.md) | Verdict NO CHANGE JUSTIFIED; G3 + margin remains the endpoint; M3 failure mechanism diagnosed |
| Week 18+ | Independent research campaign: red-team and data audit (label = depth threshold; OLD/NEW pooling), redesigned benchmark (POOLED, transfer, digital twins, stress, queries-to-target), depth-aware learners, binary-model portfolio, theory T18-1…T18-5, Astra Round 3 integration, one frozen confirmation round | [`Week 18 report`](../outputs/week18_independent_research/REPORT.md), [`map`](../outputs/week18_independent_research/README.md), [`freeze round 1`](../outputs/week18_independent_research/FREEZE_ROUND_1.md), [`attempt ledger`](../outputs/week18_independent_research/ATTEMPT_LEDGER.md), [`theory`](../outputs/week18_independent_research/THEORY_WEEK18.md) | Verdict IMPROVEMENT ON SOME TASKS ONLY: depth GPR + straddle confirmed on full-depth (OLD-type) tasks (C1 split-confirmation, fresh twins, depth stress); untested on NEW/POOLED (no NEW depth, decision D1); G3 + margin stays the binary-label endpoint |
| Consolidation | Complete branch/local audit and canonical-tree validation | [`docs/consolidation/`](consolidation/) | Repository authority record |
| Track B | Observable-signal versus hidden-state preparation | [`docs/trackB/`](trackB/) | Inventory and preregistration planning only |

## Current decisions

1. M3 is the predictive model: a trend in `log h` plus a 4D ARD Matérn-3/2 GP discrepancy.
2. M3 probability margin with frozen B16 initialization remains the live control.
3. `early8__coverage_then_margin_B40` is the frozen external challenger. Its internally replicated q20 accuracy-AULC gain over M3 margin is approximately `+0.006708`, below the predeclared `+0.01` replacement threshold.
4. `coverage_then_margin_B40` is the same-B16 attribution companion.
5. `historical_binary_A0_live` remains a historical comparator and must not be relabelled as the current control.
6. PG-RMBC did not beat Candidate B. Boundary-displacement M1 gained only about `+0.000004` over M0 and did not beat generic M2; Gate 2 was not earned.
7. The frozen external protocol was attempted on the new 136-run included cohort and stopped at `external__r003_f04`: its feature-only B16 contained one class. No endpoint or external confirmation was produced. These included outcomes are now open; any revised method/startup work on them is post-hoc development. The original methods and freeze remain unchanged.
8. Track B is a separate observability/hidden-state question, not another acquisition-function search.

## Authority and provenance

- Exact result-to-code/report/protocol links: [`AUTHORITATIVE_RESULTS_INDEX.md`](AUTHORITATIVE_RESULTS_INDEX.md)
- Track A implementation and decision freeze: [`trackA_freeze/`](trackA_freeze/)
- Historical and duplicate-tree interpretation: [`ARCHIVAL_MAP.md`](ARCHIVAL_MAP.md)
- Branch and local-file evidence: [`consolidation/REPOSITORY_FORENSIC_AUDIT.md`](consolidation/REPOSITORY_FORENSIC_AUDIT.md)
- Source-tree consolidation manifest: [`outputs/project_consolidation/source_manifest.json.gz`](../outputs/project_consolidation/source_manifest.json.gz)
- Known preserved source-package issues: [`outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md`](../outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md)

Week 11 includes label-free intake, an incomplete authorized outcome-based execution, and a separate post-hoc audit of the original 100 starts. The 49 Bug-withheld physical outcomes were not used or summarized. See the [STOP QC summary](../outputs/week11_external_execution_record/QC_SUMMARY.md) and [canonical-main publication record](week11/WEEK11_REPOSITORY_CONSOLIDATION.md). No partial endpoint claim is made.
