# Final boundary-displacement Gate 1 report

This is an internal same-path structural model test. It is not external validation and it does not identify a physical displacement field uniquely.

1. Boundary-M3 versus ordinary M3: Delta10 `+0.000004` with simultaneous 95% interval `[-0.000266,+0.000237]`.
2. Boundary-M3 versus matched generic augmentation: Delta12 `+0.000000` with simultaneous 95% interval `[-0.000233,+0.000200]`.
3. q20 log-score guardrail M1-M0: `+0.001087` (`[+0.000014,+0.002573]`).
4. q20 Keyhole-recall AULC guardrail M1-M0: `-0.000056` (`[-0.000430,+0.000298]`).
5. Covariance stability: `FAIL`; {"covariance_threshold": 0.1, "fallback_rate": 0.0, "max_alternate_start_probability_difference": 2.2737367544323206e-13, "max_alternate_start_relative_covariance_difference": 0.7073794549757965, "pass": false, "probability_threshold": 0.02, "representative_cases": 18}.
6. Structural interpretation: `boundary-specific support not established`.
7. Decision: **D_UNSTABLE_BOUNDARY_FORMULATION**.
8. Subsequent SUR gate: **NO_STOP_ACQUISITION_WORK**.

Primary q20 accuracy AULC: M0 `0.837684`, M1 `0.837688`, M2 `0.837688`.
