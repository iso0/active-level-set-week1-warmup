# Week 19 DEV pilot — attempt ledger

**Status: post-hoc exploratory; not pre-registered confirmatory evidence.** Every execution that touched the pilot's paths, fits or evaluation is listed, including runs whose outputs were thrown away.

| # | UTC (2026-10-09/10) | What ran | GP fits | Outputs | Effect on design |
|---|---|---|---|---|---|
| P0 | 23:51 | `python -m src.week19_dev_pilot p0` | 0 | All 12 P0 checks: 10 PASS, 2 INFO. Wrote `pilot_inputs.csv` and `pilot_manifest.json` (sha256 `a94ad88b…41b0`). | The manifest freezes the decision rule, the prediction (H1–H3) and the failure rules. |
| 0 | 23:52 | Dry run of the P1/P2 plumbing in the session scratchpad, with a stub engine (random probabilities, no GP fits). See the note below. | 0 | Thrown away; nothing in this directory comes from it. | None. The manifest, decision rule and hypotheses were not changed. |
| P1 | planned after the freeze commit | `python -m src.week19_dev_pilot p1`: 90 planned learner fits under the caps | ≤ 90 | `paid_paths.csv`, `fit_diagnostics.csv`, `predictions.csv`, `oracle_response_diagnostics.csv` | — |

## Note on attempt 0

The E1 learned threshold `u` depends only on the paid (depth, label) pairs. It does not depend on the GP, so the stub run already computed the real `u` values for the shared paths.

The shared maximin paths pay the late negative `H-f4fc937e86` in 23 of the 30 WHOLE_E1 checkpoints. The largest WHOLE_E1 `u` in those checkpoints is 130.3 µm, so no fit reaches the 200 µm pull level.

Under the frozen rule, H1 is therefore headed for **UNTESTABLE (WHOLE_E1 shows no pull on the shared paths)**. This was known before the real P1 run and is recorded here for that reason.

Nothing else about the GP fits was seen before the real run.
