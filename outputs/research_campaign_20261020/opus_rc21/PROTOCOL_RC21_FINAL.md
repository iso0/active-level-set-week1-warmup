# RC21 sequential stage — frozen protocol (written before any sequential RC21 outcome)

Frozen 2026-10-20 (ledger row RC21-FREEZE) before any sequential RC21 trajectory on repeats 27–34; the manifest
`final/RC21_FINAL_MANIFEST.json` hashes this file and every code file the stage uses. Structure as registered in
PROTOCOL_RC21_STAGE1.md §5 (18:40 UTC, before any outcome); amendment A1 (AMENDMENT_A1.md, after Stage 1) is the only change.

## 1. Candidate

NEW = `src.rc21_decisions.NEW` = **PHR_NR** (physical summaries + exact log-h trend, learned regularisation by marginal-likelihood
averaging over τ_F, τ_h; no residual; integrated Laplace predictive). The pre-registered residual rule chose PHR_NR; the
justification gate returned "not carried" because of a material LL harm (+0.016) next to a material BA gain (+0.010, 8/8);
amendment A1 overrides the LL part of the gate (AMENDMENT_A1.md). Expected and declared: LL / Brier harm in the secondary
contrasts. PHR_NRMAP (plug-in version of the same posterior) is recorded as an exploratory by-product only.

## 2. Design

* Pool: the 541 eligible simulations, ONE pool; OLD/NEW never read by a learner. Tasks: fresh DEV repeats 27–34 (seeded 5-fold
  splits [1919, r]; never run before), 5 folds each → 40 paired trajectories per arm.
* Every arm: the same 8-point label-free maximin startup (paid, counted), then one paid query per step to B60; every budget
  8–60 recorded on the held-out fold (evaluator only). One simulation reveals all its outputs at one query cost; missing or
  truncated channels keep their cost.
* Arms: NEW_MARGIN, H_MARGIN (SHQ_ATS_H + margin; RC20 CAND_MARGIN computation, validated identical), X_MARGIN (SHQ_ATS_X +
  margin), ATSAPPROX_MARGIN, E1S (E1RAW and E1CAL on E1's straddle path), G3_MARGIN (RC19B code unchanged, K = 10).
* The physical arms record every RC21 construction on their own paid prefix at every budget (one shared upstream fit);
  only the arm's own construction chooses the next query.

## 3. Pre-declared evaluation (constants in `src/rc21_final.py`; report `src/rc21_report.py`)

Windows: small = B8–B24, all = B8–B60 (every budget). Verdict per contrast: BETTER iff the mean paired difference is beyond
the margin in the good direction AND the good direction holds in ≥ 7/8 repeats; WORSE symmetric; otherwise NOT DIFFERENT.
* Co-primary Q1 (decision accuracy): NEW_MARGIN − H_MARGIN, BA-AULC small, higher, margin 0.020.
* Co-primary Q2 (paid queries): total paid simulations (startup included) to a confirmed BA ≥ 0.93 (at b and b + 4); FEWER iff
  mean paired difference ≤ −2, fewer in ≥ 6/8 repeats, no extra censoring (censored scored 64, a restricted lower bound).
* Answer to the main question = YES iff Q1 BETTER or Q2 FEWER; otherwise NO. Two co-primaries: the YES rule is an OR of two
  sign-consistency rules and is stated as such (no multiplicity correction claimed).
* Secondary: BA-AULC all (0.020); sensitivity / specificity AULC small and all (descriptive, same rule); LL-AULC small (0.010)
  and all (0.005); Brier all (0.005); spend to LL ≤ 0.20 (same rule); X_MARGIN − H_MARGIN (BA small / all 0.020, LL small
  0.010, LL all 0.005, both spend targets); NEW − ATSAPPROX (LL small 0.010, BA small 0.020, spend); NEW − E1CAL (LL all 0.020),
  NEW − E1RAW (BA all 0.020), NEW − G3 (LL all 0.020), spend vs each.
* Diagnostics: both recalls, q20 BA, NEW-batch conduction recall and the fast-scan-corner error counts, short-Keyhole capture,
  calibration slope / ECE, PHR posterior diagnostics, matched-path decomposition on the physical arms' own paths, decision CPU.
* Wording: a probability-only gain (LL / Brier) is never described as a decision gain; offline test BA is not a stopping rule.

## 4. Execution

Smoke: job d-smoke (repeat 1, folds 1–2, every arm; DEV repeat already used in RC19) must finish without failure and the
report/export acceptance must PASS before d-final is enabled. d-final checks the manifest before any unit. Queue: src/rc21_runner.ps1,
≤ 2 single-thread workers, Astra's share untouched, deadline 2026-10-21 11:52:22 UTC (RC20 window). Failures are kept in
`d-final/failed/`; any amendment is logged in the attempt ledger before use.
