# Week 7.1 GPC Bernoulli SUR Validation

This run validates fixed-kernel GP-classifier Bernoulli SUR refit across seeds. It does not use optimized classifier kernels.

## Run settings

- Benchmarks: `branin, hartmann4`.
- Reference size: `1500`.
- Shortlist sizes: `15, 25`.
- Total elapsed runtime: `33.4` seconds.

## Best final methods

| Benchmark | Global | q20 | q30 |
| --- | --- | --- | --- |
| Thresholded Branin | `gpc_bernoulli_sur_refit_k15` (0.168) | `gpc_bernoulli_sur_refit_k15` (0.367) | `gpc_bernoulli_sur_refit_k15` (0.283) |
| Thresholded 4D Hartmann | `gpc_bernoulli_sur_refit_k15` (0.291) | `classifier_uncertainty_repulsion` (0.412) | `classifier_uncertainty_repulsion` (0.446) |

## Answers

### Thresholded Branin
1. k15 reproduces the Week 7 seed-0 signal across all seeds: q20/q30 moved from Week 7 seed-0 `0.221` / `0.157` to five-seed `0.367` / `0.283`.
2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `True` / `True`.
3. k25 improves over k15 on q20/q30: `False` / `False`.
4. k40 was not run in this configuration.
6. Integrated uncertainty correlation with q20/q30 error over all curves: `0.308629` / `0.380228`.
7. k15 reduces uncertainty while worsening q20 versus repulsion: `False`.

### Thresholded 4D Hartmann
1. k15 reproduces the Week 7 seed-0 signal across all seeds: q20/q30 moved from Week 7 seed-0 `0.365` / `0.301` to five-seed `0.450` / `0.479`.
2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `False` / `False`.
3. k25 improves over k15 on q20/q30: `False` / `False`.
4. k40 was not run in this configuration.
6. Integrated uncertainty correlation with q20/q30 error over all curves: `-0.235349` / `-0.207418`.
7. k15 reduces uncertainty while worsening q20 versus repulsion: `True`.

## Interpretation

If SUR wins q20/q30 but not global error, that is still meaningful for this boundary-estimation thesis. If it loses to `classifier_uncertainty_repulsion`, the Week 7 seed-0 signal did not generalize. Runtime should be judged against the q20/q30 gains because every SUR step requires two fantasy classifier fits per shortlisted candidate.
