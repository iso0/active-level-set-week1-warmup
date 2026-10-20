# RC21 sequential stage — smoke (fresh DEV repeats 27–34; frozen protocol PROTOCOL_RC21_FINAL.md)

**Q1 decision accuracy (co-primary) — NEW_MARGIN − H_MARGIN, BA-AULC over the small window (margin 0.02): INCOMPLETE (0/1)** (mean Δ +nan ± nan SE; better in 0/0 repeats)

**Q2 paid simulations to a confirmed BA >= 0.93 (co-primary) — NEW_MARGIN − H_MARGIN: NO CLEAR DIFFERENCE (DEV)** (restricted mean difference +0.00 simulations; fewer/equal/more 0/1/0; censored 1/1)

**Answer to the main question (better decisions OR fewer paid simulations to the same BA target than the previous strongest model): NO (DEV).** Probability-only improvements (log loss / Brier) are reported below and are not decision superiority.

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 decision accuracy (co-primary) | NEW_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| decision, NEW vs H | NEW_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | small | higher | 0.0200 | 0.0692 | – | 0.0692 | 0.0692 | 1/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | small | higher | 0.0200 | -0.0013 | – | -0.0013 | -0.0013 | 0/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | all | higher | 0.0200 | 0.0377 | – | 0.0377 | 0.0377 | 1/1 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | all | higher | 0.0200 | 0.0030 | – | 0.0030 | 0.0030 | 1/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | -0.0169 | – | -0.0169 | -0.0169 | 1/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | 0.0018 | – | 0.0018 | 0.0018 | 0/1 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | brier | all | lower | 0.0050 | -0.0044 | – | -0.0044 | -0.0044 | 1/1 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | -0.0321 | – | -0.0321 | -0.0321 | 1/1 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | -0.0050 | – | -0.0050 | -0.0050 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | -0.0220 | – | -0.0220 | -0.0220 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | BA | small | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| control | NEW_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0295 | – | -0.0295 | -0.0295 | 1/1 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | – | – | – | – | 0/0 | INCOMPLETE (0/1) |
| control | NEW_MARGIN − G3_MARGIN | log_loss | all | lower | 0.0200 | -0.1463 | – | -0.1463 | -0.1463 | 1/1 | NOT DIFFERENT (DEV) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2100 | – | – | – | 0.0613 | – | 0.9713 | – | 0.8258 | – | 0.9736 | – | 0.7137 | – |
| E1CAL+straddle | 0.2322 | – | – | – | 0.0611 | – | 0.9763 | – | 0.8407 | – | 0.9595 | – | 0.7114 | – |
| E1RAW+straddle | 0.2704 | – | – | – | 0.0623 | – | 0.9802 | – | 0.8779 | – | 0.9467 | – | 0.7006 | – |
| G3_MARGIN | 0.3873 | – | – | – | 0.1100 | – | 0.9186 | – | 0.8042 | – | 0.9727 | – | 0.7090 | – |
| H_MARGIN | 0.2049 | – | – | – | 0.0617 | – | 0.9780 | – | 0.8057 | – | 0.9714 | – | 0.6706 | – |
| NEW_MARGIN | 0.1880 | – | – | – | 0.0501 | – | 0.9859 | – | 0.8749 | – | 0.9702 | – | 0.7475 | – |
| X_MARGIN | 0.1728 | – | – | – | 0.0517 | – | 0.9843 | – | 0.8340 | – | 0.9847 | – | 0.7071 | – |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1355 | – | – | – | 0.0396 | – | 0.9869 | – | 0.8909 | – | 0.9727 | – | 0.7662 | – |
| E1CAL+straddle | 0.1575 | – | – | – | 0.0423 | – | 0.9871 | – | 0.9288 | – | 0.9524 | – | 0.7713 | – |
| E1RAW+straddle | 0.1823 | – | – | – | 0.0440 | – | 0.9887 | – | 0.9470 | – | 0.9452 | – | 0.7700 | – |
| G3_MARGIN | 0.2742 | – | – | – | 0.0744 | – | 0.9526 | – | 0.8679 | – | 0.9713 | – | 0.7353 | – |
| H_MARGIN | 0.1261 | – | – | – | 0.0386 | – | 0.9896 | – | 0.8944 | – | 0.9703 | – | 0.7576 | – |
| NEW_MARGIN | 0.1280 | – | – | – | 0.0342 | – | 0.9923 | – | 0.9322 | – | 0.9733 | – | 0.8170 | – |
| X_MARGIN | 0.1212 | – | – | – | 0.0368 | – | 0.9915 | – | 0.8928 | – | 0.9817 | – | 0.7652 | – |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1CAL+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | E1RAW+straddle | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | G3_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | H_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | NEW_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| BA >= 0.93 | X_MARGIN | 0/1 | 1 | – | – | – | – | – | – |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | E1CAL+straddle | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | E1RAW+straddle | 1/1 | 0 | 14.00 | 20.00 | 20.00 | 20.00 | 20.00 | 20 |
| log_loss <= 0.2 | G3_MARGIN | 1/1 | 0 | 45.00 | 49.00 | 49.00 | 49.00 | 49.00 | 49 |
| log_loss <= 0.2 | H_MARGIN | 1/1 | 0 | 14.00 | 18.00 | 18.00 | 18.00 | 18.00 | 18 |
| log_loss <= 0.2 | NEW_MARGIN | 1/1 | 0 | 13.00 | 17.00 | 17.00 | 17.00 | 17.00 | 17 |
| log_loss <= 0.2 | X_MARGIN | 1/1 | 0 | 11.00 | 15.00 | 15.00 | 15.00 | 15.00 | 15 |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| NEW_MARGIN − H_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| X_MARGIN − H_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − X_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − ATSAPPROX_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1RAW+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1CAL+straddle | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − G3_MARGIN | 0.00 | 0/1/0 | 0 | – | 1/1 | –/– | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − H_MARGIN | -1.00 | 1/0/0 | 1 | -1.00 | 0/0 | 17/18 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| X_MARGIN − H_MARGIN | -3.00 | 1/0/0 | 1 | -3.00 | 0/0 | 15/18 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − X_MARGIN | 2.00 | 0/0/1 | 1 | 2.00 | 0/0 | 17/15 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − ATSAPPROX_MARGIN | 0.00 | 0/1/0 | 1 | 0.00 | 0/0 | 17/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1RAW+straddle | -3.00 | 1/0/0 | 1 | -3.00 | 0/0 | 17/20 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1CAL+straddle | 0.00 | 0/1/0 | 1 | 0.00 | 0/0 | 17/17 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − G3_MARGIN | -32.00 | 1/0/0 | 1 | -32.00 | 0/0 | 17/49 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |

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
| G3_MARGIN | 8 | – | 0.633 | 0.978 | 0.447 | 0.140 | 0.902 | 0.673 | 0.333 |
| G3_MARGIN | 12 | – | 0.696 | 0.971 | 0.462 | 0.142 | 0.845 | 0.651 | 0.000 |
| G3_MARGIN | 16 | – | 0.873 | 0.971 | 0.351 | 0.094 | 0.949 | 0.746 | 0.000 |
| G3_MARGIN | 20 | – | 0.861 | 0.986 | 0.377 | 0.103 | 0.946 | 0.718 | 0.667 |
| G3_MARGIN | 24 | – | 0.848 | 0.993 | 0.352 | 0.096 | 0.940 | 0.740 | 1.000 |
| G3_MARGIN | 32 | – | 0.861 | 0.986 | 0.313 | 0.083 | 0.937 | 0.742 | 0.667 |
| G3_MARGIN | 40 | – | 0.911 | 0.957 | 0.220 | 0.059 | 0.971 | 0.748 | 0.000 |
| G3_MARGIN | 60 | – | 0.924 | 0.978 | 0.158 | 0.039 | 0.990 | 0.792 | 0.667 |
| H_MARGIN | 8 | – | 0.646 | 0.949 | 0.426 | 0.133 | 0.871 | 0.627 | 0.333 |
| H_MARGIN | 12 | – | 0.823 | 0.978 | 0.235 | 0.068 | 0.974 | 0.649 | 0.333 |
| H_MARGIN | 16 | – | 0.810 | 0.964 | 0.171 | 0.049 | 0.988 | 0.582 | 0.333 |
| H_MARGIN | 20 | – | 0.861 | 0.971 | 0.141 | 0.043 | 0.989 | 0.697 | 0.667 |
| H_MARGIN | 24 | – | 0.886 | 0.978 | 0.110 | 0.033 | 0.994 | 0.720 | 0.667 |
| H_MARGIN | 32 | – | 0.949 | 0.971 | 0.085 | 0.025 | 0.996 | 0.818 | 0.333 |
| H_MARGIN | 40 | – | 0.937 | 0.971 | 0.091 | 0.027 | 0.995 | 0.818 | 0.333 |
| H_MARGIN | 60 | – | 0.949 | 0.971 | 0.088 | 0.028 | 0.995 | 0.818 | 0.333 |
| NEW_MARGIN | 8 | – | 0.671 | 0.942 | 0.387 | 0.119 | 0.923 | 0.606 | 0.333 |
| NEW_MARGIN | 12 | – | 0.899 | 0.978 | 0.221 | 0.054 | 0.985 | 0.792 | 0.333 |
| NEW_MARGIN | 16 | – | 0.924 | 0.964 | 0.158 | 0.039 | 0.991 | 0.772 | 0.000 |
| NEW_MARGIN | 20 | – | 0.911 | 0.971 | 0.152 | 0.040 | 0.992 | 0.794 | 0.333 |
| NEW_MARGIN | 24 | – | 0.911 | 0.964 | 0.127 | 0.035 | 0.993 | 0.748 | 0.000 |
| NEW_MARGIN | 32 | – | 0.975 | 0.971 | 0.097 | 0.025 | 0.996 | 0.865 | 0.000 |
| NEW_MARGIN | 40 | – | 0.962 | 0.978 | 0.100 | 0.027 | 0.995 | 0.863 | 0.333 |
| NEW_MARGIN | 60 | – | 0.962 | 0.971 | 0.096 | 0.026 | 0.995 | 0.842 | 0.333 |
| X_MARGIN | 8 | – | 0.620 | 0.957 | 0.419 | 0.131 | 0.889 | 0.649 | 0.667 |
| X_MARGIN | 12 | – | 0.835 | 0.986 | 0.179 | 0.050 | 0.992 | 0.718 | 0.667 |
| X_MARGIN | 16 | – | 0.861 | 0.993 | 0.142 | 0.041 | 0.991 | 0.716 | 1.000 |
| X_MARGIN | 20 | – | 0.873 | 0.986 | 0.140 | 0.043 | 0.993 | 0.742 | 0.667 |
| X_MARGIN | 24 | – | 0.899 | 0.986 | 0.114 | 0.035 | 0.994 | 0.766 | 0.667 |
| X_MARGIN | 32 | – | 0.911 | 0.971 | 0.113 | 0.035 | 0.993 | 0.746 | 0.333 |
| X_MARGIN | 40 | – | 0.911 | 0.978 | 0.109 | 0.034 | 0.992 | 0.768 | 0.667 |
| X_MARGIN | 60 | – | 0.937 | 0.986 | 0.083 | 0.025 | 0.996 | 0.837 | 0.667 |

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
| G3_MARGIN | 24 | 2.517 | 0.202 | 0 | 3 |
| G3_MARGIN | 40 | 1.638 | 0.104 | 3 | 3 |
| G3_MARGIN | 60 | 1.725 | 0.080 | 1 | 3 |
| H_MARGIN | 24 | 1.671 | 0.044 | 1 | 3 |
| H_MARGIN | 40 | 1.357 | 0.021 | 2 | 3 |
| H_MARGIN | 60 | 1.129 | 0.025 | 2 | 3 |
| NEW_MARGIN | 24 | 1.346 | 0.057 | 3 | 3 |
| NEW_MARGIN | 40 | 1.412 | 0.038 | 2 | 3 |
| NEW_MARGIN | 60 | 1.296 | 0.027 | 2 | 3 |
| X_MARGIN | 24 | 1.342 | 0.040 | 1 | 3 |
| X_MARGIN | 40 | 1.205 | 0.027 | 1 | 3 |
| X_MARGIN | 60 | 1.342 | 0.044 | 1 | 3 |

## Short-Keyhole capture (diagnostic)

| arm | budget | shortK_captured | shortK_total |
|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 7 | 9 |
| ATSAPPROX_MARGIN | 60 | 6 | 9 |
| E1CAL+straddle | 24 | 8 | 9 |
| E1CAL+straddle | 60 | 7 | 9 |
| E1RAW+straddle | 24 | 9 | 9 |
| E1RAW+straddle | 60 | 7 | 9 |
| G3_MARGIN | 24 | 4 | 9 |
| G3_MARGIN | 60 | 5 | 9 |
| H_MARGIN | 24 | 4 | 9 |
| H_MARGIN | 60 | 7 | 9 |
| NEW_MARGIN | 24 | 5 | 9 |
| NEW_MARGIN | 60 | 8 | 9 |
| X_MARGIN | 24 | 5 | 9 |
| X_MARGIN | 60 | 6 | 9 |

## Compute: decision CPU (seconds, single thread) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 2 | 4.37 | 8.73 | – | 60.00 |
| E1S | 2 | 25.29 | 50.58 | – | 60.00 |
| G3_MARGIN | 2 | 7.67 | 15.34 | – | 60.00 |
| H_MARGIN | 2 | 42.66 | 85.31 | 0.80 | 60.00 |
| NEW_MARGIN | 2 | 45.03 | 90.06 | 0.85 | 60.00 |
| X_MARGIN | 2 | 41.54 | 83.08 | 0.78 | 60.00 |

## Matched-path by-products on the physical arms' own paths (every budget; exploratory)

| arm | log_loss B8–B24 | BA B8–B24 | sensitivity B8–B24 | specificity B8–B24 | log_loss B8–B60 | BA B8–B60 | sensitivity B8–B60 | specificity B8–B60 |
|---|---|---|---|---|---|---|---|---|
| PHR@H_MARGIN | 0.2389 | – | 0.8012 | 0.9659 | 0.1475 | – | 0.8875 | 0.9677 |
| PHR@NEW_MARGIN | 0.1941 | – | 0.8742 | 0.9702 | 0.1324 | – | 0.9295 | 0.9732 |
| PHR@X_MARGIN | 0.2085 | – | 0.8533 | 0.9757 | 0.1444 | – | 0.9052 | 0.9703 |
| PHR_FX@H_MARGIN | 0.2474 | – | 0.8071 | 0.9714 | 0.1508 | – | 0.8949 | 0.9703 |
| PHR_FX@NEW_MARGIN | 0.2044 | – | 0.8660 | 0.9727 | 0.1372 | – | 0.9293 | 0.9746 |
| PHR_FX@X_MARGIN | 0.2140 | – | 0.8541 | 0.9774 | 0.1461 | – | 0.9116 | 0.9724 |
| PHR_FXMAP@H_MARGIN | 0.2046 | – | 0.8071 | 0.9714 | 0.1260 | – | 0.8949 | 0.9703 |
| PHR_FXMAP@NEW_MARGIN | 0.1661 | – | 0.8660 | 0.9727 | 0.1126 | – | 0.9293 | 0.9746 |
| PHR_FXMAP@X_MARGIN | 0.1707 | – | 0.8541 | 0.9774 | 0.1182 | – | 0.9116 | 0.9724 |
| PHR_NR@H_MARGIN | 0.2349 | – | 0.7975 | 0.9663 | 0.1444 | – | 0.8889 | 0.9683 |
| PHR_NR@NEW_MARGIN | 0.1880 | – | 0.8749 | 0.9702 | 0.1280 | – | 0.9322 | 0.9733 |
| PHR_NR@X_MARGIN | 0.2028 | – | 0.8533 | 0.9774 | 0.1405 | – | 0.9088 | 0.9709 |
| PHR_NRMAP@H_MARGIN | 0.2036 | – | 0.7937 | 0.9621 | 0.1256 | – | 0.8877 | 0.9668 |
| PHR_NRMAP@NEW_MARGIN | 0.1536 | – | 0.8742 | 0.9706 | 0.1080 | – | 0.9322 | 0.9735 |
| PHR_NRMAP@X_MARGIN | 0.1656 | – | 0.8541 | 0.9774 | 0.1168 | – | 0.9088 | 0.9709 |
| SHQ_ATS_H@H_MARGIN | 0.2049 | – | 0.8057 | 0.9714 | 0.1261 | – | 0.8944 | 0.9703 |
| SHQ_ATS_H@NEW_MARGIN | 0.1663 | – | 0.8660 | 0.9727 | 0.1126 | – | 0.9293 | 0.9746 |
| SHQ_ATS_H@X_MARGIN | 0.1709 | – | 0.8526 | 0.9774 | 0.1183 | – | 0.9112 | 0.9724 |
| SHQ_ATS_X@H_MARGIN | 0.2267 | – | 0.7684 | 0.9702 | 0.1349 | – | 0.8660 | 0.9722 |
| SHQ_ATS_X@NEW_MARGIN | 0.1830 | – | 0.8511 | 0.9744 | 0.1217 | – | 0.9169 | 0.9724 |
| SHQ_ATS_X@X_MARGIN | 0.1728 | – | 0.8340 | 0.9847 | 0.1212 | – | 0.8928 | 0.9817 |

Decomposition (paired by repeat): 'model on P's queries' = same paid prefixes, different classifier; 'path' = same classifier, different query paths.

| decomposition | contrast | window | metric | mean | se | repeats_good |
|---|---|---|---|---|---|---|
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0217 | – | 0/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | 0.0089 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | -0.0026 | – | 0/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0153 | – | 0/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | 0.0029 | – | 1/1 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | -0.0012 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0300 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0082 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0051 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0183 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0055 | – | 0/1 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0021 | – | 0/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | log_loss | 0.0319 | – | 0/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | sensitivity | 0.0007 | – | 1/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | specificity | 0.0000 | – | 0/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | log_loss | 0.0222 | – | 0/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | sensitivity | -0.0024 | – | 0/1 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | specificity | -0.0015 | – | 0/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0386 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0603 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | 0.0013 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0135 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0349 | – | 1/1 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0042 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | log_loss | -0.0469 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | sensitivity | 0.0774 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | specificity | 0.0038 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | log_loss | -0.0165 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | sensitivity | 0.0432 | – | 1/1 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | specificity | 0.0051 | – | 1/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0167 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | -0.0149 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | 0.0017 | – | 1/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0091 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | -0.0124 | – | 0/1 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | -0.0022 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0217 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0372 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0013 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0087 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0284 | – | 0/1 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0019 | – | 1/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | log_loss | 0.0019 | – | 0/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | sensitivity | -0.0186 | – | 0/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | specificity | 0.0072 | – | 1/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | log_loss | 0.0029 | – | 0/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | sensitivity | -0.0184 | – | 0/1 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | specificity | 0.0093 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0340 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0469 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | 0.0060 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0078 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0167 | – | 1/1 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0021 | – | 1/1 |

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
| NEW_MARGIN | 12 | 0.469 | 2.047 | 2.668 | 0.516 | 1.129 | 112.000 |
| NEW_MARGIN | 16 | 0.487 | 1.304 | 3.041 | 0.551 | 1.130 | 112.000 |
| NEW_MARGIN | 24 | 0.425 | 2.804 | 2.227 | 0.429 | 1.139 | 112.000 |
| NEW_MARGIN | 40 | 0.425 | 1.390 | 2.608 | 0.430 | 1.118 | 112.000 |
| NEW_MARGIN | 60 | 0.398 | 1.460 | 2.207 | 0.375 | 1.132 | 112.000 |
| X_MARGIN | 8 | 0.472 | 1.809 | 2.822 | 0.522 | 1.126 | 112.000 |
| X_MARGIN | 12 | 0.471 | 1.684 | 2.866 | 0.519 | 1.121 | 112.000 |
| X_MARGIN | 16 | 0.468 | 2.569 | 2.384 | 0.514 | 1.125 | 112.000 |
| X_MARGIN | 24 | 0.479 | 1.932 | 2.408 | 0.536 | 1.114 | 112.000 |
| X_MARGIN | 40 | 0.391 | 1.884 | 2.405 | 0.380 | 1.158 | 112.000 |
| X_MARGIN | 60 | 0.418 | 1.601 | 2.167 | 0.420 | 1.150 | 112.000 |

