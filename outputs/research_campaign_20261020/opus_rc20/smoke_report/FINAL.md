# RC20 sequential stage — smoke (fresh DEV repeats 19–26; frozen protocol PROTOCOL_RC20_FINAL.md)

**PRIMARY: model, same selector — CAND_MARGIN − ATSCF_MARGIN, log_loss AULC over the small window (lower is better, margin 0.01): NOT DIFFERENT (DEV)** (mean Δ -0.0330 ± nan SE; good direction in 1/1 repeats)

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PRIMARY: model, same selector | CAND_MARGIN − ATSCF_MARGIN | log_loss | small | lower | 0.0100 | -0.0330 | – | -0.0330 | -0.0330 | 1/1 | NOT DIFFERENT (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | log_loss | all | lower | 0.0050 | -0.0308 | – | -0.0308 | -0.0308 | 1/1 | NOT DIFFERENT (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | brier | all | lower | 0.0050 | -0.0042 | – | -0.0042 | -0.0042 | 1/1 | NOT DIFFERENT (DEV) |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | log_loss | small | lower | 0.0100 | -0.0353 | – | -0.0353 | -0.0353 | 1/1 | NOT DIFFERENT (DEV) |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| control | CAND_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | -0.0051 | – | -0.0051 | -0.0051 | 1/1 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − ATSAPPROX_MARGIN | log_loss | all | lower | 0.0050 | -0.0094 | – | -0.0094 | -0.0094 | 1/1 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0314 | – | -0.0314 | -0.0314 | 1/1 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| control | CAND_MARGIN − G3_MARGIN | log_loss | all | lower | 0.0200 | -0.1481 | – | -0.1481 | -0.1481 | 1/1 | NOT DIFFERENT (DEV) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2100 | – | – | – | 0.0613 | – | 0.9713 | – | 0.8258 | – | 0.9736 | – |
| ATSCF_MARGIN | 0.2380 | – | – | – | 0.0687 | – | 0.9596 | – | 0.8191 | – | 0.9608 | – |
| CAND_ETASTRADDLE | 0.1696 | – | – | – | 0.0479 | – | 0.9828 | – | 0.8950 | – | 0.9638 | – |
| CAND_MARGIN | 0.2049 | – | – | – | 0.0617 | – | 0.9780 | – | 0.8057 | – | 0.9714 | – |
| E1CAL+straddle | 0.2322 | – | – | – | 0.0611 | – | 0.9763 | – | 0.8407 | – | 0.9595 | – |
| E1RAW+straddle | 0.2704 | – | – | – | 0.0623 | – | 0.9802 | – | 0.8779 | – | 0.9467 | – |
| G3_MARGIN | 0.3873 | – | – | – | 0.1100 | – | 0.9186 | – | 0.8042 | – | 0.9727 | – |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1355 | – | – | – | 0.0396 | – | 0.9869 | – | 0.8909 | – | 0.9727 | – |
| ATSCF_MARGIN | 0.1569 | – | – | – | 0.0428 | – | 0.9832 | – | 0.9033 | – | 0.9677 | – |
| CAND_ETASTRADDLE | 0.1191 | – | – | – | 0.0340 | – | 0.9911 | – | 0.9360 | – | 0.9646 | – |
| CAND_MARGIN | 0.1261 | – | – | – | 0.0386 | – | 0.9896 | – | 0.8944 | – | 0.9703 | – |
| E1CAL+straddle | 0.1575 | – | – | – | 0.0423 | – | 0.9871 | – | 0.9288 | – | 0.9524 | – |
| E1RAW+straddle | 0.1823 | – | – | – | 0.0440 | – | 0.9887 | – | 0.9470 | – | 0.9452 | – |
| G3_MARGIN | 0.2742 | – | – | – | 0.0744 | – | 0.9526 | – | 0.8679 | – | 0.9713 | – |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at the second checkpoint b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | ATSCF_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | CAND_ETASTRADDLE | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | CAND_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1CAL+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1RAW+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | G3_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | ATSCF_MARGIN | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | CAND_ETASTRADDLE | 1/1 | 0 | 9.00 | 13.00 | 13.00 | 13.00 | 13.00 | 13 |
| log_loss <= 0.2 | CAND_MARGIN | 1/1 | 0 | 14.00 | 18.00 | 18.00 | 18.00 | 18.00 | 18 |
| log_loss <= 0.2 | E1CAL+straddle | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | E1RAW+straddle | 1/1 | 0 | 14.00 | 20.00 | 20.00 | 20.00 | 20.00 | 20 |
| log_loss <= 0.2 | G3_MARGIN | 1/1 | 0 | 45.00 | 49.00 | 49.00 | 49.00 | 49.00 | 49 |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| CAND_MARGIN − ATSCF_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_ETASTRADDLE − CAND_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − ATSAPPROX_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − E1RAW+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − E1CAL+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − G3_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − ATSCF_MARGIN | 1.00 | 0/0/1 | 1 | 1.00 | 0/0 | 18/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_ETASTRADDLE − CAND_MARGIN | -5.00 | 1/0/0 | 1 | -5.00 | 0/0 | 13/18 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − ATSAPPROX_MARGIN | 1.00 | 0/0/1 | 1 | 1.00 | 0/0 | 18/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − E1RAW+straddle | -2.00 | 1/0/0 | 1 | -2.00 | 0/0 | 18/20 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − E1CAL+straddle | 1.00 | 0/0/1 | 1 | 1.00 | 0/0 | 18/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − G3_MARGIN | -31.00 | 1/0/0 | 1 | -31.00 | 0/0 | 18/49 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |

## Matched budgets (mean over repeats)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | AUC | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8 | – | 0.595 | 0.942 | 0.495 | 0.152 | 0.839 | 0.599 | 1.000 |
| ATSAPPROX_MARGIN | 12 | – | 0.861 | 0.971 | 0.211 | 0.060 | 0.982 | 0.723 | 0.333 |
| ATSAPPROX_MARGIN | 16 | – | 0.873 | 0.978 | 0.161 | 0.048 | 0.990 | 0.768 | 0.667 |
| ATSAPPROX_MARGIN | 20 | – | 0.861 | 0.971 | 0.161 | 0.046 | 0.990 | 0.723 | 0.333 |
| ATSAPPROX_MARGIN | 24 | – | 0.911 | 0.971 | 0.155 | 0.042 | 0.989 | 0.794 | 0.333 |
| ATSAPPROX_MARGIN | 40 | – | 0.911 | 0.971 | 0.091 | 0.027 | 0.996 | 0.746 | 0.000 |
| ATSAPPROX_MARGIN | 60 | – | 0.937 | 0.978 | 0.087 | 0.025 | 0.996 | 0.816 | 0.333 |
| ATSCF_MARGIN | 8 | – | 0.646 | 0.928 | 0.539 | 0.166 | 0.793 | 0.651 | 0.333 |
| ATSCF_MARGIN | 12 | – | 0.848 | 0.957 | 0.218 | 0.060 | 0.987 | 0.699 | 0.333 |
| ATSCF_MARGIN | 16 | – | 0.823 | 0.986 | 0.165 | 0.049 | 0.990 | 0.647 | 0.667 |
| ATSCF_MARGIN | 20 | – | 0.886 | 0.986 | 0.144 | 0.037 | 0.994 | 0.766 | 1.000 |
| ATSCF_MARGIN | 24 | – | 0.848 | 0.986 | 0.150 | 0.041 | 0.991 | 0.695 | 1.000 |
| ATSCF_MARGIN | 40 | – | 0.975 | 0.964 | 0.130 | 0.032 | 0.994 | 0.844 | 0.333 |
| ATSCF_MARGIN | 60 | – | 0.962 | 0.978 | 0.089 | 0.025 | 0.996 | 0.863 | 0.333 |
| CAND_ETASTRADDLE | 8 | – | 0.646 | 0.949 | 0.426 | 0.133 | 0.871 | 0.627 | 0.333 |
| CAND_ETASTRADDLE | 12 | – | 0.785 | 0.986 | 0.219 | 0.065 | 0.982 | 0.671 | 0.333 |
| CAND_ETASTRADDLE | 16 | – | 0.949 | 0.964 | 0.136 | 0.035 | 0.993 | 0.796 | 0.000 |
| CAND_ETASTRADDLE | 20 | – | 0.937 | 0.971 | 0.125 | 0.034 | 0.993 | 0.794 | 0.333 |
| CAND_ETASTRADDLE | 24 | – | 0.962 | 0.957 | 0.113 | 0.031 | 0.993 | 0.798 | 0.000 |
| CAND_ETASTRADDLE | 40 | – | 0.949 | 0.964 | 0.105 | 0.030 | 0.994 | 0.796 | 0.000 |
| CAND_ETASTRADDLE | 60 | – | 0.937 | 0.964 | 0.081 | 0.026 | 0.996 | 0.772 | 0.000 |
| CAND_MARGIN | 8 | – | 0.646 | 0.949 | 0.426 | 0.133 | 0.871 | 0.627 | 0.333 |
| CAND_MARGIN | 12 | – | 0.823 | 0.978 | 0.235 | 0.068 | 0.974 | 0.649 | 0.333 |
| CAND_MARGIN | 16 | – | 0.810 | 0.964 | 0.171 | 0.049 | 0.988 | 0.582 | 0.333 |
| CAND_MARGIN | 20 | – | 0.861 | 0.971 | 0.141 | 0.043 | 0.989 | 0.697 | 0.667 |
| CAND_MARGIN | 24 | – | 0.886 | 0.978 | 0.110 | 0.033 | 0.994 | 0.720 | 0.667 |
| CAND_MARGIN | 40 | – | 0.937 | 0.971 | 0.091 | 0.027 | 0.995 | 0.818 | 0.333 |
| CAND_MARGIN | 60 | – | 0.949 | 0.971 | 0.088 | 0.028 | 0.995 | 0.818 | 0.333 |
| E1CAL+straddle | 8 | – | 0.671 | 0.986 | 0.317 | 0.089 | 0.960 | 0.695 | 0.333 |
| E1CAL+straddle | 12 | – | 0.709 | 0.949 | 0.478 | 0.106 | 0.941 | 0.627 | 0.333 |
| E1CAL+straddle | 16 | – | 0.873 | 0.949 | 0.176 | 0.051 | 0.980 | 0.655 | 0.333 |
| E1CAL+straddle | 20 | – | 0.937 | 0.949 | 0.174 | 0.047 | 0.983 | 0.774 | 0.333 |
| E1CAL+straddle | 24 | – | 0.949 | 0.964 | 0.140 | 0.037 | 0.988 | 0.796 | 0.333 |
| E1CAL+straddle | 40 | – | 0.949 | 0.935 | 0.130 | 0.041 | 0.990 | 0.709 | 0.333 |
| E1CAL+straddle | 60 | – | 0.962 | 0.957 | 0.124 | 0.032 | 0.989 | 0.798 | 0.333 |
| E1RAW+straddle | 8 | – | 0.772 | 0.986 | 0.503 | 0.082 | 0.942 | 0.695 | 0.333 |
| E1RAW+straddle | 12 | – | 0.709 | 0.964 | 0.558 | 0.111 | 0.942 | 0.649 | 0.333 |
| E1RAW+straddle | 16 | – | 0.924 | 0.935 | 0.154 | 0.048 | 0.988 | 0.707 | 0.333 |
| E1RAW+straddle | 20 | – | 0.962 | 0.913 | 0.199 | 0.052 | 0.988 | 0.733 | 0.333 |
| E1RAW+straddle | 24 | – | 0.975 | 0.928 | 0.161 | 0.042 | 0.991 | 0.757 | 0.333 |
| E1RAW+straddle | 40 | – | 0.962 | 0.935 | 0.152 | 0.045 | 0.990 | 0.733 | 0.333 |
| E1RAW+straddle | 60 | – | 0.962 | 0.957 | 0.128 | 0.031 | 0.993 | 0.798 | 0.333 |
| G3_MARGIN | 8 | – | 0.633 | 0.978 | 0.447 | 0.140 | 0.902 | 0.673 | 0.333 |
| G3_MARGIN | 12 | – | 0.696 | 0.971 | 0.462 | 0.142 | 0.845 | 0.651 | 0.000 |
| G3_MARGIN | 16 | – | 0.873 | 0.971 | 0.351 | 0.094 | 0.949 | 0.746 | 0.000 |
| G3_MARGIN | 20 | – | 0.861 | 0.986 | 0.377 | 0.103 | 0.946 | 0.718 | 0.667 |
| G3_MARGIN | 24 | – | 0.848 | 0.993 | 0.352 | 0.096 | 0.940 | 0.740 | 1.000 |
| G3_MARGIN | 40 | – | 0.911 | 0.957 | 0.220 | 0.059 | 0.971 | 0.748 | 0.000 |
| G3_MARGIN | 60 | – | 0.924 | 0.978 | 0.158 | 0.039 | 0.990 | 0.792 | 0.667 |

## Compute: GP / decision CPU (seconds) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 2 | 2.62 | 5.25 | – | 60.00 |
| ATSCF_MARGIN | 2 | 23.31 | 46.62 | – | 60.00 |
| CAND_ETASTRADDLE | 2 | 27.79 | 55.59 | 0.52 | 60.00 |
| CAND_MARGIN | 2 | 24.85 | 49.70 | 0.47 | 60.00 |
| E1S | 2 | 20.98 | 41.96 | – | 60.00 |
| G3_MARGIN | 2 | 5.79 | 11.59 | – | 60.00 |

## Exploratory: same paid prefixes on the candidate's own paths (recorded every 4 budgets)

| arm | log_loss | BA | brier |
|---|---|---|---|
| HONLY@CAND_ETASTRADDLE | 0.2025 | – | 0.0526 |
| HONLY@CAND_MARGIN | 0.2146 | – | 0.0559 |
| SHQ_A@CAND_ETASTRADDLE | 0.1707 | – | 0.0451 |
| SHQ_A@CAND_MARGIN | 0.1669 | – | 0.0465 |
| SHQ_ATS@CAND_ETASTRADDLE | 0.1585 | – | 0.0435 |
| SHQ_ATS@CAND_MARGIN | 0.1538 | – | 0.0461 |
| SHQ_ATS_H@CAND_ETASTRADDLE | 0.1329 | – | 0.0387 |
| SHQ_ATS_H@CAND_MARGIN | 0.1329 | – | 0.0407 |
| SHQ_ATS_X@CAND_ETASTRADDLE | 0.1449 | – | 0.0420 |
| SHQ_ATS_X@CAND_MARGIN | 0.1398 | – | 0.0435 |
| SHQ_A_H@CAND_ETASTRADDLE | 0.1282 | – | 0.0363 |
| SHQ_A_H@CAND_MARGIN | 0.1285 | – | 0.0376 |

