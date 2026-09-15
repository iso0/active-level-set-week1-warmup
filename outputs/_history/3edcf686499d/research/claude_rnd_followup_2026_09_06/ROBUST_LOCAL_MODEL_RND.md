# ROBUST_LOCAL_MODEL_RND — the robust-likelihood pivot, tested adversarially

## 1. Exact definition of M3R

M3R keeps M3's Stage 1 (near-unregularised logistic on standardised log h of the revealed rows, frozen) and Stage 2 (ARD Matérn-3/2 discrepancy on standardised (P, VX, LS, ST), Laplace) and replaces the Stage-2 likelihood by the symmetric contamination mixture

  p(y = 1 | f) = ε + (1 − 2ε)·σ(f),  ε ∈ {0.02, 0.05, 0.10},

the Kim & Ghahramani (2008) "outlier-robust GPC" form with a logistic link (their original uses a Heaviside link). It is a **global, symmetric label-flip contamination**: every revealed label, wherever it sits, is a priori inconsistent with the smooth latent with probability ε; the likelihood of a label that the latent strongly contradicts is bounded below by ε instead of going to zero, so such a label can no longer pull the latent by more than a bounded amount. For a deterministic simulator ε is not aleatoric noise; the only defensible readings are (a) model discrepancy that the smooth latent cannot represent, (b) annotation/provenance inconsistency (the old ledgers have undocumented annotators and label_1/label_2 disagreements), (c) plain robustification. It is not local: a genuine rare KH surrounded by C receives the same discount as an annotation error.

Two fitting modes: `fixedhyper` (kernel hyperparameters copied from the M3 fit at the same state; only the likelihood changes, so the comparison isolates the likelihood; 100 runs, all budgets, A0 and P1 paths, the 8 oracle paths, and full-324 fits) and `ml2` (hyperparameters re-optimised under the robust likelihood; 20 runs, budgets 16/24/32/40/60/80, P1 paths). ε = 0 reproduces M3's decisions exactly (agreement 1.000). Scripts `code/m3r_tests.py`, `code/rnd/m3r.py`; tables `results/m3r_fixedhyper.csv.gz`, `results/m3r_ml2.csv.gz`; logs `results/m3r_fixedhyper_analysis.txt`, `results/m3r_ml2_analysis.txt`.

## 2. Results

**Ordinary paths (A0 and M3-margin P1; 100 runs; fixed hyperparameters).** Decisions agree with M3 in ≥ 99.8% of held-out predictions at every ε and budget. AULC 16–40 differences versus ε = 0 are within ±0.0003 on q20, q30 and full accuracy; over 16–80 they are slightly negative and interval-excluding-zero at ε ≥ 0.05 (q20 −0.0007 [−0.0013, −0.0001] on A0, KH recall −0.0014 … −0.0030). Brier score worsens monotonically with ε (+0.003 at ε = 0.05, +0.010 at ε = 0.10). Accuracy on the persistent-exception rows does not improve (0.24 → 0.23 at B24; 0.15 → 0.13 at B80); ordinary-row accuracy is unchanged.

**Oracle paths (8 runs).** Robustification *erodes* the oracle's gain: q20 AULC 16–40 −0.009 [−0.015, −0.004] at ε = 0.02, −0.016 [−0.025, −0.006] at ε = 0.05, −0.023 [−0.036, −0.010] at ε = 0.10; q20 KH recall −0.026 / −0.043 / −0.062; exception-row accuracy at B24 falls from 0.41 to 0.28 (ε = 0.05) and 0.18 (ε = 0.10). The labels the oracle exploits are exactly the rare KH rows that the symmetric contamination discounts. The adversarial concern of the brief is confirmed.

**Full 324-label fits (100 runs).** q20 0.8635 (ε=0) → 0.8641 (0.02) → 0.8612 (0.05) → 0.8571 (0.10); exception accuracy 0.141 → 0.136 → 0.126 → 0.097; KH recall 0.739 → 0.739 → 0.731 → 0.720.

**Re-optimised hyperparameters (ml2, 20 runs).** ε = 0.05 versus 0: q20 −0.006 (B24), −0.003 (B32, B40, B80), 0 (B16, B60); KH recall −0.010 … −0.013; Brier worse at every budget. The fitted residual sd is *smaller* under the robust likelihood (0.50 vs 0.69 at B24; 0.74 vs 0.86 at B32): the contamination term absorbs what the discrepancy would otherwise explain, making the model less flexible where flexibility was useful.

**Nested label-blind sequences (NESTED_SUBSET_LABEL_HARM_AUDIT).** M3R(0.05) halves the late decline of the band-first sequence (+0.008 vs +0.016 for n=100 vs 324) but does not raise any peak and does not change the early curve.

## 3. Decision

| Criterion (brief §7.2 / §9 Case B) | Result |
|---|---|
| q20 AULC 16–40 improves by ≥ +0.010 with lower bound > 0 | no: ±0.0003 (fixed), −0.003 … −0.006 (ml2) |
| q30 does not materially deteriorate | satisfied, but no gain |
| q20 KH recall does not deteriorate by > 0.02 | satisfied on ordinary paths; violated on oracle paths (−0.026 … −0.062) |
| gain not confined to test-leaky paths | there is no gain anywhere; the only material effect is *loss* on the test-leaky paths |
| prevents ordinary labels from undoing useful local information without erasing true rare KH | no: it erases rare KH (exception accuracy falls) and does not prevent the label-blind late decline |

**M3R: KILL.** The symmetric contamination likelihood does what the brief feared: it downweights genuine rare keyhole cases together with inconsistent labels, removes the very information the oracle exploits, and gives nothing on label-blind paths. The previous package's recommendation ("a likelihood that discounts locally conflicting labels is the lever with real headroom") is **WRONG** as stated for symmetric contamination.

## 4. The one permitted local/nonstationary alternative — not developed, with reasons

Brief §7.3 permits one local alternative *only if the exception-clustering test supports local structure*. EXCEPTION_CLUSTERING_AUDIT finds no within-campaign geometric clustering for the exception set (p = 0.14–0.59 after conditioning on class × partition × configuration; T2 enrichment 1.3), a marginal residual for the 7 late-onset KH driven by 3 alternative-configuration rows, and none for transient KH, depth-marginal C or the rest. The clustering that exists is campaign/configuration composition. A campaign-aware discrepancy (source-specific offset in the latent; the multi-source GP analogue) would fit the old pool but is inapplicable to a single-campaign new pool and to the acquisition question, and a treed/nonstationary GPC (Broderick & Gramacy 2011; Paciorek & Schervish 2004) would be answering a question the data do not pose. ORACLE_MECHANISM_AUDIT adds that the oracle's valuable candidates are 86% ordinary rows with pool-average local density and conflict, so there is no local target for such a model to capture. **No local/nonstationary alternative is built; the line is CLOSED on the old data.**

## 5. Safe wording for the thesis

"A symmetric label-contamination likelihood (Kim & Ghahramani 2008 form) does not improve M3 on the melt-pool benchmark at any budget and reduces recall of rare keyhole cases in exactly the training subsets where those cases carry information; the exceptions that limit the near-boundary endpoint are campaign/configuration-structured, not locally clustered, so neither robust nor local likelihoods address them." This is a negative, benchmark-specific result with a mechanism; it is not a general claim about robust GPC.
