# Erratum E16-1 — non-converged Laplace fits in the Week 15 gpworld m0 = −4 cells

Found during Week 16 item 0 (PEER validation), before any Week 16 result on margin was computed.

## Defect
`src/week13_synthetic.py::LaplaceGPC.fit` runs the undamped Newton iteration of GPML Alg. 3.1 and stops as
soon as the (mismatched) objective stops increasing; it then keeps the *last* iterate. When the iteration
oscillates it therefore stores an overshoot, not the posterior mode. With the gpworld held-out prior
(var = 25, constant prior mean m0 = −4) the iteration oscillates from the second step
(Laplace objective −25.3 → −105.6 → −172.1 → …, `src/week16_laplace_audit.py`), and the stored predictive
probabilities are saturated.

## Scope (audit: `outputs/week16_theory_meets_data/laplace_audit/`)
Criterion: latent deviation at the training inputs differs from the safeguarded mode
(`src/week16_peer.py::RobustLaplaceGPC`, Newton with backtracking) by more than 1e-6.

| Code path | States checked | Failed |
|---|---:|---:|
| Week 15 held-out gpworld m0 = −4 (pool 108 and 324), margin paths, base fits | 16 paths, every step | **100%** |
| same cells, fantasy refits (as used by VSUR / EBR-D / expectation oracle) | 6 per step | **100%** |
| all other 23 Week 15 development and held-out cells, base fits | 184 paths, every step | 0 |
| same, fantasy refits | 6 per step | ≤ 0.23% in 3 cells (5 paths); 0 elsewhere |
| Week 13 synthetic generic (G) and physics-trend (M3-type) models, random labelled subsets | 179 each | 0 |
| Week 15 well-specified 3-D GP world (zero mean, var 9) | 32 | 0 |
| Week 15 NEW-136 replay model (G3 hypers, zero mean) | 95 | 0 |

A first version of the audit used a logit-based fixed-point check, which returned spurious failures for the
M3-type model (its physics-trend prior mean saturates p to 0/1 in floating point). This was replaced by the
mode-gap criterion above before any conclusion was drawn.

## Consequences
- **All Week 15 numbers for the two gpworld m0 = −4 held-out cells are invalid**, for every policy and for
  the expectation-oracle reference (WEEK15 claim 4: "0.40 vs ≤ 0.14"). With the safeguarded fit, margin's
  mean NSD over budgets 16–80 is 0.613 (pool 108; range over reps 0.47–0.69), not 0.064, and 0.598 (pool
  324), not 0.013.
- **The frozen Week 15 verdict is unchanged.** It failed S2 (no catastrophe) because of branin σ = 0
  (−0.068) and rough σ = 1 (−0.092), which are unaffected. Without the two invalid cells EBR-D beats margin
  in 5/14 cells, mean −0.0148 NSD AULC (with them: 7/16, −0.0095).
- In every other cell the safeguarded fit reproduces the Week 15 margin paths exactly (the regenerated
  NSD traces match the stored ones to 1e-16).
- Week 16 uses the safeguarded fit throughout; the gpworld m0 = −4 cells are reported as **corrected**.
- Historical Week 13–15 files are not modified; this erratum and the audit tables are the record.
- Not re-run this week: the Week 15 held-out policies in the two gpworld m0 = −4 cells with the corrected
  fit (they cannot change the verdict). Recommended before any statement about well-specified prior-shift
  cells.
