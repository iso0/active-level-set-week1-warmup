# Week 11 B80 structural feasibility

All 185 validated input rows have distinct exact `P,VX,LS,ST` configuration tokens. Two distinct deterministic, label-free advisory allocations use fixed public seeds `1101` and `1102`. Each shuffles the sorted exact-configuration tokens once and assigns them round-robin across five folds. No seed search was performed. Each witness yields 37 held-out groups and 148 training groups in every fold.

This establishes **structural capacity PASS** for B80 before Bug review. It does not approve either allocation as the frozen split and does not establish that the final eligible cohort can support B80. Final eligible-cohort B80 remains **BLOCKED** pending the independent Bug/status export and an explicit pre-label split decision.

Complete assignments and SHA-256 digests are in `structural_b80_witnesses.json`. Two demonstrated witnesses do not choose or imply a final repeat count; that remains an owner decision.
