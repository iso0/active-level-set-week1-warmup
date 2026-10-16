# Physical outputs and a small temporal model

**Independent support, 2026-10-16; no duplication of Opus's fits.** Repository roots:
main `C:/Users/ozgur/Documents/thesis`; Opus checkout
`C:/Users/ozgur/Documents/thesis/.claude/worktrees/joint-depth-label-dev`.
Evidence paths below are relative to those roots. Current physical protocol/code
were read as work-in-progress files; hashes and access times are in
`SOURCE_SNAPSHOT.json`. No physical learnability-result table was used to choose
the proposal.

## What is established, and what the new question is

Week 6 `outputs/week6_04_new_outputs_feature_effects/results_summary.md` already
studied T0 melt kinetic energy and vertical height with linear/polynomial Ridge
and Matérn GPs. Week 7 `outputs/week7_03_new_data_physical_model_stability/phase3_results_summary.md`
already reported KE predictive transfer on the then-new 165-run population (164
eligible targets, GP R² about .89). Those results concern old-era T0 summaries,
not October NEW transient dynamics, low-budget acquisition, or external validation
of today's models. Height is z_max-z_min; penetration is max(0,-z_min).

Opus's live `physical/PHYSICAL_PROTOCOL.md` and `src/jdl_physical_pilot.py` now own
seven summaries, including velocity/KE spikes, duration, lag, T0 energy, laser
power and temperature. **Reuse his completed predictions; do not re-fit those
seven targets here.** A full-fold-pool regression diagnostic is useful, but is
neither an acquisition result nor a mathematical upper bound on every smaller,
selected training design.

The additional question is whether **the amount and time distribution of physical
activity** can be learned and sampled efficiently, across the whole declared
feature population. This remains useful even with no short-K improvement.

| Question | Small, meaningful target | Controls and endpoint | Next decision |
|---|---|---|---|
| Can x predict physical activity beyond the old T0 median? | One primary scalar: duration-weighted mean melt KE over the declared active, melt-present support, in nJ; report valid duration alongside it | Reuse existing T0 KE model as a contextual control; for the new target use paid training mean, Ridge and one fixed-choice Matérn-3/2 GP; simulation-level MAE/RMSE, 90% coverage, support and fit time | One prospective target only; no summary sweep. If Opus already computed an equivalent duration-weighted target, reuse it |
| Can x predict q(x,t), not only its steady level? | **Maximum melt temperature curve** in K on physical time/exit-normalized time; energy curve is a later separate channel, not an automatic second sweep | Mean curve; scalar amplitude × paid mean shape; six-basis input × time GP; time-weighted curve error, native peak error/timing, interval coverage and duration error | Run the small temporal comparison if channel quality and cost permit, regardless of scalar-score or corner-AUC success |
| Does channel uncertainty change useful queries? | Posterior uncertainty of two declared scalar channels, normalized by paid/fixed scale | Same two models and oracle; primary variance versus fixed .5/.5 variance mixture; separate per-channel RMSE curves and joint target | The prepared synthetic extension is only a feasibility test; a real target/cost requires its own freeze |

The first row is a **future proposal**, not an instruction to change the already
frozen S1 target. Newly defined summaries are not silently substituted into
Opus's existing result tables.

## Real file meaning, alignment and quality

Verified definitions available locally:
`outputs/week6_01_melt_pool_data_audit/monitor_data_dictionary.csv`,
`outputs/week6_04_new_outputs_feature_effects/kinetic_energy_monitor_audit.csv`,
`src/week19_sources.py`, `src/week19_series.py`, and
`src/jdl_physical_data.py`. The current source pin is
`ioandanielc/sph_v2@2e1eec9c98fd57609d2815f174586336ab59da07`.
Opus's download manifest reported **952/952 verified files** at
2026-10-16 21:18:45 UTC. I read the manifest, the definitions and two initial rows
of the five channels in one cached run; I did not bulk-download or re-extract data.

| Channel | Interpretation and unit | Qualification |
|---|---|---|
| `time.dat`, `iter.dat` | physical time in seconds; iteration alignment | Align each channel with native time/iteration; never truncate unequal arrays to fit |
| `kinetic-energy_melt.dat` | instantaneous aggregate melt-phase kinetic energy, J; nJ for reporting | Not cumulative, not temperature or deposited heat; exact solver particle-mass reduction remains uncertified in the local audit |
| `maximum-temperature_melt.dat` | maximum temperature among melt particles, K | A spatial extreme, not a bulk temperature; absent melt is not a physical 0 K observation |
| `maximum-velocity_melt.dat` | maximum melt-particle speed, m/s | An extreme, not bulk velocity or vapor flow; retain known abnormal-velocity flags |
| `transferred-laser-power_melt.dat` | power transferred to the melt channel, W | Not whole-domain absorbed power or overall efficiency; integrate W×s for energy only after confirming reduction semantics |

The historical dictionary assigns medium unit confidence to these headerless
scalar channels. The current manifest proves byte identity, **not solver semantic
certification**. Preserve that distinction; units/material thresholds need source
metadata or Ioan's confirmation before stronger physical claims. `gas`/argon
channels are not metal-vapor measurements and are not used here.

Keep startup and the existing 90%-of-derived-exit rule. For planned prediction,
T_plan=min(TE, .9 t_exit) is known from settings. Actual record end is an
**observation support mask**, never a feature or a reason to stretch a short curve
to the full horizon. Melt presence requires valid phase/bounds evidence; do not
treat a sentinel as depth, energy or temperature. Duration weighting uses actual
delta-t, with intervals clipped to the cutoff and with missing support recorded.
The supplied helper explicitly excludes intervals with invalid endpoints or
unapproved gaps; no interpolation across unobserved gaps. Native peaks are
retained separately from reconstructed peaks.

**Preserved quality issue and a concrete audit gap:** the owner reports 931
nonfinite KE values and abnormal speeds in the early-ended H-e7dbd8e5ce run.
The new `physical/QC_SUMMARY.json` reports 1,358 nonfinite KE values across three
aligned runs, and one unavailable run. In `jdl_physical_pilot.extract`, the
row-count-mismatch branch returns **before** `summarize` counts nonfinite values.
Thus 1,358 is not a demonstrated all-136-file count and does not replace the 931
finding. Reconcile raw per-channel QA for the unavailable run separately, retaining
its canonical label and its paid cost. I did not silently add the two counts,
delete this run, or alter Opus's extraction. Its >100 m/s speed filter is a declared
screen, not evidence of a universal physical maximum.

## Concrete temporal construction

Let tau=t/t_exit(x), on [0,.9]. This is four inputs plus time, not five independent
simulation controls. Use fixed hat functions b_1...b_6 with knots
(0,.18,.36,.54,.72,.9). `monitor_support.time_basis` and `input_time_kernel`
implement

\[
q(x,t)=m(\tau)+\sum_{k=1}^{6}b_k(\tau)a_k(x),\qquad
K((x,t),(x',t'))=k_{3/2}(x,x')\,b(\tau)^T b(\tau').
\]

This kernel is positive semidefinite (product of an input kernel and a finite
feature-map time kernel). A regularized Gaussian prior on coefficients prevents
the unregularized partial-curve projection blow-up documented in
`src/jdl_temporal_functional.py`. Do not duplicate that PPCA repair; the fixed basis
is a cheap, interpretable alternative for the **new temperature channel**.
Basis reduction for high-dimensional simulator output is established, e.g.
[Higdon et al., 2008](https://www2.stat.duke.edu/courses/Spring14/sta961.01/ref/HigdGattWillRigh2008.pdf).
It does not guarantee a suitable basis for narrow peaks.

Concrete small implementation request: reuse DEV repeats 3–4/five-fold identities
and feature-only **B40** paid sets; all rows of each simulation stay in its fold.
Compress temperature to 12 fixed time bins by physical-duration-weighted means,
retaining masks, duration, native peak and native peak time. Fit the kernel above
directly to at most 40×12 observed bin means (one GP solve/model request, not
hundreds of thousands of native rows). Fit mean-curve and scalar-amplitude/shape
controls on the same paid simulations. Predeclare temperature transformation,
effective residual noise and prior/optimizer with Opus before execution; no
held-out tuning. At most **10 temporal GP requests**, no restarts, one thread,
20-minute separate coordinator envelope, checkpoint per fold. This is a proposed
future allocation, **not work launched or reserved by this package**.

For a reconstruction-quality gate, use paid traces only: record weighted
reconstruction RMSE and native-peak attenuation. If the six-basis/12-bin model
loses more than 10% of the peak above that trace's time mean in more than 20% of
paid traces, mark it **inadequate for peak claims**. Report curve performance but
do not conceal this failure by fitting a new rank/resolution on test curves.
This is a model-capacity diagnosis, not a reason to abandon the temporal question.

Temporal evaluation: first integrate error over each simulation's valid physical
time, then average simulations equally. Report curve MAE/RMSE in K, native-peak
absolute error, peak-time absolute error in microseconds, pointwise 90% coverage,
missing planned-duration fraction, and fitting/extraction/prediction wall time.
For duration above a threshold, the threshold must be a solver-certified material
temperature chosen before evaluation; until available, that physical duration
endpoint is **undefined**, not silently chosen for Keyhole separation. Any
statistical excursion threshold is a separate declared descriptive target.
Intervals for a maximum/duration require whole-curve uncertainty, not pointwise
bands relabeled as peak/duration intervals. For truncated traces these metrics
concern observed support; a complete planned curve cannot be verified.

## Physical motivation and short-K as a secondary question

Melt flow and temperature evolution are physically relevant because recoil and
thermocapillary flow couple energy deposition, motion and melt geometry
([Khairallah et al., 2016](https://doi.org/10.1016/j.actamat.2016.02.014),
[accessible author preprint, 2015](https://arxiv.org/abs/1512.02593)). These mechanisms
justify studying monitor dynamics; they do not identify a monitor spike as
Keyhole or prove a causal interpretation in this solver.
Experiments separately distinguish metal vapor and the ambient gas it entrains
([Ly et al., 22 June 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5481335/)).

Keep the prior observed velocity peak/median AUC .811 versus active-max-depth
.773 as a **post-hoc, uncertain clue**, not a demonstrated gain. Opus already owns
the spike/duration/lag diagnostics; no new descriptor sweep is requested. Observed
monitor-label association is distinct from x-only out-of-sample prediction.
Any later Keyhole transfer must use paid-only training and cross-prediction/joint
uncertainty, preserve all short events and exclusions, and report BA, both recalls,
short-K hit/total, q20, AUC/calibration and time. Losing short-K while BA rises is
a real tradeoff to report; it does not invalidate an independent temperature or
energy learning result.

**Required prospective interpretation correction:** the live physical protocol's
last section currently makes temporal work conditional on a LEARNABLE scalar
summary and predicted corner information. The 16 October user direction explicitly
removes that condition. Opus should preserve the existing scalar experiment and
record a prospective temporal amendment based on quality/cost. No file was edited
in his checkout. NEW remains DEV; C3 is unchanged, C4 and Stage A are unexecuted.
