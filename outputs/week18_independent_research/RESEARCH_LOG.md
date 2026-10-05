# Week 18+ research log (resume point for "continue")

Start: 2026-10-05, main = `bbb79eaf` (Week 17). Deadline context: thesis due 15 Dec; research until ~mid-Nov.

## Status board
| Phase | State | Pointer |
|---|---|---|
| 0 Re-ground / red-team | done | RED_TEAM.md, ERRATA.md, phase0/ |
| 1 Data foundation | done (NEW continuous outputs pending D1) | DATA_AUDIT.md (+ amendment) |
| 2 Benchmark redesign | done (S2 binary stress baselines not run) | BENCHMARK_SPEC.md, PHASE2_BASELINES.md |
| 3 Research loop | done: E1 kept; E2 retired; E3, C1, F1, A1, B1, D1, A2 killed | ATTEMPT_LEDGER.md, phase3/ |
| 4 Theory | T18-1…T18-5 + Astra Round 3 integrated | THEORY_WEEK18.md, phase4/ |
| 5 Confirmation | 1 round used (C1): E1 PASSED | FREEZE_ROUND_1.md, round_1/ |
| 6 Stress | E1 survived (depth stress, round-1 seeds) | round_1/ROUND_1_RESULTS.md |
| Stop | stopping rule met (candidate passed + survived) | REPORT.md — verdict IMPROVEMENT ON SOME TASKS ONLY |

## Open decisions for the owner
- D1. NEW continuous targets (depth/width) need the NEW monitors from Hugging Face `ioandanielc/sph_v2`
  (download = permission required). Not downloaded. OLD continuous targets are in the repository.

## Log
- 2026-10-05 Phase 0: sim_id fields parsed. OLD-405 mixes simulator settings: 41 runs TE = 0.00125 s
  (vs 0.0021), 27 runs with a different domain (XI −0.0002 / XF 0.0012 / XL 0.0014); time-step rule
  DT·VX/LS ≈ 0.075 (0.04–0.12) in OLD vs 0.108 (0.097–0.120) in NEW. OLD-405 = three partitions
  (new-data 164 rows / 63 KH; old-data-local 178 / 8; old-data-remote-clean 63 / 2). NEW homogeneous.
  Labels: has_keyhole = any frame labelled Keyhole (frame-level labels), so run length can matter.
  49 Bug simulations: Screenshot-Bug frames late in the run, eligibility UNRESOLVED → stay out.
- 2026-10-05 Phase 1: has_keyhole = 1[max depth ≥ ≈111 µm] on OLD (AUC 1.000); NEW has no continuous
  targets in the repo (D1). Compatibility: labels agree in the overlap; log-h "level shift" is a region effect
  (thresholds 20.91 OLD-in-NEW-box vs 20.94 NEW-in-OLD-box); no campaign offset under a flexible GPC (+0.001
  nats). POOLED (541) adopted as primary real benchmark, POOLED_STD (500) as sensitivity. DATA_AUDIT.md.
- 2026-10-05 Open item (a) resolved (`phase0/new_hyper_seed_factorial*`): margin BA AULC ≈ 0.66 under fixed
  OLD hypers and per-step ML-II and both seed schemes; random gains +0.023–0.026 from ML-II; random − margin
  −0.022/−0.003 (fixed; W15/W17 seeds) vs +0.002/+0.020 (ML-II). The NEW exception = ML-II × random-design
  interaction + seed noise; margin is not hyperparameter-limited.
- 2026-10-05 Items (b)–(d) recorded in ERRATA.md / RED_TEAM.md.
- 2026-10-05 Phase 2: BENCHMARK_SPEC.md locked (tasks R1/R1_STD/R2/R2rev/R3_NEW/R3_OLD, S1 twins, S2 stress;
  blocks DEV 1–8, C1 9–12, C2 13–16, C3 17–20; metrics incl. queries-to-target). Twin truths fitted to the 541
  pooled labels (agreement 0.946–1.000; T_NW/T_QL nearly erase NEW's rare pocket). Baseline reproduction on DEV
  launched (`src/week18_baselines.py`, caches `phase2/cache_*`).
- 2026-10-05 Phase 3 prep: censored (Tobit) GP implemented and tested (exact in the all-Gaussian case; label-only
  rows censored on either side); T_TOBIT twin (agreement 0.983 with OLD labels; NEW-like prevalence 0.915).
  Arms added: G3L (log inputs), LTn (nested LT), mix25 (exploration mixture). Kill criteria logged before runs.
- 2026-10-05 Theory T18-1: binary needs ⌈log2(N+1)⌉ (KNOWN); censored affine branch 2 queries (PROVED); censored
  smooth branch saves ≈30% only at N = 4096, nothing at N ≤ 64 (NUMERICALLY CHECKED) → prediction P-T18-1.
- 2026-10-05 Real DEV baselines running (resumable; heavy transfer tasks first).
- 2026-10-05 Integrity: 704/22,072 DEV baseline fits (R2 transfer mostly; n ≈ 413–485, fixed OLD kernel
  amplitude 378) had fixed-point error 1e-6–9e-4: the Week 17 stopping rule stops when backtracking stalls on
  round-off. Reproduced states: max |Δp| ≤ 6e-5 → DEV baselines retained. Solver now stops on the fixed-point
  error (fp ≤ 1e-9; `SafeguardedFixedMeanLaplaceGPC.FP_TOL`, set by week18_engine); Week 17 default unchanged.
- 2026-10-05 Real DEV baselines (BA AULC): R1 G3m 0.948 / M3 0.950 / H 0.947 / random 0.924; R2 G3m 0.682 /
  G3 fixed-OLD 0.686 / LT 0.685 / random 0.657; R3_NEW G3m 0.671 / random 0.681 / candB 0.674; R3_OLD G3m 0.924 /
  LT 0.931 / M3 0.930 / **GPR-depth straddle 0.944** (q20 0.817 vs 0.842); R2rev G3m 0.929 / GPR-depth 0.941.
  OLD prior lifts NEW AUC 0.819 → 0.909 (R3_NEW → R2).
- 2026-10-05 Phase 2 done (PHASE2_BASELINES.md): twins — LT+m ≥ G3+m on most binary twins; GPR-depth best on
  both depth twins incl. the non-own family (T_TOBIT OLD 0.830 vs 0.776). External validity: twins τ 0.22,
  W17 cells 0.16, real-vs-real 0.00 → no universal real ranking; Week 17's "M3 ≪ G3" fails on OLD/POOLED.
  Degenerate (single-class) NEW-like twin pools are skipped and logged.
- 2026-10-05 Phase 3: E2 (Tobit) first twin run: weak (+0.012…+0.021 vs G3, CIs include 0; E1 GPR-depth
  +0.034…+0.124) and 12.7% of fits not converged (fixed point > 1e-6) → solver rewritten (analytic GPML-5.1
  gradients — implicit term sign verified numerically; relative fixed-point stopping with round-off-floor stall
  rule); ≈ 35× faster at n = 485. New candidate E3 (mixed-likelihood depth GP: every observed depth exact, label-only
  rows censored) registered with kill criteria (commit 1ded7f43) and launched with E2 re-run and E1 on
  partial-depth tasks (depth2). Killed before running: B1 hierarchical (no campaign offset), D1 monotone (NEW
  order violations 2.4%; Week 14 G3C harm on NEW), A2 hyperprior (no headroom under margin).
- 2026-10-05 Phase 2 contrasts (phase2/contrasts_*.csv, qtt_*.csv): E1 (GPR-depth + straddle) vs G3 + margin:
  R3_OLD +0.021 [0.014, 0.030] BA AULC, median QTT to G3's B80 level 32 vs 56 (−43%); R2rev +0.012 [0.007, 0.016],
  28 vs 48. q20 lower (0.817 vs 0.842 on R3_OLD) — as in Week 7.
- 2026-10-05 **Integrity: twin truth drift caught and fixed.** T_TOBIT's truth is a TobitGP fit; rewriting the
  E2/E3 solver (1ded7f43) silently changed the truth (G3/E1 runs on T_TOBIT tasks no longer reproduced Phase 2;
  T_DEPTH and binary twins reproduced exactly). Fix: the truth now uses a frozen copy of the e351cb4f code
  (`src/week18_tobit_truth_v1.py`), verified to reproduce Phase 2 bit-for-bit; regression test
  `test_week18_twin_truth_frozen.py`. The first depth2 T_TOBIT results (against the drifted truth) are kept in
  `phase3/depth2/superseded_truth_v2/` and not used; T_TOBIT tasks re-run.
- 2026-10-05 depth2 twins (DEV, non-T_TOBIT part valid): E3 (MixGP + margin) on T_DEPTH OLD +0.066 [0.040, 0.095]
  NSD AULC vs G3 + margin (E1 +0.059). **Label-only E3 is a weaker binary classifier than G3** on all binary twins
  (−0.02 … −0.22; straddle far worse): E3's value is the depth likelihood, not its probit/log-input GPC part.
- 2026-10-05 **Astra Round 3 integrated (Phase 4)** at the owner's request (files opened with the owner's
  permission; verbatim copy in `outputs/astra_round3/`, SHA-256 manifest verified). Scope: Week 16 audit. Checked
  independently: L3, C10, R5, P5 exact; D4 bound on real data; Week 16 numerical items (E18-5). Accepted: Week 16
  interpretation narrowed (E18-4). Their level-shift conjecture tested → own Phase 1 wording corrected (E18-3:
  1-D threshold shift +0.17 [0.03, 0.29] overall, +0.01 [−0.14, 0.28] in the overlap — not decidable). Deferred:
  same-state latent/channel/updater factorial (needs Week 16 covariances, not saved; PEER is not a Week 18 candidate).
  No freeze changed.
- 2026-10-05 **depth2 results (DEV; 10,797 real fits, 0 with fixed-point error > 1e-6).** E1 (Week 7 depth GPR +
  straddle) is the only depth learner that wins on real data: R3_OLD +0.021 [0.014, 0.030], R2rev +0.012 BA AULC,
  queries to G3's B80 accuracy 32 vs 56 / 28 vs 48; gain largest at startup (B16 BA 0.904 vs 0.821) — **P-T18-1
  held** (early, conduction-rich pools; NEW-like twin +0.020 n.s.). q20 lower (−0.026 / −0.045). With partial depth
  (R1_POOLED: NEW rows have no depth in the repository) E1 is −0.037: its straddle picks NEW points whose depth it
  cannot use. **E3 killed** (R3_OLD +0.008 with straddle, R1 −0.031, below E1; its label-only part is weaker than G3
  on every binary twin). **E2 not carried forward** (R3_OLD −0.023). Twins (frozen truth): E3 ≈ E1 (+0.057–0.066
  on OLD-like depth twins). Conclusion so far: the depth advantage is real where every paid run reports depth;
  whether it extends to NEW/POOLED needs the NEW monitors (decision D1).
- 2026-10-05 Chain split to fit the 2 h background limit (dev_arms `part` = noprior / prior). Headroom restricted to
  tasks without a large prior (14 R2 tasks done before the limit are kept).
- 2026-10-05 **Confirmation round 1 (freeze fc1afb50): E1 PASSES** (round_1/ROUND_1_RESULTS.md). C1 block, first use:
  R3_OLD +0.0285 [0.010, 0.047] BA AULC, queries to REF's B80 level 30 vs 88 (−66% [44, 74]); R2rev +0.012
  [−0.001, 0.024]; fresh twins T_DEPTH +0.082 [0.041, 0.125], T_TOBIT OLD +0.062; non-inferior on every in-scope
  task (min +0.009). q20: R3_OLD −0.003 n.s., R2rev −0.024. 2,064 fits converged. Phase 6 (depth stress round 1,
  base seed 1870) launched; Weeks 12–18 regression tests running.
- 2026-10-05 **Phase 6: E1 survives** the depth stress worlds (round-1 seeds): worst SD_NOISE25 −0.018
  [−0.077, 0.034]; drift +0.052, missing-30% +0.033, noise-10% +0.082, jump +0.013, NEW-like +0.005. **Stopping
  rule met.** Remaining: finish the binary-portfolio screening (cfa) and theory checks for the record; reports.
- 2026-10-05 Binary portfolio screening (paired DEV subset): G3L, LTn, mix25 all killed (none ≥ +0.005 on 2 of 3
  real families). Partial headroom: G3 + margin at B_max equals its full-pool ceiling on R1/R2 → binary frontier
  explained. T18-5 partly refuted (length-scale bias at b = 40 harmful; amplitude unidentified; insensitive only at
  b ≥ 80). Background jobs stopped by the 2 h limit (headroom R1 22/40, R2 13/40; cfa R3_OLD 15/16) were not
  restarted. **Campaign closed: verdict IMPROVEMENT ON SOME TASKS ONLY.** Open: D1 (NEW monitors) → the unused C2/C3
  blocks can test E1 on NEW/POOLED with full depth.
- 2026-10-05 **D1 granted by the owner; NEW monitors downloaded** (272 files, 1.43 GB, all verified against the
  pinned tree). Max depth re-derived with the Week 7 definition (exact on 12 OLD runs). **On NEW the label is not a
  max-depth threshold** (AUC 0.891; 7/12 non-Keyhole runs ≥ 111 µm, concentrated in fast scans VX > 0.85;
  DATA_AUDIT amendment 2). E1 frozen definition unchanged.
- 2026-10-05 depth3 (DEV, full depth on all real tasks; E1 exactly as frozen): R1_POOLED −0.001 [−0.004, 0.003],
  R3_NEW −0.021 [−0.080, 0.039], R3_OLD +0.021 (reproduces Phase 2 exactly). In R1, E1 is no better even on the OLD
  test points (accuracy 0.959 vs 0.970 at B112): NEW's label/depth disagreement contaminates the single-threshold
  depth model. Transfer tasks running.
- 2026-10-05 **Round 2 complete (C2, freeze 1d560792):** Q2a fails (R1_POOLED +0.004 [−0.001, 0.009]); Q2b fails
  (R3_NEW −0.022; R2_TRANSFER +0.020 n.s.); Q2c fails (R3_OLD +0.016 [0.013, 0.020], positive but below the +0.02 bar;
  QTT −12%). 10 of 3,040 fits (G3 reference on R2_TRANSFER) above the fixed-point rule (≤ 2.3e-5), recorded and not
  decision-relevant. Saturation check (T18-2(i)): the saturation budget is ≈ 40 queries for N = 108…866 → the
  nonparametric law is refuted for the real-data boundary (index-like). Verdict unchanged: IMPROVEMENT ON SOME TASKS ONLY.
  C3 unused.
