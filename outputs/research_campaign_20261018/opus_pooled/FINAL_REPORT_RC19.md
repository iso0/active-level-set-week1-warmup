# RC19 — pooled, from-scratch active learning on one 541-simulation pool (Opus): final report

**Evidence label: DEV.**
- All 541 SPH simulations (405 + 136) were inspected in earlier weeks. The 8 final repeats (3–10) are new random partitions of the same runs; they are correlated with each other and are not new physical data.
- Not used: C4, Stage A, the simulator, paid cloud resources, main merges and outbound messages.
- RC18's archive-based "21 fewer simulations" is a conditional transfer result. It is preserved under its own protocol and **not** carried here.

**Records:**
- protocol `PROTOCOL_RC19.md`, frozen in **8f82e404** before any final unit;
- addendum `PROTOCOL_RC19_ADDENDUM_AX.md` (**a93f4a61**);
- definitions `MODEL_DEFINITIONS_RC19.md`;
- single results table `report/RESULTS_TABLE.md` and `report/AX_RESULTS.md`;
- queue `QUEUE.md`;
- ledger rows RC19-* in `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md`.

## 1. Information contract (what "from scratch" means here)

- **One pool:** batch identity selects no model, prior, threshold or acquisition. It is used only for evaluator-side corner diagnostics.
- **Startup:** the 8-point feature-only maximin startup is paid. Every revealed simulation costs one query, including runs with missing channels or truncated records.
- **Updating:** after each query the learner refits on all revealed runs.
- **Never in a learner:** unrevealed or test outcomes, archive emulators, full-data constants, global class counts, short-Keyhole / q20 membership.
- **Shadow validation PASS:** rerunning each learner family with every never-paid outcome randomised gave identical query paths and identical predictions (`data/PAID_ONLY_VALIDATION.json`).
- **E1's full-data one-class default** of log(111 µm) was removed. Until both classes are revealed, every arm predicts the revealed class rate.

## 2. What ran

| Stage | Content | Units |
|---|---|---|
| Data layer | 541-run pooled manifest. Checks: unique IDs; no duplicate conditions (nearest-neighbour 0.076); PHYS_AL and RC18-loader definitions agree; batches compatible where they overlap; 56 OLD runs lack 6 channels and are kept | — |
| Development | pooled DEV repeats 1–2: model and selector screening, full-pool references for absolute levels | 350 trajectories + 20 references |
| **Final** (frozen) | repeats 3–10 × 5 folds: regression 7 arms, region 8, label 7, bounded temporal | **920 units, 0 failed** |
| Addendum AX | Astra's frozen v2 selector (hash-checked copy) on 8 final tasks, SHQ posterior | 32 units, 0 failed |

- **Queue:** a single queue, `src/rc19_runner.ps1`, with a supervisor.
- **Continuation:** verified by killing the runner mid-job (ledger RC19-RESTART-TEST).
- **Capacity:** Opus ≤ 2 threads and Astra's 2 untouched; total ≤ 4 at every launch.

## 3. Results (DEV, final repeats 3–10; paired by repeat; all 8 repeats shown in `report/RESULTS_TABLE.md`)

### A. Physical outputs — 8 outputs per simulation, horizon B80

**PRIMARY A — SHQ vs M0 under the identical MAXIMIN design: BETTER (DEV).**
- R²-AULC (mean of the 8 outputs, B8–B80): +0.035, positive in **8 of 8** repeats (+0.021 to +0.077).
- Means: M0 0.817, M0Q 0.826, SHQ 0.852.

**Where the gain comes from (8 of 8 each):**
- sharing lengthscales (SHQ − M0Q): +0.026;
- paid-record quality (M0Q − M0): +0.009.

**Acquisition, same model:**

| Contrast | ΔR²-AULC | Repeats in favour |
|---|---|---|
| MOIVR − MAXIMIN, given SHQ | +0.010 | 7 of 8 (SHQ + MOIVR 0.862, the best arm) |
| MOIVR − MAXIMIN, given M0Q | +0.024 | 8 of 8 |
| RANDOM − MAXIMIN | ≈ 0 | – |

Under MOIVR, SHQ − M0Q is +0.011 (8 of 8).

**Calibration at B16 (mean of the outputs):**
- cov90: SHQ 0.850 vs M0 0.782;
- NLPD: 2.45 vs 3.79.

**Queries to the absolute level** (confirmed at b and b + 4; only pairs where both arms reached it). SHQ vs M0 under MAXIMIN saves:

| Output | Simulations saved |
|---|---|
| Energy | 8 |
| Particle number | 8 |
| Spike log-ratio | 7 |
| Laser | 3.5 |
| Depth | 1.5 |
| Temperature, KE | about 0 (both reach the level by B8–B16) |
| **Spike duration (level 0.60)** | none: never reached under MAXIMIN by either model (censored in 16 of 16) |

These are per-output numbers and are not added up.

**Joint campaign endpoint** (all 8 outputs at their levels at the same budget):
- not reached by any MAXIMIN arm (0 of 8);
- reached by SHQ + RANDOM in 7 of 8 repeats (confirmed at 36–72) and M0Q + MOIVR in 5 of 8 (44–76).
- It is limited by spike duration, a zero-inflated output whose attainable full-pool R² is only 0.70.

### B. Velocity-spike region {spike log-ratio ≥ log 2} — horizon B60

**PRIMARY B — STRADDLE vs MAXIMIN under SHQ: BETTER (DEV).**
- BA-AULC +0.027, positive in **8 of 8** repeats.
- Means: SHQ + STRADDLE 0.950 vs SHQ + MAXIMIN 0.923.

**Same selector, different model:** SHQ − M0 is +0.015 under STRADDLE (8 of 8) and +0.013 under MAXIMIN (8 of 8).

**TruVaR** (fixed settings β = 1.96, η = 0) − STRADDLE under SHQ: −0.007 (0 of 8). This does not settle the published TruVaR family.

**Queries to BA ≥ 0.95 (confirmed):**

| Arm | Reached | Queries |
|---|---|---|
| SHQ + STRADDLE | 8 of 8 | 21–26, mean 23 |
| M0 + STRADDLE | 8 of 8 | mean 29 |
| SHQ + TRUVAR | 8 of 8 | mean 29 |
| MAXIMIN | 2–3 of 8 | rest censored at B60, so no exact saving can be stated |

**Both recalls at B24, SHQ + STRADDLE:** inside 0.951, outside 0.960.

**Collection is not learning:**
- STRADDLE puts 46 % of its paid runs inside the boundary band (MAXIMIN 18 %).
- TruVaR collects 40 % yet learns less than STRADDLE.

### C. Keyhole label — horizon B60

**PRIMARY C — PHYSCF_ATS_MARGIN (from-scratch physical-output classifier) vs E1_STRADDLE: NOT DIFFERENT (DEV).**
- BA-AULC +0.005 (7 of 8 positive), below the pre-declared 0.02 margin.
- Means: PHYSCF_ATS 0.942, E1 + straddle 0.937, G3 0.928.

**Key secondary — calibration:**
- Mean log loss over B8–B60: 0.160 vs 0.245 (−0.086, lower in **8 of 8** repeats).
- Against G3: −0.103 (8 of 8).
- Brier at B60: 0.033 vs 0.036 (E1) and 0.040 (G3).

**Queries to BA ≥ 0.93 (confirmed, all 8 repeats reached):**

| Arm | Queries |
|---|---|
| PHYSCF_ATS | 11–17, mean 13.9 |
| E1 + straddle | 11–31, mean 19.8 |
| G3 | mean 24.3 |

The paired difference vs E1 is −5.9 queries (fewer in 6 of 8, equal in 1, more in 1). This is exploratory.

**Ablations:**
- **Depth-only physics classifier:** BA-AULC 0.936, log loss 0.181. Temperature and spike add a little discrimination and calibration.
- **Measured-trained, uncertainty-integrated variant (PHYSMC):** 0.940 / 0.178. Cross-fitting is slightly better on both.
- **Label-free path for the same classifier:** 0.932, so margin acquisition adds +0.010.

**Both recalls at B60:** PHYSCF_ATS sensitivity 0.944, specificity 0.963; E1 0.952 / 0.955.

**Other diagnostics:**
- q20 BA about 0.78–0.79.
- Short-Keyhole caught at B60: 16.8 of 22 (pooled rule) and 8.5 of 10 (NEW set) for PHYSCF_ATS, against 17.8 / 8.4 for E1.
- **Failed corner:** conduction recall on the NEW-batch test runs (fast scan, high power) stays at 0.30–0.46 at B60 for **every** arm. The pooled average hides it.
- No fit failures; no one-class folds after the startup.

### D. Time structure (bounded, exploratory)

**Endpoint:** early-horizon peak amplitude, 0–0.25 ms after the run's own onset.

**Pre-declared rule:** a curve model must beat both the scalar GP and the x-independent mean curve by 5 % in ≥ 7 of 8 repeats. **It was never met.**
- **KE:** the scalar GP is better (B16 error 0.12 vs 0.26 for KRONn); the mean curve is 0.78.
- **Temperature:** the scalar GP is better at B16 (117 vs 152 K). At B40 KRONn and PHASE_PCA are better on average (159 vs 176 K) but only in 2–3 of 8 repeats.
- Every model beats the mean curve.
- This is an early-horizon endpoint, not the full trajectory.

### AX. Astra's frozen v2 selector (additive, 8 tasks, SHQ posterior, horizon B40)

**Adapter acceptance PASS:** her SUR information fraction equals a dense GP update to within 2.5e-10; continuation is deterministic; paid IDs are unique; moments are finite.

**Per-task BA-AULC contrasts:**

| Contrast | Δ | Tasks in favour |
|---|---|---|
| (1) local response, boundary_regional − sur_global | −0.003 | 0 of 8 (5 ties) |
| (2) surprise anchors at fixed half-local share, quota_surprise − quota_no_surprise | −0.003 | 0 of 8 |
| (3a) the same model with a different selector, sur_global − STRADDLE | +0.006 | 6 of 8 |
| (3b) sur_global − MAXIMIN | +0.025 | 7 of 8 |

- The trigger fires only 0.38 times per trajectory.
- Her global SUR (with one exploratory random query every 4 steps) is faster early (BA 0.951 vs 0.912 at B16) and equal by B40.

**Status:** her synthetic TEST was still running and she has not inspected its endpoints. This is integration and stability evidence, not a confirmation of her method.

## 4. Recommended model + selector per supported use case (DEV evidence; equations in `MODEL_DEFINITIONS_RC19.md`)

| Use case | Recommendation | Evidence (final repeats) | Fair cost | Limit |
|---|---|---|---|---|
| Several physical outputs per simulation (emulation) | **SHQ** (shared ARD lengthscales + paid-record quality) with **MOIVR** | SHQ vs M0 +0.035 R²-AULC (8 of 8); MOIVR adds +0.010 (7 of 8) | 61 CPU s per 80-query trajectory (MAXIMIN 11 s) | spike duration stays below R² 0.6 until late or never; the joint 8-output target is censored for most arms |
| Velocity-spike region | **SHQ + STRADDLE** | +0.027 BA-AULC vs MAXIMIN (8 of 8); BA ≥ 0.95 after 21–26 simulations in 8 of 8 repeats | 20 CPU s per 60-query trajectory | Astra's global SUR is similar (+0.006, exploratory) |
| Keyhole label, decision at p = 0.5 | **E1 + straddle** or **PHYSCF_ATS + margin**: no BA difference beyond the margin | +0.005 BA-AULC (not different) | 3–4 CPU s per trajectory | the NEW fast-scan corner (conduction recall ≤ 0.46) is unresolved by every arm |
| Keyhole label, calibrated probabilities / fewer runs to BA 0.93 | **PHYSCF_ATS + margin** | log loss −0.086 (8 of 8); BA 0.93 after a mean 13.9 vs 19.8 runs (exploratory) | 4 CPU s | — |

**Not recommended (DEV):**
- TruVaR with these fixed settings over straddle;
- a local or surprise reaction (RC18 and AX: no gain);
- curve models over a direct scalar GP for early-peak endpoints;
- RANDOM over MAXIMIN for regression at equal model (≈ 0).

## 5. Costs (TOTAL revealed simulations; modelling CPU separately)

- **Simulations:** no new SPH simulation was run; each "paid simulation" is a reveal of an existing run. Budgets above are totals including the 8-run startup.
- **Modelling CPU:** final programme 2.82 h; development about 1 h; AX 0.13 h. Per-arm figures are in `report/RESULTS_TABLE.md` (Costs).
- **Wall clock:** 12:24–15:05 UTC on 19 October for the whole RC19 programme, inside the RC18 campaign budget, whose deadline 2026-10-20 08:41:20 UTC was not reset.

## 6. What remains unresolved

1. **The fast-scan corner of the Keyhole label.**
   - NEW-batch conduction runs at high power and fast scan (median VX 0.96 m/s) are mostly called Keyhole by every classifier.
   - Depth, temperature and spike outputs do not separate them; neither does an all-output variant in development.
   - A different measurement or label contract would be needed, for example a morphology or keyhole-duration monitor. This is a separate proposal.
2. **Spike duration** is zero-inflated (54 % zeros among OLD runs, 12 % among NEW) and has a low attainable accuracy. It dominates the joint campaign endpoint.
3. **Astra's method** has no confirmed scientific result yet; her TEST was still running.

## 7. Limits and disclosures

- **DEV only.** Development repeats 1–2 were seen and informed the margins, horizons, arm list and absolute levels (PROTOCOL_RC19 §8).
- **The levels** come from development full-pool references (0.9 × attainable, rounded down to 0.05), not from final outcomes.
- **Repeats are partitions of one set of 541 runs.** Paired consistency across 8 repeats is stability evidence, not independent replication.
- **No multiplicity correction** for exploratory contrasts.
- **Censored endpoints** are reported as censored. No saving is computed where an endpoint was not observed, and per-output savings are never multiplied by the number of outputs.
- **Corrections during this campaign:**
  - RC18-ERRATUM-2, from Astra's audit: RC18's last confirmation pair was not tested; the frozen RC18 verdict is unchanged.
  - RC19-CAP1: a 0.1 s text edit while both slots were busy.
  - The viewer's 4-decimal rounding initially moved a few runs across the cut (up to 0.002 BA). It was fixed before publication; the page now equals the evaluator exactly.

## 8. Reproduction and outputs

- **Queue:** `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc19_start_runner.ps1`. It is idempotent; jobs are listed in `runner/PLAN.json`.
- **Report:** `python -m src.rc19_report all`, then `python -m src.rc19_figures`, `python -m src.rc19_export`, `python -m src.rc19_ax_report` and `python -m src.rc19_viewer final 3`.
- **Figures:** `report/fig_regression_curves.png`, `fig_regression_per_output.png`, `fig_region_curves.png`, `fig_label_curves.png`.
- **Per-budget predictions and every query path:** `report/predictions_{reg,region,label}.npz` and `report/paths.csv.gz`. The unit files themselves are git-ignored and reproducible from the frozen code.
- **Interactive 3D pooled boundary view:** `report/pooled_boundary_view.html`, also a private claude.ai page: https://claude.ai/artifact/KpF6bE47rnzTWr2tmPfRow.
  - Shows final repeat 3 for the region and label tasks.
  - Axes log P, log VX and LS; ST filtered explicitly.
  - Controls for model / selector, budget and the paid runs of a fold.
  - Every balanced accuracy shown equals the evaluator's.
