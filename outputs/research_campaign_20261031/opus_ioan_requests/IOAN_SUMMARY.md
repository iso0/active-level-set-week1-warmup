# Follow-up to our meeting of 30 October: physical outputs, width and depth

Burak Öztürk, 31 October 2026.

**Data:** all 541 simulations of the pool; no new simulations.

**Method:**
- All rules were registered before any result.
- Development data only. The fresh test was not needed (see 3).

## Questions you raised

1. Is kinetic energy (and temperature, flow) related to depth, not only to the label?
2. Is melt-pool width related to depth?
3. Does using these relations help us distinguish Keyhole from conduction with fewer simulations?

## Answers

**1. Yes, strongly, but through the inputs** (Fig. 1).
- Depth correlates with:

  | output | Spearman ρ with depth |
  |---|---|
  | kinetic energy | 0.90 |
  | maximum temperature | 0.85 |
  | velocity-spike ratio | 0.85 |
  | absorbed laser power | 0.82 |
  | total energy | 0.80 |

- Almost all of this shared variation is explained by the process inputs: by h = P/√(VX·LS³) alone, ρ(h, depth) = 0.945.
- Once the inputs are known, the residual correlation with depth is ≤ 0.27, the velocity-spike ratio (0.43) being the only exception.
- In conduction, depth grows with the melt-pool energy (KE, laser power, total energy: ρ 0.83–0.86).
- In Keyhole runs, depth is tied more to temperature and melt-flow speed (velocity spikes, maximum velocity) than to kinetic energy or absorbed laser power.

**2. Moderately overall (ρ 0.50), and differently in the two regimes** (Fig. 2).
- **Conduction:** depth ∝ width^0.90 and D/W ≈ 0.34.
- **Keyhole:** depth exceeds half the width (D/W ≈ 0.9–1.5).
- **The classical criterion** "Keyhole if W/D ≤ 2" gives balanced accuracy 0.978 with no fitted parameter. The thresholds 1.5 and 2.5 used in printability maps give 0.960 and 0.886.
- **But the information is in the depth:**
  - width alone has AUC 0.64;
  - near the regime boundary, width and depth are almost unrelated (ρ 0.11);
  - adding width to depth changes nothing.

**3. No** (Figs. 3–5).
- **True values:** even with the true simulated values, no output adds label information beyond h + depth. Each one changes the cross-validated log loss by between −0.001 and +0.015.
  - Depth carries everything the inputs say about the label.
  - The other outputs are "siblings" of depth (effects of the same cause), not mediators.
- **Learnability:** depth is the easiest output to learn from few simulations. Median test R² is 0.87 after 8 simulations and 0.92 after 24. Width plateaus near 0.73 and never reaches 0.8 in half of the runs.
- **Six candidate models**, built on the recorded learning paths, used width, KE or temperature to improve the depth prediction at unsimulated inputs:
  - joint multi-output GPs;
  - your input → hidden quantity → depth chain.
- **Result:** none improved early accuracy (best +0.0001); the chain models made it worse. Knowing the TRUE kinetic energy at the test points would add only +0.001.
  - This matches GP theory: when all outputs come from the same runs, their correlation cannot transfer new information about depth.
  - The registered rule therefore stopped before any confirmation run.

## Two further findings

- **Keyhole onset** (Fig. 6). Within a simulation, maximum temperature is the only signal that rises clearly before the first Keyhole-labelled frame (about 30 µs). In runs below the depth ceiling, absorbed laser power and width also rise beforehand; kinetic energy does not. Absorbed laser power then fluctuates together with the keyhole depth (within-run ρ 0.73).
- **A depth ceiling.** 134 of 197 Keyhole runs (68 %) reach about 300 µm. This is probably the bottom of the simulation domain or substrate; I could not verify it because the domain size is not in the files I have. Keyhole depths are therefore censored. This does not affect classification, since every run at the ceiling is Keyhole.

## Consequence for the thesis

The current model (C1: predicted depth + h) is sufficient. The extra physical outputs are informative about the physics but do not reduce the number of simulations. The remaining early error is the limit of what can be known about depth at unsimulated inputs.

**Figures:** `figures/fig1_correlation_with_depth.png` to `fig6_keyhole_onset.png`.

**Full report:** `FINAL_REPORT_IR.md`.
