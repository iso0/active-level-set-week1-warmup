# Final results narrative

## 1. From synthetic active level-set benchmarks to real data

The synthetic program established that acquisition rankings are geometry- and metric-dependent. At budget 80, uncertainty-repulsion was the best q20 method on thresholded Branin, Bernoulli-SUR-k25 was best on Hartmann4, and entropy/margin was best on the optional three-seed Ackley4 diagnostic. The source-backed comparison is preserved in `synthetic_to_real_summary.csv`. Consequently, the thesis does not claim a universal acquisition winner; it treats direct pointwise boundary methods as strong baselines and evaluates them with boundary-specific metrics.

## 2. Real-data audit and physical-response reconstruction

The final common population contains 405 simulations: 73 manually labelled Keyhole and 332 non-Keyhole. All Week 8 results reuse the exact saved population and Phase 6/7 split hashes. No source label, target, physical monitor, or simulator output was changed.

## 3. Predictability of physical responses

Earlier response-modelling phases showed that maximum penetration depth is a strong continuous response and a useful classifier-side comparator. Week 8 does not refit those models; it carries forward the saved Phase 6 Max-Depth GPR and its exact query trajectory.

## 4. Physical responses and manual Keyhole morphology

Manual `has_keyhole` labels encode the presence of cavity-like Keyhole morphology in at least one valid saved frame. Continuous responses are associated with that annotation but do not redefine it. G3 achieved perfect new-data ranking and leave-one-out separation, while its transfer performance and threshold shifted by partition; maximum depth was more robust as a scalar companion.

## 5. Why G3 was not promoted to a universal boundary definition

Perfect separation within new-data is not a universal physical threshold. Phase 5.5 retained a worst predeclared G3 transfer balanced accuracy of 0.8125 and explicitly classified the threshold as partition-sensitive. The thesis therefore preserves manual `has_keyhole` ground truth and avoids a universal G3 cutoff claim.

## 6. Binary versus Max-Depth active learning

Across the common 16–80 budget grid, Binary has B1-q20 accuracy AULC 0.8138, Random 0.7711, and Max-Depth 0.7947. Max-Depth retains the strongest global balanced-accuracy AULC (0.9432 versus Binary 0.9171), making it scientifically useful as a secondary comparator rather than the primary boundary acquisition.

## 7. Hybrid negative result

Phase 7 tested two fixed ways to inject queried maximum-depth side information: a binary gate and equal-rank fusion. Neither met the preregistered robust success rule. This supports the narrow conclusion that these two Hybrids did not improve Binary; it does not prove that every conceivable hybrid is ineffective.

## 8. Final sample-efficiency result

At 40 total queries, Binary achieves 81.2% mean B1-q20 empirical near-boundary accuracy, compared with 76.8% for Random. At budget 80 Binary retains 82.4%. These are held-out classification accuracies on empirical boundary-like subsets, not probabilities that the continuous physical boundary lies at a known location.

## 9. Concrete simulator-query savings

Binary's mean 79.7% B1-q20 accuracy at budget 30 is first matched by the observed Random mean curve at about 70 queries. This corresponds to approximately 40 saved simulator calls and a 2.33x query equivalent. Binary's budget-40 performance is not matched by Random by budget 80, so only a strict >40 saving and >2.00x lower-bound statement is defensible; no value above 80 is extrapolated.

## 10. Final recommended strategy

The final primary strategy is a Binary Gaussian Process Classifier mapping `(P, VX, LS, ST)` to `P(Keyhole)`, with binary uncertainty-repulsion acquisition. `ST` is substrate temperature. Maximum depth remains a physical side variable and separate continuous comparator.

## 11. Limitations

No genuinely new simulator evaluation was run in Week 8. This is an offline retrospective active-learning benchmark. The 20 outer runs are four repeated five-fold splits of the same 405 simulations, not 20 independent physical campaigns. Saved GPC probabilities permit model-confidence diagnostics—for example, at budget 80, 60.0% of pooled B1-q20 predictions have at least 80% model confidence—but the probabilities were not post-hoc calibrated and do not quantify physical-boundary certainty. B1/B2/B3 depend on sampled points and are not the true continuous boundary. Associations are not causal.

## 12. What future prospective validation would require

A prospective study would freeze this method and its hyperparameters, start from a declared initial design, request genuinely new simulator evaluations sequentially, keep future outcomes unavailable until each query completes, and compare against a concurrently budget-matched random policy. That experiment was not available in Week 8 and is not implied by the present results.
