# Thesis Progress Log

## Thesis Project

- Title: Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries.
- Supervisor: Ioan.
- Examiner: not yet recorded in this repository.
- Start date: not yet recorded in this repository.
- Due date: not yet recorded in this repository.
- Main research goal: develop and evaluate sample-efficient active-learning methods for estimating threshold boundaries, with the longer-term application to melt-pool regime boundaries in a four-dimensional laser-metal process-parameter space.

## Week 1

- Built a `make_moons` sanity check to verify that the active-learning loop visibly contracts an uncertain boundary region.
- Built a thresholded-Branin active level-set experiment with deterministic exact labels.
- Used `GaussianProcessRegressor` on `{-1,+1}` labels as a plumbing stand-in, not as the final GP classifier.
- Used the simple acquisition rule `argmin |mu(x)|`.
- Branin threshold: 45th percentile over a reproducible 20,000-point sample.
- Branin settings: three seeds, pool size 1,500, test size 4,000, initial labelled size 6, final budget 50.
- Main Branin result: mean test error decreased from about 0.337 to about 0.061, and all three seeds finished below their initial error.
- Main caveat: the metric was global test-label misclassification error, not a boundary-specific metric.

## Week 2

- Compared acquisition rules on thresholded Branin using the same pool, test set, initial labelled points, GP model, threshold, and budget per seed.
- Methods: `random`, `smallest_abs_mu`, `straddle`, `randomized_straddle`, and `expected_feasibility`.
- Settings: five seeds, pool size 1,500, test size 4,000, initial labelled size 6, final budget 50.
- Main final mean global errors:
  - `random`: 0.119400
  - `smallest_abs_mu`: 0.065900
  - `straddle`: 0.062000
  - `randomized_straddle`: 0.060200
  - `expected_feasibility`: 0.066350
- Best global method: `randomized_straddle`.
- Fixed 8% test-error tolerance result: `randomized_straddle` reached the tolerance fastest on the mean curve at n=32; `straddle` reached n=35; `expected_feasibility` reached n=37; `smallest_abs_mu` reached n=39; `random` did not reach it.
- Main caveat: the evaluation was still mostly global classification error.

## Week 3

- Moved from 2D Branin to a four-dimensional benchmark because the target melt-pool process-parameter space is 4D.
- Initially implemented a controlled synthetic 4D boundary function. It was useful for software plumbing but was replaced as the main Week 3 result because Ioan asked for named 4D datasets or benchmarks.
- Selected thresholded 4D Ackley as the main named benchmark.
- Ackley domain: `[-5,5]^4`, with GP inputs scaled to `[0,1]^4`.
- Threshold: 50th percentile over a reproducible 100,000-point sample.
- Settings: five seeds, pool size 4,000, test size 10,000, initial labelled size 12, final budget 80.
- Added visual diagnostics: value distribution, pairwise label projections, exact 2D slices, query-location projections, and model boundary slice snapshots.
- Main final mean global errors:
  - `random`: 0.282660
  - `smallest_abs_mu`: 0.236240
  - `straddle`: 0.168400
  - `randomized_straddle`: 0.175380
  - `expected_feasibility`: 0.189820
- Best global method: `straddle`.
- Tolerance result: the mean curve reached 0.20 for `straddle` and `randomized_straddle` at n=58, and for `expected_feasibility` at n=75. No mean curve reached 0.16 or stricter tolerances by n=80.
- Main caveat: 2D projections and slices are diagnostics only; they do not show the full 4D boundary.

## Week 4

- Added boundary-focused metrics because global test-label error is not enough for a level-set estimation thesis.
- New metric 1: near-boundary error on the closest 10%, 20%, and 30% of test points by `abs(f(x) - threshold)`.
- New metric 2: query distance to true boundary, `abs(f(x_query) - threshold)`, for every acquired point.
- New metric 3: latent uncertainty-region fraction, the fraction of test points satisfying `abs(mu(x)) <= 1.96 * sigma(x)`.
- Kept global test-label error for comparison.
- Branin Week 4 findings:
  - Best final global error: `randomized_straddle`, mean 0.060.
  - Best final q10 near-boundary error: `straddle`, mean 0.358.
  - Best final q20 near-boundary error: `smallest_abs_mu`.
  - Best final q30 near-boundary error: `randomized_straddle`.
  - Closest median query distance: `smallest_abs_mu`, median 12.038580 in Branin function-value units.
- Ackley Week 4 findings:
  - Best final global error: `straddle`, mean 0.168.
  - Best final q10 near-boundary error: `randomized_straddle`, mean 0.451.
  - Best final q20 and q30 near-boundary errors: `randomized_straddle`.
  - Closest median query distance: `smallest_abs_mu`, median 0.839807 in Ackley function-value units.
- Main interpretation: boundary-focused metrics partially change the ranking. For Branin, the global winner remains competitive but q10 and q20 boundary rankings differ. For Ackley, randomized straddle is best near the boundary even though straddle is best globally.
- Main caveats:
  - Boundary distance is measured in function-value space, not Euclidean distance to the geometric contour.
  - The uncertainty-region fraction uses GP-regression latent uncertainty, not calibrated class probability.
  - The model is still a GP regressor stand-in, not the final GP classifier.
  - Runtime is about 5-6 minutes because the script computes GP mean and standard deviation on full test sets at every budget.
### Week 4 additional interpretation: Ackley boundary metrics

The Ackley boundary-focused metrics show that global classification error alone is not sufficient for interpreting active level-set performance. On thresholded 4D Ackley, `straddle` gives the best final global error, but `randomized_straddle` gives the best final near-boundary errors on q10, q20, and q30 subsets. The q10 subset is the hardest and noisiest diagnostic because it contains the test points closest to the true level set; q20 and q30 appear more stable and are more suitable as primary boundary-region metrics.

The query-distance analysis gives a separate view of sampling behavior. `smallest_abs_mu` has the closest median query distance to the true boundary in function-value units, but it does not achieve the best global or near-boundary error. This suggests that querying points close to the boundary is not sufficient by itself. The selected points must also be informative, uncertain, and well distributed across the boundary.

The latent uncertainty-region fraction gives a model-belief diagnostic rather than a correctness metric. A smaller uncertainty region means the GP-regression surrogate is less uncertain about where its latent decision boundary may lie, but this does not necessarily mean that the true boundary has been learned correctly. A method can become confidently wrong. Conversely, a method can query close to the boundary while leaving large parts of the latent boundary region uncertain.

The main methodological insight is that active level-set estimation should balance at least three signals: boundary proximity, uncertainty reduction, and coverage/diversity. The current results motivate a possible next acquisition rule that combines straddle-style boundary uncertainty with a lookahead or expected uncertainty-region reduction criterion.

In both Branin and thresholded 4D Ackley, global test error improves substantially under boundary-aware acquisition rules. However, boundary-focused metrics reveal a more nuanced picture. On Branin, several boundary-aware rules perform similarly near the boundary, with the winner changing between q10, q20, and q30. On Ackley, randomized straddle is more consistently best on near-boundary subsets, while straddle remains best globally. In both benchmarks, smallest_abs_mu tends to query closest to the true boundary in function-value distance, but this does not always translate into the best prediction error. This suggests that sampling close to the boundary is useful but insufficient; uncertainty and coverage also matter.

## Open Next Steps

- Implement a lookahead or boundary-uncertainty acquisition rule after the evaluation metrics are stable.
- Add additional named 4D benchmarks such as thresholded Rosenbrock and Rastrigin.
- Build a real laser-data loader skeleton and document expected columns, units, labels, and preprocessing.
- Transition from `GaussianProcessRegressor` on `{-1,+1}` labels to a proper GP classifier or a more defensible surrogate.
- Investigate a geometric boundary-distance metric if feasible, especially for 2D Branin and controlled 2D/4D slices.

## Week 5

- Implemented `diversified_straddle`, a first diversity-augmented acquisition heuristic.
- Rule: `(1-alpha) * normalized_straddle + alpha * normalized_diversity`, with `alpha=0.25`.
- Straddle term: `1.96 * sigma(x) - abs(mu(x))`.
- Diversity term: minimum distance from the candidate to the currently labelled set in scaled input coordinates.
- Compared six methods on both Branin and thresholded 4D Ackley: the five original Week 2/3 rules plus `diversified_straddle`.
- Kept the comparison fair by using the same threshold, pool, test set, initial labelled points, GP model, seeds, and budget within each benchmark.
- Added Week 5 outputs under `outputs/week5_diversified_straddle_comparison/`.
- Branin final mean results:
  - `diversified_straddle` global error: 0.064450.
  - Best original global error: `randomized_straddle`, 0.060200.
  - `diversified_straddle` q20 near-boundary error: 0.259250.
  - Best original q20 near-boundary error: `smallest_abs_mu`, 0.246750.
  - `diversified_straddle` q30 near-boundary error: 0.197333.
  - Best original q30 near-boundary error: `randomized_straddle`, 0.186500.
- Ackley final mean results:
  - `diversified_straddle` global error: 0.182420.
  - Best original global error: `straddle`, 0.168400.
  - `diversified_straddle` q20 near-boundary error: 0.418500.
  - Best original q20 near-boundary error: `randomized_straddle`, 0.408400.
  - `diversified_straddle` q30 near-boundary error: 0.377600.
  - Best original q30 near-boundary error: `randomized_straddle`, 0.368200.
- Main interpretation: this simple fixed-alpha diversity term did not improve the strongest original baselines in the current settings.
- Main caveats:
  - Alpha sensitivity was skipped to keep runtime manageable.
  - Query distance measures sampling behavior, not predictive correctness.
  - The uncertainty-region fraction is a GP-regression latent diagnostic, not proof that the true boundary is correct.
  - The model is still a GP regressor stand-in, not the final GP classifier.

### Boundary-gated diversified straddle follow-up

- Motivation: the first `diversified_straddle` result was negative, suggesting that generic input-space diversity over the whole pool can pull sampling away from the boundary.
- Added `boundary_gated_diversified_straddle` as a seventh method while preserving the previous `diversified_straddle`.
- Method: keep the top 10% unlabelled candidates by straddle score, with minimum shortlist size 25 when possible; inside the shortlist use `(1-beta) * normalized_straddle + beta * normalized_diversity` with `beta=0.50`.
- Branin result: the gated method improved global error over `diversified_straddle` (0.063450 vs 0.064450) and queried closer than it, but did not beat the best original methods on global, q20, or q30 error.
- Ackley result: the gated method improved q20 and q30 near-boundary error over `diversified_straddle`, and improved q20 over `straddle`, but did not beat `randomized_straddle` on q20/q30 or `straddle` on global error.
- Interpretation: boundary gating helped some diagnostics relative to naive diversity, especially on Ackley boundary metrics, but it still did not clearly beat the strongest original baselines.
- Next step: discuss with Ioan whether to run gate/beta sensitivity, use diversity along the predicted boundary rather than full input space, or move to lookahead boundary-uncertainty reduction.

### Week 5.2: Lookahead boundary-uncertainty reduction

- Motivation: Week 5.1 showed that simple input-space diversity is not enough, so Week 5.2 tests whether a query can be chosen by expected reduction in aggregate boundary uncertainty.
- Added `lookahead_boundary_uncertainty_reduction` as an eighth method while preserving both Week 5.1 diversity methods.
- Method: shortlist the top 30 unlabelled candidates by straddle score; for each candidate, fantasy-refit `+1` and `-1` labels and choose the largest expected reduction in mean positive straddle over the current unlabelled pool.
- Runtime detail: fantasy fits keep the current fitted kernel hyperparameters fixed and refit only the GP posterior; the actual active-learning fit still uses the existing `fit_gp` helper.
- Branin result: lookahead improved over the best original methods and all Week 5.1 variants on global error, q20 error, and q30 error. Final means were global 0.055900, q20 0.235500, q30 0.175333.
- Branin diagnostics: median query distance was 20.954706, global uncertainty fraction 0.284200, q20 uncertainty fraction 0.478500, and q30 uncertainty fraction 0.416833.
- Ackley result: lookahead did not improve over `straddle`, `randomized_straddle`, `diversified_straddle`, or `boundary_gated_diversified_straddle` on global, q20, or q30 error. Final means were global 0.228960, q20 0.444200, q30 0.408000.
- Ackley diagnostics: median query distance was 0.888686, closer than straddle-style methods except `smallest_abs_mu`, but uncertainty fractions were worse: global 0.849940, q20 0.917200, q30 0.911933.
- Interpretation: expected boundary-uncertainty reduction helped strongly on 2D Branin but failed on 4D Ackley under the current GP-regression surrogate. This suggests the idea is thesis-relevant but sensitive to surrogate quality, fantasy-label calibration, and the alignment between latent uncertainty reduction and true boundary correctness.
- Caveats: fantasy probabilities use `Phi(mu / sigma)` from the GP-regression latent model, not calibrated GP-classifier probabilities; query distance is an evaluation diagnostic only; shortlist sensitivity was skipped to keep runtime manageable.
- Next step: ask Ioan whether the Branin improvement is enough motivation to test a GP classifier or Ackley shortlist sensitivity, or whether to move toward a better boundary-specific objective before more acquisition variants.

### Week 5.3: Gated geometric boundary contraction

- Motivation: after diversity and lookahead experiments, Week 5.3 tests whether local GP-posterior geometry helps identify difficult boundary regions.
- Added `gated_geometric_boundary_contraction` as an eighth method, without rerunning the expensive Week 5.2 lookahead method.
- Method: shortlist the top 200 unlabelled candidates by straddle score; inside that gate, score candidates by normalized finite-difference curvature, normalized uncertainty, corrected boundary weight, and labelled-set repulsion.
- Implementation detail: curvature is a finite-difference diagonal-Hessian proxy of the GP posterior mean in scaled coordinates, clipped at 10.0; repulsion uses fixed bandwidth 0.15.
- Branin result: GBC did not improve over `straddle`, `randomized_straddle`, `diversified_straddle`, `boundary_gated_diversified_straddle`, or the best original methods on global, q20, or q30 error. Final means were global 0.071700, q20 0.271750, q30 0.210000.
- Branin diagnostics: GBC reduced latent uncertainty fractions strongly, with global 0.231450, q20 0.438750, q30 0.386500, but median query distance was worse at 24.222446.
- Ackley result: GBC also did not improve over the strongest baselines on global, q20, or q30 error. Final means were global 0.200440, q20 0.422000, q30 0.384733.
- Ackley diagnostics: GBC reduced q20/q30 uncertainty fractions to 0.838000 and 0.833667, but this did not translate into better boundary classification.
- Interpretation: finite-difference curvature under the current GP-regression surrogate is not reliably aligned with true boundary classification accuracy. The result reinforces that lower latent uncertainty can mean confident wrongness.
- Caveats: GBC is heuristic; curvature is from the GP posterior mean, not the true function; the Hessian is diagonal-only; boundary weights use a GP-regression latent probability heuristic, not calibrated GP-classifier probabilities.
- Next step: discuss with Ioan whether curvature should be abandoned for now, revisited only after a GP classifier, or tested on controlled 2D slices where geometric curvature can be inspected directly.

## Week 6

- Objective: switch from the GP-regression warm-up surrogate to `GaussianProcessClassifier` and test classifier-native acquisition rules on Branin and thresholded 4D Ackley.
- Implemented `src/week6_gp_classifier_surrogate_comparison.py` with five classifier acquisitions: `random`, `classifier_margin`, `classifier_entropy`, `classifier_gated_diversity`, and `classifier_uncertainty_repulsion`.
- Model detail: used sklearn `GaussianProcessClassifier` with fixed RBF kernel length scale 0.25 and `optimizer=None` for runtime stability and reproducibility.
- Acquisition detail: classifier rules use `predict_proba`; they do not reuse GP-regressor latent `mu`/`sigma` acquisition formulas.
- Branin result: best classifier method was `classifier_uncertainty_repulsion`, with global error 0.080400, q20 error 0.261000, and q30 error 0.197833.
- Branin reference comparison: the best available GP-regressor reference from Week 5.3 was better on global, q20, and q30 error.
- Ackley result: best classifier method was also `classifier_uncertainty_repulsion`, with global error 0.175900, q20 error 0.417500, and q30 error 0.379667.
- Ackley reference comparison: the best available GP-regressor reference from Week 5.3 was still better on global, q20, and q30 error.
- Interpretation: the GP-classifier surrogate did not clearly improve boundary metrics under this fixed-kernel implementation. Surrogate choice alone is not sufficient; kernel choice, calibration, pool geometry, and acquisition design remain important.
- Caveats: classifier probabilities are not the same as regressor latent uncertainty; binary entropy and margin are monotone-equivalent; fixed-kernel GP classification is a practical approximation; q10/q20/q30 are evaluation subsets only.
- Next step: discuss with Ioan whether to tune/calibrate the GP classifier kernel, compare against the Week 5.2 lookahead reference explicitly, or move toward real laser-data preprocessing before adding more acquisition rules.

### Week 6.1: Optimized GP-classifier surrogate

- Motivation: Week 6 used a fixed-kernel GP classifier, so the negative result could have been caused by an overly restrictive length-scale rather than by GP classification itself.
- Implemented `src/week6_1_optimized_gp_classifier_surrogate.py`.
- Compared three surrogates: `fixed_iso_gpc`, `optimized_iso_gpc`, and `optimized_ard_gpc`.
- Acquisition rules: `random`, `classifier_margin`, `classifier_entropy`, `classifier_gated_diversity`, and `classifier_uncertainty_repulsion`.
- Full command used: `.\.venv\Scripts\python.exe -m src.week6_1_optimized_gp_classifier_surrogate --full`.
- Runtime settings: `n_restarts_optimizer=2`, `optimize_every=1`, all five seeds, no runtime reduction.
- Full command runtime: about 536.9 seconds.
- Branin result: optimized ARD with `classifier_gated_diversity` was best on all primary metrics, with global error 0.035150, q20 error 0.163750, and q30 error 0.114333.
- Branin comparison: optimized ARD beat the previous Week 6 fixed classifier and the available Week 5.2 GP-regressor lookahead reference on global, q20, and q30.
- Ackley result: the fixed Week 6 classifier with `classifier_uncertainty_repulsion` remained best, with global error 0.175900, q20 error 0.417500, and q30 error 0.379667.
- Ackley comparison: optimized isotropic and ARD classifiers did not beat the fixed Week 6 classifier or the previous GP-regressor references (`straddle` for global, `randomized_straddle` for q20/q30).
- ARD helped on Branin but not on 4D Ackley; it did not support the hypothesis that ARD is automatically more useful in the higher-dimensional benchmark.
- Hyperparameter diagnostics: optimized fits often hit bounds, especially on Ackley. Ackley length-scale bound-hit fraction was 0.763 and constant bound-hit fraction was 0.504; Branin fractions were 0.425 and 0.885.
- Interpretation: kernel learning improves the classifier strongly on Branin, including boundary metrics, but does not dominate on Ackley. The result supports continuing classifier-native surrogate work, while warning that kernel optimization alone is not enough for the harder named 4D benchmark.
- Limitation: q10 remains noisy; q20/q30 are better primary boundary metrics. Query distance and uncertainty-region contraction are diagnostics, not correctness proofs.
- Reproducibility check: two quick-mode reruns in temporary output directories matched exactly for deterministic metric curves, query-distance tables, best-method rows, and comparison tables. Final metric tables matched after excluding wall-clock fit-time columns.
- Main outputs: `outputs/week6_1_optimized_gp_classifier_surrogate_comparison/`.
- Next steps: inspect why optimized Ackley hyperparameters collapse toward bounds, discuss with Ioan whether to constrain/calibrate the classifier differently, and avoid adding more acquisition complexity until the surrogate behavior is better understood.

## Week 7: Boundary-weighted IVR / Bernoulli SUR

- Motivation: test a literature-inspired Stepwise Uncertainty Reduction / targeted-IMSE idea for active level-set estimation, without claiming novelty. The question was whether globally reducing boundary-relevant membership uncertainty can beat pointwise rules such as `straddle`, `randomized_straddle`, margin, or entropy.
- Implemented `src/week7_boundary_weighted_sur.py`.
- Added benchmark: thresholded standard 4D Hartmann on `[0,1]^4`, with 50th percentile threshold, threshold seed 2026, threshold sample size 100,000, pool size 4,000, test size 10,000, five seeds, initial labelled size 12, and total budget 80.
- New GP-regressor acquisitions:
  - `gpr_boundary_weighted_ivr`: straddle-gated posterior covariance variance reduction, weighted by heuristic Bernoulli membership uncertainty `p(+1)(1-p(+1))` with `p(+1)=Phi(mu/sigma)`.
  - `gpr_bernoulli_sur_refit`: expected reduction in integrated Bernoulli uncertainty after fantasy `+1/-1` labels, implemented by an exact fixed-kernel rank-one GP posterior update equivalent to fixed-kernel refit.
- Classifier acquisition:
  - `gpc_bernoulli_sur_refit`: fixed GP-classifier fantasy refit SUR.
  - Runtime limitation: full mode ran this only on Branin and Hartmann seed 0 with classifier SUR shortlist size 15; all GP-regressor methods and fixed classifier baselines ran on all five seeds.
- Full command used: `.\.venv\Scripts\python.exe -m src.week7_boundary_weighted_sur --full`.
- Full command runtime: about 1735.1 seconds.
- Verification also ran `.\.venv\Scripts\python.exe -m compileall -q src`, `.\.venv\Scripts\python.exe -m src.week7_boundary_weighted_sur --quick`, and `.\.venv\Scripts\python.exe -m src.week7_boundary_weighted_sur --full --summarize-existing`.
- Branin five-seed comparable result: best global was `randomized_straddle` at 0.060200, best q20 was `smallest_abs_mu` at 0.246750, and best q30 was `randomized_straddle` at 0.186500. `gpr_boundary_weighted_ivr` ended at global/q20/q30 0.071350 / 0.278250 / 0.212000, and `gpr_bernoulli_sur_refit` ended at 0.074200 / 0.283250 / 0.215833. The new GP-regressor methods did not beat randomized straddle on q20/q30.
- Ackley five-seed comparable result: best global remained `straddle` at 0.168400, and best q20/q30 remained `randomized_straddle` at 0.408400 / 0.368200. `gpr_boundary_weighted_ivr` ended at 0.235560 / 0.446300 / 0.412933, and `gpr_bernoulli_sur_refit` ended at 0.272560 / 0.457600 / 0.435800. Ackley again rejected the more global uncertainty-reduction methods.
- Hartmann4 five-seed comparable result: best global was fixed classifier `classifier_uncertainty_repulsion` at 0.123640; best q20/q30 were GP-regressor `expected_feasibility` at 0.380400 / 0.325533. `gpr_boundary_weighted_ivr` ended at 0.127680 / 0.380800 / 0.327667, beating `randomized_straddle` on q20/q30 but not beating the strongest Hartmann boundary method. `gpr_bernoulli_sur_refit` ended at 0.133400 / 0.392500 / 0.338933.
- Limited classifier SUR diagnostic: `gpc_bernoulli_sur_refit` was promising on the two seed-0 benchmarks where it ran, with Branin 0.058500 / 0.221250 / 0.156667 and Hartmann4 0.112200 / 0.365500 / 0.301000, but these are one-seed limited rows and should not be compared as full five-seed winners.
- Integrated Bernoulli uncertainty did not reliably align with true q20/q30 error. On Branin, cheap IVR reduced integrated uncertainty relative to randomized straddle while worsening q20, a concrete confidently-wrong warning.
- Interpretation: Hartmann partly contradicts Ackley because cheap IVR improves over randomized straddle on Hartmann q20/q30, but the broader Week 7 lesson is still cautious. The faithful Bernoulli SUR refit did not improve over cheap IVR, and neither new GP-regressor method displaced the strongest simple baselines across benchmarks. Ackley remains uniquely hard for these uncertainty-reduction rules under the current surrogate; Hartmann suggests the failure is not universal, but also does not justify replacing robust baselines.
- Thesis-level conclusion: boundary-weighted IVR/SUR is useful as a diagnostic and literature bridge, but not yet a main method. q20/q30 remain primary. Query distance, uncertainty-region fraction, and integrated uncertainty should explain behavior, not define success.
- Main outputs: `outputs/week7_boundary_weighted_sur/`.

## Week 7.1: Fixed-GPC Bernoulli SUR validation

- Motivation: Week 7 found a promising but inconclusive seed-0 fixed-GP-classifier Bernoulli SUR result on Branin and Hartmann4. Week 7.1 tests whether that signal is robust across seeds without rerunning every Week 7 method.
- Implemented `src/week7_1_gpc_sur_validation.py`.
- Surrogate: fixed-kernel `GaussianProcessClassifier` with `ConstantKernel(1.0, fixed) * RBF(length_scale=0.25, fixed)`, `optimizer=None`, matching the fixed classifier setup from Weeks 6 and 7.
- Benchmarks:
  - Branin: threshold percentile 45, threshold seed 2026, pool 1,500, test 4,000, seeds 0-4, initial 6, budget 50.
  - Hartmann4: standard 4D Hartmann on `[0,1]^4`, threshold percentile 50, threshold seed 2026, threshold sample size 100,000, pool 4,000, test 10,000, seeds 0-4, initial 12, budget 80.
  - Ackley4: optional three-seed diagnostic only, not part of the primary validation.
- Methods: `random_classifier`, `classifier_margin`, `classifier_entropy`, `classifier_uncertainty_repulsion`, `gpc_bernoulli_sur_refit_k15`, and `gpc_bernoulli_sur_refit_k25`.
- SUR definition: choose a classifier-repulsion shortlist, fantasy-refit fixed GP classifiers with candidate label `+1` and `-1`, and maximize expected reduction in mean reference-set Bernoulli uncertainty `p(+1)(1-p(+1))`. The reference set size was 1,500 and included the most uncertain unlabelled points.
- Fairness: within each benchmark and seed, all methods used the same threshold, pool, test set, initial labelled indices, initial labels, and budget grid. Fairness checks passed for Branin, Hartmann4, and optional Ackley.
- Verification and run commands:
  - `.\.venv\Scripts\python.exe -m compileall -q src`
  - `.\.venv\Scripts\python.exe -m src.week7_1_gpc_sur_validation --quick`
  - `.\.venv\Scripts\python.exe -m src.week7_1_gpc_sur_validation --full --benchmarks branin hartmann4`
  - `.\.venv\Scripts\python.exe -m src.week7_1_gpc_sur_validation --full --benchmarks ackley --max-seeds 3`
  - `.\.venv\Scripts\python.exe -m src.week7_1_gpc_sur_validation --summarize-existing --benchmarks branin hartmann4 ackley`
- Runtime: quick smoke run took about 42.2 seconds; the full Branin/Hartmann primary run took about 1230.1 seconds; the optional Ackley three-seed diagnostic took about 535.0 seconds. k40 was not run.
- Branin result: `classifier_uncertainty_repulsion` was best on global/q20/q30 with 0.073200 / 0.256000 / 0.189667. k15 reached 0.073300 / 0.265500 / 0.201500, and k25 reached 0.077950 / 0.286250 / 0.216833.
- Hartmann4 result: `gpc_bernoulli_sur_refit_k15` was best on global error at 0.116020. `gpc_bernoulli_sur_refit_k25` was best on q20/q30 with 0.373000 / 0.315467. Both k15 and k25 beat `classifier_uncertainty_repulsion` on q20/q30.
- Optional Ackley result: SUR did not help. Best global was `classifier_uncertainty_repulsion` at 0.178367; best q20/q30 were `classifier_entropy` at 0.421167 / 0.379667. k15 and k25 both lost to `classifier_uncertainty_repulsion` on q20/q30.
- Interpretation:
  - The Week 7 seed-0 classifier SUR signal generalized on Hartmann4 but not on Branin; optional Ackley also did not support SUR.
  - k25 improved over k15 on Hartmann4 q20/q30, worsened Branin q20/q30, and was mixed on optional Ackley.
  - Integrated Bernoulli uncertainty had positive curve-level correlation with q20/q30 error, but it was not a reliable standalone objective. Branin and optional Ackley showed lower integrated uncertainty with worse boundary error versus `classifier_uncertainty_repulsion`.
  - The runtime cost is not justified as a default acquisition. Fixed-GPC SUR remains useful as a diagnostic and a Hartmann-like candidate, but not as a robust main method.
- Limitations: fixed classifier kernel only; no optimized classifier; k40 skipped; optional Ackley used three seeds; no real melt-pool data yet.
- Next steps: keep `classifier_uncertainty_repulsion`, randomized straddle, expected feasibility, and Hartmann4 SUR as comparison points; avoid adding more expensive acquisition variants until the surrogate calibration and real-data interface are clearer.
- Main outputs: `outputs/week7_1_gpc_sur_validation/`.

## Chronology correction — actual Week 4 organization (2026-07-21)

The historical entries above are intentionally preserved as originally written.
The studies previously labelled Week 5 through Week 7.1 were in fact completed
during the actual Week 4. The repository now presents this work as:

1. Week 4 Experiment 01 — boundary-focused evaluation metrics.
2. Week 4 Experiment 02 — diversified straddle.
3. Week 4 Experiment 03 — boundary-gated diversified straddle.
4. Week 4 Experiment 04 — lookahead boundary-uncertainty reduction.
5. Week 4 Experiment 05 — gated geometric boundary contraction.
6. Week 4 Experiment 06 — fixed-kernel GP classifier surrogate.
7. Week 4 Experiment 07 — optimized GP classifier surrogate.
8. Week 4 Experiment 08 — boundary-weighted IVR / Bernoulli SUR.
9. Week 4 Experiment 09 — fixed-GPC Bernoulli SUR validation.

The corresponding code is organized under flat modules
`src/week4_01_*.py` through `src/week4_09_*.py`, and the existing generated
results are preserved under `outputs/week4_01_*/` through
`outputs/week4_09_*/`. Scientific metric values, random seeds, RNG namespace
strings, quick runs, logs, figures, and historical Git commits were preserved.
Some internal CSV/JSON field names retain `previous_week6_*` or `week7_*`
prefixes for schema compatibility; these are legacy identifiers for Week 4
Experiments 06 and 08, not statements of the corrected thesis chronology.

## Week 5 — Real-data first-Conduction GP regression (2026-07-22)

- Audited the pinned Hugging Face simulation CSV at one observation per name:
  241 simulations total, 238 with an observed Conduction target, and three
  excluded because Conduction is never observed.
- Defined the response as the minimum raw timestep labelled Conduction, using
  P, VX, LS and ST as inputs. No physical-time conversion, interpolation,
  persistent-onset replacement, censored likelihood or frame-level split was
  used.
- Evaluated isotropic RBF, ARD RBF, Matérn 3/2 and Matérn 5/2 with
  simulation-level LOO and fold-local scaling on the operational no-Bug
  subgroup (91 simulations) and the inclusive broad dataset (238 simulations).
- Matérn 3/2 is the point-prediction winner on both datasets: no-Bug RMSE
  2,537.0 (R² 0.9171) and broad RMSE 16,256.3 (R² 0.4060). Broad Matérn 5/2
  has slightly better NLPD and 95% coverage, retained as a calibration caveat.
- The same-clean-points analysis shows broad training worsens predictions on
  the fixed 91 no-Bug targets for all four kernels. This is interpreted as
  subgroup/design heterogeneity, not proof that broad labels are invalid.
- Incorporated Ioan's later clarification that Screenshot Bug may describe
  repeated Initial Emptiness images. In the stored labels, 0/150 Bug
  simulations starts with Initial Emptiness, but all 147 simulations with
  pre-Conduction Bug frames keep them inside the initial empty-like block.
- Bug-containing simulations have median LS 66.48 µm versus 59.86 µm for
  no-Bug simulations, but P, VX, ST, empty-like duration and target
  distribution also differ. LS-only and four-input Bug diagnostics are weak
  (out-of-fold ROC AUC 0.5952 and 0.5926).
- The largest broad Matérn 3/2 errors are not enriched for Bug labels; they are
  more strongly associated with early/late targets and higher LS.
- L-BFGS-B, SLSQP and Powell give practically identical Matérn 3/2 LOO
  predictions, with zero fit failures, warnings or bound hits. Powell is much
  slower and no alternative materially improves on L-BFGS-B, so L-BFGS-B is
  retained.
- Permanent record: docs/week5_first_conduction_gp_log.md.
- Meeting brief: docs/week5_gp_meeting_brief.md.
- Notebooks: notebooks/week_05/01 through 04; outputs:
  outputs/week5_01_* through outputs/week5_04_*.
- Stop condition: active learning and level-set estimation were not started.

### Week 5 targeted ARD Matérn 3/2 extension (2026-07-23)

- Added `notebooks/week_05/05_ard_matern32_extension.ipynb` and structured outputs under `outputs/week5_05_ard_matern32_extension/`.
- Compared the verified Phase 2 isotropic Matérn 3/2 results with new ARD Matérn 3/2 LOO fits under identical fold-local scaling, jitter, optimizer, seed, restart and bound settings.
- No-Bug ARD improves MAE (1,560.0 versus 1,735.8) but worsens RMSE (2,808.3 versus 2,537.0) and 95% coverage (83.5% versus 90.1%). Broad ARD worsens MAE, RMSE, R² and coverage.
- Paired 10,000-resample bootstrap intervals cross zero, but RMSE point estimates favour isotropic Matérn 3/2 on both datasets.
- Broad-trained ARD still degrades the same 91 no-Bug targets: RMSE 18,051.8 versus 2,808.3 for no-Bug-only training; 15 points improve and 76 worsen.
- No-Bug LS reaches the primary ARD upper bound in 94.5% of folds and moves from 100 to 1,000 under a widened full-data bound for only a 0.0717 LML gain, indicating a weakly identified flat direction. Broad ARD lengthscales remain stable.
- Decision: retain isotropic Matérn 3/2 with L-BFGS-B; do not add further kernel complexity before discussing missing batch/design information. Active learning and level-set estimation remain not started.

## Week 7 — `sph_v2` audit and Week 6 physical-target migration (2026-08-08)

- Scope was deliberately limited to Week 7 Phase 1 and Phase 2. No GP, Ridge,
  polynomial model, classifier, kernel comparison, active learning, level-set
  estimation, or final target selection was run.
- Work was isolated from the dirty main checkout in
  `C:\Users\ozgur\Documents\thesis-week7-sph-v2-audit` on branch
  `codex/week7-phase1-2-sph-v2-audit`, based exactly on Week 6 commit
  `cba151880fc670d1b8a20ff2f7f25295f9bcb892`.
- The new Hugging Face dataset was resolved and pinned at
  `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
  Every scientific tree request and download used this 40-character revision;
  floating `main` was recorded only as a retrieval-time drift check.
- Phase 1 full remote inventory: 349,321 tree objects, 346,472 files, and 2,849
  folders. The pinned snapshot contains 407 semantic experiment folders and
  110,804 labelled frames across `new-data` (165 / 45,156),
  `old-data-local` (179 / 49,304), and `old-data-remote-clean` (63 / 16,344).
- All 20 supervisor-screenshot checks passed. The audit independently reproduced
  6,700 Keyhole frames in 73/407 experiments and 52,080 Conduction frames in
  373/407 experiments, including the reported partition-level Keyhole counts
  and rounded percentages.
- Experiment-level labels are not mutually exclusive. Among the 73 Keyhole
  experiments, none has only one saved Keyhole frame, two have at most three,
  five have at most five, 30 are transient by the stored sequence, 43 remain
  Keyhole through the last physical frame, and 16 contain more than one Keyhole
  segment. No frame-to-millisecond conversion was made in Phase 1.
- The working-student subset is not reliably identifiable. The pinned ledgers
  contain no documented annotator/provenance field or file, and the identities
  behind `label_1` and `label_2` are undocumented. Partition was not used as an
  annotator proxy. Channel disagreement occurs in 387 experiments and is kept
  as a broad review flag rather than evidence that either channel is wrong.
- The new repository retains `parameters.json`, three frame views, and
  `monitor/*.dat`, removes the Week 6 per-simulation metadata/provenance JSON,
  uses semantic folders at repository root, and adds three GIFs per experiment.
  Frame ledgers, top-level final labels, timesteps, parameters, units, and all
  three rendered-view counts are internally consistent.
- Structural limitation: 114 required-monitor entries are absent across 57
  experiments. Fifty-six `old-data-local` experiments lack both `time.dat` and
  `kinetic-energy_melt.dat`; one `new-data` experiment lacks both
  `position-bounds_melt.dat` and `kinetic-energy_melt.dat`. These source defects
  remain explicit and were not repaired from another dataset.
- Relative to the 241-experiment Week 6 design, `new-data` extends the observed
  lower LS bound by 4.971 µm, the upper P bound by 201.067 W, and the upper ST
  bound by only 0.360 K; VX adds no marginal range. Of 165 new-data experiments,
  95 lie outside at least one Week 6 marginal range and 118 lie outside the Week
  6 four-dimensional convex hull. Keyhole is observed in 59/95 outside-range
  experiments versus 4/70 inside all four old marginal ranges. This is
  descriptive design-space/covariate-shift evidence, not a causal result.
- Phase 2 imported the actual Week 6 constants and rolling-window helpers. It
  preserved valid melt rows as finite, ordered bounds below the `1e30` sentinel;
  width `y_max-y_min`; diagnostic length `x_max-x_min`; depth
  `max(0,-z_min)`; total height `z_max-z_min`; instantaneous aggregate melt
  kinetic energy in J reported as nJ; and the Week 6 T0 median over the final
  20% before `min(recording end, 0.90 × laser-exit time)`, with the unchanged
  final-50-row fallback. G3/R3 retain the 50 µm rolling-median definitions.
- The only repository-layout compatibility rule is
  `domain_max_x = min(XF, XL) + 12 µm`. It reproduces the Week 6 reconstructed
  domain end for all 241 exact identifiers. Local Week 6 monitor bytes were
  reused only when their computed Git blob IDs matched the pinned `sph_v2`
  tree; no fuzzy experiment matching was used.
- Phase 2 retained 407 target rows: 349 successful extractions and 58 explicit
  failures. By partition, successful counts are 163/165 `new-data`, 123/179
  `old-data-local`, and 63/63 `old-data-remote-clean`. The additional failure
  beyond the 57 monitor-incomplete experiments is one `new-data` bounds file
  containing the malformed token `s3.402823e+38`; it was not silently coerced.
- There are 241 exact Week 6 identifiers and 186 exact matches with sufficient
  pinned monitors for direct comparison. All comparable T0 widths, depths,
  total heights, kinetic energies, and window endpoints reproduce Week 6 within
  the declared near-machine-precision tolerances; zero material changes were
  detected.
- For the 349 successful rows, maximum depth occurs before / inside / after T0
  in 245 / 68 / 36 experiments. Among 69 successful Keyhole-positive rows, 21
  contain no saved Keyhole frame inside T0. This does not make T0 wrong: T0
  summarizes typical late-active behaviour, whereas maximum depth and a brief
  Keyhole episode answer different physical questions.
- Diagnostic flags remain visible: 141 recordings end before the 90%-domain
  cutoff under the exact Week 6 `min` rule, 16 rows meet the Week 6 T0-CV
  instability rule, eight meet the automatic depth-ambiguity candidate rule,
  and one otherwise successful row lacks the adaptive interior for G3/R3.
- Four automatically ranked side frames were inspected. One shows clearly
  separated lower components below the main melt pool, one shows a continuous
  main melt region without an obvious detached component, and two are
  inconclusive at the nearest saved-frame cadence. All flags and pinned GIF
  references are retained; no experiment is excluded.
- Validation after executed-notebook refresh: Phase 1 has 21 PASS and one FAIL
  (the upstream missing-monitor check). Phase 2 has 18 PASS, one WARNING
  (missing monitors), and one FAIL (the single malformed present bounds file).
  Requirement checklists distinguish these source-data caveats from completed
  audit deliverables.
- Smoke commands were
  `python -m src.week7_phase1_sph_v2_dataset_shift_audit --smoke --refresh-tree --workers 4`
  and
  `python -m src.week7_phase2_sph_v2_physical_target_extraction --smoke --workers 4`.
  Full commands were
  `python -m src.week7_phase1_sph_v2_dataset_shift_audit --workers 6 --refresh-tree`
  (765.1 s) and
  `python -m src.week7_phase2_sph_v2_physical_target_extraction --workers 6`
  (817.0 s).
- Executed teaching notebooks:
  `notebooks/week_07/01_sph_v2_dataset_shift_audit.ipynb` and
  `notebooks/week_07/02_sph_v2_physical_target_extraction.ipynb`. Main machine-
  readable and human-readable artifacts are under
  `outputs/week7_01_sph_v2_audit/` and
  `outputs/week7_02_sph_v2_target_extraction/`.
- Hard stop reached after Phase 2 validation. Later predictive modelling,
  classification, active learning, level-set estimation, sensitivity-based
  exclusion, and target selection remain unresolved by design.

### Phase 2 supervisor-feedback correction: no-melt sentinel (2026-08-09)

- **Observation:** A pinned-revision scan of all 406 available bounds files
  found exactly one
  textual variant, `s3.402823e+38`, as a complete CSV field. It occurs in the
  first row and `x_min` field of
  `P-447p413798058_VX-0p91078629156_LS-5p3177056457e-05_ST-328p907838563_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p29665482201e-06_H-1553ff852f`.
  No other malformed bounds token or numeric exponent in the `1e30` to
  `1e39` range was found.
- **Supervisor clarification:** Ioan confirmed that values near `1e38` in
  `position-bounds_melt.dat` are normal artifacts indicating missing melt,
  not physical melt coordinates.
- **Implementation decision:** The parser correction is deliberately narrow:
  only that exact standalone
  field is normalized to the positive numeric sentinel, after which the
  existing `abs(value) < 1e30` validity mask excludes the entire no-melt row.
  It does not strip arbitrary prefixes, replace the value with zero,
  interpolate it, or coerce unrelated malformed tokens.
- **Separate maintenance issue:** Ioan confirmed that the old-data-local
  missing monitor files can be added later through a separate Hugging Face pull
  request. They were not backfilled here and are not a blocker for new-data
  modelling.
- The rerun changed only the affected experiment from parse failure to success.
  Overall extraction is now 350/407: new-data 164/165, old-data-local 123/179,
  and remote-clean 63/63. All previously valid targets and all label-context
  fields are unchanged.
- The one remaining new-data failure,
  `P-204p165012598_VX-0p624752635414_LS-8p54709329997e-05_ST-334p626206985_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-7p72164906486e-06_H-4ecd858c02`,
  remains explicitly unavailable because both `position-bounds_melt.dat` and
  `kinetic-energy_melt.dat` are absent. The 56 old-data-local failures remain
  unchanged, each missing `time.dat` and `kinetic-energy_melt.dat`.
- Generic per-monitor availability, parse, and target-readiness flags now make
  these limitations explicit without a fixed simulation exclusion list. The
  validation result is 29 PASS, 1 expected missing-monitor WARNING, and 0 FAIL.
- The Phase 2 notebook now explains the sentinel semantics, shows the exact raw
  occurrence and before/after comparison, and preserves all four prior manual
  depth-review decisions. No Phase 3 modelling, classifier fitting, active
  learning, or level-set estimation was started.

### Week 7 Phase 3: new-data physical-response model stability (2026-08-09)

- Phase 3 starts from the verified current remote head
  `codex/week7-phase1-2-sph-v2-audit@f26f0671dd59938a8111883398fe38afedb6915d`
  on the isolated branch `codex/week7-phase3-new-data-model-stability`. The
  immutable dataset remains
  `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
- The complete 165-row `new-data` audit/label population is retained. The
  corrected Phase 2 readiness fields independently yield 164 eligible
  experiments for each of T0 width, penetration depth, total height, and melt
  kinetic energy. The one monitor-incomplete experiment remains explicit in
  the audit table and is not fabricated into a regression row.
- The executable Week 6 protocol was traced and reused: exact simulation-level
  outer LOO; fold-local X and y scaling; nested five-fold Ridge-alpha selection
  inside each outer training fold; degree-2 polynomial construction inside the
  fold; RBF, isotropic Matérn 3/2, and isotropic Matérn 5/2 GPs; the original
  bounds, L-BFGS-B optimizer, one full-run restart, deterministic seeds, and
  numerical-jitter/shared-nugget/target-summary-alpha treatments. Method C
  reproduces the 500-resample circular moving-block bootstrap and verifies
  every saved Phase 2 T0 median before estimating the uncertainty proxy.
- The primary fold table contains all 6,560 expected rows (four targets × ten
  models × 164 held-out simulations), with zero fit failures and no old-data
  row. All aggregate metrics reconcile with these held-out predictions.
- Width remains simple. Matérn 3/2 plus learned nugget has the lowest raw RMSE
  (3.505 µm; 2.103% of the 166.657 µm median scale), while degree-2 Polynomial
  Ridge remains practically competitive and is the protocol point model (MAE
  3.241 µm / 1.945%; RMSE 4.300 µm / 2.580%; R² 0.9861).
- Depth still benefits materially from GP flexibility. The raw RMSE minimum is
  Matérn 5/2 without a learned nugget (21.065 µm; 28.184%), essentially tied in
  RMSE with Matérn 3/2 without a nugget (21.068 µm). The Week 6 replacement rule
  retains Matérn 3/2 as the protocol kernel family; its learned-nugget model has
  MAE 11.937 µm / 15.972%, RMSE 21.808 µm / 29.178%, and R² 0.9103. Neither
  Ridge baseline is competitive.
- Total height changes qualitatively: Polynomial Ridge is no longer
  competitive. Matérn 3/2 without a learned nugget is the raw RMSE winner
  (21.821 µm; 21.685%); the retained protocol learned-nugget GP has MAE 12.609
  µm / 12.530%, RMSE 22.401 µm / 22.261%, and R² 0.9002.
- Kinetic energy also changes qualitatively: Matérn 3/2 plus learned nugget is
  now the raw and protocol point winner (MAE 0.3022 nJ / 9.022%; RMSE 0.5639 nJ
  / 16.832%; R² 0.8900). The Week 6 parsimonious Linear Ridge choice is not
  competitive in the new sampled domain.
- The shared learned nugget remains useful under the current regression model
  for width and kinetic energy, through calibration and/or NLPD, but not for
  depth or total height. This is predictive-model evidence only and does not
  prove physical measurement or simulator noise. The within-window Method C
  proxy is retained as a retrospective/oracle diagnostic, not a deployable
  uncertainty source.
- Relative selected-model RMSE is lower than Week 6 for width and higher for
  depth, total height, and kinetic energy. This is evidence about predictive
  error in the shifted sampled design, not evidence that the underlying physics
  became more complex.
- The Phase 2 maximum-kinetic-energy anomaly has T0 kinetic energy 4.094 nJ
  (64.6th percentile and below the conservative T0 extreme threshold), so its
  maximum remains explicitly out of Phase 3 scope and the T0 row is retained.
- A 12-experiment smoke run preceded the full run. The full command was
  `python -m src.week7_phase3_new_data_model_stability --workers 6`; a bounded
  one-hour invocation checkpointed width, depth, total height, and kinetic-
  energy Linear Ridge, and the same command resumed the remaining work in
  884.3 s. `execution_history.json` records both segments and the unmeasured
  detached-continuation boundary; `runtime_summary.json` is explicitly scoped
  to its current invocation so a cached refresh is not misreported as the full
  scientific runtime.
- The executed teaching notebook is
  `notebooks/week_07/03_new_data_physical_model_stability.ipynb`. Machine-
  readable predictions, metrics, comparisons, diagnostics, figures,
  conclusions, manifests, and summaries are under
  `outputs/week7_03_new_data_physical_model_stability/`. Final validation is
  24/24 PASS and the requirement checklist is 15/15 PASS.
- Hard stop reached after Phase 3. No classifier, feature-effect or causal
  analysis, T0-versus-maximum target decision, active learning, level-set
  estimation, acquisition change, or pooled old+new production model was run.

### Week 7 Phase 4: new-data feature effects and depth-error diagnosis (2026-08-09)

- Phase 4 starts from the exact committed and pushed Phase 3 parent
  `1118d30f3199a97b9836591f8fdea75b46dfac0d` on the isolated branch
  `codex/week7-phase4-new-data-feature-effects-depth-diagnostics`. The dataset
  remains pinned to
  `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
- The complete 165-row `new-data` audit interface is retained. Corrected Phase
  2 readiness fields independently yield 164 target-ready simulations for T0
  width, penetration depth, total height, and kinetic energy. Old-data rows are
  historical comparators only and never enter the primary effect estimation.
- The executable Week 6 feature workflow was traced before replication:
  marginal Spearman associations, fully standardized five-fold-selected Ridge,
  median-anchored controlled curves, 31 by 31 P-VX surfaces, convex-hull plus
  four-dimensional neighbour support masks, and the retained Phase 3 Matérn
  3/2 target-specific noise treatment. Full-data GPs are used only to interpret
  supported response surfaces, not to estimate out-of-sample performance.
- The strongest new-data marginal associations are P with kinetic energy
  (Spearman rho 0.935), P with depth (0.838), P with total height (0.778), and
  VX with width (-0.730). Simulation-level 2,000-resample bootstrap intervals
  are stored for all 16 input-response pairs. These are associations in the
  sampled design, not causal effects.
- The Week 6 depth directions reproduce across three independent views. For P,
  Spearman rho / standardized Ridge coefficient / median standardized local GP
  sensitivity are 0.838 / 0.549 / 0.303. For VX they are -0.445 / -0.451 /
  -0.132. LS is negative but weaker across the depth diagnostics, while the ST
  depth result is unresolved. ST remains weak across the four new-data response
  summaries, which does not establish physical unimportance.
- LS remains a material width driver: new-data Spearman rho is 0.496,
  standardized Ridge beta is 0.714, and median standardized local GP
  sensitivity is 0.671. The KE-LS relationship remains profile-dependent and
  is classified `MIXED`, not converted into a uniform global reduction claim.
  Total height preserves the supported P-positive/VX-negative pattern.
- The fixed Phase 3 LOO depth errors have a substantial heavy tail. For the
  retained Matérn 3/2 learned-nugget diagnostic, the worst 1/3/5/10 simulations
  contribute 19.1% / 35.9% / 48.2% / 67.8% of total squared error. Twenty-one
  simulations meet the cross-kernel consensus hard-case rule, and 17 of the
  top 20 are shared across all three inspected Matérn configurations.
- Absolute depth error increases with observed depth and is enriched in
  Keyhole-positive experiments, but these are diagnostic associations rather
  than causal claims. Simple standardized four-dimensional nearest-neighbour
  sparsity has weak association with absolute error (rho 0.047), whereas local
  five-neighbour observed-depth heterogeneity is stronger (rho 0.582). Phase 2
  quality indicators provide possible contributing evidence but do not support
  a single automatic exclusion rule.
- The conservative final diagnosis is `MIXED / UNRESOLVED`: high-depth and
  Keyhole/regime context, local target heterogeneity, old-domain expansion, and
  some target-quality indicators remain plausible contributors. Current
  evidence does not establish a broad model-family failure and does not justify
  replacing the retained depth GP before targeted support, regime, and raw-
  quality follow-up.
- A smoke run preceded the full 164-row analysis. The full run used 2,000
  simulation bootstraps, generated 15 figures, and completed in about 38
  seconds.
  The executed teaching notebook is
  `notebooks/week_07/04_new_data_feature_effects_depth_diagnostics.ipynb` with
  20 executed code sections and no stored errors. Final automated checks are
  24/24 PASS, the requirement checklist is 20/20 PASS, and the output manifest
  is 101/101.
- Hard stop reached after Phase 4. No Keyhole classifier, new label, T0
  redefinition, new GP family, causal analysis, active learning, level-set
  estimation, acquisition change, or pooled old+new production model was
  created. Phase 4 remains uncommitted and unpushed for review.
