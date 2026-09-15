# Week 9 Phase 1.21 — simplification and clean replication

## Verdict

**The improvement is an early boundary-coverage effect, and it replicated on untouched partitions.**

- Both simplified rules beat M3 margin on both pre-registered windows (all four Holm-adjusted p <= 0.0004, all CIs above zero, guardrails met): A REPLICATED = True, B REPLICATED = True.
- With the early start (Candidate B) the late misfit component is unnecessary: B minus old early8+CCM on 16-80 = -0.0003 [-0.0009, +0.0002], non-inferior at the frozen margin 0.0010 (pre-registered verdict `COVERAGE_SUFFICIENT`). This is outcome A of the Phase 1.21 brief.
- With the frozen seed (Candidate A) the simple rule keeps all of CCM's 16-40 gain (identical queries up to B40 in 300/300 runs) and 84% of its 16-80 gain. The remainder, A minus CCM = -0.0006 [-0.0012, +0.0000] on 16-80 (sign-flip p 0.058), is neither shown non-inferior at the 0.0010 margin nor significant (pre-registered verdict `COVERAGE_WORKS_NONINFERIORITY_INCONCLUSIVE`). This is outcome B of the brief: the necessary part is the early coverage; the late misfit component adds at most about 0.001 AULC with the frozen seed, which this replication cannot resolve.

Data: repeats 61-120 of the frozen split generator, 60 repeat blocks, 300 outer cross-validation runs per policy. These are **untouched internal replication partitions** of the same 405-simulation population. They are not 300 independent simulations, not new simulations and not external data. Runs share simulations, which is why every test uses the repeat block as its unit.

## 1. Summary

- Candidate A vs margin: AULC 16-80 +0.0032 [+0.0017, +0.0048], AULC 16-40 +0.0071 [+0.0038, +0.0106]; 42/60 and 43/60 blocks positive.
- Candidate B vs margin: AULC 16-80 +0.0067 [+0.0048, +0.0086], AULC 16-40 +0.0138 [+0.0099, +0.0178]; 54/60 and 53/60 blocks positive.
- The effect sizes agree with the earlier phases: CCM vs margin was +0.0023 / +0.0055 on repeats 11-60 and is +0.0038 / +0.0071 here; Candidate A (screened as sched_bmm_B40) was +0.0022 / +0.0067 on development repeats 1-10.
- Misfit component: B minus early8+CCM -0.0003 [-0.0009, +0.0002] (non-inferior); A minus CCM -0.0006 [-0.0012, +0.0000] (inconclusive; the gap sits in 41-80: -0.0009 [-0.0019, +0.0000]).
- Sample efficiency (mean curves, descriptive): margin's B40 q20 accuracy (0.8384) is reached at B28 by A and B26 by B, i.e. 12 and 14 fewer simulations.
- By B80 the rules converge: full81 accuracy change +0.0001 (A) and +0.0005 (B); A's final 80 queried simulations equal margin's in 211/300 runs. Coverage changes the order of the boundary queries, not the final set.
- Relative to the empirical all-label M3 reference on these partitions (q20 accuracy 0.8551), B's gain uses 48% of the observed 16-80 headroom (0.0140) and A's 23%.
- Repeats 61-120 were verified untouched: 104,165 files in 10 locations plus 83 git refs and the stash; highest repeat ever used = 60. Leakage audit: 120 states, 0 changes when every unqueried label and depth was scrambled.

## 2. Pre-registration

`PHASE1_21_PREREGISTERED_PROTOCOL.json`, frozen 2026-09-13T19:03:29.780115+00:00 (sha256 3fe51aa103213c89), before any replication run (replication checkpoints existing at freeze: []). The first replication checkpoint was written at 19:05:03 UTC. The protocol fixes the hypothesis, one control, two candidates, two descriptive references, every parameter, the repeat range, the endpoints, the estimators, Holm over 4 tests, guardrails, the replication rule, the non-inferiority margins, the numerical environment and the sha256 of all code involved. The analysis re-reads the protocol and refuses to run if its constants differ.

## 3. Untouched repeat audit

| location | files scanned | files with run ids | repeats found | files > 20 | files > 60 |
|---|---|---|---|---|---|
| thesis_1 | 9,920 | 5,481 | [1, 60] | 600 | 0 |
| thesis_work_chatgpt | 5,103 | 912 | [1, 20] | 0 | 0 |
| lean_thesis | 126 | 13 | [1, 20] | 0 | 0 |
| documents_main_repo_worktree | 23,113 | 226 | [1, 20] | 0 | 0 |
| documents_week4 | 561 | 0 | None | 0 | 0 |
| documents_week5 | 41,028 | 0 | None | 0 | 0 |
| documents_week9_18b | 4,432 | 353 | [1, 20] | 0 | 0 |
| documents_week9_19a | 5,073 | 776 | [1, 20] | 0 | 0 |
| gemini_antigravity | 14,611 | 506 | [1, 20] | 0 | 0 |
| session_scratchpad | 198 | 1 | [1, 10] | 0 | 0 |

Git (C:\Users\ozgur\Documents\thesis): 83 refs and 4 stash commits; file names with repeat >= 21: 0; text files with repeat >= 21: 0; the only explicit `build_splits(repeats=...)` call is the synthetic-data smoke-test fixture: ['src/week8_5_frozen_sample_efficiency_confirmation.py:763:    specs = build_splits(frame, repeats=2, folds=2)'].
Read errors: 22 (joblib's own test fixtures inside `.venv` that are not gzip despite the extension, and two Office `~$` lock files).
Repeats 1-20: frozen Week 8.5 splits, used by every earlier phase; Phase 1.20 developed on 1-10 and confirmed on 11-60. Repeats 21-60: used only by that Phase 1.20 confirmation. Repeats 61-120: never used before this phase.

## 4. Replication results (pre-registered tests)

| rule | window | margin AULC | rule AULC | difference [95% CI] | blocks positive | sign-flip p | Holm p |
|---|---|---|---|---|---|---|---|
| A: coverage -> margin | 16-80 | 0.8411 | 0.8442 | +0.0032 [+0.0017, +0.0048] | 42/60 | 0.0001 | 0.0004 |
| A: coverage -> margin | 16-40 | 0.8239 | 0.8309 | +0.0071 [+0.0038, +0.0106] | 43/60 | 0.0002 | 0.0004 |
| B: 8 maximin + coverage -> margin | 16-80 | 0.8411 | 0.8478 | +0.0067 [+0.0048, +0.0086] | 54/60 | 0.0001 | 0.0004 |
| B: 8 maximin + coverage -> margin | 16-40 | 0.8239 | 0.8377 | +0.0138 [+0.0099, +0.0178] | 53/60 | 0.0001 | 0.0004 |

| rule | B40 q20 Keyhole recall change (>= -0.03) | B80 full81 accuracy change (>= -0.01) | REPLICATED |
|---|---|---|---|
| A: coverage -> margin | -0.0034 | +0.0001 | True |
| B: 8 maximin + coverage -> margin | +0.0101 | +0.0005 | True |

Descriptive references against margin on the same partitions:

| reference | AULC 16-80 | AULC 16-40 |
|---|---|---|
| old CCM (reference) | +0.0038 [+0.0021, +0.0054] | +0.0071 [+0.0037, +0.0106] |
| old early8 + CCM (reference) | +0.0070 [+0.0050, +0.0091] | +0.0138 [+0.0098, +0.0178] |

## 5. Is the late misfit component needed?

| comparison | window | difference [95% CI] | sign-flip p | non-inferiority margin | non-inferior |
|---|---|---|---|---|---|
| A: coverage -> margin minus old CCM (reference) | 16-80 | -0.0006 [-0.0012, +0.0000] | 0.058 | 0.001 | False |
| A: coverage -> margin minus old CCM (reference) | 16-40 | +0.0000 [+0.0000, +0.0000] | 1.000 | 0.0025 | True |
| A: coverage -> margin minus old CCM (reference) | 41-80 | -0.0009 [-0.0019, +0.0000] | 0.063 | - | - |
| B: 8 maximin + coverage -> margin minus old early8 + CCM (reference) | 16-80 | -0.0003 [-0.0009, +0.0002] | 0.256 | 0.001 | True |
| B: 8 maximin + coverage -> margin minus old early8 + CCM (reference) | 16-40 | +0.0000 [+0.0000, +0.0000] | 1.000 | 0.0025 | True |
| B: 8 maximin + coverage -> margin minus old early8 + CCM (reference) | 41-80 | -0.0005 [-0.0014, +0.0004] | 0.288 | - | - |

16-40 is exactly zero by construction: each candidate and its CCM reference share the first 40 queries in 300/300 (A) and 300/300 (B) runs (`shared_prefix_check.json`). The informative comparison is 16-80, driven by 41-80.
Pre-registered verdicts: A `COVERAGE_WORKS_NONINFERIORITY_INCONCLUSIVE`, B `COVERAGE_SUFFICIENT`. The late component changes plain margin's choice in 76% of late steps, yet CCM's final 80-point set still overlaps margin's by Jaccard 0.93; its effect on accuracy is small.

## 6. Learning curves and paired differences

`figures/01_learning_curves.png` — mean q20 accuracy by budget for margin, the simple rule and old CCM (left: frozen seed; right: early start). `figures/02_paired_differences.png` — per-budget differences with 95% repeat-block bands, and simple minus old CCM.

What the curves show: the gain is built before B40. With the frozen seed the coverage rule first costs a little (B19: -0.0080) and overtakes margin from B20; with the early start the active steps begin before B16, so the curve is ahead from B16. After B40 all curves converge: B80 q20 accuracy 0.8559 (margin), 0.8563 (A), 0.8578 (B).

## 7. Secondary endpoints (difference vs margin, 95% CI)

| endpoint | A: coverage -> margin | B: 8 maximin + coverage -> margin | old CCM (reference) | old early8 + CCM (reference) |
|---|---|---|---|---|
| AULC 41-80 q20 accuracy | +0.0006 [-0.0004, +0.0016] | +0.0022 [+0.0007, +0.0037] | +0.0016 [+0.0003, +0.0029] | +0.0027 [+0.0010, +0.0044] |
| q30 accuracy AULC 16-80 | +0.0024 [+0.0013, +0.0037] | +0.0059 [+0.0044, +0.0073] | +0.0031 [+0.0019, +0.0043] | +0.0063 [+0.0048, +0.0077] |
| q20 balanced accuracy AULC 16-80 | +0.0025 [+0.0009, +0.0043] | +0.0061 [+0.0039, +0.0082] | +0.0026 [+0.0007, +0.0046] | +0.0061 [+0.0038, +0.0085] |
| q20 Keyhole recall AULC 16-80 | +0.0002 [-0.0033, +0.0039] | +0.0033 [-0.0013, +0.0077] | -0.0013 [-0.0053, +0.0027] | +0.0027 [-0.0018, +0.0073] |
| full81 accuracy AULC 16-80 | +0.0008 [+0.0004, +0.0012] | +0.0021 [+0.0016, +0.0026] | +0.0009 [+0.0005, +0.0014] | +0.0022 [+0.0017, +0.0027] |
| B40 q20 Keyhole recall change | -0.0034 | +0.0101 | -0.0034 | +0.0101 |
| B80 full81 accuracy change | +0.0001 | +0.0005 | +0.0004 | +0.0006 |

## 8. Simulations saved (mean curves, descriptive)

| margin budget | margin q20 accuracy | A: coverage -> margin: first budget reaching it (saved, % fewer) | B: 8 maximin + coverage -> margin: first budget reaching it (saved, % fewer) | old CCM (reference): first budget reaching it (saved, % fewer) | old early8 + CCM (reference): first budget reaching it (saved, % fewer) |
|---|---|---|---|---|---|
| B24 | 0.8202 | B22 (2, 8.3%) | B17 (7, 29.2%) | B22 (2, 8.3%) | B17 (7, 29.2%) |
| B32 | 0.8298 | B24 (8, 25.0%) | B23 (9, 28.1%) | B24 (8, 25.0%) | B23 (9, 28.1%) |
| B40 | 0.8384 | B28 (12, 30.0%) | B26 (14, 35.0%) | B28 (12, 30.0%) | B26 (14, 35.0%) |
| B60 | 0.8529 | B59 (1, 1.7%) | B52 (8, 13.3%) | B57 (3, 5.0%) | B42 (18, 30.0%) |

A single crossing of two mean curves is noisy (see B60), so these numbers illustrate the AULC result; they are not a separate test.

## 9. Mechanism (post-hoc, explanatory only)

None of these quantities enters the pre-registered verdict. `figures/03_mechanism.png`.

| budgets | rule | mean q20 false positives per run | mean q20 false negatives per run |
|---|---|---|---|
| 16-40 | M3 margin | 1.187 | 1.816 |
| 16-40 | A: coverage -> margin | 1.084 | 1.799 |
| 16-40 | B: 8 maximin + coverage -> margin | 0.993 | 1.770 |
| 41-80 | M3 margin | 0.798 | 1.725 |
| 41-80 | A: coverage -> margin | 0.783 | 1.728 |
| 41-80 | B: 8 maximin + coverage -> margin | 0.771 | 1.712 |
| all 324 labels | empirical all-label M3 reference | 0.647 | 1.817 |

In the evaluated regime, false negatives remained approximately stable (about 1.7-1.8 per run from B20 to B80, and 1.82 even with all 324 labels) while most observed learning gains came from reducing false positives. Over B16-40, compared with margin, A has 0.103 fewer false positives and 0.017 fewer false negatives per run; B has 0.194 and 0.046.

| quantity | M3 margin | A: coverage -> margin | old CCM (reference) | B: 8 maximin + coverage -> margin | old early8 + CCM (reference) |
|---|---|---|---|---|---|
| runs still separable in log h, B16 | 0.497 | 0.497 | 0.497 | 0.090 | 0.090 |
| same, B20 | 0.377 | 0.273 | 0.273 | 0.013 | 0.013 |
| same, B24 | 0.077 | 0.027 | 0.027 | 0.013 | 0.013 |
| mean nearest-neighbour distance of queried points, B24 | 1.484 | 1.586 | 1.586 | 1.231 | 1.231 |
| same, B40 | 1.023 | 1.104 | 1.104 | 0.906 | 0.906 |
| B16-39 queries inside the estimated band | 0.867 | 0.947 | 0.947 | 0.877 | 0.877 |
| B16-39 steps choosing a different row than margin would | 0.000 | 0.763 | 0.763 | 0.715 | 0.715 |
| B40-79 steps choosing a different row than margin would | 0.000 | 0.000 | 0.765 | 0.000 | 0.754 |
| query-set Jaccard with margin's own path, B40 | 1.000 | 0.703 | 0.703 | 0.549 | 0.549 |
| same, B80 | 1.000 | 0.982 | 0.930 | 0.853 | 0.833 |

Reading: margin keeps querying where the two classes are already bracketed, so 50% of the frozen-seed runs are still perfectly separable in log h at B16 and 38% at B20. The coverage rule spreads queries along the label-estimated band (larger nearest-neighbour distances at B24/B40, flatter position histogram). This breaks separability sooner (27% at B20) and removes early false positives. Starting after 8 maximin points gets the same effect even earlier (9% separable at B16).

## 10. Leakage / invariance audit

`invariance_audit.json`, status PASS: 120 development states (repeats 1-10 only) covering {'coverage (16-39)': 48, 'early-start seed/active (<16)': 32, 'margin (40-79)': 40}. Every unqueried label and depth was replaced by random values; M3 probabilities and the chosen row were identical in every state (mismatches 0). Static check that the policy code reads no unmasked array: True. Policies receive only masked label/depth arrays, test rows are never candidates, and B1 distances are computed for evaluation only.

Other gates: the extended split generator reproduces the frozen 100 runs and the 300 runs of Phase 1.20 bit-identically (`gate_splits.json`). The runner reproduced 10 of 11 Phase 1.20 trajectories bit-identically. The 11th came from a multi-threaded smoke test that diverged at a near-tie, and it was reproduced exactly under multi-threaded BLAS (`gate_runner_equivalence_addendum.json`). Every replication run used single-thread BLAS, as frozen.

## 11. What we can claim in the thesis

1. On this 405-simulation population, with M3 as the evaluator, a two-phase acquisition rule — until B40, uncertainty plus coverage inside the log-h band estimated from queried labels; from B40, plain margin — improves Fold-B1-q20 accuracy AULC over M3 margin. The gain is +0.0032 (16-80) and +0.0071 (16-40) with the frozen seed, and +0.0067 / +0.0138 with an 8-point maximin start. This was found in development (repeats 1-10), confirmed internally (repeats 11-60, CCM form) and replicated under pre-registration on 60 previously unused repeat blocks (61-120).
2. The improvement is an early boundary-coverage effect: it is built before B40, and the late misfit-avoidance component is not needed with the early start (non-inferior).
3. Descriptively, margin's B40 accuracy is reached 12-14 simulations earlier.
4. The gain costs nothing at the end: B80 full81 accuracy is unchanged (+0.0001 A, +0.0005 B) and B40 q20 Keyhole recall stays within the guardrail (-0.0034 A, +0.0101 B).
5. Improvement relative to the empirical all-label M3 reference (0.8551 on these partitions) leaves only 0.0140 observed headroom on 16-80; B's gain covers 48% of it and A's 23%.
6. The acquisition is label-blind as audited: scrambling all unqueried labels and depths changes nothing.

## 12. What we cannot claim

1. External validity. Repeats 61-120 are untouched internal replication partitions of the same 405 simulations, not new simulations, not another simulator setting and not experimental data.
2. That 300 runs are 300 independent experiments. They share simulations; the effective unit is the repeat block, and even blocks are not independent samples from a wider population.
3. That Candidate B's gain is pure acquisition. B also changes the initial design (8 instead of 16 seed points). The pure acquisition effect is Candidate A's.
4. That the misfit component is useless in general. With the frozen seed its contribution is unresolved (-0.0006 [-0.0012, +0.0000] on 16-80).
5. Any gain in final accuracy at B80, or a Keyhole-recall gain (not significant).
6. A theoretical ceiling or a maximum possible improvement. At B80 all three rules already match or slightly exceed the empirical all-label reference (q20 accuracy 0.8559-0.8578 vs 0.8551).
7. That the parameters (pad 0.25, switch B40, equal weights, 4D x) are optimal. They were never tuned in this phase.
8. A causal mechanism. The separability, coverage and false-positive analyses are post-hoc explanations, not tested hypotheses.
9. Anything about other evaluators (only M3 was used) or other boundary definitions (only Fold-B1 q20/q30 and full81).

## 13. Five sentences for Ioan

1. We simplified the Phase 1.20 acquisition rule: from B16 to B39 it queries points that are uncertain under M3 and far from already-queried points, restricted to the log-h band where queried Conduction and Keyhole labels meet; from B40 it is plain M3 margin.
2. Before running anything we pre-registered the rule, parameters, endpoints and tests, and audited every copy of the project to confirm that outer-CV repeats 61-120 had never been used — fresh partitions of the same 405 simulations, not new data.
3. On these 60 repeat blocks the rule beat margin on Fold-B1-q20 accuracy AULC 16-80 by +0.0032 (95% CI +0.0017 to +0.0048) with the frozen seed and by +0.0067 (+0.0048 to +0.0086) when active learning starts after 8 maximin points; all four Holm-adjusted p <= 0.0004, with no guardrail violations.
4. The gain is an early boundary-coverage effect: it is built before B40, reaches margin's B40 accuracy 12-14 simulations earlier, and the late misfit-avoidance part of the earlier rule is unnecessary with the early start and adds at most about 0.001 AULC with the frozen seed.
5. The rule is now frozen, and the next step would be a pre-registered blind test on a genuinely external simulation pool, which we have not opened.

## 14. Final policy freeze and external blind test

`FINAL_POLICY_FREEZE.json` (2026-09-13T20:30:49.090434+00:00): final policy `early8__coverage_then_margin_B40`, with `coverage_then_margin_B40` as its pure-acquisition companion and M3 margin as control; code sha256 recorded. No external pool has been opened, read or computed on.

## 15. Wording errata for Phase 1.20

`PHASE1_20_WORDING_ERRATA.md`: "ceiling" becomes "empirical all-label M3 reference"; "reducible-error budget" becomes "observed headroom"; "only false positives are reducible" becomes the regime-specific statement; "250 runs" becomes "250 outer cross-validation runs of the same 405 simulations". Historical files unchanged.

## Files

`src/week9_phase1_21_*.py` (repeat_audit, repeat_audit_driver, simplification_replication, invariance_audit, freeze, analysis, figures, all_label_reference, report). Outputs in this folder: protocol, audit, gates, checkpoints/ (5 x 300), REPLICATION_RESULT.json, mechanism_*.csv, all_label_reference*.{json,csv}, shared_prefix_check.json, figures/.
