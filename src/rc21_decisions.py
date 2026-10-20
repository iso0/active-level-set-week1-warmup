"""RC21 decisions taken by the pre-registered rules (PROTOCOL_RC21_STAGE1.md section 4), from the Stage 1 tables only.
NEW: the sequential candidate construction ("PHR" or "PHR_NR"); None = not carried (justification gate failed).

Stage 1 (stage1/STAGE1_DECISION.json): residual rule -> PHR_NR (PHR - PHR_NR: BA-AULC B8-B24 -0.0006, LL-AULC +0.0054 >= +0.003).
Gate vs SHQ_ATS_H (B8-B24): BA MATERIAL (+0.0102, 8/8) but LL MATERIAL HARM (+0.0164, 1/8) -> rule outcome NEW = None.
AMENDMENT A1 (opus_rc21/AMENDMENT_A1.md; logged before any sequential outcome): the LL part of the gate is overridden because it
contradicts the pre-registered co-primary endpoints of the sequential stage (decision accuracy, paid queries); NEW = PHR_NR, the
construction the pre-registered residual rule selected, unchanged. LL harm is a declared, reported secondary consequence.
"""
NEW = "PHR_NR"
NEW_RULE_OUTCOME = None          # what the pre-registered gate returned (kept for the record)
