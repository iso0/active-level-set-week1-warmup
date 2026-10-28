# Same-target query and computation accounting

The two shared query policies were fixed. These are predictor attainments on those paths, **not demonstrated acquisition savings**. Each panel has32 worlds. Confirmation requires two consecutive grid budgets; unattained cases retain burden25 and censoring at24. Counts are individual learners, not a threshold on an averaged learning curve.

| Shared path | Predictor | BA-AULC | Positive recall | Negative recall | BA≥.90 count; burden | BA≥.93 count; burden | BA≥.95 count; burden |
|---|---|---:|---:|---:|---:|---:|---:|
| maximin | strong | 0.8122 | 0.8379 | 0.7866 | 12/32; 20.312 | 8/32; 22.438 | 4/32; 24.312 |
| maximin | compact | 0.8121 | 0.8362 | 0.7879 | 12/32; 20.312 | 8/32; 22.438 | 4/32; 24.312 |
| maximin | gated | 0.8135 | 0.8353 | 0.7916 | 12/32; 20.312 | 8/32; 22.438 | 4/32; 24.188 |
| maximin | trace_match | 0.8129 | 0.8382 | 0.7876 | 12/32; 20.312 | 8/32; 22.500 | 4/32; 24.188 |
| maximin | coherent | 0.8134 | 0.8384 | 0.7885 | 12/32; 20.312 | 8/32; 22.438 | 4/32; 24.312 |
| maximin | coherent_trace | 0.8122 | 0.8378 | 0.7866 | 12/32; 20.312 | 8/32; 22.438 | 4/32; 24.312 |
| strong_margin | strong | 0.8197 | 0.8501 | 0.7892 | 14/32; 19.938 | 11/32; 22.094 | 4/32; 24.062 |
| strong_margin | compact | 0.8196 | 0.8496 | 0.7896 | 14/32; 19.938 | 11/32; 22.094 | 4/32; 24.062 |
| strong_margin | gated | 0.8199 | 0.8482 | 0.7915 | 14/32; 19.688 | 11/32; 22.156 | 4/32; 24.125 |
| strong_margin | trace_match | 0.8197 | 0.8495 | 0.7899 | 14/32; 19.688 | 11/32; 22.094 | 4/32; 24.062 |
| strong_margin | coherent | 0.8207 | 0.8500 | 0.7915 | 14/32; 19.938 | 11/32; 22.094 | 4/32; 23.812 |
| strong_margin | coherent_trace | 0.8197 | 0.8501 | 0.7893 | 14/32; 19.938 | 11/32; 22.094 | 4/32; 24.062 |

All64 v1 paths jointly evaluated four models: total measured model/prediction CPU 106.938s, mean 1.671s/path, peak RSS 124.0MiB.
V2 reused fitted backgrounds and paths: incremental prediction CPU 27.062s total, 0.423s/path, peak RSS 88.2MiB.
These timings exclude imports, world construction, supervision and some serialization. V1 joint timing is not a per-arm timing; v2 incremental timing is not full learner cost. No physical simulation duration was measured.

V1: 75,968 component solves and 142,609 optimizer evaluations. V2: 576 dense factorizations plus 73,728 rank-one updates. All 320 selected optimizer results reported success; 2 individual starts did not. Success is not proof of global optimality.

## Search accounting

Geometric footprint hits were the frozen conditional subgroup. They are not necessarily positive-regime detections. The following extra diagnostic distinguishes latent-positive and noisy-observed-positive hits inside that footprint; no membership was given to a selector. All pre-hit queries were charged.

| Family | Shared path | Worlds with footprint hit | With latent-positive footprint hit | With observed-positive footprint hit |
|---|---|---:|---:|---:|
| local_shift | maximin | 4/4 | 4/4 | 4/4 |
| local_shift | strong_margin | 4/4 | 4/4 | 4/4 |
| small_island | maximin | 3/4 | 3/4 | 3/4 |
| small_island | strong_margin | 4/4 | 4/4 | 4/4 |
| rotated_local | maximin | 4/4 | 4/4 | 4/4 |
| rotated_local | strong_margin | 3/4 | 3/4 | 3/4 |
