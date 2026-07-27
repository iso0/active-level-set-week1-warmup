# Phase 2 runtime metadata correction

## Finding

The Phase 2 field `full_pipeline_runtime_seconds` contains
`11.208154400025` seconds. The timer itself is real,
but the field name is too broad.

The value was created inside `run_full_pipeline`: the timer starts at function
entry and stops after figures and validation, immediately before reporting
files are written. File timestamps show that all
`12` GP checkpoints predate the
configuration timestamp for the timed invocation. Therefore the 11.2-second
invocation loaded cached bootstrap and LOO artifacts; it did not perform the
original expensive bootstrap or GP fits.

## Corrected name

The authoritative name is:

`cached_artifact_assembly_figure_and_validation_runtime_seconds`

The historical JSON value is preserved and marked deprecated rather than
replaced with a guessed end-to-end duration.

## Included

- Phase 1 verification
- cached uncertainty and checkpoint loading
- metric, paired, preference, and stable-sensitivity assembly
- figure generation
- validation

## Excluded

- original moving-block bootstrap
- original 241-simulation GP fits
- original stable-only GP fits
- reporting writes after the timer stop
- notebook execution

## Separately measured evidence

- Phase 2 smoke test:
  `4.719590` seconds.
- Target-summary bootstrap invocation:
  `131.802150`
  seconds.
- Primary 241-LOO aggregate fold durations:
  `1832.220684` seconds.
- Stable-only aggregate fold durations:
  `555.957606` seconds.

The fold-duration sums overlap because four workers ran folds concurrently.
They are measured diagnostic totals, not end-to-end wall-clock durations.
No unavailable duration is inferred or reported as measured.
