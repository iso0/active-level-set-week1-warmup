# Claim ledger

| Claim | Status | Evidence / limitation |
|---|---|---|
| Baseline partial order reproduces | SUPPORTED | 22,050/3 full; 19,491/3 main. |
| Inferred labels entered M3 training | FALSIFIED | Query log and engine enforce true queried labels only. |
| P3 improves finite-pool AULC over P0 | MONOTONE_POOL_HARM | Paired 20-block bootstrap and Holm family control. |
| Monotonic propagation is safe enough | MONOTONE_PROPAGATION_TOO_RISKY | Incorrect inferences are explicitly counted. |
| True-query label saving is supported | LABEL_SAVING_NOT_SUPPORTED | Threshold attainment is right-censored and requires paired CI support. |
| q20 was replaced by pool-level LSE | NOT SUPPORTED | q20/q30 remain frozen secondary diagnostics. |
| Structural inferences are guaranteed labels | NOT SUPPORTED | Three frozen violations exist. |
| Continuous-domain monotonicity is established | NOT TESTED | Finite 405-point simulator pool only. |
