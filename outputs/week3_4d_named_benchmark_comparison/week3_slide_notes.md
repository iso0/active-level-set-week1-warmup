# Week 3 Slide Notes: Thresholded 4D Ackley

## Why change the Week 3 benchmark

The earlier controlled 4D boundary was useful for software plumbing, but it was
custom-made. Ioan asked for new 4D datasets or benchmarks, so the main Week 3
result now uses a named analytic benchmark: thresholded 4D Ackley.

## Why Ackley

Ackley is deterministic, four-dimensional, nonlinear, and standard enough to
defend in a meeting. After thresholding the continuous function, every pool and
test point has an exact label. This keeps the active level-set setting while
moving beyond 2D Branin.

The domain is `[-5, 5]^4`. The GP receives scaled coordinates in
`[0,1]^4`, but plots use the original Ackley coordinates. The threshold is the
50th percentile of a reproducible random domain sample.

## How to understand a 4D boundary

We cannot draw the full boundary in one plot. Instead, the output folder
contains a value histogram, pairwise label projections, exact 2D slices, query
location projections, and model slice snapshots. These are diagnostic views,
not complete pictures of the 4D boundary.

## Fair comparison

For each seed, all five acquisition rules use the same threshold, pool, test
set, initial labelled points, GP-regression stand-in, and budget. Only the
acquisition rule changes.

## Main result

By mean final test-label misclassification error, the best method is
`straddle` with mean final error `0.168`
at budget 80.

Tolerance reach summary for the mean curves:

- 0.28: smallest_abs_mu at n=52; straddle at n=32; randomized_straddle at n=30; expected_feasibility at n=32.
- 0.24: smallest_abs_mu at n=79; straddle at n=44; randomized_straddle at n=46; expected_feasibility at n=52.
- 0.20: straddle at n=58; randomized_straddle at n=58; expected_feasibility at n=75.
- 0.18: straddle at n=70; randomized_straddle at n=75.
- 0.17: straddle at n=79.
- 0.16: no mean curve reached it.
- 0.15: no mean curve reached it.
- 0.14: no mean curve reached it.
- 0.13: no mean curve reached it.
- 0.12: no mean curve reached it.

## Caveats

This is still a first named 4D synthetic benchmark. The GP regressor is still a
stand-in, not the final GP classifier. The metric is test-label
misclassification error, not a geometric boundary-distance metric. The result
is preliminary and should be discussed with Ioan before treating it as a final
thesis direction.

## Suggested next step for Ioan

Show Ioan the Ackley diagnostics first, then the acquisition curves. Ask whether
he agrees that thresholded 4D Ackley is a reasonable named benchmark bridge, and
whether the next step should add thresholded 4D Rosenbrock/Rastrigin or move
toward the real laser data.
