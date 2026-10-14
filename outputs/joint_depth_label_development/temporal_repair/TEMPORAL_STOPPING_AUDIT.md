# Temporal stopping-rule audit: what the frozen SVGP stopping statistics measure

## Status
- **Diagnostic only.** It inspects `src/jdl_temporal_svgp.py` (frozen in `29ca7364`; byte-identical since, apart from the scheduling-only `__main__` block of T-A2).
- **Nothing is changed.** No fit is relabelled, restarted or discarded. Every fit keeps its recorded status `max_iterations`, and the frozen rule stays the rule of this study.
- **Inputs:** stored traces (`svgp_ngd_fits.jsonl`) and the checkpoint training targets. Per-fit numbers are in `stopping_audit_per_fit.csv` and `stopping_audit_summary.json` (`python -m src.jdl_temporal_stopping_audit`).

## 1. Question 1: what does the reported probe ELBO measure?

**How it is computed.**
- **Training objective:** each Adam/NGD step minimises `-VariationalELBO(likelihood, model, num_data = n)` on a minibatch of 1024 of the n training points.
- **gpytorch 1.15.1** (`_ApproximateMarginalLogLikelihood.forward`) returns

  $$\widehat{\mathcal L}_{b}=\frac1{|b|}\sum_{i\in b}E_{q}\big[\log p(y_i\mid f_i)\big]-\frac{\mathrm{KL}\{q(u)\,\|\,p(u)\}}{\texttt{num\_data}}$$

  There are no hyperpriors or added loss terms in this model. With `num_data = n`, this is an unbiased minibatch estimate of the per-point training ELBO

  $$\mathcal L/n=\overline{E_q\log p}_{\,\text{all }n}-\mathrm{KL}/n .$$
- **Probe check:** every 250 iterations the model is evaluated, deterministically and without minibatch noise, on a fixed probe set of m = min(8192, n) training points, with a new `VariationalELBO(likelihood, model, num_data = m)`.

**What the reported value is.**

$$\text{ELBO}_{\text{probe}}=\overline{E_q\log p}_{\,\text{probe}}-\mathrm{KL}/m .$$

- **Not the training objective.** It is the per-point ELBO of the probe subset treated as if it were the whole data set: the same variational posterior, but with the KL term weighted n/m times more heavily than in the training objective.
- **When the two coincide:** if n ≤ 8192, the probe is the whole training set and m = n, so the probe value is exactly the full-data per-point ELBO.
- **When they differ (n > 8192):**
  - The probe value is lower than the per-point training ELBO by KL·(1/m − 1/n), up to the sampling difference between the probe mean and the full mean of the expected log-likelihood.
  - A change in KL moves it n/m times more than it moves the training objective.
  - The relative-change test |ΔELBO_probe| / max(1, |ELBO_probe|) ≤ 5e-4 therefore monitors a KL-up-weighted objective, not the quantity being optimised.
- **What follows:**
  - The values reported as "final probe ELBO per point" (for example 1.08 for the frozen 2000-iteration fit against 1.68 for NGD at the cap) are comparable only between fits with the same n and m. They are not values of the optimised objective.
  - The monitored statistic is still a deterministic function of the parameters, so its check-to-check fluctuations reflect parameter movement under stochastic optimisation, not evaluation noise.
- **No stopping decision changed:** under either scaling, the per-check relative changes stayed far above 5e-4 (§3).

## 2. Question 2: in which units is the mean-change tolerance applied?

**Units.**
- The training targets are standardized: y = (log1p depth − ȳ) / s_y, with s_y the standard deviation of the checkpoint's training targets in log1p units.
- The probe predictive mean `f.mean` is in these standardized units, and so is the RMS change between checks.
- The protocol text and the module docstring call the 5e-3 tolerance "log1p units".

**Conversion.** RMS_log1p = s_y · RMS_std, so the tolerance actually applied in log1p units is 5e-3 · s_y.
- s_y > 1: the implemented test is looser than documented.
- s_y < 1: it is stricter.
- The per-fit s_y and the equivalent log1p tolerance are in `stopping_audit_per_fit.csv`. Whether reading the tolerance in log1p units would have stopped any fit is in `stopping_audit_summary.json` (§3).

## 3. Numbers

From queue T16 (`stopping_audit_summary.json` and `stopping_audit_per_fit.csv`, commit `b3c1c6ac`), over all 40 SVGP fits.

| Quantity | Value |
|---|---|
| Fits / recorded `converged` | 40 / 0. All stopped at the 20,000-iteration cap, i.e. 80 probe checks each |
| Fits whose probe value is the training objective (n ≤ 8192: the ten B16 checkpoints) | 10 |
| KL weight ratio n/m over all fits | 1.00–2.87 |
| s_y, the target SD in log1p units | 1.97–2.08 |
| Implemented 5e-3 mean tolerance expressed in log1p units | 0.0098–0.0104, about twice as loose as documented |
| Relative probe-ELBO change over the last 12 checks: per-fit medians (median over fits) | 0.0024–0.0192 (0.0053), 4.7–38× the 5e-4 tolerance |
| Checks per fit meeting the ELBO tolerance | median 2 of 80, at most 6 |
| Probe-mean RMS change over the last 12 checks: per-fit medians | 0.0130–0.0195 standardized (0.026–0.040 log1p) |
| Checks meeting the mean tolerance, in either unit reading | **0 in every fit** |
| Fits that would have stopped as implemented | 0 |
| Fits that would have stopped with the tolerance read in log1p units | 0 |

- **No stopping decision changes under either reading.** The mean-change criterion was never met at any check, so neither the KL scaling (§1) nor the unit question (§2) changed any decision.
- **Why no fit converged.** Check-to-check changes stay at the optimiser's noise level: about 1.6e-2 in standardized mean units and about 5e-3 relative ELBO. That is above both tolerances, and the rule cannot be met without a decaying learning rate or iterate averaging (§4).
- **Correction to the summary file.** The field `decisions_changed_by_log1p_reinterpretation` = 40 in `stopping_audit_summary.json` is an artifact.
  - Both per-fit columns `would_stop_*` are empty for all 40 fits.
  - Under pandas 3, `astype(str)` keeps missing values as missing, and missing ≠ missing, so every fit was counted as changed.
  - The correct count is **0**, consistent with the two "would have stopped" counts of 0.
  - The recorded file is kept as produced.

## 4. Corrected protocol for future temporal fits (proposal, not applied to this study)
1. **Monitor the optimised objective.**
   - Evaluate the per-point ELBO deterministically with `num_data = n`: the full training set in fixed batches, or a fixed probe with KL/n.
   - Record the expected log-likelihood and the KL term separately in every trace row.
2. **State tolerances in the units of the stopping statistic.**
   - Either de-standardize the probe mean (multiply by s_y) before computing the RMS change, or declare the tolerance in standardized units.
   - Record s_y with every fit.
3. **Make convergence attainable and checkable.**
   - Use a learning-rate schedule that decays to zero (for example cosine or 1/t over the iteration cap) or iterate averaging (Polyak–Ruppert), so that check-to-check changes can fall below the minibatch noise floor.
   - Measure that floor during a declared warm-up window (the median absolute check-to-check change), and require the tolerance to exceed it before the rule is frozen.
   - A rule whose tolerance lies below the measured noise floor of its own optimiser should be rejected at the design stage, not discovered at the cap.
4. **Make long fits resumable.**
   - Use `src/jdl_svgp_resumable.py`: atomic model, likelihood, NGD/Adam and generator-state checkpoints with SHA-256 sidecars, plus data and protocol fingerprints.
   - **Correction (2026-10-14, after queue T11; this bullet had been written before the validation ran).**
     - **First validation failed.** `checkpoint_mechanism/CHECKPOINT_MECHANISM_VALIDATION.json` (T11) **failed** both bitwise checks.
       - gpytorch draws its initial natural-parameter noise from the unseeded global torch RNG.
       - The harness seeded that RNG only once, so the compared runs started from different initialisations.
     - **Version v2 passes.** v2 checkpoints and restores the global RNG state, and its harness seeds every fresh run. Its validation (`CHECKPOINT_MECHANISM_VALIDATION_v2.json`, 29 s on one thread) **passes** every check:
       - identical to the frozen `train`;
       - interrupted-and-resumed identical to uninterrupted;
       - corrupted or foreign checkpoints refused;
       - a stale `.tmp` file harmless.
   - It is for new jobs only and was not retrofitted into the fits above.
6. **Seed the variational initialisation per fit.**
   - The frozen fits draw their initial natural-parameter noise (sd 1e-3) from the process-global torch stream, which the protocol does not seed.
   - A fit's bitwise result therefore depends on what its worker process ran before it. A re-run with a different checkpoint-to-worker order could give slightly different fits.
   - This is a reproducibility caveat for this study. The evaluation uses each fit as recorded.
5. **Give M400 and M800 equal convergence effort** under the same declared rule, and report wall time separately from convergence, with the thread count of each fit.
