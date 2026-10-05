# Week 18 Phase 0 — red-team of "G3 + margin is the defensible endpoint"

Each assumption behind the Week 12–17 endpoint, ranked by how badly it could mislead, with the test that
will be run. Status is updated as tests complete (pointer in RESEARCH_LOG.md).

| Rank | Assumption | Why it could mislead | Test | Status |
|---|---|---|---|---|
| 1 | **The binary label is the right observation.** | Every paid simulation also returns continuous outputs. On OLD, has_keyhole = 1[max_depth ≥ ≈ 111 µm] (AUC 1.000; all KH ≥ 111.2, all non-KH ≤ 111.6 µm, consistent across partitions/settings). Week 7 Phase 6 found max-depth GPR + straddle > binary on BA AULC (+0.026, CI > 0) but kept "HYBRID / NO CLEAR WINNER" because of q20 and a transfer floor. A binary GPC may waste most of each query. | Regression level-set estimation on depth (OLD real; digital twins with continuous truth); NEW needs its monitors (owner decision D1). | open — top priority |
| 2 | **NEW is a separate test campaign and OLD→NEW is a "level shift".** | OLD itself mixes three partitions and two simulator-setting groups (41 runs TE 0.00125 s, 27 runs other domain); the time-step rule differs between OLD and NEW; NEW sits in a different region (P 350–450, ST ≤ 500, LS 40–50 µm). The "shift" may be region/extrapolation or settings, not campaign. | Phase 1: overlap-region label consistency; pooled GPC with and without a campaign offset; physics thresholds in the overlap. | running |
| 3 | **The NEW "exploration beats margin" exception is real.** | Week 15 (fixed OLD hyperparameters) showed random − margin ≈ −0.021; Week 17 (per-step ML-II) +0.020 with different seeds. It may be an ML-II × margin interaction (biased hyperparameters under margin designs) or seed noise. | Factorial hyper × seeds × rule on NEW (open item a). | running |
| 4 | **Our synthetic worlds represent the real problem.** | Weeks 13–17 generators were designed by us; Week 17's development worlds were built on the physics score (LT +0.044 dev vs +0.009 held-out). Rankings on our worlds may not predict real rankings. | Phase 2 external-validity check: do S1 (digital twins fitted to real labels/depth) and S2 rankings predict R1–R3 rankings for the baselines? | planned |
| 5 | **q20 and NSD measure what matters.** | q20 rewards conservative majority predictions under imbalance (Week 13/Astra §5.3); NSD on our own worlds depends on our generators. | Report queries-to-target and BA alongside; q20 kept historical. Digital twins give NSD on a realistic truth. | planned |
| 6 | **Tiny pools (108/136) and budgets 16–80 are the right regime.** | At B80 a 108-pool is 74% labelled; random ≈ exhaustive. Differences between rules shrink by construction; NEW's exploration effect may be a pool-exhaustion artefact. | POOLED (≈ 541) and digital twins with large pools; budgets to 120; queries-to-target. | planned |
| 7 | **Hyperparameter treatment is neutral.** | Per-step ML-II on margin-selected (boundary-concentrated) data biases length-scales/amplitude; fixed transferred hypers carry OLD's geometry. | Portfolio A + open item a. | running/planned |
| 8 | **The physics coordinate log h is the right physics.** | Pooled logistic exponents (−0.59, −1.34 vs −0.5, −1.5); NEW is VX-dominated. | Phase 1 + portfolio C/D. | planned |
| 9 | **Labels are deterministic and uncontaminated.** | Frame-level labels; "any Keyhole frame" depends on run length (TE) and on screenshot bugs (49 NEW runs withheld). | Settings-group analysis; Bug runs stay out. | partly done |

## Open items from the brief (verification)
- (a) NEW exception vs hyperparameter treatment — factorial running (`src/week18_open_items.py`).
- (b) Week 17 report: the mean M3 − G3 over held-out cells is **−0.102**, not −0.110 (recomputed from the
  per-cell values in VERDICT.json). Erratum E18-1 (ERRATA.md).
- (c) Week 17's MECHANISM RESOLVED rule mixed a robustness requirement for LT (|LT − G3| ≤ 0.015 in H08)
  into a mechanism criterion. The Week 17 verdict stays as frozen; Week 18 decision rules keep mechanism and
  robustness criteria separate.
- (d) Week 17 development optimism: development worlds were built on the physics score (dev generator =
  KAPPA·(physics − c) − bump). Week 18 development data must include physics-off and physics-imperfect worlds.
