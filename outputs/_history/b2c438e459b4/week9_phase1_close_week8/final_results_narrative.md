# Week 9 Phase 1 final results narrative

## Scientific status

This is a **post-hoc H=320 horizon-extension closing diagnostic**. The frozen Week 8.5 AULC result and decision ledger remain unchanged.

## Main result

At H=320, Binary Margin confirmed 91/100 persistent Fold-B1-q20 target crossings. Random confirmed 2727/3000 (90.90%). Restricted burdens were 53.470 and 78.466 queries, respectively.

## Query-saving interpretation

An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320.

The restricted H=320 difference is descriptive. The mathematical lower-bound analysis corrects the final-tail issue created by defining Q as the first, rather than the third, checkpoint of a persistent run.

## Terminal performance and PCA

Terminal full81/q30/q20 results are in `terminal_metric_summary.csv`; their Fold-B1-q20 comparison has positive point estimates at 40, 80, 160, and 320, but the H320 contrast is practically zero and its design-conditional 95% interval [-0.0011, +0.0023] crosses zero. The positive frozen AULC contrast separately measures earlier learning speed. Feature-only StandardScaler PCA is used only for interpretation: PC1 is an LS-versus-P contrast, PC2 is mainly sampled ST variation, and PC3 is mainly VX variation. PC1+PC2 explain 58.42% and omit 41.58% of standardized input variance. Robust scaling preserves the ST/PC2 and VX/PC3 pattern but changes PC1 materially, so no loading is interpreted as physical importance, causality, or supervised Keyhole importance.

## Scope

Claims concern this fixed 405-simulation manual-label benchmark plus split/acquisition randomness. They are not causal, prospective, universally transferable, or physical-boundary certainty claims.
