# Hartmann4 Benchmark Notes

Hartmann4 is a standard deterministic 4D function on `[0,1]^4`. Week 7 thresholds it at the 50th percentile and uses exact labels `+1` if `f(x) >= threshold`, else `-1`.

- Threshold: `-0.97797833` from `100000` samples with seed `2026`.
- Saved diagnostics: `hartmann4_value_distribution.png`, `hartmann4_pairwise_label_projections_seed0.png`, and `hartmann4_exact_2d_slices.png`.
- Best Hartmann q20/q30: `expected_feasibility` / `expected_feasibility`.
- Ackley q20 best method is `randomized_straddle`; Hartmann q20 best method is `expected_feasibility`. Agreement should be judged by method family and q20/q30 behavior, not by global error alone.
