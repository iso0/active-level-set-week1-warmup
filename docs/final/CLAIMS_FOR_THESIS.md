# Claims for the thesis: what may be written, how, and what must not be written

Written on 2026-11-02. This file selects, from the full ledgers, the claims a thesis chapter will actually use. For each claim it gives the allowed wording, the status, the scope and the overclaim to avoid. Quoted wordings come from the "Allowed wording" and "Forbidden overclaim" columns of `docs/alse/claims.md`; other sources are named.

**Sources of record.** Use them when a claim is not listed here:
- `docs/alse/claims.md`: C01–C158. It covers Weeks 1–9 and RC19 → GT.
- `outputs/joint_depth_label_development/CLAIMS_MATRIX.md`: the joint study (S, F, L, U, TR, E, P, Q rows), IR and GT.
- The study ledgers of Weeks 10–20: `docs/trackA_freeze/`, `outputs/week14_research_program/CLAIM_LEDGER.md`, `outputs/week16_theory_meets_data/CLAIM_LEDGER.md`, and the Week 11–20 reports.
- The Research Hub: `docs/research/CLAIM_LEDGER.csv` on `main`, 16 scoped editorial claims up to C1C.

**One rule for every chapter.** All real-data claims are in-pool. They come from re-splits of the same SPH simulations (541 runs from RC19 on). None is an external or physical validation, and none claims a new method (C108, C114, C122, C130).

## Chapter: synthetic benchmarks (Weeks 1–4)

| ID | Claim (allowed wording) | Status | Do not write |
|---|---|---|---|
| C10 | "Method ranking depends on benchmark geometry and metric." | SUPPORTED exploratory | one acquisition is universally best; synthetic rankings transfer to the real data |
| C39 | Straddle-family GPR rules beat random sampling on synthetic level-set problems | SUPPORTED exploratory | — |
| C40 | Kernel optimisation of the synthetic GPC helps on every benchmark | NOT SUPPORTED | — |

## Chapter: data and the binary target

| ID | Claim | Status | Do not write |
|---|---|---|---|
| C36 | "The frozen benchmark population is 405 simulations with 73 manual Keyhole labels." The pooled problem adds NEW (136 runs, 124 Keyhole): 541 runs, 197 Keyhole | data fact | proxies replaced manual labels; simulations were removed |
| C37 | "Depth regression fails where the regime changes, so the boundary itself became the target." | SUPPORTED exploratory | regression was abandoned because GPs are unsuitable |
| C20, C103 | "The empirical discriminative direction is consistent with the theoretical exponents." h = P/√(VX·LS³) has units W·s^½·m⁻²; z_h is dimensionless | SUPPORTED exploratory; C103 withdrew "dimensionless" | h is dimensionless or the complete Keyhole number; LS is the spot diameter; a universal h threshold |
| C06, C07 | a universal G3 or max-depth threshold exists | PROHIBITED | — |
| W18 | on OLD, `has_keyhole` coincides with a maximum-depth threshold of about 111 µm (AUC 1.000); on NEW it does not (AUC 0.891) | descriptive (Week 18 report) | "the label is a depth threshold" without the OLD / NEW qualifier |

## Chapter: binary boundary learning on real data (Weeks 7–10)

| ID | Claim | Status | Do not write |
|---|---|---|---|
| C01 | "Under the frozen Week 8.5 protocol, binary_margin beat matched Random on Fold-B1-q20 accuracy AULC in all 20 repeat blocks." (+0.0373, one-sided lower +0.0313) | **SUPPORTED confirmatory** | universal optimality; prospective validation; the superseded "0.8138 vs 0.7711" |
| C02 | "Repulsion adds no confirmed gain over uncertainty-only sampling; the gain comes from uncertainty-directed querying." | SUPPORTED confirmatory | "repulsion significantly improves boundary accuracy" |
| C14, C15 | "Within H=160 the restricted mean query burden was 20.1 queries lower for margin, with 16.9% of Random continuations right-censored"; "the restricted H=160 burden ratio was 1.51x, with material right censoring." | QUALIFIED | "40 calls saved"; "2.33x"; "confirmed 1.51x more efficient" |
| C16, C17 | the full sample-efficiency package; "at least X queries saved" | NOT SUPPORTED | "the sample-efficiency package is confirmed" |
| C18 | "AULC measures how quickly learning improves; by 320 queries the terminal q20 gap is practically zero." | SUPPORTED exploratory (post hoc) | margin reaches a higher final accuracy |
| C21 | "Residual 4D structure matters near Fold-B1-q20; h is not sufficient for the 4D problem." | SUPPORTED exploratory | "h acquisition saves about 45 queries" |
| C23 | "The improvement comes from the surrogate, not from a better acquisition function." (Phase 1.8) | SUPPORTED exploratory | "the physics acquisition function is superior" |
| C25 | "h computed from public Ti64 data is strongly discriminative (ROC-AUC 0.98), but a generic two-slope model was better." | NOT SUPPORTED (transfer claim) | cross-material transfer; LS^-3/2 externally validated |
| C28 | "M3 is the preferred simulator surrogate on the frozen replay path." | SUPPORTED exploratory | any acquisition gain; universal validity |
| C29–C35 | correction-signal, repulsion, PA-TVR, FAST-SUR and exact GPC-SUR acquisition rules do not beat M3-margin ("Global one-step SUR did not beat the local probability margin under the same M3 evaluator.") | NOT SUPPORTED / PROHIBITED (C33) | SUR saves labels; novelty |
| Track A | M3 probability margin with feature-only B16 initialisation is the frozen historical control; Candidate B positive but below the +0.01 replacement threshold | frozen (`docs/trackA_freeze/TRACK_A_FINAL_STATE.md`; Hub TRACKA-001) | external validation of Track A |
| W11 | the frozen external validation stopped (`INCOMPLETE_FROZEN_STOP`); no effect estimate exists | frozen record | any external-validation result |

## Chapter: what limits learning (Weeks 11–20)

| ID | Claim | Status | Do not write |
|---|---|---|---|
| W13–W16 | discovering the rare class needs a structural assumption; finite-pool boundary metrics are density-weighted; the oracle headroom of acquisition is invisible to the model posterior | theorem + registered benchmarks (Week 14–16 ledgers) | "acquisition cannot matter" in general |
| W15 | EBR-D does not pass its frozen success criteria (NO NEW METHOD JUSTIFIED) | registered | — |
| W17 | NO CHANGE JUSTIFIED: G3 + margin remains the binary-label endpoint; a better model does not unlock model-aware acquisition | registered (Hub W17-001) | — |
| W18 | depth GP + straddle improves on G3 + margin only on OLD-type tasks where depth determines the label (block C1 +0.0285; block C2 +0.016 below the bar): IMPROVEMENT ON SOME TASKS ONLY | confirmatory blocks (Hub W18-001) | extension to NEW / pooled binary-label tasks |
| W20, C3 | the active-window depth target A beats the whole-record target (C3 ACTIVE − WHOLE +0.044 [+0.023, +0.067]); its BA superiority over G3 is NOT CONFIRMED (+0.007 [−0.036, +0.053]) | confirmatory (C3 block) | "ACTIVE E1 is confirmed better than G3" |
| L1–L2, C54, C67 | the NEW fast-scan corner is unresolved: every model and rule sits at BA 0.45–0.60 inside it ("An unresolved corner; the physical classifiers are weakest there.") | POST-HOC / NOT SUPPORTED that any learner resolves it | "the corner is aleatoric" (C93: untested) |
| F1, F6 | Astra's joint depth–label models failed their screens (J +0.006; V2 −0.002) | registered screens (`CLAIMS_MATRIX.md` §2) | — |
| P5 | physics summaries add nothing over E1 once depth is modelled | registered pilot | "physics is useless" in general |
| Q2–Q3 | adaptive designs need no fewer simulations than space-filling designs to learn the physical outputs (0/48; same-budget gain 1/48) | registered (DEV) | — |

## Chapter: two-stage depth-then-label learning in one pool (RC18–RC24, EL, EA)

| ID | Claim | Status | Do not write |
|---|---|---|---|
| RC18 | an OLD-trained prior mean with shared lengthscales saves about 21 NEW simulations per physical output (DEV) | DEV (frozen protocol) | savings for the Keyhole label |
| C41–C42 | shared-lengthscale emulators (SHQ) learn physical outputs better; SHQ + straddle learns the spike region faster than maximin | SUPPORTED exploratory | — |
| C48 | log h as a shrinkable term in the honest classifier improves probabilities, most at small budgets | SUPPORTED exploratory | — |
| C75 | "The information-gain selector chose very different runs but learned the boundary worse." | NOT SUPPORTED (pre-registered, failed) | that BALD never helps |
| C77 | temperature and spike summaries add information once log h, predicted depth and learned regularisation are present | NOT SUPPORTED (matched) | — |
| C81 | "Dropping temperature and spike from the whole system did not lose BA (loss smaller than 0.010 at 95 %)." (HA_LEAN) | SUPPORTED exploratory (pre-registered non-inferiority) | equivalence; BA superiority |
| C84, C88 | "Depth mainly buys probability quality and late accuracy." "h alone matches the BA curve but not the high target or the probabilities." | SUPPORTED / NOT SUPPORTED (h-only sufficiency) | an early-BA gain from depth; "depth is useless" |
| C92 | "Margin is drawn to a boundary region whose labels are interleaved." | descriptive | "margin wastes queries in any noisy region" |
| C106–C107 | "No unconditional winner; HA_LEAN kept for calibrated probabilities and target maintenance." "Any linear trend in the depth emulator helps early BA." | registered final comparison | "HA_TREND is the thesis learner"; a physics-specific early gain |
| C109 | "The trend emulator's early BA gain comes from its predictions; its own query choices add nothing early." | SUPPORTED (DEV and fresh) | "HA_TREND chooses better simulations" |
| C115–C116 | "Depth information at unqueried inputs limits early learning; with the true depth 8 labels give BA 0.957." "Mostly an information limit; a smaller part is estimation." | SUPPORTED (DEV, evaluator-only oracles) | "the classifier is the bottleneck"; oracle rungs as methods or ceilings |
| C117 | "The trend model's late loss comes from small-n hyperparameter estimation." | SUPPORTED (DEV) | "the physics trend hurts late learning" |
| C121 | "Without the trend the prior makes predictions revert to a constant mean." (C1a refuted) | REFUTED | — |

## Chapter: the final learner, confirmation and robustness (C1C, C1S, FR, IR, GT)

| ID | Claim | Status | Do not write |
|---|---|---|---|
| **C123** | "In the 541-run pool, C1 + margin learns earlier than HA_LEAN + margin; replicated on 80 fresh repeats." (early BA-AULC +0.0053 [+0.0039, +0.0068]) | **SUPPORTED (registered replication)** | "external", "in general", "new method" |
| **C124** | "Reaches 0.95 with fewer simulations on average, mainly because more learners reach it; non-inferior in keeping it (within 5 points)." (+1.81 [+0.53, +3.09]) | **SUPPORTED** (standard maximin startup) | "faster in every run", "keeps 0.95 better", "guaranteed", "superior reliability" |
| C125 | "Fewer simulations to 0.90 and 0.93 in this pool." (+0.38, +1.09) | SUPPORTED | "large saving" |
| C126 | "Sustaining 0.95 was not improved." | NOT REPLICATED | "sustains / keeps 0.95 better" |
| C127 | "Late performance is preserved within 0.003 BA." (−0.0006; BA(60) 0.9568 vs 0.9569) | SUPPORTED as non-inferiority | "late gain", "better at every budget" |
| C128 | "The early gain holds under random and clustered startups and with half or double the prior width." | SUPPORTED | "0.95 reliability under any startup", "prior-free" |
| C129 | "MAP keeps the trend model's early gain and removes its late and log-loss penalty." | SUPPORTED on identical paid data | "C1 + margin beats D early" |
| C130 | "A replicated application gain in this pool; external validation proposed." | pool-only scope | "external validation", "new method", "generalises to new regions" |
| C132 | "About four fifths of the late shortfall is a level deficit that a decision-layer stabiliser cannot remove." | SUPPORTED (DEV 82 %, fresh 81 %) | "the regressions cause the late shortfall" |
| C133, C138 | "Averaging did not change the shortfall below 0.95." "The simplest stabiliser did not pass the registered rule; C1 stays." | NOT SUPPORTED / decision | "AVG4 stabilises C1" |
| C142–C144 | "An information limit (consistent with EA's depth-at-unqueried-inputs bottleneck), not a tuning problem." HA_LEAN is "safer on K5-type held-out regions, not on K4; pooled no difference shown." | SUPPORTED (DEV) | "no paid-only rule could ever work in any design"; "HA_LEAN is safer for extrapolation" unqualified |
| C145–C147 | physical outputs are strongly associated with depth, mostly through the inputs; width moderately; "Within the tried features and models, no practical extra information." | DESCRIPTIVE | "depth carries all label information" unqualified; causal mediation |
| C148 | co-output depth models: "Not shown in the registered screen." | NOT SUPPORTED (DEV screen; sequential test not run) | "no simulation saving" unqualified |
| C150 | the ~300 µm Keyhole depth plateau is "Consistent with a geometric floor; not verified." | OBS; cause HYPOTHESIS | "the domain floor is 300 µm"; "the ceiling does not affect learning" |
| C152 | "On the same opened runs every geometric classifier was clearly below C1." (best −0.0174) | NOT SUPPORTED (DEV matched) | "geometry cannot work in any design"; fresh evidence |
| C154 | "A fixed physical threshold with learned geometry over-calls Keyhole." | POST-HOC descriptive | "the physical threshold is wrong" (it fits the true values) |
| C156–C157 | "Early temperature does not reduce the simulation count." "No execution-time benefit from temperature beyond early depth." | NOT SUPPORTED (DEV) | "CPU time saved"; "early warning system" |
| C158 | "The geometric and early-temperature routes were negative on DEV." C1 + margin unchanged | decision | "external validation"; "novel method" |

## Never write

These lines collect the forbidden overclaims that matter most for the abstract and the conclusion.
- "40 calls saved", "2.33×", or any guaranteed saving (C14–C17).
- That any result is external, prospective or physical validation (C11, C12, C130, C144, C158). The Week 11 attempt has no effect estimate.
- That C1, HA_LEAN or any learner is a new method that beats the literature (C108, C114, C122, C130).
- That an acquisition rule beats margin for the Keyhole label on this pool. None of those tested did with the model fixed. Week 17's NEW exception (post-hoc) concerns rare-class discovery.
- That C1 keeps or sustains BA 0.95 better (C126), or is reliable under every startup (C128).
- That HA_LEAN is unconditionally safer for extrapolation (C143).
- That h is dimensionless (C103), or that a universal h, depth or G3 threshold exists (C06, C07, C20).
- That the fast-scan corner is aleatoric or resolved (C54, C67, C93).
- That the 300 µm plateau is the verified domain floor (C150).
- That the Week 18 confirmation block C1 and the learner C1 are related (GLOSSARY §1).
- Synthetic Astra results as evidence about physical Keyhole labels (Research Hub scope).
