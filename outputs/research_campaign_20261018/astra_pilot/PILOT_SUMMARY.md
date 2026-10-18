# Astra's frozen pilot `astra_monitor_discovery_20261016` — run once on 2026-10-18

Status **COMPLETE**, code digest `a41a90f62843cace…` (= FROZEN_MANIFEST). Resources: {"controlled_fit_requests": 578, "component_solves": 650, "reference_fits": 4, "used_wall_s": 10.598393400025088, "unfinished": null}. Independent dense references: PASS.

Scope (manifest): synthetic feasibility only; no SPH, G3, short-K, C3/C4, Stage A or physical-simulator claim. Two seeds per world: descriptive feasibility, not general superiority or SPH evidence.

Discovery target (manifest): global error <=0.10 AND island recall >=0.75 AND island-boundary error <=0.20; confirmed at two consecutive budgets (counted at the second); `—` = not reached by B24 (right-censored).

| world | seed | arm | BA@24 | error@24 | island recall@24 | island-boundary error@24 | first discovery (query) | paid island runs | invalid paid | triggers | target reached at B | query reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| island | 61016 | surprise | 0.751 | 0.131 | 0.00 | 0.50 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island | 61016 | straddle_global | 0.751 | 0.131 | 0.00 | 0.50 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island | 61016 | straddle | 0.779 | 0.135 | 0.00 | 0.50 | — | 0 | 0 | 0 | — | global_straddle 16 |
| island | 61016 | margin | 0.675 | 0.159 | 0.00 | 0.50 | — | 0 | 0 | 0 | — | global_margin 16 |
| island | 61016 | random | 0.644 | 0.183 | 0.25 | 0.47 | 16 | 1 | 0 | 0 | — | global_random 16 |
| island | 61016 | primary_variance | 0.736 | 0.140 | 0.01 | 0.50 | 18 | 1 | 0 | 0 | — | global_primary_variance 16 |
| island | 61016 | multi_variance | 0.772 | 0.157 | 0.00 | 0.53 | 18 | 1 | 0 | 0 | — | global_multi_variance 16 |
| island | 61017 | surprise | 0.773 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island | 61017 | straddle_global | 0.773 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island | 61017 | straddle | 0.798 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_straddle 16 |
| island | 61017 | margin | 0.678 | 0.161 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_margin 16 |
| island | 61017 | random | 0.735 | 0.177 | 0.03 | 0.45 | 14 | 1 | 0 | 0 | — | global_random 16 |
| island | 61017 | primary_variance | 0.695 | 0.164 | 0.00 | 0.41 | 16 | 1 | 0 | 0 | — | global_primary_variance 16 |
| island | 61017 | multi_variance | 0.725 | 0.132 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_multi_variance 16 |
| island_bad_monitor | 61016 | surprise | 0.718 | 0.169 | 0.00 | 0.50 | — | 0 | 2 | 0 | — | global_random 4, global_straddle 12 |
| island_bad_monitor | 61016 | straddle_global | 0.718 | 0.169 | 0.00 | 0.50 | — | 0 | 2 | 0 | — | global_random 4, global_straddle 12 |
| island_bad_monitor | 61016 | straddle | 0.770 | 0.139 | 0.00 | 0.50 | — | 0 | 3 | 0 | — | global_straddle 16 |
| island_bad_monitor | 61016 | margin | 0.645 | 0.164 | 0.00 | 0.50 | — | 0 | 1 | 0 | — | global_margin 16 |
| island_bad_monitor | 61016 | random | 0.603 | 0.195 | 0.24 | 0.47 | 16 | 1 | 1 | 0 | — | global_random 16 |
| island_bad_monitor | 61017 | surprise | 0.773 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island_bad_monitor | 61017 | straddle_global | 0.773 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| island_bad_monitor | 61017 | straddle | 0.798 | 0.122 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_straddle 16 |
| island_bad_monitor | 61017 | margin | 0.678 | 0.161 | 0.00 | 0.38 | — | 0 | 0 | 0 | — | global_margin 16 |
| island_bad_monitor | 61017 | random | 0.735 | 0.177 | 0.03 | 0.45 | 14 | 1 | 0 | 0 | — | global_random 16 |
| null_bad_scale | 61016 | surprise | 0.766 | 0.111 | n/a | n/a | — | 0 | 0 | 1 | — | global_random 4, global_straddle 8, local_boundary 2, local_verify 2 |
| null_bad_scale | 61016 | straddle_global | 0.733 | 0.105 | n/a | n/a | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| null_bad_scale | 61016 | straddle | 0.818 | 0.083 | n/a | n/a | — | 0 | 0 | 0 | — | global_straddle 16 |
| null_bad_scale | 61016 | margin | 0.721 | 0.113 | n/a | n/a | — | 0 | 0 | 0 | — | global_margin 16 |
| null_bad_scale | 61016 | random | 0.663 | 0.128 | n/a | n/a | — | 0 | 0 | 0 | — | global_random 16 |
| null_bad_scale | 61017 | surprise | 0.803 | 0.088 | n/a | n/a | — | 0 | 0 | 1 | — | global_random 4, global_straddle 8, local_boundary 3, local_verify 1 |
| null_bad_scale | 61017 | straddle_global | 0.806 | 0.091 | n/a | n/a | — | 0 | 0 | 0 | — | global_random 4, global_straddle 12 |
| null_bad_scale | 61017 | straddle | 0.821 | 0.087 | n/a | n/a | — | 0 | 0 | 0 | — | global_straddle 16 |
| null_bad_scale | 61017 | margin | 0.756 | 0.103 | n/a | n/a | — | 0 | 0 | 0 | — | global_margin 16 |
| null_bad_scale | 61017 | random | 0.808 | 0.084 | n/a | n/a | — | 0 | 0 | 0 | — | global_random 16 |

**Decisive paired comparison (same GP, decision, startup and global schedule): surprise − straddle_global at B24**

| world | seed | ΔBA | Δerror | Δisland recall | Δisland-boundary error |
|---|---|---|---|---|---|
| island | 61016 | +0.000 | +0.000 | +0.00 | +0.00 |
| island | 61017 | +0.000 | +0.000 | +0.00 | +0.00 |
| island_bad_monitor | 61016 | +0.000 | +0.000 | +0.00 | +0.00 |
| island_bad_monitor | 61017 | +0.000 | +0.000 | +0.00 | +0.00 |
| null_bad_scale | 61016 | +0.033 | +0.006 | n/a | n/a |
| null_bad_scale | 61017 | -0.003 | -0.002 | n/a | n/a |
