# Standalone read-only research handoff

Neither local correction passed its DEV expansion screen. Retain the strong
GP/margin control; do not deploy this as a better canonical Keyhole learner.
The files here are reusable reference implementations of known constructions.

Dependencies: Python3.12, NumPy2.4.6, SciPy1.17.1 (exact campaign environment in
../evidence/ENVIRONMENT_LOCK.txt). No sklearn, Opus imports, network, credentials,
automatic worker launch or files outside this directory are required.
The caller must set BLAS/OpenMP threads and claim its legitimate compute budget
**before importing** this package. In this campaign use resources.Slot.

```python
from handoff.api import PaidLocalLearner

learner = PaidLocalLearner(public_candidates_0_to_1,
                          public_reference_0_to_1, model="strong")
ticket = learner.ask(selector="margin")
# Run ONE legitimately authorized simulation and reveal its available result.
learner.tell(ticket["paid_id"], monitor_value, quality="valid", cost=1.0)
checkpoint = learner.snapshot()  # caller writes atomically
learner = PaidLocalLearner.restore(checkpoint)
```

Models: strong, compact, gated, trace_match, coherent, coherent_trace.
Selections: margin and maximin only. Pending ask is idempotent; tell must match
that unique paid ID. Every missing/numerically failed observation still costs a
query. `monitor=None, quality="missing"` records that cost and excludes its missing
value from training. Startup uses feature-only maximin until eight usable monitor
values; this missing-output behavior is a tested interface rule, not an evaluated
scientific missingness advantage. No repeat-ID resimulation contract is implied.

`canonical_label` may be recorded as a separate output, but is explicitly UNUSED
by this continuous-monitor learner. Its p is P(latent monitor>=0), not P(recorded
Keyhole). A real-data integration must preserve the canonical classifier and its
honest cross-fitting, or prospectively change the observation model. Feeding
unpaid monitors or short-K/q20 membership into this adapter is invalid.

The ticket includes paid ID, model/source hash, pre-query posterior hash, mean,
latent variance and future-observation variance. Startup tickets have no fitted
posterior and correctly use null moments. Observation variance adds learned
Gaussian noise once. WhiteKernel or other noise conventions must be converted
explicitly by any adapter; do not add a noise term to an already noisy variance.
Quality flags are supplied by the observation contract, never inferred from test
outcomes. Independent heteroscedastic noise is not modeled by this v1/v2 code.

`local_core.py` is byte-identical to the frozen v1 model source.
`coherent_core.py` extracts the frozen v2 rankone_bank function unchanged.
The remaining API enforces accounting/checkpoint behavior, and does not claim an
additional model/acquisition result. The portable checks use fixed global theta
and verify restore, missing cost, unique IDs and variance semantics. Scientific
evidence remains the original immutable campaign runner, not this wrapper.

A posterior-agnostic integration needs the continuous observation likelihood,
background prior kernel on paid/test points, paid noise covariance and evidence
conditional on hyperparameters. Classifier marginals alone cannot reconstruct
these quantities. Do not manufacture cross-covariance from marginal variances.

Opus may read/copy this directory later. No message, checkout modification, merge
or push was performed. The source/results bundle is local and hash indexed.
