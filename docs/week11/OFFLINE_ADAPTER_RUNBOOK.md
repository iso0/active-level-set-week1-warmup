# Week 11 offline adapter runbook

The collection command is pinned in code to the accepted old and new revisions. It requests only root tree metadata, immediate metadata for the 185 added experiment folders, monitor-directory metadata, and each folder's approved `parameters.json`.

```powershell
.\.venv\Scripts\python.exe -m src.week11_new_data_arrival_audit collect outputs/week11_new_data_arrival_audit --workers 12
```

No label CSV, `frames.csv`, monitor content, image, archive, or model module is opened. The command stops unless the root change contains exactly 185 added folders matching the historical folder grammar, and it stops if any parameter file violates the exact approved schema.

The prepared blind intake is a separate, offline step. It uses `new185_input_manifest_candidate.csv`, the two projections under `reference_manifests/`, and `input_inventory.csv`. `prepared_intake_report.json` is intentionally blocked until the custodian supplies the missing sealed-oracle digest and resolves independence provenance. Re-running intake must preserve these unknowns; do not add a placeholder oracle entry.

It can be rebuilt without network access from the saved approved parameter projections. Use a new empty output directory and preserve the actual UTC receipt instant recorded in the checked artifact:

```powershell
.\.venv\Scripts\python.exe -m src.week11_new_data_arrival_audit build-offline outputs/week11_new_data_arrival_audit outputs/week11_offline_rebuild --received-utc 2026-09-30T07:10:16.361852Z
```

This command regenerates the canonical/candidate manifests, 185 actual local input projections, their inventory and remote-source mapping, both historical label-free projections, prepared intake report and sidecar, overlap summary, and two structural witnesses. It performs no network request.

Artifacts distinguish hash types:

- `oid` and `remote_blob_oid` are repository object identifiers.
- `raw_sha256` is calculated from the approved remote parameter bytes.
- `local_projection_sha256` hashes the actual local input-only projection bytes inventoried for intake.
- An LFS SHA-256 is recorded only when supplied explicitly; it is never inferred from `oid`.

`audit_summary.json` is the compact availability and structural-capacity summary. `root_tree_comparison.json` contains root-level change classes. `metadata_content_identity_review.json` contains archive and monitor object-identity checks. `label_blind_overlap_summary.json` and `prepared_intake_report.json` contain the input-overlap and intake results.
