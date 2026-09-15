# Letham et al. (2022) applicability memo

Primary source: Benjamin Letham, Phillip Guan, Chase Tymms, Eytan Bakshy, and Michael Shvartsman, *Look-Ahead Acquisition Functions for Bernoulli Level Set Estimation*, AISTATS 2022, [PMLR paper and supplement](https://proceedings.mlr.press/v151/letham22a.html). Associated authors' code: [facebookresearch/bernoulli_lse](https://github.com/facebookresearch/bernoulli_lse/).

## Exact answers

1. **Likelihood.** The paper studies Bernoulli observations. It notes that classification GPs can use logit or probit links, but its derivation focuses on the **probit** model, `y ~ Bernoulli(Phi(f(x)))`. Its experiments use variational inference; the acquisition derivation only requires an approximate multivariate-normal posterior for the latent `f`.
2. **Primary derivation.** Probit, not logistic.
3. **Why the bivariate-normal closed form appears.** The probit likelihood is a Gaussian CDF. Integrating products of Gaussian CDF terms against the joint Gaussian latent posterior reduces to Gaussian integral identities involving `Phi`, Owen's T, and a standard bivariate-normal CDF. The full one-step latent posterior is still intractable, but the look-ahead **level-set membership probability** is analytic.
4. **Acquisitions.** GlobalSUR is the expected reduction in the reference-set sum of posterior level-set misclassification probabilities `min(pi,1-pi)`. GlobalMI replaces that loss with the sum of binary entropies `H_b(pi)`. EAVC is expected absolute change in estimated sublevel-set volume, computed from the reference-set sum of membership probabilities. GlobalSUR and GlobalMI are SUR-form objectives; EAVC is not a SUR objective.
5. **Analytically available quantities.** Under a probit link and an MVN latent posterior: predictive Bernoulli mean, variance of the transformed probability (via Owen's T), and the one-step look-ahead level-set membership posterior for both possible outcomes (via `Phi` and the bivariate-normal CDF). GlobalSUR, LocalSUR, GlobalMI, LocalMI, and EAVC then follow analytically once summed over a reference set.
6. **Direct application to current M3.** No. M3 uses a Bernoulli-**logistic** likelihood with a custom Laplace posterior and a training-fitted logistic physics mean. Replacing `Phi` by the logistic sigmoid does not preserve the Gaussian-CDF identities that create the closed form.
7. **Changes needed.** A direct use would require a probit M3 counterpart: probit Stage-1 physics mean or another explicitly defined latent mean, probit Bernoulli residual-GP likelihood, a validated MVN latent posterior approximation and cross-covariances, consistent latent threshold `gamma` (zero for probability 0.5), and implementation/parity tests for the paper's level-set-membership updates and reference-set GlobalSUR/GlobalMI/EAVC. Alternatively, logistic M3 would require a new controlled numerical approximation; it would not be the paper's closed-form method.

## Relation to Phase 1.18B

Phase 1.18B minimized expected finite-pool predictive-probability uncertainty based on `p(1-p)` after explicit hypothetical refits. That is not Letham et al.'s level-set membership misclassification loss, not its probit closed-form update, and not evidence about every Bernoulli LSE look-ahead acquisition. This memo is mathematical applicability analysis only; Phase 1.19A implements no Letham trajectory.
