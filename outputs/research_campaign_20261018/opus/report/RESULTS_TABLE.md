# RC18 final programme — single results table (DEV; final repeats 5-8; frozen protocol PROTOCOL_20261018.md)

Every number below is computed by `src/rc18_report.py` from the frozen final units (manifest main/final/RC18_FINAL_MANIFEST.json). DEV evidence on previously inspected simulations; no C3/C4/Stage A.

## 1. PRIMARY — NEW physical outputs, model effect under the identical MAXIMIN design (TRSQ vs M0)

**Verdict: FEWER SIMULATIONS (DEV).** Mean queries saved to the sustained target level: **21.0** (per repeat {5: 13.33, 6: 32.67, 7: 19.33, 8: 18.67}). R²-AULC difference +0.083 (per repeat {5: 0.0485, 6: 0.1319, 7: 0.0804, 8: 0.0718}).

| target | M0 budget-to-target (mean of 4 repeats) | TRSQ budget-to-target | saved |
|---|---|---|---|
| log_A_um | 12.0 | 0.0 | 12.0 |
| log_ke_T0_nJ | 28.0 | 0.0 | 28.0 |
| vmax_spike_logratio | 28.0 | 0.0 | 28.0 |
| vmax_spike_us | 45.0 | 29.0 | 16.0 |
| laser_T0_W | 21.0 | 0.0 | 21.0 |
| tmax_T0_K | 21.0 | 0.0 | 21.0 |

Rule: FEWER SIMULATIONS (DEV) iff mean saved >= 8, every repeat mean > 0, no target mean < -4 (PROTOCOL_20261018 §5).

## 2. Exploratory regression contrasts (no correction; all 4 per-repeat values shown)

| contrast | pop | metric | mean | per-repeat | positive repeats |
|---|---|---|---|---|---|
| E1 QA (M0Q - M0), MAXIMIN | NEW | R2_AULC | +0.029 | [0.0185, 0.0555, 0.0228, 0.0188] | 4/4 |
| E1 QA (M0Q - M0), MAXIMIN | NEW | budget_to_target | -5.000 | [0.6667, -14.0, -2.6667, -4.0] | 1/4 |
| E1 sharing (SHQ - M0Q), MAXIMIN | NEW | R2_AULC | +0.034 | [0.0234, 0.0444, 0.0425, 0.0258] | 4/4 |
| E1 sharing (SHQ - M0Q), MAXIMIN | NEW | budget_to_target | -4.667 | [-2.0, -5.3333, -8.0, -3.3333] | 0/4 |
| E1 transfer (TRQ - M0Q), MAXIMIN | NEW | R2_AULC | +0.038 | [0.0157, 0.0593, 0.0441, 0.034] | 4/4 |
| E1 transfer (TRQ - M0Q), MAXIMIN | NEW | budget_to_target | -14.667 | [-13.3333, -16.6667, -15.3333, -13.3333] | 0/4 |
| E1 sharing given transfer (TRSQ - TRQ) | NEW | R2_AULC | +0.016 | [0.0144, 0.017, 0.0136, 0.019] | 4/4 |
| E1 sharing given transfer (TRSQ - TRQ) | NEW | budget_to_target | -1.333 | [-0.6667, -2.0, -1.3333, -1.3333] | 0/4 |
| E2 OLD rich (SHQ - M0), MAXIMIN | OLD | R2_AULC | +0.008 | [0.0031, 0.0127, 0.0022, 0.0143] | 4/4 |
| E2 OLD rich (SHQ - M0), MAXIMIN | OLD | budget_to_target | -0.429 | [0.0, -0.5714, 0.5714, -1.7143] | 1/4 |
| E3 acquisition MOIVR - MAXIMIN (M0) | NEW | R2_AULC | +0.010 | [0.0012, 0.0277, 0.0097, 0.0018] | 4/4 |
| E3 acquisition MOIVR - MAXIMIN (M0) | NEW | budget_to_target | +0.667 | [-1.3333, -6.0, 0.6667, 9.3333] | 2/4 |
| E3 design RANDOM - MAXIMIN (M0) | NEW | R2_AULC | -0.009 | [0.0043, 0.0186, -0.0423, -0.0166] | 2/4 |
| E3 design RANDOM - MAXIMIN (M0) | NEW | budget_to_target | +3.667 | [3.3333, -3.3333, 7.3333, 7.3333] | 3/4 |
| E3 acquisition MOIVR - MAXIMIN (TRSQ) | NEW | R2_AULC | +0.005 | [0.0092, 0.0062, -0.0024, 0.0076] | 3/4 |
| E3 acquisition MOIVR - MAXIMIN (TRSQ) | NEW | budget_to_target | +6.667 | [8.0, 5.3333, 6.6667, 6.6667] | 4/4 |
| E3 design RANDOM - MAXIMIN (TRSQ) | NEW | R2_AULC | +0.000 | [0.0087, -0.0059, -0.0058, 0.003] | 2/4 |
| E3 design RANDOM - MAXIMIN (TRSQ) | NEW | budget_to_target | +7.667 | [7.3333, 8.6667, 7.3333, 7.3333] | 4/4 |
| E3 rich vs simple under MOIVR (TRSQ - M0) | NEW | R2_AULC | +0.078 | [0.0565, 0.1104, 0.0684, 0.0776] | 4/4 |
| E3 rich vs simple under MOIVR (TRSQ - M0) | NEW | budget_to_target | -15.000 | [-4.0, -21.3333, -13.3333, -21.3333] | 0/4 |
| E3 acquisition MOIVR - MAXIMIN (M0) | OLD | R2_AULC | +0.003 | [-0.0061, 0.0092, -0.0029, 0.0106] | 2/4 |
| E3 acquisition MOIVR - MAXIMIN (M0) | OLD | budget_to_target | +1.571 | [4.5714, -1.1429, 1.1429, 1.7143] | 3/4 |
| E3 design RANDOM - MAXIMIN (M0) | OLD | R2_AULC | -0.015 | [-0.0208, -0.0051, -0.027, -0.0059] | 0/4 |
| E3 design RANDOM - MAXIMIN (M0) | OLD | budget_to_target | +5.286 | [5.1429, 2.8571, 8.0, 5.1429] | 4/4 |
| E3 acquisition MOIVR - MAXIMIN (SHQ) | OLD | R2_AULC | +0.010 | [0.01, 0.0089, 0.0111, 0.0095] | 4/4 |
| E3 acquisition MOIVR - MAXIMIN (SHQ) | OLD | budget_to_target | -1.000 | [0.0, 0.5714, -2.8571, -1.7143] | 1/4 |
| E3 design RANDOM - MAXIMIN (SHQ) | OLD | R2_AULC | -0.013 | [-0.0123, -0.0015, -0.0332, -0.0039] | 0/4 |
| E3 design RANDOM - MAXIMIN (SHQ) | OLD | budget_to_target | +3.429 | [5.1429, 0.5714, 4.0, 4.0] | 4/4 |
| E3 rich vs simple under MOIVR (SHQ - M0) | OLD | R2_AULC | +0.015 | [0.0192, 0.0125, 0.0163, 0.0132] | 4/4 |
| E3 rich vs simple under MOIVR (SHQ - M0) | OLD | budget_to_target | -3.000 | [-4.5714, 1.1429, -3.4286, -5.1429] | 1/4 |

**E4 calibration** (mean over primary targets and repeats, MAXIMIN design):

| pop | model | cov90 B8 | cov90 B24 | NLPD B24 | R2 B0 | R2 B8 | R2 B24 | R2 B60 |
|---|---|---|---|---|---|---|---|---|
| NEW | M0 | 0.686 | 0.777 | 3.624 | nan | 0.307 | 0.758 | 0.777 |
| NEW | M0Q | 0.682 | 0.746 | 4.034 | nan | 0.308 | 0.787 | 0.830 |
| NEW | SHQ | 0.825 | 0.806 | 2.759 | nan | 0.350 | 0.815 | 0.850 |
| NEW | TRQ | 0.710 | 0.745 | 3.554 | 0.805 | 0.762 | 0.787 | 0.832 |
| NEW | TRSQ | 0.836 | 0.830 | 2.789 | 0.805 | 0.789 | 0.810 | 0.838 |
| OLD | M0 | 0.709 | 0.877 | 1.259 | nan | 0.562 | 0.889 | 0.931 |
| OLD | SHQ | 0.818 | 0.900 | 1.080 | nan | 0.570 | 0.897 | 0.933 |

## 5a. Reaching the same accuracy at different levels (exploratory; level = factor x R2_full(M0), MAXIMIN design)

| pop | level factor | model | mean budget-to-target | share never reached by B60 |
|---|---|---|---|---|
| NEW | 0.8 | M0 | 17.7 | 0.04 |
| NEW | 0.8 | TRSQ | 3.0 | 0.00 |
| NEW | 0.8 | M0Q | 15.3 | 0.00 |
| NEW | 0.8 | SHQ | 13.7 | 0.00 |
| NEW | 0.8 | TRQ | 5.3 | 0.00 |
| NEW | 0.9 | M0 | 25.8 | 0.08 |
| NEW | 0.9 | TRSQ | 4.8 | 0.00 |
| NEW | 0.9 | M0Q | 20.8 | 0.00 |
| NEW | 0.9 | SHQ | 16.2 | 0.00 |
| NEW | 0.9 | TRQ | 6.2 | 0.00 |
| NEW | 0.95 | M0 | 32.0 | 0.12 |
| NEW | 0.95 | TRSQ | 8.3 | 0.00 |
| NEW | 0.95 | M0Q | 29.5 | 0.08 |
| NEW | 0.95 | SHQ | 22.8 | 0.00 |
| NEW | 0.95 | TRQ | 11.7 | 0.00 |
| OLD | 0.8 | M0 | 14.9 | 0.00 |
| OLD | 0.8 | SHQ | 13.3 | 0.00 |
| OLD | 0.9 | M0 | 23.1 | 0.07 |
| OLD | 0.9 | SHQ | 22.7 | 0.07 |
| OLD | 0.95 | M0 | 32.1 | 0.14 |
| OLD | 0.95 | SHQ | 31.0 | 0.14 |

## 5b. Stopping with false confidence (exploratory)

Learner-side rule: stop when the model's own self-R2 (1 - mean predictive observation variance / variance of paid outputs) reaches the level at two consecutive grid budgets. False confidence = the true out-of-fold R2 at that budget is still below the level.

| pop | model | stopped | false_confidence | stop_budget | true_budget |
|---|---|---|---|---|---|
| NEW | M0 | 1.000 | 0.833 | 10.333 | 25.833 |
| NEW | M0Q | 1.000 | 0.750 | 10.333 | 20.833 |
| NEW | SHQ | 1.000 | 0.542 | 13.500 | 16.167 |
| NEW | TRQ | 1.000 | 0.167 | 4.167 | 6.167 |
| NEW | TRSQ | 1.000 | 0.167 | 4.167 | 4.833 |
| OLD | M0 | 1.000 | 0.750 | 12.143 | 23.143 |
| OLD | SHQ | 0.929 | 0.536 | 19.143 | 22.714 |

## 3. Region learning: {velocity spike log-ratio >= log 2} (exploratory)

| pop | model | acquisition | BA-AULC | budget-to-target (cens. 44) | BA B8 | BA B16 | BA B24 | BA B40 | band share paid | minority side paid B40 |
|---|---|---|---|---|---|---|---|---|---|---|
| NEW | M0 | ASTRA_STRADDLE_GLOBAL | 0.971 | 14.0 | 0.874 | 0.963 | 0.991 | 0.985 | 0.117 | 0.655 |
| NEW | M0 | ASTRA_SURPRISE | 0.967 | 14.0 | 0.874 | 0.956 | 0.985 | 0.985 | 0.111 | 0.657 |
| NEW | M0 | MAXIMIN | 0.957 | 15.0 | 0.874 | 0.965 | 0.965 | 0.966 | 0.061 | 0.517 |
| NEW | M0 | RANDOM | 0.948 | 15.0 | 0.874 | 0.932 | 0.953 | 0.978 | 0.044 | 0.406 |
| NEW | M0 | STRADDLE | 0.969 | 15.0 | 0.874 | 0.985 | 0.985 | 0.985 | 0.125 | 0.717 |
| NEW | M0 | TRUVAR | 0.960 | 17.0 | 0.874 | 0.907 | 0.979 | 0.985 | 0.118 | 0.673 |
| NEW | TRSQ | ASTRA_STRADDLE_GLOBAL | 0.979 | 9.0 | 0.969 | 0.989 | 0.984 | 0.979 | 0.120 | 0.656 |
| NEW | TRSQ | ASTRA_SURPRISE | 0.978 | 9.0 | 0.969 | 0.989 | 0.978 | 0.979 | 0.121 | 0.665 |
| NEW | TRSQ | MAXIMIN | 0.956 | 10.0 | 0.969 | 0.953 | 0.945 | 0.972 | 0.061 | 0.517 |
| NEW | TRSQ | RANDOM | 0.955 | 17.0 | 0.969 | 0.946 | 0.958 | 0.967 | 0.044 | 0.406 |
| NEW | TRSQ | STRADDLE | 0.982 | 9.0 | 0.969 | 0.984 | 0.990 | 0.973 | 0.131 | 0.694 |
| NEW | TRSQ | TRUVAR | 0.978 | 9.0 | 0.969 | 0.977 | 0.978 | 0.979 | 0.128 | 0.695 |
| OLD | M0 | ASTRA_STRADDLE_GLOBAL | 0.882 | 39.0 | 0.773 | 0.850 | 0.894 | 0.944 | 0.369 | 0.188 |
| OLD | M0 | ASTRA_SURPRISE | 0.878 | 37.0 | 0.773 | 0.825 | 0.883 | 0.940 | 0.345 | 0.191 |
| OLD | M0 | MAXIMIN | 0.870 | 44.0 | 0.773 | 0.849 | 0.895 | 0.913 | 0.194 | 0.165 |
| OLD | M0 | RANDOM | 0.851 | 44.0 | 0.773 | 0.789 | 0.862 | 0.894 | 0.214 | 0.137 |
| OLD | M0 | STRADDLE | 0.886 | 35.0 | 0.773 | 0.834 | 0.912 | 0.950 | 0.396 | 0.202 |
| OLD | M0 | TRUVAR | 0.894 | 37.0 | 0.773 | 0.885 | 0.881 | 0.905 | 0.350 | 0.191 |
| OLD | SHQ | ASTRA_STRADDLE_GLOBAL | 0.915 | 23.0 | 0.728 | 0.898 | 0.942 | 0.972 | 0.373 | 0.183 |
| OLD | SHQ | ASTRA_SURPRISE | 0.909 | 25.0 | 0.728 | 0.889 | 0.934 | 0.963 | 0.364 | 0.188 |
| OLD | SHQ | MAXIMIN | 0.884 | 35.0 | 0.728 | 0.847 | 0.904 | 0.932 | 0.194 | 0.165 |
| OLD | SHQ | RANDOM | 0.865 | 44.0 | 0.728 | 0.843 | 0.883 | 0.923 | 0.214 | 0.137 |
| OLD | SHQ | STRADDLE | 0.919 | 22.0 | 0.728 | 0.894 | 0.940 | 0.968 | 0.419 | 0.193 |
| OLD | SHQ | TRUVAR | 0.902 | 25.0 | 0.728 | 0.874 | 0.925 | 0.960 | 0.392 | 0.190 |

| pop | contrast | metric | mean | per-repeat | positive repeats |
|---|---|---|---|---|---|
| NEW | (a) STRADDLE - MAXIMIN, M0 | BA_AULC | +0.012 | [0.0116, 0.026, 0.0286, -0.0179] | 3/4 |
| NEW | (a) STRADDLE - MAXIMIN, M0 | budget_to_target | +0.000 | [-8.0, -4.0, 4.0, 8.0] | 2/4 |
| NEW | (a) STRADDLE - MAXIMIN, M0 | band_share_paid | +0.064 | [0.0813, 0.0573, 0.0431, 0.075] | 4/4 |
| NEW | (a) STRADDLE - MAXIMIN, TRSQ | BA_AULC | +0.026 | [0.0387, 0.0322, 0.0267, 0.008] | 4/4 |
| NEW | (a) STRADDLE - MAXIMIN, TRSQ | budget_to_target | -1.000 | [-4.0, 0.0, 0.0, 0.0] | 0/4 |
| NEW | (a) STRADDLE - MAXIMIN, TRSQ | band_share_paid | +0.070 | [0.0782, 0.0595, 0.0647, 0.0784] | 4/4 |
| NEW | (a) TRUVAR - STRADDLE, M0 | BA_AULC | -0.009 | [-0.012, 0.0009, -0.0087, -0.0158] | 1/4 |
| NEW | (a) TRUVAR - STRADDLE, M0 | budget_to_target | +2.000 | [4.0, 4.0, -4.0, 4.0] | 3/4 |
| NEW | (a) TRUVAR - STRADDLE, M0 | band_share_paid | -0.008 | [-0.0063, 0.0, 0.0, -0.0246] | 0/4 |
| NEW | (a) TRUVAR - STRADDLE, TRSQ | BA_AULC | -0.004 | [-0.0007, 0.001, -0.0125, -0.0029] | 1/4 |
| NEW | (a) TRUVAR - STRADDLE, TRSQ | budget_to_target | +0.000 | [0.0, 0.0, 0.0, 0.0] | 0/4 |
| NEW | (a) TRUVAR - STRADDLE, TRSQ | band_share_paid | -0.004 | [0.0, -0.0073, -0.0077, 0.0] | 0/4 |
| NEW | (b) TRSQ - M0 under STRADDLE | BA_AULC | +0.013 | [0.0249, 0.0158, -0.0057, 0.0175] | 3/4 |
| NEW | (b) TRSQ - M0 under STRADDLE | budget_to_target | -6.000 | [-4.0, -4.0, -8.0, -8.0] | 0/4 |
| NEW | (b) TRSQ - M0 under STRADDLE | band_share_paid | +0.006 | [-0.003, 0.0022, 0.0216, 0.0034] | 3/4 |
| NEW | (b) TRSQ - M0 under MAXIMIN | BA_AULC | -0.001 | [-0.0022, 0.0096, -0.0038, -0.0085] | 1/4 |
| NEW | (b) TRSQ - M0 under MAXIMIN | budget_to_target | -5.000 | [-8.0, -8.0, -4.0, 0.0] | 0/4 |
| NEW | (b) TRSQ - M0 under MAXIMIN | band_share_paid | +0.000 | [0.0, 0.0, 0.0, 0.0] | 0/4 |
| NEW | (c) local on - off (ASTRA), M0 | BA_AULC | -0.004 | [-0.0018, -0.0129, -0.0018, -0.0001] | 0/4 |
| NEW | (c) local on - off (ASTRA), M0 | budget_to_target | +0.000 | [0.0, 0.0, 0.0, 0.0] | 0/4 |
| NEW | (c) local on - off (ASTRA), M0 | band_share_paid | -0.006 | [-0.0125, 0.0125, -0.0188, -0.0063] | 1/4 |
| NEW | (c) local on - off (ASTRA), TRSQ | BA_AULC | -0.001 | [0.0, 0.0, -0.003, 0.0] | 0/4 |
| NEW | (c) local on - off (ASTRA), TRSQ | budget_to_target | +0.000 | [0.0, 0.0, 0.0, 0.0] | 0/4 |
| NEW | (c) local on - off (ASTRA), TRSQ | band_share_paid | +0.001 | [-0.0006, -0.0004, 0.0, 0.0065] | 1/4 |
| OLD | (a) STRADDLE - MAXIMIN, M0 | BA_AULC | +0.016 | [0.0141, -0.0148, 0.0381, 0.0253] | 3/4 |
| OLD | (a) STRADDLE - MAXIMIN, M0 | budget_to_target | -9.000 | [0.0, 0.0, -24.0, -12.0] | 0/4 |
| OLD | (a) STRADDLE - MAXIMIN, M0 | band_share_paid | +0.203 | [0.2117, 0.1915, 0.192, 0.2152] | 4/4 |
| OLD | (a) STRADDLE - MAXIMIN, SHQ | BA_AULC | +0.035 | [0.0358, 0.02, 0.0352, 0.0506] | 4/4 |
| OLD | (a) STRADDLE - MAXIMIN, SHQ | budget_to_target | -13.000 | [-24.0, -4.0, -4.0, -20.0] | 0/4 |
| OLD | (a) STRADDLE - MAXIMIN, SHQ | band_share_paid | +0.225 | [0.2784, 0.1963, 0.2226, 0.2028] | 4/4 |
| OLD | (a) TRUVAR - STRADDLE, M0 | BA_AULC | +0.008 | [0.0106, 0.0287, -0.0056, -0.0007] | 2/4 |
| OLD | (a) TRUVAR - STRADDLE, M0 | budget_to_target | +2.000 | [0.0, -12.0, 8.0, 12.0] | 2/4 |
| OLD | (a) TRUVAR - STRADDLE, M0 | band_share_paid | -0.046 | [-0.0439, -0.0769, -0.0808, 0.0159] | 1/4 |
| OLD | (a) TRUVAR - STRADDLE, SHQ | BA_AULC | -0.018 | [-0.0164, -0.0268, -0.0008, -0.0266] | 0/4 |
| OLD | (a) TRUVAR - STRADDLE, SHQ | budget_to_target | +3.000 | [8.0, 0.0, 4.0, 0.0] | 2/4 |
| OLD | (a) TRUVAR - STRADDLE, SHQ | band_share_paid | -0.027 | [-0.0828, 0.0523, -0.0622, -0.0163] | 1/4 |
| OLD | (b) SHQ - M0 under STRADDLE | BA_AULC | +0.033 | [0.0386, 0.0425, 0.0078, 0.0448] | 4/4 |
| OLD | (b) SHQ - M0 under STRADDLE | budget_to_target | -13.000 | [-24.0, -16.0, -4.0, -8.0] | 0/4 |
| OLD | (b) SHQ - M0 under STRADDLE | band_share_paid | +0.022 | [0.0668, 0.0048, 0.0306, -0.0124] | 3/4 |
| OLD | (b) SHQ - M0 under MAXIMIN | BA_AULC | +0.014 | [0.0169, 0.0077, 0.0107, 0.0195] | 4/4 |
| OLD | (b) SHQ - M0 under MAXIMIN | budget_to_target | -9.000 | [0.0, -12.0, -24.0, 0.0] | 0/4 |
| OLD | (b) SHQ - M0 under MAXIMIN | band_share_paid | +0.000 | [0.0, 0.0, 0.0, 0.0] | 0/4 |
| OLD | (c) local on - off (ASTRA), M0 | BA_AULC | -0.004 | [-0.0234, -0.0153, 0.0057, 0.0177] | 2/4 |
| OLD | (c) local on - off (ASTRA), M0 | budget_to_target | -2.000 | [20.0, 0.0, -12.0, -16.0] | 1/4 |
| OLD | (c) local on - off (ASTRA), M0 | band_share_paid | -0.024 | [-0.0089, -0.0616, 0.0185, -0.0432] | 1/4 |
| OLD | (c) local on - off (ASTRA), SHQ | BA_AULC | -0.006 | [-0.013, -0.0067, 0.0003, -0.0051] | 1/4 |
| OLD | (c) local on - off (ASTRA), SHQ | budget_to_target | +2.000 | [4.0, 4.0, 0.0, 0.0] | 2/4 |
| OLD | (c) local on - off (ASTRA), SHQ | band_share_paid | -0.009 | [0.0107, 0.0003, -0.0469, 0.0014] | 3/4 |

## 4. Keyhole label arm (NEW; exploratory)

| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |
|---|---|---|---|---|---|---|---|---|---|
| ACTIVE_E1_MAXIMIN | 8 | 0.639 | 0.966 | 0.312 | 0.683 | 7.0/10 | 0.086 | 1.276 | 0.722 |
| ACTIVE_E1_MAXIMIN | 16 | 0.556 | 0.988 | 0.125 | 0.700 | 9.2/10 | 0.082 | 1.329 | 0.778 |
| ACTIVE_E1_MAXIMIN | 24 | 0.603 | 0.978 | 0.229 | 0.700 | 8.0/10 | 0.079 | 1.170 | 0.849 |
| ACTIVE_E1_MAXIMIN | 40 | 0.682 | 0.968 | 0.396 | 0.742 | 7.0/10 | 0.076 | 0.716 | 0.914 |
| ACTIVE_E1_STRADDLE | 8 | 0.639 | 0.966 | 0.312 | 0.683 | 7.0/10 | 0.086 | 1.276 | 0.722 |
| ACTIVE_E1_STRADDLE | 16 | 0.691 | 0.986 | 0.396 | 0.808 | 9.2/10 | 0.062 | 0.727 | 0.788 |
| ACTIVE_E1_STRADDLE | 24 | 0.725 | 0.972 | 0.479 | 0.783 | 7.5/10 | 0.066 | 0.527 | 0.893 |
| ACTIVE_E1_STRADDLE | 40 | 0.737 | 0.974 | 0.500 | 0.800 | 7.8/10 | 0.063 | 0.568 | 0.918 |
| G3_MARGIN | 8 | 0.615 | 0.938 | 0.292 | 0.675 | 6.5/10 | 0.111 | 0.611 | 0.645 |
| G3_MARGIN | 16 | 0.636 | 0.960 | 0.312 | 0.675 | 6.2/10 | 0.112 | 0.389 | 0.661 |
| G3_MARGIN | 24 | 0.693 | 0.927 | 0.458 | 0.717 | 6.2/10 | 0.121 | 0.411 | 0.692 |
| G3_MARGIN | 40 | 0.687 | 0.958 | 0.417 | 0.708 | 6.2/10 | 0.094 | 0.339 | 0.794 |
| TR_E1_MAXIMIN | 8 | 0.659 | 0.964 | 0.354 | 0.700 | 6.8/10 | 0.082 | 1.135 | 0.888 |
| TR_E1_MAXIMIN | 16 | 0.585 | 0.982 | 0.188 | 0.708 | 8.8/10 | 0.082 | 1.642 | 0.804 |
| TR_E1_MAXIMIN | 24 | 0.623 | 0.976 | 0.271 | 0.717 | 8.0/10 | 0.077 | 0.901 | 0.896 |
| TR_E1_MAXIMIN | 40 | 0.696 | 0.976 | 0.417 | 0.775 | 8.0/10 | 0.065 | 0.578 | 0.918 |
| TR_E1_STRADDLE | 8 | 0.659 | 0.964 | 0.354 | 0.700 | 6.8/10 | 0.082 | 1.135 | 0.888 |
| TR_E1_STRADDLE | 16 | 0.713 | 0.968 | 0.458 | 0.758 | 7.0/10 | 0.066 | 0.847 | 0.873 |
| TR_E1_STRADDLE | 24 | 0.705 | 0.972 | 0.438 | 0.775 | 7.5/10 | 0.064 | 0.499 | 0.915 |
| TR_E1_STRADDLE | 40 | 0.707 | 0.976 | 0.438 | 0.792 | 8.0/10 | 0.061 | 0.517 | 0.922 |

BA-AULC (mean BA over B8-B40) per repeat:

| repeat | ACTIVE_E1_MAXIMIN | ACTIVE_E1_STRADDLE | G3_MARGIN | TR_E1_MAXIMIN | TR_E1_STRADDLE |
|---|---|---|---|---|---|
| 5 | 0.688 | 0.698 | 0.663 | 0.681 | 0.705 |
| 6 | 0.657 | 0.761 | 0.732 | 0.700 | 0.740 |
| 7 | 0.564 | 0.698 | 0.559 | 0.558 | 0.689 |
| 8 | 0.594 | 0.719 | 0.724 | 0.617 | 0.690 |

## 6. Cost breakdown

Simulation cost = paid queries (one simulation yields every monitor output; counted once). Output reading: 0.84 s per simulation (all channels, RC18 extraction). Modelling CPU per trajectory below; the OLD emulators were a one-off 5 s on historical runs.

| job | population | model | acq | trajectories | cpu_s_mean | cpu_s_total | simulations |
|---|---|---|---|---|---|---|---|
| reg-designs | NEW | M0 | MOIVR | 20 | 6.780 | 135.690 | 60.000 |
| reg-designs | NEW | M0 | RANDOM | 20 | 5.930 | 118.530 | 60.000 |
| reg-designs | NEW | TRSQ | MOIVR | 20 | 14.740 | 294.890 | 60.000 |
| reg-designs | NEW | TRSQ | RANDOM | 20 | 12.640 | 252.870 | 60.000 |
| reg-designs | OLD | M0 | MOIVR | 20 | 10.550 | 211.070 | 60.000 |
| reg-designs | OLD | M0 | RANDOM | 20 | 4.290 | 85.880 | 60.000 |
| reg-designs | OLD | SHQ | MOIVR | 20 | 19.970 | 399.340 | 60.000 |
| reg-designs | OLD | SHQ | RANDOM | 20 | 14.540 | 290.860 | 60.000 |
| reg-new-maximin | NEW | M0 | MAXIMIN | 20 | 6.230 | 124.570 | 60.000 |
| reg-new-maximin | NEW | M0Q | MAXIMIN | 20 | 5.860 | 117.120 | 60.000 |
| reg-new-maximin | NEW | SHQ | MAXIMIN | 20 | 14.150 | 282.920 | 60.000 |
| reg-new-maximin | NEW | TRQ | MAXIMIN | 20 | 7.690 | 153.870 | 60.000 |
| reg-new-maximin | NEW | TRSQ | MAXIMIN | 20 | 13.530 | 270.580 | 60.000 |
| reg-old-maximin | OLD | M0 | MAXIMIN | 20 | 6.280 | 125.640 | 60.000 |
| reg-old-maximin | OLD | SHQ | MAXIMIN | 20 | 19.450 | 389.050 | 60.000 |
| region | NEW | M0 | ASTRA_STRADDLE_GLOBAL | 20 | 0.410 | 8.140 | 40.000 |
| region | NEW | M0 | ASTRA_SURPRISE | 20 | 0.400 | 8.080 | 40.000 |
| region | NEW | M0 | MAXIMIN | 20 | 0.330 | 6.510 | 40.000 |
| region | NEW | M0 | RANDOM | 20 | 0.350 | 7.090 | 40.000 |
| region | NEW | M0 | STRADDLE | 20 | 0.380 | 7.680 | 40.000 |
| region | NEW | M0 | TRUVAR | 20 | 0.330 | 6.560 | 40.000 |
| region | NEW | TRSQ | ASTRA_STRADDLE_GLOBAL | 20 | 7.830 | 156.660 | 40.000 |
| region | NEW | TRSQ | ASTRA_SURPRISE | 20 | 7.010 | 140.220 | 40.000 |
| region | NEW | TRSQ | MAXIMIN | 20 | 6.370 | 127.320 | 40.000 |
| region | NEW | TRSQ | RANDOM | 20 | 7.000 | 140.100 | 40.000 |
| region | NEW | TRSQ | STRADDLE | 20 | 7.150 | 142.910 | 40.000 |
| region | NEW | TRSQ | TRUVAR | 20 | 7.060 | 141.180 | 40.000 |
| region | OLD | M0 | ASTRA_STRADDLE_GLOBAL | 20 | 0.440 | 8.840 | 40.000 |
| region | OLD | M0 | ASTRA_SURPRISE | 20 | 0.470 | 9.500 | 40.000 |
| region | OLD | M0 | MAXIMIN | 20 | 0.390 | 7.880 | 40.000 |
| region | OLD | M0 | RANDOM | 20 | 0.320 | 6.480 | 40.000 |
| region | OLD | M0 | STRADDLE | 20 | 0.450 | 8.910 | 40.000 |
| region | OLD | M0 | TRUVAR | 20 | 0.430 | 8.520 | 40.000 |
| region | OLD | SHQ | ASTRA_STRADDLE_GLOBAL | 20 | 8.880 | 177.670 | 40.000 |
| region | OLD | SHQ | ASTRA_SURPRISE | 20 | 9.010 | 180.130 | 40.000 |
| region | OLD | SHQ | MAXIMIN | 20 | 9.340 | 186.790 | 40.000 |
| region | OLD | SHQ | RANDOM | 20 | 8.620 | 172.370 | 40.000 |
| region | OLD | SHQ | STRADDLE | 20 | 9.200 | 184.090 | 40.000 |
| region | OLD | SHQ | TRUVAR | 20 | 8.660 | 173.100 | 40.000 |

Total modelling CPU of the final programme: 1.50 h.


## 7. Addendum A1 — robustness on DEV repeats 3-4 (exploratory)

NEW, TRSQ vs M0 under MAXIMIN: mean queries saved **22.3** (per repeat {3: 30.0, 4: 14.67}; per target {'laser_T0_W': 16.0, 'log_A_um': 12.0, 'log_ke_T0_nJ': 40.0, 'tmax_T0_K': 16.0, 'vmax_spike_logratio': 30.0, 'vmax_spike_us': 20.0}).

| pop | model | R2-AULC | budget-to-target | R2 B0 | R2 B8 | R2 B24 |
|---|---|---|---|---|---|---|
| NEW | M0 | 0.746 | 27.3 | nan | 0.287 | 0.783 |
| NEW | M0Q | 0.774 | 22.0 | nan | 0.287 | 0.799 |
| NEW | SHQ | 0.794 | 17.7 | nan | 0.321 | 0.811 |
| NEW | TRQ | 0.805 | 6.0 | 0.805 | 0.744 | 0.798 |
| NEW | TRSQ | 0.819 | 5.0 | 0.805 | 0.771 | 0.813 |
| OLD | M0 | 0.886 | 23.7 | nan | 0.578 | 0.900 |
| OLD | SHQ | 0.890 | 22.9 | nan | 0.441 | 0.909 |

## 8. Addendum A2 — which first NEW simulations to buy once transfer exists (TRSQ; exploratory)

| design | R2-AULC B0-B24 | R2 B4 | R2 B8 | R2 B16 | R2 B24 | budget to 0.95 x R2_full (cens. 28) | share of first 8 paid with ST > 400 K |
|---|---|---|---|---|---|---|---|
| GAP0 | 0.685 | 0.656 | 0.573 | 0.734 | 0.801 | 15.2 | 0.88 |
| MAXIMIN0 | 0.788 | 0.777 | 0.789 | 0.800 | 0.810 | 7.2 | 0.46 |
| MOIVR0 | 0.792 | 0.777 | 0.777 | 0.808 | 0.824 | 6.7 | 0.46 |
| RANDOM0 | 0.775 | 0.749 | 0.775 | 0.795 | 0.808 | 10.7 | 0.41 |

Per-repeat R2-AULC B0-B24 (mean of primary targets):

| repeat | GAP0 | MAXIMIN0 | MOIVR0 | RANDOM0 |
|---|---|---|---|---|
| 5 | 0.684 | 0.782 | 0.789 | 0.792 |
| 6 | 0.678 | 0.789 | 0.796 | 0.735 |
| 7 | 0.687 | 0.796 | 0.795 | 0.778 |
| 8 | 0.691 | 0.786 | 0.787 | 0.795 |

## 9. Addendum A3 — physics-mediated cross-campaign label model vs the final label arm (NEW; exploratory)

| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |
|---|---|---|---|---|---|---|---|---|---|
| ACTIVE_E1_MAXIMIN | 8 | 0.639 | 0.966 | 0.312 | 0.683 | 7.0/10 | 0.086 | 1.276 | 0.722 |
| ACTIVE_E1_MAXIMIN | 16 | 0.556 | 0.988 | 0.125 | 0.700 | 9.2/10 | 0.082 | 1.329 | 0.778 |
| ACTIVE_E1_MAXIMIN | 24 | 0.603 | 0.978 | 0.229 | 0.700 | 8.0/10 | 0.079 | 1.170 | 0.849 |
| ACTIVE_E1_MAXIMIN | 40 | 0.682 | 0.968 | 0.396 | 0.742 | 7.0/10 | 0.076 | 0.716 | 0.914 |
| ACTIVE_E1_STRADDLE | 8 | 0.639 | 0.966 | 0.312 | 0.683 | 7.0/10 | 0.086 | 1.276 | 0.722 |
| ACTIVE_E1_STRADDLE | 16 | 0.691 | 0.986 | 0.396 | 0.808 | 9.2/10 | 0.062 | 0.727 | 0.788 |
| ACTIVE_E1_STRADDLE | 24 | 0.725 | 0.972 | 0.479 | 0.783 | 7.5/10 | 0.066 | 0.527 | 0.893 |
| ACTIVE_E1_STRADDLE | 40 | 0.737 | 0.974 | 0.500 | 0.800 | 7.8/10 | 0.063 | 0.568 | 0.918 |
| G3_MARGIN | 8 | 0.615 | 0.938 | 0.292 | 0.675 | 6.5/10 | 0.111 | 0.611 | 0.645 |
| G3_MARGIN | 16 | 0.636 | 0.960 | 0.312 | 0.675 | 6.2/10 | 0.112 | 0.389 | 0.661 |
| G3_MARGIN | 24 | 0.693 | 0.927 | 0.458 | 0.717 | 6.2/10 | 0.121 | 0.411 | 0.692 |
| G3_MARGIN | 40 | 0.687 | 0.958 | 0.417 | 0.708 | 6.2/10 | 0.094 | 0.339 | 0.794 |
| PHYS_TR_MARGIN | 8 | 0.720 | 0.962 | 0.479 | 0.750 | 6.2/10 | 0.053 | 0.189 | 0.917 |
| PHYS_TR_MARGIN | 16 | 0.708 | 0.978 | 0.438 | 0.800 | 8.2/10 | 0.052 | 0.187 | 0.921 |
| PHYS_TR_MARGIN | 24 | 0.693 | 0.970 | 0.417 | 0.767 | 7.2/10 | 0.052 | 0.188 | 0.910 |
| PHYS_TR_MARGIN | 40 | 0.706 | 0.974 | 0.438 | 0.783 | 7.8/10 | 0.052 | 0.188 | 0.904 |
| PHYS_TR_MAXIMIN | 0 | 0.692 | 0.968 | 0.417 | 0.758 | 7.0/10 | 0.053 | 0.193 | 0.921 |
| PHYS_TR_MAXIMIN | 4 | 0.711 | 0.964 | 0.458 | 0.758 | 6.5/10 | 0.054 | 0.188 | 0.923 |
| PHYS_TR_MAXIMIN | 8 | 0.720 | 0.962 | 0.479 | 0.750 | 6.2/10 | 0.053 | 0.189 | 0.917 |
| PHYS_TR_MAXIMIN | 16 | 0.693 | 0.970 | 0.417 | 0.758 | 7.2/10 | 0.053 | 0.187 | 0.924 |
| PHYS_TR_MAXIMIN | 24 | 0.694 | 0.972 | 0.417 | 0.767 | 7.5/10 | 0.053 | 0.191 | 0.913 |
| PHYS_TR_MAXIMIN | 40 | 0.706 | 0.974 | 0.438 | 0.783 | 7.8/10 | 0.052 | 0.187 | 0.906 |
| TR_E1_MAXIMIN | 8 | 0.659 | 0.964 | 0.354 | 0.700 | 6.8/10 | 0.082 | 1.135 | 0.888 |
| TR_E1_MAXIMIN | 16 | 0.585 | 0.982 | 0.188 | 0.708 | 8.8/10 | 0.082 | 1.642 | 0.804 |
| TR_E1_MAXIMIN | 24 | 0.623 | 0.976 | 0.271 | 0.717 | 8.0/10 | 0.077 | 0.901 | 0.896 |
| TR_E1_MAXIMIN | 40 | 0.696 | 0.976 | 0.417 | 0.775 | 8.0/10 | 0.065 | 0.578 | 0.918 |
| TR_E1_STRADDLE | 8 | 0.659 | 0.964 | 0.354 | 0.700 | 6.8/10 | 0.082 | 1.135 | 0.888 |
| TR_E1_STRADDLE | 16 | 0.713 | 0.968 | 0.458 | 0.758 | 7.0/10 | 0.066 | 0.847 | 0.873 |
| TR_E1_STRADDLE | 24 | 0.705 | 0.972 | 0.438 | 0.775 | 7.5/10 | 0.064 | 0.499 | 0.915 |
| TR_E1_STRADDLE | 40 | 0.707 | 0.976 | 0.438 | 0.792 | 8.0/10 | 0.061 | 0.517 | 0.922 |

BA-AULC over B8-B40 per repeat (mean BA):

| repeat | ACTIVE_E1_MAXIMIN | ACTIVE_E1_STRADDLE | G3_MARGIN | PHYS_TR_MARGIN | PHYS_TR_MAXIMIN | TR_E1_MAXIMIN | TR_E1_STRADDLE |
|---|---|---|---|---|---|---|---|
| 5 | 0.688 | 0.698 | 0.663 | 0.693 | 0.704 | 0.681 | 0.705 |
| 6 | 0.657 | 0.761 | 0.732 | 0.694 | 0.709 | 0.700 | 0.740 |
| 7 | 0.564 | 0.698 | 0.559 | 0.697 | 0.711 | 0.558 | 0.689 |
| 8 | 0.594 | 0.719 | 0.724 | 0.714 | 0.704 | 0.617 | 0.690 |

## 10. D2 — native-time phase features: learning curves on the MAXIMIN design (exploratory)

| pop | feature | R2_full M0 | M0 budget-to-target | RICH budget-to-target | M0 R2 B8 | RICH R2 B0 | RICH R2 B8 | M0 R2 B40 | RICH R2 B40 |
|---|---|---|---|---|---|---|---|---|---|
| NEW | ke__epeak | 0.982 | 14.0 | 0.0 | 0.852 | 0.958 | 0.958 | 0.978 | 0.974 |
| NEW | ke__epeak_ms | -0.218 | 46.0 | 13.0 | -0.965 | 0.133 | -0.216 | -0.268 | -0.144 |
| NEW | ke__fluct | 0.082 | 64.0 | 0.0 | -0.795 | 0.211 | 0.171 | -0.416 | 0.168 |
| NEW | ke__overshoot | 0.694 | 48.0 | 58.0 | 0.008 | 0.566 | 0.535 | 0.615 | 0.584 |
| NEW | ke__peak | 0.619 | 43.0 | 2.0 | -0.231 | 0.638 | 0.607 | 0.531 | 0.651 |
| NEW | ke__peak_ms | 0.407 | 56.0 | 64.0 | -0.451 | 0.158 | 0.069 | 0.200 | 0.211 |
| NEW | ke__plateau | 0.662 | 29.0 | 0.0 | -0.514 | 0.677 | 0.676 | 0.560 | 0.661 |
| NEW | ke__t90_ms | 0.619 | 34.0 | 7.0 | 0.181 | 0.724 | 0.614 | 0.521 | 0.686 |
| NEW | t_on_ms | 1.000 | 4.0 | 12.0 | 0.996 | 0.790 | 0.891 | 1.000 | 0.968 |
| NEW | tmax__epeak | 0.811 | 43.0 | 64.0 | -0.101 | -19.040 | -18.776 | 0.723 | -22.497 |
| NEW | tmax__epeak_ms | 0.329 | 64.0 | 64.0 | -0.171 | 0.277 | 0.157 | 0.197 | 0.148 |
| NEW | tmax__fluct | -0.250 | 4.0 | 0.0 | -0.076 | -0.034 | -0.043 | -0.696 | -0.027 |
| NEW | tmax__overshoot | -0.898 | 4.0 | 0.0 | -0.015 | -0.162 | -0.165 | -0.594 | -0.721 |
| NEW | tmax__peak | -0.806 | 4.0 | 0.0 | -0.002 | -0.195 | -0.166 | -0.565 | -0.666 |
| NEW | tmax__peak_ms | 0.120 | 8.0 | 0.0 | 0.266 | 0.355 | 0.327 | 0.040 | 0.263 |
| NEW | tmax__plateau | 0.841 | 23.0 | 0.0 | 0.594 | 0.841 | 0.819 | 0.836 | 0.847 |
| NEW | tmax__t90_ms | 0.915 | 14.0 | 7.0 | 0.750 | 0.829 | 0.831 | 0.898 | 0.885 |
| OLD | ke__epeak | 0.988 | 15.0 | 14.0 | 0.620 | nan | 0.528 | 0.938 | 0.942 |
| OLD | ke__epeak_ms | 0.199 | 64.0 | 64.0 | -1.010 | nan | -0.342 | -0.461 | -0.166 |
| OLD | ke__fluct | 0.333 | 64.0 | 64.0 | -0.213 | nan | -0.115 | 0.172 | 0.169 |
| OLD | ke__overshoot | 0.573 | 64.0 | 64.0 | -0.159 | nan | -0.047 | 0.288 | 0.231 |
| OLD | ke__peak | 0.972 | 7.0 | 14.0 | 0.907 | nan | 0.620 | 0.945 | 0.954 |
| OLD | ke__peak_ms | 0.734 | 54.0 | 41.0 | 0.190 | nan | 0.076 | 0.635 | 0.656 |
| OLD | ke__plateau | 0.972 | 6.0 | 14.0 | 0.918 | nan | 0.630 | 0.949 | 0.955 |
| OLD | ke__t90_ms | 0.852 | 60.0 | 52.0 | 0.143 | nan | 0.134 | 0.719 | 0.755 |
| OLD | t_on_ms | 0.982 | 64.0 | 64.0 | 0.270 | nan | 0.448 | 0.761 | 0.645 |
| OLD | tmax__epeak | -0.098 | 15.0 | 9.0 | -2.482 | nan | -0.641 | -0.600 | 0.156 |
| OLD | tmax__epeak_ms | 0.737 | 64.0 | 64.0 | -0.015 | nan | 0.004 | 0.540 | 0.595 |
| OLD | tmax__fluct | 0.611 | 64.0 | 64.0 | -0.342 | nan | -0.215 | 0.161 | 0.283 |
| OLD | tmax__overshoot | -0.317 | 11.0 | 9.0 | -3.881 | nan | -0.845 | -0.723 | 0.001 |
| OLD | tmax__peak | -0.258 | 14.0 | 9.0 | -2.711 | nan | -0.589 | -0.438 | 0.195 |
| OLD | tmax__peak_ms | 0.360 | 64.0 | 64.0 | -0.378 | nan | -0.113 | 0.226 | 0.152 |
| OLD | tmax__plateau | 0.943 | 19.0 | 18.0 | 0.564 | nan | 0.134 | 0.896 | 0.910 |
| OLD | tmax__t90_ms | 0.799 | 64.0 | 42.0 | -0.124 | nan | 0.096 | 0.571 | 0.718 |

Native early-horizon curves (0-0.25 ms after onset): R2_curve vs the mean curve and peak errors (mean over folds and repeats):

| pop | channel | model | budget | R2c KRONn | R2c PHASE | R2c PHASE_PCA | peak-time err KRONn / PHASE / PCA / scalar (ms) | peak err KRONn / scalar |
|---|---|---|---|---|---|---|---|---|
| NEW | ke | M0 | 16 | 0.958 | 0.571 | 0.830 | 0.0055 / 0.0057 / 0.0058 / 0.0078 | 0.137 / 0.110 |
| NEW | ke | M0 | 40 | 0.980 | 0.609 | 0.848 | 0.0057 / 0.0061 / 0.0061 / 0.0074 | 0.074 / 0.066 |
| NEW | ke | M0 | full | 0.985 | 0.658 | 0.873 | 0.0056 / 0.0058 / 0.0058 / 0.0070 | 0.064 / 0.059 |
| NEW | ke | TRSQ | 16 | 0.958 | 0.621 | 0.873 | 0.0055 / 0.0057 / 0.0058 / 0.0073 | 0.137 / 0.089 |
| NEW | ke | TRSQ | 40 | 0.980 | 0.650 | 0.884 | 0.0057 / 0.0060 / 0.0061 / 0.0070 | 0.074 / 0.073 |
| NEW | ke | TRSQ | full | 0.985 | 0.660 | 0.894 | 0.0056 / 0.0057 / 0.0057 / 0.0062 | 0.064 / 0.072 |
| NEW | tmax | M0 | 16 | 0.504 | -0.044 | 0.328 | 0.0193 / 0.0615 / 0.0686 / 0.0191 | 168.645 / 97.391 |
| NEW | tmax | M0 | 40 | 0.576 | 0.069 | 0.506 | 0.0182 / 0.0620 / 0.0652 / 0.0168 | 154.908 / 76.479 |
| NEW | tmax | M0 | full | 0.573 | 0.147 | 0.579 | 0.0179 / 0.0626 / 0.0670 / 0.0154 | 151.039 / 65.031 |
| NEW | tmax | TRSQ | 16 | 0.504 | -0.051 | 0.306 | 0.0193 / 0.0552 / 0.0627 / 0.0162 | 168.645 / 391.881 |
| NEW | tmax | TRSQ | 40 | 0.576 | 0.051 | 0.466 | 0.0182 / 0.0609 / 0.0637 / 0.0164 | 154.908 / 387.923 |
| NEW | tmax | TRSQ | full | 0.573 | 0.138 | 0.564 | 0.0179 / 0.0604 / 0.0646 / 0.0163 | 151.039 / 293.703 |
| OLD | ke | M0 | 16 | 0.584 | 0.120 | 0.407 | 0.0058 / 0.0054 / 0.0060 / 0.0133 | 0.331 / 0.157 |
| OLD | ke | M0 | 40 | 0.856 | 0.189 | 0.429 | 0.0055 / 0.0055 / 0.0056 / 0.0093 | 0.115 / 0.107 |
| OLD | ke | M0 | full | 0.958 | 0.288 | 0.785 | 0.0056 / 0.0051 / 0.0057 / 0.0066 | 0.064 / 0.057 |
| OLD | ke | SHQ | 16 | 0.584 | 0.119 | 0.445 | 0.0058 / 0.0055 / 0.0061 / 0.0125 | 0.331 / 0.148 |
| OLD | ke | SHQ | 40 | 0.856 | 0.200 | 0.461 | 0.0055 / 0.0054 / 0.0055 / 0.0093 | 0.115 / 0.104 |
| OLD | ke | SHQ | full | 0.958 | 0.304 | 0.792 | 0.0056 / 0.0051 / 0.0057 / 0.0068 | 0.064 / 0.062 |
| OLD | tmax | M0 | 16 | 0.617 | 0.624 | 0.634 | 0.0623 / 0.0526 / 0.0534 / 0.0461 | 185.592 / 226.944 |
| OLD | tmax | M0 | 40 | 0.735 | 0.730 | 0.782 | 0.0431 / 0.0498 / 0.0467 / 0.0354 | 133.632 / 162.447 |
| OLD | tmax | M0 | full | 0.755 | 0.753 | 0.822 | 0.0369 / 0.0505 / 0.0430 / 0.0253 | 135.275 / 143.483 |
| OLD | tmax | SHQ | 16 | 0.617 | 0.694 | 0.714 | 0.0623 / 0.0486 / 0.0486 / 0.0478 | 185.592 / 171.855 |
| OLD | tmax | SHQ | 40 | 0.735 | 0.752 | 0.797 | 0.0431 / 0.0478 / 0.0451 / 0.0348 | 133.632 / 120.015 |
| OLD | tmax | SHQ | full | 0.755 | 0.765 | 0.830 | 0.0369 / 0.0505 / 0.0431 / 0.0254 | 135.275 / 149.507 |


## 11. Addendum A4 — PHYS_TR prior + NEW-label residual GPC (NEW; exploratory; registered before it ran)

GPC fits: 1393 succeeded, 67 failed (prior used at that budget), 20 prior-only evaluations (no paid label: PHYS_GPC_MAXIMIN at B0).

| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |
|---|---|---|---|---|---|---|---|---|---|
| ACTIVE_E1_STRADDLE | 8 | 0.639 | 0.966 | 0.312 | 0.683 | 7.0/10 | 0.086 | 1.276 | 0.722 |
| ACTIVE_E1_STRADDLE | 16 | 0.691 | 0.986 | 0.396 | 0.808 | 9.2/10 | 0.062 | 0.727 | 0.788 |
| ACTIVE_E1_STRADDLE | 24 | 0.725 | 0.972 | 0.479 | 0.783 | 7.5/10 | 0.066 | 0.527 | 0.893 |
| ACTIVE_E1_STRADDLE | 32 | 0.737 | 0.974 | 0.500 | 0.800 | 7.8/10 | 0.062 | 0.529 | 0.925 |
| ACTIVE_E1_STRADDLE | 40 | 0.737 | 0.974 | 0.500 | 0.800 | 7.8/10 | 0.063 | 0.568 | 0.918 |
| G3_MARGIN | 8 | 0.615 | 0.937 | 0.292 | 0.675 | 6.5/10 | 0.111 | 0.611 | 0.645 |
| G3_MARGIN | 16 | 0.636 | 0.960 | 0.312 | 0.675 | 6.2/10 | 0.112 | 0.389 | 0.661 |
| G3_MARGIN | 24 | 0.693 | 0.927 | 0.458 | 0.717 | 6.2/10 | 0.121 | 0.411 | 0.692 |
| G3_MARGIN | 32 | 0.696 | 0.954 | 0.438 | 0.700 | 5.8/10 | 0.101 | 0.362 | 0.786 |
| G3_MARGIN | 40 | 0.687 | 0.958 | 0.417 | 0.708 | 6.2/10 | 0.094 | 0.339 | 0.794 |
| PHYS_GPC_MARGIN | 8 | 0.704 | 0.970 | 0.438 | 0.758 | 7.2/10 | 0.052 | 0.178 | 0.917 |
| PHYS_GPC_MARGIN | 16 | 0.709 | 0.980 | 0.438 | 0.817 | 8.5/10 | 0.052 | 0.170 | 0.914 |
| PHYS_GPC_MARGIN | 24 | 0.701 | 0.964 | 0.438 | 0.750 | 6.5/10 | 0.053 | 0.172 | 0.925 |
| PHYS_GPC_MARGIN | 32 | 0.701 | 0.964 | 0.438 | 0.750 | 6.5/10 | 0.052 | 0.171 | 0.917 |
| PHYS_GPC_MARGIN | 40 | 0.701 | 0.964 | 0.438 | 0.750 | 6.5/10 | 0.052 | 0.172 | 0.905 |
| PHYS_GPC_MAXIMIN | 0 | 0.692 | 0.968 | 0.417 | 0.758 | 7.0/10 | 0.053 | 0.193 | 0.920 |
| PHYS_GPC_MAXIMIN | 4 | 0.721 | 0.964 | 0.479 | 0.750 | 6.5/10 | 0.053 | 0.177 | 0.903 |
| PHYS_GPC_MAXIMIN | 8 | 0.704 | 0.970 | 0.438 | 0.758 | 7.2/10 | 0.052 | 0.178 | 0.917 |
| PHYS_GPC_MAXIMIN | 16 | 0.686 | 0.976 | 0.396 | 0.767 | 8.0/10 | 0.053 | 0.173 | 0.914 |
| PHYS_GPC_MAXIMIN | 24 | 0.718 | 0.978 | 0.458 | 0.800 | 8.2/10 | 0.054 | 0.175 | 0.919 |
| PHYS_GPC_MAXIMIN | 32 | 0.717 | 0.976 | 0.458 | 0.792 | 8.0/10 | 0.053 | 0.176 | 0.906 |
| PHYS_GPC_MAXIMIN | 40 | 0.714 | 0.970 | 0.458 | 0.767 | 7.2/10 | 0.055 | 0.178 | 0.906 |
| PHYS_TR_MARGIN | 8 | 0.720 | 0.962 | 0.479 | 0.750 | 6.2/10 | 0.053 | 0.189 | 0.917 |
| PHYS_TR_MARGIN | 16 | 0.708 | 0.978 | 0.438 | 0.800 | 8.2/10 | 0.052 | 0.187 | 0.921 |
| PHYS_TR_MARGIN | 24 | 0.693 | 0.970 | 0.417 | 0.767 | 7.2/10 | 0.052 | 0.188 | 0.910 |
| PHYS_TR_MARGIN | 32 | 0.703 | 0.968 | 0.438 | 0.767 | 7.0/10 | 0.053 | 0.192 | 0.904 |
| PHYS_TR_MARGIN | 40 | 0.706 | 0.974 | 0.438 | 0.783 | 7.8/10 | 0.052 | 0.188 | 0.904 |
| PHYS_TR_MAXIMIN | 0 | 0.692 | 0.968 | 0.417 | 0.758 | 7.0/10 | 0.053 | 0.193 | 0.921 |
| PHYS_TR_MAXIMIN | 4 | 0.711 | 0.964 | 0.458 | 0.758 | 6.5/10 | 0.054 | 0.188 | 0.923 |
| PHYS_TR_MAXIMIN | 8 | 0.720 | 0.962 | 0.479 | 0.750 | 6.2/10 | 0.053 | 0.189 | 0.917 |
| PHYS_TR_MAXIMIN | 16 | 0.693 | 0.970 | 0.417 | 0.758 | 7.2/10 | 0.053 | 0.187 | 0.924 |
| PHYS_TR_MAXIMIN | 24 | 0.694 | 0.972 | 0.417 | 0.767 | 7.5/10 | 0.053 | 0.191 | 0.913 |
| PHYS_TR_MAXIMIN | 32 | 0.717 | 0.976 | 0.458 | 0.800 | 8.0/10 | 0.052 | 0.187 | 0.908 |
| PHYS_TR_MAXIMIN | 40 | 0.706 | 0.974 | 0.438 | 0.783 | 7.8/10 | 0.052 | 0.187 | 0.906 |

BA-AULC over B8-B40 per repeat (mean BA), all label arms:

| repeat | ACTIVE_E1_MAXIMIN | ACTIVE_E1_STRADDLE | G3_MARGIN | PHYS_GPC_MARGIN | PHYS_GPC_MAXIMIN | PHYS_TR_MARGIN | PHYS_TR_MAXIMIN | TR_E1_MAXIMIN | TR_E1_STRADDLE |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.688 | 0.698 | 0.663 | 0.688 | 0.722 | 0.693 | 0.704 | 0.681 | 0.705 |
| 6 | 0.657 | 0.761 | 0.732 | 0.702 | 0.715 | 0.694 | 0.709 | 0.700 | 0.740 |
| 7 | 0.564 | 0.698 | 0.559 | 0.686 | 0.701 | 0.697 | 0.711 | 0.558 | 0.689 |
| 8 | 0.594 | 0.719 | 0.724 | 0.721 | 0.696 | 0.714 | 0.704 | 0.617 | 0.690 |

Difference to ACTIVE_E1_STRADDLE (the final label arm's best) per repeat:

| repeat | ACTIVE_E1_MAXIMIN | G3_MARGIN | PHYS_GPC_MARGIN | PHYS_GPC_MAXIMIN | PHYS_TR_MARGIN | PHYS_TR_MAXIMIN | TR_E1_MAXIMIN | TR_E1_STRADDLE |
|---|---|---|---|---|---|---|---|---|
| 5 | -0.011 | -0.035 | -0.010 | 0.024 | -0.005 | 0.006 | -0.017 | 0.007 |
| 6 | -0.104 | -0.029 | -0.059 | -0.046 | -0.067 | -0.052 | -0.062 | -0.021 |
| 7 | -0.133 | -0.138 | -0.012 | 0.003 | -0.001 | 0.013 | -0.140 | -0.009 |
| 8 | -0.125 | 0.005 | 0.002 | -0.023 | -0.005 | -0.015 | -0.102 | -0.029 |


## 12. D2 — the two pre-registered rules (computed; exploratory)

**Rule 1 — PHASE BEATS KRONn** (PHASE or PHASE_PCA early-horizon RMSE <= 0.95 x KRONn in >= 3 of 4 repeats, whole pool):

| population | channel | model | repeats_won | rmse_KRONn | rmse_PHASE | rmse_PHASE_PCA | verdict |
|---|---|---|---|---|---|---|---|
| NEW | ke | M0 | 0 | 0.098 | 0.472 | 0.280 | no |
| NEW | ke | TRSQ | 0 | 0.098 | 0.472 | 0.256 | no |
| NEW | tmax | M0 | 0 | 112.119 | 156.755 | 110.065 | no |
| NEW | tmax | TRSQ | 0 | 112.119 | 157.414 | 111.914 | no |
| OLD | ke | M0 | 0 | 0.172 | 0.703 | 0.384 | no |
| OLD | ke | SHQ | 0 | 0.172 | 0.696 | 0.377 | no |
| OLD | tmax | M0 | 4 | 156.975 | 159.742 | 140.016 | PHASE BEATS KRONn |
| OLD | tmax | SHQ | 4 | 156.975 | 156.721 | 137.813 | PHASE BEATS KRONn |

**Rule 2 — TEMPORAL BEATS SCALAR** (curve-derived error <= 0.95 x the direct scalar GP error in >= 3 of 4 repeats). The protocol does not single out one curve model or budget, so every curve model and budget is evaluated (full table: report/D2_rule2_summary.csv). Diagnostic added at reporting time: whether the x-independent MEAN curve (mean paid curve) also meets the rule in the same cell; if it does, the cell says the scalar GP is poor, not that the curve model learned x-dependence.

Curve-model cells meeting the rule: 49 of 144; of these, 42 are also met by the MEAN curve. Cells met by a curve model but NOT by the MEAN curve:

| population | channel | model | quantity | curve_model | budget | repeats_won | curve_err | scalar_err | verdict |
|---|---|---|---|---|---|---|---|---|---|
| NEW | ke | TRSQ | early peak amplitude | KRONn | full | 4 | 0.064 | 0.072 | TEMPORAL BEATS SCALAR |
| NEW | ke | TRSQ | early peak time | KRONn | full | 4 | 5.593 | 6.182 | TEMPORAL BEATS SCALAR |
| NEW | ke | TRSQ | early peak time | PHASE_PCA | full | 3 | 5.704 | 6.182 | TEMPORAL BEATS SCALAR |
| OLD | tmax | M0 | early peak amplitude | PHASE_PCA | full | 4 | 111.440 | 144.006 | TEMPORAL BEATS SCALAR |
| OLD | tmax | SHQ | early peak amplitude | KRONn | full | 4 | 135.828 | 150.308 | TEMPORAL BEATS SCALAR |
| OLD | tmax | SHQ | early peak amplitude | PHASE | full | 4 | 129.947 | 150.308 | TEMPORAL BEATS SCALAR |
| OLD | tmax | SHQ | early peak amplitude | PHASE_PCA | full | 4 | 109.236 | 150.308 | TEMPORAL BEATS SCALAR |

Units in this table: µs for peak times; K (temperature) or log nJ (KE) for amplitudes (the CSV keeps ms).


## 13. False confidence as worded in PROTOCOL_20261018 §5 (exploratory)

Share of test runs outside the 90 % observation interval at the budget where the arm first claims the level (claim = the learner-side self-R2 rule of section 5b, committed before any final result). Nominal value 0.10. Section 5b reports a different, trajectory-level measure (true R2 still below the level at the claim); both are kept.

| pop | model | trajectories | claim_budget | share_outside_90_mean | share_outside_90_max |
|---|---|---|---|---|---|
| NEW | M0 | 24 | 10.333 | 0.286 | 0.430 |
| NEW | M0Q | 24 | 10.333 | 0.310 | 0.474 |
| NEW | SHQ | 24 | 13.500 | 0.191 | 0.385 |
| NEW | TRQ | 24 | 4.167 | 0.183 | 0.459 |
| NEW | TRSQ | 24 | 4.167 | 0.169 | 0.348 |
| OLD | M0 | 28 | 12.143 | 0.255 | 0.559 |
| OLD | SHQ | 26 | 15.692 | 0.133 | 0.241 |

