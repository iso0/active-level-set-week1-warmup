# Phase 1.5 validation report

Overall status: **PASS**

| Check | Status | Evidence |
|---|---|---|
| focused tests | PASS | ......                                                                   [100%] 6 passed in 14.72s |
| notebook execution | PASS | 6 code cells; errors=0 |
| figure count and hashes | PASS | figures=8; hashes recomputed |
| active information flow | PASS | {"B1_B2_B3_used": false, "full_pool_label_threshold_used": false, "hidden_pool_labels_used": false, "test_rows_used": false} |
| historical tracked outputs unchanged | PASS | no tracked diff |
| baseline reproduction | PASS | numerical tolerance gate |
| GPC fallbacks and bound diagnostics | PASS | fallbacks=0; bound hits disclosed in gpc_kernel_bound_diagnostics.csv |

The frozen Week 8.5 and existing Week 9 Phase 1 directories were read-only inputs. The original dirty checkout was not edited; this study ran in its own worktree and branch.

Scientific scope limits: fixed 405-run Ti-6Al-4V simulator population; repeated-split uncertainty rather than new-experiment uncertainty; no prospective, cross-alloy, causal, or manufacturing-safety validation.
