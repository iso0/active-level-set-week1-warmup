## Addendum AX — Astra's frozen v2 selector on the pooled region (8 frozen tasks; SHQ posterior; exploratory, DEV)

Her synthetic v2 TEST was still running and her own scientific endpoints were not inspected at registration: this is an integration and stability check on inspected simulations, not a confirmation of her method.

BA-AULC over B8–B40 per task (each task's own test fold):

| repeat | fold | ASTRA_BOUNDARY_REGIONAL | ASTRA_QUOTA_NO_SURPRISE | ASTRA_QUOTA_SURPRISE | ASTRA_SUR_GLOBAL | MAIN_MAXIMIN | MAIN_STRADDLE |
|---|---|---|---|---|---|---|---|
| 3.0000 | 1.0000 | 0.9407 | 0.9407 | 0.9407 | 0.9407 | 0.9342 | 0.9429 |
| 3.0000 | 2.0000 | 0.9702 | 0.9489 | 0.9489 | 0.9702 | 0.9352 | 0.9525 |
| 3.0000 | 3.0000 | 0.8983 | 0.9080 | 0.8983 | 0.9173 | 0.8719 | 0.9126 |
| 3.0000 | 4.0000 | 0.9270 | 0.9210 | 0.9210 | 0.9270 | 0.9122 | 0.9461 |
| 3.0000 | 5.0000 | 0.9371 | 0.9411 | 0.9305 | 0.9390 | 0.9426 | 0.9219 |
| 4.0000 | 1.0000 | 0.9361 | 0.9128 | 0.9128 | 0.9361 | 0.9051 | 0.9317 |
| 4.0000 | 2.0000 | 0.9406 | 0.9450 | 0.9382 | 0.9453 | 0.8939 | 0.9345 |
| 4.0000 | 3.0000 | 0.9307 | 0.9218 | 0.9218 | 0.9307 | 0.9100 | 0.9189 |

Paired contrasts (per task):

| contrast | mean | tasks_positive | min | max |
|---|---|---|---|---|
| (1) local response: boundary_regional − sur_global | -0.0032 | 0/8 | -0.0190 | 0.0000 |
| (2) surprise anchors at fixed share: quota_surprise − quota_no_surprise | -0.0034 | 0/8 | -0.0106 | 0.0000 |
| (3a) same model, selector: sur_global − main STRADDLE | 0.0056 | 6/8 | -0.0191 | 0.0177 |
| (3b) same model, selector: sur_global − main MAXIMIN | 0.0251 | 7/8 | -0.0037 | 0.0515 |

Both recalls at the readouts (mean over the 8 tasks):

| arm | budget | BA | recall_in | recall_out |
|---|---|---|---|---|
| ASTRA_BOUNDARY_REGIONAL | 16 | 0.951 | 0.927 | 0.974 |
| ASTRA_BOUNDARY_REGIONAL | 24 | 0.956 | 0.928 | 0.984 |
| ASTRA_BOUNDARY_REGIONAL | 32 | 0.963 | 0.948 | 0.979 |
| ASTRA_BOUNDARY_REGIONAL | 40 | 0.965 | 0.943 | 0.986 |
| ASTRA_QUOTA_NO_SURPRISE | 16 | 0.931 | 0.904 | 0.958 |
| ASTRA_QUOTA_NO_SURPRISE | 24 | 0.954 | 0.942 | 0.966 |
| ASTRA_QUOTA_NO_SURPRISE | 32 | 0.964 | 0.944 | 0.984 |
| ASTRA_QUOTA_NO_SURPRISE | 40 | 0.963 | 0.947 | 0.979 |
| ASTRA_QUOTA_SURPRISE | 16 | 0.914 | 0.896 | 0.931 |
| ASTRA_QUOTA_SURPRISE | 24 | 0.943 | 0.925 | 0.962 |
| ASTRA_QUOTA_SURPRISE | 32 | 0.962 | 0.943 | 0.982 |
| ASTRA_QUOTA_SURPRISE | 40 | 0.967 | 0.949 | 0.985 |
| ASTRA_SUR_GLOBAL | 16 | 0.951 | 0.939 | 0.963 |
| ASTRA_SUR_GLOBAL | 24 | 0.957 | 0.922 | 0.993 |
| ASTRA_SUR_GLOBAL | 32 | 0.965 | 0.943 | 0.988 |
| ASTRA_SUR_GLOBAL | 40 | 0.968 | 0.948 | 0.988 |
| MAIN_MAXIMIN | 16 | 0.911 | 0.873 | 0.949 |
| MAIN_MAXIMIN | 24 | 0.927 | 0.899 | 0.956 |
| MAIN_MAXIMIN | 32 | 0.927 | 0.889 | 0.965 |
| MAIN_MAXIMIN | 40 | 0.934 | 0.906 | 0.962 |
| MAIN_STRADDLE | 16 | 0.912 | 0.940 | 0.884 |
| MAIN_STRADDLE | 24 | 0.967 | 0.956 | 0.978 |
| MAIN_STRADDLE | 32 | 0.968 | 0.962 | 0.973 |
| MAIN_STRADDLE | 40 | 0.971 | 0.962 | 0.980 |

Mechanism counts per trajectory (mean over tasks) and cost:

| arm | triggers | confirmations | local_queries | global_random | near_ties | band_share_paid | seconds |
|---|---|---|---|---|---|---|---|
| ASTRA_BOUNDARY_REGIONAL | 0.38 | 0.12 | 1.12 | 8.00 | 1.00 | 0.40 | 15.94 |
| ASTRA_QUOTA_NO_SURPRISE | 0.00 | 0.00 | 16.00 | 8.00 | 1.25 | 0.31 | 15.10 |
| ASTRA_QUOTA_SURPRISE | 0.50 | 0.25 | 16.00 | 8.00 | 1.12 | 0.31 | 14.67 |
| ASTRA_SUR_GLOBAL | 0.00 | 0.00 | 0.00 | 8.00 | 1.12 | 0.40 | 15.96 |

Adapter acceptance before the run: PASS (information fraction vs dense rank-one update: max |Δ| = 2.5e-10).

