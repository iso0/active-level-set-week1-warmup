# Bounded development and numerical gate — recorded before the first new GP fit

This version fixes one additive local proposal: null probability 0.5, compact
support R=0.45 or 0.9 each probability 0.25, local SD 0.6. These are three
interpretable covariance alternatives, not a residual/threshold sweep. The
background is exactly the old scalar structure bank (12 components); the local
bank has 36. Values select posterior weights, not new prior support locations.

Numerical work first validates the dense latent/noise contract, PSD, additive
posterior decomposition, shrinkage toward the null, startup influence, Gaussian
one-step and contingent two-step calculations, and an exact finite investment
example. Initial GH orders are 9/17/33, score tolerance 0.0005, tie tolerance
0.00002, with order 65 reserved for independent fixtures. Failure of a numerical
identity stops dependent execution; a documented repair retains the failed attempt.
A numerical setting may be selected by reference error, rank/tie stability and
CPU, never by a held-out scientific outcome.

Initial pilot: the 10 mechanism families smooth, coordinate anisotropy, rotated
anisotropy, local scale, small/large island, heteroskedastic, heavy tail, null and
correlated corruption; seeds beginning 720201 are DEVELOPMENT. Additional missing
primary output is an observation-contract control. The exact pilot unit list,
candidate/reference sizes and budget are recorded before launch. At most 40
development trajectories, B32 initially, may estimate timing and diagnose code/
representation. No new TEST world is read until source, generator, primary
contrasts, seeds, tolerances, arms, horizon and run size have a hash-pinned freeze.

The learned ARD comparator optimizes four lengths, amplitude and noise. Bounds:
lengths [0.015,5], amplitude SD [0.03,3], noise SD [0.015,0.6]. It uses all seven
isotropic/coordinate-short starting length vectors at both noise starts on every
four-query refresh, plus its previous solution. L-BFGS-B maxiter 120, ftol 1e-9,
gtol 1e-5. Optimizer failures and chosen solution status are retained. Between
refreshes the fitted hyperparameters stay fixed but the posterior conditions on
every newly paid observation. This schedule is a practical learned baseline, not
full integration over ARD hyperparameters; its CPU is charged.

The pilot determines a useful balanced TEST size inside the 24-hour/two-thread
envelope. No efficacy effect size is predicted. Whole-world contrasts, uncertainty
and all difficult-region harms will be retained. The prior TEST is exposed DEV.
There is at most one later alternative mechanism; it requires a prospective note
and independent evaluation, not relabelling development as TEST.
