# Week 11 label-blind arrival adapter

## Scope

The adapter compares pinned Hugging Face tree metadata and validates only an explicitly approved input file: `<experiment>/parameters.json`. It does not read label ledgers, `frames.csv`, monitor values, images, archives, physical annotations, or model code.

## Source-grounded input contract

`src/week7_sph_v2_common.py` lines 64-123 define the folder grammar `P,VX,LS,ST,M,XI,XF,XL,TE,DT,H` with `p` decoded as a decimal point. Folder tokens are identifiers and provenance fields; they are not silently treated as the exact feature values.

`src/week7_phase1_sph_v2_dataset_shift_audit.py` lines 215-279 reads four `parameters.json` entries: `laser_power`, `scan_speed_x`, `laser_spot_size`, and `substrate_temperature`. Each has `value` and `unit`; the canonical units are `W`, `m/s`, `m`, and `K`. The Week 11 validator requires exactly this schema, finite numeric values, and those units. A folder/JSON disagreement above the historical absolute tolerance of `1e-14` is reported and is never converted into an invented exclusion.

One pinned new simulation file was inspected after approval. It had exactly the four documented keys, exactly `value` and `unit` inside each, size 298 bytes, and SHA-256 `7306b26c41e2a036965a36a0881dd52cffa869f44702c9e16618507acd54adf5`.

## Hash semantics

The Hugging Face tree field `oid` is retained as `oid`; it is not called SHA-256. A downloaded approved parameter file receives a locally calculated SHA-256. An LFS SHA-256 is recorded only when the remote API explicitly supplies one. Missing or incomparable identities produce `unknown_content_change`, not an equality claim.

## Blockers

`frames.csv` contains a `label` column according to the historical source and is blocked. The root label ledger mixes input, Bug/status, timestep, and physical outcome columns and is blocked. No independent Bug/status file was found in the inspected source or accepted metadata. Therefore Bug eligibility, Bug counts, onset, and reasons remain unknown pending a separate custodian export. No row is excluded on that basis.

The B80 helper checks only a proposed label-free exact-configuration fold certificate and training capacity. Its output is advisory and cannot establish final Bug eligibility or modify the frozen evaluation.

## Pinned collection result

At `2e1eec9c98fd57609d2815f174586336ab59da07`, all 185 added experiment directories supplied one approved `parameters.json`; all 185 passed the strict schema, finiteness, unit, and folder-agreement checks. They contain 185 distinct exact input tuples, with no simulation-ID or exact-input overlap against OLD-407 (and therefore none against its OLD-405 subset).

The frozen `src.external_validation.intake.intake` function was executed unchanged. It accepted all 185 input rows with zero technical exclusions and reproduced zero OLD-407/OLD-405 overlap. Its result is **BLOCKED** by `INDEPENDENCE_OR_PROVENANCE_UNRESOLVED` and `ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED`. The inventory contains hashes of the 185 actual local input projection files. It contains no invented oracle row or digest.

The label-free exact-configuration capacity witness has 37 held-out groups and 148 training groups in each of five folds, so B80 is structurally feasible for this advisory construction. This does not approve a split or establish eligibility after Bug review.

All 185 folders expose the same six immediate path types and the same 34 monitor filenames in repository metadata. Monitor contents were not opened. Six monitor object identities recur across 179 simulations (`time.dat`, `dt.dat`, `iter.dat`, the gas and substrate minimum-heat-capacity files, and gas particle count). These are file-level metadata matches only; they do not establish duplicate simulations or justify exclusion.

All 185 current archive object identities are distinct. The accepted historical repository inventory contains no `original_data_archive.tar.gz` rows, so archive identity overlap with the historical 407 is unresolved. Zero observed matches cannot be interpreted as archive non-overlap.
