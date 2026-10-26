# NEXT ACTION

Updated at every milestone; a new session resumes from here.

## Done

**Stage 1 (diagnosis):**
- `PROTOCOL_EA_HYPOTHESES.md` (d4dc329d), amendments 1 (fb7e361f) and 2 (613c9c7b).
- Ladder job `ea-diag` 272/272; D2/D3/D4 `ea-diag2` 200/200; D2T `ea-d2t` 200/200.
- Report: `diagnosis/DIAGNOSIS.md`.

**Stage 2 registration:** `PROTOCOL_EA_CANDIDATES.md` (0020b07e). C1 = HA_TREND with MAP hyperparameters under a fixed weak prior; controls C1a / C1b.

## Now

1. Job `ea-cand-dev` (272 units on the recorded HA_LEAN paths of STD 123–162, K5 33–40, K4 17–24) runs in the EA runner.
2. When it finishes, run `python -m src.ea_cand_eval` and apply the carry rule of `PROTOCOL_EA_CANDIDATES.md` §5.
3. If a candidate is carried:
   - write `PROTOCOL_EA_VALIDATION.md` (fresh STD 163–202, K5 41–48, K4 25–32; separate verdicts for early / 0.93 / 0.95; harm limits) and the SHA-256 freeze;
   - commit and push;
   - queue the forward job.
4. If nothing is carried: report the DEV result, then do the records, exports and close.

## Resume after a restart

- Run `powershell -NoProfile -ExecutionPolicy Bypass -File src\ea_start_runner.ps1`. It is idempotent.
- Then read `runner/HEARTBEAT.json` and `STATE.json`.
