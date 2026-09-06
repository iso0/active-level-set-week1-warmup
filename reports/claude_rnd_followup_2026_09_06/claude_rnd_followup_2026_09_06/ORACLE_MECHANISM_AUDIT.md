# ORACLE_MECHANISM_AUDIT — is the oracle's headroom identifiable before querying?

Development data only (old 405 cases). Scripts: `code/oracle_values.py`, `code/oracle_analysis.py`. Tables: `results/oracle_values.csv.gz` (candidate-level), `results/oracle_feature_associations.csv`, `results/oracle_feature_partial_margin.csv`, `results/oracle_predictor_crossfit.csv`, `results/oracle_composition.csv`; console log `results/oracle_analysis.txt`.

## 1. The candidate-level oracle value

States: the committed Phase 1.14 M3-margin (P1) prefixes at B ∈ {16, 24, 32, 40} on 20 outer runs (one fold per repeat) — 80 states. Eligible candidates: unrevealed training rows in the physical band or with current M3 p ∈ (0.02, 0.98) (109–114 per state; 8,987 candidate-state rows). For each eligible x,

  V_oracle(x) = q20 accuracy of M3 refit on (revealed ∪ {x, true label}) − q20 accuracy of the current M3,

plus the same difference for q20 BA, q20 KH recall, q30 accuracy, full-fold accuracy and BA. This uses held-out labels and the candidate's true label; it is evaluation-only.

Distribution of V (q20 accuracy): 10.5% of candidate-states have V > 0, 6.8% have V < 0, 82.7% have V = 0 (one label rarely changes a 17-row decision set); per state the best candidate gains on average +0.062 (B16: +0.077, B24: +0.068, B32: +0.056, B40: +0.047), i.e. one to 1.3 held-out decisions; 72% of states contain at least one candidate with V > 0. The margin pick's V averages −0.005 (B16 −0.012, B24 +0.001, B32 −0.006, B40 0.000): **the margin choice is on average neutral-to-slightly harmful for the immediate q20 outcome, while the best candidate is worth +1 decision.** Cumulated greedily this is the +0.095 AULC of the previous package's oracle.

## 2. Allowed pre-query features tested (all computable from inputs, revealed labels, revealed-label models, label-free geometry)

Physics/geometry: log h; signed and absolute distance to the current Stage-1 threshold; physical-band membership; log VX, log LS, ST; distance to the nearest revealed row / revealed KH / revealed C; pool density (r = 0.5 sd); revealed density (r = 0.5, 1.0); configuration flag. Revealed-label locality: KH fraction, label entropy and physics-order conflict among the 5 nearest revealed rows. Model uncertainty: M3 p, probability margin, latent mean, |latent mean|, latent variance, π-margin; H probability; |M3 − H|; |M3 − 4-D logistic on revealed data|; |M3 − frozen T|; T threshold sd; T-TV leverage; T-XSUR (S2) score and expected flip count. (Campaign identity as a raw label was not included as a predictor because it is a fixed partition label that a new single-campaign pool cannot use; the configuration flag was.)

## 3. Association with V (within state, then aggregated over states and repeat blocks)

| Feature | median within-state Spearman with V | block mean ± sd | states with ρ > 0 | AUROC for the oracle top-10% | top-10% enrichment |
|---|---:|---:|---:|---:|---:|
| \|M3 − T\| disagreement | 0.112 | 0.037 ± 0.131 | 61% | 0.655 | 2.2 |
| revealed density (r=1) | 0.046 | 0.030 ± 0.054 | 58% | 0.556 | 1.4 |
| \|M3 − 4-D logistic\| | 0.028 | 0.044 ± 0.118 | 61% | 0.591 | 1.7 |
| T-TV leverage | 0.023 | 0.016 ± 0.119 | 54% | 0.653 | 1.5 |
| M3 probability margin | 0.013 | −0.006 ± 0.170 | 54% | 0.656 | 4.8 |
| π-margin | 0.018 | 0.008 ± 0.161 | 57% | 0.683 | 5.5 |
| physical band | −0.004 | −0.009 ± 0.176 | 47% | 0.599 | 7.2 |
| T-XSUR expected flips | −0.059 | −0.032 ± 0.119 | 42% | 0.369 | 0.2 |
| \|distance to threshold\| | −0.086 | −0.049 ± 0.143 | 34% | 0.286 | 0.1 |
| all other features | \|ρ\| ≤ 0.07 | | 35–58% | 0.42–0.52 | 0.4–1.1 |

Controlling for margin (within-state residuals) leaves no feature with |partial ρ| > 0.09 except the configuration flag (−0.23, i.e. alternative-configuration candidates are worth *less*) and revealed density at r = 0.5 (−0.13).

Reading: margin-type quantities are the only features that *enrich* the oracle's top decile (AUROC 0.65–0.68, enrichment 4.8–7.2 for margin/π-margin/band — the oracle's best candidates are near the boundary), but they carry **no rank information about V** (ρ ≈ 0, block sd 0.17): near-boundary candidates have both the largest gains and the largest losses. Nothing else has |ρ| > 0.11 in median or > 0.05 in block mean, and no feature is positive in more than 61% of states.

## 4. Cross-fitted predictor of V (leave-whole-repeat-block-out, 20 blocks)

| Model (31 allowed features) | out-of-block R² | median within-state ρ(pred, V) | block mean ± sd | states with ρ > 0 | AUROC top-10% | enrichment top-10% | mean V of predicted top-1 | mean V of margin top-1 | mean best V |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ridge (CV α) | −0.089 | −0.018 | −0.001 ± 0.130 | 47% | 0.515 | 0.95 | +0.010 | −0.005 | +0.067 |
| Gradient boosting (150 stumps of depth 2) | −0.071 | −0.049 | −0.021 ± 0.128 | 43% | 0.470 | 1.78 | +0.004 | −0.005 | +0.067 |

Both predictors are at chance out of block (R² < 0, ρ ≈ 0, AUROC ≈ 0.5). The GBM's top-decile "enrichment" of 1.8 is not accompanied by any rank skill (AUROC 0.47) and its predicted-top-1 candidate is worth +0.004, against +0.067 for the oracle's best and −0.005 for margin's choice.

**Gate (brief §4.3: out-of-block Spearman ≥ 0.30 AND ≥ 2× top-10% enrichment): FAILED on both counts.** Classification: **the +0.095 oracle headroom is UNATTAINABLE BY ANY CURRENTLY IDENTIFIED LABEL-BLIND SIGNAL.** This is a statement about the 31 features and two model families tested, not a proof of impossibility.

## 5. What the oracle selects (composition; true labels used descriptively only)

| Set | n | KH | persistent exception | late-onset KH | transient KH | in band | main cfg | new-data partition | mean margin | mean V |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all eligible | 8,987 | 30% | 5.1% | 11% | 16% | 44% | 91% | 53% | 0.23 | +0.002 |
| oracle top-10% (V > 0 and top decile) | 908 | 42% | 14% | 17% | 16% | 52% | 92% | 52% | 0.33 | +0.066 |
| margin top-1 per state | 177 | 70% | 14% | 31% | 45% | 98% | 95% | 71% | 0.33 | −0.002 |

The oracle's valuable candidates are moderately enriched in KH (42% vs 30%) and in persistent exceptions (14% vs 5%) but are **not** predominantly exceptions (86% are ordinary rows), not predominantly in the band (52%), and not more clustered in pool density than the eligible average (1.78 vs 1.95 neighbours within 0.5 sd) or in local revealed-label conflict (0.37 vs 0.37). Margin's own picks are *more* KH-rich (70%), more exception-rich in relative terms of late/transient KH, and almost always in band — yet worth nothing on average. Mean V by true label: C candidates +0.0004, KH candidates +0.0067: revealing a KH label helps more often than a C label, but a KH label is not identifiable before querying beyond what M3's p already says (and p has ρ ≈ −0.06 with V).

Answer to the brief's question: the oracle-selected points are high-value **because the oracle directly optimises the particular held-out q20 decisions** — it picks, at each step, the one label whose effect on the M3 fit flips the specific 1–2 held-out near-boundary rows that are currently wrong. Neither "cluster revelation" nor "unusual label" describes them: their composition is close to the eligible pool's, and revealing the same rows in a different order (or one step later) changes their value, which is why V has no stable pre-query correlates.

## 6. Consequences

- The +0.095 headroom is real as a *training-subset sensitivity* of M3 (ORACLE_ENDPOINT_SENSITIVITY confirms it on q30 and full-fold metrics too), but it is not accessible to a label-blind acquisition using any of the tested signals. No new acquisition candidate is derived from it (brief §9, Case A is closed).
- The previous package's sentence "adding margin-selected labels *lowers* q20 ... queried exceptions poison neighbours" is re-examined in NESTED_SUBSET_LABEL_HARM_AUDIT.md; the candidate-level data already show that a single margin-selected label lowers q20 in 6.8% of candidate-states and raises it in 10.5%, with a mean effect of −0.005 for the margin pick — a small, symmetric-looking selection variance, not a systematic harm.
