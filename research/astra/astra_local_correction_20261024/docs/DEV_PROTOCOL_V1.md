# Prospective discriminating DEV pilot v1

Frozen before generating or inspecting these DEV outcomes. No TEST is authorized
by this manifest; future independent TEST requires a separate prospective freeze.

- 32 independent 4D worlds: eight families x four seeds. Families: smooth,
  local_shift, small_island, rotated_local, rare_negative, heteroskedastic,
  outliers, correlated_corruption. Noise/corruption controls are retained.
- Each world has 256 candidate inputs, 768 independent reference inputs (uniform),
  fixed hidden noisy outcomes and latent truth. Learners receive public inputs
  and paid continuous observations only; evaluator regions and generator
  parameters are not passed to a model or selector.
- Two common paths per world: feature-only maximin; strong-GP margin after the
  same eight maximin startup points. Four models evaluated at B8,10,...,24.
  Initial observations, noise realizations and paths are identical across models.
- Primary descriptive model endpoint: trapezoidal BA-AULC B8–B24 /16, reported
  separately for each path panel and equally weighted families. Also class
  recalls, log loss, Brier, sign error, latent RMSE, error inside/outside the
  evaluator's local region, gate support, null weight, evidence determinant and
  fit terms, paid regional hits and pre-query standardized residuals.
- 0.90/0.93/0.95 attainment: a single world's learner must pass at two successive
  evaluation budgets; confirmation cost is the later budget. B24-only passes are
  unconfirmed. Report attainment counts, censor at24 and restricted burden25;
  neither restricted burden nor a matched-path prediction change alone proves
  acquisition sample savings. Conditional post-hit results include charged
  pre-hit queries and report their selected-world denominator.
- Whole-world paired analysis; paths are dependent and not extra replications.
  Pilot bootstrap intervals are pointwise descriptive (2000 stratified resamples,
  seed716204), not multiplicity-controlled confirmatory intervals. No family or
  incomplete world is removed to improve the average; failed/censored counts stay.
- Expansion requires gated vs strong AND vs trace_match mean early BA improvement
  >=0.005 in the pooled three local-structure families, and a positive mean local
  error reduction, with mean BA harm <0.01 in smooth/noise/corruption controls.
  These are pragmatic DEV screening quantities, not evidence of a final win.
  If not passed, diagnose location coverage, null-noise absorption and prior
  dilution before at most one mechanistically justified v2. No threshold sweep.
- Finite envelope: 10,000 top-level model requests, 200,000 component solves,
  300,000 optimizer evaluations, 2000 independent reference solves. Reservations
  precede calculation; unused block reservations and interrupted attempts remain.
  Initial queue: 64 whole-world/path units plus one independent reference unit.
- Numerical acceptance: dense posterior and covariance update absolute tolerance
  1e-8; gradient relative tolerance1e-4; trace match1e-12; positive-semidefinite
  eigenvalues >=-1e-10; mixture normalization1e-12. No tolerance is chosen by BA.
  Optimizer: maxiter80, ftol1e-9, gtol1e-5, maxls20; non-success flags retained.
  Scales/amplitude/noise bounds inherit prior ARD; jitter1e-10. No silent fallback.

The expected direction is conditional: a covered local departure with enough
lawful observations may favor gated over full compact variance. Sparse hits,
wrong geometry and noisy artifacts may not. No unsupported numeric effect-size
prediction is made. Source hashes, exact seeds and settings are in FROZEN_DEV_V1.json.
