# Week 8.5 critic audit

Audit role: adversarial verification of the frozen confirmation evidence. No benchmark trajectory and no bootstrap draw was rerun. All arithmetic below was independently reconstructed from the saved trajectory/checkpoint tables or recomputed from the already-saved bootstrap draws. No result artifact was modified.

## Verdict

**No result-changing scientific or computational bug was found.** The saved decision ledger is correct:

| Claim | Point estimate | One-sided 95% lower bound | Required condition | Audit decision |
|---|---:|---:|---|---|
| Margin vs Random B1-q20 AULC 16–80 | +0.037300 | +0.031270 | lower bound >= 0.020 | **PASS** |
| Restricted-horizon query saving | +20.099 queries | +13.90995 | lower bound >= 10 and rho_random >= .95 | **QUALIFY** |
| Restricted-horizon multiplier | 1.5144x | 1.3292x | lower bound >= 1.25 and rho_random >= .95 | **QUALIFY** |
| Repulsion h=.15, minimum of full/low-budget endpoints | +0.001829 | -0.000625 | simultaneous lower bound >= 0.010 | **QUALIFY** |
| Overall primary confirmation | — | — | performance, saving, and multiplier all PASS | **NOT_CONFIRMED** |

The query-saving and multiplier bounds exceed their numeric thresholds, but Random still has only `rho_random(160)=0.831`. The preregistered censoring gate therefore forces both claims to remain **QUALIFY**. They must not be promoted to PASS.

## Independent arithmetic from saved raw results

### Primary AULC and repeat stability

Reintegrating every saved integer-grid B1-q20 trajectory from budgets 16–80 with `trapezoid(accuracy,budget)/64` gave:

- Margin mean AULC: **0.8135202206**.
- Mean of the 30 matched Random continuations within each outer fold, then mean across folds: **0.7762204350**.
- Primary contrast: **+0.0372997855**, exactly matching the ledger.
- All **20/20** repeat-level contrasts were positive. Repeat contrast median was **0.0407093**, range **0.0088143 to 0.0675153**, and IQR **0.0223736 to 0.0468436**.
- Leave-one-repeat-out primary estimates ranged only from **0.0357095 to 0.0387990**. The primary effect is not driven by a single repeat.

### Budget-40 boundary performance and class metrics

Direct aggregation of the saved budget-40 rows gave:

| Endpoint | Margin | Random | Margin - Random |
|---|---:|---:|---:|
| B1-q20 accuracy | 0.817059 | 0.774510 | **+0.042549** |
| B1-q30 accuracy | 0.870800 | 0.828760 | **+0.042040** |
| B1-q20 recall | 0.711044 | 0.606751 | +0.104293 |
| B1-q20 balanced accuracy | 0.797113 | 0.740758 | +0.056354 |
| B1-q20 mean false negatives per fold/continuation | 1.910 | 2.547 | -0.637 |
| B1-q20 mean false positives per fold/continuation | 1.200 | 1.287 | -0.087 |
| B1-q30 recall | 0.752739 | 0.644707 | +0.108032 |
| B1-q30 balanced accuracy | 0.839690 | 0.779801 | +0.059888 |

Each B1-q20 test subset contains 17 rows. Its Keyhole count ranged from 3 to 10 across the 100 folds, with mean prevalence **38.94%**. Accuracy is therefore exactly equal under macro and pooled aggregation here because every fold/continuation has the same denominator. Recall and balanced accuracy are explicitly reported and should remain beside accuracy.

### Persistent crossings and censoring

Reapplying the preregistered “target plus next two declared checkpoints” rule to saved trajectories produced:

| Horizon | Finite Random crossings | rho_random |
|---:|---:|---:|
| 80 | 2201 / 3000 | 0.733667 |
| 120 | 2394 / 3000 | 0.798000 |
| 160 | 2493 / 3000 | 0.831000 |

At H=160, Margin had 91/100 finite persistent crossings and Random had 2493/3000. Restricted crossing means were **39.070** for Margin and **59.169** for Random, yielding **20.099** saved queries and a **1.5144356x** burden ratio. The finite-only medians (Margin 22, Random 24) are not substitutes for these restricted-horizon estimands because censoring differs materially.

### Repulsion endpoint and mechanism audit

Saved trajectories independently give repulsion-minus-margin AULC contrasts of:

- Full 16–80: **+0.00182904**; 13/20 repeat contrasts positive, repeat range -0.00625 to +0.01103.
- Low-budget 16–40: **+0.00261029**; 12/20 repeat contrasts positive, repeat range -0.01740 to +0.02843.
- Saved simultaneous bootstrap-minimum 5th percentile: **-0.000625**.

All 14,400 repulsion selections recorded exactly `h=0.15`. Repulsion and margin selected the same row in 81.33% of low-budget steps and 30.06% of all steps; all 100 runs eventually diverged, at a median first divergence budget of 39. In the low-budget window, mean selected distance to the queried set was 0.9516 and only 7.5% of repulsion selections accepted normalized uncertainty below 0.99. Across the full horizon those values were 0.6556 and 60.45%, respectively. This is evidence that the fixed repulsion score eventually trades some uncertainty for distance, but the performance increment is small and not simultaneously robust. **QUALIFY**, not “repulsion confirmed,” is the correct statement.

### Bootstrap implementation and stored quantiles

The code resamples 20 repeat IDs with replacement, retains all five folds for each selected repeat, and resamples 30 Random continuation IDs within each selected fold. It computes fold-matched contrasts before averaging. This matches the preregistered hierarchical repeat-block design and does not treat 100 folds or 3000 continuations as independent physical campaigns.

Recomputing percentiles from the 20,000 saved draw rows reproduced every reported bound (floating-point differences below 1e-15):

| Estimand | Saved-draw mean | 5th percentile |
|---|---:|---:|
| Delta AULC | 0.03730960 | 0.03127034 |
| Delta Q | 20.0876813 | 13.9099500 |
| Multiplier | 1.5210948 | 1.3292101 |
| Repulsion AULC 16–80 | 0.00181829 | 0.00051448 |
| Repulsion AULC 16–40 | 0.00258916 | -0.00062500 |
| Repulsion endpoint minimum | 0.00160190 | -0.00062500 |

The small difference between the direct point estimates and bootstrap-draw means is ordinary Monte Carlo resampling variation; the ledger correctly uses direct point estimates and bootstrap percentile bounds.

## Twenty-risk adversarial register

| # | Risk | Status | Evidence and correction |
|---:|---|---|---|
| 1 | Train/test leakage | **PASS** | Model scaling is fit on the 324-row training pool, GPC fits use queried training rows, acquisition candidates are training-only, and predictions are evaluated on the 81 untouched test rows. B1 is a label-derived evaluation stratifier over the frozen population; it does not enter fitting or acquisition and must not be described as an unlabeled deploy-time boundary detector. |
| 2 | Test labels into acquisition | **PASS** | Test labels are referenced only in post-selection metric computation. Candidate selection receives probabilities, scaled pool inputs, and queried indices—not test labels. |
| 3 | B1/B2/B3 scores into acquisition | **PASS** | B1 flags are built outside acquisition and never passed to the chooser. Checkpoint mechanism records consistently declare `B1_available_to_acquisition=false`. |
| 4 | Old seed reuse | **PASS** | All 317,120 complete seed keys use the new `week8_5_frozen_confirmation|v1` namespace; zero keys contain `6022026`, `primary_common`, or `shared_pool_permutation`. All 20 split partitions are distinct. |
| 5 | Warm starts / initial designs | **PASS** | Every run has exactly 16 unique feature-only maximin queries, shared across all arms. Each contains both classes (2–7 Keyhole rows), and no old warm-start trajectory is reused. The saved manifest has zero `hidden_label_used_for_selection=true` rows. |
| 6 | Duplicate Random seeds | **QUALIFY** | The 3000 Random-order keys and their 32-bit seeds are all unique. Across the full 317,120-entry registry, however, 12 pairs of distinct fit keys collide after reduction to 32 bits (nine Random-fit/Random-fit pairs and three cross-arm pairs). All saved fits are `optimized_primary`, the collisions occur on different data/budgets, and no duplicate order results, so this is not evidence of duplicated trajectories or a changed headline. Still, future registries should either validate `seed_u32` collisions explicitly or retain a wider seed. |
| 7 | Duplicate Random orders | **PASS** | Each of the 100 runs has 30/30 distinct full Random continuation orders; zero within-run duplicate order hashes were found. |
| 8 | Fold construction | **PASS** | There are 100 unique 81-row test-fold memberships; every fold has 324 train and 81 test rows, with exact group disjointness. |
| 9 | Repeat construction | **PASS** | All 20 five-fold partition hashes are distinct, and every one of the 405 rows appears exactly once as test data within each repeat. |
| 10 | Pseudoreplication | **QUALIFY** | The hierarchical bootstrap correctly treats repeats as blocks and nests Random continuation uncertainty, but all repeats repartition the same 405 saved simulations. Inference concerns this population plus split/acquisition randomness, not 20 independent physical campaigns. |
| 11 | Target preregistration | **PASS** | Targets .75/.80/.85, with .80 primary, are in the canonical protocol whose SHA-256 was recorded before the first full-horizon report. No target-dependent adaptive decision is used except the preregistered Random .80 finite fraction. |
| 12 | Budget/grid preregistration | **PASS** | AULC 16–80 uses every integer budget; post-80 checkpoints are exactly 82:2:120 and 124:4:160. The adaptive rule extended all 3200 trajectories uniformly at both gates. |
| 13 | Censoring | **PASS** | Non-crossings remain right-censored and are mapped to H only in the explicitly restricted burden estimands. `rho_random` is reported before restricted means; no interpolation or extrapolation is used. |
| 14 | AULC orientation | **PASS** | Direct integration of saved accuracy—not error—reproduces Margin 0.813520, Random 0.776220, and positive Margin-minus-Random contrast +0.037300. Higher is better. |
| 15 | Accuracy/error sign | **PASS** | Budget-40 accuracy and class-count reconstruction agree, and the ledger uses Margin minus Random. No error-to-accuracy sign inversion was found. |
| 16 | Fair Margin-vs-Repulsion comparison | **PASS** | Both arms share identical 16-row prefixes in all 100 runs, use the same split, GPC implementation, budget grid, and one trajectory per run; only acquisition rule and its declared arm-specific seed namespace differ. |
| 17 | No h tuning | **PASS** | Source, protocol, seed keys, and all mechanism records contain only `h=0.15`. No alternate bandwidth result appears in the consumed confirmation evidence. |
| 18 | Pooled vs macro confusion | **PASS** | The primary estimand is fold-macro after averaging Random continuations within fold. Equal q20/q30 denominators make pooled and macro accuracy identical; recall/BA are reported as macro metrics and are not substituted for the primary accuracy AULC. |
| 19 | Imbalance / domain shift | **QUALIFY** | The population is imbalanced (73/405 Keyhole), while B1-q20 is boundary-enriched (mean 38.94% Keyhole, fold range 3–10 of 17). Recall and balanced accuracy support the direction of the budget-40 effect. No external population or prospective domain shift is tested, so the result cannot be generalized beyond the frozen 405 rows. |
| 20 | Repeat stability / outlier drive | **PASS** | All 20 repeat contrasts are positive; the smallest remains +0.00881. Leave-one-repeat-out estimates stay in 0.03571–0.03880, excluding single-repeat drive. |

## Validation and provenance qualifications

1. `validation_report.json` labels the information-flow check PASS, but the implementation sets that particular check to literal `True`; it is declarative rather than executable. This critic audit supports the conclusion through source inspection and saved mechanism fields, not through that validator alone.
2. The built-in AULC orientation check integrates budget against budget. It checks trapezoid direction mechanically, but does not independently detect an accuracy/error sign swap. The direct saved-trajectory reconstruction above supplies that missing check.
3. `run_manifest.json` contains 39 output-file hashes; all **39/39** were independently verified over 979,898,326 bytes with zero missing files or mismatches. However, `source_hashes_json` omits the Week 8.5 driver itself. The currently audited driver SHA-256 is `ada5a4a116592590287b429e6e3995cfe399c24a4cec09d95d90e37f38dd4629`. This should be added to provenance in any future regenerated package, without altering the frozen numerical outputs.
4. The 32-bit seed-collision finding above is not captured by the current `seed_key_uniqueness` validator, which checks complete keys only. It does not affect the 3000 unique Random orders, but should be made explicit rather than described as zero seed collisions.

## Safe thesis-facing conclusion

On the frozen 405-row saved-simulation population, uncertainty-only Binary GPC margin acquisition has a stable, preregistered B1-q20 accuracy-AULC advantage over 30 matched Random continuations per fold. The primary performance claim passes. Query burden is directionally and statistically lower under the restricted H=160 estimand, but persistent Random crossings remain too censored (`rho_random=0.831`) for confirmatory query-saving or multiplier claims. Fixed-h=.15 repulsion is only a small, non-simultaneously-robust qualification. These are empirical boundary-subset and split/acquisition-randomness results, not causal evidence, prospective simulator validation, external-domain validation, or physical-boundary certainty.

## Post-correction re-audit — 2026-08-26

**Status: PASS WITH QUALIFICATIONS; scientific verdict unchanged.** This round inspected only the corrected driver validation/figure paths, focused tests, validation/provenance/runtime reports, manifest, and six visual derivatives. It did not rerun trajectories or bootstrap draws.

- All **22/22** frozen numerical/result artifacts checked against their pre-correction SHA-256 values are unchanged, including trajectories, run/checkpoint/repeat metrics, crossings, query summaries, decision ledgers, seed/split/design manifests, and bootstrap draws/summaries. There is **no scientific result drift**.
- The refreshed run manifest contains **41 artifacts**. All entries, byte counts, and SHA-256 values verified before this mandated audit-file update; the audit/provenance linkage is refreshed after this append so the final package remains internally consistent.
- The new information-flow validator is executable within its declared scope: it checks all 3,200 saved checkpoints and 460,800 mechanism records against the persisted train/test split membership and uniqueness constraints, checks guard fields, rejects forbidden B1/B2/B3/hidden-label chooser fields, and AST-checks the sole chooser call's keyword inputs. It does **not** replay acquisition or prove behavior internal to the imported Phase 6 chooser; that dependency remains pinned by source hash. This scope is adequate for a post-run saved-artifact validation, not a formal whole-program noninterference proof.
- Seed wording is now correct: complete keys remain unique; Random-order keys and uint32 values are **3000/3000 unique**; the **12 distinct fit-seed uint32 collision groups remain explicitly QUALIFY**. They are not duplicate Random orders and do not change the saved result.
- Driver and focused-test SHA-256 values match `postrun_provenance_addendum.json`. The three new bounded tests for chooser-source inputs, seed-collision qualification, and one persisted-checkpoint/split audit pass **3/3**.
- All six runtime-listed figures exist, decode as RGBA PNGs, have dimensions from 1367x1030 to 1779x1077 at approximately 220 dpi, and are readable on visual inspection. Figure 3 and Figure 4 retain code-style arm/metric labels with underscores; this is a presentation polish limitation, not a scientific or computational defect.

### Final mechanism-completeness recheck

**Status remains PASS WITH QUALIFICATIONS; no result drift.** The completed mechanism derivative contains exactly **28,800** unique `(run, arm, selection budget)` rows: 14,400 Margin and 14,400 repulsion rows, comprising budgets 17–160 for all 100 matched runs. Independent reconstruction from the 200 saved active-arm checkpoints reproduced every selected index and recorded mechanism field; sequential nearest-standardized-distance differences were at most `2.22e-16`.

All four mechanism summary rows reproduce independently from checkpoint histories. At budgets 17–40, repulsion increases mean nearest-query distance by **0.0099602**, reduces mean selected uncertainty by **0.0048296**, selects the same row as Margin on **81.33%** of steps, and 58/100 runs diverge by budget 40 (median first divergence 32). Across 17–160, the corresponding distance shift is **0.0051667**, uncertainty shift is **-0.0014159**, same-row fraction is **30.06%**, and all 100 runs diverge (median first divergence 39). These diagnostics strengthen mechanism completeness but do not change the small, non-simultaneously-robust repulsion performance conclusion.

The new `06_selected_query_nearest_distance.png` exists, decodes as a 2285x1044 RGBA PNG at approximately 220 dpi, is visually readable, and is listed by the runtime report. The focused mechanism schema/count test passes. Frozen performance, trajectory, crossing, and bootstrap hashes are unchanged, and the corrected package manifest verifies **43/43** artifacts. The only standing qualification remains the explicitly reported 12 fit-seed uint32 collision groups; Random orders remain 3000/3000 unique.
