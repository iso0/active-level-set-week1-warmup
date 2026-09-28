# New Ioan batch arrival runbook

This runbook has one hard boundary: **Steps 1-6 are label-blind. The sealed oracle must not be opened until Step 7.** Use a custodian who is not performing method-side intake to prepare the inventory and sealed oracle.

## Step 1 — quarantine the delivery

Place the received files in a new read-only quarantine directory outside ordinary analysis paths. Preserve the original filenames and delivery metadata. Do not browse, preview, index or recursively hash the sealed oracle or raw payload from the method-side account.

## Step 2 — obtain four explicit label-free inputs

First export the canonical historical references without invoking historical loaders:

```powershell
.\.venv\Scripts\python.exe -m src.external_validation.cli export-references `
  --output-directory <label_free_reference_directory>
```

Ask the custodian for:

1. `external_manifest.csv` with exactly `sim_id,config_token,group_token,P,VX,LS,ST`;
2. `delivery_inventory.csv` with exactly `file_name,sim_id,kind,byte_size,sha256,status`;
3. a label-free OLD-407 reference manifest in the external-manifest schema;
4. a label-free OLD-405 reference manifest in the same schema.

The inventory may contain the sealed oracle's filename, size and digest. The intake process never opens that file. Inventory filenames must be basenames, so a row cannot cause directory traversal.

## Step 3 — run label-blind intake

Copy `docs/external_validation/templates/provenance.json` and `units.json`, replace the provenance placeholders, and keep the canonical units `W`, `m/s`, `m`, `K`. Then run:

```powershell
.\.venv\Scripts\python.exe -m src.external_validation.cli intake `
  --manifest <external_manifest.csv> `
  --old407 <old407_label_free.csv> `
  --old405 <old405_label_free.csv> `
  --inventory <delivery_inventory.csv> `
  --provenance <provenance.json> `
  --units <units.json> `
  --output <LABEL_BLIND_INTAKE.json>
```

## Step 4 — inspect only the permitted report

Review `LABEL_BLIND_INTAKE.json` and its hash. Resolve every blocker using provenance or label-free technical information only. Do not inspect class balance, q20/q30 membership, outcomes, or class-conditioned summaries. An OLD-407/OLD-405 overlap is a stop until provenance is resolved.

## Step 5 — obtain the explicit owner decisions

Copy `docs/external_validation/templates/owner_decisions.json`. The protocol owner must replace its placeholders before labels: included IDs, label-free technical exclusions, at least two repeats/seeds, and an explicit assignment of every included `group_token` to exactly one of five held-out folds per repeat. The generator derives every fold's training complement and proves its size; a declared minimum is not accepted as proof. The supported paired interval and failure/fallback strings in the template are exact executable contracts.

`StratifiedGroupKFold` is not currently accepted because its exact fold sizes depend on labels and therefore cannot prove B80 feasibility before the oracle opens. The owner may choose the supported preassigned label-free group folds or document a different pre-label amendment; the software will not choose automatically.

If the batch or planned folds cannot support B80, stop here. The only permitted next action is a documented pre-label owner decision to defer or amend. Never shorten the endpoint automatically.

## Step 6 — generate, review, commit and hash the addendum

```powershell
.\.venv\Scripts\python.exe -m src.external_validation.cli freeze `
  --intake <LABEL_BLIND_INTAKE.json> `
  --decisions <owner_decisions.json> `
  --output-directory <freeze_directory>

.\.venv\Scripts\python.exe -m src.external_validation.cli verify-bindings
```

Review `EXTERNAL_BATCH_FREEZE.json` and `EXTERNAL_BATCH_FREEZE.sha256`. Commit both files and every source file named in `source_code_hashes`. Record the resulting full 40-character commit SHA.

> **LABEL-ACCESS BOUNDARY — STOP**
>
> Do not proceed unless the exact freeze JSON and hash are committed, all intake blockers are resolved, and the owner has approved every dataset-specific choice. Steps below may access `has_keyhole`.

## Step 7 — open the sealed oracle through the gate

Run only the locked command. It verifies the freeze hash, proves the freeze, sidecar and required sources are present unchanged in the named ancestral commit, checks the environment, manifest and unused output paths, and only then reads the original oracle. The original oracle is not rewritten after technical exclusions: its frozen custodian size/SHA-256 must match, unknown or duplicate IDs are rejected, and only the frozen included IDs are returned to execution.

```powershell
.\.venv\Scripts\python.exe -m src.external_validation.cli execute `
  --manifest <external_manifest.csv> `
  --oracle <sealed_oracle.csv> `
  --freeze <freeze_directory\EXTERNAL_BATCH_FREEZE.json> `
  --freeze-commit <40-character-commit-sha> `
  --output-root <external_validation_output_root>
```

Do not run the Phase 1.22 availability script or any historical population loader on the new delivery.

## Step 8 — review execution barriers and artifacts

Confirm that the split manifest has five folds per repeat, every training pool supports B80, all three arms share each split, every path is unique through B80, and failures/fallback events match the frozen rules. If the B16 feature-only design lacks both classes, stop; do not reseed, extend past B16 or replace it after seeing labels.

## Step 9 — issue the frozen claim ledger

Review the preserved per-budget predictions and metrics, repeat-block contrasts, guardrails, fit diagnostics, validation report and claim ledger. Report the three decisions separately:

- external confirmation;
- incumbent replacement;
- pure acquisition attribution from the same-B16 control.

A positive mean alone is not a pass. A missing eligible batch or stopped execution is “validation not run,” not a method failure.
