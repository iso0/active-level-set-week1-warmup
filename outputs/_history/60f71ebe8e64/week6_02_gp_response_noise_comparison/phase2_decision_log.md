# Week 6 Phase 2 decision log

## Fixed scientific scope

Matérn 3/2 is fixed because this phase asks whether observation treatment changes
predictive behavior when the covariance family is held constant. Comparing RBF,
Matérn 5/2, ARD, or other kernels here would confound that question. Kernel-family
comparison, feature-effect analysis, active learning, and level-set estimation remain
deferred.

## Meaning of the three treatments

- **Approach A** treats the selected deterministic target as exact and adds only
  `alpha=1e-6` in normalized units for numerical stability. This is jitter, not noise.
- **Approach B** learns a homoskedastic WhiteKernel effective nugget. It may absorb
  target-summary variability, unresolved inputs, fixed-kernel misspecification, and
  model discrepancy. It is not evidence that the simulator itself is stochastic.
- **Approach C** uses simulation- and response-specific moving-block-bootstrap
  variances of the selected-window median. These are target-summary uncertainty
  proxies, transformed fold-locally into normalized alpha values.

## Limitations of the target-summary uncertainty proxy

The proxy describes temporal stability of a median within an already simulated
window. It does not measure experimental error, numerical discretization error,
between-run simulator randomness, or uncertainty for an unseen simulation. Its
retrospective oracle interval uses the held-out simulation's own bootstrap variance
and therefore is not deployable before that simulation has been run.

## Preferred treatments

- **width:** `B_learned_nugget` — robust paired-RMSE advantage.
- **length:** `B_learned_nugget` — robust paired-RMSE advantage.
- **depth:** `C_heteroskedastic` — numerical preference; paired uncertainty overlaps zero.

Point prediction is the first selection criterion. NLPD and coverage, optimization
stability, scientific interpretation, and cost are secondary. A numerical winner is
not described as superior when paired bootstrap intervals include zero.

## Remaining work

Later work may study feature effects only after accepting the predictive treatment.
Active learning and level-set estimation have not started.

## Rebuild command

From the isolated Week 6 repository root:

```powershell
.\.venv\Scripts\python.exe src\week6_phase2_gp_response_noise_comparison.py --full --force --workers 4
```

Without `--force`, valid per-target/per-method checkpoints are reused.



## Phase 2.5 addendum — matched stable-depth B/C closure

Phase 2.5 reran only penetration-depth Methods B and C on the same 230 stable
simulation IDs with identical fold ordering, fold-local scaling, seed logic,
kernel bounds, optimizer, and restart count. Historical Phase 2 results above
remain unchanged.

Decision: **B is preferred for stable-window penetration depth.**

`MAE_C − MAE_B = +0.274396 µm`
(95% paired-bootstrap CI
`[+0.134941,
+0.422091]`);
`RMSE_C − RMSE_B = +0.284855 µm`
(CI `[+0.048306,
+0.549011]`).

Runtime metadata correction: the historical `full_pipeline_runtime_seconds`
value is preserved but deprecated. It measured a cached pre-report invocation,
not the original end-to-end experiment. Its authoritative descriptive name is
`cached_artifact_assembly_figure_and_validation_runtime_seconds`. Full provenance is in
`outputs/week6_02_5_depth_model_closure/runtime_provenance.json`.

Phase 3, feature-effect analysis, active learning, and level-set estimation
remain deferred.
