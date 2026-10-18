# Opus runner status (auto-generated)

Updated 2026-10-18T08:53:32Z. Runner PID 27680 (started 2026-10-18T08:53:31Z). State **RUNNING**. Budget: elapsed 0.2 h, remaining 47.8 h (deadline 2026-10-20T08:41:20Z).

Capacity: Opus share 2 threads, runner slots 1, Opus used 1, Astra used 0 (her reserved share is 2). Leaves: 

| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |
|---|---|---|---|---|---|---|
| selftest | 0/3 | 0 | 3 | 0 | False |  () |

| worker PID | job | start (UTC) | CPU s | log |
|---|---|---|---|---|
| 16492 (children ) | selftest | 2026-10-18T08:53:32Z | 0.1 | C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev\outputs\research_campaign_20261018\opus\runner\workers\selftest_1.log |

Restart (idempotent): `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)`
