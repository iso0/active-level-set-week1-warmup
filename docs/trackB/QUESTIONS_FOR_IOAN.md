# Track B: concise decisions for Ioan

Prepared 2026-09-27. This is a checklist, not a sent message. The repository already establishes `ST` as substrate temperature, the manual `has_keyhole` target, modest width-ranking evidence, failed width acquisition, and the frozen Track A decision. Those facts are not questions to reopen.

## The six decisions needed first

1. **Which experimental setup and observation streams can we actually obtain?** Identify material/process regime, machine, coaxial or off-axis camera, thermal camera/pyrometer, photodiode, microphone, OCT, and whether raw frames/waveforms or only vendor summaries can be shared. Which of these is already installed and synchronized? Literature availability is not setup availability.
2. **What is the intended hidden target and decision time?** Choose run-level probability of ever being labelled keyhole, current keyhole state, future onset within a specified horizon, melt penetration, or retained defect outcome. Is the objective probability estimation, thresholded classification, or early warning? The existing binary label supplies no onset timestamp.
3. **How will the target be independently verified?** Are synchronized X-ray observations available, or only sectioned tracks/final XCT/manual inspection? For each available reference, what physical quantity, timestamp/spatial registration and uncertainty does it supply? Cross sections and final pores do not automatically label transient keyhole presence.
4. **Can the available width measurement resolve the proposed event?** Provide frame rate, exposure, object-plane pixel scale, latency, laser-on trigger and field of view. Can the actual surface-width boundary be extracted during the run? The current simulation feature spans a median 68 microseconds; a generic statement that the camera is high speed is insufficient.
5. **Can we match the simulation and sensor definitions?** Do retained raw SPH fields permit a view-matched surface width rather than only all-molten-particle `Ymax-Ymin`? Are raw times and laser-on events retained? Is the experimental thermal output calibrated temperature or radiance/intensity, and what calibration/emissivity/occlusion information accompanies it? Which simulation quantities have defensible sensor analogues?
6. **What independent validation can this thesis realistically support?** Can an untouched experimental set with grouped runs/builds and independent reference labels be reserved? If only new SPH runs will exist, should Track B explicitly remain a simulation-domain application/measurement-feasibility study? Which of the two [candidate pairs](OBSERVABLE_HIDDEN_PRIORITIES.md) answers your intended scientific question?

## Information to request with the answer

- One sensor specification or example acquisition schema, with no future external labels exposed to the method team.
- A target annotation definition and its observation time; an example definition is enough before label access.
- Definition of independent units: repeated configurations, scan tracks, builds, material batches, and simulator revisions.
- Whether `P`/`VX` are commands or measured delivered quantities, the beam-radius calibration for `LS`, and setpoint versus measured substrate temperature for `ST`.
- Permission/ownership route for measurement data and the person who will hold the sealed target oracle.

## Separate Track A arrival decisions

Track A does not need a new method. Its [arrival runbook](../external_validation/NEW_DATA_ARRIVAL_RUNBOOK.md) identifies the label-free, dataset-specific grouping, splits, repeats, seeds, feasible B16-B80 horizon and failure rules that still need to be sealed. Supply provenance and a separate feature manifest before any label file is opened. If a training pool cannot reach B80, defer or record an explicit pre-label amendment; do not shorten the endpoint automatically.
