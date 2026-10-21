# HA_TREND + margin: equations, algorithm and reproduction

## Notation

| symbol | meaning |
|---|---|
| x = (P, VX, LS, ST) | public inputs |
| z(x) | log inputs standardised on the candidate pool |
| z_h(x) | log h = log P − ½ log VX − 3/2 log LS, standardised on the pool |
| L | the paid set at budget b; for j ∈ L, the paid outcomes are y_j ∈ {0, 1}, a_j (log active maximum depth; may be missing) and q_j (short-record flag) |

## 1. Physics-anchored depth emulator

Model (targets standardised on the paid complete records):

  a_j = μ + θ z_h(x_j) + g(x_j) + e_j,
  θ ~ N(0, b²) with b = 3 (fixed),
  g ~ GP(0, s_f² k(x, x′)),
  k = Matérn-3/2 with ARD lengthscales ℓ on z,
  e_j ~ N(0, s_n² w_j), w_j = 10⁴ if q_j else 1.

Integrating θ gives the covariance

  C(x, x′) = s_f² k(x, x′) + b² z_h(x) z_h(x′).

The hyperparameters (s_f², ℓ, s_n²) maximise the log marginal likelihood (L-BFGS-B; bounds as in `src/rc18_gp.py`).

The predictive mean at x is m(x) = μ + c(x)ᵀ (C_L + s_n² W)⁻¹ (a_L − μ). Far from the data, m(x) → μ + θ̂ z_h(x), where θ̂ = b² z_hᵀ (C_L + s_n² W)⁻¹ (a_L − μ). This was validated numerically (V3, relative error 1e-14).

## 2. Honest stacking

- The folds are f(j) = j mod K over the query order, with K = min(10, |L|).
- Each fold model is fitted on L \ fold, including its own hyperparameters and normalisation.
- For a paid run j, the feature is the out-of-fold prediction Â_j = m_{−f(j)}(x_j).
- For an unqueried x, the feature is Â(x) = m(x), the full fit.

## 3. Learned-regularisation classifier

- **Features:** u = [z_h, Â], standardised on the paid rows. The latent is f(x) = b₀ + β_h ũ_1 + β_A ũ_2.
- **Priors:** b₀ ~ N(0, 10²), β_h ~ N(0, τ_h²), β_A ~ N(0, τ_A²). Equivalently, the kernel is K = 100 + τ_h² ũ₁ũ₁′ + τ_A² ũ₂ũ₂′.
- **Fit:** for each g = (τ_A, τ_h) ∈ {0.5, 1, 2, 4}², the Laplace mode f̂_g is computed (Newton iteration; GPML Alg. 3.1, logistic likelihood) together with the log evidence log Z_g.
- **Weights:** w_g ∝ exp(log Z_g).
- **Prediction:** m_g(x) = k_g(x, L)ᵀ (y − σ(f̂_g)), and

  p(x) = Σ_g w_g σ(m_g(x))   (plug-in per configuration).

- **One-class rule:** until both classes are present among the paid runs with a depth, p is the paid class rate.

## 4. Acquisition (margin)

- Next query: argmax over the unpaid candidates of −|p(x) − ½|, first index on ties.
- Before both classes are paid, the next query is the next point of the label-free maximin startup path.

## 5. Algorithm

```
pay the 8 startup runs (label-free maximin order of the pool)
for b = 8 .. B_max:
    if both classes are paid:
        fit the physics-anchored emulator on the paid depths (full fit + K honest fold fits)
        fit the 16 Laplace classifiers on [z_h, OOF depth], weight them by evidence
        p(x) for the test rows and the candidates
        query argmax_x -|p(x) - 1/2| among the candidates
    else:
        query the next point of the maximin path; p = paid class rate
```

- Cost: about 0.2 s CPU per step at n ≤ 60 (one CPU thread).
- Variant HT_PHYS: replace the query line with the margin of the h-only classifier (Section 3 with u = [z_h] only).

## 6. Reproduction (from the repository root, branch joint-depth-label-dev)

| step | command | output |
|---|---|---|
| decision-rule correction | `python -m src.rc24_correction decision` / `witness` | `correction/` |
| Stage A acceptance | `python -m src.rc24_validate` | `validation/RC24_STAGE_A_VALIDATION.json` |
| Stage B acceptance | `python -m src.rc24_validate_b` | `validation/RC24_STAGE_B_P1_VALIDATION.json` |
| queue | `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc24_start_runner.ps1` (jobs in `runner/PLAN.json`; idempotent, checkpointed) | unit folders |
| one job by hand | `python -m src.rc24_jobs work a-own`, `python -m src.rc24_confirm work c-own`, `python -m src.rc24_synth work s-test` | `<job>/units/*.json.gz` |
| reports | `python -m src.rc24_report stage_a` / `stage_c`; `python -m src.rc24_synth_eval s-test`; `python -m src.rc24_hard verify` / `mechanism` | `stage_a/`, `stage_c/`, `synthetic/`, `hard_region/` |
| freeze checks | `python -m src.rc24_freeze check a-own` / `c-own` / `s-test` | stage manifests in `freeze/` |

Data:
- `outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv`, hash-frozen.
- The per-frame labels for the hard-region mechanism are read only from `data/raw/sph_v2/2e1eec9c…/labels_new_data_4_prep.csv`, the Hugging Face ioandanielc/sph_v2 revision 2e1eec9c (git-ignored).
