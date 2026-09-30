# Week 11 new-data arrival decision gate

Audit date: 2026-09-30. Scope: provenance, label-blind intake, Bug semantics, B80 feasibility and signal availability only. This report does not authorize label opening or external validation.

## Publication prerequisite

The reviewed readiness series was pushed and fast-forwarded into `main`. Local and remote `main` were verified at `5ae71520073435ff4d312c9b1bc99683c8a3eb4a` before Week 11 began. The three readiness commits are `a60ec89923b08d1ab9a362e960d38eea0257a427`, `eabda3a99b0c5552ece6e9865f74b2654695edc6` and `5ae71520073435ff4d312c9b1bc99683c8a3eb4a`. Their 22 added files matched the previously reviewed scope. Reverification passed 17 mock/infrastructure tests; the real-M3 smoke test was deliberately deselected under this task's no-model-execution instruction. Syntax, committed-range whitespace and JSON checks passed. The user's `.codex/` was not committed. No history was rewritten.

## Exact source identity

| Question | Answer |
|---|---|
| Final HF revision | `2e1eec9c98fd57609d2815f174586336ab59da07` |
| Final HF commit timestamp | `2026-09-29T18:39:05Z` |
| Previous HF revision used by current OLD-407 and OLD-405 | `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8` |
| Original OLD-407 audit revision | `d69dac5bda8b622bc0de316b112815c6056c06ec` |
| Current simulation directories | 592 |
| Newly added simulations / total new batch | **185** |
| Modified historical simulation subtrees | **0** |
| Unchanged historical simulation subtrees | **407** |
| Deleted historical simulation subtrees | **0** |
| Matches Ioan's statement of 185 | **YES, exactly** |
| Exact duplicate added subtree OIDs, or added OIDs matching old subtrees | None |

Simulation identity is proved by pinned Git tree paths and subtree OIDs, not upload times. All historical simulation subtrees are unchanged. At repository root, the three historical annotation files are unchanged, `.gitattributes` changed, and `labels_new_data_4_prep.csv` was added. Subtree identity is a statement about committed content; it does not certify simulator independence, scientific validity, experimental observability or physical file integrity after download.

## Execution gate

| Question | Answer |
|---|---|
| Label-blind intake | **BLOCKED overall**; the prepared intake was run unchanged and accepted all 185 input rows technically |
| Stable IDs / exact four-input configurations | 185 / 185 unique |
| Parameter schema and units | All 185 passed; only the four approved parameter values and W, m/s, m, K units were read |
| Technical exclusion candidates | 0; no Bug-based exclusion was applied |
| OLD-405/407 ID, configuration-token and exact-input overlap | **NONE** |
| Bug representation in the new data | **UNRESOLVED**; historical annotation schemas are frame-level and mixed with physical outcomes |
| Wall-touch distinguishable from other Bug reasons | **UNRESOLVED**; no separate reason source established |
| Bug exclusion rule known | **NO** |
| Ioan clarification required | **YES** |
| B80 feasibility | **BLOCKED for the final eligible cohort; structural capacity PASS** on all 185 input-valid configurations |
| Ready for dataset-specific pre-label freeze | **NO** |

The prepared intake reports exactly `INDEPENDENCE_OR_PROVENANCE_UNRESOLVED` and `ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED`. Source snapshot identity and input non-overlap are established; simulator/version and scientific generation provenance remain unresolved. The newly added annotation CSV is not represented as a prepared simulation-level oracle. No oracle row or digest was fabricated to clear the gate.

The 185 input-valid configurations admit balanced five-fold construction with 37 held-out and 148 training rows per fold. Two distinct deterministic witnesses use public seeds 1101 and 1102; no seed search or outcome information is involved. This demonstrates two feasible repeat allocations, not an approved repeat count or a maximal count of possible allocations. It is not a proof that the cohort remains large enough after an unresolved eligibility decision. The complete assignments and repeat accounting are in [the B80 audit](WEEK11_B80_FEASIBILITY.md).

All 185 simulations have metadata entries for frames, GIFs, `frames.csv`, parameters, an archive and a monitor directory containing the same 34 filenames. Melt/gas bounds, temperature-related monitors and simulation-time monitors are **present as files**. An explicit surface-area output is **absent from the listed monitor names**. Laser-on timing, verified raw geometry inside archives, and validated width/length/penetration trajectories are **unresolved**. No monitor values, image contents or archives were opened. [The availability inventory](WEEK11_TRACKB_SIGNAL_AVAILABILITY.md) separates source-file presence from derived quantities.

The 185 new archive OIDs are distinct. A historical archive-content comparison is unresolved because the accepted historical file inventory contains no archive entries. Six repeated monitor OID groups concern shared time/iteration/step or static-count/capacity files; these are file-level duplicates, not evidence that whole simulations are duplicates. No case is excluded on that basis.

**No pre-label freeze is approved.** The new annotation payload remains unopened.

The historical schema places Bug indicators beside physical class labels, and per-simulation `frames.csv` also contains physical labels. Historical `bug_free` and categorical `Screenshot Bug` are not interchangeable. No existing source establishes a general exclusion rule or distinguishes wall-touch from other Bug reasons. The new annotation schema, affected-run count, first affected frame and later-only Bug incidence cannot be asserted from filenames or hashes.

An early Bug-free interval is not automatically an eligible run for the frozen run-level target. Conversely, a Bug flag must not silently remove a run or turn its physical outcome into Conduction or Keyhole. Eligibility needs an explicit definition before labels are opened. A structural B80 witness on all input-valid rows, if available, cannot settle eligibility after an unresolved exclusion policy.

Ioan's phrase "of no use to the models" is not yet a reproducible technical eligibility criterion. A rule based on apparent model usefulness could select cases according to their outcomes or difficulty. This audit neither assumes that happened nor implements such a rule. The reason and unit of invalidity must be specified first. In particular, absence of an observed physical label in a Bug-affected trace must not silently become a negative target.

## Research interpretation of the permitted input comparison

The new campaign occupies a shifted input distribution. Power spans approximately 350.03–449.85 W and spot size 40.00–49.95 micrometres, concentrating on higher power and smaller spots than OLD-407. Substrate temperature spans 301.61–499.77 K; 86 of 185 inputs exceed the historical maximum of about 399.82 K. Scan speeds remain within the historical range. These are label-free facts from the prepared intake, not class or outcome evidence.

This makes the future study a test on a changed input campaign. It supplies no reason to tune M3, Candidate B, q20/q30 or the B16-B80 horizon. Whether the shifted campaign also changes physical outcomes remains unknown and deliberately uninspected.

## Exact remaining blockers

1. Define Bug eligibility for the frozen run-level target and obtain a separate Bug-only export. Until then, affected-run counts, first-Bug times, later-only Bug incidence and the final eligible cohort are unknown.
2. Confirm simulator/version and generation provenance, including the intended independent grouping unit. Exact configuration groups are available, but their existence does not identify every possible campaign or solver dependency.
3. Prepare a separately held simulation-level oracle and its custodial inventory/digest. The raw mixed annotation file's remote identity is recorded; its contents were not transformed or opened here.
4. Once those issues are resolved, approve the final included/excluded IDs, grouping, repeat/fold assignment, seeds and the remaining dataset-addendum fields before freezing. Recheck B80 on that exact cohort. This audit does not silently make those owner decisions.

## Minimal clarification for Ioan

> For the frozen run-level validation, does Bug invalidate the whole simulation or only the trace from its first affected frame, and what objective technical criterion does "of no use to the models" mean? Please provide a separate label-blind export with simulation ID, frame index/time, the actual Bug flag(s), and a reason distinguishing wall-contact from other unusable cases where known. Please keep physical class labels and `has_keyhole` out of that export.

The export must preserve distinctions between existing Bug fields; it must not collapse `bug_free` into a categorical Bug indicator. If the cause was not recorded, state that it is unknown rather than reconstructing it from physical outcomes. This question is prepared for the user; no message has been sent to Ioan.

## Non-negotiable boundary

- New Ioan `has_keyhole` or equivalent physical outcome values accessed: **NO**.
- Track A model executed: **NO**. Only model-free readiness checks were repeated during publication.
- Track B statistical analysis executed: **NO**.
- Frozen methods, q20/q30 definitions and B16-B80 horizon changed: **NO**.
- Dataset-specific freeze created or labels approved for opening: **NO**.

Week 11 stops at this audit. Any subsequent label opening or external validation requires the user's approval after the exact blockers are resolved.

## Verification and review status

The single complete supervisor review is finished. Accepted evidence from the scouts was reused. Localized corrections covered use of the existing intake to emit an honest blocked report, reproducible offline manifest construction, two distinct capacity witnesses, hash consistency, precise report names and the distinction between inspected metadata and unopened data. No broader research or method review was restarted.

The Week 11 focused suite passed **11 tests**. Compilation, local document links, deterministic manifest/input-inventory/witness reconstruction, semantic intake reproduction, inventory hashes and the raw intake report's SHA-256 sidecar passed. Every pre-existing tracked file still matched readiness `main` at verification. The Track A freeze file SHA-256 remained `2e2cb37eae26d1dc16fd0b16f5101fb9ece559c99277704bb97effeb9a87cf24`.

Detailed results and artifact hashes are recorded in [VALIDATION.json](../../outputs/week11_new_data_arrival_audit/VALIDATION.json). Reproduction commands are in [the offline runbook](OFFLINE_ADAPTER_RUNBOOK.md). The [185-row manifest](../../outputs/week11_new_data_arrival_audit/WEEK11_NEW_BATCH_MANIFEST.csv) is an audited input manifest, not an approved final evaluation cohort.

Review branch: `codex/week11-new-data-arrival-audit`, based on published `main` `5ae71520073435ff4d312c9b1bc99683c8a3eb4a`. Publication is limited to this branch; Week 11 is not to be merged into `main` by this task. The user's `.codex/` remains outside the commit. The branch commit is identified by the Git history for this report, avoiding a self-referential commit hash inside the file.
