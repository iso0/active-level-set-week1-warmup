# Supervisor one-page — Phase 1.10 closure

## Frozen result

Phase 1.10 remains **GENERIC_DIRECTION_SUPERIOR** under its predeclared bundle-level protocol (H−G ROC-AUC -0.0156 [-0.0167, -0.0145]).

## Three closure answers

1. **External exponent:** Ti64 alpha=-1.7130 [-1.8931, -1.5209] (THEORY_OFFSET_RESOLVED; 100/100 valid); 316L alpha=-1.2195 [-1.4597, -0.9060] (THEORY_OFFSET_RESOLVED; 99/100 valid). Coefficients were converted back from standardized to raw log-input scale; instability and sign flips are explicit.
2. **Strict C/K:** Ti64 H/G ROC-AUC=1.0000/1.0000, H−G=+0.0000 [+0.0000, +0.0000]. 316L H/G=1.0000/1.0000.
3. **Regularization:** transition-inclusive Ti64 H−G is -0.0156 at C=1 and +0.0146 at C=1e6; recovered alpha is -1.7130/-2.3340. The sign reversal makes G>H regularization-sensitive. `penalty=None` was not run because the installed API emits a deprecation warning.

## Safe thesis interpretation

The experimental map strongly supports a monotone physics-aligned P–VX organization, but its C=1 logistic optimum is materially steeper than −0.5. Pure C/K is perfectly ranked by both H and G; transition labels create the frozen performance gap. That gap reverses under weak regularization, so it is not penalty-robust. The frozen primary verdict remains real for its declared protocol, but no exact exponent agreement, LS exponent, universal law, causal exponent, or active-learning benefit is established.
