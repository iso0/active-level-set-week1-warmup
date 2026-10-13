# C4 — new-split stability check: DRAFT (not frozen, not executed)

*Written 2026-10-13, before any Stage M result. No C4 split object was built, no model was scored on C4, and nothing here was tuned.*

## What C4 is, and what it is not
- **What it is:** a one-time stability check of **one** fully specified future candidate, on new random partitions of the **same 541 simulations**. All of these simulations have been inspected repeatedly: labels, depth monitors, Week 18–20 development, and the C3 confirmation, which failed and stays unchanged.
- **What it is not:** independent data, a new simulator setting, or evidence that removes selection bias. A stable result on C4 would mean only that the candidate's advantage does not depend on the particular DEV/C3 partitions.
- **When it may run:** only after a candidate exists with a frozen manifest, together with a separate owner decision. This request does not authorize running C4, scoring any model on it, or using it for tuning.

## Audit: have repeats / seeds 21–24 been used? (`c4_audit.json`)

| Population | Split construction | Repeats 21–24 |
|---|---|---|
| **OLD (405)** | Week 8.5 `build_splits`: StratifiedGroupKFold(5), seed `seed_u32("outer_split\|repeat\|NN")` | **USED.** Week 9 Phase 1.20 confirmation used repeats 21–60 of this generator. The checkpoints are in `outputs/week9_phase1_20_acquisition_search/checkpoints/*/…r21_ … r24_…`, 20 files in each of three arms. Phase 1.21 then used repeats 61–120. |
| NEW (136) | Week 11 owner-approved label-free group-fold certificate (`EXTERNAL_BATCH_FREEZE.json`, 20 seeds) | Not generated; the certificate holds repeats 1–20 only. |
| POOLED (541) | `src.week18_tasks.pooled_tasks`: campaign × label stratified shuffle, `default_rng([1818, rep])` | Not generated (the code loops over `range(1, 21)`). |

- **Result: collision.** Repeats 21–24 cannot serve as a common C4 block. For OLD they are partitions whose results were already inspected in Phase 1.20.
- The OLD generator's repeats 61–120 are also spent (Phase 1.21).

## Proposed unused seeds
- **Namespace:** one new string namespace for all three populations, used with each population's own historical split construction:
  - **OLD:** StratifiedGroupKFold(5, shuffle) on the canonical label, with exact-input-tuple groups (the Week 8.5 rule). `random_state = seed_u32("C4|OLD|repeat|k")`.
  - **NEW:** label-free random assignment of input-tuple groups to 5 folds (the Week 11 certificate procedure; its code will be located and reused, not rewritten). Seed `seed_u32("C4|NEW|repeat|k")`.
  - **POOLED:** campaign × label stratified shuffle (the `pooled_tasks` rule). `np.random.default_rng(seed_u32("C4|POOLED|repeat|k"))`.
  - In every case k = 1, 2, 3, 4.
- **Pre-freeze check (label-free):**
  - Every proposed partition must differ from all 120 historical OLD repeats, the 20 NEW repeats and the 20 POOLED repeats (exact fold-set comparison).
  - Each training pool must have at least 80 runs.
  - If any partition repeats a historical one, replace k with the next unused integer and record the change.

## Execution rule (for the future freeze)
1. **One candidate.** A single fully specified candidate (model, acquisition, budgets, startup, code hashes) is frozen first, as for C3, with the endpoint, a stability criterion and its interpretation. C4 split objects are built only after that commit.
2. **One run.** Each C4 run is executed once: no reruns, no reseeding, no partial-result selection. The reference and system controls run on the same paths.
3. **Endpoint.** The candidate's own frozen primary endpoint, together with a pre-stated **stability** criterion (sign and magnitude relative to its DEV estimate). It is reported as a stability check on previously inspected simulations.
4. **No overwriting.** C3's failed decision (`week20 …/c3/decision_c3.json`) stays as it is and is reported next to any C4 result.

**Ledger:** C4-D in `ATTEMPT_LEDGER.md`.
