# Week 4 Experiment 09 GPC Bernoulli SUR Validation

This run validates fixed-kernel GP-classifier Bernoulli SUR refit across seeds. It does not use optimized classifier kernels.

## Run settings

- Benchmarks: `branin, hartmann4, ackley`.
- Reference size: `1500`.
- Shortlist sizes: `15, 25`.
- Total elapsed runtime: `1721.4` seconds.

## Best final methods

| Benchmark | Global | q20 | q30 |
| --- | --- | --- | --- |
| Thresholded Branin | `classifier_uncertainty_repulsion` (0.073) | `classifier_uncertainty_repulsion` (0.256) | `classifier_uncertainty_repulsion` (0.190) |
| Thresholded 4D Hartmann | `gpc_bernoulli_sur_refit_k15` (0.116) | `gpc_bernoulli_sur_refit_k25` (0.373) | `gpc_bernoulli_sur_refit_k25` (0.315) |
| Thresholded 4D Ackley | `classifier_uncertainty_repulsion` (0.178) | `classifier_entropy` (0.421) | `classifier_entropy` (0.380) |

## Answers

### Thresholded Branin
1. k15 reproduces the Week 4 Experiment 08 seed-0 signal across this run: `False`. Week 4 Experiment 08 seed-0 q20/q30 was `0.221` / `0.157`; this run gives `0.266` / `0.202`.
2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `False` / `False`.
3. k25 improves over k15 on q20/q30: `False` / `False`.
4. k40 was not run in this configuration.
5. This benchmark does not support GPC SUR as a replacement for `classifier_uncertainty_repulsion`.
6. Integrated uncertainty correlation with q20/q30 error over all curves: `0.189988` / `0.193611`.
7. k15 reduces uncertainty while worsening q20/q30 versus repulsion: `True` / `True`.
8. Runtime cost: k25 mean runtime per seed `38.5` seconds versus repulsion `2.0` seconds.

### Thresholded 4D Hartmann
1. k15 reproduces the Week 4 Experiment 08 seed-0 signal across this run: `True`. Week 4 Experiment 08 seed-0 q20/q30 was `0.365` / `0.301`; this run gives `0.375` / `0.316`.
2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `True` / `True`.
3. k25 improves over k15 on q20/q30: `True` / `True`.
4. k40 was not run in this configuration.
5. This is the benchmark where GPC SUR helps most: a SUR method is best on both q20 and q30.
6. Integrated uncertainty correlation with q20/q30 error over all curves: `0.448055` / `0.482410`.
7. k15 reduces uncertainty while worsening q20/q30 versus repulsion: `False` / `False`.
8. Runtime cost: k25 mean runtime per seed `78.8` seconds versus repulsion `11.6` seconds.

### Thresholded 4D Ackley
1. No Week 4 Experiment 08 seed-0 SUR reference row was available for this benchmark; this run gives k15 q20/q30 `0.428` / `0.385`.
2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `False` / `False`.
3. k25 improves over k15 on q20/q30: `True` / `False`.
4. k40 was not run in this configuration.
5. This optional benchmark does not support extending GPC SUR to Ackley by default.
6. Integrated uncertainty correlation with q20/q30 error over all curves: `0.372583` / `0.451087`.
7. k15 reduces uncertainty while worsening q20/q30 versus repulsion: `True` / `True`.
8. Runtime cost: k25 mean runtime per seed `81.0` seconds versus repulsion `11.5` seconds.

## Interpretation

1. k15 reproduced the promising Week 4 Experiment 08 seed-0 behavior only on Hartmann4. It did not generalize on Branin, and the optional Ackley check did not support SUR.
2. k15 beat `classifier_uncertainty_repulsion` on q20/q30 only on Hartmann4; it lost on Branin and optional Ackley.
3. k25 improved over k15 on Hartmann4 q20/q30, worsened Branin q20/q30, and was mixed on optional Ackley.
4. k40 was not run. The k15/k25 runtime was already enough to answer the validation question, and k25 was not uniformly better than k15.
5. GPC SUR helped more on Hartmann4 than on Branin. Hartmann4 is the only primary benchmark where a SUR method is best on both q20 and q30.
6. Integrated Bernoulli uncertainty has positive curve-level correlation with q20/q30 error, but it is not a reliable standalone proxy. The Branin and optional Ackley rows show lower uncertainty can still coincide with worse near-boundary error.
7. Confidence can be misaligned: k15 reduced integrated uncertainty while worsening q20/q30 versus repulsion on Branin and optional Ackley, but uncertainty reduction aligned with lower boundary error on Hartmann4.
8. Runtime cost is not justified as a default acquisition. It may be acceptable as a focused Hartmann-like diagnostic, but every SUR step pays for two fantasy classifier fits per shortlisted candidate.
9. Thesis-level conclusion: fixed-GPC Bernoulli SUR refit is a serious diagnostic and a Hartmann4 candidate, but it is not robust enough to replace `classifier_uncertainty_repulsion` or the stronger GP-regressor baselines as a default acquisition.
