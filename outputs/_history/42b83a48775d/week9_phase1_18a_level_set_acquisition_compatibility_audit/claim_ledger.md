# Phase 1.18A claim ledger

| Claim | Status | Boundary |
|---|---|---|
| M3 Margin is variance-blind. | NOT SUPPORTED | Predictive probability integrates latent variance. |
| Margin lacks an explicit expected global reduction objective. | SUPPORTED | Score is point-local current probability. |
| Straddle and EMI are latent-Gaussian compatible. | QUALIFIED | Original theory is not logistic-Laplace GPC theory. |
| Approximate SMOCU/SUR are exact literature implementations. | NOT SUPPORTED | Disclosed rank-one moment approximation. |
| GPC SUR exists in prior art. | SUPPORTED | Menz et al. 2025 and excursion-set SUR lineage. |
| Physics-informed GPC active boundary work exists. | SUPPORTED | Hardcastle et al. 2025. |
| PA-TVR has a derived Matérn tangent integral. | NOT SUPPORTED | No valid derivation identified. |
| PA-TVR is global/non-myopic. | NOT SUPPORTED | No domain-wide cross-covariance term. |
| PA-TVR is parameter-free. | NOT SUPPORTED | It inherits model, bounds, kernel and constants. |
| ARD length scales are causal physical importance. | NOT SUPPORTED | Standardized model geometry only. |
| Phase 1.18A proves sample-efficiency. | NOT TESTED | Frozen-prefix ranking audit only. |
| PA-TVR should proceed prospectively. | REJECTED | Mathematical falsification is sufficient. |
