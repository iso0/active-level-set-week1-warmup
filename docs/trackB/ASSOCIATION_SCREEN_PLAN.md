# Track B association-screen plan

## Scope

This plan screens approved observable candidates for association with a hidden state. It does not choose simulation queries, optimize Track A, or search broadly over flexible model families.

## Prerequisites before execution

1. Create a label-blinded data manifest with immutable sample IDs, provenance, units, timestamps, signal availability, and hashes.
2. Mark each signal with the inventory class and document the evidence required for experimental use.
3. Freeze the prediction time `t`, eligible prefix/window, cohort exclusions, missingness handling, group structure, and target definition.
4. Freeze train/validation/test partitions or grouped repeats before inspecting hidden labels.
5. Keep any genuinely new Ioan labels sealed until the complete protocol and executable checks are committed.

## Small, interpretable first screen

For each eligible candidate, compare:

- process-input baseline `[P, VX, LS, ST]`;
- one prespecified observable feature added to that baseline;
- an observable-only univariate ranking view for interpretation.

Use simple regularized logistic models or another single preregistered probabilistic model. Fit imputation, scaling, feature extraction thresholds, and calibration on training data only. Preserve time order: a feature available after prediction time is ineligible.

Primary evaluation should emphasize discrimination and calibration without hiding class imbalance: PR-AUC, ROC-AUC, log loss/Brier score, calibration slope/intercept, and a separately reported thresholded recall/specificity view. Effect estimates are paired against the process-only baseline with confidence intervals. Multiplicity across signals must use a prespecified correction or false-discovery control.

## Mandatory controls

- label permutation/scrambling test;
- ID and metadata leakage audit;
- future-time/prefix leakage audit;
- grouped split audit for related runs;
- missingness-only baseline and missingness-by-class report;
- sensitivity to signal resolution and preprocessing fixed without test labels;
- process-only and signal-only ablations;
- explicit separation of “association,” “incremental prediction,” and “experimental observability.”

## Stop and interpretation rules

- A null result is retained in the negative-results record.
- An internally positive result is only an internal association until tested in an independent experimental domain.
- Strong performance caused by monitor availability, future samples, simulator-only state, or a label-derived feature is a failed validity check.
- No result from this screen authorizes a new acquisition function.
- No large screen begins until the inventory, measurement definitions, hypotheses, endpoints, and multiplicity rule are frozen.

## Width as the first bounded candidate

If the measurement review supports it, the first candidate should reproduce the already defined early-prefix width feature rather than inventing a new feature family. The simulation definition, experimental image-derived definition, sampling rate, prefix, smoothing, and missingness policy must be reconciled before testing transfer.
