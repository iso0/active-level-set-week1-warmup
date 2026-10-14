**Prospective diagnostic amendment — after the frozen comparison, before these extra checks**

13 October 2026. The original 200 static and 90 sequential model requests are complete, with no failure or fallback. Their models, generators, outcomes and endpoints remain frozen. Current total including correctness work: 302 requests / 568 component solves.

The one-negative stress reveals that improving approximation can increase the fixed-bridge model's probability at its paid negative. This warrants checking the original V1 case against a non-Gaussian numerical reference, rather than attributing every wrong probability to Laplace.

Perform only the following supplemental diagnostics; do not add comparative worlds, choose priors or rescore a real-data endpoint:

1. Reproduce the original V1 one-negative case, with unchanged V1 coordinates/defaults and labels. Fit V1 Laplace, fixed-rho=1 EP and the frozen V2 mixture: three requests / five component solves. Independently sample the **fixed V1 model's** paid latent posterior by elliptical slice sampling: four fixed seeds 4301–4304, 2,000 warmup and 8,000 retained iterations each, no thinning or adaptive tuning. Report paid-negative probability, Monte Carlo standard error, split R-hat, and paid-latent covariance difference. If split R-hat exceeds 1.05 or probability MCSE exceeds 0.01, mark the reference inconclusive; do not increase sampling after seeing its answer. A reference probability above 0.5 would demonstrate an unfavorable posterior under the fixed bridge, rather than an error caused solely by Laplace. No numeric result is forecast.
2. Corrupt all unpaid/test outputs in one existing static world, refit V2 from the unchanged paid prefix, and verify predictions and acquisition are invariant: one request / three component solves.
3. Force an EP numerical exception in a tiny fixture and verify the declared whole-mixture Laplace fallback, including failure logging and all three retained components: one request / four component solves. This induced exception is a correctness test, not an observed experimental failure.

Additional controlled work is bounded at five requests / twelve component solves. Combined total is at most 307 / 580, within the original 600 ceiling. The four sampling chains are separately counted numerical-reference computations. Preserve supplemental results separately and cross-reference them from the final record.
