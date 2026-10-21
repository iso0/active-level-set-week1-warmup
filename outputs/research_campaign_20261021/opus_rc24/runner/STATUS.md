# Opus RC24 runner status (auto-generated)

Updated 2026-10-21T23:25:30Z. Runner PID 29516 (started 2026-10-21T21:06:53Z). State **IDLE**. Budget: elapsed 2.88 h, remaining 45.12 h (deadline 2026-10-23T20:32:31Z).

Capacity: Opus share 8 threads, runner slots 8, Opus used 1, Astra used 0 (capacity 8 logical CPUs; all-cores authorisation RC24). Leaves: other:10976:1

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| a_match | 240/240 | 0 | 0 | 0 | False | PATH_G3_MARGIN__r66_f5.json.gz (2026-10-21T21:29:59Z) |
| a_own | 240/240 | 0 | 0 | 0 | False | E1S__r66_f5.json.gz (2026-10-21T21:18:07Z) |
| a_smoke | 7/7 | 0 | 0 | 0 | False | PATH_HA_LEAN_MARGIN__r1_f1.json.gz (2026-10-21T21:07:06Z) |
| b_pilot | 160/160 | 0 | 0 | 0 | False | MATCH_BLOCK__s8_b5.json.gz (2026-10-21T21:50:47Z) |
| b_pilot2 | 18/80 | 0 | 62 | 0 | True | STD__r54_f2__PAC_JEER.json.gz (2026-10-21T22:12:05Z) |
| b_pilot3 | 80/80 | 0 | 0 | 0 | False | s8_b5__HA_TREND_MARGIN.json.gz (2026-10-21T22:21:00Z) |
| b_smoke | 1/1 | 0 | 0 | 0 | False | STD__r1_f1__PAC_MARGIN.json.gz (2026-10-21T21:46:28Z) |
| b_smoke2 | 1/1 | 0 | 0 | 0 | False | STD__r1_f1__PAC_JEER.json.gz (2026-10-21T21:51:28Z) |
| c_match | 160/160 | 0 | 0 | 0 | False | MATCH_BLOCK__s16_b5__HONLY_MARGIN.json.gz (2026-10-21T23:25:19Z) |
| c_own | 240/240 | 0 | 0 | 0 | False | BLOCK__s16_b5__HA_TREND_MARGIN.json.gz (2026-10-21T22:35:46Z) |
| c_smoke | 3/3 | 0 | 0 | 0 | False | STD__r1_f1__HA_TREND_MARGIN.json.gz (2026-10-21T22:24:47Z) |
| d_paths | 80/80 | 0 | 0 | 0 | False | HA_LEAN_MARGIN__r66_f5.json.gz (2026-10-21T22:18:34Z) |
| s_dev | 192/192 | 0 | 0 | 0 | False | D6_aleatoric_corner__s4__block__HA_TREND_MARGIN.json.gz (2026-10-21T22:20:43Z) |
| s_test | 640/640 | 0 | 0 | 0 | False | T8_corner_partial45__s110__block__HA_LEAN_MARGIN.json.gz (2026-10-21T23:17:29Z) |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc24_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
