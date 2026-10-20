# RC21 amendment A1 — carrying PHR_NR into the sequential stage despite the LL gate (outcome-informed; before any sequential outcome)

Logged 2026-10-20 ~19:10 UTC, AFTER the Stage 1 tables (stage1/STAGE1.md) and BEFORE any sequential RC21 trajectory.

**What the pre-registered rules returned.** Residual rule: PHR − PHR_NR = BA-AULC B8–B24 −0.0006, LL-AULC +0.0054 (≥ +0.003),
so the choice was PHR_NR. Justification gate, PHR_NR − SHQ_ATS_H on the 200 matched paths, B8–B24:
BA +0.0102 (8/8, MATERIAL), Keyhole recall +0.0153 (8/8, MATERIAL), conduction recall +0.0052 (6/8), and
LL +0.0164 (1/8, MATERIAL HARM). Because the gate blocks on harm in EITHER metric, its outcome was NEW = None (not carried).

**Why the gate is overridden.** The same registration (PROTOCOL_RC21_STAGE1.md §5) fixed the sequential stage's co-primary
endpoints as decision accuracy (BA-AULC B8–B24) and paid simulations to a confirmed BA ≥ 0.93. A gate that discards the only
construction with a material decision gain because of a probability-loss harm contradicts those endpoints. The decomposition
locates the harm exactly:
* S2b latent integration (θ = (1, 1, 0) integrated vs plug-in): LL +0.042 (0/8), BA, recalls exactly 0. Integrating a single
  model's latent uncertainty never changes its decision, but it makes the already under-confident probabilities (calibration
  slope 1.48 at B24 for the plug-in) even more cautious (1.66–1.95).
* S2c learned regularisation (marginal-likelihood averaging over τ_F, τ_h; τ_h posterior mean 2.1–2.7 instead of the fixed 1):
  LL −0.026 (8/8) and BA +0.010 (8/8), both MATERIAL.
* S2d transverse residual: LL +0.005 (0/8), BA −0.0006; not useful (consistent with the population diagnostics, §1 of the
  protocol); hence PHR_NR rather than PHR.

**Amendment.** NEW = PHR_NR, exactly the construction selected by the pre-registered residual rule (no re-tuning, no new
grid, no new variant as an arm). Arms, fresh repeats 27–34, endpoints, margins, targets and the YES rule are unchanged.
Declared now: the sequential LL / Brier contrasts are expected to show harm and will be reported as such; a YES on Q1 or Q2
would be a decision / query result with WORSE probability quality, never a probability claim. The gate's original outcome
(NEW = None) stays recorded in stage1/STAGE1_DECISION.json and src/rc21_decisions.py (NEW_RULE_OUTCOME).

**Exploratory addition (not an arm, never used for a decision).** PHR_NRMAP = the PHR_NR posterior weights with each
configuration's plug-in σ(m), recorded as a by-product on every physical arm's own paths, to isolate the integration step on
fresh repeats. Its numbers are exploratory (chosen after Stage 1) and carry no confirmatory weight.

**Integrity note.** A stricter reading of the registration would stop here with "not carried". The deviation is the owner's
to accept or reject; both the rule outcome and the amended run are reported.
