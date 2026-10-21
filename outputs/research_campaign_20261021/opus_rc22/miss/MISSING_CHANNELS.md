# RC22 part 1c — missing monitor channels and record quality (matched RC21B REF paths; paid training monitors only)

REAL condition reproduces the recorded RC21B probabilities: max |Δ| = 2.98e-08.

## AULC by condition (fold-pooled; mean over 8 repeats)

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se | window |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PHR_NRMAP|MCAR25 | 0.9186 | 0.0046 | 0.2100 | 0.0073 | 0.9051 | 0.0109 | 0.9320 | 0.0039 | 0.0598 | 0.0023 | B8–B24 |
| PHR_NRMAP|MCAR50 | 0.9191 | 0.0060 | 0.2124 | 0.0096 | 0.9052 | 0.0127 | 0.9330 | 0.0070 | 0.0602 | 0.0034 | B8–B24 |
| PHR_NRMAP|QOFF | 0.9222 | 0.0060 | 0.2040 | 0.0116 | 0.9108 | 0.0105 | 0.9336 | 0.0045 | 0.0582 | 0.0038 | B8–B24 |
| PHR_NRMAP|REAL | 0.9222 | 0.0059 | 0.2043 | 0.0118 | 0.9117 | 0.0103 | 0.9328 | 0.0047 | 0.0583 | 0.0038 | B8–B24 |
| PHR_NRMAP|SHORTDROP | 0.9229 | 0.0053 | 0.2037 | 0.0105 | 0.9133 | 0.0097 | 0.9324 | 0.0045 | 0.0580 | 0.0034 | B8–B24 |
| SHQ_ATS_H|MCAR25 | 0.9050 | 0.0042 | 0.2742 | 0.0048 | 0.8876 | 0.0107 | 0.9225 | 0.0057 | 0.0779 | 0.0017 | B8–B24 |
| SHQ_ATS_H|MCAR50 | 0.9055 | 0.0050 | 0.2742 | 0.0058 | 0.8862 | 0.0131 | 0.9249 | 0.0067 | 0.0773 | 0.0024 | B8–B24 |
| SHQ_ATS_H|QOFF | 0.9162 | 0.0049 | 0.2363 | 0.0096 | 0.8985 | 0.0089 | 0.9339 | 0.0044 | 0.0658 | 0.0030 | B8–B24 |
| SHQ_ATS_H|REAL | 0.9158 | 0.0049 | 0.2366 | 0.0092 | 0.8985 | 0.0089 | 0.9331 | 0.0043 | 0.0660 | 0.0030 | B8–B24 |
| SHQ_ATS_H|SHORTDROP | 0.9173 | 0.0040 | 0.2370 | 0.0081 | 0.9019 | 0.0080 | 0.9326 | 0.0043 | 0.0660 | 0.0025 | B8–B24 |

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se | window |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PHR_NRMAP|MCAR25 | 0.9288 | 0.0034 | 0.1858 | 0.0054 | 0.9172 | 0.0076 | 0.9404 | 0.0027 | 0.0526 | 0.0017 | B8–B60 |
| PHR_NRMAP|MCAR50 | 0.9282 | 0.0046 | 0.1919 | 0.0076 | 0.9163 | 0.0091 | 0.9401 | 0.0052 | 0.0539 | 0.0027 | B8–B60 |
| PHR_NRMAP|QOFF | 0.9321 | 0.0043 | 0.1791 | 0.0086 | 0.9230 | 0.0075 | 0.9412 | 0.0031 | 0.0509 | 0.0028 | B8–B60 |
| PHR_NRMAP|REAL | 0.9323 | 0.0044 | 0.1793 | 0.0088 | 0.9238 | 0.0074 | 0.9408 | 0.0033 | 0.0509 | 0.0028 | B8–B60 |
| PHR_NRMAP|SHORTDROP | 0.9327 | 0.0039 | 0.1788 | 0.0078 | 0.9249 | 0.0071 | 0.9404 | 0.0030 | 0.0508 | 0.0025 | B8–B60 |
| SHQ_ATS_H|MCAR25 | 0.9188 | 0.0032 | 0.2343 | 0.0040 | 0.9050 | 0.0076 | 0.9326 | 0.0040 | 0.0660 | 0.0013 | B8–B60 |
| SHQ_ATS_H|MCAR50 | 0.9175 | 0.0039 | 0.2404 | 0.0048 | 0.9012 | 0.0090 | 0.9339 | 0.0051 | 0.0672 | 0.0020 | B8–B60 |
| SHQ_ATS_H|QOFF | 0.9279 | 0.0035 | 0.2031 | 0.0071 | 0.9143 | 0.0063 | 0.9414 | 0.0030 | 0.0564 | 0.0022 | B8–B60 |
| SHQ_ATS_H|REAL | 0.9274 | 0.0036 | 0.2033 | 0.0068 | 0.9142 | 0.0063 | 0.9406 | 0.0030 | 0.0565 | 0.0021 | B8–B60 |
| SHQ_ATS_H|SHORTDROP | 0.9285 | 0.0029 | 0.2034 | 0.0060 | 0.9168 | 0.0056 | 0.9403 | 0.0030 | 0.0564 | 0.0018 | B8–B60 |

## Contrasts (MATERIAL rule)

| window | kind | contrast | metric | mean | se | good | label |
|---|---|---|---|---|---|---|---|
| small | stress − real | PHR_NRMAP|MCAR25 − PHR_NRMAP|REAL | BA | -0.0037 | 0.0034 | 2/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|MCAR25 − PHR_NRMAP|REAL | log_loss | 0.0057 | 0.0070 | 3/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|MCAR50 − PHR_NRMAP|REAL | BA | -0.0031 | 0.0038 | 4/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|MCAR50 − PHR_NRMAP|REAL | log_loss | 0.0081 | 0.0057 | 3/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|QOFF − PHR_NRMAP|REAL | BA | -0.0000 | 0.0002 | 3/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|QOFF − PHR_NRMAP|REAL | log_loss | -0.0003 | 0.0003 | 3/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|SHORTDROP − PHR_NRMAP|REAL | BA | 0.0006 | 0.0011 | 1/8 | NOT MATERIAL |
| small | stress − real | PHR_NRMAP|SHORTDROP − PHR_NRMAP|REAL | log_loss | -0.0006 | 0.0016 | 2/8 | NOT MATERIAL |
| small | stress − real | SHQ_ATS_H|MCAR25 − SHQ_ATS_H|REAL | BA | -0.0108 | 0.0038 | 1/8 | MATERIAL HARM |
| small | stress − real | SHQ_ATS_H|MCAR25 − SHQ_ATS_H|REAL | log_loss | 0.0376 | 0.0073 | 1/8 | MATERIAL HARM |
| small | stress − real | SHQ_ATS_H|MCAR50 − SHQ_ATS_H|REAL | BA | -0.0103 | 0.0043 | 1/8 | MATERIAL HARM |
| small | stress − real | SHQ_ATS_H|MCAR50 − SHQ_ATS_H|REAL | log_loss | 0.0375 | 0.0085 | 0/8 | MATERIAL HARM |
| small | stress − real | SHQ_ATS_H|QOFF − SHQ_ATS_H|REAL | BA | 0.0004 | 0.0003 | 3/8 | NOT MATERIAL |
| small | stress − real | SHQ_ATS_H|QOFF − SHQ_ATS_H|REAL | log_loss | -0.0003 | 0.0008 | 3/8 | NOT MATERIAL |
| small | stress − real | SHQ_ATS_H|SHORTDROP − SHQ_ATS_H|REAL | BA | 0.0015 | 0.0014 | 3/8 | NOT MATERIAL |
| small | stress − real | SHQ_ATS_H|SHORTDROP − SHQ_ATS_H|REAL | log_loss | 0.0003 | 0.0017 | 3/8 | NOT MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|REAL − SHQ_ATS_H|REAL | BA | 0.0064 | 0.0030 | 6/8 | NOT MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|REAL − SHQ_ATS_H|REAL | log_loss | -0.0323 | 0.0053 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|MCAR25 − SHQ_ATS_H|MCAR25 | BA | 0.0136 | 0.0015 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|MCAR25 − SHQ_ATS_H|MCAR25 | log_loss | -0.0642 | 0.0052 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|MCAR50 − SHQ_ATS_H|MCAR50 | BA | 0.0136 | 0.0028 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|MCAR50 − SHQ_ATS_H|MCAR50 | log_loss | -0.0618 | 0.0067 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|QOFF − SHQ_ATS_H|QOFF | BA | 0.0060 | 0.0028 | 6/8 | NOT MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|QOFF − SHQ_ATS_H|QOFF | log_loss | -0.0323 | 0.0047 | 8/8 | MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|SHORTDROP − SHQ_ATS_H|SHORTDROP | BA | 0.0056 | 0.0027 | 6/8 | NOT MATERIAL |
| small | REF − H under the condition | PHR_NRMAP|SHORTDROP − SHQ_ATS_H|SHORTDROP | log_loss | -0.0333 | 0.0053 | 8/8 | MATERIAL |
| all | stress − real | PHR_NRMAP|MCAR25 − PHR_NRMAP|REAL | BA | -0.0035 | 0.0022 | 2/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|MCAR25 − PHR_NRMAP|REAL | log_loss | 0.0065 | 0.0051 | 2/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|MCAR50 − PHR_NRMAP|REAL | BA | -0.0040 | 0.0029 | 3/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|MCAR50 − PHR_NRMAP|REAL | log_loss | 0.0126 | 0.0044 | 1/8 | MATERIAL HARM |
| all | stress − real | PHR_NRMAP|QOFF − PHR_NRMAP|REAL | BA | -0.0002 | 0.0002 | 2/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|QOFF − PHR_NRMAP|REAL | log_loss | -0.0002 | 0.0003 | 5/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|SHORTDROP − PHR_NRMAP|REAL | BA | 0.0004 | 0.0009 | 1/8 | NOT MATERIAL |
| all | stress − real | PHR_NRMAP|SHORTDROP − PHR_NRMAP|REAL | log_loss | -0.0005 | 0.0012 | 3/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|MCAR25 − SHQ_ATS_H|REAL | BA | -0.0086 | 0.0026 | 1/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|MCAR25 − SHQ_ATS_H|REAL | log_loss | 0.0310 | 0.0054 | 0/8 | MATERIAL HARM |
| all | stress − real | SHQ_ATS_H|MCAR50 − SHQ_ATS_H|REAL | BA | -0.0099 | 0.0029 | 0/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|MCAR50 − SHQ_ATS_H|REAL | log_loss | 0.0372 | 0.0055 | 0/8 | MATERIAL HARM |
| all | stress − real | SHQ_ATS_H|QOFF − SHQ_ATS_H|REAL | BA | 0.0005 | 0.0002 | 6/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|QOFF − SHQ_ATS_H|REAL | log_loss | -0.0002 | 0.0005 | 4/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|SHORTDROP − SHQ_ATS_H|REAL | BA | 0.0011 | 0.0010 | 4/8 | NOT MATERIAL |
| all | stress − real | SHQ_ATS_H|SHORTDROP − SHQ_ATS_H|REAL | log_loss | 0.0002 | 0.0013 | 3/8 | NOT MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|REAL − SHQ_ATS_H|REAL | BA | 0.0049 | 0.0022 | 6/8 | NOT MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|REAL − SHQ_ATS_H|REAL | log_loss | -0.0240 | 0.0037 | 8/8 | MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|MCAR25 − SHQ_ATS_H|MCAR25 | BA | 0.0100 | 0.0011 | 8/8 | NOT MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|MCAR25 − SHQ_ATS_H|MCAR25 | log_loss | -0.0485 | 0.0041 | 8/8 | MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|MCAR50 − SHQ_ATS_H|MCAR50 | BA | 0.0107 | 0.0017 | 8/8 | MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|MCAR50 − SHQ_ATS_H|MCAR50 | log_loss | -0.0485 | 0.0047 | 8/8 | MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|QOFF − SHQ_ATS_H|QOFF | BA | 0.0042 | 0.0020 | 6/8 | NOT MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|QOFF − SHQ_ATS_H|QOFF | log_loss | -0.0240 | 0.0034 | 8/8 | MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|SHORTDROP − SHQ_ATS_H|SHORTDROP | BA | 0.0041 | 0.0020 | 6/8 | NOT MATERIAL |
| all | REF − H under the condition | PHR_NRMAP|SHORTDROP − SHQ_ATS_H|SHORTDROP | log_loss | -0.0246 | 0.0037 | 8/8 | MATERIAL |

## Masked values and paid short records per state (means)

| cond | budget | n_masked | n_short_paid |
|---|---|---|---|
| MCAR25 | 8 | 4.00 | 0.05 |
| MCAR25 | 12 | 5.95 | 0.10 |
| MCAR25 | 16 | 8.10 | 0.12 |
| MCAR25 | 20 | 10.10 | 0.15 |
| MCAR25 | 24 | 12.15 | 0.20 |
| MCAR25 | 40 | 20.35 | 0.35 |
| MCAR25 | 60 | 32.80 | 0.85 |
| MCAR50 | 8 | 6.40 | 0.05 |
| MCAR50 | 12 | 10.25 | 0.10 |
| MCAR50 | 16 | 14.38 | 0.12 |
| MCAR50 | 20 | 18.20 | 0.15 |
| MCAR50 | 24 | 21.82 | 0.20 |
| MCAR50 | 40 | 36.90 | 0.35 |
| MCAR50 | 60 | 56.68 | 0.85 |
| QOFF | 8 | 0.00 | 0.00 |
| QOFF | 12 | 0.00 | 0.00 |
| QOFF | 16 | 0.00 | 0.00 |
| QOFF | 20 | 0.00 | 0.00 |
| QOFF | 24 | 0.00 | 0.00 |
| QOFF | 40 | 0.00 | 0.00 |
| QOFF | 60 | 0.00 | 0.00 |
| REAL | 8 | 0.00 | 0.05 |
| REAL | 12 | 0.00 | 0.10 |
| REAL | 16 | 0.00 | 0.12 |
| REAL | 20 | 0.00 | 0.15 |
| REAL | 24 | 0.00 | 0.20 |
| REAL | 40 | 0.00 | 0.35 |
| REAL | 60 | 0.00 | 0.85 |
| SHORTDROP | 8 | 0.10 | 0.05 |
| SHORTDROP | 12 | 0.20 | 0.10 |
| SHORTDROP | 16 | 0.25 | 0.12 |
| SHORTDROP | 20 | 0.30 | 0.15 |
| SHORTDROP | 24 | 0.40 | 0.20 |
| SHORTDROP | 40 | 0.70 | 0.35 |
| SHORTDROP | 60 | 1.70 | 0.85 |

