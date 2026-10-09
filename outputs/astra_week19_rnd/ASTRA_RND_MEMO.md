# Week 19: independent R&D decision

**Decision: run one bounded DEV test of the active-window target and E1's threshold rule before investing in a temporal GP.** Time-aware depth is a plausible improvement in the measured response, not yet an explanation of Keyhole morphology or a better boundary estimator. A scalar target can rank simulations well while discarding the short events that define `has_keyhole`.

**POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE.** Prepared 10 October 2026 from branch `week19-temporal-audit`, commit `f3206f292f48db79d9c4af496e7c7aed40c0ce62`. Read the handoff before the report; independently checked compact tables, relevant extraction/learning code, and Figure 6. No model fitting, simulator runs, canonical relabelling, additional exclusions, C3 execution, commit or publication was performed. New arithmetic is recorded in `ASTRA_REVIEW_CHECKS.json`; the proposed operations are in `OPUS_IMPLEMENTATION_REQUEST.md`.

## 1. What the evidence establishes

The populations are OLD 405/73 positive, October NEW 136/124 positive, and POOLED 541/197 positive. OLD's partition named `new-data` is not October NEW. The 49 Bug-withheld runs remain outside this work. `has_keyhole` means at least one **observed** K frame, not latent Keyhole at any time during an unobserved complete scan. Opus reproduced that label for all 541 eligible runs and mapped all 140,594 frames through iteration to monitor time. These are audit findings, not an independent repetition of raw-file recovery. [Handoff][handoff]; [report §§1–2][report].

**The window improvement survives a fair denominator check, but fixes only one fixed-threshold error on the common NEW cohort.** Independent arithmetic from [depth definitions][depth] and [separability][sep]:

| Observed NEW score | Evaluated runs (K / non-K) | AUC | BA at OLD reference 110.9641 µm | FP / FN |
|---|---:|---:|---:|---:|
| Whole-record maximum | 136 (124 / 12) | .89113 | .70430 | 7 / 1 |
| Whole maximum, same available cases as A | 135 (124 / 11) | .88930 | .72324 | 6 / 1 |
| A: observed active-window maximum | 135 (124 / 11) | .97801 | .76870 | 5 / 1 |

The missing case is the bounds/time-mismatched `H-e7dbd8e5ce`; it stays in the benchmark. A's own OLD-fitted threshold is 110.5164 µm, at which its NEW BA is only .72324: the late negative's A=110.755 µm again exceeds the threshold. Thus higher AUC does not establish threshold transfer.

**A's impressive same-population oracle BA hides a damaging subgroup trade-off.** The table's 142.2322 µm oracle threshold produces TP=114, FN=10, TN=11, FP=0 on the 135 available cases. Nine of those ten false negatives belong to NEW's ten positives with `0 < K/(F+C+K) < .10`: short-K sensitivity is **1/10**, despite BA=.95968. The remaining false negative is the post-cutoff positive `H-349225d53c`. This is a descriptive audit of the selected oracle threshold, not a held-out predictor or a proof that every alternative threshold fails equally. [Source values][depth]; [oracle definition][sep].

**Window, startup and unresolved morphology disagreements coexist.** `H-f4fc937e86` has sustained post-exit elevation, not an isolated startup spike. `H-29cf03a279` peaks within the pipeline active interior but before the first C frame, during manually labelled Forming; these descriptions are compatible. Four other negatives reach elevated depth after C starts, including `H-b2eec677b1` with G3 persistent depth 111.9 µm. The matched fast-scan negative has a higher maximum than its short-K positive counterpart. Conversely, `H-349225d53c` has K frames only after the 90% cutoff, around and after the derived exit. Melt bounds do not settle which annotations correspond to a vapour cavity. H suffixes are display abbreviations; joins must use full simulation names. [Twelve-case table][negative]; [Figure 6][fig6].

**The dynamics are real observed sequences, but their mechanisms are unresolved.** There are 26 OLD/23 NEW instances of K followed only by C, and 13/9 simulations with observed C between K blocks. Fast K-to-C cases have short startup episodes; slow cases switch near the recording end while scanning remains incomplete. First K-to-C transitions are inside A in 30/31 OLD and 34/34 NEW cases, ruling out post-exit contamination as a universal explanation. Of 98 NEW positives with K ongoing at observation end, 65 end before 90% of derived exit. “Persistent Keyhole” and an input-space “sweet spot” are not established. [Report §§2–3][report].

**E1's threshold instability is an algorithmic lead, not a causal attribution.** The fold table has 13/32 NEW folds with the late negative in the training candidate pool and thresholds ≥200 µm, versus 0/8 with it held out; 76 budget checkpoints exceed 200 µm. The table maximum is **309.6191 µm**, slightly above the report's 309.3. Mean E1−G3 BA over budgets is −.09022 in 12 pulled folds with defined BA, versus +.00625 across the other 26 defined folds. That average is not AULC. The table records test membership, not acquisition time; inspected caches and their writer omit paid query order. Historical exposure and temporal precedence require a saved query ledger, not inference from membership alone. [Fold table][pull]; [audit code][analysis]; [cache writer][writer].

Historical DEV BA-AULC E1/G3/M3 values are OLD .9443/.9237/.9299, POOLED .9474/.9479/.9499 and NEW .6507/.6713/.6014. C2 preserves an OLD E1−G3 BA-AULC advantage (+.016) but has worse OLD q20 AULC (−.028); POOLED/NEW superiority is not established. These are prior complete-system comparisons, not results of the proposed matched-path pilot. [Checks C16][checks]; [C2 results][c2].

## 2. Ranked hypotheses and cheapest discriminating tests

Ranking reflects scientific value and identifiability with existing files.

| Rank / explanation | Supporting evidence | Contrary evidence or limit | Discriminating observation and cheapest useful test |
|---|---|---|---|
| **1. Observation-window and endpoint mismatch** explains some deep negatives and campaign disagreement. | The 312 µm negative is post-exit; a positive's K is post-cutoff; common-cohort AUC rises .889→.978. | Most first K→C switches are inside A; four post-C deep negatives remain. Derived exit is a convention, not measured laser-off. | Overlay configured scan position, SS frames, exact bounds and native images for the two opposite end cases. Recompute the two scalar targets on identical paid prefixes; separate threshold from regression effects. |
| **2. Startup state, morphology and annotation criteria are not reducible to penetration depth.** Explains K→C and deep non-K. | The manually forming `H-29cf03a279`; matched opposite-label traces; persistent post-C elevation. | The pair is near-matched, not identical; label disagreement may be correct morphology rather than annotation error. | Blind review of native front/side/top frames around the matched peaks and the persistent negative, then compare cavity shape with the preserved annotations. No relabelling in the benchmark. |
| **3. Incomplete observation and right censoring distort “stable,” “only C” and occupancy descriptions.** | 79/136 NEW and 167/405 OLD records end before 90% of exit; one NEW negative has only IE/F and mismatched bounds. | Fast K→C cases have hundreds of subsequent frames; censoring cannot erase those observed switches. | Report observed support and interval/censor flags beside each event and ratio. Compare only genuinely observed segments; do not extrapolate an unseen recovery or treat technical KEEP as complete scanning. |
| **4. Genuine cavity/flow instability versus annotation flicker causes alternation.** | C lies between K blocks in 22 simulations; some Figure 6 transitions accompany depth changes. Instability is physically plausible. | Depth oscillations and melt kinetic energy do not identify cavity collapse; brief labelled changes can occur without a resolved geometric change. | For the two representative alternating cases, compare native image brackets with unsmoothed depth/width/length on the exact clock. Require reproducible geometry changes across several switches; otherwise retain “mechanism unresolved.” |
| **5. Coverage and protocol differences make the OLD threshold look more universal than it is.** | Common fast region: only nine OLD cases, two negative; NEW has 13, eight negative. OLD partitions and NEW do not sample the same ranges. | Similar timing and frame spacing in spot-crossing units argue against a simple campaign-wide sampling-rate explanation. A bounding box of overlap is not dense conditional overlap. | Tabulate nearest-neighbour distances in all four inputs and existing settings/provenance; inspect matched cases without fitting a campaign effect. A causal campaign contrast or genuine sweet spot needs additional controlled evidence. |

Cunningham et al. directly distinguish the evolving vapour depression and melt-pool morphology; Zhao et al. observe a mechanism linking keyhole-tip instability to trapped pores. These support competing physical hypotheses, not diagnoses of these SPH runs. **Melt penetration, vapour-cavity depth and a trapped pore are different quantities. Melt kinetic energy is neither absorbed power nor absorbed laser energy.** [Cunningham et al., 2019, Figs. 1–3][cunningham]; [Zhao et al., 2020][zhao].

A perfect predictor of A would still not yield an exact increasing scalar threshold for the recorded any-K label: positive/negative depth order inversions remain. This disproves that particular threshold representation on these observations. It does **not** prove that all temporal features, an input-dependent decision rule, or every scalar score must fail. Nearly coincident opposite-label curves raise an identifiability question that requires morphology and annotation evidence before further modelling.

## 3. Three formulations, with their actual estimands

Let x=(P,VX,LS,ST), with LS the **radius**. Let dᵢ(t)=10⁶ max(0,−z_min,ᵢ(t)) µm on valid monitor rows; eᵢ=(min(XFᵢ,XLᵢ)+12 µm)/VXᵢ under the existing x=VX·t convention. Define Wᵢ as valid observed times at t≤min(T_record,ᵢ,0.9eᵢ). Startup remains included.

The canonical label is Yᵢ=1{at least one recorded frame is K}. Ioan's frame fraction is r_KC=N_K/(N_K+N_C), **undefined** at zero denominator; one OLD and one NEW case are undefined. A duration-weighted counterpart uses midpoint interval weights and reports covered time and gaps. Neither equals K/(F+C+K), full-scan occupancy, nor a collection of independent Bernoulli trials. Keep ≥5%/≥10% outcomes as separate target sensitivities.

| Formulation | Exact target and relation to Y | Required observations / validation | Scientific question |
|---|---|---|---|
| **1. Four-input simulation summaries — recommended first** | Aᵢ=max_{t∈Wᵢ}dᵢ(t); optionally separate r_KC, observed K-block count or bracketed switch time. L_A(u)={x:A(x)≥u} and L_r(α)={x:r_KC(x)≥α} are different level sets from {x:Y=1}. | One trajectory, time/iteration/bounds metadata; occupancy/switch targets additionally require annotations. Hold out whole simulations using existing DEV folds. Preserve unavailable targets without removing their simulations. | Does a specified observation window or persistence descriptor provide a more reliable target, and where does its relation to morphology fail? |
| **2. Functional response with a small basis** | zᵢ(s)=log(1+dᵢ(eᵢs)/(1 µm))=μ(s)+Σ_{r=1}³a_r(xᵢ)φ_r(s)+εᵢ(s), on observed s=t/eᵢ≤.9. Model coefficients over all four inputs. Derive maxima/occupancy of **depth exceedance** from posterior trajectories, not from the maximum of the posterior mean. These are not K probabilities without a validated bridge. | A common reference coordinate, a basis learned from training trajectories only, and an explicit mask/uncertainty for incomplete coefficient estimation. Fit basis/scalers/bridge within the revealed training data, never across held-out simulations. | Do curve shape and event timing add useful information beyond A, at modest cost? A rank-three reconstruction is a baseline, not a claim that all dynamics have rank three. |
| **3. Five-coordinate GP f(x,s)** | Same log-depth trajectory, with a separable input×time covariance below. Posterior functionals describe depth trajectories; binary morphology remains a separate target. | Whole simulations held out, native time support, common-grid/noise audit, training-only calibration. Irregular rows are possible but the simple Kronecker solver has additional conditions. | Is temporal covariance needed beyond the scalar and basis models, and does it preserve the short events relevant to Y? |

**Cost for every formulation:** one paid query purchases one simulation/trajectory and its permitted outputs. Fifty time rows do not cost fifty independent simulator queries and do not create fifty independent validation units. Annotation effort and computation are recorded separately. Geometry, TE and recording failures must remain in provenance: A is an **observed-window** endpoint, not automatically the full physical active-window maximum. Differing settings can undermine a universal four-input map; do not silently omit ST or insert new predictor coordinates. A trajectory model's pre-query class prediction must use a horizon known from scheduled settings, H_plan=min(TE,0.9e), not the eventual test recording end. Actual test masks can restrict curve-error scoring only. If a truncated observed A differs from the planned-horizon functional, those are different estimands; stop a claimed like-for-like comparison rather than exploit future support information.

These are offline input-to-response tasks. An online question would instead be Pr(K occurs in (t₀,t₀+h] | x, monitor history through t₀). It needs landmark evaluation on held-out simulations and no future maxima, future annotations or future recording-end alignment. Current evidence does not justify reopening the broader observable-to-unobservable project. First-C/K alignment remains legitimate for audit only.

## 4. Kernels, timing resolution and computational feasibility

For scalar E1-compatible regression use log A and the current four-dimensional ARD Matérn-3/2 kernel, with scalers fitted as in the pinned engine. If z_j are standardized log inputs, r_x²=Σ_{j=1}⁴[(z_j−z′_j)/ℓ_j]² and k_x=σ_f²(1+√3 r_x)exp(−√3 r_x). Retain a Gaussian nugget, the existing one-start optimization bounds, and separate latent from observation uncertainty. The prototype functional model can use independent coefficient GPs with this same family.

For the temporal candidate, use

\[
f(x,s)\sim GP(m(x,s),k_x(x,x')k_t(s,s')),\qquad
k_t(s,s')=(1+\sqrt3|s-s'|/\ell_t)e^{-\sqrt3|s-s'|/\ell_t}.
\]

This is four physical inputs **plus time**. Stationary separability forces the same temporal correlation scale across input settings; changing transition times, event-specific variance and curve warping may violate it. Check residuals and event errors by phase and VX. A single, justified gate extension is possible: k_x[g(s)g(s′)k_pre+(1−g(s))(1−g(s′))k_post]. A common g preserves input×time separability; an input-specific gate generally does not. Do not search changepoints against test annotations. Covariance changepoints are not automatically morphology transitions. Roberts et al. provide the time-series/covariance framework, including changepoints, rather than evidence that this dataset needs them. [Roberts et al., 2013, §§3b, 5c][roberts].

With n simulations observed at the same m time coordinates and independent common-variance Gaussian noise,

\[
K_y=K_x\otimes K_t+\sigma_n^2I,\quad
\lambda_{ab}(K_y)=\lambda_a(K_x)\lambda_b(K_t)+\sigma_n^2.
\]

An eigensolver can use these factors without building the full matrix. The four-dimensional x locations need not themselves form a lattice: the required grid is **simulation locations × common times**. For n=541,m=50 there are 27,050 observations, not 27,050 purchases; a single dense double matrix is about 5.85 GB. Factor storage is O(n²+m²+nm); eigendecomposition plus transforms costs O(n³+m³+n²m+nm²) per parameter evaluation. This is feasible in principle, not a runtime promise. [Saatçi, 2011, ch. 5][saatci].

The eigensolution is exact for the stated gridded Gaussian model. Variable support, missing rows, heteroscedastic noise, censoring and annotation likelihoods invalidate that simple formula. Masked Kronecker products can support other solvers, but require their own residual and likelihood checks. Interpolation does not restore genuinely missing observations and changes noise correlations. Never stretch every truncated recording to [0,1], fill unobserved tails, or discard cases to manufacture a complete grid. A generic dense GP implementation does not obtain these savings automatically.

**A quantified warning about 50 points.** I placed a label-blind phase grid s_j=0.9j/49, j=0…49, on each audited run, retaining only times between first valid observation and A's cutoff. Comparing with the existing K-run core/bracket table gives:

| Annotation-resolution diagnostic | OLD | NEW |
|---|---:|---:|
| K runs whose observed first-to-last-K interval intersects A | 116 | 136 |
| Those intervals containing no grid point | 40 | 11 |
| No grid point even in the clipped outer onset/offset bracket | 20 | 4 |
| Active-positive simulations with no hit in any K core / any outer bracket | 5 / 2 | 4 / 1 |

One additional NEW positive has no K core in A at all: that is window loss, not subsampling loss. These are geometric sampling diagnostics under Opus's episode definitions, including single-frame cores, not measured GP errors or proof of continuous-time K duration. Internal invalid monitor gaps could worsen fidelity. The check does not condemn every 50-point design; it shows that this explicit common-phase design is inadequate for preserving all observed events. [K-run intervals][kruns]; `ASTRA_REVIEW_CHECKS.json`.

## 5. Primary pilot, fallback and stopping decision

**Primary: a matched-path scalar target/threshold pilot on NEW only.** Use DEV repeats 1–2, their five frozen simulation-level folds, and B16/B40/B80. Generate one feature-only maximin order per training pool using the pinned routine and seed; every method receives identical revealed prefixes. Fit whole-depth E1, A-depth E1, and G3 on these prefixes: at most **90 fits**, with no acquisition-method comparison. All 136 cases remain eligible, including the record without A. Keep label/target availability explicit; an unavailable regression response consumes its paid query and is not fabricated.

The sole primary comparison is A-E1 minus whole-E1 **q20 accuracy at B40**. BA, specificity, Brier, AUC and sensitivity in the fixed ten-case short-K subgroup are safeguards/diagnostics; B16/B80 describe budget dependence. Preserve the existing evaluator-only q20 masks. Three checkpoints do not reproduce historical AULC, and q20 is an empirical boundary-proximity diagnostic, not a physical boundary ground truth.

Separately inspect observed-score threshold errors, logit slope/root stability, and predicted-score errors on the same cases. This distinguishes a changed response, threshold calibration and regression error. Fixing a threshold on unchanged predictions is an algorithmic counterfactual, not a physical intervention. Missing historical query logs should remain a stated limit, not trigger expensive trajectory reconstruction.

Provisional advance rule: mean Δq20(B40)≥.01 with a paired 95% lower bound above zero, no mean BA loss, and short-K sensitivity no more than .05 below either matched comparator. Report per-repeat results and a stratified **simulation-cluster** bootstrap carrying all predictions for each ID; its interval is conditional on these fits and two historical splits, not external uncertainty. An unusable two-class prefix makes that checkpoint unavailable; only the already fixed larger checkpoints may follow. Any unavailable B40 comparison prevents advancement. Stop on numerical failure, leakage or budget excess; no reseeding or result-driven repair. A promising but imprecise result stays inconclusive. These are proposed DEV decision rules, not amendments to the frozen external campaign.

Only a passed scalar gate and a passed representation-fidelity audit justify a later rank-three-basis versus separable-GP comparison on the same DEV simulations, at B40. The GP must improve meaningful held-out event/target fidelity beyond the cheap basis and preserve q20/short-K performance. A smoother curve or higher global R² alone does not justify it. Detailed gates and resource ceilings are in the implementation request.

**Fallback: the bounded eight-case morphology/observation review.** If scalar target changes do not help boundary performance, or time-grid/observation assumptions fail, stop predictive expansion and resolve which depth–label disagreements can actually be interpreted. A negative result here is useful; it does not require inventing another model.

Two focused extensions can change a decision: (i) inspect the conditioning of E1's root, log u=−a/b, since an almost-zero or nonpositive logistic slope can invalidate its assumed increasing mapping; (ii) check existing domain z-extent and bounds semantics against the 301–305 µm cluster before treating plateau variation as informative. Neither permits a new threshold/kernel search or a censoring model selected to rescue E1.

## 6. What to show Ioan on 15 October 2026

1. The two observed K→C forms, an alternating case and the matched opposite-label pair, with exact monitor clocks, frame brackets and observation-end markers. Native morphology review, if completed, should accompany the trace rather than be inferred from it.
2. The common-cohort .889→.978 ranking improvement alongside the much smaller fixed-threshold BA change and the four unresolved post-C negatives. Do not describe all deep negatives as startup artefacts.
3. The strongest useful negative finding already available: **the high-BA active-depth oracle misses nine of ten short-K positives.** Better depth prediction alone does not establish faithful recovery of the current label or sample-efficient boundary estimation.
4. If the bounded pilot is completed, show its prespecified matched-path q20 and short-event results, including failure or inconclusiveness. Otherwise show the design, not projected gains. K/(K+C) is an observed occupancy description with undefined/censored cases, not an automatic replacement label.

C3 remains unused and reserved. A later frozen C3 assessment could provide split-confirmation on already inspected simulations, never fresh external validation. No legacy Phase 4 figure is used here as evidence about October NEW.

[handoff]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/ASTRA_HANDOFF.md
[report]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/REPORT.md
[depth]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/depth_definitions.csv
[sep]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/separability.csv
[negative]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/new_negatives_12_cases.csv
[fig6]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/figures/fig6_representative_cases.png
[pull]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/oof_E1_threshold_pull_by_fold.csv
[analysis]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/src/week19_analysis.py#L402
[writer]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/src/week18_dev_arms.py#L45
[checks]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/CHECKS.csv
[c2]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week18_independent_research/round_2/ROUND_2_RESULTS.md
[kruns]: https://github.com/iso0/active-level-set-week1-warmup/blob/f3206f292f48db79d9c4af496e7c7aed40c0ce62/outputs/week19_temporal_regime_audit/tables/k_runs.csv
[cunningham]: https://doi.org/10.1126/science.aav4687
[zhao]: https://pubmed.ncbi.nlm.nih.gov/33243887/
[roberts]: https://www.robots.ox.ac.uk/~sjrob/Pubs/Phil.%20Trans.%20R.%20Soc.%20A-2013-Roberts-.pdf
[saatci]: https://mlg.eng.cam.ac.uk/pub/pdf/Saa11.pdf
