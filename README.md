# Active Level-Set Estimation Thesis

Current thesis title:

> Sample-Efficient Active Level-Set Estimation, with an Application to
> Melt-Pool Regime Boundaries

This repository contains the Week 1-5 warm-up and benchmark-extension work
from Ioan's working brief. It starts with 2D synthetic-data plumbing, moves to a
named 4D analytic benchmark, adds boundary-focused diagnostics, and tests a
first diversity-augmented acquisition heuristic before the main thesis work on
melt-pool regime boundaries.

## Setup

From the project root in VS Code's PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For notebooks, select `.venv` as the Python kernel in VS Code.

## Week 1 in plain language

Week 1 asks two different questions:

1. **Does the loop visibly work?** `make_moons` is a simple visual sanity
   check. We can watch the estimated boundary change as labels are acquired.
2. **Can we measure whether it works?** Thresholded Branin has an exact known
   boundary. This lets us count how many independent test points the model
   labels incorrectly.

Both experiments currently use `GaussianProcessRegressor` on labels in
`{-1, +1}`. Its latent posterior mean is called `mu(x)`, and the believed
boundary is `mu(x) = 0`. This is a deliberately simple stand-in for Week 1. It
is **not** the final GP classifier, and its displayed scores are not calibrated
class probabilities.

The Week 1 acquisition rule is also intentionally simple:

```text
Choose the unlabelled pool point with the smallest |mu(x)|.
```

That is the point the current GP believes is nearest its decision boundary.
Only the selected point's label is revealed, mimicking an expensive simulator.

## Run make_moons

```powershell
python -m src.make_moons_sanity_check
```

Or run:

```text
notebooks/01_make_moons_sanity_check.ipynb
```

Outputs are saved under `outputs/make_moons/`.

The experiment uses 600 noisy-but-nearly-deterministic moon points, maps labels
to `{-1, +1}`, scales coordinates to `[0,1]^2`, starts from 6 labels, and stops
at 50. Its initial design is stratified random: three points from each class.
This avoids an uninformative one-class start and is recorded in the JSON.

## Run thresholded Branin

```powershell
python -m src.branin_week1
```

Or run:

```text
notebooks/02_branin_week1_loop.ipynb
```

Outputs are saved under `outputs/branin_week1/`:

- `dataset_overview.png`: exact thresholded-Branin regimes and boundary.
- `active_learning_snapshots_seed0.png`: GP belief at 6, 20, and 50 labels.
- `error_vs_evaluations.png`: error histories for three seeds and their mean.
- `summary.json`: threshold, settings, initial/final errors, and full histories.

The Branin threshold is estimated once as the 45th percentile over 20,000
uniform random domain points. Each seed then gets a reproducible pool of 1,500
points and an independent test set of 4,000 points. The model receives scaled
coordinates, while figures use the original Branin axes.

The six initial Branin points are random. In the rare case that all six have
the same label, the complete six-point draw is repeated until both classes are
present. The number of attempts is recorded in `summary.json`.

## Understanding the Branin error

After every GP fit, predictions on the 4,000-point test set are converted to
labels using:

```text
mu(x) >= 0  ->  +1
mu(x) < 0   ->  -1
```

The reported error is the fraction of these labels that disagree with the
exact thresholded-Branin labels. Lower is better. The curve does not need to
decrease after every single query because a newly fitted GP can move one part
of its boundary while improving another. The important Week 1 check is a clear
downward trend across the full budget and across multiple seeds.

Slide-ready notes are in `outputs/week1_slide_notes.md`.

## Week 2 in plain language

Week 2 asks a fair comparison question:

```text
If the data, GP model, initial labelled points, test set, and budget stay fixed,
which acquisition rule chooses the most useful next Branin labels?
```

Ioan's Week 2 brief asks us to hold the loop fixed and change only the
selection rule. The original brief names three rules: random, smallest `|mu|`,
and straddle. This project also adds two useful boundary-focused variants, for
five rules total:

- `random`: choose a random unlabelled pool point. This is the floor baseline.
- `smallest_abs_mu`: choose the point with the smallest `|mu(x)|`. This is the
  Week 1 rule.
- `straddle`: choose the largest `1.96 * sigma(x) - |mu(x)|`, balancing boundary
  closeness and uncertainty.
- `randomized_straddle`: draw one reproducible `beta ~ chi-square(df=2)` per
  acquisition step, then choose the largest `sqrt(beta) * sigma(x) - |mu(x)|`.
- `expected_feasibility`: choose a point with high expected improvement for the
  zero contour, approximating
  `E[max((1.96*sigma(x))^2 - Y(x)^2, 0)]` for
  `Y(x) ~ Normal(mu(x), sigma(x)^2)`.

The Week 2 comparison still uses `GaussianProcessRegressor` on `{-1, +1}`
labels. This keeps it aligned with the Week 1 plumbing, but it is still a
stand-in rather than the final GP classifier.

## Run Week 2 acquisition comparison

```powershell
python -m src.week2_acquisition_comparison
```

Or open:

```text
notebooks/03_week2_acquisition_comparison.ipynb
```

Outputs are saved under `outputs/week2_acquisition_comparison/`:

- `summary.json`: threshold, settings, fairness checks, full error histories,
  per-method/per-seed errors, an 8% test-error tolerance check, and the best
  method by mean final error.
- `error_curves_all_methods.png`: mean error-vs-evaluations curves for all five
  acquisition rules.
- `final_error_bar_chart.png`: final error at budget 50 for each method.
- `selected_budget_table.csv`: method errors at budgets 6, 20, and 50.
- `method_summary_table.csv`: initial/final mean error, improvement, standard
  deviation, and rank.
- `query_locations_seed0.png`: where each method queried by budget 50.
- `snapshots_best_*_seed0.png` and `snapshots_straddle_seed0.png`: model belief
  snapshots at 6, 20, and 50 labels.
- `week2_slide_notes.md`: beginner-friendly notes for Google Slides.

## Week 3 in plain language

Week 3 starts moving the benchmark from 2D Branin toward the real
laser-metal setting, where the process-parameter space is four-dimensional.
The main Week 3 benchmark is now a named analytic benchmark:
thresholded 4D Ackley.

Ackley is deterministic and can be evaluated exactly in four dimensions. After
thresholding the continuous function, every pool and test point has an exact
binary label:

```text
Ackley(x) >= threshold  ->  +1
Ackley(x) < threshold   ->  -1
```

The script uses the domain `[-5,5]^4`. This keeps the central Ackley basin and
level-set boundary visible for a finite pool and an 80-query active-learning
budget. Internally, the GP receives linearly scaled coordinates in `[0,1]^4`,
similar to the Branin scaling from Week 1 and Week 2.

The previous controlled synthetic 4D boundary script is still present as a
secondary / optional experiment:

```powershell
python -m src.week3_4d_benchmark_comparison
```

It is useful for controlled studies, but it is no longer the main Week 3
benchmark because Ioan asked for a known 4D dataset or benchmark.

## Understanding the 4D Ackley benchmark

In 2D Branin we could draw the full exact boundary. In 4D, we cannot visualize
the full boundary in one plot. The named Week 3 script therefore creates
diagnostic views:

- `dataset_value_distribution.png`: histogram of Ackley values with the chosen
  threshold and class balance.
- `pairwise_label_projections_seed0.png`: all six pairwise 2D projections of
  seed-0 pool labels.
- `exact_boundary_2d_slices.png`: exact label regions and threshold contours on
  fixed 2D slices through the 4D function.
- `query_locations_projection_seed0.png`: seed-0 acquisition locations,
  projected to `x0` vs `x1`.
- `straddle_slice_snapshots_seed0.png` and
  `randomized_straddle_slice_snapshots_seed0.png`: GP boundary snapshots on a
  fixed 2D slice, compared with the exact threshold contour.

These plots are diagnostics, not complete pictures of the 4D boundary.

## Run Week 3 named 4D benchmark comparison

```powershell
python -m src.week3_4d_named_benchmark_comparison
```

Outputs are saved under `outputs/week3_4d_named_benchmark_comparison/`:

- `summary.json`: benchmark choice, formula in words, domain, scaling,
  threshold, class balance, fairness checks, method summaries, richer tolerance
  analysis, caveats, and generated diagnostics.
- `error_curves_all_methods.png`: mean error-vs-evaluations curves for all five
  acquisition rules.
- `final_error_bar_chart.png`: final error at budget 80 for each method.
- `selected_budget_table.csv`: method errors at budgets 12, 40, and 80.
- `method_summary_table.csv`: initial/final mean error, improvement, standard
  deviation, and rank.
- `tolerance_reach_table.csv` and `tolerance_reach_table.md`: first budgets at
  which each method reaches several test-error tolerances.
- `week3_slide_notes.md`: beginner-friendly notes for Google Slides.

The comparison keeps the Week 2 fairness structure:

- same threshold,
- same 4D pool and test set within each seed,
- same initial labelled points within each seed,
- same GP-regression stand-in,
- same total budget,
- same five acquisition rules,
- only the acquisition rule changes.

The Week 3 settings are intentionally larger than Branin while still
laptop-reasonable: five seeds, pool size 4,000, test size 10,000, initial
labelled size 12, and total budget 80.

Important caveats: this is a first named 4D synthetic benchmark. The model is
still `GaussianProcessRegressor` on `{-1,+1}` labels, not the final GP
classifier. The metric is test-label misclassification error, not a geometric
boundary-distance metric. The result is preliminary and should be discussed
with Ioan before treating it as a final thesis direction.

The short benchmark search note is saved in
`week3_4d_benchmark_search/week3_4d_benchmark_candidates.md`.

## Week 4 — Boundary Metrics, Acquisition Experiments and GP Classifier/SUR Studies

The nine studies in this section were all performed during the actual Week 4
and are therefore organized as Experiments 01–09. Older Git commits and legacy
branch names may still contain the original incorrect Week 5–7.1 labels because
Git history was intentionally preserved.

### Experiment 01 — Boundary-focused evaluation metrics

Experiment 01 strengthens the evaluation. Global test-label misclassification
error is useful, but the thesis is about active level-set estimation and
boundary identification. A method can improve global accuracy while still
doing poorly near the true threshold boundary.

The Experiment 01 script keeps the existing Week 2 Branin and Week 3 Ackley
experiments fixed and adds boundary-focused metrics:

- Near-boundary error: test error restricted to the closest 10%, 20%, and 30%
  of test points by `abs(f(x) - threshold)`.
- Query distance to boundary: `abs(f(x_query) - threshold)` for each newly
  acquired point.
- Latent uncertainty-region fraction: the fraction of test points satisfying
  `abs(mu(x)) <= 1.96 * sigma(x)` under the GP-regression stand-in.
- Global error: the original all-test-point misclassification error, kept for
  comparison.

The near-boundary distance is a function-value distance proxy. It is not
Euclidean distance to the geometric contour. The uncertainty-region fraction is
based on the GP-regression latent mean and standard deviation, not calibrated
class probability.

Run:

```powershell
python -m src.week4_01_boundary_metrics
```

Outputs are saved under `outputs/week4_01_boundary_metrics/`:

- `branin/`: Week 2 Branin boundary metrics, plots, tables, and notes.
- `ackley/`: Week 3 thresholded-4D-Ackley boundary metrics, plots, tables, and
  notes.
- `combined/`: high-level comparison of Branin and Ackley conclusions.

Each benchmark folder includes:

- `summary.json`
- `boundary_metric_summary_table.csv`
- `final_boundary_metrics_table.csv`
- `raw_boundary_metrics.csv`
- `query_distance_table.csv`
- near-boundary error curves for q10/q20/q30
- final global-vs-near-boundary error plot
- query-distance boxplot and over-budget plot
- uncertainty-region fraction curves
- `boundary_metric_notes.md`

The run computes all budgets for both benchmarks. On the current laptop setup,
it takes about 5-6 minutes because it predicts both GP means and standard
deviations on the full test sets at every budget.

### Experiment 02 — Diversified straddle

Experiment 02 tests a first new acquisition heuristic:

```text
diversified_straddle =
    (1 - alpha) * normalized_straddle + alpha * normalized_diversity
```

Here `straddle = 1.96 * sigma(x) - |mu(x)|`, and diversity is the minimum
distance from a candidate pool point to the currently labelled set in scaled
input coordinates. The default `alpha` is 0.25. The purpose is to test whether
adding a small coverage pressure to straddle helps avoid repeatedly sampling
near the same part of the boundary.

Run:

```powershell
python -m src.week4_02_diversified_straddle
```

Outputs are saved under `outputs/week4_02_diversified_straddle/`:

- `branin/`: Week 2 Branin with the five original rules plus
  `diversified_straddle`.
- `ackley/`: Week 3 thresholded-4D-Ackley with the same six-rule comparison.
- `combined/`: summary tables comparing `diversified_straddle` against the best
  original methods and selected baselines.

Each benchmark folder includes final metric tables, selected-budget tables,
raw metric traces, query-distance tables, global and near-boundary error plots,
query-distance plots, uncertainty-region fraction plots, `summary.json`, and
`diversified_straddle_notes.md`.

The first result is preliminary: `diversified_straddle` with `alpha=0.25` did
not beat the best original acquisition rule on global error, q20 near-boundary
error, q30 near-boundary error, query distance, or q20/q30 uncertainty-region
fraction on either Branin or Ackley. This does not rule out diversity as a useful
idea; it only says that this simple fixed-alpha version was not better in the
current settings.

Important caveats: the GP regressor is still a stand-in, not the final GP
classifier. The metric is test-label misclassification error plus diagnostic
boundary proxies, not a geometric boundary-distance metric. Alpha sensitivity
was skipped to keep runtime manageable. This result should be discussed with
Ioan before treating it as a final thesis direction.

### Experiment 03 — Boundary-gated diversified straddle

The first `diversified_straddle` result suggested that generic input-space
diversity over the full unlabelled pool was not enough. It can pull queries
away from the boundary, while the thesis goal is boundary coverage.

The boundary-gated follow-up keeps `diversified_straddle` and adds a seventh
method:

```text
boundary_gated_diversified_straddle
```

The method first computes the usual straddle score:

```text
straddle_score(x) = 1.96 * sigma(x) - abs(mu(x))
```

It then keeps only the top 10% of unlabelled candidates by straddle score, with
a minimum shortlist size of 25 when possible. Inside that shortlist only, it
uses:

```text
score = (1 - beta) * normalized_straddle + beta * normalized_diversity
```

with `beta=0.50`. Diversity is the minimum distance to the currently labelled
set in scaled input coordinates.

Run:

```powershell
python -m src.week4_03_boundary_gated_diversified_straddle
```

Outputs are saved under:

```text
outputs/week4_03_boundary_gated_diversified_straddle/
```

The run compares seven methods on Branin and thresholded 4D Ackley. It keeps the
same threshold, pool, test set, initial labelled points, GP model, seeds, and
budget within each benchmark. Sensitivity over `gate_fraction` and `beta` was
skipped to keep runtime manageable.

This is still a heuristic benchmark extension. Query distance is a sampling
diagnostic, not predictive correctness. The uncertainty-region fraction is a
GP-regression latent diagnostic, not calibrated classification uncertainty.

### Experiment 04 — Lookahead boundary-uncertainty reduction

Experiment 04 tests a more thesis-aligned acquisition idea. Instead of asking
only whether a candidate itself has high straddle score, it asks which
candidate is expected to reduce aggregate boundary uncertainty over the
unlabelled pool.

The new method is:

```text
lookahead_boundary_uncertainty_reduction
```

At each step it shortlists the top 30 unlabelled candidates by straddle score:

```text
1.96 * sigma(x) - abs(mu(x))
```

For each shortlisted candidate, it creates two fantasy updates, one with label
`+1` and one with label `-1`. It refits the GP posterior under each fantasy
label and computes the mean positive straddle value over the current unlabelled
pool:

```text
mean(max(0, 1.96 * sigma(x) - abs(mu(x))))
```

The selected point is the one with the largest expected reduction in that
aggregate uncertainty. The fantasy label probability uses
`Phi(mu / max(sigma, 1e-9))`, which is a heuristic GP-regression latent
probability, not a calibrated GP-classifier probability.

Run:

```powershell
python -m src.week4_04_lookahead_boundary_uncertainty
```

Outputs are saved under:

```text
outputs/week4_04_lookahead_boundary_uncertainty/
```

The run compares eight methods: the five original rules, the two Experiments 02–03
diversity rules, and the new lookahead rule. It keeps the same threshold, pool,
test set, initial labelled points, GP model, seeds, and budget within each
benchmark.

The lookahead computation is expensive because each query evaluates fantasy
`+1` and `-1` refits for 30 shortlisted candidates. To keep the runtime
manageable, fantasy fits keep the current fitted kernel hyperparameters fixed
and refit only the posterior; the actual active-learning model fit at each
budget still uses the existing `fit_gp` helper. Ackley shortlist sensitivity was
skipped to keep runtime manageable.

Caveats: this is still a heuristic. It does not use true labels, function
values, test labels, or true boundary masks during acquisition. Query distance
is still only an evaluation diagnostic. The uncertainty-region fraction measures
GP latent uncertainty, not correctness, and a method can become confidently
wrong.

### Experiment 05 — Gated geometric boundary contraction

Experiment 05 tests a curvature-aware acquisition rule inspired by geometric
boundary contraction, reimplemented inside the existing sklearn
`GaussianProcessRegressor` pipeline:

```text
gated_geometric_boundary_contraction
```

The motivation is that not all predicted boundary points are equally useful:
high-curvature parts of the GP-predicted boundary may need more samples than
flat parts. The method is gated by straddle so curvature is only considered
among candidates that already look boundary-relevant.

At each step it keeps the top 200 unlabelled candidates by:

```text
1.96 * sigma(x) - abs(mu(x))
```

Inside that shortlist it computes:

```text
normalized_curvature
* normalized_uncertainty
* boundary_weight
* repulsion
```

Curvature is estimated by finite differences of the GP posterior mean in scaled
coordinates using only the diagonal Hessian terms. The boundary weight uses the
heuristic GP-regression latent probability
`Phi(mu / sqrt(1 + sigma^2))`, not calibrated GP-classifier probabilities.
Repulsion uses distance to the currently labelled set with fixed bandwidth
`0.15`.

Run:

```powershell
python -m src.week4_05_gated_geometric_boundary_contraction
```

Outputs are saved under:

```text
outputs/week4_05_gated_geometric_boundary_contraction/
```

The run compares eight methods: the five original rules, the two Experiments 02–03
diversity rules, and GBC. It does not rerun the expensive Experiment 04 lookahead
method; if Experiment 04 outputs are present, the combined summary includes those
lookahead numbers only as labelled reference data.

Caveats: GBC is heuristic. Curvature is estimated from the GP posterior mean,
not the true function. The Hessian approximation is diagonal-only for speed.
Curvature is evaluated only within a straddle-gated shortlist. Lower
uncertainty-region fraction or closer query distance does not necessarily imply
better boundary classification.

### Experiment 06 — Fixed-kernel GP classifier surrogate

Experiment 06 changes the surrogate model. The preceding experiments used
`GaussianProcessRegressor` on `{-1,+1}` labels as a warm-up stand-in. Experiment 06
uses sklearn's `GaussianProcessClassifier`, so acquisition rules are based on
class probabilities from `predict_proba` instead of GP-regression latent
`mu`/`sigma`.

Run:

```powershell
python -m src.week4_06_gp_classifier_surrogate
```

Outputs are saved under:

```text
outputs/week4_06_gp_classifier_surrogate/
```

The script compares classifier-native acquisition rules:

- `random`
- `classifier_margin`
- `classifier_entropy`
- `classifier_gated_diversity`
- `classifier_uncertainty_repulsion`

The classifier uses a fixed RBF kernel with `optimizer=None` for runtime
stability and reproducibility. This is a practical first GP-classifier
surrogate benchmark, not the final modelling choice.

The combined summary includes labelled reference comparisons against existing
GP-regressor outputs when available. Those rows are not acquisition-only
comparisons, because the surrogate model family changed. Previous Week 1–3 and
Week 4 Experiment 01–05 outputs are preserved.

Caveats: GP-classifier probabilities are not the same object as GP-regressor
latent mean and standard deviation. Binary entropy and margin are
monotone-equivalent, so they may select identical points. Lower classifier
uncertainty-region fraction does not automatically prove correct boundary
learning. The q10/q20/q30 subsets are evaluation diagnostics only.

### Experiment 07 — Optimized GP classifier surrogate

Experiment 07 tests whether learning `GaussianProcessClassifier` kernel
hyperparameters fixes the main limitation of the Experiment 06 fixed-kernel
classifier. The run compares three classifier surrogates:

- `fixed_iso_gpc`: the Experiment 06 fixed isotropic RBF classifier.
- `optimized_iso_gpc`: learns one shared RBF length-scale and kernel constant.
- `optimized_ard_gpc`: learns one RBF length-scale per input dimension plus the
  kernel constant.

Run:

```powershell
python -m src.week4_07_optimized_gp_classifier_surrogate --full
```

Outputs are saved under:

```text
outputs/week4_07_optimized_gp_classifier_surrogate/
```

The full run used all five seeds, all five Experiment 06 classifier acquisitions,
`n_restarts_optimizer=2`, and `optimize_every=1`; no runtime reduction was
needed. On this machine the command completed in about 537 seconds.

Main result:

- Branin: optimized ARD with `classifier_gated_diversity` was best on global
  error, q20, and q30, with final means 0.035150, 0.163750, and 0.114333. It
  beat the previous Experiment 06 fixed classifier and the available Experiment 04
  GP-regressor reference on those metrics.
- Ackley: the fixed Experiment 06 classifier with `classifier_uncertainty_repulsion`
  remained best, with final means 0.175900, 0.417500, and 0.379667. Optimized
  isotropic and ARD classifiers did not beat the fixed classifier or the
  previous GP-regressor references.

Interpretation: kernel learning clearly helps the classifier on 2D Branin, but
does not solve the harder 4D Ackley benchmark. Hyperparameter bound hits are
common, especially on Ackley, so this is diagnostic rather than a final claim
that GP classification dominates. q20/q30 remain the main boundary metrics;
q10 is kept only as a noisy diagnostic.

Reproducibility check: two quick-mode reruns into temporary output directories
matched exactly on deterministic metric curves, query-distance tables,
best-method tables, and comparison tables. Final metric tables also matched
after excluding wall-clock fit-time columns.

For schema compatibility, existing CSV/JSON keys such as `previous_week6_*` and
`optimized_classifier_beats_previous_fixed_week6` are retained as legacy field
names. They refer to Experiment 06 and do not describe the corrected chronology.

### Experiment 08 — Boundary-weighted IVR / Bernoulli SUR

Experiment 08 tests a literature-inspired boundary-weighted uncertainty-reduction
family before the real melt-pool dataset arrives. The new script is:

```powershell
python -m src.week4_08_boundary_weighted_sur --full
```

Outputs are saved under:

```text
outputs/week4_08_boundary_weighted_sur/
```

The experiment keeps Branin and thresholded 4D Ackley and adds thresholded 4D
Hartmann on `[0,1]^4`. Hartmann uses the standard 4D Hartmann function, a 50th
percentile threshold estimated from 100,000 random points with seed 2026, pools
of 4,000 points, test sets of 10,000 points, five seeds, 12 initial labels, and
budget 80.

The new GP-regressor acquisitions are:

- `gpr_boundary_weighted_ivr`: straddle-gated posterior variance reduction over
  a boundary-weighted reference set, with weights `p(+1)(1-p(+1))`.
- `gpr_bernoulli_sur_refit`: expected reduction in integrated Bernoulli
  membership uncertainty after fantasy `+1/-1` updates. The implementation uses
  the exact fixed-kernel rank-one posterior update equivalent to a fixed-kernel
  GP posterior refit.

The classifier version, `gpc_bernoulli_sur_refit`, is much more expensive. In
the full Experiment 08 run it was limited to Branin and Hartmann seed 0 with classifier
SUR shortlist size 15; GP-regressor methods and fixed classifier baselines were
run on all five seeds.

Full-run comparable five-seed results:

- Branin: best global was `randomized_straddle` (0.060200), best q20 was
  `smallest_abs_mu` (0.246750), and best q30 was `randomized_straddle`
  (0.186500). The new GP-regressor IVR/SUR methods did not beat randomized
  straddle on q20 or q30.
- Ackley: best global was `straddle` (0.168400), and best q20/q30 remained
  `randomized_straddle` (0.408400 / 0.368200). Both new GP-regressor methods
  were worse on q20/q30.
- Hartmann4: best comparable global was fixed classifier
  `classifier_uncertainty_repulsion` (0.123640), while best q20/q30 were
  GP-regressor `expected_feasibility` (0.380400 / 0.325533). Cheap
  boundary-weighted IVR beat `randomized_straddle` on q20/q30, but did not beat
  the strongest Hartmann q20/q30 method.

Interpretation: boundary-weighted IVR is useful enough to keep as a thesis
diagnostic, especially because Hartmann differs from Ackley, but Bernoulli SUR
refit did not justify its extra complexity under the current GP-regression
surrogate. Ackley remains the hardest benchmark for these uncertainty-reduction
rules. Lower integrated Bernoulli uncertainty did not reliably imply lower
q20/q30 error, so uncertainty contraction must be treated as a diagnostic, not
as success by itself.

### Experiment 09 — Fixed-GPC Bernoulli SUR validation

Experiment 09 validates the promising Experiment 08 seed-0 classifier SUR result across
seeds without rerunning every earlier method. The new script is:

```powershell
python -m src.week4_09_gpc_bernoulli_sur_validation --full --benchmarks branin hartmann4
```

Outputs are saved under:

```text
outputs/week4_09_gpc_bernoulli_sur_validation/
```

The experiment uses the same fixed-kernel GP classifier as Experiments 06 and 08:
`ConstantKernel(1.0, fixed) * RBF(length_scale=0.25, fixed)`, with
`optimizer=None`. It compares `random_classifier`, `classifier_margin`,
`classifier_entropy`, `classifier_uncertainty_repulsion`, and classifier-native
Bernoulli SUR refit with shortlists k15 and k25. k40 was not run. The SUR
objective is expected reduction in mean reference-set Bernoulli uncertainty
`p(+1)(1-p(+1))` after fantasy `+1/-1` classifier refits.

Full primary validation used Branin and Hartmann4, all five seeds, reference
size 1500, and shortlists 15 and 25. Ackley was run only as an optional
three-seed diagnostic.

Main results:

- Branin: `classifier_uncertainty_repulsion` was best on global/q20/q30 with
  0.073200 / 0.256000 / 0.189667. SUR k15 reached 0.073300 / 0.265500 /
  0.201500, so the Experiment 08 seed-0 classifier SUR signal did not generalize on
  Branin.
- Hartmann4: SUR won the primary boundary metrics. k15 was best on global
  error at 0.116020, while k25 was best on q20/q30 at 0.373000 / 0.315467.
  Both k15 and k25 beat `classifier_uncertainty_repulsion` on q20/q30.
- Optional Ackley, three seeds: SUR did not help. Best global was
  `classifier_uncertainty_repulsion` at 0.178367, while best q20/q30 were
  `classifier_entropy` at 0.421167 / 0.379667.

Interpretation: fixed-GPC Bernoulli SUR is a serious diagnostic and a
Hartmann4 candidate, but it is not robust enough to replace
`classifier_uncertainty_repulsion` or the stronger GP-regressor baselines as a
default method. Integrated Bernoulli uncertainty had positive curve-level
correlation with q20/q30 error, but Branin and optional Ackley show that lower
uncertainty can still mean confidently wrong boundary classification. The
runtime cost is only defensible for focused diagnostics, not as a default
pool-based acquisition loop for real laser data.

For schema compatibility, the generated validation summaries retain legacy
`week7_seed0_*` and `week7_best_full_*` column names. These fields refer to the
Experiment 08 reference run; RNG namespace strings are also intentionally
unchanged so that reruns remain reproducible.

## Week 5 — First-Conduction GP Regression on Real Simulation Data

The actual Week 5 work begins the real-data surrogate-model warm-up. One
observation is one simulation, identified by name. The four inputs are laser
power (P), scan velocity (VX), laser spot radius (LS), and substrate
temperature (ST). The target is the first raw timestep at which
label_final equals Conduction; it is not converted to physical time.

The pinned CSV contains 241 simulations. Of these, 238 have an observed
Conduction target and three are excluded because the target is undefined.
The regression is reported separately for an operational no-Screenshot-Bug
subgroup (91 simulations) and the inclusive broad dataset (238 simulations).
The no-Bug subgroup is not claimed to be higher-quality data.

Four kernels were compared with simulation-level leave-one-out evaluation:
isotropic RBF, ARD RBF, Matérn 3/2, and Matérn 5/2. Matérn 3/2 gives the best
point-prediction metrics on both datasets. A subsequent L-BFGS-B, SLSQP,
Powell, and no-optimization comparison finds the three optimized solutions
practically identical; L-BFGS-B remains the recommended default.

A targeted [ARD Matérn 3/2 robustness extension](notebooks/week_05/05_ard_matern32_extension.ipynb) did not improve RMSE on either dataset and therefore leaves the isotropic Matérn 3/2 recommendation unchanged; see the [concise extension results](outputs/week5_05_ard_matern32_extension/week5_05_results_summary.md).

The Week 5 notebooks are:

- notebooks/week_05/01_first_conduction_data_audit.ipynb
- notebooks/week_05/02_first_conduction_gp_kernel_comparison.ipynb
- notebooks/week_05/03_bug_initial_emptiness_ls_analysis.ipynb
- notebooks/week_05/04_matern32_optimizer_comparison.ipynb
- notebooks/week_05/05_ard_matern32_extension.ipynb

The label-sequence diagnostic incorporates the supervisor's clarification that
Screenshot Bug may represent repeated Initial Emptiness frames rather than
corrupted simulation data. It also reviews LS and other input differences and
the largest Matérn 3/2 LOO errors without changing the fixed regression target.

See the cumulative [Week 5 thesis decision log](docs/week5_first_conduction_gp_log.md)
and the concise [Week 5 meeting brief](docs/week5_gp_meeting_brief.md). Generated
artifacts are under outputs/week5_01_* through outputs/week5_05_*.

Week 5 stops at regression diagnostics and packaging. Active learning and
level-set estimation have not started.
