# Active Level-Set Estimation Thesis

Current thesis title:

> Sample-Efficient Active Level-Set Estimation, with an Application to
> Melt-Pool Regime Boundaries

This repository contains the Week 1 and Week 2 warm-up project from Ioan's
working brief. It is the 2D synthetic-data plumbing stage before the main thesis
work on melt-pool regime boundaries. The purpose is to build one complete
active-learning loop, then compare acquisition rules before introducing the
final thesis model.

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
The new experiment is still synthetic, but it uses a deterministic 4D
continuous function on `[0,1]^4` and exact labels from a fixed threshold.

The selected first 4D benchmark is a controlled synthetic boundary function.
It combines a tilted 4D trend, nonlinear interaction waves, and a localized
bump. The threshold is fixed as the median of a reproducible uniform sample,
so labels are deterministic and the test labels are known exactly. This is
better aligned with active level-set estimation than ordinary classification
datasets such as Iris, because those datasets do not provide an exact
continuous level-set oracle.

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

## Run Week 3 4D benchmark comparison

```powershell
python -m src.week3_4d_benchmark_comparison
```

Outputs are saved under `outputs/week3_4d_benchmark_comparison/`:

- `summary.json`: benchmark definition, threshold rule, settings, fairness
  checks, method summaries, fixed test-error tolerance check, and caveats.
- `error_curves_all_methods.png`: mean error-vs-evaluations curves for all five
  acquisition rules.
- `final_error_bar_chart.png`: final error at budget 80 for each method.
- `selected_budget_table.csv`: method errors at budgets 12, 40, and 80.
- `method_summary_table.csv`: initial/final mean error, improvement, standard
  deviation, and rank.
- `week3_slide_notes.md`: beginner-friendly notes for Google Slides.

Important caveats: this is a first 4D synthetic benchmark. The model is still
`GaussianProcessRegressor` on `{-1,+1}` labels, not the final GP classifier.
The metric is test-label misclassification error, not a geometric
boundary-distance metric. The result is preliminary and should be discussed
with Ioan before treating it as a final thesis direction.

The short benchmark search note is saved in
`week3_4d_benchmark_search/week3_4d_benchmark_candidates.md`.
