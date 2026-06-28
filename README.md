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

## Week 4 in plain language

Week 4 strengthens the evaluation. Global test-label misclassification error is
useful, but the thesis is about active level-set estimation and boundary
identification. A method can improve global accuracy while still doing poorly
near the true threshold boundary.

The Week 4 script keeps the existing Week 2 Branin and Week 3 Ackley
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
python -m src.week4_boundary_metrics
```

Outputs are saved under `outputs/week4_boundary_metrics/`:

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
- `week4_boundary_metric_notes.md`

The run computes all budgets for both benchmarks. On the current laptop setup,
it takes about 5-6 minutes because it predicts both GP means and standard
deviations on the full test sets at every budget.

## Week 5 in plain language

Week 5 tests a first new acquisition heuristic:

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
python -m src.week5_diversified_straddle_comparison
```

Outputs are saved under `outputs/week5_diversified_straddle_comparison/`:

- `branin/`: Week 2 Branin with the five original rules plus
  `diversified_straddle`.
- `ackley/`: Week 3 thresholded-4D-Ackley with the same six-rule comparison.
- `combined/`: summary tables comparing `diversified_straddle` against the best
  original methods and selected baselines.

Each benchmark folder includes final metric tables, selected-budget tables,
raw metric traces, query-distance tables, global and near-boundary error plots,
query-distance plots, uncertainty-region fraction plots, `summary.json`, and
`week5_notes.md`.

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

### Week 5 boundary-gated extension

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
python -m src.week5_boundary_gated_straddle_comparison
```

Outputs are saved under:

```text
outputs/week5_boundary_gated_diversified_straddle_comparison/
```

The run compares seven methods on Branin and thresholded 4D Ackley. It keeps the
same threshold, pool, test set, initial labelled points, GP model, seeds, and
budget within each benchmark. Sensitivity over `gate_fraction` and `beta` was
skipped to keep runtime manageable.

This is still a heuristic benchmark extension. Query distance is a sampling
diagnostic, not predictive correctness. The uncertainty-region fraction is a
GP-regression latent diagnostic, not calibrated classification uncertainty.

### Week 5.2 lookahead boundary-uncertainty extension

Week 5.2 tests a more thesis-aligned acquisition idea. Instead of asking only
whether a candidate itself has high straddle score, it asks which candidate is
expected to reduce aggregate boundary uncertainty over the unlabelled pool.

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
python -m src.week5_2_lookahead_boundary_uncertainty
```

Outputs are saved under:

```text
outputs/week5_2_lookahead_boundary_uncertainty/
```

The run compares eight methods: the five original rules, the two Week 5.1
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

### Week 5.3 gated geometric boundary contraction

Week 5.3 tests a curvature-aware acquisition rule inspired by geometric boundary
contraction, reimplemented inside the existing sklearn `GaussianProcessRegressor`
pipeline:

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
python -m src.week5_3_gated_geometric_boundary_contraction
```

Outputs are saved under:

```text
outputs/week5_3_gated_geometric_boundary_contraction/
```

The run compares eight methods: the five original rules, the two Week 5.1
diversity rules, and GBC. It does not rerun the expensive Week 5.2 lookahead
method; if Week 5.2 outputs are present, the combined summary includes those
lookahead numbers only as labelled reference data.

Caveats: GBC is heuristic. Curvature is estimated from the GP posterior mean,
not the true function. The Hessian approximation is diagonal-only for speed.
Curvature is evaluated only within a straddle-gated shortlist. Lower
uncertainty-region fraction or closer query distance does not necessarily imply
better boundary classification.
