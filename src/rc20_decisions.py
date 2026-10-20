"""RC20 decisions taken by pre-registered rules (each value cites its rule and its evidence; never edited after use)."""

# Remedy rule (PROTOCOL_RC20_STAGE1.md section 5; pilot c-pilot, 20 units, opus_rc20/pilot/PILOT_DECISION.json, 2026-10-20 12:14 UTC):
# mean per-unit test log loss over B12-B24, remedy minus SHQ_ATS: FD +0.0100 (better in 19/80 unit-budgets), MAP +0.0021 (60/80).
# Neither <= -0.005 -> NONE: no remedy is carried into the main replay or any sequential stage (branch stopped at its gate).
REMEDY = ()

# Candidate rule (PROTOCOL_RC20_STAGE1.md section 6; Stage 1 replay c-replay, 200 units; opus_rc20/stage1/STAGE1.md, 2026-10-20 12:52 UTC):
# candidates SHQ_ATS_H 0.2254 and SHQT_ATS 0.2458 all-path LL-AULC B8-B24 (SHQ_ATS 0.2610); constraints: LL B8-B60 0.1647 / 0.1871
# <= 0.1894, BA B8-B60 0.9384 / 0.9379 >= 0.9253 -> c* = SHQ_ATS_H. Justification gate: -0.0356 (<= -0.010), negative in 8/8 (>= 6/8) -> PASSED.
CAND = "SHQ_ATS_H"
