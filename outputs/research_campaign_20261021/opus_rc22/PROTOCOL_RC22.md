# RC22 — robustness, necessary ingredients and one acquisition test for PHR_NRMAP + margin (protocol F1)

Registered 2026-10-21 ~14:05 UTC, before any RC22 outcome (only the numerical acceptance `RC22_VALIDATION.json` has been run;
it computes no evaluation metric). Owner instruction of 2026-10-21 (pasted, English): a NEW bounded programme, start
**2026-10-21 13:48:07 UTC**, cap **2026-10-22 13:48:07 UTC**, ≤ 2 Opus numerical threads; earlier grants are finished and not
reset; Astra's share is released (no live jobs) and is not used; combined numerical work ≤ 4. Local commits only; no physical
simulation, cloud, C4, Stage A, BA_RISK, main merge, upload or external message.

## 0. Intake (what was read; what it changes)

* RC21 / RC21B state (commit 1eedff2f): PHR_NRMAP + margin vs SHQ_ATS_H + margin on fresh repeats 35–42: BA-AULC B8–B24 +0.0030
  (6/8, NOT DIFFERENT), paid simulations to a confirmed BA ≥ 0.93 −0.38 (NO CLEAR DIFFERENCE), LL-AULC B8–B24 −0.0298 (8/8, BETTER).
  The reference is a strong candidate with a probability gain, not a proven decision winner.
* Astra's completed package `astra_representation_planning_20261020` (read only; not copied into any bundle): learned-ARD GP control
  helped on synthetic worlds; the local component and the two-step planner did not establish broad benefit; no query-saving
  criterion passed. Her 21 October context audit of RC21 makes three corrections that RC22 adopts (erratum
  `opus_rc21/ERRATUM_RC21_20261021.md`): (i) the corner's low nearest-neighbour agreement (0.44 vs 0.91) is NOT an impossibility
  proof — finite distinct inputs can be interpolated by smooth bumps; it shows difficulty at that metric and density;
  (ii) the h-transverse residual prevents only the residual from copying the h trend; β_h is not likelihood-identified against
  the physical-summary terms (they can vary along h); (iii) RC21 targets were applied to FOLD-POOLED repeat curves, not to
  individual learners. The localized-variance explanation is an untested hypothesis and is not used here; her experiments are
  not repeated.

## 1. Reference, controls, common rules

Reference REF = PHR_NRMAP + margin (frozen RC21 code; here computed on the 16 residual-free configurations, validated equal to RC21
within 9.5e−13 and trajectory-identical to RC21B). Controls: H = SHQ_ATS_H + margin; E1S = E1RAW / E1CAL + straddle (RC19B code).
Plain names (Turkish reporting): REF "öğrenilmiş düzenlileştirmeli fizik sınıflandırıcısı + margin", H "sabit cezalı fizik
sınıflandırıcısı + margin", E1S "derinlik GP'si + straddle". One 541-run pool; OLD/NEW only for evaluator diagnostics; every
startup and class-discovery query counted; paid outcomes only; one-class rule of RC19 (label-free continuation until both classes
are paid). All results DEV.

Metrics (src/rc22_eval.py, frozen): per individual learner (one test fold / block) and per FOLD-POOLED curve (the 5 learners of a
repeat pooled, the RC19–RC21 convention). AULC windows B8–B24 (small, primary for early learning) and B8–B60 (all). Paired by
repeat (8 units). Verdicts as RC20/RC21: BETTER / WORSE iff mean beyond the margin and the direction holds in ≥ 7/8; margins BA
0.020, LL 0.010 (small) / 0.005 (all), Brier 0.005. Targets (offline benchmarks, not stopping rules): BA ≥ 0.93 (primary),
BA ≥ 0.95, LL ≤ 0.20; confirmed at b and b + 4; censored = not confirmed by B60 (restricted score 64 in paired differences, never
a fictional completion budget); FEWER iff mean ≤ −2, fewer in ≥ 6/8, no extra censoring. Individual-learner attainment is reported
next to the pooled curve. A test simulation appearing in several repeats is a repeated measurement, not a new observation.

## 2. Part 1 — robustness of REF (no gate; where it works, where it degrades)

(a) Startups (job g-start; the RC21B splits, repeats 35–42, so the standard startup S0 = the completed RC21B trajectories, reused,
not regenerated): RAND8 (8 uniformly random pool points) and LOCAL8 (the 8 pool points nearest to one random pool point; often
one-class; class-discovery queries counted). Arms REF, H, E1S (240 new trajectories). Report per startup: REF − H and REF − E1
(BA / LL AULC, spend to each target), one-class starts and discovery queries, and the change from S0.
(b) Geometry blocks (job g-block): k-means (k = 5, seed 2222) on the standardised log inputs of all 541 runs, fixed in code before
any RC22 outcome; each block is withheld from fitting and querying in turn (pool = the other blocks); 8 startup seeds × 5 blocks,
arms REF, H, E1S (120 trajectories). Block class counts (validation, labels evaluator-side): 1/148, 84/4, 0/91, 101/17, 11/84
(Keyhole / conduction): every block is extrapolation in input space and most are nearly one-class, so per-block BA is often
undefined or unstable; reported per block are class counts, the defined recall(s), LL and errors; the pooled-over-blocks curve per
seed (all 541 runs predicted once) carries the paired contrasts. Blocks are not changed after results.
(c) Missing channels / record quality (job g-miss; matched, RC21B REF paths, budgets 8, 12, 16, 20, 24, 40, 60): REAL (the
unchanged benchmark, also a reproduction check); MCAR25 / MCAR50 (each paid run's T and S monitor values independently missing
with probability 0.25 / 0.50; seeded per simulation, so nested across budgets); QOFF (the record-quality treatment switched off:
short records weighted as full ones); SHORTDROP (paid short records lose T and S). Never labels, never depth, never unpaid runs.
Report per model cond − REAL and REF − H under each condition (MATERIAL rule).

## 3. Part 2 — necessary ingredients (job g-ingr; identical saved paid prefixes)

States: the RC21B NEW_MARGIN and H_MARGIN prefixes (repeats 35–42, 80 paths) at budgets 8, 12, 16, 20, 24, 32, 40, 60. Same
upstream fit per state for every construction: HONLY_LR (exact log h only, learned τ_h), HA_LR (log h + predicted depth, learned
τ_F, τ_h), PHR_NRMAP (full REF construction), SHQ_ATS_H, SHQ_ATS_H_RECAL (paid-only scalar logit recalibration from honest 5-fold
out-of-fold predictions of the complete pipeline; fallback identity below 12 paid runs or 3 of a class; validated honest).
Reported: matched contrasts (MATERIAL iff |Δ| ≥ 0.010 in the good direction and ≥ 7/8), both recalls; per state the fit of
logit(PHR_NRMAP) on logit(SHQ_ATS_H) over the candidates (slope, intercept, R²), sign disagreements, Spearman of the margin scores,
top-1 and top-5 agreement of the margin choice; the recalibration coefficients. A common positive logit scaling would give slope
> 0, intercept 0, R² = 1, no sign disagreement and identical margin ranking — the observed distance from that case is measured.
SIMPLE rule (fixed now): the first of HONLY_LR, HA_LR, SHQ_ATS_H_RECAL with all-path matched BA-AULC B8–B24 ≥ REF − 0.003 AND
LL-AULC B8–B24 ≤ REF + 0.003 becomes a prospective arm A5_SIMPLE (+ margin) in the acquisition stage; otherwise none. REF stays
unchanged in every case.

## 4. Part 3 — acquisition audit (same g-ingr states)

What PHR_NRMAP exposes: a posterior-weighted mixture of 16 plug-in logistic classifiers (weights w_g); for each, a Laplace latent
mean m_g and variance v_g at a candidate given the PLUG-IN emulator features. Upstream emulator uncertainty is not propagated.
Candidates (Houlsby et al. 2011, BALD): BALD_LAP = H(Σ w_g E σ(f_g)) − Σ w_g E H(σ(f_g)), f_g ~ N(m_g, v_g) (classifier-weight and
grid information; 64-node Gauss–Hermite, validated against Monte Carlo); BALD_GRID = H(Σ w_g σ(m_g)) − Σ w_g H(σ(m_g)) (partial:
grid disagreement only; coherent with the reported mixture). The reported probabilities and the 0.5 cutoff stay PHR_NRMAP.
SELECTOR rule (fixed now): the first of BALD_LAP, BALD_GRID meeting ALL of: numerics PASS; median over states of max_x I / max_x
H(p_REF) ≥ 0.05; < 10 % of states with max I < 1e−6 (no collapse); its top-1 differs from margin's in ≥ 25 % of states and median
Spearman(I, margin score) < 0.95; its top-1 differs from SHQ_ATS_H eta-straddle's (RC20, failed) in ≥ 25 % of states; extra
selection CPU ≤ 0.5 s per step. Otherwise SELECTOR = None and the stage runs without a selector arm (reported as rejected). No
other selector is added without a new registration.

## 5. Part 3 — acquisition comparison (job g-acq; frozen as F2 after the two rules above are applied)

Fresh DEV repeats 43–50 × 5 folds; standard startup; predictive model PHR_NRMAP and cutoff 0.5 fixed in every arm:
A1_MARGIN (unchanged REF); A2_MARGIN_COV (margin with the fixed coverage schedule: every 5th query after the startup, query numbers
13, 18, …, 58, is the candidate farthest from all paid runs in standardised log inputs — label-free, cadence fixed now, not tuned);
A3_SEL_COV (SELECTOR with the SAME coverage schedule; only if SELECTOR ≠ None); A4_MAXIMIN (label-free farthest-point design
reference); A5_SIMPLE (only if SIMPLE ≠ None). Primary (selector): A3 − A2, Q1 BA-AULC B8–B24 (margin 0.020, 7/8) and Q2 paid
simulations to a confirmed BA ≥ 0.93 (FEWER rule). SUCCESS iff (Q1 BETTER or Q2 FEWER) AND A3 − A2 BA-AULC B8–B60 is not WORSE
at margin 0.010. Secondary: A2 − A1 (coverage), A3 − A1 (system), A4 − A1 (design), A5 − A1 (simplification, prospective), LL
(probability only; never turns a failed BA / query goal into success), BA ≥ 0.95 and LL ≤ 0.20 targets, both recalls, individual
learner attainment, corner / short-Keyhole / q20 diagnostics, discovery (first paid run in the evaluator-defined corner, first
corner conduction hit) separated from learning after the first hit, selection CPU.

## 6. Execution and failures

Queue src/rc22_runner.ps1 (≤ 2 single-thread workers, deadline from its plan), jobs g-ingr → g-miss → g-start → g-block (F1
manifest checked by every worker), then g-acq after F2. Smoke g-smoke (DEV repeat 1 / seed 1) before F1. Failed units stay in
`failed/`; a code repair is logged as an amendment before any rerun; a failed gate is never overridden. If the deadline arrives
first, unfinished units are reported as INCOMPLETE.
