# Week 18 theory track

Every result: statement · proof or counterexample · check · literature · status · falsifiable prediction run in
the benchmark. Code: `src/week18_theory.py`; tests `src/tests/test_week18_theory.py`.

## T18-1 Binary vs censored-continuous threshold localization (1-D finite pool)
**Setting.** Pool x₁ < … < x_N; increasing conduction branch c; label yᵢ = 1[c(xᵢ) ≥ u]; boundary index
k* = min{i : c(xᵢ) ≥ u} (k* = N + 1 if none). *Censored observation*: yᵢ always; c(xᵢ) only when yᵢ = 0
(a Keyhole run reveals only that the branch has crossed — the max-depth structure found in DATA_AUDIT §2).

**(a) Binary labels.** Every (adaptive, possibly randomized) algorithm that always identifies k* needs
⌈log₂(N + 1)⌉ queries on some input; bisection attains this. *Proof.* N + 1 outcomes, each query returns one
bit, so a decision tree of depth < log₂(N + 1) has fewer leaves than outcomes. **KNOWN** (binary search).

**(b) Censored, affine branch.** If c(x) = α + βx with unknown α, β > 0, two queries always suffice.
*Proof.* Query x₁, x₂. If either is Keyhole, k* ∈ {1, 2}. Otherwise both values are observed, which determines
α and β and hence k*. **PROVED** (elementary). Checked exactly for N ∈ {16, …, 4096}.

**(c) Censored, smooth branch.** For c with c′ > 0 and bounded curvature, the Keyhole side never returns a value,
so bracketing methods that rely on function values on both sides of the root (regula falsi / Illinois,
Dowell & Jarratt 1971) do not apply. One-sided extrapolation from conduction values (secant through the last two,
quadratic through the last three; bisection safeguard when the extrapolation leaves the bracket or stalls)
gives, on random smooth monotone branches (400 per N):

| N | bisection (mean / worst-case bound) | censored secant mean | censored quadratic mean |
|---:|---|---:|---:|
| 16 | 4.05 / 5 | 5.76 | 5.75 |
| 64 | 6.05 / 7 | 6.63 | 6.48 |
| 256 | 8.06 / 9 | 7.64 | 7.15 |
| 1024 | 10.04 / 11 | 9.43 | 7.98 |
| 4096 | 12.05 / 13 | 10.66 | 8.44 |

**NUMERICALLY CHECKED.** Continuous (censored) information helps 1-D localization only when the pool is fine
relative to the branch curvature (≈ 30% fewer queries at N = 4096, none at N ≤ 64); one-sided censoring removes
the superlinear convergence two-sided methods enjoy.

**Prediction P-T18-1 (to be tested in Phase 3, E2).** Our pools hold only a handful of points along any line
through the boundary, so a depth-aware learner cannot win by 1-D localization. If it wins on the 4-D tasks, the
gain must come from depth information shared across the boundary surface, and it should then appear already at
small budgets, mostly in tasks where conduction runs are plentiful (OLD-like, pooled); it should be small on
NEW-like pools (≈ 9% conduction runs).
