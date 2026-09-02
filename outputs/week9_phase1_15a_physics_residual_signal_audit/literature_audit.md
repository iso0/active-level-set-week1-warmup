# Focused literature audit

The closest work shows that neither discrepancy-aware design nor physics-informed GP active learning is new in broad terms. The possible contribution here is narrower: a transparent finite-pool binary level-set score that combines the final M3 boundary relevance with the magnitude/direction of its correction to a nested physics prior.

| paper | source | model | physics_information | discrepancy_or_residual | acquisition | task | boundary_target | similarity | difference |
|---|---|---|---|---|---|---|---|---|---|
| Gardner et al. (2021) | https://doi.org/10.1016/j.ymssp.2020.107381 | GP model-discrepancy regression with uncertainty marginalization | simulator predictions | yes | sampling-based discrepancy inference; not a sequential boundary acquisition | regression/calibration | no | explicit physics/model plus GP discrepancy | does not use classification correction magnitude for pool-based level-set queries |
| Yang, Chen & Wu (2025) | https://doi.org/10.1016/j.cma.2025.118198 | physics model plus learned discrepancy in sequential BED | convection-diffusion solver | yes | BED plus ensemble information-gain indicator for discrepancy updates | inverse problem/regression | no | actively learns discrepancy around a physics model | information-gain BED with continuous measurements, not binary finite-pool boundary learning |
| Polanska et al. (2026) | https://arxiv.org/abs/2605.21348 | neural operator | PDE residual | physics residual, not GP correction to a prior mean | query where PDE residual indicates weak physical consistency | operator regression | no | physics-residual signal guides acquisition | PDE residual and continuous fields rather than probabilistic class correction |
| Hardcastle et al. (2025) | https://doi.org/10.1039/D5DD00084J | GPC/GPR with physics-informed prior mean | CALPHAD or constraint prior | GP corrects informative prior | in-silico active refinement of phase diagrams/constraints | classification and threshold regression | yes | closest model/application analogue: physics prior plus GP correction and active boundary refinement | does not establish this exact correction-magnitude-times-margin score or melt-pool setting |
| Houlsby et al. (2011) | https://arxiv.org/abs/1112.5745 | Bayesian GP classification | none | no explicit physics discrepancy | BALD mutual information between label and parameters | classification/preference learning | indirect | separates epistemic information from predictive entropy | does not compare physics backbone with hybrid correction |
| Gotovos et al. (2013) | https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf | GP level-set estimator | none | no | confidence-bound ambiguity near threshold | level-set classification | yes | canonical boundary-focused uncertainty design | no physics prior/correction term |
| Bryan & Schneider (2008) | https://publications.ri.cmu.edu/actively-learning-level-sets-of-composite-functions | composite target from multiple observables | multiple model/data components | not a GP discrepancy decomposition | selects sample and observable for composite level-set learning | level-set estimation | yes | acquisition can exploit structured components rather than only final score | components are separately observable, unlike nested H and M3 probabilities |

## Conservative novelty boundary

- Gardner et al. establish GP discrepancy modelling, but not this active classification score.
- Yang et al. directly study active learning of discrepancy with Bayesian experimental design; this rules out a broad discrepancy-active-learning novelty claim.
- Polanska et al. use a physics residual for acquisition; this rules out a broad physics-residual-acquisition novelty claim.
- Hardcastle et al. are the closest model/application analogue: physics-informed prior-mean GP classification with active phase-boundary refinement.
- BALD and level-set confidence-bound methods remain simpler standard alternatives that any future replay must compare against.

No source was interpreted as establishing the exact proposed formula, but absence from this focused audit is not proof of novelty.
