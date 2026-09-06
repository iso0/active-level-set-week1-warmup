# EXCEPTION_CLUSTERING_AUDIT — are the persistent exceptions locally clustered after conditioning on campaign and class?

Data: the 13 rows misclassified by full-label M3 in ≥ 50% of the folds in which they are held out (previous package, `results/diag_fulltrain_pointwise.csv`). Groups: late-onset KH (Conduction → Keyhole sequence; 7 of the 13, of which 3 are the alternative-configuration KH), transient KH (3), alternative-configuration KH (3; subset of late-onset), depth-marginal C (|D − 112 µm| < 15 µm; 2), other (1 C at log h 20.84 + 1 persistent KH). Script: `code/clustering_test.py`; table: `results/exception_clustering_tests.csv`.

Statistics (each computed in three metrics: standardised (log P, log VX, log LS, ST); standardised (log h, log VX, log LS, ST); log h alone): T1 = mean distance from each exception to the nearest other exception in the group; T2 = mean number of group members among each member's 10 nearest neighbours in the whole pool. Null distributions: 3,000 draws of |group| rows matched on (i) nothing, (ii) class, (iii) class × campaign partition, (iv) class × partition × configuration. p-values are one-sided (smaller T1 / larger T2 than the null).

## Results (standardised log-input metric)

| Group | n | null | T1 obs / null mean | p(T1 smaller) | T2 obs / null mean | p(T2 larger) | T2 enrichment |
|---|---:|---|---|---:|---|---:|---:|
| all 13 | 13 | unconditioned | 1.09 / 1.30 | 0.117 | 1.08 / 0.30 | **0.003** | 3.6 |
| | | class | 1.09 / 1.19 | 0.268 | 1.08 / 0.75 | 0.178 | 1.4 |
| | | class × partition | 1.09 / 1.14 | 0.385 | 1.08 / 0.61 | 0.051 | 1.8 |
| | | class × partition × cfg | 1.09 / 1.06 | 0.591 | 1.08 / 0.82 | 0.139 | 1.3 |
| late-onset KH | 7 | unconditioned | 0.63 / 1.60 | **<0.001** | 1.29 / 0.15 | **<0.001** | 8.5 |
| | | class | 0.63 / 1.24 | **0.006** | 1.29 / 0.61 | 0.066 | 2.1 |
| | | class × partition | 0.63 / 1.10 | **0.001** | 1.29 / 0.63 | **0.032** | 2.0 |
| | | class × partition × cfg | 0.63 / 0.93 | **0.013** | 1.29 / 1.05 | 0.167 | 1.2 |
| alt-configuration KH | 3 | class × partition | 0.33 / 1.69 | **0.014** | 2.0 / 0.26 | **0.020** | 7.7 |
| | | class × partition × cfg | 0.33 / 0.33 | 0.671 | 2.0 / 2.0 | 1.000 | 1.0 |
| transient KH | 3 | any | 1.64 / 1.7–2.2 | 0.19–0.50 | 0 / 0.05–0.25 | 1.0 | 0 |
| depth-marginal C | 2 | any | 2.15 / 2.2–2.6 | 0.32–0.48 | 0 | 1.0 | 0 |

The (log h, tangent) and log-h-only metrics give the same pattern (all-13: p(T2) = 0.008 unconditioned, 0.10–0.26 conditioned).

## Reading

1. The exception set **as a whole** is clustered only relative to an unconditioned null (p = 0.003). Conditioning on class removes most of it (p = 0.18), because KH rows are rare and therefore mutually close; conditioning on class × campaign leaves a marginal signal (p = 0.05); conditioning additionally on configuration leaves none (p = 0.14, enrichment 1.3).
2. **Late-onset KH** is the only subgroup with residual clustering after conditioning on class and campaign (T1 p = 0.001, T2 p = 0.03). After also conditioning on configuration it is marginal (T1 p = 0.013, T2 p = 0.17, enrichment 1.2). Three of its seven members are the alternative-configuration KH, whose clustering is entirely explained by configuration (p = 0.67 once configuration is matched). The four remaining late-onset KH in the main configuration are at log h 20.36–20.76 with VX 0.48–0.58 m/s; with n = 4 a within-configuration test has no power.
3. Transient KH, depth-marginal C and the residual rows show **no** clustering under any null (T2 = 0: none of them has another exception among its ten nearest neighbours).

## What may and may not be claimed

- May be claimed: the exceptions are **campaign- and configuration-structured** (they concentrate in the old-data partitions and in the 27-row alternative configuration; all nine late-onset KH of the population are in the old partitions); within a campaign, at most the late-onset KH show weak residual proximity (p ≈ 0.01–0.03 for one statistic, not the other).
- May not be claimed: "a local geometric exception process" (clusters of exceptions inside a conduction region) as a general feature of the boundary; the causal sentence in the previous package ("the exceptions are locally clustered so that a training set containing the right cluster members makes M3 predict them") is **TOO STRONG** — the oracle's gains come predominantly through campaign/configuration composition and through individual near-transition rows (ORACLE_MECHANISM_AUDIT §4), not through a within-campaign geometric cluster.
- Consequence for §7.3 of the brief: a local/nonstationary model is not justified by this test; a campaign-aware discrepancy would be justified on the old pool but is unusable for a single-campaign new pool. No local alternative is developed.
