# RC24 literature matrix: active classification with a known physics coordinate and an auxiliary response per query

The problem being compared against:
- **Task:** pool-based active classification (keyhole vs conduction) on simulations.
- **Known before a query:** the inputs x = (P, VX, LS, ST) and the dimensionless physics coordinate h = P/√(VX·LS³).
- **Returned by one query (one simulation):** the label, an auxiliary physical response (active-window maximum depth, plus temperature and spike summaries), and a record-quality flag.
- **Loss:** balanced accuracy over the input distribution, at budgets 8–60.

**Reading depth** (last column):
- **F** = full text read in RC24 (sections on model and acquisition).
- **S** = abstract plus method summary from the publisher, arXiv or official package pages, read in RC24.
- **R** = standard reference used from prior knowledge, not re-read in RC24.

**Columns (the owner's matrix):**
- **Before query:** what is known before the query.
- **Per query:** outputs per query.
- **Physics:** where physics is used.
- **Propagation:** how intermediate uncertainty is propagated.
- **Loss reduced:** the loss the acquisition reduces.
- **Difference:** the difference from our problem.
- **Special case?:** whether our recipe is a special case.
- **Code:** reproducible implementation.

| work | task | before query | per query | physics | propagation | loss reduced | difference | special case? | code | read |
|---|---|---|---|---|---|---|---|---|---|---|
| Bryan et al. 2005 (straddle) | level set of a scalar black box | x | f(x) (noisy) | none | GP variance (straddle 1.96σ − \|μ − t\|) | heuristic ambiguity | no label; a single output | HA_LEAN straddle (RC24 Q3) is the straddle on a classifier latent; it lost to margin | – | R |
| Gotovos et al. 2013, IJCAI (LSE) | classify a finite set as above or below h | x, threshold | f(x) + noise | none | GP confidence regions Q_t = μ ± β^{1/2}σ, intersected over t | ambiguity a_t(x); with Q_t it is exactly the straddle; sample-complexity guarantee | scalar f observed directly; no binary label and no auxiliary output | no (we observe labels, not f) | – | F |
| Bryan & Schneider 2008, ICML | level set of a composite f = Σ f_i | x | ONE chosen observable f_i(x) | known composition (sum, e.g. χ²) | kriging variance per observable; heuristic variance-maxvarstraddle | heuristic, chooses point and observable | the link is known and fixed; the label is never observed; one output per query | our depth GP + label link is a composite with a LEARNED link and an observed label | – | F |
| Astudillo & Frazier 2019, ICML (EI-CF) | optimisation of g(h(x)) | x, cheap g | vector h(x) | the structure of g | multi-output GP of h; MC through g | expected improvement | optimisation, not classification; g known | structurally close (composite through an observed intermediate) | BoTorch | S |
| Astudillo & Frazier 2021, NeurIPS (function networks) | optimisation of a network of functions | x | every node output | network structure | GP per node; posterior on the objective by sampling | EI on the implied objective | optimisation; node functions all learned as GPs; no labels | a 2-node network x → depth → label, with h as a known side input, is a special case of the structure, not of the loss | BoTorch | S |
| Bect et al. 2012, Stat. Comput. (SUR) | probability of failure / excursion volume | x | f(x) | none | GP; expected future uncertainty | integrated misclassification / volume variance | scalar f observed; no labels | JEER (RC24 P2) is a SUR-type criterion on our joint model | KrigInv (R) | S |
| Menz, Munoz-Zuniga, Sinoquet 2023 / ARCHISSUR 2025 | hidden feasible set from pass/fail runs | x | binary label only | none | GPC (latent sign); Vorob'ev deviation | integrated Vorob'ev uncertainty (SUR) | no auxiliary response, no physics coordinate | closest SUR-for-labels reference; we add the depth observation and the anchor | ARCHISSUR (CRAN) | S |
| Houlsby et al. 2011 (BALD) | Bayesian active classification | x | label | none | parameter posterior (mutual information) | information about parameters | labels only | BALD_LAP failed in RC22 | many | R |
| Bickford Smith et al. 2023, AISTATS (EPIG) | prediction-oriented active learning | x, target input distribution | label | none | predictive information on target inputs | information about predictions on target inputs | labels only | JEER shares EPIG's "value on OTHER target inputs", with a 0-1 loss and a depth fantasy | yes | S |
| Roy & McCallum 2001 (EER) | expected error reduction | x | label | none | refit per fantasy label | expected future error on the pool | labels only | JEER = EER with two observations and the own-label term excluded | – | R |
| Ziatdinov, Ghosh, Kalinin 2021 (arXiv 2108.10280) | BO / active learning with a physics model | x | scalar y | the GP MEAN is a parametric physical model m(x; φ) | φ and kernel hyperparameters jointly by HMC (fully Bayesian) | Thompson / UCB / variance | regression or optimisation of one output; no label | our physics-anchored depth GP is a linear-Gaussian instance (m = μ + θ z_h, θ integrated analytically) on the AUXILIARY output | gpax | F |
| Hardcastle, O'Mullan, Arróyave, Vela 2025, Digital Discovery (DOI 10.1039/D5DD00084J) | constraint satisfaction / phase classification | x, CALPHAD / VEC priors | label (or a continuous property for threshold models) | FIXED prior mean of the GPC latent (e.g. logit 0.55), set by designer judgment | latent GP variance only; the prior is not propagated; GP fit to ±5 targets with a Gaussian likelihood, then sigmoid | maximum entropy (≈ margin) | the physics prior is fixed and not learned; one output per query | the fixed-prior idea is the historical M3 (saturated h mean); RC24 shows it is BA-similar but badly calibrated | Code Ocean 10.24433/CO.5262732.v1 | S (arXiv HTML) |
| Week 9 M3 (this thesis, Phase 1.13) | active Keyhole classification | x, h | label | logistic h mean (C = 1e6, frozen) + ARD residual GPC | Laplace latent variance | margin | historical control | ported bit-exact (RC24 T1) | sibling repo 25520785 | F |
| Vapnik & Vashist 2009 (LUPI) | classification with privileged information at training | x | label + x* (training only) | none | – | – | passive; x* unavailable at test | depth is "privileged" at paid points but PREDICTED at unqueried points | – | R |
| Hernández-Lobato et al. 2014, NeurIPS (GPC+) | GPC with privileged noise | x | label + x* | none | x* sets the latent noise (confidence) of each training point | – | passive | an input-dependent label-noise idea for the aleatoric corner (not built) | – | S |
| Moreno-Muñoz, Artés, Álvarez 2018, NeurIPS (heterogeneous MOGP) | joint prediction of mixed-likelihood outputs | x | several outputs (Gaussian, Bernoulli, …) | none | LMC coupling + variational inference | – | passive; no physics coordinate | a joint label–depth GP is an instance; our structural composite is a rank-1, physics-anchored special case | yes | S |
| Wolpert 1992; Breiman 1996; van der Laan et al. 2007 (stacking / super learner) | combine learners via honest out-of-fold predictions | – | – | – | out-of-fold predictions; oracle inequality | – | passive | HA_LEAN = stacking of an emulator into a classifier (honest K = 10) | SuperLearner, sl3 | S |
| Carroll, Ruppert, Stefanski, Crainiceanu 2006 (measurement error) | nonlinear regression with error-prone covariates | – | – | – | regression calibration; E[Φ(a + bX)] = Φ((a + bμ)/√(1 + b²σ²)) | – | passive | PAC's errors-in-variables integration is this result with a GP-predicted covariate | – | R |
| King et al. 2014, J. Mater. Process. Technol. | keyhole-mode threshold in LPBF | process parameters | experiments | normalised enthalpy ΔH/h_s ∝ P/√(VX·LS³) correlates with melt depth and keyholing | – | – | physics only | the source of the anchor z_h | – | S |
| Meng & Zhang 2020, JOM (GP + enthalpy criterion) | LPBF process maps | P, v | melt depth (simulation / literature) | normalised-enthalpy criterion on top of a depth GP | GP variance | passive | no active label learning | closest physics-side reference | – | S |

## Where the RC24 recipe sits

The nearest structures are:
- Bryan & Schneider: a composite level set with a known link.
- Astudillo & Frazier: composite functions and function networks for optimisation.
- Ziatdinov et al.: a physics model as the GP mean.
- Hardcastle et al.: a physics prior mean in a GPC.

None of them combines the three ingredients of our setting:
1. a binary label that is observed directly at every query, together with an auxiliary physical response from the same record;
2. a known dimensionless physics coordinate that enters both the label model and the mean of the auxiliary-response emulator;
3. a pool-based classification loss with small budgets.

The RC24 evidence (pilot and Stage C confirmation in `FINAL_REPORT_RC24.md`; HA_TREND + margin CONFIRMED) separates the parts:
- **What helps** is anchoring the auxiliary emulator's mean on the physics coordinate, with the trend coefficient integrated, inside honest stacking.
- **What does not help** is the structural errors-in-variables composite, the fixed physics mean (M3) and straddle-type acquisition.

By itself, renaming SUR, EER or straddle is not counted as a contribution.
