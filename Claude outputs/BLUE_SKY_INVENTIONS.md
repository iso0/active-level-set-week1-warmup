# BLUE_SKY_INVENTIONS — a last first-principles attempt to value an unqueried simulator point

Development data only (old 405 cases; the same 80 states and 8,987 eligible candidate-states as ORACLE_MECHANISM_AUDIT, so every number is directly comparable with the 31 failed proxies). No new-pool label or input accessed. Scripts: `code/inventions.py`, `code/inventions_analysis.py`, `code/error_field_test.py`; tables: `results/inventions_features.csv.gz`, `results/inventions_associations.csv`, `results/inventions_crossfit.csv`, `results/error_field_test.csv`, `results/calibration_uncertain_refs.txt`; console: `results/inventions_analysis.txt`.

## 0. What the oracle value *is* (derivation that fixes what any invention must supply)

Let R be the reference set on which the endpoint is scored (the 17 q20 rows), ŷ_u the current M3 decision at u, y_u the truth, and e_u = 2·1{ŷ_u = y_u} − 1 ∈ {+1, −1} the *signed correctness* of the current decision. Adding (x, y) and refitting flips the decisions of a set F_y(x) ⊂ R. Then exactly

  V(x, y) = −(1/|R|) Σ_{u ∈ F_y(x)} e_u  (a flip at a currently-wrong u adds +1/|R|, at a currently-right u −1/|R|),

and the oracle value is V(x, y_x). Three quantities enter: the flipped set F_y(x) (computable label-blind for both y — this is *influence*), the label y_x (unknown; the model's belief is p_x), and the signed correctness field e_u on R (unknown; the model's belief is E[e_u] = 2π_u − 1 when ŷ_u = 1, i.e. ≈ 0 exactly where u is flippable). A label-blind valuation can only be a function of D_n and inputs; under a coherent posterior its expectation of V is Σ_y P(y) Σ_{u∈F_y} (−E[e_u | D_n])/|R|, which is small because flippable references have π_u ≈ ½ — this is the SUR family, already shown to lose to margin. **So an invention can beat margin only by supplying information about the signed field {e_u} (or about y_x) that the model's own posterior does not contain.** The three inventions below are three different sources for such information: (A) the *structure* of the counterfactual refit (influence/instability), (B) *realised* errors of the model on the revealed data (an error map), (C) *structural* hypotheses the data have not excluded (a physics version space).

Evaluation-only decomposition on the 80 states (consistency check: V_oracle ≡ V(x, y_true) to machine precision): the true label's refit flips 4.2 pool decisions on average when V > 0, 2.4 when V < 0 and 0.6 when V = 0 — influence is necessary; and among candidates with V > 0 only **31%** are "surprises" (true label ≠ M3's prediction; base rate 8%): **69% of the valuable queries confirm what the model already predicts and still flip held-out decisions in the right direction.** The value therefore sits mostly in the signs e_u on the reference set, not in the candidate's own label.

## A. Invention 1 — Counterfactual Structural Influence (CSI)

*Object.* For each hypothetical label y ∈ {0,1}, the exact M3 refit on D_n ∪ {(x,y)} including Stage-1 (the near-unregularised log-h logistic) and Stage-2 ML-II hyperparameters; from it: I_y(x) = number of unrevealed-pool decisions that flip; Δτ_y(x) = shift of the Stage-1 threshold in log-h units; Δℓ_y(x) = Σ|Δ log length-scales|; Δσ_y; mean |Δp| on the pool. Scores: I_exp = p I_1 + (1−p) I_0; I_max; I_surprise = I of the label M3 does not predict; I_confirm; |Δτ|_exp, |Δτ|_max, Δℓ_exp, |Δp|_exp.
*Information used.* The *global instability* of the fitted model to one label: Stage-1 refits move the whole threshold (a single low-h KH shifts it by 0.03–0.10 log-h), which no Gaussian look-ahead (SUR/XSUR/TV) sees because those hold hyperparameters fixed.
*Why it could beat margin.* A candidate with p = 0.9 can have I_0 ≫ I_1: its *unlikely* label would move the boundary for many pool rows (a lever-arm quantity), whereas margin only sees p. Not a monotone transform of margin: within-state Spearman of I_max with margin is −0.27, of I_surprise −0.27, of |Δτ|_max −0.65 (large threshold shifts belong to *confident* candidates far from the current threshold).
*Closest prior art (checked after derivation).* Influence functions / "expected model change" (Settles, Craven & Ray 2008, expected gradient length; Cook's distance; Koh & Liang 2017); hyperparameter-refit look-ahead is the "physics-refit SUR" of Phase 1.18B in spirit but scores decision flips of the pool rather than p(1−p).
*Result.* Median within-state Spearman with V: I_exp −0.007, I_max −0.006, I_surprise −0.007, I_confirm −0.021, |Δτ|_exp +0.002, |Δτ|_max +0.017, Δℓ_exp +0.038, |Δp|_exp +0.022; top-decile enrichment 0.3–2.1 (|Δp|_exp 2.05 with AUROC 0.61); mean V of the score's top-1 pick −0.004…+0.002 (margin −0.005; oracle best +0.062). **KILLED** (ρ < 0.30 and enrichment < 2× for every variant). Influence predicts |V| (where V ≠ 0), not V: the sign is set by e_u.

## B. Invention 2 — Realised-error map (LOO meta-error and bias-corrected margin)

*Object.* Leave-one-out M3 on the revealed set gives realised error indicators e_i^LOO and signed residuals r_i = y_i − p_i^LOO at the revealed rows — the only *realised* model errors a label-blind learner has. Kernel-smooth them to candidates and reference rows: ê(u) (local LOO error rate; bandwidths 0.5, 1.0 sd in 4-D and 0.15 in log h), b̂(u) (signed local bias), the bias-corrected probability p̃ = clip(p + b̂) and its margin, and products with influence ê·I_exp (expected flips weighted by the local error rate — the label-blind analogue of the exact identity in §0 with ê in place of e_u).
*Information used.* Where the model has actually been wrong in held-out fashion on the data it has, rather than where it believes it is uncertain.
*Why it could beat margin.* If M3's errors are spatially structured (campaign region, VX range), a realised-error map would tilt E[e_u] away from zero at the flippable references and give the sign that §0 says is missing.
*Not a monotone transform of margin:* Spearman with margin 0.26–0.28 for ê, 0.00 for b̂.
*Closest prior art.* Error-driven / disagreement-based active learning with a residual model (e.g., "learning loss for active learning", Yoo & Kweon 2019; conformal residual scores); cross-validation error maps for sequential design (Sacks et al. 1989-type CV-based criteria).
*Result.* ê (log-h kernel): ρ_median 0.078, block mean 0.080 ± 0.152, AUROC 0.705, enrichment 1.7; |b̂| (log-h): 0.087, 0.067 ± 0.133, enrichment 1.6; ê·I_exp: −0.001…−0.044; corrected margin: −0.004/−0.008. **KILLED.** Direct test of the premise (`error_field_test.csv`): at the same states the LOO error map identifies the model's realised errors on unrevealed pool/test rows with AUROC 0.62–0.67, while M3's own margin does so with AUROC 0.86–0.93; the corrected margin never exceeds margin. The model already knows *where* it is wrong; the LOO map adds nothing, and neither carries the *sign*: on held-out rows with 0.3 < p < 0.7 (1,956 row-states) the mean signed error y − p is −0.014, i.e. E[e_u] ≈ 0 at the flippable references, exactly as the posterior says.

## C. Invention 3 — Structural-hypothesis committee (physics version space)

*Object.* Nine physics coordinates h_ab = P/(VX^a LS^b), (a,b) ∈ {0.25,0.5,0.75}×{1,1.5,2} (the thesis's h is (0.5,1.5)); each hypothesis = Stage-1 logistic on log h_ab + the same Stage-2 ARD discrepancy, fitted to the revealed data; weights ∝ exp(Laplace log-marginal likelihood). Disagreement D(x) = weighted variance of the nine hard decisions at x; D_u unweighted; probability spread; products with influence.
*Information used.* Which structural hypotheses (scaling exponents) the revealed data have not yet excluded — a version-space quantity over *physics*, not over GP samples (bootstraps/QBC) and not one alternative model (|M3 − T| was the best of the 31 proxies at ρ 0.11).
*Why it could beat margin.* Candidates on which surviving exponent hypotheses disagree are where the *boundary orientation* is unresolved; margin measures only distance to the current boundary. Not monotone in margin (Spearman 0.35–0.65).
*Closest prior art.* Query-by-committee (Seung, Opper & Sompolinsky 1992; Freund et al. 1997); Bayesian model averaging over structural hypotheses (hypothesis-space QBC).
*Result.* D_w: ρ_median 0.014; D_u 0.012 (enrichment 2.2, AUROC 0.59); probability spread 0.072, block mean 0.033 ± 0.163; D·I_exp 0.023. **KILLED.** The nine exponent hypotheses disagree mainly far from the current boundary (their decisions coincide near it after 16–40 labels), so D is an orientation-uncertainty measure that does not locate the flippable references.

## D. Oracle-value predictability (all three, plus the 31 old proxies, cross-fitted leave-repeat-block-out)

| Predictor set | model | out-of-block R² | median within-state ρ | block mean ± sd | AUROC top-10% | enrichment top-10% | mean V of top-1 pick |
|---|---|---:|---:|---:|---:|---:|---:|
| 27 new scores only | ridge / GBM | −0.088 / −0.162 | −0.014 / −0.015 | 0.001 ± 0.15 / −0.001 ± 0.11 | 0.55 / 0.50 | 1.30 / 1.06 | −0.002 / 0.000 |
| 28 old + 27 new | ridge / GBM | −0.096 / −0.108 | 0.054 / 0.006 | 0.043 ± 0.14 / 0.023 ± 0.13 | 0.60 / 0.53 | 1.31 / 1.24 | +0.005 / +0.007 |
| oracle best per state (reference) | — | — | — | — | — | — | +0.062 |
| evaluation-only E_p[V(x,·)] (uses test labels; NOT a valuation) | — | — | 0.423 | 0.458 ± 0.11 | 0.88 | 14.1 | +0.029 |

The last row is the diagnostic that closes the question: if the *reference-side* signed errors e_u were known but the candidate's label were not, the model-belief-weighted counterfactual E_p[V] would already reach ρ 0.46 and 14× enrichment. Everything label-blind stays at ρ ≈ 0. The missing information is on the reference side, not the candidate side.

## E. Killed

All three inventions and all 27 derived scores (gate: ρ ≥ 0.30 and ≥ 2× top-decile enrichment). Also excluded before testing as renamings: bootstrapped-parameter QBC (a parameter-uncertainty version of A/C, monotone in M3's latent variance), expected gradient length (a smooth version of A's |Δp|_exp), conformal nonconformity of the candidate (a monotone function of p on the revealed calibration set).

## F. Surviving invention

None.

## G. The information-theoretic missing variable

By §0, V(x, y_x) = −|R|⁻¹ Σ_{u ∈ F_{y_x}(x)} e_u. The flipped sets F_y(x) are label-blind computable (Invention A), the model locates the flippable references well (margin AUROC 0.86–0.93 for its own errors), and the model's posterior is unbiased about their sign (mean y − p = −0.014 at 0.3 < p < 0.7). Hence every label-blind observable is, in expectation, *even* in the signs {e_u} of the flippable references, while V is *odd* in them. The missing variable is the **signed correctness of the current decisions at the uncertain unqueried rows** — equivalently, the labels of the other near-boundary points — and in 69% of the valuable queries the candidate's own label is not even the surprise; the reference signs are. No function of (inputs, revealed labels, revealed-label models, pool geometry) is informative about those signs beyond π_u itself, because the only realised errors available (LOO on 16–40 revealed rows) do not map onto them (AUROC 0.62–0.67 vs 0.86–0.93 for margin). This is not a proof of impossibility for all conceivable observables; it is a proof that the observable would have to carry label information about unqueried rows.

## H. What additional simulator output or metadata would make oracle-value prediction possible

1. **Any cheap proxy label for unqueried rows** — under the "active manual annotation" cost regime, the already-computed simulator outputs of all pool rows are free: the max-depth separator classifies the manual label at 99.75% on the old pool, so the signed field e_u becomes observable for every row and the oracle's +0.095 is trivially attainable (one or two labels to calibrate the depth threshold). This changes the cost claim from "fewer simulations" to "fewer manual labels" and must be registered as such; under the thesis's simulator-cost regime it is unavailable by definition.
2. **A low-fidelity or partial simulation** at pool rows (coarse resolution, shorter track) giving a noisy label proxy at a fraction of the cost — multi-fidelity active classification (Cutforth et al. 2025-type) would then have the reference-sign information the single-fidelity setting lacks.
3. **Per-frame/onset metadata of already-revealed rows** (first-KH time, episode length, depth trajectory) does not help: it informs the *revealed* rows' labels, which are known; it cannot inform unqueried signs.
4. **Larger revealed sets**: the LOO error map might become informative once realised errors are dense (n ≫ 100), but by then the label-blind curve has reached its plateau (RESEARCH_DIAGNOSIS §2), so the regime where it could matter has no headroom.
5. **Campaign/configuration identity of new rows** (metadata): informative only if the new pool mixes campaigns; the exception structure is campaign-level (EXCEPTION_CLUSTERING_AUDIT), so a campaign-aware prior on E[e_u] could tilt the sign for rows of a campaign already seen to be under-predicted — a single-campaign new pool offers nothing of the kind.

## I. Does anything here alter the frozen external protocol?

No. No valuation survived; no arm, endpoint, gate or success rule changes. Two consequences are recorded in the prediction study only: (i) P9 (oracle gain) stands as a selection-sensitivity measurement; (ii) a new descriptive prediction P10 may be added if the new pool retains depth extraction — "the max-depth separator classifies the supervisor's labels at ≥ 0.97 on the new pool" — which quantifies how much of the oracle's headroom the annotation-cost regime would make attainable. It is a statement about the cost regime, not about the acquisition arms, and it uses no label until the prediction study is run after unblinding.
