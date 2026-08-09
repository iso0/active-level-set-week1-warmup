# Week 7 Phase 2 — sph_v2 physical-target extraction

## Outcome

The smoke run applied the executable Week 6 T0,
width, depth, total-height, kinetic-energy, G3, and R3 definitions to
`ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.  The compatibility layer changes paths
and reconstructs `domain_max_x` from folder `min(XF, XL)`; it does not change the
scientific target definition.

- Target rows retained: **18**.
- Successful extractions: **17**.
- Explicit failures: **1**.
- Exact Week 6 identifiers matched: **12**.
- Exact matches with sufficient pinned monitors for target comparison: **11**.

## Supervisor clarification: no-melt `1e38` sentinel

The raw-token audit found `3.402823e+38` **1,209,000** times,
`-3.402823e+38` **1,209,000** times, and the exact
non-numeric field `s3.402823e+38` **0** time(s). No other numeric or textual
variant near `1e38` was found. The parser recognizes only that exact complete
field as the ordinary positive no-melt sentinel and then excludes its entire
row with the unchanged Week 6 `abs(value) < 1e30` rule. It does not strip
arbitrary letters, replace the sentinel with zero, interpolate it, or use it as
a physical coordinate.

- New-data readiness after correction: **6/6**.
- Extraction-status changes: **0** — none.
- Unexpected changes among previously valid targets: **0**.
- Remaining new-data failures:
- None.

## T0 and extreme-event evidence

Maximum depth occurs before T0 in **12/17** successful
experiments.  Among **4** successful Keyhole-positive experiments,
**2** have no stored Keyhole-labelled frame inside T0.  This does
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
boxes alone.  Of **0** automatically selected side frames reviewed,
**0** clearly shows separated lower components,
**0** shows a continuous main melt region without an obvious
detached component, and **0** are inconclusive at the nearest
saved-frame cadence.  The automatic table retains all flags and pinned GIF
references; nothing is excluded.

## Validation dashboard

- PASS: **28**
- WARNING: **2**
- FAIL: **0**

## Hard stop

No GP, Ridge, polynomial model, classifier, active learning, kernel comparison,
or level-set estimation was run.  Phase 2 ends here.
