# IR attempt ledger

Each row is written before its attempt runs. The result column is filled in afterwards. Rows are never deleted.

| id | attempt | label | kill / stop criterion (set before running) | registered | result |
|---|---|---|---|---|---|
| IR-PRE | first look (`prelook/`): width extraction, Spearman with depth, 10-fold CV oracle | DESCRIPTIVE, before registration | none (disclosed in PROTOCOL §0) | after the fact, 2026-10-31 | done 2026-10-31; superseded by parts A/F |
| IR-P1 | data extraction D1–D3 + acceptance V1/V2 | DATA | V1 failure (any |ΔA| > 1e-9) stops parts B–D until fixed | 2026-10-31 (this commit) | done 16:18 UTC: V1 PASS (max |ΔA| 5.7e-14 µm, 540 runs; 1 known bounds/time-mismatch run unavailable); width 540, KE 539, T/V/laser/E/N ≈ 485 (55–56 OLD runs without the file); 197 Keyhole event windows. V2 shadow PASS (0.0), V4 PASS, V5 PASS (0.0), V6 g* frozen (BA on true depth 0.978) |
| IR-A | correlation structure A1–A5 | DESCRIPTIVE | none (all listed quantities reported) | 2026-10-31 | done 16:43 UTC (`descriptive/`) |
| IR-B | learnability on recorded C1 paths | DEV-DESCRIPTIVE | none | 2026-10-31 | done 16:52 UTC (`screen/partB_learnability_STD.csv`); full STD set (timing 0.81 worker-h ≤ 8) |
| IR-C | method screen: LMC_{W,KE,T}, CHAIN_{W,KE,T}; controls SUM2, ICM_W, ORACLE_CHAIN_{W,KE,T} | DEV | carry rule S1–S4; none pass → stop, no part D/E | 2026-10-31 | done 16:53 UTC: 272/272 units, 0 failed, LMC/SUM2/ICM optimiser success 2176/2176 each; **no candidate passes S1** (best S1 mean +0.0001); carried: none; independent recomputation PASS (max |Δ| 0.0) |
| IR-D | downstream DEV test of the carried candidate | DEV | rule D1–D4; any fails → stop, no part E | 2026-10-31 (runs only if IR-C carries) | NOT RUN (no carried candidate; registered stop) |
| IR-E | fresh test | FRESH | separate protocol registered before any fresh result | runs only if IR-D passes | NOT RUN; fresh IDs STD 383+, K5 49+, K4 33+ remain unused |
| IR-F | within-run time coupling F1–F4 | DESCRIPTIVE | none | 2026-10-31 | done 16:55 UTC (`temporal/`) |
| IR-G | literature check | LITERATURE | none | 2026-10-31 | done (`LITERATURE.md`) |
| IR-X | EXTRAS after registration: W/D ≤ 2.75 (from part G); the ~300 µm depth ceiling (134/197 Keyhole runs) and parts A1/A3/F1/F3 below vs at it | EXTRA (interpretation aid) | none; changes no registered rule or number | 2026-10-31, after parts A/F results (disclosed) | done (`extras/EXTRAS.json`) |
