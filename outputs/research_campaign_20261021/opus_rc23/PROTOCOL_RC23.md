# RC23 — the fully lean h + depth system and one model decision (protocol; registered before any RC23 outcome)

Registered 2026-10-21 ~18:00 UTC, before any RC23 outcome; only the numerical acceptance `RC23_VALIDATION.json` has been run, and it
computes no metric.

**Programme:** owner instruction of 2026-10-21 (Turkish, pasted). One 24-hour window from 17:46:17 UTC (cap 2026-10-22 17:46:17
UTC), ≤ 2 Opus threads. Astra's share is released and has no jobs. Margin is the selector in every arm; no BALD, coverage or new
selector. Local commits, then a push of the development branch (owner request), without Astra's files.

**Rules:**
- One 541-run pool; OLD/NEW never selects a model.
- Every startup and query is counted; all available outputs of a paid run are bought at once.
- Labels, exclusions and q20 are unchanged.
- The corner and short-Keyhole results are diagnostics only.
- All results are DEV.

## 1. Constructions (src/rc23_common.py; plain names first)

| plain name | code alias | upstream | classifier inputs |
|---|---|---|---|
| RC22 reference | PHR_NRMAP | SHQ shared over (log A, T, S) | log h, A, T, S |
| RC22 candidate, shared upstream | HA_LR | the same shared three-channel upstream | log h, A |
| fully lean h + depth system | HA_LEAN | the same SHQ GP code fitted on paid DEPTHS ONLY | log h, A |
| h-only control | HONLY_LR | no emulator | log h |

- **HA_LEAN:** same kernel, honest K = 10 cross-fitting, record-quality treatment and normalisation as the SHQ upstream; temperature and spike never enter.
- **Classifier:** the same learned-regularisation classifier in every arm (Laplace marginal-likelihood averaging over τ on {0.5, 1, 2, 4}; plug-in mixture).
- **Decision:** cutoff 0.5; next query = margin on the arm's own construction.

**Acceptance (PASS):**
- reproduction of RC22 trajectories (HA_LR, PHR_NRMAP) and values (HONLY_LR);
- HA_LEAN and HONLY_LR identical when paid T / S are changed or removed, for a state and for a whole trajectory;
- HA_LR and PHR_NRMAP change (up to 0.53 and 0.47);
- shadow test of unpaid outcomes 0.0; the depth-only cross-fit is honest;
- CPU per state: PHR_NRMAP 0.39–0.62 s, HA_LR 0.40–0.62 s, HA_LEAN 0.10–0.18 s, HONLY_LR 0.005 s.

## 2. Stage 1 — mechanism on identical saved paid prefixes (job h-match; descriptive, no gate)

- **Paths:** the RC22 acquisition paths A1_MARGIN (PHR_NRMAP) and A5_SIMPLE (HA_LR), repeats 43–50, budgets 8, 12, …, 60.
- **Computed:** all four constructions on identical prefixes, plus candidate probabilities.
- **Reported:**
  - HA_LEAN − HA_LR (removing T / S from the upstream only), HA_LEAN − HONLY_LR (what depth adds) and the reference contrasts;
  - fold-pooled AULC, both recalls, LL;
  - same-path decision disagreement, Spearman of the margin scores and agreement of the margin top-1 choice.
- Fixed-path results are reported separately from the active-learning results.

## 3. Stage 2 — prospective primary comparison (job h-std)

- **Data:** fresh repeats 51–58 (first unused IDs in the ledger: RC19 1–10, RC19B 11–18, RC20 19–26, RC21 27–34, RC21B 35–42, RC22 43–50) × 5 folds, standard 8-point maximin startup, B8 → B60.
- **Arms:** PHR_NRMAP, HA_LR, HA_LEAN and HONLY_LR, each + margin (160 trajectories).

## 4. Stage 3 — the candidates' own robustness (jobs h-rob, h-block; completed results reused)

| condition | data | reused PHR_NRMAP results |
|---|---|---|
| (i) standard startup | repeats 35–42 | RC21B e-final |
| (ii) RAND8 | the same splits | RC22 g-start |
| (iii) LOCAL8 (clustered, often one-class) | the same splits | RC22 g-start |
| (iv) geometry blocks | RC22 k-means k = 5, seeds 1–8; each block withheld from fitting and querying | RC22 g-block |

- New arms in every condition: HA_LR, HA_LEAN, HONLY_LR (360 + 120 trajectories).
- Blocks are a harder generalisation question and are interpreted separately.
- BA is undefined for single-class blocks and is never set to 0 or 1; the defined recall is shown instead.

## 5. Metrics (src/rc23_eval.py with the frozen src/rc22_eval.py functions)

**Primary:**
- BA-AULC B8–B24 and B8–B60;
- attainment of BA targets and the total paid simulations.

**Secondary:**
- Keyhole and conduction recall;
- log loss and Brier (probability quality);
- decision / training CPU.

**Units and pairing:** fold-pooled repeat curves are the paired units (8 per condition); individual learners (40) are reported separately. Folds and budgets are never counted as independent replicates.

**Targets** BA ≥ 0.80, 0.90, 0.93, 0.95. For each:
- first budget reaching the level (8 = already at the startup; never "fewer than 8");
- confirmation at b and b + 4 (it does not imply staying above the level in between; a sustained share is reported);
- spend = b + 4;
- attained / censored by B60;
- for paired arms: attainment counts, the observed difference on the both-attained pairs, and a restricted score with censored = 61 (the smallest confirmation spend possible after B60), with the FEWER rule (mean ≤ −2, fewer in ≥ 6/8, no extra censoring) applied to the restricted score.

Target spends use test labels: they are offline evaluations, not a stopping rule.

## 6. Decisions fixed now

| decision | rule |
|---|---|
| Practical superiority | BA-AULC B8–B24 or B8–B60 mean ≥ +0.020 and better in ≥ 7/8 (RC20–RC22 margin, unchanged), or FEWER simulations to BA ≥ 0.93 |
| Performance preservation (non-inferiority) | one-sided 95 % lower bound (t, 7 df) of the paired BA-AULC difference ≥ −δ, δ = 0.010, in BOTH windows; "not shown" is never written as equivalence |
| Acceptable loss for preferring the simpler system | δ = 0.010 BA-AULC (half the superiority margin) |
| Robustness of a candidate vs PHR_NRMAP | in each of (i)–(iv): no WORSE BA verdict (margin 0.020, 7/8) in either window, and mean BA-AULC B8–B60 difference ≥ −0.010 |

A candidate PASSES iff, on fresh repeats 51–58:
- non-inferior to PHR_NRMAP in both windows;
- the paired spend to BA ≥ 0.93 is not "MORE SIMULATIONS";
- robust in (i)–(iv).

**Final decision:**
- **D1** "the fully lean system is sufficient — HA_LEAN + margin" iff HA_LEAN passes;
- otherwise **D2** "the shared upstream is needed — HA_LR + margin" iff HA_LR passes;
- otherwise **D3** "simplification not robust enough — keep PHR_NRMAP + margin".

HONLY_LR is a control, not a decision candidate; what depth adds is reported (HA_LEAN − HONLY_LR). Log-loss gains are never reported as BA gains.

## 7. Execution

- **Queue:** src/rc23_runner.ps1 (≤ 2 single-thread workers; plan deadline). Smoke h-smoke before the freeze; workers verify `freeze/RC23_MANIFEST.json`.
- **Failures:** failed units stay recorded; repairs are logged before any rerun; no gate is overridden.
- **Exports:** per-budget predictions and paid IDs, with metric recomputation acceptance.
