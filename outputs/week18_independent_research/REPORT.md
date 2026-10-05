# Week 18+ independent research campaign — report

Status: IN PROGRESS (this file is completed at the end of the campaign; evidence labels as in CLAIM_LEDGER.md).
Start `bbb79eaf` (Week 17). Resume point: RESEARCH_LOG.md. Every attempt: ATTEMPT_LEDGER.md.

## 1. What was re-tested and what changed (Phases 0–2)
- **NEW exception (open item a).** Margin is not hyperparameter-limited on NEW (BA AULC ≈ 0.66 with fixed OLD
  hyperparameters and with per-step ML-II, under both seed schemes). Random refinement gains +0.023–0.026 from
  ML-II, so "random ≥ margin on NEW" (Week 17) is an ML-II × random-design interaction plus seed noise
  (POST-HOC, phase0/).
- **The label is a threshold.** On OLD, has_keyhole = 1[max depth ≥ ≈ 111 µm] to within one run (HISTORICAL,
  DATA_AUDIT §2). Week 7's depth-GPR result reproduces on the new benchmark (DEVELOPMENT): +0.021 BA AULC on R3_OLD,
  43% fewer paid simulations to reach G3 + margin's B80 accuracy, lower q20.
- **Pooling OLD + NEW is legitimate.** Labels agree where the campaigns overlap; the log-h "level shift" is a
  region effect (20.91 vs 20.94 in the overlap); a campaign offset adds nothing (+0.001 nats) (POST-HOC, DATA_AUDIT §3).
- **No universal real ranking.** The five common baselines are ordered differently on every real task (Kendall τ
  between real tasks 0.00); twins (0.22) and Week 17 cells (0.16) cannot be validated as proxies of "the" real
  ranking. Week 17's held-out "M3 ≪ G3" holds on NEW (−0.070) but not on OLD / POOLED (+0.006 / +0.002).
- **Integrity fixes this week:** fixed-point stopping rule for large-kernel Laplace fits (704 Phase 2 fits affected,
  |Δp| ≤ 6e-5); Tobit solver rewrite (12.7% unconverged fits in the first E2 run); twin-truth drift caught and frozen.

## 2. Benchmark (BENCHMARK_SPEC.md, locked before method work)
R1 POOLED, R2 TRANSFER / R2rev, R3 NEW / OLD; S1 twins (T_GP, T_GBT, T_NW, T_QL, T_DEPTH, T_TOBIT); S2 stress
(Week 17 cells re-seeded, rare pocket, two-campaign). Blocks DEV 1–8, C1 9–12, C2 13–16, C3 17–20. Metrics: BA
AULC, q20 (historical definition), queries-to-target, NSD AULC.

## 3. Research loop (Phase 3) — see ATTEMPT_LEDGER.md
TBD.

## 4. Theory (Phase 4) — see THEORY_WEEK18.md
TBD.

## 5. Confirmation (Phase 5) and stress tests (Phase 6)
TBD.

## 6. Verdict
TBD.
