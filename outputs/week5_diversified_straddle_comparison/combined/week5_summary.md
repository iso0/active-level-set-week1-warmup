# Week 5 Diversified Straddle Summary

`diversified_straddle` uses alpha `0.25`.
Alpha sensitivity was not run to keep runtime manageable.

| Benchmark | Improves global | Improves q20 | Improves q30 | Queries closer | Reduces q20 uncertainty | Reduces q30 uncertainty |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | False | False | False | False | False | False |
| Thresholded 4D Ackley | False | False | False | False | False | False |

## Interpretation

Negative differences in `new_method_vs_baselines_table.csv` are better for error and uncertainty metrics.
For query distance, smaller means closer to the true threshold in function-value space, but this is sampling behavior rather than predictive correctness.
