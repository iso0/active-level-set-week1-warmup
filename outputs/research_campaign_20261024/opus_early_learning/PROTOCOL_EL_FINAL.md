# EL forward validation: protocol

Registered 2026-10-25 after the DEV stage (`dev/DEV_CROSS.md`) and before any fresh run. It is frozen with `freeze/EL_FINAL_MANIFEST.json`, the SHA-256 of every code file below.

## 1. What is tested

- **Primary candidate (chosen by the registered DEV rule):** D = HA_LEAN selects (margin), HA_TREND predicts. Reference: A = HA_LEAN selects, HA_LEAN predicts (the RC23 / RC24P thesis learner).
- **Secondary:** B = HA_TREND selects / predicts and C = HA_TREND selects / HA_LEAN predicts. The same rule is applied to each against A. D against B is reported without a verdict.
- **No stage-2 system:** the DEV rule found the fixed crossing "enough" (`src/el_final.py` EXTRA = ()).

## 2. Fresh IDs

All are new splits or startups of the same 541 runs, so this is DEV evidence, not independent physical validation.

| condition | IDs | learners | IDs used before |
|---|---|---|---|
| STD | repeats 83–122 × 5 folds | 200 learners in 40 clusters | repeats 1–82 |
| K5 (the same five k = 5 regions) | startups 25–32 × 5 blocks | 40 learners; block 3 is one-class | startups 1–24 |
| K4 (the k = 4 partition) | startups 9–16 × 4 blocks | 32 learners | startups 1–8 |

## 3. Runs

**Job `el-fwd`** (`src/el_final.py`): 544 units.
- Per task, two units:
  - HA_LEAN-selected path → A (own) + D (HA_TREND on the path, every budget);
  - HA_TREND-selected path → B (own) + C (HA_LEAN on the path, every budget).
- Budgets are 8..60, with the 8-point label-free maximin startup counted.
- Each cross prediction at budget b uses only the first b paid runs of the path.

**Preceding job `el-smoke`:** repeat 1, fold 1 (DEV), budget 14; never evaluated.

**Resources:** at most 3 single-thread workers (`src/el_runner.ps1`); Astra's share is not used. One 48 h window, ending 2026-10-27 20:07:51 UTC.

## 4. Evaluation and decision

**Code:** `src/el_decide.py` (metrics `src/el_eval.py`). The rule is exactly `PROTOCOL_EL_OBJECTIVES.md` §9, checked on STD, individual learners, over 40 repeat clusters:

| part | condition | result |
|---|---|---|
| E1 | ΔBA-AULC B8–B24 (D − A), one-sided 95 % LCB > 0 | EARLY GAIN SHOWN |
| E2 | restricted-mean saving RMS_A − RMS_D, horizon 60, at τ = 0.93 and 0.95: LCB > 0 | SAVING SHOWN |
| | LCB > −1.0 simulation | NOT WORSE |
| | otherwise | NOT SHOWN |
| E3 | τ = 0.93 and 0.95: Δattainment LCB ≥ −0.05 and Δkept LCB ≥ −0.05 | reliability not worse |
| E4 | ΔLL B8–B60 ≤ +0.030, ΔBrier B8–B60 ≤ +0.010 (point estimates), mean CPU per step ≤ 3 × A's | guardrails hold |

**Verdict:** if E1, E3 and E4 hold and E2 is at least NOT WORSE at both targets:
- SAVINGS_SHOWN when the saving is shown at both targets;
- PARTIAL_SAVINGS when it is shown at one;
- EARLY_ONLY when it is shown at neither.

Otherwise the verdict is NOT_ADOPTED.

**Robustness** (reported, not in the verdict):
- A warning is raised if the per-region BA-AULC B8–B60 against A has an LCB below −0.02 in K5 or K4.
- Pooled and per-region block tables are reported, as is the short-Keyhole hard group.

**Exports and independent check (after the decision; nothing in the rule changes):**
- the predictions of all four systems and every paid simulation ID of both paths, per condition;
- a recomputation of BA, AULC and spend from the export files by separate code (`src/el_export.py`).

## 5. Known before this run (DEV, `dev/DEV_CROSS.md`)

**D − A on 24 DEV clusters:**
- early +0.0053 [+0.0040, +0.0067];
- RMS saving at 0.93: +0.75 [+0.03, +1.47];
- RMS saving at 0.95: +0.96 [−1.15, +3.07];
- Δkept(0.95) −0.008 [−0.061, +0.044];
- ΔLL +0.0050.

**Expected power:**
- The DEV standard error of the 0.95 saving was about 1.2 simulations with 24 clusters, so about 0.95 is expected with 40.
- If the true saving is about 1 simulation, E2 at 0.95 is more likely to end NOT WORSE than SAVING SHOWN.
- Δkept is close to the −0.05 reliability margin.

These expectations are written down before the run. They are not reasons to change anything afterwards.

## 6. Not allowed after this registration

- Changing the rule, the margins, the IDs, the candidate or the metrics.
- Adding systems to the verdict.
- Rerunning with other seeds to obtain a different outcome.
