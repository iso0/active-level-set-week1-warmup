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
*(Filled in from `stopping_audit_summary.json` once all 40 SVGP fits have finished.)*

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
   - It has been validated to resume bitwise-identically (`checkpoint_mechanism/CHECKPOINT_MECHANISM_VALIDATION.json`).
   - It is for new jobs only and was not retrofitted into the fits above.
5. **Give M400 and M800 equal convergence effort** under the same declared rule, and report wall time separately from convergence, with the thread count of each fit.
