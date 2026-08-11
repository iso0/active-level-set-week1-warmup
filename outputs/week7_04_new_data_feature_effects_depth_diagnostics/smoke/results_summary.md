# Week 7 Phase 4 — new-data feature effects and depth-error diagnosis

## Scope and provenance

- Parent Phase 3 commit: `1118d30f3199a97b9836591f8fdea75b46dfac0d`.
- Dataset: `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
- Primary analysis: corrected Phase 2 target-ready `new-data` rows only.
- Historical Week 6 values were loaded from saved artifacts; no old/new pooling occurred.
- Full-data GPs are interpretive response-surface fits, not performance estimates.

## Main feature findings

- Depth P trend: **REPRODUCED** (Spearman 0.843, Ridge 0.565, GP local sensitivity 0.409).
- Depth VX trend: **REPRODUCED** (Spearman -0.281, Ridge -0.197, GP local sensitivity -0.196).
- ST statements describe association in the sampled design; they do not establish physical unimportance.

## Depth-error concentration and diagnosis

- Worst 1/3/5/10 simulations contribute **19.1% / 35.9% / 48.2% / 67.8%** of primary-model squared error.
- Consensus hard cases: **21**.
- Spearman association of absolute error with nearest-neighbour distance: **0.047**.
- Spearman association of absolute error with local 5-NN depth SD: **0.582**.
- Overall diagnosis category: **MIXED / UNRESOLVED**.
- Current evidence does **not** justify changing the GP family before targeted support/regime/target-quality follow-up.

## D1–D10 decision table

- **D1 — heavy-error tail:** Worst 5/10 contribute 48.2%/67.8% of total squared error.
- **D2 — associated:** Spearman(|error|, observed depth)=0.607, p=7.23e-18.
- **D3 — enriched:** RMSE Keyhole true/false=32.931/9.788 um.
- **D4 — see timing groups:** Timing-specific fixed-residual group metrics are reported without causal interpretation.
- **D5 — weak or absent:** rho=0.047, p=0.548.
- **D6 — yes:** rho=0.582, p=2.95e-16.
- **D7 — possible:** Strongest continuous quality association: T0_sample_count, rho=0.400.
- **D8 — yes:** Common top-20 cases=17; three-way top-20 Jaccard=0.773.
- **D9 — yes:** P=REPRODUCED; VX=REPRODUCED.
- **D10 — NO - retain for now:** Phase 4 diagnoses fixed-model errors first; no new family is justified solely by uncomfortable RMSE. Revisit only after targeted regime/support and target-quality work.

## Week 6 stability

Reproduced statements: ["LS has a material positive association with width after controlling P, VX and ST.", "Power is positively associated with T0 penetration depth.", "Scan speed is negatively associated with T0 penetration depth.", "P-VX interactions shape the supported depth response surface."]

Changed or unresolved statements: [{"week6_statement": "The KE-LS relationship is power-profile dependent; Week 6 did not support a uniform global LS reduction claim.", "status": "MIXED"}, {"week6_statement": "Total height rises with P and falls with VX in the sampled design.", "status": "MIXED"}, {"week6_statement": "ST associations were comparatively weak in the Week 6 sampled design.", "status": "WEAKENED"}]

## Validation and hard stop

Validation: {'PASS': 24}. Figures: 15.

No classifier, T0 redefinition, new GP kernel, active learning, level-set estimation, causal inference, or pooled production model was created.
