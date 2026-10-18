# RC18 D2 — native-time phase model for temperature and kinetic energy (frozen before its final run)

**Code:** `src/rc18_temporal.py`. **Data:** the 1-µs native bins of the RC18 data layer (fix A2/A3). **Evidence label:** DEV, final repeats 5–8 (as `PROTOCOL_20261018.md`). Populations are evaluated separately.

## Question

Can the time structure of the maximum melt temperature and the melt kinetic energy be predicted from x in native time — onset, rise, peak amplitude and timing, plateau and fluctuation — with alignment learned from training curves and predicted from x alone? Does a curve model add anything over direct scalar GPs for the same quantities?

**Motivation, measured in RC18-A2A3:** the earlier 40-bin onset-normalised median curve keeps only 0.37 (median) of the native NEW velocity peak and 0.95 of the temperature peak, with peak-time errors of 0.07–0.10 ms. Here everything is evaluated in native time.

## Phase features (per run; definitions in the module docstring)

- **Curve:** a 5-µs block-median curve c(τ), with τ = t − t_on in native ms, from the 1-µs bin medians (valid rows only), inside the active window [t_on, cutoff].
- **Features:**
  - t_on (onset after the laser start);
  - plateau (T0 median of c; log for KE);
  - t90 (first τ with c ≥ 0.9 × plateau);
  - peak and peak_ms over the active window;
  - overshoot = peak / plateau;
  - fluct = (p90 − p10) / plateau over T0;
  - epeak and epeak_ms (peak inside the early horizon τ ∈ [0, 0.25 ms]).
- **Early-horizon curve:** E = c on 50 blocks of 5 µs over [0, 0.25 ms]; every active window is longer than 0.27 ms.
- **QA:** truncated records (Q rule) are excluded from the curve-template training rows and down-weighted in the scalar GPs. They stay in evaluation.

## Models

**Scalar GPs** for each feature:
- M0;
- RICH: NEW → TRSQ with OLD-campaign feature emulators as the prior mean; OLD → SHQ.

**Curve models** on the early horizon:

| Model | Definition |
|---|---|
| MEAN | mean paid curve |
| KRONn | the separable exact Kronecker GP of pilot C, Matérn x ⊗ Matérn τ, on the NATIVE τ grid |
| PHASE | shape-invariant model: template ḡ(u) on u = τ / t90 (mean of the paid runs' normalised curves, c / plateau for temperature and c − plateau in log for KE), reconstructed with the x-predicted t90 and plateau of the scalar GP (M0 or RICH) |
| PHASE_PCA | PHASE plus up to 3 aligned-shape PCA scores (90 % variance), one GP each |

**Leakage guard:** a test run's alignment (t90) and level are predicted from x only; its own curve is never used.

## Design and endpoints (exploratory; no superiority claim without the rule below)

**(a) Feature learning curves.** MAXIMIN path (b ≥ 0 for TRSQ, b ≥ 3 otherwise) to B60, for M0 and RICH:
- R²(b) per feature;
- R²-AULC over B8–B60;
- sustained budget-to-target, with level 0.9 × R²_full(M0).

**(b) Curve models** at budgets B16 and B40 of the MAXIMIN path and with the whole pool (upper bound):
- early-horizon native RMSE and R²_curve = 1 − SSE / SSE_MEAN;
- |peak error| and |peak-time error| of the curve-derived early peak;
- for comparison, the direct scalar GP errors for epeak, epeak_ms and t90.

**Rules:**
- **PHASE BEATS KRONn** for a channel iff PHASE or PHASE_PCA curve RMSE ≤ 0.95 × KRONn in ≥ 3 of 4 repeats (whole pool).
- **TEMPORAL BEATS SCALAR** for a quantity iff the curve-derived error ≤ 0.95 × the scalar GP error in ≥ 3 of 4 repeats.
- **Cost:** the CPU seconds of each fit are reported.

## Disclosure

- The features were computed on all runs before this freeze, without any model comparison.
- In development (repeats 1–2), only feasibility and timing were checked.
