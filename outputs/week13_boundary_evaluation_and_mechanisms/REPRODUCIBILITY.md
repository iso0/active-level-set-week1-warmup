# Week 13 reproduction

Runtime: the repository `.venv` (Python 3.14, scikit-learn 1.9.0, numpy 2.4.6, pandas 2.3.3, scipy 1.17.1).

```bash
.venv/Scripts/python.exe -m src.week13_real_diagnostics          # real_data/ (extracts the Week 8.5 per-budget table from its tarball to a temp dir)
.venv/Scripts/python.exe -m src.week13_discovery_and_anchoring    # theory_checks/
.venv/Scripts/python.exe -m src.week13_level_shift                # real_data/level_shift_summary.json
.venv/Scripts/python.exe -W ignore -m src.week13_synthetic_al --jobs 7   # ~53 min on 7 cores; writes synthetic/paths/*.parquet
.venv/Scripts/python.exe -W ignore -m src.week13_synthetic_analysis      # consolidated into synthetic/all_paths.parquet after the run
.venv/Scripts/python.exe -W ignore -m src.week13_synthetic_analysis --displaced
.venv/Scripts/python.exe -W ignore -m src.week13_synthetic_transfer --jobs 5
.venv/Scripts/python.exe -m src.week13_figures
.venv/Scripts/python.exe -m pytest -q src/tests/test_week13_propositions.py
```

The 2,880 per-path parquet files were concatenated without modification into `synthetic/all_paths.parquet`
(211,680 rows); `week13_synthetic_analysis` reads that file when present. All seeds are deterministic
functions of (scenario, sigma, pool size, replicate, policy).
