# PA-TVR derivation audit

The first factor is a defensible *local* Laplace rank-one variance-reduction approximation: adding site precision `W` at the same location changes variance by `v^2 W/(1+vW)`. `W_B` is the curvature at a plug-in posterior mean; `W_C` is more coherent before observing a label because it averages site curvature under the current latent posterior. `W_A` is predictive-label variance and is not the Laplace Hessian.

The second factor fails the audit. No integral over a tangent hyperplane was identified that yields `S^-1/2 exp(-2mu^2/S)` for an ARD Matérn-3/2 posterior. It resembles a Gaussian/RBF density gate under additional local-linear assumptions, but those assumptions neither match M3 nor account for cross-covariance to other points. Consequently the object is a physics-gradient-scaled local contour-density weighting, not demonstrated tangent variance reduction and not non-myopic SUR.
