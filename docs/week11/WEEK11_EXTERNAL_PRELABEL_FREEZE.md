# Week 11 External Pre-Label Freeze Preparation

Status: **BLOCKED AND NOT LABEL AUTHORIZATION**.

Source snapshot: `ioandanielc/sph_v2@2e1eec9c98fd57609d2815f174586336ab59da07`.

This preparation applies the delegated, outcome-blind eligibility rule to the canonical 185-row Week 11 manifest. Exactly 136 simulations have no explicit Bug annotation and consistent approved status flags; they are the candidate external-validation cohort. Exactly 49 simulations are recorded as `WITHHELD_DUE_TO_BUG_FOR_EXTERNAL_VALIDATION`. This is an experiment-specific technical withholding decision. It does not declare those simulations permanently invalid and does not reinterpret their physical class.

The included cohort has 136 unique simulation IDs, exact `[P,VX,LS,ST]` configurations, configuration tokens, and group tokens. Every row retains all four canonical input fields. Accepted file-tree metadata records `parameters.json`, `frames.csv`, `monitor/iter.dat`, and `monitor/time.dat` for every included simulation. The accepted label-blind comparison reports zero simulation-ID overlap and zero exact-input overlap with OLD-407/OLD-405. These are metadata and input-only findings; no physical outcome was opened or derived.

One label-free scope observation matters. VX for the included 136 has minimum/median/maximum 0.209302/0.468615/0.985530 m/s, while the withheld 49 has 0.602896/0.816523/0.974206 m/s. Bug withholding therefore creates structured input selection rather than random loss. Future external-validation claims must be conditional on the 136-run Bug-cleared cohort, not generalized to all 185 arrivals. This requires no additional exclusion or label work before freezing.

The dataset decision fixes 20 repeat blocks with seeds 1101 through 1120. For each repeat, Python `random.Random(seed)` shuffles sorted exact-configuration group IDs once and assigns them round-robin to folds 1–5. There was no seed search. Each of the 100 folds holds out 27 or 28 simulations, leaving 108 or 109 for training; the minimum training pool is 108, so every fold supports B80. The repeats are repeated split blocks over one cohort, not 20 independent cohorts. Twenty blocks were selected before labels because two blocks are only the software minimum and provide an unsuitable three-point support for the frozen percentile-bootstrap interval.

All scientific contracts remain unchanged: the three frozen arms, every integer budget B16–B80, q20 accuracy normalized AULC B16–B80 as primary, the paired repeat-block percentile bootstrap with 10,000 draws, frozen failure/fallback rules, output paths, initial-design seed namespace, environment, and source hashes. The execution output root is fixed as `outputs/week11_track_a_external_validation` and has not been created. `FREEZE_PREPARATION.json` records these bindings. The full 185-row delivery manifest is retained alongside separate 136-row included and 49-row withheld manifests.

External confirmation still requires a positive primary mean with its 95% paired interval entirely above zero, B40 q20 recall change at least -0.03, and B80 full-test accuracy change at least -0.01. Replacement additionally requires a primary mean improvement of at least +0.01. These existing thresholds are bound through the unchanged Track A freeze and execution sources; no outcome was calculated here.

Two required custody gates are absent:

1. Independent scientific provenance and simulator/version metadata have not been supplied and cannot be inferred from the Hugging Face tree.
2. A separate custodial `sim_id,has_keyhole` oracle filename, byte size, and SHA-256 have not been supplied. The mixed annotation payload is not accepted as that oracle.

The preparation invokes the existing freeze builder and confirms that it stops on these intake blockers. It creates neither `EXTERNAL_BATCH_FREEZE.json` nor `EXTERNAL_BATCH_FREEZE.sha256`. The owner is recorded as `Thesis protocol owner (user instructions dated 2026-10-01)`. Once both custodial records exist, rerun the existing label-blind intake, review its zero-blocker report, and pass the recorded decisions to `src.external_validation.cli freeze`.

Reproduce the current blocked preparation with:

```powershell
.\.venv\Scripts\python.exe -m src.week11_external_freeze_prep `
  --manifest outputs/week11_new_data_arrival_audit/WEEK11_NEW_BATCH_MANIFEST.csv `
  --bug-status outputs/week11_bug_audit/simulation_bug_status.csv `
  --overlap outputs/week11_new_data_arrival_audit/label_blind_overlap_summary.json `
  --directory-metadata outputs/week11_new_data_arrival_audit/new_directory_metadata.json `
  --monitor-metadata outputs/week11_new_data_arrival_audit/new_monitor_metadata.json `
  --intake outputs/week11_new_data_arrival_audit/prepared_intake_report.json `
  --output-directory outputs/week11_external_prelabel_freeze_reproduced
```

**READY TO OPEN SEALED LABEL ORACLE: NO.** Stop before label access.
