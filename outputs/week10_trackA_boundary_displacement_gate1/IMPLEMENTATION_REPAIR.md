# Gate 1 implementation repair

The frozen protocol intended representative alternate-start stability checks on repeats 61, 90, and 120, fold 1, at B16/B28/B40. The initial implementation matched literal strings `w85__r061_f01` and `w85__r090_f01`, while the historical run IDs omit leading zeroes (`w85__r61_f01`, `w85__r90_f01`). As a result, the first analysis contained only the six repeat-120 model/budget stability records.

The selector was repaired to use numeric repeat and fold fields. No model equation, optimizer, path, endpoint, threshold, predictive checkpoint, or decision rule changed. The three intended run checkpoints were regenerated from the same frozen paths; full predictive results remain governed by the unchanged protocol hash.
