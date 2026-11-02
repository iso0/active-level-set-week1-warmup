# GT study (2026-11-02): geometric Keyhole classifier and early temperature

Start with `FINAL_REPORT_GT.md` (Turkish). The rules are in `PROTOCOL_GT.md`, registered as 9dcee41f before any result. The attempts are in `ATTEMPT_LEDGER.md`.

| path | content |
|---|---|
| `TASK.md` | the owner's brief (summary) |
| `data/GT_RUNS.csv`, `temporal/GT_EARLY.npz` | frozen data layer (`src/gt_data.py`): geometry definitions per run and causal early features |
| `acceptance/ACCEPTANCE_G1.json` | shadow tests, depth-GP identity, linearity identity, Monte-Carlo check |
| `dev/G2_*` | matched DEV comparison on the 272 recorded C1 paths: result, selection, summaries, subgroups, CPU, checks |
| `dev/G3_*` | DEV own paths (only if G2 was promising) |
| `freeze/`, `validation/` | G4 fresh validation (only if G3's transition rule passed) |
| `temporal/TB_DEV_*` | QT-B: early evaluation of a started run (DEV half; the VAL half stays closed unless the benefit rule passed) |
| `ceiling/CEILING_EVIDENCE.json` | the ~300 µm depth pile-up: sources searched and internal evidence |
| `regression/` | the full test-suite log and the old-base (b0e9569f) rerun of the two earlier failures |
| `exports/` | predictions (float32) and query IDs per stage, with the independent recomputation acceptance |
| `figures/` | fig1 definitions, fig2 G2, fig3 G3, fig4 early temperature, fig5 ceiling |
| `runner/`, `logs/` | worker logs, status and restart commands (`src/gt_runner.ps1`) |

Code: `src/gt_*.py`.
- The C1 reference is unchanged: `src/ea_cand.py` and `src/ea_fwd.py`.
- Raw per-unit files (`*/units/`) are git-ignored. Their content is in `exports/`.
