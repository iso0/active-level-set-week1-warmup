# Execution repair 01 — 18 October 2026, before controlled outcomes

The first numerical reference FAILED before any GP fit or controlled world ran.
The Gaussian SUR formula was not rejected: the independent integration routine
split an infinite domain at -a/rho, which can be -100; adaptive quadrature then
missed the central Gaussian mass. Maximum discrepancy was 0.1586552539.

A bounded diagnostic, under Astra's registered one-thread slot, used [-12,12],
split at both zero and the decision kink. Its omitted-tail bound is 2 Phi(-12).
An independent integral of the correlation derivative agreed to 1.27e-14 over
20 fixtures. All rows and the failed original attempt remain in results/.
This repairs the reference, not the selector, model, target, seeds or tolerance.
No numerical setting was selected using a scientific performance score.

Version v1.1 uses the repaired reference and an explicit active-manifest pointer
so later execution/scientific versions can be recorded without overwriting their
frozen manifests. Original v1 sources remain in Git commit 4f3e2c3; its manifest
remains unchanged. Unexecuted old queue units are marked SUPERSEDED, not erased;
the failed reference retains FAILED. New units use prefix v1_1 and the same
unexposed seed lists. Counts and the absolute deadline are unchanged. The
20-case diagnostic uses no GP fits; no reserved requests have been refunded.

The background supervisor persisted through the inactive chat interval and
correctly waited on failed numerical acceptance. This consumed wall budget;
it does not reset the 48-hour clock. Future phase review remains autonomous.
