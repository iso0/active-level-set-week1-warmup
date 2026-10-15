# Intake of Astra's controlled decision/acquisition study (EXTERNAL; her unreviewed results; integrated as hypotheses only)

**Status (read only; her workspace was not written, nothing was duplicated, no checkpoint was deserialised).**
- **Her pipeline:** `COMPUTATION_FINISHED_REVIEW_REQUIRED` since 2026-10-15 00:58:11 UTC. In her words, "Results and report tables saved. Final scientific and artifact review still required."
- **Her study status:** `INCOMPLETE_WITH_PRESERVED_STOPS`. 72 of 84 trajectories are complete. Budget used: 374 top-level requests and 1,122 component solves.
- **Snapshot:** a verbatim copy is in `outputs/astra_balanced_decision_acquisition/results_2026-10-15T0058Z/`. `CONTROLLED_RESULTS.json` and `ledger.jsonl` are stored gzip-compressed. Hashes are in `intake/ASTRA_RESULTS_INTAKE.json`.
- **Frozen sources:** her method code is byte-identical to the 2026-10-14 intake.
- **Until she has reviewed them**, these are her numbers, not claims of this branch.

## What her study is
- **Worlds:** synthetic, seven of them (informative, redundant, harmful, rare_negatives, locally_mixed, selected_fraction, missing_depth), with four seeds each and budgets up to B10.
- **Selectors:** her balanced-risk selector against probability-variance and balanced-margin, all with the same model and decision rule.
- **Endpoints:** BA-AULC, terminal BA and class recalls, proper scores, region errors, and decision-only readouts that compare her prospective batch rule (PBR = the finite-batch rule) with cutoff 0.5, the paid fraction and posterior-mean π.
- **Relation to our audit:** a different study from Opus's decision-only audit (`DECISION_AUDIT_REPORT.md`), with different data (synthetic worlds vs NEW posteriors) and a different question (acquisition vs decision rules on fixed posteriors).

## Her headline numbers (from `CONTROLLED_SUMMARY.md` and `RESULTS_SUMMARY.json`; Student-t intervals over 4 or fewer synthetic seeds)
- **Balanced-risk selector minus comparators, mean BA-AULC difference:** −0.011 to +0.063.
  - Every interval includes 0 except selected_fraction vs probability-variance: +0.041 [+0.003, +0.080], 3 seeds.
  - Her own conclusion: no universal selector ranking and no query-saving claim.
- **Decision-only readouts at B10** (balanced-margin path; BA difference, mean over seeds):

  | Contrast | Result |
  |---|---|
  | PBR − cutoff 0.5 | +0.051 to +0.097 in five worlds. All seeds are positive in four of them, but the interval excludes 0 only in missing_depth (+0.097 [+0.021, +0.174]). In rare_negatives it is −0.074 (2 seeds) |
  | PBR − paid fraction | −0.036 to +0.051 |
  | PBR − posterior-mean π | within ±0.0065 |

- **Numerics:**
  - All 12 incomplete trajectories are `DECISION_NUMERICAL_STOP` at B6: rare_negatives seeds 5102 and 5104 (each with all three selectors), locally_mixed seed 5102, and selected_fraction seed 5102.
  - These outputs are preserved and not treated as endpoints.
  - There were 128 accepted near-tie query decisions, and the maximum risk-tower discrepancy was 0.0011.

## Hypotheses this suggests for our work (HYP; not tested here)
1. **The ladder stops are a method-level numerical problem, not specific to NEW.** The same frozen QMC acceptance stopped her synthetic trajectories, most of all in the rare-negatives world, which resembles NEW (few negatives, high prevalence). It also left our real-data primary unavailable (11 of 20 checkpoints accepted). The registered extended ladder DA-A1 tests whether more QMC points resolve this on our posteriors.
2. **Where it is computable, the finite-batch rule behaves like a prevalence-level cutoff, not like 0.5.** In her worlds PBR is nearly identical to the posterior-mean-π rule (within ±0.007) and within ±0.05 of the paid-fraction rule, and mostly above 0.5 in BA. On NEW the paid-fraction rule's BA gain over 0.5 comes with a loss of short-Keyhole sensitivity (V2 B40: short-K 0.80 → 0.00). A finite-batch gain would therefore be a re-weighting of the same scores, not new discriminatory information.
3. **No selector advantage or simulation saving is established,** by her study or by ours.
