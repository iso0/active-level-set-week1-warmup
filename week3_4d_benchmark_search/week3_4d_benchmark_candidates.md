# Week 3: 4D Benchmark Candidate Review

The Week 3 goal is to move the active level-set estimation plumbing from the
2D Branin example toward a setting closer to the laser-metal process-parameter
problem. The real application has four input variables, so the first useful
extension is a deterministic 4D benchmark with exact threshold labels.

The important correction for this iteration is that the main Week 3 benchmark
should be a known or named analytic benchmark, not a custom-made function. A
controlled synthetic boundary is still useful for controlled studies, but Ioan's
request was to find or select 4D datasets/benchmarks.

| Candidate | Dimension | Label generation | Why it is useful for active level-set estimation | Pros | Cons / caveats | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded 4D Ackley | 4 | Evaluate the named Ackley function on `[-5,5]^4`, then label points by whether the value is above a fixed percentile threshold. | Gives a deterministic 4D continuous oracle with exact labels and a nonlinear level set. | Known benchmark; deterministic; easy to evaluate in 4D; defensible as a named benchmark; keeps the expensive-oracle / threshold-label setting; produces useful 2D slices and projections. | Threshold choice affects class balance and difficulty; the full `[-32.768,32.768]^4` optimization domain would put many points on the outer plateau, so `[-5,5]^4` is more practical for this active-learning budget. | Best first Week 3 main benchmark. It is named, reproducible, 4D, and aligned with active level-set estimation after thresholding. |
| Thresholded 4D Rosenbrock | 4 | Evaluate the named Rosenbrock function and threshold its value. | Produces curved level sets around a narrow valley, giving a deterministic nonlinear binary problem. | Standard, smooth, deterministic, easy to compute. | The valley geometry is strongly optimization-flavored; thresholded classes can be imbalanced or dominated by the valley structure; may be less visually intuitive in 4D. | Good follow-up benchmark after Ackley, especially if Ioan wants a smoother non-oscillatory named function. |
| Thresholded 4D Rastrigin | 4 | Evaluate the named Rastrigin function and threshold its value. | Creates many repeated local structures, so acquisition rules must handle multiple disconnected boundary pieces. | Standard, deterministic, highly multimodal, easy to compute. | Very periodic and potentially too wiggly for the current GP-regression stand-in; failures may reflect model mismatch more than acquisition-rule quality. | Useful stress test, but not the cleanest first named 4D benchmark. |
| Thresholded 4D Styblinski-Tang | 4 | Evaluate the named Styblinski-Tang function and threshold its value. | Gives a deterministic 4D polynomial benchmark with multiple basins. | Standard, cheap to evaluate, reproducible, less periodic than Rastrigin. | Separable structure may underrepresent interactions between process parameters; threshold selection still matters. | Reasonable additional benchmark, but less familiar than Ackley/Rosenbrock for a first discussion. |
| Hartmann-style benchmark | 4 if adapted | Threshold a Hartmann-style continuous function after choosing a 4D variant or adaptation. | Hartmann functions are common nonlinear benchmark functions with localized basins. | Potentially useful if a well-defined 4D version is chosen and documented. | Standard Hartmann benchmarks are usually 3D or 6D, so a 4D version may require adaptation; this weakens the "named benchmark" argument unless the variant is carefully sourced. | Do not use as the first main Week 3 benchmark unless Ioan specifically wants Hartmann-style tests. |
| Controlled synthetic 4D boundary function | 4 | Define a smooth continuous function directly on `[0,1]^4`, then threshold it. | Lets us design the boundary difficulty and class balance for controlled studies. | Highly controllable; deterministic; exact labels; useful as an appendix or debugging benchmark. | Custom-made, so it is less defensible as the answer to "find/select 4D benchmarks"; should not be presented as the main Week 3 benchmark. | Keep as secondary / optional, not as the main result. |
| Public 4-feature classification datasets such as Iris | 4 | Use dataset class labels directly, or create a binary task from selected classes. | Can sanity-check code on a familiar four-feature table. | Familiar; tiny; easy to load. | Not an exact deterministic level-set oracle; no known continuous threshold function; labels are empirical class labels rather than simulator-style exact labels; pool/test sizes are limited. | Use only as a secondary sanity check, not as the thesis benchmark. |

## Recommendation

The main Week 3 benchmark should be thresholded 4D Ackley. It is a known
analytic benchmark, it can be evaluated exactly in four dimensions, and after
thresholding it gives deterministic labels and exact test labels. This is more
defensible for Ioan's request than using a custom-controlled boundary as the
main result.

Analytic thresholded functions remain better aligned with this thesis than
ordinary classification datasets because they provide an exact oracle and a
known continuous function. Public datasets can still be useful for software
sanity checks, but they do not provide the deterministic level-set boundary
needed for the main benchmark.

The previous controlled 4D boundary should stay as a secondary or appendix-style
experiment. It is useful for controlled studies, but the primary Week 3 story
should be the named thresholded-Ackley benchmark.
