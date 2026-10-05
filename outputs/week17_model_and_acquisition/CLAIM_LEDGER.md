# Week 17 claim ledger

Tags: THEOREM/EXACT · NUMERICAL AUDIT · HELD-OUT-SYNTHETIC (frozen `f04d23ed`) · DEVELOPMENT · POST-HOC (NEW) ·
HISTORICAL (OLD) · POST-HOC DIAGNOSTIC (after the decisive run) · SPECULATIVE.

| # | Claim | Tag | Evidence |
|---|---|---|---|
| 1 | G3 (sklearn GPC) fits are at their Laplace mode in every authoritative use (1,595 fits). | NUMERICAL AUDIT | `integrity/laplace_mode_audit*.csv` |
| 2 | Historical M3 fits stall after two Newton steps in 46% of OLD A0 fits, 9% of Week 12 AL prefixes and the OLD-405 transfer fit; a safeguarded refit changes no historical conclusion (≤ 0.0025 q20/BA; Candidate B − margin ≤ 0.0017). | NUMERICAL AUDIT | ERRATA_OR_INTEGRITY_AUDIT §2–3 |
| 3 | Week 15 "exact Bayes look-ahead" = Laplace-refit Monte-Carlo look-ahead; B3 is asymptotic and its Dice normalization gives a tie; PEER = EER/SUR with the Letham et al. 2022 closed form. | ERRATUM | ERRATA_OR_INTEGRITY_AUDIT §4 |
| 4 | The C = 1e6 physics mean saturates early (OLD B8–B16: 55–75% of prefixes separable in log h, |m| ≈ 50) and is badly miscalibrated (NEW AL log loss 0.686 vs 0.253 with C = 1). | HISTORICAL / POST-HOC | `phase1/physics_mean_*` |
| 5 | M3's discrepancy cap binds (median r² = 1.0) and cannot override the physics mean: truth contradicts the physics sign at ≈ 10% of NEW test rows, M3 overrides at 0% (median; mean 2.7%). | POST-HOC | `phase1/diagnose_real.csv.gz` |
| 6 | Strict OLD→NEW transfer failure of M3 is a physics *level* shift (oracle intercept: BA 0.579 → 0.700 = G3) plus a weaker physics *direction* on NEW (AUC log h 0.857 vs VX 0.899; M3 AUC 0.881 vs G3 0.924); it is not label shift (prevalence correction → BA 0.5 for every model). | POST-HOC | `phase1/transfer_*` |
| 7 | The logistic GPC attributes 20–67% of predictive variance in its boundary band to label noise in deterministic worlds, but a noise-free look-ahead does not make model-aware acquisition align with true value. | CONTROLLED SYNTHETIC (Week 16 states) | `phase1/likelihood_*` |
| 8 | Regularizing M3 (C = 1) improves calibration but not BA/rare recall; regularize + uncap (M3_Cfree) recovers most of M3's held-out loss (−0.022 vs −0.110 relative to G3) but stays below G3. | POST-HOC + HELD-OUT-SYNTHETIC | Phase 1 table; `heldout/` |
| 9 | The learned-strength physics-trend GP (LT) is **not** a robust improvement over G3 on held-out worlds: mean +0.0086 NSD AULC, 7/12 cells, worst −0.046 (local label noise); frozen model criteria fail. | HELD-OUT-SYNTHETIC | VERDICT.json |
| 10 | LT helps when the physics direction is right or under strong imbalance (+0.034 to +0.050) and at small n (common design n = 24: NSD 0.576 vs 0.542), and gives the best latent-sign log loss at every n; it costs up to 0.02–0.075 when physics is off/useless at larger n. | HELD-OUT-SYNTHETIC | `heldout/` quality rows |
| 11 | Original M3 is far below G3 whenever physics is not exact (−0.10 to −0.16 NSD AULC in 9/12 held-out cells). | HELD-OUT-SYNTHETIC | `heldout/` |
| 12 | On held-out worlds (and OLD), margin is the best acquisition rule under every model; PEER (coherent one-step EER/SUR) loses to margin in 12/12 cells under G3, LT and M3_Cfree (11/12 under M3), most under LT (−0.155); coverage (Candidate-B-like) ≈ margin. | HELD-OUT-SYNTHETIC | VERDICT.json `acquisition` |
| 13 | Truth-oracle one-step headroom 0.03–0.04 NSD; margin captures 9–17%, PEER 2–10%; the model's value is uninformative about true value for every model (ρ ≈ 0); PEER picks lie farther from the true boundary than margin picks (12/12 cells). | HELD-OUT-SYNTHETIC (diagnostic oracle) | oracle rows |
| 14 | LT's single-start ML-II lands below G3's evidence in 4.9% of states (17% in H08); a G3-warm-started refit removes those failures (NSD 0.656 → 0.841). | POST-HOC DIAGNOSTIC | `heldout/posthoc_lt_optimizer_check.csv` |
| 15 | OLD real AL (margin): LT − G3 BA AULC +0.024 [0.012, 0.033], q20 +0.023 [0.006, 0.039]; M3 remains best on OLD (BA 0.930); Candidate B ≈ margin; PEER ≪ margin. | HISTORICAL | `real_al/` |
| 16 | NEW real AL (margin): G3 remains the leader (BA AULC 0.661, q20 0.682); LT −0.017 BA [−0.037, +0.003], M3 −0.041 [−0.065, −0.017]. | POST-HOC | `real_al/`, VERDICT.json |
| 16b | On NEW only, exploration beats margin: under G3/LT random (+0.020/+0.027 BA), Candidate B (+0.012/+0.017) and PEER (+0.010/+0.030; non-KH recall +0.08) exceed margin; random does as well as the model-aware rules, so the gain is rare-pocket exploration, not a better acquisition formula; it does not replicate on OLD or held-out worlds. | POST-HOC (descriptive) | `real_al/` |
| 17 | A nested multi-start ML-II could make LT "never worse than G3". | SPECULATIVE | claim 14 |

## Claims that must not be made
- That LT (or any Week 17 model) is a validated improvement over G3, or that any acquisition beats margin in general
  (the NEW-only advantage of exploration is post-hoc and shared by random refinement).
- That regularizing M3 (C ≈ 1) is "the fix" (it repairs calibration, not BA, and does not reach G3).
- That NEW-136 analyses are external or confirmatory.
- That the Laplace convergence issue invalidates historical conclusions (it does not).
