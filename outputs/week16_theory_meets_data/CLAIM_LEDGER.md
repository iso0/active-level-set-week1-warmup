# Week 16 claim ledger

Tags: THEOREM/EXACT · CONTROLLED SYNTHETIC (development = Week 13 generator; held-out = Week 15 cells, now
descriptive) · POST-HOC NEW · HISTORICAL OLD · SPECULATIVE. Predictions frozen at `ae165086`.

| # | Claim | Tag | Evidence |
|---|---|---|---|
| 1 | Astra's eq. (1), the sharp 1/(N−1) margin bound, κ_N (table, construction, minimax, bound (4)), Prop. 5.1 (with its decimals), eqs. (9)–(11), the §5.3 q20 construction on the historical evaluator, §5.4 and §7 are correct as stated. | THEOREM/EXACT | `src/tests/test_week16_astra.py` (46 exact tests) |
| 2 | Binary-observation lemma e(T\|O) = (1 − max(\|ET\|, \|E[TO]\|))/2 and PEER's closed form under a Gaussian latent posterior with probit observation noise. | THEOREM/EXACT | THEORY_WEEK16 L1–L2; exact and MC tests |
| 3 | Exact one-step Bayes values are ≥ 0; Week 15's VSUR/EBR-D Laplace-refit look-ahead violates the martingale property (median Σ\|E q′ − q\| = 1.1 per 400 targets) and is negative for most candidates in 13/18 states, so it did not compute its model's Bayes value. | THEOREM + CONTROLLED SYNTHETIC | THEORY_WEEK16 L3; `validation/peer_validation.csv` |
| 4 | With latent-sign targets observed through label noise, margin's model-relative ratio can be arbitrarily close to 0 (the 1/(N−1) guarantee requires noiseless revelation of the target). | THEOREM/EXACT | THEORY_WEEK16 W16-1; `test_noisy_observation_breaks_margin_bound` |
| 5 | Erratum E16-1: Week 13 `LaplaceGPC` stores non-converged fits in 100% of the Week 15 gpworld m0 = −4 fits and in no base fit elsewhere; all Week 15 numbers for those two cells are withdrawn; the Week 15 verdict is unchanged (5/14 cells, mean −0.0148 without them). | CONTROLLED SYNTHETIC (audit) | ERRATUM_LAPLACE.md; `laplace_audit/` |
| 6 | Margin is far from optimal under its own model (median r_model 0.41 in physics-like families; P1 ≥ 0.8 rejected). | CONTROLLED SYNTHETIC | `headroom/states.csv`, VERDICTS.json |
| 7 | The model-optimal query recovers almost none of the oracle headroom (ΣA/ΣH −0.08…0.16 by family; P2 holds), and V_model ranks candidates nearly independently of their true value (median Spearman ≈ 0.03–0.11). | CONTROLLED SYNTHETIC | `headroom/summary.csv` |
| 8 | In misspecified physics-like families margin's one-step true value is ≥ PEER-argmax's and above a random candidate's (NSD: dev +0.0019, curvedMono +0.0023 over random, CIs above 0); in the well-specified GP world PEER-argmax roughly doubles margin's one-step value (+0.66 points of 400, CI [−0.22, 1.55]). | CONTROLLED SYNTHETIC (descriptive) | `headroom/pick_contrasts.csv` |
| 9 | Low-value margin picks are aleatoric (true latent near 0, posterior sd 1.5–2.6 vs 4.3–5.2), not extrapolation decoys; a constant ML-II or physics mean does not reduce them (P3 rejected). | CONTROLLED SYNTHETIC | `headroom/decoy_sd.csv`, `decoy_variants.csv` |
| 10 | Joint near-pair calibration does not explain margin's acquisition quality beyond marginal calibration (P4 rejected: within-cell rank correlation of the two scores 0.985; partial ρ −0.01, p = 0.89); no calibration score predicts one-step regret. | CONTROLLED SYNTHETIC | `calibration/within_cell_spearman.csv`, VERDICTS.json |
| 10b | Where a physics score is informative, a physics prior mean fitted on the campaign's own labels improves both calibration and margin's NSD AULC (+0.012 to +0.044). | CONTROLLED SYNTHETIC (descriptive) | `calibration/cell_variant_means.csv` |
| 11 | On NEW, model variants with better marginal log loss have worse BA/DC-BD AULC under margin (within-repeat Spearman −0.53/−0.49); on OLD no relation. | POST-HOC NEW / HISTORICAL OLD | `real_data/calibration_spearman.csv` |
| 12 | PEER-argmax vs margin on real pools: no resolvable difference (NEW −0.0022 BA [−0.0056, 0.0011]; OLD +0.0022 [−0.0033, 0.0080]). | POST-HOC NEW / HISTORICAL OLD | `real_data/summary.csv` |
| 13 | Physics-score tails are enriched for the rare class in every NEW and OLD training pool for M ∈ {5,10,15,20} (P5 holds); Week 12's uniform-random discovery costs match the exact law; maximin8 and adaptive8 produce identical states through B16 in 94/100 pools and no consistent posterior-quality difference in the other 6. | POST-HOC NEW / HISTORICAL OLD | `discovery/` |
| 14 | A coherent (PEER-type) look-ahead could help where the model is well specified. | SPECULATIVE (one-step, descriptive gpworld only) | — |

## Claims that must not be made
- That PEER or any Week 16 rule is a better acquisition method (no confirmatory test; development A ≤ 0).
- That Astra's 1/(N−1) guarantee applies to the thesis's GPC acquisition (it does not with noisy labels).
- That Week 15's gpworld m0 = −4 results stand, or that the Week 15 verdict depended on them.
- That real-data analyses validate anything (NEW is post-hoc; OLD historical; descriptive only).
