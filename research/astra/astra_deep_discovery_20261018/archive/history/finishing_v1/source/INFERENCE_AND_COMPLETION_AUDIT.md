# Inference and completion checks, without changing the frozen experiment

Added 19 October 2026 before inspecting v2 scientific outcomes. Main TEST is
already running. No loss, candidate, model, seed, comparison or numerical setting
is chosen here. This supplements the original analysis, preserving its output.

The 24 independent realizations per family are the replication units. Adaptive
readouts, the multiple arms on one world, and the fixed-share reruns are not new
independent worlds. Stratified paired bootstrap intervals are approximate sampling
intervals for these specified generator families; they are not distribution-free
or external SPH uncertainty. The four primary endpoint p-values use paired sign
flips. Their exact randomization interpretation requires exchangeability of the
paired differences under the null (or a suitable symmetry assumption); algorithm
identities were not experimentally randomized. A zero mean alone is insufficient.
Holm correction addresses four primary comparisons, not that assumption.

Keep the original p-values and registered pass flags, but disclose this limitation
in the final scientific judgment. Family and other-metric intervals, including
the many descriptive query-burden comparisons, are pointwise rather than a
simultaneous confidence guarantee. The frozen query-savings flag requires both
arms to attain the full unchanged target in at least 80% of worlds and a negative
upper paired interval for burden difference. Passing that operational criterion
does not resolve unadjusted selection across secondary comparisons. Always show
attainment, horizon/censoring and fixed-budget errors beside query counts.

RANDOM/MAXIMIN model contrasts require identical FULL query paths, not merely
the same startup. `completion_integrity.py` checks this for every paired v2 world
and also verifies all unit IDs, terminal budgets, pre-query hash presence, matched
world identities and fixed-share local/global expenditure. The original replay
provides a separate, stronger numerical check on selected complete pre-query
states. An overall zero path-error count cannot substitute for that replay.

`completion_audits.ps1` waits until the already registered postprocessing pipeline
finishes, then runs the exact finite decision example, the already frozen six-
prefix mixture quadrature audit, and the full-path integrity checks. It acquires
no extra numerical capacity: each Python process claims one Astra slot, with
BLAS limited to one, before numerical work. It obeys the original deadline.

Additional budget: zero new controlled experiment trajectories; six controlled
fit requests/72 component solves already reserved prospectively by the earlier
acquisition-audit plan; four finite analytic cases (128 prior atoms, at most 4000
recursion nodes) and a read-only traversal of registered artifacts. No GP fits
for the analytic or file-integrity checks. These stay inside the existing total
700000-request/6000000-component envelope. Failed diagnostics are retained and
never silently retried or counted as successful science. A failed numerical
reference may limit an approximation claim without erasing completed experiments.

`resume_remaining.ps1` is the new complete idempotent recovery entry. It calls the
existing unchanged `resume_all.ps1`, then starts this final observer if needed.
Main/postprocess sources remain byte-identical to their frozen manifests.
The observer's completion means records are ready for scientific and visual
review, not that the research hypothesis succeeded or the handoff is finished.
