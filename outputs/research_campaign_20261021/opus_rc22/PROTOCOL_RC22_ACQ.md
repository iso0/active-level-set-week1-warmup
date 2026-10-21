# RC22 acquisition stage — freeze F2 (written after the pre-registered decision rules, before any acquisition outcome)

Frozen 2026-10-21 16:00 UTC. The design, endpoints, margins, success rule and failure handling are those of PROTOCOL_RC22.md §5
(registered 14:05 UTC, before any outcome). This file records only the two rule outcomes (src/rc22_decisions.py;
ingr/DECISIONS.json) and the resulting arm list. The robustness reports (parts 1a–1c) had not been generated when this was frozen.

* SELECTOR = **BALD_LAP** (classifier-weight + grid information of the PHR_NRMAP mixture's Laplace posterior given the plug-in
  emulator features; upstream emulator uncertainty is not included; reported probabilities and the 0.5 cutoff remain PHR_NRMAP).
  Audit: median max-information / max-entropy 0.25; no collapse (0 % of states below 1e−6); top-1 differs from margin in 97.5 %
  of states (median Spearman 0.25) and from SHQ_ATS_H eta-straddle in 95 %; GH vs Monte Carlo within MC error; extra CPU 0.03 s.
* SIMPLE = **HA_LR** (exact log h + predicted depth, the same learned-regularisation classifier): matched BA-AULC B8–B24 +0.0095,
  LL −0.0152 vs PHR_NRMAP. HONLY_LR failed the LL criterion (+0.0046) despite BA +0.0166 and is not carried.

Arms on fresh DEV repeats 43–50 × 5 folds (200 trajectories), standard 8-point maximin startup, B8 → B60:
A1_MARGIN (PHR_NRMAP + margin), A2_MARGIN_COV (+ coverage every 5th query), A3_SEL_COV (BALD_LAP + the same coverage),
A4_MAXIMIN (label-free farthest-point), A5_SIMPLE (HA_LR + margin). Physical arms record SHQ_ATS_H and PHR_NRMAP on their own paths.

Primary: A3 − A2 — Q1 BA-AULC B8–B24 BETTER (≥ +0.020, 7/8) or Q2 FEWER simulations to a confirmed BA ≥ 0.93 (mean ≤ −2, 6/8, no
extra censoring); SUCCESS additionally requires A3 − A2 BA-AULC B8–B60 not WORSE at margin 0.010. Secondary: A2 − A1, A3 − A1,
A4 − A1, A5 − A1 (BA small / all, LL, both recalls, the three targets), individual-learner attainment, discovery diagnostics, CPU.
Evaluation: src/rc22_eval.py (frozen in F1, unchanged) via src/rc22_report.py acq.
