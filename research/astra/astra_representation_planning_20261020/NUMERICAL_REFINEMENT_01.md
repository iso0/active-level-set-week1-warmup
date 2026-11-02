# Numerical refinement before any comparative trajectory

20 October 2026. The independent initial reference passed covariance, noise,
shrinkage, startup influence and one-step checks. The two-step fixture exposes
an exact tie between candidates 0 and 2 (independent losses agree to 8e-15), yet
GH orders 9/17/33/65 alternate their ordering. Maximum score discrepancy from
independent nested adaptive quadrature is 0.000732 at order 17, 0.000632 at 33,
and 0.000114 at 65. One adjacent refinement can look converged prematurely.

Prospective repair: use orders 9/17/33/65, require two consecutive score changes
below 0.0005 for early acceptance, and stop at 65. Inside twice the larger of
the declared tolerance and the last two observed refinement changes, retain
candidate ambiguity and choose the best one-step action within that unresolved
set (ordinary deterministic ID ties at 0.00002). This diagnostic width is not a
proved error bound. Report all fallback, near-tie and unresolved integration
frequencies. No numerical refinement is selected by classification performance.
The original successful-but-limited reference remains intact; it is not rerun.

The exact rational investment example selects a noisy direct observation
myopically (loss 1/5), but a switch observation first under two-step planning
(final loss 0 after a contingent paid second query). This establishes a possible
mechanism, not an empirical benefit of our Gaussian working planner.
