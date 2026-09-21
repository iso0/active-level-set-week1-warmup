# Archival and historical-content map

## Canonical versus historical material

- The current authoritative tree is `main` after the complete-consolidation validation and merge.
- Current scientific decisions are indexed in [`AUTHORITATIVE_RESULTS_INDEX.md`](AUTHORITATIVE_RESULTS_INDEX.md).
- Phase-specific source, reports, protocols, and negative outputs remain at their original explicit paths.
- `_history/` and `_variants/` identify content-distinct historical versions. They are retained for provenance and are not interchangeable with current implementations.
- An identical hash is stored once when practical; content-distinct experiments are preserved separately even when names are similar.

## Repository-wide provenance layers

| Evidence | Location | Use |
|---|---|---|
| Consolidated source manifest | [`outputs/project_consolidation/source_manifest.json.gz`](../outputs/project_consolidation/source_manifest.json.gz) | Maps the earlier Week 1–9 source roots and content hashes into the unified tree |
| Branch audit | [`consolidation/REMOTE_BRANCH_AUDIT.csv`](consolidation/REMOTE_BRANCH_AUDIT.csv) | Records every initial remote branch tip and its relationship to old `main` |
| File union | [`consolidation/BRANCH_FILE_UNION.csv`](consolidation/BRANCH_FILE_UNION.csv) | Records scientifically relevant paths and blob identities across branch tips |
| Branch provenance | [`consolidation/BRANCH_PROVENANCE.csv`](consolidation/BRANCH_PROVENANCE.csv) | Maps branch tips and unique paths to the canonical tree before branch deletion |
| Local import manifest | [`consolidation/LOCAL_IMPORT_MANIFEST.csv`](consolidation/LOCAL_IMPORT_MANIFEST.csv) | Maps every imported untracked Week 10 artifact to its SHA-256 and repository destination |
| Local-vs-GitHub audit | [`consolidation/LOCAL_VS_GITHUB_AUDIT.csv`](consolidation/LOCAL_VS_GITHUB_AUDIT.csv) | Classifies tracked, local-branch, uncommitted, ignored, and excluded local material |
| Known legacy issues | [`outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md`](../outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md) | Preserves two source-package manifest mismatches without silently repairing history |

The pre-deletion all-ref Git bundle is held locally under `.git/consolidation_20260921/`; it is a safety copy, not a repository artifact or a substitute for canonical `main`.

## Latest Week 10 placement

- PG-RMBC source and reports: [`src/week10_trackA_pg_rmbc.py`](../src/week10_trackA_pg_rmbc.py), [`outputs/week10_trackA_pg_rmbc/`](../outputs/week10_trackA_pg_rmbc/)
- Phase 1.20–1.22/comparator audit: [`src/week10_trackA_phase121_comparator_audit.py`](../src/week10_trackA_phase121_comparator_audit.py), [`outputs/week10_trackA_phase120_122_audit/`](../outputs/week10_trackA_phase120_122_audit/)
- Boundary-displacement Gate 1: [`src/week10_trackA_boundary_displacement_gate1.py`](../src/week10_trackA_boundary_displacement_gate1.py), [`outputs/week10_trackA_boundary_displacement_gate1/`](../outputs/week10_trackA_boundary_displacement_gate1/)

Branch deletion does not erase these records: their file content, tip SHAs, merge bases, commit reachability, and canonical destinations are documented under `docs/consolidation/`, and scientifically relevant ancestry is retained from `main` where feasible.
