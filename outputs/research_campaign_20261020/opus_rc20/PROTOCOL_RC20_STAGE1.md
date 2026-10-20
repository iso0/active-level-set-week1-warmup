# RC20 Stage 1 — matched-path attribution, log-h variants and the honest cross-fit remedy (registered before any RC20 outcome)

**Owner instruction:** 2026-10-20, a NEW bounded research programme (Priorities 1–3 plus documentary repairs).

**Clock and resources:**
- Start 2026-10-20 11:52:22 UTC; hard cap 24 h, 2026-10-21 11:52:22 UTC. The completed 48-hour campaign is not reset.
- Opus uses 2 compute threads. Astra holds a separate, fresh 2-thread reservation (`astra_representation_planning_20261020`, until 2026-10-21 11:58:58 UTC), which is never used.
- Combined numerical work ≤ 4 threads. Every Opus leaf process runs with OMP / OPENBLAS / MKL_NUM_THREADS = 1.

**Starting state verified:**
- Repository iso0/active-level-set-week1-warmup, branch `joint-depth-label-dev` at c2f720c6 (local = origin; nothing newer).
- The RC19/RC19B reports, protocols, definitions, exports, code and ledger rows were re-read. RC19/RC19B outputs stay unchanged; this programme writes only to `outputs/research_campaign_20261020/opus_rc20/` and `src/rc20_*`.

**Evidence label: DEV.** Every partition of the 541 inspected simulations is development evidence, not physical validation.

## 0. Contract (unchanged)

- One 541-run pool; OLD/NEW is provenance only.
- Public-feature-only matched starts (8 label-free maximin points); every paid simulation is counted.
- A query reveals all available outputs of that run at one cost. Missing or truncated channels keep their cost.
- Learners, preprocessing, calibration and acquisition use public inputs and paid outcomes only; test outcomes are evaluator-only.
- Labels, exclusions, q20, short-Keyhole and the fast-scan corner are unchanged. The last two are diagnostics only.

## 1. Numerical acceptance (done before this registration was finalised; `RC20_VALIDATION.json` PASS, 2026-10-20 12:05 UTC)

- **Reproduction:** recomputing SHQ_ATS and M0Q_A on cached RC19B final paid prefixes equals the cached ATSCF and DEPTHCF (max |Δ| 3.0e-8, float32 storage).
- **Honesty:** for M0Q, SHQ, SHQT and SHQM, changing a paid run's own outcomes never changes its own out-of-fold feature or its own fold model (0.0); other folds change (3/3).
- **Shadow:** randomising every never-paid outcome leaves all 13 constructions identical (max |Δ| 0.0).
- **log h:** equals `week18_engine.logh` after the public pool standardisation (|Δ| 0.0).
  - LS is the Gaussian spot radius in metres (40–90 µm; claims C20); h = P / sqrt(VX · LS³) in W s^½ m⁻².
  - h is a public scaling proxy, not a measured enthalpy or an observed channel.
- **The h-trend GP** (`src/rc20_gp.py validate`) PASS:
  - analytic gradient error 2.7e-9;
  - a real trend is recovered;
  - with no h-signal the strength shrinks to its 1e-8 bound and predictions equal the plain GP (|Δ| 9e-8).

## 2. Constructions (all honest unless named APPROX; definitions in `src/rc20_attr.py`)

**Upstream emulators**, each predicting A, T, S from the standardised log inputs:
- **M0Q:** independent per-output GPs.
- **SHQ:** lengthscales shared by A, T, S, plus record quality (the ATSCF upstream).
- **SHQT:** SHQ plus a per-output Gaussian-prior linear basis in standardised log h. The strength b² is learned by ML-II inside each training subset and can shrink to 1e-8. The coefficient is integrated out, so trend uncertainty is propagated, not plugged in. The Matérn part keeps all four inputs, ST included.
- **SHQM:** SHQ with MAP lengthscales, prior log ℓ ~ N(0, 1²).

**Cross-fitting:** K = min(10, n) folds by paid order (fold = j mod K). Each fold's hyperparameters, shared lengthscales, trend strength, normalisation and Q weights use only the paid runs outside the fold.

**Classifier:** g = L2 logistic (C = 1) on standardised out-of-fold features, deployed on the full-paid fit's means. The same g is used for every feature set.

**Constructions:**

| name | upstream | classifier features | role |
|---|---|---|---|
| M0Q_A | M0Q | A | = DEPTHCF (K = 10) |
| M0Q_ATS | M0Q | A, T, S | factorial cell |
| SHQ_A | SHQ (fitted on A, T, S) | A | factorial cell; the decisive control |
| SHQ_ATS | SHQ | A, T, S | = ATSCF (K = 10) |
| SHQ_A_H, SHQ_ATS_H | SHQ | + exact log h~ in the same g | variant 1: a shrinkable classifier h term |
| SHQT_A, SHQT_ATS | SHQT | A / ATS | variant 2: h-mean emulators + GP residual |
| HONLY | none | log h~ only | physics-proxy reference |
| SHQ_ATS_FD | SHQ | ATS; deployment averaged over the K fold models | remedy candidate: training construction |
| SHQM_ATS | SHQM | ATS | remedy candidate: regularisation |

**System controls**, read from the RC19B caches on the same paid prefixes: E1RAW, E1CAL, ATSCF, DEPTHCF, ATSAPPROX, G3.

## 3. Data and metrics

- **Matched paths:** the 200 RC19B final trajectories (repeats 11–18 × 5 folds × the 5 arms' own paths). Budgets 8, 12, …, 60 (total paid simulations).
- **Metrics per (construction, path type, repeat):** test runs pooled over the 5 folds; LL-AULC over B8–B60 and over B8–B24 (small budgets), BA-AULC, Brier-AULC, both recalls, AUC, reliability, fast-scan corner counts.
- **Summary contrast:** paired per repeat; the all-path value is the mean of the five path types. Per-path values are reported too.
- **Effect labels** (component attribution, lower LL better):
  - **MATERIAL** if the mean all-path Δ ≤ −0.010 and Δ < 0 in ≥ 7 of 8 repeats;
  - **MATERIAL HARM** if the mean ≥ +0.010 and Δ > 0 in ≥ 7 of 8;
  - **NOT MATERIAL** otherwise.
  - Mean, SE, range and per-path values are always reported.

## 4. Hypotheses and pre-declared contrasts

| ID | question | contrast (LL-AULC B8–B60 unless stated) |
|---|---|---|
| **H1 (decisive)** | do T and S add information beyond depth with IDENTICAL SHQ upstream fits, folds, normalisation, quality treatment and paths? | SHQ_ATS − SHQ_A |
| H1b | the same under M0Q | M0Q_ATS − M0Q_A |
| H2 | does sharing lengthscales (upstream representation) help? | SHQ_A − M0Q_A; SHQ_ATS − M0Q_ATS |
| H3 | E1 probability mapping | E1CAL − E1RAW |
| H4 | depth representation (calibrated) | M0Q_A − E1CAL |
| H5 | honest vs approximation | ATSAPPROX − SHQ_ATS |
| **H6 (h, variant 1)** | shrinkable log h in the classifier | SHQ_ATS_H − SHQ_ATS on **B8–B24** (primary for h) and B8–B60; also SHQ_A_H − SHQ_A |
| **H7 (h, variant 2)** | log-h mean emulators | SHQT_ATS − SHQ_ATS on **B8–B24** and B8–B60; also SHQT_A − SHQ_A |

- The confounded RC19B contrast ATSCF − DEPTHCF = H2(A) + H1 is reported in both decomposition orders (2×2 main effects and interaction).
- No percentage split is claimed unless both orders agree within 0.005.

## 5. Remedy selection (pilot; `c-pilot`, 20 units: repeats 11–12 × 5 folds × the E1S and ATSCF_MARGIN paths; budgets 8–24, 40, 60)

**Mechanism under test** (RC19B development):
- About one third of the honest-vs-approximation deficit is fold size.
- The rest comes from re-estimating hyperparameters per fold. Two candidate mechanisms:
  - (a) unstable small-n ML-II makes the fold features noisier, addressed by regularisation (SHQM);
  - (b) the classifier is trained on fold-model features but deployed on full-fit features, addressed by fold-deployment (FD).

**Rule:**
1. For each remedy R, compute Δ_R = mean over the 20 pilot units and budgets {12, 16, 20, 24} of the per-unit test log loss of (R − SHQ_ATS).
2. The remedy with the more negative Δ_R is carried into the main replay (`src/rc20_decisions.REMEDY`).
3. If neither Δ_R ≤ −0.005, no remedy is carried.
4. Ties within 0.002 go to FD (cheaper).
5. The pilot diagnostics (fold log-lengthscale spread; RMS of honest-vs-approximation and honest-vs-in-sample features; classifier coefficient norms) are reported to explain the choice. They do not override the rule.
6. The pilot decides only this.

## 6. Candidate rule for a later sequential stage (Priority 3; declared now)

**Candidates:** honest constructions only — SHQ_ATS_H, SHQT_ATS, the carried remedy applied to SHQ_ATS, and, if the remedy is FD, also SHQ_ATS_H_FD and SHQT_ATS_FD.

**Selection:**
- c* = the candidate with the lowest all-path LL-AULC over B8–B24.
- Subject to: LL-AULC B8–B60 ≤ SHQ_ATS + 0.005, and BA-AULC B8–B60 ≥ SHQ_ATS − 0.005.

**Justification gate:** a sequential stage is justified only if c* improves on SHQ_ATS at B8–B24 by ≥ 0.010 (mean) with Δ < 0 in ≥ 6 of 8 repeats.
- **If yes:** a separate sequential comparison is frozen before it runs: c* + margin, c* + η-straddle (same posterior), ATSCF + margin (unchanged), ATSAPPROX + margin, E1 + straddle (E1RAW/E1CAL) and G3 + margin, on fresh repeats with matched starts.
- **If no:** no sequential stage runs and the null is reported.

## 7. What Stage 1 cannot claim

- No paid-query saving: replays fix the paths.
- No physical validation.
- Exploratory contrasts carry no multiplicity correction; the effect labels above are descriptive gates.
