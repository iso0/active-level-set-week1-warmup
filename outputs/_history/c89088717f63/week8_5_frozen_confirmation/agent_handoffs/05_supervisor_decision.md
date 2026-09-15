# Week 8.5 supervisor decision

Protocol: `week8_5_frozen_confirmation_protocol/v1.0.0`

Protocol SHA-256: `bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66`

Source base: Week 8 `401b51c3da96897995d2156cde92604231ba9b4a`; Phase 7 ancestor `167aad945b20822de712e891e901bd3ec6d5ffc6`

Scientific scope: offline confirmation on the frozen 405-simulation population; no new simulator run or external-domain validation.

## Supervisor verdict

The preregistered **performance question is confirmed**: Binary GPC uncertainty-only (`binary_margin`) outperforms matched Random acquisition on Fold-B1-q20 accuracy AULC over total budgets 16–80.

The broader practical package is **not fully confirmed**. The restricted-horizon analysis supports fewer queries and a ratio above one, but 16.9% of Random continuations still lack a persistent 0.80 crossing at the maximum predeclared horizon of 160. The protocol therefore requires both the simple query-saving and multiplier claims to remain `QUALIFY`.

Historical h=0.15 repulsion produces a very small change in both diversity and performance. It does not pass the preregistered simultaneous full/low-budget criterion and should not be the thesis headline method.

## Answers to the seven supervisor questions

### 1. Is uncertainty-only confirmed to outperform Random?

**Yes, on the frozen primary endpoint.**

| Quantity | Result |
|---|---:|
| Margin Fold-B1-q20 accuracy AULC 16–80 | 0.813520 |
| Mean matched Random AULC | 0.776220 |
| Difference | +0.037300 |
| One-sided 95% lower bound | +0.031270 |
| Two-sided 95% interval | +0.030132 to +0.044416 |
| Repeat stability | 20/20 repeat-block contrasts positive |

This passes the frozen lower-bound threshold of +0.020. It is evidence about empirical near-boundary classification in the saved 405-row population, not physical-boundary certainty or prospective simulator performance.

### 2. Can we say it saves simulator queries?

**Only with an explicit restricted-horizon qualification.** For the predeclared persistent Fold-B1-q20 accuracy >=0.80 target, a crossing must hold for three consecutive declared checkpoints. At H=160:

- Margin: 91/100 finite crossings.
- Random: 2493/3000 finite crossings (`rho_random=0.831`).
- Restricted mean burden: Margin 39.070; Random 59.169.
- Restricted saving: **20.099 queries**.
- One-sided 95% lower bound: **13.910** queries.
- Two-sided 95% interval: **12.485 to 26.711** queries.

Non-crossers are counted as 160 only for this explicitly bounded burden estimand; their unknown crossing times are not imputed or extrapolated. Because Random finite crossings remain below the preregistered 95% gate, the simple uncensored “20 queries saved” claim does not PASS.

### 3. Can we state an X-times query-efficiency claim?

**Not as a clean confirmed multiplier.** The H=160 restricted burden ratio is:

- `mean restricted Random burden / mean restricted Margin burden = 1.5144x`.
- One-sided 95% lower bound: `1.3292x`.
- Two-sided 95% interval: `1.2928x to 1.7605x`.

The numerical interval exceeds one, but the 95% finite-crossing gate fails. The defensible wording is “the restricted H=160 burden ratio was estimated as 1.51x, with material right censoring,” not “Binary is confirmed 1.51x more efficient.”

### 4. Does repulsion add value beyond uncertainty-only?

**No robust performance contribution was confirmed.**

| Endpoint, repulsion minus margin | Difference |
|---|---:|
| Fold-B1-q20 AULC 16–80 | +0.001829 |
| Fold-B1-q20 AULC 16–40 | +0.002610 |
| Simultaneous one-sided lower bound | -0.000625 |

The direction is slightly positive on average, but the low-budget endpoint is unstable and the effect is far below the +0.010 preregistered threshold.

Mechanistically, repulsion does change selection, but only modestly:

- Same selected row in 81.33% of low-budget acquisitions and 30.06% over the full horizon.
- Mean nearest-queried distance increase: +0.00996 in budgets 17–40 and +0.00517 over 17–160.
- Mean selected uncertainty decreases by 0.00483 and 0.00142 respectively.
- Selected Keyhole fraction is effectively unchanged: 0.2506 for margin, 0.2502 for repulsion.

This is evidence of a small uncertainty-for-distance trade, not a meaningful accuracy improvement.

### 5. What is repulsion's thesis role?

Repulsion is a **useful negative/near-null ablation and secondary mechanism heuristic**, not the primary methodological contribution. The simpler uncertainty-only policy achieves essentially the same boundary performance. This strengthens the thesis by showing that the main gain comes from uncertainty-directed querying rather than added acquisition complexity.

### 6. Claim decisions

| Claim | Decision | Safe wording |
|---|---|---|
| Margin improves Fold-B1-q20 AULC over Random | **PASS** | Confirmed on the frozen offline 405-row benchmark. |
| Budget-40 q20/q30 checkpoint advantage | **PASS as secondary descriptive evidence** | q20: 0.8171 vs 0.7745; q30: 0.8708 vs 0.8288. |
| Fewer queries to persistent 0.80 target | **QUALIFY** | Restricted H=160 estimate: 20.1 fewer; censoring remains material. |
| 1.51x query-efficiency | **QUALIFY** | Restricted burden ratio only; not a clean uncensored multiplier. |
| “40 calls saved”, “2.33x”, “>40 guaranteed” | **FAIL** | Superseded by the frozen confirmation and censor-aware analysis. |
| Repulsion improves performance | **QUALIFY / not confirmed** | Tiny positive point estimate; simultaneous lower bound crosses zero. |
| Repulsion increases diversity | **QUALIFY** | Small nearest-distance increase; no meaningful performance payoff. |
| Prospective/general physical-boundary validation | **FAIL / not tested** | No new simulator campaign or external-domain holdout. |

Machine-readable authority: `../claim_decisions.csv` and `../bootstrap_or_hierarchical_ci.csv`.

### 7. Strongest Ioan-facing story

Week 8.5 confirms the core methodological result but simplifies its interpretation: uncertainty-only Binary GPC is reliably better than Random for empirical near-boundary classification. The strongest result is the preregistered AULC contrast, supported in all 20 new repeat blocks. The practical query burden is lower within H=160, but remaining right censoring prevents a clean uncensored “X calls saved” or “Y-times” headline. Historical repulsion adds only a tiny diversity and accuracy change, so the simpler margin policy is the defensible primary method.

## Limitations and audit qualifications

- The 20 repeat blocks repartition the same 405 simulations; they are not 20 independent physical campaigns.
- `has_keyhole` is the only ground truth. Fold-B1-q20 is a manual-label-dependent evaluation subset and never enters acquisition.
- The 405-row population is class-imbalanced and no new-data/domain-shift confirmation was performed.
- Twelve pairs of distinct GPC fit-seed keys collide after reduction to 32 bits. Random order seeds and all 3000 Random orders are unique, so no duplicate trajectory or headline change was found. This remains a provenance qualification.
- The final executable information-flow audit checks all 3200 checkpoints, persisted train/test memberships, 460800 acquisition records, and the chooser signature. It passes.
- Critic found no result-changing bug; final status is `PASS_WITH_QUALIFICATIONS`.

## Exact support

- Primary and secondary metrics: `../run_level_metrics.csv`, `../repeat_level_metrics.csv`, `../learning_curves.csv`.
- Intervals: `../bootstrap_or_hierarchical_ci.csv`, `../hierarchical_bootstrap_summary.json`.
- Crossings and censoring: `../query_crossings.csv`, `../query_savings_summary.csv`, `../adaptive_horizon_decision.json`.
- Repulsion: `../repulsion_ablation_summary.csv`, `../repulsion_mechanism_diagnostics.csv`, `../repulsion_mechanism_summary.csv`.
- Decisions: `../claim_decisions.csv`.
- Integrity: `../validation_report.json`, `../postrun_provenance_addendum.json`, `../run_manifest.json`.
- Independent audit: `04_critic_audit.md`.
