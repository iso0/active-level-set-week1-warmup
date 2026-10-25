# Opus EL runner status (auto-generated)

Updated 2026-10-25T23:15:11Z. Runner PID 14300 (started 2026-10-25T20:21:29Z). State **IDLE**. Window: elapsed 3.12 h, remaining 44.88 h (deadline 2026-10-27T20:07:51Z).

Capacity: Opus cap 3 single-thread leaves (logical CPUs 8), runner slots 3, Opus used 0, Astra used 0 (her share is never used), free memory 16923 MB (min 3072). Leaves: 

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| el_cross | 464/464 | 0 | 0 | 0 | False | D__K4__r8_f4.json.gz (2026-10-25T20:41:34Z) |
| el_fwd | 544/544 | 0 | 0 | 0 | False | K4__s16_b4__T.json.gz (2026-10-25T21:36:52Z) |
| el_mix_dev | 544/544 | 0 | 0 | 0 | False | K4__s16_b4.json.gz (2026-10-25T22:36:24Z) |
| el_mix_fwd | 272/272 | 0 | 0 | 0 | False | K4__s24_b4.json.gz (2026-10-25T23:15:09Z) |
| el_mix_smoke | 1/1 | 0 | 0 | 0 | False | STD__r1_f1.json.gz (2026-10-25T22:40:33Z) |
| el_smoke | 2/2 | 0 | 0 | 0 | False | STD__r1_f1__T.json.gz (2026-10-25T20:51:06Z) |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\el_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
