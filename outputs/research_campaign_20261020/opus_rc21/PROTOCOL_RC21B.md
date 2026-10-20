# RC21B — confirmation of the plug-in learned-regularisation classifier (registered before any RC21B outcome)

Registered 2026-10-20 ~20:28 UTC, after the RC21 results (ledger RC21-RESULTS) and before any RC21B trajectory. Same window
(cap 2026-10-21 11:52:22 UTC), same 2-thread share, Astra untouched, same pooled / paid-only / honest-CF / DEV rules.

## 1. Why this test, and what was already seen

RC21 answered NO: PHR_NR + margin was not better than SHQ_ATS_H + margin in decisions (BA-AULC B8–B24 +0.002, 5/8) or in paid
simulations to BA ≥ 0.93 (−1.75, 4/1/3), and its probabilities were worse (LL +0.020). Its decomposition located the parts:
learned regularisation helps on identical queries (Stage 1 BA +0.010, LL −0.026 vs the fixed-prior integrated model); the
latent integration only adds under-confidence (Stage 1 LL +0.042, decisions unchanged); the transverse residual does not help.
The exploratory by-product PHR_NRMAP (same posterior weights over τ_F, τ_h as PHR_NR, each configuration's plug-in σ(m)) was
recorded on the RC21 physical paths (repeats 27–34) and SEEN: on H's own paths, B8–B24 LL 0.183 vs SHQ_ATS_H 0.213, BA 0.932
vs 0.927. PHR_NRMAP is therefore selected after seeing data; this stage is its confirmation on fresh repeats. It is the same
RC21 combination (physical summaries + exact log-h trend, regularisation strengths learned from the paid labels), with the
component that the decomposition identified as harmful removed; no new grid, prior or feature.

## 2. Design

Fresh DEV repeats 35–42 (never run) × 5 folds. Arms: NEW_MARGIN = PHR_NRMAP + margin; H_MARGIN = SHQ_ATS_H + margin (validated
identical to the RC21 / RC20 computation); ATSAPPROX_MARGIN; E1S (E1RAW / E1CAL + straddle). G3 is not rerun (far behind in RC20
and RC21; the instruction lists it "when needed"); X_MARGIN is not rerun (its own-query comparison was done in RC21).
Startup, budgets (8 → 60), K = 10, one-class rule, recording of all RC21 constructions on the physical paths: as RC21.

## 3. Pre-declared evaluation (constants in src/rc21b_final.py; report = the frozen src/rc21_report.py code via src/rc21b_report.py)

* Co-primary Q1: NEW − H BA-AULC B8–B24, margin 0.020, BETTER iff mean ≥ +0.020 and ≥ 7/8.
* Co-primary Q2: paid simulations to a confirmed BA ≥ 0.93; FEWER iff mean ≤ −2, fewer in ≥ 6/8, no extra censoring.
* Answer YES iff Q1 BETTER or Q2 FEWER.
* Key secondary (the reason for this variant, a probability endpoint, never reported as decision superiority):
  NEW − H LL-AULC B8–B24, margin 0.010; also LL B8–B60 (0.005), Brier (0.005), both recalls (descriptive), spend to LL ≤ 0.20.
* Controls: NEW − ATSAPPROX (LL B8–B24 0.010, LL B8–B60 0.005, BA B8–B24 0.020, spend); H − ATSAPPROX spend; NEW − E1CAL LL
  B8–B60 (0.020); NEW − E1RAW BA B8–B60 (0.020); spend vs both E1 arms.
* Diagnostics as RC21 (corner, q20, short-Keyhole, calibration, matched-path decomposition, CPU).
