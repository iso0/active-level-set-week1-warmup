# Claims matrix: joint depth–label study (branch `joint-depth-label-dev`)

**Evidence labels:**
- **PRED:** held-out predictions under a frozen protocol.
- **OBS:** logs, tables or validation.
- **EXPL:** exploratory, with a manifest committed before the run.
- **POST-HOC:** computed after the results were seen.
- **HYP:** interpretation.

All population results are on previously inspected simulations: DEV repeats 1–8, with the C1–C3 blocks already used. Nothing in this study is a confirmation.

## 1. Supported

| # | Claim | Evidence | Label | Scope and caveats |
|---|---|---|---|---|
| S1 | The port `src/jdl_model.py` reproduces Astra's joint model and passes independent checks | 26/26 Astra checks reproduced; 21 independent checks PASS (`validation/validation_results.json`) | OBS | The Laplace error against exact orthant probabilities on a 6-label case is up to 0.040 (a limitation, L6) |
| S2 | Every Stage M J-family fit converged, and the gradient criterion was met | 240/240 accepted; maximum whitened gradient 9.7e-12 (`stage_m/fit_log.csv`) | OBS | Solver status and gradient acceptance are recorded separately |
| S3 | The learner receives paid outcomes only | Corrupting every unpaid and test label and depth leaves predictions bitwise identical (test); a missing response keeps its label and cost | OBS | Evaluator-only columns, such as the response oracle, are marked NOT DEPLOYABLE |
| S4 | NEW Stage M paths are exactly the Week 19 paths | 10/10 identical (`stage_m/path_verification_NEW_vs_week19.csv`) | OBS | OLD/POOLED paths come from the same routine and seeds |
| S5 | On NEW, paid depth improves ranking and probability quality over the matched binary model | B40 J − Binary_matched: log loss −0.172 [−0.203, −0.130]; AUC +0.074 [+0.020, +0.142]; Brier −0.045 (SM-H3) | PRED | DEV repeats 1–2 |
| S6 | On OLD, paid depth adds balanced accuracy | J − Binary_matched BA: +0.067 [+0.036, +0.100] at B16 and +0.057 [+0.028, +0.089] at B40 (SM-H4) | PRED | Same direction on DEV repeats 5–8: J_trained − Binary_matched at 0.5 = +0.063 [+0.037, +0.091] (POST-HOC) |
| S7 | The threshold posterior is informative but centred near 111 µm | θ posterior SD 0.147–0.207 at B40 against a prior SD of 0.35 (SM-H8); mean −0.15 to +0.10 | PRED/OBS | θ and δ do not carry the label–depth disagreement (see L4) |
| S8 | At about 90 % prevalence, the BA-aligned rule p ≥ π̂ turns J's ranking into balanced accuracy | EX1-P1: NEW B40 +0.335 [+0.241, +0.419], with every repeat between +0.31 and +0.34; P2: specificity +0.81, sensitivity −0.14 | EXPL (registered) | DEV repeats 5–8. Train-only π̂. The control Binary_matched loses −0.067 under the same rule (P3) |
| S9 | J at π̂ beats ACTIVE_E1 at its frozen rule | EX1-P4: +0.196 [+0.074, +0.318] | EXPL (registered) | A comparison of complete systems |
| S10 | A response prior trained on the paid depths reduces depth error and adds label value | EX2-P1: NEW B40 response RMSE −0.091 [−0.113, −0.070]; fast scans 0.236 → 0.117. EX2-P2: BA at π̂ +0.028 [+0.012, +0.047]; log loss −0.048 | EXPL (registered) | DEV repeats 5–8. Log loss is better in all three populations |
| S11 | The PPCA functional model removes the exploding coefficients of the frozen functional model | Maximum \|posterior-mean coefficient\| 9.79 against 26,571 for the frozen ALS, at 30/30 checkpoints | OBS | EM reached its iteration cap at every checkpoint (L9). Trajectory and A accuracy: see §5 |
| S12 | The V2 port `src/jdl_v2_model.py` reproduces Astra's V2 and passes independent checks | `v2_model_comparison/validation/V2_VALIDATION.json`: 17/17 hard checks PASS, using 144 component solves and 16 sampling chains | OBS | 180/180 comparison fits `ok`, no fallback, 284 of 300 component attempts used |
| S13 | On NEW, V2's depth sharing improves probability quality over its binary counterpart | B40 V2_EP_mixture − Binary_V2_EP: log loss −0.040 [−0.065, −0.013]; Brier −0.009 [−0.015, −0.004]; AUC +0.067 [+0.023, +0.125] | PRED | DEV repeats 1–2. It does not improve BA at 0.5 (F6) |
| S14 | With the trained response prior, the V2 mixture concentrates on full sharing | EX3-P1: median NEW B40 mass on ρ = 1 is 0.889 (prediction ≥ 0.8) | EXPL (registered) | DEV repeats 5–8 |
| S15 | The atomic SVGP checkpoint mechanism (for future jobs) resumes bitwise-identically | `checkpoint_mechanism/CHECKPOINT_MECHANISM_VALIDATION_v2.json` PASS on all 5 checks | OBS | Synthetic data. The first validation (T11) failed because of a harness defect (F8); the mechanism was not retrofitted |

## 2. Failed or not established (frozen decisions, preserved)

| # | Claim tested | Result | Status |
|---|---|---|---|
| F1 | Stage M screen: NEW B40 J − Binary_matched BA ≥ +0.01, specificity not lower and log loss not worse | BA +0.006 [−0.052, +0.065] | **SCREEN FAILED.** Under the frozen rule, Stage A is not recommended |
| F2 | SM-H1: NEW B40 BA, J > Binary_matched | +0.006; repeats −0.034 and +0.046 | Direction only; not established |
| F3 | SM-H6: NEW B40 BA, J ≥ J_no_delta | −0.023 [−0.087, +0.042] | Falsified (point estimate) |
| F4 | Week 20 C3 confirmation | NOT CONFIRMED at the frozen bar | Unchanged (a test checks this) |
| F5 | The frozen SVGP stopping rule (relative ELBO ≤ 5e-4 and mean RMS ≤ 5e-3) can be met | No fit converged; per-check minibatch noise is about 1e-2 | The rule is below the noise floor (see §5) |
| F6 | V2 screen (Astra's): NEW B40 BA of V2_EP_mixture − Binary_V2_EP ≥ +0.01, specificity not lower, log loss not worse | BA −0.002 [−0.006, 0.000]; specificity equal; log loss −0.040 | **SCREEN NOT PASSED** (`V2_DECISION.json`, `V2_MODEL_REPORT.md`) |
| F7 | EX3-P2: \|BA(V2_trained) − BA(rho1_trained_EP)\| < 0.01 at NEW B40 | −0.042 [−0.094, 0.000] | Falsified: uncertainty over ρ costs specificity against forced sharing |
| F9 | Decision-audit primary: Astra's finite-batch rule on all 20 V2_EP_mixture checkpoints | 11/20 numerically accepted (frozen ladder up to 2^14) | **PRIMARY_UNAVAILABLE**; no surviving-subset metric reported (see U5) |
| F8 | First validation of the checkpoint mechanism (queue T11) | FAIL on both bitwise checks; cause: gpytorch's initialisation noise comes from the unseeded global RNG | Superseded by v2 PASS (S15); the FAIL file is kept |

## 3. Limitations (what qualifies the supported claims)

| # | Limitation | Evidence | Label |
|---|---|---|---|
| L1 | **The NEW gain at π̂ is a fast-corner split.** J and J_trained reject all 11 fast-scan negatives and miss nearly all 12 fast-scan positives (9.5–9.75 of the 10 short-K positives). The Week 19 cut VX > 0.85 → no Keyhole, which is a reference point and not a learner, reaches NEW BA 0.910; J_trained at π̂ reaches 0.906 | `exploratory/POSTHOC_descriptive/` | POST-HOC |
| L2 | **No model resolves the fast-scan corner.** BA inside the 23 corner runs is 0.45–0.60 for every model and rule; corner depths overlap (positives 79–148 µm, negatives 79–131 µm) | same | POST-HOC |
| L3 | **One persistent NEW false positive** under every model: `P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce`, a slow scan whose recording ended early and which has no A. It caps NEW specificity at 11/12. Its label is preserved | same; `MECHANISM_REPORT.md` | OBS |
| L4 | **θ and δ are unidentified at B16–B40.** The fixed-θ and no-δ ablations perform like J; posterior \|δ\| is 0.04–0.06 against a prior SD of 0.35 | `MECHANISM_REPORT.md` §2 | OBS |
| L5 | **The Laplace approximation carries error on study data.** Against slice sampling, max \|Δp\| is 0.019–0.092, with 0–1 decision changes per fold | `mechanism/laplace_error_NEW_r1_B40_ess.csv` | OBS |
| L6 | **Laplace against exact on a small case:** maximum probability error 0.040, mean 0.016 | `validation/validation_results.json` | OBS |
| L7 | **Low precision on NEW.** There are 12 NEW negatives, so one negative is worth 0.042 BA per repeat. Bootstrap intervals are conditional on the stored fits and splits | — | OBS |
| L8 | **Response-prior fits hit their bounds.** sklearn raised bound warnings in 102 of 120 EX2 fits; the ST lengthscale is at its upper bound in 99 of 120 | `POSTHOC_descriptive/EX2_learned_response_hyperparameters.csv` | OBS |
| L9 | **PPCA EM did not reach its tolerance.** It hit the 3000-iteration cap at all 30 checkpoints | `temporal_repair/functional_ppca_fits.jsonl` | OBS |
| L10 | **The data are not independent.** All DEV repeats and C1–C3 have been inspected, and C4 would re-partition the same 541 simulations. A defined after NEW labels were inspected; the 0.85 cut came from Week 19's inspection of NEW | `C4_STABILITY_DRAFT.md` | OBS |
| L11 | **V2's "uncertain sharing" was not tested where it would matter.** At NEW B40 the mixture puts 0.949 of its mass on ρ = 1, so V2_EP_mixture − rho1_EP = 0.000 BA | `v2_model_comparison/component_masses_and_moments.csv` | OBS |
| L12 | **The temporal SVGP fits are not bitwise reproducible across worker histories.** Their initial natural-parameter noise (sd 1e-3) comes from the unseeded process-global torch RNG | `TEMPORAL_STOPPING_AUDIT.md` §4.6; ledger CKV | OBS |

## 4. Untested or not authorized

| # | Question | Status | What it would take |
|---|---|---|---|
| U1 | Does probability-variance acquisition beat margin with the model held fixed (Stage A)? | Runner validated (`stage_a/stage_a_runner_validation.json`); **not executed** | An owner decision. With J_trained, also a per-step ML-II refit, a margin at π̂, and re-validation |
| U2 | Does the candidate J_trained + π̂ generalise beyond the DEV partitions, and does it beat a train-only VX stump? | Generalisation is untested. The train-only stump was measured on DEV repeats 1–2 in the V2 comparison: VX_stump B40 BA 0.851, against J_trained 0.707 at 0.5 and 0.906 at π̂ (descriptive; no frozen contrast between those two) | A frozen C4 stability check (about 600 fits, under 1 CPU-minute); owner decision |
| U5 | Does Astra's finite-batch BA rule (m = 136) change decisions or BA on the frozen V2 posteriors (the cached-posterior decision audit)? | **Run, but unanswered: PRIMARY_UNAVAILABLE.** The owner-authorized recovery R04–R08 ran the audit. Only 11 of the 20 primary V2_EP_mixture checkpoints passed Astra's frozen QMC acceptance; every stop failed the 0.015 margin-change limit at 2^14. Probability parity was exact. Readouts: `v2_decision_audit/DECISION_AUDIT_REPORT.md` | A prospectively registered numerical amendment (e.g. a 2^16 level, or a margin criterion over the decision inputs) as a new attempt; owner decision |
| U3 | Query savings / sample efficiency | Not claimable from identical feature-only paths | A pre-specified target and a hitting-time design |
| U4 | What separates Keyhole from no Keyhole inside the fast-scan corner? | Untested; depth at 111 µm does not | New simulations inside the corner (simulator time; outside this request) |

## 5. Temporal repair (`TEMPORAL_REPAIR_REPORT.md`)
*Filled in after the 30 M400 and 10 M800 SVGP fits and the evaluation have finished.*
