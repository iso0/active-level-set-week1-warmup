# Width: experimental reality check

Assessment date: 2026-09-27. No new simulation or statistical association analysis was run.

**Width can be estimated during LPBF in documented optical setups. The exact SPH early maximum-positive-width-change feature is not yet an experimentally validated quantity.** Actual availability in Ioan's setup is UNKNOWN.

## Three different widths

| Quantity | How obtained | What it describes |
|---|---|---|
| SPH transverse extent | `Ymax-Ymin` of the retained molten-region bounds | Extent of the simulator's selected molten volume; depends on particle/phase selection |
| Optical width | Boundary of a projected, thresholded or calibrated image region | Visible/radiant surface support under a particular wavelength, view, exposure and segmentation rule |
| Metallographic track/pool width | Microscopy of retained material or sectioned track | Post-process geometry at sampled positions; not a movie of the instantaneous liquid boundary |

These can correlate without being numerically interchangeable. A coaxial view reduces perspective complications; off-axis images require geometric correction and can still have occlusion. Neither view automatically reproduces extrema over the complete molten volume. Width measured perpendicular to the scan direction, ellipse minor-axis width and image-axis bounding-box width also need not coincide.

## What primary measurement papers demonstrate

| Source and access | Setup and actual reported sampling | Boundary/validation | Implication and limit |
|---|---|---|---|
| [Lane et al. 2017, NIST AMMT sensor characterization](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=924025), full primary PDF | Nickel alloy 625, bare plate/powder; coaxial 30,000 fps, 33 microsecond exposure, 20 micrometres/pixel; 850 +/- 20 nm | Thresholded imagery, major/minor axes; sensor characterization | Demonstrates fast optical geometry. Actual experiment rate must be distinguished from higher advertised camera capability; pixel pitch is not optical resolution. |
| [Zheng et al. 2019](https://doi.org/10.1016/j.matdes.2019.108110), publisher abstract | Ti-6Al-4V; coaxial infrared LumaSense MCS640; frame rate/pixel size not independently verified here | Spatial temperature-gradient boundary; average transverse width compared with microscope track width | Supports online-width estimation, with best reported discrepancy around 5%; not validation of a 68 microsecond transient or an identical molten-volume boundary. |
| [Le et al. 2021](https://doi.org/10.1016/j.jmapro.2021.07.007), publisher abstract | Off-axis visible camera; IN718 and 316L; rate/pixel scale unresolved in accessed text | Perspective transformation; gray-profile/derivative boundary; 316L width compared with microscopy | Reported width discrepancy within 6% does not validate every material/view or the length estimate, whose comparison partly uses numerical results. |
| [Zalameda et al. 2022, NASA NTRS 20220004217](https://ntrs.nasa.gov/api/citations/20220004217/downloads/thermosense2022jnzfinalv2.pdf), full primary PDF | Ti-6Al-4V bare plate; coaxial approximately 2,000 fps, 200 microsecond exposure, 8.55 micrometres/pixel | Blackbody calibration, emissivity/solidus-based boundary, serial-section microscopy, deblurring | Larger startup widths are discussed in relation to startup velocity. Temporal/startup geometry is therefore prior art; this is not the exact maximum-positive-increment classifier. |
| [Myers et al. 2023](https://doi.org/10.1016/j.addma.2023.103663), [full primary PDF](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=935822) | 316L, IN718 and Ti64; two-color thermal imaging at 22,500 fps; 5.6 micrometres/pixel, 3x3 demosaicing neighborhood of 16.8 micrometres | Blackbody calibration; spectral-emissivity assumptions remain | Under the selected exposure/dynamic range, temperatures below 2000 K were not measurable; full melt-pool length was not measured. A high-speed thermal movie need not reveal the actual melting boundary. |

The papers use different definitions and references. Their quoted errors are not a pooled accuracy estimate and cannot be transferred to Ioan's machine. Primary abstracts are explicitly labelled where full methods could not be inspected; missing rates are left missing.

## The project's feature and its clock

The inspected sources are [`_parse_trace`](../../src/week9_phase2_temporal_width_dynamics.py), [`transition_table` / `simple_features`](../../src/week9_phase2_1r_simple_width_change_control.py), and [`build_prefix_features`](../../src/week9_phase2_1re_early_prefix_width_control.py).

- The trace parser obtains transverse width from `(bounds[:,3]-bounds[:,2])*1e6`, retains a valid interval, and uses normalized time based on retained duration before interpolation to 201 analysis points.
- `max_positive_delta_W` is the largest positive difference between successive **resampled analysis points**, or zero if no increment is positive. Dividing by time produces a different feature.
- At 5%, the prefix contains ten transitions. The [existing report](../../outputs/week9_phase2_1re_early_prefix_width_control/FINAL_PHASE2_1RE_REPORT.md) gives a median 68 microseconds and 95.4% equality with the full-trace maximum on the 350 usable runs. These are previously computed results, not a new screen.

For orientation, ten transitions in 68 microseconds means about 6.8 microseconds per interval, or approximately **147 kHz** for literal sampling at that median spacing, before exposure and processing latency are considered. This arithmetic is not a universal camera requirement: the simulation durations vary, resampled values are not raw observations, and a different experimentally defined statistic might use another cadence. Such a change needs pre-label scientific agreement; it must not be chosen from outcome performance.

A 10 kHz camera has 100 microseconds between samples; the 30 kfps and 22.5 kfps examples above have roughly 33 and 44 microseconds respectively. Demonstrating optical width at these rates does not demonstrate recovery of the ten-increment startup statistic. Long exposure further averages the motion. More interpolation cannot recover lost temporal information.

## A plausible experimental analogue

The analogue would be a maximum positive increment in an image-derived transverse-width sequence, over a window fixed relative to an observed laser-on trigger, with fixed sampling, exposure, segmentation and one-sided preprocessing. This is plausible in principle, subject to actual sensor performance. It is **not** a validated transfer of the numerical SPH feature.

The current prefix audit checks that no later *analysis-grid point* is included. Prospective extraction also needs to establish that the grid/window duration was known at prediction time and that interpolation or smoothing uses no raw sample arriving after that time. A percentage of completed trace duration is not automatically an online clock. This limits deployment interpretation without changing the historical retrospective result.

## Why the maximum increment is especially vulnerable

- A single spatter attachment or segmentation jump can determine the maximum. Increasing frame count changes the opportunity for an extreme noise increment.
- Plume, ejecta, vapor and changing reflections can alter the apparent boundary without moving the liquid boundary.
- Thresholds, emissivity, spectral response, saturation and focus can change width estimates. Two-color methods still require appropriate spectral-emissivity assumptions; they do not make every pixel a perfect thermometer.
- Exposure, perspective correction, demosaicing, pixel scale and spatial point-spread effects change small increments. Nominal micrometres/pixel are insufficient to specify measurement uncertainty.
- A startup-velocity transient or trigger offset can masquerade as a physically diagnostic startup response. Width-monitor failure must be analysed as measurement quality, not treated as a free predictor of keyhole state.

[Weeks et al. 2026](https://doi.org/10.1016/j.addma.2026.105245) specifically studies thermal-emission reflections in keyhole geometry and simulated/measured temperature discrepancies. This reinforces the need for a measurement model when importing simulator temperature or geometry into optical inference; the accessible primary abstract does not provide a validated observation model for our SPH data.

## Decision before any new association screen

Obtain the actual raw stream specification and an agreed width definition. Establish view/phase correspondence, a causal absolute-time window, and a measurement-error/availability policy. Ask whether the available cadence can resolve the phenomenon of interest; if it cannot, report that limitation before fitting another model.

The targeted search found prior startup-width and temporal imaging studies, but no verified experimental study using this exact early maximum-positive-increment definition. That is an unresolved search result, **not evidence of novelty**. The defensible present conclusion is experimental plausibility with an unproven measurement and transfer bridge.
