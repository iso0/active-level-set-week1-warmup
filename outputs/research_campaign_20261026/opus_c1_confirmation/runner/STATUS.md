# Opus C1C runner status (auto-generated)

Updated 2026-10-26T21:43:18Z. Runner PID 14908 (started 2026-10-26T18:33:46Z). State **IDLE**. Window: elapsed 3.63 h, remaining 44.37 h (deadline 2026-10-28T18:05:16Z).

Capacity: Opus cap 3 single-thread leaves (logical CPUs 8), runner slots 3, Opus used 0, Astra used 0 (her share is never used), free memory 18389 MB (min 3072). Leaves: 

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| c1c_main | 800/800 | 0 | 0 | 0 | False | STD__r282_f5__L.json.gz (2026-10-26T20:19:02Z) |
| c1c_prior | 200/200 | 0 | 0 | 0 | False | STD__r162_f5.json.gz (2026-10-26T21:33:00Z) |
| c1c_start | 400/400 | 0 | 0 | 0 | False | LOCAL8__r322_f5__X.json.gz (2026-10-26T21:12:35Z) |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\c1c_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
