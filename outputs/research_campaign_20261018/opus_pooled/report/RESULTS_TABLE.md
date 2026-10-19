# RC19 pooled from-scratch benchmark — single results table (DEV; final repeats 3–10; frozen protocol PROTOCOL_RC19.md)

One pool of 541 inspected SPH simulations; every revealed simulation counts, startup included; learners refit on all revealed rows after each query.

## A. Physical outputs (pooled, from scratch)

**PRIMARY A — SHQ vs M0, matched MAXIMIN, R²-AULC over B8–B80 (mean over the primary outputs): BETTER (DEV)**
Δ per repeat: {"3": 0.028, "4": 0.0774, "5": 0.0351, "6": 0.0359, "7": 0.0268, "8": 0.0206, "9": 0.0256, "10": 0.0285}; mean +0.0347; practical margin 0.02.

Exploratory contrasts (R²-AULC, mean over primary outputs; all repeats shown):

| contrast | mean | per_repeat | positive_repeats |
|---|---|---|---|
| quality: M0Q − M0 | 0.0091 | {"3": 0.0044, "4": 0.0367, "5": 0.0017, "6": 0.0126, "7": 0.0073, "8": 0.0013, "9": 0.0062, "10": 0.0024} | 8/8 |
| sharing: SHQ − M0Q | 0.0257 | {"3": 0.0236, "4": 0.0407, "5": 0.0334, "6": 0.0233, "7": 0.0195, "8": 0.0193, "9": 0.0194, "10": 0.0261} | 8/8 |
| MOIVR − MAXIMIN given SHQ | 0.0098 | {"3": 0.0024, "4": 0.0123, "5": 0.0126, "6": 0.0077, "7": 0.0164, "8": -0.0016, "9": 0.0164, "10": 0.012} | 7/8 |
| RANDOM − MAXIMIN given SHQ | -0.0004 | {"3": -0.008, "4": -0.0015, "5": -0.0027, "6": -0.0102, "7": -0.0031, "8": -0.003, "9": 0.0168, "10": 0.0087} | 2/8 |
| MOIVR − MAXIMIN given M0Q | 0.0240 | {"3": 0.0153, "4": 0.0366, "5": 0.0385, "6": 0.0112, "7": 0.023, "8": 0.0078, "9": 0.0311, "10": 0.0285} | 8/8 |
| RANDOM − MAXIMIN given M0Q | 0.0015 | {"3": -0.0053, "4": -0.0081, "5": 0.025, "6": -0.0107, "7": -0.0025, "8": -0.0131, "9": 0.0187, "10": 0.0082} | 3/8 |
| SHQ − M0Q given MOIVR | 0.0114 | {"3": 0.0108, "4": 0.0164, "5": 0.0076, "6": 0.0198, "7": 0.0128, "8": 0.0098, "9": 0.0047, "10": 0.0096} | 8/8 |

Joint campaign endpoint (all primary outputs at their absolute levels {"log_A_um": 0.85, "log_ke_T0_nJ": 0.85, "vmax_spike_logratio": 0.8, "vmax_spike_us": 0.6, "laser_T0_W": 0.85, "tmax_T0_K": 0.85, "log_etot_T0_J": 0.8, "log_npart_T0": 0.8} simultaneously; confirmed = also at b+4; per repeat; '–' = not reached, censored):

| model | acq | completed | first_qualifying | confirmed |
|---|---|---|---|---|
| M0 | MAXIMIN | 0/8 | 72,–,–,–,68,80,–,– | –,–,–,–,–,–,–,– |
| M0Q | MAXIMIN | 0/8 | –,–,–,–,68,–,–,– | –,–,–,–,–,–,–,– |
| M0Q | MOIVR | 5/8 | 52,72,–,76,44,–,44,64 | 52,–,–,76,44,–,44,64 |
| M0Q | RANDOM | 2/8 | –,80,64,68,68,–,64,– | –,–,–,–,68,–,64,– |
| SHQ | MAXIMIN | 0/8 | –,–,–,–,–,–,–,– | –,–,–,–,–,–,–,– |
| SHQ | MOIVR | 1/8 | –,56,–,–,–,–,–,– | –,56,–,–,–,–,–,– |
| SHQ | RANDOM | 7/8 | 64,64,36,72,64,64,72,60 | –,64,36,72,64,64,72,60 |

Per-output endpoints (confirmed budget per repeat; '–' = censored at the horizon):

| model | acq | target | completed | confirmed | AULC |
|---|---|---|---|---|---|
| M0 | MAXIMIN | laser_T0_W | 8/8 | 20,20,24,20,28,20,20,36 | 0.892 |
| M0 | MAXIMIN | log_A_um | 8/8 | 12,16,12,12,16,16,8,12 | 0.944 |
| M0 | MAXIMIN | log_etot_T0_J | 8/8 | 20,44,16,20,20,16,16,16 | 0.851 |
| M0 | MAXIMIN | log_ke_T0_nJ | 8/8 | 8,16,8,8,8,8,8,8 | 0.946 |
| M0 | MAXIMIN | log_npart_T0 | 8/8 | 20,44,16,20,20,16,16,16 | 0.831 |
| M0 | MAXIMIN | tmax_T0_K | 8/8 | 12,12,16,12,8,8,12,16 | 0.940 |
| M0 | MAXIMIN | vmax_spike_logratio | 8/8 | 28,44,48,36,44,28,36,44 | 0.776 |
| M0 | MAXIMIN | vmax_spike_us | 0/8 | –,–,–,–,–,–,–,– | 0.359 |
| M0Q | MAXIMIN | laser_T0_W | 8/8 | 20,20,24,24,28,20,20,36 | 0.895 |
| M0Q | MAXIMIN | log_A_um | 8/8 | 12,16,12,12,16,16,8,12 | 0.944 |
| M0Q | MAXIMIN | log_etot_T0_J | 8/8 | 16,12,16,20,20,16,16,16 | 0.880 |
| M0Q | MAXIMIN | log_ke_T0_nJ | 8/8 | 8,8,8,8,8,8,8,8 | 0.950 |
| M0Q | MAXIMIN | log_npart_T0 | 8/8 | 16,16,16,20,20,16,16,16 | 0.866 |
| M0Q | MAXIMIN | tmax_T0_K | 8/8 | 12,12,16,12,8,8,12,16 | 0.938 |
| M0Q | MAXIMIN | vmax_spike_logratio | 8/8 | 28,44,48,40,44,28,36,44 | 0.780 |
| M0Q | MAXIMIN | vmax_spike_us | 0/8 | –,–,–,–,–,–,–,– | 0.356 |
| M0Q | MOIVR | laser_T0_W | 8/8 | 20,24,20,24,24,24,28,28 | 0.906 |
| M0Q | MOIVR | log_A_um | 8/8 | 12,16,12,12,16,12,8,12 | 0.943 |
| M0Q | MOIVR | log_etot_T0_J | 8/8 | 16,12,12,16,20,16,16,16 | 0.880 |
| M0Q | MOIVR | log_ke_T0_nJ | 8/8 | 8,8,8,8,8,8,8,8 | 0.953 |
| M0Q | MOIVR | log_npart_T0 | 8/8 | 20,16,12,16,20,16,16,16 | 0.865 |
| M0Q | MOIVR | tmax_T0_K | 8/8 | 12,12,12,12,8,8,12,12 | 0.944 |
| M0Q | MOIVR | vmax_spike_logratio | 8/8 | 28,28,24,24,28,20,36,28 | 0.801 |
| M0Q | MOIVR | vmax_spike_us | 5/8 | 52,–,–,76,44,–,44,64 | 0.510 |
| M0Q | RANDOM | laser_T0_W | 8/8 | 20,24,16,20,20,24,20,24 | 0.901 |
| M0Q | RANDOM | log_A_um | 8/8 | 12,20,16,12,16,16,8,12 | 0.933 |
| M0Q | RANDOM | log_etot_T0_J | 8/8 | 16,12,16,24,20,24,16,16 | 0.863 |
| M0Q | RANDOM | log_ke_T0_nJ | 8/8 | 8,8,8,8,20,8,8,8 | 0.946 |
| M0Q | RANDOM | log_npart_T0 | 8/8 | 20,16,24,24,20,24,16,20 | 0.850 |
| M0Q | RANDOM | tmax_T0_K | 8/8 | 12,12,12,12,8,8,12,12 | 0.935 |
| M0Q | RANDOM | vmax_spike_logratio | 8/8 | 44,48,52,36,52,44,40,36 | 0.763 |
| M0Q | RANDOM | vmax_spike_us | 2/8 | –,–,–,–,68,–,64,– | 0.432 |
| SHQ | MAXIMIN | laser_T0_W | 8/8 | 16,20,24,20,24,20,16,20 | 0.911 |
| SHQ | MAXIMIN | log_A_um | 8/8 | 12,12,12,8,12,12,12,12 | 0.944 |
| SHQ | MAXIMIN | log_etot_T0_J | 8/8 | 12,12,12,12,16,12,16,12 | 0.896 |
| SHQ | MAXIMIN | log_ke_T0_nJ | 8/8 | 8,8,12,8,12,8,12,8 | 0.955 |
| SHQ | MAXIMIN | log_npart_T0 | 8/8 | 12,12,12,12,16,12,16,12 | 0.882 |
| SHQ | MAXIMIN | tmax_T0_K | 8/8 | 12,12,12,12,12,12,12,12 | 0.936 |
| SHQ | MAXIMIN | vmax_spike_logratio | 8/8 | 20,40,40,20,24,24,36,48 | 0.795 |
| SHQ | MAXIMIN | vmax_spike_us | 0/8 | –,–,–,–,–,–,–,– | 0.498 |
| SHQ | MOIVR | laser_T0_W | 8/8 | 16,16,16,16,16,16,20,16 | 0.927 |
| SHQ | MOIVR | log_A_um | 8/8 | 12,12,12,8,12,12,12,12 | 0.946 |
| SHQ | MOIVR | log_etot_T0_J | 8/8 | 16,12,16,16,16,16,16,12 | 0.896 |
| SHQ | MOIVR | log_ke_T0_nJ | 8/8 | 8,8,12,8,12,8,12,8 | 0.959 |
| SHQ | MOIVR | log_npart_T0 | 8/8 | 16,12,16,16,16,16,16,16 | 0.882 |
| SHQ | MOIVR | tmax_T0_K | 8/8 | 12,12,12,12,12,12,12,12 | 0.944 |
| SHQ | MOIVR | vmax_spike_logratio | 8/8 | 24,28,20,24,28,24,28,32 | 0.806 |
| SHQ | MOIVR | vmax_spike_us | 1/8 | –,56,–,–,–,–,–,– | 0.534 |
| SHQ | RANDOM | laser_T0_W | 8/8 | 20,20,24,20,20,16,16,24 | 0.918 |
| SHQ | RANDOM | log_A_um | 8/8 | 12,12,16,8,12,16,12,12 | 0.939 |
| SHQ | RANDOM | log_etot_T0_J | 8/8 | 16,12,16,16,16,16,16,16 | 0.880 |
| SHQ | RANDOM | log_ke_T0_nJ | 8/8 | 8,8,16,8,12,8,12,8 | 0.952 |
| SHQ | RANDOM | log_npart_T0 | 8/8 | 16,12,24,16,16,16,16,16 | 0.865 |
| SHQ | RANDOM | tmax_T0_K | 8/8 | 12,12,16,12,16,12,12,12 | 0.934 |
| SHQ | RANDOM | vmax_spike_logratio | 8/8 | 28,28,28,28,48,32,36,24 | 0.798 |
| SHQ | RANDOM | vmax_spike_us | 7/8 | –,64,36,72,64,64,72,60 | 0.528 |

Accuracy and calibration at matched budgets (mean over primary outputs and repeats):

| model | acq | budget | R2 | cov90 | nlpd |
|---|---|---|---|---|---|
| M0 | MAXIMIN | 16 | 0.760 | 0.782 | 3.791 |
| M0 | MAXIMIN | 40 | 0.824 | 0.837 | 3.309 |
| M0 | MAXIMIN | 80 | 0.876 | 0.871 | 3.553 |
| M0Q | MAXIMIN | 16 | 0.769 | 0.780 | 3.750 |
| M0Q | MAXIMIN | 40 | 0.834 | 0.832 | 3.217 |
| M0Q | MAXIMIN | 80 | 0.884 | 0.862 | 3.659 |
| M0Q | MOIVR | 16 | 0.789 | 0.724 | 4.787 |
| M0Q | MOIVR | 40 | 0.873 | 0.820 | 3.733 |
| M0Q | MOIVR | 80 | 0.901 | 0.853 | 3.831 |
| M0Q | RANDOM | 16 | 0.743 | 0.745 | 4.074 |
| M0Q | RANDOM | 40 | 0.852 | 0.828 | 4.227 |
| M0Q | RANDOM | 80 | 0.894 | 0.869 | 4.511 |
| SHQ | MAXIMIN | 16 | 0.824 | 0.850 | 2.454 |
| SHQ | MAXIMIN | 40 | 0.869 | 0.874 | 2.817 |
| SHQ | MAXIMIN | 80 | 0.889 | 0.886 | 3.499 |
| SHQ | MOIVR | 16 | 0.844 | 0.827 | 2.710 |
| SHQ | MOIVR | 40 | 0.882 | 0.864 | 2.859 |
| SHQ | MOIVR | 80 | 0.897 | 0.880 | 4.045 |
| SHQ | RANDOM | 16 | 0.814 | 0.833 | 2.631 |
| SHQ | RANDOM | 40 | 0.871 | 0.867 | 4.093 |
| SHQ | RANDOM | 80 | 0.897 | 0.889 | 4.139 |

## B. Velocity-spike region {spike log-ratio ≥ log 2} (pooled, from scratch)

**PRIMARY B — STRADDLE vs MAXIMIN under SHQ, BA-AULC over B8–B60: BETTER (DEV)**
Δ per repeat: {"3": 0.0195, "4": 0.0267, "5": 0.0351, "6": 0.0158, "7": 0.0364, "8": 0.0161, "9": 0.0329, "10": 0.0316}; mean +0.0268; practical margin 0.02.

Exploratory contrasts (BA-AULC):

| contrast | mean | per_repeat | positive_repeats |
|---|---|---|---|
| same model SHQ: TRUVAR − STRADDLE | -0.0071 | {"3": -0.007, "4": -0.0012, "5": -0.0003, "6": -0.0132, "7": -0.0111, "8": -0.0105, "9": -0.0129, "10": -0.0006} | 0/8 |
| same model SHQ: RANDOM − MAXIMIN | -0.0064 | {"3": 0.001, "4": -0.0103, "5": 0.0095, "6": -0.0106, "7": 0.0119, "8": -0.0369, "9": -0.0098, "10": -0.006} | 3/8 |
| same model M0: STRADDLE − MAXIMIN | 0.0243 | {"3": 0.0314, "4": 0.0194, "5": 0.0361, "6": 0.0066, "7": 0.0366, "8": 0.0008, "9": 0.0246, "10": 0.0385} | 8/8 |
| same model M0: TRUVAR − STRADDLE | 0.0021 | {"3": 0.0026, "4": 0.0095, "5": 0.0072, "6": 0.0126, "7": -0.0064, "8": 0.0032, "9": -0.0029, "10": -0.0085} | 5/8 |
| same selector STRADDLE: SHQ − M0 | 0.0152 | {"3": 0.0119, "4": 0.0185, "5": 0.0127, "6": 0.0172, "7": 0.0084, "8": 0.0264, "9": 0.018, "10": 0.0086} | 8/8 |
| same selector MAXIMIN: SHQ − M0 | 0.0127 | {"3": 0.0239, "4": 0.0112, "5": 0.0138, "6": 0.008, "7": 0.0086, "8": 0.0111, "9": 0.0096, "10": 0.0154} | 8/8 |

Both recalls at matched budgets (mean over repeats):

| model | acq | budget | BA | recall_in | recall_out |
|---|---|---|---|---|---|
| M0 | MAXIMIN | 16 | 0.875 | 0.877 | 0.874 |
| M0 | MAXIMIN | 24 | 0.911 | 0.908 | 0.913 |
| M0 | MAXIMIN | 40 | 0.927 | 0.914 | 0.940 |
| M0 | MAXIMIN | 60 | 0.948 | 0.928 | 0.968 |
| M0 | RANDOM | 16 | 0.849 | 0.840 | 0.857 |
| M0 | RANDOM | 24 | 0.891 | 0.873 | 0.909 |
| M0 | RANDOM | 40 | 0.930 | 0.909 | 0.950 |
| M0 | RANDOM | 60 | 0.942 | 0.926 | 0.957 |
| M0 | STRADDLE | 16 | 0.885 | 0.875 | 0.896 |
| M0 | STRADDLE | 24 | 0.940 | 0.932 | 0.947 |
| M0 | STRADDLE | 40 | 0.955 | 0.956 | 0.955 |
| M0 | STRADDLE | 60 | 0.975 | 0.967 | 0.984 |
| M0 | TRUVAR | 16 | 0.918 | 0.888 | 0.948 |
| M0 | TRUVAR | 24 | 0.941 | 0.911 | 0.972 |
| M0 | TRUVAR | 40 | 0.959 | 0.943 | 0.975 |
| M0 | TRUVAR | 60 | 0.968 | 0.955 | 0.981 |
| SHQ | MAXIMIN | 16 | 0.912 | 0.906 | 0.918 |
| SHQ | MAXIMIN | 24 | 0.922 | 0.926 | 0.918 |
| SHQ | MAXIMIN | 40 | 0.933 | 0.924 | 0.942 |
| SHQ | MAXIMIN | 60 | 0.952 | 0.936 | 0.967 |
| SHQ | RANDOM | 16 | 0.884 | 0.865 | 0.902 |
| SHQ | RANDOM | 24 | 0.912 | 0.893 | 0.930 |
| SHQ | RANDOM | 40 | 0.937 | 0.915 | 0.959 |
| SHQ | RANDOM | 60 | 0.947 | 0.924 | 0.971 |
| SHQ | STRADDLE | 16 | 0.918 | 0.917 | 0.918 |
| SHQ | STRADDLE | 24 | 0.955 | 0.951 | 0.960 |
| SHQ | STRADDLE | 40 | 0.975 | 0.967 | 0.982 |
| SHQ | STRADDLE | 60 | 0.979 | 0.968 | 0.991 |
| SHQ | TRUVAR | 16 | 0.919 | 0.889 | 0.949 |
| SHQ | TRUVAR | 24 | 0.943 | 0.913 | 0.974 |
| SHQ | TRUVAR | 40 | 0.961 | 0.939 | 0.983 |
| SHQ | TRUVAR | 60 | 0.969 | 0.954 | 0.984 |

Queries to BA ≥ 0.95 (confirmed: BA ≥ level at b and at b+4; per repeat; '–' = censored at the horizon):

| model | acq | completed | confirmed |
|---|---|---|---|
| M0 | MAXIMIN | 2/8 | –,–,–,37,–,26,–,– |
| M0 | RANDOM | 2/8 | 41,–,–,–,49,–,–,– |
| M0 | STRADDLE | 8/8 | 23,34,32,25,25,29,36,31 |
| M0 | TRUVAR | 8/8 | 33,33,29,16,23,31,38,37 |
| SHQ | MAXIMIN | 3/8 | –,–,–,33,–,33,–,44 |
| SHQ | RANDOM | 3/8 | 34,–,–,–,49,–,–,55 |
| SHQ | STRADDLE | 8/8 | 22,22,26,22,23,24,21,25 |
| SHQ | TRUVAR | 8/8 | 32,18,27,37,28,29,33,25 |

Collection (where the post-startup paid runs fall; paid truth) — collection is not learning:

| model | acq | band_share_paid | in_region_paid_share | invalid_paid_share |
|---|---|---|---|---|
| M0 | MAXIMIN | 0.183 | 0.443 | 0.080 |
| M0 | RANDOM | 0.166 | 0.472 | 0.102 |
| M0 | STRADDLE | 0.422 | 0.471 | 0.093 |
| M0 | TRUVAR | 0.373 | 0.483 | 0.104 |
| SHQ | MAXIMIN | 0.183 | 0.443 | 0.080 |
| SHQ | RANDOM | 0.166 | 0.472 | 0.102 |
| SHQ | STRADDLE | 0.463 | 0.465 | 0.080 |
| SHQ | TRUVAR | 0.399 | 0.466 | 0.100 |

## C. Keyhole label (pooled, from scratch)

**PRIMARY C — PHYSCF_ATS_MARGIN vs E1_STRADDLE, BA-AULC over B8–B60: NOT DIFFERENT (DEV; within the practical margin or not consistent across repeats)**
Δ per repeat: {"3": 0.0054, "4": 0.0182, "5": 0.0023, "6": 0.0116, "7": 0.0007, "8": -0.0006, "9": 0.0011, "10": 0.0008}; mean +0.0050; practical margin 0.02.

Exploratory paired contrasts (BA-AULC and mean log loss over B8–B60):

| arm | vs | dBA_AULC | BA_positive_repeats | dLogLoss | LL_lower_repeats |
|---|---|---|---|---|---|
| E1_MAXIMIN | E1_STRADDLE | -0.0098 | 1/8 | 0.0612 | 0/8 |
| E1_MAXIMIN | G3_MARGIN | -0.0004 | 3/8 | 0.0436 | 1/8 |
| E1_STRADDLE | G3_MARGIN | 0.0093 | 6/8 | -0.0176 | 6/8 |
| G3_MARGIN | E1_STRADDLE | -0.0093 | 2/8 | 0.0176 | 2/8 |
| PHYSCF_ATS_MARGIN | E1_STRADDLE | 0.0050 | 7/8 | -0.0855 | 8/8 |
| PHYSCF_ATS_MARGIN | G3_MARGIN | 0.0143 | 8/8 | -0.1031 | 8/8 |
| PHYSCF_ATS_MAXIMIN | E1_STRADDLE | -0.0050 | 3/8 | -0.0703 | 8/8 |
| PHYSCF_ATS_MAXIMIN | G3_MARGIN | 0.0044 | 6/8 | -0.0879 | 8/8 |
| PHYSCF_A_MARGIN | E1_STRADDLE | -0.0015 | 3/8 | -0.0641 | 8/8 |
| PHYSCF_A_MARGIN | G3_MARGIN | 0.0078 | 8/8 | -0.0817 | 8/8 |
| PHYSMC_ATS_MARGIN | E1_STRADDLE | 0.0030 | 6/8 | -0.0672 | 8/8 |
| PHYSMC_ATS_MARGIN | G3_MARGIN | 0.0123 | 8/8 | -0.0848 | 8/8 |

Matched budgets (mean over repeats). spec_NEW = conduction recall on the NEW-batch test runs (the fast-scan corner; evaluator-only diagnostic):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | shortK_pooled_total | shortK_NEW_captured | shortK_NEW_total | BA_OLD | spec_NEW | sens_NEW | one_class_folds | failed_fits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1_MAXIMIN | 8 | 0.856 | 0.879 | 0.833 | 0.927 | 0.116 | 0.626 | 0.659 | 15.750 | 22.000 | 8.125 | 10.000 | 0.818 | 0.333 | 0.935 | 0.000 | 0.000 |
| E1_MAXIMIN | 16 | 0.900 | 0.930 | 0.871 | 0.972 | 0.084 | 0.391 | 0.689 | 15.000 | 22.000 | 6.875 | 10.000 | 0.878 | 0.385 | 0.966 | 0.000 | 0.000 |
| E1_MAXIMIN | 24 | 0.929 | 0.940 | 0.918 | 0.982 | 0.059 | 0.285 | 0.722 | 15.250 | 22.000 | 7.000 | 10.000 | 0.913 | 0.417 | 0.970 | 0.000 | 0.000 |
| E1_MAXIMIN | 40 | 0.941 | 0.951 | 0.930 | 0.987 | 0.051 | 0.255 | 0.745 | 17.250 | 22.000 | 8.000 | 10.000 | 0.931 | 0.354 | 0.975 | 0.000 | 0.000 |
| E1_MAXIMIN | 60 | 0.947 | 0.952 | 0.942 | 0.988 | 0.046 | 0.251 | 0.767 | 16.375 | 22.000 | 7.625 | 10.000 | 0.940 | 0.385 | 0.973 | 0.000 | 0.000 |
| E1_STRADDLE | 8 | 0.856 | 0.879 | 0.833 | 0.927 | 0.116 | 0.626 | 0.659 | 15.750 | 22.000 | 8.125 | 10.000 | 0.818 | 0.333 | 0.935 | 0.000 | 0.000 |
| E1_STRADDLE | 16 | 0.909 | 0.918 | 0.900 | 0.968 | 0.073 | 0.341 | 0.695 | 15.250 | 22.000 | 7.500 | 10.000 | 0.880 | 0.385 | 0.963 | 0.000 | 0.000 |
| E1_STRADDLE | 24 | 0.933 | 0.945 | 0.921 | 0.980 | 0.056 | 0.259 | 0.733 | 16.750 | 22.000 | 8.000 | 10.000 | 0.918 | 0.312 | 0.977 | 0.000 | 0.000 |
| E1_STRADDLE | 40 | 0.952 | 0.952 | 0.951 | 0.988 | 0.039 | 0.165 | 0.779 | 17.750 | 22.000 | 8.750 | 10.000 | 0.937 | 0.375 | 0.982 | 0.000 | 0.000 |
| E1_STRADDLE | 60 | 0.953 | 0.952 | 0.955 | 0.990 | 0.036 | 0.153 | 0.781 | 17.750 | 22.000 | 8.375 | 10.000 | 0.939 | 0.427 | 0.980 | 0.000 | 0.000 |
| G3_MARGIN | 8 | 0.854 | 0.827 | 0.881 | 0.910 | 0.129 | 0.426 | 0.671 | 15.750 | 22.000 | 8.250 | 10.000 | 0.796 | 0.198 | 0.909 | 0.000 | 0.000 |
| G3_MARGIN | 16 | 0.906 | 0.878 | 0.935 | 0.934 | 0.104 | 0.371 | 0.710 | 16.750 | 22.000 | 9.125 | 10.000 | 0.840 | 0.198 | 0.972 | 0.000 | 0.000 |
| G3_MARGIN | 24 | 0.926 | 0.912 | 0.939 | 0.963 | 0.079 | 0.302 | 0.728 | 16.500 | 22.000 | 8.625 | 10.000 | 0.879 | 0.198 | 0.983 | 0.000 | 0.000 |
| G3_MARGIN | 40 | 0.945 | 0.927 | 0.962 | 0.982 | 0.053 | 0.216 | 0.774 | 16.375 | 22.000 | 8.250 | 10.000 | 0.912 | 0.365 | 0.978 | 0.000 | 0.000 |
| G3_MARGIN | 60 | 0.951 | 0.940 | 0.963 | 0.988 | 0.040 | 0.161 | 0.780 | 16.375 | 22.000 | 7.750 | 10.000 | 0.935 | 0.354 | 0.973 | 0.000 | 0.000 |
| PHYSCF_ATS_MARGIN | 8 | 0.863 | 0.808 | 0.918 | 0.946 | 0.099 | 0.333 | 0.680 | 11.750 | 22.000 | 5.750 | 10.000 | 0.814 | 0.458 | 0.875 | 0.000 | 0.000 |
| PHYSCF_ATS_MARGIN | 16 | 0.931 | 0.914 | 0.947 | 0.981 | 0.053 | 0.200 | 0.755 | 16.250 | 22.000 | 8.000 | 10.000 | 0.891 | 0.323 | 0.974 | 0.000 | 0.000 |
| PHYSCF_ATS_MARGIN | 24 | 0.943 | 0.926 | 0.960 | 0.987 | 0.041 | 0.157 | 0.771 | 16.750 | 22.000 | 8.500 | 10.000 | 0.909 | 0.312 | 0.980 | 0.000 | 0.000 |
| PHYSCF_ATS_MARGIN | 40 | 0.951 | 0.942 | 0.960 | 0.989 | 0.036 | 0.135 | 0.780 | 16.875 | 22.000 | 8.500 | 10.000 | 0.931 | 0.312 | 0.980 | 0.000 | 0.000 |
| PHYSCF_ATS_MARGIN | 60 | 0.953 | 0.944 | 0.963 | 0.990 | 0.033 | 0.123 | 0.787 | 16.750 | 22.000 | 8.500 | 10.000 | 0.933 | 0.354 | 0.980 | 0.000 | 0.000 |
| PHYSCF_ATS_MAXIMIN | 8 | 0.863 | 0.808 | 0.918 | 0.946 | 0.099 | 0.333 | 0.680 | 11.750 | 22.000 | 5.750 | 10.000 | 0.814 | 0.458 | 0.875 | 0.000 | 0.000 |
| PHYSCF_ATS_MAXIMIN | 16 | 0.928 | 0.905 | 0.951 | 0.983 | 0.054 | 0.205 | 0.742 | 13.250 | 22.000 | 6.000 | 10.000 | 0.892 | 0.479 | 0.959 | 0.000 | 0.000 |
| PHYSCF_ATS_MAXIMIN | 24 | 0.935 | 0.913 | 0.957 | 0.986 | 0.046 | 0.176 | 0.755 | 13.250 | 22.000 | 6.250 | 10.000 | 0.903 | 0.438 | 0.962 | 0.000 | 0.000 |
| PHYSCF_ATS_MAXIMIN | 40 | 0.940 | 0.923 | 0.958 | 0.989 | 0.041 | 0.153 | 0.758 | 14.750 | 22.000 | 7.000 | 10.000 | 0.916 | 0.354 | 0.965 | 0.000 | 0.000 |
| PHYSCF_ATS_MAXIMIN | 60 | 0.946 | 0.931 | 0.960 | 0.990 | 0.037 | 0.136 | 0.775 | 15.750 | 22.000 | 7.500 | 10.000 | 0.923 | 0.302 | 0.972 | 0.000 | 0.000 |
| PHYSCF_A_MARGIN | 8 | 0.849 | 0.811 | 0.887 | 0.934 | 0.121 | 0.401 | 0.664 | 12.250 | 22.000 | 6.375 | 10.000 | 0.795 | 0.521 | 0.882 | 0.000 | 0.000 |
| PHYSCF_A_MARGIN | 16 | 0.921 | 0.887 | 0.954 | 0.980 | 0.062 | 0.238 | 0.732 | 11.125 | 22.000 | 5.250 | 10.000 | 0.877 | 0.594 | 0.947 | 0.000 | 0.000 |
| PHYSCF_A_MARGIN | 24 | 0.933 | 0.919 | 0.947 | 0.985 | 0.050 | 0.191 | 0.737 | 13.500 | 22.000 | 6.625 | 10.000 | 0.904 | 0.531 | 0.962 | 0.000 | 0.000 |
| PHYSCF_A_MARGIN | 40 | 0.947 | 0.935 | 0.959 | 0.989 | 0.038 | 0.145 | 0.777 | 15.375 | 22.000 | 7.750 | 10.000 | 0.924 | 0.448 | 0.973 | 0.000 | 0.000 |
| PHYSCF_A_MARGIN | 60 | 0.949 | 0.935 | 0.963 | 0.989 | 0.033 | 0.125 | 0.779 | 15.875 | 22.000 | 7.500 | 10.000 | 0.927 | 0.458 | 0.972 | 0.000 | 0.000 |
| PHYSMC_ATS_MARGIN | 8 | 0.822 | 0.854 | 0.790 | 0.917 | 0.136 | 0.428 | 0.634 | 13.500 | 22.000 | 6.875 | 10.000 | 0.784 | 0.375 | 0.907 | 0.000 | 0.000 |
| PHYSMC_ATS_MARGIN | 16 | 0.936 | 0.928 | 0.944 | 0.985 | 0.054 | 0.214 | 0.734 | 14.875 | 22.000 | 7.250 | 10.000 | 0.914 | 0.250 | 0.970 | 0.000 | 0.000 |
| PHYSMC_ATS_MARGIN | 24 | 0.944 | 0.934 | 0.954 | 0.987 | 0.045 | 0.176 | 0.762 | 16.250 | 22.000 | 8.000 | 10.000 | 0.923 | 0.333 | 0.972 | 0.000 | 0.000 |
| PHYSMC_ATS_MARGIN | 40 | 0.950 | 0.944 | 0.957 | 0.989 | 0.038 | 0.147 | 0.778 | 17.250 | 22.000 | 8.625 | 10.000 | 0.931 | 0.365 | 0.979 | 0.000 | 0.000 |
| PHYSMC_ATS_MARGIN | 60 | 0.954 | 0.949 | 0.959 | 0.990 | 0.034 | 0.129 | 0.790 | 18.000 | 22.000 | 8.750 | 10.000 | 0.937 | 0.333 | 0.982 | 0.000 | 0.000 |

Queries to BA ≥ 0.93 (confirmed: BA ≥ level at b and at b+4; per repeat; '–' = censored):

| arm | completed | confirmed |
|---|---|---|
| E1_MAXIMIN | 8/8 | 37,23,21,23,30,14,21,34 |
| E1_STRADDLE | 8/8 | 17,31,25,25,18,15,16,11 |
| G3_MARGIN | 8/8 | 26,19,23,27,21,30,20,28 |
| PHYSCF_ATS_MARGIN | 8/8 | 12,16,15,13,14,13,17,11 |
| PHYSCF_ATS_MAXIMIN | 8/8 | 15,17,47,21,14,12,17,15 |
| PHYSCF_A_MARGIN | 8/8 | 20,22,23,27,23,21,13,16 |
| PHYSMC_ATS_MARGIN | 8/8 | 12,12,23,15,11,15,20,19 |

## D. Time structure (bounded; exploratory)

Endpoint: early-horizon peak amplitude (0–0.25 ms after the run's own onset; log nJ for KE, K for temperature), MAXIMIN paid path, M0Q. Rule: a curve model beats the scalar GP iff its error ≤ 0.95 × the scalar GP error AND ≤ 0.95 × the x-independent mean-curve error in ≥ 7 of 8 repeats. This is an early-horizon endpoint, not the full trajectory.

| channel | budget | curve_model | repeats_won | curve_err | scalar_err | mean_curve_err | verdict |
|---|---|---|---|---|---|---|---|
| ke | 16 | KRONn | 0 | 0.2580 | 0.1193 | 0.7759 | no |
| ke | 16 | PHASE | 0 | 0.6568 | 0.1193 | 0.7759 | no |
| ke | 16 | PHASE_PCA | 0 | 0.4595 | 0.1193 | 0.7759 | no |
| ke | 40 | KRONn | 0 | 0.1112 | 0.0944 | 0.7699 | no |
| ke | 40 | PHASE | 0 | 0.5998 | 0.0944 | 0.7699 | no |
| ke | 40 | PHASE_PCA | 0 | 0.3546 | 0.0944 | 0.7699 | no |
| tmax | 16 | KRONn | 0 | 151.7120 | 116.7132 | 373.8648 | no |
| tmax | 16 | PHASE | 0 | 203.7133 | 116.7132 | 373.8648 | no |
| tmax | 16 | PHASE_PCA | 0 | 170.3034 | 116.7132 | 373.8648 | no |
| tmax | 40 | KRONn | 2 | 159.1560 | 175.5220 | 382.2033 | no |
| tmax | 40 | PHASE | 2 | 185.2750 | 175.5220 | 382.2033 | no |
| tmax | 40 | PHASE_PCA | 3 | 158.9867 | 175.5220 | 382.2033 | no |

## Costs

Simulation cost = total revealed queries per trajectory (startup included; one simulation reveals every output, counted once). Modelling CPU is separate.

| job | arm | design | trajectories | cpu_s_mean | cpu_s_total | queries |
|---|---|---|---|---|---|---|
| final-label | E1_MAXIMIN |  | 40 | 2.9 | 114.7 | 60.0 |
| final-label | E1_STRADDLE |  | 40 | 3.0 | 121.1 | 60.0 |
| final-label | G3_MARGIN |  | 40 | 9.7 | 386.2 | 60.0 |
| final-label | PHYSCF_ATS_MARGIN |  | 40 | 4.1 | 164.9 | 60.0 |
| final-label | PHYSCF_ATS_MAXIMIN |  | 40 | 4.7 | 190.0 | 60.0 |
| final-label | PHYSCF_A_MARGIN |  | 40 | 1.3 | 52.4 | 60.0 |
| final-label | PHYSMC_ATS_MARGIN |  | 40 | 5.2 | 207.8 | 60.0 |
| final-reg | M0 | MAXIMIN | 40 | 3.2 | 129.5 | 80.0 |
| final-reg | M0Q | MAXIMIN | 40 | 3.2 | 129.0 | 80.0 |
| final-reg | M0Q | MOIVR | 40 | 30.4 | 1216.0 | 80.0 |
| final-reg | M0Q | RANDOM | 40 | 3.2 | 129.4 | 80.0 |
| final-reg | SHQ | MAXIMIN | 40 | 11.4 | 457.4 | 80.0 |
| final-reg | SHQ | MOIVR | 40 | 61.3 | 2450.1 | 80.0 |
| final-reg | SHQ | RANDOM | 40 | 10.5 | 419.1 | 80.0 |
| final-region | M0 | MAXIMIN | 40 | 0.9 | 36.1 | 60.0 |
| final-region | M0 | RANDOM | 40 | 0.9 | 36.3 | 60.0 |
| final-region | M0 | STRADDLE | 40 | 1.0 | 39.6 | 60.0 |
| final-region | M0 | TRUVAR | 40 | 1.3 | 52.1 | 60.0 |
| final-region | SHQ | MAXIMIN | 40 | 24.7 | 989.4 | 60.0 |
| final-region | SHQ | RANDOM | 40 | 22.6 | 903.0 | 60.0 |
| final-region | SHQ | STRADDLE | 40 | 20.0 | 801.4 | 60.0 |
| final-region | SHQ | TRUVAR | 40 | 24.4 | 977.6 | 60.0 |
| final-temporal | M0Q |  | 40 | 3.4 | 135.9 | – |

Total modelling CPU of the final programme: 2.82 h.

