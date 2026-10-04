# Week 15 freeze — committed before any held-out or real-data result

## Development history (designated development families only)
Week 13 generator (BAL/OLD/NEW, σ ∈ {0, 0.5, 1}, pool 108, 8 reps) and a well-specified 3-D GP world.
1. Expectation oracle (no label peeking): beats margin by 0.050/0.074/0.076 NSD AULC; peeking adds only
   0.003/0.000/0.028 → the Week 14 headroom is mostly attainable *with knowledge of the truth*.
2. EBR (unnormalized expected error-set perimeter): ≈ margin without noise, catastrophic in NEW-like
   σ = 1 (0.267 vs 0.747). Mechanism: Proposition B3 (size bias). **One principled revision: EBR-D**
   (Dice-normalized). EBR-D removes the catastrophe (0.669) but remains below margin in all 9
   development cells (mean −0.002 to −0.078).
3. VSUR, BALD and coverage are also ≤ margin on the development family.
4. Oracle-alignment: no legal criterion correlates with the oracle's per-candidate gain (|ρ| ≤ 0.27).
5. Well-specified GP world: EBR-D +0.0099 and exact Bayes look-ahead +0.0097 NSD AULC over margin
   (7/12 and 6/12 reps); ASSD −0.026 [−0.065, 0.006] and −0.035 [−0.072, −0.004]; VSUR −0.007.
**Pre-stated expectation:** EBR-D is unlikely to beat margin on physics-like noisy families and may
help in well-specified worlds. The frozen test can refute either expectation.

## Exact method (main): EBR-D
- Model: fixed-hyperparameter logistic Laplace GPC, Matérn-3/2 ARD (oracle hyperparameters fitted once
  per family/cell by ML-II on 500 labelled cases; the GP world uses its true prior incl. the constant
  mean m0), `src/week15_ebr.py: make_gp`.
- Reference cloud: N_REF = 400 points uniform in the unit model box (seed [15, 99]); symmetric kNN graph,
  K_REF = 8. For real data: uniform in the training pool's bounding box (seed [15, 97]).
- Edge probabilities: Laplace posterior marginals and pairwise correlations; bivariate-normal orthant
  probabilities via Owen's T (`bvn_lower`).
- Risk R_D(D) = Σ_e P(mismatch_e) / (Σ_e P(true cut_e) + Σ_e 1[predicted cut_e]) (`edge_dice_risk`).
- Acquisition: argmax over all unlabelled pool cases of R_D(D) − Σ_y p_D(y|c) R_D(D ∪ (c,y)), with p_D the
  model's predictive probability and a full refit per fantasy (`lookahead_scores(kind="EBRD")`).
- Startup shared with every policy: 8 maximin points + maximin continuation until both classes.

## Ablation: VSUR
Same look-ahead machinery with R = Σ_z min(q_z, 1 − q_z), q_z = Φ(μ_z/s_z) (expected misclassified latent-sign volume).

## Comparators
random; margin; coverage (Candidate-B-like: physics-score band + rank(uncertainty) + rank(distance)
before B40 where a physics score exists, band-free otherwise); BALD; expectation-oracle reference on two
cells (curvedMono NEW σ = 1 pool 108 and gpworld m0 = −4 pool 108, 4 reps; unattainable).

## Held-out families and cells (`src/week15_heldout.py: CELLS`, 16 cells, 8 reps each)
gpworld m0 ∈ {0, −4} × pool {108, 324}; curvedMono box {OLD, NEW} × σ {0, 0.5, 1} × pool 108 and NEW ×
σ {0.5, 1} × pool 324; branin4d σ {0, 0.5}; rough σ {0.5, 1}. Seeds `[152, …]`. Budgets 16–80 step 4.

## Endpoints
Primary: true-boundary NSD (τ = 0.1, unit box) AULC 16–80 and ASSD AULC. Also NSD τ = 0.05, q20 accuracy
(historical construction), balanced accuracy, flipped-label share among acquired cases.

## Success criteria (`src/week15_analyze.py`)
- S1 EBR-D NSD AULC > margin in > 50% of cells and ASSD AULC < margin in > 50% of cells.
- S2 no catastrophe: no cell with EBR-D − margin NSD AULC < −0.05 and no cell with ASSD ratio > 1.5.
- S3 noisy cells (σ > 0, gpworld, rough): mean EBR-D − margin NSD > 0 and margin's flipped share exceeds
  EBR-D's in > 50% of them.
- S4 noise-free cells (curvedMono σ = 0, branin σ = 0): |EBR-D − margin| ≤ 0.01 in each.
- S5 identical startup across policies in every (cell, rep).
- S6 mean EBR-D − margin NSD > 0 within pool 108 and pool 324 cells, and within imbalanced
  (gpworld m0 = −4, NEW box, rough, branin) and balanced/OLD-like cells.
- Verdict: all of S1–S6 → **METHOD BREAKTHROUGH**; else if S2 and [gpworld or noisy group has mean > 0
  with ≥ 2 cells whose 95% paired bootstrap CI is above 0] → **USEFUL BUT NOT DOMINANT**; else →
  **NO NEW METHOD JUSTIFIED**.

## Metric (DC-BD) held-out criteria (`src/week15_metric_confirm.py`, `week15_analyze.py --metric`)
Shapes sphere d = 3, 5 and two-component d = 3; designs uniform / smoothA / smoothB / denseA / denseB;
n 136/405; 20 reps. r = twice the median 5-NN distance; kNN density with k = round(√n) (≥ 5); weights
trimmed at the 95th percentile.
- M-a: DC-BD density sensitivity < unweighted r-graph BD and < q20 accuracy in every smooth cell.
- M-b: DC-BD rank agreement with −ASSD ≥ q20 accuracy's in every non-band cell.

## Real-data secondary (`src/week15_real.py`, descriptive only)
NEW-136 100 original partitions (POST-HOC), OLD Week 8.5 repeats 1–4 (HISTORICAL), Masinelli Ti64/316L
5-fold × 4 (EXTERNAL); policies random, margin, EBR-D; q20 accuracy, pooled BA, pooled DC-BD, minority
recall. No real-data result can change the verdict.
