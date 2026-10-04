# Week 17 protocol, predictions and freeze (committed and pushed before the decisive runs)

Date 2026-10-05. Phase 0 integrity commit `ef111167`. Model definitions: MODEL_SPEC.md. Decision code:
`src/week17_analyze.py` (committed with this file). Runners: `src/week17_heldout_run.py`,
`src/week17_real_al.py`. Nothing below has been run on the frozen seeds; code was smoke-tested only on
synthetic rep 1000 (outside the frozen reps) and on real splits with horizon 20 (no endpoint inspected).

## Evidence labels
| Evidence | Label |
|---|---|
| Phase 0 audit, Phase 1 real-data diagnosis (transfer, NEW CV, NEW AL prefixes, OLD A0 prefixes) | POST-HOC (NEW) / HISTORICAL (OLD) — already seen; used to design |
| Phase 2 development AL (Week 13 generator, Week 15 curvedMono cells) | DEVELOPMENT |
| 12 new synthetic worlds (`src/week17_heldout.py`), reps 0–7 | **HELD-OUT-SYNTHETIC (decisive)** |
| Real AL on NEW-136 (100 frozen splits) | POST-HOC (NEW was examined extensively; no "external validation") |
| Real AL on OLD-405 (Week 8.5 repeats 1–4) | HISTORICAL |
No new real data; the 49 withheld Bug simulations are not used.

## Datasets, splits, budgets
- Synthetic: 12 cells (H01–H12, see `week17_heldout.CELLS`): physics direction exact / 30° / 60° / 90° off,
  order-preserving distortion, order violation, curvature 0.3 / 1.0, prevalence 0.5 / 0.3 / 0.1, pool 108 /
  324, clean labels, localized label noise, pool support shift. Seeds [1717, cell, rep]; reps 0–7; dense truth
  [1717, 999] (8,000 uniform points); reference cloud [15, 99]. Startup: 8 maximin + continuation
  ([1717, rep, 2]). Budgets 16–80 step 4 (AULC normalized by 64, Week 15 convention).
- Real: NEW 100 frozen splits; OLD Week 8.5 repeats 1–4 (20 runs); startup 8 maximin + continuation
  ([1717, 10·repeat + fold, 2]); budgets 16–80 step 4; pooled out-of-fold per repeat; q20 = the exact
  historical construction (NEW: `boundary_flags(entire_evaluation_batch)`; OLD: Week 8.5 B1 distance),
  reported as mean-fold q20 AULC.

## Arms
Models G3, M3, LT, M3_Cfree × rules margin / coverage (real: exact historical Candidate-B selector) / PEER /
random (16 arms), identical startup and query accounting. H is evaluated for model quality only.
Synthetic common-design model quality: startup + uniform random fill to n ∈ {24, 48, 80}, all five models.
Oracle diagnostics (truth-knowing, diagnostic only): expectation oracle with fixed-hyperparameter refits of
the same model at B24 and B48 on every margin path (≤ 60 candidates incl. the margin and PEER picks).

## Metrics
Synthetic primary: true-boundary NSD (τ = 0.1) AULC under each model's own margin path. Secondary: ASSD,
NSD τ = 0.05, dense BA, finite-pool q20 accuracy and BA, minority recall; common design: NSD, BA,
reference-cloud latent-sign log loss/Brier. Real: pooled BA AULC, historical q20 AULC, DC-BD AULC (Week 14/15
caveats: a finite-pool proxy, not a continuous boundary), minority (NEW: non-Keyhole; OLD: Keyhole) recall
and AUC at B80; convergence (`fp_err`).

## Decision rules (`week17_analyze.verdict`)
Synthetic, LT vs G3 under margin (cell = mean over 8 reps):
- **M1** mean over cells of LT − G3 NSD AULC ≥ +0.015; **M2** LT > G3 in ≥ 8/12 cells; **M3** no cell
  with LT − G3 < −0.03. (**M4**, attribution only: LT > M3 and LT > M3_Cfree cell counts.)
- **M5** (real non-inferiority): NEW LT − G3 pooled BA AULC ≥ −0.02 and q20 AULC ≥ −0.02; OLD LT − G3 BA AULC ≥ 0.
- **MODEL BREAKTHROUGH** ⇔ M1 ∧ M2 ∧ M3 ∧ M5.
- **Acquisition**: rule R beats margin under LT if mean(R − margin) ≥ +0.01, R > margin in ≥ 8/12 cells,
  no cell < −0.03 (A1 = PEER, A3 = coverage; A2 = PEER under G3 reported). **MODEL + ACQUISITION BREAKTHROUGH**
  ⇔ MODEL BREAKTHROUGH ∧ (A1 or A3) ∧ the same rule under LT is ≥ margin on NEW in both q20 and BA AULC.
- **MECHANISM RESOLVED** (if no model breakthrough): M3 − G3 < 0 in ≥ 2 of {H07, H08, H09}; |LT − G3| ≤ 0.015
  in H08 (physics useless); PEER − margin < 0 on average under G3 and LT; PEER's pick has larger |true latent|
  than margin's pick in the majority of oracle states in ≥ 10/12 cells.
- Otherwise **NO CHANGE JUSTIFIED**.

## Numerical predictions (from Phase 1–2; DEVELOPMENT-informed)
| Quantity | Prediction |
|---|---|
| LT − G3 NSD AULC, mean over cells (margin) | +0.03 (range +0.01 to +0.05); > 0 in ≥ 9/12 cells |
| LT − G3 in H08 (physics useless) / H09 (order violation) | within ±0.015 / within ±0.02 |
| M3 − G3 | > 0 in H01/H02 (physics exact); ≤ −0.02 in H07, H08, H09; mean over cells ≤ 0 |
| LT − M3_Cfree | > 0 in ≥ 8/12 cells |
| PEER − margin (NSD AULC) | ≤ −0.10 under LT and G3; ≈ −0.03 under M3; negative in ≥ 10/12 cells for every model |
| coverage − margin | within ±0.01 on average for every model |
| random − margin | ≤ −0.05 for every model |
| Oracle (B24/B48, margin paths) | H_nsd(LT) < H_nsd(G3) in ≥ 8/12 cells; mean A_nsd < 0 for every model; ρ(V_model, V_true) higher for LT than G3; PEER picks farther from the true boundary than margin picks in ≥ 10/12 cells |
| Common design | LT NSD ≥ G3 at n = 24, 48, 80 in θ ≤ 30° cells; LT reference-cloud sign log loss < G3 |
| q20 vs NSD | the sign of LT − G3 agrees between finite q20 AULC and NSD AULC in ≥ 8/12 cells |
| NEW real AL | LT − G3 BA AULC in [−0.015, +0.01]; q20 AULC within ±0.01; M3 − G3 BA AULC ≤ −0.03; Candidate B − margin (G3) q20 AULC within ±0.01; PEER − margin BA AULC ≤ −0.02 under every model |
| OLD real AL | LT − G3 BA AULC in [0, +0.02]; LT within ±0.01 of M3 |
| Predicted verdict | MODEL BREAKTHROUGH ONLY if M5 holds on NEW; MECHANISM RESOLVED otherwise |

## Discipline
No arm, metric, cell or seed is added, dropped or redefined after this commit; deviations are logged in
WEEK17_REPORT.md. If no criterion is met, the result is reported as such.
