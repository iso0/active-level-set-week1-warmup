# Opus EA runner status (auto-generated)

Updated 2026-10-26T17:13:47Z. Runner PID 20572 (started 2026-10-26T13:47:22Z). State **IDLE**. Window: elapsed 3.68 h, remaining 44.32 h (deadline 2026-10-28T13:33:01Z).

Capacity: Opus cap 3 single-thread leaves (logical CPUs 8), runner slots 3, Opus used 0, Astra used 0 (her share is never used), free memory 17967 MB (min 3072). Leaves: 

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| ea_cand_dev | 272/272 | 0 | 0 | 0 | False | K4__s24_b3.json.gz (2026-10-26T15:49:38Z) |
| ea_d2t | 200/200 | 0 | 0 | 0 | False | STD__r122_f5.json.gz (2026-10-26T14:51:42Z) |
| ea_diag | 272/272 | 0 | 0 | 0 | False | K4__s16_b4.json.gz (2026-10-26T14:20:10Z) |
| ea_diag2 | 200/200 | 0 | 0 | 0 | False | STD__r122_f5.json.gz (2026-10-26T14:46:03Z) |
| ea_fwd | 544/544 | 0 | 0 | 0 | False | K4__s32_b4__X.json.gz (2026-10-26T17:13:36Z) |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\ea_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
