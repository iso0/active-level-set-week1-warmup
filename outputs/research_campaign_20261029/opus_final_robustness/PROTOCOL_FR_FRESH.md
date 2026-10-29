# FR step 3: fresh test of GATE + margin. NOT RUN (drafted only)

> **Status (2026-10-29, after the DEV result): NOT RUN, never frozen.**
> - This plan was drafted while the DEV replay was running, before its result was seen.
> - The registered DEV rule (`PROTOCOL_FR_DEV.md`) then failed at C-GEO (+0.0045 [−0.0016] against ≥ +0.010 with LCB > 0), which closes the task.
> - No `freeze/FR_MANIFEST.json` was made and no fresh unit ran. The fresh IDs below stay unused.
> - The text is kept unchanged below for transparency.

This text and `freeze/FR_MANIFEST.json` were to be committed and pushed before the first fresh unit runs. Every fresh worker would check the manifest (SHA-256) before its first unit.

**Evidence label:** fresh splits and startups of the same 541-run pool. This is not new physical data, not a new independent region and not external validation.

## Systems

| key | definition | role |
|---|---|---|
| GATE | GATE + margin on its own path (`src/fr_gate.py` run_gate) | candidate |
| C1 | C1 + margin on its own path (`src/ea_fwd.py` unit_X, unchanged) | main method |
| A | HA_LEAN + margin on its own path (`src/rc23_common.py` run_arm, unchanged) | reference |
| D_on_A | HA_TREND (ML-II) on A's path (`src/el_mix.py` mix_state p_T) | the registered strong alternative (EL / EA definition) |
| AVG_on_G | fixed w = 0.5 at GATE's paid data | control: is the local rule needed? |
| C1_on_G, A_on_G | C1 and HA_LEAN at GATE's paid data | model-versus-path split |
| A_on_C1 | HA_LEAN at C1's paid data | model-versus-path split |

The candidate, its constants and the code are unchanged since `PROTOCOL_FR_DEV.md`.

## Fresh IDs (inventory: `freeze/ID_INVENTORY.json`)

Used so far: STD up to 382 (gaps 59–66 stay unused), K5 startups up to 48, K4 startups up to 32.

| design | IDs | learners | clusters |
|---|---|---|---|
| STD | repeats 383–406 × 5 folds | 120 | 24 |
| K5 | startups 49–60 × 5 regions | 60 | 12 |
| K4 | startups 33–44 × 4 regions | 48 | 12 |

- Each learner has three units (G, X, L): 684 units in all.
- **Dependence:** the K5 and K4 test regions are the same fixed k-means regions for every startup. A new startup changes the paid path, not the test set. Geometric uncertainty is therefore path variability over 24 startup clusters; a block startup is not a new region.
- STD learners of one repeat share the split, so the repeat is the cluster.

## Metrics

- **BA:** threshold 0.5.
- **BA-AULC:** the mean over budgets 8..24, 25..60 or 8..60.
- **Blocks:** per region, i.e. the mean over a startup's regions that contain both classes, then the difference per startup cluster. K5 and K4 clusters are pooled for the geometric verdict, and are also reported separately.
- **Targets 0.90 / 0.93 / 0.95** (STD):
  - first attainment;
  - confirmation: first b ≤ 56 with BA(b) ≥ τ and BA(b + 4) ≥ τ;
  - spend = confirmed b + 4, counting the 8 startup simulations;
  - attained and not attained;
  - kept: BA(60) ≥ τ;
  - sustained: BA ≥ τ at every budget from the confirmation to 60.
- The restricted mean capped at 61 is a learning-speed score, not a cost.
- **Statistics:** cluster means; one-sided 95 % t-bounds over clusters; a bootstrap check (10,000 resamples, seed 2024).

## Registered verdicts (GATE − C1, own paths, end to end)

**V-GEO (primary development target):** geometric per-region BA-AULC B8–B60.

| result | status |
|---|---|
| LCB > 0 and mean ≥ +0.010 | GEO_GAIN_SHOWN+PRACTICAL |
| LCB > 0 only | GEO_GAIN_SHOWN |
| otherwise | NOT_SHOWN |

**V-EARLY:** STD BA-AULC B8–B24, LCB > −0.003, gives EARLY_NONINFERIOR (C1's early advantage kept). The 0.003 margin is the C1C margin, not relaxed.

**Harm limits, GATE − C1:** all must hold for HARM_OK.

| quantity | limit |
|---|---|
| STD late BA-AULC B25–B60 | LCB ≥ −0.003 |
| STD Keyhole recall and conduction recall, AULC B8–B60 | each LCB ≥ −0.005 |
| STD restricted-mean spend at 0.90, 0.93 and 0.95 | saving LCB ≥ −1.0 simulation |
| STD Δattained(0.95) and Δkept(0.95) | each LCB ≥ −0.05 |
| K5 alone and K4 alone, per-region B8–B60 | no loss shown (UCB < 0 is a failure); a gain on one design may not hide a loss on the other |

These are the C1S / C1C limits. None is relaxed.

**Hard group (STD; evaluator descriptors only):** short-Keyhole NEW recall and NEW conduction specificity are kept separate.
- **IMPROVED:** one rises (LCB > 0) without the other showing a loss.
- **TRADE_OFF:** one rises while the other falls (UCB < 0). This does not count as a solution.

**Control (is the local rule needed?):** GATE − AVG_on_G at identical paid data. "Needed" means:
- the geometric B8–B60 or the STD B8–B24 difference has LCB > 0;
- and neither shows a loss.

**Reported:**
- GATE − A, C1 − A, D_on_A − C1, D_on_A − A and GATE − D_on_A;
- the model and path split on GATE's path (GATE − C1_on_G; C1_on_G − C1);
- log loss and Brier (supplementary);
- the pooled block BA;
- CPU, and simulations per method and as a union of shared runs.

## Use decision (fixed now)

1. **ADOPT_GATE_FOR_GEOMETRIC_ROBUSTNESS** if all hold:
   - V-GEO = GEO_GAIN_SHOWN+PRACTICAL;
   - V-EARLY = EARLY_NONINFERIOR;
   - HARM_OK.

   Then GATE + margin is recommended where prediction outside the paid region matters. In-pool it is non-inferior to C1, and it equals C1 below b = 16 by construction. C1 + margin remains the frozen reference.
2. **GATE_EVIDENCE_FOR_BLOCK_EXTRAPOLATION_ONLY** if V-GEO is GEO_GAIN_SHOWN (any size) and V-EARLY holds, but the practical size or a harm limit fails. GATE carries evidence only for that limited use, and C1 stays unchanged as the learner.
3. **KEEP_C1_UNCHANGED** otherwise.

A successful part is never widened into general superiority. No claim of guaranteed 0.95 keeping or of safe stopping in real use is made.

## Time and stopping rules (fixed now)

- Projected wall time: about 684 units at about 24 s CPU each over 3 workers, roughly 90 min.
- The fresh test is launched only if its projected end plus 60 min is before 19:31:37 UTC, and it starts by 16:45 UTC.
- Workers carry `RC18_DEADLINE_UTC = 2026-10-29T18:15:00Z`: no unit is claimed after it.
- If the test is incomplete at that point, it is reported as incomplete. It is never presented as a finished test, and it is never extended.
- There is no size increase, no rule change and no new candidate after any fresh result.
