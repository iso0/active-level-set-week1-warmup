# RC21 design diagnostics (evaluator-side, full 541-run DEV pool; NOT results)

Boundary direction: 4-input logistic exponents (relative to P) [1.0, -0.59, -1.341, -0.083] vs h-law (1, −0.5, −1.5, 0); cosine with the h direction in standardised log-input space 0.9965.

5-fold CV on the 484 runs with all three outputs (oracle rows use the TRUE outputs and are evaluator-only bounds):

| model | LL | BA | NEW-conduction recall |
|---|---|---|---|
| h only (C=1) | 0.1350 | 0.9475 | 0.000 |
| h only (C=100) | 0.1296 | 0.9449 | 0.000 |
| 4 log inputs (C=1) | 0.1331 | 0.9424 | 0.000 |
| 4 log inputs (C=100) | 0.1289 | 0.9449 | 0.091 |
| h + U linear | 0.1365 | 0.9424 | 0.000 |
| h + U + quadratic | 0.1350 | 0.9510 | 0.455 |
| ARD-RBF GPC on Z | 0.1101 | 0.9690 | 0.455 |
| oracle log A (evaluator only) | 0.0718 | 0.9777 | 0.909 |
| oracle A, T, S | 0.0683 | 0.9742 | 0.727 |
| oracle A, T, S + h | 0.0674 | 0.9750 | 0.545 |

Fast-scan corner (VX > 0.85 m/s and P > 330 W): 39 runs (22 Keyhole, 17 conduction; 7.2 % of the pool); nearest-neighbour label agreement 0.44 in the corner vs 0.91 in the whole pool.

Share of the RC20 paid budget spent in the corner (fresh repeats 19–26):

| arm | budget | share |
|---|---|---|
| ATSAPPROX_MARGIN | 24 | 0.317 |
| ATSAPPROX_MARGIN | 60 | 0.430 |
| ATSCF_MARGIN | 24 | 0.310 |
| ATSCF_MARGIN | 60 | 0.432 |
| CAND_ETASTRADDLE | 24 | 0.139 |
| CAND_ETASTRADDLE | 60 | 0.284 |
| CAND_MARGIN | 24 | 0.269 |
| CAND_MARGIN | 60 | 0.414 |
| E1S | 24 | 0.146 |
| E1S | 60 | 0.260 |
| G3_MARGIN | 24 | 0.165 |
| G3_MARGIN | 60 | 0.274 |

