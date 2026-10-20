# RC20 compute accounting (single-thread CPU seconds recorded by each unit; validation and evaluation runs excluded, each < 5 min)

| job | units | CPU-h |
|---|---|---|
| c-pilot | 20 | 0.08 |
| c-replay | 200 | 1.15 |
| c-smoke | 12 | 0.06 |
| c-final | 240 | 1.39 |
| c-replay-x | 200 | 0.36 |
| **total** | 672 | **3.04** |

Paid simulations are a separate cost axis: every Keyhole trajectory spends up to 60 (startup included); no new physical simulation was run (all outcomes are from the 541-run pool). Decision CPU per sequential step: CAND_MARGIN 0.56 s, CAND_ETASTRADDLE 0.61 s.
