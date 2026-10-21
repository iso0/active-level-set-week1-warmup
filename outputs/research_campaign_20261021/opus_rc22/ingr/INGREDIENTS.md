# RC22 part 2 and acquisition audit — identical saved paid prefixes (RC21B NEW_MARGIN and H_MARGIN paths, repeats 35–42)

Reproduction of the recorded RC21B probabilities: max |Δ| = 2.98e-08.

**Pre-registered decisions: SELECTOR = BALD_LAP; SIMPLE = HA_LR.**

```
{
 "selector_rule": {
  "BALD_LAP": {
   "criteria": {
    "numerics": true,
    "median_ratio_max_ge_0.05": true,
    "states_with_max_below_1e-6_lt_10pct": true,
    "top1_differs_from_margin_ge_25pct": true,
    "median_spearman_vs_margin_lt_0.95": true,
    "top1_differs_from_eta_straddle_ge_25pct": true,
    "extra_cpu_le_0.5s": true
   },
   "pass": true,
   "summary": {
    "median_ratio_max": 0.2513336543812501,
    "top1_differs_from_margin": 0.975,
    "median_spearman_vs_margin": 0.25167136784761446,
    "top1_differs_from_eta_straddle": 0.9546875
   }
  },
  "BALD_GRID": {
   "criteria": {
    "numerics": true,
    "median_ratio_max_ge_0.05": true,
    "states_with_max_below_1e-6_lt_10pct": true,
    "top1_differs_from_margin_ge_25pct": true,
    "median_spearman_vs_margin_lt_0.95": true,
    "top1_differs_from_eta_straddle_ge_25pct": true,
    "extra_cpu_le_0.5s": true
   },
   "pass": true,
   "summary": {
    "median_ratio_max": 0.0595047108727175,
    "top1_differs_from_margin": 0.9765625,
    "median_spearman_vs_margin": 0.647383995932211,
    "top1_differs_from_eta_straddle": 0.9296875
   }
  }
 },
 "simple_rule": {
  "HONLY_LR": {
   "dBA_B8_B24": 0.016608318085231943,
   "dLL_B8_B24": 0.004627830669237769,
   "equivalent": false
  },
  "HA_LR": {
   "dBA_B8_B24": 0.009458464909691891,
   "dLL_B8_B24": -0.01521772698458123,
   "equivalent": true
  },
  "SHQ_ATS_H_RECAL": {
   "dBA_B8_B24": -0.0075239235332310445,
   "dLL_B8_B24": 0.04987599273350191,
   "equivalent": false
  }
 }
}
```

## All-path means (fold-pooled curves; mean over the 2 path types and 8 repeats)

| construction | BA small | log_loss small | sensitivity small | specificity small | BA all | log_loss all | sensitivity all | specificity all |
|---|---|---|---|---|---|---|---|---|
| SHQ_ATS_H | 0.9166 | 0.2352 | 0.8982 | 0.9351 | 0.9313 | 0.1946 | 0.9181 | 0.9444 |
| PHR_NRMAP | 0.9214 | 0.2050 | 0.9093 | 0.9336 | 0.9343 | 0.1746 | 0.9249 | 0.9436 |
| HA_LR | 0.9309 | 0.1898 | 0.9244 | 0.9374 | 0.9402 | 0.1653 | 0.9344 | 0.9459 |
| HONLY_LR | 0.9380 | 0.2096 | 0.9322 | 0.9439 | 0.9409 | 0.2034 | 0.9338 | 0.9480 |
| SHQ_ATS_H_RECAL | 0.9139 | 0.2549 | 0.8945 | 0.9333 | 0.9290 | 0.2121 | 0.9148 | 0.9432 |

## Matched contrasts (MATERIAL iff |Δ| ≥ 0.010 in the good direction and good in ≥ 7/8)

| window | contrast | metric | mean | se | good | label |
|---|---|---|---|---|---|---|
| small | HONLY_LR − PHR_NRMAP | BA | 0.0166 | 0.0051 | 7/8 | MATERIAL |
| small | HONLY_LR − PHR_NRMAP | log_loss | 0.0046 | 0.0075 | 3/8 | NOT MATERIAL |
| small | HONLY_LR − PHR_NRMAP | sensitivity | 0.0230 | 0.0047 | 8/8 | MATERIAL |
| small | HONLY_LR − PHR_NRMAP | specificity | 0.0102 | 0.0061 | 5/8 | NOT MATERIAL |
| small | HA_LR − PHR_NRMAP | BA | 0.0095 | 0.0038 | 7/8 | NOT MATERIAL |
| small | HA_LR − PHR_NRMAP | log_loss | -0.0152 | 0.0065 | 7/8 | MATERIAL |
| small | HA_LR − PHR_NRMAP | sensitivity | 0.0151 | 0.0051 | 7/8 | MATERIAL |
| small | HA_LR − PHR_NRMAP | specificity | 0.0038 | 0.0038 | 5/8 | NOT MATERIAL |
| small | HA_LR − HONLY_LR | BA | -0.0071 | 0.0020 | 1/8 | NOT MATERIAL |
| small | HA_LR − HONLY_LR | log_loss | -0.0198 | 0.0016 | 8/8 | MATERIAL |
| small | HA_LR − HONLY_LR | sensitivity | -0.0079 | 0.0034 | 2/8 | NOT MATERIAL |
| small | HA_LR − HONLY_LR | specificity | -0.0064 | 0.0033 | 3/8 | NOT MATERIAL |
| small | PHR_NRMAP − HA_LR | BA | -0.0095 | 0.0038 | 1/8 | NOT MATERIAL |
| small | PHR_NRMAP − HA_LR | log_loss | 0.0152 | 0.0065 | 1/8 | MATERIAL HARM |
| small | PHR_NRMAP − HA_LR | sensitivity | -0.0151 | 0.0051 | 1/8 | MATERIAL HARM |
| small | PHR_NRMAP − HA_LR | specificity | -0.0038 | 0.0038 | 3/8 | NOT MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H | BA | 0.0048 | 0.0032 | 6/8 | NOT MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H | log_loss | -0.0302 | 0.0049 | 8/8 | MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H | sensitivity | 0.0111 | 0.0050 | 6/8 | NOT MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H | specificity | -0.0015 | 0.0016 | 2/8 | NOT MATERIAL |
| small | SHQ_ATS_H_RECAL − SHQ_ATS_H | BA | -0.0027 | 0.0011 | 2/8 | NOT MATERIAL |
| small | SHQ_ATS_H_RECAL − SHQ_ATS_H | log_loss | 0.0197 | 0.0048 | 0/8 | MATERIAL HARM |
| small | SHQ_ATS_H_RECAL − SHQ_ATS_H | sensitivity | -0.0036 | 0.0022 | 3/8 | NOT MATERIAL |
| small | SHQ_ATS_H_RECAL − SHQ_ATS_H | specificity | -0.0019 | 0.0021 | 4/8 | NOT MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H_RECAL | BA | 0.0075 | 0.0032 | 7/8 | NOT MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H_RECAL | log_loss | -0.0499 | 0.0067 | 8/8 | MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H_RECAL | sensitivity | 0.0147 | 0.0049 | 7/8 | MATERIAL |
| small | PHR_NRMAP − SHQ_ATS_H_RECAL | specificity | 0.0003 | 0.0024 | 2/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | BA | 0.0066 | 0.0034 | 7/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | log_loss | 0.0288 | 0.0049 | 0/8 | MATERIAL HARM |
| all | HONLY_LR − PHR_NRMAP | sensitivity | 0.0089 | 0.0033 | 6/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | specificity | 0.0044 | 0.0040 | 5/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | BA | 0.0059 | 0.0026 | 7/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | log_loss | -0.0093 | 0.0041 | 7/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | sensitivity | 0.0095 | 0.0036 | 7/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | specificity | 0.0023 | 0.0025 | 5/8 | NOT MATERIAL |
| all | HA_LR − HONLY_LR | BA | -0.0007 | 0.0017 | 2/8 | NOT MATERIAL |
| all | HA_LR − HONLY_LR | log_loss | -0.0381 | 0.0014 | 8/8 | MATERIAL |
| all | HA_LR − HONLY_LR | sensitivity | 0.0006 | 0.0030 | 4/8 | NOT MATERIAL |
| all | HA_LR − HONLY_LR | specificity | -0.0021 | 0.0019 | 4/8 | NOT MATERIAL |
| all | PHR_NRMAP − HA_LR | BA | -0.0059 | 0.0026 | 1/8 | NOT MATERIAL |
| all | PHR_NRMAP − HA_LR | log_loss | 0.0093 | 0.0041 | 1/8 | NOT MATERIAL |
| all | PHR_NRMAP − HA_LR | sensitivity | -0.0095 | 0.0036 | 1/8 | NOT MATERIAL |
| all | PHR_NRMAP − HA_LR | specificity | -0.0023 | 0.0025 | 3/8 | NOT MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H | BA | 0.0030 | 0.0021 | 6/8 | NOT MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H | log_loss | -0.0200 | 0.0030 | 8/8 | MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H | sensitivity | 0.0068 | 0.0034 | 6/8 | NOT MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H | specificity | -0.0008 | 0.0010 | 3/8 | NOT MATERIAL |
| all | SHQ_ATS_H_RECAL − SHQ_ATS_H | BA | -0.0023 | 0.0006 | 1/8 | NOT MATERIAL |
| all | SHQ_ATS_H_RECAL − SHQ_ATS_H | log_loss | 0.0175 | 0.0038 | 0/8 | MATERIAL HARM |
| all | SHQ_ATS_H_RECAL − SHQ_ATS_H | sensitivity | -0.0034 | 0.0013 | 2/8 | NOT MATERIAL |
| all | SHQ_ATS_H_RECAL − SHQ_ATS_H | specificity | -0.0012 | 0.0013 | 3/8 | NOT MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H_RECAL | BA | 0.0053 | 0.0020 | 7/8 | NOT MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H_RECAL | log_loss | -0.0374 | 0.0045 | 8/8 | MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H_RECAL | sensitivity | 0.0102 | 0.0031 | 7/8 | MATERIAL |
| all | PHR_NRMAP − SHQ_ATS_H_RECAL | specificity | 0.0004 | 0.0014 | 3/8 | NOT MATERIAL |

## How far is PHR_NRMAP (and the controls) from a common positive scaling of SHQ_ATS_H's logit? (medians / means over states, candidates only)

| pair | budget | slope | intercept | R2 | sign_disagree | spearman_margin | top1_same | top5_jaccard |
|---|---|---|---|---|---|---|---|---|
| HA_LR vs SHQ_ATS_H | 8 | 1.231 | 0.004 | 0.980 | 0.069 | 0.968 | 0.000 | 0.073 |
| HA_LR vs SHQ_ATS_H | 12 | 1.275 | -0.068 | 0.983 | 0.026 | 0.965 | 0.062 | 0.156 |
| HA_LR vs SHQ_ATS_H | 16 | 1.175 | -0.095 | 0.986 | 0.023 | 0.973 | 0.025 | 0.153 |
| HA_LR vs SHQ_ATS_H | 20 | 1.173 | -0.090 | 0.989 | 0.013 | 0.979 | 0.062 | 0.226 |
| HA_LR vs SHQ_ATS_H | 24 | 1.102 | -0.120 | 0.991 | 0.010 | 0.977 | 0.188 | 0.289 |
| HA_LR vs SHQ_ATS_H | 32 | 1.066 | -0.079 | 0.992 | 0.005 | 0.985 | 0.138 | 0.452 |
| HA_LR vs SHQ_ATS_H | 40 | 1.048 | -0.040 | 0.995 | 0.001 | 0.990 | 0.412 | 0.535 |
| HA_LR vs SHQ_ATS_H | 60 | 1.000 | 0.001 | 0.998 | 0.000 | 0.988 | 0.662 | 0.678 |
| HONLY_LR vs SHQ_ATS_H | 8 | 1.001 | 0.055 | 0.939 | 0.109 | 0.835 | 0.000 | 0.020 |
| HONLY_LR vs SHQ_ATS_H | 12 | 1.112 | -0.098 | 0.971 | 0.041 | 0.932 | 0.037 | 0.078 |
| HONLY_LR vs SHQ_ATS_H | 16 | 0.923 | -0.110 | 0.971 | 0.035 | 0.929 | 0.050 | 0.078 |
| HONLY_LR vs SHQ_ATS_H | 20 | 0.945 | -0.175 | 0.973 | 0.025 | 0.924 | 0.037 | 0.084 |
| HONLY_LR vs SHQ_ATS_H | 24 | 0.832 | -0.236 | 0.971 | 0.020 | 0.916 | 0.050 | 0.109 |
| HONLY_LR vs SHQ_ATS_H | 32 | 0.659 | -0.268 | 0.967 | 0.014 | 0.897 | 0.037 | 0.087 |
| HONLY_LR vs SHQ_ATS_H | 40 | 0.601 | -0.264 | 0.967 | 0.008 | 0.860 | 0.050 | 0.101 |
| HONLY_LR vs SHQ_ATS_H | 60 | 0.467 | -0.468 | 0.952 | 0.002 | 0.763 | 0.037 | 0.090 |
| PHR_NRMAP vs SHQ_ATS_H | 8 | 1.354 | 0.016 | 0.991 | 0.036 | 0.988 | 0.050 | 0.169 |
| PHR_NRMAP vs SHQ_ATS_H | 12 | 1.361 | -0.038 | 0.992 | 0.016 | 0.988 | 0.100 | 0.213 |
| PHR_NRMAP vs SHQ_ATS_H | 16 | 1.266 | -0.063 | 0.994 | 0.013 | 0.989 | 0.125 | 0.254 |
| PHR_NRMAP vs SHQ_ATS_H | 20 | 1.236 | -0.073 | 0.995 | 0.008 | 0.990 | 0.163 | 0.323 |
| PHR_NRMAP vs SHQ_ATS_H | 24 | 1.181 | -0.089 | 0.995 | 0.008 | 0.991 | 0.212 | 0.404 |
| PHR_NRMAP vs SHQ_ATS_H | 32 | 1.095 | -0.080 | 0.996 | 0.004 | 0.992 | 0.338 | 0.543 |
| PHR_NRMAP vs SHQ_ATS_H | 40 | 1.033 | -0.047 | 0.997 | 0.001 | 0.994 | 0.562 | 0.677 |
| PHR_NRMAP vs SHQ_ATS_H | 60 | 0.983 | -0.043 | 0.999 | 0.000 | 0.996 | 0.713 | 0.836 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 8 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 12 | 1.020 | 0.056 | 1.000 | 0.016 | 0.993 | 0.075 | 0.238 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 16 | 0.946 | -0.032 | 1.000 | 0.012 | 0.997 | 0.125 | 0.367 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 20 | 0.948 | -0.012 | 1.000 | 0.012 | 0.997 | 0.263 | 0.569 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 24 | 0.904 | -0.022 | 1.000 | 0.003 | 0.999 | 0.350 | 0.662 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 32 | 0.946 | -0.003 | 1.000 | 0.002 | 0.999 | 0.600 | 0.735 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 40 | 0.916 | -0.011 | 1.000 | 0.000 | 0.999 | 0.775 | 0.800 |
| SHQ_ATS_H_RECAL vs SHQ_ATS_H | 60 | 1.009 | 0.004 | 1.000 | 0.000 | 0.999 | 0.912 | 0.873 |

## Recalibration coefficients of SHQ_ATS_H_RECAL (logit p' = a + c logit p; fallback = identity)

| budget | fallback | a_median | c_median | c_q25 | c_q75 |
|---|---|---|---|---|---|
| 8.000 | 1.000 | – | – | – | – |
| 12.000 | 0.000 | 0.056 | 1.020 | 0.814 | 1.201 |
| 16.000 | 0.000 | -0.032 | 0.946 | 0.804 | 1.124 |
| 20.000 | 0.000 | -0.012 | 0.948 | 0.758 | 1.056 |
| 24.000 | 0.000 | -0.021 | 0.904 | 0.776 | 1.048 |
| 32.000 | 0.000 | -0.002 | 0.946 | 0.794 | 1.102 |
| 40.000 | 0.000 | -0.012 | 0.916 | 0.816 | 1.052 |
| 60.000 | 0.000 | -0.001 | 1.012 | 0.908 | 1.127 |

## Acquisition audit by budget (BALD_LAP = classifier-weight + grid information; BALD_GRID = grid only)

| selector | budget | median_ratio_max | frac_states_max_lt_1e6 | top1_differs_margin | median_spearman_margin | top1_differs_eta | p_ref_at_top1 | corner_top1 | corner_margin_top1 |
|---|---|---|---|---|---|---|---|---|---|
| bald_grid | 8 | 0.138 | 0.000 | 1.000 | 0.390 | 1.000 | 0.595 | 0.100 | 0.150 |
| bald_grid | 12 | 0.090 | 0.000 | 0.975 | 0.471 | 0.963 | 0.386 | 0.050 | 0.200 |
| bald_grid | 16 | 0.070 | 0.000 | 1.000 | 0.494 | 0.900 | 0.380 | 0.062 | 0.325 |
| bald_grid | 20 | 0.059 | 0.000 | 0.988 | 0.645 | 0.912 | 0.419 | 0.062 | 0.212 |
| bald_grid | 24 | 0.063 | 0.000 | 0.938 | 0.673 | 0.887 | 0.349 | 0.075 | 0.325 |
| bald_grid | 32 | 0.053 | 0.000 | 0.963 | 0.769 | 0.912 | 0.290 | 0.087 | 0.388 |
| bald_grid | 40 | 0.043 | 0.000 | 0.988 | 0.815 | 0.938 | 0.225 | 0.100 | 0.325 |
| bald_grid | 60 | 0.034 | 0.000 | 0.963 | 0.900 | 0.925 | 0.093 | 0.037 | 0.463 |
| bald_lap | 8 | 0.468 | 0.000 | 1.000 | 0.245 | 1.000 | 0.537 | 0.125 | 0.150 |
| bald_lap | 12 | 0.373 | 0.000 | 0.988 | -0.034 | 0.950 | 0.351 | 0.013 | 0.200 |
| bald_lap | 16 | 0.295 | 0.000 | 1.000 | 0.028 | 0.975 | 0.383 | 0.113 | 0.325 |
| bald_lap | 20 | 0.257 | 0.000 | 0.988 | 0.145 | 0.963 | 0.403 | 0.087 | 0.212 |
| bald_lap | 24 | 0.234 | 0.000 | 0.975 | 0.194 | 0.925 | 0.404 | 0.062 | 0.325 |
| bald_lap | 32 | 0.207 | 0.000 | 0.950 | 0.394 | 0.950 | 0.494 | 0.113 | 0.388 |
| bald_lap | 40 | 0.170 | 0.000 | 0.975 | 0.446 | 0.963 | 0.239 | 0.050 | 0.325 |
| bald_lap | 60 | 0.148 | 0.000 | 0.925 | 0.752 | 0.912 | 0.105 | 0.013 | 0.463 |

