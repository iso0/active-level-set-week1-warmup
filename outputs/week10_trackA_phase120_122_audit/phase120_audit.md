# Phase 1.20 independent audit

## Verdict

**PASS_WITH_CAVEATS**

The stored comparison is scientifically usable. The caveat concerns numerical optimization diagnostics, not leakage or protocol integrity.

## What was tested, and why

P1 lets M3 choose the next simulation by M3 probability margin. P2 lets the separate G3 classifier choose by G3 probability margin, while the unchanged M3 model still evaluates both paths. This isolates acquisition-path value from predictive-model value: a model can predict well without choosing the best next data point.

## Design audit

- Exact branch: `codex/week9-phase1-20-m3-g3-margin-acquisition`.
- Local and origin SHA: `49a054e3f80b8601fcb175826d54d71519f2813a`.
- Frozen population: 405 rows, 73 Keyhole, 332 Conduction; inputs P, VX, LS and ST, where ST is substrate temperature; `has_keyhole` is the manual any-frame label.
- 20 repeats × 5 folds = 100 outer runs; 324 training-pool rows and 81 held-out rows; identical B16 starts.
- P2 is live sequential. At each budget G3 is refit from current training-pool features and revealed queried labels, current unqueried candidates are scored, and the selected label is appended only after selection (`src/week9_phase1_20_m3_g3_margin_acquisition.py:46-65,168-204`).
- The selector interface excludes held-out features/labels, hidden candidate labels and q20/q30 flags. Stored candidate tables contain no truth or subset columns (`frozen_protocol.json:20-27`; `validation_report.json:3,21-24,43`).
- G3 is the standalone four-input ARD Matérn-3/2 GPC with four length scales (`src/week9_phase1_12_gpc_kernel_adequacy.py:54,67-72,123-131`). It is neither the old isotropic Week 8.5 GPC (`src/week7_phase6_real_data_boundary_active_level_set.py:677-686`) nor the historical physical-depth quantity also called G3.
- P1 and P2 use the same M3 evaluator and held-out prediction routine (`src/week9_phase1_20_m3_g3_margin_acquisition.py:68-74,191-197`; `src/week9_phase1_14_m3_margin_acquisition.py:145-160`).
- AULCs are computed per fold; the five folds are averaged within each repeat, and the bootstrap resamples the 20 paired repeat means (`src/week9_phase1_20_analysis.py:217-245`).

## Verified result

| Endpoint | P2−P1 mean | 95% repeat-block interval | Positive repeats | Role |
|---|---:|---:|---:|---|
| q20 balanced-accuracy AULC B16–B40 | -0.002560 | [-0.010570, +0.005446] | 9/20 | Primary |
| q20 balanced-accuracy AULC B16–B80 | -0.007014 | [-0.011681, -0.002494] | 7/20 | Secondary |

Source: `outputs/week9_phase1_20_m3_g3_margin_acquisition/paired_contrasts.csv:2,4`.

P2 genuinely changed the acquisition path. All 100 sequences differ from P1; active-only Jaccard overlap is 0.314 at B40 and 0.549 at B80 (`path_overlap_summary.csv:5-7`). Therefore the null/negative result is not caused by replaying the incumbent trajectory.

## Endpoint and numerical caveats

The Phase 1.20 headline is **balanced accuracy** AULC. Older numbers such as P1 ≈ 0.844623 are ordinary-accuracy AULCs and must not be compared numerically with the balanced-accuracy P1 value ≈ 0.823115 (`FINAL_PHASE1_20_REPORT.md:26-30`). q30 is secondary.

There were zero fallback fits. However, 85.17% of G3 fits hit at least one length-scale bound and warnings were common; M3 reported convergence for 91.92% of fits and had 64.52% any-length-bound hits (`fit_diagnostics_summary.csv:2-3`). These diagnostics do not invalidate the paired deterministic comparison, but claims must be limited to the exact frozen implementations.

## Plain-language conclusion

- **What happened:** G3 chose different simulations, but those choices did not help M3 on the main early q20 balanced-accuracy measure.
- **Why it matters:** It directly tests acquisition value rather than assuming predictive quality transfers to query quality.
- **What it means:** Keep M3-margin as incumbent; the early result is small/unresolved and the full window favors M3-margin.
- **What it does not mean:** G3 is not proven to be a worse predictor, and nothing here proves external performance or real simulator savings.

## Week 10 use

Safe for thesis main text as a scoped negative/unresolved acquisition result. Put optimizer diagnostics, q30 and detailed path overlap in backup/appendix. Do not use it as evidence against G3 predictive quality.
