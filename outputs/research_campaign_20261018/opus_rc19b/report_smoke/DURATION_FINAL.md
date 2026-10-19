# RC19B physical outputs — spike-duration hurdle and bottleneck-aware acquisition (fresh DEV repeats 11–18; frozen protocol)

Fixed absolute targets (RC19): {"log_A_um": 0.85, "log_ke_T0_nJ": 0.85, "vmax_spike_logratio": 0.8, "vmax_spike_us": 0.6, "laser_T0_W": 0.85, "tmax_T0_K": 0.85, "log_etot_T0_J": 0.8, "log_npart_T0": 0.8}; joint = all 8 at their targets at the same budget, confirmed at b and b + 4; spend = b + 4 (total revealed simulations, startup included); horizon B80. Joint-from-dur_curves vs evaluator joint (own GP duration) mismatches: 0.

## Pre-declared contrasts

| role | arm | contrast | mean | se | repeats_good | verdict |
|---|---|---|---|---|---|---|
| D1 duration R2-AULC, matched path | SHQ+RANDOM | HURDLE − own GP duration | -0.095 | – | 0/1 | INCOMPLETE (1/8) |
| D2 joint completion by B80, matched path | SHQ+RANDOM | HURDLE vs own GP duration | -1.000 | – | 0/1 vs 1/1 (lost 1) | INCOMPLETE (1/8) |
| D1 duration R2-AULC, matched path | M0Q+MOIVR | HURDLE − own GP duration | -0.014 | – | 0/1 | INCOMPLETE (1/8) |
| D2 joint completion by B80, matched path | M0Q+MOIVR | HURDLE vs own GP duration | -1.000 | – | 0/1 vs 1/1 (lost 1) | INCOMPLETE (1/8) |
| D1 duration R2-AULC, matched path | SHQ+MOIVR | HURDLE − own GP duration | -0.072 | – | 0/1 | INCOMPLETE (1/8) |
| D2 joint completion by B80, matched path | SHQ+MOIVR | HURDLE vs own GP duration | 0.000 | – | 0/1 vs 0/1 (lost 0) | INCOMPLETE (1/8) |
| D1 duration R2-AULC, matched path | SHQ+MOIVRB | HURDLE − own GP duration | -0.127 | – | 0/1 | INCOMPLETE (1/8) |
| D2 joint completion by B80, matched path | SHQ+MOIVRB | HURDLE vs own GP duration | 0.000 | – | 0/1 vs 0/1 (lost 0) | INCOMPLETE (1/8) |
| D3 joint spend, own GP duration (acquisition contrast) | M0Q+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | 0.000 | – | 0/1 | INCOMPLETE (1/8) |
| D3 joint spend, own GP duration (acquisition contrast) | SHQ+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | 20.000 | – | 0/1 | INCOMPLETE (1/8) |
| D3 joint spend, own GP duration (acquisition contrast) | SHQ+MOIVRB | − SHQ+RANDOM (censored = 84, lower bound) | 20.000 | – | 0/1 | INCOMPLETE (1/8) |
| D3b joint spend, hurdle duration (secondary) | M0Q+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | 0.000 | – | 0/1 | INCOMPLETE (1/8) |
| D3b joint spend, hurdle duration (secondary) | SHQ+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | 0.000 | – | 0/1 | INCOMPLETE (1/8) |
| D3b joint spend, hurdle duration (secondary) | SHQ+MOIVRB | − SHQ+RANDOM (censored = 84, lower bound) | 0.000 | – | 0/1 | INCOMPLETE (1/8) |

## Joint completion, every arm, with the arm's own GP duration (ORIG_GP) and with the hurdle duration (HURDLE)

| model | acq | variant | joint_confirmed | joint_censored | joint_ever_qualified | joint_spend_mean | joint_spend_per_repeat | dur_confirmed | dur_spend_per_repeat | dur_R2_AULC |
|---|---|---|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | HURDLE | 0/1 | 1 | 0/1 | – | – | 0/1 | – | 0.48 |
| M0Q | MOIVR | ORIG_GP | 1/1 | 0 | 1/1 | 64.00 | 64 | 1/1 | 64 | 0.49 |
| SHQ | MOIVR | HURDLE | 0/1 | 1 | 0/1 | – | – | 0/1 | – | 0.48 |
| SHQ | MOIVR | ORIG_GP | 0/1 | 1 | 0/1 | – | – | 0/1 | – | 0.55 |
| SHQ | MOIVRB | HURDLE | 0/1 | 1 | 0/1 | – | – | 0/1 | – | 0.43 |
| SHQ | MOIVRB | ORIG_GP | 0/1 | 1 | 1/1 | – | – | 0/1 | – | 0.56 |
| SHQ | RANDOM | HURDLE | 0/1 | 1 | 0/1 | – | – | 0/1 | – | 0.47 |
| SHQ | RANDOM | ORIG_GP | 1/1 | 0 | 1/1 | 64.00 | 64 | 1/1 | 64 | 0.57 |

## Per-output completion (own GP models; spend per repeat)

| model | acq | target | confirmed | spend_per_repeat | AULC |
|---|---|---|---|---|---|
| M0Q | MOIVR | laser_T0_W | 1/1 | 32 | 0.886 |
| M0Q | MOIVR | log_A_um | 1/1 | 16 | 0.941 |
| M0Q | MOIVR | log_etot_T0_J | 1/1 | 24 | 0.856 |
| M0Q | MOIVR | log_ke_T0_nJ | 1/1 | 12 | 0.949 |
| M0Q | MOIVR | log_npart_T0 | 1/1 | 32 | 0.843 |
| M0Q | MOIVR | tmax_T0_K | 1/1 | 16 | 0.946 |
| M0Q | MOIVR | vmax_spike_logratio | 1/1 | 40 | 0.799 |
| M0Q | MOIVR | vmax_spike_us | 1/1 | 64 | 0.493 |
| SHQ | MOIVR | laser_T0_W | 1/1 | 20 | 0.932 |
| SHQ | MOIVR | log_A_um | 1/1 | 16 | 0.950 |
| SHQ | MOIVR | log_etot_T0_J | 1/1 | 20 | 0.893 |
| SHQ | MOIVR | log_ke_T0_nJ | 1/1 | 12 | 0.957 |
| SHQ | MOIVR | log_npart_T0 | 1/1 | 20 | 0.879 |
| SHQ | MOIVR | tmax_T0_K | 1/1 | 16 | 0.946 |
| SHQ | MOIVR | vmax_spike_logratio | 1/1 | 32 | 0.812 |
| SHQ | MOIVR | vmax_spike_us | 0/1 | – | 0.551 |
| SHQ | MOIVRB | laser_T0_W | 1/1 | 20 | 0.932 |
| SHQ | MOIVRB | log_A_um | 1/1 | 16 | 0.946 |
| SHQ | MOIVRB | log_etot_T0_J | 1/1 | 20 | 0.900 |
| SHQ | MOIVRB | log_ke_T0_nJ | 1/1 | 12 | 0.961 |
| SHQ | MOIVRB | log_npart_T0 | 1/1 | 20 | 0.887 |
| SHQ | MOIVRB | tmax_T0_K | 1/1 | 16 | 0.947 |
| SHQ | MOIVRB | vmax_spike_logratio | 1/1 | 24 | 0.817 |
| SHQ | MOIVRB | vmax_spike_us | 0/1 | – | 0.557 |
| SHQ | RANDOM | laser_T0_W | 1/1 | 28 | 0.922 |
| SHQ | RANDOM | log_A_um | 1/1 | 16 | 0.946 |
| SHQ | RANDOM | log_etot_T0_J | 1/1 | 20 | 0.884 |
| SHQ | RANDOM | log_ke_T0_nJ | 1/1 | 12 | 0.949 |
| SHQ | RANDOM | log_npart_T0 | 1/1 | 20 | 0.873 |
| SHQ | RANDOM | tmax_T0_K | 1/1 | 20 | 0.941 |
| SHQ | RANDOM | vmax_spike_logratio | 1/1 | 36 | 0.816 |
| SHQ | RANDOM | vmax_spike_us | 1/1 | 64 | 0.566 |

## Duration accuracy at matched budgets (mean, min, max over repeats; zero_rmse = error on true zeros, positive_rmse = error on positive durations, µs)

| model | acq | variant | budget | R2 | R2_min | R2_max | cov90 | zero_rmse | positive_rmse |
|---|---|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | HURDLE | 16 | 0.379 | 0.379 | 0.379 | 0.936 | 24.867 | 56.704 |
| M0Q | MOIVR | HURDLE | 40 | 0.558 | 0.558 | 0.558 | 0.895 | 14.894 | 49.897 |
| M0Q | MOIVR | HURDLE | 80 | 0.524 | 0.524 | 0.524 | 0.868 | 17.563 | 51.150 |
| M0Q | MOIVR | ORIG_GP | 16 | 0.308 | 0.308 | 0.308 | 0.692 | 27.785 | 59.194 |
| M0Q | MOIVR | ORIG_GP | 40 | 0.489 | 0.489 | 0.489 | 0.818 | 11.866 | 54.680 |
| M0Q | MOIVR | ORIG_GP | 80 | 0.489 | 0.489 | 0.489 | 0.783 | 10.609 | 54.886 |
| SHQ | MOIVR | HURDLE | 16 | 0.428 | 0.428 | 0.428 | 0.942 | 21.595 | 55.269 |
| SHQ | MOIVR | HURDLE | 40 | 0.483 | 0.483 | 0.483 | 0.845 | 14.598 | 54.353 |
| SHQ | MOIVR | HURDLE | 80 | 0.517 | 0.517 | 0.517 | 0.880 | 14.406 | 52.504 |
| SHQ | MOIVR | ORIG_GP | 16 | 0.535 | 0.535 | 0.535 | 0.874 | 12.612 | 51.841 |
| SHQ | MOIVR | ORIG_GP | 40 | 0.565 | 0.565 | 0.565 | 0.880 | 9.089 | 50.777 |
| SHQ | MOIVR | ORIG_GP | 80 | 0.585 | 0.585 | 0.585 | 0.917 | 11.721 | 49.030 |
| SHQ | MOIVRB | HURDLE | 16 | 0.360 | 0.360 | 0.360 | 0.932 | 28.205 | 56.268 |
| SHQ | MOIVRB | HURDLE | 40 | 0.514 | 0.514 | 0.514 | 0.824 | 13.704 | 52.847 |
| SHQ | MOIVRB | HURDLE | 80 | 0.396 | 0.396 | 0.396 | 0.853 | 27.668 | 54.518 |
| SHQ | MOIVRB | ORIG_GP | 16 | 0.518 | 0.518 | 0.518 | 0.897 | 17.140 | 51.630 |
| SHQ | MOIVRB | ORIG_GP | 40 | 0.578 | 0.578 | 0.578 | 0.878 | 10.485 | 49.743 |
| SHQ | MOIVRB | ORIG_GP | 80 | 0.602 | 0.602 | 0.602 | 0.911 | 13.300 | 47.567 |
| SHQ | RANDOM | HURDLE | 16 | 0.480 | 0.480 | 0.480 | 0.897 | 15.420 | 54.359 |
| SHQ | RANDOM | HURDLE | 40 | 0.441 | 0.441 | 0.441 | 0.882 | 14.441 | 56.737 |
| SHQ | RANDOM | HURDLE | 80 | 0.583 | 0.583 | 0.583 | 0.919 | 15.168 | 48.249 |
| SHQ | RANDOM | ORIG_GP | 16 | 0.546 | 0.546 | 0.546 | 0.833 | 13.501 | 50.977 |
| SHQ | RANDOM | ORIG_GP | 40 | 0.590 | 0.590 | 0.590 | 0.876 | 10.304 | 49.037 |
| SHQ | RANDOM | ORIG_GP | 80 | 0.627 | 0.627 | 0.627 | 0.884 | 11.140 | 46.464 |

## Bottleneck-aware weights (MOIVRB: w_t = max(0.05, 1 − paid LOO-R²_t); mean over trajectories; step = acquisition steps after the startup, every 4th)

| step | log_A_um | log_ke_T0_nJ | vmax_spike_logratio | vmax_spike_us | laser_T0_W | tmax_T0_K | log_etot_T0_J | log_npart_T0 |
|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.166 | 0.172 | 0.276 | 0.611 | 0.356 | 0.335 | 0.327 | 0.328 |
| 4.000 | 0.139 | 0.112 | 0.252 | 0.428 | 0.305 | 0.198 | 0.304 | 0.304 |
| 8.000 | 0.087 | 0.087 | 0.234 | 0.419 | 0.266 | 0.092 | 0.179 | 0.190 |
| 12.000 | 0.072 | 0.098 | 0.227 | 0.472 | 0.246 | 0.064 | 0.177 | 0.193 |
| 16.000 | 0.066 | 0.081 | 0.177 | 0.417 | 0.174 | 0.051 | 0.142 | 0.157 |
| 20.000 | 0.077 | 0.070 | 0.169 | 0.385 | 0.144 | 0.052 | 0.130 | 0.143 |
| 24.000 | 0.065 | 0.055 | 0.170 | 0.363 | 0.101 | 0.050 | 0.113 | 0.122 |
| 28.000 | 0.067 | 0.055 | 0.160 | 0.403 | 0.077 | 0.053 | 0.094 | 0.105 |
| 32.000 | 0.066 | 0.053 | 0.146 | 0.430 | 0.076 | 0.052 | 0.098 | 0.112 |
| 36.000 | 0.063 | 0.050 | 0.149 | 0.436 | 0.065 | 0.050 | 0.088 | 0.100 |
| 40.000 | 0.060 | 0.050 | 0.145 | 0.420 | 0.059 | 0.050 | 0.082 | 0.093 |
| 44.000 | 0.060 | 0.050 | 0.141 | 0.436 | 0.057 | 0.050 | 0.080 | 0.091 |
| 48.000 | 0.060 | 0.050 | 0.140 | 0.408 | 0.055 | 0.053 | 0.075 | 0.086 |
| 52.000 | 0.057 | 0.050 | 0.134 | 0.441 | 0.053 | 0.052 | 0.073 | 0.083 |
| 56.000 | 0.054 | 0.050 | 0.142 | 0.432 | 0.052 | 0.051 | 0.070 | 0.080 |
| 60.000 | 0.055 | 0.050 | 0.141 | 0.465 | 0.050 | 0.053 | 0.074 | 0.084 |
| 64.000 | 0.054 | 0.050 | 0.137 | 0.451 | 0.050 | 0.051 | 0.080 | 0.094 |
| 68.000 | 0.053 | 0.050 | 0.141 | 0.439 | 0.050 | 0.050 | 0.077 | 0.091 |

