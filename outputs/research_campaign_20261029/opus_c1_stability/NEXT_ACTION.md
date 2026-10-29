# NEXT ACTION

Stage 2 is registered: `PROTOCOL_C1S.md` and `freeze/C1S_MANIFEST.json` are committed and pushed. The fresh test is running or pending.

- Code map: [graphify/C1_CODE_MAP.md](graphify/C1_CODE_MAP.md). Graphify usage: [graphify/GRAPHIFY_USAGE.md](graphify/GRAPHIFY_USAGE.md). Use the explicit pinned graph only.
- DEV diagnosis: [diag/DIAGNOSIS_C1S.md](diag/DIAGNOSIS_C1S.md).

1. **Runs:** c1s-main (400 units) and c1s-start (200).
   - Restart, idempotent: `powershell -NoProfile -ExecutionPolicy Bypass -File src\c1s_start_runner.ps1`
2. **Before evaluating:** do NOT evaluate before all 600 units are done.
3. **Afterwards, in order:**
   - `python -m src.c1s_freeze check final`
   - `python -m src.c1s_eval all`
   - `python -m src.c1s_export`
   - the reports, records, commit + push, then close the runner and the campaign.
