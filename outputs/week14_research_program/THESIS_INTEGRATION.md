# Thesis integration plan (Weeks 1–14)

Working title: **Sample-Efficient Active Level-Set Estimation in Rare-Regime Finite Pools —
with an Application to Melt-Pool Regime Boundaries.**

The thesis argument, in one sentence: in expensive finite simulation pools with a rare regime, the
binding constraints are discovery, structural transfer and evaluation validity — each governed by an
explicit structural assumption — rather than the choice among acquisition functions; physics helps
most when it enters as an ordering and is dangerous when it fixes the level.

## Chapter structure

1. **Introduction.** Keyhole/conduction boundary in LPBF; expensive deterministic SPH; finite pools;
   rare regimes; contributions list (below).
2. **Background.** GP classification and Laplace inference; level-set estimation (Gotovos 2013;
   Letham 2022); pool-based AL and margin; scaling laws (h; keyhole number of Gan et al. 2021);
   monotone classification and dominance; graph-cut limits; boundary metrics; ROC iso-performance.
3. **Synthetic foundations (Weeks 1–4).** Short; metric definitions.
4. **The SPH campaigns and the physics coordinate (Weeks 5–9).** OLD-405, h, H, M3; the order
   (P↑, VX↓, LS↓) validated on OLD before NEW (3 violations / 22,050 pairs; Phase 1.19A).
5. **Acquisition on OLD (Weeks 8–10).** Margin ≫ random (+0.037); the refinement zoo; Candidate B
   (+0.0067 < +0.01); headroom reference 0.014 — *explicitly a model-specific reference gap, not a
   ceiling* (Week 14 C7).
6. **The prospective attempt (Week 11).** Frozen protocol; single-class B16 STOP; why STOP was correct.
7. **Discovery: impossibility and structural certificates (Week 13 + 14).**
   - Theorem D1 (no free lunch), D2 (geometric certificate, minimax covering), D3 (Pareto-front
     certificate, minimax antichain), D4 (score), D5 (hedge). Proofs in the main text.
   - Table: held-out benchmark (WEEK14_MASTER_REPORT B1). Figure: `week14/figures/fig1_discovery_by_dimension.png`.
   - Real campaigns: `fig2_discovery_real_campaigns.png`; OLD certified geometrically and by order;
     NEW: geometry not certified (Week 13 fig1), order violated (`fig6_new_order_violations.png`),
     score ordering succeeds (≤ 7). Masinelli external confirmation.
   - Counterexample C5 (maximin worse than random).
8. **Evaluation of boundary recovery (Week 13 + 14).**
   - Theorem E1 (precision-threshold characterization; Week 13 Props. 1–2 as corollaries; credit
     Provost & Fawcett). Remark on hubness.
   - Theorem E2 (cut-edge recall limit and interpretation). Counterexamples C1–C4.
   - Density-induced rank reversal (`fig4_metric_density_sensitivity.png`), length weighting as a
     partial fix (P7a held; P7b failed in 3/12 — report it).
   - Recommendation: report q20 (historical), BA, minority recall, BEF1 and a trivial baseline; never
     compare boundary scores across campaigns with different densities as boundary quality.
9. **Acquisition headroom and its identifiability (Week 14 Study 4).**
   - Prop. H1 + counterexample C6 + empirical vacuity.
   - `fig5_headroom_identifiability.png`: finite-metric oracle overfits; true-objective oracle shows
     +0.05–0.10 NSD over margin by avoiding noisy boundary labels; BALD does not capture it.
10. **Physics priors under campaign shift (Week 12 + 13 + 14).**
    - Week 13 transfer diagnosis; Prop. O1 (dominance = exponent-robust order); Week 13 Prop. 7
      (anchoring bound) and heuristic O2.
    - Risk asymmetry (`fig3_physics_risk_asymmetry.png`, C2 table, real table B3).
    - Closure override: where it helps (valid order, within-material Masinelli), where it fails
      (omitted-coordinate violations; NEW). Monotone GP failure mechanism (C10).
    - Information sufficiency Prop. I1 and the NEW order-violation audit (one case = 64/75 violations).
11. **Discussion and limitations.** Development vs confirmation; post-hoc status of NEW; 12 rare
    cases; synthetic generators; what a future campaign should pre-register (startup: score ordering
    or hedge with an explicit structural assumption; secondary endpoints from Ch. 8; order-violation
    check before using order inference; audit of the anomalous NEW case).
12. **Conclusion.**

## Exact items to include

| Item | Source |
|---|---|
| Theorems D1, D2, D3; Props. D4, D5 | `week14_research_program/THEORY.md` Part D |
| Prop. O1, heuristic O2; Week 13 Prop. 7 | THEORY Part O; Week 13 THEORY |
| Prop. I1 | THEORY Part I |
| Theorem E1 (with Week 13 Props. 1–2) | THEORY Part E |
| Theorem E2 | THEORY Part E |
| Prop. H1, Counterexample H2/C6 | THEORY Part H; COUNTEREXAMPLES |
| Counterexamples C1–C11 (select C1, C3, C5, C7, C8, C10) | `COUNTEREXAMPLES.md` |
| Table: held-out discovery | MASTER_REPORT B1 |
| Table: real discovery | MASTER_REPORT B2 |
| Table: model BA under shift (synthetic + real) | MASTER_REPORT B3; `benchmarks/C2_paired_contrasts.csv`; `real_data/real_models.csv` |
| Table: metric density sensitivity | MASTER_REPORT B4 |
| Table: headroom | MASTER_REPORT B5 |
| Figures | `week14_research_program/figures/fig1–fig6`; Week 13 `figures/fig1–fig7` |
| Pre-registration and deviations | `CONFIRMATORY_BENCHMARK_FREEZE.md`, `DEVIATIONS.md` (appendix) |

## Contributions list for Chapter 1 (defensible wording)

1. An assumption-explicit theory of cold-start discovery for finite-pool level-set estimation: an
   exchangeability impossibility result and sharp certificates with minimax characterizations under
   geometric, order and score structure.
2. Evidence on a frozen held-out benchmark and three real campaigns, including an explained failure
   on the shifted SPH campaign.
3. Exact and asymptotic characterizations of finite-pool evaluation metrics, showing prevalence and
   density dependence, and that finite-pool metrics cannot identify acquisition headroom on the true
   boundary.
4. A risk analysis of physics encodings under campaign shift: physics as level versus as order.
5. A transparent record of negative results (Candidate B, monotone GP, BALD, closure on NEW).
