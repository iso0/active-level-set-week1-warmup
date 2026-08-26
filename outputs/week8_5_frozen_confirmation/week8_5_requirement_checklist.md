# Week 8.5 requirement checklist

| Requirement | Status | Evidence |
|---|---|---|
| Start from authoritative Week 8 commit | PASS | Branch created from `401b51c3da96897995d2156cde92604231ba9b4a`; Phase 7 ancestor verified as `167aad945b20822de712e891e901bd3ec6d5ffc6`. |
| New branch | PASS | `codex/week8-5-frozen-sample-efficiency-confirmation`. |
| Preserve Week 6/7/8 outputs | PASS | All new artifacts are under `outputs/week8_5_frozen_confirmation/` and `notebooks/week_08_5/`; no authoritative old output modified. |
| Five-role sequential workflow | PASS | Research map, Product contract, Coding execution, Critic audit, Supervisor decision. Later roles used compact handoffs rather than repeating history. |
| Research evidence map | PASS | `agent_handoffs/01_research_evidence_map.md`. |
| Frozen preregistration before results | PASS | `agent_handoffs/02_preregistered_claim_contract.md`, `preregistered_protocol.json`, SHA-256 `bb168...b1c66`. |
| Frozen 405 population and manual ground truth | PASS | 405 rows; 73 Keyhole/332 non-Keyhole; manual `has_keyhole`; `P,VX,LS,ST`. |
| New seeds only | PASS WITH QUALIFICATION | New namespace; 20 new partitions; 3000 unique Random orders. Twelve distinct fit-key pairs collide after uint32 reduction and are documented. |
| 20 new repeats × 5 grouped folds | PASS | 100 outer runs; 324 train/81 untouched test; no group overlap. |
| Matched split/pool/warm start | PASS | Shared feature-only 16-query initial design across arms in every run. |
| 30 Random continuations per split | PASS | 3000/3000 complete and unique within run. |
| Required three methods | PASS | Random, `binary_margin`, historical `binary_uncertainty_repulsion` h=0.15. |
| No tuning/new hybrid | PASS | Only h=0.15 confirmatory repulsion; optional h sensitivity skipped. |
| Primary AULC convention 16–80 | PASS | Integer grid 16–80; trapezoid/64; accuracy orientation independently reconstructed. |
| Persistent crossing and censoring | PASS | Three-checkpoint rule; .80 primary, .75/.85 sensitivity; non-crossings remain censored. |
| Adaptive horizons | PASS | Random rho triggered uniform H=120 and H=160 extensions; no effect-size-based decision. |
| Hierarchical inference | PASS | 20 repeat blocks; five folds retained; 30 Random continuations resampled within fold; 20000 draws. |
| Information-flow constraints | PASS | Executable audit across 3200 checkpoints, split manifests, 460800 acquisition records and chooser AST; test/B1/hidden labels excluded. |
| Deterministic tests | PASS | 11/11 focused tests. |
| Smoke test | PASS | Isolated 2×2×3 fixture; excluded from final aggregation. |
| Resume/checkpoint behavior | PASS | H=80/120/160 each 3200/3200, zero failures; Coding-agent interruption resumed without rerunning completed work. |
| Full machine-readable outputs | PASS | All user-named CSV/JSON files present; `run_manifest.json` provides hashes. |
| Per-acquisition repulsion diagnostics | PASS | 28800 rows in `repulsion_mechanism_diagnostics.csv`; 14400 margin + 14400 repulsion. |
| Requested figures | PASS | Seven figures: Random uncertainty curve, curve with repulsion, censored crossings, budget-40 class/boundary result, paired repulsion endpoints, nearest-distance mechanism comparison, primary AULC contrasts. |
| Main notebook | PASS | `notebooks/week_08_5/01_frozen_sample_efficiency_confirmation.ipynb`; four code cells executed, zero stored errors. |
| Critic audit | PASS WITH QUALIFICATIONS | `agent_handoffs/04_critic_audit.md`; no result-changing bug, numerical hashes unchanged. |
| Supervisor decision and narrative | PASS | `agent_handoffs/05_supervisor_decision.md`, `final_results_narrative.md`, `claim_decisions.csv`. |
| Large-artifact portability | PASS | Oversized CSVs and restart checkpoints are preserved in `week8_5_large_machine_readable_artifacts.tar.gz` and `week8_5_checkpoint_bundle.tar.gz`; raw local copies remain available and ignored for normal Git publication. |
| Manifest/hash verification | PASS | Final `run_manifest.json` hashes the uncompressed scientific artifacts, compact bundles, Supervisor documents, figures and audit material. |
| Repository publication | NOT REQUESTED | No push, PR, or merge performed. |
