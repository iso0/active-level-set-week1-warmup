# Week 20: active temporal development (post-hoc DEV research)

**Start here:** [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md) (results, failures, mechanisms, temporal-GP comparison) and [ATTEMPT_LEDGER.md](ATTEMPT_LEDGER.md) (every execution and fit count). [NAMED_RUNS.csv](NAMED_RUNS.csv) maps each run named by an H code to its full sim ID; H suffixes are not unique.

| Folder | Content |
|---|---|
| `track1/` | Real active-learning benchmark (WHOLE E1 + straddle, ACTIVE E1 + straddle, G3 + margin; R3_NEW / R3_OLD / R1_POOLED, repeats 1–4). Frozen manifest and hypotheses; complete query ledgers; per-step fits; grid predictions; curves; Week 18 AULC, contrasts and QTT; fidelity to the Week 18 caches; threshold mechanism. Post-hoc files are prefixed `POSTHOC_`. |
| `track2/` | Temporal-GP development on NEW (repeats 1–2, 10 folds, B16/40/80, the Week 19 shared paid paths). Frozen manifest and hypotheses, post-start declaration (T2-PS1) and evaluation rules (written before scoring); trajectory inventory; compression errors and the resolution rule; checkpoints; fit tables; SVGP validation; evaluation tables, hypothesis verdicts and figures. Post-hoc files are prefixed `POSTHOC_`. |
| `ioan_addendum/` | G5 (H-b302fc6cbd) frame 81, front/side/top, at the pinned NEW revision. The Week 19 gallery is unchanged apart from an appended pointer. |
| `provenance/` | Run logs and the `.venv` install log. |
| `_cache/` | Git-ignored resumable caches: per-run ledgers and per-step predictions, native trajectories, checkpoint arrays, Track 2 predictions. |

**Reproduce:**

```
python -m src.week20_track1_al manifest
python -m src.week20_track1_al run 4
python -m src.week20_track1_analysis
python -m src.week20_track2_data extract
python -m src.week20_track2_models prep
python -m src.week20_track2_models scalar
python -m src.week20_track2_models functional
.venv/Scripts/python.exe -m src.week20_track2_svgp validate
.venv/Scripts/python.exe -m src.week20_track2_svgp fit
.venv/Scripts/python.exe -m src.week20_track2_svgp fidelity
.venv/Scripts/python.exe -m src.week20_track2_svgp_poststart
python -m src.week20_track2_eval
python -m src.week20_ioan_addendum
```

**Environment:**
- **System Python 3.14.4:** numpy 2.5.1, pandas 3.0.5, scipy 1.18.0, scikit-learn 1.9.0.
- **`.venv` (git-ignored):** built on the system site packages, plus torch 2.13.0+cpu and gpytorch 1.15.1. Inside it numpy resolves to 2.4.6, so only the GPyTorch script runs there.

**Local inputs, not committed:** the raw cache `data/raw/sph_v2/` and `outputs/week19_temporal_regime_audit/_cache/frames.pkl`.

**Scope:** C3 (repeats 17–20) unused. No label, eligibility or exclusion change. The 49 Bug-withheld NEW runs are not used.
