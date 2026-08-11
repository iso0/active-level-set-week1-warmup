# Week 7 Phase 5.5 — G3 robustness and transfer stress test

## Evidence boundary

Phase 5.5 starts from exact Phase 5 commit `3367f4c9b5af2def802f72a65258f5cc01896bac` and analyses the current merged `sph_v2` revision `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8`. The Git-tree audit found exactly 110 additions: 55 `time.dat` and 55 `kinetic-energy_melt.dat`, all in old-data-local. No label, new-data, position-bounds, or iteration path changed.

The 55 affected targets were re-extracted with the unchanged corrected Phase 2 definitions. The other 352 rows were reused only because their scientific inputs are unchanged in the exact revision diff. All 407 simulations remain present; two are explicitly physical-target-ineligible.

## Current usable population

- new-data: **164/165**
- old-data-local: **178/179**
- old-data-remote-clean: **63/63**
- all old: **241/242**
- all combined: **405/407**

## Transfer result

G3 mean within-population LOO balanced accuracy is **0.9305**. Its mean held-out cross-population transfer balanced accuracy is **0.8866**, and its worst predeclared transfer result is **0.8125**. Descriptive threshold directions agree across populations at **1.000**.

Candidate stress-test ordering (worst transfer balanced accuracy):

- `max_depth`: 0.9444 — ROBUST CROSS-PARTITION SCALAR COMPANION
- `G3`: 0.8125 — TRANSFERABLE WITH PARTITION-SHIFT CAVEAT
- `R3`: 0.7500 — TRANSFERABLE WITH PARTITION-SHIFT CAVEAT
- `T0_depth`: 0.7353 — PARTITION-SENSITIVE SCALAR COMPANION

## Scientific interpretation

G3 is evaluated as a continuous physical companion to the manual morphology label. A stable threshold does not retroactively define the label, and a partition-sensitive threshold is not silently promoted to a universal boundary. The Phase 6 recommendation therefore retains the unchanged binary `has_keyhole` reference and, if separately approved, compares it with continuous G3 under an explicit modelling protocol.

## Hard stop

No classifier, Gaussian process, regression surrogate, active learning, acquisition, level-set estimation, relabelling, or new target definition was performed. Phase 5.5 is intentionally left uncommitted and unpushed.

## Final validation dashboard

- validation: **24/24 PASS**
- requirements: **12/12 PASS**
- notebook: **20 executed code cells, zero stored errors**
- figures: **20 verified images**
