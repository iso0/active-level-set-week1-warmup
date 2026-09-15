# Supervisor one-page — Phase 1.19B

- **Question:** Can the near-monotone `(P up, VX down, LS down)` order reduce true simulator queries in finite-pool regime recovery?
- **Protocol:** 20 repeats, four frozen arms, B16–B120, full 405 and main 364; no inferred label entered M3.
- **AULC:** P0 0.9849; P1 0.9753; P2 0.9717; P3 0.9764.
- **Primary P3−P0:** -0.0085, CI [-0.0119,-0.0053], Holm p=0.
- **Mechanism:** P3 structurally resolved the pool with 86.35 mean true queries, but B120 BA was 0.9867 versus P0 0.9992; cheap coverage did not translate into better AULC.
- **Inference error:** P3 B120 0.769% among inferred labels, but KH-as-C is 2.47% of the KH class versus 0.20% of the C class; the directional safety gate fails.
- **Boundary:** q20: P0=0.9560, P3=0.9347, difference=-0.0213; q30: P0=0.9663, P3=0.9497, difference=-0.0166.
- **Decisions:** MONOTONE_POOL_HARM; MONOTONE_PROPAGATION_TOO_RISKY; LABEL_SAVING_NOT_SUPPORTED.
- **Claim limit:** prospective finite-pool evidence only; no universal monotonicity or guaranteed free labels.
