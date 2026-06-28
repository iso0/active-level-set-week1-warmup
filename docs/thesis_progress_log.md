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
