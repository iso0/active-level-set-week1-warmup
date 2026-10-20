# RC21 — exploiting exact public inputs beyond SHQ_ATS_H (protocol, registered before any RC21 outcome)

Registered 2026-10-20 18:40 UTC, before any matched-path or sequential RC21 result was computed. Owner instruction of
2026-10-20 (evening, Turkish): continue inside the REMAINING RC20 window (t0 2026-10-20 11:52:22 UTC, cap 2026-10-21 11:52:22 UTC;
the 24-hour clock is not restarted), Opus share 2 threads, Astra's jobs and two-thread share untouched, combined numerical work
≤ 4. All 541 eligible simulations are ONE pool (OLD/NEW is provenance only); every startup query is counted; honest cross-fitting
is preserved; every partition of these 541 runs remains DEV. No new physical simulation, no paid cloud, no upload, no main merge.

## 1. What was already seen (disclosed design information, all DEV)

* RC20 (frozen, commit b46f4f62): SHQ_ATS_H + margin beat ATSCF + margin in LL-AULC B8–B24 (−0.038, 8/8) and reached BA ≥ 0.93 /
  LL ≤ 0.20 with fewer paid simulations; BA differences stayed below the 0.020 margin; equal to ATSAPPROX; the fast-scan corner
  stayed unresolved (NEW-conduction recall 0.31). RC20 by-products on the candidate's own paths (exploratory): SHQ_ATS_X LL 0.166 /
  BA 0.938, SHQ_ATS_H 0.159 / 0.944, SHQ_A_H 0.164 / 0.948, HONLY 0.246 / 0.940. Stage-1 replay: generic inputs (ATS + 4 exact log
  inputs) −0.0148 vs ATS; h beats generic inputs by 0.0049 (7/8).
* Population diagnostics run for this design (full 541-run pool, labels and outputs seen, evaluator-side; not a result):
  - a logistic fit on the 4 standardised log inputs points along the h direction (cosine 0.996; fitted exponents P^1 VX^−0.59
    LS^−1.34 ST^−0.08 against the h-law 1, −0.5, −1.5, 0); 5-fold CV: h alone LL 0.135–0.141 / BA 0.943–0.947, 4 inputs 0.140 /
    0.944–0.950, h + linear transverse coordinates no better (0.137 / 0.942);
  - nonlinear input models help (ARD-RBF GPC on Z: LL 0.110, BA 0.969; h + quadratic transverse terms BA 0.951);
  - oracle physical summaries (true outputs, evaluator only) define the label almost completely (log A alone LL 0.072, BA 0.978),
    so emulator accuracy, not the classifier family, bounds the physical route;
  - the fast-scan corner (VX > 0.85 m/s, P > 330 W; 39 runs, 22 Keyhole / 17 conduction) is label-interleaved in input space:
    nearest-neighbour label agreement 0.44 there vs 0.91 in the whole pool; RC20 margin paths spent ~41 % of B60 in that 7 % of
    the pool. No input-smooth model is expected to classify it; it remains a reported diagnostic, not a target.

## 2. The single new combination: PHR (src/rc21_phr.py, src/rc21_attr.py)

One discriminative layer, latent Keyhole score
  η(x) = b0 + β_h z_h(x) + Σ_t w_t F̃_t(x) + r(U(x)),
with F̃ = the honest out-of-fold SHQ predictions of (log A, T0 max temperature, spike log-ratio) for training and the full-paid
fit's means for deployment (identical upstream to SHQ_ATS_H), z_h = exact standardised log h, and U = the standardised log inputs
projected on the 3-dimensional complement of the h direction (Z·d is exactly proportional to z_h), so r is constant along h.
Priors b0 ~ N(0, 10²), β_h ~ N(0, τ_h²), w ~ N(0, τ_F² I), r ~ GP(0, σ_r² exp(−|U−U′|²/2ℓ²)); coefficients integrated out
(one GP kernel). Hyperparameters on a fixed grid: τ_F, τ_h ∈ {0.5, 1, 2, 4} log-uniform; P(σ_r = 0) = 1/2, σ_r ∈ {0.5, 1, 2} 1/6
each; ℓ ∈ {0.75, 1.5}. Posterior weights from the Laplace marginal likelihood on the paid labels; predictions are posterior
averages of Laplace predictive probabilities (64-node Gauss–Hermite over the latent predictive). Paid outcomes only; one-class
rule of RC19.

Why this is a different mechanism from the earlier h attempts:
* M3 (Week 9, P113/P114): label-only GPC on a FROZEN h-logistic mean (C = 1e6, fitted once on the archive design) plus a capped
  ARD Matérn residual over all 4 inputs (residual SD at its bound in 47.9 % of fits). No physical summaries; the residual could
  re-learn the h trend; the trend was never re-estimated; archive-based.
* LT (Week 18): a learnable h basis inside the label GPC (G3 inputs) — h duplicated in an input-space kernel; no gain over G3.
* SHQH (RC19 DEV): log h as a 5th input of the output emulators (a deterministic coordinate added as if it were new input
  information); not carried. SHQT (RC20 V2): h-mean emulators; not material.
* SHQ_ATS_H (RC20 V1): h in the classifier with the same fixed C = 1 penalty as the emulated features, no residual.
* PHR: (i) h appears ONCE, as the trend of the decision layer (emulators stay on x without h; no product of h-based and
  feature-based evidence); (ii) the residual lives only transverse to h, so β_h is identified and r cannot double the trend;
  (iii) the strength of the h trend, of the physical summaries and of the residual is learned from the paid labels (marginal
  likelihood, averaged over a small fixed grid that contains the no-residual model with prior mass 1/2), instead of fixed
  (C = 1, C = 1e6) or capped; (iv) the predictive integrates the latent uncertainty; (v) no archive, paid-only.
Nesting: θ = (1, 1, 0) with the plug-in σ(m) is SHQ_ATS_H up to the intercept prior (validated, §3).

## 3. Numerical acceptance (done before this registration; outputs/.../opus_rc21/RC21_VALIDATION.json, PASS)

Function-space Laplace = independent weight-space Laplace (max 3.6e−11); with the residual the Newton mode is stationary
(2.4e−12) and not worse than a generic optimiser; 64-node quadrature = 200-node (3.2e−8) and MC (1.2e−3, MC error); PHR_FXMAP vs
SHQ_ATS_H ≤ 1.1e−3 (intercept prior), vs the exact free-intercept optimum ≤ 1.1e−5 when the intercept prior is widened (sklearn's
own solver gap ≤ 3.2e−4, informational); rc21 SHQ_ATS_H = RC20 c-replay cache (≤ 3e−8) and = RC20 cand_state (0.0); shadow test
(randomised never-paid outcomes) 0.0 for every construction; transverse geometry exact; CPU 0.4–0.9 s per paid state including
the 112 Laplace fits (single thread).

## 4. Stage 1 — matched paths (development; model contribution on identical queries)

Paths: the 200 RC19B final trajectories (repeats 11–18 × 5 folds × their own arms E1S, ATSCF_MARGIN, DEPTHCF_MARGIN, G3_MARGIN,
ATSAPPROX_MARGIN), budgets 8, 12, …, 60 (job d-replay, 200 units). Computed: PHR, PHR_NR, PHR_FX, PHR_FXMAP, SHQ_ATS_H (check vs
RC20 cache). NOT recomputed: SHQ_ATS_X and SHQ_ATS_H (RC20 c-replay-x / c-replay caches, used as the references), E1RAW, E1CAL,
ATSAPPROX, G3 (RC19B caches). Metrics: the unchanged RC19 evaluator (log loss, BA, sensitivity = Keyhole recall, specificity =
conduction recall, Brier, AUC, q20 BA, NEW-corner conduction errors, short-Keyhole capture). AULC windows B8–B24 and B8–B60;
all-path means per repeat, paired over the 8 repeats.

Contrasts (labels: LL/Brier MATERIAL iff mean Δ ≤ −0.010 and favourable in ≥ 7/8; BA MATERIAL iff mean Δ ≥ +0.010 and ≥ 7/8;
MATERIAL HARM symmetric; otherwise NOT MATERIAL):
* S1 PHR − SHQ_ATS_H (the model contribution of the new combination);
* S2 decomposition: PHR_FXMAP − SHQ_ATS_H (intercept prior, ≈ 0), PHR_FX − PHR_FXMAP (latent integration), PHR_NR − PHR_FX
  (learned regularisation), PHR − PHR_NR (transverse residual);
* S3 PHR − SHQ_ATS_X, and SHQ_ATS_X − SHQ_ATS_H (cached, reproduces the RC20 control);
* S4 PHR − ATSAPPROX, − E1CAL, − E1RAW, − G3.
Reported also: posterior residual mass and posterior mean scales by budget; NEW-corner errors; both recalls by budget.

Development choice (fixed now): the sequential candidate NEW = PHR, unless the transverse residual hurts on matched paths —
mean (PHR − PHR_NR) BA-AULC B8–B24 ≤ −0.003 or mean LL-AULC B8–B24 ≥ +0.003 — in which case NEW = PHR_NR. Justification gate:
NEW enters the sequential stage unless it is MATERIALLY HARMFUL versus SHQ_ATS_H on matched paths (LL B8–B24 or BA B8–B24) or
fails numerically; then the sequential stage runs H, X and the references only. src/rc21_decisions.py records the outcome.

## 5. Sequential stage (structure fixed now; details frozen in PROTOCOL_RC21_FINAL.md before any of its outcomes)

Fresh DEV repeats 27–34 (never run: RC19 1–10, RC19B 11–18, RC20 19–26) × 5 folds; matched public-feature startup (8 label-free
maximin points, paid and counted), one query per step, B8 → B60, every budget recorded; K = 10 honest folds.
Arms: NEW_MARGIN (NEW + margin), H_MARGIN (SHQ_ATS_H + margin = RC20 CAND_MARGIN code path), X_MARGIN (SHQ_ATS_X + margin, item 2
of the instruction: generic inputs on their own queries), ATSAPPROX_MARGIN, E1S (E1RAW / E1CAL + straddle), G3_MARGIN. The three
physical arms evaluate every RC21 construction on their own paid prefixes at every budget (matched-path by-products).
Co-primary questions, NEW_MARGIN − H_MARGIN (margins and targets unchanged from RC20):
  Q1 decision accuracy: BA-AULC B8–B24, higher, margin 0.020, BETTER iff mean ≥ +0.020 and better in ≥ 7/8 repeats;
  Q2 paid queries: total paid simulations (startup included) to a CONFIRMED BA ≥ 0.93 (at b and at b + 4), FEWER iff mean
     paired difference ≤ −2, fewer in ≥ 6/8 repeats and no extra censoring (censored = 64, restricted score).
Secondary (never reported as decision superiority when only probability metrics move): BA-AULC B8–B60 (0.020); sensitivity
and specificity AULC (descriptive); LL-AULC B8–B24 (0.010) and B8–B60 (0.005); Brier B8–B60 (0.005); spend to LL ≤ 0.20 (same
rule); q20 BA; NEW-corner conduction errors; short-Keyhole capture. X_MARGIN − H_MARGIN on Q1, Q2, LL B8–B24 / B8–B60. Controls:
NEW − ATSAPPROX (LL B8–B24 0.010, BA B8–B24 0.020, Q2), NEW − E1CAL / E1RAW + straddle (LL B8–B60 0.020, BA B8–B60 0.020, Q2),
NEW − G3 (LL B8–B60 0.020, Q2). Offline test BA is an evaluator benchmark, not a stopping rule; outputs from one simulation are
one query.
