# Track B literature questions

This is a review agenda, not evidence that a modality works in the intended setup.

## Measurement feasibility

1. Which in-situ modalities can estimate melt-pool width, length, projected area, or shape during the relevant process, and at what frame rate, spatial resolution, latency, and viewing geometry?
2. How is “melt-pool width” operationally defined in experiments, and can that estimand be matched to the SPH transverse-width trace?
3. Which occlusion, plume, spatter, saturation, emissivity, focus, and segmentation effects bias those measurements?
4. Can a maximum positive width change be estimated robustly at a prespecified early prefix, or is it dominated by sensor/segmentation jitter?
5. What calibration objects, uncertainty budgets, and synchronization procedures are required?
6. Which temperature-related observables are genuine temperature estimates, and which are only radiance/intensity proxies?

## Hidden-state definition

7. How is keyhole formation operationally defined in comparable experiments: direct observation, post-process evidence, acoustic/optical proxy, or model-based label?
8. At what time can experimental ground truth be assigned, and is it independent of the candidate signal?
9. Does the simulation `has_keyhole` label correspond to the same physical event and time scale as the proposed experimental target?
10. Which hidden states are mutually distinguishable from the available surface observations, and under what process regimes?

## Transfer and validation

11. What domain shifts arise between SPH geometry signals and camera/pyrometry signals?
12. Are reported observable-to-keyhole associations validated across machines, materials, optics, and operating regimes?
13. How are class prevalence, run grouping, temporal leakage, and measurement failure handled?
14. What evidence would support probability calibration rather than ranking alone?
15. What independent experimental sample size and success rule are realistic before any deployment language is used?

Each reviewed paper or setup note should be entered with the exact modality, material/process regime, signal definition, target definition, timing, sample size, validation design, and limitations. Generic statements such as “a camera can see width” are insufficient.
