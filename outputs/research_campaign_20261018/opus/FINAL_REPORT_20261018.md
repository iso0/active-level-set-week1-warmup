# Research campaign 20261018 — physical modelling and sample efficiency (Opus)

**Evidence label: DEV.** All numbers come from previously inspected SPH simulations: NEW (136) and OLD (405), evaluated separately.
- Final repeats 5–8 are new partitions of the same data, not new data.
- C3's decision stands; C4, real-data Stage A, the simulator, paid cloud, main merges and outbound messages were not used.

**Records:**
- Protocol: `PROTOCOL_20261018.md` (frozen in commit eaba0c8d before any final run).
- Addenda: A1 (robustness), A2 (transfer-gap acquisition).
- D2 protocol: `temporal/TEMPORAL_PHASE_PROTOCOL.md`.
- Attempts: `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md`, rows RC18-*.
- Single results table: `report/RESULTS_TABLE.md`.

## 1. Main answer

*(filled from the final tables; see §4)*

## 2. What was actually run

| Step | What | Where |
|---|---|---|
| Coordination | Single machine record `pool/POOL_PLAN.json`. Opus has 2 threads; Astra has 2, reserved at 08:46:11 UTC before any heavy Opus work. | `COORDINATION.md` |
| Runner | `src/rc18_runner.ps1` plus a supervisor launched detached via WMI. Units are checkpointed and finished units skipped; the deadline is enforced; failures pause only the failing job; heartbeat every 30 s. | `runner/` |
| Astra's pilot | Her frozen 17-Oct package, run once from a hash-identical copy: COMPLETE, 578 fits, 10.6 s. | `../astra_pilot/` |
| Fix A1 | Variance contract: a hand-solvable GP check, an exact 20/20 replay, and the prospective PHYS_DISCOVERY v1.1. | `fixes/A1_variance_contract/` |
| Fixes A2/A3 | Channel-independent loader; separate QA counters; three summary families; the 40-bin peak loss measured. | `data/` |
| Inspection | Ranges, physics coordinate, regime heteroskedasticity, OLD→NEW transfer, truncated records. | `inspection/` |
| Development | DEV repeats 1–2: about 26,000 GP fits, used to choose the rich model. | `main/dev/` |
| Final programme | DEV repeats 5–8: regression (5 NEW and 2 OLD models × 3 designs), region (2 models × 6 acquisitions), label (5 arms). | `main/final/` |
| D2 | Native-time phase model for temperature and KE. | `temporal/` |
| Addenda | A1 (repeats 3–4) and A2 (transfer-gap design). | `main/robust_r34/`, `main/transfer_design/` |

## 3. Models and acquisitions (definitions)

**Common GP** (src/rc18_gp.py; equal to sklearn's ML-II optimum to 1e-13):

  y = m0(x) + μ + σ·f(z) + ε,   f ~ GP(0, s_f² k₃⁄₂(z, z′; ℓ)),   ε_i ~ N(0, σ² s_n² w_i),

- **Kernel:** k₃⁄₂(r) = (1 + √3 r) e^{−√3 r}, with r² = Σ_d (z_d − z′_d)² / ℓ_d².
- **Inputs:** z are the fold-standardised log inputs (P, VX, LS, ST).
- **Standardisation:** μ and σ are the mean and SD of y − m0 over the paid rows.
- **Fitting:** ML-II by L-BFGS-B with analytic gradients.
- **Predictions:** latent mean μ*(x), latent variance v*(x) and observation variance v*(x) + σ² s_n². The noise is never added twice (fix A1).

**Model family:**
- **M0** (simple; PHYS_AL's GP): m0 = 0, w_i = 1, per-output ML-II.
- **Q** (QA-aware observation model): w_i = 10⁴ if paid run i ended before 0.95 × its planned end time TE, else 1. The truncated run stays paid, keeps its label and is evaluated.
- **SH** (partial sharing across outputs): one ARD lengthscale vector ℓ is shared by all 8 outputs, maximising Σ_k log p(y_k | ℓ, s_f,k², s_n,k²); each output keeps its own variances.
  - Rationale: with isotopic outputs and a common kernel, cokriging equals kriging. A coregionalised model (ICM) therefore adds parameters but no predictive information; better-identified hyperparameters are what remains to gain.
- **TR** (cross-campaign transfer, NEW only): m0(x) = μ_OLD(x), the posterior mean of a GP fitted once on all OLD runs per target. The OLD runs predate NEW and need only x at a NEW run. A residual GP is fitted on the paid NEW rows; below 5 usable rows the model is μ_OLD + mean residual.
- **RICH:** TRSQ = TR + SH + Q for NEW; SHQ for OLD.

**Acquisitions:**

| Name | Rule |
|---|---|
| MAXIMIN | the frozen label-free path |
| RANDOM | seeded random choice |
| MOIVR | argmax_x Σ_t IVR_t(x)/Var(paid y_t), where IVR_t(x) = Σ_{j∈pool} Cov_t(j, x)² / (v_t(x) + noise_t) |
| STRADDLE | argmax 1.96 √v − \|μ − τ\| |
| TRUVAR | argmax total latent-variance reduction over the unclassified set {\|μ − τ\| < 1.96 √v} (Bogunovic et al. 2016, LSE form) |
| ASTRA_SURPRISE / ASTRA_STRADDLE_GLOBAL | Astra's frozen ask/tell selector, with the local reaction on or off under the same global schedule |
| GAP0 (A2) | argmax Σ_t [v_δ,t(x) + v_OLD,t(x)] / Var_t |

## 4. Results

### 4.1 PRIMARY — NEW physical outputs, TRSQ vs M0 under the identical MAXIMIN design

**FEWER SIMULATIONS (DEV)** under the frozen rule.
- **Simulations saved:** mean **21.0** NEW simulations per target to the sustained level 0.9 × R²_full(M0). Per repeat: 13.3 / 32.7 / 19.3 / 18.7, all > 0. Smallest target mean +12.
- **TRSQ reaches the level with 0 NEW simulations** (B0, sustained at B4) for log A, log KE T0, spike log-ratio, laser T0 and max temperature T0, in all 4 repeats. Spike duration needs 28–32, against 24–64 for M0.
- **R²-AULC (B8–B60):** +0.083 (per repeat +0.049 / +0.132 / +0.080 / +0.072).

*(decomposition, OLD, designs, calibration, levels, false confidence, region, label, D2, costs: filled from report/RESULTS_TABLE.md)*

## 5. Thesis contribution sentence

*(filled after all final tables)*

## 6. Limits and disclosures

*(filled; includes: DEV only; the level is defined on M0's attainable accuracy; development results were seen before the freeze; the transfer source is a different source revision of the same simulator family; the robustness repeats 3–4 were used by earlier studies for other questions)*
