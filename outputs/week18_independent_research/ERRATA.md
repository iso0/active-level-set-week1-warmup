# Week 18 errata to earlier weeks (historical files are not modified)

- **E18-1 (Week 17 report, Phase 4 text).** "Original M3 ... (mean M3_Cfree − G3 −0.022 vs M3 − G3 −0.110)":
  the mean of the twelve per-cell M3 − G3 NSD AULC differences in `outputs/week17_model_and_acquisition/VERDICT.json`
  is **−0.102** (sum −1.225 / 12). M3_Cfree − G3 (−0.022) is correct. No conclusion changes.
- **E18-2 (Week 17 design note).** The Week 17 MECHANISM RESOLVED criterion included a robustness condition on LT
  (|LT − G3| ≤ 0.015 in the physics-useless cell). That condition tests LT's robustness, not the M3/PEER
  mechanisms. The frozen Week 17 verdict (NO CHANGE JUSTIFIED) is unchanged; later decision rules separate the two.
- **E18-3 (Week 18 DATA_AUDIT §3, own erratum; prompted by Astra Round 3 §10 "level shifts, order survives").**
  "The log-h level shift is a region effect" is too strong. A shared-slope logistic y ~ log h + NEW (profile
  likelihood) gives a NEW threshold shift of **+0.17 log-h units [0.03, 0.29]** on all 541 runs, and **+0.01
  [−0.14, 0.28]** inside the campaign overlap (112 runs; only 2 OLD and 8 NEW non-Keyhole runs). The overlap point
  estimates (20.91 vs 20.94) carry no usable precision. Correct statement: in a 1-D physics index the campaigns
  differ in threshold; whether this is a campaign shift or a region effect (the boundary is not a level set of log h)
  cannot be decided from the overlap. The pooling decision is unaffected: it rests on the flexible 4-D GPC, where a
  NEW offset adds +0.001 nats (DATA_AUDIT §3), and on label agreement in the overlap. `phase4/astra3_*`.
- **E18-4 (Week 16 interpretation; Astra Round 3 §1, §8, §14, independently re-read).** Week 16's "the remaining
  oracle gap is (inaccessible) model information" does not follow from the headroom identity: the truth-conditioned
  refit oracle mixes latent law, observation channel (logistic/probit working likelihood vs deterministic labels),
  approximate refitting and loss. Replace by: the tested model, observation assumption, update procedure and
  acquisition objective did not jointly turn PEER's model-internal value into boundary improvement. The empirical
  Week 16 numbers stand.
- **E18-5 (Week 16 numerical statements; Astra §8, verified here from saved tables).** (i) "martingale gap … max
  4.3" is the maximum of per-state medians (4.268, 18 states); the candidate-wise maximum is 7.158
  (`validation/peer_validation.csv`). (ii) THEORY_WEEK16's saturation illustration (curvedMono NEW σ = 1, budget 24,
  max V = 0.002) is not saturated under the declared 1e-6 rule (0.0018); the one saturated state is budget 48
  (`headroom/states.csv`), as WEEK16_REPORT says.
