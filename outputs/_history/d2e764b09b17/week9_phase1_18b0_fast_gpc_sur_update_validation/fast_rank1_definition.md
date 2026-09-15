# FAST_RANK1 definition

For current posterior moments at reference point `u` and candidate `x`,

`v_new(u)=v(u)-Cov(f(u),f(x))^2 W_x/[1+v(x)W_x]`,

`mu_new(u)=mu(u)+Cov(f(u),f(x))(y-p_n(x))/[1+v(x)W_x]`,

with `W_x=E[sigmoid(F_x)(1-sigmoid(F_x))]`. Updated probabilities use the unchanged M3 logistic-Gaussian integration. This exactly reproduces Phase 1.18A. It is a rank-one moment approximation, not an exact enlarged-data Laplace solve.
