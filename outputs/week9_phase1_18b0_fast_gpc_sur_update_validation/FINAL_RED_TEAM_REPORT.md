# Final red-team report

1. FAST ranking fidelity fails: median Spearman 0.481.
2. Posterior probabilities are close (median snapshot MAE 1.06e-05); ranking failure is not hidden by that fact.
3. Hypothetical Keyhole error is larger than Conduction.
4–6. Candidate-regime table includes boundary, variance, FAST-top and controls; no outcome-based selection occurred.
7. Fidelity deteriorates notably at B60; late median is 0.475.
8. Bound-hit association is descriptive and not a physical interpretation.
9. Physics refit is a major source of full-pipeline disagreement.
10. Kernel refit is comparatively smaller.
11. Fixed-hyperparameter exact Laplace is the cleaner literature one-step update contract.
12. FAST preserves exact top-1 only 44.0%.
13. FAST top-1 has median exact rank 2.0, but aggregate top-k criteria still fail.
14. FAST is faster, but speed cannot rescue invalid rankings.
15. No guarded fallback passed the partial gate; no corrected variant was introduced.
16. A prospective FAST SUR-vs-Margin benchmark is not justified.
