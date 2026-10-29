# C1 stability (C1S): registered protocol for the fresh test

**Registered** 2026-10-29, before any fresh result. Frozen by:
- the SHA-256 manifest `freeze/C1S_MANIFEST.json`;
- the registration commit on branch `c1-stability-20261029`, pushed.

Every worker verifies the manifest before its first unit.

## 0. What was done before registration (DEV only)

- **Diagnosis:** `diag/DIAGNOSIS_C1S.md`, on already-evaluated C1C data (STD 203–282, RAND8 283–302, LOCAL8 303–322). It includes an instrumented, bit-exact replay of 50 learners chosen by ID.
- **Decision-layer screen:** `dev/DEV_SCREEN.json`, path-identical variants of C1 on the same data.
- **Dry run:** the evaluation and export code below was run on the OLD C1C units only. It reproduces the DEV screen, and its exports pass the independent recomputation.
- No fresh ID was used for anything.

## 1. Mechanism found on DEV

**The regressions**
- C1's late regressions are single near-boundary test points (median |p − 0.5| = 0.023).
- They are mostly Keyhole points (68 % of the BA lost), in the label-interleaved fast-scan corner (×5.7) and the hard group (×7).
- Each new margin label flips them locally (55 % in the nearest quarter; 80 % towards the new label).
- Components:
  - classifier refit, 62 %;
  - smooth MAP hyperparameter drift, 28 %;
  - configuration-weight switches, 12 %;
  - response standardisation, about 0 %;
  - no second hyperparameter mode.
- Flips are balanced: 0.24 harmful against 0.27 helpful per step.

**The shortfall**
- They explain about 18 % of the B24–B60 shortfall below 0.95.
- The rest is a persistent level deficit of hard test folds, the irreducible interleaved runs found in EA.

## 2. Candidates and the one carried forward

**Candidates.** At most two were screened on DEV. Both are path-identical decision layers on C1's own probabilities:
- AVG4: mean of the last 4 budgets, from b = 25;
- HYST05: decision hysteresis ±0.05.

**Dropped before becoming a candidate:** mode averaging, because the two MAP starts reach the same optimum.

**Selection rule** (applied on DEV): the lowest mean ΔS95 among candidates that meet every harm limit of §4.
- HYST05 failed the spend limit (0.95 restricted-mean saving LCB −1.27 < −1.0).
- **AVG4 is carried.** On DEV:
  - ΔS95 −0.0001 [UCB −0.0000];
  - sustained(0.95) +0.058 [+0.037];
  - 0.95 saving −0.52 [−0.91];
  - early identical.

**AVG4, exactly** (`src.c1s_dev.variant`, b0 = 24):
- For b ≤ 24, the reported probability is C1's own p_b.
- For b ≥ 25, it is (p_{b−3} + p_{b−2} + p_{b−1} + p_b) / 4, each p computed by C1 at that budget from the runs opened by then.
- Decision threshold 0.5.
- The query path, the selector (margin on C1's current p) and the opened runs are C1's. There are no extra queries, and the CPU cost is negligible (averaging four stored vectors).

**Simple mechanism controls** (same path, same runs):
- EVERY4 = "update less often": for b ≥ 24, the probabilities of the last multiple-of-4 budget.
- FREEZE24 = "freeze at a fixed budget": for b ≥ 24, p_24.

**References:**
- unchanged C1 + margin (the method);
- HA_LEAN + margin (historical reference, own path);
- C1 on HA_LEAN's path (decomposition).

## 3. Fresh IDs and runs

**Inventory.** The highest repeat used before is 322 (STD 1–282, RAND8 / LOCAL8 1, 35–42 and 283–322, the C1S DEV trace on 203–275).

| set | repeats × folds | learners | role |
|---|---|---|---|
| STD | 323–362 × 5 | 200 (40 clusters) | primary set, fixed size |
| RAND8 | 363–372 × 5 | 50 (10 clusters) | limited startup control |
| LOCAL8 | 373–382 × 5 | 50 (10 clusters) | limited startup control |

**Runs.**
- Jobs `c1s-main` (400 units) and `c1s-start` (200 units).
- Code: `src/c1s_fwd.py`, using `src/ea_fwd.py` unit_L / unit_X and `src/c1c_fwd.tasks`, all unchanged.
- No interim result is looked at. The size, the candidate and the rules never change after this registration.
- No C4 or protected gate is used.

## 4. Decisions

All contrasts are AVG4 − C1 unless stated. They use individual learners, repeat clusters, one-sided 95 % t bounds, and a 10,000-resample cluster bootstrap check. Pooled values are reported beside.

| decision | quantity | rule |
|---|---|---|
| **STABILITY (primary)** | ΔS95, where S95 = mean over b = 24..60 of max(0, 0.95 − BA(b)) per learner | STABILITY_GAIN_SHOWN if UCB < 0; +PRACTICAL if mean ≤ −0.0005; STABILITY_LOSS_SHOWN if LCB > 0; else NOT_SHOWN |
| EARLY | ΔBA-AULC B8–B24 | EARLY_NONINFERIOR if LCB > −0.003 (C1C's margin, not relaxed); identical by construction, checked |
| FEWER SIMULATIONS (separate) | restricted-mean saving at 0.90 / 0.93 / 0.95 | EA statuses: SAVING_SHOWN (LCB > 0) / NOT_WORSE (LCB > −1) / NOT_SHOWN |
| SUSTAINMENT (secondary, use-specific) | Δsustained(0.93), Δsustained(0.95), over all learners (non-attainers = 0) | SUSTAIN_GAIN_SHOWN if LCB > 0 |

**Harm limits** (all must hold):
- Keyhole recall B24–B60 LCB ≥ −0.005 and conduction recall B24–B60 LCB ≥ −0.005;
- late BA-AULC B24–B60 LCB ≥ −0.003;
- spend: restricted-mean saving LCB ≥ −1.0 at 0.90, 0.93 and 0.95;
- attainment(0.95) and kept(0.95) LCB ≥ −0.05.

**Practical threshold.** −0.0005 is about 8 % of C1's DEV S95 (0.0064) and about 43 % of its fluctuation part (0.00115), the part a stabiliser can address. The DEV expectation (−0.0001) is far from it.

**Use decision** (fixed now):
1. **STABILITY +PRACTICAL and all harm limits met:** adopt AVG4 as C1's reported classifier from b = 25.
2. **Otherwise, if sustained(0.95) SUSTAIN_GAIN_SHOWN and all harm limits met:** recommend AVG4 only for the hold-the-target use (a decision that must stay ≥ 0.95 once reached). C1 stays unchanged for the early and stop-at-target uses.
3. **Otherwise:** keep C1 unchanged; AVG4 is not adopted.

In every case C1 remains the early method; AVG4 equals C1 for b ≤ 24.

**Startup rule.** Descriptive, 10 clusters each; this is a check, not a confirmation. The recommendation is restricted to the standard maximin startup if, in RAND8 or LOCAL8, any of these holds:
- the ΔS95 mean is > 0;
- STABILITY_LOSS_SHOWN;
- a harm limit fails.

**Mechanism checks on the fresh data** (descriptive predictions written now, from DEV):
1. ≥ 90 % of C1's regression steps contain ≤ 2 harmful flips;
2. ≥ 30 % of C1's flips lie in the corner;
3. harmful / helpful flips per step between 0.8 and 1.0;
4. the level part ≥ 70 % of C1's S95;
5. AVG4 roughly halves C1's flips per step.

**Separate reports.**
- C1 − A and AVG4 − A, all metrics.
- AVG4 − EVERY4: does the gain exceed "updating less often"?
- FREEZE24 − C1.
- Per target (0.90 / 0.93 / 0.95) and per system:
  - first attainment;
  - confirmation at b and b + 4;
  - spend including the 8 startup runs and the 4 confirmation queries;
  - attained / censored counts;
  - kept at B60 and above target at B60;
  - sustained from the confirmed b to 60;
  - attainer-only means and medians with denominators;
  - cumulative attainment.
- Both recalls, FN / FP, F2 and precision (supplementary), log loss, Brier, CPU.
- Hard-group recall and specificity, kept beside the old results.
- The EA K5 per-region warning stands; no new geometric split.

**Caveats fixed now.**
- The 61-capped spend score is not a cost or a bound.
- An attainer-only mean is not a general saving.
- "Stability", "early BA" and "fewer simulations" are separate decisions.

**Expectations from DEV** (written before the run): ΔS95 ≈ −0.0001 (SHOWN at most, not PRACTICAL); sustained(0.95) ≈ +0.06; 0.95 saving ≈ −0.5; attainment(0.95) ≈ −0.02. They change no rule.

## 5. Information rules

**Data**
- One 541-run pool. No OLD/NEW routing, no free archive.
- Every opened run counts, the startup included; no run is charged twice.
- Hard-group membership, unopened outcomes and test labels never reach a learner.
- No label, exclusion, threshold or error-weight change.

**Scope**
- C1C stays closed and its frozen code is unchanged.
- No physical simulator, paid service or new physical data.

## 6. Resources and continuity

| item | value |
|---|---|
| runner | `src/c1s_runner.ps1` (copy of the C1C runner): detached via WMI, supervised, checkpointed, O_EXCL unit locks, finished units never rerun |
| window | one 48 h window, 2026-10-29T00:10:41Z – 2026-10-31T00:10:41Z, closed early when done |
| capacity | ≤ 3 single-thread numerical workers (Astra 3, system 2), memory guard 3072 MB |
| coordination | `C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json` (campaign id `opus_c1_stability_20261029`); Astra's files are read, never written |
| estimate | 600 units ≈ 4.2 worker-hours, about 1.5 h wall-clock |
