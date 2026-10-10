# Key to the six-case gallery (open after the first pass)

*Recorded labels (`label_final`, canonical `has_keyhole`), monitored melt-subset depth at the frame's exact monitor row, and the pilot's B40 predictions. The depth is a melt-bound reading, not an image-derived cavity measurement. The predictions are post-hoc DEV predictions from the Week 19 pilot; they are not evidence about these runs' morphology.*

## G1 = H-349225d53c (has_keyhole = 1)

Full ID: `P-351p92267109_VX-0p98107853237_LS-4p98248594664e-05_ST-477p481832276_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p91716049617e-06_H-349225d53c`  
Why selected: late Keyhole at shallow depth. Are its Keyhole frames (all after the 90 % cutoff, around the exit) consistent with a keyhole at 80–90 µm depth?  
Bracket: Keyhole frames, first to last; frames 248–364 (1.229302–1.804600 ms); labels in bracket K. 1 Keyhole run; 90 % cutoff at 1.112 ms, derived exit at 1.235 ms.  
Whole-record max 88.81 µm; A (active window) 79.04 µm.

**Note.** At frame 364 (the last Keyhole frame) the monitored melt depth is 0.00 µm, and the front and side views are nearly empty.

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 248 | 1.229302 | Keyhole | 70.25 |
| 364 | 1.804600 | Keyhole | 0.00 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 0.995 / Keyhole | 0.621 / Keyhole |
| ACTIVE_E1_SHARED | 0.352 / no Keyhole | 0.001 / no Keyhole |
| G3_SHARED | 0.700 / Keyhole | 0.834 / Keyhole |

## G2 = H-f4fc937e86 (has_keyhole = 0)

Full ID: `P-353p784791664_VX-0p953661701626_LS-4p00659722232e-05_ST-310p795032219_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p05852399734e-06_H-f4fc937e86`  
Why selected: late-window maximum. Is the 312 µm depth after the derived exit (frames labelled Scanning Stopped) a real cavity or an end-of-track artefact?  
Bracket: depth ≥ 300 µm episode, first to last monitor row; frames 340–410 (1.750245–2.100003 ms); labels in bracket SS. First Scanning Stopped frame at 1.305 ms.  
Whole-record max 312.00 µm; A (active window) 110.75 µm.

**Note.** At frames 340 and 398 the monitored depth reads 309–312 µm, while the images are blank, nearly empty, or show content only at the border.

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 340 | 1.750245 | Scanning Stopped | 309.42 |
| 398 | 2.043650 | Scanning Stopped | 311.55 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 0.279 / no Keyhole | 0.544 / Keyhole |
| ACTIVE_E1_SHARED | 0.202 / no Keyhole | 0.514 / Keyhole |
| G3_SHARED | 0.560 / Keyhole | 0.667 / Keyhole |

## G3 = H-6ca7f366ce (has_keyhole = 1)

Full ID: `P-366p200299346_VX-0p894349968262_LS-4p89176892953e-05_ST-476p393782659_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p39399650496e-06_H-6ca7f366ce`  
Why selected: alternating Keyhole/Conduction, short K. Are the K→C→K switches (one frame interval each) physical alternation or label flicker?  
Bracket: all K/C switches, first to last; frames 74–88 (0.409944–0.485468 ms); labels in bracket K-F-C-K-C-K-C. Switches: K→C frames 74→76 (0.4099→0.4207 ms); C→K frames 80→81 (0.4423→0.4477 ms); K→C frames 81→82 (0.4477→0.4531 ms); C→K frames 83→84 (0.4585→0.4639 ms); K→C frames 87→88 (0.4801→0.4855 ms).  
Whole-record max 111.26 µm; A (active window) 111.26 µm.

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 74 | 0.409944 | Keyhole | 98.42 |
| 76 | 0.420749 | Conduction | 106.70 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 0.999 / Keyhole | 0.805 / Keyhole |
| ACTIVE_E1_SHARED | 0.995 / Keyhole | 0.335 / no Keyhole |
| G3_SHARED | 0.767 / Keyhole | 0.878 / Keyhole |

## G4 = H-b7e3ed2e12 (has_keyhole = 1)

Full ID: `P-380p041479483_VX-0p952843483906_LS-4p56527036263e-05_ST-376p177191048_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p0628678104e-06_H-b7e3ed2e12`  
Why selected: fast-scan positive of the matched pair. Do the 16 Keyhole frames around its startup peak look different from the negative's frames at the same time?  
Bracket: the positive's Keyhole window, same times in both runs; frames 74–89 (0.394919–0.470862 ms); labels in bracket K.  
Whole-record max 112.30 µm; A (active window) 112.30 µm.

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 81 | 0.430353 | Keyhole | 111.81 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 0.000 / no Keyhole | 0.001 / no Keyhole |
| ACTIVE_E1_SHARED | 0.000 / no Keyhole | 0.000 / no Keyhole |
| G3_SHARED | 0.381 / no Keyhole | 0.208 / no Keyhole |

## G5 = H-b302fc6cbd (has_keyhole = 0)

Full ID: `P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd`  
Why selected: fast-scan negative of the matched pair. Is the startup peak (115.6 µm at 0.427 ms) a short Keyhole that was labelled Conduction/Forming?  
Bracket: the positive's Keyhole window, same times in both runs; frames 76–90 (0.396920–0.467260 ms); labels in bracket F-C.  
Whole-record max 115.58 µm; A (active window) 115.58 µm.

**Note.** Frame 82 is 0.18 µs after this run's depth maximum (115.58 µm at 0.426879 ms). It follows a sharp drop in monitored depth (114.30 µm at frame 81 → 89.05 µm at frame 82), so its images show the state after the drop. The near-peak frame 81 is not among the 30 linked images. In the G4/G5 sheet, G4's frame 81 is near its own maximum (111.81 µm).

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 82 | 0.427061 | Conduction | 89.05 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 0.057 / no Keyhole | 0.078 / no Keyhole |
| ACTIVE_E1_SHARED | 0.158 / no Keyhole | 0.000 / no Keyhole |
| G3_SHARED | 0.552 / Keyhole | 0.258 / no Keyhole |

## G6 = H-b2eec677b1 (has_keyhole = 0)

Full ID: `P-426p768553369_VX-0p970152058637_LS-4p12602194162e-05_ST-379p997827854_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p97254070645e-06_H-b2eec677b1`  
Why selected: persistent depth elevation after the first Conduction frame. Is the elevated depth just after the first Conduction frame a cavity that the labels missed?  
Bracket: first Conduction frame to the persistent-depth event; frames 89–97 (0.442558–0.482340 ms); labels in bracket C. A maximum 118.8 µm at 0.455 ms.  
Whole-record max 118.83 µm; A (active window) 118.83 µm.

| Frame | Time (ms) | Recorded label | Depth at frame (µm) |
|---:|---:|---|---:|
| 91 | 0.452508 | Conduction | 118.20 |
| 97 | 0.482340 | Conduction | 111.85 |

| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |
|---|---|---|
| WHOLE_E1_SHARED | 1.000 / Keyhole | 1.000 / Keyhole |
| ACTIVE_E1_SHARED | 0.991 / Keyhole | 0.992 / Keyhole |
| G3_SHARED | 0.753 / Keyhole | 0.461 / no Keyhole |
