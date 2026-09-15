# Phase 1.8 claim ledger

| Claim | Decision | Evidence / qualification |
|---|---|---|
| Frozen 2 × 2 paths are exact and leakage-free | PASS | `path_audit.json`; prefix-only replay |
| Published total q20 AULC gain reproduces | PASS | +0.020018382 |
| Dominance decision is MODEL_DOMINANT | PASS | MODEL-PATH CI [+0.013244,+0.032978] |
| Physics model improves on original 4D path | PASS | ME_A0 +0.016452 [+0.010859,+0.022091] |
| Physics path helps ordinary 4D GPC | FAIL | PE_M0 -0.006333 [-0.014049,+0.001439] |
| Query-path effect proves acquisition-function superiority | REJECT | Policies use different posteriors; only fixed path contribution is identified |
| Sensitivity selects a better residual bound | REJECT | Diagnostic only; no setting selected |
| Universal physical or prospective validity | REJECT | One retrospective simulator/material benchmark |
