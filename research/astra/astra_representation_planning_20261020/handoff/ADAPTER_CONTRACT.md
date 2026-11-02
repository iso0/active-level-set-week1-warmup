# Posterior-agnostic integration contract

This is a local review package, not an instruction to replace Opus's physical
posterior or run real-data Stage A. The eligible physical application is one
archive-free 541-run pool. Public inputs are P, VX, LS, ST. No OLD/NEW routing,
free 405-output archive, global label count, short-K/q20 mask or unpaid monitor
may enter an ask call. One paid ID returns every available output together.
Missing channels retain their cost and other usable outputs.

The tested objective here is **uniform latent-monitor sign error at zero**.
It is not canonical recorded-Keyhole balanced accuracy or a physical regime
oracle. Integrating a different loss, threshold or joint-output lookahead needs
its own numerical reference and prospective application protocol.

The core API is `planner.plan(GaussianState, horizon, ...)`. The caller supplies:

- Reference latent means and variances on its frozen target-distribution cloud.
- Candidate latent means and FULL candidate latent covariance on a common
  shortlist, plus reference-by-candidate latent cross covariance.
- Independent observation-noise variance for the paid scalar channel; do not
  include it in latent variance and add it a second time. Correlated observation
  errors or joint outputs need an extended covariance contract.
- Paid-only availability probability, posterior source hash and candidate IDs.
- Remaining paid-query budget, numerical tolerances, and any forced second
  exploration priorities fixed by the acquisition schedule.

`GaussianState` is a working Gaussian approximation, which may come from a
stronger backend than the fixed bank. Mixture means/covariances must include
within- and between-component uncertainty. Gaussian lookahead does not update
future mixture weights; actual Bayesian model averaging at the next real
observation does not remove that approximation. The separate tested mixture-h1
control retains future component learning and has its own saved numerical
diagnostics. The published tiny counterexample changes its preferred one-step
action under the Gaussian approximation.

`adapter.py` provides a pending-ticket ask/tell wrapper. The external backend
owns actual posterior updates; this wrapper never fits or secretly reads a
future value. It stores all outputs and quality fields but the supplied state
values one scalar primary channel. Retaining other outputs is not evidence that
their information was used by this acquisition.

Only the first action of a two-step plan is executed. Its actual observation
updates the backend, then the caller constructs a new snapshot and replans.
Both paid queries count. Reject duplicate paid IDs and stale snapshot hashes.
Startup outcomes enter the posterior once; no invented pre-start surprise is
required. The local compact model is a fixed additive prior whose posterior
representers use all paid inputs, including startup.

Numerics: h1 is analytic for the working Gaussian; h2 uses GH9/17/33/65,
score resolution 5e-5 and ordinary tie tolerance 2e-5. Record unaccepted
refinements, the finite-resolution set, tie fallbacks and cost. The bounded
selection rule is not an exact-posterior or globally optimal planning guarantee.
The implementation and standalone checks require Python, NumPy and SciPy;
analysis/plots additionally require Matplotlib and psutil for resource records.

Do not integrate automatically from a favorable mean. Inspect matched model/
horizon effects, the mixture-aware h1 control, learned ARD and full-pool
straddle, both recalls and regional harms, equal-compute results, numerical
replay and censoring. All application fits remain unperformed in this campaign.
