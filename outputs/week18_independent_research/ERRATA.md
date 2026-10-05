# Week 18 errata to earlier weeks (historical files are not modified)

- **E18-1 (Week 17 report, Phase 4 text).** "Original M3 ... (mean M3_Cfree − G3 −0.022 vs M3 − G3 −0.110)":
  the mean of the twelve per-cell M3 − G3 NSD AULC differences in `outputs/week17_model_and_acquisition/VERDICT.json`
  is **−0.102** (sum −1.225 / 12). M3_Cfree − G3 (−0.022) is correct. No conclusion changes.
- **E18-2 (Week 17 design note).** The Week 17 MECHANISM RESOLVED criterion included a robustness condition on LT
  (|LT − G3| ≤ 0.015 in the physics-useless cell). That condition tests LT's robustness, not the M3/PEER
  mechanisms. The frozen Week 17 verdict (NO CHANGE JUSTIFIED) is unchanged; later decision rules separate the two.
