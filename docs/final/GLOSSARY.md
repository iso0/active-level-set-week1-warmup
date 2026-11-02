# Glossary and identifier map

Written on 2026-11-02 during the finalization. It defines the names used across the records. Every definition points to the record that fixed it; nothing here changes a definition.

**Read this first when you write.** Several short names were reused by different studies and mean different things. Section 1 lists every reuse. In the thesis, write the full name (for example "the C1C learner C1" or "the Week 18 confirmation block C1"), never the bare letter.

## 1. Names with more than one meaning

| Name | Meanings, in time order | How to write it in the thesis |
|---|---|---|
| **C1** | (1) Week 18 confirmation block C1 (repeats 9–12 of the Week 18 real-data benchmark; blocks are DEV 1–8, C1 9–12, C2 13–16, C3 17–20 in `src/week18_tasks.py`), used once for E1 vs G3. (2) The 2026-10-15 execution study CORNER_LOCAL, filed as "C1" (with STOP_RULE as "C2"). (3) **The final learner**: EA candidate C1 = HA_TREND with MAP hyperparameters under a fixed weak hyperprior (`src/ea_cand.py`, `SYSTEMS["C1"]`), confirmed by C1C. (4) Claim IDs C01–C158 of `docs/alse/claims.md` are unrelated. | (3) is "C1" in the thesis; call (1) "Week 18 block C1" and (2) "the corner-local study" |
| **C2** | (1) Week 18 confirmation block C2 (repeats 13–16). (2) The 2026-10-15 STOP_RULE study. | "Week 18 block C2"; "the stop-rule study" |
| **C3** | Week 18 confirmation block C3 (repeats 17–20), the last clean block; spent once in Week 20 on ACTIVE E1 + straddle vs G3 + margin. | "the C3 confirmation" |
| **C4** | A proposed stability check of J_trained + π̂ (joint study). Never run. | — |
| **G3** | (1) Week 6 Phase 3.5 regime target: persistent maximum depth above 50 µm (with R3 = depth over width). Demoted in Week 7 Phase 5.5. (2) Week 9 Phase 1.12 classifier: 4-input GPC with an ARD Matérn-3/2 kernel. Weeks 12–20 used (2) as "G3 + margin", the binary-label reference. | (2) is "the G3 classifier"; (1) is "the G3 depth target" |
| **M0** | (1) Phase 6 GPC (Week 7 central benchmark model). (2) RC18 / RC19 baseline emulator: independent GP per physical output (M0Q = M0 with record-quality weights). | "Phase 6 GPC" vs "independent-output emulator" |
| **E1** | (1) Week 18 arm: depth GP regression + straddle, label = depth above the learned threshold (Week 7 formulation). ACTIVE_E1 / WHOLE_E1 (Weeks 19–20) use the active-window or whole-record maximum depth. (2) Row E1 of `CLAIMS_MATRIX.md` §6 (TRAINED_AL). | "E1 (depth GP + straddle)" |
| **A** | (1) Week 19–20 target: maximum depth inside the active window (`A_active_max_um`). (2) EL / EA / C1C system A = HA_LEAN selects and predicts, i.e. **HA_LEAN + margin, the reference** ("C1 − A"). (3) GT route A: separate log-depth and log-width predictions. (4) RC24 Stage A. | (2): "HA_LEAN + margin"; (1): "the active-window depth A" |
| **B** | (1) Track A Candidate B (Phase 1.21, `early8__coverage_then_margin_B40`). (2) EL system B = HA_TREND selects and predicts. (3) GT route B: direct ratio target g = log(2d/w). | "Candidate B"; "EL system B"; "GT route B" |
| **D** | EL system D = HA_LEAN selects, HA_TREND predicts (the strong early control of C1C). | "control D" |
| **D1** | (1) Week 7 dataset step D1 (`experiments.md` Table A). (2) Week 18 owner grant D1: download of the NEW monitors from Hugging Face. (3) RC23 decision D1: HA_LEAN + margin becomes the thesis learner. | give the study with it |
| **D2, D3, D4** | (1) Week 14 theorems D1–D5 (discovery certificates). (2) EA stage-1 diagnostics: D2 hyperparameter oracle, D3 linear-in-z_h emulator, D4 corner-capped margin path; D2T = trend variant. (3) RC18 "D2" curve-model question. | give the study with it |
| **E** | EL stage-2 system E: HA_LEAN selects, evidence-weighted HA_LEAN + HA_TREND mixture predicts. | "EL mixture E" |
| **H** | (1) The h-only logistic model (Phase 1.5). (2) "H codes": the last 10 hex characters of a simulation ID (`_H-xxxxxxxxxx`). **H codes are not unique** (NEW has 136 runs and 88 codes); always use the full simulation ID (ledger FIN-IDS). | — |
| **S1–S5** | (1) RC24 synthetic test families S1–S5. (2) Week 18 twins S1 / stress worlds S2. (3) IR carry rule S1–S4. | give the study with it |

## 2. Learners, from first to final

All of these are "model + acquisition" systems. Acquisition is margin (minimum |p − 0.5| over the unopened pool) unless the name says otherwise.

| System | Definition | Where fixed |
|---|---|---|
| `binary_margin` | 4-input Matérn-3/2 GPC + margin; primary thesis method after Week 8.5 | W8.5 decision ledger; claims C01–C02 |
| H | logistic regression on log h | Phase 1.5 (C20–C21) |
| M1 | physics ridge + Matérn-3/2 residual GPC | Phase 1.7 (C22) |
| M2 | frozen h logistic mean + isotropic residual GPC | Phase 1.11 (C26) |
| M3 | frozen h logistic mean + ARD Matérn-3/2 residual GPC; Track A historical control | Phase 1.13 (C28); `docs/trackA_freeze/` |
| G3 | ARD Matérn-3/2 GPC on the 4 inputs (binary-label reference of Weeks 12–20) | Phase 1.12 (C27); Week 17 |
| E1 | depth GP regression + straddle; label from the learned depth threshold | Week 18 |
| ACTIVE E1 | E1 on the active-window maximum depth A | Weeks 19–20 |
| J, J_trained | Astra's joint depth–label model (ported), trained-response variant | joint study, `CLAIMS_MATRIX.md` §1 |
| V2 | Astra's second joint model (sharing mixture over ρ) | `V2_MODEL_REPORT.md` |
| SHQ | GP emulators of the 8 physical outputs with shared ARD lengthscales and record-quality weights | RC19 (C41) |
| TRSQ | SHQ with an OLD-emulator prior mean (transfer) and quality noise for truncated records | RC18 |
| ATSCF | honest K = 10 cross-fitted classifier on predicted physical responses (depth, temperature, spike) | RC19B (C44) |
| SHQ_ATS_H | ATSCF plus the exact public coordinate log h | RC20 (C48, C55) |
| PHR_NR, PHR_NRMAP | SHQ_ATS_H whose term strengths (h trend, physical summaries) are learned from the paid labels: evidence weights over a fixed grid of configurations. PHR_NR uses the integrated Laplace predictive; PHR_NRMAP uses the same weights with each configuration's plug-in σ(m) (RC21 amendment A1) | RC21 / RC21B (C60–C62, C65) |
| HA_LR | log h + predicted depth, learned regularisation, depth from the shared upstream | RC22 (C73) |
| **HA_LEAN** | log h + predicted depth, learned regularisation; the depth GP learns from paid depths only (no temperature or flow anywhere). **Frozen reference arm** | RC23 decision D1 (C81–C84) |
| HONLY_LR | log h only, learned regularisation (control) | RC23 (C84, C88) |
| HA_TREND | HA_LEAN whose depth GP has the physics trend θ·z_h with θ ~ N(0, 3²) integrated (universal kriging); ML-II hyperparameters | RC24 (C94–C107) |
| HT_PHYS | HA_TREND predictions, h-only margin queries (decoupled) | RC24 (C97) |
| **C1** | **HA_TREND with MAP hyperparameters** under a fixed weak hyperprior: log s_f² ~ N(0, 1.5²), log ℓ_k ~ N(0, 1), log s_n² ~ N(log 0.01, 1.5²); L-BFGS-B from two fixed starts; classifier = learned-regularisation logistic on [z_h, D̂] with honest K = 10 out-of-fold stacking and the one-class rule; acquisition margin. **The recommended in-pool learner** | `src/ea_cand.py`; EA (C115–C122); C1C (C123–C130) |
| C1a, C1b | controls: the same prior on the constant-mean GP (C1a, refuted); two starts without prior (C1b) | EA |
| AVG4 | mean of C1's last 4 per-budget probabilities from b = 25 (decision-layer stabiliser) | C1S (C133–C135) |
| GATE | paid-only, support-dependent trust weight between C1 and HA_LEAN | FR (C141) |
| GEO_A1/A2, GEO_B1/B2/B3 | label-free geometric classifiers from predicted depth d and width w with the fixed boundary d/w = 1/2 | GT (C152–C153) |
| C1_G, CAL_B1, C1_T, ORACLE_T | GT controls: ratio added to C1; label-calibrated geometry; predicted early temperature added to C1; true early temperature (evaluator-only) | GT (C155–C156) |

## 3. Data and labels

| Term | Meaning | Source |
|---|---|---|
| OLD | 405 SPH simulations of `sph_v2` at revision `b6dc254a`, 73 Keyhole (from 407 experiments) | C36; Week 7 Phase 5.5 |
| NEW | 136 included SPH simulations from Ioan's later batch at revision `2e1eec9c` (185 delivered; 49 withheld because of the Bug and never used); 124 Keyhole, 12 no-Keyhole | Week 11; Week 19 audit |
| POOLED, "the pool" | OLD + NEW = **541 runs, 197 Keyhole**: the single pool of every study from RC19 on | RC19 protocol |
| `has_keyhole` | 1 if any frame has `label_final == Keyhole` (manual labels) | Week 7 Phase 1 decision |
| short-Keyhole (pooled) | `has_keyhole = 1` and 0 < frac_K_FCK < 0.10: 22 runs (the NEW-only original set has 10) | `PROTOCOL_RC19.md` |
| fast-scan corner | NEW runs with VX > 0.85: 23 runs (11 no-Keyhole, 12 Keyhole including all 10 NEW short-Keyhole) | execution studies 2026-10-15 |
| h, z_h | h = P / √(VX · LS³), LS = spot radius; units W·s^½·m⁻² (h is **not** dimensionless, C103). z_h = standardised log h | C20, C103 |
| D, D̂, A | maximum melt-pool depth (whole record); D̂ its GP prediction; A = active-window maximum depth (Week 19) | Weeks 18–19 |
| W, W_A | melt-pool width (not the beam); width at its own maximum | IR, GT (C151) |
| DT | frame interval of the monitor files, **not** the solver step; never compute timestep × DT | Week 19 audit |
| ~300 µm plateau | 134 of 197 Keyhole runs reach a depth of 300.2 µm (SD 0.7). The cause is a **hypothesis** (domain floor); no available file holds the domain z-extent | IR, GT (C150) |

## 4. Tasks, startups and repeat IDs (one pool)

Every repeat ID below is a new split or startup of **the same 541 runs**. None is external or physical validation.

| Term | Meaning |
|---|---|
| STD | seeded random split of the pool (5 folds per repeat); learners start from an 8-run maximin design and buy one run per step up to budget 60 |
| K5, K4 | geometric blocks: k-means regions of the input space (5 or 4); per-region metrics measure extrapolation |
| RAND8, LOCAL8 | random and clustered 8-run startups (startup robustness) |
| q20 flags | the 20 % of evaluation runs nearest the empirical boundary (historical q20 accuracy AULC; unchanged definition) |
| DEV / fresh | DEV = already-inspected repeats used for development; fresh = repeat IDs registered before any result and used once |
| Fresh STD ranges used | 51–58 (RC23), 59–66 (RC24 A), 67–74 (RC24 C), 75–82 (RC24 post-audit), 83–122 (EL forward), 123–162 (EL stage 2; then EA DEV), 163–202 (EA fresh), 203–282 (C1C), 283–302 / 303–322 (C1C RAND8 / LOCAL8), 323–362 (C1S), 363–372 / 373–382 (C1S startups) |
| Still unused | STD 383+, K5 49+, K4 33+ (GT registered them and stopped before using them) |

## 5. Metrics

| Metric | Definition |
|---|---|
| BA | balanced accuracy on the held-out fold at threshold 0.5 |
| BA-AULC | mean BA over the budget window: early B8–B24, late B28–B60, whole B8–B60 |
| restricted-mean saving (RMS) | difference in paid simulations to reach a BA target τ (0.90 / 0.93 / 0.95) and confirm it at b and b + 4, counting the startup runs; non-attainers get the restricted maximum |
| attain / kept / sustained | reached τ by budget 60 / was at or above τ at budget 60 / stayed at or above τ after first reaching it |
| q20 accuracy AULC | historical near-boundary metric of Weeks 8–12 (budgets 16–80) |
| NSD / ASSD | twin-world boundary distance metrics (Weeks 14–18) |
| log loss, Brier | probability quality, used as harm limits (ΔLL ≤ 0.030, ΔBrier ≤ 0.010) |
| CPU | decision CPU per step; harm limit 3× |

## 6. Evidence labels

| Label | Meaning |
|---|---|
| SUPPORTED confirmatory / exploratory, QUALIFIED, NOT SUPPORTED, PROHIBITED | status vocabulary of `docs/alse/claims.md` |
| CONFIRMED, NOT CONFIRMED, NOT_ADOPTED, SHOWN, NOT SHOWN, RELIABLE, NOT_WORSE | registered verdict words of the individual protocols (RC24, EL, EA, C1C, C1S, FR) |
| DEV | evidence from already-inspected repeats; development only |
| PRED / OBS / EXPL / POST-HOC / HYP | joint-study labels (`CLAIMS_MATRIX.md`): held-out predictions / logs and tables / exploratory with a manifest committed first / computed after seeing results / interpretation |
| DESCRIPTIVE | association or count, no model comparison (IR, GT) |
| SOURCE-TRANSFERRED | condensed from an Astra package; not recomputed by Opus |
| HYPOTHESIS | stated cause without verification (for example the 300 µm plateau) |
