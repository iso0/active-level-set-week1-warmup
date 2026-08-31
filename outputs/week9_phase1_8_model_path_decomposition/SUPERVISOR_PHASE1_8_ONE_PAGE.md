# Week 9 Phase 1.8 — Supervisor one-page summary

## Result

The published Phase 1.7 q20 AULC gain is +0.020018. The symmetric decomposition assigns +0.021402 [+0.014550,+0.028858] to the prediction model and -0.001383 [-0.005340,+0.002606] to the changed query path. The predeclared decision is **MODEL_DOMINANT**.

| Combination | q20 AULC |
|---|---:|
| Y00: 4D model / 4D path | 0.813520 |
| Y10: physics model / 4D path | 0.829972 |
| Y01: 4D model / physics path | 0.807187 |
| Y11: physics model / physics path | 0.833539 |

At budget 16 the paths are identical. The q20 accuracy advantage is +0.052941, so the early gain is necessarily a model/inductive-bias effect.

The physics model still changes q20 AULC by +0.016452 when forced onto the original 4D path. The physics-induced path changes ordinary 4D-GPC q20 AULC by -0.006333. Call the latter a **query-path contribution induced by the physics-informed model/policy**, not acquisition superiority.

Fixed-path bounds 0.5/1.0/2.0 give a maximum A1 checkpoint q20-accuracy spread of 0.0100; verdict: checkpoint-level advantage locally stable in direction, with small variation.

## Safe thesis claim

“On the frozen 405-simulation benchmark, the Phase 1.7 model/policy gain can be decomposed into a physics-informed prediction-model contribution and a posterior-induced query-path contribution; the dominance classification is MODEL_DOMINANT.”
