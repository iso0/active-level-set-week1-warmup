**Controlled descriptive results — no real-simulation performance evidence**

Static table: B16 averages over two frozen seeds; all worlds and arms are retained.

| World | V2 BA | V1 BA | Binary EP BA | V2 − binary specificity | V2 − binary Brier | V2 pi coverage / width |
|---|---:|---:|---:|---:|---:|---:|
| informative_depth | 0.880 | 0.916 | 0.815 | +0.147 | -0.027 | 1.000 / 0.764 |
| redundant_depth | 0.889 | 0.889 | 0.884 | +0.000 | +0.005 | 1.000 / 0.890 |
| local_contradiction | 0.728 | 0.738 | 0.710 | -0.008 | -0.011 | 0.932 / 0.897 |
| harmful_bridge | 0.854 | 0.627 | 0.854 | +0.000 | +0.000 | 1.000 / 0.900 |
| uncertain_threshold | 0.910 | 0.910 | 0.875 | +0.017 | -0.016 | 1.000 / 0.787 |
| zero_paid_negatives | 0.500 | 0.500 | 0.500 | +0.000 | +0.002 | 0.818 / 0.288 |
| one_paid_negative | 0.500 | 0.500 | 0.516 | -0.031 | +0.001 | 0.938 / 0.594 |
| two_paid_negatives | 0.531 | 0.531 | 0.531 | +0.000 | +0.001 | 0.969 / 0.660 |
| missing_response | 0.869 | 0.885 | 0.815 | +0.134 | -0.019 | 1.000 / 0.782 |
| model_generated | 0.523 | 0.513 | 0.523 | +0.000 | +0.003 | 0.880 / 0.639 |

Sequential table: paired minus margin AULC over B6–B10 with the same V2 model and paid-output contract.

| World / seed | BA | Specificity | Sensitivity | Brier | Log loss | First divergence |
|---|---:|---:|---:|---:|---:|---:|
| informative_depth / 2301 | -0.006 | +0.021 | -0.033 | -0.001 | +0.001 | 7 |
| informative_depth / 2302 | -0.010 | -0.015 | -0.004 | +0.002 | +0.005 | 8 |
| informative_depth / 2303 | -0.051 | -0.189 | +0.088 | -0.001 | -0.005 | 7 |
| local_contradiction / 2301 | -0.008 | +0.021 | -0.038 | -0.005 | -0.010 | 7 |
| local_contradiction / 2302 | -0.002 | +0.041 | -0.045 | +0.003 | +0.015 | 7 |
| local_contradiction / 2303 | +0.033 | -0.059 | +0.125 | -0.012 | -0.028 | 8 |
| harmful_bridge / 2301 | +0.093 | -0.047 | +0.233 | -0.016 | -0.031 | 7 |
| harmful_bridge / 2302 | -0.003 | +0.029 | -0.035 | +0.010 | +0.022 | 7 |
| harmful_bridge / 2303 | -0.009 | -0.039 | +0.021 | +0.001 | +0.002 | 8 |

BA differences use the fixed p>=0.5 decision. Coverage is of the known synthetic probability law, not of a binary event. Narrower intervals are not necessarily better.

Fit failures: 0; numerical query stops: 0; fallbacks: 0.
