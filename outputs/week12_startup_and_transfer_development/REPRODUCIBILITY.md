# Reproduction and evidence map

All scientific results here are post-hoc development or exploratory analyses.
The Week 11 external attempt remains closed. `ST` is substrate temperature.

## Runtime and inputs

Use the repository `.venv/Scripts/python.exe`: Python 3.14.4, NumPy 2.4.6,
pandas 2.3.3, SciPy 1.17.1, scikit-learn 1.9.0, threadpoolctl 3.6.0. This
matches the recorded Week 11 runtime. The system Python environment differs.
The exact manifest, truth-source and frozen-split hashes are in
`audit/input_provenance.json`; 387 protected file hashes are in
`audit/protected_hashes.json`.

The included truth mapping reads only `sim_id,truth` from the already-open
Week 11 predictions. It does not read their probabilities or evaluate the
completed subset. No sealed oracle or withheld outcome is needed.

## Ordered execution

The commands below describe the executed pipeline. Reproduction should use a
separate working copy/output archive so that published result files are retained.
The initial audit intentionally refuses to overwrite an existing snapshot.

```powershell
.\.venv\Scripts\python.exe -m src.week12_development_common
.\.venv\Scripts\python.exe -m src.week12_startup --mode diagnosis
.\.venv\Scripts\python.exe -m src.week12_startup --mode benchmark
.\.venv\Scripts\python.exe -m src.week12_models --mode transfer
.\.venv\Scripts\python.exe -m src.week12_models --mode new-only
.\.venv\Scripts\python.exe -m src.week12_active_learning run --workers 4
.\.venv\Scripts\python.exe -m src.week12_active_learning summarize
.\.venv\Scripts\python.exe -m src.week12_reporting startup
.\.venv\Scripts\python.exe -m src.week12_reporting models
.\.venv\Scripts\python.exe -m src.week12_reporting transfer
.\.venv\Scripts\python.exe -m src.week12_reporting active
.\.venv\Scripts\python.exe -m pytest -q src/tests/test_week12_startup.py src/tests/test_week12_models.py src/tests/test_week12_active_learning.py
.\.venv\Scripts\python.exe -m src.week12_validate
```

The developmental acquisition configuration was committed before execution at
`064e854b`. It must be present before running that lane. The runner checks
configuration and source hashes before reusing its own complete checkpoints;
it never reads the original frozen performance checkpoints. Do not edit code
mid-run. Failed developmental paths remain explicit failures.

## Source versions

- Initial scope and input audit: `ff600d2d`.
- Mechanistic diagnosis: `4f660103`; this commit contains the exact diagnostic
  source before subsequent startup-rule implementation.
- Corrected four-rule startup benchmark and final model runner: `1b9e215c`.
- Complete acquisition configuration: `064e854b`.
- Separated model results: `31943fab`.
- Completed acquisition paths and reporting source: `e0f0c849`.

The superseded startup implementation selected the low physics stratum until
exhaustion rather than cycling through all three strata. All erroneous outputs
are retained in `startup/benchmark_implementation_error_v0/`. Its original
source is archived there and matches the original recorded SHA-256
`d9b9816ff5c4d394ee86cb1e10942a279c218643d268da847c7bed5fad9452ec`.
Those results are excluded from scientific conclusions. The corrected rule
uses the originally intended round-robin schedule; no parameter was selected
based on which version performed better.

## Statistical conventions

- All 100 original feature-only folds are reused as paired developmental
  partitions, with new model fits and query paths.
- Original q20 construction is retained exactly. Its truth-dependent mask is
  evaluator-only. It is a finite-pool empirical boundary proxy.
- Nine test folds and 13 q20 subsets have only one class. Undefined class
  metrics are null, never zero. No such fold is discarded from accuracy.
- Full five-fold OOF predictions are pooled within each repeat for secondary
  class-sensitive metrics; repeat spread is partition sensitivity on one
  campaign, not uncertainty from 20 independent campaigns.
- Transfer bootstrap draws resample fixed predictions within each observed
  class. They do not account for OLD training uncertainty or future campaigns.
- Every discovery and refinement query contributes to total budget. During
  prescribed unfinished startup, the predictor is an explicit Beta(1,1)
  observed-prevalence baseline; no one-class GP is fit. B8-B80 is secondary
  because the historical endpoint begins at B16.
- Active-learning execution completed 800 paths with no fallback or failed
  path. There are 950 nonconverged optimizer records among 55,230 per-arm
  records; identical prefix fits may occur in multiple arms. These flags
  remain in the raw diagnostics and are not silently excluded.
- The all-Keyhole primary reference uses equal-fold q20 aggregation, matching
  the primary endpoint, and equals .6850. Pooled class-sensitive metrics are
  explicitly secondary.
- Run the final validator after all reporting edits to refresh the artifact
  manifest. It checks integrity and structural correctness, not scientific
  generalization or convergence of every optimizer invocation.

## Historical test limitations

The broader Phase1.13/1.14 check yielded 16 passing historical implementation
checks and four failures in old archive/branch assumptions. Two tests compare
the unified tree with an old branch baseline; two require sensitivity files
already absent at the starting `d8fa330c` commit. These are documented in
`audit/historical_test_limitations.json`; historical artifacts were not repaired
or rewritten. The Week 12 suite is checked separately.

## Reading order

Use `COMPREHENSIVE_REPORT.md` for the A-N synthesis and Q1-Q12 decisions.
Then inspect `startup/diagnosis`, `startup/benchmark`, `models/transfer`,
`models/new_only`, `active_learning`, and `interpretation` for raw evidence.
The machine-readable final QC and artifact manifest record completion and
integrity. The superseded implementation archive is provenance only.
