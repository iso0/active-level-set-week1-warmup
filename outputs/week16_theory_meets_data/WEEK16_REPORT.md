# Week 16 — Does the Astra theory operate in our models and data?

Commits: predictions freeze `ae165086` (pushed before items 1–4 ran); results: this commit.
Evidence categories: THEOREM/EXACT · CONTROLLED SYNTHETIC (development cells = Week 13 generator; Week 15
held-out cells, now *descriptive*) · POST-HOC NEW (NEW-136) · HISTORICAL OLD (OLD-405). No new real data;
nothing here is validation, and no confirmatory test was run.

## Summary
1. **Astra's results are correct as stated** (46 exact tests, including the q20 construction run through
   the historical evaluator). The generalized binary-observation lemma gives an exact, refit-free one-step
   value for latent-sign targets under the Laplace posterior (PEER), which matches Monte Carlo.
2. **Two defects in our own machinery surfaced before any result was seen.** (a) Week 15's VSUR/EBR-D
   Laplace-refit look-ahead is not martingale-consistent and is not its model's Bayes one-step value.
   (b) The Week 13 Laplace fit does not converge in the two gpworld m0 = −4 held-out cells (erratum E16-1;
   Week 15 verdict unchanged).
3. **Margin is far from optimal under its own model** (median r_model 0.41; P1 rejected). The reason is
   theoretical and visible in the data: with noisy labels of a latent target, Astra's 1/(N−1) guarantee does
   not hold (W16-1). Margin's low-value picks are aleatoric points: on the true boundary, with a pinned
   latent. They are not extrapolation decoys, and a constant or physics prior mean does not remove them
   (P3 rejected).
4. **But acting on the model's value does not recover the oracle headroom** (ΣA/ΣH between −0.08 and 0.16;
   P2 holds). V_model ranks candidates essentially independently of their true value in misspecified
   families. There margin's true one-step value is at least PEER-argmax's and above a random candidate's.
   Only in the well-specified GP world does PEER's argmax roughly double margin's one-step value (CI includes
   0). Week 15's headroom is truth knowledge, not unused model information. No freeze proposal is made.
5. **Joint calibration explains nothing beyond marginal calibration** (P4 rejected; joint and marginal log
   loss rank variants identically, 0.985). On NEW, better-calibrated variants acquire *worse* boundaries
   (descriptive).
6. **The discovery theory operates exactly on the real pools** (P5 holds). Physics tails are enriched in
   every pool, Week 12's random startups follow eq. (9)–(10), and faster discovery did not change later
   posterior quality.

## 0. Verification (THEOREM/EXACT)
**Astra's statements.** `src/tests/test_week16_astra.py` (46 tests, rational arithmetic) checks: eq. (1)
against the definition of Δ_j on random and degenerate joint laws (N ≤ 5); the 1/(N−1) bound (2) for every
margin maximizer on random laws (N ≤ 6) and its sharpness family (decoy + cluster, exact ratio
1/(M(1−2η))); κ_N (the printed table including N = 17, the root–leaf construction for N = 2…12 with fair
marginals, both labels in every world, exact equality of the uniform ratio, minimax at a leaf), the lower
bound (4) with equality iff N − 1 is a square (N < 200), and κ_N ≤ uniform ratio on random fair laws;
Prop. 5.1 with its printed decimals (Brier excess 0.0000306931, classification excess 0.000198020, gains
0.00495050 vs 0.485149); eqs. (9)–(10) against permutation enumeration and the NEW-136 reference values
(E T = 10.63446, P(T > 9) = 0.42394, P(T > 16) = 0.20787, 95%/99% budgets 29/42); the first-hit identities;
eq. (11) exhaustively for N < 16; §5.3 on the **historical q20 evaluator itself**
(`src/external_validation/analysis.py::boundary_flags`), §5.4 and the §7 parity example. All pass.

**Generalized lemma and PEER.** For binary T and O, e(T | O) = (1 − max(|E T|, |E[TO]|))/2 (exact test on
3,000 rational 2 × 2 laws). PEER, V(j) = ½ Σ_i w_i (|E[T_i O_j]| − |E T_i|)_+ with bivariate-normal
orthants under the Laplace posterior and probit observation noise 8/π (`src/week16_peer.py`), equals Monte
Carlo from the same Gaussian posterior (Pearson ≥ 0.996 on the 16 validation states where values are not
identically 0; `validation/peer_validation.csv`). Derivations: THEORY_WEEK16.md.

**PEER vs Week 15's VSUR refit look-ahead (18 states).** Spearman over candidates median 0.05 (range
−0.74 to 0.81; top-5 overlap median 0). The refit look-ahead violates the martingale property
(median Σ_i |E_y q_i' − q_i| = 1.1 per 400 targets, max 4.3), and VSUR scores are negative for more than half of
the candidates in 13 of 18 states — impossible for an exact Bayes one-step value (THEORY_WEEK16 L3). The
same holds for the Week 15 implementation (identical scores outside gpworld m0 = −4). **Week 15's
look-ahead rules (VSUR, EBR, EBR-D) were not computing their own model's Bayes one-step value**; Week 15's
negative verdict on them is a verdict on Laplace-refit look-ahead, not on exact one-step Bayes.

**Erratum E16-1 (ERRATUM_LAPLACE.md).** The undamped Newton iteration of the Week 13 `LaplaceGPC` stores an
overshoot when it oscillates. This happens in 100% of fits in the two Week 15 gpworld m0 = −4 cells and in
none of the other 23 cells (base fits; ≤ 0.23% of sampled refits in three cells), nor in the Week 13 G/M3-type
synthetic models, the Week 15 well-specified 3-D world or the NEW-136 replay model. With a safeguarded
Newton (backtracking) margin's mean NSD in those cells is 0.61/0.60 instead of 0.06/0.01. All Week 15
gpworld m0 = −4 numbers are withdrawn; the Week 15 verdict is unchanged (S2 failed on branin σ = 0 and rough
σ = 1; without the two cells EBR-D beats margin in 5/14 cells, mean −0.0148). Week 16 uses the safeguarded
fit everywhere; it reproduces every other Week 15 margin path exactly (NSD traces equal to 1e-16).

**Noisy observations (THEORY_WEEK16 W16-1).** Astra's 1/(N−1) bound relies on revealing the target itself.
For latent-sign targets observed through label noise, margin's self-value at p = ½ is
(1/π)·arcsin(s/√(s² + 8/π)) → 0 as the posterior sd s → 0, so margin's model-relative ratio can be
arbitrarily close to 0 (exact test). This is the regime of every GPC in this thesis.

## 1. Headroom decomposition (CONTROLLED SYNTHETIC; held-out cells descriptive)
1,197 states (200 regenerated margin paths × 6 budgets; in two rough σ = 0.5 paths the paid startup exceeded
budget 16 or 24, so 3 states do not exist). Tables: `headroom/summary.csv` (by family, σ, pool, budget, cell), `headroom/pick_values.csv`,
`headroom/pick_contrasts.csv` (cluster bootstrap over paths), `VERDICTS.json`; figures 2–3.

**Margin under its own model: far from model-optimal (P1 fails).** Median r_model (reference-cloud target)
over the 908 non-saturated physics-like states is **0.41** (dev 0.45, curvedMono 0.44, rough 0.17; branin
0.39, gpworld 0.36); 56–82% of states are decoys (r_model < 0.5). Pool-target r_model is similar (0.15–0.47).
Only 1 state of 1,197 was saturated (curvedMono NEW σ = 1, budget 48), fewer than forecast.

**But the model's preferred query is not better in truth (P2 holds).** Primary pairing (PEER on the
reference cloud vs the oracle's true Hamming error on the same cloud): ΣA/ΣH = −0.06 (dev), −0.004
(curvedMono), −0.08 (branin), 0.16 (rough), 0.10 (gpworld). With other objectives: pool-target PEER vs
pool Hamming −0.10…0.15; PEER vs NSD −0.17…0.09. The per-state rank agreement between V_model and V_true is
≈ 0 (median Spearman 0.03–0.11; gpworld −0.06; against NSD −0.01–0.06). The true one-step landscape is itself
nearly flat: mean H is 1.3–6.8 points of 400 (NSD 0.014–0.057) and the margin pick changes no reference
point in 36–61% of physics-like states.

Mean one-step true value of the pick (points of 400 on the reference cloud; cluster-bootstrap 95% CI for
the contrasts):

| family | margin | PEER argmax | random candidate | best candidate | PEER − margin | margin − random |
|---|---:|---:|---:|---:|---|---|
| development | 0.21 | 0.12 | 0.07 | 1.83 | −0.10 [−0.35, 0.16] | 0.14 [−0.06, 0.34] |
| curvedMono | 0.21 | 0.20 | 0.06 | 1.47 | −0.01 [−0.17, 0.17] | 0.15 [0.00, 0.30] |
| rough | 0.00 | 0.39 | 0.08 | 2.42 | 0.38 [−0.24, 1.04] | −0.08 [−0.54, 0.34] |
| branin4d | 0.68 | 0.36 | 0.12 | 4.55 | −0.32 [−0.75, 0.08] | 0.56 [0.02, 1.12] |
| gpworld (well-specified) | 0.52 | 1.19 | 0.35 | 7.27 | 0.66 [−0.22, 1.55] | 0.17 [−0.19, 0.54] |

On NSD, PEER − margin is −0.0025 [−0.0045, −0.0004] in curvedMono, −0.0016 [−0.0038, 0.0006] in dev and
+0.0038 [−0.0009, +0.0084] in gpworld; margin − random is +0.0019 [0.0001, 0.0038] (dev) and +0.0023 [0.0005,
0.0043] (curvedMono). Cells where PEER's argmax beats margin with a CI above 0 (Hamming): gpworld m0 = −4
pool 324 (+1.31), rough σ = 1 (+0.83), curvedMono OLD σ = 1 (+0.51); no cell has a CI below 0.

**Reading.** H − A is almost all of H everywhere: the one-step headroom of Week 15's expectation oracle is
truth knowledge the model does not have, not value that a better use of the model's own beliefs would
recover. The model's own value function ranks candidates essentially independently of their true value
in the misspecified physics-like families, and there margin is at least as good as PEER's argmax and
better than random. Only in the well-specified GP world does acting on the model's value roughly double
margin's one-step value (point estimate, CI includes 0). On development states argmax V_model does **not**
beat margin (mean A = −0.00024 Hamming [−0.00086, 0.00039]; −0.0016 NSD [−0.0038, 0.0006]), so — per the
brief — no freeze proposal for a PEER-based method is made.

**Real data (descriptive; realized labels).** NEW (599 states): median r_model 0.37, decoys 55%; OLD (120
states): 0.13, decoys 83%. A = V_true(argmax PEER) − V_true(margin): NEW −0.0022 test BA [−0.0056, 0.0011],
+0.0010 DC-BD [−0.0028, 0.0048]; OLD +0.0022 BA [−0.0033, 0.0080], −0.0042 DC-BD [−0.0095, 0.0009]. Rank
agreement of V_model with realized gains is slightly negative on NEW (median Spearman −0.16 for BA and
DC-BD) and ≈ 0 on OLD. Same conclusion as in synthetic misspecified families (`real_data/summary.csv`).

## 2. Decoys (P3 fails, but the mechanism is identified)
Physics-like non-saturated states, base model (`headroom/states.csv`, `headroom/decoy_sd.csv`,
`headroom/decoy_variants.csv`; fig. 4).

- **Not extrapolation.** Decoy margin picks lie outside the labelled convex hull in 64% of states — the same
  rate as non-decoy margin picks (64%), so hull membership does not distinguish them (the base rate over all
  candidates was not measured). They
  are *closer* to the labelled set than the median candidate (distance ratio 0.75 vs 0.84 for non-decoys);
  the forecast ratio ≥ 1.5 fails.
- **They sit on the true boundary with a pinned latent.** Median |true latent| at decoys 0.96 vs 2.92 at
  non-decoy margin picks; posterior latent sd at decoys 1.5–2.6 vs 4.3–5.2 at non-decoys and 4.0–6.4 at
  PEER's argmax (curvedMono 1.51 vs 4.79; dev 2.56 vs 5.21; rough 1.60 vs 4.27; branin 3.13 vs 10.46). The
  self-information ratio ρ_self = s/√(s² + 8/π) is 0.69–0.85 at decoys vs 0.94–0.96 at non-decoys;
  Spearman(r_model, ρ_self) = 0.32 over all states. These are W16-1's *aleatoric* picks: p ≈ ½ because the latent is
  known to be ≈ 0, so the noisy label cannot flip any decision.
- **A non-zero mean does not remove them.** Decoy share: zero mean 0.59, ML-II constant mean 0.63, physics
  mean 0.64 (physics-like); gpworld: true m0 0.63, zero 0.66, ML-II 0.57. Real data: NEW 0.55 → 0.58 (ML-II)
  → 0.79 (physics mean); OLD 0.83 → 0.85 → 0.84. The mean rule moves the boundary, not the aleatoric
  structure at it. The oracle value of the margin pick changes little with the mean rule (synthetic:
  NSD gain 0.0031 → 0.0039 ML-II → 0.0048 physics; Hamming 0.19 → 0.27 → 0.25 points of 400).

P3 as stated ("extrapolation decoys that a physics mean removes") is therefore rejected; the decoys are a
consequence of label noise in the model (W16-1), not of the zero prior mean.

## 3. Joint vs marginal calibration (P4 fails)
Margin acquisition fixed; 7 model variants (6 where no physics score) × 25 cells × reps 0–3
(`calibration/calibration.csv`, `cell_variant_means.csv`, `within_cell_spearman.csv`; fig. 5). Scores are
averaged over budgets {16, 32, 48, 64, 80} and reps; outcomes are margin's NSD and dense-BA AULC and the
one-step regret H at budgets {24, 48}.

| within-cell Spearman(−score, outcome), mean over 25 cells | NSD AULC | BA AULC | −H (Hamming) |
|---|---:|---:|---:|
| marginal log loss | 0.38 | 0.25 | −0.08 |
| marginal Brier | 0.52 | 0.39 | −0.04 |
| joint near-pair log loss | 0.37 | 0.27 | −0.07 |
| joint near-pair Brier | 0.48 | 0.40 | −0.03 |
| joint random-pair log loss | 0.39 | 0.29 | −0.09 |
| dependence excess (near) | −0.35 | −0.26 | 0.06 |

- Joint near-pair log loss ranks the variants almost exactly like marginal log loss (within-cell rank
  correlation 0.985). Difference in mean within-cell Spearman −0.009 (rule: ≥ 0.1); partial within-cell
  Spearman of joint near-pair log loss with NSD AULC given marginal log loss −0.011 (p = 0.89); for the
  dependence excess +0.07 (p = 0.35). **P4 is rejected.**
- No score predicts the one-step regret H (|ρ| ≤ 0.09): calibration differences between variants explain
  margin's AULC moderately but not how much one-step value margin leaves.
- Variant effects (mean ΔNSD AULC vs base): ls × 2 and var × 0.25 (smoother/flatter) −0.004 to −0.15;
  ls × 0.5 and var × 4 −0.02 to +0.03; ML-II constant mean ≈ 0; **physics mean +0.044 (curvedMono),
  +0.026 (rough), +0.012 (dev)**, also the lowest marginal log loss and the smallest H (0.0026 vs
  0.0058). Where a physics score is informative, a physics mean improves both calibration and margin's
  boundary AULC — the opposite of the M3 *transfer* failure of Weeks 12–13, because here the trend is fitted
  on the current campaign's own labels.
- Real data (descriptive; 7 variants, pooled out-of-fold per repeat; `real_data/calibration_*.csv`): on
  NEW the variants with *better* marginal log loss have *worse* margin AULC (within-repeat Spearman of −LL
  with BA −0.53, DC-BD −0.49, q20 −0.21); joint near-pair log loss behaves the same (−0.55, −0.50, −0.23);
  the dependence excess has the opposite sign (+0.54, +0.50). Sharper variants (ls × 0.5, var × 4) reach
  BA 0.68 vs 0.66 for the base G3 and 0.62 for the smoothest; the physics-mean variant reaches BA 0.681,
  q20 0.721, DC-BD 0.420 (base 0.661/0.708/0.394). On OLD all variants are within 0.008 BA. This is a
  real-data instance of Astra's Prop. 5.1 phenomenon (a better proper score does not imply better
  acquisition), not evidence for any method.

## 4. Discovery on real data (POST-HOC NEW / HISTORICAL OLD)
Tails per PREDICTIONS.md (`discovery/`). **Enrichment holds everywhere (P5 holds).** NEW (100 training
pools, N = 108–109, r = 7–12 non-Keyhole): the 5 lowest-log h points hold 55.6% non-Keyhole on average vs a
pool share of 8.8% (M = 20: 37.5%); s/M ≥ r/N and stochastic dominance D_A ≤_st D_X in 100/100 pools for
every M ∈ {5, 10, 15, 20}. Exact uniform-in-tail first-hit means 1.6 (M = 5) to 2.5 (M = 20) queries vs
10.5 for the whole pool; P(D > 3) = 0.03–0.23 vs 0.76. The deterministic order (lowest log h first) hits the
rare class at rank ≤ 4 in every pool (median 2). OLD (20 Week 8.5 training pools, N = 324, r = 58–59
Keyhole): the highest-log h tails are pure Keyhole for M ≤ 15 (99% at M = 20) — maximal enrichment, which by
Astra's caveat discovers both classes only because a common-class anchor is already present in the maximin
start.

**Observed vs exact discovery (Week 12, NEW).** Uniform random startups: mean cost 11.32 (SE 1.04) vs the
exact pool-wise mean 10.64 (eq. 10); P(T > 8) 0.48 vs 0.47; P(T > 16) 0.22 vs 0.21 — the exact law explains the
random baseline. Maximin (4.83, max 24) and adaptive physics (4.43, max 9) are far below the uniform law: the
geometric and physics orders are both "enriched" designs, and the adaptive rule's tail benefit is exactly the
eq. (11) mechanism applied after a maximin anchor.

**Posterior quality at discovery (§6.4).** From the stored Week 12 predictions: `maximin8` and
`adaptive_physics8` have identical query sets through B16 in 94/100 pools (identical predictions). In the 6
pools where they differ, adaptive reaches T earlier (mean 9.0 vs 15.7) and is better at B16 (test log loss
0.299 vs 0.359, accuracy 0.877 vs 0.865) but worse at B40 (0.280 vs 0.256; minority recall 0.083 vs 0.167).
Faster discovery did not determine later refinement quality — consistent with Astra §5.4/§6.4, and with the
Week 12 null contrast (−0.000313 q20 AULC). Six pools: descriptive only.

## 5. Which parts of Astra's theory operate here
| Astra statement | Operates in our models/data? | Evidence |
|---|---|---|
| Eq. (1): query value = decisions flipped (self + elsewhere) | **Yes, and it explains the scale of everything.** One-step values are positive-part sums over decision flips; under the fitted models most candidates flip little, and under the truth the best single query changes 1.3–6.8 of 400 reference points while margin's pick changes none in 36–61% of physics-like states | §1; THEORY L1 |
| Eq. (2), sharp 1/(N−1) for margin | **Not as stated.** It assumes the query reveals the target itself. Our GPCs observe noisy labels of a latent-sign target; margin's model-relative ratio has median 0.41 and can be ≈ 0 (W16-1). The low-ratio picks are exactly the aleatoric points W16-1 predicts | §1, §2; THEORY W16-1 |
| Theorem 2 / κ_N (marginal-only minimax at p ≡ ½) | **Not testable here and not the operative regime.** Posteriors are not all ½, selectors are not marginal-only, and geometry is informative (margin beats a random candidate in truth in dev/curvedMono). It stays a worst-case bound | §1 |
| Prop. 5.1 (better predictor, worse query) | **Partly.** In synthetic cells marginal and joint log loss both track margin's AULC in the same direction (better calibration ↔ better AULC); on NEW the better-calibrated variants have *worse* BA/DC-BD AULC under margin (Spearman −0.53/−0.49), a real-data instance of the phenomenon (descriptive) | §3 |
| Cor. 6.1 (marginals + pairwise moments control regret) | **Yes, in its contrapositive.** Where the model's pairwise structure is wrong (misspecified physics-like families, real data), its value function is uninformative about true value (Spearman ≈ 0) and acting on it does not reduce regret; only the well-specified GP world shows a (one-step, CI-inclusive) gain | §1, §3 |
| §5.2 (no guarantee for disjoint targets) | Consistent: reference-cloud, pool and NSD objectives give the same picture | §1 |
| Eqs. (9)–(11), first-hit, minimax discovery | **Yes, exactly.** Uniform-random Week 12 startups follow eq. (9)–(10); physics tails satisfy the enrichment condition in every pool, which is why the adaptive rule's tail is short | §4 |
| §5.4/§6.4 (T is not a sufficient refinement state) | **Yes.** Equal or faster discovery leaves later posterior quality unchanged or mixed (94/100 identical; 6 mixed) | §4 |
| §5.3 (q20 can reverse geometry) | Construction verified on the historical evaluator; no new data needed | §0 |

**What this says about Week 15.** The expectation-oracle headroom is not margin "leaving model-visible value
on the table": acting optimally on the model's own one-step value recovers ≈ 0 of it outside the
well-specified world (A/H ≈ 0), so it is truth knowledge the models lack. Week 15's look-ahead rules failed for
two separate reasons now identified: (i) their Laplace-refit look-ahead is not a coherent Bayes value (L3),
and (ii) even the coherent value is uninformative in misspecified families. (ii) is the binding constraint:
a better look-ahead computation would not have rescued EBR-D/VSUR there. *Interpretation (not tested):*
margin's robustness may come from ignoring the model's (wrong) dependence structure and using only the
marginal, which in these families appears to be the more reliable part of the posterior.

## Deviations from PREDICTIONS.md
1. Item 0 used 18 validation states (brief: ≈ 20); PREDICTIONS cites "15 states" for the PEER–MC check from
   the first validation run; the re-run with safeguarded fits has 16 states with non-constant values (all ≥ 0.996).
2. Item 3 synthetic was run on reps 0–3 (PREDICTIONS fixed no rep count; compute), with a 60-candidate cap
   for its regret H (item 1 used 120).
3. P3's decision rule refers to "both decoy-location conditions"; they were read as the forecast thresholds
   (outside-hull share ≥ 0.6 and distance ratio ≥ 1.5). The rejection does not depend on this reading:
   the decoy share is not lower under ML-II or physics means either.
4. Additional analyses not named in PREDICTIONS (descriptive, labelled as such): pick-value contrasts with a
   random-candidate baseline (`pick_contrasts.csv`) and posterior sd at the picks (`decoy_sd.csv`).
5. Erratum E16-1 led to the safeguarded fit; this was decided and documented before PREDICTIONS.md.

## Files
- Theory and checks: THEORY_WEEK16.md, `src/week16_astra.py`, `src/week16_peer.py`,
  `src/tests/test_week16_astra.py`, `src/tests/test_week16_peer.py`; Astra note `outputs/astra_round1/ASTRA_ROUND1.md`.
- Item 0: `validation/peer_validation.csv` (`src/week16_validate.py`); `laplace_audit/` (`src/week16_laplace_audit.py`), ERRATUM_LAPLACE.md.
- Item 1–2: `headroom/` (`src/week16_cells.py`, `src/week16_headroom.py`, `src/week16_contrasts.py`, `src/week16_decoy_sd.py`).
- Item 3: `calibration/` (`src/week16_calibration.py`); real data `real_data/` (`src/week16_real.py`).
- Item 4: `discovery/` (`src/week16_discovery.py`).
- Decisions: PREDICTIONS.md (frozen `ae165086`), VERDICTS.json (`src/week16_analyze.py`); figures `figures/` (`src/week16_figures.py`); CLAIM_LEDGER.md.
