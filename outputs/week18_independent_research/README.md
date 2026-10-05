# Week 18+ independent research campaign — map

Start `bbb79eaf` (Week 17). Resume with "continue": read RESEARCH_LOG.md (status board + dated log) first.

| File / folder | Content |
|---|---|
| [REPORT.md](REPORT.md) | campaign report (phases, results, verdict) |
| [RESEARCH_LOG.md](RESEARCH_LOG.md) | status board, open owner decisions (D1: NEW monitors), dated log |
| [ATTEMPT_LEDGER.md](ATTEMPT_LEDGER.md) | every model / rule / variant / setting tried, data, kill criterion, outcome, decision |
| [CLAIM_LEDGER.md](CLAIM_LEDGER.md) | claims with evidence labels |
| [RED_TEAM.md](RED_TEAM.md) | Phase 0 red-team of the Week 12–17 endpoint |
| [ERRATA.md](ERRATA.md) | errata to earlier weeks and to Week 18's own files (historical outputs untouched) |
| [DATA_AUDIT.md](DATA_AUDIT.md) | Phase 1: settings, label = depth threshold, OLD/NEW compatibility, Bug withholding (+ amendment) |
| [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md) | locked tasks, blocks (DEV 1–8, C1–C3), metrics, schedules |
| [PHASE2_BASELINES.md](PHASE2_BASELINES.md) | baselines on real DEV tasks and twins; external validity |
| [THEORY_WEEK18.md](THEORY_WEEK18.md) | T18-1 … T18-5, predictions, Astra Round 3 integration |
| [FREEZE_ROUND_1.md](FREEZE_ROUND_1.md), `round_1/` | round-1 freeze (E1 depth GPR + straddle), runs, decision |
| [THESIS_IMPLICATIONS.md](THESIS_IMPLICATIONS.md) | what changes in the thesis text |
| `phase0/` | NEW hyperparameter × seed × rule factorial (open item a) |
| `phase1/` | compatibility and pooled CV tables |
| `phase2/` | baseline caches, curves, AULC, contrasts, QTT, external validity |
| `phase3/` | development experiments: `depth/` (E2 first run), `depth2/` (E1b/E2/E3), `cfa/` (C1/F1/A1), `headroom/` |
| `phase4/` | theory checks (Astra Round 3 checks, ML-II design check, saturation) |
| `figures/` | figures |

Code: `src/week18_*.py` (engine, tasks, twins, stress worlds, Tobit/mixed depth GP, baselines, dev runner, confirmation
runner, analyses); tests `src/tests/test_week18_*.py` and `test_week17_integrity.py`.
Astra Round 3 package (verbatim): `outputs/astra_round3/`.
