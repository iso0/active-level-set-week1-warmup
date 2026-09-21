# Phase 1.21 independent audit

## Repository location

No dedicated Phase 1.21 branch/ref is recoverable locally or on current origin heads. The phase first appears as tracked content in consolidation commit `8e90497864fade6b14ca500b9dcbd098a7c95a9d`, now on `main` at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`.

Exact source files are:

- `src/week9_phase1_21_all_label_reference.py`
- `src/week9_phase1_21_analysis.py`
- `src/week9_phase1_21_figures.py`
- `src/week9_phase1_21_freeze.py`
- `src/week9_phase1_21_invariance_audit.py`
- `src/week9_phase1_21_repeat_audit.py`
- `src/week9_phase1_21_repeat_audit_driver.py`
- `src/week9_phase1_21_report.py`
- `src/week9_phase1_21_simplification_replication.py`

Outputs are under `outputs/week9_phase1_21_simplification_replication/`, especially `FINAL_PHASE1_21_REPORT.md`, `PHASE1_21_PREREGISTERED_PROTOCOL.json`, `REPLICATION_RESULT.json`, `invariance_audit.json` and `FINAL_POLICY_FREEZE.json`.

## Classification

**D. VALID FROZEN CHALLENGER FOR EXTERNAL TEST**

It is too strong and too cleanly preregistered to call merely exploratory, but it is not external evidence and is not strong enough to replace M3-margin.

## What was tested, and why

The phase asked whether the useful part of an earlier complex policy was simply early coverage near the estimated boundary.

- Candidate A, `coverage_then_margin_B40`: frozen B16 start; before B40, use only queried labels to estimate a log-h boundary band, then combine M3 uncertainty rank with distance-from-queried rank in standardized P/VX/LS/ST; from B40, use plain M3 margin.
- Candidate B, `early8__coverage_then_margin_B40`: same rule after the first eight points of the frozen maximin order, extended sequentially only until both revealed classes exist.
- Evaluator: the same frozen M3 model, refit at each budget.

Candidate A is a pure acquisition comparison because it shares the incumbent B16 seed. Candidate B is a composite initial-design-plus-acquisition policy.

## Freeze, splits and leakage

- Protocol frozen at `2026-09-13T19:03:29.780115Z`, with no replication checkpoint yet; the first checkpoint followed at 19:05:03 (`FINAL_PHASE1_21_REPORT.md:24-26`).
- Repeats 61–120 were unused before this phase, giving 60 repeat blocks and 300 five-fold outer runs (`FINAL_PHASE1_21_REPORT.md:11,45`).
- These are new partitions of the same 405 simulations. They are not new simulations and are not 300 independent experiments.
- Candidate A's family/settings had already been screened on Phase 1.20 development evidence (`PHASE1_21_PREREGISTERED_PROTOCOL.json:23`). Phase 1.21 is therefore preregistered internal replication, not independent method discovery.
- The policy runner masks all unqueried labels/depths and restricts candidates to the outer training pool (`src/week9_phase1_21_simplification_replication.py:117-155`).
- A stored invariance audit scrambled all unqueried labels/depths in 120 audited states and found zero selection/probability changes (`invariance_audit.json:1-9`; `FINAL_PHASE1_21_REPORT.md:142-146`). This is strong implementation evidence, although the sampled states came from development repeats rather than every replication checkpoint.
- Holm correction covered four main tests, and the repeat block—not each fold—was the inferential unit (`PHASE1_21_PREREGISTERED_PROTOCOL.json:61-66`).

## Verified result

The preregistered primary endpoint was q20 **accuracy** AULC B16–B80, not balanced accuracy.

| Policy | Window | Difference vs M3-margin | Positive repeats |
|---|---:|---:|---:|
| Candidate A | B16–B80 | +0.003171 [0.001671, 0.004759] | 42/60 |
| Candidate A | B16–B40 | +0.007055 [0.003762, 0.010596] | 43/60 |
| Candidate B | B16–B80 | +0.006708 [0.004775, 0.008632] | 54/60 |
| Candidate B | B16–B40 | +0.013803 [0.009861, 0.017790] | 53/60 |

All four Holm-adjusted p-values were approximately 0.0004 (`FINAL_PHASE1_21_REPORT.md:47-59`). Secondary q20 balanced-accuracy AULC B16–B80 effects were A `+0.002499 [0.000854,0.004296]` and B `+0.006059 [0.003899,0.008248]` (`FINAL_PHASE1_21_REPORT.md:88-98`). q30 remained secondary.

Neither full B16–B80 mean reaches 0.01. The 0.01 threshold was not Phase 1.21's preregistered success rule, so it must not be retroactively used to call the replication a failure. It is, however, a valid prospective bar for incumbent replacement.

## Researcher degrees of freedom

Phase 1.21 fixed one control, two candidates, parameters, repeats, endpoints, multiplicity and guardrails before replication. No outcome-based tuning occurred inside the replication. The important limitation is earlier family screening on related Phase 1.20 development data and reuse of the same 405-row population. This lowers external credibility, not internal protocol validity.

## Plain-language conclusion

- **What happened:** Spreading early queries along the estimated boundary improved early learning on new splits of the same data.
- **Why it matters:** It identifies one simple, frozen challenger worth testing on genuinely new simulations.
- **What it means:** Carry Candidate B forward as one composite challenger; retain Candidate A only to attribute whether an external gain comes from acquisition rather than the 8-point start.
- **What it does not mean:** It does not prove external validity, a practically large full-window gain, improved Keyhole recall, better final B80 accuracy, or a pure acquisition effect for Candidate B.

## Week 10 controlled comparator addendum

The missing controls were frozen before execution and then run on the same Phase 1.21 repeats 61–120. This is a post-result attribution audit on the OLD-405 population, not a second independent replication.

- **Coverage with the early start held fixed:** Candidate B minus `early8__margin`, q20 accuracy AULC B16–B80 = `+0.001939 [+0.000458,+0.003402]`, 37/60 positive repeats, two-test Holm-adjusted `p=0.02622`. Both recall and final-accuracy guardrails passed. This shows a small positive acquisition contribution from coverage after holding the early-start rule fixed.
- **Candidate A versus historical Binary-A0:** `+0.002990 [+0.000590,+0.005434]`, 35/60 positive repeats, Holm-adjusted `p=0.02622`; guardrails passed. Historical A0 was not replayed: its Week 8.5 implementation first reproduced all 100 canonical stored paths exactly, then ran live on repeats 61–120. Both paths were evaluated by the same M3.
- **Decomposition of Candidate B versus M3-margin:** total `+0.006708` = early-start margin contribution `+0.004769` + coverage contribution conditional on early start `+0.001939`; closure error is zero. About 71% of the mean total difference is associated with starting active selection earlier and about 29% with coverage conditional on that start. This is an attribution decomposition, not a causal percentage claim.
- **Metric caveat:** the new q20 balanced-accuracy contrasts remain unresolved: Candidate B minus early8 margin `+0.001290 [-0.000396,+0.002930]`; Candidate A minus historical A0 `+0.001296 [-0.001514,+0.004011]`. The resolved result is on the frozen primary endpoint, q20 accuracy AULC.
- **Practical decision:** neither new primary mean, Candidate A's known `+0.003171`, nor Candidate B's total `+0.006708` reaches the prospective `+0.01` incumbent-replacement threshold. The incumbent therefore remains M3-margin B16.

Execution gates passed: 900/900 stored Phase 1.21 checkpoints validated; 100/100 canonical A0 paths reproduced; three hidden-label counterfactual cases caused exactly zero probability or selection change; 600/600 new outer runs completed with zero checkpoint reuse; 10/10 focused tests passed. In the new A0-path M3 evaluations, 1,376/19,500 optimizer fits had a non-convergence flag but no fallback occurred. Because the identical M3 implementation is the evaluator for every arm and no fallback was used, this is a qualification rather than a rejection criterion.

## Thesis use

- **Main text:** preregistered internal replication on the same 405-simulation population, with exact effect sizes and the external-validity limitation.
- **Backup/appendix:** secondary balanced-accuracy/q30 results, mechanism analyses, non-inferiority to old CCM, and descriptive 12–14-simulation curve crossing.
- **Not usable:** “external validation,” “300 independent experiments,” “12–14 simulations saved” as an inferential claim, or “Candidate B proves better acquisition.”
