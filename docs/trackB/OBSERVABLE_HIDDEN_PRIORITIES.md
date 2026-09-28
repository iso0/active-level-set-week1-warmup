# Track B: two defensible observable-to-hidden candidates

Research judgment, 2026-09-27. Preparation only; no association screen or new-data analysis executed. Track A remains frozen. These are candidates for discussion, not an approved experimental protocol.

## Selection principle

An impressive sensing paper is not enough. A thesis candidate also needs a corresponding SPH quantity, a physically defensible measurement definition, an independently defined target, and a feasible validation route. We retain **two** candidates. The first has direct project evidence; the second is conditional and less mature. Neither is yet confirmed available in Ioan's experiment.

| Priority | Observable -> hidden target | Repository support | Present decision |
|---|---|---|---|
| 1 | Early measured transverse-width change, conditional on process inputs -> probability of the run-level manual `has_keyhole` outcome | Existing width traces and the Phase 2.1R-E retrospective early-prefix result | First discussion candidate; measurement and timing gates must pass |
| 2 | Measured surface melt-pool width, optionally length/area if independently available -> below-surface **melt penetration** | Existing geometry/penetration definitions in Week 6 | Reserve candidate; require matched geometry and a paired target audit |

## 1. Early width change -> run-level keyhole probability

**Observable.** A width trace extracted from a documented camera view, then the existing maximum-positive-width-increment concept over a fixed causal prefix. Process inputs `[P,VX,LS,ST]` remain the comparison baseline. Do not transport the old numerical threshold, normalized-time window, or resampling choices directly to a camera.

**Hidden target.** Initially the existing *simulation-level* manual binary label. That supports probability of the labelled run outcome conditional on observations so far. It does not establish instantaneous keyhole presence, a transition timestamp, pore formation, or positive warning lead time. An instantaneous/early-warning target would require separately confirmed time-resolved labels and a decision horizon.

**Physical rationale (hypothesis).** Startup surface expansion may reflect how energy couples into the material and how the molten region develops; this may carry information beyond commanded settings. A change in surface width is not a unique measurement of subsurface morphology. The old association does not establish a causal mechanism.

**Experimental evidence.** Coaxial image-derived width has been demonstrated, including comparison with cross-sectioned melt-pool dimensions in [Goossens and Van Hooreweder (2021)](https://doi.org/10.1016/j.addma.2021.101923). That supports a measurement route, not equivalence with SPH extrema or recovery of the present startup feature. See [the width reality check](WIDTH_EXPERIMENTAL_REALITY_CHECK.md) for sampling and boundary-definition evidence.

**Simulation evidence.** [Phase 2.1R-E](../../outputs/week9_phase2_1re_early_prefix_width_control/FINAL_PHASE2_1RE_REPORT.md) retained 350 of 405 runs; the first ten transitions on the 201-point resampled grid span a median 68 microseconds. The result supports modest incremental ranking information, with no supported hard-classification improvement in that early-prefix comparison. The feature is dominated by startup; it is not a measured keyhole-onset detector. [Phase 2.2](../../outputs/week9_phase2_2_width_informed_active_learning/FINAL_PHASE2_2_REPORT.md) supplies no successful acquisition claim.

**Main confounder.** Process settings, startup definition and observation cadence can drive both the feature and the outcome. Optical threshold changes and failed width extraction may dominate the observed increment. Missing traces are a selection issue, not an invitation to use simulator missingness as a sensor.

**Leakage risk.** Whole-trace normalization, interpolation requiring a later raw sample, choosing the largest jump after the decision time, class-dependent segmentation, and splitting adjacent frames of the same run across train/test. The existing no-later-grid-point check is useful retrospective evidence but does not certify a causal camera pipeline.

**Expected thesis value.** A bounded test of whether a simulation-derived association survives an experimentally realistic measurement operator and adds discrimination **and** probability quality beyond process inputs. A well-explained failure under realistic sampling is useful thesis evidence. Another positive random split on the old runs would add little.

**Ioan must confirm.** Camera/raw frames, actual frame rate/exposure/pixel scale, laser-on synchronization, width definition, accessible raw SPH geometry and time axis, meaning/timing of manual labels, and the independent experimental reference. All actual-setup availability remains UNKNOWN.

## 2. Surface geometry -> below-surface melt penetration

**Observable.** Calibrated surface width at a matched time or spatial track location; length/area are optional only if the measurement definition and SPH support are confirmed. This is not a request to screen a large shape-feature family.

**Hidden target.** Melt penetration below the original surface. The repository defines penetration as `max(0,-z_min)`; total height `z_max-z_min` is a different response. Melt penetration also differs from vapor-cavity depth. Neither should be renamed keyhole depth without a separate definition.

**Physical rationale (hypothesis).** Surface and subsurface molten geometry share heat-input and heat-transport constraints. Width alone need not identify depth uniquely; the relationship depends on regime, beam shape, material and history. A conditional probability or uncertainty interval is more defensible than a universal width-to-depth rule.

**Experimental evidence.** Width-assisted virtual depth sensing already exists ([Goossens 2021](https://doi.org/10.1016/j.addma.2021.101923)). Simulation-trained surface-temperature-to-depth prediction with an experimental cross-section comparison also exists ([Ogoke et al. 2023](https://doi.org/10.1007/s00170-023-12384-z)). These are direct precedents, not evidence that our SPH output transfers.

**Simulation evidence.** The existing [Week 6 response-analysis source](../../src/week6_phase4_new_outputs_feature_effects.py) retains distinct width, total-height and penetration targets. It establishes that corresponding physical quantities have existed in this project. It does **not** establish a complete, synchronized paired dataset in the forthcoming batch or comparability of its temporal summaries with experimental metallography. No paired association has been executed here.

**Main confounder.** Common dependence on power/speed/spot size and the conflation of maximum, time-averaged and sectioned-track dimensions. A final cross section is an independent measurement of a retained geometry envelope, not instantaneous cavity truth.

**Leakage risk.** Supplying hidden depth/phase fields as predictors, deriving target and predictor from an experimentally inaccessible identical mask, or treating many frames from one track as independent observations. Target availability in simulation cannot certify observable availability.

**Expected thesis value.** A physically interpretable fallback if width timing cannot support the first candidate but paired surface geometry and reliable penetration references exist. Its broad task is already established; value must come from a useful validation question or quantified limits in this specific setup, not a claim to invent virtual sensing.

**Ioan must confirm.** Which depth definition and temporal/spatial support are scientifically relevant; whether raw SPH fields and paired width/penetration survive; whether sectioned tracks, OCT with validated interpretation, or another independent reference are available; and whether this question matters more than the binary target.

## Why there is no third priority

Acoustic emission, photodiodes, plume/spatter imaging, pyrometry and OCT are credible literature modalities. The current inventory does not establish their corresponding SPH observation streams or a validated forward model. Temperature fields alone are not radiance; fluid variables alone are not a microphone waveform. Creating such a bridge could become substantial new work, but it cannot be assumed into this thesis while Ioan's setup is unknown.

Likewise, final porosity is a different outcome from keyhole formation. A new pore-prediction direction would require retained pore labels and experimental registration, neither established by the present inventory. Do not fill the shortlist to three merely because three were allowed.
