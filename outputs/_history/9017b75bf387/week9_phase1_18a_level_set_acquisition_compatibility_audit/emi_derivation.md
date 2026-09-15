# EMI derivation

Let `F~N(mu,sigma^2)` and classify by the sign of `mu`. Latent incorrectness is the magnitude lying on the opposite side: `(-F)_+` for `mu>0` and `(F)_+` for `mu<0`. Normal partial-moment integration yields

`EMI = sigma phi(|mu|/sigma)-|mu| Phi(-|mu|/sigma)`.

At `mu=0`, symmetry gives `sigma/sqrt(2 pi)`. The supplied Monte Carlo grid verifies this closed form. This is the Beachy-Grandhi point-local latent-Gaussian form applied to M3 moments, not an exact Bernoulli-GPC future-posterior criterion.
