# RC23 stage 3 — robustness, startup STD (repeats 35–42; PHR_NRMAP reused from RC21B / RC22)

Arms (plain name, code alias): RC22 reference (PHR_NRMAP); RC22 candidate, shared upstream (HA_LR); fully lean h + depth (HA_LEAN); h only (HONLY_LR). Selector: margin in every arm.

## AULC (fold-pooled repeat curves; mean and SE over the paired units)

B8–B24:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9327 | 0.0018 | 0.1851 | 0.0049 | 0.0512 | 0.0012 | 0.9248 | 0.0057 | 0.9406 | 0.0031 |
| HA_LR | 0.9367 | 0.0022 | 0.1807 | 0.0057 | 0.0494 | 0.0014 | 0.9263 | 0.0063 | 0.9472 | 0.0031 |
| HONLY_LR | 0.9415 | 0.0016 | 0.2075 | 0.0084 | 0.0542 | 0.0020 | 0.9390 | 0.0044 | 0.9440 | 0.0020 |
| PHR_NRMAP | 0.9283 | 0.0036 | 0.1912 | 0.0072 | 0.0537 | 0.0021 | 0.9170 | 0.0085 | 0.9396 | 0.0036 |

B8–B60:

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | brier_mean | brier_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9485 | 0.0009 | 0.1436 | 0.0018 | 0.0395 | 0.0004 | 0.9435 | 0.0029 | 0.9535 | 0.0013 |
| HA_LR | 0.9494 | 0.0013 | 0.1407 | 0.0030 | 0.0386 | 0.0008 | 0.9434 | 0.0031 | 0.9554 | 0.0018 |
| HONLY_LR | 0.9463 | 0.0007 | 0.1804 | 0.0056 | 0.0477 | 0.0012 | 0.9431 | 0.0017 | 0.9495 | 0.0006 |
| PHR_NRMAP | 0.9463 | 0.0017 | 0.1459 | 0.0037 | 0.0404 | 0.0010 | 0.9398 | 0.0034 | 0.9529 | 0.0013 |

## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0044 | 0.0027 | -0.0045 | 0.0157 | 5/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | higher | 0.0200 | 0.0022 | 0.0015 | -0.0023 | 0.0090 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0062 | 0.0059 | -0.0345 | 0.0133 | 5/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0023 | 0.0024 | -0.0109 | 0.0078 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0078 | 0.0052 | -0.0105 | 0.0334 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − PHR_NRMAP | specificity | higher | 0.0200 | 0.0010 | 0.0042 | -0.0162 | 0.0200 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0084 | 0.0029 | 0.0011 | 0.0248 | 8/8 | NOT DIFFERENT (DEV) |
| all | HA_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0031 | 0.0015 | -0.0016 | 0.0094 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | log_loss | lower | 0.0100 | -0.0105 | 0.0049 | -0.0355 | 0.0145 | 7/8 | BETTER (DEV) |
| all | HA_LR − PHR_NRMAP | log_loss | lower | 0.0050 | -0.0052 | 0.0027 | -0.0151 | 0.0085 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0093 | 0.0088 | -0.0230 | 0.0570 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0076 | 0.0049 | -0.0074 | 0.0393 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | BA | higher | 0.0200 | -0.0040 | 0.0015 | -0.0092 | 0.0044 | 1/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | BA | higher | 0.0200 | -0.0009 | 0.0009 | -0.0037 | 0.0022 | 3/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | log_loss | lower | 0.0100 | 0.0044 | 0.0052 | -0.0222 | 0.0266 | 3/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HA_LR | log_loss | lower | 0.0050 | 0.0029 | 0.0025 | -0.0082 | 0.0138 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | sensitivity | higher | 0.0200 | -0.0015 | 0.0049 | -0.0317 | 0.0128 | 4/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HA_LR | specificity | higher | 0.0200 | -0.0065 | 0.0045 | -0.0241 | 0.0133 | 2/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | -0.0088 | 0.0020 | -0.0183 | -0.0033 | 0/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | BA | higher | 0.0200 | 0.0022 | 0.0009 | -0.0018 | 0.0049 | 6/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | log_loss | lower | 0.0100 | -0.0224 | 0.0057 | -0.0425 | 0.0033 | 6/8 | NOT DIFFERENT (DEV) |
| all | HA_LEAN − HONLY_LR | log_loss | lower | 0.0050 | -0.0368 | 0.0042 | -0.0508 | -0.0181 | 8/8 | BETTER (DEV) |
| small | HA_LEAN − HONLY_LR | sensitivity | higher | 0.0200 | -0.0142 | 0.0049 | -0.0361 | 0.0060 | 1/8 | NOT DIFFERENT (DEV) |
| small | HA_LEAN − HONLY_LR | specificity | higher | 0.0200 | -0.0034 | 0.0026 | -0.0145 | 0.0070 | 2/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | 0.0132 | 0.0025 | -0.0003 | 0.0221 | 7/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | higher | 0.0200 | -0.0001 | 0.0013 | -0.0061 | 0.0064 | 3/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0100 | 0.0162 | 0.0053 | -0.0057 | 0.0373 | 1/8 | WORSE (DEV) |
| all | HONLY_LR − PHR_NRMAP | log_loss | lower | 0.0050 | 0.0345 | 0.0041 | 0.0138 | 0.0473 | 0/8 | WORSE (DEV) |
| small | HONLY_LR − PHR_NRMAP | sensitivity | higher | 0.0200 | 0.0221 | 0.0066 | -0.0069 | 0.0430 | 7/8 | BETTER (DEV) |
| small | HONLY_LR − PHR_NRMAP | specificity | higher | 0.0200 | 0.0044 | 0.0040 | -0.0079 | 0.0296 | 5/8 | NOT DIFFERENT (DEV) |

## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)

| window | contrast | metric | mean | se | lower_95 | delta | good | verdict |
|---|---|---|---|---|---|---|---|---|
| small | HA_LEAN − PHR_NRMAP | BA | 0.0044 | 0.0027 | -0.0007 | 0.0100 | 5/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0022 | 0.0015 | -0.0007 | 0.0100 | 5/8 | NON-INFERIOR (DEV) |
| small | HA_LR − PHR_NRMAP | BA | 0.0084 | 0.0029 | 0.0030 | 0.0100 | 8/8 | NON-INFERIOR (DEV) |
| all | HA_LR − PHR_NRMAP | BA | 0.0031 | 0.0015 | 0.0003 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HA_LR | BA | -0.0040 | 0.0015 | -0.0069 | 0.0100 | 1/8 | NON-INFERIOR (DEV) |
| all | HA_LEAN − HA_LR | BA | -0.0009 | 0.0009 | -0.0025 | 0.0100 | 3/8 | NON-INFERIOR (DEV) |
| small | HA_LEAN − HONLY_LR | BA | -0.0088 | 0.0020 | -0.0126 | 0.0100 | 0/8 | NON-INFERIORITY NOT SHOWN |
| all | HA_LEAN − HONLY_LR | BA | 0.0022 | 0.0009 | 0.0006 | 0.0100 | 6/8 | NON-INFERIOR (DEV) |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0132 | 0.0025 | 0.0085 | 0.0100 | 7/8 | NON-INFERIOR (DEV) |
| all | HONLY_LR − PHR_NRMAP | BA | -0.0001 | 0.0013 | -0.0026 | 0.0100 | 3/8 | NON-INFERIOR (DEV) |

## BA at fixed budgets (fold-pooled, mean over units)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 8 | 0.860 | 0.845 | 0.876 | 0.304 | 0.094 | 0.260 | 0.672 |
| HA_LEAN | 12 | 0.937 | 0.933 | 0.940 | 0.198 | 0.054 | 0.208 | 0.741 |
| HA_LEAN | 16 | 0.936 | 0.924 | 0.948 | 0.179 | 0.048 | 0.156 | 0.736 |
| HA_LEAN | 20 | 0.941 | 0.935 | 0.948 | 0.159 | 0.044 | 0.104 | 0.748 |
| HA_LEAN | 24 | 0.946 | 0.940 | 0.951 | 0.143 | 0.039 | 0.156 | 0.760 |
| HA_LEAN | 32 | 0.953 | 0.950 | 0.957 | 0.131 | 0.036 | 0.198 | 0.785 |
| HA_LEAN | 40 | 0.959 | 0.956 | 0.961 | 0.123 | 0.034 | 0.229 | 0.801 |
| HA_LEAN | 60 | 0.959 | 0.954 | 0.964 | 0.113 | 0.031 | 0.344 | 0.814 |
| HA_LR | 8 | 0.891 | 0.891 | 0.891 | 0.276 | 0.081 | 0.208 | 0.689 |
| HA_LR | 12 | 0.933 | 0.914 | 0.951 | 0.195 | 0.053 | 0.229 | 0.741 |
| HA_LR | 16 | 0.942 | 0.937 | 0.947 | 0.174 | 0.047 | 0.146 | 0.749 |
| HA_LR | 20 | 0.946 | 0.940 | 0.952 | 0.155 | 0.042 | 0.188 | 0.762 |
| HA_LR | 24 | 0.948 | 0.945 | 0.951 | 0.146 | 0.040 | 0.177 | 0.773 |
| HA_LR | 32 | 0.953 | 0.951 | 0.956 | 0.131 | 0.036 | 0.198 | 0.786 |
| HA_LR | 40 | 0.958 | 0.957 | 0.959 | 0.123 | 0.033 | 0.240 | 0.800 |
| HA_LR | 60 | 0.957 | 0.951 | 0.963 | 0.110 | 0.031 | 0.354 | 0.805 |
| HONLY_LR | 8 | 0.926 | 0.924 | 0.927 | 0.271 | 0.074 | 0.146 | 0.716 |
| HONLY_LR | 12 | 0.939 | 0.933 | 0.945 | 0.214 | 0.055 | 0.083 | 0.743 |
| HONLY_LR | 16 | 0.945 | 0.944 | 0.946 | 0.199 | 0.051 | 0.021 | 0.752 |
| HONLY_LR | 20 | 0.944 | 0.943 | 0.946 | 0.190 | 0.049 | 0.000 | 0.746 |
| HONLY_LR | 24 | 0.945 | 0.944 | 0.947 | 0.185 | 0.048 | 0.000 | 0.756 |
| HONLY_LR | 32 | 0.947 | 0.946 | 0.948 | 0.180 | 0.047 | 0.000 | 0.758 |
| HONLY_LR | 40 | 0.949 | 0.946 | 0.952 | 0.168 | 0.045 | 0.000 | 0.762 |
| HONLY_LR | 60 | 0.950 | 0.944 | 0.955 | 0.153 | 0.042 | 0.000 | 0.771 |
| PHR_NRMAP | 8 | 0.862 | 0.848 | 0.875 | 0.332 | 0.101 | 0.250 | 0.690 |
| PHR_NRMAP | 12 | 0.929 | 0.924 | 0.934 | 0.204 | 0.057 | 0.188 | 0.742 |
| PHR_NRMAP | 16 | 0.935 | 0.921 | 0.949 | 0.176 | 0.049 | 0.240 | 0.737 |
| PHR_NRMAP | 20 | 0.940 | 0.929 | 0.952 | 0.160 | 0.044 | 0.292 | 0.749 |
| PHR_NRMAP | 24 | 0.945 | 0.936 | 0.953 | 0.150 | 0.041 | 0.260 | 0.771 |
| PHR_NRMAP | 32 | 0.951 | 0.945 | 0.956 | 0.136 | 0.037 | 0.292 | 0.783 |
| PHR_NRMAP | 40 | 0.957 | 0.957 | 0.958 | 0.123 | 0.034 | 0.281 | 0.800 |
| PHR_NRMAP | 60 | 0.957 | 0.951 | 0.964 | 0.110 | 0.031 | 0.354 | 0.806 |

## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 8 | 8 | 8 | 8.00 | 6 | 12.25 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 9.00 | 3 | 12.88 | 13.00 | 1.00 |
| BA >= 0.90 | HA_LR | 8 | 8 | 8 | 9.00 | 3 | 12.88 | 13.00 | 1.00 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | PHR_NRMAP | 8 | 8 | 8 | 9.00 | 3 | 13.00 | 13.00 | 0.99 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 8 | 10.00 | 0 | 14.88 | 14.00 | 0.98 |
| BA >= 0.93 | HA_LR | 8 | 8 | 8 | 9.00 | 1 | 16.00 | 16.00 | 0.99 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.50 | 4 | 13.00 | 12.50 | 0.99 |
| BA >= 0.93 | PHR_NRMAP | 8 | 8 | 8 | 11.50 | 1 | 16.38 | 17.00 | 0.97 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 8 | 25.00 | 0 | 30.88 | 31.00 | 0.92 |
| BA >= 0.95 | HA_LR | 8 | 8 | 8 | 16.00 | 0 | 29.25 | 29.50 | 0.90 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 5 | 21.00 | 0 | 38.80 | 43.00 | 0.70 |
| BA >= 0.95 | PHR_NRMAP | 8 | 8 | 8 | 25.00 | 0 | 30.50 | 29.50 | 0.86 |

## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 40 | 40 | 40 | 8.00 | 33 | 12.22 | 12.00 | 1.00 |
| BA >= 0.80 | HA_LR | 40 | 40 | 40 | 8.00 | 34 | 12.15 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 40 | 40 | 40 | 8.00 | 38 | 12.05 | 12.00 | 1.00 |
| BA >= 0.80 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 33 | 12.22 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 40 | 40 | 40 | 9.00 | 19 | 13.97 | 13.00 | 0.98 |
| BA >= 0.90 | HA_LR | 40 | 40 | 40 | 8.00 | 23 | 13.05 | 12.00 | 0.99 |
| BA >= 0.90 | HONLY_LR | 40 | 40 | 40 | 8.00 | 34 | 12.65 | 12.00 | 0.99 |
| BA >= 0.90 | PHR_NRMAP | 40 | 40 | 40 | 8.00 | 21 | 13.82 | 13.00 | 0.98 |
| BA >= 0.93 | HA_LEAN | 40 | 40 | 38 | 9.00 | 12 | 17.29 | 13.50 | 0.95 |
| BA >= 0.93 | HA_LR | 40 | 40 | 38 | 9.00 | 18 | 17.21 | 13.00 | 0.95 |
| BA >= 0.93 | HONLY_LR | 40 | 40 | 34 | 8.00 | 25 | 14.06 | 12.00 | 0.95 |
| BA >= 0.93 | PHR_NRMAP | 40 | 40 | 40 | 9.00 | 14 | 18.77 | 14.00 | 0.89 |
| BA >= 0.95 | HA_LEAN | 40 | 40 | 33 | 11.00 | 5 | 22.06 | 16.00 | 0.82 |
| BA >= 0.95 | HA_LR | 40 | 40 | 36 | 10.50 | 6 | 22.14 | 17.00 | 0.79 |
| BA >= 0.95 | HONLY_LR | 40 | 40 | 26 | 9.00 | 12 | 15.31 | 13.50 | 0.82 |
| BA >= 0.95 | PHR_NRMAP | 40 | 40 | 35 | 11.50 | 6 | 24.74 | 23.00 | 0.81 |

## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)

| contrast | target | units | attained_a | attained_b | both_attained | observed_mean_diff_both_attained | restricted_mean_diff(censored=61) | fewer/equal/more(restricted) | per_unit | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 12/13;12/12;12/12;12/12;12/12;13/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 2/5/1 | 13/13;12/12;12/12;13/14;12/14;14/14;13/13;14/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -1.50 | -1.50 | 5/1/2 | 14/18;13/12;13/20;21/14;14/18;16/19;14/14;14/16 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | 0.38 | 0.38 | 3/0/5 | 33/30;27/21;33/29;34/33;36/28;29/38;29/36;26/29 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.25 | -0.25 | 2/6/0 | 12/13;12/12;12/12;12/12;12/12;12/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -0.12 | -0.12 | 1/7/0 | 13/13;12/12;12/12;14/14;13/14;14/14;13/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -0.38 | -0.38 | 4/2/2 | 13/18;12/12;20/20;20/14;14/18;18/19;13/14;18/16 | NO CLEAR DIFFERENCE (DEV) |
| HA_LR − PHR_NRMAP | BA >= 0.95 | 8 | 8 | 8 | 8 | -1.25 | -1.25 | 5/0/3 | 27/30;19/21;20/29;34/33;32/28;36/38;27/36;39/29 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 0/7/1 | 12/12;12/12;12/12;12/12;12/12;13/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.00 | 0.00 | 2/5/1 | 13/13;12/12;12/12;13/14;12/13;14/14;13/13;14/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | -1.12 | -1.12 | 3/1/4 | 14/13;13/12;13/20;21/20;14/14;16/18;14/13;14/18 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HA_LR | BA >= 0.95 | 8 | 8 | 8 | 8 | 1.62 | 1.62 | 2/1/5 | 33/27;27/19;33/20;34/34;36/32;29/36;29/27;26/39 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.80 | 8 | 8 | 8 | 8 | 0.12 | 0.12 | 0/7/1 | 12/12;12/12;12/12;12/12;12/12;13/12;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.90 | 8 | 8 | 8 | 8 | 0.88 | 0.88 | 0/3/5 | 13/12;12/12;12/12;13/12;12/12;14/12;13/12;14/12 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.93 | 8 | 8 | 8 | 8 | 1.88 | 1.88 | 1/1/6 | 14/12;13/13;13/12;21/12;14/13;16/17;14/12;14/13 | NO CLEAR DIFFERENCE (DEV) |
| HA_LEAN − HONLY_LR | BA >= 0.95 | 8 | 8 | 5 | 5 | -8.00 | -16.25 | 7/0/1 | 33/–;27/24;33/50;34/–;36/44;29/43;29/33;26/– | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.80 | 8 | 8 | 8 | 8 | -0.25 | -0.25 | 2/6/0 | 12/13;12/12;12/12;12/12;12/12;12/13;12/12;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.90 | 8 | 8 | 8 | 8 | -1.00 | -1.00 | 5/3/0 | 12/13;12/12;12/12;12/14;12/14;12/14;12/13;12/12 | NO CLEAR DIFFERENCE (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.93 | 8 | 8 | 8 | 8 | -3.38 | -3.38 | 7/0/1 | 12/18;13/12;12/20;12/14;13/18;17/19;12/14;13/16 | FEWER SIMULATIONS (DEV) |
| HONLY_LR − PHR_NRMAP | BA >= 0.95 | 8 | 5 | 8 | 5 | 8.40 | 16.62 | 1/0/7 | –/30;24/21;50/29;–/33;44/28;43/38;33/36;–/29 | MORE SIMULATIONS (DEV) |

## Decision / training CPU of each arm's own construction (single thread)

| arm | cpu_s_per_step | cpu_s_trajectory |
|---|---|---|
| HA_LEAN | 0.141 | 7.498 |
| HA_LR | 0.468 | 24.805 |
| HONLY_LR | 0.005 | 0.271 |
| PHR_NRMAP | 0.878 | 46.564 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

