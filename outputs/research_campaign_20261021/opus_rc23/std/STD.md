# RC23 stage 2 — prospective primary comparison, fresh DEV repeats 51–58, standard startup

Arms (plain name, code alias): RC22 reference (PHR_NRMAP); RC22 candidate, shared upstream (HA_LR); fully lean h + depth (HA_LEAN); h only (HONLY_LR). Selector: margin in every arm.

## AULC (fold-pooled repeat curves; mean and SE over the paired units)

B8–B24:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9352 | 0.0028 | 0.1844 | 0.0052 | 0.0506 | 0.0013 | 0.9300 | 0.0074 | 0.9404 | 0.0029 |
| HA_LR | 0.9332 | 0.0023 | 0.1848 | 0.0047 | 0.0511 | 0.0012 | 0.9228 | 0.0054 | 0.9436 | 0.0038 |
| HONLY_LR | 0.9409 | 0.0016 | 0.2073 | 0.0092 | 0.0548 | 0.0021 | 0.9399 | 0.0036 | 0.9419 | 0.0020 |
| PHR_NRMAP | 0.9296 | 0.0025 | 0.1968 | 0.0056 | 0.0547 | 0.0017 | 0.9225 | 0.0064 | 0.9368 | 0.0042 |

B8–B60:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9474 | 0.0009 | 0.1433 | 0.0023 | 0.0393 | 0.0005 | 0.9403 | 0.0027 | 0.9544 | 0.0015 |
| HA_LR | 0.9465 | 0.0009 | 0.1454 | 0.0023 | 0.0399 | 0.0005 | 0.9381 | 0.0030 | 0.9549 | 0.0018 |
| HONLY_LR | 0.9440 | 0.0010 | 0.1805 | 0.0052 | 0.0480 | 0.0010 | 0.9397 | 0.0022 | 0.9483 | 0.0010 |
| PHR_NRMAP | 0.9436 | 0.0015 | 0.1493 | 0.0027 | 0.0418 | 0.0009 | 0.9366 | 0.0036 | 0.9505 | 0.0021 |

## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0056 | 0.0026 | -0.0037 | 0.0186 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0038 | 0.0017 | -0.0025 | 0.0114 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0124 | 0.0056 | -0.0340 | 0.0154 | 7/8 | BETTER (DEV) |
| all | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0060 | 0.0030 | -0.0194 | 0.0053 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0075 | 0.0056 | -0.0119 | 0.0296 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | specificity | higher | 0.0200 | 0.0036 | 0.0038 | -0.0118 | 0.0215 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0036 | 0.0027 | -0.0061 | 0.0174 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0030 | 0.0016 | -0.0013 | 0.0119 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0119 | 0.0061 | -0.0319 | 0.0241 | 7/8 | BETTER (DEV) |
| all | HA_LR − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0039 | 0.0035 | -0.0144 | 0.0165 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0003 | 0.0053 | -0.0248 | 0.0221 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0068 | 0.0040 | -0.0099 | 0.0212 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0020 | 0.0035 | -0.0182 | 0.0119 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | BA | higher | 0.0200 | 0.0009 | 0.0015 | -0.0067 | 0.0048 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | log_loss | lower | 0.0100 | -0.0004 | 0.0042 | -0.0135 | 0.0196 | 5/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | log_loss | lower | 0.0050 | -0.0021 | 0.0028 | -0.0121 | 0.0105 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | sensitivity | higher | 0.0200 | 0.0072 | 0.0067 | -0.0328 | 0.0257 | 7/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | specificity | higher | 0.0200 | -0.0032 | 0.0024 | -0.0118 | 0.0089 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | -0.0058 | 0.0032 | -0.0240 | 0.0021 | 2/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | 0.0034 | 0.0015 | -0.0036 | 0.0093 | 7/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | log_loss | lower | 0.0100 | -0.0229 | 0.0056 | -0.0551 | 0.0004 | 7/8 | BETTER (DEV) |
| all | HA_LEAN − HONLY_LR | log_loss | lower | 0.0050 | -0.0372 | 0.0042 | -0.0586 | -0.0162 | 8/8 | BETTER (DEV) |
| small | HA_LEAN − HONLY_LR | sensitivity | higher | 0.0200 | -0.0099 | 0.0074 | -0.0445 | 0.0209 | 3/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | specificity | higher | 0.0200 | -0.0016 | 0.0028 | -0.0168 | 0.0079 | 3/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0113 | 0.0028 | -0.0005 | 0.0232 | 7/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0004 | 0.0017 | -0.0053 | 0.0087 | 4/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0100 | 0.0105 | 0.0093 | -0.0134 | 0.0705 | 3/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0312 | 0.0052 | 0.0140 | 0.0631 | 0/8 | WORSE (DEV) |
| small | HONLY_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0175 | 0.0048 | -0.0060 | 0.0337 | 7/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0052 | 0.0033 | -0.0149 | 0.0137 | 6/8 | NOT DIFFERENT (DEV) |

## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)

| window | contrast | metric | mean | se | lower_95 | delta | good | verdict |
|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | 0.0056 | 0.0026 | 0.0006 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0038 | 0.0017 | 0.0005 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LR − PHR_NRMAP | BA | 0.0036 | 0.0027 | -0.0015 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| all | HA_LR − PHR_NRMAP | BA | 0.0030 | 0.0016 | -0.0000 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HA_LR | BA | 0.0020 | 0.0035 | -0.0047 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HA_LR | BA | 0.0009 | 0.0015 | -0.0021 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HONLY_LR | BA | -0.0058 | 0.0032 | -0.0117 | 0.0100 | 2/8 | NON-INFERIORITY NOT SHOWN |
| all | HA_LEAN − HONLY_LR | BA | 0.0034 | 0.0015 | 0.0006 | 0.0100 | 7/8 | NON-INFERIOR (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0113 | 0.0028 | 0.0060 | 0.0100 | 7/8 | NON-INFERIOR (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | 0.0004 | 0.0017 | -0.0028 | 0.0100 | 4/8 | NON-INFERIOR (DEV) |

## BA at fixed budgets (fold-pooled, mean over units)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 8 | 0.886 | 0.881 | 0.891 | 0.284 | 0.084 | 0.229 | 0.698 |
| HA_LEAN | 12 | 0.930 | 0.921 | 0.939 | 0.200 | 0.055 | 0.208 | 0.733 |
| HA_LEAN | 16 | 0.937 | 0.927 | 0.947 | 0.172 | 0.047 | 0.115 | 0.741 |
| HA_LEAN | 20 | 0.943 | 0.938 | 0.949 | 0.158 | 0.043 | 0.167 | 0.756 |
| HA_LEAN | 24 | 0.947 | 0.940 | 0.955 | 0.150 | 0.041 | 0.188 | 0.765 |
| HA_LEAN | 32 | 0.952 | 0.947 | 0.957 | 0.129 | 0.035 | 0.188 | 0.774 |
| HA_LEAN | 40 | 0.953 | 0.947 | 0.960 | 0.122 | 0.034 | 0.219 | 0.779 |
| HA_LEAN | 60 | 0.956 | 0.947 | 0.965 | 0.112 | 0.031 | 0.333 | 0.797 |
| HA_LR | 8 | 0.884 | 0.889 | 0.878 | 0.293 | 0.088 | 0.219 | 0.690 |
| HA_LR | 12 | 0.930 | 0.918 | 0.942 | 0.205 | 0.056 | 0.146 | 0.735 |
| HA_LR | 16 | 0.942 | 0.931 | 0.953 | 0.163 | 0.044 | 0.229 | 0.753 |
| HA_LR | 20 | 0.942 | 0.933 | 0.951 | 0.161 | 0.043 | 0.177 | 0.756 |
| HA_LR | 24 | 0.943 | 0.933 | 0.952 | 0.151 | 0.041 | 0.167 | 0.755 |
| HA_LR | 32 | 0.949 | 0.941 | 0.957 | 0.138 | 0.037 | 0.167 | 0.763 |
| HA_LR | 40 | 0.953 | 0.946 | 0.960 | 0.128 | 0.035 | 0.167 | 0.781 |
| HA_LR | 60 | 0.958 | 0.951 | 0.965 | 0.113 | 0.032 | 0.344 | 0.804 |
| HONLY_LR | 8 | 0.934 | 0.940 | 0.927 | 0.265 | 0.072 | 0.125 | 0.735 |
| HONLY_LR | 12 | 0.941 | 0.942 | 0.940 | 0.218 | 0.057 | 0.052 | 0.738 |
| HONLY_LR | 16 | 0.942 | 0.943 | 0.941 | 0.200 | 0.053 | 0.031 | 0.737 |
| HONLY_LR | 20 | 0.941 | 0.933 | 0.948 | 0.191 | 0.050 | 0.010 | 0.740 |
| HONLY_LR | 24 | 0.944 | 0.939 | 0.949 | 0.184 | 0.049 | 0.000 | 0.751 |
| HONLY_LR | 32 | 0.946 | 0.942 | 0.949 | 0.175 | 0.046 | 0.000 | 0.756 |
| HONLY_LR | 40 | 0.943 | 0.937 | 0.950 | 0.171 | 0.045 | 0.000 | 0.752 |
| HONLY_LR | 60 | 0.945 | 0.937 | 0.953 | 0.153 | 0.042 | 0.000 | 0.759 |
| PHR_NRMAP | 8 | 0.877 | 0.869 | 0.884 | 0.314 | 0.095 | 0.198 | 0.691 |
| PHR_NRMAP | 12 | 0.922 | 0.905 | 0.939 | 0.213 | 0.059 | 0.219 | 0.713 |
| PHR_NRMAP | 16 | 0.942 | 0.945 | 0.940 | 0.179 | 0.048 | 0.156 | 0.755 |
| PHR_NRMAP | 20 | 0.943 | 0.940 | 0.945 | 0.161 | 0.043 | 0.135 | 0.747 |
| PHR_NRMAP | 24 | 0.944 | 0.940 | 0.948 | 0.154 | 0.042 | 0.115 | 0.749 |
| PHR_NRMAP | 32 | 0.946 | 0.940 | 0.952 | 0.142 | 0.039 | 0.167 | 0.755 |
| PHR_NRMAP | 40 | 0.951 | 0.944 | 0.958 | 0.124 | 0.035 | 0.281 | 0.775 |
| PHR_NRMAP | 60 | 0.956 | 0.947 | 0.965 | 0.116 | 0.033 | 0.354 | 0.799 |

## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 8 | 8 | 8 | 8.00 | 6 | 12.25 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 8.00 | 5 | 12.38 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LR | 8 | 8 | 8 | 8.50 | 4 | 12.88 | 13.00 | 0.99 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | PHR_NRMAP | 8 | 8 | 8 | 8.50 | 4 | 12.75 | 13.00 | 0.99 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 8 | 10.00 | 0 | 15.38 | 14.00 | 0.98 |
| BA >= 0.93 | HA_LR | 8 | 8 | 8 | 10.00 | 2 | 14.62 | 14.50 | 0.97 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.00 | 6 | 13.00 | 12.50 | 0.99 |
| BA >= 0.93 | PHR_NRMAP | 8 | 8 | 8 | 12.00 | 0 | 16.62 | 17.00 | 0.98 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 8 | 18.50 | 0 | 32.12 | 31.50 | 0.83 |
| BA >= 0.95 | HA_LR | 8 | 8 | 7 | 24.00 | 0 | 33.29 | 37.00 | 0.90 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 3 | 19.00 | 0 | 29.00 | 25.00 | 0.30 |
| BA >= 0.95 | PHR_NRMAP | 8 | 8 | 8 | 19.00 | 0 | 40.75 | 41.00 | 0.76 |

## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 40 | 40 | 40 | 8.00 | 38 | 12.05 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 40 | 40 | 40 | 8.00 | 36 | 12.15 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 40 | 40 | 40 | 8.00 | 40 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 36 | 12.15 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 40 | 40 | 40 | 8.00 | 27 | 13.03 | 12.00 | 0.98 |
| BA >= 0.90 | HA_LR | 40 | 40 | 40 | 8.00 | 28 | 13.18 | 12.00 | 0.98 |
| BA >= 0.90 | HONLY_LR | 40 | 40 | 40 | 8.00 | 36 | 12.15 | 12.00 | 0.97 |
| BA >= 0.90 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 28 | 13.45 | 12.00 | 0.96 |
| BA >= 0.93 | HA_LEAN | 40 | 40 | 40 | 9.00 | 14 | 17.35 | 13.00 | 0.86 |
| BA >= 0.93 | HA_LR | 40 | 40 | 40 | 8.00 | 21 | 17.52 | 14.00 | 0.86 |
| BA >= 0.93 | HONLY_LR | 40 | 40 | 36 | 8.00 | 23 | 15.03 | 12.50 | 0.87 |
| BA >= 0.93 | PHR_NRMAP | 40 | 40 | 38 | 9.00 | 17 | 16.29 | 14.00 | 0.87 |
| BA >= 0.95 | HA_LEAN | 40 | 40 | 32 | 10.00 | 8 | 20.84 | 15.50 | 0.76 |
| BA >= 0.95 | HA_LR | 40 | 40 | 32 | 11.00 | 6 | 20.91 | 18.00 | 0.75 |
| BA >= 0.95 | HONLY_LR | 40 | 40 | 23 | 9.00 | 12 | 17.17 | 13.00 | 0.88 |
| BA >= 0.95 | PHR_NRMAP | 40 | 40 | 30 | 10.00 | 10 | 22.87 | 18.00 | 0.76 |

## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)

| contrast | target | units | attained_a | attained_b | both_attained | observed_mean_diff_both_attained | restricted_mean_diff(censored=61) | fewer/equal/more(restricted) | per_unit | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/13;12/12;12/12;12/12;12/12;12/12;13/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 2/6/0 | 12/13;13/13;12/12;12/12;13/13;12/12;13/13;12/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -1.25 | -1.25 | 5/1/2 | 14/15;13/17;25/17;14/14;14/21;14/13;15/17;14/19 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -8.62 | -8.62 | 6/0/2 | 24/48;41/32;33/52;42/38;29/31;37/43;21/40;30/42 | FEWER SIMULATIONS (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/13;12/12;12/12;12/12;12/12;12/12;13/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 0/7/1 | 13/13;13/13;12/12;12/12;14/13;12/12;13/13;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -2.00 | -2.00 | 6/1/1 | 15/15;14/17;15/17;12/14;16/21;12/13;19/17;14/19 | FEWER SIMULATIONS (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.95 | 8 | 7 | 8 | 7 | -7.14 | -4.00 | 6/0/2 | 37/48;30/32;18/52;22/38;48/31;–/43;38/40;40/42 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 0/8/0 | 12/12;12/12;12/12;12/12;12/12;12/12;13/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.50 | -0.50 | 3/5/0 | 12/13;13/13;12/12;12/12;13/14;12/12;13/13;12/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | 0.75 | 0.75 | 4/1/3 | 14/15;13/14;25/15;14/12;14/16;14/12;15/19;14/14 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.95 | 8 | 8 | 7 | 7 | -1.86 | -4.62 | 5/0/3 | 24/37;41/30;33/18;42/22;29/48;37/–;21/38;30/40 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 0/7/1 | 12/12;12/12;12/12;12/12;12/12;12/12;13/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.38 | 0.38 | 0/5/3 | 12/12;13/12;12/12;12/12;13/12;12/12;13/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | 2.38 | 2.38 | 1/0/7 | 14/12;13/12;25/13;14/13;14/12;14/12;15/17;14/13 | MORE SIMULATIONS (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.95 | 8 | 8 | 3 | 3 | 8.33 | -16.88 | 6/0/2 | 24/–;41/–;33/48;42/25;29/–;37/14;21/–;30/– | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.25 | -0.25 | 2/6/0 | 12/13;12/12;12/12;12/12;12/12;12/12;12/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.75 | -0.75 | 5/3/0 | 12/13;12/13;12/12;12/12;12/13;12/12;12/13;12/14 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -3.62 | -3.62 | 7/1/0 | 12/15;12/17;13/17;13/14;12/21;12/13;17/17;13/19 | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.95 | 8 | 3 | 8 | 3 | -15.33 | 8.25 | 3/0/5 | –/48;–/32;48/52;25/38;–/31;14/43;–/40;–/42 | NO CLEAR DIFFERENCE (DEV) |

## Decision / training CPU of each arm's own construction (single thread)

| arm | cpu_s_per_step | cpu_s_trajectory |
|---|---|---|
| HA_LEAN | 0.143 | 7.588 |
| HA_LR | 0.463 | 24.543 |
| HONLY_LR | 0.005 | 0.261 |
| PHR_NRMAP | 0.478 | 25.358 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

