# Study index: every study, why it was run, what it found, what it led to

Written on 2026-11-02 during the finalization. It is the one chronological table of the whole programme, from Week 1 to GT. Each row gives the question, the earlier result that triggered it, the answer, the strength of the evidence, the record that holds it, and the study it led to.

Numbers are copied from the named records; nothing was recomputed. Read identifiers with [GLOSSARY.md](GLOSSARY.md): several short names (C1, C3, E1, A, G3, D1) mean different things in different studies. The narrative that connects the rows is in [THESIS_SYNTHESIS.md](THESIS_SYNTHESIS.md).

**Evidence words in the last-but-one column:**
- *confirmatory*: a registered rule on frozen or fresh data;
- *DEV*: development on already-inspected data;
- *descriptive*: an association or count without a model comparison;
- *post-hoc*: computed after the result was seen;
- *source-transferred*: condensed from Astra's own package.

All real-data studies use the same SPH simulations: OLD 405 runs, NEW 136 runs, pooled 541. None of them is an external or physical validation.

## Phase I — Synthetic active level-set estimation (Weeks 1–4, 2026-06-22 → 06-29)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| W1 | 06-22 | Can an active learner find the level set of a thresholded function? | thesis question | GPR stand-in on ±1 labels for thresholded Branin; error 0.337 → 0.061 | exploratory | `outputs/branin_week1/summary.json` | W2 |
| W2 | 06-22 | Which pool rule? | W1 | straddle family adopted (randomized straddle 0.0602, straddle 0.0620, random 0.1194) | exploratory | `outputs/week2_acquisition_comparison/` | W3 |
| W3 | 06-25 | Does it hold in 4-D? | W2 | thresholded Ackley4 adopted; straddle 0.1684 vs random 0.2827 | exploratory | `outputs/week3_4d_named_benchmark_comparison/` | W4 |
| W4 | 06-27 → 06-29 | Which boundary metric, surrogate and acquisition? | W3 | near-boundary q10/q20/q30 metrics; GPR heuristics negative; fixed-kernel GPC and uncertainty repulsion; Hartmann4 and Bernoulli SUR: **no acquisition universally dominates** (C10) | exploratory | `outputs/week4_*`; `docs/alse/decisions.md` rows 2026-06-27 to 06-29 | move to real data |

## Phase II — Real SPH data and the Keyhole label (Weeks 5–7, 07-22 → 08-12)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| W5 | 07-22/23 | Can a GP regress a real SPH quantity? | Phase I | first-Conduction timestep on `sph_dataset` (241 sims): isotropic Matérn 3/2 default; ARD rejected | exploratory | `outputs/week5_02_*`, `outputs/week5_05_*` | W6 |
| W6 | 07-27 → 08-08 | Which physical targets? | W5 | T0 window rule; learned nugget for depth; regime targets G3 (depth > 50 µm) and R3 (depth / width) defined | exploratory | `outputs/week6_*` | W7 |
| W7 P1–P5.5 | 08-09 → 08-11 | What is the Keyhole label on `sph_v2`, and can a depth model carry it? | W6 | `has_keyhole` = any manual `Keyhole` frame (405 OLD runs, 73 Keyhole); depth error heavy-tailed and Keyhole-concentrated → **pivot to the binary boundary**; no universal G3 threshold; max depth the robust scalar companion | exploratory; data facts | `outputs/week7_01_*` to `outputs/week7_05_5_*`; C36, C37 | W7 P6 |
| W7 P6–P7 | 08-11/12 | Binary or depth acquisition on real data? | W7 P1–P5.5 | central benchmark HYBRID / NO CLEAR WINNER; registered hybrid rule → **BINARY ACQUISITION PRIMARY** | registered (exploratory protocol) | `outputs/week7_06_*`, `outputs/week7_07_*`; C03, C04 | W8 |

## Phase III — Sample efficiency and the physics coordinate (Weeks 8–9, 08-21 → 09-21)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| W8 | 08-21 | How many simulations does margin save? | W7 | headline "0.8138 vs 0.7711, about 40 saved calls, 2.33×" | exploratory | `outputs/week8_02_thesis_consolidation/` | W8.5 (it failed there) |
| W8.5 | 08-26 | Does the saving survive a frozen protocol? | W8 | performance PASS (+0.0373 q20 AULC, lower +0.0313); query saving and multiplier QUALIFY; "40 calls" and "2.33×" FAIL; **`binary_margin` becomes the primary method** | **confirmatory** | `outputs/week8_5_frozen_confirmation/`; C01, C02, C14–C17 | W9 |
| W9 P1–P1.9 | 08-29 → 08-31 | Why is the boundary learnable, and does physics help? | W8.5 | H = 320 closure: saving claim not supported in the tail; **h = P/√(VX·LS³)** separates the classes (log h AUC 0.990); physics-ridge residual GPC +0.020; MODEL_DOMINANT (model +0.021, path −0.001); physics-specific +0.018 | exploratory | `outputs/week9_phase1_close_week8/`, `..._1_5_*` to `..._1_9_*`; C18–C24 | W9 P1.10–1.18 |
| W9 P1.10–1.18B | 09-01 → 09-03 | Better surrogate? Better acquisition? External check? | W9 P1–1.9 | external Masinelli Ti64: generic direction superior (appendix only); fixed-mean GPC, ARD kernel (G3 classifier), **M3** surrogate best on replay; **no acquisition beats margin** (correction signal, repulsion scales, PA-TVR, FAST-SUR, exact GPC-SUR all fail) | exploratory | `outputs/week9_phase1_10_*` to `..._18b_*`; C25–C35 | lean tree; W9 P1.19–P2 |
| W9 P1.19–P2 | 09 | Integrity, robust monotone LSE, acquisition search, M3 + G3 margin, simplification, external blind test, method validity, width dynamics | W9 P1.18B | G3-margin early q20 BA −0.0026 [−0.0106, +0.0054] (not supported); CCM search read with the Phase 1.21 errata; Phase 1.22 stopped (no eligible external blind pool); Phase 1.23 incomplete (no final report); Phase 2 width controls | exploratory | `docs/phases/week9_phase1_19a_*` to `week9_phase2_*`; progress log 2026-09-14 | consolidation |
| CONS | 09-14/15 | One repository | many working copies | 76 output families, 18,559 source contents mapped; history in `docs/_history/` | records | `docs/PROJECT_INDEX.md`, `outputs/project_consolidation/` | W10 |
| W10 | 09-21 | Does the Track A candidate replicate internally? | W9 | PG-RMBC P4 − P1 −0.0026 [−0.0063, +0.0011]; **Track A frozen**: M3 + margin historical control, Candidate B positive but below the +0.01 threshold, boundary displacement no gain | registered | `outputs/week10_trackA_pg_rmbc/FINAL_METHOD_REPORT.md`, `docs/trackA_freeze/TRACK_A_FINAL_STATE.md` | W11 |

## Phase IV — NEW data and the diagnosis of what limits learning (Weeks 11–18, 10-02 → 10-05)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| W11 | 10-02 | Frozen external validation on Ioan's NEW batch | Track A freeze | 185 runs delivered, 136 included, 49 held back because of the Bug (never used); **INCOMPLETE_FROZEN_STOP**: the fixed B16 start of repeat 3 / fold 4 is one-class, so no effect, interval or ranking exists | confirmatory attempt (stopped) | `outputs/week11_external_execution_record/CONFIRMATORY_STOP_REPORT.md`; `docs/week11/WEEK11_THESIS_DECISIVE_STAGE_REPORT.md` | W12 |
| W12 | 10-03 | Paid startup, OLD → NEW transfer, NEW-only learning | W11 stop | adaptive physics startup finds both classes by B9 in all 100 splits but later q20 does not improve; Candidate B − margin16 +0.0026 [−0.0048, +0.0098]; **no strong general acquisition advantage** | DEV | `outputs/week12_startup_and_transfer_development/COMPREHENSIVE_REPORT.md` | W13 |
| W13 | 10-03 | What has the thesis actually found? | W8–W12 | the limit is not the acquisition function but (1) rare-class discovery, (2) class-ratio dependence of the metric, (3) physics prior anchoring under campaign shift | exploratory diagnosis | `outputs/week13_boundary_evaluation_and_mechanisms/WEEK13_RESEARCH_REPORT.md` | W14 |
| W14 | 10-04 | Theory of discovery and of finite-pool metrics | W13 | discovery needs a structural assumption (D1–D5 certificates); finite-pool boundary metrics are density-weighted and cannot identify acquisition headroom | theorem + frozen benchmark | `outputs/week14_research_program/WEEK14_MASTER_REPORT.md` | W15 |
| W15 | 10-04 | Can the true-boundary oracle be approximated? | W14 | **NO NEW METHOD JUSTIFIED**: EBR-D −0.0095 NSD AULC (7/16 cells); corrected T_both law; headroom is mostly truth knowledge | registered | `outputs/week15_boundary_acquisition/WEEK15_REPORT.md` | W16 |
| W16 | 10-04/05 | Does Astra's theory operate in our models? | W15; Astra round 3 | 46 exact tests pass; margin far from optimal under its own model, but acting on the model's value does not recover the headroom | exploratory | `outputs/week16_theory_meets_data/WEEK16_REPORT.md` | W17 |
| W17 | 10-05 | Is the remaining difficulty a fixable model problem? | W16 | **NO CHANGE JUSTIFIED**: G3 + margin remains; M3's saturated physics mean diagnosed; a better model does not unlock model-aware acquisition | registered | `outputs/week17_model_and_acquisition/WEEK17_REPORT.md` | W18 |
| W18 | 10-05 | Re-question the assumptions | W17 | OLD label = max depth above ≈ 111 µm (AUC 1.000); **depth GP + straddle (E1) beats G3 + margin on OLD** (R3_OLD +0.0285, block C1); C2 replication +0.016 below the +0.02 bar; NEW label is not a depth threshold (AUC 0.891, fast scans) → **IMPROVEMENT ON SOME TASKS ONLY** | confirmatory blocks C1, C2 | `outputs/week18_independent_research/REPORT.md` | W19 |

## Phase V — Temporal regimes (Weeks 19–20, 10-09 → 10-13)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| W19 audit | 10-09 | Ioan: Keyhole → conduction transitions in time | W18 NEW gap | two forms of "K then only C" (short start-up K in fast scans; switch near the 2.1 ms recording end in slow scans); the active-window depth A raises NEW AUC 0.891 → 0.978 | descriptive | `outputs/week19_temporal_regime_audit/REPORT.md` | W19 pilot |
| W19 pilot | 10-10 | Does target A help E1? | W19 audit | ACTIVE 0.730 vs WHOLE 0.632 vs G3 0.618 at B40; **ADVANCE (exploratory gate only)** | DEV, post-hoc target | `outputs/week19_temporal_regime_dev_pilot/PILOT_REPORT.md` | W20 |
| W20 | 10-12/13 | Real active learning with A; temporal GPs | W19 | NEW ACTIVE − G3 +0.056 [+0.015, +0.103] on DEV 1–8; the gain comes from A, not from avoiding the reversed slope; temporal GPs predict A about 10× worse than a scalar GP | DEV | `outputs/week20_active_temporal_development/DEVELOPMENT_REPORT.md` | C3 |
| C3 | 10-13 | Confirm ACTIVE E1 + straddle vs G3 + margin | W20 | **NOT CONFIRMED** at the frozen bar: +0.007 [−0.036, +0.053]; ACTIVE − WHOLE +0.044 replicated; no specificity gain | **confirmatory** (last clean block) | `outputs/week20_active_temporal_development/c3/decision_c3.json` | joint study |

## Phase VI — Joint depth–label models and physical outputs (10-13 → 10-17)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| JDL Stage M | 10-13/14 | Does Astra's joint depth–label model J beat a matched binary model? | C3 | **SCREEN FAILED**: NEW B40 BA +0.006 [−0.052, +0.065]; better log loss (−0.172) and AUC (+0.074); OLD BA +0.067 / +0.057; at π̂ the NEW gain is a fast-corner split (L1); no model resolves the fast-scan corner (L2) | registered screen + exploratory | `outputs/joint_depth_label_development/STAGE_M_REPORT.md`, `CLAIMS_MATRIX.md` §1–3 | V2, audit |
| JDL V2, audit, temporal | 10-14/15 | V2 joint model; finite-batch decision rule; temporal repair | Stage M | V2 screen NOT PASSED (BA −0.002); decision audit PRIMARY_UNAVAILABLE (amended A1: 0.858, a cutoff trade); PPCA and NGD-SVGP repair the temporal models but the scalar A GP stays the A model | registered | `V2_MODEL_REPORT.md`, `v2_decision_audit/DECISION_AUDIT_REPORT.md`, `TEMPORAL_REPAIR_REPORT.md`; `CLAIMS_MATRIX.md` §4–5 | execution studies |
| JDL execution | 10-15 | Trained-response AL, corner-local model, stop rule, Astra's BA-risk selector | Ioan meeting 10-15 | TRAINED_AL primary unavailable (one-class start); corner-local NOT SUPPORTED; stopping saves ~10 of 40 queries but a fixed stop at B30 is as good; ASTRA_AL **stopped by the owner** (incomplete, not negative) | registered | `IOAN_RESEARCH_UPDATE.md`; `CLAIMS_MATRIX.md` §6 | pilots |
| JDL pilots | 10-16 | Surprise discovery, physical outputs, temporal velocity | 10-15 | no discovery gain on real NEW; 5 of 7 physical summaries learnable from x (out-of-fold R² 0.70–0.92); physics helps an x-only GPC (+0.09) but **is redundant over E1** (≈ 0); velocity curve R² 0.64 | registered | `PILOT_CAMPAIGN_20261016.md`; `CLAIMS_MATRIX.md` §7 | studies 10-17 |
| JDL studies | 10-17 | Physical outputs from x: fewer simulations? discovery? curves? | Ioan meeting 10-15 | learnable 6/6 NEW, 7/8 OLD; **fewer simulations 0/48**, same-budget gain 1/48; no discovery gain; a direct scalar GP beats curve-derived scalars everywhere | registered | `STUDIES_REPORT_20261017.md`; `CLAIMS_MATRIX.md` §8 | one-pool campaign |

## Phase VII — One pool, paid-only learning from scratch (RC18–RC24, 10-18 → 10-22)

From here on every study uses the single 541-run pool. Every opened simulation counts, including the startup; only paid outcomes reach a learner.

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| RC18 | 10-18 | Physical-output emulation with fewer simulations (48 h campaign) | owner decision 10-18 | TRSQ (OLD prior mean + shared lengthscales + quality noise) saves **21 NEW simulations per output** (DEV); acquisition differences small; label from physics alone at B0: BA 0.69 / AUC 0.92; corner unresolved | DEV (frozen) | `outputs/research_campaign_20261018/opus/FINAL_REPORT_20261018.md` | RC19 |
| RC19 | 10-19 | Pooled, paid-only, from scratch | RC18 | SHQ better for physical outputs (+0.035 R²-AULC); straddle better for the spike region; physics classifier NOT DIFFERENT in BA (better log loss) | DEV | `.../opus_pooled/FINAL_REPORT_RC19.md`; C41–C43 | RC19B |
| RC19B | 10-19/20 | Honest cross-fit Keyhole classifier vs calibrated E1 | RC19 | ATSCF better in log loss (−0.030, 7/8); spike-duration hurdle WORSE | DEV | `.../opus_rc19b/FINAL_REPORT_RC19B.md`; C44–C54 | RC20 |
| RC20 | 10-20 | Where does the gain come from? | RC19B | from the extra physical features, not the SHQ upstream; **log h in the classifier material**; SHQ_ATS_H + margin better and needs fewer simulations to the offline targets | DEV | `outputs/research_campaign_20261020/opus_rc20/final_report/FINAL.md`; C55–C59 | RC21 |
| RC21 / RC21B | 10-20 | Learn the regularisation from paid labels | RC20 | main question NO (no BA or spend gain); PHR_NRMAP better log loss (−0.030, 8/8) | DEV | `.../opus_rc21/final_report/FINAL.md`, `b_final_report/FINAL.md`; C60–C69 | RC22 |
| RC22 | 10-21 | Robustness, needed ingredients, one information-gain selector | RC21 | BALD selector FAILED vs margin + coverage; temperature and spike **useless once log h and predicted depth are present**; no learner extrapolates well; HA_LR + margin recommended | DEV | `outputs/research_campaign_20261021/opus_rc22/FINAL_REPORT_RC22.md`; C70–C80 | RC23 |
| RC23 | 10-21 | Is the fully lean h + depth system enough? | RC22 | **decision D1: HA_LEAN + margin is the thesis learner**: non-inferior to PHR_NRMAP (+0.0056 / +0.0038, lower bounds > −0.010), robust in 4 conditions, about 3× less CPU | registered | `.../opus_rc23/FINAL_REPORT_RC23.md`, `DECISION.json`; C81–C87 | RC24 |
| RC24 | 10-21/22 | Physics-anchored depth emulator (HA_TREND); synthetic families | RC23 | Stage C CONFIRMED on its pooled criterion; **post-audit final comparison keeps HA_LEAN + margin** (HA_TREND log-loss non-inferiority FAIL, +0.0073); the trend gain is equally given by a generic trend; propositions corrected (h has units; P2 withdrawn) | registered | `.../opus_rc24/FINAL_REPORT_RC24.md`, `post_audit/FINAL_REPORT_RC24P.md`; C88–C108 | EL |

## Phase VIII — From an early gain to the final learner (EL → C1C, 10-24 → 10-26)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| EL | 10-24/25 | Does HA_TREND's early gain become a single-learner saving? | RC24 | the early gain is a **prediction effect, not a query-path effect**; D and the mixture E NOT_ADOPTED (keeping BA 0.95 fails the reliability margin); learner stays HA_LEAN | registered, fresh 83–162 | `outputs/research_campaign_20261024/opus_early_learning/FINAL_REPORT_EL.md`; C109–C114 | EA |
| EA | 10-26 | Which stage limits learning? | EL | **bottleneck = depth at unqueried inputs** (information limit); HA_TREND's late loss is a small-n ML-II artefact; **C1 = HA_TREND + MAP under a weak hyperprior**: early +0.0056 [+0.0038], 0.95 saving +2.00 (one fresh test) | DEV + one registered fresh test | `outputs/research_campaign_20261026/opus_error_attribution/FINAL_REPORT_EA.md`; C115–C122 | C1C |
| C1C | 10-26 | Does C1's advantage replicate? | EA | every registered verdict passed on 80 fresh repeats: early +0.0053 [+0.0039]; 0.95 saving +1.81 [+0.53]; RELIABLE; late preserved (−0.0006); **C1 + margin = recommended in-pool learner**, HA_LEAN + margin = frozen reference | **confirmatory** (fresh 203–322) | `.../opus_c1_confirmation/DECISION_C1C.md`, `FINAL_REPORT_C1C.md`; C123–C130 | C1S |

## Phase IX — Robustness and the supervisor's last questions (C1S → GT, 10-29 → 11-02)

| ID | Date | Question | Triggered by | Answer | Evidence | Record | Led to |
|---|---|---|---|---|---|---|---|
| C1S | 10-29 | Why does C1 sometimes fall below 0.95 late, and can a stabiliser fix it? | C1C caveat (sustaining) | late regressions are balanced boundary flips; 81 % of the gap is a persistent level deficit; **AVG4 NOT adopted** (primary not shown; 0.95 spend harm); C1 unchanged | **confirmatory** (fresh 323–382) | `outputs/research_campaign_20261029/opus_c1_stability/DECISION_C1S.md`; C131–C138 | FR |
| FR | 10-29 | Can a paid-only trust rule between C1 and HA_LEAN fix C1's extrapolation loss? | C1C / EA K5 warning | GATE failed the registered DEV rule (geometric +0.0045 [−0.0016]); the paid runs cannot reveal which model is right in an unopened region; **information limit**; C1 unchanged | DEV (registered rule; no fresh test) | `.../opus_final_robustness/FINAL_REPORT_FR.md`; C139–C144 | writing; Ioan meeting 10-30 |
| IR | 10-31 | Ioan: do other outputs, especially width, relate to depth? | meeting 2026-10-30 | outputs strongly related to depth, mostly through the inputs (residual ρ ≤ 0.27); width moderate (ρ 0.50; true W/D ≤ 2 BA 0.978); no tried output adds label information beyond h + depth; co-output depth models failed the matched screen | descriptive + DEV screen | `outputs/research_campaign_20261031/opus_ioan_requests/FINAL_REPORT_IR.md`, `IOAN_SUMMARY.md`, `IR_ADDENDUM_20261102.md`; C145–C150 | GT |
| GT | 11-02 | Can predicted geometry (d/w = 1/2) or early temperature replace or help C1? | IR | every label-free geometric classifier clearly below C1 (best −0.0174 early); fixed threshold sits at the conduction cluster's edge (post-hoc); early temperature adds nothing before or within a run; **C1 unchanged** | DEV (registered stops) | `outputs/research_campaign_20261102/opus_geometry_temperature/FINAL_REPORT_GT.md`; C151–C158 | finalization |
| FIN | 11-02 | Finalize the record for writing | owner, 2026-11-02 | this folder; test causes found and fixed; records completed; nothing recomputed | records | `docs/final/` | thesis writing |

## Astra's parallel track (external theory assistant; integrated as hypotheses only)

Astra's results were never used as a learner input. Each was integrated by re-deriving its numbers independently, or was recorded as source-transferred.

| ID | Date | Topic | Status here | Record |
|---|---|---|---|---|
| Rounds 1–3 | 09 → 10-05 | theory notes, counterexamples, sequential physics | integrated as hypotheses; Week 16 tests and Week 18 errata | `outputs/astra_round1/` to `outputs/astra_round3/` |
| Week 19 R&D, Week 20 method development | 10-10 → 10-13 | temporal regime audit plan; joint model | P0–P2 run by Opus in Week 19; the joint model ported in the joint study | `outputs/astra_week19_rnd/`, `outputs/astra_week20_method_development/` |
| Balanced decision acquisition | 10-15 | BA-risk selector, synthetic worlds | INCOMPLETE_WITH_PRESERVED_STOPS (72/84); no ranking or saving claim (U6) | `outputs/astra_balanced_decision_acquisition/` |
| Joint model V2, monitor discovery | 10-14 → 10-16 | V2; monitor-discovery package | V2 ported and screened; monitor package not run | `outputs/astra_joint_model_v2/`, `outputs/astra_monitor_discovery_20261016/` |
| AD18, RP20, LC24, JL26 | 10-18 → 10-26 | synthetic campaigns | source-transferred (claims ledger, C1S addendum); published on the Research Hub | `research/astra/` (Hub, on `main`) |
| FPA29 | 10-29 | finite-pool assurance of a fixed C1 | source-transferred; original practical gate FAILED | `outputs/research_campaign_20261029/opus_final_robustness/hub/ASTRA_FINITE_POOL_ASSURANCE_RECORD.md` |

## Publication layer

| ID | Date | What | Record |
|---|---|---|---|
| Research Hub v1 | 10-28 | public reading layer on `main`: scoped claims (16), experiment registry (15), curated Astra evidence (56 files), MIT / CC BY scopes. Its files are SHA-256-locked and were not edited in the finalization. It covers results up to C1C | `RESEARCH_INDEX.md`, `docs/research/` |
