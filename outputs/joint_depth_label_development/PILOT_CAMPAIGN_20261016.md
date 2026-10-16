# Pilot campaign of 2026-10-16 (owner instruction; 2-hour first-pilot budget, 21:04–23:05 UTC)

All pilots were registered before their outcomes (commits are listed in `ATTEMPT_LEDGER.md`). All are DEV evidence on NEW simulations that were inspected before, so a new split is not new data. C3's failed superiority result is unchanged. No saving is claimed anywhere: no arm sustained BA ≥ 0.75, short-K ≥ 0.70 and q20 ≥ 0.70.

## 0. ASTRA_AL / BA_RISK stopped (21:01–21:03 UTC)

- **Shutdown:** the plan entry was disabled first. Then the finalizer, the three verified BA_RISK workers and the pool runner (by itself, with POOL_END) stopped. Checkpoints are identical before and after the stop.
- **Verification:** 0 numeric processes remain, and nothing restarted.
- **Status:** P2 is **not completed (stopped by owner)**; it is not a negative result. Record: `astra_al/cancellation/`.
- **Verified on disk:** 48/48 finished BA_RISK selections had no resolved ranking (index tie-break). The median selection took 2.57 h; V2 variance took 20.5 s.

## 1. Same-budget comparison (NEW DEV r3–4; frozen B16 starts; B40; one-class rule = frozen-path continuation for all arms)

| Arm | Role | BA-AULC B16–40 (r3 / r4) | BA at B40 (r3 / r4) | Short-K caught at B40 | Budget | Compute (10 trajectories) |
|---|---|---|---|---|---|---|
| ACTIVE E1 + straddle | reference | 0.708 / 0.714 | 0.780 / 0.738 | 16/20 | 40 | 5.8 s |
| G3 + margin | reference | 0.693 / 0.625 | 0.767 / 0.609 | 13/20 | 40 | 14.7 s |
| Random (G3 model) | control | — | 0.613 / 0.696 | 16/20 | 40 | 10.8 s |
| SD + margin | candidate (surprise discovery) | — | 0.730 / 0.609 | 14/20 | 40 | 13.6 s |
| SD + straddle | candidate (surprise discovery) | — | 0.780 / 0.738 | 16/20 | 40 | 6.2 s |
| GPC on x only | control (for PHYS_AUX) | 0.615 / 0.608 | 0.647 / 0.609 | 14/20 | 40 | 7.9 s |
| PHYS_AUX (GPC on x + predicted physics) | candidate (physical auxiliary) | 0.703 / 0.706 | 0.696 / 0.734 | 15/20 | 40 | 23.1 s |
| E1_AUX (E1 + predicted physics) | correction | 0.707 / 0.696 | 0.776 / 0.734 | 14/20 | 40 | 17.3 s |

**Repeats 5–8, separate block** (BA-AULC per repeat; short-K of 40):
- G3: 0.601 / 0.755 / 0.504 / 0.589 (28)
- E1: 0.685 / 0.751 / 0.671 / 0.720 (31)
- GPC_X: 0.592 / 0.713 / 0.565 / 0.602 (30)
- PHYS_AUX: 0.656 / 0.750 / 0.666 / 0.656 (28)
- E1_AUX: 0.691 / 0.757 / 0.667 / 0.713 (28)

## 2. Verdicts (pre-registered rules)

| Question | Result | Verdict |
|---|---|---|
| Surprise discovery, synthetic, after a planted surprise | Island AUDC +0.126 [+0.058, +0.201] (margin base) and +0.175 [+0.132, +0.206] (straddle base); BA −0.003 / −0.006 | mechanism works once a surprise is bought |
| Surprise discovery, synthetic, free | No early island hit, so the rule never fires (SD equals its base) | first-hit problem |
| Surprise discovery, real NEW | SD + margin − G3 +0.002 [−0.024, +0.029]; SD + straddle − E1 −0.049 [−0.083, −0.022] (no-Keyhole discovery AUDC) | **no discovery gain**. Straddle already searches the rare regime and finds 92% of the no-Keyhole runs by B40 |
| Physical auxiliary over x alone | PHYS_AUX − GPC_X +0.093 [+0.016, +0.175] (r3–4) and +0.064 [+0.020, +0.108] (r5–8, 4/4 positive) | **practically better; reproduced** |
| Physical auxiliary vs G3 | +0.046 [−0.029, +0.117] (r3–4); +0.070 [+0.024, +0.112] (r5–8, one repeat −0.005, one at 6/10 short-K) | no practical difference (strict rule) |
| Physical auxiliary vs ACTIVE E1 | −0.006 (r3–4); −0.025 (r5–8) | no practical difference; E1 is stronger |
| E1 + physical auxiliary vs E1 (correction) | −0.009 [−0.031, +0.010]; −0.000 [−0.013, +0.013] | **no difference**: physics is redundant once depth is modelled |

**Contribution split (r3–4):**
- **Decision threshold:** all arms use their frozen 0.5 / straddle rules here.
- **Probability ranking:** PHYS_AUX and E1 reach AUC 0.91–0.92 and corner AUC 0.64; G3 reaches AUC 0.84 / 0.60 and corner AUC 0.54.
- **Calibration:** Brier is 0.05 for PHYS_AUX vs 0.10–0.11 for G3.
- **Query path:** all margin- and straddle-type arms end up buying the corner. SD only reorders queries.

## 3. Physical outputs learned from x (pilot B; out-of-fold, DEV r3–4; train = fold pool)

| Summary | GP R² (r3 / r4) | Verdict | Relative RMSE | 90% coverage | Corner AUC: observed / x-predicted (diagnostic) |
|---|---|---|---|---|---|
| KE_T0 median (nJ) | 0.73 / 0.75 | LEARNABLE | 0.14 | 0.93 | 0.705 / 0.773 |
| Velocity spike log(p99.9/median) | 0.88 / 0.86 | LEARNABLE | 0.14 | 0.90 | 0.758 / 0.667 |
| Velocity spike duration (µs) | 0.71 / 0.70 | LEARNABLE | 0.63 | 0.87 | 0.712 / 0.561 |
| KE spike log-ratio | 0.30 / 0.35 | WEAK | 0.70 | 0.93 | 0.242 / 0.598 |
| KE → depth peak lag (µs) | 0.24 / 0.19 | WEAK | 3.13 | 0.86 | 0.530 / 0.477 |
| Laser power to melt, T0 (W) | 0.91 / 0.92 | LEARNABLE | 0.06 | 0.94 | 0.576 / 0.720 |
| Max melt temperature, T0 (K) | 0.82 / 0.87 | LEARNABLE | 0.02 | 0.86 | 0.530 / 0.621 |

- **Starting point:** Week 7 (OLD-era data) had KE_T0 R² 0.89.
- **New answer:** on NEW, steady physics and the velocity **spike size** are learnable from x, while KE spike timing is not.
- **QC:**
  - 135/136 runs usable. The early-ended H-e7dbd8e5ce is UNAVAILABLE for time summaries; its raw KE has 0 non-finite values.
  - 931 non-finite KE values are in H-ce04be44b1, plus 364 and 63 in two other runs.
  - 39 implausible velocity rows in 9 runs.
  - Everything is counted; nothing is silently excluded.

## 4. Temporal GP q(x, τ) on melt velocity (pilot C; exact Kronecker GP, 5-D)

- **Curve:** R²_curve 0.64 / 0.64 (RMSE 0.21 vs 0.35 for the mean curve); corner R²_curve 0.98.
- **Peak size:** error 1.17–1.18 vs 1.38 log units, so the GP is better.
- **Peak timing:** worse, 7.4–7.9 vs 6.5 bins.
- **Uncertainty:** coverage 0.87.
- **Cost:** about 1 s per fold, 38 s wall.
- **Verdict:** USEFUL at the curve level. The spike timing that matters for brief events is not captured.

## 5. What this means and what is left to the owner

- **What carries the signal.** E1's depth response already carries the useful physics. Adding learned energy and velocity outputs helps a label-only classifier, but adds nothing on top of E1.
- **Surprise-driven local search.** It helps only for isolated islands that the base selector ignores; NEW's rare regime is not one.
- **The open question is the same as before.** Whether corner labels are learnable at all needs new simulations inside the corner, or a target decision on brief Keyhole events; both are owner decisions.
- **Astra's new package** (`astra_monitor_discovery_20261016`) was received but not run: it is not frozen (no `FROZEN_MANIFEST.json`). Its null and bad-monitor worlds and its same-schedule ablation are a 1-thread option for the owner (`COORDINATION.md`).
