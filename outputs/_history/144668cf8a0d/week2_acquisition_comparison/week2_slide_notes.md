# Week 2 Slide Notes

## What Week 2 tests

Week 2 keeps the Week 1 Branin active-learning loop fixed and changes only the
acquisition rule. The question is: if the same GP, same pool, same test set,
same initial labels, and same budget are used, which rule chooses the most useful
next labels?

## Why only the acquisition changes

Ioan's instruction is to make the comparison fair. For each seed, all five
methods start from the exact same six labelled Branin points and evaluate on the
same 4,000-point test set. Any difference in the error curves should therefore
come from the rule used to choose the next point.

## The five rules in plain English

- Random: choose any unlabelled point uniformly at random. This is the floor
  baseline.
- Smallest |mu|: choose the point closest to the current GP boundary. This is
  the Week 1 rule and a noiseless label-uncertainty stand-in.
- Straddle: choose points that are both close to the boundary and uncertain,
  using 1.96*sigma - |mu|.
- Randomized straddle: same idea as straddle, but the uncertainty weight changes
  each step using one reproducible chi-square random draw.
- Expected feasibility: a contour-focused expected-improvement-style heuristic.
  It scores points by how plausible it is that the latent GP value lies near the
  zero contour.

## How to read the error curves

The y-axis is the fraction of 4,000 independent Branin test points whose exact
threshold label is predicted incorrectly. Lower is better. The curve can move
up at individual steps because refitting the GP moves the whole boundary.
Compare the overall trend and the final error at budget 50.

## Which method performed best

By mean final error over the seeds, the best method in this run is
`randomized_straddle` with mean final error `0.060`.

Using a fixed 8% test-error tolerance as a lightweight proxy
for the brief's tolerance check:

- random: did not reach 8% mean test error.
- smallest_abs_mu: reached 8% mean test error at n=39.
- straddle: reached 8% mean test error at n=35.
- randomized_straddle: reached 8% mean test error at n=32.
- expected_feasibility: reached 8% mean test error at n=37.

## Caveats

The GP regressor on -1/+1 labels is still a stand-in. The final thesis method
should use a proper GP classifier or a more suitable surrogate. Smallest |mu|,
straddle, randomized straddle, and expected feasibility are heuristic rules in
this plumbing stage. The tolerance check above is based on test
misclassification error, not a separate geometric contour-distance metric.

