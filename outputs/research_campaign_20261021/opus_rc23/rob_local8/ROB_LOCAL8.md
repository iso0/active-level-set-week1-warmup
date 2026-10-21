# RC23 stage 3 — robustness, startup LOCAL8 (repeats 35–42; PHR_NRMAP reused from RC21B / RC22)

Arms (plain name, code alias): RC22 reference (PHR_NRMAP); RC22 candidate, shared upstream (HA_LR); fully lean h + depth (HA_LEAN); h only (HONLY_LR). Selector: margin in every arm.

## AULC (fold-pooled repeat curves; mean and SE over the paired units)

B8–B24:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.8951 | 0.0046 | 0.5472 | 0.0368 | 0.0822 | 0.0035 | 0.8821 | 0.0120 | 0.9082 | 0.0076 |
| HA_LR | 0.8909 | 0.0047 | 0.5566 | 0.0369 | 0.0857 | 0.0035 | 0.8734 | 0.0162 | 0.9083 | 0.0102 |
| HONLY_LR | 0.9077 | 0.0055 | 0.5174 | 0.0350 | 0.0738 | 0.0033 | 0.8953 | 0.0140 | 0.9201 | 0.0062 |
| PHR_NRMAP | 0.8918 | 0.0035 | 0.5449 | 0.0354 | 0.0829 | 0.0026 | 0.8691 | 0.0101 | 0.9145 | 0.0062 |

B8–B60:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9360 | 0.0019 | 0.2578 | 0.0124 | 0.0490 | 0.0015 | 0.9301 | 0.0043 | 0.9420 | 0.0026 |
| HA_LR | 0.9339 | 0.0022 | 0.2653 | 0.0116 | 0.0513 | 0.0013 | 0.9267 | 0.0065 | 0.9410 | 0.0035 |
| HONLY_LR | 0.9359 | 0.0020 | 0.2660 | 0.0117 | 0.0516 | 0.0012 | 0.9303 | 0.0049 | 0.9415 | 0.0020 |
| PHR_NRMAP | 0.9349 | 0.0013 | 0.2555 | 0.0116 | 0.0494 | 0.0009 | 0.9260 | 0.0038 | 0.9437 | 0.0022 |

## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0033 | 0.0030 | -0.0089 | 0.0142 | 5/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0012 | 0.0015 | -0.0049 | 0.0071 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0100 | 0.0023 | 0.0029 | -0.0130 | 0.0121 | 2/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0023 | 0.0017 | -0.0036 | 0.0088 | 3/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0129 | 0.0060 | -0.0173 | 0.0325 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | specificity | higher | 0.0200 | -0.0063 | 0.0044 | -0.0291 | 0.0130 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | -0.0010 | 0.0021 | -0.0081 | 0.0058 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | -0.0010 | 0.0013 | -0.0042 | 0.0041 | 3/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | log_loss | lower | 0.0100 | 0.0118 | 0.0055 | -0.0021 | 0.0465 | 2/8 | NOT DIFFERENT (DEV) |
| all | HA_LR − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0098 | 0.0034 | -0.0044 | 0.0281 | 1/8 | WORSE (DEV) |
| small | HA_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0043 | 0.0071 | -0.0263 | 0.0257 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | specificity | higher | 0.0200 | -0.0062 | 0.0063 | -0.0417 | 0.0133 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0043 | 0.0026 | -0.0008 | 0.0207 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0022 | 0.0017 | -0.0037 | 0.0113 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | log_loss | lower | 0.0100 | -0.0095 | 0.0048 | -0.0344 | 0.0110 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | log_loss | lower | 0.0050 | -0.0075 | 0.0037 | -0.0247 | 0.0047 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | sensitivity | higher | 0.0200 | 0.0086 | 0.0070 | -0.0119 | 0.0537 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | specificity | higher | 0.0200 | -0.0001 | 0.0034 | -0.0123 | 0.0127 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | -0.0126 | 0.0026 | -0.0210 | 0.0033 | 1/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | 0.0002 | 0.0012 | -0.0047 | 0.0072 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | log_loss | lower | 0.0100 | 0.0298 | 0.0072 | -0.0004 | 0.0597 | 1/8 | WORSE (DEV) |
| all | HA_LEAN − HONLY_LR | log_loss | lower | 0.0050 | -0.0082 | 0.0034 | -0.0231 | 0.0070 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | sensitivity | higher | 0.0200 | -0.0133 | 0.0080 | -0.0376 | 0.0364 | 1/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | specificity | higher | 0.0200 | -0.0119 | 0.0039 | -0.0298 | 0.0079 | 1/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0159 | 0.0031 | 0.0041 | 0.0276 | 8/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0010 | 0.0016 | -0.0044 | 0.0084 | 5/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0275 | 0.0073 | -0.0573 | 0.0125 | 7/8 | BETTER (DEV) |
| all | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0105 | 0.0031 | -0.0031 | 0.0265 | 1/8 | WORSE (DEV) |
| small | HONLY_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0262 | 0.0091 | -0.0063 | 0.0621 | 6/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0056 | 0.0057 | -0.0246 | 0.0224 | 5/8 | NOT DIFFERENT (DEV) |

## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)

| window | contrast | metric | mean | se | lower_95 | delta | good | verdict |
|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | 0.0033 | 0.0030 | -0.0024 | 0.0100 | 5/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0012 | 0.0015 | -0.0016 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LR − PHR_NRMAP | BA | -0.0010 | 0.0021 | -0.0050 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| all | HA_LR − PHR_NRMAP | BA | -0.0010 | 0.0013 | -0.0035 | 0.0100 | 3/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HA_LR | BA | 0.0043 | 0.0026 | -0.0007 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HA_LR | BA | 0.0022 | 0.0017 | -0.0011 | 0.0100 | 5/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HONLY_LR | BA | -0.0126 | 0.0026 | -0.0174 | 0.0100 | 1/8 | NON-INFERIORITY NOT SHOWN |
| all | HA_LEAN − HONLY_LR | BA | 0.0002 | 0.0012 | -0.0021 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0159 | 0.0031 | 0.0101 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | 0.0010 | 0.0016 | -0.0020 | 0.0100 | 5/8 | NON-INFERIOR (DEV) |

## BA at fixed budgets (fold-pooled, mean over units)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 8 | 0.573 | 0.463 | 0.683 | 5.036 | 0.386 | 0.521 | 0.551 |
| HA_LEAN | 12 | 0.907 | 0.888 | 0.927 | 0.329 | 0.067 | 0.198 | 0.696 |
| HA_LEAN | 16 | 0.924 | 0.909 | 0.939 | 0.180 | 0.052 | 0.115 | 0.722 |
| HA_LEAN | 20 | 0.942 | 0.937 | 0.948 | 0.149 | 0.042 | 0.083 | 0.753 |
| HA_LEAN | 24 | 0.943 | 0.935 | 0.950 | 0.145 | 0.040 | 0.104 | 0.747 |
| HA_LEAN | 32 | 0.952 | 0.948 | 0.957 | 0.124 | 0.035 | 0.208 | 0.786 |
| HA_LEAN | 40 | 0.957 | 0.956 | 0.957 | 0.118 | 0.033 | 0.219 | 0.792 |
| HA_LEAN | 60 | 0.961 | 0.960 | 0.962 | 0.113 | 0.031 | 0.312 | 0.815 |
| HA_LR | 8 | 0.578 | 0.468 | 0.688 | 5.031 | 0.384 | 0.510 | 0.558 |
| HA_LR | 12 | 0.893 | 0.852 | 0.935 | 0.344 | 0.073 | 0.250 | 0.702 |
| HA_LR | 16 | 0.933 | 0.928 | 0.938 | 0.172 | 0.048 | 0.167 | 0.716 |
| HA_LR | 20 | 0.940 | 0.934 | 0.946 | 0.157 | 0.043 | 0.115 | 0.741 |
| HA_LR | 24 | 0.946 | 0.940 | 0.952 | 0.147 | 0.040 | 0.125 | 0.760 |
| HA_LR | 32 | 0.951 | 0.949 | 0.952 | 0.135 | 0.038 | 0.167 | 0.771 |
| HA_LR | 40 | 0.954 | 0.951 | 0.956 | 0.124 | 0.034 | 0.240 | 0.784 |
| HA_LR | 60 | 0.958 | 0.954 | 0.962 | 0.115 | 0.031 | 0.302 | 0.803 |
| HONLY_LR | 8 | 0.606 | 0.520 | 0.691 | 4.995 | 0.371 | 0.469 | 0.579 |
| HONLY_LR | 12 | 0.924 | 0.907 | 0.940 | 0.306 | 0.058 | 0.135 | 0.729 |
| HONLY_LR | 16 | 0.937 | 0.923 | 0.951 | 0.163 | 0.045 | 0.073 | 0.753 |
| HONLY_LR | 20 | 0.944 | 0.940 | 0.947 | 0.157 | 0.043 | 0.021 | 0.758 |
| HONLY_LR | 24 | 0.946 | 0.943 | 0.949 | 0.152 | 0.042 | 0.010 | 0.761 |
| HONLY_LR | 32 | 0.949 | 0.949 | 0.949 | 0.151 | 0.042 | 0.000 | 0.763 |
| HONLY_LR | 40 | 0.949 | 0.947 | 0.951 | 0.148 | 0.041 | 0.000 | 0.766 |
| HONLY_LR | 60 | 0.950 | 0.945 | 0.955 | 0.143 | 0.040 | 0.000 | 0.772 |
| PHR_NRMAP | 8 | 0.580 | 0.473 | 0.688 | 5.028 | 0.384 | 0.500 | 0.559 |
| PHR_NRMAP | 12 | 0.901 | 0.867 | 0.935 | 0.334 | 0.070 | 0.219 | 0.707 |
| PHR_NRMAP | 16 | 0.933 | 0.926 | 0.940 | 0.178 | 0.051 | 0.156 | 0.755 |
| PHR_NRMAP | 20 | 0.939 | 0.931 | 0.947 | 0.154 | 0.044 | 0.188 | 0.755 |
| PHR_NRMAP | 24 | 0.941 | 0.935 | 0.948 | 0.143 | 0.041 | 0.135 | 0.755 |
| PHR_NRMAP | 32 | 0.952 | 0.949 | 0.955 | 0.127 | 0.036 | 0.177 | 0.784 |
| PHR_NRMAP | 40 | 0.958 | 0.956 | 0.959 | 0.117 | 0.033 | 0.292 | 0.803 |
| PHR_NRMAP | 60 | 0.958 | 0.956 | 0.960 | 0.108 | 0.031 | 0.333 | 0.808 |

## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 10.00 | 0 | 14.12 | 14.00 | 1.00 |
| BA >= 0.80 | HA_LR | 8 | 8 | 8 | 10.00 | 0 | 14.25 | 14.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 9.50 | 0 | 13.50 | 13.50 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 8 | 8 | 8 | 10.00 | 0 | 14.12 | 14.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 10.00 | 0 | 15.25 | 14.00 | 1.00 |
| BA >= 0.90 | HA_LR | 8 | 8 | 8 | 11.00 | 0 | 15.62 | 15.00 | 1.00 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 10.00 | 0 | 14.88 | 14.00 | 1.00 |
| BA >= 0.90 | PHR_NRMAP | 8 | 8 | 8 | 11.00 | 0 | 15.50 | 15.00 | 0.99 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 8 | 13.00 | 0 | 18.50 | 17.00 | 0.98 |
| BA >= 0.93 | HA_LR | 8 | 8 | 8 | 13.00 | 0 | 20.00 | 19.00 | 0.98 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 11.00 | 0 | 16.50 | 15.00 | 0.99 |
| BA >= 0.93 | PHR_NRMAP | 8 | 8 | 8 | 13.00 | 0 | 19.38 | 18.50 | 0.95 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 8 | 26.50 | 0 | 34.00 | 34.00 | 0.94 |
| BA >= 0.95 | HA_LR | 8 | 8 | 8 | 25.50 | 0 | 34.12 | 33.50 | 0.92 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 8 | 26.50 | 0 | 40.88 | 41.00 | 0.59 |
| BA >= 0.95 | PHR_NRMAP | 8 | 8 | 8 | 23.50 | 0 | 34.50 | 34.00 | 0.93 |

## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 40 | 40 | 40 | 9.50 | 7 | 13.57 | 13.50 | 1.00 |
| BA >= 0.80 | HA_LR | 40 | 40 | 40 | 9.00 | 8 | 13.53 | 13.00 | 0.99 |
| BA >= 0.80 | HONLY_LR | 40 | 40 | 40 | 9.00 | 10 | 13.28 | 13.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 40 | 40 | 40 | 10.00 | 8 | 13.57 | 14.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 40 | 40 | 40 | 10.00 | 7 | 13.90 | 14.00 | 0.96 |
| BA >= 0.90 | HA_LR | 40 | 40 | 40 | 10.00 | 7 | 15.05 | 14.00 | 0.97 |
| BA >= 0.90 | HONLY_LR | 40 | 40 | 40 | 10.00 | 10 | 14.25 | 14.00 | 0.99 |
| BA >= 0.90 | PHR_NRMAP | 40 | 40 | 40 | 10.00 | 7 | 14.80 | 14.00 | 0.96 |
| BA >= 0.93 | HA_LEAN | 40 | 40 | 39 | 10.00 | 5 | 18.59 | 15.00 | 0.91 |
| BA >= 0.93 | HA_LR | 40 | 40 | 38 | 11.00 | 5 | 19.97 | 16.50 | 0.90 |
| BA >= 0.93 | HONLY_LR | 40 | 40 | 35 | 10.00 | 7 | 15.00 | 14.00 | 0.93 |
| BA >= 0.93 | PHR_NRMAP | 40 | 40 | 39 | 10.50 | 6 | 17.72 | 15.00 | 0.89 |
| BA >= 0.95 | HA_LEAN | 40 | 40 | 34 | 11.50 | 2 | 25.18 | 22.00 | 0.85 |
| BA >= 0.95 | HA_LR | 40 | 40 | 31 | 13.00 | 2 | 23.52 | 21.00 | 0.84 |
| BA >= 0.95 | HONLY_LR | 40 | 40 | 27 | 11.00 | 4 | 18.11 | 16.00 | 0.84 |
| BA >= 0.95 | PHR_NRMAP | 40 | 40 | 34 | 12.00 | 3 | 25.56 | 23.50 | 0.81 |

## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)

| contrast | target | units | attained_a | attained_b | both_attained | observed_mean_diff_both_attained | restricted_mean_diff(censored=61) | fewer/equal/more(restricted) | per_unit | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 2/4/2 | 15/14;13/14;15/14;14/14;14/14;14/15;14/14;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.25 | -0.25 | 3/4/1 | 22/20;14/14;15/16;14/14;14/14;15/15;14/15;14/16 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -0.88 | -0.88 | 5/1/2 | 22/22;17/18;20/16;27/17;14/23;17/19;17/22;14/18 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -0.50 | -0.50 | 3/1/4 | 39/37;30/30;22/40;41/34;36/32;32/33;32/34;40/36 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 0/7/1 | 14/14;14/14;14/14;14/14;14/14;15/15;15/14;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 3/2/3 | 19/20;15/14;15/16;17/14;14/14;16/15;15/15;14/16 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | 0.62 | 0.62 | 3/1/4 | 27/22;20/18;17/16;17/17;18/23;23/19;21/22;17/18 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 5/0/3 | 40/37;23/30;36/40;40/34;28/32;46/33;29/34;31/36 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 3/3/2 | 15/14;13/14;15/14;14/14;14/14;14/15;14/15;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 4/3/1 | 22/19;14/15;15/15;14/17;14/14;15/16;14/15;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | -1.50 | -1.50 | 6/0/2 | 22/27;17/20;20/17;27/17;14/18;17/23;17/21;14/17 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.95 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 3/0/5 | 39/40;30/23;22/36;41/40;36/28;32/46;32/29;40/31 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.62 | 0.62 | 0/3/5 | 15/14;13/13;15/14;14/14;14/13;14/13;14/14;14/13 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.38 | 0.38 | 1/4/3 | 22/20;14/14;15/14;14/14;14/14;15/14;14/15;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | 2.00 | 2.00 | 2/2/4 | 22/24;17/15;20/15;27/15;14/14;17/15;17/20;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.95 | 8 | 8 | 8 | 8 | -6.88 | -6.88 | 7/0/1 | 39/57;30/35;22/28;41/43;36/41;32/41;32/55;40/27 | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.62 | -0.62 | 4/4/0 | 14/14;13/14;14/14;14/14;13/14;13/15;14/14;13/14 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.62 | -0.62 | 3/5/0 | 20/20;14/14;14/16;14/14;14/14;14/15;15/15;14/16 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -2.88 | -2.88 | 7/0/1 | 24/22;15/18;15/16;15/17;14/23;15/19;20/22;14/18 | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | 6.38 | 6.38 | 2/0/6 | 57/37;35/30;28/40;43/34;41/32;41/33;55/34;27/36 | MORE SIMULATIONS (DEV) |

## Decision / training CPU of each arm's own construction (single thread)

| arm | cpu_s_per_step | cpu_s_trajectory |
|---|---|---|
| HA_LEAN | 0.150 | 7.943 |
| HA_LR | 0.501 | 26.546 |
| HONLY_LR | 0.005 | 0.269 |
| PHR_NRMAP | 0.460 | 24.377 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

