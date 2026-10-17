# Studies of 2026-10-17: physical outputs, outsider discovery, structured temporal GPs

**Owner approval:** "hepsine onay veriyorum. ne gerekli ise yap" (2026-10-17). This approves the three studies proposed after Ioan's meeting and both monitor downloads.

**Scope:**
- All of this is DEV work on simulations that were inspected before. A new split is not new data.
- The failed C3 superiority decision is unchanged.
- Nothing here used C4, Stage A, the simulator, paid cloud, a main merge or an external message.

**Integrity:**
- Each study was registered and frozen (protocol, validation, manifest, code hashes) before any outcome: PAL-REG/PAL-FIX, PD-REG, TS-REG in `ATTEMPT_LEDGER.md`.
- Repairs made before any outcome are recorded (PAL-FIX). Outcomes are recorded as PD-OUT, TS-NEW, TS-OLD, PAL-OUT.
- Capacity was at most 4 leaf processes with 1 BLAS thread each. One sub-second slip is logged as CAP-OBS.

Tables generated from the frozen result files are in `STUDIES_20261017_TABLES.md` (`src/jdl_studies_report.py`, formatting only).

## 0. Data added (DL2-OUT, PAL-EXT)

**Download:** NEW total energy and particle number, plus the OLD monitor channels. 3639/3639 files were verified against the pinned revisions; 278 OLD paths are missing remotely.

**Usable runs:**

| | NEW | OLD |
|---|---|---|
| Usable for the PHYS_AL monitor targets | 135/136 | 349/405 |
| Unavailable | the early-ended H-e7dbd8e5ce (no active-window cutoff) | 56 runs with no remote velocity, laser power, particle number or total energy channel at the pinned revision |

- The depth target log A is available for all eligible runs.
- One known-malformed token in an OLD bounds file was mapped by Week 7's supervisor-confirmed rule.
- **No silent exclusion:** every unavailable run is listed with its reason in `phys_al/extracted_summaries.csv`.
- **Argon output:** it is not used as a metal-vapour quantity anywhere.

## 1. Study 1 — PHYS_AL: learning physical outputs from x with few simulations

**Question (Ioan):** "try to fit other quantities … energy or temperature", starting from the earlier energy models.
- **New question:** how many paid simulations does each acquisition need to learn a physical output from the four inputs, and does an adaptive design need fewer than a space-filling or random one?

**Design:**
- **Arms:** RANDOM and MAXIMIN (target-independent paths, every target predicted); MAXVAR and IVR (per target); MO_MAXVAR (one shared acquisition over the six primary targets).
- **Model:** GP Matérn 3/2 ARD.
- **Splits and budget:** DEV r3–4 × 5 folds, B8–B60.
- **Scale:** 380/380 trajectories ran, about 42,000 GP fits. Figures: `studies_20261017_figures/phys_al_r2_curves_{NEW,OLD}.png`.

**Attainable accuracy:** R²_full, the out-of-fold R² with the whole fold pool paid (mean of r3, r4).

| Target | NEW R²_full | OLD R²_full |
|---|---|---|
| log A (active maximum depth) | 0.96 | 0.98 |
| laser power to melt, T0 | 0.92 | 0.99 |
| velocity spike log-ratio | 0.87 | 0.91 |
| max melt temperature, T0 | 0.84 | 0.95 |
| velocity spike duration | 0.70 | **0.48 (not learnable)** |
| log KE, T0 | 0.68 | 0.97 |
| log total melt energy, T0 (new channel) | **0.30 (not learnable)** | 0.97 |
| log melt particle number, T0 (new channel) | **0.22 (not learnable)** | 0.96 |

**Budget to the target level** (0.9 × R²_full, sustained; r3 / r4; `+` = censored at 64):

| Target | NEW RANDOM | NEW MAXIMIN | NEW IVR | OLD RANDOM | OLD MAXIMIN | OLD IVR |
|---|---|---|---|---|---|---|
| log A | 12 / 12 | 12 / 12 | 12 / 24 | 20 / 24 | 16 / 24 | 20 / 20 |
| laser T0 | 24 / 16 | 16 / 16 | 16 / 12 | 36 / 32 | 24 / 24 | 32 / 36 |
| max temperature T0 | 20 / 20 | 12 / 20 | 12 / 12 | 20 / 24 | 16 / 20 | 20 / 32 |
| spike log-ratio | 20 / 16 | 44 / 24 | 20 / 12 | 52 / 64+ | 64+ / 64+ | 64+ / 64+ |
| spike duration | 28 / 24 | 64+ / 28 | 52 / 36 | 64+ / 64+ | 64+ / 64+ | 64+ / 64+ |
| log KE T0 | 44 / 20 | 64+ / 16 | 24 / 16 | 12 / 8 | 12 / 8 | 12 / 8 |

**Registered verdicts:** there are 48 comparisons (MAXVAR, IVR and MO_MAXVAR × 8 targets × 2 populations), each against the better of RANDOM and MAXIMIN.

| Verdict | Result |
|---|---|
| FEWER SIMULATIONS (DEV): at least 4 queries earlier than both references, in both repeats | **none** |
| SAME-BUDGET GAIN (DEV): mean ΔAULC ≥ +0.02 and positive in both repeats | **1 of 48**: IVR on laser power T0 in NEW (+0.037 / +0.016) |
| Closest misses | NEW max temperature IVR (+0.015 / +0.024, mean 0.0195); OLD spike log-ratio IVR (+0.022 / +0.013) |

**Answers to the three registered questions:**
1. **Fewer simulations?** No.
   - Space-filling MAXIMIN and even RANDOM learn the physical outputs as fast as any adaptive arm. One pass in 48 comparisons could plausibly arise by chance (interpretation), so it is reported but not generalised.
   - Pure variance sampling (MAXVAR) is often *worse* than the non-adaptive designs, e.g. NEW log KE −0.125 / −0.147 and OLD log particle number −0.052 / −0.065. IVR is the best adaptive rule but stays within about ±0.04 AULC of the references on the learnable targets.
   - By simulation count, the steady physical outputs reach 90% of their attainable accuracy after about 12–24 paid simulations in NEW (log A, laser power, max temperature) and about 8–36 in OLD.
2. **Shared acquisition?** It loses accuracy. The single shared acquisition (MO_MAXVAR) has a lower mean AULC than target-specific IVR in 13 of 16 target–population cases. Because one simulation reveals every output, a target-independent space-filling design is the practical choice.
3. **ICM vs independent GPs?** The answer is descriptive; no rule was registered.
   - The median RMSE ratio ICM / independent over the grid is 0.91–1.00 in NEW and 0.82–1.06 in OLD. ICM is about 5–10% better for log KE and spike duration, but worse at B8 (up to 1.39 NEW, 2.05 OLD), where 22 hyperparameters face 8 runs.
   - As stated in advance, the gains of joint modelling on fully observed (isotopic) outputs are small.

**New-channel answer:**
- **Total melt energy and particle number:** almost perfectly learnable from x in OLD (R²_full 0.96–0.97), but not in NEW (0.22–0.30). This population difference is recorded as an observation. Possible reasons (HYP, not tested): the NEW T0 summaries vary little between runs, or vary in a way the four inputs do not explain.
- **Argon:** no channel was interpreted as metal-vapour quantity.

## 2. Study 2 — PHYS_DISCOVERY: find an outsider, then expand to its family

**Question (Ioan):** "find some kind of an outsider and then expand to find its whole family".

**Setup:**
- **Response:** the velocity spike log-ratio, which is learnable (pilot B R² 0.87).
- **Family:** the top decile, defined on the evaluator side only.
- **Candidate SD_MAXVAR:** a run is a surprise when |z| ≥ 2.5 under the GP fitted before it was paid, and it passes QC. Each surprise triggers up to 3 nearest-unpaid probes, alternating 1:1 with MAXVAR.
- **Design:** DEV r3–4 × 5 folds, B8–B60.

| Population (family size) | Arm | family AUDC | found by B60 | queries to half (cens. 64) | R²-AULC r3 / r4 |
|---|---|---|---|---|---|
| NEW (14) | MAXVAR | 0.503 | 0.82 | 29.6 | 0.765 / 0.795 |
| | SD_MAXVAR | 0.462 | 0.79 | 34.9 | 0.806 / 0.765 |
| | MAXIMIN | 0.479 | 0.76 | 34.7 | 0.766 / 0.824 |
| | RANDOM | 0.383 | 0.61 | 44.2 | 0.780 / 0.763 |
| OLD (35) | MAXVAR | 0.189 | 0.32 | 64 | 0.731 / 0.694 |
| | SD_MAXVAR | 0.178 | 0.29 | 64 | 0.749 / 0.692 |
| | MAXIMIN | 0.185 | 0.31 | 64 | 0.725 / 0.706 |
| | RANDOM | 0.160 | 0.25 | 64 | 0.671 / 0.653 |

**Registered contrast:** SD_MAXVAR − MAXVAR family AUDC, with a 10-pair bootstrap.

| Population | SD_MAXVAR − MAXVAR | Verdict |
|---|---|---|
| NEW | −0.040 [−0.073, −0.009] | **NO DISCOVERY GAIN ESTABLISHED** (the local probes were slower) |
| OLD | −0.011 [−0.039, +0.011] | **NO DISCOVERY GAIN ESTABLISHED** |

The no-harm check passes in both populations (ΔR²-AULC +0.006 / +0.008), but it is moot.

**Descriptive contrasts:**

| Contrast | NEW | OLD |
|---|---|---|
| MAXVAR − RANDOM | +0.119 [+0.065, +0.171] | +0.030 [+0.003, +0.059] |
| MAXVAR − MAXIMIN | +0.024 [−0.027, +0.086] | +0.004 [−0.014, +0.026] |

**Reading:**
- **Variance-driven exploration finds the high-spike family faster than random.** NEW reaches half the family in about 30 queries vs 44.
- **Surprise-seeded local probes add nothing on top of it.** SD_MAXVAR fired 3.2 surprises per trajectory in NEW and 4.6 in OLD. On average 5.0 / 5.3 of its paid runs per trajectory were QC-flagged; QC events are logged for SD_MAXVAR only, so this is not a comparison with the other arms. Its probes spend queries next to a surprise.
- **Interpretation (HYP, not tested here):** high spike values sit where the predictive variance is already high, so plain MAXVAR samples them without a local reaction.
- **This matches pilot A on labels.** The local reaction pays only for an isolated island that the base selector ignores, and neither the label regime nor the high-spike family is such an island here.

## 3. Study 3 — TEMPORAL_STRUCT: structured temporal GPs for monitor curves

**Question (Ioan):** "5d and time is a dimension … some structure for the temporal dimension".

**Setup:**
- **Channels:** log velocity, log KE and log depth, each on 40 onset-normalized bins.
- **Models:**
  - KRON: separable x ⊗ τ (pilot C);
  - PCA: Higdon basis emulator;
  - FULL5D: non-separable GP on (x, τ), NEW only, every 4th bin;
  - SCALAR: a direct GP on each derived quantity.
- **Design:** out of fold on DEV r3–4 with every pool run revealed, so this is an upper bound, not an acquisition result.

**NEW** (135 curves per channel; repeats 3 / 4):

| Channel | R²_curve KRON | R²_curve PCA | R²_sub KRON vs FULL5D | T0 RMSE best temporal vs SCALAR | peak RMSE best temporal vs SCALAR | abs. peak-position error, MEAN / KRON / PCA (bins) |
|---|---|---|---|---|---|---|
| velocity | 0.64 / 0.64 | 0.68 / 0.67 | 0.65 vs **0.69** / 0.65 vs **0.69** | 0.158 vs **0.149** / 0.158 vs **0.147** | 0.226 vs **0.121** / 0.223 vs **0.127** | 3.9 / 5.4 / 3.9 · 3.7 / 6.1 / 3.7 |
| KE | 0.26 / 0.26 | 0.28 / 0.23 | 0.22 vs 0.20 / 0.22 vs 0.24 | 0.172 vs **0.155** / 0.179 vs **0.144** | 0.267 vs **0.195** / 0.280 vs **0.177** | 8.2 / 5.9 / 7.5 · 8.2 / 5.8 / 8.3 |
| depth | 0.55 / 0.56 | 0.51 / 0.53 | 0.55 vs 0.55 / 0.57 vs 0.49 | 0.165 vs **0.155** / 0.188 vs **0.173** | 0.144 vs **0.074** / 0.167 vs **0.078** | 3.5 / 7.5 / 6.3 · 3.5 / 7.5 / 7.3 |

**Verdicts (registered):**

| Verdict | Velocity | KE | Depth |
|---|---|---|---|
| STRUCTURE HELPS (PCA ≤ 0.95 × KRON curve RMSE, both repeats) | no; closest at 0.952 | no | no |
| FULL5D beats KRON on the subgrid | **yes** | no | no |
| TEMPORAL BEATS SCALAR (T0 level, peak height) | no | no | no |

- **Coverage (90% nominal):** 0.87–0.93.
- **Median fit cost:** KRON 1.8 s, PCA 0.37 s, FULL5D 17.4 s.

**Reading:**
- **The curves can be emulated.** Velocity reaches R²_curve 0.64–0.69 and depth 0.51–0.56; KE does not (0.23–0.28).
- **Treating time as a dimension with a non-separable kernel helps velocity.** FULL5D gains +0.05 R² over the separable kernel, at about 10× the cost.
- **A curve model is the wrong tool for a scalar question.** For the T0 level and the peak height, a direct scalar GP is better in every channel, e.g. peak 0.12 vs 0.23 log units for velocity.
- **Peak timing is mostly not learned.** For velocity and depth, no temporal model locates the peak better than the mean curve; KRON is worse (5.4–7.5 vs 3.5–3.9 bins). KE is the exception: KRON locates the peak better than the mean curve (5.8–5.9 vs 8.2 bins).

**OLD** (349 curves per channel; KRON and PCA only, by protocol; repeats 3 / 4):

| Channel | R²_curve KRON | R²_curve PCA | T0 RMSE best temporal vs SCALAR | peak RMSE best temporal vs SCALAR | abs. peak-position error, MEAN / KRON / PCA (bins) |
|---|---|---|---|---|---|
| velocity | 0.85 / 0.85 | 0.85 / 0.86 | 0.161 vs 0.165 / 0.158 vs 0.160 | 0.134 vs **0.091** / 0.143 vs **0.095** | 11.9 / 7.9 / 7.6 · 12.4 / 7.1 / 7.9 |
| KE | 0.94 / 0.94 | 0.93 / 0.94 | 0.122 vs **0.115** / 0.125 vs **0.113** | 0.128 vs 0.127 / 0.133 vs 0.124 | 5.6 / 3.1 / 4.4 · 5.6 / 3.3 / 4.3 |
| depth | 0.95 / 0.95 | 0.94 / 0.94 | 0.094 vs **0.085** / 0.094 vs **0.088** | 0.126 vs **0.100** / 0.120 vs 0.122 | 8.2 / 6.4 / 9.0 · 8.5 / 6.2 / 8.7 |

**Verdicts:**
- STRUCTURE HELPS: **no** in every channel.
- TEMPORAL BEATS SCALAR: **no** in every channel and quantity.

**The closest calls:**
- **Velocity T0:** the best temporal model, PCA, is about 2% better than SCALAR, short of the registered 5%.
- **KE peak:** KRON and SCALAR are within 1–7% of each other.
- **Depth peak, repeat 4:** KRON is marginally better, 0.120 vs 0.122.

**Cost:** median KRON 10.0 s and PCA 1.4 s per fit, with about 280 training curves per fold.

**NEW vs OLD:**
- **Curve quality:** OLD curves are emulated much better than NEW curves (R²_curve 0.85–0.95 vs 0.23–0.68). OLD runs differ more from each other (MEAN-curve RMSE 0.40–0.73 vs 0.35–0.54), and the pools are about 2.6× larger.
- **Peak timing:** in OLD, KRON locates the curve peak better than the mean curve in every channel.
- **The decisive control does not change:** a direct scalar GP is as good or better for the scalar summaries in both populations.

## 4. What this means for the thesis

The three studies follow the owner's priority order.

**1. Active discovery of interesting regions (Ioan's "outsider → family").**
- **Result: a null on real data, in both forms tested.** These are pilot A on the binary label and Study 2 on a continuous physical response, the top decile of the velocity spike log-ratio.
- **What works is plain uncertainty sampling.** It finds the extreme-response family faster than random: NEW +0.119 AUDC, about 30 vs 44 queries to half of the family.
- **The surprise-seeded local expansion adds nothing**, and in NEW it is slower (−0.040 [−0.073, −0.009]).
- **The mechanism itself works only on a planted, isolated island** (synthetic, pilot A).
- **Thesis statement:** "On these SPH populations, outsider-driven local expansion does not improve discovery over variance-driven exploration. Its benefit requires an isolated region that the base selector ignores, and no such region was found."

**2. Energy, temperature and flow outputs from the four inputs (Ioan's "fit other quantities").**
- **Learnable from x:**
  - in NEW, the steady physical outputs and the spike size, R²_full 0.68–0.96;
  - in OLD, every output except spike duration, R²_full 0.91–0.99.
- **The new NEW channels, total melt energy and particle number, are not learnable** (R²_full 0.22–0.30), while the same channels are in OLD.
- **No acquisition rule needs fewer simulations** than a space-filling or random design. The only same-budget gain is 1 of 48 comparisons.
- **Thesis statement:** "For multi-output emulation of physical summaries, a target-independent space-filling design is as efficient as adaptive variance-based acquisition. About 12–24 simulations reach 90% of the attainable accuracy for the steady outputs."
- **Pilot findings that still stand:** physics helps a label-only classifier, but it is redundant over E1's depth response.

**3. Temporal GP (Ioan's "time is a dimension").**
- **Monitor curves can be emulated:** R²_curve 0.85–0.95 in OLD; in NEW, 0.64–0.69 for velocity and 0.51–0.56 for depth. NEW KE is the exception at 0.23–0.28.
- **A non-separable 5-D GP improves the NEW velocity curve** over the separable Kronecker GP (+0.05 R²), at about 10× the cost.
- **The PCA basis emulator** (Higdon et al. 2008) is the cheapest model and never worse by more than about 10%. It did not pass the registered 5% improvement bar.
- **A direct scalar GP is better for scalar summaries** (T0 level, peak height) in every channel and population.
- **Peak timing:** for NEW velocity and depth it is no better than the mean curve. It is better for NEW KE and for every OLD channel.
- **Thesis statement:** "Temporal emulators reproduce the monitor curves, but a quantity of interest that is a scalar summary should be emulated directly."

**Short-K:** these studies change nothing for short-K. They contain no new classifier, so the short-K results stand as reported in section 6 of the claims matrix.

**Overall:**
- No new method beats the established ones on these data.
- The studies do give the thesis three registered answers to the supervisor's questions, with honest nulls and a clear practical recommendation: a space-filling design for physical outputs, a scalar emulator for scalar summaries, and variance sampling rather than surprise-local search for discovery.
- No further numerical study is needed to write these chapters.

## 5. Limits and disclosures

- **DEV only.** All repeats were inspected before, and the families and targets are evaluator-defined. R²_full and every TEMPORAL_STRUCT model use every pool run, so they are upper bounds.
- **Study 2:** the validation printed one trajectory's event counts before the freeze (disclosed in the protocol). The family threshold is computed from all runs on the evaluator side; no selector sees it.
- **Study 3, OLD:**
  - The frozen curve loader reads all three channels in one step. The 56 OLD runs without a remote velocity file are therefore UNAVAILABLE for the KE and depth curves too, although those two files exist.
  - This is a coded limitation, recorded in the status counts and not changed after the outcome. It reduces OLD to the 349 runs with complete monitors.
- **Study 1, ICM:** the ICM fits use only the paid runs where all six primary targets are finite, while the independent GPs use each target's own finite runs. In OLD this gives ICM fewer runs for log A, a small disadvantage that was coded before the outcome.
- **Study 1, multiplicity:** there were 48 registered acquisition comparisons and no correction for multiplicity. The single SAME-BUDGET GAIN is therefore reported as a DEV observation, not as a property of IVR.

## 6. Figures and compute

**Figures** (`studies_20261017_figures/`, from `src/jdl_studies_figures.py`): descriptive plots of the registered endpoints, made from the frozen caches with the evaluators' definitions and no new fits.
- `phys_al_r2_curves_NEW.png` and `phys_al_r2_curves_OLD.png`: R²(b) for every target and arm, with the target level.
- `phys_discovery_curves.png`: the fraction of the family found against the budget, with interquartile bands.
- `temporal_struct_summary.png`: curve accuracy, FULL5D vs KRON, and derived quantities relative to SCALAR.

**Compute:**

| Step | Wall time (UTC) | Threads |
|---|---|---|
| Units of Studies 1–3 and ICM | 23:24–23:48, 2026-10-16 | ≤ 4 leaf processes × 1 BLAS thread |
| Evaluations | ≤ 23:50 | 1 |
| Total CPU | ≈ 1.3 CPU-hours | — |

**Not used:** simulator, cloud, C4 or Stage A.
