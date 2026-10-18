# Existing work and one focused numerical-contract finding

Review date: **17 October 2026**. Paths in the table are relative to Opus's
`outputs/joint_depth_label_development/`. His source/results were read only.

## Avoiding duplicated experiments

| Existing protocol | Already addressed there | Distinct scope of this package |
|---|---|---|
| `surprise_discovery/SURPRISE_PROTOCOL.md` | 2D islands, planted/unplanted starts; improbable paid binary label seeds a FIFO queue of nearest-neighbor probes | 4D scalar surprise; frozen before-anchor corroboration; finite non-renewable episode; calibration/QA guard; same-schedule episode ablation |
| `phys_discovery/PHYS_DISCOVERY_PROTOCOL.md` | Continuous velocity-ratio surprise, MAXVAR plus nearest neighbors, local re-seeding; evaluator top-decile family AUDC | Evaluator geometric region/boundary, not a response-decile family; bounded straddle episode with fixed global exploration quota |
| `phys_al/PHYS_AL_PROTOCOL.md` | Several scalar physical targets; random/maximin/MAXVAR/IVR/multi-output acquisition | No duplicate fits. A synthetic two-output variance extension is only a mechanism check; duration-weighted active KE is a possible different future target |
| `temporal_vel/` and `temporal_struct/` protocols | 40-bin velocity/KE/depth curves; mean, separable kernel, PCA, full 5D and scalar controls | A proposed temperature channel, physical-duration support and native peak evaluation; no invented novelty for a product kernel |

The new prototype is a limited adaptation, not a demonstrated superior successor.
CA-SMART already has close surprise/local/global prior art (references in DESIGN).
The most useful comparison isolates the local episode from the added global
coverage schedule. If it collects more island points without learning the boundary
better, it has demonstrated local collection, not resolved boundary estimation.

## Exposure and implementation chronology

`METHOD_CHOICE_RECORD.json`, timestamp 2026-10-17T07:23:37Z, records the selected
algorithm/generator code before reading the newly added study protocols. Reading
commit metadata for `6fe4e9d439a8bf5bacdcd42e3b28fba58786bea3` then unexpectedly
displayed aggregate PHYS_AL, PHYS_DISCOVERY and TEMPORAL_STRUCT results in its body.
Their outcome tables were not opened for method selection. This is **incidental
outcome exposure**, not a fully blinded review; those summaries were not
independently audited and are not presented here as new evidence.

After that exposure, the selector, synthetic world, priors, thresholds and budget
were left unchanged. Source review found two runner issues: an undefined `m` in
the model-identity hash (replaced by the function argument `manifest`), and unclear
failure on a null reservation list (now a clear refusal). A dummy-model
bookkeeping/resume check was added. A separate explicit variance-convention helper
and hand checks were added for the source finding below. These are pre-execution
wiring/contract repairs, not score-based numerical settings or method tuning.

## Demonstrated source-level finding: predictive noise counted twice

`src/jdl_phys_al.py:178-184` constructs scikit-learn GPR with
`ConstantKernel * Matern + WhiteKernel`, with `normalize_y=True`.
`src/jdl_phys_discovery.py:92-93` obtains `s` with `predict(return_std=True)`, then
computes `z=(y-m)/sqrt(s*s+noise)`, where noise is the fitted WhiteKernel variance
restored with the squared training-output scale.

For this additive kernel, the GPR predictive diagonal already includes WhiteKernel
variance. It subtracts the conditioning term and restores output units before
returning SD. WhiteKernel's cross-covariance is zero for distinct prediction/training
arguments, and its predictive diagonal is its noise level. This is confirmed in
the locally installed `_gpr.py` and `kernels.py` recorded in SOURCE_SNAPSHOT, and
the [official GPR source](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/gaussian_process/_gpr.py)
and [WhiteKernel definition](https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.kernels.WhiteKernel.html)
(accessed 17 October 2026).

The installed-source snapshot is from the thesis venv, not a verified environment
capture from Opus's already completed worker. The public API behavior and his
source establish this contract issue; an executed historical worker check remains
separate from the source audit.

Writing v_f for latent conditional variance and v_e for noise, the intended
predictive residual uses sqrt(v_f+v_e); that code uses sqrt(v_f+2v_e). Its absolute
z is multiplied by sqrt((v_f+v_e)/(v_f+2v_e)), between 1/sqrt(2) and 1. This can
suppress a trigger, never increase it at the same saved state. The historical
effect on paths, model learning or final rankings is **unknown**.

Hand counterexample: residual 3.8, v_f=1, v_e=1 gives correct z=2.687 versus
double-counted z=2.194, on opposite sides of the declared 2.5 trigger. This
arithmetic example is implemented/tested in `variance_contract.py`; it is not a
fitted example or an estimate of the frequency of the bug in real data.

The convention is model-specific: training-only `alpha` regularization is not
automatically predictive test noise. Our `FixedGP.predict` returns latent SD and
therefore legitimately adds its explicit .08 observation SD for residual checks.

## Falsifiable effect hypothesis, cheap check and stopping condition

**Hypothesis:** double-counting materially suppressed local episodes because a
nontrivial share of valid paid surprises fell near the 2.5 threshold and had
non-negligible fitted noise. This is separate from the primary local-discovery
mechanism and is the one additional issue pursued here.

First inspect existing saved pre-query means, predictive SDs and noise variances
if available; compute both z values on the **same historical paid observations**
and count changed trigger decisions, stratified by noise/predictive-variance ratio.
No selector replay or new model fit is necessary for such complete cached moments.
The reviewed `sd_log` stores z/event/ID but omits these moments, so it is insufficient
by itself; no invented reconstruction from final models is valid. If moments are
unavailable, Opus may validate the adapter on one reserved fixed-model numerical
reference; that checks semantics, not historical causation. Astra launched none.

**Stop** the historical-impact claim if the needed states are unavailable. If
complete cached states show no trigger changes (or noise is negligible), stop this
explanation for the failed historical endpoint. If changes exist, preserve the
old result and document a prospective corrected comparison; a trigger difference
alone does not establish improved acquisition or justify a rescue sweep.
