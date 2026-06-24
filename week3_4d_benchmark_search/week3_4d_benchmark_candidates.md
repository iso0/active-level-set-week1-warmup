# Week 3: 4D Benchmark Candidate Review

The Week 3 goal is to move the active level-set estimation plumbing from the
2D Branin example toward a setting closer to the laser-metal process-parameter
problem. The real application has four input variables, so the first useful
extension is a deterministic 4D benchmark with exact threshold labels.

| Candidate | Dimension | Label generation | Why it is useful for active level-set estimation | Pros | Cons / caveats | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded 4D Ackley | 4 | Evaluate the analytic Ackley function on `[0, 1]^4` or a rescaled box, then label points by whether the value is above a fixed threshold or percentile. | Gives a smooth but multimodal continuous function with a known oracle and exact labels for any pool or test point. | Standard benchmark; nonlinear in all four coordinates; deterministic; easy to reproduce; useful bridge from optimization benchmarks to level-set estimation. | The level set can be shaped by global-optimization landscape features rather than by a controlled physical boundary; threshold choice strongly affects class balance and boundary complexity. | Good secondary choice. Use if we want a named benchmark function that readers recognize. |
| Thresholded 4D Rastrigin | 4 | Evaluate the analytic Rastrigin function and threshold its value. | Creates many repeated local structures, so acquisition rules must handle multiple disconnected boundary pieces. | Standard, deterministic, highly multimodal, easy to compute. | Can be artificially oscillatory and too periodic compared with melt-pool regimes; a small GP-regression stand-in may struggle for reasons unrelated to active learning. | Useful stress test after the first 4D benchmark, but probably too wiggly as the first Week 3 extension. |
| Thresholded 4D Rosenbrock | 4 | Evaluate the analytic Rosenbrock function and threshold its value. | Produces curved level sets around a narrow valley, giving a deterministic nonlinear boundary. | Standard, smooth, deterministic, easy to compute. | The function is strongly tied to an optimization valley; thresholded labels may be imbalanced unless the threshold is chosen carefully; less directly boundary-focused than a custom construction. | Reasonable baseline, but not the best first benchmark for explaining active level-set estimation. |
| Thresholded 4D Styblinski-Tang | 4 | Evaluate the analytic Styblinski-Tang function and threshold its value. | Gives a deterministic 4D function with nonlinear polynomial structure and multiple basins. | Standard, separable, cheap to evaluate, easy to reproduce. | Separability may make the boundary less representative of interacting process parameters; threshold selection matters. | Useful as an additional analytic benchmark once the first 4D comparison is working. |
| Controlled synthetic 4D boundary function | 4 | Define a smooth continuous function directly on `[0, 1]^4`, including linear trends, interactions, and sinusoidal terms; threshold it at a fixed percentile. | Designed for level-set estimation rather than optimization: the boundary is the object of interest, labels are deterministic, and exact test labels are computable. | Most aligned with the thesis plumbing; class balance and boundary difficulty can be controlled; uses the same pool-based active-learning setup as Week 2; easy to describe to Ioan as a first 4D synthetic benchmark. | Less recognizable than Ackley/Rastrigin; because it is custom, it should not be overclaimed as a standard benchmark. | Best first Week 3 benchmark. It preserves the thesis setting while making the 4D move explicit and controllable. |
| Public 4-feature classification datasets such as Iris | 4 | Use dataset class labels directly, or create a binary task from selected classes. | Can sanity-check whether code works on a familiar 4-feature table. | Familiar; tiny; easy to load; useful as a secondary classification smoke test. | Not an exact deterministic level-set oracle; no known continuous threshold function; labels are empirical class labels, not exact simulator labels; active pool/test splits are limited by dataset size. | Use only as a secondary sanity check, not as the main thesis benchmark. |

## Recommendation

For the main Week 3 benchmark, analytic thresholded functions are better aligned
with this thesis than ordinary classification datasets. They give deterministic
oracle labels, exact test labels, reproducible pools, and a clear thresholded
continuous function. Public classification datasets can still be useful for
software sanity checks, but they do not provide the exact deterministic
level-set boundary that the thesis setting needs.

I recommend starting with the controlled synthetic 4D boundary function. It is a
first 4D synthetic benchmark, not a final thesis direction. It lets us keep the
Week 2 comparison fair while introducing four inputs, a larger pool, a larger
test set, and an explicitly known threshold-label oracle.
