# Opus C1S runner status (auto-generated)

Updated 2026-10-29T02:10:09Z. Runner PID 27048 (started 2026-10-29T00:46:06Z). State **IDLE**. Window: elapsed 1.99 h, remaining 46.01 h (deadline 2026-10-31T00:10:41Z).

Capacity: Opus cap 3 single-thread leaves (logical CPUs 8), runner slots 3, Opus used 0, Astra used 0 (her share is never used), free memory 17055 MB (min 3072). Leaves: 

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| c1s_main | 400/400 | 0 | 0 | 0 | False | STD__r362_f5__L.json.gz (2026-10-29T01:38:17Z) |
| c1s_start | 200/200 | 0 | 0 | 0 | False | LOCAL8__r382_f5__X.json.gz (2026-10-29T02:04:50Z) |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\c1s_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
