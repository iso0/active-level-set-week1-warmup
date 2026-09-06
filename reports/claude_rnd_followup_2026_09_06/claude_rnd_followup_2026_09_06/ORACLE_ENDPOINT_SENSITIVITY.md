# ORACLE_ENDPOINT_SENSITIVITY — is the oracle gain q20-specific?

The q20-greedy test-label oracle paths of the previous package (8 runs; queries B16–B39 chosen with held-out labels to maximise held-out q20 accuracy, margin thereafter) were re-evaluated on every endpoint against the committed M3-margin paths on the same runs (`results/oracle_endpoint_sensitivity.csv`). The oracle was optimised for q20 accuracy only; its gains on the other endpoints are therefore *transfer* gains, a conservative measure of breadth.

| Endpoint | oracle AULC 16–40 | M3-margin | Δ [95% bootstrap over 8 runs] | Δ over 16–80 |
|---|---:|---:|---|---:|
| q20 accuracy (the oracle's objective) | 0.925 | 0.830 | +0.095 [+0.078, +0.114] | +0.045 |
| q20 balanced accuracy | 0.921 | 0.822 | +0.099 [+0.079, +0.120] | +0.043 |
| q20 KH recall | 0.903 | 0.784 | +0.119 [+0.047, +0.196] | +0.040 |
| q30 accuracy | 0.943 | 0.874 | +0.069 [+0.050, +0.087] | +0.031 |
| q30 balanced accuracy | 0.932 | 0.859 | +0.074 [+0.059, +0.090] | +0.030 |
| q30 KH recall | 0.908 | 0.811 | +0.097 [+0.039, +0.156] | +0.032 |
| full held-out accuracy (81 rows) | 0.981 | 0.960 | +0.021 [+0.015, +0.026] | +0.009 |
| full balanced accuracy | 0.967 | 0.936 | +0.032 [+0.015, +0.048] | +0.012 |
| full KH recall | 0.946 | 0.897 | +0.049 [+0.005, +0.091] | +0.015 |

Checkpoints: full-fold accuracy 0.983 (B24) and 0.985 (B40) on the oracle path versus 0.955 / 0.968 for margin and 0.968 for the full-324-label fit; full-fold balanced accuracy 0.974 / 0.978 vs 0.933 / 0.951; q20 KH recall 0.926 / 0.951 vs 0.776 / 0.833. Conduction recall does not fall (full accuracy rises while KH recall rises), so the gain is not class-directional.

## Classification

The gain is **broad in sign and class-neutral, but concentrated in magnitude on the near-boundary subsets**: +0.095 on q20, +0.069 on q30, +0.021 on the full fold. The full-fold gain is small in absolute terms only because 60–70% of held-out rows are far from the boundary and already correct under any policy; on the rows where predictions can change, the q20 oracle improves everything it touches, including the full-fold balanced accuracy by 0.03 and KH recall by 0.05–0.12. This is neither pure endpoint-specific overfitting (case B) nor a class trade-off (case C); it is case A **restricted to the boundary region** — a genuine training-subset sensitivity of M3's boundary, measured on 81-row folds that the oracle did not use except through q20 accuracy.

Two qualifications. (i) The oracle optimises q20 accuracy of the *same* held-out fold on which all endpoints are evaluated; q30 and full-fold gains are on rows partly overlapping q20 (q20 ⊂ q30 ⊂ full), so they are not independent confirmations, only evidence that the gain is not confined to the 17 q20 rows. (ii) The oracle's full-fold accuracy (0.983) exceeds the 324-label fit (0.968): the training-subset sensitivity holds for the whole fold, not only for the near-boundary metric.

Decision for the brief's §5: **broad model phenomenon at the boundary (A), with magnitude proportional to boundary proximity**; a model-side pivot is therefore *not excluded* by endpoint specificity — it is excluded or admitted by ORACLE_MECHANISM_AUDIT (attainability) and ROBUST_LOCAL_MODEL_RND (whether any label-blind model captures it).
