# Track 2 post-start declaration (written after 2 of 30 SVGP fits, before any held-out evaluation)

**Basis.** This declaration rests only on training diagnostics, not on any held-out result:
- In the first two separable-SVGP fits (`ckpt_r1_f1_B16` and `ckpt_r1_f1_B40`), the per-50-iteration training loss was still falling at iteration 2000 (−0.032 and −0.041 between the last two 200-iteration blocks).
- The learned time length scale was 0.22–0.26 in s units.

**The frozen protocol is unchanged.** All 30 frozen fits, with 2000 iterations and M = 400, are completed and reported as the primary SVGP result.

**Added sensitivity, POST-START.**
- **What runs:** `T2-PS1`, the same model, data, seed and M = 400 with **6000** iterations. It covers the five repeat-1 B40 checkpoints (`ckpt_r1_f{1..5}_B40`), which adds 5 fits.
- **Fit count:** the temporal/functional total becomes 128 of the 160 cap.
- **Hypothesis T2-PS1:** the simulation-weighted trajectory RMSE on these five checkpoints changes by less than 10 % (relative) between 2000 and 6000 iterations, meaning under-convergence is not the main driver of SVGP accuracy.
- **Falsified if** the relative change is 10 % or more.
- **Reporting:** the result is reported beside the frozen fits; it does not replace them.

The frozen M = 800 inducing-point check (`ckpt_r1_f1_B40`) is unchanged.
