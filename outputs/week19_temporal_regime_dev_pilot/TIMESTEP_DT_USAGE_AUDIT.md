# Did any earlier week use `timestep × DT` as physical time?

**Answer: no.** No earlier week converted a frame `timestep` (solver iteration) into time by multiplying it by the folder `DT`. Nothing needs to be rerun. Nothing was rewritten in this audit.

## Why it would have been wrong

The Week 19 audit, check C1 in `../week19_temporal_regime_audit/REPORT.md` §0, established two facts:

- **The folder `DT` is the frame interval, not the solver step.** The median frame Δt equals `DT` (ratio 1.000 ± 0.003).
- **`timestep` is the solver iteration.** So `timestep × DT` overstates monitor time by the number of iterations per frame (median 410 OLD, 567 NEW).

Physical time must come from `iter.dat` → `time.dat`.

## What the searches found

The searches were rerun by `python -m src.week19_pilot_reports dtaudit`:

- every row is in `tables/timestep_dt_search_hits.csv`;
- the curated findings are in `tables/timestep_dt_usage.csv`.

| Class | Location | What it is | Assessment |
|---|---|---|---|
| none | `src/week19_series.py` 172–182 (Week 19 audit) | `timestep × DT` compared with `time.dat` | The only such product in the code. It is a diagnostic that *shows* the mismatch; it is never used as time. |
| wording | `src/week18_data_audit.py` 39 | `DTr = DT · VX / LS` | Frame spacing in spot-crossing units, not a solver time step. Values unaffected. |
| wording | `outputs/week18_independent_research/DATA_AUDIT.md` 14 | "Time-step rule differs: DT·VX/LS …" | Should read "frame-spacing rule". The numbers (0.075 OLD vs 0.108 NEW) stand. |
| wording | `outputs/week18_independent_research/RESEARCH_LOG.md` 23–24 | "time-step rule DT·VX/LS …" | Same wording point. |
| wording | `outputs/week18_independent_research/RED_TEAM.md` 9 | "the time-step rule differs between OLD and NEW" | Same wording point. |
| caveat | Week 5 notebooks `notebooks/week_05/01`–`05`, their outputs `outputs/week5_01…05`, `docs/week5_first_conduction_gp_log.md` (33, 51, 190), `docs/week5_gp_meeting_brief.md` (5) | First-Conduction GP regression on the **raw timestep** | See note below. |

**Note on Week 5.** The response there is an iteration count, and those files say so explicitly ("not established as physical time"; `DT` is only parsed, and notebook 01 cell 68 records "physical-time interpretation blocked"). This is not a ×DT error.

Iterations per frame differ between runs (median 410 OLD vs 567 NEW). Raw timesteps, and their MAE/RMSE in "timesteps", are therefore not comparable across runs or campaigns as durations.

**Correct timing elsewhere.** The other weeks' code reads monitor time from `time.dat`: 23 source files in Weeks 6, 7, 9, 11 and 18, listed as `reads_monitor_time_dat` in the hits file. Two cases differ, and both are already documented:

- Week 7 phase 1 (`src/week7_phase1_sph_v2_dataset_shift_audit.py`) leaves durations NaN: `physical_time_duration_available = False`, Keyhole duration counted in frames, "no ms conversion";
- Week 9 phases 2.1r and 2.1re (`src/week9_phase2_1r_simple_width_change_control.py`, `src/week9_phase2_1re_early_prefix_width_control.py`) use resampled monitor points.

## Suggested errata (not applied)

1. Week 18: replace "time-step rule" with "frame-spacing rule (DT·VX/LS = frame interval in spot-crossing units)" in `DATA_AUDIT.md`, `RESEARCH_LOG.md` and `RED_TEAM.md`.
2. Week 5: add "iteration units; not comparable across runs as time" beside the first-Conduction target wherever it is cited in the thesis.

Under the errata-only rule, these are listed here and left to the owner.
