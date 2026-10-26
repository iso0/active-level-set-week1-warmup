# NEXT ACTION

Stage 1 is registered: `PROTOCOL_C1C.md` and `freeze/C1C_MANIFEST.json` are committed and pushed. The registered runs are pending or running.

1. **Runs:** the runner works through c1c-main (800 units), c1c-start (400) and c1c-prior (200).
   - Restart, idempotent: `powershell -NoProfile -ExecutionPolicy Bypass -File src\c1c_start_runner.ps1`
   - Status: `outputs/research_campaign_20261026/opus_c1_confirmation/runner/STATUS.md`
2. **Before evaluating:** do NOT evaluate or look at any result until all 1,400 units are done. No stopping and no resizing.
3. **Afterwards, in order:**
   - `python -m src.c1c_freeze check final`
   - `python -m src.c1c_eval all`
   - `python -m src.c1c_export`
   - the reports (§9 of the protocol), the records, commit + push, then close the runner and the campaign.

Never edit a file listed in the manifest after the registration commit. A change needs a recorded amendment.
