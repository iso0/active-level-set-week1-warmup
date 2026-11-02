# Scientific figure and numerical replay review

21 October 2026, approximately 06:21–06:27 UTC. Reviewed visually by the
assistant through the local image viewer. This is not a claim that the owner
or another human reviewer inspected the package. Twelve original PNG figures
and three corrected derived PNGs were opened and inspected. PDF counterparts
were generated from the same plotting objects; no separate PDF rendering review
is claimed. The byte hashes are in VISUAL_REVIEW.json.

| Figure | Inspection and interpretation |
|---|---|
| all_family_learning_curves | Eleven families present and readable. Clear learned-ARD advantage in several smooth/axis-aligned families, essentially chance behavior in rotated family, and harm in corrupted-monitor family. The null control remains zero. Curves are descriptive, completion conditional, with uncertainty in paired tables. |
| primary_mechanism_contrasts | Original label replacement was misleading (“Conditional island Global error”). Superseded for reading by figures/reviewed/primary_mechanism_contrasts. Corrected plot separates conditional island error, marks degenerate coordinates and missing-outcome limitations, and does not interpret interaction sign as benefit. All six numerical estimates/intervals are unchanged. |
| target_query_compute_cost | Values agree with the source table. Original plot's panel scope was not prominent. Use figures/reviewed/target_query_compute_cost, explicitly B32-to-B48 and completion conditional. Weighted attainment fractions differ from pooled raw counts. No arm meets 80% overall attainment. |
| equal_compute_readouts | Readable. This is the **common-prefix** panel, using available predictions; paired-common-available tables, not these marginal curves, support comparisons. Lower CPU caps give different available budgets. No extrapolation after B48. |
| end_to_end_first_hit | Original plot insufficiently emphasized the 15/16 completed existing/h2 small-island denominator. Use figures/reviewed/end_to_end_first_hit with per-line n and explicit failure note. Complete no-hit and no-pool-candidate worlds stay in denominators. These are not survival estimates for interrupted paths. All eight learned arms, including ARD/h1, remain in FINAL_REVIEW_FACTS.json even though the registered figure displays five. |
| slice_smooth | Same B32 observations give different prediction sharpness; ARD is visibly closer in this example. B48 paths differ. A single slice is illustrative, not a full-domain performance estimate. |
| slice_coordinate | Learned ARD resolves this coordinate-aligned periodic structure with sharp contours; existing/local mixtures nearly overlap. No inference to rotations. |
| slice_rotated | Predicted contours fail to follow the diagonal latent bands. Apparent vertical detail is not boundary recovery. Both representations and learned axis-ARD can fail. |
| slice_local_scale | ARD captures broad structure but misses some local oscillations; the local bank does not visibly resolve those in this fixed example. |
| slice_island_small | This prespecified x2=x3=0.5 plane does not display the 4D island. It must not be presented as a no-island world or successful island recovery. No truth-selected alternative slice was substituted. |
| slice_island_large | The latent island is visible as a dotted contour; most of it remains predicted negative. A small positive patch is not recovery of the full region. |
| slice_corrupt_correlated | No true latent boundary on the displayed plane. Some paid positive points are projected from elsewhere in 4D; they do not contradict the slice. Greater prediction sharpness alone does not certify physical truth. |

All seven geometric figures use the first frozen world of the named family and
the fixed x2=x3=0.5 plane. Paid points and path lines are 4D projections, explicitly
labelled as such. All 84 reconstruction metric comparisons were exactly zero
against cached outputs; this is reproducibility, not external validation.

The 24 registered query replays were read numerically, including stored scores,
selected IDs, one-step winners, higher-order rankings, ties, integration mass and
effective-node diagnostics. Three h2 deterministic tie choices differed under
ordinary tie-breaking after refinement, each with zero score gap to the refined
maximum. No paid query or score tolerance was changed. Maximum cached-to-refined
score differences were 5.36e-5 (h2) and 6.73e-5 (mixture h1). They do not prove
exact posterior planning; independent dense/toy checks remain separate.

The full path audit checked 99,256 immutable pre-query states and 4,093 completed
paths. Its only issues are the three preserved missing-result paths, whose
partial records are independently captured. They are not silently excluded from
the completion status. Figures/reviewed contains presentation corrections only;
the original source, figures and frozen finishing receipt are preserved.
