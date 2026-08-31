# Phase 1.5 claim ledger

| Claim | Decision | Evidence and code path |
|---|---|---|
| h has genuine physical support | PASS | Gan Eq. 1/3; `reports/01_*`; `h_coordinates` |
| empirical exponents match theory | QUALIFY | `empirical_exponent_summary.csv`; both theory points lie inside marginal bootstrap CIs; consistency, not proof |
| h is dimensionless | REJECT | SI audit gives `W s^(1/2) m^-2`; full material normalization is missing |
| ST is irrelevant | REJECT | only partial correction in a narrow 300–400 K domain was tested; it did not help |
| h is sufficient over 4D | QUALIFY | high global AUC, but worse PR/Brier and q20 Keyhole recall than 4D GPC |
| three-zone screening is useful | QUALIFY | `screening_zone_summary.csv`; OOF retrospective simulator-domain only |
| one numerical h threshold transfers across alloys | REJECT | absorptivity/material constants and spot conventions are absent |
| h active learning saves about 45 queries | REJECT | exact persistent/censored protocol does not establish this headline |
| 5D GPC improves sample efficiency | REJECT | q20 AULC difference vs 4D Margin has a 95% CI crossing zero |
| pure 1D h acquisition plateaus | QUALIFY | H160 stable-target results remain censored and pure h querying underperforms for a 4D GPC |
| physics-based initial boundary clustering helps | REJECT | not tested; exact frozen 16-point initial design was preserved |
| additive physics-ridge modeling is promising | QUALIFY | residual structure motivates one prototype, but no additive model was fitted here |

Primary literature: Gan et al. 2021; Cunningham et al. 2019; King et al. 2014; Hann et al. 2010/2011. Numerical artifacts are under `outputs/week9_phase1_5_h_physics_confirmation/`; implementation is `src/week9_phase1_5_h_physics_confirmation.py`.
