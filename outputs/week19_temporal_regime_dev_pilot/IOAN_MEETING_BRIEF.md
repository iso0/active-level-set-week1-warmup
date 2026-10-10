# Meeting brief for Ioan: Week 19 (10 October 2026)

**Purpose.** We would like your judgement on six NEW simulations where monitored melt depth and the recorded Keyhole/Conduction labels disagree or switch quickly. Nothing has been relabelled or excluded.

**How to look.**
1. **[Gallery](ioan_gallery/GALLERY.md).** 30 native images (10 frames × front/side/top), with exact frame, iteration and monitor time, and links to the originals. No labels or predictions are shown.
2. **[Key](ioan_gallery/KEY.md).** Recorded labels, monitored depths and model predictions. Open it after your first pass.
3. **Background.** The [summary](IOAN_SUMMARY.md), the [pilot report](PILOT_REPORT.md) and the [review](review/REVIEW.md).

**Image usability** (no morphology judgement):
- 22 of the 30 images show content.
- 6 are nearly empty, 1 is blank and 1 shows content only at its border.
- G2 has no usable image.
- G5's frame follows a sharp depth drop; the preceding frame is not included.

**Pilot, briefly.** On development folds only, a Gaussian-process model of the active-window depth classified held-out NEW runs better than the same model of the whole-record maximum: balanced accuracy 0.73 vs 0.63, with 40 training runs per fold.

Limits:
- the result is exploratory and unconfirmed;
- the depth window was chosen after the labels were seen;
- there are only 12 negatives;
- the gain mixes changed depth predictions with changed thresholds;
- four fast-scan negatives stay misclassified.

**Questions**

**Q1.** G4 and G5 have similar inputs and depth trajectories, but opposite recorded labels; the morphology difference has not been established. Do frames 81 and 82 differ in a way your labelling criterion uses?

**Q2.** What separated Keyhole from Conduction near the startup depth peak in fast scans (VX > 0.85 m/s)?

**Q3.** The front and side views in G1 (frame 364) and G2 (frames 340, 398) show only background. Is the melt pool outside the camera field, and should such frames carry regime labels?

**Q4.** G2's monitored depth stays near 310 µm after its derived exit time, while its images show nothing. Is that physical, or an artefact of the melt bounds?

**Q5.** In G3, labels switch between Keyhole and Conduction across adjacent frames, about 5 µs apart. Is that physical alternation or label flicker?
