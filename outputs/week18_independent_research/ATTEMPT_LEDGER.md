# Attempt ledger (every model / rule / variant / setting tried in Week 18+)

Columns: id · date · what (model + acquisition + hyperparameter treatment) · mechanism hypothesis · data
(label) · kill criterion (set before running) · outcome · decision (kept / killed / pending) · pointer.

Inherited from Weeks 12–17 (for multiplicity accounting; not re-counted as Week 18 attempts): Week 9
acquisition search (≈ 30 policies, OLD), Weeks 13–17 synthetic acquisition variants (margin, coverage,
BALD, EBR, EBR-D, VSUR, PEER, random), Week 17 models (G3, M3, M3_C, M3_free, M3_Cfree, LT, H).

| id | date | what | mechanism | data | kill criterion | outcome | decision | pointer |
|---|---|---|---|---|---|---|---|---|
| A0 | 2026-10-05 | G3 margin/random × hyper {fixed OLD, per-step ML-II} × seeds {W15, W17} | NEW "random > margin" is a hyper/seed artefact | R3_NEW all 100 splits (POST-HOC) | — (diagnostic) | margin ≈ 0.66 everywhere; random gains +0.023–0.026 from ML-II; exception = ML-II × random + seed noise | resolved (no method) | phase0/ |
| E1 | 2026-10-05 | GPR on log max depth + straddle (Week 7 formulation, reproduced as baseline) | continuous depth carries distance-to-boundary information | DEV real (tasks with depth), twins T_DEPTH/T_TOBIT | killed if BA AULC < G3+margin − 0.005 on R3_OLD DEV and no QTT gain | pending | pending | phase2/, phase3/ |
| E2 | 2026-10-05 | Censored (Tobit) GP: conduction depth exact, Keyhole censored above, label-only non-Keyhole censored below; ML-II every 4 queries (warm start); margin and straddle | conduction runs reveal distance to the transition; Keyhole depth is another regime and must not be regressed on | DEV: R3_OLD, R2rev, R2 (OLD prior depth), R1_POOLED (OLD depth only), twins T_TOBIT {pooled, OLD, NEW}, T_DEPTH OLD | killed if, vs G3+margin with the same ML-II schedule, BA AULC gain < +0.005 on R3_OLD DEV **and** twin NSD AULC gain < +0.01 on both depth twins **and** QTT(B80 target) not ≥ 10% lower | pending | pending | phase3/ |
| C1 | 2026-10-05 | G3 on (log P, log VX, log LS, ST) (G3L) + margin, per-step ML-II | power-law physics → boundary more stationary/linear in log inputs | DEV real R1/R2/R3, twins | killed unless G3L − G3 (margin) BA AULC ≥ +0.005 on ≥ 2 of {R1, R3_NEW, R3_OLD} and no family < −0.01 | pending | pending | phase3/ |
| F1 | 2026-10-05 | LT with nested two-start ML-II (default start + G3 optimum) (LTn) + margin | removes the Week 17 single-start optimizer failure; LT then ≥ G3 where physics is useless | DEV real, twins | killed unless LTn − G3 (margin) ≥ +0.005 on ≥ 2 real families and no family < −0.01 | pending | pending | phase3/ |
| A1 | 2026-10-05 | G3 + exploration mixture (random w.p. 0.25, else margin) (mix25), per-step ML-II | random queries inform ML-II and find rare pockets (NEW factorial, item a) | DEV real, twins | killed unless mix25 − margin ≥ +0.005 BA AULC on ≥ 2 real families and no family < −0.01 | pending | pending | phase3/ |
