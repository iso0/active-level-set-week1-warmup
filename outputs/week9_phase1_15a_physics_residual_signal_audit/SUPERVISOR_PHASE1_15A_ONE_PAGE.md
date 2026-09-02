# Supervisor Phase 1.15A — one page

**Decision:** `CORRECTION_SIGNAL_PARTIAL`

- Reconstructed the H and M3 components at ten budgets on the already-published P1 path; no new active-learning trajectory was run.
- Large-correction Q5: fix 0.005, harm 0.006, net -0.001; repeat CI [-0.001, +0.001].
- Pooled Q5 q20-like enrichment 2.34×; mean per-run 2.92×, repeat CI [2.75, 3.09].
- Correction magnitude is highly redundant with margin (rho -0.95); early Q5 net-fix CI [-0.003, +0.006].
- At B40, P1−P0 q20-Keyhole mean M3 probability -0.011 and recall -0.024; descriptive, not causal.
- Numerical pressure remains high (residual upper-hit 66%, length upper-hit 75%), although convergence is 96% and L1000 sensitivity was locally stable.
- Future replay recommendation: **No Phase 1.15B replay yet**. A1 remains a simple design only if later evidence separates correction value from ordinary margin.

Closest literature already covers active discrepancy learning and physics-informed prior-mean GP active learning; any novelty possibility is narrow and unresolved.
