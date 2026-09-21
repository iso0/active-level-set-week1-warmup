# Week 10 Track A — Phase 1.21 comparator audit

## Executive verdict

- Candidate A vs current M3-margin (known matched B16 result): +0.003171 [+0.001671, +0.004759].
- Coverage effect with the early-8 start held fixed: +0.001939 [+0.000458, +0.003402], positive repeats 37/60, Holm p=0.0262197.
- Candidate A vs live recreation of historical Binary-A0: +0.002990 [+0.000590, +0.005434], positive repeats 35/60, Holm p=0.0262197.
- Practical incumbent replacement at +0.01: FAIL.
- Incumbent remains M3-margin B16; Candidate B remains the one frozen external challenger.
- These are internal OLD-405 results, not external validation.

## What was tested

Candidate A and the current M3-margin incumbent share the frozen B16 start, so their difference is a pure acquisition comparison. Candidate B was compared with a new early8__margin control that shares the identical early-start rule, isolating coverage. Candidate A was also compared with the frozen Week 8.5 Binary-GPC margin policy recreated live on the same repeats; every path was evaluated by M3.

## Primary results

| Contrast | q20 accuracy AULC B16-B80 | Statistical superiority | Practical replacement |
|---|---:|---:|---:|
| Candidate B - early8 margin | +0.001939 [+0.000458,+0.003402] | PASS | FAIL |
| Candidate A - historical Binary-A0 live | +0.002990 [+0.000590,+0.005434] | PASS | FAIL |

## Acquisition decomposition

- Coverage contribution given early start: +0.001939.
- Early-start contribution under margin: +0.004769.
- Total Candidate B minus M3-margin: +0.006708.
- Algebraic closure error: 0.000e+00.

The early-start margin component accounts for about 71% of the mean total contrast and coverage conditional on that start about 29%. This is an algebraic attribution on the same runs, not a causal percentage claim.

## Important caveats

- The two new q20 balanced-accuracy B16–B80 effects are unresolved: Candidate B minus early8 margin `+0.001290 [-0.000396,+0.002930]`; Candidate A minus historical A0 `+0.001296 [-0.001514,+0.004011]`. The positive conclusion is specific to the frozen primary q20 accuracy endpoint.
- Candidate A versus historical A0 compares complete acquisition systems: M3 probabilities plus coverage versus isotropic Binary-GPC probabilities plus margin. It is a fair policy comparison under the same B16 and M3 evaluator, but it does not isolate only one formula component.
- In the 19,500 M3 fits used to evaluate live A0 paths, 1,376 had a non-convergence flag and none used fallback. This qualifies the exact frozen implementation comparison but does not selectively favor one evaluator, because M3 and its settings are identical across arms.
- The audit is post-result attribution on the same 405 simulations. It is not a new independent confirmation.

## Plain-language interpretation

Phase 1.21 does not replace the M3 model; it uses M3 and changes only which simulation is queried. A statistically positive difference therefore means a better query order on this fixed population. Replacement still requires a gain of at least +0.01 over the full primary window, plus the frozen guardrails. Even a passing internal comparison cannot establish performance on Ioan's future independent batch.

## Evidence files

- `AUDIT_PROTOCOL.json` and `EXECUTION_FREEZE.json`
- `preflight_validation.json` and `a0_recreation_parity.json`
- `repeat_block_contrasts.csv`
- `effect_decomposition.json`
- `query_path_overlap.csv`
