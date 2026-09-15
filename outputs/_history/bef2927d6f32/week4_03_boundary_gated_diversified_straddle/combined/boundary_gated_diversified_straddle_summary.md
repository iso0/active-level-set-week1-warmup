# Week 4 Experiment 03 Boundary-Gated Diversified Straddle Summary

`diversified_straddle` is preserved with alpha `0.25`.
`boundary_gated_diversified_straddle` uses gate_fraction `0.1` and beta `0.5`.
Sensitivity was skipped to keep runtime manageable.

| Benchmark | Global vs best original | Global vs diversified | q20 vs best original | q20 vs diversified | q30 vs best original | q30 vs diversified |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | False | True | False | False | False | False |
| Thresholded 4D Ackley | False | False | False | True | False | True |

## Interpretation

Negative differences in `new_methods_vs_baselines_table.csv` are better for error, uncertainty, and query-distance metrics.
For query distance, smaller means closer to the true threshold in function-value space, but this is sampling behavior rather than predictive correctness.
If the gated method improves, this suggests diversity can help after filtering to boundary-relevant candidates.
If it does not improve, simple input-space diversity may still be insufficient; possible next steps are lookahead boundary-uncertainty reduction, boundary-manifold diversity, a GP classifier, or gate/beta sensitivity.
