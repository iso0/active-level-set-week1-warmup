# Week 6 Phase 3.5 results summary

## Main conclusion

T0 remains the geometry target.  The strongest provisional regime-oriented
candidate is R3: maximum 50 µm rolling-median penetration depth divided by
transverse width in the adaptive active interior.  G3 persistent depth should
remain a companion sensitivity, and the later problem should retain two
outputs until independently generated labels are available.

This is a provisional physical recommendation—not an independent validation
against final ground truth.

## Raw chain of evidence

`position-bounds_melt.dat` and exact monitor time/iteration streams
→ physical laser X and normalized scan position
→ instantaneous depth, width, and guarded depth/width
→ global, q95, and physical-distance persistent summaries
→ exact alignment to provisional frame labels
→ clustered and simulation-level comparison
→ robustness across windows, domains, censoring, VX, and unstable simulations
→ target recommendation for later design.

## Labels and alignment

- Labelled frames: 65,472.
- Conduction: 43,881.
- Forming Phase: 10,326.
- Keyhole: 521.
- Initial Emptiness: 3,275.
- Screenshot Bug: 7,469.
- Keyhole-containing simulations: 9/241.
- Both Conduction and Keyhole: 8.
- Exact label-to-monitor matches: 65,472; ambiguous: 0.

Labels are sparse relative to 25,884,257 monitor rows and strongly imbalanced.
All 241 provenance files record a depth-based `median-zmin` automatic seed;
177 are marked human-verified and 64 automatic.  Label agreement is therefore
descriptive and potentially circular.

## Coverage and event positions

- Reaches s=0.85: 136/241.
- Reaches s=0.90: 130/241.
- Reaches s=0.95: 121/241.
- Reaches s=1.00 with active melt: 113/241.
- Median global maximum-depth position: 0.511.
- Median persistent maximum-depth position: 0.534.
- Median global maximum-ratio position: 0.506.
- Median persistent maximum-ratio position: 0.505.

The event distributions are broad.  A median near the middle of the track does
not imply that every simulation is deepest at mid-track.  The late T0 window
misses many earlier/interior maxima; that is expected because T0 measures
typical late geometry rather than the strongest episode.

## Candidate-versus-label results

Simulation-level any-Keyhole prevalence is
0.0375 (9/241).

| Candidate | ROC AUC (95% bootstrap CI) | PR AUC (95% bootstrap CI) |
|---|---:|---:|
| G0 T0 depth | 0.967 [0.922, 0.996] | 0.678 [0.365, 0.917] |
| G1 max depth | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| G2 q95 depth | 0.975 [0.944, 1.000] | 0.763 [0.467, 1.000] |
| G3 persistent depth | 0.971 [0.935, 1.000] | 0.762 [0.464, 1.000] |
| R2 q95 ratio | 0.978 [0.943, 1.000] | 0.797 [0.511, 1.000] |
| R3 persistent ratio | 0.969 [0.925, 1.000] | 0.771 [0.478, 1.000] |

G1 and R1 can rank the current labels perfectly while remaining scientifically
inferior regime targets: a one-frame peak is not persistence, and the labels
were seeded from depth.  The perfect ranking is evidence of circularity, not a
reason to choose the global maximum.

At frame level, 50 µm rolling aspect ratio has ROC AUC
0.985
[0.968,
0.995] and PR AUC
0.709
[0.330,
0.856], against a frame prevalence
baseline of 0.0119.  CIs
resample whole simulations.

All reported thresholded metrics use exact nested leave-one-simulation-out:
thresholds are selected on outer-training labels only and applied once to the
held-out simulation.

## Robustness and recommendation

Persistence was evaluated at 20, 50, and 100 µm and at 1%, 2.5%, and 5% of
track length.  Candidate values were compared under a data-supported common
interior and a per-simulation adaptive active interior, with 8/12/20 µm width
guards, with and without the eleven Phase 1 unstable simulations, by coverage,
by VX tertile, and by track region.

The evidence supports:

- **Geometry:** retain T0.
- **Regime propensity:** provisionally use R3 at 50 µm.
- **Companion:** retain G3 to test whether width adds information.
- **Later design:** keep geometry and regime as two outputs until Ioan confirms
  the physical target and updated independent labels are available.

The actual-frame sequence is drawn only from pinned Hugging Face files.  The
six case studies are selected by explicit population rules rather than manual
choice.

## Automated closeout

- Validation: 59/59 PASS.
- Requirement checklist: 150/150 PASS.
- Full wall time: 32.728 seconds.
- Presentation-ready figures: 18.
- No commit or push occurred; the original dirty worktree remained hash-identical.
