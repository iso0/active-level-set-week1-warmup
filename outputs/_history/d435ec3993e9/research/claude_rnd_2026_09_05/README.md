# Research R&D package — active level-set estimation, melt-pool regime boundary (2026-09-05)

Development data: the frozen 405 SPH cases only. No new-pool label was accessed (none were available; HF `ioandanielc/sph_v2` main still holds only the old 407 folders).

Documents (read in this order):
1. RESEARCH_DIAGNOSIS.md — evidence chain, ceiling/exception decomposition, ranked bottlenecks
2. MATHEMATICAL_DEVELOPMENT.md — losses, models, derived acquisitions, reductions; §9 exact propositions (information collapse, leverage identity, coherent SUR via Owen's T)
3. LITERATURE_AND_NOVELTY.md — nearest prior work and what is/is not new
4. OLD_DATA_RND_REPORT.md — all development experiments (100-run replays), kills, oracle bound, prior sensitivity
5. SATURATION_PREDICTIONS.md — nine frozen numerical predictions for the unseen pool
6. NEW_POOL_FEASIBILITY_SPEC.md — label-free audit and gates (code/new_pool_audit.py)
7. EXTERNAL_CONFIRMATION_PROTOCOL.md + external_confirmation_protocol.json — frozen blinded protocol
8. FINAL_DECISION.md — A–J decision, one frozen challenger (M3 + TV), probabilities, redirection (§I′)

Code: code/challenger.py (frozen challenger), code/label_oracle.py (oracle + isolated evaluator with access log), code/run_external.py (prepare/run/regression), code/new_pool_audit.py, code/tests (6 tests, all pass; arm A reproduces the committed Phase 1.14 path through the oracle). code/rnd/ holds the development scripts (core harness wrapping the repository modules, T model, CDL, exact SUR, replays).

Results: results/*.csv|txt — ceilings, per-point exceptions, same-path model contrasts, acquisition replays (F7, TIGHT, XSUR, XSURT), oracle, window power, feasibility power table, literature notes.

Environment: Python 3.12, numpy/scipy/scikit-learn/pandas; repository `iso0/active-level-set-week1-warmup` at bf4782881bc27fe1ec5256dc3ba0516478a1ed13 must be importable as `src` (core.py sets the path to /home/claude/active-level-set-week1-warmup; adjust REPO there).
