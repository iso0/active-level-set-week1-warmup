# Week 17 — Is the remaining difficulty a fixable model problem, and does a better model unlock acquisition?

Commits: Phase 0 integrity `ef111167`; protocol freeze `f04d23ed` (pushed before the decisive runs);
results: this commit. Evidence labels as in PREDICTIONS_AND_FREEZE.md.

## Summary
**Frozen verdict: NO CHANGE JUSTIFIED.** G3 + margin remains the defensible endpoint. What Week 17 adds is a
diagnosed mechanism and a measured boundary on what a better model can buy.

1. **What was wrong.** Historical M3 combines a near-unregularized physics logistic (C = 1e6), which
   separates and saturates on early labels, with a discrepancy GP capped at sd 1. The cap binds, so
   deterministic labels that contradict physics are absorbed as noise instead of moving the boundary.
   Between campaigns the physics *level* moved and its *direction* weakened (NEW is VX-dominated). The C = 1e6
   mean also stalls the Laplace Newton loop, but that changes no historical conclusion.
2. **Regularizing M3 is not the fix.** C = 1 repairs calibration (NEW AL log loss 0.69 -> 0.25) but lowers
   BA/rare recall. Regularize + uncap recovers most of M3's held-out loss but stays below G3.
3. **The principled learned-strength physics trend (LT) is useful but not robust.** It helps where physics is
   right and under imbalance (held-out +0.03 to +0.05 NSD AULC; OLD real BA +0.024 over G3). It loses under
   local label noise (-0.046) and slightly where physics is useless or misleading, and is 0.017 BA behind G3
   on NEW. The frozen model criteria fail (mean +0.0086, 7/12 cells, worst -0.046).
4. **A better model does not unlock model-aware acquisition.** On held-out worlds and OLD, margin beats
   coherent one-step EER/SUR (PEER) under every model, and Candidate-B-like coverage is about equal to margin.
   The truth oracle's one-step headroom (0.03-0.04 NSD) is invisible in every model's posterior (rho ~ 0);
   margin captures 9-17% of it.
5. **NEW is the exception, and it points to exploration, not model-awareness.** On NEW (post-hoc) random,
   Candidate B and PEER all beat margin under G3/LT by 0.01-0.03 BA AULC. Random is as good as the
   model-aware rules, so this is the rare-pocket discovery problem of Weeks 12-16, not a better acquisition
   formula.

## Phase 0 — numerical integrity (ERRATA_OR_INTEGRITY_AUDIT.md)
- **G3 (sklearn GPC) is numerically sound** in all 1,595 audited authoritative fits (Week 12 transfer, NEW
  CV, Week 12 AL prefixes, Week 9 OLD A0 paths).
- **Historical M3 is not at its Laplace mode** in 229/500 OLD A0 fits, 91/994 Week 12 AL prefixes, 2/100 NEW
  CV fits and the OLD-405 transfer fit: with the C = 1e6 physics mean the undamped Newton loop stops after two
  steps. A full safeguarded refit (mode *and* ML-II) changes mean q20/BA by ≤ 0.0025 in every set and the
  Candidate B − margin contrast by ≤ 0.0017 — **no historical conclusion changes**.
- Terminology/theory errata: E17-T1 ("exact Bayes" in Week 15 = Laplace-refit Monte-Carlo look-ahead;
  Week 9 `EXACT_LAPLACE_FIXED_MODEL` SUR likewise), E17-T2 (B3 is asymptotic; Dice normalization gives a tie),
  E17-T3 (PEER = EER/SUR with the Letham et al. 2022 closed form).

## Phase 1 — what is actually wrong (POST-HOC NEW / HISTORICAL OLD / DEVELOPMENT)
All models below run through one code path (safeguarded Laplace, ML-II at every state); pooled out-of-fold
metrics per repeat (`phase1/diagnose_pooled*.csv`).

| Set | Model | BA | rare recall | AUC | rare AP | log loss | q20 |
|---|---|---:|---:|---:|---:|---:|---:|
| NEW CV (100 splits) | G3 | **0.693** | **0.42** | **0.895** | **0.541** | **0.205** | 0.704 |
| | M3 | 0.620 | 0.27 | 0.858 | 0.507 | 0.273 | 0.675 |
| | M3 with C = 1 | 0.630 | 0.28 | 0.867 | 0.528 | 0.230 | **0.715** |
| | M3, residual uncapped | 0.629 | 0.30 | 0.834 | 0.451 | 0.262 | 0.653 |
| | M3_Cfree (C = 1 + uncapped) | 0.651 | 0.34 | 0.852 | 0.480 | 0.232 | 0.676 |
| | LT | 0.687 | 0.41 | 0.891 | 0.533 | 0.209 | 0.700 |
| | H | 0.540 | 0.10 | 0.840 | 0.478 | 0.280 | 0.700 |
| NEW AL prefixes (B16–80) | G3 | **0.667** | **0.40** | 0.830 | 0.411 | 0.315 | 0.683 |
| | M3 | 0.614 | 0.27 | 0.830 | 0.373 | 0.686 | 0.660 |
| | M3 with C = 1 | 0.583 | 0.20 | **0.845** | 0.402 | **0.253** | 0.668 |
| | M3_Cfree | 0.619 | 0.28 | 0.827 | 0.380 | 0.280 | 0.657 |
| | LT | 0.661 | 0.38 | 0.820 | 0.402 | 0.314 | 0.677 |
| OLD A0 prefixes (B16–80) | G3 | 0.906 | 0.84 | 0.968 | 0.915 | 0.202 | 0.817 |
| | M3 | **0.928** | **0.88** | 0.985 | 0.938 | 0.175 | **0.838** |
| | M3 with C = 1 | 0.910 | 0.84 | **0.988** | **0.948** | 0.173 | 0.822 |
| | LT | 0.920 | 0.86 | 0.987 | 0.946 | **0.144** | 0.817 |
| Transfer OLD → NEW | G3 | **0.700** | **0.42** | **0.924** | **0.560** | **0.167** | **0.821** |
| | M3 | 0.579 | 0.17 | 0.881 | 0.512 | 0.216 | 0.714 |
| | M3_Cfree | 0.659 | 0.33 | 0.881 | 0.531 | 0.178 | 0.786 |
| | LT | 0.696 | 0.42 | 0.885 | 0.528 | 0.210 | 0.786 |

**A. Physics-mean saturation (`phase1/physics_mean_*`).** With C = 1e6 the revealed labels are perfectly
separable in log h in 55–75% of OLD prefixes at B8–B16 (21% of NEW prefixes at B8); the standardized
coefficient is then ≈ 20, the latent mean reaches |m| ≈ 50 and 65–69% of the OLD campaign receives a
saturated prior (|m| > 5). Regularization (C = 1) removes this: NEW AL-prefix log loss of H 4.56 → 0.27 and
of M3 0.686 → 0.253. **But C = 1 is not a BA fix**: it lowers BA and rare recall at small budgets (NEW AL
0.614 → 0.583) and on OLD (0.928 → 0.910) because the shrunk mean predicts the rare class less often under
91% / 18% prevalence. (Week 9's acquisition search had already tried a C = 1 scoring posterior,
"margin_tempered": −0.001 q20 AULC vs margin on OLD.)

**The binding defect is the capped discrepancy.** The M3 residual variance sits at its upper bound
(median 1.0 in every set). On NEW AL prefixes the truth contradicts the sign of the physics mean at 10.7% of
test points; M3 overrides it at 0% (median; mean 2.7%), the uncapped variants at 3.7% (mean 4.9–5.6%). ML-II, when allowed, asks for a
residual variance of 4.7–9.7 on NEW and ≈ 1 or less on OLD. A deterministic label that contradicts a
confident physics prior is therefore absorbed as logistic noise instead of moving the boundary.

**B. Deterministic simulator vs logistic likelihood (`phase1/likelihood_*`, Week 16 states).** Inside its
predicted boundary band the logistic GPC attributes 20–67% of predictive variance to label noise even in
deterministic worlds (curvedMono 0.67, rough 0.61, dev 0.42, gpworld 0.39, branin 0.20) — the "aleatoric
reading" of a deterministic boundary is real. It is not the acquisition bottleneck: a noise-free look-ahead
(PEER_det) aligns with the true one-step value no better than the noisy one (per-state Spearman ≤ 0.07), and
latent-sign margin (−|μ|/s) is only marginally better than predictive margin in deterministic cells
(true one-step value of the pick 0.0004 vs 0.0003 Hamming, 0.0027 vs 0.0024 NSD).

**C. Transfer failure (`phase1/transfer_*`).** (i) *Not label shift*: correcting OLD predictions for NEW's
prevalence alone collapses every model to BA 0.5 — the class-conditional distributions changed.
(ii) *Physics level shift*: the log-h threshold moved from 20.69 (OLD) to 20.82 (NEW); an oracle intercept
on NEW lifts M3's transfer BA from 0.579 to 0.700 (= G3), while G3 gains nothing (0.700 → 0.692).
(iii) *Physics direction*: log h ranks OLD almost perfectly (AUC 0.991) but NEW only moderately (0.857),
where VX alone does better (0.899); on NEW, G3's ML-II uses VX and ST (ℓ_P, ℓ_LS at the upper bound) and
M3's AUC (0.881) stays below G3's (0.924) under any recalibration. (iv) *Support*: no model recovers the
non-Keyhole rows farthest from OLD support (only 2 of the 12 lie in that tertile — descriptive).

**D. Acquisition consequence (Week 16 states and Phase 2 development).** Fixing the observation model of the
look-ahead does not align model-aware acquisition (B). PEER's picks lie far from the true boundary
(|true latent| 5.4 under LT and 2.9 under G3 vs 1.4 and 0.8 for margin on a development path): the one-step
Hamming value on a uniform reference volume rewards resolving large regions the model is unsure about, which
in deterministic worlds are already correctly classified.

## Phase 2 — development and the one model (DEVELOPMENT; `development/dev_results.csv.gz`)
Week 13 generator (BAL/OLD/NEW × σ ∈ {0, 0.5}) and curvedMono (OLD/NEW × σ ∈ {0, 0.5}), 4 reps, per-step
ML-II: margin NSD AULC LT 0.905, M3_Cfree 0.867, G3 0.861, M3 0.853; LT > G3 in 10/10 cells (+0.002 to
+0.122), M3 and M3_Cfree mixed (−0.10 to +0.12). PEER < margin under every model (G3 0.620, LT 0.634,
M3 0.821, M3_Cfree 0.724). Oracle splits: LT leaves the least one-step headroom (H_nsd 0.0041 vs G3 0.0162)
and has the best V_model–V_true alignment (ρ_nsd 0.21 vs 0.08), but PEER's pick is still worse than
margin's (A_nsd < 0 for every model).
Selected: **LT** (learned-strength integrated physics trend + uncapped ARD residual) as the one model;
**M3_Cfree** ("regularize and uncap M3") as the ablation. G3, original M3 and H remain baselines.

## Phase 3 — freeze
Protocol, model definitions, decision code and numerical predictions committed and pushed at `f04d23ed`
before any decisive run (PREDICTIONS_AND_FREEZE.md, MODEL_SPEC.md, `src/week17_analyze.py`).

## Phase 4 — decisive model tests
### Held-out synthetic worlds (HELD-OUT-SYNTHETIC; 12 cells × 8 reps; `heldout/heldout_results.csv.gz`)
Margin NSD AULC (each model on its own margin path; cell means):

| Cell | G3 | LT | M3 | M3_Cfree | LT − G3 |
|---|---:|---:|---:|---:|---:|
| H01 physics exact, prev 0.5 | 0.868 | **0.907** | 0.852 | 0.881 | +0.039 |
| H02 physics exact, prev 0.1 | 0.790 | **0.824** | 0.774 | 0.745 | +0.034 |
| H03 30° off, prev 0.5 | **0.815** | 0.793 | 0.656 | 0.772 | −0.022 |
| H04 30° off, prev 0.1 | 0.608 | **0.644** | 0.449 | 0.543 | +0.036 |
| H05 30° off, prev 0.1, pool 324 | 0.753 | **0.799** | 0.604 | 0.735 | +0.045 |
| H06 30° off, strong curvature | 0.786 | **0.805** | 0.683 | **0.805** | +0.019 |
| H07 60° off | 0.772 | **0.773** | 0.629 | 0.758 | +0.000 |
| H08 physics useless (90°) | 0.730 | 0.713 | 0.610 | **0.746** | −0.017 |
| H09 physics order violated | **0.792** | 0.772 | 0.654 | 0.749 | −0.020 |
| H10 order-preserving distortion | 0.858 | **0.907** | 0.878 | 0.831 | +0.050 |
| H11 30° off, local label noise | **0.697** | 0.651 | 0.598 | 0.665 | −0.046 |
| H12 30° off, support shift | **0.745** | 0.729 | 0.601 | 0.725 | −0.016 |

Frozen model criteria: **M1** mean LT − G3 = +0.0086 (95% path-bootstrap −0.004 to +0.022; required ≥ +0.015)
— fails; **M2** LT > G3 in 7/12 cells (required ≥ 8) — fails; **M3** worst cell −0.046 (H11; required ≥ −0.03)
— fails. **MODEL BREAKTHROUGH is not established.** Attribution (M4): LT > M3 in 12/12 cells and
LT > M3_Cfree in 9/12. Original M3 is far below G3 whenever physics is not exact (−0.10 to −0.16 in 9 cells;
≈ −0.016 even when it is exact; +0.021 only under the order-preserving distortion). The ablation
(regularize + uncap) recovers most of M3's loss (mean M3_Cfree − G3 −0.022 vs M3 − G3 −0.110) but not G3.
Secondary endpoints under margin agree in direction (LT − G3: dense BA +0.006, finite q20 +0.005, ASSD
−0.004, NSD τ = 0.05 +0.007; M3 − G3: q20 −0.064, BA −0.036); q20 and NSD agree in the sign of LT − G3 in 9/12
cells.

**Common design (random labelled sets; model quality independent of acquisition).** LT is better than G3 at
n = 24 (NSD 0.576 vs 0.542, sign log loss 0.375 vs 0.407), equal at n = 48 (0.694 vs 0.694) and worse at
n = 80 (0.792 vs 0.810); its latent-sign log loss is the best of all models at every n. The n = 80 deficit
is concentrated where physics is off or useless (H03, H07, H08, H12: −0.04 to −0.075). Physics helps early and
when right; with more data, an imperfect trend costs more than it gives.

**Why LT is not robust (POST-HOC diagnostics, labelled).** (i) Learned strength does not switch a useless
trend off reliably: in H08 ML-II activates it transiently at mid budgets (s₁² ≈ 29–51 at B32), which
redirects the margin path; (ii) the single-start ML-II sometimes lands below G3's evidence although LT nests
G3 (e.g. −3.95 nats, H08 rep 4 at B48) — an optimizer failure, quantified in
`heldout/posthoc_lt_optimizer_check.csv`: on LT's regenerated margin paths (288 states at B24/48/80) the
frozen single-start ML-II ends below G3's evidence in 4.9% of states (H08 17%, H07 13%, H03/H04 8%), and in
those states LT's NSD is 0.656 against 0.841 for an LT refit warm-started at G3's optimum (G3 0.844); the
warm start reaches at least G3's evidence in 100% of states. This is a fixable weakness of the frozen LT
implementation, identified after the run; it does not change the verdict; (iii) under localized label noise the evidence favours the
trend (LML LT − G3 ≈ +2) while the boundary gets worse — marginal likelihood and boundary geometry disagree.

### Real data (POST-HOC NEW / HISTORICAL OLD)
Model quality on fixed designs is the Phase 1 table above (already seen during diagnosis — descriptive):
G3 remains the predictive leader on NEW (CV, AL prefixes, strict transfer); LT is within 0.006 BA of G3 on
NEW and better than G3 on OLD (BA 0.920 vs 0.906, log loss 0.144 vs 0.202); original M3 is best on OLD BA
and worst-calibrated; regularizing M3 (C = 1) fixes calibration but not BA.

**Real active learning (own paths; `real_al/`; 20 repeats NEW, 4 repeats OLD; repeat-level bootstrap,
descriptive).**

| Margin, pooled AULC | NEW BA | NEW q20 | NEW DC-BD | NEW non-KH recall B80 | OLD BA | OLD q20 | OLD DC-BD |
|---|---:|---:|---:|---:|---:|---:|---:|
| G3 | **0.661** | **0.682** | **0.400** | **0.354** | 0.898 | 0.802 | 0.549 |
| M3 | 0.620 | 0.666 | 0.351 | 0.300 | **0.930** | **0.853** | **0.629** |
| LT | 0.643 | 0.672 | 0.386 | 0.321 | 0.922 | 0.825 | 0.615 |
| M3_Cfree | 0.638 | 0.669 | 0.386 | 0.329 | 0.925 | 0.842 | 0.618 |

LT - G3: NEW BA -0.017 [-0.037, +0.003], q20 -0.010 [-0.023, +0.002] (frozen non-inferiority M5 holds);
OLD BA +0.024 [+0.012, +0.033], q20 +0.023 [+0.006, +0.039]. M3 - G3: NEW BA -0.041 [-0.065, -0.017];
OLD BA +0.031 [+0.010, +0.046]. **G3 is still the predictive leader on NEW; physics models lead on OLD.**

## Phase 5 — does a better model unlock acquisition?
Held-out synthetic, rule − margin NSD AULC (mean over cells; cells where the rule beats margin; 95% path CI):

| Model | PEER − margin | coverage (Candidate-B-like) − margin | random − margin |
|---|---|---|---|
| G3 | −0.108 (0/12) [−0.134, −0.085] | −0.001 (5/12) [−0.014, +0.011] | −0.091 (0/12) |
| M3 | −0.026 (1/12) [−0.034, −0.017] | −0.011 (2/12) [−0.018, −0.004] | −0.087 (0/12) |
| LT | −0.155 (0/12) [−0.190, −0.124] | −0.003 (4/12) [−0.012, +0.007] | −0.104 (0/12) |
| M3_Cfree | −0.065 (0/12) [−0.084, −0.047] | −0.008 (3/12) [−0.015, −0.001] | −0.114 (0/12) |

No rule beats margin under any model (A1, A2, A3 all fail). **Margin remains the acquisition leader**, and
the better model (LT) makes the coherent model-aware rule *worse*, not better.

**Headroom decomposition (oracle splits at B24/B48 on margin paths; one-step true NSD gain).**

| Model | best candidate (truth oracle) | margin pick | PEER pick | random | H = best − margin | V_model–V_true ρ |
|---|---:|---:|---:|---:|---:|---:|
| G3 | 0.041 | 0.0060 | 0.0035 | 0.0021 | 0.035 | −0.010 |
| M3 | 0.035 | 0.0059 | 0.0016 | 0.0006 | 0.029 | −0.016 |
| LT | 0.031 | 0.0053 | 0.0005 | 0.0014 | 0.026 | −0.003 |
| M3_Cfree | 0.028 | 0.0024 | 0.0028 | 0.0010 | 0.026 | +0.065 |

Truth-oracle headroom → visible under the model → captured: the oracle's best one-step candidate gains
0.03–0.04 NSD; margin captures 9–17% of it (G3 15%, M3 17%, LT 17%, M3_Cfree 9%); the improved model leaves less headroom
(LT < G3 in 9/12 cells) because its states are better, but makes **none** of the remainder visible: the
model's own value ranks candidates independently of their true value (ρ ≈ 0 for every model) and PEER's
argmax captures 2–10%. PEER's pick is farther from the true boundary than margin's in the majority of
states in 12/12 cells. Of the four candidate explanations: (a) the model dependence is still wrong
(ρ ≈ 0 even for LT) — yes; (b) one-step objectives are insufficient — the one-step *volume* objective is
actively misdirected (far-field epistemic regions), margin is not; (c) the evaluation target is sparse — the
NSD gain of any single query is small and concentrated on a few candidates; (d) the oracle advantage uses
inaccessible information — yes: with ρ ≈ 0 the oracle's choices are not predictable from the model's
posterior, i.e. the headroom is truth knowledge (as in Weeks 15–16).

## Phase 6 — stress tests (held-out cells)
| Stress | Cells | LT − G3 | M3 − G3 | margin still best? |
|---|---|---|---|---|
| imbalance (prev 0.1) | H02, H04, H05 | +0.034, +0.036, +0.045 | −0.016, −0.160, −0.149 | yes |
| pool size 324 | H05 | +0.045 | −0.149 | yes |
| boundary curvature | H06 | +0.019 | −0.103 | yes |
| physics-order-preserving distortion | H10 | +0.050 | +0.021 | yes |
| physics weak / useless | H07, H08 | +0.000, −0.017 | −0.143, −0.120 | yes |
| physics order violated (misleading) | H09 | −0.020 | −0.138 | yes |
| localized label noise | H11 | −0.046 | −0.098 | yes |
| support / covariate shift | H12 | −0.016 | −0.144 | yes |
| clean deterministic boundary | all except H11 | as above | as above | yes |
Physics-level shift (campaign transfer) is tested on the real OLD → NEW pair (Phase 1C), where it is the
dominant M3 failure; inside a single campaign the level is learned.

## Candidate B
Held-out synthetic: Candidate-B-like coverage -> margin vs margin is -0.001 (G3), -0.011 (M3), -0.003 (LT),
-0.008 (M3_Cfree) NSD AULC, winning in 2-5 of 12 cells. Real, using the exact historical Candidate-B selector
fed with each model's probabilities: OLD q20 +0.004 (G3), +0.005 (M3), +0.006 (LT), all CIs including 0.
NEW q20 +0.020 [-0.000, +0.039] under G3 and +0.020 [+0.005, +0.034] under LT, but random refinement does as
well on NEW (+0.020 / +0.030). Candidate B remains what Weeks 9-12 found: a reasonable challenger with no
established superiority. Its NEW gain is shared by random exploration and does not replicate on held-out
worlds or OLD.

**NEW rule contrasts (rule - margin, POST-HOC, 20 overlapping repeats):**

| Model | Candidate B BA / q20 | PEER BA / q20 / non-KH recall B80 | random BA / q20 |
|---|---|---|---|
| G3 | +0.012 [-0.004, +0.027] / +0.020 [-0.000, +0.039] | +0.010 / +0.011 / **+0.079 [+0.021, +0.142]** | +0.020 [-0.004, +0.044] / +0.020 |
| LT | **+0.017 [+0.002, +0.032]** / **+0.020 [+0.005, +0.034]** | **+0.030 [+0.003, +0.059]** / +0.007 / **+0.088** | +0.027 [+0.000, +0.056] / **+0.030** |
| M3 | -0.017 / +0.013 | -0.033 / +0.009 / -0.042 | -0.019 / +0.013 |
| M3_Cfree | -0.007 / -0.006 | +0.027 / **+0.026** / **+0.063** | -0.002 / **+0.022** |

On OLD, by contrast, PEER is far worse than margin (-0.065 to -0.077 BA under G3/LT/M3_Cfree) and random is
worse (-0.018 to -0.063). NEW's training pools are small (about 108) and contain about 9 rare points in one VX
pocket; exploration (random or PEER's far-field preference) finds that pocket more often than margin on a model
that mostly predicts Keyhole. This repeats the discovery-limited character of NEW (Weeks 12-16). It is not
evidence that a model-aware rule is better in general: the same rules lose decisively on OLD and on every
held-out world.

## Prediction scorecard (PREDICTIONS_AND_FREEZE.md)
| Prediction | Observed | |
|---|---|---|
| LT - G3 mean +0.03 (+0.01...+0.05), > 0 in >= 9/12 | +0.0086, 7/12 | failed |
| H08 within +-0.015; H09 within +-0.02 | -0.0174; -0.0202 | failed (narrowly) |
| M3 - G3 > 0 in H01/H02; <= -0.02 in H07-H09; mean <= 0 | -0.016/-0.016; -0.143/-0.120/-0.138; -0.110 | 2 of 3 parts held |
| LT - M3_Cfree > 0 in >= 8/12 | 9/12 | held |
| PEER - margin <= -0.10 (LT, G3), about -0.03 (M3), negative in >= 10/12 for every model | -0.155, -0.108, -0.026; 12, 11, 12, 12 cells | held |
| coverage - margin within +-0.01 for every model | -0.001, -0.011, -0.003, -0.008 | 3 of 4 |
| random - margin <= -0.05 for every model | -0.087 ... -0.114 | held |
| H(LT) < H(G3) in >= 8/12; mean A < 0 every model; rho(LT) > rho(G3); PEER farther in >= 10/12 | 9/12; 3 of 4 (M3_Cfree +0.0004); -0.003 vs -0.010; 12/12 | mostly held |
| common design: LT >= G3 at n = 24/48/80 (theta <= 30 deg); LT sign log loss < G3 | n = 24 yes, n = 48/80 no; log loss yes | partly |
| q20/NSD sign agreement >= 8/12 | 9/12 | held |
| NEW: LT - G3 BA in [-0.015, +0.01]; q20 +-0.01; M3 - G3 <= -0.03; Cand B - margin (G3) q20 +-0.01; PEER - margin <= -0.02 every model | -0.017; -0.010; -0.041; +0.020; +0.010/+0.030/+0.027/-0.033 | 2 of 5 |
| OLD: LT - G3 BA in [0, +0.02]; LT within +-0.01 of M3 | +0.024; -0.007 | 1 of 2 |
| verdict MODEL BREAKTHROUGH ONLY or MECHANISM RESOLVED | NO CHANGE JUSTIFIED | failed |

The two misses that matter: LT's held-out gain was a third of the forecast, and on NEW the margin control
lost to exploration, the opposite of the forecast.

## Deviations and post-hoc additions
1. Post-hoc diagnostic after the decisive run: `src/week17_lt_optimizer_check.py` (LT ML-II optimizer
   failure); labelled as such, not used in the verdict.
2. The mechanism criterion missed by 0.0024 (|LT - G3| in H08 = 0.0174 vs 0.015); the verdict follows the
   frozen rule. The mechanism findings themselves (Phase 1, oracle analysis) are reported on their merits.
3. Real model-quality tables (Phase 1) were computed during diagnosis, before the freeze, and are labelled
   POST-HOC/HISTORICAL; only the real AL runs and the synthetic held-out runs were prospective.
4. No arm, cell, seed or metric was changed after `f04d23ed`.
5. In 5 real splits the paid startup exceeded 16 queries, so B16 is missing there for all 16 arms (identical
   startup across arms; contrasts unaffected; AULC normalized by 64 as in Week 15).

## Literature / novelty
LT is a GP with explicit basis functions (O'Hagan 1978; Rasmussen & Williams 2006 sec. 2.7), not a new model
class. Expected-error-reduction / SUR acquisition: Roy & McCallum 2001; Bect et al. 2012; analytic look-ahead
level-set posteriors for Bernoulli LSE: Letham et al. AISTATS 2022. Margin's robustness on tabular data:
Bahri et al. 2022. Label shift vs covariate shift: Saerens et al. 2002. The contribution is the measured
diagnosis (saturating fixed physics prior + capped discrepancy; level vs direction shift; oracle headroom
invisible to every posterior), not a method.

## Files
- Integrity: ERRATA_OR_INTEGRITY_AUDIT.md, `integrity/`, `src/week17_audit*.py`, `src/tests/test_week17_integrity.py`.
- Diagnosis: `phase1/` (`src/week17_physics_mean.py`, `week17_diagnose_real.py`, `week17_pooled.py`,
  `week17_transfer.py`, `week17_likelihood.py`); development `development/` (`src/week17_dev.py`).
- Models and engines: MODEL_SPEC.md, `src/week17_models.py`, `src/week17_al.py`.
- Decisive: PREDICTIONS_AND_FREEZE.md, `heldout/` (`src/week17_heldout.py`, `week17_heldout_run.py`),
  `real_al/` (`src/week17_real_al.py`), VERDICT.json (`src/week17_analyze.py`), post-hoc
  `heldout/posthoc_lt_optimizer_check.csv`.
- Figures `figures/fig1-fig5` (`src/week17_figures.py`); CLAIM_LEDGER.md; THESIS_IMPLICATIONS.md.

