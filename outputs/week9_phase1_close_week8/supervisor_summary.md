# Week 9 Phase 1 — supervisor-ready messages

1. **The remaining question was censoring, not method selection.** Frozen Week 8.5 already confirmed a positive Fold-B1-q20 AULC contrast of +0.0373; Phase 1 only continued the same Margin and Random trajectories.

2. **The H=320 extension is explicitly post-hoc.** It does not rewrite the H=160 protocol or upgrade the old Week 8.5 QUALIFY ledger.

3. **Persistent target attainment at H=320:** Binary Margin reached the persistent 0.80 Fold-B1-q20 target in 91/100 outer runs; Random reached it in 2727/3000 continuations (90.9%), leaving 273 unresolved.

4. **Restricted H=320 burden:** Margin averaged 53.470 queries and matched Random 78.466; the descriptive difference is 24.996 queries and the ratio is 1.467×.

5. **Safe query-saving statement:** An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320. The naive argument that every unresolved H=320 path has `Q>320` is false under the frozen start-of-three definition.

6. **AULC and terminal accuracy answer different questions.** The terminal Fold-B1-q20 accuracy comparison has positive point estimates at 40, 80, 160, and 320, but the H320 contrast is practically zero and its design-conditional 95% interval [-0.0011, +0.0023] crosses zero. The frozen AULC contrast remains positive and measures earlier learning speed; balanced accuracy and Keyhole recall are separate descriptive endpoints, and full81, q30, and q20 results remain separated in `terminal_metric_summary.csv`.

7. **PCA describes sampled-input variance, not Keyhole importance.** After standardizing `P`, `VX`, `LS`, and `ST`, PC1 is an LS-versus-P contrast, PC2 is mainly sampled ST variation, and PC3 is mainly VX variation. PC1+PC2 retain 58.4%, so the 2D view omits 41.6% including most VX variation. The single RobustScaler sensitivity check preserves the ST/PC2 and VX/PC3 pattern but changes PC1 materially, so the interpretation is scaling-aware. In the representative, label-informed visualization fold, mean 10-neighbour opposite-label mixing is 0.218 for q20 versus 0.043 outside q30 (higher); Margin queries 17–40 average 0.412 versus 0.017 for queries 161–320 (higher); this is descriptive 2D association, not proof of a physical boundary. Labels do not enter PCA fitting; the representative-fold choice is explicitly label-informed and visualization-only. PCA coordinates and held-out or unrevealed labels did not enter acquisition, while labels of already queried rows trained later GPC fits.

8. **Main limitations:** fixed 405-simulation population, manual labels, 17-row q20 subsets, post-hoc H=320 choice, unobservable persistent-Q tail near the final horizon, design-conditional bootstrap uncertainty, and PCA that optimizes input variance rather than class separation. The secondary GPC slice fixes PC3=PC4=0 and is masked only by the projected 2D hull—not verified support on the observed 4D manifold or a physical boundary.

<!-- discriminative-update:start -->

## Label-aware discriminative upgrade

1. **Individual variables:** Power is the strongest positive univariate discriminator (direction-adjusted AUC 0.931); spot radius is strongly negative (0.897); velocity is weaker and negative (0.614); ST is near chance (0.528) within the sampled 300–400 K range.
2. **Four-input model:** The leak-free repeated-CV main-effects logistic model reaches ROC-AUC 0.990. Adding P×VX gives 0.994; the incremental predictive gain is +0.0034, so interaction claims remain proportional to the evidence.
3. **Physics-inspired score:** The fixed process-parameter score `h = P / sqrt(VX*LS^3)` reaches ROC-AUC 0.990 after logistic calibration (keyhole_process_score_h__log). Raw and log forms rank cases almost identically; log(h) is preferred because calibration scores are better. It is proportional to the process-parameter part of published Keyhole-number scaling, but is not dimensionless without material/thermal factors and is not a zero-parameter classifier.
4. **Operational geometry:** The best two physical planes are P–LS and P–VX. Their dashed contours are fitted transition estimates, not true physical boundaries.
5. **Why Margin helps:** In exact saved query orders, queries 17–40 are closer than the initial design by 0.935 fold-standardized B1 units and closer than the H160-unqueried pool by 12.591 absolute M3-logit units. Both findings hold in 100/100 outer runs and 20/20 repeat blocks. These post-hoc references never entered acquisition.

<!-- discriminative-update:end -->
