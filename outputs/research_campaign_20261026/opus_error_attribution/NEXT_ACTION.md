# NEXT ACTION

Updated at every milestone; a new session resumes from here.

**Now:**
1. Register `PROTOCOL_EA_HYPOTHESES.md` (hypotheses A–D, rung ladder, analyses), commit and push it.
2. Then implement `src/ea_diag.py` and test it on two DEV learners. Code checks: R0_L = recorded A and R0_T = recorded D, both bit-exact.
3. Then queue job `ea-diag` on the EL-1 forward HA_LEAN paths (STD 83–122, K5 25–32, K4 9–16) with `src/ea_runner.ps1`, using at most 3 workers.

**Resume after a restart:**
- Run `powershell -NoProfile -ExecutionPolicy Bypass -File src\ea_start_runner.ps1`. It is idempotent: finished units are skipped.
- Then read `runner/HEARTBEAT.json` and `STATE.json`.
