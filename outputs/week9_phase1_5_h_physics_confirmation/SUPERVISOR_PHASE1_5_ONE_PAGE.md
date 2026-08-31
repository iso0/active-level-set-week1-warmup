# Supervisor one-page summary — Week 9 Phase 1.5

## Question

Can the physics-inspired coordinate `h=P/sqrt(VX·LS^3)` explain the Conduction–Keyhole regime and improve active learning under the exact frozen Week 8.5 protocol?

## What is physically correct

Gan et al. use `Ke = eta P / [(Tl-T0) pi rho Cp sqrt(alpha V r0^3)]`; therefore h has the correct process exponents when `LS=r0`. Repository source code confirms LS is the Gaussian spot radius. Bare h has units `W s^(1/2) m^-2`, so it is not dimensionless and no universal cross-alloy threshold is claimed.

## Main results

- Empirical exponents are consistent with theory: VX/P -0.518 and LS/P -1.444, with both theoretical values inside bootstrap intervals.
- Globally, log(h) is strong (ROC-AUC 0.9897) but below 4D GPC (0.9926), especially in PR-AUC and probability quality.
- At q20, h misses more Keyholes: recall 0.710 versus 0.732 for 4D GPC.
- The 5D redundant GPC does not give a resolved static or active-learning improvement.
- All GPC fits optimized, but frequent constant-kernel upper-bound hits—especially for 4D GPC—qualify probability/calibration interpretation.
- q20 AULC: 4D Margin 0.81352; h query→h model 0.83174; h query→4D GPC 0.80083; 5D Margin 0.81539; 4D×h uncertainty 0.80547.

## Interpretation

The physics ridge is a useful low-dimensional inductive bias, but it is not a sufficient acquisition coordinate for learning the full 4D empirical boundary. The h-only model/policy composite is strong at low budget; however, this cannot isolate an acquisition benefit, and its query sequence makes a 4D GPC significantly worse than canonical 4D Margin. The honest conclusion is not “h saves 45 queries.” It is: **h captures the dominant global direction, while canonical 4D Margin remains the best verified policy for residual boundary structure.**

## Recommendation

Show figures 1, 4 and 6. If Phase 2 pursues this thread, test one clean additive `g(log h)+r(x)` GP against frozen 4D Margin; do not expand the acquisition zoo.
