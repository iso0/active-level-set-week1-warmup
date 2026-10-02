# POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE

# Research interpretation and targeted novelty assessment

This work began only after the frozen confirmatory STOP report was closed and committed at `f83b0c17a24339ed8c09d507473de0f4e5394a5a`. It does not reopen that experiment. Inputs are the already authorized 136 included outcomes saved in held-out predictions, the input manifest and the original 100 frozen split assignments. No new seed, model, acquisition arm, cutoff, budget, exclusion, q20/q30 definition or target was introduced. No withheld outcome or sealed oracle was accessed in this analysis.

## Finding 1: initial class discovery is a separate feasibility condition

**Observation.** Every one of the 100 training pools contains both classes (7–12 non-Keyhole cases), but three of their fixed B16 designs miss the non-Keyhole class entirely. The other 97 contain both classes. This is a complete enumeration of the originally assigned designs, not a search for acceptable replacements.

| Frozen split | Training non-Keyhole / Keyhole | B16 non-Keyhole / Keyhole | Meaning |
|---|---:|---:|---|
| external__r003_f04 | 8 / 101 | 0 / 16 | Observed fatal STOP in the locked run |
| external__r009_f05 | 7 / 102 | 0 / 16 | Post-hoc startup certificate; no model execution |
| external__r019_f04 | 8 / 101 | 0 / 16 | Post-hoc startup certificate; no model execution |

The B16 non-Keyhole-count distribution is 0:3, 1:17, 2:38, 3:27, 4:12, 5:3; median 2. These are overlapping partitions of the same campaign. Neither 3/100 nor 97/100 is an estimate from 100 independent external datasets.

**Interpretation.** The pre-label B80 feasibility gate correctly established enough available training points. It could not guarantee class discovery within a label-blind B16 start. The frozen experiment required every planned fold to be executable; high average startup coverage was insufficient for that contract. M3 was the first arm attempted at the failing split, so the observed STOP is not evidence of an incumbent-specific weakness. By the frozen starting rule, Candidate A uses the same 16, and Candidate B can extend its early 8 only through the same 16 until both classes appear. A single-class full 16 therefore cannot satisfy any of the three startup contracts. This last statement is a rule-based implication, not an additional model run.

**Alternative explanation and countercheck.** It would be misleading to conclude that geometric coverage is generally worse than random. For a uniformly sampled 16 without replacement from each fixed training pool, the exact one-class probability is `(C(n0,16)+C(n1,16))/C(N,16)`. The sum across the 100 pools is **20.805190** expected one-class designs, compared descriptively with 3 actual frozen maximin failures. Linearity of expectation does not require independent pools. This comparison is not a new experimental arm, a significance test, a probability that the whole experiment fails, or evidence about downstream accuracy/acquisition efficiency. It indicates that the observed maximin schedule has relatively good class capture against this analytic reference while still lacking the all-fold guarantee required here.

**Confidence.** High for the finite-cohort startup facts and exact failure mechanism; limited for generalization beyond this campaign. The same observed labels produced the imbalance summary and the diagnostic. Bug withholding changed the input distribution, but its causal contribution to class imbalance cannot be identified without the withheld outcomes, which remain unexamined.

**Publication relevance.** This is a useful thesis result about experimental validity and external operational robustness. It is not evidence that Candidate B generalizes poorly in accuracy, nor by itself a new active-learning principle.

## Finding 2: the physics coordinate has a directional association but no perfect scalar separation

The included non-Keyhole group has VX median 0.956925 m/s versus 0.450605 for Keyhole, and `log h` median 20.993218 versus 21.414695. This is consistent with the direction of the frozen energy-related trend, but it is descriptive and selected after seeing outcomes. The 12 non-Keyhole observations are a small subgroup.

The non-Keyhole `log h` range is [20.786813, 21.706142]; the Keyhole range is [20.733458, 22.040425]. Their overlap includes Keyhole observations below some non-Keyhole observations in `log h`, so a deterministic increasing threshold in this scalar cannot perfectly reproduce the observed included labels. No threshold was optimized or tested. This observation is compatible with retaining a discrepancy component or other sources of variation, but does not establish M3's comparative predictive advantage.

Alternative explanations include other input coordinates, stochastic or annotation variation, and the any-genuine-Keyhole-frame target. This experiment does not distinguish them. In particular, the expanded ST range is not by itself evidence that ST caused the missed class, changed a learned ARD scale, or explains the startup failures. No calibration, ARD, residual or partial-trajectory performance screen was performed.

Confidence is high in the sample summaries and scalar non-separability, low in any causal or transferable mechanism claim. Publication relevance is conditional on a future matched-model comparison and independent replication; this is presently a supporting observation, not a novel result.

## Targeted literature check

The broad mechanism is already recognized. [Sener and Savarese, *Active Learning for Convolutional Neural Networks: A Core-Set Approach* (ICLR 2018)](https://arxiv.org/abs/1708.00489) studies geometric coverage in a learned representation. That supports a conceptual coverage rationale, not an identity with our raw-input maximin initializer or a guarantee of every class in B16.

[Barata et al., *Active Learning for Imbalanced Data Under Cold Start* (ICAIF 2021)](https://arxiv.org/abs/2107.07724) explicitly treats the warm-up period in which supervised active learning has too few labels or only one observed class. Its proposed unsupervised/outlier stage is studied in streaming fraud data, not this finite 4D physics pool. It establishes relevant precedent, not a validated remedy here.

A third closely related primary study, [Yu et al., *Active Learning From Imbalanced Data: A Solution of Online Weighted Extreme Learning Machine* (2019)](https://pubmed.ncbi.nlm.nih.gov/30137013/), uses clustering-based initialization in an ELM setting. It further limits any claim that class-aware startup concerns are new. This was a targeted three-paper check, not an exhaustive novelty review. **No novelty claim is established.**

## Ranked publication opportunities

1. **External robustness of an entire acquisition protocol, including startup.** The defensible question is when a previously frozen policy becomes operationally unevaluable under a shifted finite campaign, before its nominal acquisition comparison can be completed. Available evidence is the independently delivered campaign, pre-label freeze, preserved STOP and exact 100-start audit. Missing evidence is systematic replication across campaigns and a prospectively specified startup policy that charges all discovery queries and handles one-class observations. The smallest next experiment would compare a small, predeclared set of startup feasibility rules on the now-open cohort as development only, without an acquisition search. Any rule selected or evaluated after this diagnosis needs a future independent campaign for external confirmation. Current strength: solid thesis validity lesson; a workshop case study would need broader mechanistic evidence; not a standalone stronger-paper claim.

2. **Where a physics trend is informative but insufficient under a changed input domain.** The scalar-range overlap and median direction motivate this question; they do not answer it. The smallest informative follow-up would be a matched-path comparison of the fixed trend alone against its frozen discrepancy model after a new startup protocol is explicitly specified. It would be post-hoc development on these 136. Independent confirmation would require new data. Current strength: a hypothesis for further work, weaker than opportunity 1.

## Recommended next step

Keep the frozen external result closed as incomplete and retain M3 as the prior incumbent. Discuss and preregister how future experiments will handle a one-class start and how every discovery query is charged. Any small feasibility study on these 136 must remain development; do not reseed or resume this sealed 20-repeat experiment and call it the original confirmation. Seek a future independent campaign for the next confirmatory test. No additional method was prototyped in this task.
