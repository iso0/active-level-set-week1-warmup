# Week 16 predictions (committed before items 1–4 are run)

Date 2026-10-04. Committed after item 0 (exact verification, PEER validation, Laplace audit) and before any
computation of margin's model value (r_model), oracle values (V_true), headroom splits, calibration scores
or real-data enrichment. The analysis code for items 1–2 (`src/week16_headroom.py`) is committed with this
file; code for items 3–4 follows and must implement the definitions below.

## What was already seen (item 0; it informs the forecasts)
1. All Astra statements checked exactly (`src/tests/test_week16_astra.py`, 46 tests): eq. 1, the 1/(N−1)
   bound and its sharpness family, κ_N (table, construction for N ≤ 12, lower bound (4)), Prop. 5.1 incl.
   the printed decimals, eqs. 9–11, NEW-136 reference values, §5.3 on the historical q20 evaluator, §5.4, §7.
2. PEER closed form = Monte Carlo from the same Gaussian posterior (Pearson ≥ 0.996 on 15 states).
3. PEER vs VSUR refit look-ahead (Week 15 implementation and safeguarded refits): Spearman over candidates
   from −0.74 to +0.81, median ≈ 0; VSUR scores are negative for most candidates in most states, and the
   refit look-ahead violates the martingale property (median Σ_i |E_y q_i' − q_i| from 0.3 to 4.3 per
   400 targets). Exact Bayesian one-step values cannot be negative, so **Week 15's look-ahead rules were not
   computing the Bayes one-step value of their own model**.
4. In some states the model's coherent one-step Hamming value is ≈ 0 for every candidate (curvedMono NEW
   σ = 1: the model is confident on the whole reference cloud). These states are called *saturated*.
5. Erratum E16-1: non-converged Laplace fits in the gpworld m0 = −4 cells (see ERRATUM_LAPLACE.md).
   All Week 16 analyses use the safeguarded fit.

## Operational definitions
- States: regenerated Week 15 margin paths (seeds unchanged), budgets {16, 24, 32, 48, 64, 80}, reps 0–7, on
  the 9 development cells (Week 13 generator; BAL/OLD/NEW × σ ∈ {0, 0.5, 1}) and the 16 Week 15 held-out
  cells (now descriptive). *Physics-like families*: development cells, curvedMono, rough.
- V_model(j): PEER under the fitted model; target (b) the 400-point reference cloud (primary; gpworld uses
  the first 400 dense truth points), target (a) all pool points. r_model = V_model(margin)/max_j V_model(j);
  undefined (state reported as saturated) when max_j V_model < 1e-6.
- V_true(j): expectation oracle with the same refit model; primary objective = true Hamming error on the
  reference cloud (matched to target b); also pool latent-sign Hamming (matched to a), dense error rate and
  NSD τ = 0.1. Pool-324 cells: all candidates for V_model, 120 for V_true (always including the margin and
  both V_model argmaxes); H is then a lower bound.
- H = max V_true − V_true(margin); A = V_true(argmax V_model) − V_true(margin). Aggregate A/H = ΣA/ΣH over
  states of a group (primary), also median of per-state ratios over states with H > 0.
- Decoy: margin pick with r_model(ref) < 0.5. Features: distance to nearest labelled point (model units)
  relative to the state's median candidate distance; |true latent|; outside the labelled convex hull (LP).
  Mean variants at the same states: zero/base mean, ML-II constant mean (Laplace evidence, kernel fixed),
  physics mean b0 + b1·s(z) (L2-logistic on the labelled set, C = 1) where a physics score exists.
- Item 3 variants (margin acquisition, each variant's own path): base, ls × 0.5, ls × 2, var × 0.25,
  var × 4, ML-II constant mean, physics mean (where available). Scores at budgets {16, 32, 48, 64, 80} on the
  reference cloud's true latent signs: marginal log loss and Brier; joint near-pair log loss and Brier on
  the reference cloud's 8-NN graph edges; joint random-pair log loss on 2,000 fixed random pairs; dependence
  excess = joint − sum of marginal log losses. Outcomes: margin NSD AULC 16–80 (step 4), dense-BA AULC, and
  one-step regret H (ham_ref) at budgets {24, 48}. Real data: G3 base, M3-type physics mean (log h),
  ls × 0.5, ls × 2, var × 0.25, var × 4, ML-II constant mean; outcomes realized test BA AULC, q20 AULC,
  DC-BD.
- Item 4: tails = the M lowest-log h points (NEW; rare class non-Keyhole) or the M highest-log h points
  (OLD; rare class Keyhole) of each training pool, M ∈ {5, 10, 15, 20}; enrichment s/M vs r/N; exact
  first-hit and T_both laws (eqs. 9–11) vs the observed Week 12 discovery costs; posterior quality at T and
  at B16 from the stored Week 12 predictions of `M3_margin__maximin8_continue` vs
  `M3_margin__adaptive_physics8` (pools where the startups differ).

## Hypotheses (from the brief) and our numeric forecasts
| # | Hypothesis as stated | Our forecast (point / range) | Decision rule |
|---|---|---|---|
| P1 | median r_model ≥ 0.8 in physics-like families | median r_model(ref) ≈ 0.6 (0.4–0.8); ≥ 20% of non-saturated states are decoys; saturated share ≥ 10% at B ≥ 48 in σ = 0 cells | holds iff the median over non-saturated physics-like states ≥ 0.8 |
| P2 | A/H < 0.25 except gpworld | ΣA/ΣH ≈ 0.10 (0.0–0.25) in physics-like families, branin and rough; gpworld 0.25–0.5 | holds iff ΣA/ΣH < 0.25 in every non-gpworld family (dev, curvedMono, branin, rough) |
| P3 | low-r_model picks lie in extrapolation regions under zero mean; their share drops with a non-zero/physics mean | decoys: outside hull ≥ 60%, distance ratio ≥ 1.5; decoy share drops by ≥ 25% (relative) with ML-II or physics mean | holds iff both decoy-location conditions hold in pooled physics-like states and the decoy share is lower under ML-II and physics mean |
| P4 | joint near-pair log loss tracks margin AULC better than marginal log loss | fails: within-cell Spearman(−JLL_near, NSD AULC) − Spearman(−LL, NSD AULC) < 0.1; partial correlation ≈ 0 | holds iff mean within-cell difference ≥ 0.1 **and** pooled within-cell partial Spearman (JLL_near vs AULC given LL) has |ρ| ≥ 0.2 with p < 0.05 |
| P5 | physics tail enriched on both real pools | holds: s/M ≥ r/N in ≥ 95% of training pools for every M on NEW and on OLD | holds iff ≥ 90% of pools satisfy enrichment at every M on both campaigns |

Additional forecasts (not hypotheses): the median per-state Spearman(V_model, V_true ham_ref) is 0.1–0.4;
V_true(margin)/max V_true median 0.3–0.7; posterior quality at B16 does not differ between maximin8 and
adaptive8 by more than 0.02 test BA.

## Discipline
- If argmax V_model beats margin on development states: descriptive report and a freeze proposal for new
  held-out families only; no confirmatory test this week.
- No hypothesis is re-defined after seeing results; deviations are logged in WEEK16_REPORT.md §Deviations.
- Real-data analyses are descriptive (NEW = POST-HOC, OLD = HISTORICAL); none is validation.
