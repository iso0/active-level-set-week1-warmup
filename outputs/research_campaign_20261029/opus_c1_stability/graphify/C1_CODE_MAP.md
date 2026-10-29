# C1 code map

Source-verified at 3caf7c4e, the same `src/` as main 4fc9b5d. Paths are relative to the repository root.

## Active-learning path: one learner (repeat, fold)

| step | function | file:line | what it does |
|---|---|---|---|
| task | `tasks(repeats)` | `src/rc19_pool.py:157` | seeded 5-fold split of the 541 runs (SPLIT_SEED 1919); pool = 4 folds, test = 1 fold; label-free maximin path |
| alternative startup | `startup_task(task, kind)` | `src/rc22_common.py:73` | RAND8 / LOCAL8, plus `farthest_continuation` (L61) |
| reveal | `Reveal` | `src/rc19_pool.py:183` | the only route to outcomes; `paid` = query order (L210) |
| startup | `startup(task, rev)` | `src/rc22_common.py:107` | opens `task["path"][:8]` (B0 = 8, counted) |
| C1 own path | `unit_X(task, M)` | `src/ea_fwd.py:40` | loop b = 8..60: `CA.predict` on test + candidates (L44); one-class → `LN.next_on_path` (`src/rc19_learn.py:58`); else margin argmax −\|p − 0.5\|; then cross-predicts HA_LEAN on the same path (`C23.state`) |
| HA_LEAN own path | `unit_L(task, M)` | `src/ea_fwd.py:29` | `C23.run_arm(task, "HA_LEAN")` (`src/rc23_common.py:51`); on that path: C1 (`CA.predict`, L34), D / E (`el_mix.mix_state`) |

## C1 prediction at one budget: `ea_cand.predict(task, rev, Z, rows, SYSTEMS["C1"])`

`src/ea_cand.py:76`.

1. **One-class rule.** If the paid runs with a usable depth hold one class, the prediction is the class rate (L78–79).
2. **Physics column.** `h = A.hcol(task)` (`src/rc20_attr.py:38`): standardised log P − ½ log VX − 3/2 log LS.
3. **Depth features.** `F, E = D2.cf_generic(rev, Z, rows, fitter, predictor)` (`src/ea_diag2.py:50`).
   - Folds: `K.folds(n, 10)` = `np.arange(n) % 10` by query position (`src/rc19b_keyhole.py:43`). They are nested: a new query never moves an old run to another fold.
   - Out-of-fold F for paid runs: fold j's runs are predicted by a fit on the other folds.
   - E for test and candidate rows comes from the full fit.
   - Fallback to the mean depth when a fit is None (fewer than 3 good rows).
4. **Fitter.** `depth_fit_cand(task, rev, Z, "phys", rows, True, STARTS)` (`src/ea_cand.py:63`).
   - Y = log A (`PC.DEPTH_COL`); W = 10⁴ for short records.
   - H = h as the trend column.
   - Calls `gp_fit` (L54): `GPMAP(H_cols=1, b=3)` fitted from each of the 2 STARTS (L36); the lower NLML-plus-prior is kept.
5. **GP.**
   - `GPMAP._nlml` (`src/ea_cand.py:47`) = `GP._nlml` (`src/rc18_gp.py:54`) + ½ Σ((θ − PRIOR_M)/PRIOR_S)² (L33–34).
   - `GP.fit` (`src/rc18_gp.py:75`): response standardised by the mean and SD of good rows; L-BFGS-B within B_SF2, B_ELL, B_SN2 (L28); trend b² H Hᵀ.
   - `GP.predict` (L105): de-standardised latent mean.
6. **Predictor.** `PC.depth_predict(fit, Z, idx)[0]` (`src/rc24_pac.py:81`).
7. **Classifier.** `DG.lin(F, h[L], y, E, h[rows])` (`src/ea_diag.py:79`) calls `C22.phr_family(..., feats=(0,))[0]` (`src/rc22_common.py:113`).
   - Features [h, F], standardised by their training mean and SD.
   - 16 configurations (τ_F, τ_h) ∈ {0.5, 1, 2, 4}², each a Laplace logistic (`PH.laplace`), plug-in predictive.
   - Weights w ∝ exp(logZ); the output is p = w · σ(m).
   - It also returns `{"w", "m", "v", "cfg"}`, which DG.lin drops.

## Evaluation (evaluator only)

| function | file:line | what it does |
|---|---|---|
| `learner_rows` | `src/el_eval.py:30` | BA at threshold 0.5, Keyhole recall (sens), conduction recall (spec), log loss, Brier |
| `endpoints` | `src/el_eval.py:71` | first / confirmed / spend / kept |
| `aulc` | `src/el_eval.py:64` | windows |
| `cluster_diff` / `tstats` | `src/el_eval.py:106` / `:90` | repeat-cluster t bounds |
| `sustained` | `src/ea_cand_eval.py:22` | the sustained endpoint |

## Records of the C1C runs

These are evaluated on DEV in this task.

**Units.**
- `outputs/research_campaign_20261026/opus_c1_confirmation/c1c-main/units/STD__r{203..282}_f{1..5}__{L,X}.json.gz` (untracked raw)
- `c1c-start/units/{RAND8,LOCAL8}__...`
- EA `opus_error_attribution/ea-fwd/units/STD__r{163..202}_...`

**Exports** (committed): `outputs/research_campaign_20261026/opus_c1_confirmation/exports/main_s1|main_s2/predictions_f32.npz` + `paths.csv.gz`.
