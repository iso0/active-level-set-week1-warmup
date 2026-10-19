# RC19B physical outputs — spike-duration hurdle and bottleneck-aware acquisition (fresh DEV repeats 11–18; frozen protocol)

Fixed absolute targets (RC19): {"log_A_um": 0.85, "log_ke_T0_nJ": 0.85, "vmax_spike_logratio": 0.8, "vmax_spike_us": 0.6, "laser_T0_W": 0.85, "tmax_T0_K": 0.85, "log_etot_T0_J": 0.8, "log_npart_T0": 0.8}; joint = all 8 at their targets at the same budget, confirmed at b and b + 4; spend = b + 4 (total revealed simulations, startup included); horizon B80. Joint-from-dur_curves vs evaluator joint (own GP duration) mismatches: 0.

## Pre-declared contrasts

| role | arm | contrast | mean | se | repeats_good | verdict |
|---|---|---|---|---|---|---|
| D1 duration R2-AULC, matched path | SHQ+RANDOM | HURDLE − own GP duration | -0.077 | 0.017 | 0/8 | WORSE (DEV) |
| D2 joint completion by B80, matched path | SHQ+RANDOM | HURDLE vs own GP duration | -2.000 | – | 2/8 vs 4/8 (lost 3) | WORSE (DEV) |
| D1 duration R2-AULC, matched path | M0Q+MOIVR | HURDLE − own GP duration | -0.013 | 0.010 | 4/8 | NOT DIFFERENT (DEV) |
| D2 joint completion by B80, matched path | M0Q+MOIVR | HURDLE vs own GP duration | -2.000 | – | 5/8 vs 7/8 (lost 2) | WORSE (DEV) |
| D1 duration R2-AULC, matched path | SHQ+MOIVR | HURDLE − own GP duration | -0.074 | 0.021 | 1/8 | WORSE (DEV) |
| D2 joint completion by B80, matched path | SHQ+MOIVR | HURDLE vs own GP duration | 1.000 | – | 2/8 vs 1/8 (lost 1) | NO CLEAR CHANGE (DEV) |
| D1 duration R2-AULC, matched path | SHQ+MOIVRB | HURDLE − own GP duration | -0.097 | 0.011 | 0/8 | WORSE (DEV) |
| D2 joint completion by B80, matched path | SHQ+MOIVRB | HURDLE vs own GP duration | -3.000 | – | 0/8 vs 3/8 (lost 3) | WORSE (DEV) |
| D3 joint spend, own GP duration (acquisition contrast) | M0Q+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | -23.500 | 4.625 | 7/8 | BETTER (DEV) |
| D3 joint spend, own GP duration (acquisition contrast) | SHQ+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | 5.000 | 4.123 | 1/8 | NOT DIFFERENT (DEV) |
| D3 joint spend, own GP duration (acquisition contrast) | SHQ+MOIVRB | − SHQ+RANDOM (censored = 84, lower bound) | 4.000 | 3.780 | 1/8 | NOT DIFFERENT (DEV) |
| D3b joint spend, hurdle duration (secondary) | M0Q+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | -14.000 | 6.325 | 5/8 | NOT DIFFERENT (DEV) |
| D3b joint spend, hurdle duration (secondary) | SHQ+MOIVR | − SHQ+RANDOM (censored = 84, lower bound) | -3.000 | 3.606 | 2/8 | NOT DIFFERENT (DEV) |
| D3b joint spend, hurdle duration (secondary) | SHQ+MOIVRB | − SHQ+RANDOM (censored = 84, lower bound) | 4.500 | 3.157 | 0/8 | NOT DIFFERENT (DEV) |

## Joint completion, every arm, with the arm's own GP duration (ORIG_GP) and with the hurdle duration (HURDLE)

| model | acq | variant | joint_confirmed | joint_censored | joint_ever_qualified | joint_spend_mean | joint_spend_per_repeat | dur_confirmed | dur_spend_per_repeat | dur_R2_AULC |
|---|---|---|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | HURDLE | 5/8 | 3 | 5/8 | 54.40 | 52,–,–,52,48,52,–,68 | 5/8 | 52,–,–,52,48,52,–,68 | 0.52 |
| M0Q | MOIVR | ORIG_GP | 7/8 | 1 | 7/8 | 49.71 | 44,40,–,60,48,48,56,52 | 7/8 | 44,40,–,60,48,48,56,52 | 0.54 |
| SHQ | MOIVR | HURDLE | 2/8 | 6 | 5/8 | 54.00 | 44,–,–,–,–,64,–,– | 2/8 | 44,–,–,–,–,64,–,– | 0.47 |
| SHQ | MOIVR | ORIG_GP | 1/8 | 7 | 5/8 | 72.00 | –,–,–,72,–,–,–,– | 1/8 | –,–,–,72,–,–,–,– | 0.54 |
| SHQ | MOIVRB | HURDLE | 0/8 | 8 | 1/8 | – | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– | 0.44 |
| SHQ | MOIVRB | ORIG_GP | 3/8 | 5 | 3/8 | 77.33 | 80,–,–,–,72,80,–,– | 3/8 | 80,–,–,–,72,80,–,– | 0.54 |
| SHQ | RANDOM | HURDLE | 2/8 | 6 | 2/8 | 66.00 | 60,–,72,–,–,–,–,– | 2/8 | 60,–,72,–,–,–,–,– | 0.45 |
| SHQ | RANDOM | ORIG_GP | 4/8 | 4 | 7/8 | 71.00 | 56,76,–,–,–,80,72,– | 4/8 | 56,76,–,–,–,80,72,– | 0.53 |

## Per-output completion (own GP models; spend per repeat)

| model | acq | target | confirmed | spend_per_repeat | AULC |
|---|---|---|---|---|---|
| M0Q | MOIVR | laser_T0_W | 8/8 | 28,32,32,36,28,28,32,32 | 0.905 |
| M0Q | MOIVR | log_A_um | 8/8 | 20,16,16,16,16,20,20,16 | 0.941 |
| M0Q | MOIVR | log_etot_T0_J | 8/8 | 20,24,20,20,16,24,20,20 | 0.879 |
| M0Q | MOIVR | log_ke_T0_nJ | 8/8 | 12,12,12,12,12,12,12,12 | 0.955 |
| M0Q | MOIVR | log_npart_T0 | 8/8 | 20,24,24,28,20,28,20,20 | 0.861 |
| M0Q | MOIVR | tmax_T0_K | 8/8 | 16,16,12,12,16,16,12,16 | 0.945 |
| M0Q | MOIVR | vmax_spike_logratio | 8/8 | 32,32,36,40,36,32,36,24 | 0.797 |
| M0Q | MOIVR | vmax_spike_us | 7/8 | 44,40,–,60,48,48,56,52 | 0.536 |
| SHQ | MOIVR | laser_T0_W | 8/8 | 24,24,24,20,20,24,20,20 | 0.930 |
| SHQ | MOIVR | log_A_um | 8/8 | 16,16,16,12,16,16,20,16 | 0.947 |
| SHQ | MOIVR | log_etot_T0_J | 8/8 | 20,16,16,16,16,20,20,16 | 0.898 |
| SHQ | MOIVR | log_ke_T0_nJ | 8/8 | 12,12,12,12,12,12,12,12 | 0.962 |
| SHQ | MOIVR | log_npart_T0 | 8/8 | 20,20,16,16,16,20,20,20 | 0.884 |
| SHQ | MOIVR | tmax_T0_K | 8/8 | 12,16,16,16,20,16,16,16 | 0.944 |
| SHQ | MOIVR | vmax_spike_logratio | 8/8 | 36,32,28,32,32,24,32,24 | 0.805 |
| SHQ | MOIVR | vmax_spike_us | 1/8 | –,–,–,72,–,–,–,– | 0.545 |
| SHQ | MOIVRB | laser_T0_W | 8/8 | 24,20,24,20,20,24,20,20 | 0.929 |
| SHQ | MOIVRB | log_A_um | 8/8 | 16,16,16,12,16,16,16,16 | 0.944 |
| SHQ | MOIVRB | log_etot_T0_J | 8/8 | 20,16,16,16,16,20,20,16 | 0.899 |
| SHQ | MOIVRB | log_ke_T0_nJ | 8/8 | 12,12,12,12,12,12,12,12 | 0.963 |
| SHQ | MOIVRB | log_npart_T0 | 8/8 | 20,20,20,16,16,20,20,20 | 0.886 |
| SHQ | MOIVRB | tmax_T0_K | 8/8 | 12,16,16,16,16,16,16,16 | 0.944 |
| SHQ | MOIVRB | vmax_spike_logratio | 8/8 | 36,36,32,32,32,24,32,32 | 0.802 |
| SHQ | MOIVRB | vmax_spike_us | 3/8 | 80,–,–,–,72,80,–,– | 0.537 |
| SHQ | RANDOM | laser_T0_W | 8/8 | 16,20,28,16,20,20,24,20 | 0.923 |
| SHQ | RANDOM | log_A_um | 8/8 | 16,16,16,12,16,16,16,16 | 0.945 |
| SHQ | RANDOM | log_etot_T0_J | 8/8 | 16,20,20,16,16,24,20,16 | 0.885 |
| SHQ | RANDOM | log_ke_T0_nJ | 8/8 | 12,12,12,12,12,12,12,12 | 0.956 |
| SHQ | RANDOM | log_npart_T0 | 8/8 | 16,20,20,16,16,24,20,16 | 0.871 |
| SHQ | RANDOM | tmax_T0_K | 8/8 | 12,16,16,16,16,16,16,16 | 0.937 |
| SHQ | RANDOM | vmax_spike_logratio | 8/8 | 32,36,36,40,40,24,32,28 | 0.806 |
| SHQ | RANDOM | vmax_spike_us | 4/8 | 56,76,–,–,–,80,72,– | 0.532 |

## Duration accuracy at matched budgets (mean, min, max over repeats; zero_rmse = error on true zeros, positive_rmse = error on positive durations, µs)

| model | acq | variant | budget | R2 | R2_min | R2_max | cov90 | zero_rmse | positive_rmse |
|---|---|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | HURDLE | 16 | 0.383 | 0.259 | 0.559 | 0.814 | 19.169 | 58.252 |
| M0Q | MOIVR | HURDLE | 40 | 0.564 | 0.530 | 0.595 | 0.835 | 13.820 | 49.711 |
| M0Q | MOIVR | HURDLE | 80 | 0.587 | 0.490 | 0.675 | 0.885 | 15.778 | 47.656 |
| M0Q | MOIVR | ORIG_GP | 16 | 0.394 | 0.295 | 0.498 | 0.688 | 15.614 | 58.616 |
| M0Q | MOIVR | ORIG_GP | 40 | 0.574 | 0.521 | 0.636 | 0.758 | 10.158 | 49.935 |
| M0Q | MOIVR | ORIG_GP | 80 | 0.623 | 0.493 | 0.685 | 0.841 | 11.644 | 46.401 |
| SHQ | MOIVR | HURDLE | 16 | 0.367 | 0.291 | 0.507 | 0.800 | 18.901 | 59.237 |
| SHQ | MOIVR | HURDLE | 40 | 0.493 | 0.390 | 0.604 | 0.873 | 16.638 | 53.029 |
| SHQ | MOIVR | HURDLE | 80 | 0.574 | 0.489 | 0.624 | 0.882 | 18.025 | 47.781 |
| SHQ | MOIVR | ORIG_GP | 16 | 0.514 | 0.428 | 0.565 | 0.785 | 12.928 | 52.891 |
| SHQ | MOIVR | ORIG_GP | 40 | 0.561 | 0.524 | 0.582 | 0.890 | 12.572 | 50.263 |
| SHQ | MOIVR | ORIG_GP | 80 | 0.593 | 0.545 | 0.630 | 0.921 | 12.659 | 48.255 |
| SHQ | MOIVRB | HURDLE | 16 | 0.375 | 0.303 | 0.460 | 0.797 | 17.630 | 59.223 |
| SHQ | MOIVRB | HURDLE | 40 | 0.433 | 0.340 | 0.560 | 0.852 | 22.111 | 54.537 |
| SHQ | MOIVRB | HURDLE | 80 | 0.521 | 0.450 | 0.623 | 0.878 | 21.680 | 49.724 |
| SHQ | MOIVRB | ORIG_GP | 16 | 0.517 | 0.461 | 0.546 | 0.782 | 13.244 | 52.719 |
| SHQ | MOIVRB | ORIG_GP | 40 | 0.558 | 0.489 | 0.585 | 0.885 | 13.200 | 50.281 |
| SHQ | MOIVRB | ORIG_GP | 80 | 0.586 | 0.563 | 0.629 | 0.900 | 13.471 | 48.493 |
| SHQ | RANDOM | HURDLE | 16 | 0.399 | 0.242 | 0.521 | 0.863 | 23.231 | 55.866 |
| SHQ | RANDOM | HURDLE | 40 | 0.463 | 0.252 | 0.559 | 0.884 | 21.111 | 53.165 |
| SHQ | RANDOM | HURDLE | 80 | 0.544 | 0.500 | 0.622 | 0.900 | 15.955 | 50.308 |
| SHQ | RANDOM | ORIG_GP | 16 | 0.468 | 0.278 | 0.549 | 0.835 | 17.333 | 53.952 |
| SHQ | RANDOM | ORIG_GP | 40 | 0.552 | 0.524 | 0.586 | 0.883 | 13.459 | 50.514 |
| SHQ | RANDOM | ORIG_GP | 80 | 0.610 | 0.585 | 0.639 | 0.909 | 10.682 | 47.653 |

## Bottleneck-aware weights (MOIVRB: w_t = max(0.05, 1 − paid LOO-R²_t); mean over trajectories; step = acquisition steps after the startup, every 4th)

| step | log_A_um | log_ke_T0_nJ | vmax_spike_logratio | vmax_spike_us | laser_T0_W | tmax_T0_K | log_etot_T0_J | log_npart_T0 |
|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.209 | 0.177 | 0.417 | 0.554 | 0.292 | 0.368 | 0.416 | 0.419 |
| 4.000 | 0.121 | 0.091 | 0.251 | 0.470 | 0.192 | 0.195 | 0.213 | 0.223 |
| 8.000 | 0.085 | 0.070 | 0.202 | 0.419 | 0.166 | 0.092 | 0.142 | 0.150 |
| 12.000 | 0.073 | 0.057 | 0.183 | 0.403 | 0.158 | 0.081 | 0.103 | 0.106 |
| 16.000 | 0.077 | 0.053 | 0.187 | 0.425 | 0.120 | 0.073 | 0.081 | 0.084 |
| 20.000 | 0.070 | 0.057 | 0.180 | 0.419 | 0.097 | 0.065 | 0.078 | 0.083 |
| 24.000 | 0.067 | 0.056 | 0.178 | 0.442 | 0.087 | 0.064 | 0.074 | 0.079 |
| 28.000 | 0.065 | 0.054 | 0.170 | 0.444 | 0.076 | 0.059 | 0.073 | 0.078 |
| 32.000 | 0.064 | 0.053 | 0.165 | 0.434 | 0.068 | 0.057 | 0.074 | 0.079 |
| 36.000 | 0.063 | 0.054 | 0.167 | 0.449 | 0.059 | 0.055 | 0.073 | 0.078 |
| 40.000 | 0.061 | 0.054 | 0.163 | 0.451 | 0.056 | 0.053 | 0.073 | 0.079 |
| 44.000 | 0.059 | 0.054 | 0.164 | 0.456 | 0.055 | 0.053 | 0.071 | 0.077 |
| 48.000 | 0.056 | 0.053 | 0.161 | 0.450 | 0.052 | 0.054 | 0.067 | 0.072 |
| 52.000 | 0.054 | 0.053 | 0.155 | 0.457 | 0.052 | 0.053 | 0.067 | 0.072 |
| 56.000 | 0.054 | 0.052 | 0.152 | 0.461 | 0.051 | 0.052 | 0.066 | 0.072 |
| 60.000 | 0.053 | 0.052 | 0.150 | 0.460 | 0.050 | 0.052 | 0.063 | 0.069 |
| 64.000 | 0.052 | 0.053 | 0.149 | 0.466 | 0.050 | 0.052 | 0.065 | 0.071 |
| 68.000 | 0.053 | 0.054 | 0.148 | 0.457 | 0.050 | 0.051 | 0.064 | 0.070 |

