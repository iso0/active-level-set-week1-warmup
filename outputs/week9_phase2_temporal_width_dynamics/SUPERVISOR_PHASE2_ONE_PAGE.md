# Supervisor Phase 2 — one page

## What Ioan asked
Whether temporal melt-pool width development, W(t) and dW/dt, distinguishes eventual Keyhole tracks and can add monitoring information beyond the pre-process physics score h.

## Data and derivative
350/405 simulations have technically usable pinned traces (70 Keyhole, 280 Conduction); 55 are missing/unusable and were reported rather than silently dropped. Following the explicit Phase 2 protocol, W is `x_max - x_min` in metres. Historical Week 6/7 code calls ΔX “length” and ΔY “width”; this nomenclature conflict is a central limitation. The primary derivative is a centered physical-time finite difference, displayed in **µm/ms**, over the active interval only. A fixed five-point local-linear slope is the non-tuned robustness version.

## Clearest temporal difference
Static/profile width is clearly larger for eventual Keyhole tracks: median W_max is 552.5 versus 378.6 µm, and median W_T0 is 511.5 versus 370.0 µm.

The largest predeclared feature effect was `early_dWdt_20_um_per_ms`: Conduction median -424, Keyhole median 271.3, Cliff's delta +0.869 (median-difference 95% bootstrap interval [+574.5, +956.3]).

This raw finite-difference separation is **not robust to the fixed mild local-linear derivative**: the corresponding robust early-20% medians are 604.3 versus 474.9, Cliff's delta -0.190, with median-difference interval [-188.1, -46.07]. Raw pointwise dW/dt therefore must not be treated as a stable physical discriminator here.

## Prediction beyond h
On Fold-B1-q20, repeat-level balanced accuracy was h-only 0.821, static width 0.654, width dynamics 0.734, and h+width dynamics 0.790. The paired h+width minus h effect was -0.031 [-0.039, -0.024]. Keyhole recall changed from 0.731 to 0.675; paired difference -0.055 [-0.065, -0.044]. On q20 OOF occurrences, width corrected 5 h errors and worsened 45 h-correct cases.

## Early information and onset language
The prefix models use only samples at or before each declared τ. At τ=0.20 the q20 balanced-accuracy contrast is -0.006 [-0.013, +0.001], so there is no statistically supported useful early prefix. Outcome: **NO INCREMENTAL SIGNAL**.

First-observed manually labelled Keyhole timing is available for 70 usable Keyhole tracks. A raw dW/dt peak precedes the first observed Keyhole frame in 25.7%; the robustness-derivative peak does so in 97.1%, with median descriptive lead 0.248 ms among those cases. The robust peak is usually the generic startup-growth peak and is not Keyhole-specific. The onset result remains **QUALIFIED** because saved frames are sparse, peak timing is not a trained warning score, and continuous physical onset is unknown. No validated pre-onset warning is claimed.

## Recommendation
Use the temporal profile, PCA, and leak-free model comparison as evidence about monitoring value. Do not call eventual-Keyhole prefix prediction a verified pre-onset warning. The next step, only if desired, is denser frame-level onset annotation or prospective top-view measurements.
