# IR attempt ledger

Each row is written before its attempt runs. The result column is filled in afterwards. Rows are never deleted.

| id | attempt | label | kill / stop criterion (set before running) | registered | result |
|---|---|---|---|---|---|
| IR-PRE | first look (`prelook/`): width extraction, Spearman with depth, 10-fold CV oracle | DESCRIPTIVE, before registration | none (disclosed in PROTOCOL §0) | after the fact, 2026-10-31 | done 2026-10-31; superseded by parts A/F |
| IR-P1 | data extraction D1–D3 + acceptance V1/V2 | DATA | V1 failure (any |ΔA| > 1e-9) stops parts B–D until fixed | 2026-10-31 (this commit) | pending |
| IR-A | correlation structure A1–A5 | DESCRIPTIVE | none (all listed quantities reported) | 2026-10-31 | pending |
| IR-B | learnability on recorded C1 paths | DEV-DESCRIPTIVE | none | 2026-10-31 | pending |
| IR-C | method screen: LMC_{W,KE,T}, CHAIN_{W,KE,T}; controls SUM2, ICM_W, ORACLE_CHAIN_{W,KE,T} | DEV | carry rule S1–S4; none pass → stop, no part D/E | 2026-10-31 | pending |
| IR-D | downstream DEV test of the carried candidate | DEV | rule D1–D4; any fails → stop, no part E | 2026-10-31 (runs only if IR-C carries) | pending |
| IR-E | fresh test | FRESH | separate protocol registered before any fresh result | runs only if IR-D passes | pending |
| IR-F | within-run time coupling F1–F4 | DESCRIPTIVE | none | 2026-10-31 | pending |
| IR-G | literature check | LITERATURE | none | 2026-10-31 | pending |
