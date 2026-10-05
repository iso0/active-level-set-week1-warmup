# Week 18+ independent research campaign — report

Start `bbb79eaf` (Week 17). Commits: `dd7fde9c` (Phase 0–1), `b17bed56` (benchmark lock), `e351cb4f`, `092582f4`,
`e183d345` (Phase 2), `1ded7f43` (E3 registered, solver fix), `3b3ac406` (Astra Round 3, truth freeze),
`fc1afb50` (**FREEZE round 1**), `0e8aaa82` (round 1 results), `9ee38d3f` (Phase 6). Evidence labels as in
CLAIM_LEDGER.md; every attempt in ATTEMPT_LEDGER.md; resume point RESEARCH_LOG.md.

## 0. Summary
- **Confirmed improvement, scoped.** Where each paid simulation reports its max melt-pool depth, a GP on log depth
  with straddle acquisition (E1, Week 7's formulation) beats the G3 + margin endpoint. On the untouched C1 block
  of R3_OLD it gives **+0.0285 BA AULC [0.010, 0.047]** and reaches G3's B80 accuracy after **30 instead of 88
  simulations (−66% [44, 74])** (SPLIT-CONFIRMATION). Fresh twin seeds give +0.082 NSD AULC [0.041, 0.125]
  (SEMI-SYNTHETIC). It survives six depth stress worlds; the worst is 25% depth noise at −0.018 (HELD-OUT-SYNTHETIC).
- **Not shown, and why.** NEW runs have no depth in this repository, so POOLED/NEW could not be tested with full
  depth (owner decision D1). With partial depth, E1 is worse than G3 on POOLED (DEVELOPMENT −0.037). q20 does not
  improve. For binary-only data no new model or rule cleared its kill criteria: G3 + margin stays the endpoint there.
- **Several earlier conclusions were benchmark or framing artefacts** (§1). These are: the NEW exploration exception;
  the transfer of Week 17's held-out synthetic ranking to real tasks; and the strength of the OLD→NEW level-shift claim.

## 1. Phase 0–1: re-grounding (POST-HOC / HISTORICAL)
| Earlier conclusion | Week 18 finding | Status |
|---|---|---|
| NEW: exploration (random, Candidate B) ≥ margin (Week 17) | Margin ≈ 0.66 BA AULC under fixed OLD and per-step ML-II hyperparameters, both seed schemes. Random gains +0.023–0.026 from ML-II. random − margin = −0.022 / −0.003 (fixed) vs +0.002 / +0.020 (ML-II) | **artefact**: ML-II × random-design interaction + seed noise |
| Week 17 mean M3 − G3 −0.110 | −0.102 | erratum E18-1 |
| has_keyhole is a primary binary outcome | OLD: has_keyhole = 1[max depth ≥ ≈ 111 µm], AUC 1.000 | **framing**: the label is a threshold of an observed continuous output |
| OLD→NEW "physics level shift" (Week 17) | Labels agree in the overlap (94.4%); a flexible GPC needs no campaign offset (+0.001 nats). 1-D log-h shift +0.17 [0.03, 0.29] overall, +0.01 [−0.14, 0.28] in the overlap | **not decidable** (E18-3); pooling legitimate |
| Week 16 "remaining gap = model information" | The truth-conditioned oracle mixes law, channel, updater and loss (Astra Round 3; independently re-read) | narrowed (E18-4, E18-5) |
| G3 + margin is the defensible endpoint | Holds for binary labels; superseded where depth is observed (§4) | refined |

## 2. Phase 2: benchmark and baselines (DEVELOPMENT)
Locked before method work (BENCHMARK_SPEC.md): real R1 POOLED (541 runs), R2 TRANSFER (+ reverse), R3 NEW / OLD;
digital twins fitted to the real labels and OLD depth (T_GP, T_GBT, T_NW, T_QL, T_DEPTH, T_TOBIT; truths frozen);
S2 stress worlds; blocks DEV 1–8, C1 9–12, C2 13–16, C3 17–20; BA AULC, q20, queries-to-target (QTT), NSD AULC.
Baselines: PHASE2_BASELINES.md, figure `figures/fig_w18_real_baseline_curves.png`.
- **External validity.** Real tasks share no ordering of the common baselines (mean Kendall τ 0.00). Twins agree with
  real tasks at 0.22 and the Week 17 cells at 0.16. Synthetic rankings cannot be validated as predictions of "the"
  real ranking. Week 17's "M3 ≪ G3" holds on NEW (−0.070) but not on OLD/POOLED (+0.006/+0.002).
- **Random refinement** is the worst G3 rule everywhere except NEW-like pools (T18-4 explains why).
- **Integrity.** 704 Phase 2 fits stopped at fixed-point error 1e-6–9e-4 under the Week 17 rule. The impact was
  |Δp| ≤ 6e-5; the stopping rule was fixed. Twin-truth drift was caught and frozen. All later fits converged
  (max fixed-point error ≈ 2e-7).

## 3. Phase 3: research loop (DEVELOPMENT; ATTEMPT_LEDGER.md)
| id | candidate | mechanism | outcome | decision |
|---|---|---|---|---|
| A0 | hyper × seed × rule factorial (NEW) | NEW exception = hyper/seed artefact | confirmed | resolved |
| E1 | depth GPR + straddle | depth carries distance-to-boundary | R3_OLD +0.021, R2rev +0.012, QTT −43%; partial depth −0.037 | **frozen, round 1** |
| E2 | censored (Tobit) depth GP | Keyhole depth is another regime | R3_OLD −0.023; first run 12.7% unconverged fits → solver rewritten | not carried forward |
| E3 | mixed-likelihood depth GP (all depths exact + label-only rows) | use label-only NEW rows | R3_OLD +0.008, R1 −0.031; label-only part < G3 on all binary twins | killed |
| B1 | hierarchical two-campaign GPC | campaign level shift | premise unsupported (+0.001 nats) | killed before running |
| D1 | monotone inference (closure / monotone prior) | physics order gives free labels | NEW order violations 2.4%; Week 14 harm on NEW | killed before running |
| A2 | hyperprior / transferred hypers | stabilize small-n ML-II | no headroom under margin (A0) | killed before running |
| C1 | G3 on log inputs (G3L) | power-law physics | R1 −0.003, R3_NEW +0.003, R3_OLD −0.006 | killed |
| F1 | LT with nested two-start ML-II (LTn) | single-start optimizer failure | R1 +0.000, R3_NEW +0.011 (n.s.), R3_OLD −0.002 | killed |
| A1 | exploration mixture (mix25) | random queries inform ML-II / pockets | R1 −0.003, R3_NEW +0.005 (n.s.), R3_OLD +0.001 | killed |
| E1-sched | E1 with ML-II every 8 queries | — | R2rev −0.081 (fragile) | E1 frozen per-step |

### 3a. Binary-portfolio screening (C1, F1, A1)
Paired screening subset (DEV repeats 1–8 × folds 1–2), because the full per-step nested-LT run measured at ≈ 17 h.
All three need ≥ +0.005 BA AULC on at least 2 of {R1, R3_NEW, R3_OLD}; none reaches it on more than one (all
intervals include 0). With the headroom result (§5, T18-2: G3 + margin at B_max already equals its full-pool ceiling
on R1/R2), the binary portfolio is exhausted: **for binary labels the frontier is explained, not moved.**

## 4. Phase 5–6: confirmation (round_1/ROUND_1_RESULTS.md; figure `figures/fig_w18_round1_confirmation.png`)
FREEZE_ROUND_1.md was pushed before any round-1 run (`fc1afb50`); the runner refuses to start otherwise.
| Task | E1 − G3 + margin | 95% interval | label |
|---|---:|---|---|
| R3_OLD BA AULC (primary) | **+0.0285** | [0.010, 0.047] | SPLIT-CONFIRMATION |
| R3_OLD queries to G3's B80 level | **30 vs 88 (−66%)** | [44%, 74%] | SPLIT-CONFIRMATION |
| R2rev BA AULC | +0.012 | [−0.001, 0.024] | SPLIT-CONFIRMATION |
| q20 R3_OLD / R2rev | −0.003 / −0.024 | [−0.031, 0.026] / [−0.046, −0.001] | SPLIT-CONFIRMATION |
| T_DEPTH NSD AULC (primary twin) | **+0.082** | [0.041, 0.125] | SEMI-SYNTHETIC |
| T_TOBIT OLD / pooled / NEW | +0.062 / +0.039 / +0.009 | — | SEMI-SYNTHETIC |
| depth stress: worst world (25% depth noise) | −0.018 | [−0.077, 0.034] | HELD-OUT-SYNTHETIC |
Decision: all three success routes held, non-inferior on every in-scope task (minimum +0.009), no stress world
below −0.03 → **passes, survives; stopping rule met after one round** (C2/C3 unused).

## 5. Phase 4: theory (THEORY_WEEK18.md)
| Result | Status | Prediction / check | Held? |
|---|---|---|---|
| T18-1 binary vs censored 1-D threshold search | KNOWN / PROVED / NUMERICALLY CHECKED | depth gains on coarse 4-D pools must come from shared surface information, appear early, be small on NEW-like pools | **yes** (B24 0.927 vs 0.863; NEW-like twin +0.009) |
| T18-2 finite-pool floor N^{−α/(α+d−1)}, saturation budget N^{(d−1)/(α+d−1)} | KNOWN / DERIVED | at B_max no rule/model headroom; gains only at small budgets | **yes** (R1: G3 + margin B120 0.961 = full-pool ceiling 0.960; model ceilings within 0.008); N-scaling not run |
| T18-3 binary source labels identify only nesting, not a level shift | PROVED | prior lifts AUC more than BA | **yes** (AUC +0.09, BA +0.011; agrees with Astra P6) |
| T18-4 information per query (probit Fisher information vs 1/σ²) | KNOWN (application PROVED) | depth gain early and conduction-rich; random loses on large pools; gain falls with depth noise | **yes** (round 1, Phase 6 noise trend) |
| T18-5 ML-II under boundary-concentrated designs | CONJECTURE | shorter length-scales, larger amplitude, classifier insensitive | **partly refuted**: length-scale bias harmful at b = 40 (−0.03…−0.10 BA); amplitude unidentified (at the bound), not inflated; insensitive only at b ≥ 80 |
| Astra Round 3 | integrated as hypotheses; L3, C10, R5, P5, D4 independently checked | level-shift conjecture tested → E18-3 | partly |

## 6. Verdict
**IMPROVEMENT ON SOME TASKS ONLY** — confirmed where depth is observed (OLD-type tasks), untested on NEW/POOLED for
lack of NEW depth, and none for binary-only data.
