"""RC22 decisions taken by the pre-registered rules (PROTOCOL_RC22.md sections 3-4) from the matched-state tables only
(opus_rc22/ingr/DECISIONS.json, 2026-10-21 ~16:00 UTC; robustness results were not looked at before this file was written).
SELECTOR: BALD_LAP passed every criterion (median max-information / max-entropy 0.25; top-1 differs from margin in 97.5 % of states,
          median Spearman vs margin 0.25; differs from SHQ_ATS_H eta-straddle in 95 %); BALD_LAP precedes BALD_GRID in the order.
SIMPLE:   HONLY_LR failed the LL criterion (BA-AULC B8-B24 +0.0166, LL +0.0046 > +0.003); HA_LR passed (BA +0.0095, LL -0.0152).
"""
SELECTOR = "BALD_LAP"
SIMPLE = "HA_LR"
