# Week 6 Phase 2.5 stable-depth closure

## Scope

Exactly `230` Phase 1 stable-window simulations were used after
removing the independently verified 11 flagged IDs. Features remained exactly
`[P, VX, LS, ST]`; the target remained the Phase 1 penetration depth converted
from metres to micrometres. No width/length model, Method A, kernel family,
target definition, feature-effect analysis, active learning, or level-set
estimation was introduced.

## Stable-only exact LOO

| Method | MAE µm | RMSE µm | R² | Mean NLPD | Latent coverage | Total/oracle coverage |
|---|---:|---:|---:|---:|---:|---:|
| B learned nugget | 1.802271 | 2.728943 | 0.968873 | 2.440425 | 0.8783 | 0.9522 |
| C heteroskedastic alpha | 2.076667 | 3.013798 | 0.962036 | 2.703817 | 0.9130 | 0.9130 |

## Paired B-versus-C evidence

- B/C improved counts:
  `134` / `96`;
  ties `0`.
- `MAE_C − MAE_B`:
  `+0.274396 µm`,
  95% CI `[+0.134941,
  +0.422091]`.
- `RMSE_C − RMSE_B`:
  `+0.284855 µm`,
  95% CI `[+0.048306,
  +0.549011]`.

## Training-set sensitivity

- B RMSE full-trained/stable-held-outs → stable-only:
  `3.382290`
  → `2.728943 µm`
  (`-19.317%`).
- C RMSE full-trained/stable-held-outs → stable-only:
  `3.517802`
  → `3.013798 µm`
  (`-14.327%`).

The 5% threshold is descriptive only.

## Observation scales and interpretation

B's median effective-nugget standard deviation is
`1.776750 µm`. C's median/q95/max target-summary
uncertainty standard deviations are `0.007317`,
`0.474441`, and `1.149503 µm`.
B is an effective discrepancy model; C is a within-window stability proxy.
Neither is evidence of stochastic simulator noise. C's oracle interval is
retrospective and not deployable for an unseen simulation.

## Decision

**B is preferred for stable-window penetration depth.**

This conclusion is limited to stable-window penetration depth under the fixed
isotropic Matérn 3/2 protocol.

## Runtime correction and validation

The historical Phase 2 `11.2`-second field was a cached pre-report invocation,
not the original end-to-end experiment. It is deprecated and accurately renamed
in `runtime_provenance.json`; no guessed runtime was substituted.

Automated validation: `30/30`
PASS.
