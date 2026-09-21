# Track A result provenance

| Result/status | Source code | Outputs/report | Protocol/provenance | Git provenance |
|---|---|---|---|---|
| M3 predictive model | `src/week9_phase1_11_fixed_mean_discrepancy_gp.py`; `src/week9_phase1_13_fixed_physics_ard_discrepancy.py` | `outputs/week9_phase1_13_fixed_physics_ard_discrepancy/` | `kernel_specification.json`, validation and run manifest in that directory | historical branch tip `fbe76352f86580818659ab87fa23ec29a74c7f59`; preserved on old main `5b7d030413ed2aa24e6e4c8f124dd5145f735618` |
| Live M3-margin control | `src/week9_phase1_14_m3_margin_acquisition.py` | `outputs/week9_phase1_14_m3_margin_acquisition/` | frozen protocol/input provenance in output tree | branch tip `5a7a6c05ae5bf3191b74766156407211ad414360`; preserved on old main |
| Candidate A/B internal replication | `src/week9_phase1_20_acquisition_search.py`; `src/week9_phase1_20_early_start.py`; `src/week9_phase1_21_simplification_replication.py` | `outputs/week9_phase1_21_simplification_replication/FINAL_PHASE1_21_REPORT.md` | `PHASE1_21_PREREGISTERED_PROTOCOL.json`, `FINAL_POLICY_FREEZE.json`, `REPLICATION_RESULT.json`, `invariance_audit.json` | first tracked in unified content commit `8e90497864fade6b14ca500b9dcbd098a7c95a9d` |
| Locked matched-control audit | `src/week10_trackA_phase121_comparator_audit.py` | `outputs/week10_trackA_phase120_122_audit/phase121_comparator_audit/FINAL_COMPARATOR_AUDIT.md` | `AUDIT_PROTOCOL.json`, `EXECUTION_FREEZE.json`, preflight and parity evidence | local import commit `81a5bafe58f1480bd169226d9f56957fe4149ab7` |
| PG-RMBC closure | `src/week10_trackA_pg_rmbc.py` | `outputs/week10_trackA_pg_rmbc/FINAL_METHOD_REPORT.md` | `METHOD_PROTOCOL_FREEZE.md`, `run_manifest.json`, validation report | source tip `a380aeb07f6328d8365273835c09a452b4e33d8b`; ancestry merged at `b3fb6a1cc7a03777c03c209ea2a3a728c76fcd66` |
| Boundary-displacement Gate 1 closure | `src/week10_trackA_boundary_displacement_gate1.py` | `outputs/week10_trackA_boundary_displacement_gate1/FINAL_GATE1_REPORT.md` | `METHOD_PROTOCOL_FREEZE.md`, `IMPLEMENTATION_REPAIR.md`, `run_manifest.json`, validation report | local import commit `81a5bafe58f1480bd169226d9f56957fe4149ab7` |
| Phase 2 width evidence | `src/week9_phase2_temporal_width_dynamics.py`; Phase 2.1/2.2 source files | `outputs/week9_phase2_temporal_width_dynamics/`; `outputs/week9_phase2_1re_early_prefix_width_control/`; `outputs/week9_phase2_2_width_informed_active_learning/` | each output tree's protocol, run manifest, validation and claim ledger | preserved on old main; see branch provenance for `codex/week9-phase2-temporal-width-dynamics` |

## Pinned SHA-256 values

- `src/week9_phase1_11_fixed_mean_discrepancy_gp.py`: `cfbbbd4a8ddcdf88d04467b64c3908489c49265cedac1292bb77baa2cd8fc0e5`
- `src/week9_phase1_13_fixed_physics_ard_discrepancy.py`: `03928c4dbb11a1b925586443b7c9ace61e1ca0164782e3af7fa1b7401bffb0ba`
- `src/week9_phase1_20_acquisition_search.py`: `a47a4c2a872bda39da0ef1415360447d9fafb570c603cf3e6687ead5681a26b2`
- `src/week9_phase1_20_early_start.py`: `5a515d6c89d2a4c547f005fd58067d7385b2343795d136ac26b23bf8501b9a43`
- `src/week9_phase1_21_simplification_replication.py`: `b7c436e88c15cb569c4c5f8cf2f26f3c2742f436da403c8c4b6fce85386d19c9`
- `outputs/week9_phase1_21_simplification_replication/FINAL_POLICY_FREEZE.json`: `84be2a270aaba453321c4a20a1603ec7834fb4de41afd5d48347bf78070be631`
- `outputs/week9_phase1_21_simplification_replication/PHASE1_21_PREREGISTERED_PROTOCOL.json`: `3fe51aa103213c890c4d8da593387e6cd937707147f6ae703a7c1eb2e6a9c6ae`

The repository-wide branch/file maps are in `docs/consolidation/REMOTE_BRANCH_AUDIT.csv`, `BRANCH_FILE_UNION.csv`, and `BRANCH_PROVENANCE.csv`. Two older Phase 2 manifest-hash mismatches remain documented in `outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md`; they are not silently repaired by this freeze.
