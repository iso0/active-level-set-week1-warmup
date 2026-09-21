# Track B problem definition

## Question

Can a quantity that is genuinely available during a physical experiment carry useful information about a hidden, simulation-labelled state such as `has_keyhole`?

The intended direction is:

`experimentally available observation up to time t` → `calibrated probability of a hidden state`

This is an observability and inference problem. It is not an active-learning acquisition study and does not change the frozen Track A method.

## Present evidence boundary

- The repository contains simulations and retrospective simulation-derived features. Existence in a simulator does **not** establish experimental observability.
- `has_keyhole` is the manual ground-truth label used in this project. It is the hidden target, not an assumed online measurement.
- The strongest proof-of-concept currently available is the width work: a simple maximum positive width-change feature added modest predictive ranking information beyond `[P, VX, LS, ST]` in the old 405-simulation study. It did not establish sensor feasibility and did not succeed as an acquisition variable.
- No genuinely new Ioan batch was opened, summarized, labelled, or used while preparing Track B.
- No signal is presently certified by this repository as **experimentally observable online**. Such certification requires a documented measurement modality, temporal availability, calibration, resolution, failure mode, and deployment context.

## Four evidence classes

1. **experimentally observable online** — demonstrated in the intended experimental setup with adequate time resolution and a documented measurement path.
2. **potentially observable / literature-dependent** — physically plausible or reported elsewhere, but not demonstrated for this setup and definition.
3. **simulation-only / hidden** — requires internal simulator state, a post-hoc label, destructive observation, or unavailable ground truth.
4. **uncertain** — definition, modality, timing, or provenance is currently insufficient for either conclusion.

The initial classifications are in [`SIGNAL_INVENTORY.csv`](SIGNAL_INVENTORY.csv). They are evidence statuses, not statements of physical impossibility.

## Separation from Track A

Track A asks which already-frozen sampling policy should choose expensive simulation evaluations. Track B asks whether observable experimental signals can support inference about a hidden state. Track B must not be used to reopen acquisition-function development on the old 405 simulations.

## Success language

A candidate can first support only an **internal association** claim. An experimental-observability claim additionally needs measurement evidence. A deployment claim additionally needs prospective, experiment-domain validation, calibration, temporal-causality checks, and predefined safety limits. Internal cross-validation alone cannot provide those claims.
