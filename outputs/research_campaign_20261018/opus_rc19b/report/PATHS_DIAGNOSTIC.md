# RC19B path diagnostic (exploratory, evaluator-side): where the final Keyhole arms spend their queries

Pool: 541 runs, Keyhole share 0.364; fast-scan conduction corner = 12 runs (2.2%). Distance = standardised log-input distance to the nearest run of the other class (pool median 1.229; smaller = nearer the boundary). Means over 40 trajectories (8 repeats × 5 folds) per arm.

| arm | budget | keyhole_share | corner_paid_mean | corner_paid_max | median_dist_to_opposite |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.484 | 0.950 | 3 | 0.793 |
| ATSAPPROX_MARGIN | 24 | 0.481 | 2.425 | 5 | 0.648 |
| ATSAPPROX_MARGIN | 40 | 0.487 | 5.125 | 9 | 0.565 |
| ATSAPPROX_MARGIN | 60 | 0.504 | 8.250 | 11 | 0.497 |
| ATSCF_MARGIN | 16 | 0.484 | 0.850 | 3 | 0.810 |
| ATSCF_MARGIN | 24 | 0.487 | 1.925 | 6 | 0.659 |
| ATSCF_MARGIN | 40 | 0.490 | 5.350 | 9 | 0.548 |
| ATSCF_MARGIN | 60 | 0.508 | 8.250 | 11 | 0.502 |
| DEPTHCF_MARGIN | 16 | 0.467 | 0.700 | 4 | 0.877 |
| DEPTHCF_MARGIN | 24 | 0.483 | 1.950 | 5 | 0.709 |
| DEPTHCF_MARGIN | 40 | 0.492 | 4.150 | 7 | 0.578 |
| DEPTHCF_MARGIN | 60 | 0.479 | 7.900 | 11 | 0.510 |
| E1S | 16 | 0.384 | 0.325 | 2 | 1.072 |
| E1S | 24 | 0.365 | 0.600 | 2 | 0.954 |
| E1S | 40 | 0.366 | 1.825 | 3 | 0.786 |
| E1S | 60 | 0.370 | 3.850 | 6 | 0.691 |
| G3_MARGIN | 16 | 0.459 | 0.400 | 2 | 1.012 |
| G3_MARGIN | 24 | 0.455 | 0.900 | 4 | 0.896 |
| G3_MARGIN | 40 | 0.466 | 2.675 | 7 | 0.736 |
| G3_MARGIN | 60 | 0.460 | 5.950 | 9 | 0.633 |

