# Frozen external validation protocol

Status: **FROZEN CORE; DATASET-SPECIFIC INSTANTIATION PENDING LABEL-FREE INTAKE**.

The methods, endpoints, comparisons, information barriers, and decision rules below are frozen. Exact batch identity, technical exclusions, split/repeat seeds, and feasible budget grid cannot be truthfully instantiated before the new immutable manifest exists. They must be sealed in a machine-readable addendum committed before any label file is opened. This is a completion step, not permission to tune the method.

## Step 0 — receipt and custody

Receive two physically/logically separate objects:

1. a label-free immutable manifest with stable simulation IDs/configuration tokens and `[P,VX,LS,ST]`;
2. a sealed label oracle containing `has_keyhole` that method-side investigators do not inspect.

Record SHA-256, byte size, delivery time, source, simulator/version metadata, and access controls. Do not compute on the label file before the pre-label freeze is committed.

## Step 1 — label-free eligibility audit

- Prove the batch is not the old 407 campaign, the OLD-405 analysis population, or a subset/copy/renaming of either.
- Check IDs, configuration tokens, exact/near input duplicates, schema, missingness, units, ranges, and simulator/domain changes using manifest/input fields only.
- Apply only technical exclusions defined without labels, and record every excluded ID and reason.
- Stop if independence/provenance cannot be established.

## Step 2 — pre-label instantiation

Commit an immutable JSON record containing the accepted-manifest hash, exclusions, usable count, grouping rule, outer split algorithm, number of repeat blocks, five-fold pairing, seed namespace, exact feasible integer budgets, environment, code hashes, failure handling, and all output paths.

Default target horizon is B16-B80. If every outer training pool cannot support B80, stop before labels and obtain a documented owner decision either to defer the test or to approve a pre-label amendment. Never shorten the horizon after seeing labels or outcomes.

## Step 3 — locked arms

Run paired paths on identical outer splits:

- Control: `M3_margin_incumbent` with frozen B16 initialization.
- Challenger: `early8__coverage_then_margin_B40`.
- Attribution control: `coverage_then_margin_B40` with the control's B16 initialization.

The M3 evaluator is identical for all arms. Historical Binary-A0 is not the live control and is not required as an external arm.

## Step 4 — information barrier and execution

- A selector receives training-pool input features, its own queried indices, and labels only after selection.
- Held-out labels, unqueried labels, q20/q30 membership, opposite-class distances, and auxiliary hidden targets remain inaccessible.
- Generate the paired outer split objects using the committed algorithm/seed only after the protocol is sealed; label use required for stratification/evaluation occurs inside the controlled evaluation layer, not method selection.
- Fit M3 and choose one query at every integer budget. Preserve per-budget probabilities, paths, fit diagnostics, failures/fallbacks, and environment metadata.

## Step 5 — endpoints and inference

Primary contrast: challenger minus control on q20 accuracy AULC B16-B80.

Mandatory attribution contrast: same-B16 attribution control minus control on that same endpoint. This determines whether a successful composite policy can additionally support a pure acquisition statement.

Use paired repeat-block differences after averaging the five folds. Report the mean, a two-sided 95% paired repeat-block interval, the number of positive repeat blocks, and all failures. Report separately:

- q20 accuracy AULC B16-B40;
- q20 balanced-accuracy AULC B16-B80 and B16-B40;
- q30 counterparts;
- q20 Keyhole-recall AULC and B40 recall;
- full-test accuracy AULC and B80 accuracy;
- descriptive first-crossing/sample-efficiency summaries, without guaranteed-savings language.

## Step 6 — frozen decisions

- **External confirmation:** primary mean is positive, its 95% paired repeat-block interval is entirely above zero, B40 q20 Keyhole-recall change is at least `-0.03`, and B80 full-test accuracy change is at least `-0.01`.
- **Incumbent replacement:** external confirmation passes and the primary mean is at least `+0.01` AULC.
- **Pure acquisition claim:** in addition, the same-B16 attribution contrast must have a positive mean and 95% interval entirely above zero. Otherwise any benefit is attributed only to the composite policy.
- A positive mean alone is insufficient. Failure to obtain an eligible batch is “validation not run,” not method failure.

## Required outputs

The future run must preserve the label-free intake report, frozen instantiation JSON and hash, split manifest, path manifest, per-budget metrics, repeat-block contrasts, guardrails, fit diagnostics, run manifest, validation report, and final claim ledger. No current file contains or derives from the genuinely new batch.
