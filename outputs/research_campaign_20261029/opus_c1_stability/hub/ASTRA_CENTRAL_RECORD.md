# Astra campaigns: central record completed from the published Research Hub

**Status: SOURCE-TRANSFERRED.** Every statement below is copied, with its scope and limits, from the read-only published Research Hub on `main` 4fc9b5d50308f29013b7844ec39090b257aa713d (`docs/research/CLAIM_LEDGER.csv`, `docs/research/EXPERIMENT_REGISTRY.csv` and the campaign reports named below).
- Nothing here was recomputed by Opus, and none of it is an independent finding of this task.
- Astra's live folders, Git, environment and processes were not touched.

**Why this file exists.** Before this task, the thesis' central records had no row for these four Astra campaigns:
- `docs/alse/claims.md`, `experiments.md`, `decisions.md`: none of the four;
- the progress log: only a short LC24 hand-off entry;
- the attempt ledger: RP20 mentioned only.

**Common scope.** All four are synthetic latent-monitor studies. They are distinct from physical Keyhole labels and from the C1C in-pool evidence; the Hub's scientific navigation states this.

| campaign | original Astra commit | report (Hub path) | claims (Hub IDs) | experiments (Hub IDs) |
|---|---|---|---|---|
| AD18 deep discovery (2026-10-18) | 833211403b50051e1bee25c8af38de8443e154b4 | `research/astra/astra_deep_discovery_20261018/FINAL_REPORT.md` | AD18-001, AD18-002 | AD18-DEV-V1.1, AD18-DEV-V2, AD18-TEST-V2, AD18-QUOTA-TEST |
| RP20 representation planning (2026-10-20) | 797654d1aad53f28139db1ff994a6602096b7801 | `research/astra/astra_representation_planning_20261020/FINAL_REPORT.md` | RP20-001, RP20-002 | RP20-TEST-V1 |
| LC24 local correction (2026-10-24) | 3b3eb1f5cc596b30d445b0ecc59ac6baa71c98f2 | `research/astra/astra_local_correction_20261024/FINAL_REPORT.md` | LC24-001, LC24-002 | LC24-DEV-V1, LC24-DEV-V2 |
| JL26 joint local (2026-10-26) | a71c638ac9338297021bfc5ba75bd73b1aa0cb9c | `research/astra/astra_joint_local_20261026/FINAL_REPORT.md` | JL26-001, JL26-002 | JL26-DEV-V1, JL26-TEST-V1 |

## Transferred findings

These are the Hub's wording and status, condensed.

**AD18**
- **Statement:** local surprise / regional acquisition did not establish aggregate improvement or query savings; small islands remain poorly learned. Status NEGATIVE_OR_UNRESOLVED_ACQUISITION_RESULT.
- **Structural covariance alternatives:** they address the tested coordinate-anisotropy failure. Status SCOPED_SYNTHETIC_MODEL_FINDING.
- **TEST:** 336 worlds in 14 families, 10,224 trajectories (not independent realizations). Status COMPLETE_NO_GENERAL_ACQUISITION_GAIN.
- **Quota control:** equal local share, 28 of 56 queries.

**RP20**
- **Statement:** neither the local representation nor bounded two-step planning established a general gain. Status COMPLETED_WITH_PRESERVED_OPERATIONAL_FAILURES.
- **Incomplete paths:** 3 of 4,096 learned paths are incomplete (PermissionError), kept, not retried and not imputed, so there is no clean primary pass.
- **Model finding:** a same-paid-data prediction advantage of learned GP length scales is a separate scoped finding. Small-island harm coexists, and there is no query-saving claim.

**LC24**
- **Statement:** both prospective local-correction DEV expansion screens failed (32 DEV worlds, 64 paid paths). Status DEV_SCREEN_NOT_PASSED.
- **V2:** reuses the same worlds and paths, so its units are not independent.
- **Scope:** no independent TEST and no local-model acquisition experiment were run. Status EXPLICIT_NOT_RUN_BOUNDARY.

**JL26**
- **Statement:** joint global/local fitting gives a positive independent synthetic model increment (144 fresh worlds, 288 dependent matched paths). Status POSITIVE_MODEL_EFFECT_PRACTICAL_GATE_NOT_PASSED.
- **Against the practical gate:** +0.402 pp against fixed local, while +0.50 was required; the interval includes the threshold.
- **Limits:**
  - regional harms remain;
  - query savings are unresolved;
  - confirmed attainments 109/65/25 vs 107/64/24;
  - about 3.02 vs 1.05 CPU s per path;
  - no acquisition expansion.

## Relation to this task (Opus C1S)

- **No Astra result is used as evidence for or against C1** (different data type).
- **Analogy noted, not combined:** JL26's distinction that attaining, sustaining and reducing simulation cost are separate claims matches this task's registered separation of stability, early BA and fewer simulations.
- **Astra's new independent module:** it was running or announced during this task. It was not waited for, not read live and not integrated.
