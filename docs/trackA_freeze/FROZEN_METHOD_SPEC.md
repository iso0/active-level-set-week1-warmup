# Frozen Track A method specification

## 1. Data contract

- Inputs are `[P, VX, LS, ST]`; `ST` means substrate temperature.
- Target is the manual binary ground truth `has_keyhole`.
- OLD-405 is the completed 405-row internal population. It is development/internal-replication evidence only.
- Selectors may see training-pool input features and labels only after the corresponding row has been queried. Held-out labels, unqueried labels, q20/q30 membership, B1 distances, and simulation-only auxiliary targets are unavailable to selection.

## 2. M3 predictive model

At every integer budget, M3 is refitted on the revealed prefix.

1. Compute `log h = log P - 0.5 log VX - 1.5 log LS`.
2. Fit `StandardScaler` to revealed `log h` values only.
3. Fit a near-unregularized logistic trend to revealed labels: `LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000)` with the frozen deterministic seed namespace.
4. Freeze that fitted latent logit mean for the discrepancy stage.
5. Fit a separate `StandardScaler` on `[P,VX,LS,ST]` using the complete outer training pool's feature values only.
6. Fit the fixed-mean binary Laplace GPC discrepancy to the revealed rows. Its kernel is `ConstantKernel(0.09, [0.05^2,1.0^2]) * Matern(length_scale=[1,1,1,1], length_scale_bounds=[0.01,100], nu=1.5)`.
7. Optimize the kernel with L-BFGS-B, zero restarts, `maxiter=150`, `ftol=1e-12`, and `gtol=1e-7`. The documented deterministic initial-kernel fallback applies only if optimization raises or returns non-finite values.
8. Predict with the sum of the frozen physics latent mean and the learned four-dimensional GP discrepancy. `log h` is not a fifth discrepancy input.

Authoritative implementation: `src/week9_phase1_13_fixed_physics_ard_discrepancy.py`, supported by `src/week9_phase1_11_fixed_mean_discrepancy_gp.py`.

## 3. Live control

`M3_margin_incumbent` means exactly:

- the frozen feature-only B16 maximin design from `week8_5_frozen_sample_efficiency_confirmation.initial_design`;
- thereafter, select the unqueried training-pool row with M3 probability closest to 0.5;
- use the frozen deterministic tie behavior;
- refit M3 after every revealed label.

Do not rename historical Binary-A0 as this control.

## 4. Frozen external challenger

`early8__coverage_then_margin_B40` means exactly:

1. Take the first eight points of the same frozen feature-space maximin order.
2. If those eight contain only one observed class, extend along that same order, one point at a time, until both classes have been revealed. No hidden label is used to reorder the sequence.
3. Before total budget B40, estimate the transition band in `log h` from revealed labels only: the queried-label bracket between the lowest revealed Keyhole and highest revealed Conduction while separable, with the frozen fallback semantics in the implementation.
4. Pad the band by `max(0.05, 0.25 * band_width)`.
5. Within the nonempty band, rank candidates by `rank(1 - 2*abs(p_M3-0.5)) + rank(d4)`, with both weights 1. `d4` is nearest-queried Euclidean distance in standardized `[P,VX,LS,ST]`; the scaler is fitted on outer-training-pool features only.
6. If the eligible band is empty, fall back to plain M3 probability margin.
7. From B40 onward, use plain M3 probability margin.
8. Final ties use the frozen smaller population-row-index rule.

Parameters are fixed: `k_seed=8`, `pad_fraction=0.25`, `pad_floor=0.05`, `uncertainty_weight=1.0`, `switch_budget=40`.

## 5. Attribution control

`coverage_then_margin_B40` uses the challenger acquisition rule but starts from the incumbent's exact B16 maximin design. It isolates acquisition from the changed early-start design. It is mandatory in the external comparison but is not a second challenger.

## 6. Evaluation definitions

- Primary internal/external endpoint: Fold-B1-q20 **accuracy** normalized trapezoidal AULC over every integer budget B16-B80, divided by 64.
- Early endpoint: the same metric over B16-B40, divided by 24.
- q20 is the closest `ceil(0.20 * n_test)` held-out rows to an opposite-class neighbor in standardized four-dimensional input space. This label-dependent flag is evaluation-only.
- q30, q20 balanced accuracy, q20 Keyhole recall, and full-test accuracy are separate secondary/guardrail quantities.
- Repeat block is the inferential unit; five folds are averaged inside a repeat before paired inference.

## 7. Frozen prohibitions

No new acquisition function, OLD-405 method search, outcome-based parameter change, q30 promotion, auxiliary-output acquisition, new-batch tuning, or claim of external validation is permitted under this freeze.
