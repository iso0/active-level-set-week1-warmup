# Supervisor Phase 1.18A — one page

- **Design:** 600 frozen M3 snapshots, 169,200 candidate occurrences, no new acquisition path.
- **Margin correction:** it integrates latent uncertainty through `p_M3`; it simply lacks an explicit global expected-reduction objective.
- **Local criteria:** Straddle vs Margin median Spearman 0.9991, top-1 66.3%; EMI 0.9872, top-1 66.0%.
- **Global candidates:** SMOCU/SUR were scored with an explicit logistic-Laplace rank-one approximation and remain approximation-requiring, not exact results.
- **PA-TVR:** the local variance update is defensible, but the claimed tangent Matérn geometry and global interpretation are not. L100/L1000 median Spearman 1.0000.
- **Decision:** **PA_TVR_REJECTED**. Do not repair it ad hoc.
- **One possible next experiment:** FAST_GPC_SUR, only after a faithful GPC-SUR update validation gate. No q20 optimization or sample-efficiency claim was performed here.
