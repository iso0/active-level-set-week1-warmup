# TEMPORAL_STRUCT (Study 3) — structured temporal GPs for monitor curves

**Status: REGISTERED BEFORE ANY TEMPORAL_STRUCT OUTCOME.** Owner approval of 2026-10-17.
- **Mandate:** Ioan, 2026-10-15: "try the temporal Gaussians for the monitor data … 5d and time is a dimension … maybe you'll find some paper where they have some structure for the temporal dimension".
- **Code:** `src/jdl_temporal_struct.py`.
- **Manifest:** `TEMPORAL_STRUCT_MANIFEST.json`.
- **Starting point:** pilot C's Kronecker GP (velocity). Its curves fit reasonably (R²_curve 0.64), but it got peak timing wrong.

## Curves

- **Channels:** three, each as the log of the bin median over K = 40 equal bins of onset-normalized active-window time τ (as in pilot C):
  - maximum melt velocity;
  - melt kinetic energy;
  - melt-pool depth, i.e. max(0, −z_min).
- **Rows used:** post-onset valid active rows.
  - Non-finite values, velocities above 100 m/s and non-positive values are excluded from the bin statistic only.
  - OLD bounds files use Week 7's rule for the known malformed sentinel token.
- **Availability:** a run missing any of the 40 bins of a channel is UNAVAILABLE for that channel, and this is recorded.

## Models

All models are fitted out of fold on DEV repeats 3–4, training on the fold pool with every pool run revealed. This gives an upper bound, not an acquisition result.

| Model | Structure | Literature |
|---|---|---|
| MEAN | per-bin training mean | baseline |
| KRON | separable 5-D GP: Matérn 3/2 ARD in x ⊗ Matérn 3/2 in τ, exact Kronecker ML-II (pilot C, unchanged) | separable covariance of multi-output and dynamic emulators (Conti & O'Hagan 2010) |
| PCA | basis emulator: PCA of the centred curves (k reaching 95% of the variance, k ≤ 10), then one GP per score, then reconstruction. The variance comes from the score variances plus the residual variance. | Higdon et al. (2008) |
| FULL5D | non-separable GP on (x, τ) jointly, with Matérn 3/2 ARD over all 5 dimensions. It is fitted on every 4th bin, NEW only, because of cost. | Ioan's literal "time is a dimension" |
| SCALAR | a direct GP on each derived scalar | decisive control for the derived quantities |

**Derived quantities**, computed from each predicted curve and from each observed curve:
- the T0 level (mean of the last 8 bins);
- the peak height (maximum bin value);
- the peak position (argmax bin).

## Endpoints (fixed)

- **Measures:**
  - curve RMSE and R²_curve = 1 − SSE_model / SSE_MEAN, per channel and repeat;
  - 90% pointwise coverage;
  - derived-quantity RMSE (T0 level, peak height) and mean |peak-position error| in bins;
  - fit cost.
- **Verdict: STRUCTURE HELPS** for a channel iff PCA beats KRON on curve RMSE by ≥ 5% in both repeats. FULL5D is compared with KRON on the same subgrid.
- **Verdict: TEMPORAL BEATS SCALAR** for a derived quantity iff the better temporal model's RMSE is ≤ 0.95 × SCALAR's in both repeats.
  - Otherwise the temporal model adds nothing for that quantity, which is a valid answer.
- **Populations:** NEW and OLD are reported separately.

## Limits

- This is DEV work, and revealing all pool runs makes the result an upper bound.
- The bin medians smooth very short spikes. Peak height is therefore the peak of the median curve, consistently for every model and for the observed curve.
- Validation checks:
  - the PCA identity;
  - that the PCA and FULL5D models run;
  - curve extraction for all three channels;
  - the derived-quantity definitions.
