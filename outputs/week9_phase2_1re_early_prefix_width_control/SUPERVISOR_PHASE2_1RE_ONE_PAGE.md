# What did we actually ask?

Phase 2.1R found two things that, put together, ask an obvious next question.

1. Adding the largest width jump to the four process inputs improves how well the model **ranks**
   Keyhole risk (q20 PR-AUC +0.0145), though it does not change hard classification.
2. **95.4%** of those largest jumps happen inside the first 5% of the trace.

So: **if the signal is all at the beginning, do we need the rest of the trace at all?**

This phase rebuilds exactly the same feature using only an opening slice of each simulation, and
sweeps how long that slice is: 2%, 5%, 10%, 20%, 40% and 100% of the trace. Nothing else changes —
same 350 simulations, same 100 frozen folds, same ARD Matérn-3/2 GPC.

The slices are counted in **consecutive resampled analysis point** steps on the pinned Phase 2 grid
(201 points per simulation, so 5% is the first 10 transitions), never in raw solver timesteps.

Concrete example. A simulation's opening widths might be 4, 31, 52, 56, 63 µm, so the changes are
`[+27, +21, +4, +7]`. Allowed to watch only the first five analysis points, we record
`max_positive_delta_W = 27`. Allowed the whole trace, we might find something bigger later — this
phase measures how often we do, and what it costs when we do not.

**Strict no-future rule.** The feature at prefix *p* uses only transitions ending at or before
analysis point `ceil(p × 200)`. `prefix_no_future_audit.csv` recomputes every value a second,
independent way and records the latest analysis point consulted.

## Does an opening slice already contain the full-trace number?

350 of 405 simulations have a usable trace (70 Keyhole, 280 Conduction).

| prefix | transitions seen | median window | already equal to full-trace value | correlation with full | median shortfall |
|---|---|---|---|---|---|
| 2% | 4 | 27 µs | 91.1% | 0.9797 | 0.000 µm |
| 5% | 10 | 68 µs | 95.4% | 0.9937 | 0.000 µm |
| 10% | 20 | 137 µs | 99.7% | 0.9975 | 0.000 µm |
| 20% | 40 | 274 µs | 99.7% | 0.9999 | 0.000 µm |
| 40% | 80 | 547 µs | 100.0% | 1.0000 | 0.000 µm |
| 100% | 200 | 1368 µs | 100.0% | 1.0000 | 0.000 µm |

**At the 5% prefix — a median window of 68 µs —
95.4% of simulations already have exactly the same number they would have had from
the whole trace.**

## Marginal separation at each prefix

| prefix | Conduction median | Keyhole median | Cliff's δ | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|
| 2% | 29.783 | 29.275 | -0.200 | 0.400 | 0.168 |
| 5% | 29.783 | 29.275 | -0.203 | 0.399 | 0.168 |
| 10% | 29.819 | 29.275 | -0.202 | 0.399 | 0.168 |
| 20% | 29.819 | 29.275 | -0.204 | 0.398 | 0.168 |
| 40% | 29.819 | 29.275 | -0.204 | 0.398 | 0.168 |
| 100% | 29.819 | 29.275 | -0.204 | 0.398 | 0.168 |

The sign is negative at every prefix: Keyhole simulations widen **more slowly** in their opening, at
every observation window tested.

## Does the early feature help the 4D GPC?

| prefix | median window | q20 PR-AUC | gain over 4D-only [95% CI] | verdict |
|---|---|---|---|---|
| 2% | 27 µs | 0.8854 | +0.0085 [+0.0032, +0.0133] | IMPROVES |
| 5% | 68 µs | 0.8922 | +0.0153 [+0.0101, +0.0206] | IMPROVES |
| 10% | 137 µs | 0.8914 | +0.0145 [+0.0093, +0.0198] | IMPROVES |
| 20% | 274 µs | 0.8915 | +0.0146 [+0.0093, +0.0200] | IMPROVES |
| 40% | 547 µs | 0.8914 | +0.0145 [+0.0092, +0.0199] | IMPROVES |
| 100% | 1368 µs | 0.8914 | +0.0145 [+0.0092, +0.0203] | IMPROVES |

### The primary contrast: opening 5% only, versus 4D-only, on q20

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
| accuracy | higher is better | +0.0053 [-0.0019, +0.0126] | 0.1408 | 0.1529 | **NO DETECTABLE DIFFERENCE** |
| balanced accuracy | higher is better | +0.0085 [+0.0000, +0.0174] | 0.0764 | 0.1529 | **NO DETECTABLE DIFFERENCE** |
| keyhole recall | higher is better | +0.0234 [+0.0078, +0.0398] | 0.0142 | 0.0568 | **NO DETECTABLE DIFFERENCE** |
| brier score | lower is better | -0.0020 [-0.0036, -0.0004] | 0.0294 | 0.0883 | **NO DETECTABLE DIFFERENCE** |
| pr auc | higher is better | +0.0153 [+0.0101, +0.0206] | 0.0001 | 0.0006 | **IMPROVES** |
| roc auc | higher is better | +0.0081 [+0.0047, +0.0116] | 0.0002 | 0.0010 | **IMPROVES** |

**Hard classification: NOT SUPPORTED. Ranking / probability: SUPPORTED.**

## Does the rest of the trace add anything?

Predeclared equivalence margin **±0.005** on each metric — roughly a third of the
Phase 2.1R gain, so a demanding rather than a flattering test. The question is whether the whole 95%
interval for (whole trace − opening 5%) sits inside it.

| metric | whole trace − early prefix [95% CI] | inside margin? | verdict |
|---|---|---|---|
| balanced accuracy | +0.0005 [-0.0030, +0.0042] | yes | EQUIVALENT WITHIN MARGIN |
| accuracy | +0.0000 [-0.0033, +0.0033] | yes | EQUIVALENT WITHIN MARGIN |
| keyhole recall | +0.0032 [-0.0034, +0.0099] | no | INCONCLUSIVE |
| roc auc | -0.0000 [-0.0005, +0.0004] | yes | EQUIVALENT WITHIN MARGIN |
| pr auc | -0.0008 [-0.0022, +0.0003] | yes | EQUIVALENT WITHIN MARGIN |
| brier score | -0.0000 [-0.0003, +0.0002] | yes | EQUIVALENT WITHIN MARGIN |

5 of 6 q20 metrics are
equivalent within the margin.

## The simple threshold rule at each prefix

| prefix | region | median learned cut | folds choosing 'small means Keyhole' | balanced accuracy | Keyhole recall |
|---|---|---|---|---|---|
| 2% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 5% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 10% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 20% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 40% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 100% | full | 32.408 µm | 100% | 0.6239 ± 0.0083 | 0.9218 |
| 2% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 5% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 10% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 20% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 40% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 100% | q20 | 32.408 µm | 100% | 0.5643 ± 0.0247 | 0.8661 |
| 2% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |
| 5% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |
| 10% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |
| 20% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |
| 40% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |
| 100% | q30 | 32.408 µm | 100% | 0.5714 ± 0.0190 | 0.8795 |

## Claim ledger

| claim | status | guardrail |
|---|---|---|
| PRIMARY — watching only the opening 5% of the trace improves ranking over [P, VX, LS, ST] | SUPPORTED | q20 PR-AUC 0.8769 -> 0.8922; median observed window 68 µs; Holm over six metrics |
| PRIMARY — the same 5% prefix improves hard classification on q20 | NOT SUPPORTED | q20 balanced accuracy / accuracy / Keyhole recall, read separately from the ranking metrics |
| The rest of the trace adds nothing beyond the opening 5% (equivalence within ±0.005) | QUALIFIED | 5/6 q20 metrics have their whole 95% interval inside ±0.005; predeclared margin, about a third of the Phase 2.1R gain |
| An even shorter look (2% of the trace) is already enough for the ranking gain | SUPPORTED | median observed window 27 µs; q20 PR-AUC gain +0.0085 |
| Watching longer keeps improving the model | NOT SUPPORTED | q20 PR-AUC gain across prefixes: +0.0085 / +0.0153 / +0.0145 / +0.0146 / +0.0145 / +0.0145 |
| The opening prefix already contains the full-trace value of the feature | SUPPORTED | at the 5% prefix, 95.4% of simulations already have exactly the full-trace maximum |
| A simple leak-free threshold on the early feature beats chance on q20 | SUPPORTED | q20 balanced accuracy 0.564 ± 0.025; on the full held-out set 0.624 |
| Phase 2.1R's shared models are reproduced exactly by this pipeline | SUPPORTED | phase2_1r_reproduction_gate.csv: the 4D baseline and the 100% prefix both match Phase 2.1R to <1e-9 on every metric and region |
| No prefix feature uses a later analysis point | SUPPORTED | prefix_no_future_audit.csv independently recomputes every prefix feature and checks the latest analysis point consulted |
| This is an in-process monitoring result | NOT SUPPORTED | retrospective prefix analysis of SPH monitor traces; no camera, no sensor model, no prospective experiment, and the window is tens of microseconds |
| This changes the active-learning acquisition rule | NOT SUPPORTED | predictive feature-value study on the frozen folds; the A0 path is untouched |
| Results generalise to simulations with no usable width trace | NOT SUPPORTED | every model is trained and scored only on the 350 usable simulations |

## What this is not

A retrospective prefix analysis of simulation monitor traces is **not** an in-process monitoring
result. There is no camera, no sensor noise model, no latency budget, and the windows involved are
tens of microseconds. Nothing here changes the active-learning acquisition rule, and nothing here
transfers to the 55 simulations with no usable trace.
