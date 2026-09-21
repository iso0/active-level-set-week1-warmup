# Validation and test log

Audit date: 2026-09-20

## Scope controls

- No expensive historical experiment was rerun.
- No notebook was opened.
- No large checkpoint archive or generated CSV was read into the supervisor context.
- No scientific result, branch or historical artifact was modified.

## Repository/provenance checks

- Enumerated local branches, remote-tracking branches and current remote heads.
- Checked `git log --all` for the first tracked appearance of Phase 1.21/1.22 files.
- Confirmed Phase 1.20 local/origin SHA equality at `49a054e3f80b8601fcb175826d54d71519f2813a`.
- Confirmed no dedicated Phase 1.21/1.22 branch exists in current refs; both first appear in `8e90497864fade6b14ca500b9dcbd098a7c95a9d` and are now on `main` at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`.
- Read consolidation provenance for Phase 1.21/1.22 from `outputs/project_consolidation/source_manifest.json.gz`.

## Phase 1.20 executed checks

- Re-executed the five focused selector-boundary, hidden-label rejection, metric and repeat-bootstrap tests: **5/5 passed**.
- Verified all 41 `run_manifest.json` raw-file SHA-256 entries against committed blob bytes: **41/41 matched**.
- Parsed and independently recomputed the two audited q20 balanced-accuracy contrasts from stored compact metric artifacts; means, intervals and positive-repeat counts matched `paired_contrasts.csv`.
- Rechecked stored candidate-selection records: 1,769,600 candidate rows across 6,400 decisions; each selected row matched the frozen minimum-margin rule and stored P2 path.
- Rechecked split sizes, B16 identity, path eligibility/uniqueness and P1/P2 path divergence.

Result: protocol/integrity checks passed; numerical optimization diagnostics remain a disclosed caveat.

## Phase 1.21 executed checks

- Parsed `PHASE1_21_PREREGISTERED_PROTOCOL.json`, `REPLICATION_RESULT.json`, `FINAL_POLICY_FREEZE.json` and `invariance_audit.json` successfully.
- Recomputed SHA-256 for the five source files pinned in `FINAL_POLICY_FREEZE.json`: **5/5 matched**.
- Cross-checked preregistration time against the first replication checkpoint time.
- Cross-checked primary/secondary endpoint definitions, repeat-block counts, exact effects, intervals, positive-repeat counts, multiplicity and frozen policy roles.

Not rerun: the 300-run replication. Existing checkpoint/results were audited instead.

## Phase 1.21 Week 10 comparator addendum

- Froze `phase121_comparator_audit/AUDIT_PROTOCOL.json` before the two missing controls were run.
- Added and ran 10 focused tests for protocol hash, authoritative A0 provenance, deterministic bootstrap, AULC normalization, Holm correction, exact two-test primary family, q30-secondary endpoints, fail-closed checkpoint sidecars, metric identity/subset sizes and Week 8.5 canonical-protocol equivalence: **10/10 passed**.
- Validated all stored Phase 1.21 arms: **900/900 checkpoints passed** path, split, metric and schema gates and were hash-bound into `EXECUTION_FREEZE.json`.
- Recreated the historical Week 8.5 Binary-GPC margin implementation and obtained **100/100 exact full-path matches** against the authoritative checkpoint bundle.
- The Windows checkout's historical protocol file had CRLF serialization while its frozen implementation requires LF canonical bytes. Parsed JSON canonicalized to the exact recorded SHA-256 and was semantically identical; the original historical file was not modified. The audit-local canonical copy and both source hashes were frozen.
- Reproduced stored M3-margin path and metrics exactly on three Phase 1.21 runs under single-thread BLAS: **3/3 passed**.
- Executed a live hidden-label counterfactual on three separated runs. Flipping every unrevealed label changed neither the next selected row nor any candidate probability for M3-margin or Binary-A0: **3/3 passed, maximum probability change 0**.
- Ran `early8__margin`: **300/300 new outer runs**, zero checkpoint reuse, 2,313 seconds.
- Ran `historical_binary_A0_live` and evaluated every B16–B80 prefix with M3: **300/300 new outer runs**, zero checkpoint reuse, 3,714 seconds.
- Validated **600/600 checkpoint/sidecar pairs**, 80 unique training-pool queries per run, no test queries, 65 budgets and exact full81/q30/q20 row counts of 81/25/17.
- Recomputed paired repeat-block AULCs, 20,000-draw intervals and 100,000-draw sign-flip tests. Five folds were averaged inside each of 60 repeats; Holm correction was applied only to the two locked new primary tests.
- Checked path divergence: both new primary treatment/control pairs had different query sequences in **300/300** runs after their shared starting rule; Candidate A and historical A0 shared B16 exactly.
- Checked effect decomposition: `+0.00670802696 = +0.00476868873 + +0.00193933824`, closure error `0`.
- Independently reviewed the final comparison with GPT-5.6 Sol High: **GO_WITH_CAVEATS**. It confirmed the matched contrasts, inference, multiplicity, guardrails and incumbent/challenger decision.

Result: Phase 1.21 contains a statistically positive but small q20-accuracy acquisition signal. It does not pass the prospective `+0.01` replacement rule and is not external validation.

## Phase 1.22 executed checks

- Parsed `EXTERNAL_POOL_AUDIT.json` successfully.
- Cross-checked label-access declaration, candidate-pool overlap findings, unavailable-new-pool finding and stop-before-Step-2 state.

Not rerun: broad disk/repository/data-source discovery. The stored audit evidence and current repository provenance were reviewed.

## Final artifact checks

- All seven audit deliverables exist: **pass**.
- `audit_evidence_table.csv` parses as 42 data rows with the five expected columns: **pass**.
- `FINAL_AUDIT_REPORT.md` contains the required title and Sections 1–9 in order: **pass**.
- All new text files were scanned for trailing whitespace: **pass**.
- Git status shows only the new untracked audit directory and its dedicated comparator source/test files; no historical tracked file was modified: **pass**.
