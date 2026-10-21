# RC23 stage 3 — geometry blocks (each block withheld from fitting and querying; PHR_NRMAP reused from RC22)

Arms (plain name, code alias): RC22 reference (PHR_NRMAP); RC22 candidate, shared upstream (HA_LR); fully lean h + depth (HA_LEAN); h only (HONLY_LR). Selector: margin in every arm.

## AULC (fold-pooled repeat curves; mean and SE over the paired units)

B8–B24:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9228 | 0.0055 | 0.2114 | 0.0082 | 0.0609 | 0.0031 | 0.9331 | 0.0073 | 0.9124 | 0.0058 |
| HA_LR | 0.9209 | 0.0055 | 0.2154 | 0.0107 | 0.0623 | 0.0038 | 0.9326 | 0.0088 | 0.9091 | 0.0100 |
| HONLY_LR | 0.9364 | 0.0034 | 0.2098 | 0.0060 | 0.0563 | 0.0016 | 0.9416 | 0.0075 | 0.9312 | 0.0048 |
| PHR_NRMAP | 0.8991 | 0.0098 | 0.2520 | 0.0128 | 0.0754 | 0.0047 | 0.9038 | 0.0180 | 0.8944 | 0.0088 |

B8–B60:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9251 | 0.0031 | 0.2035 | 0.0083 | 0.0605 | 0.0027 | 0.9549 | 0.0032 | 0.8953 | 0.0051 |
| HA_LR | 0.9239 | 0.0035 | 0.2100 | 0.0092 | 0.0624 | 0.0031 | 0.9556 | 0.0040 | 0.8922 | 0.0071 |
| HONLY_LR | 0.9454 | 0.0011 | 0.1854 | 0.0041 | 0.0497 | 0.0008 | 0.9486 | 0.0024 | 0.9423 | 0.0012 |
| PHR_NRMAP | 0.9131 | 0.0043 | 0.2384 | 0.0147 | 0.0698 | 0.0038 | 0.9428 | 0.0066 | 0.8835 | 0.0070 |

## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0237 | 0.0087 | 0.0015 | 0.0761 | 8/8 | BETTER (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0120 | 0.0032 | -0.0002 | 0.0294 | 7/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0406 | 0.0100 | -0.0794 | 0.0041 | 7/8 | BETTER (DEV) |
| all | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0349 | 0.0110 | -0.0679 | 0.0195 | 7/8 | BETTER (DEV) |
| small | HA_LEAN − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0293 | 0.0163 | -0.0331 | 0.1132 | 7/8 | BETTER (DEV) |
| small | HA_LEAN − PHR_NRMAP | specificity | higher | 0.0200 | 0.0181 | 0.0094 | -0.0212 | 0.0544 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0218 | 0.0064 | 0.0023 | 0.0522 | 8/8 | BETTER (DEV) |
| all | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0108 | 0.0035 | -0.0085 | 0.0214 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0367 | 0.0105 | -0.0737 | 0.0087 | 7/8 | BETTER (DEV) |
| all | HA_LR − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0284 | 0.0144 | -0.0825 | 0.0350 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0288 | 0.0139 | -0.0233 | 0.0848 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0147 | 0.0130 | -0.0243 | 0.0792 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0019 | 0.0044 | -0.0115 | 0.0239 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0012 | 0.0030 | -0.0086 | 0.0140 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | log_loss | lower | 0.0100 | -0.0040 | 0.0076 | -0.0325 | 0.0221 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | log_loss | lower | 0.0050 | -0.0065 | 0.0103 | -0.0470 | 0.0292 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | sensitivity | higher | 0.0200 | 0.0004 | 0.0066 | -0.0248 | 0.0319 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | specificity | higher | 0.0200 | 0.0034 | 0.0073 | -0.0248 | 0.0354 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | -0.0136 | 0.0026 | -0.0279 | -0.0036 | 0/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | -0.0204 | 0.0022 | -0.0334 | -0.0136 | 0/8 | WORSE (DEV) |
| small | HA_LEAN − HONLY_LR | log_loss | lower | 0.0100 | 0.0016 | 0.0074 | -0.0215 | 0.0419 | 4/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | log_loss | lower | 0.0050 | 0.0181 | 0.0103 | -0.0091 | 0.0793 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | sensitivity | higher | 0.0200 | -0.0085 | 0.0044 | -0.0281 | 0.0096 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | specificity | higher | 0.0200 | -0.0187 | 0.0070 | -0.0439 | 0.0144 | 2/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0373 | 0.0094 | 0.0135 | 0.0907 | 8/8 | BETTER (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0323 | 0.0037 | 0.0183 | 0.0484 | 8/8 | BETTER (DEV) |
| small | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0423 | 0.0094 | -0.0754 | -0.0107 | 8/8 | BETTER (DEV) |
| all | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0530 | 0.0156 | -0.1472 | -0.0116 | 8/8 | BETTER (DEV) |
| small | HONLY_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0378 | 0.0168 | -0.0051 | 0.1221 | 7/8 | BETTER (DEV) |
| small | HONLY_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0368 | 0.0098 | 0.0092 | 0.0911 | 8/8 | BETTER (DEV) |

## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)

| window | contrast | metric | mean | se | lower_95 | delta | good | verdict |
|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | 0.0237 | 0.0087 | 0.0071 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0120 | 0.0032 | 0.0059 | 0.0100 | 7/8 | NON-INFERIOR (DEV) |
| small | HA_LR − PHR_NRMAP | BA | 0.0218 | 0.0064 | 0.0097 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HA_LR − PHR_NRMAP | BA | 0.0108 | 0.0035 | 0.0041 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HA_LR | BA | 0.0019 | 0.0044 | -0.0065 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HA_LR | BA | 0.0012 | 0.0030 | -0.0044 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HONLY_LR | BA | -0.0136 | 0.0026 | -0.0185 | 0.0100 | 0/8 | NON-INFERIORITY NOT SHOWN |
| all | HA_LEAN − HONLY_LR | BA | -0.0204 | 0.0022 | -0.0245 | 0.0100 | 0/8 | NON-INFERIORITY NOT SHOWN |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0373 | 0.0094 | 0.0195 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | 0.0323 | 0.0037 | 0.0253 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |

## BA at fixed budgets (fold-pooled, mean over units)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 8 | 0.855 | 0.832 | 0.877 | 0.314 | 0.097 | 0.125 | 0.696 |
| HA_LEAN | 12 | 0.924 | 0.928 | 0.920 | 0.211 | 0.059 | 0.156 | 0.763 |
| HA_LEAN | 16 | 0.930 | 0.940 | 0.919 | 0.200 | 0.057 | 0.135 | 0.786 |
| HA_LEAN | 20 | 0.932 | 0.949 | 0.915 | 0.186 | 0.054 | 0.094 | 0.795 |
| HA_LEAN | 24 | 0.924 | 0.962 | 0.887 | 0.203 | 0.061 | 0.073 | 0.801 |
| HA_LEAN | 32 | 0.917 | 0.949 | 0.885 | 0.211 | 0.063 | 0.073 | 0.784 |
| HA_LEAN | 40 | 0.924 | 0.963 | 0.886 | 0.201 | 0.061 | 0.094 | 0.800 |
| HA_LEAN | 60 | 0.937 | 0.973 | 0.901 | 0.173 | 0.052 | 0.229 | 0.803 |
| HA_LR | 8 | 0.802 | 0.744 | 0.861 | 0.366 | 0.119 | 0.240 | 0.680 |
| HA_LR | 12 | 0.938 | 0.944 | 0.932 | 0.199 | 0.054 | 0.083 | 0.799 |
| HA_LR | 16 | 0.932 | 0.948 | 0.915 | 0.195 | 0.055 | 0.031 | 0.793 |
| HA_LR | 20 | 0.926 | 0.961 | 0.891 | 0.206 | 0.061 | 0.021 | 0.796 |
| HA_LR | 24 | 0.928 | 0.958 | 0.898 | 0.206 | 0.060 | 0.031 | 0.800 |
| HA_LR | 32 | 0.917 | 0.962 | 0.873 | 0.229 | 0.069 | 0.073 | 0.790 |
| HA_LR | 40 | 0.923 | 0.964 | 0.882 | 0.209 | 0.063 | 0.135 | 0.801 |
| HA_LR | 60 | 0.937 | 0.980 | 0.895 | 0.186 | 0.055 | 0.208 | 0.817 |
| HONLY_LR | 8 | 0.879 | 0.831 | 0.928 | 0.296 | 0.086 | 0.135 | 0.731 |
| HONLY_LR | 12 | 0.938 | 0.939 | 0.936 | 0.207 | 0.054 | 0.042 | 0.799 |
| HONLY_LR | 16 | 0.943 | 0.954 | 0.933 | 0.194 | 0.051 | 0.000 | 0.812 |
| HONLY_LR | 20 | 0.944 | 0.959 | 0.929 | 0.195 | 0.052 | 0.000 | 0.822 |
| HONLY_LR | 24 | 0.947 | 0.957 | 0.936 | 0.194 | 0.051 | 0.000 | 0.823 |
| HONLY_LR | 32 | 0.949 | 0.957 | 0.941 | 0.172 | 0.047 | 0.000 | 0.826 |
| HONLY_LR | 40 | 0.951 | 0.951 | 0.950 | 0.171 | 0.046 | 0.000 | 0.825 |
| HONLY_LR | 60 | 0.951 | 0.945 | 0.956 | 0.165 | 0.045 | 0.000 | 0.823 |
| PHR_NRMAP | 8 | 0.799 | 0.718 | 0.880 | 0.392 | 0.127 | 0.260 | 0.690 |
| PHR_NRMAP | 12 | 0.863 | 0.850 | 0.876 | 0.282 | 0.088 | 0.229 | 0.724 |
| PHR_NRMAP | 16 | 0.923 | 0.935 | 0.911 | 0.215 | 0.061 | 0.198 | 0.777 |
| PHR_NRMAP | 20 | 0.914 | 0.935 | 0.893 | 0.228 | 0.067 | 0.031 | 0.793 |
| PHR_NRMAP | 24 | 0.915 | 0.957 | 0.873 | 0.242 | 0.071 | 0.052 | 0.781 |
| PHR_NRMAP | 32 | 0.913 | 0.958 | 0.868 | 0.258 | 0.074 | 0.094 | 0.786 |
| PHR_NRMAP | 40 | 0.915 | 0.960 | 0.871 | 0.242 | 0.072 | 0.083 | 0.796 |
| PHR_NRMAP | 60 | 0.938 | 0.968 | 0.908 | 0.168 | 0.050 | 0.146 | 0.798 |

## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 8 | 8 | 8 | 8.00 | 5 | 12.50 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 8 | 8 | 8 | 8.00 | 6 | 12.50 | 12.00 | 0.99 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 9.00 | 2 | 13.00 | 13.00 | 0.96 |
| BA >= 0.90 | HA_LR | 8 | 8 | 8 | 9.00 | 3 | 13.12 | 13.00 | 0.99 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.50 | 4 | 12.75 | 12.50 | 1.00 |
| BA >= 0.90 | PHR_NRMAP | 8 | 8 | 8 | 9.50 | 3 | 20.38 | 15.50 | 0.96 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 7 | 9.50 | 1 | 15.43 | 14.00 | 0.52 |
| BA >= 0.93 | HA_LR | 8 | 8 | 8 | 10.00 | 0 | 19.50 | 14.50 | 0.53 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.50 | 4 | 13.50 | 12.50 | 0.99 |
| BA >= 0.93 | PHR_NRMAP | 8 | 8 | 6 | 12.00 | 1 | 27.17 | 24.00 | 0.37 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 0 | 12.00 | 0 | – | – | – |
| BA >= 0.95 | HA_LR | 8 | 8 | 1 | 12.00 | 0 | 55.00 | 55.00 | 0.50 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 8 | 17.50 | 0 | 37.75 | 35.00 | 0.59 |
| BA >= 0.95 | PHR_NRMAP | 8 | 8 | 0 | 16.00 | 0 | – | – | – |

## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 40 | 32 | 17 | 9.00 | 7 | 18.71 | 13.00 | 0.64 |
| BA >= 0.80 | HA_LR | 40 | 32 | 16 | 9.00 | 8 | 24.94 | 23.50 | 0.73 |
| BA >= 0.80 | HONLY_LR | 40 | 32 | 9 | 8.50 | 7 | 15.89 | 12.00 | 0.89 |
| BA >= 0.80 | PHR_NRMAP | 40 | 32 | 18 | 11.50 | 8 | 19.72 | 16.50 | 0.39 |
| BA >= 0.90 | HA_LEAN | 40 | 32 | 8 | 8.00 | 6 | 20.38 | 12.50 | 0.82 |
| BA >= 0.90 | HA_LR | 40 | 32 | 8 | 8.00 | 6 | 27.62 | 32.50 | 0.91 |
| BA >= 0.90 | HONLY_LR | 40 | 32 | 1 | 8.00 | 3 | 12.00 | 12.00 | 0.11 |
| BA >= 0.90 | PHR_NRMAP | 40 | 32 | 7 | 8.00 | 5 | 20.71 | 14.00 | 0.36 |
| BA >= 0.93 | HA_LEAN | 40 | 32 | 8 | 8.00 | 6 | 20.38 | 12.50 | 0.82 |
| BA >= 0.93 | HA_LR | 40 | 32 | 8 | 8.00 | 6 | 27.62 | 32.50 | 0.91 |
| BA >= 0.93 | HONLY_LR | 40 | 32 | 1 | 8.00 | 3 | 12.00 | 12.00 | 0.11 |
| BA >= 0.93 | PHR_NRMAP | 40 | 32 | 7 | 8.00 | 5 | 20.71 | 14.00 | 0.36 |
| BA >= 0.95 | HA_LEAN | 40 | 32 | 8 | 8.00 | 5 | 23.50 | 17.50 | 0.86 |
| BA >= 0.95 | HA_LR | 40 | 32 | 8 | 8.50 | 4 | 27.88 | 32.50 | 0.91 |
| BA >= 0.95 | HONLY_LR | 40 | 32 | 1 | 8.00 | 3 | 12.00 | 12.00 | 0.11 |
| BA >= 0.95 | PHR_NRMAP | 40 | 32 | 7 | 8.50 | 4 | 20.86 | 14.00 | 0.35 |

## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)

| contrast | target | units | attained_a | attained_b | both_attained | observed_mean_diff_both_attained | restricted_mean_diff(censored=61) | fewer/equal/more(restricted) | per_unit | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 2/5/1 | 13/12;12/14;12/12;12/14;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -7.38 | -7.38 | 5/2/1 | 15/56;13/20;13/17;13/20;12/12;13/14;12/12;13/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.93 | 8 | 7 | 6 | 6 | -11.33 | -14.50 | 7/1/0 | –/–;14/49;20/33;22/29;12/18;14/19;13/15;13/– | FEWER SIMULATIONS (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.95 | 8 | 0 | 0 | 0 | – | 0.00 | 0/8/0 | –/–;–/–;–/–;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 2/5/1 | 14/12;13/14;12/12;13/14;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -7.25 | -7.25 | 4/4/0 | 16/56;13/20;13/17;13/20;12/12;14/14;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 6 | 6 | -12.83 | -16.12 | 8/0/0 | 18/–;15/49;14/33;17/29;13/18;14/19;13/15;52/– | FEWER SIMULATIONS (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.95 | 8 | 1 | 0 | 0 | – | -0.75 | 1/7/0 | –/–;–/–;55/–;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 3/5/0 | 13/14;12/13;12/12;12/13;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 2/5/1 | 15/16;13/13;13/13;13/13;12/12;13/14;12/12;13/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.93 | 8 | 7 | 8 | 7 | -4.29 | 1.62 | 3/2/3 | –/18;14/15;20/14;22/17;12/13;14/14;13/13;13/52 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.95 | 8 | 0 | 1 | 0 | – | 0.75 | 0/7/1 | –/–;–/–;–/55;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 0/8/0 | 13/13;12/12;12/12;12/12;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.25 | 0.25 | 0/6/2 | 15/15;13/12;13/13;13/13;12/12;13/13;12/12;13/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.93 | 8 | 7 | 8 | 7 | 2.57 | 7.62 | 0/1/7 | –/18;14/12;20/14;22/15;12/12;14/13;13/12;13/12 | MORE SIMULATIONS (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.95 | 8 | 0 | 8 | 0 | – | 23.25 | 0/0/8 | –/34;–/57;–/36;–/20;–/39;–/57;–/29;–/30 | MORE SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 2/5/1 | 13/12;12/14;12/12;12/14;12/12;12/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -7.62 | -7.62 | 5/3/0 | 15/56;12/20;13/17;13/20;12/12;13/14;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 6 | 6 | -14.17 | -22.12 | 8/0/0 | 18/–;12/49;14/33;15/29;12/18;13/19;12/15;12/– | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 0 | 0 | – | -23.25 | 8/0/0 | 34/–;57/–;36/–;20/–;39/–;57/–;29/–;30/– | FEWER SIMULATIONS (DEV) |

## Decision / training CPU of each arm's own construction (single thread)

| arm | cpu_s_per_step | cpu_s_trajectory |
|---|---|---|
| HA_LEAN | 0.137 | 7.285 |
| HA_LR | 0.474 | 25.129 |
| HONLY_LR | 0.005 | 0.269 |
| PHR_NRMAP | 0.404 | 21.410 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

