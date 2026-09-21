# Track B next steps

## Before new Ioan data arrive

1. Agree with Ioan on the exact hidden state and intended inference time.
2. Complete the targeted literature review in [`LITERATURE_QUESTIONS.md`](LITERATURE_QUESTIONS.md).
3. Obtain setup-specific definitions for sensors, commanded variables, time bases, calibration, and missingness.
4. Freeze the eligible signal list; do not add features after labels are revealed.
5. Turn [`ASSOCIATION_SCREEN_PLAN.md`](ASSOCIATION_SCREEN_PLAN.md) into a dataset-specific, hashed protocol with fixed splits, endpoints, multiplicity handling, and stop rules.

## When new data arrive

1. Quarantine the batch and create a label-blind file manifest; do not inspect hidden labels.
2. Verify sample IDs, schema, units, timestamps, groups, signal definitions, and measurement provenance without computing label-conditioned summaries.
3. Classify each received field using [`SIGNAL_INVENTORY.csv`](SIGNAL_INVENTORY.csv); exclude simulator-only/hidden predictors and unresolved leakage paths.
4. Freeze the dataset-specific protocol and executable validation checks in Git before unsealing labels.
5. Run only the preregistered, bounded association screen, beginning with the process-only baseline and the approved width proof-of-concept feature if measurement equivalence has been established.
6. Report missingness, calibration, discrimination, uncertainty, negative results, and domain limitations. Keep internal association separate from experimental validation and deployment.

## Explicit non-actions

- Do not tune the Track A acquisition policy on the new batch.
- Do not reopen method search on the old 405 simulations.
- Do not infer that a simulator variable is measurable.
- Do not use future portions of a signal to make an earlier prediction.
- Do not claim external validation merely because a new file or experimental-looking variable is present.
