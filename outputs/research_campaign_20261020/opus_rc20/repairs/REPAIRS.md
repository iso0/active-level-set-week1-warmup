# RC20 documentary repairs (qualifications only; no frozen outcome rewritten)

The full wording is in `outputs/research_campaign_20261018/opus_rc19b/ADDENDUM_RC19B_20261020.md`.

1. **The 23.5-query regression difference.**
   - It is a restricted score with every non-completer imputed at 84 simulations, not an observed complete-time saving.
   - Only 4 of 8 repeats have both arms observed: differences −12, −36, −32, −16.
   - Attainment over RC19 + RC19B: M0Q + MOIVR 12/16 vs SHQ + RANDOM 11/16, unstable (the ranking flipped between the two repeat sets).
2. **Monitor cadence** (`DURATION_CADENCE_REPAIR.json`).
   - The filename DT (1.9–32 µs) is not the time.dat monitor cadence, which is 0.0181–0.0182 µs in every run.
   - Raw time.dat was spot-checked in 5 runs, all matching the summaries.
   - Spike durations span a median of 3,008 monitor rows; only 7 of 250 positives last ≤ 2 rows (5 last ≤ 1 row), not 46.
   - The "partly resolution-limited" remark is withdrawn. Durations and the 0.60 target are unchanged.
3. **The isotonic duration reference** (R² 0.59–0.75 from the true spike ratio) is an empirical, model-specific reference, not a theoretical information ceiling.
