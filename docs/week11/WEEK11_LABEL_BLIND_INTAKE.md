# Week 11 prepared blind intake result

`src.external_validation.intake.intake` ran unchanged on the input-only Week 11 manifest, the frozen OLD-407/OLD-405 projections, and a truthful inventory of 185 local input projections. Each inventory SHA-256 hashes the actual local projection bytes. `input_projection_source_mapping.csv` separately preserves the approved remote parameter path, its raw-byte SHA-256, repository object ID, and revision.

The result contains 185 technically usable rows, zero technical exclusion candidates, zero duplicate IDs, zero exact-input duplicates, zero OLD-407 overlap, and zero OLD-405 overlap. Units are `W`, `m/s`, `m`, and `K`.

The intake status is **BLOCKED** by exactly `INDEPENDENCE_OR_PROVENANCE_UNRESOLVED` and `ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED`. No placeholder oracle row or digest was added. `WEEK11_NEW_BATCH_MANIFEST.csv` is the canonical input manifest for review, not a final approved evaluation cohort.

The input campaign is shifted without supporting any class or outcome inference. New P spans 350.033-449.849 W versus 52.545-449.762 W historically; LS spans 40.003-49.947 micrometres versus 40.029-89.704 micrometres; ST spans 301.610-499.769 K versus 300.000-399.818 K, with 86 of 185 rows above the historical ST maximum. VX remains within the historical range. These descriptive input facts do not authorize method retuning.
