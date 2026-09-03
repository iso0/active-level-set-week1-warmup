# PA-TVR supplied proposal

The supplied candidate is `v^2 W/(1+vW) * S^-1/2 * exp(-2 mu_f^2/S)`, with `S=sum_j (g_j l_j)^2`, `g=grad_z m_h`, and ARD lengths `l_j`. The primary implementation uses `W_C=E[sigmoid(F)(1-sigmoid(F))]`; `W_A` and `W_B` are audited but not selected by outcomes. The score has no new tuned acquisition parameter, but it inherits kernel, bounds, likelihood approximation, physics mean, and gate constants; it is not parameter-free.
