# Week 7 Phase 1 — sph_v2 dataset and design-space audit

## Scope and provenance

This full audit used `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.  All
scientific access was pinned to that immutable revision; the floating `main`
pointer was recorded only as provenance.  No source label was changed, no
experiment was removed, and no predictive model was fitted.

## Reproduced population

- Experiments: **407**.
- Labelled frames: **110,804**.
- Experiments containing Keyhole: **73**.
- Experiments containing Conduction: **373**.
- Ioan reference checks: **20/20 PASS**.

At experiment level labels are not mutually exclusive: one simulation can pass
through both Conduction and Keyhole at different labelled timesteps.  Keyhole
duration is therefore reported in labelled frames and segments.  No conversion
to milliseconds is made because a repository-wide physical mapping from saved
frame index to time has not yet been validated.

## Label quality and annotator boundary

The working-student subset is **not reliably identifiable** from the pinned
repository.  There is no annotator/provenance field or file and the identities
behind `label_1` and `label_2` are undocumented.  A partition is not treated as
an annotator proxy.  The automated anomaly table contains **387**
experiments warranting review; these records remain in the data.

## Observed parameter-domain change

- LS lower-bound expansion relative to Week 6: **4.971 µm**.
- ST upper-bound expansion relative to Week 6: **0.360 K**.
- New-data experiments outside at least one Week 6 marginal range: **95/165**.
- New-data experiments outside the Week 6 four-dimensional convex hull: **118/165**.

These are observed design-space/covariate shifts.  They do not establish that
smaller LS or larger ST causes Keyhole.

## Phase 1 decision

The pinned repository is usable for the complete label/parameter audit and is
**partially usable** for Phase 2 physical extraction.  There are
**114 missing required-monitor entries across
57 experiments**.  Label anomalies, the absent annotator
split, and these structural gaps must remain visible.  Phase 2 must preserve
exact partition and revision provenance, retain every extraction failure as an
explicit row, and make no label corrections.

## Validation dashboard

- PASS: **21**
- WARNING: **0**
- FAIL: **1**
