# RC23 stage 3 — robustness, startup RAND8 (repeats 35–42; PHR_NRMAP reused from RC21B / RC22)

Arms (plain name, code alias): RC22 reference (PHR_NRMAP); RC22 candidate, shared upstream (HA_LR); fully lean h + depth (HA_LEAN); h only (HONLY_LR). Selector: margin in every arm.

## AULC (fold-pooled repeat curves; mean and SE over the paired units)

B8–B24:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9386 | 0.0026 | 0.1593 | 0.0034 | 0.0447 | 0.0010 | 0.9296 | 0.0063 | 0.9476 | 0.0020 |
| HA_LR | 0.9334 | 0.0033 | 0.1612 | 0.0034 | 0.0460 | 0.0011 | 0.9187 | 0.0090 | 0.9481 | 0.0032 |
| HONLY_LR | 0.9376 | 0.0036 | 0.1689 | 0.0044 | 0.0462 | 0.0014 | 0.9298 | 0.0087 | 0.9454 | 0.0022 |
| PHR_NRMAP | 0.9254 | 0.0059 | 0.1814 | 0.0085 | 0.0519 | 0.0028 | 0.9069 | 0.0113 | 0.9439 | 0.0036 |

B8–B60:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9505 | 0.0016 | 0.1318 | 0.0027 | 0.0365 | 0.0008 | 0.9454 | 0.0034 | 0.9556 | 0.0011 |
| HA_LR | 0.9474 | 0.0016 | 0.1332 | 0.0019 | 0.0375 | 0.0006 | 0.9405 | 0.0041 | 0.9543 | 0.0015 |
| HONLY_LR | 0.9456 | 0.0010 | 0.1545 | 0.0027 | 0.0426 | 0.0006 | 0.9415 | 0.0027 | 0.9497 | 0.0009 |
| PHR_NRMAP | 0.9448 | 0.0021 | 0.1398 | 0.0038 | 0.0396 | 0.0012 | 0.9362 | 0.0037 | 0.9533 | 0.0015 |

## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0131 | 0.0044 | 0.0000 | 0.0350 | 8/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0058 | 0.0011 | 0.0010 | 0.0100 | 8/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0221 | 0.0085 | -0.0733 | 0.0062 | 7/8 | BETTER (DEV) |
| all | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0080 | 0.0046 | -0.0321 | 0.0130 | 7/8 | BETTER (DEV) |
| small | HA_LEAN − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0227 | 0.0077 | -0.0048 | 0.0627 | 7/8 | BETTER (DEV) |
| small | HA_LEAN − PHR_NRMAP | specificity | higher | 0.0200 | 0.0036 | 0.0046 | -0.0091 | 0.0262 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0080 | 0.0037 | -0.0051 | 0.0229 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0026 | 0.0012 | -0.0027 | 0.0075 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0203 | 0.0059 | -0.0479 | 0.0006 | 7/8 | BETTER (DEV) |
| all | HA_LR − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0066 | 0.0035 | -0.0201 | 0.0064 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0118 | 0.0054 | -0.0030 | 0.0406 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0041 | 0.0036 | -0.0104 | 0.0186 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0052 | 0.0016 | -0.0030 | 0.0124 | 7/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0032 | 0.0010 | -0.0009 | 0.0063 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | log_loss | lower | 0.0100 | -0.0019 | 0.0041 | -0.0254 | 0.0113 | 5/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | log_loss | lower | 0.0050 | -0.0014 | 0.0039 | -0.0186 | 0.0163 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | sensitivity | higher | 0.0200 | 0.0109 | 0.0044 | -0.0152 | 0.0221 | 7/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | specificity | higher | 0.0200 | -0.0005 | 0.0029 | -0.0142 | 0.0092 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | 0.0010 | 0.0013 | -0.0029 | 0.0080 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | 0.0049 | 0.0010 | 0.0012 | 0.0096 | 8/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | log_loss | lower | 0.0100 | -0.0096 | 0.0028 | -0.0180 | 0.0063 | 7/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | log_loss | lower | 0.0050 | -0.0227 | 0.0016 | -0.0284 | -0.0134 | 8/8 | BETTER (DEV) |
| small | HA_LEAN − HONLY_LR | sensitivity | higher | 0.0200 | -0.0001 | 0.0042 | -0.0137 | 0.0230 | 3/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | specificity | higher | 0.0200 | 0.0022 | 0.0021 | -0.0070 | 0.0106 | 6/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0121 | 0.0040 | 0.0020 | 0.0366 | 8/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0009 | 0.0014 | -0.0033 | 0.0067 | 4/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0125 | 0.0078 | -0.0608 | 0.0147 | 7/8 | BETTER (DEV) |
| all | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0147 | 0.0035 | -0.0052 | 0.0264 | 1/8 | WORSE (DEV) |
| small | HONLY_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0228 | 0.0066 | -0.0051 | 0.0576 | 7/8 | BETTER (DEV) |
| small | HONLY_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0015 | 0.0033 | -0.0101 | 0.0156 | 4/8 | NOT DIFFERENT (DEV) |

## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)

| window | contrast | metric | mean | se | lower_95 | delta | good | verdict |
|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | 0.0131 | 0.0044 | 0.0049 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0058 | 0.0011 | 0.0037 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| small | HA_LR − PHR_NRMAP | BA | 0.0080 | 0.0037 | 0.0010 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| all | HA_LR − PHR_NRMAP | BA | 0.0026 | 0.0012 | 0.0004 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HA_LR | BA | 0.0052 | 0.0016 | 0.0022 | 0.0100 | 7/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HA_LR | BA | 0.0032 | 0.0010 | 0.0014 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HONLY_LR | BA | 0.0010 | 0.0013 | -0.0014 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HONLY_LR | BA | 0.0049 | 0.0010 | 0.0031 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0121 | 0.0040 | 0.0046 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | 0.0009 | 0.0014 | -0.0017 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |

## BA at fixed budgets (fold-pooled, mean over units)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 8 | 0.910 | 0.887 | 0.934 | 0.223 | 0.064 | 0.229 | 0.726 |
| HA_LEAN | 12 | 0.939 | 0.935 | 0.944 | 0.168 | 0.047 | 0.177 | 0.741 |
| HA_LEAN | 16 | 0.943 | 0.938 | 0.948 | 0.148 | 0.041 | 0.104 | 0.751 |
| HA_LEAN | 20 | 0.946 | 0.940 | 0.952 | 0.142 | 0.040 | 0.094 | 0.762 |
| HA_LEAN | 24 | 0.949 | 0.942 | 0.956 | 0.133 | 0.037 | 0.177 | 0.770 |
| HA_LEAN | 32 | 0.952 | 0.947 | 0.958 | 0.127 | 0.035 | 0.177 | 0.781 |
| HA_LEAN | 40 | 0.957 | 0.954 | 0.960 | 0.119 | 0.033 | 0.188 | 0.791 |
| HA_LEAN | 60 | 0.958 | 0.954 | 0.962 | 0.109 | 0.030 | 0.312 | 0.810 |
| HA_LR | 8 | 0.885 | 0.831 | 0.939 | 0.241 | 0.072 | 0.260 | 0.707 |
| HA_LR | 12 | 0.937 | 0.930 | 0.945 | 0.166 | 0.047 | 0.198 | 0.747 |
| HA_LR | 16 | 0.938 | 0.924 | 0.951 | 0.149 | 0.042 | 0.240 | 0.753 |
| HA_LR | 20 | 0.944 | 0.935 | 0.952 | 0.139 | 0.039 | 0.198 | 0.761 |
| HA_LR | 24 | 0.943 | 0.935 | 0.952 | 0.140 | 0.040 | 0.188 | 0.755 |
| HA_LR | 32 | 0.951 | 0.947 | 0.955 | 0.126 | 0.035 | 0.167 | 0.776 |
| HA_LR | 40 | 0.955 | 0.954 | 0.956 | 0.122 | 0.033 | 0.177 | 0.784 |
| HA_LR | 60 | 0.956 | 0.950 | 0.962 | 0.109 | 0.031 | 0.333 | 0.802 |
| HONLY_LR | 8 | 0.915 | 0.886 | 0.944 | 0.220 | 0.062 | 0.167 | 0.731 |
| HONLY_LR | 12 | 0.933 | 0.919 | 0.948 | 0.178 | 0.049 | 0.146 | 0.738 |
| HONLY_LR | 16 | 0.942 | 0.938 | 0.946 | 0.159 | 0.043 | 0.042 | 0.744 |
| HONLY_LR | 20 | 0.944 | 0.941 | 0.946 | 0.152 | 0.041 | 0.000 | 0.749 |
| HONLY_LR | 24 | 0.946 | 0.944 | 0.949 | 0.150 | 0.041 | 0.000 | 0.754 |
| HONLY_LR | 32 | 0.949 | 0.949 | 0.949 | 0.151 | 0.041 | 0.000 | 0.763 |
| HONLY_LR | 40 | 0.948 | 0.947 | 0.950 | 0.149 | 0.041 | 0.000 | 0.757 |
| HONLY_LR | 60 | 0.949 | 0.944 | 0.954 | 0.144 | 0.040 | 0.000 | 0.767 |
| PHR_NRMAP | 8 | 0.881 | 0.836 | 0.926 | 0.256 | 0.078 | 0.240 | 0.699 |
| PHR_NRMAP | 12 | 0.914 | 0.886 | 0.943 | 0.194 | 0.056 | 0.281 | 0.718 |
| PHR_NRMAP | 16 | 0.936 | 0.926 | 0.947 | 0.169 | 0.047 | 0.229 | 0.739 |
| PHR_NRMAP | 20 | 0.939 | 0.930 | 0.949 | 0.155 | 0.044 | 0.198 | 0.753 |
| PHR_NRMAP | 24 | 0.942 | 0.935 | 0.950 | 0.146 | 0.041 | 0.146 | 0.754 |
| PHR_NRMAP | 32 | 0.948 | 0.944 | 0.953 | 0.132 | 0.037 | 0.188 | 0.762 |
| PHR_NRMAP | 40 | 0.957 | 0.956 | 0.958 | 0.118 | 0.033 | 0.260 | 0.800 |
| PHR_NRMAP | 60 | 0.957 | 0.952 | 0.963 | 0.110 | 0.032 | 0.365 | 0.805 |

## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 8.00 | 6 | 12.62 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LR | 8 | 8 | 8 | 8.50 | 4 | 13.12 | 12.50 | 1.00 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.00 | 6 | 12.50 | 12.00 | 1.00 |
| BA >= 0.90 | PHR_NRMAP | 8 | 8 | 8 | 8.50 | 4 | 13.62 | 12.50 | 0.99 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 8 | 8.50 | 4 | 13.62 | 12.50 | 0.98 |
| BA >= 0.93 | HA_LR | 8 | 8 | 8 | 9.50 | 2 | 13.75 | 13.50 | 0.96 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.00 | 5 | 14.88 | 12.50 | 0.99 |
| BA >= 0.93 | PHR_NRMAP | 8 | 8 | 8 | 10.00 | 2 | 17.62 | 18.50 | 0.98 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 8 | 19.00 | 0 | 32.25 | 30.00 | 0.91 |
| BA >= 0.95 | HA_LR | 8 | 8 | 8 | 24.00 | 0 | 33.38 | 35.00 | 0.93 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 7 | 23.50 | 0 | 34.71 | 33.00 | 0.63 |
| BA >= 0.95 | PHR_NRMAP | 8 | 8 | 8 | 25.00 | 0 | 36.12 | 36.50 | 0.91 |

## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 40 | 40 | 40 | 8.00 | 38 | 12.07 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 40 | 40 | 40 | 8.00 | 35 | 12.15 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 40 | 40 | 40 | 8.00 | 37 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 35 | 12.28 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 40 | 40 | 40 | 8.00 | 28 | 12.75 | 12.00 | 0.98 |
| BA >= 0.90 | HA_LR | 40 | 40 | 40 | 8.00 | 26 | 12.85 | 12.00 | 0.98 |
| BA >= 0.90 | HONLY_LR | 40 | 40 | 40 | 8.00 | 32 | 12.72 | 12.00 | 0.99 |
| BA >= 0.90 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 28 | 13.45 | 12.00 | 0.98 |
| BA >= 0.93 | HA_LEAN | 40 | 40 | 39 | 9.00 | 16 | 17.26 | 13.00 | 0.93 |
| BA >= 0.93 | HA_LR | 40 | 40 | 37 | 9.00 | 18 | 16.46 | 13.00 | 0.94 |
| BA >= 0.93 | HONLY_LR | 40 | 40 | 34 | 8.00 | 21 | 14.68 | 12.50 | 0.96 |
| BA >= 0.93 | PHR_NRMAP | 40 | 40 | 38 | 9.00 | 17 | 17.47 | 13.50 | 0.91 |
| BA >= 0.95 | HA_LEAN | 40 | 40 | 35 | 11.00 | 10 | 21.46 | 18.00 | 0.80 |
| BA >= 0.95 | HA_LR | 40 | 40 | 32 | 12.00 | 9 | 25.16 | 22.50 | 0.83 |
| BA >= 0.95 | HONLY_LR | 40 | 40 | 27 | 9.00 | 12 | 18.67 | 15.00 | 0.86 |
| BA >= 0.95 | PHR_NRMAP | 40 | 40 | 32 | 12.00 | 8 | 23.91 | 23.50 | 0.83 |

## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)

| contrast | target | units | attained_a | attained_b | both_attained | observed_mean_diff_both_attained | restricted_mean_diff(censored=61) | fewer/equal/more(restricted) | per_unit | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/12;12/12;12/12;12/12;12/12;12/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -1.00 | -1.00 | 3/5/0 | 12/17;12/12;12/12;12/12;14/16;15/15;12/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -4.00 | -4.00 | 6/2/0 | 12/19;12/18;12/15;12/12;18/26;17/19;13/13;13/19 | FEWER SIMULATIONS (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -3.88 | -3.88 | 5/0/3 | 45/34;28/35;26/33;26/39;43/40;32/39;33/31;25/38 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 0/8/0 | 12/12;12/12;12/12;12/12;12/12;13/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.50 | -0.50 | 2/5/1 | 13/17;12/12;12/12;12/12;16/16;14/15;14/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -3.88 | -3.88 | 6/1/1 | 14/19;12/18;13/15;12/12;16/26;16/19;14/13;13/19 | FEWER SIMULATIONS (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -2.75 | -2.75 | 5/0/3 | 44/34;30/35;34/33;26/39;37/40;38/39;36/31;22/38 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/12;12/12;12/12;12/12;12/12;12/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.50 | -0.50 | 3/4/1 | 12/13;12/12;12/12;12/12;14/16;15/14;12/14;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 3/3/2 | 12/14;12/12;12/13;12/12;18/16;17/16;13/14;13/13 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.95 | 8 | 8 | 8 | 8 | -1.12 | -1.12 | 4/1/3 | 45/44;28/30;26/34;26/26;43/37;32/38;33/36;25/22 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 0/8/0 | 12/12;12/12;12/12;12/12;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 1/6/1 | 12/12;12/12;12/12;12/12;14/15;15/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | -1.25 | -1.25 | 4/3/1 | 12/13;12/12;12/12;12/12;18/21;17/19;13/12;13/18 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.95 | 8 | 8 | 7 | 7 | -4.29 | -5.75 | 5/0/3 | 45/–;28/32;26/50;26/33;43/41;32/35;33/30;25/22 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/12;12/12;12/12;12/12;12/12;12/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -1.12 | -1.12 | 4/4/0 | 12/17;12/12;12/12;12/12;15/16;13/15;12/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -2.75 | -2.75 | 6/2/0 | 13/19;12/18;12/15;12/12;21/26;19/19;12/13;18/19 | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.95 | 8 | 7 | 8 | 7 | -1.71 | 1.88 | 5/0/3 | –/34;32/35;50/33;33/39;41/40;35/39;30/31;22/38 | NO CLEAR DIFFERENCE (DEV) |

## Decision / training CPU of each arm's own construction (single thread)

| arm | cpu_s_per_step | cpu_s_trajectory |
|---|---|---|
| HA_LEAN | 0.144 | 7.654 |
| HA_LR | 0.493 | 26.114 |
| HONLY_LR | 0.005 | 0.261 |
| PHR_NRMAP | 0.464 | 24.587 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

