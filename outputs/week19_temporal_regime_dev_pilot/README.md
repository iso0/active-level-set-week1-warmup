# Week 19 DEV pilot (post-hoc exploratory)

This directory holds a bounded test on the R3_NEW folds, DEV repeats 1–2: does the active-window depth A help E1 relative to the whole-record maximum and G3? All arms are fitted on identical label-blind paid paths.

The pilot is P0–P2 of Astra's request in `../astra_week19_rnd/`, with the owner's changes of 2026-10-10. It also holds the descriptive table, Ioan's summary and the `timestep × DT` audit.

- **Start here:**
  - `PILOT_REPORT.md`: verdict, prediction versus outcome, results, limitations;
  - `IOAN_SUMMARY.md`: one page for Ioan, with six cases and verified image links;
  - `TIMESTEP_DT_USAGE_AUDIT.md`;
  - `IOAN_MEETING_BRIEF.md` (≤ 350 words) and `ioan_gallery/` (the 30 native images as contact sheets; labels in a separate `KEY.md`);
  - `review/` (2026-10-10 post-hoc review, no new fits): `REVIEW.md` and `REPORTING_CORRECTIONS.md`.
- **Integrity:** `pilot_manifest.json` was frozen before any fit (commit `c88f92c9`). `ATTEMPT_LEDGER.md` lists every execution. `decision.json` holds the verdict.
- **Code:**
  - `src/week19_dev_pilot.py` (P0, P1, P2);
  - `src/week19_pilot_reports.py` (descriptive table, Ioan figures and cases, pilot figures, DT audit, summary);
  - `src/week19_pilot_review.py` (review decomposition, late-negative isolation, same-cohort oracle check, gallery, checks; reads saved outputs only);
  - tests in `src/tests/test_week19_dev_pilot.py` and `src/tests/test_week19_pilot_review.py`.
- **Reproduce:**
  ```
  python -m src.week19_dev_pilot p0
  python -m src.week19_dev_pilot p1
  python -m src.week19_dev_pilot p2
  python -m src.week19_pilot_reports all
  python -m src.week19_pilot_review all
  ```
  Requirements:
  - **Committed:** the Week 19 audit tables.
  - **Local, not committed:**
    - the Week 18 phase 2 cache `outputs/week18_independent_research/phase2/cache_real/`, for the q20 equality check;
    - the raw cache `data/raw/sph_v2/` and `outputs/week19_temporal_regime_audit/_cache/frames.pkl`, for the figures.
  - **Network:** the image-link check queries the Hugging Face metadata API at the pinned revision.
- **Not done:** P3 (temporal follow-up), the morphology fallback, any C3 repeat, any label or exclusion change.

**Units:** depth µm, time ms (monitor time from `iter.dat` → `time.dat`), LS radius m, P W, VX m/s, ST K.

**Counts in `metrics.csv`:**
- `n_unique_simulations`, `n_positive` and `n_negative` count simulations;
- `n_available` and `n_missing` count held-out predictions (simulation × repeat).
