# Research campaign 20261018 — physical modelling and sample efficiency (Opus)

**Evidence label: DEV.** All numbers come from previously inspected SPH simulations: NEW (136 runs) and OLD (405 runs), always evaluated separately.
- The final repeats 5–8 are new random partitions of the same simulations, not new data.
- C3's decision stands. C4, real-data Stage A, the simulator, paid cloud resources, main-branch merges and outbound messages were not used.

**Records:**
- **Protocols:**
  - frozen protocol `PROTOCOL_20261018.md` (manifest commit eaba0c8d, before any final run);
  - addenda A1–A4 (`PROTOCOL_ADDENDUM_A1..A4.md`), each committed before it ran;
  - D2 protocol `temporal/TEMPORAL_PHASE_PROTOCOL.md` (b6466777).
- **Attempts:** `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md`, rows RC18-* (including the erratum RC18-FINAL-P-ERRATUM).
- **Coordination:** `pool/POOL_PLAN.json` and `COORDINATION.md`.
- **Single results table:** `report/RESULTS_TABLE.md`, sections 1–13. Every CSV and figure is in `report/`.

## 1. Main answer

**Verdict (frozen primary rule): FEWER SIMULATIONS (DEV).** The saving comes from the model, not from the acquisition.

1. **Physical outputs (NEW, primary).** TRSQ combines three things:
   - the OLD campaign as the GP prior mean;
   - lengthscales shared across the 8 outputs of each simulation;
   - a QA-aware observation model for truncated records.

   It reaches the sustained target accuracy (0.9 × R²_full of the simple GP M0) with **21.0 fewer NEW simulations per output** on average (per repeat 13.3 / 32.7 / 19.3 / 18.7). It needs **zero NEW simulations for 5 of the 6 outputs, in all 4 repeats**. The result replicates on DEV repeats 3–4 (22.3). Without a predecessor campaign, sharing plus QA alone save about 10 of 26 simulations (exploratory).
2. **Acquisition adds little for these outputs.** Against the space-filling MAXIMIN design, MOIVR and RANDOM change R²-AULC by at most ±0.015 and never save more than about one simulation on average. Under the transfer model, MOIVR needs 6.7 *more* simulations (4/4 repeats), and a transfer-gap selector (A2) is worse in 4/4 repeats.
3. **Physically defined region (OLD velocity-spike level set; exploratory).** Here the acquisition matters as much as the model:
   - straddle: +0.035 BA-AULC;
   - shared-kernel model: +0.033;
   - together: about 22 instead of ≥ 44 simulations.

   TruVaR does not beat straddle. Astra's surprise-triggered local reaction adds nothing under the same global schedule.
4. **Keyhole label (NEW; exploratory).** The physics-mediated cross-campaign classifier PHYS_TR reaches BA 0.69 and AUC 0.92 with **zero NEW simulations**, and it is the best-calibrated arm. Active E1 + straddle matches it at about B16 and leads from about B24 (0.74 at B40). A residual GPC on top of PHYS_TR (A4) changes nothing. No arm resolves the NEW fast-scan corner (specificity ≤ 0.50).
5. **Time structure (D2; exploratory).** Native-time level features (onset, plateau, t90, KE early peak) are learnable and transfer across campaigns. Curve models do not beat scalar GPs at B16 or B40. The pre-registered "temporal beats scalar" rule is met mostly trivially, because an x-independent mean curve meets it too. It is met genuinely only for the OLD temperature early-peak amplitude with the whole pool.

## 2. What was run

| Step | What | Where |
|---|---|---|
| Coordination | One machine record, `pool/POOL_PLAN.json`. Opus has 2 threads; Astra has 2, reserved at 08:46:11 UTC before any heavy Opus work. Astra's share was never used by Opus, and Astra registered no jobs. | `COORDINATION.md` |
| Runner | `src/rc18_runner.ps1` plus a supervisor, launched detached via WMI (runner PID 29180, supervisor PID 7136). Units are checkpointed and finished units are skipped. The deadline is enforced. A failure pauses only the failing job. Heartbeat every 30 s. Every production job exited 0 with 0 failed units; the crash self-test failed by design. | `runner/`, `COORDINATION.md` job table |
| Astra's pilot | Her frozen 17-Oct package, run once from a hash-identical copy: COMPLETE, 578 fits, 10.6 s. The surprise trigger never fired, which is the first-hit problem. | `../astra_pilot/` |
| Fix A1 | Variance contract: a hand-solvable GP check, an exact 20/20 replay, and the prospective PHYS_DISCOVERY v1.1 (NO DISCOVERY GAIN, unchanged). | `fixes/A1_variance_contract/` |
| Fixes A2/A3 | Channel-independent loader; separate QA counters (row mismatch ≠ non-finite values); three summary families; the 40-bin peak loss measured. | `data/` |
| Inspection | Ranges, physics coordinate, regime heteroskedasticity, OLD→NEW transfer, truncated records, label transfer. Results-independent; it chose directions D1 and D2. | `inspection/` |
| Development | DEV repeats 1–2: 480 trajectories (regression 140, MOIVR 50, region 240, label 50), 0.85 CPU h. Used to choose RICH and the Q rule. | `main/dev/` |
| Final programme | DEV repeats 5–8, frozen: regression (5 NEW and 2 OLD models × 3 designs), region (2 models × 6 acquisitions), label (5 arms). 880 trajectories. | `main/final/` |
| D2 | Native-time phase features and early-horizon curve models: 160 units. | `temporal/` |
| Addenda | A1 (repeats 3–4), A2 (transfer-gap design), A3 (PHYS_TR), A4 (PHYS_GPC): 210 trajectories. | `main/robust_r34/`, `main/transfer_design/`, `main/physlabel/`, `main/physgpc/` |

## 3. Models, acquisitions and endpoints (definitions)

### 3.1 Common GP engine (`src/rc18_gp.py`; equal to sklearn's ML-II optimum to 1e-13)

  y_i = m0(x_i) + μ + σ·f(z_i) + ε_i,   f ~ GP(0, s_f² k₃⁄₂(z, z′; ℓ)),   ε_i ~ N(0, σ² s_n² w_i)

- **Kernel:** k₃⁄₂(r) = (1 + √3 r) e^{−√3 r}, with r² = Σ_d (z_d − z′_d)² / ℓ_d².
- **Inputs:** z are the fold-standardised log inputs (P, VX, LS, ST).
- **Scaling:** μ and σ are the mean and SD of y − m0 over the paid rows.
- **Fit:** ML-II by L-BFGS-B with analytic gradients.
- **Prediction:** latent mean μ*(x), latent variance v*(x), and observation variance v*(x) + σ² s_n² w. The noise is never added twice (fix A1).

### 3.2 Regression model family

- **M0** (simple; PHYS_AL's GP): m0 = 0, w_i = 1, per-output ML-II.
- **Q** (QA-aware observation model): w_i = 10⁴ if paid run i ended before 0.95 × its planned end time TE, else 1. The truncated run stays paid, keeps its label and is evaluated.
- **SH** (partial sharing across outputs): one ARD lengthscale vector ℓ is shared by the 8 outputs, maximising Σ_k log p(y_k | ℓ, s_f,k², s_n,k²). Each output keeps its own variances.
  - With isotopic outputs and a common kernel, cokriging equals kriging. An ICM would add parameters but no predictive information. What remains to gain is better-identified hyperparameters.
- **TR** (cross-campaign transfer, NEW only): m0(x) = μ_OLD(x), the posterior mean of a GP fitted once on all OLD runs per target. The OLD runs predate NEW and need only x at a NEW run. A residual GP is fitted on the paid NEW rows. Below 5 usable rows, the model is μ_OLD + the mean residual.
- **RICH:** TRSQ = TR + SH + Q for NEW; SHQ for OLD.

### 3.3 Acquisitions

| Name | Rule |
|---|---|
| MAXIMIN | the frozen label-free space-filling path; its first 8 points are every arm's common start |
| RANDOM | seeded random choice |
| MOIVR | argmax_x Σ_t IVR_t(x) / Var(paid y_t), with IVR_t(x) = Σ_{j∈pool} Cov_t(j, x)² / (v_t(x) + noise_t) |
| STRADDLE | argmax 1.96 √v(x) − \|μ(x) − τ\| |
| TRUVAR | argmax total latent-variance reduction over the unclassified set {\|μ − τ\| < 1.96 √v} (Bogunovic et al. 2016, LSE form) |
| ASTRA_SURPRISE / ASTRA_STRADDLE_GLOBAL | Astra's frozen ask/tell `SurpriseLocalDiscovery` selector, with the local reaction on or off under the same global schedule |
| GAP0 (A2) | argmax Σ_t [v_δ,t(x) + v_OLD,t(x)] / Var_t (the transfer gap) |

### 3.4 Keyhole label models (NEW)

- **G3_MARGIN:** Week 18 G3, a GP classifier on x (ML-II). Query argmin \|p − 0.5\|.
- **ACTIVE_E1_STRADDLE:** frozen Week 18 E1.
  - A GP regression of log depth A on x.
  - The Keyhole threshold u comes from the paid (log A, label) pairs: the midpoint if they are separable, otherwise a 1-D logistic boundary; the default is log 111 µm.
  - P(K \| x) = Φ((μ_A(x) − u) / σ_A(x)).
  - Query argmax 1.96 σ_A − \|μ_A − u\|.
- **TR_E1_STRADDLE:** the same rule and acquisition, with the depth model TRQ.
- **PHYS_TR (A3):**
  - P_phys(x) = (1/S) Σ_s g(ỹ_s(x)), with ỹ_s ~ N(μ_TRSQ(x), diag v_obs(x)) and S = 400.
  - The three outputs are log A, spike log-ratio and max temperature T0.
  - g is a logistic regression on standardised outputs, trained on the OLD campaign's observed outputs and labels plus the paid NEW runs (truncated records excluded).
- **PHYS_GPC (A4):**
  - f(x) = logit(clip(P_phys(x), 0.01, 0.99)) + r(x), with r ~ GP(0, C·k₃⁄₂-ARD).
  - Bernoulli-logit likelihood, Laplace approximation, ML-II.
  - P(K \| x) is the predictive probability. A failed fit falls back to P_phys.
- **Arms:** "_MARGIN" or "_STRADDLE" are adaptive; "_MAXIMIN" follows the label-free path. Selectors never receive unpaid or test labels, short-K or q20 membership.
- **Rule used throughout:** predicted auxiliary outputs are functions of x, not measurements. In PHYS_TR the information comes from the OLD campaign's observed outputs and labels; the predicted NEW outputs only carry it to NEW inputs.

### 3.5 Temporal models (D2)

- **Phase features per run** (5-µs block-median curve c(τ), τ = t − t_on):
  - t_on;
  - plateau (T0 median; log for KE);
  - t90 = first τ with c ≥ 0.9 × plateau;
  - peak and peak_ms;
  - overshoot = peak / plateau;
  - fluct = (p90 − p10) / plateau;
  - epeak and epeak_ms: the peak inside τ ∈ [0, 0.25 ms].
- **KRONn:** k((x, τ), (x′, τ′)) = k₃⁄₂(x, x′) · k₃⁄₂(τ, τ′), on the 50 native 5-µs blocks of [0, 0.25 ms].
- **PHASE:** ĉ(τ \| x) = p̂(x) · ḡ(τ / t̂90(x)) for temperature, and exp(log p̂(x) + ḡ(τ / t̂90(x))) for KE. ḡ is the mean normalised training curve; p̂ and t̂90 come from the scalar GPs, from x only.
- **PHASE_PCA:** ḡ + Σ_{k≤3} ŝ_k(x) φ_k(u).

### 3.6 Endpoints

- **R²(b)** = 1 − Σ(y − μ)² / Σ(y − ȳ)² over the test runs, pooled over the 5 folds of a repeat. **R²-AULC** = mean R² over B8–B60.
- **Sustained budget-to-target:** the first b on {0, 4, …, 56} with R² ≥ level at both b and b + 4, censored at 64. The level is 0.9 × R²_full(M0). Queries saved: S = B_M0 − B_RICH.
- **Region:**
  - BA(b) = ½ (recall_in + recall_out) of {μ ≥ τ}, with τ = log 2;
  - BA-AULC over B8–B40;
  - budget to 0.95 × BA_full(M0), censored at 44;
  - collection = share of paid runs with \|y − τ\| ≤ 0.25.
- **Label:** BA at p ≥ 0.5, sensitivity, specificity, q20, short-K captured/total, Brier, log loss, AUC.
- **Calibration:** cov90 = share of test runs inside μ ± 1.645 sd_obs; NLPD.
- **False confidence:**
  - **(§5b)** share of trajectories whose true R² is below the level when the learner's own self-R² first claims it. Self-R² = 1 − mean predictive observation variance / variance of the paid outputs, sustained over 2 grid budgets.
  - **(§13, the protocol's wording)** share of test runs outside the 90 % interval at that claim budget.

## 4. Results

### 4.1 PRIMARY — NEW physical outputs, TRSQ vs M0 under the identical MAXIMIN design

**FEWER SIMULATIONS (DEV)** under the frozen rule (mean saved ≥ 8, every repeat > 0, no target < −4).

| Target | M0: NEW simulations to the level (mean of 4 repeats) | TRSQ | Saved |
|---|---|---|---|
| log A (depth) | 12.0 | 0 | 12.0 |
| log KE T0 | 28.0 | 0 | 28.0 |
| spike log-ratio | 28.0 | 0 | 28.0 |
| spike duration | 45.0 | 29.0 | 16.0 |
| laser T0 | 21.0 | 0 | 21.0 |
| max temperature T0 | 21.0 | 0 | 21.0 |
| **mean** | **25.8** | **4.8** | **21.0** |

- **Saved per repeat:** 13.3 / 32.7 / 19.3 / 18.7.
- **R²-AULC (B8–B60):** +0.083 (per repeat +0.049 / +0.132 / +0.080 / +0.072).
- **"0":** the level is held at B0 and B4 without any NEW simulation, in all 4 repeats.
- **Figures:** `report/budget_to_target_NEW.png`, `report/learning_curves_NEW.png`, and `report/transfer_scatter_NEW.png` (OLD emulator vs NEW observed).

### 4.2 Where the gain comes from (E1 decomposition, NEW, MAXIMIN; exploratory)

| Step | R²-AULC | Simulations saved | Repeats in favour |
|---|---|---|---|
| QA: M0Q − M0 | +0.029 | 5.0 | AULC 4/4; budget 3/4 |
| Transfer: TRQ − M0Q | +0.038 | 14.7 | 4/4 |
| Sharing given transfer: TRSQ − TRQ | +0.016 | 1.3 | 4/4 |
| **Sum = primary (TRSQ − M0)** | **+0.083** | **21.0** | |
| Sharing without transfer: SHQ − M0Q | +0.034 | 4.7 | 4/4 |

- **Without a predecessor campaign** (SHQ vs M0): 16.2 instead of 25.8 simulations (all 4 repeats fewer); R²-AULC 0.799 vs 0.736.
- **OLD** (E2; 1 truncated record, no transfer source): SHQ − M0 is +0.008 R²-AULC (4/4) and −0.4 simulations, so no meaningful saving.
- **Why QA matters in NEW:** 6 of its 136 runs have truncated records, which are gross outliers (z down to −80).

### 4.3 Model versus acquisition — the four distinctions

**1. Same model, old vs new acquisition.**
- **Regression:**
  - MOIVR − MAXIMIN: NEW M0 +0.010 (4/4) with +0.7 simulations; NEW TRSQ +0.005 (3/4) with +6.7 (4/4 worse); OLD M0 +0.003 with +1.6; OLD SHQ +0.010 (4/4) with −1.0.
  - RANDOM − MAXIMIN: between +0.000 and −0.015, with 3.4–7.7 more simulations.
- **Region (OLD):** STRADDLE − MAXIMIN is +0.035 under SHQ (4/4, −13 simulations) and +0.016 under M0 (3/4, −9).
- **Label:** E1 + straddle − E1 on the label-free path is +0.093 BA-AULC (4/4); TR_E1 straddle − maximin is +0.067 (4/4). PHYS_TR margin − maximin is −0.007, and PHYS_GPC margin − maximin is −0.009.
- **Reading:** acquisition matters for decision quantities (region, label) and hardly at all for the smooth physical outputs.

**2. Same acquisition, simple vs rich model.**
- **Regression:**
  - TRSQ − M0: +0.083 and −21.0 under MAXIMIN (primary); +0.078 and −15.0 under MOIVR (4/4).
  - OLD SHQ − M0 under MOIVR: +0.015 and −3.0.
- **Region:** SHQ − M0 is +0.033 under STRADDLE (4/4, −13) and +0.014 under MAXIMIN (4/4, −9).
- **Label:** TR_E1 − ACTIVE_E1 under straddle is +0.007 / −0.021 / −0.009 / −0.029 BA-AULC per repeat, so no gain. PHYS_TR (no NEW simulation) vs E1 + straddle: 0.707 vs 0.719 BA-AULC.

**3. Same global schedule, local reaction on vs off** (Astra's ask/tell selector, region).
- BA-AULC −0.004 (M0) and −0.006 (SHQ) in OLD; −0.004 and −0.001 in NEW. No gain.
- This agrees with her synthetic pilot: the surprise trigger needs a first hit that a level-set-focused global schedule does not produce.

**4. Collecting samples vs learning.**
- **STRADDLE** pays 40–42 % of its runs inside the boundary band (MAXIMIN 19 %) and learns faster.
- **TRUVAR** collects almost as much (35–39 %) but learns less than STRADDLE under SHQ (−0.018, 0/4).
- **RANDOM** collects 21 % and learns worst.
- **A2's GAP0** pays 88 % of its first 8 runs where transfer is least certain (ST > 400 K), yet learns worst (R²-AULC 0.685 vs 0.788).
- **Conclusion:** collection is not learning. The interactive view shows both side by side for any model, acquisition and budget.

### 4.4 Accuracy levels, never-reached cases, calibration, false confidence (MAXIMIN; exploratory)

**Levels** (mean NEW simulations to the level; share of target × repeat cases never reached by B60 in parentheses):

| Population | Level factor | M0 | M0Q | SHQ | TRQ | TRSQ |
|---|---|---|---|---|---|---|
| NEW | 0.80 | 17.7 (4 %) | 15.3 | 13.7 | 5.3 | 3.0 |
| NEW | 0.90 | 25.8 (8 %) | 20.8 | 16.2 | 6.2 | 4.8 |
| NEW | 0.95 | 32.0 (12 %) | 29.5 (8 %) | 22.8 | 11.7 | 8.3 |
| OLD | 0.80 / 0.90 / 0.95 | 14.9 / 23.1 (7 %) / 32.1 (14 %) | — | 13.3 / 22.7 (7 %) / 31.0 (14 %) | — | — |

**Calibration:**
- cov90 at B8, NEW: M0 0.69 vs TRSQ 0.84. At B24: 0.78 vs 0.83, with NLPD 3.62 vs 2.79.
- cov90 at B8, OLD: M0 0.71 vs SHQ 0.82.

**False confidence:**

| Population | Model | Trajectories claiming too early (§5b) | Test runs outside the 90 % interval at the claim (§13; nominal 0.10) |
|---|---|---|---|
| NEW | M0 | 0.83 | 0.29 |
| NEW | M0Q | 0.75 | 0.31 |
| NEW | SHQ | 0.54 | 0.19 |
| NEW | TRSQ | 0.17 | 0.17 |
| OLD | M0 | 0.75 | 0.26 |
| OLD | SHQ | 0.54 | 0.13 |

- Every model is overconfident when it first claims the level.
- The rich models are less overconfident: NEW TRSQ claims at 4.2 simulations and really gets there at 4.8, while M0 claims at 10.3 and gets there at 25.8.

### 4.5 Region learning: {velocity spike log-ratio ≥ log 2} (exploratory)

**OLD (the informative population):**

| Model | MAXIMIN | RANDOM | STRADDLE | TRUVAR | ASTRA straddle_global | ASTRA surprise |
|---|---|---|---|---|---|---|
| M0: BA-AULC (budget) | 0.870 (44 = never) | 0.851 (44) | 0.886 (35) | 0.894 (37) | 0.882 (39) | 0.878 (37) |
| SHQ: BA-AULC (budget) | 0.884 (35) | 0.865 (44) | **0.919 (22)** | 0.902 (25) | 0.915 (23) | 0.909 (25) |

- **NEW is at ceiling** (BA 0.95–0.99). STRADDLE − MAXIMIN under TRSQ is +0.026 (4/4), saving about 1 simulation.
- **Interactive view:** `report/boundary_view.html` (also a private claude.ai page: https://claude.ai/artifact/3gpsHhmiSnowJLeCrohFKB). It shows OLD repeat 5, with model / acquisition / budget / fold controls, the predicted side, wrong predictions and the paid runs. Its balanced accuracies equal the frozen evaluator's (12 arms × 5 budgets, largest difference 1.1e-16).

### 4.6 Keyhole label (NEW; exploratory; label and short-K definitions unchanged)

| Arm | B0 | B8 | B16 | B24 | B40 | BA-AULC B8–B40 | Specificity B40 | Log loss B40 | AUC B40 | Short-K B40 |
|---|---|---|---|---|---|---|---|---|---|---|
| G3_MARGIN | — | 0.615 | 0.636 | 0.693 | 0.687 | 0.670 | 0.417 | 0.339 | 0.794 | 6.2/10 |
| ACTIVE_E1_STRADDLE | — | 0.639 | 0.691 | 0.725 | **0.737** | **0.719** | 0.500 | 0.568 | 0.918 | 7.8/10 |
| TR_E1_STRADDLE | — | 0.659 | 0.713 | 0.705 | 0.707 | 0.706 | 0.438 | 0.517 | 0.922 | 8.0/10 |
| PHYS_TR_MAXIMIN (A3) | **0.692** | 0.720 | 0.693 | 0.694 | 0.706 | 0.707 | 0.438 | **0.187** | 0.906 | 7.8/10 |
| PHYS_GPC_MAXIMIN (A4) | 0.692 | 0.704 | 0.686 | 0.718 | 0.714 | 0.709 | 0.458 | **0.178** | 0.906 | 7.2/10 |
| PHYS_GPC_MARGIN (A4) | — | 0.704 | 0.709 | 0.701 | 0.701 | 0.699 | 0.438 | 0.172 | 0.905 | 6.5/10 |

- **Columns:** BA at p ≥ 0.5, mean of repeats 5–8.
- **Sensitivity** is 0.96–0.98 for every arm.
- **q20 at B40:** E1 straddle 0.80, PHYS_TR 0.78, G3 0.71.
- **BA-AULC per repeat:**
  - PHYS_TR: 0.704 / 0.709 / 0.711 / 0.704;
  - E1 + straddle: 0.698 / 0.761 / 0.698 / 0.719.
- **A4 fits:** 67 of 1,460 GPC fits failed, mostly at B1–B8, and fell back to the prior.
- **Figure:** `report/label_curves.png`.

### 4.7 Time structure (D2; exploratory)

**(a) Phase-feature learning curves (MAXIMIN).**
- **Transfer to B0 (NEW, OLD feature emulators as prior mean):** the KE early peak (R² 0.96 at B0), KE plateau (0.68) and temperature plateau (0.84) reach the level with **zero NEW simulations**. M0 needs 14, 29 and 23.
- **t90:** 7 simulations instead of 34 for KE and 14 for temperature.
- **Negative transfer:** the temperature early peak (R² −19 at B0, never reaches the level) and onset t_on (12 vs 4).
- **No meaningful level** for features with R²_full(M0) ≤ 0.12: KE early-peak time and fluctuation; temperature peak, peak time, overshoot and fluctuation.
- **OLD (SHQ):** close to M0.

**(b) Early-horizon curve models (0–0.25 ms), with the two pre-registered rules (`RESULTS_TABLE.md` §12).**
- **PHASE BEATS KRONn** only for OLD temperature: PHASE_PCA RMSE 138–140 K vs KRONn 157 K, 4/4 repeats. It is not met for NEW, nor for KE, where KRONn's NEW curve R² is 0.96–0.985.
- **TEMPORAL BEATS SCALAR** is met in 49 of 144 curve-model cells. In 42 of them the x-independent MEAN curve meets it too, so they show a weak scalar GP rather than a learned time structure.
  - The 7 remaining cells are all whole-pool. They are the OLD temperature early-peak amplitude (PHASE_PCA 109–111 K vs scalar 144–150 K) and NEW KE under TRSQ (amplitude 0.064 vs 0.072 log nJ; peak time 5.6 vs 6.2 µs, at the 5-µs block resolution).
  - **None is met at B16 or B40.**
- **Reading:** time structure is learnable as level features, and these transfer across campaigns. Curve models add nothing over scalar GPs at realistic budgets. The temperature early peak is not predictable in NEW.

### 4.8 Robustness and transfer-gap design (A1, A2)

- **A1, DEV repeats 3–4:** TRSQ vs M0 saves **22.3** simulations (per repeat 30.0 / 14.7; per target 12–40, all > 0). R²-AULC NEW 0.746 → 0.819; OLD M0 0.886 → SHQ 0.890.
- **A2, the first NEW simulations to buy once transfer exists** (TRSQ, R²-AULC B0–B24):

  | Design | R²-AULC B0–B24 | Simulations to 0.95 × R²_full |
  |---|---|---|
  | MOIVR0 | 0.792 | 6.7 |
  | MAXIMIN0 | 0.788 | 7.2 |
  | RANDOM0 | 0.775 | 10.7 |
  | **GAP0** | **0.685** | 15.2 |

  GAP0 is lowest in 4/4 repeats.

### 4.9 Costs

| Item | Amount |
|---|---|
| Wall clock | T0 08:41:20 to the last runner fit 13:39:51: about **5.0 h of the 48 h** budget. Report-time M0 reference fits ran until about 13:52. About 42.6 h remain, kept in reserve. |
| Recorded modelling CPU | **4.15 h**: data extraction 0.12, fix A1 0.01, DEV 0.85, final programme 1.50, addenda A1–A4 0.39, D2 1.29 |
| Per 60-query regression trajectory | M0 about 6 s, TRSQ about 13–15 s, OLD SHQ about 19–20 s; TRSQ's extra CPU is about 7 s per trajectory |
| Per 40-query region trajectory | M0 about 0.4 s, TRSQ/SHQ about 7–9 s |
| Simulations | **0 new SPH runs.** Each "paid" simulation is a retrospective query of an existing run, counted once for all its outputs. |
| Output reading | 0.84 s per simulation, all channels |
| OLD emulator | one-off 5 s, on historical runs |
| Threads | Opus ≤ 2 (runner + interactive). Astra's 2 reserved threads were not used by Opus. Capacity slips CAP1 and CAP2: seconds-long, no fits. |

## 5. Thesis contribution sentence

> On previously inspected SPH laser-melting simulations (DEV evidence), most of the sample efficiency of active learning for physical monitor outputs came from the surrogate model, not the acquisition rule. A Gaussian-process emulator that uses an earlier 405-run campaign as its prior mean, shares lengthscales across the eight outputs of each simulation and down-weights truncated records reached the out-of-fold accuracy of the standard per-output GP with on average 21 fewer new simulations per output. It needed none for 5 of 6 outputs and saved 22 in two further repeats. It was also better calibrated and less often falsely confident. Adaptive acquisition, by contrast, changed accuracy by at most ±0.015 R²-AULC. For a physically defined region (the velocity-spike level set), the shared-kernel model and straddle acquisition contributed comparably: each added about +0.03 balanced-accuracy AULC, and together they needed about 22 instead of ≥ 44 simulations.

**Short form:** "Sample efficiency for the physical outputs came from the model, not the acquisition: cross-campaign transfer, output-shared lengthscales and QA-aware noise saved 21 of about 26 new simulations per output (DEV)."

**What the thesis cannot claim from this campaign:**
- independent or Stage-A evidence;
- generalisation to campaigns far from the predecessor;
- a better Keyhole classifier: PHYS_TR is "comparable BA with zero new simulations, best calibrated", not better;
- a gain from curve models over scalar GPs.

## 6. Limits and disclosures

1. **DEV only.** All 541 runs were inspected before. Repeats 5–8 are new partitions of the same runs, not independent data. C4 and Stage A were not used.
2. **Development results were seen before the freeze.** RICH = TRSQ / SHQ and the Q rule were chosen on repeats 1–2, and the primary bar was set knowing the development effect. The primary is a replication on new partitions. Repeats 3–4 (A1) had been used by earlier studies for other questions.
3. **The level is relative to M0's attainable accuracy** (0.9 × R²_full(M0)). In NEW, truncated records lower M0's ceiling (e.g. log KE). Part of the saving, 5.0 of 21.0, is that QA effect, and it is reported separately. The direction holds at 0.8 and 0.95 (§4.4).
4. **Transfer needs a predecessor campaign.**
   - The OLD runs are a sunk cost and predate NEW.
   - OLD and NEW come from different source revisions of the same simulator (b6dc254a vs 2e1eec9c).
   - NEW lies in OLD's high-power corner. Its 63 runs with ST > 400 K are outside OLD's range, and their B0 transfer error is 15–40 % larger.
   - Gains would shrink for a campaign far from its predecessor. Without one, the exploratory saving is about 10 of 26.
5. **"Zero NEW simulations"** means the level is held at B0 and B4 under the frozen rule. Spike duration still needs 28–32.
6. **Region.** NEW is at ceiling and uninformative. The threshold log 2 was fixed before development and not tuned.
7. **Label (exploratory).**
   - The short-K subgroup was monitored only and never given to a selector.
   - The NEW fast-scan corner is unresolved.
   - In A4, 67 of 1,460 GPC fits failed and the prior was used at those budgets.
   - PHYS_TR uses OLD labels: a cross-campaign source, disclosed as such.
8. **D2.** Rule 2 names no curve model or budget, so all of them are reported. The MEAN-curve diagnostic was added at reporting time and is labelled as such. KE peak-time differences sit at the 5-µs block resolution.
9. **False confidence has two definitions.**
   - §5b, trajectory level: the report code committed before any final result (3cdfc91a).
   - §13, the protocol's wording (test runs outside the 90 % interval at the claim budget): added at reporting time after the mismatch was noticed.

   Both are reported and agree in direction.
10. **Erratum RC18-FINAL-P-ERRATUM.** A summary line in RC18-FINAL-P was averaged over all targets but labelled "primary". The verdict is unaffected.
11. **Report repairs** (figure layout, a markdown helper, viewer rendering) are formatting only; no number changed.
12. **Exploratory contrasts** carry no multiple-comparison correction. All 4 per-repeat values are shown in `RESULTS_TABLE.md`.
13. **Predicted auxiliary outputs** are functions of x and were never counted as new measurements.
14. **The interactive view** shows one OLD repeat (5). Its numbers were checked equal to the evaluator.

## 7. Reproduction and outputs

- **Runner restart** (idempotent; skips finished units; a lock prevents a second runner):

  `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_start_runner.ps1`

  The jobs are listed in `runner/PLAN.json`.
- **Final programme:** `python -m src.rc18_final <job> --threads 1`. Each worker refuses to start if a frozen code or data hash changed.
- **Report:**
  - `python -m src.rc18_report all` writes §1–6;
  - `python -m src.rc18_report2 all` appends A1–A3 and D2;
  - `python -m src.rc18_report3 all`, `d2rules` and `fcp` append §11–13;
  - `python -m src.rc18_viewer` builds the view.
  - Each appending mode is run once.
- **Figures** (`report/`):
  - `budget_to_target_NEW.png`;
  - `learning_curves_NEW.png` and `learning_curves_OLD.png`;
  - `transfer_scatter_NEW.png`;
  - `region_curves.png`;
  - `label_curves.png`.
- **Tables** (`report/`):
  - `RESULTS_TABLE.md`;
  - `regression_endpoints.csv`, `regression_contrasts.csv`, `levels_budget.csv`;
  - `false_confidence.csv`, `false_confidence_protocol.csv`;
  - `region_endpoints.csv`, `region_contrasts.csv`;
  - `label_endpoints.csv`, `A1_r34_endpoints.csv`, `A2_transfer_design.csv`, `A3_label_endpoints.csv`, `A4_label_endpoints.csv`, `A4_gpc_status.csv`;
  - `D2_feature_curves.csv`, `D2_curve_models.csv`, `D2_rule2_summary.csv`, `D2_rule2_per_repeat.csv`;
  - `COSTS.csv`, `PRIMARY.json`.
- **Interactive view:** `report/boundary_view.html`. A private claude.ai copy exists (link in §4.5); it is not shared with anyone.
