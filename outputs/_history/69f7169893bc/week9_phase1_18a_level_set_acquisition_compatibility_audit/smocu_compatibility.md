# SMOCU compatibility

SMOCU softens maximum class probability with LogSumExp and chooses the query with greatest expected global increase after hypothetical labels. It is a genuine finite-pool one-step look-ahead. The original efficient GPC derivation uses a different posterior approximation. Here both hypothetical outcomes are weighted by current M3 probability and transmitted through posterior cross-covariance using a documented logistic-Laplace rank-one moment approximation. It is explicitly `M3_SMOCU_APPROX`, not exact SMOCU.
