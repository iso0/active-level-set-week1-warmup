# OPUS_IMPLEMENTATION_REQUEST — bounded Week 19 DEV pilot

**Priority:** distinguish response-window improvement, threshold instability and unresolved morphology before adding temporal-GP complexity. This is a proposed implementation specification, not an executed experiment. Read `ASTRA_RND_MEMO.md` and `ASTRA_REVIEW_CHECKS.json` beside this file.

**POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE.** Base: `f3206f292f48db79d9c4af496e7c7aed40c0ce62`, branch `week19-temporal-audit`. Preserve original `has_keyhole`, all 541 eligible simulations, all historical outputs, the 49 withheld exclusions and the closed external campaign. C3 (repeats 17–20) remains reserved. No push or publication. Put new pilot artifacts in a distinct `outputs/week19_temporal_regime_dev_pilot/` directory; do not overwrite the audit.

## P0 — provenance, target contract and decision freeze

1. Read the pinned compact tables: `temporal_registry.csv`, `depth_definitions.csv`, `k_runs.csv`, `regime_switches.csv`, `separability.csv`, `representative_cases.csv`, `new_negatives_12_cases.csv`, `oof_E1_threshold_pull_by_fold.csv`. Resolve paths under `outputs/week19_temporal_regime_audit/`; record hashes. Reuse the existing raw cache only where a specific check needs it. Do not repeat bulk recovery.
2. Reproduce counts OLD 405/73, NEW 136/124, unique full simulation names, canonical label agreement, the one unavailable A target and two undefined K/(K+C) ratios. No join by H suffix. Preserve `H-e7dbd8e5ce` as an observed-label negative with unavailable temporal target, not proven Conduction and not a new exclusion.
3. Reproduce Astra's paired-cohort AUC/BA and oracle confusion from table values. At u=142.2322 µm, A must give TP/FN/TN/FP=114/10/11/0 and short-K sensitivity 1/10 on NEW. At u_ref=110.9641179189907 µm, common-cohort whole versus A must have FP 6 versus 5 and FN 1 in both. Tolerance 1e-10 for these table-derived rates.
4. Record that the fold table's maximum u is 309.619080770828 µm. Its membership flag alone does not prove acquisition. Check for existing paid-query logs; if absent, mark historical acquisition timing **unavailable** and leave the causal claim unresolved. Do not regenerate historical adaptive runs merely to reconstruct the logs.
5. Save `pilot_manifest.json` before any fit: base/code/input hashes, explicit DEV repeat allowlist `[1,2]`, original fold IDs, full population order, arm IDs, budgets `[16,40,80]`, target definitions, units, seeds, preprocessing, q20 source, decision thresholds, resource ceilings and failure rules. Record the initial C3-cache inventory for a final unchanged comparison. Construct only the allowed tasks; do not call a convenience runner that executes all blocks.

**Exact target:** retain the pinned valid-row/sentinel rules and `d_um=1e6*max(0,-z_min_m)`. `A=max(d_um)` over valid mapped rows with `t<=min(recording_end,0.9*(min(XF,XL)+12e-6)/VX)`. It retains startup and is an observed-window endpoint. No new first-C/K window, changed cutoff, repaired time array, tail extrapolation or geometry correction. B stays an annotation-dependent audit target. A pre-existing window constant does not make this target selection prospective.

Output `pilot_inputs.csv`, one row per eligible simulation, with:

`sim_id:str, campaign:{OLD,NEW}, partition:str, P_W, VX_m_s, LS_radius_m, ST_K, has_keyhole:int, whole_max_um, A_um:nullable, A_available:bool, A_failure:str, first_valid_ms, recording_end_ms, derived_exit_ms, active_cutoff_ms, early_end:bool, frac_K_FCK:nullable, frac_K_KC:nullable, n_K_frames:int, n_C_frames:int, source_revision:str, source_table_sha256:str`.

Null is unavailable, never zero. Keep settings/geometry as provenance, not extra undisclosed model coordinates. **Stop P0** for wrong populations, ambiguous joins, source drift, changed labels, or non-reproducing arithmetic; issue a discrepancy table without model work.

## P1 — identical paid paths, three learners, one primary comparison

**Scope:** R3_NEW only, all 136 eligible simulations. Use repeats 1–2 and all five folds from `outputs/week12_startup_and_transfer_development/audit/original_splits.json`, with the pinned `src/week18_tasks.py` population ordering. No NEW prior labels and no OLD warm start. OLD is descriptive reference only in this pilot.

**Path:** for each training pool call the existing `src.week13_synthetic_al.maximin_order` on raw `[P,VX,LS,ST]`, using `np.random.default_rng([1820,repeat,fold,2])`. That routine standardizes the raw four inputs within the pool. Save the first 80 IDs once, before revealing labels; use this entire fixed order rather than E1/G3 adaptive acquisitions. No seed selection, forced inclusion of the late negative, or reordering after outcomes. The shared path isolates learner/target differences; it is not an acquisition comparison.

At B16/B40/B80 fit:

| Arm | Response / model | Class mapping |
|---|---|---|
| `WHOLE_E1_SHARED` | Pinned `DepthGPR`, log whole-record maximum | Existing learned threshold from revealed valid depth/label pairs |
| `ACTIVE_E1_SHARED` | Same response model and optimization, log A | Same learned-threshold procedure on revealed valid A/label pairs |
| `G3_SHARED` | Pinned G3 binary GP classifier | Existing classifier probability |

Use existing learner-specific feature transforms and kernel bounds unchanged; all models keep ST. Response normalization is fitted only to revealed valid responses. Feature scaling may use the label-blind candidate pool exactly as the pinned engine does. A query supplies one simulation and its permitted complete output; all rows and unavailable responses still cost one query. An A-missing queried case contributes no invented regression target; its canonical label remains recorded, available to G3, and evaluated when held out. Log the smaller number of finite A pairs.

If a prefix or its usable depth/label pairs lacks both classes, mark that arm/checkpoint unavailable; do not use the engine's implicit 111 µm single-class fallback to manufacture comparability. Continue only to the already fixed larger checkpoints, counting all queries. A missing B40 result in any arm/fold prevents the primary advancement decision. No reseeding, interpolation of scores, extra queries or deletion of the affected simulation. Likewise stop the affected fit for nonpositive depth under the frozen log transform, nonfinite predictions, failed convergence or a nonpositive logistic slope; these are reported failures, not repaired models.

**Separate calibration from regression without extra GP fits.** For each fitted depth GP, additionally evaluate its fixed-u_ref probabilities from the same latent mean/variance as a labelled diagnostic. Using *observed held-out scalar values*, apply the training-prefix learned threshold as a separate **ORACLE RESPONSE — NOT DEPLOYABLE** diagnostic. Do not use those observed test responses to fit a threshold or calibrator. These two comparisons identify calibration and response-prediction contributions; they are not additional candidates in a winner search.

In the logistic branch, preserve C=1e6 and record intercept a, slope b and log u=−a/b. Log near-zero slope (`abs(b)<1e-6` in raw log-µm coordinates), roots outside the revealed depth range, class counts and actual acquisition index of the late negative. Do not clip roots, rebalance classes or substitute a new threshold estimator. Point-threshold uncertainty is a diagnostic limitation; do not add an unplanned hierarchical model. If a saved historical ledger exists, one scalar-only replacement of the revealed late negative's whole target by its A value may be reported as a post-hoc influence check, leaving the GP, labels and path unchanged. This does not identify physical causation.

Required outputs:

| File | Required fields / unit |
|---|---|
| `paid_paths.csv` | `task,repeat,fold,query_index,sim_id,path_seed,path_sha256`; one row per paid simulation; unique within path |
| `fit_diagnostics.csv` | `arm,repeat,fold,budget,n_paid,n_response_available,n_positive_pairs,n_negative_pairs,threshold_branch,a,b,log_u,u_um,root_outside_range,late_negative_revealed,late_negative_query_index,converged,status,wall_seconds,peak_memory_bytes` |
| `predictions.csv` | `arm,threshold_mode,repeat,fold,budget,sim_id,p_keyhole,latent_mean,latent_variance,response_available,prediction_status`; one held-out simulation per checkpoint; keep oracle rows in a separate file |
| `oracle_response_diagnostics.csv` | `target,repeat,fold,budget,sim_id,observed_score,training_threshold,predicted_label,status`; explicit oracle flag |
| `evaluation.csv` | Join canonical `y`, fixed `q20`, campaign, short-K group **only in the evaluator**, never the selector/learner |
| `metrics.csv` | `arm,contrast,budget,metric,estimate,lo95,hi95,n_unique_simulations,n_positive,n_negative,n_available,n_missing,scope` |

Meaningful checks: train/test ID disjointness; exact path equality across arms; no future-query response or label in fitting; identical q20 flags to the pinned evaluator/cache; one prediction per simulation per repeat/checkpoint; missing-target accounting; positive finite variances and probabilities in [0,1]; unchanged labels/eligibility/old artifacts/C3 inventory. Test these invariants and the target extraction fixtures; do not expand into a historical all-repository test campaign.

## P2 — evaluation, uncertainty and finite stopping rules

**Primary endpoint:** `ACTIVE_E1_SHARED − WHOLE_E1_SHARED`, q20 **accuracy** at B40, preserving the Week 18 mean-fold construction, averaged across the two repeats. q20 uses the original four-input nearest-opposite-class evaluator and its frozen IDs; it must not be redefined using A, temporal features or alternative labels. It is an evaluator-only historical boundary-proximity measure.

**Safeguards/diagnostics:** pooled-per-repeat BA, specificity over the 12 observed-label negatives, sensitivity over all positives and the fixed ten NEW positives with `0<K/(F+C+K)<.10`, Brier, AUC, and observed-response error where available. Report case counts, including `H-349225d53c` and `H-e7dbd8e5ce`. Short-K has one class: report sensitivity, never BA. Keep K/(K+C) and ≥5%/≥10% redefinitions in a separate descriptive sensitivity table, not another predictive search. B16/B80 are secondary checkpoints. Do not call a three-checkpoint area the historical AULC, estimate queries-to-target, or claim saved simulator queries.

For a paired interval, use 2,000 bootstrap draws with seed 191026, resampling unique simulations within original label strata and carrying each sampled ID's full paired predictions across folds/repeats. Recompute the stated aggregation; report any undefined draw and its reason. Keep q20 membership fixed. Show both repeat estimates and the twelve individual negative-case prediction summaries. This is a **conditional bootstrap interval given two sets of fitted historical DEV models**, not independent-fold replication, full refitting uncertainty or external confirmation. Do not bootstrap temporal rows as independent experiments.

**Advance only if all hold:** mean Δq20(B40)≥.01 and its paired 95% lower bound>0; mean pooled BA does not decline; ACTIVE short-K sensitivity is no more than .05 below either WHOLE or G3; all B40 comparisons available; checks pass. This is a newly proposed exploratory gate, not the old confirmatory replacement threshold. Otherwise record `NO_ADVANCE` or `INCONCLUSIVE`, retain original labels/models, and take the fallback. No extra repeats to narrow an inconvenient interval.

**Resource cap:** ≤90 learner fits, one optimization start per fit, ≤2 CPU threads, 8 GiB resident memory and four hours elapsed for P1–P2. Stop at the first exceeded cap or numerical/leakage failure and save the partial diagnostic log; no partial primary win claim. A reduced threshold-pull rate without q20/short-K benefit is a valid negative result.

## P3 — conditional temporal follow-up, not part of the initial 90 fits

Start with representation checks only. Reproduce the memo's phase-grid50 calculation from `k_runs.csv`: s_j=.9j/49; clip samples to `[first_valid_ms, active_cutoff_ms]`. Separate no event in the window, no sample in the first-to-last-K core, and no sample even in the outer bracket. For a missing onset/offset bracket use first K / recording end respectively, matching `ASTRA_REVIEW_CHECKS.json`. Do not bridge technical/F gaps into one K run.

Write `representation_fidelity.csv` with `sim_id,grid_id,coordinate,n_grid,n_supported,n_native,K_runs_total,K_runs_intersecting_window,K_cores_missed,K_outer_brackets_missed,window_lost_all_K,sampling_lost_all_K,max_depth_error_um,exceedance_duration_error_ms,missing_tail,status`. Compute native scalar maxima before resampling. Any candidate interpolation must use observed bracketing values only; record how it changes extrema and time-above-u_ref. Include depth/label-native sampling limits and bracket uncertainty. The current 50-point design fails preservation; do not assume a smooth reconstructed curve repairs an unobserved short event.

At most one prespecified refinement is allowed: choose the coarsest common phase grid for which every training simulation's physical time spacing satisfies `Δt<=δ_min/2`, where δ_min is the shortest positive-duration K core in the revealed training data; cap at 200 points and report single-frame episodes separately. This is **label-informed training resolution selection**, not a label-free design, and must never use test episode lengths. Validate on held-out simulations. If the cap or missing support prevents event preservation, stop this branch. Do not change the canonical target or remove cases to pass.

For the simple exact Kronecker route require genuine complete Cartesian coverage of the fitted simulation locations × times, a common Gaussian-noise model, and verified numerical structure. Missing tails must not be interpolated. If the route is unsuitable, record why and defer another solver rather than writing a broad inference framework. Verify a tiny complete-grid Kronecker solve against dense Gaussian regression to 1e-8 in posterior mean/log likelihood and 1e-6 relative residual; record covariance ordering. The n simulation inputs may be irregular in 4D. Before any trajectory-to-class comparison, require that its planned horizon `min(TE,0.9*exit)` is known before the query and represents the same endpoint as A. Actual held-out recording ends/masks may restrict error scoring, never choose the predictor's maximum window. If unexpected truncation breaks that equivalence, report a different estimand and stop the like-for-like class comparison; do not fill the tail or remove the case.

Only after P2 and these checks pass, freeze a separate B40 comparison on the same ten DEV folds: scalar A baseline; a rank-three training-only functional basis with coefficient GPs; one separable Matérn-3/2 input×time GP. Both trajectory models must use the same fixed coordinate, mask policy and transformation `log(1+d_um)`, and recover maxima with posterior-function uncertainty. No target-informed test alignment or free test coefficients. Use the same A threshold learned from revealed native A/label pairs as in P1; the posterior probability of exceeding it is a depth-based proxy for Y, not demonstrated morphology probability. Basis extraction and reconstruction fidelity must be measured before claiming the GP outperforms a cheap temporal representation.

Bound this follow-up to 30 coefficient-GP fits plus 10 temporal fits, one start each, the same four-hour/8-GiB limits, and no changepoint/kernel sweep. Earn further work only with ≥10% reduction in mean held-out simulation-weighted log-trajectory RMSE versus the basis **and** ≤5 µm absolute error in reconstructed A for at least 95% of evaluable simulations, no missed sampled outer-bracket event in the short-K group, and no >.01 q20 or >.05 short-K sensitivity loss versus scalar A. Report support/coverage and predictive calibration. These are engineering gates, not guarantees of true event recovery. Better curve RMSE alone means `NO_REGIME_ADVANCE`.

## Fallback — eight-case morphology package and one geometry check

Prepare, without sending externally, a gallery for the full IDs resolved from the audit tables: the verified fast-scan negative/positive pair (negative `H-b302fc6cbd`, VX≈.960; positive `H-b7e3ed2e12`), `H-f4fc937e86`, `H-29cf03a279`, `H-b2eec677b1`, `H-349225d53c`, OLD alternating `H-eac21b41c2` and NEW alternating `H-6ca7f366ce`. Use at most five native frame times per case, with available front/side/top views and exact clock/bounds overlays. Select times from documented peak/switch brackets; this is deliberately label-informed audit selection. No bulk download. Missing views stay missing.

`frame_review.csv`: `sim_id,frame_idx,solver_iteration,time_ms,view,source_revision,image_path,source_hash,selection_reason,depth_um,width_um,length_um,original_label,reviewer,criterion_version,cavity_visible:{yes,no,uncertain},cavity_shape_note,pore_visible:{yes,no,uncertain},review_status`. Hide original labels and E1 predictions during any independent visual judgement, then compare without altering canonical labels. A melt bound is not an image-derived cavity measurement.

Check existing parameter/geometry metadata for actual z-extent and monitor inclusion rules against the 301–305 µm plateau; output `geometry_check.csv` with full ID, source, units, domain bottom, depth origin, bounds semantics and `verified/unknown/inconsistent`. An unknown geometry is not a censored response. Do not fit a censoring model from the plateau alone.

**Success for the fallback:** resolve a specific observation/annotation ambiguity or document why available images cannot distinguish the hypotheses. No new “winning” learner is required. Prepare an October 15 note separating observations, unresolved mechanisms and DEV results; if P1 fails, the common-cohort improvement, short-K oracle failure and unresolved morphology remain scientifically useful findings. C3 stays reserved throughout.
