# ACQUISITION_CLOSURE — status of every acquisition line after the follow-up

## 1. Is there an attainable oracle signal? — NO IDENTIFIED SIGNAL

ORACLE_MECHANISM_AUDIT: 31 allowed pre-query features and two cross-fitted predictors (ridge, small GBM; leave-whole-repeat-block-out) predict the candidate-level oracle value with median within-state Spearman ≤ 0.11 (block means ≤ 0.05, sd 0.13), out-of-block R² < 0, AUROC for the oracle's top decile ≈ 0.5, and the predicted top candidate is worth +0.004–0.010 versus +0.067 for the true best and −0.005 for margin's pick. The §4.3 gate (ρ ≥ 0.30 and ≥ 2× top-10% enrichment) fails on both counts. **Case A (brief §9) is closed: no new acquisition is derived.** The +0.095 headroom is a training-subset sensitivity that only evaluation labels can steer.

## 2. Corrected XSUR (exact-semantics) replays

Under the corrected probabilistic semantics (S2: probit-observed query, latent-membership target; S3: probit-observed query, label target) the coherent one-step 0-1 set-risk criterion under the frozen T posterior remains dominated by margin: −0.028 [−0.041, −0.015] (S2) and −0.029 [−0.042, −0.016] (S3) on q20 AULC 16–40 versus the committed M3-margin path, versus −0.028 under the previous latent-sign semantics (S1). Selection behaviour is identical (half the early queries outside the band, p ≈ 0.36, 5–8% agreement with margin's top-1). **The negative result survives; the previous package's numbers stand within 0.003 and its terminology is corrected (MATHEMATICAL_SEMANTICS_AUDIT §3–4).**

## 3. Status of every acquisition line

| Line | Status | Basis |
|---|---|---|
| Probability margin (M3) | **KEEP** (incumbent, path A) | Week 8.5 vs Random; information-optimal for boundary-determining targets with noiseless labels (P1-C); no tested rule beats it on old data |
| M3 + TV (threshold-variance reduction under the frozen T posterior) | **EXTERNAL-TEST ONLY** (path C) | only non-redundant, non-harmful candidate; +0.0058 [+0.0002, +0.0117] vs same-posterior margin, +0.0025 [−0.003, +0.008] vs incumbent, prior-sensitive; not supported as a gain |
| T-margin (path B′) | **EXTERNAL-TEST ONLY** as control | isolates the leverage term |
| Random (path D) | KEEP as baseline | — |
| Moment-matched GlobalSUR-π (eq. 8) | **CLOSED** | non-coherent (credits variance shrinkage without flips); −0.026 |
| Coherent 0-1 set-risk reduction XSUR, semantics S1/S2/S3, wide and tight priors | **CLOSED** | −0.011 … −0.029 in all forms; mechanism: model-expected flips in uncalibrated regions |
| Oracle-value-guided acquisition (any feature-based proxy of V_oracle) | **CLOSED** | no pre-query signal (§1) |
| Robust-likelihood-driven acquisition (M3R + margin) | **CLOSED** | M3R killed (ROBUST_LOCAL_MODEL_RND) |
| Local/nonstationary/campaign-aware model + margin | **CLOSED** on the old data | no within-campaign local structure to model; campaign effects unusable on a single-campaign pool |
| Auxiliary-output (depth) acquisition | CLOSED (previous package) | model worse at every budget |
| Repulsion, residual mixtures, PA-TVR, FAST-SUR, exact p(1−p)-SUR, physics-refit SUR, monotone propagation, T model as predictor | CLOSED (repository Phases 1.15A–1.19B; previous package) | — |
| BALD / GlobalMI-type information criteria | **CLOSED without replay** | for noiseless labels and a boundary-determining target they equal margin exactly (P1-C); with the soft link they differ by a term that is nearly constant on M3 states (RESEARCH_DIAGNOSIS §5, ρ ≥ 0.98 for the π/p margins) |
| Brier-SUR / log-loss-SUR under T | **CLOSED without replay** | positive whenever the posterior moves (no flip requirement), so they inherit the same off-band, uncalibrated-region preference that sank XSUR; their local weights are monotone in margin on M3 |

## 4. What the acquisition theory now says

1. For a deterministic simulator and any target that determines the queried label (the boundary), the information-optimal one-step rule is margin (GBS). Beating margin on a *decision* endpoint requires a loss-directed rule whose value comes from decisions the outcome would flip (0-1) or from posterior movement (variance/entropy), and both are only as good as the posterior's calibration at the reference points — at 16–40 labels that calibration does not exist away from the data-anchored boundary.
2. Empirically, every loss-directed rule tested (six forms of SUR/XSUR, TV) either loses to margin by 0.01–0.03 or is indistinguishable from it; the only near-neutral one (TV) gates its leverage term by margin.
3. The headroom that exists (+0.095 by oracle; +0.016 by label-blind band-restriction of the *training set*) is a property of which labels the model is fitted to, not of which label is queried next; no pre-query signal identifies it.

## 5. Final acquisition recommendation

Retain the four-path external design with **M3 + TV as the single challenger** (Case C). No new candidate replaces it, no rescue variant is added, and no acquisition line remains open on the old data.
