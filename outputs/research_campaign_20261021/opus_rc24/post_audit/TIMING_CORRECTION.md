# Dated correction (2026-10-22) of the RC24 short-Keyhole timing statement

`hard_region/HARD_MECHANISM.json` (RC24, kept unchanged) has two defects:
- it took `forming_end` as the LAST "Forming Phase" frame of the whole record;
- it expressed times on a 0..1 relative axis.

From these it concluded: "every keyhole frame lies within forming + 10 %, so the short keyhole is a start-up transient at the end of the forming phase". That inference is not supported as stated:
- in 4 of the 10 runs the label re-enters "Forming Phase" after the first keyhole frame, so the first keyhole frame lies BEFORE that last forming frame;
- in 3 runs every keyhole frame ends before it;
- the condition "last keyhole frame ≤ forming_end + 0.10" says nothing about whether the event happens right when forming ends.

## Corrected diagnostic (`src/rc24p_timing.py` → `TIMING_DIAGNOSTIC.json`, `timing_frames_summary.csv`)

**Method.**
- Physical time of every saved frame is taken from the solver's `monitor/time.dat` against `iter.dat`. The frame interval is about 5.07 µs (median).
- The label sequence is segmented into runs of identical labels.

**10 NEW short-Keyhole originals:**

| quantity | result |
|---|---|
| first keyhole frame | in all 10 runs, the frame immediately after the FIRST contiguous forming segment |
| end of the first forming segment | 0.355–0.421 ms (median 0.406) |
| first keyhole frame | 0.360–0.426 ms |
| last keyhole frame | 0.395–0.511 ms (median 0.476) |
| keyhole duration | 5–19 frames (≈ 0.025–0.095 ms) |
| label pattern in 6 runs | Forming → Keyhole → Conduction |
| label pattern in 4 runs | Forming → Keyhole → Forming → (Keyhole → Forming …) → Conduction: the label alternates 2–3 times before conduction |
| labelling agreement | both labelling passes (`label_1`, `label_2`) mark every keyhole frame Keyhole; the per-frame label equals `label_final` everywhere |

**12 NEW conduction runs:**
- the first forming segment ends at 0.349–0.555 ms; one slow-scan run ends at 0.726 ms;
- they never carry a keyhole label.

## What can be said

**Supported.** In the label sequence, the short keyhole is a brief episode at the end of the first forming segment, about 0.4–0.5 ms after the start. In 4 of the 10 runs it is interleaved with forming labels.

**Not decided by these data:**
- whether this is a physical start-up transient (for example a depth overshoot when the melt pool first develops), or a structure created by how the regime labels were assigned at the forming / steady transition;
- the frame images (`frames/*.png`) referenced by `frames.csv` are not in the local copy, so the frames could not be inspected visually.

**Withdrawn.**
- "The short keyhole is a start-up transient at the end of the forming phase", as a mechanism statement.
- Any reading of the scalar-summary results (leave-one-out AUC 0.745; nothing added by the T0 summaries) as evidence that the region cannot be separated, or that it is aleatoric. Those results concern a few scalar summaries in a group of 21 runs only.

The corner is neither solved nor shown to be unlearnable.
