# RC22 compute accounting (single-thread CPU seconds recorded by each unit; validation / reporting runs excluded, each < 10 min)

| job | units | CPU-h |
|---|---|---|
| g-smoke | 11 | 0.08 |
| g-ingr | 80 | 0.43 |
| g-miss | 40 | 0.15 |
| g-start | 240 | 1.46 |
| g-block | 120 | 0.64 |
| g-acq | 200 | 1.37 |

Total 4.13 CPU-h on <= 2 single-thread workers (Astra's share released, never used). Paid simulations are a separate axis: every trajectory spends <= 60 (startup included); no new physical simulation was run.
