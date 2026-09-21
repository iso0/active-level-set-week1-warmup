# Frozen Week 10 Track A plan

## Scientific status

- Incumbent: **M3 probability margin with frozen B16 start**.
- One external challenger: **`early8__coverage_then_margin_B40`**, a composite initial-design-plus-acquisition policy.
- Attribution control: **`coverage_then_margin_B40`**, same B16 start as the incumbent. It is not a second challenger.
- Evaluator: frozen M3 = physics/log-h mean plus ARD four-dimensional Matérn-3/2 GP discrepancy.
- No new acquisition search, M3 redesign, q30 promotion, Phase 1.23 invention or outcome-based tuning.

## Internal attribution resolved before external data

- Candidate A versus M3-margin, with the same B16 start and M3 evaluator, remains a positive pure-acquisition result: q20 accuracy AULC B16–B80 `+0.003171 [+0.001671,+0.004759]`.
- Candidate B versus a newly run matched `early8__margin` control isolates coverage after holding the early-start rule fixed: `+0.001939 [+0.000458,+0.003402]`, Holm-adjusted `p=0.02622`.
- Candidate A versus a live, 100/100 parity-verified recreation of historical Binary-A0 is `+0.002990 [+0.000590,+0.005434]`, Holm-adjusted `p=0.02622`.
- Candidate B's total `+0.006708` versus M3-margin decomposes into `+0.004769` from the earlier active-start margin path and `+0.001939` from coverage conditional on that start.
- These are same-405 internal/post-result attribution results. They do not change the external-test arms or the replacement rule. None reaches `+0.01`, and the new balanced-accuracy contrasts remain unresolved.

## Frozen challenger implementation

- Start with the first eight points of the frozen maximin order.
- If only one class has been observed, extend sequentially along that same frozen order until both classes are revealed.
- Before B40, estimate the log-h band from queried labels only and pad it by `max(0.05, 0.25 × width)`.
- Inside the band, select by equal-weight rank sum of M3 uncertainty and nearest-queried distance in standardized P/VX/LS/ST.
- Fit scaling on the current training pool only.
- Fall back to plain M3 margin if the band is empty.
- From B40 onward, use plain M3 probability margin.
- Preserve existing tie-breaking, numerical environment and code hashes from `FINAL_POLICY_FREEZE.json`.

## Frozen external questions

1. Does the complete composite challenger outperform the incumbent on a genuinely new simulation batch?
2. If yes, does the same-seed attribution control also improve, supporting an acquisition-specific explanation?

## Metrics and decision rules

- Primary subset: Fold-B1 q20. q30 is secondary and never replaces q20.
- Confirmatory endpoint: paired q20 accuracy AULC B16–B80 for challenger minus incumbent, matching the Phase 1.21 claim.
- Prespecified secondary outputs: q20 accuracy AULC B16–B40; q20 balanced-accuracy AULC B16–B40 and B16–B80; q30 accuracy AULC; q20 Keyhole recall; full held-out accuracy; B40/B80 checkpoints.
- Report accuracy and balanced accuracy separately; never compare their AULCs as the same endpoint.
- Confirmation requires a lower 95% paired repeat-block interval above zero, multiplicity control for all confirmatory contrasts, and no frozen guardrail violation.
- Replacement requires the above plus mean primary AULC gain at least `+0.01`.
- A pure acquisition replacement claim also requires the same-seed attribution control to improve over M3-margin. If only the composite challenger succeeds, claim only a system-policy benefit.
- Descriptive curve-crossing or “simulations saved” values never determine success.

## Label-blind intake and freeze sequence

1. Receive stable IDs/configuration tokens and P, VX, LS, ST in an immutable label-free manifest. Receive labels separately and keep them sealed.
2. Hash the delivered files and record owner, delivery time, simulator/configuration provenance and candidate exclusions.
3. Rerun the Phase 1.22 overlap audit against the exact original 407/405 identities. Stop if the pool is not disjoint.
4. Confirm in writing that method-side investigators have not viewed labels.
5. Perform only label-free schema, duplicate, missingness, units/ranges and sample-size feasibility checks.
6. Freeze usable rows, technical exclusions, split/repeat seeds, paired initial orders, training/test membership procedure, exact budget grid, Fold-B1/q20/q30 construction, endpoints, intervals, multiplicity, guardrails, failure handling, package versions, thread settings and code/file hashes.
7. Verify that every outer training pool can support B80. If not, stop for a pre-label protocol decision; do not improvise after unsealing.
8. Run a dry integrity check with synthetic labels or interface mocks only. It must show that selectors cannot access held-out labels/features, hidden candidate labels or q20/q30 membership.
9. Only then unseal labels into the oracle and run the locked paired benchmark.

## Locked execution order after unsealing

1. Build the frozen paired outer splits and initial orders.
2. Run M3-margin control.
3. Run the single composite challenger.
4. Run the same-seed attribution control.
5. Evaluate all arms with the identical frozen M3 evaluator on untouched held-out rows.
6. Compute repeat-block paired effects and audit all query paths for eligibility and invariance.
7. Apply the frozen confirmation/replacement rules once.
8. Report PASS/UNRESOLVED/FAIL without tuning or launching follow-up R&D.

## Pending Ioan inputs

- Refined email/reading list and observability direction: Track B dependency.
- New simulation batch: Track A external-validation dependency.

The first action when the batch arrives is the **label-free Phase 1.22 intake/provenance audit**. No model should be fit first.
