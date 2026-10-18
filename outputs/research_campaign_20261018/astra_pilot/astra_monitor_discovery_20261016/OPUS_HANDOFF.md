# Opus handoff — bounded surprise discovery, finalized 17 October 2026

**Ready code, not a request to resume BA_RISK.** This file is a handoff artifact;
no message was sent on the owner's behalf. V1/V2, ASTRA_AL, labels, exclusions,
inputs, q20 and C3 remain unchanged. The unfinished real-data P2 is not a final
negative result. No C4, Stage A or new simulator run is authorized here.

## One immediate action

Allocate **one thread in the existing single coordination record**, then run the
bounded synthetic pilot below. The decisive comparison is `surprise` versus
`straddle_global`: same GP, fixed level decision, startup, outputs, global schedule
and budget; only the bounded local reaction changes. Straddle, regression-posterior
margin and random are additional controls. No G3/SPH superiority follows from a
toy result. All 34 trajectories fit inside the frozen cap; no rescue search.

Package directory:
`C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_monitor_discovery_20261016/`

This is the final handoff source. A read-only snapshot of earlier files exists at
the same relative output path in your checkout, created on October 16 at 21:46 UTC.
It lacks the final manifest and later contract repairs. It was not overwritten;
run the absolute path above, not that earlier snapshot.

Existing coordination record inspected read-only:
`C:/Users/ozgur/Documents/thesis/.claude/worktrees/joint-depth-label-dev/outputs/joint_depth_label_development/pool/POOL_PLAN.json`

At the access snapshot it contained no allocation for this new package. An idle
host or the earlier `POOL_END` is **not** a reservation. No numeric run was launched
by Astra. Opus remains the sole numerical coordinator.

## Run command and numerical envelope

```powershell
$pkg = 'C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_monitor_discovery_20261016'
$coord = 'C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev\outputs\joint_depth_label_development\pool\POOL_PLAN.json'
& 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe' -B "$pkg\run_pilot.py" --dry-run
# ONLY after Opus grants the reservation in $coord:
& 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe' -B "$pkg\run_pilot.py" --run --coordination-record $coord
```

Required coordinator-owned entry in the same JSON's `external_reservations` list:
`job: astra_monitor_discovery_20261016`, `status: active`, `granted_by: Opus`,
`threads: 1`, actual `host`, `combined_active_threads` between 1 and 4,
`code_digest` exactly from `FROZEN_MANIFEST.json`, and a timezone-aware future
`expires_utc`. This package does **not** create or activate that entry. The entry
is an allocation record, not a new background queue. If the existing scheduler
does not read this field, Opus must reserve its capacity explicitly (at most three
other numerical threads) while running this one foreground process. The runner
enforces its own BLAS cap and rechecks the declared reservation before each fit;
it cannot certify the configuration of unrelated processes.

The budget is **1,200 cumulative wall seconds**, one numerical thread, 578
controlled fit requests/646 controlled GP solves and four independent small
reference fits, for **650 total solves**. No optimizer/restarts/fantasies.
Caps are checked before each small bounded step. Do not automatically renew an
expired allocation or add time/repeats after looking at results.

`--dry-run` checks code hashes and imports no numerical libraries. Standard-library
checks use `python -B test_fitfree.py`; their JSON is already included. Under the
reservation, the runner first checks four small GPs against independent
scalar/dense-inverse conditioning, tolerance 1e-9. This reference is **not yet run**
and a numerical pass will not establish scientific correctness or GP adequacy.

## Outputs, resume and interpretation

Everything is written under this package's `pilot/`: environment/reservation
snapshot, per-seed/per-arm JSON, paid paths and pre-observation hashes, trusted
local checkpoints, attempt ledger, resource counters, independent reference
checks and `CONTROLLED_RESULTS.json`. Invalid observations, trigger failures,
calibration warnings, losses and stopped units remain visible.

Resume with the identical command and an active reservation only after a safe
checkpoint stop. A failed or unresolved interrupted fit blocks automatic retry;
review it and record any prospective amendment separately. A time-budget stop
does not reset time on resume. Do not delete a live lock, re-seed, cherry-pick a
successful island example or infer failure from an unfinished comparison.

Report all paired outcomes and seed ranges. With only two seeds per world, this
is feasibility work. Count discovery during startup; report undiscovered islands
as censored. Boundary learning is separate from finding three positives. Equal
performance means the exact joint target in `FROZEN_MANIFEST.json` confirmed at
two consecutive budgets; path changes and a higher final BA are not sample savings.
For null/bad-monitor worlds, inspect spurious episode cost and quality handling,
not an invented missing-island score. The auxiliary variance comparison reports
**both** scalar errors; a gain in the second channel can coexist with worse
boundary learning.

## Integration and physical handoff, without duplicating your fits

Use `discovery.SurpriseLocalDiscovery`, `Predictions`, `Observation` directly as
shown in `DATA_CONTRACT.md`. Fit the primary scalar model outside the selector and
save its posterior **before** reading the new run. Code consumes no future labels,
short-K/q20 membership, post-hoc fast-scan cut or true unpaid monitor.

`MONITOR_MODEL_SUPPORT.md` specifies one new duration-weighted energy question and
a small maximum-temperature time model with a concrete PSD input × time kernel;
`monitor_support.py` implements duration/support accounting and that kernel.
Reuse your existing seven scalar fits and depth PPCA/SVGP work. The proposed
temperature comparison is at most ten B40 simulation-wise checkpoints, one small
GP per checkpoint plus simple controls, under a **separate prospective allocation**.
Your later PHYS_AL, PHYS_DISCOVERY, TEMPORAL_VEL and TEMPORAL_STRUCT protocols were
also inspected to avoid duplication: velocity/KE/depth curve fits and scalar
acquisition comparisons already exist. The proposed temperature curve and
duration-weighted full-active KE mean are different questions. They are not queued
or counted as already executed here.

Three source/interpretation issues are recorded, without requesting a replay:

1. The older `physical/PHYSICAL_PROTOCOL.md` gates temporal work on scalar
   learnability and predicted corner information. Your later temporal studies
   have already run. For future temperature work, preserve their protocols and
   use the owner's independent quality/cost criterion, without a scalar/corner gate.
2. In `src/jdl_physical_pilot.py`, the row-mismatch branch precedes per-channel
   nonfinite counting. The 1,358 aligned-run total already includes the 931 values
   in H-ce04be44b1; the early-ended H-e7dbd8e5ce has blank QA counts. These are
   distinct findings. Preserve both runs and labels, reconcile raw QA counts even
   when temporal summaries are unavailable, and
   distinguish row-quantiles from physical-duration weighting. The new helper's
   interpolation convention must not silently change your frozen hold-rule results.
3. `jdl_phys_discovery.py:92-93` adds the learned WhiteKernel variance to an SD
   whose square already includes that noise. The standardized surprise is therefore
   smaller than the predictive-residual formula specifies. Historical ranking
   impact is unknown. `CONTEXT_AND_VARIANCE_AUDIT.md` gives source evidence, a cheap
   discriminating check and a stopping condition; `variance_contract.py` supplies
   the explicit adapter. The current log contains z but not all moments, so a
   complete trigger reconstruction cannot be asserted from that log alone.

Our selector was chosen before the newer protocol reads; the commit body
incidentally exposed aggregate outcomes afterwards. No thresholds, generators or
acquisition choices were revised using them. A runner variable-name repair and
null-reservation handling were checked with a dummy model, without GP fitting.
The final manifest preserves this chronology rather than describing the review as
fully blind. See `METHOD_CHOICE_RECORD.json` and `SOURCE_SNAPSHOT.json`.

The strongest competing explanation for an apparent selector gain is improved
global coverage. The same-schedule episode ablation is the discriminating test.
If valid local hits rise but boundary error does not improve, retain that loss and
investigate model restriction before claiming the acquisition solved the boundary.
Short-K is retained as a separate eventual diagnostic; it is not this pilot's
gate or a privileged selector input.
