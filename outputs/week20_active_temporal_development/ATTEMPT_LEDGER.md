# Week 20 attempt ledger (post-hoc DEV research)

Every execution that fits a model, computes acquisition paths or evaluates results is listed. Runs whose outputs were thrown away are listed too.

**Fit accounting:**
- **Caps:** 15,000 scalar learner fits; 160 temporal or functional fits; ≤ 4 CPU threads; ≤ 8 GiB; ≤ 8 h in total.
- **Scope:** C3 (repeats 17–20) is reserved and unused. No simulator job, no label change, no exclusion change.

| # | UTC | What ran | Scalar fits | Temporal/functional fits | Outputs | Notes |
|---|---|---|---:|---:|---|---|
| M1 | 2026-10-12 | `python -m src.week20_track1_al manifest`: builds the 60 task-folds and checks responses and labels against the Week 19 inputs; no fit | 0 | 0 | `track1/manifest_track1.json`, `track1/HYPOTHESES_TRACK1.md` | Committed and pushed before any Track 1 fit. |
