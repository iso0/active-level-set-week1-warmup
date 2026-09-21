# Week 10 Track A — Phase 1.20–1.22 Audit

## 1. Executive verdict

- Phase 1.20: **PASS_WITH_CAVEATS**. P2 was generated live and sequentially without detected leakage, but it did not improve the same M3 evaluator; retain M3-margin.
- Phase 1.21: **D. VALID FROZEN CHALLENGER FOR EXTERNAL TEST**. A new locked comparator audit confirms a small acquisition effect: coverage versus matched early-start margin `+0.001939 [+0.000458,+0.003402]`, and Candidate A versus live historical Binary-A0 `+0.002990 [+0.000590,+0.005434]`. This remains internal OLD-405 evidence, not external validation.
- Phase 1.22: **PASS as a label-free availability/stop audit; external validation NOT RUN**. It correctly stopped because no genuinely new pool was available.
- Phase 1.21 and 1.22 have no dedicated recoverable branch/ref. Their first tracked appearance is consolidation commit `8e90497864fade6b14ca500b9dcbd098a7c95a9d`, now on `main` at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`.
- The current acquisition incumbent remains **M3 probability margin with the frozen B16 start**.
- Exactly one challenger is carried forward: **`early8__coverage_then_margin_B40`**, explicitly as a composite initial-design-plus-acquisition policy. `coverage_then_margin_B40` is its attribution control, not a second challenger.
- Phase 1.20 and 1.21 headline values are not directly comparable: Phase 1.20 uses q20 balanced-accuracy AULC B16–B40; Phase 1.21 preregistered q20 accuracy AULC B16–B80.
- q20 remains primary. q30 is secondary in every carry-forward decision and does not replace q20.
- No result reaches the prospective `+0.01` full-window replacement threshold; M3-margin remains incumbent until a genuinely external, label-blind test.
- Track A waits for Ioan's new simulation batch; Ioan's refined email/reading list mainly affects Track B.

## 2. Phase 1.20

- **Question:** Does a standalone G3 ARD Matérn-3/2 GPC probability-margin selector choose simulations that let the unchanged M3 evaluator learn faster than M3's own probability-margin selector?
- **Design:** Same frozen 405 simulations, 20 repeats × 5 folds, 324-row training pool, 81-row held-out test, and identical B16 starts. P2 refits G3 at every budget using only training-pool features and revealed queried labels; M3 evaluates both P1 and P2.
- **Verified result:** Primary q20 balanced-accuracy AULC B16–B40, P2−P1 = `-0.002560`, repeat-block 95% interval `[-0.010570,+0.005446]`, 9/20 positive repeats. B16–B80 = `-0.007014 [-0.011681,-0.002494]`, 7/20 positive. All 100 P2 paths differ from P1; this was not a replay of A0.
- **Audit verdict:** **PASS_WITH_CAVEATS**. Leakage, split, evaluator, endpoint and repeat-block checks pass. No fallback fits occurred, but G3 warnings/bound hits and some M3 non-convergence are frequent; interpret the comparison as the exact frozen implementations, not idealized model families.
- **Safe interpretation:** G3 selected genuinely different points, but those choices did not improve M3 on the primary early endpoint. This supports retaining M3-margin. It does **not** prove that G3 is a worse predictor, establish external validity, or demonstrate simulator savings.

## 3. Phase 1.21

- **Question:** Can the earlier complex coverage/misfit policy be simplified to an early boundary-coverage rule and reproduce a gain over M3-margin on previously unused internal split repeats?
- **Design:** Candidate A, `coverage_then_margin_B40`, keeps the frozen B16 seed; until B40 it ranks uncertain M3 candidates inside a queried-label-estimated log-h band together with 4D distance from queried points, then uses M3 margin. Candidate B, `early8__coverage_then_margin_B40`, uses the same rule after an 8-point maximin start extended only until both observed classes appear. M3 is the evaluator. Repeats 61–120 give 60 repeat blocks and 300 outer runs on the same 405 simulations.
- **Verified result:** The protocol was frozen before the first replication checkpoint and no within-replication tuning occurred. Primary q20 **accuracy** AULC B16–B80: A−margin `+0.003171 [0.001671,0.004759]`, 42/60 positive; B−margin `+0.006708 [0.004775,0.008632]`, 54/60 positive. The Week 10 locked addendum then ran the two missing matched controls. B−early8-margin = `+0.001939 [+0.000458,+0.003402]`, 37/60; A−live historical Binary-A0 = `+0.002990 [+0.000590,+0.005434]`, 35/60. Both passed the two-test Holm rule (`p=0.02622`) and guardrails. Historical A0 first reproduced 100/100 canonical paths, then ran live; all 600 new outer runs completed with zero reuse.
- **Audit verdict:** **D. VALID FROZEN CHALLENGER FOR EXTERNAL TEST**. No hidden-label leakage was detected. The family was developed/screened earlier, and replication uses new partitions of the same population; therefore it is credible internal confirmation, not independent external validation. Neither full-window mean reaches 0.01, and that threshold was not the registered Phase 1.21 success rule.
- **Safe interpretation:** There is now evidence for a real but small acquisition benefit on the frozen q20 accuracy endpoint. Candidate B's total `+0.006708` decomposes exactly into `+0.004769` from the earlier active-start margin path and `+0.001939` from coverage conditional on that start; most of the total advantage is therefore not the coverage rule alone. New balanced-accuracy contrasts cross zero, and no full-window gain reaches `+0.01`. Candidate B remains the single frozen external challenger, not the incumbent. The result does **not** prove external validity, final-B80 accuracy gain, improved Keyhole recall, or confirmed simulator savings.

## 4. Phase 1.22

- **Question:** Was a genuinely new, label-blind simulation pool available and eligible for external validation?
- **Design:** A label-free provenance and availability audit read names, repository metadata, identifiers and P/VX/LS/ST only. It was explicitly limited to Steps 0–1.
- **Verified result:** Every accessible simulation source was the existing 407-campaign/405-analysis population or a subset/copy. The proposed new supervisor pool had no accessible manifest, inputs or labels. `EXTERNAL_BLIND_POOL_VALID=false`; no external label was read, no external protocol was frozen and no external run was made.
- **Audit verdict:** **PASS — protocol preparation/stop decision only; external validation NOT RUN.**
- **Safe interpretation:** Phase 1.22 protected the future blind test by refusing to relabel old data as external. It does **not** mean the external method failed. It is ready to resume the intake audit when the new manifest arrives, but it is not yet a fully frozen, executable external experiment.

## 5. Current acquisition status

- **Incumbent:** M3 probability margin, frozen B16 start.
- **One challenger:** `early8__coverage_then_margin_B40`, treated as a composite policy package.
- **Mandatory attribution control:** `coverage_then_margin_B40`, same B16 start as the incumbent; it is not counted as a second challenger.
- **Resolved internal attribution:** Candidate A versus M3-margin is a positive pure-acquisition contrast (`+0.003171`); coverage also remains positive when the early-start rule is held fixed (`+0.001939`). These effects are statistically resolved on q20 accuracy but practically small and not resolved on the new balanced-accuracy comparisons.
- **Discarded/closed for Week 10:** standalone G3-margin as a replacement selector; the older complex CCM/late-misfit variants; any new acquisition search.

The positive Phase 1.21 result is an acquisition/system-policy result evaluated by M3. Phase 1.20 separately shows why a better or interesting predictive model does not automatically provide a better acquisition path.

| Placement | Safe claims |
|---|---|
| Thesis main text | Phase 1.20 is a valid negative/unresolved acquisition comparison; Phase 1.21 is a preregistered internal replication with a Week 10 matched-control audit showing a small q20-accuracy acquisition effect on the same population; Phase 1.22 found no eligible external pool and ran no validation. |
| Backup/appendix | Optimizer/bound diagnostics, path overlap, q30, secondary balanced-accuracy results, mechanism analyses, non-inferiority details and descriptive curve crossings. |
| Not usable | External-validation claims, confirmed simulator savings, Candidate B as a pure acquisition effect, G3 predictive inferiority, or numerical comparison of accuracy AULC with balanced-accuracy AULC. |

## 6. What is frozen before new data

- No method development or tuning against the new batch.
- Incumbent, challenger, attribution control, M3 evaluator and the code hashes recorded in `FINAL_POLICY_FREEZE.json`.
- Challenger parameters: 8-point frozen maximin prefix, sequential extension until both revealed classes appear, queried-label-only log-h band, pad fraction 0.25, pad floor 0.05, equal uncertainty/coverage rank weights, standardized P/VX/LS/ST using training-pool-only scaling, switch to plain M3 margin at B40, and frozen tie/fallback behavior.
- q20 remains the primary near-boundary subset; q30 remains secondary.
- External confirmatory endpoint: challenger versus incumbent on q20 accuracy AULC B16–B80, matching Phase 1.21. Early q20 accuracy B16–B40, q20 balanced accuracy, q30, Keyhole recall and full-test accuracy are prespecified secondary/guardrail outputs and must be reported separately.
- External confirmation requires a lower 95% paired repeat-block interval above zero and the frozen recall/final-accuracy guardrails. Replacement requires, in addition, a mean effect of at least +0.01 AULC; a positive mean alone is insufficient.
- A pure acquisition replacement claim additionally requires the same-seed attribution control to improve over M3-margin; otherwise any benefit is attributed only to the composite policy.
- Pool identity, exclusions, split seeds, Fold-B1/q20 construction, exact feasible budget grid and all file/code hashes must be sealed after label-free intake and before labels are unsealed.

## 7. What waits for Ioan

- **Ioan's refined email / reading list and observability direction:** mainly a Track B dependency. It does not change the frozen Track A incumbent/challenger decision.
- **Ioan's new simulation batch:** the crucial Track A dependency. Expected size is approximately 162, perhaps about 140 usable, but the analysis must use the delivered immutable manifest rather than the estimate.

## 8. Exact next actions when new data arrive

1. Receive an immutable label-free manifest containing stable IDs/configuration tokens and P, VX, LS, ST; keep labels in a separate sealed file.
2. Rerun the Phase 1.22 provenance/overlap audit first. Confirm the batch is disjoint from the old 407/405 campaign and document simulator/domain changes.
3. Confirm that method-side investigators have not seen the labels; stop if this cannot be established.
4. Perform label-free schema, duplicate, missingness, range and usable-row checks. Apply only prespecified technical exclusions.
5. Before unsealing labels, freeze the manifest hash, exclusions, split/repeat seeds, paired starts, budget feasibility, q20/q30 construction, metrics, intervals, multiplicity, guardrails, failure handling, numerical environment and code hashes.
6. If every training fold supports B80, run the locked paired comparison: M3-margin control, the single composite challenger, and the same-seed attribution control. Do not tune parameters.
7. Reveal labels only through the sequential oracle for queried training rows; keep held-out labels, q20/q30 membership and hidden candidate labels unavailable to selectors.
8. Evaluate with the same M3 implementation, compute paired repeat-block contrasts, and report accuracy and balanced-accuracy endpoints separately.
9. Apply the frozen confirmation/replacement rules. Do not promote a policy from a positive mean alone.

The first executable action is therefore the **label-free Phase 1.22 intake/provenance audit**, not model fitting.

## 9. Issues requiring Burak's decision

No incumbent or challenger choice remains unresolved in this audit. One conditional decision remains: if the label-free usable count makes B80 infeasible in the frozen outer-training design, Burak must choose **before any label is opened** between deferring the external test or approving a documented pre-label protocol amendment. The budget window must not be changed after seeing outcomes.
