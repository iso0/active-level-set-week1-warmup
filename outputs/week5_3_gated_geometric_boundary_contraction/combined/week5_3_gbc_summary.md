# Week 5.3 Gated Geometric Boundary Contraction Summary

`gated_geometric_boundary_contraction` uses straddle-gated shortlist size `200`.
Finite-difference h: `0.001`; curvature clip: `10.0`; repulsion bandwidth: `0.15`.
Week 5.2 lookahead numbers are included only as reference if existing outputs are available; they are not rerun in this Week 5.3 experiment.

| Benchmark | Global vs best original | Global vs straddle | Global vs gated diversity | q20 vs best original | q20 vs straddle | q20 vs gated diversity | q30 vs best original | q30 vs randomized | q30 vs gated diversity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | False | False | False | False | False | False | False | False | False |
| Thresholded 4D Ackley | False | False | False | False | False | False | False | False | False |

## Lookahead Reference

- Thresholded Branin: lookahead reference global `0.055900`, q20 `0.235500`, q30 `0.175333`.
- Thresholded 4D Ackley: lookahead reference global `0.228960`, q20 `0.444200`, q30 `0.408000`.

## Interpretation

Negative differences in `gbc_vs_baselines_table.csv` are better for error, uncertainty, and query-distance metrics.
For query distance, smaller means closer to the true threshold in function-value space, but this is sampling behavior rather than predictive correctness.
If GBC improves, this suggests local geometric information from the GP posterior boundary can help sample-efficient boundary learning.
If GBC does not improve, finite-difference curvature under the current GP-regression surrogate may not be reliably aligned with true boundary classification accuracy.
Caveats: GBC is heuristic; curvature comes from the GP posterior mean, not the true function; the Hessian is diagonal-only; the boundary weight uses a latent GP-regression probability heuristic; lower uncertainty does not prove correctness.
