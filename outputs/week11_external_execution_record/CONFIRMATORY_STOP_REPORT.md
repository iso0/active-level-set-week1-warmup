# Frozen external validation: confirmatory STOP report

Status: **CONFIRMATORY ATTEMPT CLOSED — INCOMPLETE FROZEN STOP.**
Date: 2026-10-02. This report closes the prescribed confirmatory attempt before any separate post-hoc investigation. The experiment was not completed, and no confirmatory method comparison is estimable.

## Repository and pre-oracle gates

Canonical local and remote `main` were verified at `ed491faa08782bcb9db42ac4bbc031bd2e32457f` before execution. The four Week 11 commits were preserved by fast-forward, with the original seal commit `e0adbc28b6368ee6366c6dcd7d500632c7b5f8f1` reachable. Separate records preserve all previous branch tips and 16 previously unarchived historical stash artifacts. Only `main` remains as a local or remote development branch; historical worktrees and both stashes remain available.

Freeze SHA-256 remains `856219763ec41ba22eb13ebb5c23e2137fb3d6eb884de71a44f96d80debe1eee`. The locked execution gate checked committed freeze/source ancestry, source hashes, the exact `.venv` environment, manifest identity, folds and unused output paths before verifying and opening the sealed oracle. Oracle identity remains filename `NEW185_SEALED_ORACLE.csv`, size 28608 bytes, SHA-256 `cdd338fb76148a02f98b7353102424df481a6a709bc4048730c5e0c50adb7d35`. It was opened only by the locked pathway. No withheld physical outcomes were reported or used in execution or this report.

## Data and unchanged design

Source: `ioandanielc/sph_v2@2e1eec9c98fd57609d2815f174586336ab59da07`. Of 185 genuinely new simulations, 136 were included and 49 remain `WITHHELD_DUE_TO_BUG_FOR_EXTERNAL_VALIDATION`. Independence is an explicit owner statement; the simulator version is `SIMULATOR_VERSION_NOT_SEPARATELY_DOCUMENTED`, accepted by the owner before labels.

The included cohort contains **124 Keyhole and 12 non-Keyhole simulations** (91.18% and 8.82%), obtained by deduplicating consistent included-ID truth in already saved held-out predictions. All 136 included IDs appear there; the sealed oracle was not reopened for this summary. Non-Keyhole is the binary target complement, not a reassignment of Bug to Conduction.

The committed design remains 20 repeats x 5 folds, seeds 1101–1120, training complements 108–109, and every integer budget B16–B80. Arms remain M3-margin, Candidate B (`early8__coverage_then_margin_B40`) and same-B16 Candidate A (`coverage_then_margin_B40`). The M3 evaluator is common to all three. q20 accuracy normalized AULC B16–B80 remains the primary endpoint; q30 remains secondary.

| Input (canonical units) | OLD-405 min / median / max | Included NEW-136 min / median / max |
|---|---|---|
| P (W) | 52.545 / 193.441 / 449.762 | 350.033 / 387.079 / 449.849 |
| VX (m/s) | 0.2010 / 0.6358 / 0.9983 | 0.2093 / 0.4686 / 0.9855 |
| LS (m) | 4.0029e-5 / 6.2163e-5 / 8.9704e-5 | 4.0003e-5 / 4.4679e-5 / 4.9947e-5 |
| ST (K) | 300.000 / 349.298 / 399.818 | 301.610 / 397.461 / 499.769 |

Sources are the included manifest and `reference_manifests/OLD405_LABEL_FREE.csv`. Bug withholding changes the observed input distribution: withheld VX median is 0.816523 versus included 0.468615, a difference of 0.347908 m/s. These are cohort descriptions, not estimates of a causal Bug effect.

## What happened

The exact locked command ran from 2026-10-02 14:52:36 UTC to 14:56:15 UTC and exited with the prescribed STOP at `external__r003_f04`, before the incumbent arm could start:

> B16 frozen feature-only design lacks both classes; STOP, do not reseed or extend

Thirteen paired folds completed: all five folds in repeats 1 and 2, then folds 1–3 in repeat 3. Preserved artifacts contain 39 complete arm paths, 3120 query records, 2535 split-arm-budget groups, 69030 held-out prediction rows, 2638 fit diagnostics and 103 logged fallback events. All 103 are the frozen `empty_band_margin_fallback`: 81 in Candidate B, 22 in Candidate A, and none in the incumbent; no optimizer fallback is logged. These are prescribed selection fallbacks, not the fatal STOP. All 100 planned folds remain in the split manifest; this does not mean they all executed. The remaining 87 folds and 261 arm paths were not completed. Failures and incomplete coverage are not dropped.

This is a frozen initialization feasibility failure, not an unexpected code exception to repair. B80 pool-size feasibility was satisfied, but that label-free fact cannot guarantee that a fixed feature-only B16 design observes both outcome classes. No alternative seed, extra initial query, class-conditioned initialization, exclusion change, budget change or technical repair was attempted.

## Confirmatory results and decisions

| Required result | Status |
|---|---|
| Candidate B minus M3 primary mean / 95% interval / positive repeats | NOT ESTIMABLE: incomplete frozen run |
| B40 q20 Keyhole-recall guardrail | NOT EVALUATED |
| B80 full-test accuracy guardrail | NOT EVALUATED |
| External confirmation | NOT ESTABLISHED; no valid pass/fail effect test |
| Incumbent replacement | NOT ESTABLISHED; incumbent retained |
| Candidate A minus M3 primary contrast / pure acquisition claim | NOT ESTABLISHED; contrast not estimated |
| Frozen secondary endpoints, q30 robustness, crossings | NOT CALCULATED |

No endpoint or interval was computed from the 13 completed folds or the two complete repeat blocks. Such a subset was not the frozen 20-repeat experiment. Absence of confirmation is not evidence that Candidate B underperforms M3. Incumbent retention is the unchanged prior decision, not an observed win on the new campaign. The locked analysis intentionally wrote none of its eight success-only analysis artifacts. Partial predictions are preserved for reproducibility, not presented as confirmatory scores.

## Historical comparison and limitations

The canonical OLD-405 result in `docs/trackA_freeze/TRACK_A_FREEZE.json` is Candidate B minus M3 = +0.0067080269607842965, 95% interval [+0.004774777879901932, +0.008632084865196085], 54/60 positive repeats. Candidate A minus M3 = +0.0031709558823529087, interval [+0.0016712622549019446, +0.004759497549019562], 42/60 positive repeats. There is no completed external effect size with which to compare these, and old and new observations are not pooled.

Any valid future analysis of these outcomes concerns the 136 Bug-cleared simulations, not the complete 185 delivery or the 49 withheld cases. The 20 repetitions are partitions of one independent new campaign, not 20 independent external datasets; their intended interval describes partition variation conditional on this cohort. All three arms share M3, so this design alone cannot establish M3's advantage over a non-physics model or direct transfer of an OLD-405-trained model.

The included outcomes are now open. A revised initialization rule developed after this STOP would be post-hoc development on this cohort and would need a future independent cohort for fresh external confirmation. No change to the frozen conclusion is permitted.

## Audit boundary

Independent artifact checks are complete: `QC_VALIDATION.json` and `QC_SUMMARY.md` report forensic PASS with the scientific status INCOMPLETE_FROZEN_STOP. Five focused checker tests passed. The full manifest digest, included-ID ordering, all 100 split assignments, all 13 completed feature-only B16 designs, and Candidate B early8/extension prefixes match their frozen bindings. The failed B16 is independently reproduced from saved included-cohort prediction truth. All 120 frozen source-file hashes remain unchanged. This report does not compute exploratory metrics. A separate post-hoc record may examine why fixed B16 class coverage failed, using only these already authorized included outcomes; it cannot reopen the confirmatory experiment.
