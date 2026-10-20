# RC21B confirmation stage (PHR_NRMAP) — smoke (fresh DEV repeats 35–42; frozen protocol PROTOCOL_RC21B.md)

**Q1 decision accuracy (co-primary) — NEW_MARGIN − H_MARGIN, BA-AULC over the small window (margin 0.02): INCOMPLETE (0/1)** (mean Δ +nan ± nan SE; better in 0/0 repeats)

**Q2 paid simulations to a confirmed BA >= 0.93 (co-primary) — NEW_MARGIN − H_MARGIN: NO CLEAR DIFFERENCE (DEV)** (restricted mean difference +0.00 simulations; fewer/equal/more 0/1/0; censored 1/1)

**Answer to the main question (better decisions OR fewer paid simulations to the same BA target than the previous strongest model): NO (DEV).** Probability-only improvements (log loss / Brier) are reported below and are not decision superiority.

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 decision accuracy (co-primary) | NEW_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| decision, NEW vs H | NEW_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | small | higher | 0.0200 | 0.0819 | – | 0.0819 | 0.0819 | 1/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | small | higher | 0.0200 | -0.0107 | – | -0.0107 | -0.0107 | 0/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | all | higher | 0.0200 | 0.0365 | – | 0.0365 | 0.0365 | 1/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | all | higher | 0.0200 | -0.0088 | – | -0.0088 | -0.0088 | 0/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H (key secondary) | NEW_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | -0.0513 | – | -0.0513 | -0.0513 | 1/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | -0.0054 | – | -0.0054 | -0.0054 | 1/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | brier | all | lower | 0.0050 | -0.0022 | – | -0.0022 | -0.0022 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | -0.0564 | – | -0.0564 | -0.0564 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | all | lower | 0.0050 | -0.0148 | – | -0.0148 | -0.0148 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| control | NEW_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0367 | – | -0.0367 | -0.0367 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2100 | – | – | – | 0.0613 | – | 0.9713 | – | 0.8258 | – | 0.9736 | – | 0.7137 | – |
| E1CAL+straddle | 0.2322 | – | – | – | 0.0611 | – | 0.9763 | – | 0.8407 | – | 0.9595 | – | 0.7114 | – |
| E1RAW+straddle | 0.2704 | – | – | – | 0.0623 | – | 0.9802 | – | 0.8779 | – | 0.9467 | – | 0.7006 | – |
| H_MARGIN | 0.2049 | – | – | – | 0.0617 | – | 0.9780 | – | 0.8057 | – | 0.9714 | – | 0.6706 | – |
| NEW_MARGIN | 0.1536 | – | – | – | 0.0471 | – | 0.9841 | – | 0.8876 | – | 0.9608 | – | 0.7428 | – |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1355 | – | – | – | 0.0396 | – | 0.9869 | – | 0.8909 | – | 0.9727 | – | 0.7662 | – |
| E1CAL+straddle | 0.1575 | – | – | – | 0.0423 | – | 0.9871 | – | 0.9288 | – | 0.9524 | – | 0.7713 | – |
| E1RAW+straddle | 0.1823 | – | – | – | 0.0440 | – | 0.9887 | – | 0.9470 | – | 0.9452 | – | 0.7700 | – |
| H_MARGIN | 0.1261 | – | – | – | 0.0386 | – | 0.9896 | – | 0.8944 | – | 0.9703 | – | 0.7576 | – |
| NEW_MARGIN | 0.1208 | – | – | – | 0.0364 | – | 0.9905 | – | 0.9310 | – | 0.9616 | – | 0.7843 | – |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1CAL+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1RAW+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | H_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | NEW_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | E1CAL+straddle | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | E1RAW+straddle | 1/1 | 0 | 14.00 | 20.00 | 20.00 | 20.00 | 20.00 | 20 |
| log_loss <= 0.2 | H_MARGIN | 1/1 | 0 | 14.00 | 18.00 | 18.00 | 18.00 | 18.00 | 18 |
| log_loss <= 0.2 | NEW_MARGIN | 1/1 | 0 | 11.00 | 15.00 | 15.00 | 15.00 | 15.00 | 15 |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| NEW_MARGIN − H_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − ATSAPPROX_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| H_MARGIN − ATSAPPROX_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1RAW+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1CAL+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − H_MARGIN | -3.00 | 1/0/0 | 1 | -3.00 | 0/0 | 15/18 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − ATSAPPROX_MARGIN | -2.00 | 1/0/0 | 1 | -2.00 | 0/0 | 15/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| H_MARGIN − ATSAPPROX_MARGIN | 1.00 | 0/0/1 | 1 | 1.00 | 0/0 | 18/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1RAW+straddle | -5.00 | 1/0/0 | 1 | -5.00 | 0/0 | 15/20 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1CAL+straddle | -2.00 | 1/0/0 | 1 | -2.00 | 0/0 | 15/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |

## Matched budgets (mean over repeats): both recalls, q20 and the NEW-batch conduction recall (corner diagnostic)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | AUC | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8 | – | 0.595 | 0.942 | 0.495 | 0.152 | 0.839 | 0.599 | 1.000 |
| ATSAPPROX_MARGIN | 12 | – | 0.861 | 0.971 | 0.211 | 0.060 | 0.982 | 0.723 | 0.333 |
| ATSAPPROX_MARGIN | 16 | – | 0.873 | 0.978 | 0.161 | 0.048 | 0.990 | 0.768 | 0.667 |
| ATSAPPROX_MARGIN | 20 | – | 0.861 | 0.971 | 0.161 | 0.046 | 0.990 | 0.723 | 0.333 |
| ATSAPPROX_MARGIN | 24 | – | 0.911 | 0.971 | 0.155 | 0.042 | 0.989 | 0.794 | 0.333 |
| ATSAPPROX_MARGIN | 32 | – | 0.937 | 0.978 | 0.101 | 0.026 | 0.995 | 0.816 | 0.667 |
| ATSAPPROX_MARGIN | 40 | – | 0.911 | 0.971 | 0.091 | 0.027 | 0.996 | 0.746 | 0.000 |
| ATSAPPROX_MARGIN | 60 | – | 0.937 | 0.978 | 0.087 | 0.025 | 0.996 | 0.816 | 0.333 |
| E1CAL+straddle | 8 | – | 0.671 | 0.986 | 0.317 | 0.089 | 0.960 | 0.695 | 0.333 |
| E1CAL+straddle | 12 | – | 0.709 | 0.949 | 0.478 | 0.106 | 0.941 | 0.627 | 0.333 |
| E1CAL+straddle | 16 | – | 0.873 | 0.949 | 0.176 | 0.051 | 0.980 | 0.655 | 0.333 |
| E1CAL+straddle | 20 | – | 0.937 | 0.949 | 0.174 | 0.047 | 0.983 | 0.774 | 0.333 |
| E1CAL+straddle | 24 | – | 0.949 | 0.964 | 0.140 | 0.037 | 0.988 | 0.796 | 0.333 |
| E1CAL+straddle | 32 | – | 0.987 | 0.942 | 0.147 | 0.035 | 0.991 | 0.824 | 0.333 |
| E1CAL+straddle | 40 | – | 0.949 | 0.935 | 0.130 | 0.041 | 0.990 | 0.709 | 0.333 |
| E1CAL+straddle | 60 | – | 0.962 | 0.957 | 0.124 | 0.032 | 0.989 | 0.798 | 0.333 |
| E1RAW+straddle | 8 | – | 0.772 | 0.986 | 0.503 | 0.082 | 0.942 | 0.695 | 0.333 |
| E1RAW+straddle | 12 | – | 0.709 | 0.964 | 0.558 | 0.111 | 0.942 | 0.649 | 0.333 |
| E1RAW+straddle | 16 | – | 0.924 | 0.935 | 0.154 | 0.048 | 0.988 | 0.707 | 0.333 |
| E1RAW+straddle | 20 | – | 0.962 | 0.913 | 0.199 | 0.052 | 0.988 | 0.733 | 0.333 |
| E1RAW+straddle | 24 | – | 0.975 | 0.928 | 0.161 | 0.042 | 0.991 | 0.757 | 0.333 |
| E1RAW+straddle | 32 | – | 0.987 | 0.928 | 0.167 | 0.039 | 0.992 | 0.781 | 0.000 |
| E1RAW+straddle | 40 | – | 0.962 | 0.935 | 0.152 | 0.045 | 0.990 | 0.733 | 0.333 |
| E1RAW+straddle | 60 | – | 0.962 | 0.957 | 0.128 | 0.031 | 0.993 | 0.798 | 0.333 |
| H_MARGIN | 8 | – | 0.646 | 0.949 | 0.426 | 0.133 | 0.871 | 0.627 | 0.333 |
| H_MARGIN | 12 | – | 0.823 | 0.978 | 0.235 | 0.068 | 0.974 | 0.649 | 0.333 |
| H_MARGIN | 16 | – | 0.810 | 0.964 | 0.171 | 0.049 | 0.988 | 0.582 | 0.333 |
| H_MARGIN | 20 | – | 0.861 | 0.971 | 0.141 | 0.043 | 0.989 | 0.697 | 0.667 |
| H_MARGIN | 24 | – | 0.886 | 0.978 | 0.110 | 0.033 | 0.994 | 0.720 | 0.667 |
| H_MARGIN | 32 | – | 0.949 | 0.971 | 0.085 | 0.025 | 0.996 | 0.818 | 0.333 |
| H_MARGIN | 40 | – | 0.937 | 0.971 | 0.091 | 0.027 | 0.995 | 0.818 | 0.333 |
| H_MARGIN | 60 | – | 0.949 | 0.971 | 0.088 | 0.028 | 0.995 | 0.818 | 0.333 |
| NEW_MARGIN | 8 | – | 0.671 | 0.942 | 0.370 | 0.120 | 0.917 | 0.606 | 0.333 |
| NEW_MARGIN | 12 | – | 0.911 | 0.957 | 0.143 | 0.042 | 0.988 | 0.751 | 0.000 |
| NEW_MARGIN | 16 | – | 0.924 | 0.957 | 0.127 | 0.037 | 0.990 | 0.751 | 0.000 |
| NEW_MARGIN | 20 | – | 0.911 | 0.978 | 0.121 | 0.037 | 0.992 | 0.816 | 0.333 |
| NEW_MARGIN | 24 | – | 0.924 | 0.964 | 0.120 | 0.037 | 0.992 | 0.772 | 0.000 |
| NEW_MARGIN | 32 | – | 0.949 | 0.964 | 0.108 | 0.031 | 0.992 | 0.796 | 0.000 |
| NEW_MARGIN | 40 | – | 0.949 | 0.964 | 0.101 | 0.031 | 0.994 | 0.796 | 0.000 |
| NEW_MARGIN | 60 | – | 0.949 | 0.971 | 0.103 | 0.030 | 0.994 | 0.818 | 0.333 |

## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over repeats) and calibration

| arm | budget | cal_slope | ECE | corner_errors | corner_n |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 1.566 | 0.053 | 2 | 3 |
| ATSAPPROX_MARGIN | 40 | 1.492 | 0.044 | 3 | 3 |
| ATSAPPROX_MARGIN | 60 | 1.346 | 0.031 | 2 | 3 |
| E1CAL+straddle | 24 | 1.012 | 0.030 | 2 | 3 |
| E1CAL+straddle | 40 | 0.922 | 0.032 | 2 | 3 |
| E1CAL+straddle | 60 | 1.176 | 0.033 | 2 | 3 |
| E1RAW+straddle | 24 | 0.600 | 0.039 | 2 | 3 |
| E1RAW+straddle | 40 | 0.594 | 0.047 | 2 | 3 |
| E1RAW+straddle | 60 | 0.610 | 0.031 | 2 | 3 |
| H_MARGIN | 24 | 1.671 | 0.044 | 1 | 3 |
| H_MARGIN | 40 | 1.357 | 0.021 | 2 | 3 |
| H_MARGIN | 60 | 1.129 | 0.025 | 2 | 3 |
| NEW_MARGIN | 24 | 0.926 | 0.036 | 3 | 3 |
| NEW_MARGIN | 40 | 0.901 | 0.034 | 3 | 3 |
| NEW_MARGIN | 60 | 1.135 | 0.027 | 2 | 3 |

## Short-Keyhole capture (diagnostic)

| arm | budget | shortK_captured | shortK_total |
|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 7 | 9 |
| ATSAPPROX_MARGIN | 60 | 6 | 9 |
| E1CAL+straddle | 24 | 8 | 9 |
| E1CAL+straddle | 60 | 7 | 9 |
| E1RAW+straddle | 24 | 9 | 9 |
| E1RAW+straddle | 60 | 7 | 9 |
| H_MARGIN | 24 | 4 | 9 |
| H_MARGIN | 60 | 7 | 9 |
| NEW_MARGIN | 24 | 7 | 9 |
| NEW_MARGIN | 60 | 7 | 9 |

## Compute: decision CPU (seconds, single thread) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 2 | 4.09 | 8.17 | – | 60.00 |
| E1S | 2 | 25.11 | 50.22 | – | 60.00 |
| H_MARGIN | 2 | 42.25 | 84.50 | 0.80 | 60.00 |
| NEW_MARGIN | 2 | 44.84 | 89.69 | 0.85 | 60.00 |

## Matched-path by-products on the physical arms' own paths (every budget; exploratory)

| arm | log_loss B8–B24 | BA B8–B24 | sensitivity B8–B24 | specificity B8–B24 | log_loss B8–B60 | BA B8–B60 | sensitivity B8–B60 | specificity B8–B60 |
|---|---|---|---|---|---|---|---|---|
| PHR@H_MARGIN | 0.2389 | – | 0.8012 | 0.9659 | 0.1475 | – | 0.8875 | 0.9677 |
| PHR@NEW_MARGIN | 0.1963 | – | 0.8868 | 0.9604 | 0.1470 | – | 0.9272 | 0.9617 |
| PHR_FX@H_MARGIN | 0.2474 | – | 0.8071 | 0.9714 | 0.1508 | – | 0.8949 | 0.9703 |
| PHR_FX@NEW_MARGIN | 0.2052 | – | 0.8846 | 0.9599 | 0.1520 | – | 0.9305 | 0.9624 |
| PHR_FXMAP@H_MARGIN | 0.2046 | – | 0.8071 | 0.9714 | 0.1260 | – | 0.8949 | 0.9703 |
| PHR_FXMAP@NEW_MARGIN | 0.1657 | – | 0.8846 | 0.9599 | 0.1242 | – | 0.9305 | 0.9624 |
| PHR_NR@H_MARGIN | 0.2349 | – | 0.7975 | 0.9663 | 0.1444 | – | 0.8889 | 0.9683 |
| PHR_NR@NEW_MARGIN | 0.1916 | – | 0.8883 | 0.9608 | 0.1421 | – | 0.9312 | 0.9619 |
| PHR_NRMAP@H_MARGIN | 0.2036 | – | 0.7937 | 0.9621 | 0.1256 | – | 0.8877 | 0.9668 |
| PHR_NRMAP@NEW_MARGIN | 0.1536 | – | 0.8876 | 0.9608 | 0.1208 | – | 0.9310 | 0.9616 |
| SHQ_ATS_H@H_MARGIN | 0.2049 | – | 0.8057 | 0.9714 | 0.1261 | – | 0.8944 | 0.9703 |
| SHQ_ATS_H@NEW_MARGIN | 0.1659 | – | 0.8846 | 0.9599 | 0.1243 | – | 0.9305 | 0.9624 |
| SHQ_ATS_X@H_MARGIN | 0.2267 | – | 0.7684 | 0.9702 | 0.1349 | – | 0.8660 | 0.9722 |
| SHQ_ATS_X@NEW_MARGIN | 0.1673 | – | 0.8757 | 0.9650 | 0.1335 | – | 0.9221 | 0.9629 |

Decomposition (paired by repeat): 'model on P's queries' = same paid prefixes, different classifier; 'path' = same classifier, different query paths.

| decomposition | contrast | window | metric | mean | se | repeats_good |
|---|---|---|---|---|---|---|
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | -0.0122 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | 0.0030 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | 0.0009 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | -0.0035 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | 0.0005 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | -0.0008 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0014 | – | 1/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0119 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0094 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0005 | – | 1/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0067 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0036 | – | 0/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0390 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0789 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0115 | – | 0/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0018 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0361 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0079 | – | 0/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | log_loss | -0.0499 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | sensitivity | 0.0938 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | specificity | -0.0013 | – | 0/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | log_loss | -0.0048 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | sensitivity | 0.0432 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | specificity | -0.0052 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0014 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | -0.0089 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | 0.0051 | – | 1/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0092 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | -0.0084 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | 0.0005 | – | 1/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0217 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0372 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0013 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0087 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0284 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0019 | – | 1/1 |

## PHR posterior diagnostics along the physical arms' paths (means)

| arm | budget | post_residual | post_mean_tau_F | post_mean_tau_h | post_mean_sigma_r | post_mean_ell_given_res | n_configs |
|---|---|---|---|---|---|---|---|
| H_MARGIN | 8 | 0.472 | 1.809 | 2.822 | 0.522 | 1.126 | 112.000 |
| H_MARGIN | 12 | 0.462 | 2.052 | 2.675 | 0.502 | 1.125 | 112.000 |
| H_MARGIN | 16 | 0.457 | 2.228 | 2.610 | 0.492 | 1.143 | 112.000 |
| H_MARGIN | 24 | 0.420 | 2.670 | 2.728 | 0.421 | 1.132 | 112.000 |
| H_MARGIN | 40 | 0.379 | 1.818 | 2.237 | 0.350 | 1.121 | 112.000 |
| H_MARGIN | 60 | 0.333 | 1.388 | 2.468 | 0.277 | 1.123 | 112.000 |
| NEW_MARGIN | 8 | 0.472 | 1.809 | 2.822 | 0.522 | 1.126 | 112.000 |
| NEW_MARGIN | 12 | 0.482 | 2.026 | 2.439 | 0.543 | 1.119 | 112.000 |
| NEW_MARGIN | 16 | 0.453 | 1.876 | 2.549 | 0.484 | 1.116 | 112.000 |
| NEW_MARGIN | 24 | 0.401 | 1.802 | 2.773 | 0.384 | 1.137 | 112.000 |
| NEW_MARGIN | 40 | 0.533 | 1.508 | 2.875 | 0.667 | 1.077 | 112.000 |
| NEW_MARGIN | 60 | 0.413 | 1.615 | 2.506 | 0.402 | 1.113 | 112.000 |

