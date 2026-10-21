# RC23 compute accounting (single-thread CPU recorded by each unit; validation and reporting runs excluded, each < 10 min)

| job | units | CPU-h |
|---|---|---|
| h-smoke | 6 | 0.02 |
| h-match | 80 | 0.20 |
| h-std | 160 | 0.64 |
| h-rob | 360 | 1.13 |
| h-block | 120 | 0.36 |
| **total** | 726 | **2.35** |

Per-step decision / training CPU of each arm's own construction (fresh repeats 51-58): HA_LEAN 0.143 s, HA_LR 0.463 s, PHR_NRMAP 0.478 s, HONLY_LR 0.005 s. Paid simulations are a separate axis; no new physical simulation was run.
