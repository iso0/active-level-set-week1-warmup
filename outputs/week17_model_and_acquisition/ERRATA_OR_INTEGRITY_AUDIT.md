# Week 17 — integrity audit and errata (Phase 0)

Committed before any Week 17 model development. Historical outputs are not modified; this file and
`integrity/` are the record. Code: `src/week17_audit.py`, `src/week17_audit_impact.py`; tests
`src/tests/test_week17_integrity.py`.

## 1. Which implementations are authoritative
| Model | Code actually executed (Weeks 9–12, frozen attempt) | Likelihood / inference |
|---|---|---|
| H | `week9_phase1_11.fit_physics_mean`: StandardScaler(log h) on revealed rows + LogisticRegression(**C = 1e6**) | plug-in logistic |
| G3 | `week9_phase1_12.fit_gpc_model('G3')`: sklearn `GaussianProcessClassifier`, ARD Matérn-3/2 × constant, ML-II (L-BFGS-B, 0 restarts) | sklearn Laplace (GPML 3.1) |
| M3 | `week9_phase1_13.fit_hybrid(…, 'M3', 100)`: H as a fixed prior mean + `week9_phase1_11.FixedMeanLaplaceGPC` with residual ARD Matérn-3/2, **residual sd bounds [0.05, 1]**, length scales [0.01, 100], ML-II | GPML 3.1 with fixed mean |
| Week 12 AL / frozen attempt | `external_validation.runner.FrozenM3Evaluator` → the same `fit_physics_mean` + `fit_hybrid` | as M3 |
| Week 13–15 synthetic | `week13_synthetic.LaplaceGPC` (fixed hypers) | own Newton (E16-1) |
| Week 16 | `week16_peer.Model` → `RobustLaplaceGPC` (safeguarded) | safeguarded |
`src/alse/physics.py` is a re-packaging of the Week 9 code (`frozen:` tags); it was not the executed path.

All non-Week-16 implementations use the undamped GPML Alg. 3.1 Newton iteration and stop as soon as the
in-loop objective (computed with the *previous* W) fails to rise; sklearn and `FixedMeanLaplaceGPC` keep π
from the iterate *before* the last step, so a premature stop leaves a state that is not a fixed point of
f = m + K(y − π(f)). The stored log marginal likelihood is computed from mismatched pieces and can exceed the
true Laplace value; the ML-II optimizer then optimizes an inexact objective.

## 2. Audit (`integrity/laplace_mode_audit.csv.gz`)
Each fit is compared with the Laplace mode found by a safeguarded Newton (backtracking on
Ψ(a) = −½aᵀKa + Σ log σ(s(m + Ka))) at the *same* kernel and mean. Flag: latent gap > 1e-6 or Δp > 1e-4.

| Fit set | G3 flagged | M3 flagged | M3 max Δp | M3 states with ≥ 1 test-class change |
|---|---:|---:|---:|---:|
| A. Week 12 strict OLD→NEW transfer (fit on OLD-405) | 0/1 | **1/1** | 0.027 | 0 |
| B. Week 12 NEW-only CV (100 frozen splits) | 0/100 | 2/100 | 0.012 | 0 |
| C. Week 12 AL prefixes (2 protocols × 100 splits × 5 budgets) | 0/994 | **91/994** | 0.026 | 7 |
| D. Week 9 OLD A0 paths (100 runs × 5 budgets) | 1/500 (Δp 1e-5) | **229/500** | 0.058 | 11 |

G3 is numerically sound in every authoritative use. M3's stored state is not the Laplace mode in a large
share of fits: with the C = 1e6 prior mean (|m| up to 10–50 on the campaign) the in-loop objective stops
rising after two Newton steps (`posterior_iterations = 2` in every flagged fit).

## 3. Impact on historical conclusions (`integrity/m3_safeguarded_refit_impact*.csv`)
M3 was refitted on the same states with the safeguarded mode inside the ML-II optimization (so the
hyperparameters are also re-optimized on the correct objective).

| Fit set | States | States with a test-class change | Mean q20 (historical → safeguarded) | Mean BA |
|---|---:|---:|---|---|
| A. transfer | 1 | 0 | 0.7143 → 0.7143 | 0.5793 → 0.5793 |
| B. NEW CV | 100 | 1 | 0.6700 → 0.6683 | 0.6374 → 0.6349 |
| C. Week 12 AL | 994 | 16 | 0.6648 → 0.6663 | 0.6498 → 0.6512 |
| D. OLD A0 | 500 | 27 | 0.8360 → 0.8362 | 0.9270 → 0.9278 |

On fixed query paths, the Candidate B − margin q20 contrast changes by at most 0.0017 at any budget
(B16 +0.0533 → +0.0533; B40 +0.0117 → +0.0117; B80 +0.0017 → +0.0017). **No historical OLD/NEW conclusion
changes.** Not re-run: paths themselves (selections could change where margin ties are broken by tiny Δp);
since Week 12 already found no established acquisition difference, re-running cannot create one that the
numerical noise floor (≈ 0.002 q20) would support.

Side finding used in Phase 1: the M3 residual variance sits at its upper bound 1.0 in the median fit of
every set (sets A–C; 0.95 on OLD A0) — the cap binds.

## 4. Terminology and theory corrections
**E17-T1 ("exact Bayes", Week 15).** WEEK15_REPORT §1/§D, CLAIM_LEDGER #9, FREEZE item 5, RESEARCH_LOG and
NOVELTY_AUDIT call the well-specified-world rule of `week15_bayes_frontier.py` / `week15_wellspec_paths.py`
an "exact (one-step) Bayes look-ahead". It is a **Laplace-refit Monte-Carlo look-ahead**: each fantasy
label is handled by refitting the Laplace GPC, and the expected NSD is estimated from 24 Matheron pathwise
samples of that Laplace Gaussian. It is neither exact conditioning nor exact Bayes; Week 16 (L3) showed that
refit look-aheads are not martingale-consistent. Read "exact Bayes" in those files as "Laplace-refit MC
look-ahead"; their numbers are unchanged.
Likewise Week 9's `EXACT_LAPLACE_FIXED_MODEL` SUR (Phase 1.18B0/B) is an exact computation of a
*refit-Laplace* SUR score on the M3 model (with the M3 convergence caveat of §2), not exact Bayes.

**E17-T2 (Proposition B3, Week 15).** Tagged "EXACT counterexample", B3 is an asymptotic argument
(location spread s ≫ graph scale r; "≈ 2ca") checked numerically on a graph
(`test_B3_unnormalized_risk_prefers_erasing_uncertain_boundary`), not an exact statement. Its Dice
normalization makes the two configurations *tie* (both ≈ 1); it removes the incentive to erase the boundary
but does not reward the correct one. It is one candidate mechanism for EBR's development collapse, not
"exactly" its cause; Week 16 L3 identified a second (refit incoherence).

**E17-T3 (PEER attribution, Week 16).** "PEER" is our label for expected error reduction (Roy & McCallum
2001) with a Hamming target, equivalently one-step SUR with the expected-misclassification risk
(Bect et al. 2012; Chevalier et al. 2014), computed by exact conditioning of the Laplace Gaussian on a
probit-approximated label. The analytic look-ahead *level-set* posterior in terms of Φ and the bivariate
normal CDF is established for Bernoulli LSE by Letham et al. (AISTATS 2022); the binary-observation Bayes
error lemma is elementary. Week 16's contribution is its use as a diagnostic (coherence check, headroom
split), not the formula.

## 5. Rules adopted for Week 17
All Week 17 fits use the safeguarded Newton (`SafeguardedFixedMeanLaplaceGPC`, or the Week 16
`RobustLaplaceGPC` for fixed hyperparameters) and record convergence; historical baselines are reported both
as historically implemented (for continuity) and refitted safely (for comparisons with new models).
