# RC22 part 1a — lawful startups (STD = completed RC21B trajectories, reused; RAND8 / LOCAL8 new)

## Pre-declared contrasts (fold-pooled curves, paired by repeat / seed)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | REF|STD − H|STD | BA | higher | 0.0200 | 0.0030 | 0.0034 | -0.0105 | 0.0157 | 6/8 | NOT DIFFERENT (DEV) |
| all | REF|STD − H|STD | BA | higher | 0.0200 | 0.0012 | 0.0011 | -0.0033 | 0.0049 | 5/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − H|STD | log_loss | lower | 0.0100 | -0.0298 | 0.0048 | -0.0434 | -0.0116 | 8/8 | BETTER (DEV) |
| all | REF|STD − H|STD | log_loss | lower | 0.0050 | -0.0123 | 0.0024 | -0.0215 | -0.0034 | 8/8 | BETTER (DEV) |
| small | REF|STD − E1RAW+straddle|STD | BA | higher | 0.0200 | 0.0186 | 0.0043 | 0.0027 | 0.0354 | 8/8 | NOT DIFFERENT (DEV) |
| all | REF|STD − E1RAW+straddle|STD | BA | higher | 0.0200 | 0.0094 | 0.0015 | 0.0029 | 0.0162 | 8/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − E1RAW+straddle|STD | log_loss | lower | 0.0100 | -0.1867 | 0.0317 | -0.3581 | -0.0937 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1RAW+straddle|STD | log_loss | lower | 0.0050 | -0.0968 | 0.0106 | -0.1539 | -0.0586 | 8/8 | BETTER (DEV) |
| small | REF|STD − E1CAL+straddle|STD | BA | higher | 0.0200 | 0.0385 | 0.0053 | 0.0203 | 0.0638 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1CAL+straddle|STD | BA | higher | 0.0200 | 0.0196 | 0.0021 | 0.0126 | 0.0296 | 8/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − E1CAL+straddle|STD | log_loss | lower | 0.0100 | -0.1269 | 0.0157 | -0.2117 | -0.0730 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1CAL+straddle|STD | log_loss | lower | 0.0050 | -0.0644 | 0.0058 | -0.0975 | -0.0511 | 8/8 | BETTER (DEV) |
| small | REF|RAND8 − H|RAND8 | BA | higher | 0.0200 | 0.0042 | 0.0038 | -0.0108 | 0.0226 | 5/8 | NOT DIFFERENT (DEV) |
| all | REF|RAND8 − H|RAND8 | BA | higher | 0.0200 | 0.0004 | 0.0019 | -0.0053 | 0.0105 | 4/8 | NOT DIFFERENT (DEV) |
| small | REF|RAND8 − H|RAND8 | log_loss | lower | 0.0100 | -0.0181 | 0.0056 | -0.0383 | 0.0014 | 6/8 | NOT DIFFERENT (DEV) |
| all | REF|RAND8 − H|RAND8 | log_loss | lower | 0.0050 | -0.0062 | 0.0033 | -0.0188 | 0.0061 | 6/8 | NOT DIFFERENT (DEV) |
| small | REF|RAND8 − E1RAW+straddle|RAND8 | BA | higher | 0.0200 | 0.0164 | 0.0067 | -0.0130 | 0.0405 | 6/8 | NOT DIFFERENT (DEV) |
| all | REF|RAND8 − E1RAW+straddle|RAND8 | BA | higher | 0.0200 | 0.0068 | 0.0030 | -0.0085 | 0.0166 | 6/8 | NOT DIFFERENT (DEV) |
| small | REF|RAND8 − E1RAW+straddle|RAND8 | log_loss | lower | 0.0100 | -0.2278 | 0.0205 | -0.3334 | -0.1254 | 8/8 | BETTER (DEV) |
| all | REF|RAND8 − E1RAW+straddle|RAND8 | log_loss | lower | 0.0050 | -0.1083 | 0.0110 | -0.1394 | -0.0520 | 8/8 | BETTER (DEV) |
| small | REF|RAND8 − E1CAL+straddle|RAND8 | BA | higher | 0.0200 | 0.0240 | 0.0070 | -0.0093 | 0.0597 | 7/8 | BETTER (DEV) |
| all | REF|RAND8 − E1CAL+straddle|RAND8 | BA | higher | 0.0200 | 0.0122 | 0.0033 | -0.0030 | 0.0300 | 7/8 | NOT DIFFERENT (DEV) |
| small | REF|RAND8 − E1CAL+straddle|RAND8 | log_loss | lower | 0.0100 | -0.1291 | 0.0124 | -0.1699 | -0.0881 | 8/8 | BETTER (DEV) |
| all | REF|RAND8 − E1CAL+straddle|RAND8 | log_loss | lower | 0.0050 | -0.0590 | 0.0059 | -0.0801 | -0.0283 | 8/8 | BETTER (DEV) |
| small | REF|LOCAL8 − H|LOCAL8 | BA | higher | 0.0200 | 0.0137 | 0.0037 | -0.0020 | 0.0255 | 7/8 | NOT DIFFERENT (DEV) |
| all | REF|LOCAL8 − H|LOCAL8 | BA | higher | 0.0200 | 0.0060 | 0.0010 | 0.0010 | 0.0095 | 8/8 | NOT DIFFERENT (DEV) |
| small | REF|LOCAL8 − H|LOCAL8 | log_loss | lower | 0.0100 | -0.1118 | 0.0277 | -0.2578 | -0.0240 | 8/8 | BETTER (DEV) |
| all | REF|LOCAL8 − H|LOCAL8 | log_loss | lower | 0.0050 | -0.0420 | 0.0087 | -0.0852 | -0.0102 | 8/8 | BETTER (DEV) |
| small | REF|LOCAL8 − E1RAW+straddle|LOCAL8 | BA | higher | 0.0200 | 0.0421 | 0.0072 | 0.0151 | 0.0729 | 8/8 | BETTER (DEV) |
| all | REF|LOCAL8 − E1RAW+straddle|LOCAL8 | BA | higher | 0.0200 | 0.0194 | 0.0031 | 0.0086 | 0.0319 | 8/8 | NOT DIFFERENT (DEV) |
| small | REF|LOCAL8 − E1RAW+straddle|LOCAL8 | log_loss | lower | 0.0100 | -0.3673 | 0.0342 | -0.5524 | -0.2201 | 8/8 | BETTER (DEV) |
| all | REF|LOCAL8 − E1RAW+straddle|LOCAL8 | log_loss | lower | 0.0050 | -0.1791 | 0.0151 | -0.2551 | -0.1261 | 8/8 | BETTER (DEV) |
| small | REF|LOCAL8 − E1CAL+straddle|LOCAL8 | BA | higher | 0.0200 | 0.0506 | 0.0082 | 0.0194 | 0.0809 | 8/8 | BETTER (DEV) |
| all | REF|LOCAL8 − E1CAL+straddle|LOCAL8 | BA | higher | 0.0200 | 0.0247 | 0.0029 | 0.0140 | 0.0346 | 8/8 | BETTER (DEV) |
| small | REF|LOCAL8 − E1CAL+straddle|LOCAL8 | log_loss | lower | 0.0100 | -0.1797 | 0.0161 | -0.2255 | -0.1020 | 8/8 | BETTER (DEV) |
| all | REF|LOCAL8 − E1CAL+straddle|LOCAL8 | log_loss | lower | 0.0050 | -0.0946 | 0.0100 | -0.1456 | -0.0679 | 8/8 | BETTER (DEV) |
| small | REF|RAND8 − REF|STD | BA | higher | 0.0200 | -0.0028 | 0.0050 | -0.0290 | 0.0131 | 4/8 | NOT DIFFERENT (DEV) |
| all | REF|RAND8 − REF|STD | BA | higher | 0.0200 | -0.0016 | 0.0015 | -0.0091 | 0.0030 | 4/8 | NOT DIFFERENT (DEV) |
| small | REF|RAND8 − REF|STD | log_loss | lower | 0.0100 | -0.0098 | 0.0093 | -0.0576 | 0.0209 | 6/8 | NOT DIFFERENT (DEV) |
| all | REF|RAND8 − REF|STD | log_loss | lower | 0.0050 | -0.0061 | 0.0051 | -0.0334 | 0.0164 | 6/8 | NOT DIFFERENT (DEV) |
| small | REF|LOCAL8 − REF|STD | BA | higher | 0.0200 | -0.0365 | 0.0030 | -0.0537 | -0.0247 | 0/8 | WORSE (DEV) |
| all | REF|LOCAL8 − REF|STD | BA | higher | 0.0200 | -0.0115 | 0.0012 | -0.0175 | -0.0066 | 0/8 | NOT DIFFERENT (DEV) |
| small | REF|LOCAL8 − REF|STD | log_loss | lower | 0.0100 | 0.3536 | 0.0337 | 0.2425 | 0.4789 | 0/8 | WORSE (DEV) |
| all | REF|LOCAL8 − REF|STD | log_loss | lower | 0.0050 | 0.1096 | 0.0118 | 0.0704 | 0.1528 | 0/8 | WORSE (DEV) |
| small | H|RAND8 − H|STD | BA | higher | 0.0200 | -0.0041 | 0.0030 | -0.0161 | 0.0064 | 3/8 | NOT DIFFERENT (DEV) |
| all | H|RAND8 − H|STD | BA | higher | 0.0200 | -0.0009 | 0.0017 | -0.0063 | 0.0071 | 4/8 | NOT DIFFERENT (DEV) |
| small | H|RAND8 − H|STD | log_loss | lower | 0.0100 | -0.0216 | 0.0040 | -0.0349 | -0.0084 | 8/8 | BETTER (DEV) |
| all | H|RAND8 − H|STD | log_loss | lower | 0.0050 | -0.0121 | 0.0021 | -0.0218 | -0.0049 | 8/8 | BETTER (DEV) |
| small | H|LOCAL8 − H|STD | BA | higher | 0.0200 | -0.0471 | 0.0069 | -0.0726 | -0.0166 | 0/8 | WORSE (DEV) |
| all | H|LOCAL8 − H|STD | BA | higher | 0.0200 | -0.0163 | 0.0022 | -0.0244 | -0.0050 | 0/8 | NOT DIFFERENT (DEV) |
| small | H|LOCAL8 − H|STD | log_loss | lower | 0.0100 | 0.4356 | 0.0584 | 0.2271 | 0.6800 | 0/8 | WORSE (DEV) |
| all | H|LOCAL8 − H|STD | log_loss | lower | 0.0050 | 0.1393 | 0.0188 | 0.0668 | 0.2222 | 0/8 | WORSE (DEV) |
| small | E1RAW+straddle|RAND8 − E1RAW+straddle|STD | BA | higher | 0.0200 | -0.0007 | 0.0079 | -0.0370 | 0.0319 | 4/8 | NOT DIFFERENT (DEV) |
| all | E1RAW+straddle|RAND8 − E1RAW+straddle|STD | BA | higher | 0.0200 | 0.0010 | 0.0034 | -0.0118 | 0.0163 | 4/8 | NOT DIFFERENT (DEV) |
| small | E1RAW+straddle|RAND8 − E1RAW+straddle|STD | log_loss | lower | 0.0100 | 0.0312 | 0.0408 | -0.1462 | 0.2193 | 2/8 | NOT DIFFERENT (DEV) |
| all | E1RAW+straddle|RAND8 − E1RAW+straddle|STD | log_loss | lower | 0.0050 | 0.0054 | 0.0150 | -0.0419 | 0.0700 | 4/8 | NOT DIFFERENT (DEV) |
| small | E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | BA | higher | 0.0200 | -0.0600 | 0.0084 | -0.0929 | -0.0324 | 0/8 | WORSE (DEV) |
| all | E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | BA | higher | 0.0200 | -0.0214 | 0.0031 | -0.0325 | -0.0088 | 0/8 | WORSE (DEV) |
| small | E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | log_loss | lower | 0.0100 | 0.5341 | 0.0669 | 0.2715 | 0.8102 | 0/8 | WORSE (DEV) |
| all | E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | log_loss | lower | 0.0050 | 0.1920 | 0.0182 | 0.0911 | 0.2614 | 0/8 | WORSE (DEV) |

## AULC B8–B24

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| E1CAL+straddle|LOCAL8 | 0.8412 | 0.0088 | 0.7246 | 0.0395 | 0.8070 | 0.0210 | 0.8754 | 0.0101 | 0.1219 | 0.0045 |
| E1CAL+straddle|RAND8 | 0.9015 | 0.0075 | 0.3105 | 0.0068 | 0.8769 | 0.0172 | 0.9260 | 0.0068 | 0.0733 | 0.0033 |
| E1CAL+straddle|STD | 0.8898 | 0.0071 | 0.3181 | 0.0186 | 0.8697 | 0.0156 | 0.9098 | 0.0059 | 0.0812 | 0.0035 |
| E1RAW+straddle|LOCAL8 | 0.8498 | 0.0079 | 0.9121 | 0.0553 | 0.8349 | 0.0201 | 0.8647 | 0.0093 | 0.1223 | 0.0042 |
| E1RAW+straddle|RAND8 | 0.9090 | 0.0057 | 0.4092 | 0.0155 | 0.9065 | 0.0145 | 0.9115 | 0.0081 | 0.0735 | 0.0033 |
| E1RAW+straddle|STD | 0.9097 | 0.0037 | 0.3780 | 0.0343 | 0.9329 | 0.0059 | 0.8866 | 0.0079 | 0.0759 | 0.0039 |
| H|LOCAL8 | 0.8781 | 0.0067 | 0.6566 | 0.0577 | 0.8489 | 0.0147 | 0.9074 | 0.0080 | 0.0951 | 0.0048 |
| H|RAND8 | 0.9212 | 0.0047 | 0.1995 | 0.0044 | 0.8930 | 0.0115 | 0.9495 | 0.0035 | 0.0555 | 0.0016 |
| H|STD | 0.9253 | 0.0047 | 0.2211 | 0.0044 | 0.9087 | 0.0102 | 0.9419 | 0.0015 | 0.0602 | 0.0016 |
| REF|LOCAL8 | 0.8918 | 0.0035 | 0.5449 | 0.0354 | 0.8691 | 0.0101 | 0.9145 | 0.0062 | 0.0829 | 0.0026 |
| REF|RAND8 | 0.9254 | 0.0059 | 0.1814 | 0.0085 | 0.9069 | 0.0113 | 0.9439 | 0.0036 | 0.0519 | 0.0028 |
| REF|STD | 0.9283 | 0.0036 | 0.1912 | 0.0072 | 0.9170 | 0.0085 | 0.9396 | 0.0036 | 0.0537 | 0.0021 |

## AULC B8–B60

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| E1CAL+straddle|LOCAL8 | 0.9102 | 0.0031 | 0.3502 | 0.0140 | 0.8910 | 0.0058 | 0.9294 | 0.0027 | 0.0680 | 0.0021 |
| E1CAL+straddle|RAND8 | 0.9326 | 0.0031 | 0.1988 | 0.0050 | 0.9186 | 0.0061 | 0.9466 | 0.0027 | 0.0498 | 0.0017 |
| E1CAL+straddle|STD | 0.9267 | 0.0027 | 0.2103 | 0.0082 | 0.9135 | 0.0057 | 0.9400 | 0.0023 | 0.0544 | 0.0015 |
| E1RAW+straddle|LOCAL8 | 0.9155 | 0.0032 | 0.4346 | 0.0184 | 0.9129 | 0.0059 | 0.9182 | 0.0028 | 0.0690 | 0.0021 |
| E1RAW+straddle|RAND8 | 0.9379 | 0.0026 | 0.2481 | 0.0090 | 0.9413 | 0.0059 | 0.9345 | 0.0043 | 0.0508 | 0.0020 |
| E1RAW+straddle|STD | 0.9369 | 0.0014 | 0.2427 | 0.0123 | 0.9485 | 0.0035 | 0.9254 | 0.0030 | 0.0526 | 0.0015 |
| H|LOCAL8 | 0.9289 | 0.0017 | 0.2975 | 0.0187 | 0.9164 | 0.0038 | 0.9413 | 0.0030 | 0.0542 | 0.0016 |
| H|RAND8 | 0.9443 | 0.0020 | 0.1461 | 0.0024 | 0.9329 | 0.0043 | 0.9557 | 0.0016 | 0.0405 | 0.0008 |
| H|STD | 0.9452 | 0.0020 | 0.1582 | 0.0020 | 0.9358 | 0.0042 | 0.9546 | 0.0009 | 0.0429 | 0.0007 |
| REF|LOCAL8 | 0.9349 | 0.0013 | 0.2555 | 0.0116 | 0.9260 | 0.0038 | 0.9437 | 0.0022 | 0.0494 | 0.0009 |
| REF|RAND8 | 0.9448 | 0.0021 | 0.1398 | 0.0038 | 0.9362 | 0.0037 | 0.9533 | 0.0015 | 0.0396 | 0.0012 |
| REF|STD | 0.9463 | 0.0017 | 0.1459 | 0.0037 | 0.9398 | 0.0034 | 0.9529 | 0.0013 | 0.0404 | 0.0010 |

## Target attainment of the fold-pooled curves

| target | arm | confirmed | spend_mean | spend_max |
|---|---|---|---|---|
| BA >= 0.93 | E1CAL+straddle|LOCAL8 | 8/8 | 29.25 | 40.00 |
| BA >= 0.93 | E1CAL+straddle|RAND8 | 8/8 | 24.38 | 31.00 |
| BA >= 0.93 | E1CAL+straddle|STD | 8/8 | 25.38 | 35.00 |
| BA >= 0.93 | E1RAW+straddle|LOCAL8 | 8/8 | 27.75 | 35.00 |
| BA >= 0.93 | E1RAW+straddle|RAND8 | 8/8 | 22.88 | 29.00 |
| BA >= 0.93 | E1RAW+straddle|STD | 8/8 | 24.25 | 30.00 |
| BA >= 0.93 | H|LOCAL8 | 8/8 | 20.00 | 28.00 |
| BA >= 0.93 | H|RAND8 | 8/8 | 19.00 | 26.00 |
| BA >= 0.93 | H|STD | 8/8 | 16.75 | 23.00 |
| BA >= 0.93 | REF|LOCAL8 | 8/8 | 19.38 | 23.00 |
| BA >= 0.93 | REF|RAND8 | 8/8 | 17.62 | 26.00 |
| BA >= 0.93 | REF|STD | 8/8 | 16.38 | 20.00 |
| BA >= 0.95 | E1CAL+straddle|LOCAL8 | 7/8 | 51.29 | 59.00 |
| BA >= 0.95 | E1CAL+straddle|RAND8 | 7/8 | 42.14 | 56.00 |
| BA >= 0.95 | E1CAL+straddle|STD | 6/8 | 42.67 | 57.00 |
| BA >= 0.95 | E1RAW+straddle|LOCAL8 | 8/8 | 46.62 | 58.00 |
| BA >= 0.95 | E1RAW+straddle|RAND8 | 8/8 | 37.12 | 56.00 |
| BA >= 0.95 | E1RAW+straddle|STD | 7/8 | 35.86 | 44.00 |
| BA >= 0.95 | H|LOCAL8 | 8/8 | 32.00 | 40.00 |
| BA >= 0.95 | H|RAND8 | 8/8 | 30.38 | 44.00 |
| BA >= 0.95 | H|STD | 8/8 | 29.62 | 36.00 |
| BA >= 0.95 | REF|LOCAL8 | 8/8 | 34.50 | 40.00 |
| BA >= 0.95 | REF|RAND8 | 8/8 | 36.12 | 40.00 |
| BA >= 0.95 | REF|STD | 8/8 | 30.50 | 38.00 |
| log_loss <= 0.2 | E1CAL+straddle|LOCAL8 | 8/8 | 34.62 | 47.00 |
| log_loss <= 0.2 | E1CAL+straddle|RAND8 | 8/8 | 25.25 | 28.00 |
| log_loss <= 0.2 | E1CAL+straddle|STD | 8/8 | 27.75 | 34.00 |
| log_loss <= 0.2 | E1RAW+straddle|LOCAL8 | 7/8 | 37.86 | 54.00 |
| log_loss <= 0.2 | E1RAW+straddle|RAND8 | 8/8 | 29.62 | 38.00 |
| log_loss <= 0.2 | E1RAW+straddle|STD | 8/8 | 30.75 | 34.00 |
| log_loss <= 0.2 | H|LOCAL8 | 8/8 | 19.00 | 21.00 |
| log_loss <= 0.2 | H|RAND8 | 8/8 | 17.50 | 19.00 |
| log_loss <= 0.2 | H|STD | 8/8 | 20.62 | 24.00 |
| log_loss <= 0.2 | REF|LOCAL8 | 8/8 | 17.12 | 20.00 |
| log_loss <= 0.2 | REF|RAND8 | 8/8 | 14.00 | 17.00 |
| log_loss <= 0.2 | REF|STD | 8/8 | 16.88 | 22.00 |

| contrast | target | restricted_mean_difference(censored=64) | fewer/equal/more | censored_a/b | per_unit | verdict |
|---|---|---|---|---|---|---|
| REF|STD − H|STD | BA >= 0.93 | -0.38 | 4/1/3 | 0/0 | 18/14;12/14;20/16;14/15;18/16;19/23;14/20;16/16 | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − H|STD | BA >= 0.95 | 0.88 | 4/0/4 | 0/0 | 30/32;21/22;29/24;33/35;28/26;38/36;36/26;29/36 | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − H|STD | log_loss <= 0.2 | -3.75 | 7/0/1 | 0/0 | 22/24;13/19;19/18;15/21;16/20;18/20;14/20;18/23 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1RAW+straddle|STD | BA >= 0.93 | -7.88 | 8/0/0 | 0/0 | 18/26;12/23;20/27;14/22;18/21;19/23;14/22;16/30 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1RAW+straddle|STD | BA >= 0.95 | -8.88 | 7/0/1 | 0/1 | 30/34;21/30;29/42;33/35;28/–;38/44;36/29;29/37 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1RAW+straddle|STD | log_loss <= 0.2 | -13.88 | 8/0/0 | 0/0 | 22/34;13/26;19/34;15/32;16/31;18/34;14/23;18/32 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1CAL+straddle|STD | BA >= 0.93 | -9.00 | 8/0/0 | 0/0 | 18/26;12/14;20/34;14/25;18/21;19/23;14/25;16/35 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1CAL+straddle|STD | BA >= 0.95 | -17.50 | 7/0/1 | 0/2 | 30/34;21/26;29/–;33/55;28/57;38/34;36/–;29/50 | FEWER SIMULATIONS (DEV) |
| REF|STD − E1CAL+straddle|STD | log_loss <= 0.2 | -10.88 | 8/0/0 | 0/0 | 22/24;13/24;19/30;15/27;16/23;18/31;14/29;18/34 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − H|RAND8 | BA >= 0.93 | -1.38 | 3/2/3 | 0/0 | 19/18;18/20;15/15;12/26;26/21;19/19;13/15;19/18 | NO CLEAR DIFFERENCE (DEV) |
| REF|RAND8 − H|RAND8 | BA >= 0.95 | 5.75 | 1/0/7 | 0/0 | 34/30;35/27;33/21;39/35;40/28;39/30;31/44;38/28 | MORE SIMULATIONS (DEV) |
| REF|RAND8 − H|RAND8 | log_loss <= 0.2 | -3.50 | 8/0/0 | 0/0 | 17/18;13/19;13/14;12/18;16/17;15/17;13/19;13/18 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − E1RAW+straddle|RAND8 | BA >= 0.93 | -5.25 | 6/1/1 | 0/0 | 19/24;18/23;15/21;12/19;26/22;19/19;13/29;19/26 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − E1RAW+straddle|RAND8 | BA >= 0.95 | -1.00 | 4/0/4 | 0/0 | 34/38;35/34;33/23;39/56;40/42;39/33;31/38;38/33 | NO CLEAR DIFFERENCE (DEV) |
| REF|RAND8 − E1RAW+straddle|RAND8 | log_loss <= 0.2 | -15.62 | 8/0/0 | 0/0 | 17/26;13/28;13/28;12/38;16/24;15/26;13/33;13/34 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − E1CAL+straddle|RAND8 | BA >= 0.93 | -6.75 | 7/0/1 | 0/0 | 19/27;18/26;15/23;12/20;26/22;19/20;13/31;19/26 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − E1CAL+straddle|RAND8 | BA >= 0.95 | -8.75 | 7/0/1 | 0/1 | 34/40;35/43;33/34;39/34;40/46;39/42;31/56;38/– | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − E1CAL+straddle|RAND8 | log_loss <= 0.2 | -11.25 | 8/0/0 | 0/0 | 17/24;13/24;13/23;12/27;16/24;15/26;13/28;13/26 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − H|LOCAL8 | BA >= 0.93 | -0.62 | 5/0/3 | 0/0 | 22/28;18/16;16/17;17/21;23/18;19/21;22/20;18/19 | NO CLEAR DIFFERENCE (DEV) |
| REF|LOCAL8 − H|LOCAL8 | BA >= 0.95 | 2.50 | 5/0/3 | 0/0 | 37/35;30/19;40/23;34/35;32/33;33/36;34/35;36/40 | NO CLEAR DIFFERENCE (DEV) |
| REF|LOCAL8 − H|LOCAL8 | log_loss <= 0.2 | -1.88 | 7/0/1 | 0/0 | 20/21;18/16;16/20;19/20;15/18;18/19;15/18;16/20 | NO CLEAR DIFFERENCE (DEV) |
| REF|LOCAL8 − E1RAW+straddle|LOCAL8 | BA >= 0.93 | -8.38 | 7/1/0 | 0/0 | 22/28;18/26;16/35;17/24;23/23;19/25;22/33;18/28 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − E1RAW+straddle|LOCAL8 | BA >= 0.95 | -12.12 | 8/0/0 | 0/0 | 37/44;30/36;40/58;34/41;32/56;33/52;34/45;36/41 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − E1RAW+straddle|LOCAL8 | log_loss <= 0.2 | -24.00 | 8/0/0 | 0/1 | 20/30;18/31;16/39;19/41;15/54;18/31;15/39;16/– | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − E1CAL+straddle|LOCAL8 | BA >= 0.93 | -9.88 | 8/0/0 | 0/0 | 22/29;18/26;16/40;17/26;23/25;19/29;22/31;18/28 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − E1CAL+straddle|LOCAL8 | BA >= 0.95 | -18.38 | 8/0/0 | 0/1 | 37/59;30/36;40/57;34/45;32/56;33/52;34/–;36/54 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − E1CAL+straddle|LOCAL8 | log_loss <= 0.2 | -17.50 | 8/0/0 | 0/0 | 20/28;18/30;16/28;19/41;15/40;18/29;15/34;16/47 | FEWER SIMULATIONS (DEV) |
| REF|RAND8 − REF|STD | BA >= 0.93 | 1.25 | 3/1/4 | 0/0 | 19/18;18/12;15/20;12/14;26/18;19/19;13/14;19/16 | NO CLEAR DIFFERENCE (DEV) |
| REF|RAND8 − REF|STD | BA >= 0.95 | 5.62 | 1/0/7 | 0/0 | 34/30;35/21;33/29;39/33;40/28;39/38;31/36;38/29 | MORE SIMULATIONS (DEV) |
| REF|RAND8 − REF|STD | log_loss <= 0.2 | -2.88 | 6/2/0 | 0/0 | 17/22;13/13;13/19;12/15;16/16;15/18;13/14;13/18 | FEWER SIMULATIONS (DEV) |
| REF|LOCAL8 − REF|STD | BA >= 0.93 | 3.00 | 1/1/6 | 0/0 | 22/18;18/12;16/20;17/14;23/18;19/19;22/14;18/16 | MORE SIMULATIONS (DEV) |
| REF|LOCAL8 − REF|STD | BA >= 0.95 | 4.00 | 2/0/6 | 0/0 | 37/30;30/21;40/29;34/33;32/28;33/38;34/36;36/29 | MORE SIMULATIONS (DEV) |
| REF|LOCAL8 − REF|STD | log_loss <= 0.2 | 0.25 | 4/1/3 | 0/0 | 20/22;18/13;16/19;19/15;15/16;18/18;15/14;16/18 | NO CLEAR DIFFERENCE (DEV) |
| H|RAND8 − H|STD | BA >= 0.93 | 2.25 | 3/0/5 | 0/0 | 18/14;20/14;15/16;26/15;21/16;19/23;15/20;18/16 | NO CLEAR DIFFERENCE (DEV) |
| H|RAND8 − H|STD | BA >= 0.95 | 0.75 | 4/1/3 | 0/0 | 30/32;27/22;21/24;35/35;28/26;30/36;44/26;28/36 | NO CLEAR DIFFERENCE (DEV) |
| H|RAND8 − H|STD | log_loss <= 0.2 | -3.12 | 7/1/0 | 0/0 | 18/24;19/19;14/18;18/21;17/20;17/20;19/20;18/23 | FEWER SIMULATIONS (DEV) |
| H|LOCAL8 − H|STD | BA >= 0.93 | 3.25 | 1/1/6 | 0/0 | 28/14;16/14;17/16;21/15;18/16;21/23;20/20;19/16 | MORE SIMULATIONS (DEV) |
| H|LOCAL8 − H|STD | BA >= 0.95 | 2.38 | 2/2/4 | 0/0 | 35/32;19/22;23/24;35/35;33/26;36/36;35/26;40/36 | NO CLEAR DIFFERENCE (DEV) |
| H|LOCAL8 − H|STD | log_loss <= 0.2 | -1.62 | 7/0/1 | 0/0 | 21/24;16/19;20/18;20/21;18/20;19/20;18/20;20/23 | NO CLEAR DIFFERENCE (DEV) |
| E1RAW+straddle|RAND8 − E1RAW+straddle|STD | BA >= 0.93 | -1.38 | 5/1/2 | 0/0 | 24/26;23/23;21/27;19/22;22/21;19/23;29/22;26/30 | NO CLEAR DIFFERENCE (DEV) |
| E1RAW+straddle|RAND8 − E1RAW+straddle|STD | BA >= 0.95 | -2.25 | 4/0/4 | 0/1 | 38/34;34/30;23/42;56/35;42/–;33/44;38/29;33/37 | NO CLEAR DIFFERENCE (DEV) |
| E1RAW+straddle|RAND8 − E1RAW+straddle|STD | log_loss <= 0.2 | -1.12 | 4/0/4 | 0/0 | 26/34;28/26;28/34;38/32;24/31;26/34;33/23;34/32 | NO CLEAR DIFFERENCE (DEV) |
| E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | BA >= 0.93 | 3.50 | 1/0/7 | 0/0 | 28/26;26/23;35/27;24/22;23/21;25/23;33/22;28/30 | MORE SIMULATIONS (DEV) |
| E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | BA >= 0.95 | 7.25 | 1/0/7 | 0/1 | 44/34;36/30;58/42;41/35;56/–;52/44;45/29;41/37 | NO CLEAR DIFFERENCE (DEV) |
| E1RAW+straddle|LOCAL8 − E1RAW+straddle|STD | log_loss <= 0.2 | 10.38 | 2/0/6 | 1/0 | 30/34;31/26;39/34;41/32;54/31;31/34;39/23;–/32 | MORE SIMULATIONS (DEV) |

## Individual learners (one fold / block each): confirmed own BA ≥ 0.93 by B60 (undefined when the learner's test set has one class)

| arm | learners | defined | attained | spend_mean_attainers | spend_median_attainers |
|---|---|---|---|---|---|
| E1CAL+straddle|LOCAL8 | 40 | 40 | 35 | 23.86 | 23.00 |
| E1CAL+straddle|RAND8 | 40 | 40 | 35 | 20.63 | 19.00 |
| E1CAL+straddle|STD | 40 | 40 | 36 | 24.00 | 20.50 |
| E1RAW+straddle|LOCAL8 | 40 | 40 | 38 | 27.11 | 24.00 |
| E1RAW+straddle|RAND8 | 40 | 40 | 36 | 20.22 | 17.00 |
| E1RAW+straddle|STD | 40 | 40 | 37 | 22.11 | 20.00 |
| H|LOCAL8 | 40 | 40 | 38 | 18.74 | 16.50 |
| H|RAND8 | 40 | 40 | 37 | 17.73 | 15.00 |
| H|STD | 40 | 40 | 39 | 17.69 | 15.00 |
| REF|LOCAL8 | 40 | 40 | 39 | 17.72 | 15.00 |
| REF|RAND8 | 40 | 40 | 38 | 17.47 | 13.50 |
| REF|STD | 40 | 40 | 40 | 18.77 | 14.00 |

## Matched budgets (fold-pooled, mean over repeats)

| arm | budget | BA | sensitivity | specificity | log_loss | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|
| E1CAL+straddle|LOCAL8 | 8 | 0.501 | 0.410 | 0.593 | 5.134 | 0.562 | 0.505 |
| E1CAL+straddle|LOCAL8 | 12 | 0.818 | 0.776 | 0.859 | 0.642 | 0.333 | 0.637 |
| E1CAL+straddle|LOCAL8 | 16 | 0.878 | 0.846 | 0.910 | 0.393 | 0.302 | 0.672 |
| E1CAL+straddle|LOCAL8 | 24 | 0.927 | 0.918 | 0.936 | 0.228 | 0.375 | 0.714 |
| E1CAL+straddle|LOCAL8 | 40 | 0.943 | 0.930 | 0.957 | 0.173 | 0.458 | 0.767 |
| E1CAL+straddle|LOCAL8 | 60 | 0.948 | 0.937 | 0.960 | 0.140 | 0.427 | 0.779 |
| E1CAL+straddle|RAND8 | 8 | 0.818 | 0.756 | 0.879 | 0.557 | 0.323 | 0.660 |
| E1CAL+straddle|RAND8 | 12 | 0.894 | 0.868 | 0.919 | 0.369 | 0.448 | 0.696 |
| E1CAL+straddle|RAND8 | 16 | 0.904 | 0.881 | 0.927 | 0.282 | 0.490 | 0.710 |
| E1CAL+straddle|RAND8 | 24 | 0.936 | 0.921 | 0.952 | 0.177 | 0.448 | 0.751 |
| E1CAL+straddle|RAND8 | 40 | 0.948 | 0.941 | 0.954 | 0.147 | 0.406 | 0.778 |
| E1CAL+straddle|RAND8 | 60 | 0.951 | 0.942 | 0.960 | 0.136 | 0.406 | 0.792 |
| E1CAL+straddle|STD | 8 | 0.789 | 0.775 | 0.803 | 0.515 | 0.406 | 0.624 |
| E1CAL+straddle|STD | 12 | 0.860 | 0.815 | 0.904 | 0.378 | 0.448 | 0.667 |
| E1CAL+straddle|STD | 16 | 0.910 | 0.900 | 0.920 | 0.301 | 0.365 | 0.708 |
| E1CAL+straddle|STD | 24 | 0.919 | 0.888 | 0.949 | 0.223 | 0.510 | 0.743 |
| E1CAL+straddle|STD | 40 | 0.946 | 0.937 | 0.954 | 0.155 | 0.438 | 0.770 |
| E1CAL+straddle|STD | 60 | 0.950 | 0.943 | 0.957 | 0.146 | 0.438 | 0.783 |
| E1RAW+straddle|LOCAL8 | 8 | 0.520 | 0.454 | 0.587 | 5.396 | 0.531 | 0.512 |
| E1RAW+straddle|LOCAL8 | 12 | 0.831 | 0.806 | 0.856 | 0.798 | 0.323 | 0.641 |
| E1RAW+straddle|LOCAL8 | 16 | 0.878 | 0.860 | 0.895 | 0.581 | 0.292 | 0.674 |
| E1RAW+straddle|LOCAL8 | 24 | 0.929 | 0.938 | 0.919 | 0.300 | 0.302 | 0.716 |
| E1RAW+straddle|LOCAL8 | 40 | 0.949 | 0.952 | 0.946 | 0.196 | 0.365 | 0.773 |
| E1RAW+straddle|LOCAL8 | 60 | 0.955 | 0.956 | 0.954 | 0.160 | 0.365 | 0.790 |
| E1RAW+straddle|RAND8 | 8 | 0.835 | 0.801 | 0.869 | 0.845 | 0.312 | 0.679 |
| E1RAW+straddle|RAND8 | 12 | 0.897 | 0.886 | 0.909 | 0.504 | 0.406 | 0.702 |
| E1RAW+straddle|RAND8 | 16 | 0.913 | 0.915 | 0.910 | 0.342 | 0.406 | 0.705 |
| E1RAW+straddle|RAND8 | 24 | 0.940 | 0.944 | 0.936 | 0.201 | 0.375 | 0.748 |
| E1RAW+straddle|RAND8 | 40 | 0.952 | 0.959 | 0.945 | 0.176 | 0.354 | 0.783 |
| E1RAW+straddle|RAND8 | 60 | 0.957 | 0.961 | 0.953 | 0.154 | 0.385 | 0.799 |
| E1RAW+straddle|STD | 8 | 0.849 | 0.888 | 0.810 | 0.598 | 0.292 | 0.646 |
| E1RAW+straddle|STD | 12 | 0.894 | 0.920 | 0.868 | 0.441 | 0.344 | 0.669 |
| E1RAW+straddle|STD | 16 | 0.915 | 0.941 | 0.890 | 0.350 | 0.229 | 0.695 |
| E1RAW+straddle|STD | 24 | 0.938 | 0.953 | 0.923 | 0.238 | 0.292 | 0.749 |
| E1RAW+straddle|STD | 40 | 0.949 | 0.953 | 0.946 | 0.172 | 0.396 | 0.778 |
| E1RAW+straddle|STD | 60 | 0.952 | 0.953 | 0.950 | 0.162 | 0.396 | 0.778 |
| H|LOCAL8 | 8 | 0.576 | 0.468 | 0.684 | 5.026 | 0.521 | 0.550 |
| H|LOCAL8 | 12 | 0.848 | 0.808 | 0.888 | 0.445 | 0.302 | 0.683 |
| H|LOCAL8 | 16 | 0.929 | 0.914 | 0.945 | 0.189 | 0.229 | 0.745 |
| H|LOCAL8 | 24 | 0.943 | 0.937 | 0.949 | 0.160 | 0.177 | 0.760 |
| H|LOCAL8 | 40 | 0.953 | 0.949 | 0.957 | 0.126 | 0.229 | 0.781 |
| H|LOCAL8 | 60 | 0.958 | 0.954 | 0.961 | 0.115 | 0.323 | 0.805 |
| H|RAND8 | 8 | 0.859 | 0.795 | 0.923 | 0.328 | 0.323 | 0.675 |
| H|RAND8 | 12 | 0.915 | 0.891 | 0.938 | 0.222 | 0.250 | 0.741 |
| H|RAND8 | 16 | 0.932 | 0.913 | 0.952 | 0.185 | 0.323 | 0.738 |
| H|RAND8 | 24 | 0.947 | 0.932 | 0.963 | 0.141 | 0.354 | 0.786 |
| H|RAND8 | 40 | 0.953 | 0.947 | 0.959 | 0.122 | 0.271 | 0.791 |
| H|RAND8 | 60 | 0.959 | 0.957 | 0.961 | 0.108 | 0.344 | 0.809 |
| H|STD | 8 | 0.845 | 0.805 | 0.884 | 0.382 | 0.260 | 0.675 |
| H|STD | 12 | 0.922 | 0.906 | 0.938 | 0.245 | 0.135 | 0.735 |
| H|STD | 16 | 0.929 | 0.909 | 0.948 | 0.201 | 0.219 | 0.740 |
| H|STD | 24 | 0.947 | 0.934 | 0.959 | 0.164 | 0.219 | 0.770 |
| H|STD | 40 | 0.958 | 0.952 | 0.963 | 0.127 | 0.302 | 0.804 |
| H|STD | 60 | 0.956 | 0.952 | 0.961 | 0.116 | 0.333 | 0.801 |
| REF|LOCAL8 | 8 | 0.580 | 0.473 | 0.688 | 5.028 | 0.500 | 0.559 |
| REF|LOCAL8 | 12 | 0.901 | 0.867 | 0.935 | 0.334 | 0.219 | 0.707 |
| REF|LOCAL8 | 16 | 0.933 | 0.926 | 0.940 | 0.178 | 0.156 | 0.755 |
| REF|LOCAL8 | 24 | 0.941 | 0.935 | 0.948 | 0.143 | 0.135 | 0.755 |
| REF|LOCAL8 | 40 | 0.958 | 0.956 | 0.959 | 0.117 | 0.292 | 0.803 |
| REF|LOCAL8 | 60 | 0.958 | 0.956 | 0.960 | 0.108 | 0.333 | 0.808 |
| REF|RAND8 | 8 | 0.881 | 0.836 | 0.926 | 0.256 | 0.240 | 0.699 |
| REF|RAND8 | 12 | 0.914 | 0.886 | 0.943 | 0.194 | 0.281 | 0.718 |
| REF|RAND8 | 16 | 0.936 | 0.926 | 0.947 | 0.169 | 0.229 | 0.739 |
| REF|RAND8 | 24 | 0.942 | 0.935 | 0.950 | 0.146 | 0.146 | 0.754 |
| REF|RAND8 | 40 | 0.957 | 0.956 | 0.958 | 0.118 | 0.260 | 0.800 |
| REF|RAND8 | 60 | 0.957 | 0.952 | 0.963 | 0.110 | 0.365 | 0.805 |
| REF|STD | 8 | 0.862 | 0.848 | 0.875 | 0.332 | 0.250 | 0.690 |
| REF|STD | 12 | 0.929 | 0.924 | 0.934 | 0.204 | 0.188 | 0.742 |
| REF|STD | 16 | 0.935 | 0.921 | 0.949 | 0.176 | 0.240 | 0.737 |
| REF|STD | 24 | 0.945 | 0.936 | 0.953 | 0.150 | 0.260 | 0.771 |
| REF|STD | 40 | 0.957 | 0.957 | 0.958 | 0.123 | 0.281 | 0.800 |
| REF|STD | 60 | 0.957 | 0.951 | 0.964 | 0.110 | 0.354 | 0.806 |

Export acceptance: {"cells": 5088, "cells_table": 5088, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

## Class discovery (label-free continuation until both classes are paid; counted in every budget)

| startup | arm | learners | one_class_starts | discovery_queries_mean | discovery_queries_max |
|---|---|---|---|---|---|
| LOCAL8 | E1S | 40 | 30 | 0.93 | 6 |
| LOCAL8 | H | 40 | 30 | 0.93 | 6 |
| LOCAL8 | REF | 40 | 30 | 0.93 | 6 |
| RAND8 | E1S | 40 | 0 | 0.00 | 0 |
| RAND8 | H | 40 | 0 | 0.00 | 0 |
| RAND8 | REF | 40 | 0 | 0.00 | 0 |
| STD | E1S | 40 | 0 | 0.00 | 0 |
| STD | H | 40 | 0 | 0.00 | 0 |
| STD | REF | 40 | 0 | 0.00 | 0 |

