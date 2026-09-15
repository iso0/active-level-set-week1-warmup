# NEW_POOL_FEASIBILITY_SPEC — label-free audit and gates for the unseen pool

Status of the new inputs at the time of writing: the Hugging Face dataset `ioandanielc/sph_v2` (main, commit `b6dc254a…`, 2026-08-10, "Restore missing old-data monitor streams") contains the same 407 experiment folders as the pinned revision `d69dac5b…` plus the three label ledgers; **no new simulation folders are present there**, and no other location was supplied. The audit below is therefore specified as an executable script (`code/new_pool_audit.py`) that runs on a manifest of the new experiment-folder names (or an input-only CSV). It refuses to run on any file containing a label-like column. Run it once the manifest is available and **before** the protocol commit is finalised; its output is attached to the protocol.

## 1. What the audit computes (all label-free)

| Quantity | Definition | Old-pool reference |
|---|---|---|
| N | number of new simulations with parseable inputs | 405 |
| Configurations | distinct (XI, XF, XL, TE) tuples from the folder names; fraction in the main configuration `0.0002|0.0014|0.0012|0.0021` | 364/405 main; 27 + 14 in two others |
| Campaign identity | folder-name hash suffix groups (`H-…`), TE/DT patterns, ST fixed vs varying | old pool = 3 partitions with different P ranges and KH rates |
| N_band | rows with log h ∈ [20.3621, 21.2533] (band frozen from old labels) | 82 (20%) |
| N_band per training pool | N_band × (1 − 1/K) | ≈ 66 (61 at B16) |
| Old-model uncertainty | rows with 0.1 < p < 0.9 under M3 fitted to all 405 old labels | (self-fit) |
| Support | nearest-neighbour distance of each new row to the old pool in standardised (log P, log VX, log LS, ST), compared with the old pool's own NN quantiles; fraction beyond the old 95% quantile | — |
| Context density | median within-new NN distance; unique (VX, LS, ST) contexts | 405/405 unique |
| Duplicates | exact duplicates of old experiments or of input tuples within the new pool (indivisible groups in partitions) | 0 |
| Input ranges | P, VX, LS, ST ranges vs old | P 52–450 W, VX 0.20–1.0 m/s, LS 41–90 µm, ST 300–400 K |

## 2. Derived gates

### 2.1 Fold rule and horizon (frozen)
Largest K ∈ {5, 4, 3, 2} with N/K ≥ 85 (memo rule: evaluation folds of at least ≈ 85 rows keep q20 at ≥ 17 rows); otherwise K = 2 and the study is at most a small benchmark. n_train = N − N/K. Horizon H = min(80, ⌊0.8·n_train⌋). The primary window 16–40 requires H ≥ 40, hence **n_train ≥ 50**; the full 16–80 secondary requires n_train ≥ 100.

### 2.2 Band-support gate (derived from old-pool query behaviour)
M3-margin places 94% of its early (B16–B39) queries in the physical band and queries 23.5 band rows between B16 and B40. If fewer than 24 band rows are available in a training pool, every band-seeking policy queries essentially the same set inside the primary window in some order and the arms cannot diverge. Therefore:
- N_band per training pool < **24** → TOO WEAK for any acquisition claim.
- 24 ≤ N_band per training pool < **45** → SMALL EXTERNAL BENCHMARK only (arms can diverge, but the number of distinguishable selections is below the old pool's 61 and the early effect, if any, would be truncated).
- N_band per training pool ≥ **45** → full locked protocol (band support comparable to the old pool's B16 state).

### 2.3 Old-model-uncertainty gate
Expected rows with 0.1 < p_M3(405) < 0.9 per training pool < **12** (old pool at B16: 46 with 0.1<p<0.9 under a 16-label fit; under the full-405 fit the count is the self-consistent boundary-proximity count) → the new pool has little near-boundary support under the old boundary; TOO WEAK.

### 2.4 Support/transfer gate
If > **50%** of new rows lie beyond the old pool's 95% NN-distance quantile, the frozen T hyperparameters and the old physical band are extrapolations; downgrade to SMALL EXTERNAL BENCHMARK and report that the historical band cannot be assumed.

### 2.5 Configuration/window compatibility
Report the configuration table. Rows in configurations absent from the old pool are **retained**, flagged, and used in a predeclared subgroup diagnostic (main-configuration-only replication of the primary contrast). No configuration is removed. If the new pool has a single configuration that differs from the old main configuration, the external prediction P1 keeps its interval but the comparison is labelled "different observation window".

### 2.6 Power-based statement (from `results/feasibility_power_by_N.csv`)
Per-run paired noise of the early-window AULC (17 q20 rows) from the old pool: block sd 0.0137 (5 runs/block). Scaling by fold count and q20 size gives the expected half-width of the primary 95% interval and the power to detect an AULC 16–40 gain Δ with the "lower bound > 0" rule:

| N | K | n_test | n_q20 | n_train | runs | CI half-width | power Δ=0.005 | Δ=0.01 | Δ=0.015 | Δ=0.02 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 2 | 50 | 10 | 50 | 40 | 0.0124 | 0.12 | 0.35 | 0.66 | 0.89 |
| 150 | 2 | 75 | 15 | 75 | 40 | 0.0101 | 0.16 | 0.49 | 0.83 | 0.97 |
| 200 | 2 | 100 | 20 | 100 | 40 | 0.0088 | 0.20 | 0.61 | 0.92 | 0.99 |
| 300 | 3 | 100 | 20 | 200 | 60 | 0.0071 | 0.28 | 0.78 | 0.98 | 1.00 |
| 405 | 4 | 101 | 21 | 303 | 80 | 0.0060 | 0.37 | 0.90 | 1.00 | 1.00 |
| 500 | 5 | 100 | 20 | 400 | 100 | 0.0055 | 0.42 | 0.94 | 1.00 | 1.00 |

The frozen minimum practically meaningful effect is Δ = 0.01 (a third of the old-pool early headroom). Power ≥ 0.6 requires N ≥ 200; the study is reported as underpowered below that, without changing the endpoint.

## 3. Decision rule (frozen)

1. If H < 40 or N_band/train < 24 or old-model-uncertain/train < 12 → **TOO WEAK FOR AN ACQUISITION CLAIM**: run only the external *prediction* study (old-trained H, M3, T evaluated once on the full new pool) and the P1/P2/P7/P8 predictions.
2. Else if N_band/train < 45 or N < 200 or support gate fails → **SMALL EXTERNAL BENCHMARK**: run the four paths with the reduced K/H, report the primary contrast with its interval, but classify the inferential result as an underpowered benchmark; no success claim is made even if the interval excludes zero unless N ≥ 200.
3. Else → **FULL LOCKED PROTOCOL** (EXTERNAL_CONFIRMATION_PROTOCOL.md).

The gate level, all audit quantities and the manifest SHA-256 are written by `code/new_pool_audit.py` into `new_pool_audit.json`, which is committed alongside the protocol before any label is read.

## 4. What must also be recorded from the data owner (no labels)

Immutable simulation ID list; exact parameter conventions (LS is the spot radius in m, VX in m/s, P in W, ST in K); XI/XF/XL/TE/DT and material; recording/observation window and termination reasons; whether monitor streams (geometry, depth) exist for each simulation (needed only for prediction P2, not for the challenger); the labelling rule used by the supervisor (ever-observed KH over which frames) and whether it matches the old ledgers' `label_final` rule; whether anyone on the method side has seen any new label (if so, the study is external validation, not blinded confirmation).
