# Branch provenance and deletion eligibility

Candidate canonical commit: `e02e15c4903c4bebe5da0ccbf3033ba358a1c6fb`.

A `true` eligibility value is conditional on the final validation PASS and verified publication of this exact candidate or its descendant to remote `main`.

| Branch | Scope | Remote tip | Unique paths before import | Reachable now | Missing now | Disposition | Eligible after PASS |
|---|---|---:|---:|:---:|---:|---|:---:|
| `codex/archive-week3-named-benchmark` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/external-masinelli-feasibility-audit` | remote_and_local | `8d99c1976890 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/thesis-complete-consolidation` | local_only | `- ` | 3917 | true | 0 | RETAIN_UNTIL_MAIN_VERIFIED_THEN_DELETE | false |
| `codex/thesis-unified-project` | remote_and_local | `5b7d030413ed ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week10-pg-rmbc-internal-replication` | remote_and_local | `a380aeb07f63 ` | 1532 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week3-4d-benchmark` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week4-chronology-restructure` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week5-first-conduction-gp` | remote_and_local | `1751286bb0da ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week6-1-optimized-gpc` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week6-phase1-melt-pool-data-audit` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week6-phase2-5-depth-closure` | remote_and_local | `b112f6b22898 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week6-phase2-gp-response-models` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week6-phase3-5-regime-target-design` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week6-phase3-model-target-robustness` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week6-phase4-new-outputs-feature-effects` | remote_and_local | `cba151880fc6 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-1-gpc-sur-validation` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week7-boundary-weighted-sur` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week7-comprehensive-presentation` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week7-phase1-2-sph-v2-audit` | remote_and_local | `7ab7ada0c896 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase3-new-data-model-stability` | remote_and_local | `1118d30f3199 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase4-new-data-feature-effects-depth-diagnostics` | remote_and_local | `5b7004017cad ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase5-5-g3-robustness-transfer` | remote_and_local | `6cc2ea150b9d ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase5-keyhole-physical-proxy-analysis` | remote_and_local | `3367f4c9b5af ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase6-real-data-boundary-active-level-set` | remote_and_local | `5734de6f533e ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week7-phase7-final-boundary-hybrid-benchmark` | remote_and_local | `167aad945b20 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week8-5-frozen-sample-efficiency-confirmation` | remote_and_local | `6487722fe5e6 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week8-definitive-sample-efficiency-presentation` | local_only | `- ` | 0 | true | 0 | LOCAL_ONLY_NO_REMOTE_DELETION | false |
| `codex/week8-final-sample-efficiency-thesis-consolidation` | remote_and_local | `401b51c3da96 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-no-phase-controls-r-and-d` | remote_and_local | `9c487d61ced8 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-10-closure-diagnostics` | remote_and_local | `e33cca4f81b8 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-10-external-experimental-validation` | remote_and_local | `45e2677b7a57 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-11-fixed-mean-discrepancy-gp` | remote_and_local | `5a21e5dce37f ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-12-gpc-kernel-adequacy` | remote_and_local | `161453983996 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-13-fixed-physics-ard-discrepancy` | remote_and_local | `fbe76352f865 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-14-m3-margin-acquisition` | remote_and_local | `5a7a6c05ae5b ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-15a-physics-residual-signal-audit` | remote_and_local | `a8eafbbb814f ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-16-m3-repulsion-scale-audit` | remote_and_local | `746b19153f37 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-17a-physics-contour-geometry-audit` | remote_and_local | `2acdb9aba6bb ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-18a-level-set-acquisition-compatibility-audit` | remote_and_local | `658d5b73cf27 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-18b-prospective-global-gpc-sur-benchmark` | remote_and_local | `255207857d22 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-18b0-fast-gpc-sur-update-validation` | remote_and_local | `1e34b4759037 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-19a-integrity-posterior-monotonicity-audit` | remote_and_local | `2975e72326f1 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-19b-prospective-robust-monotone-pool-lse` | remote_and_local | `7c2c45f7f152 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-20-m3-g3-margin-acquisition` | remote_and_local | `49a054e3f80b ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-5-h-physics-confirmation` | remote_and_local | `b36a815e12df ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-7-physics-ridge-residual-gp` | remote_and_local | `2f750c8c270b ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-8-model-path-decomposition` | remote_and_local | `f74c6252bbb4 ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-9-physics-specificity-control` | remote_and_local | `0df38fd5492d ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase1-close-week8-sample-efficiency` | remote_and_local | `bdb6eb3628ae ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `codex/week9-phase2-temporal-width-dynamics` | remote_and_local | `da913797d14b ` | 0 | true | 0 | DELETE_AFTER_REMOTE_MAIN_PASS | true |
| `main` | remote_and_local | `5b7d030413ed ` | 0 | true | 0 | RETAIN_CANONICAL | false |

Exact commit lists, unique paths, canonical destinations, PR state, and reasons are in `BRANCH_PROVENANCE.csv`. Historical branches with zero initially unique paths were already preserved by the previous content-addressed union and ancestry merge. PG-RMBC's initially unique paths were imported at their original paths and its actual branch ancestry was merged.
