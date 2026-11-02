# Prospective integration refinement, before independent TEST

The existing reference fixture changed ranking with iid reference cloud size.
This is an integration-accuracy issue, not a held-out scientific score. Before
independent TEST, evaluate scrambled Sobol reference clouds at N=128,256,512,1024,
2048 against N=8192, for four predeclared scrambles (251018..251021). Use the
same analytical model fixture as the numerical check; no DEV/TEST evaluator labels
or performance metrics enter this choice. One mixture fit, four component solves,
charged to the independent-reference envelope. Maximum 24 cloud evaluations.

Select the smallest size whose maximum absolute candidate-score difference from
its corresponding 8192 reference is <=5e-4 for all four scrambles and whose
reference regret for choosing its best candidate is <=5e-4 in each. Near ties may
change winner without meaningful loss; report both. If none passes, report failure
and the cost/accuracy limit rather than tuning against scientific outcomes. A
finite high-resolution reference is not exact continuum integration.

Any adopted cloud change is a prospective numerical amendment. Preserve all v1
DEV outcomes, separate the policy RNG stream from the generator seed, and keep
the underlying function/noise realizations fixed by retaining the original 128
reference RNG draws before replacing the public integration cloud. This avoids
accidentally changing the world when changing quadrature resolution.
