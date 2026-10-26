# EA study (error attribution → improvement): task record

Opus; owner instruction of 2026-10-26.

## Goal

Find a system that reaches high early BA with few simulations and reaches the target accuracies with fewer queries:
1. First separate the stage the current system's error comes from.
2. Then implement and validate one concrete improvement based on that finding.
3. Go to the end when a justified opportunity exists, not only a diagnosis.

## Start

| item | value |
|---|---|
| HEAD = origin | acf673924b44413a64f55511660baefd9256e9a0 (branch joint-depth-label-dev) |
| later commits | none |
| tracked changes | none |
| first action | 2026-10-26 13:33:01 UTC |
| window | ONE 48 h window, until 2026-10-28 13:33:01 UTC |

Quota, restarts and session changes never reset the window. It is closed early when done.

## Workspace

| item | location |
|---|---|
| worktree | C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev |
| outputs | outputs/research_campaign_20261026/opus_error_attribution/ |
| code | src/ea_*.py |
| runner | src/ea_runner.ps1 |
| coordination | C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261026\ — only opus_state.json and my own lock / temp files are written; Astra's state is read only |

## Resources

- At most 3 heavy numerical single-thread workers on 8 logical CPUs, leaving 3 for Astra and 2 for the system.
- Heavy analyses count in the 3. The limit is lowered on a smaller machine, with a memory guard.
- Astra's share is never taken.
- Astra state at start: astra_local_correction_20261024 CLOSED ("both prospective DEV screens failed; complete artifact handoff sealed").
- The handoff was copied read-only, with SHA-256s, to the scratchpad for reading. None of Astra's code is run or imported, and none of her files is added to Git.

## Order of work

| stage | content | registered before results in |
|---|---|---|
| 1 | hypotheses A–D and diagnostic design | `PROTOCOL_EA_HYPOTHESES.md` |
| 2 | diagnostics on the recorded paths (evaluator-only oracles marked) | |
| 3 | design decision, candidates and controls | candidate protocol |
| 4 | validation rules, candidates and IDs | validation protocol |
| 5 | fresh-ID validation (selector stays margin) | |
| 6 | exports, independent recomputation, report, thesis records, commit / push | |

## Rules

- 541 runs form one pool; OLD/NEW is provenance only, and there is no free archive.
- Every opened simulation is counted, including the 8 startup runs. The channels of a simulation are opened once.
- Unopened outcomes are never given to a learner.
- Labels, exclusions and the hard-group definition are not changed.
- No physical simulator, paid API / cloud or C4.
- Old frozen decisions are not changed.
- No oracle quantity, test label or hard-group membership enters any candidate.
