# Week 11 repository provenance audit

The source chain is: initial 407-simulation audit revision `d69dac5bda8b622bc0de316b112815c6056c06ec`; current 407-simulation revision `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8`; then the label-free OLD-405 projection from `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv`. The supporting pointers are `outputs/week7_01_sph_v2_audit/dataset_provenance.json`, `outputs/week7_05_5_g3_robustness_transfer_analysis/input_provenance.json`, the Phase 6 population construction in `src/week7_phase6_real_data_boundary_active_level_set.py` lines 321-411, and the label-free projection in `src/external_validation/reference_manifests.py`.

The new snapshot is pinned to `2e1eec9c98fd57609d2815f174586336ab59da07`, recorded by Hugging Face at `2026-09-29T18:39:05Z`. Root tree comparison reports 407 unchanged historical experiment directories plus 185 added experiment directories, giving 592. It also reports one modified `.gitattributes`, one added label CSV, no deleted root entry, and no rename. Every historical directory keeps its prior object ID; every new directory object ID is distinct from the old set and from the other new IDs.

These Git tree identities prove repository snapshot structure. Simulator version and scientific generation independence are not established by the inspected tree metadata or approved input files. No claim is made about evidence that might exist in unopened files.

All 185 current archive object IDs are distinct. The accepted historical repository inventory contains no archive rows, leaving historical archive-identity overlap unresolved. The machine evidence is in `old_root_tree.json`, `new_root_tree.json`, `root_tree_comparison.json`, and `metadata_content_identity_review.json`.
