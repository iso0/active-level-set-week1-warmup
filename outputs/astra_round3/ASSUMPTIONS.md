## 11. Explicit assumptions table

| Tag | Result family | Pool / target | Observation and update | Essential assumption; consequence if absent |
|---|---|---|---|---|
| PROVED | Binary moment identity / one-step transfer | Fixed finite targets, weights fixed; queries may differ | Binary observations; coherent joint P or Q; unconstrained binary coordinate decisions | Other losses or label-coupled decisions require their own Bayes action |
| PROVED | Sharp common-noise margin | N≥2, queries equal all equally weighted targets | Common independent sign-noise attenuation α>0; ideal conditioning | Different reliabilities or disjoint targets can have zero ratio |
| PROVED | Self-information ratio | Each query is a target of positive weight | Binary observations; self gain ≥α observation uncertainty | No uniform positive constant if self reliability or minimum target weight vanishes |
| PROVED | Q/P regret certificates | Same loss, target, candidates and feasible rules | Correctly defined laws at the compared history | Model fit quality on different states is not the theorem's discrepancy |
| PROVED | Sequential simulation | Common finite horizon and action contract; loss in [0,1] | Kernels at reached histories and terminal posteriors; null-history versions specified | Initial pair calibration alone is insufficient |
| KNOWN/PRIOR ART | Adaptive greedy horizon bound | Common realization utility and unit costs | Actual-law adaptive monotonicity and submodularity | Coherence alone supplies neither diminishing returns nor 1−1/e |
| PROVED | Block EER optimum | Fixed Hamming weights, independent copy blocks | Noiseless block revelation | Coupled blocks/noisy channels need new analysis |
| PROVED / KNOWN/PRIOR ART | Threshold shrinkage | Scalar threshold and squared error | Exact normal-location observation | Binary GP fitting is not automatically this experiment |
| PROVED | Bounded shift / moment robust Bayes | Known anchor; declared D | Independent Gaussian noise | Bounded-support affine minimax and moment-class global minimax are different claims |
| PROVED | Order-only binary search | Distinct scalar scores; realizable one-threshold labels | Noiseless label revelation | Stochastic monotonicity and high AUC do not justify elimination |
| PROVED | Discovery laws | Fixed finite class counts | Uniform ordering in stated pool/subset, or a fixed ranked ordering | History-conditioned extreme selection is a different policy |
| PROVED | Coalescence | Same truth and sufficient state | Identical future transitions/seeds | Same query set alone can be insufficient for order-dependent fits |
| PROVED | Graph displacement | Single graph per base coordinate; declared base measure | Posterior over roots, legitimate graph actions | Multiple roots/topology changes invalidate this representation |
| PROVED | Continuous geometry bridge | Uniform coverage, bounded slopes; positive density for L1-to-sup | Labels/graph positions related by stated reconstruction | Sparse arbitrary pools cannot guarantee geometry between samples |
| PROVED | Normal-tube expansion | Injective tube, bounded curvature, corresponding surfaces | No additional components; density Lipschitz | Small volume error alone cannot control topology or Hausdorff |
| NUMERICALLY CHECKED | Empirical Week 16 audit | Existing saved states and reference clouds | Safeguarded logistic Laplace fits plus declared PEER surrogate | Reproduction of aggregates is not a new confirmatory trajectory experiment |
