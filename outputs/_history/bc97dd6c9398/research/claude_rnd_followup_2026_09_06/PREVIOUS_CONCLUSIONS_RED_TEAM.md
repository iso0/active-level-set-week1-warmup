# PREVIOUS_CONCLUSIONS_RED_TEAM — audit of the previous package's statements

| Statement (previous package) | Verdict | Why |
|---|---|---|
| "0.8565 is the q20 ceiling" | **WRONG** as a ceiling; VALID as two other quantities (below) | The test-label oracle reaches q20 0.93–0.94 with 8–24 selected labels and the band-first label-blind sequence reaches 0.860 at n ≈ 100 versus 0.844 at n = 324 on the same 20 runs. 0.8565 bounds neither arbitrary subsets nor label-blind sequences; it is the all-label fit. |
| "13 exceptions explain the ceiling" | **VALID WITH QUALIFICATION** | Exact as an accounting identity for the *all-label fit's* q20 error (they occupy 14.1% of q20 slots; all-label q20 error 14.35%). Not valid as "13 rows are wrongly labelled/irreducible": on oracle-selected training subsets M3 classifies 41–47% of them correctly (vs 22–24% on margin paths), so roughly half are fit-dependent. See mechanism table below. |
| "more labels poison the model" | **TOO STRONG** as causal wording; the observable is VALID WITH QUALIFICATION | The post-oracle decline is mostly regression from an evaluation-selected optimum. A label-blind decline exists (band-first or margin sequences: q20 −0.016 [−0.031, −0.004], q30 −0.011, full −0.0045, KH recall −0.04 from n ≈ 100 to 324) but is produced by adding far-from-boundary rows late, not by local contradiction. "Poison" withdrawn. |
| "the exceptions are locally clustered, so the right cluster members make M3 predict them" | **TOO STRONG** | Clustering vanishes after conditioning on class × campaign × configuration (p = 0.14–0.59); only the late-onset KH keep a marginal residual (p = 0.013 / 0.17), three of which are the alternative-configuration rows. |
| "margin is information-optimal for deterministic simulators" (Prop. 1) | **TOO STRONG as a slogan; VALID for targets that determine Y_x** | I(Y_x; h) = H_b(π_x) for any h that determines Y_x (boundary, set, full labelling) — the generalised-binary-search fact. For the labels of *other* points the gain is H_b(π_x) − H(Y_x | Y_{−x}) ≤ H_b(π_x) and margin is not the maximiser. |
| "BALD/joint-entropy set criteria cannot beat margin; only non-entropic losses can differ" | **WRONG** as written | Information about the other labels (an entropic quantity) differs from margin; BALD with a soft link differs by E_g H_b(Φ(g_x)). |
| Prop. 2 leverage identity (zero one-step 0-1 risk reduction without a decision flip; flip contributions ≤ margin) | **VALID AS WRITTEN** for 0-1 / plug-in-set losses; **not new** (EVSI; MOCU Lemma) | Holds for weighted references, references excluding x, asymmetric costs (flip threshold moves). Does not extend to Brier, log-loss, threshold-variance or Hausdorff losses. |
| "exact Bayes-optimal transductive rule (XSUR)" | **TOO STRONG** as terminology; the result is VALID | Correct wording: coherent one-step reduction of the posterior 0-1 set risk under the Gaussian-Laplace posterior with stated observation semantics. The previous computation used latent-sign query semantics (S1); the corrected S2/S3 replays give the same negative result within 0.003. |
| "M3+TV is the only non-redundant, non-harmful candidate" | VALID AS WRITTEN | Re-confirmed; still not supported as a gain (prior-sensitive). |
| "a likelihood that discounts locally conflicting labels is the lever with real headroom" | **WRONG** for symmetric contamination | M3R gives nothing on label-blind paths and destroys the oracle's gain (−0.016 … −0.023 q20 AULC; KH recall −0.04 … −0.06). |

## 2.1 The concept rewritten

| Quantity | Value on the old pool | Meaning |
|---|---|---|
| All-training-label M3 performance (324 labels, 100 folds) | q20 0.8565 (0.844 on the 20-run subset) | what the incumbent gives with every label |
| Empirical convergence level of label-blind policies at B60–80 | 0.856–0.862 | where margin/T-margin/TV/SUR/XSUR all end |
| Best label-blind nested sequence (band-first, n ≈ 100; 20 runs) | 0.860 | above the all-label fit by 0.016 |
| Best over training subsets found (test-label greedy oracle, 8–24 labels) | 0.93–0.94 | selection sensitivity; not attainable label-blind (ORACLE_MECHANISM_AUDIT) |
| Best attainable by a label-blind acquisition | unknown; ≥ 0.862 (achieved), no tested signal reaches the oracle | the object the external test measures |
| Bayes / model-class ceiling | not computable from 405 labels; the oracle shows M3's class can represent 0.93+ on q20 with suitable subsets | — |

## 2.2 Mechanisms behind the 13 persistent exceptions (quantified)

| Mechanism | Evidence | Rows |
|---|---|---|
| Campaign/configuration structure | all 9 late-onset KH of the population lie in the two old partitions; 3/3 KH of the 27-row alternative configuration are exceptions; clustering of the exception set disappears once class × partition × configuration are matched | 7 (late-onset KH incl. 3 alt-cfg) |
| Observation-window sensitivity | late-onset episodes begin late in the scan; the "ever-KH" label depends on window length; 167/405 recordings end before 90% traversal (Phase 1.19A) | same 7; not separable from the campaign mechanism with n = 4 in the main configuration |
| Transient episodes (4–19 KH frames) | label defined by any KH frame; short episodes are boundary-marginal by construction | 3 |
| Depth-marginal conduction | max depth 105–112 µm at the 112 µm depth separator | 2 |
| Model misspecification / fit dependence | 41–47% of exceptions are classified correctly under oracle-selected subsets vs 22–24% under margin subsets | ≈ half of the 13, overlapping the groups above |
| Annotation ambiguity | annotator identity undocumented; label_1/label_2 disagreement flags exist; cannot be quantified from the pinned data | unknown |
| True fine-scale physics | not excluded; the within-configuration clustering test has no power at n = 4 | unknown |

## 2.3 The post-oracle decline, separated

| Explanation | Assessment |
|---|---|
| Overfitting of the oracle subset to the held-out q20 endpoint | **dominant**: the oracle optimises the same 17 rows it is scored on; its full-fold gain is smaller (+0.021) and any label added afterwards is expected to regress it |
| q20 discreteness / instability | contributes: one label changes q20 by 1/17; single margin labels have V = −0.06 in 6.8% and +0.06 in 10.5% of candidate-states |
| Genuine local conflict under the M3 likelihood | **not supported**: label-blind decline arises from far rows, not local contradiction; M3R does not remove it |
| Campaign-cluster effects | contributes to *which* rows are exceptions, not to the decline mechanism |
| Genuine global-fit degradation from far labels | **supported, small**: −0.016 q20 from n ≈ 100 to 324 under band-first/margin sequences |
