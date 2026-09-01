# Final red-team report — Phase 1.10

Status: **PASS WITH CLAIM QUALIFICATION**

| Attack | Check | Disposition |
|---|---|---|
| Replicate leakage | Exact `(P,VX)` condition has one fold per repeat; all 2,400 manifest rows checked. | PASS |
| Diameter/radius error | Source says 50 µm `1/e²` diameter; executable constant is 25e-6 m radius. | PASS |
| Transition mapping | Raw modes retained; only `C=0`, every `T/CT/TK/K=1`. | PASS |
| Small effective N | Reports lead with 38 unique conditions, not 60 independent settings. | QUALIFIED |
| Split instability | 20 fixed grouped repeats; intervals explicitly described as partition sensitivity. | PASS |
| Class imbalance | ROC-AUC accompanied by PR-AUC, balanced accuracy and class recalls. | PASS |
| Post-outcome tuning | Two fixed logistics and one predeclared Matérn-3/2 GPC only; no model/kernel search. | PASS |
| Predictor leakage | H receives only `log_h`; G/GPC only `[log_P,log_VX]`; no optical or label-derived input. | PASS |
| Fixed exponent leaked into G | G uses independently fitted coefficients on the two standardized log inputs. | PASS |
| Alloy pooling/transfer overclaim | Ti64 and 316L are fitted separately; 316L is explicitly secondary within-material evidence. | PASS |
| Internal boundary import | No B1/q20/q30 feature or endpoint exists. | PASS |
| Confidence overstatement | Bootstrap CI is not called an experimental-population CI. | PASS |
| Discordant conditions | Primary bundle-level Ti64 H−G is -0.0156 [-0.0167, -0.0145]; after excluding two discordant ties it is -0.0012 [-0.0027, +0.0002]. | CLAIM QUALIFIED |
| External proof language | Claim ledger rejects universal law, SPH proof, LS-exponent validation and AL benefit. | PASS |

Adversarial conclusion: the data support a strong external discriminator, but not superiority of the constrained direction. The generic direction is superior under the predeclared bundle-level primary protocol. The size and stability of that gap are qualified by the two Ti64 conditions with irreconcilable repeated labels.
