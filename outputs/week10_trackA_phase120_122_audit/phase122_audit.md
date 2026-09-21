# Phase 1.22 independent audit

## Repository location

No dedicated Phase 1.22 branch/ref is recoverable locally or on current origin heads. Its source and output first appear as tracked content in consolidation commit `8e90497864fade6b14ca500b9dcbd098a7c95a9d`, now on `main` at `5b7d030413ed2aa24e6e4c8f124dd5145f735618`.

- Source: `src/week9_phase1_22_external_pool_audit.py`
- Only phase output: `outputs/week9_phase1_22_external_blind_test/EXTERNAL_POOL_AUDIT.json`
- No standalone final report, frozen external protocol, notebook or phase-specific test file exists.

## Verdict

**PASS — valid protocol-preparation/availability audit; external validation NOT RUN.**

## What was tested, and why

Phase 1.22 asked whether any accessible dataset was genuinely new, disjoint from the original campaign and still label-blind to the method side. This check is necessary before calling any result external validation.

The phase was explicitly limited to Steps 0–1 and read no outcomes. It accessed names, repository metadata, identifiers and P/VX/LS/ST only (`EXTERNAL_POOL_AUDIT.json:2-4`).

## Verified findings

- `sph_v2` and its pinned revision contain the existing 407-experiment campaign and the already used 405-row analysis population (`EXTERNAL_POOL_AUDIT.json:119-150`).
- Other accessible Week 5–6/local copies are subsets or copies, not an independent batch (`EXTERNAL_POOL_AUDIT.json:155-303`).
- The proposed new supervisor pool had no accessible immutable manifest, inputs or labels and could not be audited (`EXTERNAL_POOL_AUDIT.json:319-333`).
- Final state: `EXTERNAL_BLIND_POOL_VALID=false` (`EXTERNAL_POOL_AUDIT.json:336`).
- The phase stopped before Step 2: no external label was read, no external protocol was frozen and no external run was made (`EXTERNAL_POOL_AUDIT.json:337-342`).

## What is and is not ready

Ready now:

- the conservative stop rule;
- the existing-pool overlap/provenance checks;
- the requirement for a label-free manifest and separately sealed labels;
- resumption of the intake audit as soon as the new batch arrives.

Not yet complete:

- immutable identity/hash of the new pool;
- final usable-row/exclusion ledger;
- pool-specific outer splits and budgets;
- external Fold-B1/q20 construction;
- fully sealed external protocol and unsealing procedure.

Phase 1.21 had already frozen the candidate methods, M3 evaluator and within-training-pool scaling rule. Phase 1.22 itself did **not** freeze the external pool's metrics, splits, q20 adaptation, thresholds or unsealing sequence because the pool did not exist in an accessible form.

## Plain-language conclusion

- **What happened:** The audit looked for new data but found only old or already examined data; the anticipated new batch was not accessible.
- **Why it matters:** Reusing the 405 cases would falsely label an internal analysis as external validation.
- **What it means:** The stop was correct and protects the thesis claim.
- **What it does not mean:** The challenger failed external validation. No external experiment occurred.

## Week 10 use

Safe for the thesis as a provenance/availability statement and evidence that no external claim has yet been made. Do not report it as a failed validation experiment.
