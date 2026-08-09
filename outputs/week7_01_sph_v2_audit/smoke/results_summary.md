# Week 7 Phase 1 — sph_v2 dataset and design-space audit

## Scope and provenance

This smoke audit used `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.  All
scientific access was pinned to that immutable revision; the floating `main`
pointer was recorded only as provenance.  No source label was changed, no
experiment was removed, and no predictive model was fitted.

## Reproduced population

- Experiments: **18**.
- Labelled frames: **4,286**.
- Experiments containing Keyhole: **4**.
- Experiments containing Conduction: **18**.
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
an annotator proxy.  The automated anomaly table contains **17**
experiments warranting review; these records remain in the data.

## Observed parameter-domain change

- LS lower-bound expansion relative to Week 6: **0.000 µm**.
- ST upper-bound expansion relative to Week 6: **0.000 K**.
- New-data experiments outside at least one Week 6 marginal range: **1/6**.
- New-data experiments outside the Week 6 four-dimensional convex hull: **3/6**.

These are observed design-space/covariate shifts.  They do not establish that
smaller LS or larger ST causes Keyhole.

## Phase 1 decision

The pinned repository is structurally usable for Phase 2 if the compatibility
table's required monitor checks pass.  Label anomalies and the absent annotator
split must remain visible.  Phase 2 should preserve exact partition and revision
provenance, retain every extraction failure as an explicit row, and make no
label corrections.

## Validation dashboard

- PASS: **20**
- WARNING: **1**
- FAIL: **1**
