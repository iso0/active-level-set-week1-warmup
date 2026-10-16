# Paid-output and integration contract

The selector receives only four publicly known features, previously paid indices,
and posterior moments from a model fitted to paid observations. Its constructor
cannot receive island, fast-scan, short-K, q20, frame-level or held-out-label masks.
`synthetic.py` belongs to the **oracle/evaluator**, not to the policy. Module
separation is an auditable software contract, not an operating-system security sandbox.

## Direct callable interface

```python
from discovery import SurpriseLocalDiscovery, Predictions, Observation, Config

policy = SurpriseLocalDiscovery(
    X_pool_scaled_to_unit_bounds, paid_indices=startup_indices,
    seed=global_order_seed, mode="surprise", config=Config(threshold=frozen_level)
)
# Refit the SAME scalar model used by controls, with PAID valid observations only.
pre = Predictions(
    model_id=paid_data_and_model_hash, paid_count=len(paid_indices),
    mean=posterior_mean_over_candidates,
    latent_sd=posterior_latent_sd_over_candidates,
    noise_sd=predictive_observation_noise_sd_over_candidates,
)
choice = policy.ask(pre)   # immutable snapshot/hash stored BEFORE paying
# Execute/pay exactly choice.index, then validate this run's monitor.
event = policy.tell(Observation(
    index=choice.index, value=paid_primary_scalar_or_None,
    quality_ok=monitor_quality_ok, quality_note=recorded_quality_reason,
    canonical_label=paid_recorded_label_or_None,
))
# Always add the index to the paid ledger. Add a scalar training row only if valid.
# Keep the original canonical label and the raw monitor/QC record separately.
```

`ask` refuses a stale paid count, nonfinite moments, negative uncertainties,
duplicate pending queries and invalid feature coordinates. `tell` refuses an
index different from the pending query. It copies the posterior arrays; changing
the caller's lists after `ask` cannot change the trigger or reference. The model
ID must hash paid-data identity, hyperparameters/transform and the model version;
the policy checks the count but cannot independently verify a dishonest adapter.

The scalar must have the same transformation and units as the saved moments.
Examples are log1p(melt KE in nJ) or a standardized temperature summary. Changing
transform, domain bounds, uncertainty convention, primary channel or scalar level
requires a prospective integration specification. The synthetic level zero is
**not** a physical Keyhole threshold. This prototype does not replace E1's
paid-pair logistic calibration or claim that a monitor level equals morphology.

The G3 comparator in the thesis remains a GP classifier from (P,VX,LS,ST), with
margin acquisition. ACTIVE E1 predicts log active-max depth from these four inputs,
learns u from paid depth–label pairs, and uses a depth-posterior level probability
and straddle. A new run's true depth is not an input to either x-only predictor.
Our toy `margin` is a regression-posterior control, not a re-run of G3 or C3.

## Quality, cost and availability

The paid contract is one run's canonical recorded label plus declared monitor
outputs, availability and QA metadata. Every attempted/purchased simulation counts
even when a monitor is missing or broken. Store nonfinite counts, outlier counts,
row-count mismatch, observed/planned support, units and source revision. A failed
primary channel cannot trigger a discovery episode or become a finite fabricated
regression target. Its label is retained; it is not removed from classification
evaluation. Store raw extreme values outside the selector, not only the filtered
summary. QA plausibility limits must come from declared semantics/solver evidence,
not a held-out label or desired AUC. Correlated undetected faults remain possible.

For a non-Gaussian physical posterior, a calibrated predictive tail check may be a
better later trigger; the current standardized residual is explicitly an
approximation and does not imply a universal 2.5-SD false-alarm rate. A fitted
nugget is effective unresolved variation, not established simulator noise.

`monitor_support.time_summary` accepts explicit physical seconds, a planned
active horizon, actual observed support, a validity mask and an explicit maximum
gap. It clips to the observed window and reports missing duration. Its
piecewise-linear rule is a **new support helper**, not a silent replacement of
Opus's previously frozen row-hold summaries. The choice between hold and linear
interpolation must be named in the next protocol.

## Auxiliary outputs and evaluator restrictions

Only paid simulations train auxiliary models. A prediction of a monitor at unpaid
x is a function of x and paid data, not a free extra measurement. Downstream
Keyhole transfer needs cross-fitted training predictions or a coherent joint
model with propagated uncertainty. True held-out/unpaid monitors must never be
concatenated to x. A separately observed in-situ monitor defines a different
oracle and cannot substantiate pre-simulation query savings.

The evaluator alone owns complete synthetic truth, the detached-island mask,
boundary-band mask, unpurchased outputs and the independent evaluation cloud.
For a later real Keyhole study it alone owns short-K/q20 memberships and held-out
labels. Report BA, each recall, short-K numerator/denominator, q20, AUC/proper
scores/calibration and cost there; no q30 or relabeling. Whole-pool or random
re-split NEW results remain DEV, not new independent evidence. C3's completed
decision is preserved; this package consumes neither C4 nor real Stage A.
