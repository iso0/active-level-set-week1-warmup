# Open-items register: every open, pending or untested point, with its final status

Written on 2026-11-02 during the finalization. Every item that looked open in a record (an "untested", "pending", "next step", "hypothesis" or "not run" entry) is listed once. Each has one of these final statuses:

| Status | Meaning for the thesis |
|---|---|
| **ANSWERED** | a later study answered it; cite that study |
| **CLOSED** | a registered rule, a stop or the owner ended it; report it as recorded |
| **LIMITATION** | stays open within this data; state it in the limitations section |
| **FUTURE WORK** | needs new simulations or new data; state it in the outlook |
| **FIXED** | a record or test defect, repaired in the finalization without changing any frozen number |
| **ASK IOAN** | a fact only the supervisor or the simulation setup can supply; one question before writing |

No item remains without a status.

## 1. Scientific questions

| # | Item (where it was raised) | Final status | Where answered or stated |
|---|---|---|---|
| 1 | U1: does probability-variance acquisition beat margin with the joint model held fixed? (Stage A not executed; `CLAIMS_MATRIX.md` §4) | **ANSWERED** in the later one-pool setting with the model fixed: no selector beat margin (RC22 BALD, C75; RC24 principled straddle, C91; EL: the query path adds nothing early, C109). The joint model line itself was closed after its screens failed (F1, F6) | `CLAIMS_MATRIX.md` §11 |
| 2 | U2: does J_trained + π̂ generalise (C4 stability check)? | **CLOSED** (not run; superseded): the J line ended with failed screens, and the thesis learner comes from the one-pool programme | §11 |
| 3 | U3: query savings were not claimable from identical feature-only paths | **ANSWERED**: own-path registered designs measured savings (EL, EA; C1C restricted-mean saving to 0.95 +1.81 [+0.53, +3.09]) | C124–C125 |
| 4 | U4 and L2: what separates Keyhole from conduction inside the NEW fast-scan corner (VX > 0.85)? | **LIMITATION / FUTURE WORK**: no model resolves it (C54, C67); the label hinges on a short start-up keyhole (C93, C105). Testing it needs replicate runs inside the corner (RC24 proposal R1–R2) | `opus_rc24/PHYSICAL_DATA_PROPOSAL.md` |
| 5 | U5: does Astra's finite-batch BA rule change decisions on the frozen V2 posteriors? | **CLOSED**: frozen result PRIMARY_UNAVAILABLE; amendment A1 complete (0.858, a cutoff trade that equals the posterior-mean-π rule, not new information) | `CLAIMS_MATRIX.md` U5 |
| 6 | U6: does Astra's balanced-risk selector beat variance or balanced margin? | **CLOSED**: external and incomplete (INCOMPLETE_WITH_PRESERVED_STOPS, 72/84; no ranking or saving claim); the on-data test ASTRA_AL was stopped by the owner (P2 incomplete, not negative) | `CLAIMS_MATRIX.md` U6, E7 |
| 7 | Week 11: frozen external validation on the NEW batch | **CLOSED** as INCOMPLETE_FROZEN_STOP (no effect estimate). The 49 Bug-withheld runs were never used | `outputs/week11_external_execution_record/CONFIRMATORY_STOP_REPORT.md` |
| 8 | External validation of the final learner (C1C NEXT_ACTION) | **FUTURE WORK**: the plan (`EXTERNAL_VALIDATION_PLAN_C1C.md`, 176 runs: V1 new pool 136, R3 external anchor 16, R1 corner replicates 24) is written but was not sent or run; the owner stated that no new simulations would come before writing | C130 |
| 9 | Week 9 Phase 1.22: external blind test | **CLOSED** (stopped before Step 2: no eligible external blind pool) | `docs/phases/week9_phase1_22_external_blind_test.md` |
| 10 | Week 9 Phase 1.23: method-validity substudies | **CLOSED** as incomplete (no final report; not used as evidence) | progress log 2026-09-14 |
| 11 | Week 19: P3, the morphology fallback, C3 | P3 and the fallback **CLOSED** (never started; the line moved to the active-window target); C3 **ANSWERED** (spent in Week 20: NOT CONFIRMED) | Week 20 report |
| 12 | Week 19: Ioan's image review and his five meeting questions | **ANSWERED / superseded**: the 2026-10-15 meeting requests were answered by the 10-16 pilots and the 10-17 studies; the one request of 2026-10-30 was answered by IR and extended by GT | `STUDIES_REPORT_20261017.md`; IR, GT |
| 13 | EA NEXT_ACTION: one larger fresh replication of the 0.95 verdict | **ANSWERED** by C1C (80 fresh repeats; every registered verdict passed) | `DECISION_C1C.md` |
| 14 | C1C caveat: sustaining 0.95 not improved; 65 of 400 C1 learners lost 0.95 after reaching it | **LIMITATION**. C1S tested a stabiliser (AVG4) and it was not adopted: 81 % of the late gap is a level deficit (C132–C135) | C126, C132 |
| 15 | C1C caveat: keeping 0.95 not shown non-inferior under random / clustered startups | **LIMITATION** (the RELIABLE verdict belongs to the standard maximin startup) | C128 |
| 16 | C1 vs HA_LEAN under extrapolation (EA K5 per-region −0.049) | **LIMITATION**, design-dependent (K5 yes, K4 no). FR found no paid-only rule that recovers it: an information limit (C139–C144) | C143 |
| 17 | C1S: kept(0.95) −0.030 [−0.071] on the third fresh set | **LIMITATION** (caution beside C124) | C137 |
| 18 | The C1 prior was chosen after full-pool ML-II diagnostics | **LIMITATION** (design exposure; fresh IDs remove outcome selection, not this) | `DECISION_C1C.md` §3 |
| 19 | IR: the full sequential co-output comparison (parts D / E) | **CLOSED** by the registered stop (screen S1 failed); wording limited to "not shown in the registered screen" | C148; `IR_ADDENDUM_20261102.md` |
| 20 | IR: maximum temperature rises before the first Keyhole frame | **CLOSED**: GT tested causal early windows from the simulation start; no benefit beyond early depth (C157) | GT |
| 21 | IR / GT: the ~300 µm Keyhole depth plateau (134 of 197 Keyhole runs) | **ASK IOAN**: the cause (domain or substrate floor) stays a hypothesis because no available file holds the domain z-extent. One question settles it (§3); GT showed the geometric loss does not come from the plateau | C150 |
| 22 | GT: own-path (G3) and fresh (G4) stages | **CLOSED** by the registered promising rule (GEO_B1 −0.0174); fresh IDs STD 383+, K5 49+, K4 33+ stay unused | `FINAL_REPORT_GT.md` |
| 23 | GT: QT-B validation half | **CLOSED** (benefit rule failed on DEV; half kept closed) | C157 |
| 24 | RC24 synthetic families: S1, S4 not supported as registered; S5 not observed | **CLOSED** as recorded (C99) | `FINAL_REPORT_RC24.md` |
| 25 | RC24 propositions: h "dimensionless"; P2 "wrong anchor asymptotically harmless" | **FIXED** at the time by dated corrections (C103 withdrawn, C104 withdrawn) | `docs/alse/claims.md` |
| 26 | Joint study L12: temporal SVGP fits are not bitwise reproducible across worker histories | **LIMITATION** (unseeded torch RNG; the temporal models were not used for any decision) | `CLAIMS_MATRIX.md` L12 |
| 27 | Week 18 "time-step rule" wording | **FIXED** at the time (Week 19 `TIMESTEP_DT_USAGE_AUDIT.md`: no earlier week used timestep × DT as time) | Week 19 pilot folder |

## 2. Record, test and repository items

| # | Item | Final status | Where |
|---|---|---|---|
| 28 | `test_t_tobit_truth_is_the_frozen_phase2_truth` failed (GT guessed "library versions") | **FIXED**: the frozen truth is reproduced exactly with the default 8 OpenBLAS threads (max \|Δθ\| 4.4e-7), not with 1 (0.26) or 4 (0.058). The GT runs had BLAS = 1. The test now pins 8 threads; the frozen values are unchanged | central ledger FIN-TOBIT; `src/tests/test_week18_twin_truth_frozen.py` |
| 29 | `test_reports_use_full_simulation_ids` failed (bare H suffixes) | **FIXED**: 10 historical lines (not only the 2 GT listed) are resolved to full IDs by the dated ledger row FIN-IDS. The earlier QC-REC-ERRATUM (2026-10-18) already recorded the wrong-run check; an independent re-read of the raw monitors agrees with it. The test exempts exactly these lines and requires FIN-IDS | central ledger FIN-IDS |
| 30 | 38 legacy failures in the Week 8.5–9 tests of the full suite | **CLOSED as known legacy**: historical-integrity checks against the old layouts (git diffs against Week 9 start SHAs, the old `tests/` folder, notebook re-execution, ignored checkpoint folders); identical on the IR base 0a57d644; not changed (historical tests are not edited to pass) | `opus_geometry_temperature/regression/FULL_SUITE_NOTE.md` |
| 31 | Running the legacy suite rewrites 3 tracked Week 9 outputs and downloads 3 public Masinelli files | **Known; documented**: run the legacy suite only in a scratch worktree, and restore with `git restore`. The Weeks 12+ suite is the regression gate | REPOSITORY_MAP §6 |
| 32 | `main` (Research Hub, 2026-10-28) lacked C1S, FR, IR and GT; ten study branches | **FIXED**: the finalization branch merged `main`; `main` now holds everything; Hub files kept byte-identical (they are SHA-256-locked) and marked as a dated layer up to C1C | REPOSITORY_MAP §1 |
| 33 | About 3 GB of raw unit outputs existed only in this worktree (not in git) | **FIXED**: copied with a SHA-256 manifest to `Documents\thesis_archive\worktree_raw_outputs_20261102\` (18,972 files; 0 conflicts); originals untouched | REPOSITORY_MAP §4 |
| 34 | Many thesis folders on the computer (worktrees and staging copies) | **FIXED / documented**: map of every folder; nothing deleted; an optional, logged archive step is provided | REPOSITORY_MAP §3 |
| 35 | The decision log, experiment index and progress log had no rows for Week 10 → RC18 | **FIXED**: dated rows and entries added (2026-11-02), each pointing to its report | `docs/alse/decisions.md`, `experiments.md`, `docs/thesis_progress_log.md` |
| 36 | The claims ledger has no rows for Weeks 10–20, the joint study and RC18 (their claims are in the study ledgers) | **FIXED** by a pointer addendum and by CLAIMS_FOR_THESIS.md | `docs/alse/claims.md` addendum 2026-11-02 |
| 37 | C1C, EA and C1S have tables but no figures | **FIXED**: three figures drawn from the frozen C1C exports, checked against the reported numbers | `docs/final/figures/` |
| 38 | Stale "live" runner status files (`runner/STATUS.md` with "remaining … h") | **Known**: snapshots at closure; every study STATE and coordination record says CLOSED | REPOSITORY_MAP §5 |

## 3. Questions for Ioan before or during writing

These are the only points that need someone else. None blocks writing.

1. **Domain depth.** What is the z-extent of the SPH domain or the substrate thickness? Is 300 µm the floor of the simulated domain? This turns item 21 from a hypothesis into a fact.
2. **External runs (optional, for the outlook).** Would a small new batch be possible after the thesis, per `EXTERNAL_VALIDATION_PLAN_C1C.md`? A minimal version is V1 + R3, 152 runs; adding the R1 corner replicates gives 176. Nothing has been sent.
3. **The 49 Bug-withheld NEW runs.** Did the Bug change their physics or only their bookkeeping? If they are valid, they are the one untouched set that could serve as a small external check. They stay unused until he answers.
