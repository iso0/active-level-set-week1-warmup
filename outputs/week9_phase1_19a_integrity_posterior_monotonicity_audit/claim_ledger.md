# Claim ledger

| Claim | Status | Evidence / guardrail |
|---|---|---|
| Multiple exact simulation configurations are present | SUPPORTED | `configuration_summary.csv`; verified folder fields. |
| Shorter windows caused false Conduction labels | NOT PROVEN | Timing creates sensitivity, but counterfactual labels are unavailable. |
| Main model conclusions survive main-config restriction | QUALIFIED | `main_configuration_model_sensitivity.csv`; model-only grouped-fold check. |
| A terminal depth pile is likely floor-censored | SUPPORTED | Label-free gap and pile in `depth_censoring_summary.csv`. |
| Binary level-set labels are invalidated by depth censoring | NOT SUPPORTED | Depth is a separate continuous target. |
| Stage-1 prefixes exhibit logistic separation | SUPPORTED | Exact one-dimensional threshold check and fixed-C diagnostic. |
| Large Stage-1 logits alone prove miscalibration | NOT SUPPORTED | Held-out Brier/log loss/ECE are required. |
| M3 remains a supported predictive hybrid | SUPPORTED WITH CAVEAT | Audit separates hard decisions from uncertainty calibration. |
| Primary labels are approximately monotone | SUPPORTED | Exact pair enumeration, full and main-only. |
| Exact hard monotonic pseudo-labelling is safe | NOT SUPPORTED | Retrospective wrong implications exist. |
| A future soft monotone pool-LSE audit is justified | SUPPORTED AS NEXT TEST | Structural evidence only; no prospective result here. |
| Phase 1.18B tested Letham GlobalSUR | FALSIFIED | Different loss, likelihood treatment, and update. |
| Letham closed form directly applies to logistic M3 | FALSIFIED | Probit/MVN identities require a compatible model. |
| Phase 1.19A demonstrates sample efficiency | NOT TESTED | No new trajectory was generated. |
