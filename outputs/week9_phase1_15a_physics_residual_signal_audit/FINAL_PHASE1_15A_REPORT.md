# Week 9 Phase 1.15A — Physics–Residual Signal Audit and Acquisition Design

## Decision: CORRECTION_SIGNAL_PARTIAL

No new acquisition trajectory was run. The exact Phase 1.14 P1 prefixes were replayed only to reconstruct pre-reveal model components.

## Strongest correction finding
Within-budget Q5 corrections fixed H mistakes at rate 0.0049 and harmed correct H predictions at 0.0058; net -0.0008. The 20-repeat interval for Q5 net fix was [-0.0006, +0.0013]. Q1 net was +0.0000.
Correction magnitude versus final M3 margin Spearman rho=-0.951; A0 versus A1 score rho=+0.983, with the same top candidate in 37.4% of frozen states. The correction is not treated as independent-model disagreement.

## Boundary relevance
Pooled Q5 q20-like enrichment was 2.343; mean per-run enrichment was 2.924 with repeat-block interval [2.753, 3.093]. This is largely entangled with ordinary margin because correction magnitude is strongly anticorrelated with M3 margin. B1/q membership entered only after the candidate table was frozen.

## Class and budget behavior
- B16_24, truth=0: mean Δp +0.0046, fix 0.0006, harm 0.0013, net -0.0007.
- B16_24, truth=1: mean Δp -0.0044, fix 0.0058, harm 0.0049, net +0.0008.
- B25_40, truth=0: mean Δp +0.0062, fix 0.0006, harm 0.0011, net -0.0005.
- B25_40, truth=1: mean Δp -0.0080, fix 0.0049, harm 0.0026, net +0.0023.
- B41_80, truth=0: mean Δp +0.0030, fix 0.0000, harm 0.0000, net +0.0000.
- B41_80, truth=1: mean Δp -0.0073, fix 0.0002, harm 0.0000, net +0.0002.

Early Q5 net-fix interval: [-0.0027, +0.0061]. Keyhole Q5 interval: [+0.0024, +0.0063].

## Phase 1.14 B40 mechanism
P1−P0 revealed-Keyhole fraction -0.0235; residual SD +0.1537; held-out q20-Keyhole mean M3 probability -0.0111; q20-Keyhole recall -0.0237; active-query standardized spread -0.1532. These are paired path associations, not causal effects.

## Numerical reliability
P1 residual-SD upper-hit 65.7%; any-length upper-hit 75.1%; convergence 96.0%. Phase 1.14 L100/L1000 sensitivity does not trigger the predeclared unreliability rule, but bound pressure limits mechanistic interpretation.

## Acquisition recommendation
No Phase 1.15B replay yet. The recommendation is prospective and unvalidated; Phase 1.15A itself demonstrates no sample-efficiency gain.

## Claim boundary
The decomposition is not identifiable physics: h is derived from P,VX,LS and the residual uses those inputs. No universal acquisition, theoretical sample-complexity, external-transfer, causal-ARD, or broad novelty claim is supported.
