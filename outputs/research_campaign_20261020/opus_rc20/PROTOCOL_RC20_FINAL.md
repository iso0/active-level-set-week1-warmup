# RC20 sequential stage — frozen before any of its outcomes (Priority 3: does the model gain become learning efficiency?)

**Status:** FROZEN by `final/RC20_FINAL_MANIFEST.json`. It hashes the learner, the sequential code, the decisions, the evaluator, the report/export code, the data manifest and this protocol. Every `c-final` worker verifies the hashes before claiming a unit (`src/rc20_jobs.work` → `src/rc20_final.check`). Commit before any final unit runs (local commit only).

**Evidence label: DEV** (new partitions of the 541 inspected simulations; not physical validation).

**Clock:** inside the RC20 cap (2026-10-21 11:52:22 UTC). Opus 2 threads; Astra's separate 2-thread reservation untouched.

## 1. Why this stage runs (decided by the Stage 1 rules, `PROTOCOL_RC20_STAGE1.md` section 6)

- **Candidate c* = SHQ_ATS_H.** It is the honest SHQ cross-fitted physical-response classifier (A, T, S out-of-fold features), with the exact public coordinate log h~ added to the SAME L2 logistic classifier (C = 1, standardised, shrinkable coefficient).
- On the 200 matched RC19B paths it lowered LL-AULC B8–B24 by −0.0356 vs ATSCF (8/8) and B8–B60 by −0.0197 (8/8); BA B8–B60 +0.008. The justification gate passed.
- The remedy branch was null (pilot), so no remedy is used.
- The log-h emulator mean (SHQT) was not material and is not run.

## 2. Design

- **Repeats:** fresh DEV repeats 19–26, never run before; seeded random 5-fold partition per repeat (seed [1919, r], the RC19 rule).
- **Matched starts:** the same 8 label-free maximin points.
- **Budgets:** 8 → 60 total paid simulations (startup included), every budget recorded.
- **One-class rule:** as in RC19.
- **Arms** (6 × 40 = 240 trajectories):

| arm | probability | selector | role |
|---|---|---|---|
| CAND_MARGIN | SHQ_ATS_H | margin \|p − 0.5\| on the candidates | model change under the SAME selector as ATSCF |
| CAND_ETASTRADDLE | SHQ_ATS_H | eta-straddle 1.96 sd(eta) − \|eta\| | selector change under the SAME posterior |
| ATSCF_MARGIN | ATSCF (K = 10), unchanged RC19B code | margin | strong control |
| ATSAPPROX_MARGIN | RC19 approximation, unchanged | margin | strong control (best empirical scorer) |
| E1S → E1RAW+straddle, E1CAL+straddle | E1 / E1 + honest map (K = 10), unchanged | E1 straddle | system controls |
| G3_MARGIN | Week 18 G3, unchanged | margin | system control |

**eta-straddle:**
- eta(x) is the candidate classifier's linear predictor at the full-paid upstream means.
- Var eta(x) = Σ_t (w_t / s_t)² v_t(x), with v_t the upstream GP latent variances; no observation noise.
- The outputs are independent given the hyperparameters (SHQ shares lengthscales only; there is no joint-output covariance model), and the classifier weights are a plug-in.
- Validated against a Monte-Carlo estimate before the freeze (`RC20_VALIDATION_FINAL.json`).
- Straddle needs only marginal variances. No SUR selector is used: it would require validated cross-covariances of a joint label-plus-output model, which is not available here.

**Separation of effects:**
- **Model improvement under the same selector:** CAND_MARGIN − ATSCF_MARGIN.
- **Selector improvement under the same compatible posterior:** CAND_ETASTRADDLE − CAND_MARGIN.
- **No change of loss or reference distribution:** every arm is scored on the same held-out test fold with the same metrics (test log loss; BA at p = 0.5 with both recalls; Brier; AUC) at the same total paid budgets. eta-straddle targets the p = 0.5 boundary that BA scores.

## 3. Pre-declared contrasts (`src/rc20_final.PRIMARY` / `SECONDARY`)

**Verdict rule:** paired by repeat (8). BETTER iff the mean difference is beyond the margin in the good direction AND in the good direction in ≥ 7 of 8 repeats; WORSE symmetrically; else NOT DIFFERENT. AULC = mean over every recorded budget in the window.

- **PRIMARY:** CAND_MARGIN − ATSCF_MARGIN, **LL-AULC over B8–B24**, lower is better, margin **0.010**.
- **Secondary:**
  - CAND_MARGIN − ATSCF_MARGIN: LL B8–B60 (0.005); BA B8–B60 and B8–B24 (0.020); Brier B8–B60 (0.005).
  - CAND_ETASTRADDLE − CAND_MARGIN: LL B8–B24 (0.010); BA B8–B60 (0.020).
  - CAND_MARGIN vs ATSAPPROX_MARGIN: LL B8–B24 (0.010) and B8–B60 (0.005).
  - CAND_MARGIN vs E1CAL+straddle: LL B8–B60 (0.020).
  - CAND_MARGIN vs E1RAW+straddle: BA B8–B60 (0.020).
  - CAND_MARGIN vs G3_MARGIN: LL B8–B60 (0.020).

## 4. Paid-query targets (offline held-out benchmarks, not stopping rules)

**Targets:**
- **BA ≥ 0.93:** the RC19/RC19B label level, kept for continuity.
- **Test log loss ≤ 0.20:** declared prospectively. In RC19B the honest arms crossed 0.20 between about B16 and B40, so the level separates learning speed between the arms. It was chosen before any RC20 sequential outcome.

**Confirmation:** the level is met at b and at the second checkpoint b + 4. Spend = b + 4 total paid simulations. Censored = no confirmed pair by B60.

**Paired spend rule:** FEWER SIMULATIONS iff the restricted mean paired difference (censored scored 64, a lower bound) is ≤ −2 simulations, fewer in ≥ 6 of 8 repeats, and no more censoring than the reference. Observed differences (both confirmed) and censoring are reported separately.

**Pairs:**
- CAND_MARGIN − ATSCF_MARGIN
- CAND_ETASTRADDLE − CAND_MARGIN
- CAND_MARGIN − ATSAPPROX_MARGIN
- CAND_MARGIN − E1RAW+straddle
- CAND_MARGIN − E1CAL+straddle
- CAND_MARGIN − G3_MARGIN

A simulation reveals all its outputs at one cost, so savings are never multiplied by outputs.

## 5. Also reported (no verdict)

- learning curves (log loss, BA, recalls, Brier, AUC); matched-budget tables;
- reliability (slope, intercept, ECE);
- fast-scan corner counts; q20; short-K;
- GP/decision CPU per step and per trajectory, separate from the paid-simulation count;
- per-budget predictions (float32) and every paid path with an acceptance check.
- **Exploratory by-products on the candidate's own paths every 4 budgets**, from the SAME upstream fit:
  - SHQ_ATS (no h), SHQ_A, SHQ_A_H, HONLY;
  - SHQ_ATS_X: a generic control in which the 4 exact log inputs replace log h in the same classifier, to test whether the gain is h-specific.

## 6. Acceptance before the freeze

- `RC20_VALIDATION_FINAL.json` must PASS:
  - shadow test of both candidate arms;
  - eta-variance Monte-Carlo check;
  - sequential step = Stage 1 construction.
- Smoke test on seen DEV repeat 1 (12 units) with the frozen report and export run end to end.

## 7. Not claimed

- No physical validation.
- No deployable stopping rule.
- No multiplication of savings across outputs.
- No claim beyond DEV.
