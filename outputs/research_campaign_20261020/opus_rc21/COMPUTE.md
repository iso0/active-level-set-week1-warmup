# RC21 compute accounting (single-thread CPU seconds recorded by each unit; validation, evaluation and reporting runs excluded, each < 5 min)

| job | units | CPU-h |
|---|---|---|
| d-replay | 200 | 0.61 |
| d-smoke | 12 | 0.09 |
| d-final | 240 | 1.99 |
| e-smoke | 8 | 0.06 |
| e-final | 160 | 1.38 |
| **total** | 620 | **4.13** |

Paid simulations are a separate cost axis: every Keyhole trajectory spends up to 60 (startup included); no new physical simulation was run (all outcomes are from the 541-run pool).
