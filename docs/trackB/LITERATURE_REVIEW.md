# Track B: targeted evidence review

Search and assessment date: **2026-09-27**. Scope: realistically observable LPBF signals used to infer a hidden physical state or a later defect. No new data, association screen, feature tuning or acquisition development was performed.

## Research answer

The broad idea is already established. Optical, acoustic and multimodal signals have been paired with synchrotron observations, metallographic sections, final XCT and simulation to infer keyhole behavior, melt depth or pores. Simulation-generated hidden-state supervision is also prior art, including preliminary simulation-to-experiment depth prediction. The unresolved thesis question is whether **our precisely defined, experimentally obtainable signal adds useful information beyond process settings under realistic measurement and independent validation**.

The closest precedents are L01-L05 and the recent L10-L13. A different simulator or an unreported name for a width statistic does not by itself create novelty. This targeted search is not an exhaustive systematic review or novelty clearance.

## Search scope and evidence standard

Searches combined `laser powder bed fusion` / `LPBF` with in-situ monitoring, width/length/area, coaxial/off-axis imaging, two-color pyrometry, photodiodes, acoustic emission, plume/spatter, OCT/inline coherent imaging, X-ray, keyhole, penetration, pores, simulation supervision, sim-to-real, virtual/soft sensing and digital twins. Recent 2024-2026 papers were checked specifically for overlap with the proposed contribution. Primary publisher pages, primary author manuscripts and NIST/NASA/institutional records were preferred.

**Twenty-four primary studies/records are assessed below.** Access depth differs: a full primary text or manuscript supports a methods-level reading; a publisher abstract/preview supports only the details shown there. This is not a claim that all 24 full papers were read. Unverified material, split details and latency are marked unresolved. Review-only leads and unrelated welding studies do not count as direct LPBF deployment evidence.

Ground-truth types must remain separate:

| Reference | What it can establish | What it does not establish automatically |
|---|---|---|
| Synchronized X-ray radiography | Cavity geometry, collapse or pore-generation events visible in the research specimen | Identical behavior in a production machine; final pore survival |
| Destructive section / microscopy | Retained track or melt-boundary geometry at sampled locations | Instantaneous cavity shape or exact onset time |
| Final XCT | Retained pore locations/geometry within resolution limits | One-to-one transient keyhole history; every generated pore survives |
| Simulation state | Precisely paired numerical observables and hidden states | Experimental truth or a faithful sensor observation model |
| Process/regime proxy | An operational class defined by a selected rule | Independent evidence that the hidden event actually occurred |

Online **acquisition** of a signal, offline **analysis** of that signal, a low inference time, and a prospectively deployed closed-loop system are four different claims. We preserve those distinctions below.

## Closest observable-to-hidden inference precedents

### L01 — Goossens & Van Hooreweder (2021)

[*A virtual sensing approach for monitoring melt-pool dimensions using high speed coaxial imaging during laser powder bed fusion of metals*](https://doi.org/10.1016/j.addma.2021.101923), Additive Manufacturing 40, 101923. **Access: publisher abstract.**

316L single-layer strips. GPU-processed coaxial images supply width; a physics-based depth/width model supplies penetration estimates. Independently sectioned, polished and etched strips provide geometry validation. The sensing is in situ; the depth validation is offline. No cross-machine validation was verified. This directly precedes width-assisted hidden-depth inference, but not our early width-change/keyhole-probability task.

### L02 — Ogoke et al. (2023)

[*Convolutional neural networks for melt depth prediction and visualization in laser powder bed fusion*](https://doi.org/10.1007/s00170-023-12384-z), International Journal of Advanced Manufacturing Technology 129, 3047-3062. **Access: full publisher text.**

FLOW-3D surface temperature and process inputs supervise CNN prediction of melt and vapor-cavity depth maps. The initial study uses 46 Ti64 simulations and five-fold validation; independence of every augmented frame's fold was not fully established in this review. A further 340 SS316L simulations support an experimental two-color-image test against etched sections at held-out settings. It is preliminary experimental transfer, not merely synthetic proof. Online implementation remains prospective. This rules out claiming that simulation-paired supervision or initial sim-to-real hidden-depth prediction is new.

### L03 — Ogoke et al. (2024)

[*Deep Learning for Melt Pool Depth Contour Prediction From Surface Thermal Images via Vision Transformers*](https://doi.org/10.1016/j.addlet.2024.100243), Additive Manufacturing Letters 11, 100243; [author manuscript](https://arxiv.org/abs/2404.17699). **Access: primary manuscript.**

Thermal image sequences feed CNN spatial embeddings and a temporal Transformer predicting cross-sectional contours. Forty usable power/velocity combinations remain from 64; 24 lacked measurable sections. Splits are by parameter combination, not adjacent frames. FLOW-3D/Eagar-Tsai pretraining and experimental fine-tuning test transfer with limited experimental conditions. Experimental material was not independently extracted in this review. Ground truth is microscopy, not time-resolved internal-state imaging. Temporal averaging preprocessing also requires latency accounting before an early-warning claim. This is a particularly close simulation-to-experiment precedent.

### L04 — Ren et al. (2023)

[Science 379, 89-94, DOI 10.1126/science.add4667](https://doi.org/10.1126/science.add4667). **Access: primary record/accessible paper content; exhaustive split audit not performed.**

Ti64 thermal imaging, operando synchrotron X-ray and multiphysics simulation connect keyhole oscillation signatures to pore-generation detection. The observable is thermal behavior; the hidden event is pore generation, not simply the run-level presence of a keyhole. Learning-based signal inference is supported; exact architecture and train/test grouping are left unverified here. The specialized simultaneous reference makes this stronger hidden-event supervision than a parameter-defined regime label. Its existence narrows the novelty space substantially.

### L05 — Ren et al. (2024)

[*Sub-millisecond keyhole pore detection in laser powder bed fusion using sound and light sensors and machine learning*](https://doi.org/10.1088/2752-5724/ad89e2), Materials Futures 3, 045001; [primary PDF](https://www.materialsfutures.org/en/article/pdf/preview/10.1088/2752-5724/ad89e2.pdf). **Access: full primary PDF.**

Ti64 thin-plate synchrotron experiments synchronously collect NIR images, microphones and a backscattered-laser photodiode. X-ray marks bubble separation/pore generation. Wavelet-scalogram/SqueezeNet classification uses 0.1 ms windows. Reported single-sensor accuracy exceeds 90%, with sensor-dependent results; this is not our expected accuracy. Full track-level split independence was not audited here. The geometry is beamline-compatible, and pore motion/remelting complicate final-defect interpretation. Strong observable-to-hidden-event precedent; it does not supply an SPH acoustic observation operator.

### L06 — Gorgannejad et al. (2023)

[*Localized keyhole pore prediction in laser powder bed fusion via multimodal process monitoring and X-ray radiography*](https://doi.org/10.1016/j.addma.2023.103810), Additive Manufacturing 78, 103810. **Access: primary record/abstract-level extraction.**

Ti64 coaxial/off-axis photodiodes and acoustic emission are paired with 20 kHz X-ray, allowing approximately 50 microsecond registration. Spectral/time-series features feed SVM/KNN/Gaussian-naive-Bayes models. Reported F1 reaches 0.95 in the studied setup; grouping and independent-machine validation were not verified. This is in-situ data with supervised hidden pore-event inference, not evidence for our width feature or final pore survival.

### L07 — Hamidi-Nasab et al. (2023)

[Nature Communications, DOI 10.1038/s41467-023-43371-3](https://doi.org/10.1038/s41467-023-43371-3); [primary full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC10697982/). **Access: primary abstract and methods extraction.**

Synchronized acoustic/X-ray measurements infer melting regimes with approximately 100 microsecond windows in 316L thin-wall remelting **without powder**. Acoustic signatures include the effect of pulsing. Exact classifier/split details are not claimed here. The experimental reference is unusually informative, but machine sound, powder and excitation changes matter for transfer. It supports acoustics as a real observation; it does not establish an acoustic channel in our SPH data.

### L08 — Pandiyan et al. (2022)

[Additive Manufacturing 58, 103007, DOI 10.1016/j.addma.2022.103007](https://doi.org/10.1016/j.addma.2022.103007). **Access: primary record/abstract-level extraction.**

316L multimodal back-reflection, visible, infrared and structure-borne acoustic signals feed CNN-LSTM classification of lack-of-fusion/conduction/keyhole regimes in 0.5-4 ms windows, with operando X-ray guidance. Exact grouping and domain-holdout design were not verified. Regime classification is useful prior art but distinct from calibrated run-level risk, instantaneous cavity-depth estimation and pore persistence. No performance number is imported into the thesis expectation.

### L09 — Tao et al. (2025)

[*Data-driven keyhole pore detection in laser powder bed fusion: Integrating process insights with X-CT*](https://doi.org/10.1016/j.jmapro.2025.03.107), Journal of Manufacturing Processes 142, 293-316; [publisher record](https://www.sciencedirect.com/science/article/abs/pii/S1526612525003597). **Access: publisher preview.**

Coaxial high-speed process images produce 88 morphology/thermal-distribution features. Final X-CT supplies pore outcomes, aligned using a many-to-one thermal-history construction; roughly 13 images occur during traversal of a location. Alloy, final estimator and grouped validation were not verified from the accessed preview. This is process-signal-to-retained-defect prediction. Registration and pore migration prevent treating its labels as exact transient keyhole-state truth.

### L10 — Taylor et al. (2026)

[*PI-TSAD: A physically informed time-series anomaly detection framework for real-time monitoring of keyhole collapse in laser powder bed fusion*](https://doi.org/10.1016/j.jmapro.2026.04.026), Journal of Manufacturing Processes 168, 178-191. **Access: primary abstract/preview.**

200 kHz coaxial photodiode emission, filtered over a physics-guided band, supplies time/frequency features to a random-forest anomaly detector. APS X-ray supplies collapse truth. Application without retraining to commercial DMG MORI LASERTEC 12 SLM build signals is compared with CT porosity. Material and complete validation design remain unresolved here. Distinguish synchronized collapse supervision from commercial-build final-defect correlation. The title's real-time claim is not independently verified end-to-end latency evidence in this review.

### L11 — Peng et al. (2025)

[*A sensor-integrated digital twin framework for molten pool monitoring of laser powder bed fusion*](https://doi.org/10.1016/j.compind.2025.104332), Computers in Industry 171, 104332; [publisher preview](https://www.sciencedirect.com/science/article/pii/S0166361525000971). **Access: abstract/preview.**

High-speed camera information and a POD-RBF reduced-order model estimate width, depth and mean temperature, with optical-microscopy geometry comparison. The reported scope includes conduction and slight-keyhole conditions. Material, independent partitions and the exact chronology of sensor calibration versus baseline ROM validation are unresolved from the preview. It supports a sensor/simulation virtual-sensing precedent; it is not evidence that an arbitrary simulator or a digital-twin label provides trustworthy hidden states.

### L12 — Zhang et al. (2026)

[*Insights beneath the surface: Physics-guided multi-task learning for in situ defect detection in laser powder bed fusion*](https://doi.org/10.1016/j.jmapro.2026.04.032), Journal of Manufacturing Processes 169, 126-136; [publisher record](https://www.sciencedirect.com/science/article/pii/S1526612526003907). **Access: publisher abstract/introduction.**

Paired synthetic top-view thermal videos and side-view depth supervise a ViViT multitask defect model. The auxiliary depth branch is removed at inference. Material, exact split construction and independent experimental transfer were not established from accessible methods. This is direct prior art for hidden simulation quantities supervising an inference system that receives only surface observations. Do not call synthetic performance external experimental validation.

### L13 — AlSi10Mg virtual-sensing study (2026)

[*Predicting melt pool geometry dimensions of AlSi10Mg single track in laser powder bed fusion using coaxial high-speed camera signals*](https://doi.org/10.1016/j.amf.2026.200303), Additive Manufacturing Frontiers 5(2), 200303. **Access: publisher abstract.**

10 kHz coaxial size/shape/intensity/texture features and power/speed predict depth and layer height with SVR, random forest and DNN. The abstract describes 330 tracks and an 80/20 split; regime-aware optimization is included. Destructive geometry motivates the targets, but exact reference preparation and split-group independence were not verified. Online sensing plus retrospective model validation is not proof of prospective operation. This recent study further reduces the novelty of simply adding camera features to process inputs for depth prediction.

## Measurement and physical-ground-truth papers

These papers establish what can actually be measured and how reference states are obtained. They are not all predictive-inference studies. Details relevant to the project's feature are consolidated in the [width reality check](WIDTH_EXPERIMENTAL_REALITY_CHECK.md).

| ID and citation | Process/material; observation | Target/model/reference and validation | Timing, limit and thesis relevance; access |
|---|---|---|---|
| L14 [Zheng et al. 2019, *Melt pool boundary extraction and its width prediction from infrared images in selective laser melting*](https://doi.org/10.1016/j.matdes.2019.108110) | Ti64; coaxial IR | Gradient-based boundary; width compared with microscopy | In-situ images/offline dimensional validation; exact early increment untested. Publisher abstract. |
| L15 [Lane et al. 2017, *Performance Characterization of Process Monitoring Sensors on the NIST Additive Manufacturing Metrology Testbed*](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=924025) | Nickel alloy 625; coaxial imagery | Sensor characterization and thresholded image geometry; no hidden-state classifier | Quantifies sensing constraints; optical pixel pitch is not effective resolution. Full primary PDF. |
| L16 [Zalameda et al. 2022, *Comparison of In-situ Near Infrared Melt Pool Imagery to Optical Microscopy Measurements*, NTRS 20220004217](https://ntrs.nasa.gov/api/citations/20220004217/downloads/thermosense2022jnzfinalv2.pdf) | Ti64 bare plate; calibrated coaxial NIR | Emissivity/solidus boundary and deblurring; serial-section comparison | Startup geometry has prior study; sections do not supply instantaneous keyhole truth. Full primary PDF. |
| L17 [Le et al. 2021, *Vision-based in-situ monitoring system for melt-pool detection in laser powder bed fusion process*](https://doi.org/10.1016/j.jmapro.2021.07.007) | IN718/316L; off-axis visible images | Perspective correction and derivative edges; microscope width comparison | Alternative measurement route, view dependent; no demonstrated transfer of our feature. Publisher abstract. |
| L18 [Myers et al. 2023, *High-resolution melt pool thermal imaging … using the two-color method with a color camera*](https://doi.org/10.1016/j.addma.2023.103663) | 316L/IN718/Ti64; two-color camera | Calibrated surface-temperature measurement; no hidden-state prediction model | Full melting boundary can lie outside measurable temperature range. Full primary PDF. |
| L19 [Fisher et al. 2018, *Toward determining melt pool quality metrics via coaxial monitoring …*](https://doi.org/10.1016/j.mfglet.2018.02.009) | Laser powder-bed-fusion testbed; alloy not verified in extracted evidence | Integrated emission correlated with ex-situ cross-sectional area | Fast signal acquisition; emission, image area and section area are different quantities. Full primary PDF. |
| L20 [Kanko, Sibley & Fraser 2016, *In situ morphology-based defect detection … through inline coherent imaging*](https://doi.org/10.1016/j.jmatprotec.2015.12.024) | LPBF; material unresolved; 200 kHz ICI | Surface morphology/ranging, not arbitrary hidden melt-boundary reconstruction | Specialized online optical access; actual Ioan instrument unknown. Publisher abstract/introduction. |
| L21 [Fleming et al. 2023, *Synchrotron validation of inline coherent imaging for tracking laser keyhole depth*](https://doi.org/10.1016/j.addma.2023.103798) | **Laser welding**, material unresolved; ICI + X-ray | Cavity-depth ranging checked against simultaneous X-ray | Cavity reflections/outliers; adjacent-process precedent, not direct LPBF deployment. Author repository abstract. |
| L22 [Bitharas et al. 2022, Nature Communications 13, 2959](https://doi.org/10.1038/s41467-022-30667-z) | Ti64; simultaneous schlieren and X-ray | Physical plume/keyhole/flow association, not a deployed classifier | Supports plume observability and mechanism; no unique mapping or SPH plume operator established. Full primary text. |
| L23 [Zhao et al. 2017, Scientific Reports 7, 3602](https://doi.org/10.1038/s41598-017-03761-2) | Ti64 miniature powder-bed specimen; stationary heating | High-speed synchrotron visualizes cavities/pores; measurement study | Research ground truth; specimen and stationary excitation differ from industrial scanning. Full primary text. |
| L24 [Weeks, Singh & Malen 2026, *Modeling internal reflections of thermal emission in melt pool keyholes to resolve discrepancies in simulated and measured temperatures*](https://doi.org/10.1016/j.addma.2026.105245) | Thermal imaging of concave hot/keyhole surfaces; material not verified | Radiation/reflection modelling addresses simulated/measured temperature mismatch | Measurement-operator precedent; not a validated SPH sensor model. Publisher abstract. |

## Observability inventory: how to read the evidence table

[`OBSERVABILITY_EVIDENCE_TABLE.csv`](OBSERVABILITY_EVIDENCE_TABLE.csv) preserves the original S01-S15 classifications in a separate column and adds modality rows. The original [`SIGNAL_INVENTORY.csv`](SIGNAL_INVENTORY.csv) is unchanged.

- **A:** strong literature evidence for online observation of the precisely named signal in some setup.
- **B:** plausible or demonstrated under specialized/setup-dependent conditions, or only a conditional analogue of the SPH quantity.
- **C:** offline/post-process outcome.
- **D:** project simulation-only/hidden field or target.
- **E:** unresolved definition, measurement route or transferable meaning.

Class A does not mean available to Ioan. The dedicated `confirmed_available_in_Ioan_setup` column is **UNKNOWN in every row**. Thus optical projected width may be A as a literature modality while the exact SPH molten-volume width remains B. X-ray and coherent cavity ranging do not silently promote internal SPH depth or topology into deployable predictors. A paper about melt-pool temperature also does not prove a substrate-temperature channel.

## What remains scientifically unresolved

1. **Target mismatch:** stable keyhole presence, unstable collapse, pore generation, retained porosity and melt penetration are distinct. Good results on one do not validate another.
2. **Time mismatch:** a run-level label can support run-risk inference; it cannot certify instantaneous-state estimation or early warning. Any later label definition must match the intended decision time.
3. **Measurement mismatch:** extrema of molten particles are not necessarily projected surface boundaries. Radiance is not simulator temperature. Camera noise augmentation alone does not establish a physical observation model.
4. **Validation mismatch:** adjacent frames are not independent runs. Held-out parameter conditions are stronger than random frame splits, but still differ from a held-out machine/material/build. Experimental use of a predictor is not equivalent to independent experimental truth for every prediction.
5. **Incremental-value mismatch:** a sensor can correlate with a label because both follow the same process inputs. The project needs a process-only comparison, not merely good sensor-only accuracy.

These limits support the [two-pair shortlist](OBSERVABLE_HIDDEN_PRIORITIES.md), [questions for Ioan](QUESTIONS_FOR_IOAN.md), and the present [B recommendation](TRACK_B_RESEARCH_POSITION.md). They do not justify a new acquisition method or changing the Track A freeze.
