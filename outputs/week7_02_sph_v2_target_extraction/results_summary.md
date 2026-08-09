# Week 7 Phase 2 — sph_v2 physical-target extraction

## Outcome

The full run applied the executable Week 6 T0,
width, depth, total-height, kinetic-energy, G3, and R3 definitions to
`ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.  The compatibility layer changes paths
and reconstructs `domain_max_x` from folder `min(XF, XL)`; it does not change the
scientific target definition.

- Target rows retained: **407**.
- Successful extractions: **350**.
- Explicit failures: **57**.
- Exact Week 6 identifiers matched: **241**.
- Exact matches with sufficient pinned monitors for target comparison: **186**.

## Supervisor clarification: no-melt `1e38` sentinel

The raw-token audit found `3.402823e+38` **24,059,576** times,
`-3.402823e+38` **24,060,282** times, and the exact
non-numeric field `s3.402823e+38` **1** time(s). No other numeric or textual
variant near `1e38` was found. The parser recognizes only that exact complete
field as the ordinary positive no-melt sentinel and then excludes its entire
row with the unchanged Week 6 `abs(value) < 1e30` rule. It does not strip
arbitrary letters, replace the sentinel with zero, interpolate it, or use it as
a physical coordinate.

- New-data readiness after correction: **164/165**.
- Extraction-status changes: **1** — P-447p413798058_VX-0p91078629156_LS-5p3177056457e-05_ST-328p907838563_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p29665482201e-06_H-1553ff852f.
- Unexpected changes among previously valid targets: **0**.
- Remaining new-data failures:
- `P-204p165012598_VX-0p624752635414_LS-8p54709329997e-05_ST-334p626206985_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-7p72164906486e-06_H-4ecd858c02`: missing kinetic-energy_melt.dat; missing position-bounds_melt.dat

## T0 and extreme-event evidence

Maximum depth occurs before T0 in **246/350** successful
experiments.  Among **70** successful Keyhole-positive experiments,
**22** have no stored Keyhole-labelled frame inside T0.  This does
not make T0 wrong: T0 represents typical late-active behaviour, while maxima
and brief Keyhole labels answer different physical questions.

## Migration boundary

All exact matches use identifier equality through Week 6
`metadata.json.original_folder_name`; no fuzzy match is used.  Local Week 6
monitor bytes are reused only when their computed Git blob IDs equal the pinned
`sph_v2` tree. Missing monitors are never fabricated or backfilled. The only
textual parser compatibility is the exact confirmed sentinel field above;
unrelated malformed values remain parse failures.

Ioan confirmed that the old-data-local missing files may later be restored by a
separate Hugging Face pull request. They remain visible here as upstream
maintenance flags and are not a blocker for new-data target readiness.

The blue-dot/disconnected-component question cannot be decided from bounding
boxes alone.  Of **4** automatically selected side frames reviewed,
**1** clearly shows separated lower components,
**1** shows a continuous main melt region without an obvious
detached component, and **2** are inconclusive at the nearest
saved-frame cadence.  The automatic table retains all flags and pinned GIF
references; nothing is excluded.

## Validation dashboard

- PASS: **29**
- WARNING: **1**
- FAIL: **0**

## Hard stop

No GP, Ridge, polynomial model, classifier, active learning, kernel comparison,
or level-set estimation was run.  Phase 2 ends here.
