# Supervisor one-page — Phase 1.18B

- **Question:** Does global finite-pool predictive-uncertainty reduction beat local M3 probability margin?
- **P0 / P1 / P2 q20 AULC:** 0.844623 / 0.843244 / 0.840170.
- **Primary P1−P0:** -0.001379, 95% repeat-block CI [-0.003801, +0.000726].
- **Physics-refit P2−P0:** -0.004453, CI [-0.010703, +0.001627].
- **P2−P1:** -0.003074, CI [-0.009072, +0.003056].
- **Holm-adjusted primary p-values:** P1−P0 1; P2−P0 1.
- **B40 q20 Keyhole recall:** P0/P1/P2 = 0.7487/0.7397/0.7447.
- **Decisions:** `GLOBAL_SUR_NO_GAIN`; `PHYSICS_REFIT_SUR_CHANGES_PATH_ONLY`; `LABEL_SAVING_NOT_SUPPORTED`.
- **Numerics:** 0 failed hypothetical solves; 0 disclosed deterministic retries.
- **Safe interpretation:** the benchmark isolates the acquisition path under the same M3 evaluator. q30, individual budgets, and path diversity cannot override the q20 primary result.
- **Stopping rule:** this closes the planned Week 9 acquisition search unless validation exposes an implementation error.
