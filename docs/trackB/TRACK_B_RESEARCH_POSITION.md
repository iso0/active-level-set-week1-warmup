# Track B research position

Assessment date: 2026-09-27. Literature-led judgment; no Track B association screen or new Ioan data analysis executed.

## Recommendation: B now; A is conditional

**B. Track B is useful, but should currently remain a bounded application and validation study.** It has a coherent question and an existing simulation-side lead. It does not yet have confirmed experimental observations, an equivalent measurement definition, time-resolved hidden-state truth, or evidence of transfer. Those are research dependencies, not coding gaps.

**A can become defensible** if Ioan can provide a realizable sensor-to-SPH mapping, independently labelled experimental observations, and a sufficiently distinct question about incremental information, calibrated uncertainty or transfer failure. This would support considering a substantial second contribution. Passing those gates does not guarantee paper novelty or a positive result.

**C is too strong.** Existing literature makes the broad invention claim redundant, but it does not answer whether this project's specific signal is useful after measurement constraints and process inputs are accounted for. A carefully delimited result, including a credible null result, can contribute to the thesis.

## What the literature already settles

The [targeted literature review](LITERATURE_REVIEW.md) separates observed quantities, hidden truth and validation design. Three precedents are sufficient to rule out a broad novelty claim:

- Image-derived width has already been combined with a physical model to estimate depth and checked against metallographic sections: [Goossens and Van Hooreweder, 2021](https://doi.org/10.1016/j.addma.2021.101923).
- Simulated surface-temperature fields have already supervised hidden melt-pool/keyhole geometry prediction, with an initial experimental thermal-image/cross-section comparison: [Ogoke et al., 2023](https://doi.org/10.1007/s00170-023-12384-z).
- Optical/acoustic signals have already been used for keyhole-pore detection with synchronized X-ray supervision: [Ren et al., 2024](https://doi.org/10.1088/2752-5724/ad89e2).

Thus Ioan's broad idea is **known and actively developed**, with transfer and trustworthy state estimation still dependent on sensor, material and target. Simulation-generated paired supervision is not itself novel. A different simulator, a simpler classifier, or a different width statistic alone does not establish a substantive advance. The 2024-2026 work documented in the review makes this caution more, not less, necessary.

This is a targeted reconnaissance, not an exhaustive novelty clearance. No claim of being first is warranted by failing to find a paper with the exact feature name.

## The strongest defensible research question

> At a prespecified time after laser-on, does an experimentally realizable, causally extracted transverse-width signal add useful discrimination and probability quality beyond `[P,VX,LS,ST]` for the independently defined run-level keyhole outcome, and how much of that added information survives matching SPH outputs to the sensor's spatial and temporal resolution on independent runs or batches?

This is the question supportable by the existing run-level label. If Ioan instead wants current-state estimation or advance warning, replace the target only after an independent time-resolved state/onset definition and horizon are available. The historical startup feature must not silently become an onset detector.

Experimental calibration/transfer is a later claim level requiring untouched experimental reference data. If the forthcoming data are SPH only, the permitted conclusion stays within simulation. A new simulation campaign may test simulation-domain generalization without becoming experimental validation.

## Why width remains a candidate, not a promised contribution

The [early-prefix report](../../outputs/week9_phase2_1re_early_prefix_width_control/FINAL_PHASE2_1RE_REPORT.md) shows modest ranking gains on the usable old-data subset. It does not establish a strong standalone sensor or hard-classification improvement. Its ten-transition window has a median duration of 68 microseconds. Sensor cadence and exposure may erase or reshape the statistic before any machine-learning choice matters.

The SPH quantity `Ymax-Ymin` across a molten region and an optical thresholded surface width are different estimands. A full-trace normalized time axis also needs a prospectively known timing rule before it can define an online prefix. These are reasons to assess measurement fidelity, not to tune more width features on OLD-405.

Even an ideal surface signal need not uniquely determine an internal state. Similar surface observations can accompany different subsurface histories. The inferential goal should therefore be a validated conditional probability with quantified limits; deterministic reconstruction and guaranteed early warning are stronger claims requiring different evidence.

## What would justify expanding the contribution

| Gate | Evidence needed | If unavailable |
|---|---|---|
| Physical observation | Actual sensor, raw stream, calibration, exposure/cadence and extraction definition | Keep signal labelled plausible; no online-feasibility claim |
| Matched simulation quantity | Explicit sensor observation operator or justified view/threshold/time correspondence | Report definition mismatch; do not call extrema a camera measurement |
| Independent truth | Precisely defined run/state/depth/outcome reference with registration | Restrict to simulation labels and their scope |
| Incremental information | Prespecified process-only comparison, grouped validation, missingness/time-leakage checks | Signal-only accuracy is insufficient |
| Transfer | Untouched relevant experimental domain and train-only preprocessing/calibration | No experimental-transfer claim |
| Distinct research value | Clear unresolved question relative to the closest papers, including recent work | Retain a smaller thesis study rather than promise a new method paper |

No numerical acceptance threshold, signal window, model family or statistical screen is frozen by this recommendation. Those choices require Ioan's target/setup decision and the existing [association-screen prerequisites](ASSOCIATION_SCREEN_PLAN.md). This document does not execute or approve that screen.

## Consequence for the thesis direction

Keep Track A closed and execute its external test only after the receipt/freeze gates. Keep the width result as a modest simulation proof of concept. Refine Track B from a broad hidden-state prediction claim into a measurement-aware, process-conditioned validation question. There is no evidence here requiring a change to the current M3 control, Candidate B, primary endpoint, or frozen conclusions.

The next useful investment is obtaining Ioan's sensor and target specification. A broad new feature/model search or a general-purpose digital twin would get ahead of the available evidence.
