# EL stage 2 confirmation: protocol

Registered 2026-10-25 after the stage-2 DEV evaluation (`el2_dev/EL2_DEV.md`) and before any confirmation run. Frozen with `freeze/EL2_FINAL_MANIFEST.json`.

## 1. What is tested

- **Primary:** E = HA_LEAN selects (margin) / the evidence-weighted HA_LEAN + HA_TREND mixture predicts. It is exactly as defined in `PROTOCOL_EL2_MECHANISM.md` §2, code `src/el_mix.py`.
- **Reference:** A = HA_LEAN selects / HA_LEAN predicts.
- **Secondary:** D = HA_LEAN selects / HA_TREND predicts, a replication of the EL-1 verdict on new data.
- **Same path:** E, A and D share the same HA_LEAN-selected path in every learner.
- **Not run:** B and C.

## 2. Fresh IDs

All are new splits or startups of the same 541 runs, so this is DEV evidence, not independent physical validation.

| condition | IDs | learners | IDs used before |
|---|---|---|---|
| STD | repeats 123–162 × 5 folds | 200 learners in 40 clusters | repeats 1–122 |
| K5 | startups 33–40 × 5 blocks | 40 learners | startups 1–32 |
| K4 | startups 17–24 × 4 blocks | 32 learners | startups 1–16 |

These are the IDs named in `PROTOCOL_EL2_MECHANISM.md` §4 and used by `src/el_mix.py` (FWD_STD, FWD_K5, FWD_K4).

## 3. Runs

**Job `el-mix-fwd`** (`src/el_mix.py`): 272 units.
- Per task, the HA_LEAN margin path is run (src.rc23_common.run_arm, unchanged).
- At every budget 8..60 on that path, both stacked classifiers are fitted on the first b paid runs, with their evidence grids, giving A, D and E at the test rows.
- **Check:** p_L must equal the path's own HA_LEAN predictions exactly.

**Preceding job `el-mix-smoke`:** repeat 1, fold 1, budget 14; never evaluated.

**Resources:** at most 3 single-thread workers, inside the same 48 h window (end 2026-10-27 20:07:51 UTC).

## 4. Decision

`PROTOCOL_EL_OBJECTIVES.md` §9, unchanged, implemented by `src.el_decide.verdict` and applied to E against A on STD (individual learners, 40 clusters):

| part | condition |
|---|---|
| E1 | ΔBA-AULC B8–B24, LCB > 0 |
| E2 | restricted-mean saving at 0.93 and 0.95: SAVING SHOWN if LCB > 0; NOT WORSE if LCB > −1.0 |
| E3 | Δattainment and Δkept, LCB ≥ −0.05 at both targets |
| E4 | ΔLL ≤ +0.030; ΔBrier ≤ +0.010; CPU ≤ 3 × A |

**Verdict:** SAVINGS_SHOWN / PARTIAL_SAVINGS / EARLY_ONLY / NOT_ADOPTED. The same rule is applied to D (secondary).

**Robustness:** a per-region BA-AULC B8–B60 LCB below −0.02 against A, in K5 or K4, raises a warning. It is not part of the verdict.

**Expected power, written before the run.** From the DEV standard errors scaled to 40 clusters:
- E1 is likely shown (DEV +0.0029, SE about 0.0005);
- E2 at 0.93 is borderline (DEV +0.68, SE about 0.42);
- E2 at 0.95 is most likely NOT WORSE (DEV +0.57, SE about 0.76).

## 5. Not allowed after this registration

- Changing the rule, the margins, the IDs, the mechanism or the metrics.
- Adding systems.
- Rerunning with other seeds.
