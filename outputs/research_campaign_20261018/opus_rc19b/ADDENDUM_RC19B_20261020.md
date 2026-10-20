# Addendum to RC19B (dated 2026-10-20; written during RC20; qualifications only)

No frozen RC19B outcome, table or verdict is rewritten. The original files stay as published (commit c2f720c6). Each item below qualifies a sentence of `FINAL_REPORT_RC19B.md` or of the ledger row RC19B-RESULTS.

## 1. "M0Q + MOIVR needs 23.5 fewer simulations than SHQ + RANDOM" is an imputed, restricted score

- The pre-declared D3 contrast replaced every non-completion (no confirmed joint pair by B80) with 84 simulations. That value is a lower bound of the unknown completion spend.
- Per repeat (r11–r18), the joint confirmation spends were:

  | arm | spends per repeat | completed |
  |---|---|---|
  | M0Q + MOIVR | 44, 40, –, 60, 48, 48, 56, 52 | 7/8 |
  | SHQ + RANDOM | 56, 76, –, –, –, 80, 72, – | 4/8 |

- With 84 imputed, the means are 54.0 and 77.5, a difference of −23.5. This is a restricted-mean score, not an observed complete-time saving:
  - only 4 repeats (r11, r12, r16, r17) have both arms observed (differences −12, −36, −32, −16);
  - in 3 repeats only M0Q + MOIVR completed (the difference is bounded, not observed);
  - in 1 repeat neither completed.
- Attainment is unstable across repeat sets: RC19 (r3–r10) had SHQ + RANDOM 7/8 and M0Q + MOIVR 5/8; RC19B (r11–r18) has 4/8 and 7/8. Combined over 16 repeats: M0Q + MOIVR 12/16, SHQ + RANDOM 11/16.
- The joint target equals spike-duration completion, whose R² sits near its 0.60 target at B60–B80.
- **Allowed wording:** "With non-completers scored at 84, the restricted joint-spend score favoured M0Q + MOIVR by 23.5 simulations in RC19B. Attainment was 12/16 vs 11/16 over RC19 + RC19B and is not stable."

## 2. Monitor cadence: the "≤ 2 rows" statement used the wrong time step

- The duration audit divided spike durations by the time step DT parsed from the run name.
- That DT (1.9–32 µs) is not the cadence of the monitor rows. In time.dat the row interval is 0.0181–0.0182 µs in every run (median 115,600 rows over 2.1 ms). This was spot-checked against the raw time.dat of 5 runs.
- Spike durations are sums of time.dat row hold times. Recounted in monitor rows (`opus_rc20/repairs/DURATION_CADENCE_REPAIR.json`):
  - positive durations span a median of 3,008 monitor rows;
  - **7** of 250 positives last ≤ 2 rows (5 last ≤ 1 row), not 46.
- The remark that the zero/positive boundary is "partly resolution-limited" is withdrawn.
- The zero audit itself (234 zeros of 484; no zero has spike ratio ≥ 2) and all duration values and targets are unchanged.

## 3. The isotonic duration reference is not a theoretical ceiling

- The R² 0.59–0.75 reference came from an isotonic map from the TRUE spike log-ratio to duration, evaluated on random train/test splits. It is an empirical, model-specific reference, not an information bound:
  - a model using the spike ratio together with x, or other outputs, could exceed it;
  - finite-sample noise also enters.
- **Allowed wording:** "An isotonic map from the true spike ratio reaches R² 0.59–0.75, so duration is noisy even given the spike strength."
- **Forbidden:** "a ceiling of 0.75" or "duration cannot be predicted better".

## Unchanged

- The positive physical-sharing result (SHQ) and the velocity-spike-region result (SHQ + straddle) stand.
- The failed hurdle-duration and MOIVRB results stand and are not rerun.
- Energy and monitor hypotheses remain in the backlog. No gas mechanism is claimed without a validated gas-related channel.
