# Pre-new-data readiness

Prepared 2026-09-27 to 2026-09-28 on `codex/pre-new-data-readiness`, based on canonical `main` commit `3b42fb235ca3e39c1712ed6b60c4dba71084f3f1`.

## Research judgment

**Keep the thesis direction. Keep Track A frozen. Treat Track B as recommendation B: a bounded measurement-aware application/validation study, with a larger second contribution conditional on actual sensors, matched simulation observations and independent experimental truth.**

The broad observable-to-hidden-state idea and simulation-generated paired supervision already exist in the literature. A defensible question is whether a causally available, experimentally realizable early width signal adds useful discrimination and probability quality beyond `[P,VX,LS,ST]`, and whether that information survives measurement constraints and independent validation. No novelty claim rests merely on using SPH or a differently named feature.

## Track A

**Infrastructure status: PASS on focused synthetic verification. Real execution: CONDITIONAL on the future batch and a committed, owner-approved pre-label addendum. External validation: NOT RUN.**

| Required item | Status |
|---|---|
| Frozen science changed | NO |
| New Ioan data accessed | NO |
| New acquisition method or OLD-405 method search | NO |
| Implementation map | Complete; requirements, code, allowed inputs, label boundary, checks and unresolved batch choices mapped |
| Label-blind intake | Ready for the supported feature-manifest, inventory, provenance and canonical-unit contract |
| Dataset-freeze generator | Ready; exact group folds prove every training complement supports B80 before labels |
| Locked three-arm runner | Ready; pinned M3 bindings, historical seed parity, sequential label access, held-out isolation and preserved failure artifacts checked |
| Frozen analysis | Ready; primary/secondary endpoints, paired repeat-block inference, guardrails and three separate claims implemented |
| Mock dry run / information barriers | PASS: 18 focused tests, a real M3 fit on synthetic data, and a mocked three-arm run over ten splits |
| Real external validation | NOT RUN |

Authoritative operational documents: [implementation map](../external_validation/IMPLEMENTATION_MAP.md) and [new-data arrival runbook](../external_validation/NEW_DATA_ARRIVAL_RUNBOOK.md).

One complete supervisor review was performed. Its localized repairs were delegated to the engineer and accepted after targeted review and verification. These cover pre-label B80 feasibility, complete freeze decisions, validation before oracle access, custodial hash verification, complete exclusion accounting, preserved failures/fallbacks, historical initialization parity, paired reporting and claim logic. The final oracle repair preserves the original custodial file even when known manifest rows are technically excluded; only included labels enter execution. Accepted research evidence was reused.

### What remains a legitimate pre-label dependency

- A genuinely new, provenance-supported batch with a separate allowed-feature manifest and sealed oracle.
- Explicit protocol-owner decisions for grouping, supported split construction, repeat blocks/seeds, all technical exclusions, interval implementation and failure rules. The implemented option requires preassigned label-free group folds, five per repeat and at least two repeats; it is not an automatic scientific choice. Label-dependent grouped stratification is unsupported without a pre-label B80 feasibility proof.
- A label-free demonstration that every planned training pool supports B80. A declared minimum is not proof; unsupported construction or inadequate size must stop before labels.
- A committed dataset addendum and hash, matching code/environment, and resolved intake blockers.

These are future execution conditions. No shorter endpoint, reseeding rule or new acquisition policy is authorized. Custodian-provided raw/oracle hashes and corruption statements are provenance assertions before the boundary; the method-side intake does not independently read sealed payloads to verify them. A schema barrier cannot detect a target deliberately disguised as an allowed numeric feature.

### On the day the batch arrives

Quarantine the delivery and keep the feature manifest separate from the sealed oracle. Export the historical label-free reference manifests, run the blind intake, and resolve only its permitted provenance, overlap, units and technical-exclusion findings. Complete the owner-decision template, generate and review the addendum, then commit its JSON, digest and pinned source files. The locked command verifies those records, the environment, manifest, fold feasibility and unused output paths before opening the original oracle. It then executes the three arms and produces the frozen report and separate claim ledger.

No successful mock result is scientific evidence for Candidate B. A stopped or incomplete run cannot confirm, replace or establish acquisition attribution. Real M3 was smoke-tested on a small synthetic fit; a full real-model external run has not been performed.

## Track B

| Required item | Result |
|---|---|
| Papers reviewed | 24 primary studies/records assessed; full-text versus abstract/preview access is disclosed |
| Evidence inventory | 26 rows: 15 original signals plus 11 modality rows |
| Original conservative classifications | All 15 retained exactly; original inventory unchanged |
| Ioan setup availability | UNKNOWN for all 26 rows |
| Literature-supported observations | Optical width/geometry, thermal radiance, conditional calibrated temperature, photodiodes, acoustic emission, plume/spatter, specialized ICI/OCT and research X-ray |
| Candidate hidden targets | Existing run-level manual keyhole outcome; conditional melt penetration |
| Serious observable-hidden pairs | Two; no unsupported third candidate |
| Width experimental plausibility | Optical width is measurable in documented setups; the exact SPH extrema/startup-increment correspondence is unproven |
| Novelty | Broad concept already published; narrow contribution depends on measurement fidelity, incremental value and independent validation |
| Track B statistical association analysis executed | **NO** |

The six outputs are:

1. [Targeted literature review](../trackB/LITERATURE_REVIEW.md)
2. [Observability evidence table](../trackB/OBSERVABILITY_EVIDENCE_TABLE.csv)
3. [Width experimental reality check](../trackB/WIDTH_EXPERIMENTAL_REALITY_CHECK.md)
4. [Two observable-hidden priorities](../trackB/OBSERVABLE_HIDDEN_PRIORITIES.md)
5. [Questions for Ioan](../trackB/QUESTIONS_FOR_IOAN.md)
6. [Research position](../trackB/TRACK_B_RESEARCH_POSITION.md)

The central width limitation is physical and temporal: ten historical resampled increments span a median 68 microseconds, whereas camera cadence/exposure may not resolve that startup interval. The retrospective prefix result is not proof of a prospectively causal camera pipeline. The existing run-level label also cannot supply an instantaneous onset timestamp.

Ioan needs to identify the available sensor/raw stream, actual timing/calibration, intended target and decision time, independent truth source, SPH-to-sensor correspondence, and realistic independent experimental validation. These answers determine whether Track B remains a smaller thesis study or merits expansion.

## Verification and Git

### Completed verification

| Check | Result and scope |
|---|---|
| Focused infrastructure suite | **18 passed** in `src/tests/test_external_validation_readiness.py` |
| Intake barriers | Successful intake; duplicate IDs; OLD-population overlap; missing features; forbidden target schema/read attempts; canonical units and safe paths checked |
| Pre-label and execution gates | Insufficient B80 capacity; fold certificates; unsupported choices; malformed freeze digest; committed source/freeze and environment checks; policy/endpoint overrides checked |
| Oracle integrity and exclusions | Original size/digest required; known excluded IDs allowed; duplicate/unknown IDs rejected; included labels returned |
| Method integration | Pinned modules bind; historical feature-only seed/path parity checked; Candidate B observes its prefix sequentially; changing held-out labels or features cannot change acquisition paths |
| Failure handling | Fatal partial results preserved; optimizer and empty-band fallbacks distinguished; incomplete prediction coverage rejected |
| Real M3 smoke | A 24-row synthetic fixture with 16 revealed labels fitted the actual frozen evaluator; probabilities were finite and strictly between zero and one |
| Mock CLI execution and analysis | PASS: 105 fake rows, ten splits, three arms, B16–B80, 40,950 prediction rows, 2,400 selected-path rows and 2,030 diagnostic rows |
| Frozen reporting | Separate confirmation, replacement and acquisition decisions; repeat-block contrasts, q30 counterparts, B16/B40/B80 checkpoints and separate descriptive B24/B32/B40/B60 crossings |
| Syntax and whitespace | `compileall` passed; staged-file whitespace checks passed after two documentation-only whitespace fixes |
| Track B mechanical QA | 24 source records; 26 parseable evidence rows; all 15 original classifications preserved; all actual-setup availability UNKNOWN; local links checked |

Commands used:

```powershell
.\.venv\Scripts\python.exe -m pytest -q src\tests\test_external_validation_readiness.py
.\.venv\Scripts\python.exe -m src.external_validation.cli synthetic-dry-run --output outputs\external_validation_synthetic_readiness\SYNTHETIC_READINESS.json
.\.venv\Scripts\python.exe -m compileall -q src\external_validation src\tests\test_external_validation_readiness.py
git diff --check
git diff --cached --check
```

The real M3 smoke used `FrozenM3Evaluator.fit_predict`, NumPy seed 121, 24 synthetic four-feature rows, the first 16 rows with alternating labels, a 20-row training pool and four held-out rows. It checks binding and numerical execution, not model quality. The [saved mock evidence](../../outputs/external_validation_synthetic_readiness/SYNTHETIC_READINESS.json) is explicitly labelled `FAKE_SYNTHETIC_ONLY`. Historical scientific suites were not rerun or represented as passing.

### Review branch and file scope

Branch: `codex/pre-new-data-readiness`. Base and unchanged local `main`: `3b42fb235ca3e39c1712ed6b60c4dba71084f3f1`.

The commit series contains only the new external-validation package, its focused tests, implementation map/runbook/templates, synthetic summary, six Track B outputs listed above, and this report. No pre-existing tracked scientific file is modified. The user's untracked `.codex/` agent configuration is preserved and excluded from the series. No merge or push is performed.

| Commit | Scope |
|---|---|
| `a60ec89923b08d1ab9a362e960d38eea0257a427` | Track A infrastructure: 15 new files |
| `eabda3a99b0c5552ece6e9865f74b2654695edc6` | Track B evidence and research judgment: six new files |
| `Record pre-new-data readiness and verification` | This report, the third and final commit in the review series; its SHA is available from `git log -1 --format=%H -- docs/pre_new_data/PRE_NEW_DATA_READINESS.md` |

Total: **22 added files, no modified or deleted pre-existing tracked files**. Final working-tree accounting: only the preserved user-owned `?? .codex/` remains untracked; no staged or unstaged tracked changes. Generated Python bytecode is excluded. The review branch is local and has not been pushed; no claim of remote synchronization is made.

The engineer's usage limit was reached only during final packaging, after implementation and tests were complete. The supervisor completed explicit-file staging and commits; no additional agent or scientific review was started.
