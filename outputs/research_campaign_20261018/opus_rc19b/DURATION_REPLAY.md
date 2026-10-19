# RC19B duration — hurdle replay (DEVELOPMENT on RC19 final repeats 3–10; same paid prefixes, other 7 outputs unchanged)

Duration level R2 ≥ 0.6; joint = all 8 outputs at their RC19 levels; spend = b + 4 of the first confirmed pair (total revealed simulations).

| model | acq | variant | dur_AULC | dur_completed | dur_spend | joint_completed | joint_spend |
|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | ORIG_GP | 0.510 | 5/8 | 56,–,–,80,48,–,48,68 | 5/8 | 56,–,–,80,48,–,48,68 |
| M0Q | MOIVR | QG3_LOG | 0.198 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| M0Q | MOIVR | QG3_RAW | 0.469 | 4/8 | 60,–,–,–,56,–,56,72 | 4/8 | 60,–,–,–,56,–,56,72 |
| M0Q | MOIVR | QS_LOG | 0.016 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| M0Q | MOIVR | QS_RAW | 0.471 | 4/8 | 68,–,–,–,56,–,52,68 | 4/8 | 68,–,–,–,56,–,52,68 |
| SHQ | MOIVR | ORIG_GP | 0.534 | 1/8 | –,60,–,–,–,–,–,– | 1/8 | –,60,–,–,–,–,–,– |
| SHQ | MOIVR | QG3_LOG | 0.282 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| SHQ | MOIVR | QG3_RAW | 0.487 | 4/8 | –,52,–,–,52,64,–,48 | 4/8 | –,52,–,–,52,64,–,48 |
| SHQ | MOIVR | QS_LOG | 0.172 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| SHQ | MOIVR | QS_RAW | 0.490 | 4/8 | –,52,–,–,52,64,–,52 | 4/8 | –,52,–,–,52,64,–,52 |
| SHQ | RANDOM | ORIG_GP | 0.528 | 7/8 | –,68,40,76,68,68,76,64 | 7/8 | –,68,40,76,68,68,76,64 |
| SHQ | RANDOM | QG3_LOG | -0.106 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| SHQ | RANDOM | QG3_RAW | 0.444 | 1/8 | –,–,–,–,–,–,64,– | 1/8 | –,–,–,–,–,–,64,– |
| SHQ | RANDOM | QS_LOG | -0.456 | 0/8 | –,–,–,–,–,–,–,– | 0/8 | –,–,–,–,–,–,–,– |
| SHQ | RANDOM | QS_RAW | 0.443 | 1/8 | –,–,–,–,–,–,64,– | 1/8 | –,–,–,–,–,–,64,– |

Duration accuracy at matched budgets (mean over repeats; zero_rmse = error on true zeros, positive_rmse = error on positive durations, µs):

| model | acq | variant | budget | R2 | cov90 | zero_rmse | positive_rmse |
|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | ORIG_GP | 16 | 0.405 | 0.660 | 13.778 | 58.596 |
| M0Q | MOIVR | ORIG_GP | 40 | 0.489 | 0.763 | 13.743 | 53.959 |
| M0Q | MOIVR | ORIG_GP | 80 | 0.607 | 0.822 | 13.136 | 46.887 |
| M0Q | MOIVR | QG3_LOG | 16 | 0.154 | 0.836 | 20.466 | 68.295 |
| M0Q | MOIVR | QG3_LOG | 40 | 0.203 | 0.910 | 13.976 | 67.376 |
| M0Q | MOIVR | QG3_LOG | 80 | 0.019 | 0.932 | 15.084 | 73.105 |
| M0Q | MOIVR | QG3_RAW | 16 | 0.308 | 0.876 | 19.710 | 61.947 |
| M0Q | MOIVR | QG3_RAW | 40 | 0.481 | 0.910 | 13.473 | 54.554 |
| M0Q | MOIVR | QG3_RAW | 80 | 0.586 | 0.930 | 12.495 | 48.731 |
| M0Q | MOIVR | QS_LOG | 16 | 0.022 | 0.798 | 18.845 | 73.205 |
| M0Q | MOIVR | QS_LOG | 40 | -0.030 | 0.876 | 17.930 | 75.170 |
| M0Q | MOIVR | QS_LOG | 80 | -0.291 | 0.917 | 23.737 | 81.408 |
| M0Q | MOIVR | QS_RAW | 16 | 0.354 | 0.804 | 18.721 | 59.830 |
| M0Q | MOIVR | QS_RAW | 40 | 0.490 | 0.855 | 13.888 | 53.983 |
| M0Q | MOIVR | QS_RAW | 80 | 0.579 | 0.880 | 15.012 | 48.385 |
| SHQ | MOIVR | ORIG_GP | 16 | 0.510 | 0.769 | 13.272 | 53.044 |
| SHQ | MOIVR | ORIG_GP | 40 | 0.561 | 0.885 | 12.696 | 50.273 |
| SHQ | MOIVR | ORIG_GP | 80 | 0.591 | 0.921 | 13.733 | 48.126 |
| SHQ | MOIVR | QG3_LOG | 16 | 0.291 | 0.866 | 19.385 | 62.832 |
| SHQ | MOIVR | QG3_LOG | 40 | 0.343 | 0.902 | 13.539 | 61.726 |
| SHQ | MOIVR | QG3_LOG | 80 | 0.309 | 0.930 | 13.248 | 62.725 |
| SHQ | MOIVR | QG3_RAW | 16 | 0.327 | 0.891 | 20.392 | 60.719 |
| SHQ | MOIVR | QG3_RAW | 40 | 0.494 | 0.912 | 15.033 | 53.469 |
| SHQ | MOIVR | QG3_RAW | 80 | 0.588 | 0.931 | 13.608 | 48.319 |
| SHQ | MOIVR | QS_LOG | 16 | 0.245 | 0.845 | 19.254 | 64.858 |
| SHQ | MOIVR | QS_LOG | 40 | 0.237 | 0.891 | 16.813 | 65.789 |
| SHQ | MOIVR | QS_LOG | 80 | 0.135 | 0.923 | 20.725 | 68.348 |
| SHQ | MOIVR | QS_RAW | 16 | 0.374 | 0.831 | 20.528 | 57.857 |
| SHQ | MOIVR | QS_RAW | 40 | 0.501 | 0.862 | 17.743 | 52.289 |
| SHQ | MOIVR | QS_RAW | 80 | 0.563 | 0.883 | 19.327 | 48.009 |
| SHQ | RANDOM | ORIG_GP | 16 | 0.455 | 0.803 | 18.744 | 54.275 |
| SHQ | RANDOM | ORIG_GP | 40 | 0.542 | 0.889 | 13.774 | 51.054 |
| SHQ | RANDOM | ORIG_GP | 80 | 0.610 | 0.908 | 10.577 | 47.649 |
| SHQ | RANDOM | QG3_LOG | 16 | 0.160 | 0.868 | 24.933 | 66.984 |
| SHQ | RANDOM | QG3_LOG | 40 | -3.166 | 0.915 | 20.832 | 116.263 |
| SHQ | RANDOM | QG3_LOG | 80 | 0.281 | 0.926 | 9.668 | 64.648 |
| SHQ | RANDOM | QG3_RAW | 16 | 0.288 | 0.910 | 25.514 | 60.697 |
| SHQ | RANDOM | QG3_RAW | 40 | 0.427 | 0.930 | 19.098 | 55.922 |
| SHQ | RANDOM | QG3_RAW | 80 | 0.565 | 0.947 | 14.001 | 49.589 |
| SHQ | RANDOM | QS_LOG | 16 | 0.007 | 0.849 | 27.054 | 72.742 |
| SHQ | RANDOM | QS_LOG | 40 | -5.044 | 0.901 | 27.677 | 135.157 |
| SHQ | RANDOM | QS_LOG | 80 | 0.035 | 0.917 | 12.554 | 74.473 |
| SHQ | RANDOM | QS_RAW | 16 | 0.258 | 0.846 | 26.256 | 61.212 |
| SHQ | RANDOM | QS_RAW | 40 | 0.416 | 0.882 | 21.560 | 55.489 |
| SHQ | RANDOM | QS_RAW | 80 | 0.564 | 0.909 | 15.028 | 49.254 |

