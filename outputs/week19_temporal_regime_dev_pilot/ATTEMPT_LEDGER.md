# Week 19 DEV pilot — attempt ledger

**Status: post-hoc exploratory; not pre-registered confirmatory evidence.** Every execution that touched the pilot's paths, fits or evaluation is listed, including runs whose outputs were thrown away.

| # | UTC, 2026-10-09 | What ran | GP fits | Outputs | Effect on design |
|---|---|---|---|---|---|
| P0 | 23:51 | `python -m src.week19_dev_pilot p0` | 0 | 12 P0 checks: 10 PASS, 2 INFO. Wrote `pilot_inputs.csv` and `pilot_manifest.json` (sha256 `a94ad88b…41b0`). | The manifest freezes the decision rule, the prediction (H1–H3) and the failure rules. |
| 0 | 23:52 | Dry run of the P1/P2 plumbing in the session scratchpad, with a stub engine (random probabilities, no GP fits). See the note below. | 0 | Thrown away; nothing in this directory comes from it. | None. |
| freeze | 23:53 | Commit `c88f92c9`: code, manifest, P0 tables, Astra package | — | — | Timestamps the freeze before any fit. |
| P1 | 23:53:34–39 | `python -m src.week19_dev_pilot p1` | **90** (cap 90) | `paid_paths.csv`, `fit_diagnostics.csv`, `predictions.csv`, `oracle_response_diagnostics.csv`, `provenance/p1_run.json`, `provenance/p1_stdout.log`. 90/90 ok. | — |
| P2a | 23:54–23:56 | `python -m src.week19_dev_pilot p2` | 0 | Metrics, bootstrap, decision: ADVANCE. | — |
| P2b | 23:56 | P2 rerun after a code correction (see below) | 0 | `metrics.csv` byte-identical to P2a; verdict unchanged (ADVANCE). | None. The decision rule and its thresholds were not changed. |
| R1 | 2026-10-10 | Post-hoc review: `python -m src.week19_pilot_review margins`, `latent`, `oracle`, `gallery`, `review`, `checks`. It reads the saved predictions, thresholds and oracle diagnostics only. | **0** | `review/`, `ioan_gallery/`. Reporting corrections are listed in `review/REPORTING_CORRECTIONS.md`. | None. The verdict, manifest, decision and saved predictions are unchanged (`review/experimental_files_unchanged.csv`). |
| D1 | 2026-10-10 | Download of the 30 already-linked native images at the pinned NEW revision. No local copy existed. Each was identity-verified by LFS SHA-256 and stored in the git-ignored raw cache. | 0 | `ioan_gallery/image_inventory.csv` | None. No other image was fetched. |
| T1 | 2026-10-10 | `pytest src/tests/test_week19_pilot_review.py src/tests/test_week19_dev_pilot.py`: 18 passed. The existing pilot test file includes one synthetic unit test of the E1 threshold rule (two small GP fits on 30 random points). No learner was fitted to thesis data. | 0 on thesis data | — | None. |

## Notes

**Attempt 0.** The E1 learned threshold `u` depends only on the paid (depth, label) pairs. It does not depend on the GP, so the stub run already computed the real `u` values for the shared paths.

The shared maximin paths pay the late negative `H-f4fc937e86` in 23 of the 30 WHOLE_E1 checkpoints. The largest WHOLE_E1 `u` in those checkpoints is 130.3 µm, so no fit reaches the 200 µm pull level. Under the frozen rule, H1 was therefore headed for **UNTESTABLE (no pull on the shared paths)** before the real P1 run.

Nothing about the GP fits, predictions or metrics was seen before P1.

**P2b correction.** After P2a, three things changed in `decide()`:

1. **Exact-arithmetic comparisons.** The gate comparisons and the H3 comparisons now carry a tolerance of 1e-12. The metrics are fractions k/20 and k/24. The short-K gate sits exactly at its limit (ACTIVE 12/20 against WHOLE 13/20 − 0.05 = 12/20), and a floating-point representation could otherwise flip it. P2a had already evaluated it as passing.
2. **No boundary claim from q20.** The q20 field no longer implies a boundary claim: q20 did not deteriorate, but its interval includes 0.
3. **More reporting.** Counts and margins were added to `decision.json`.

No threshold, metric, aggregation or bootstrap setting changed.

**No other executions.** No fits were run outside P1; the review (R1) fits nothing. Neither P3 nor the morphology fallback, nor any C3 repeat, was run.
