# Week 9 Phase 1 — supervisor-ready messages

1. **The remaining question was censoring, not method selection.** Frozen Week 8.5 already confirmed a positive Fold-B1-q20 AULC contrast of +0.0373; Phase 1 only continued the same Margin and Random trajectories.

2. **The H=320 extension is explicitly post-hoc.** It does not rewrite the H=160 protocol or upgrade the old Week 8.5 QUALIFY ledger.

3. **Persistent target attainment at H=320:** Binary Margin reached the persistent 0.80 Fold-B1-q20 target in 91/100 outer runs; Random reached it in 2727/3000 continuations (90.9%), leaving 273 unresolved.

4. **Restricted H=320 burden:** Margin averaged 53.470 queries and matched Random 78.466; the descriptive difference is 24.996 queries and the ratio is 1.467×.

5. **Safe query-saving statement:** An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320. The naive argument that every unresolved H=320 path has `Q>320` is false under the frozen start-of-three definition.

6. **AULC and terminal accuracy answer different questions.** The terminal Fold-B1-q20 accuracy comparison has positive point estimates at 40, 80, 160, and 320, but the H320 contrast is practically zero and its design-conditional 95% interval [-0.0011, +0.0023] crosses zero. The frozen AULC contrast remains positive and measures earlier learning speed; balanced accuracy and Keyhole recall are separate descriptive endpoints, and full81, q30, and q20 results remain separated in `terminal_metric_summary.csv`.

7. **PCA makes the 4D geometry explainable, not physically certain.** PC1+PC2 explain 58.4% of standardized feature variance; PC1 is dominated by LS and PC2 by ST. In the representative, label-informed visualization fold, mean 10-neighbour opposite-label mixing is 0.218 for q20 versus 0.043 outside q30 (higher); Margin queries 17–40 average 0.412 versus 0.079 for rows not queried by available horizon (higher). PCA fitting is label-free, but the representative-fold choice is explicitly label-informed and visualization-only.

8. **Main limitations:** fixed 405-simulation population, manual labels, 17-row q20 subsets, post-hoc H=320 choice, unobservable persistent-Q tail near the final horizon, design-conditional bootstrap uncertainty, and a PCA slice masked only by the projected 2D hull—not verified support on the observed 4D manifold or a physical boundary.
