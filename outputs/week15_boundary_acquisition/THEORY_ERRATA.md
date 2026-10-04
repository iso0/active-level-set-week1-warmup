# Week 15 theory audit and errata (2026-10-04)

Independent re-audit of `outputs/week14_research_program/THEORY.md` (D1–D5, O1, I1, E1, E2, H1, L) and of
the discovery statements carried over from Week 13. Each item was re-derived; numerical checks are in
`src/tests/test_week15_theory_errata.py`.

| ID | Location | Problem | Correction | Status |
|---|---|---|---|---|
| E15-1 | Week 14 D1 | "The same holds for T_both" after the T_m formula; the formula C(n−t,K)/C(n,K) is not the law of T_both. | P(T_both > 0) = 1; P(T_both > t) = [C(K,t) + C(n−K,t)]/C(n,t) for t ≥ 1; E[T_both] = (n+1)/(K+1) + (n+1)/(n−K+1) − 1. Proof for adaptive rules via the two ξ-determined sequences σ⁰, σ¹ (disjoint events for t ≥ 1). | Corrected in place, marked |
| E15-2 | Week 14 D3 numerical comparison | Expected front size for n = 108, k = 3 stated as ≈ 11. | H₁₀₈⁽²⁾ = 14.67. | Corrected |
| E15-3 | Week 14 D4 | Tightness "all minority cases tied in rank". | Tight iff minority cases are consecutive in the score order; first relation is an equality. | Corrected |
| E15-4 | Week 14 O1a | Implied set for positive-exponent log-linear laws stated to *equal* the dominance closure of convex hulls. | It *contains* that closure; exact characterization is two LP feasibility checks per point. | Corrected |
| E15-5 | Week 13 Prop. 6 | E[T_both] = Σ_{b≥0}[C(n0,b)+C(n1,b)]/C(N,b) includes a b = 0 term equal to 2. | b = 0 term is 1 (formula valid for b ≥ 1). Week 13 code already did this; Week 13 file not edited (historical). | Erratum recorded here |

Re-checked without finding errors: D2 (both directions of the "iff", the packing lower bound
E[T] ≥ (M+1)/2 and M_{2r} ≥ N(2r)), D3 (minimal elements, singleton lower-bound labellings, Bentley
formula — verified numerically), D5 (factor J also for T_both), O1, I1 (exact under monotone labels;
under violations it is a statement about domination only), E1 (sign analysis including the
Pareto-dominance case), E2 part 1 (ordered-pair kernel counts each cut edge once; requires a predictor
independent of the evaluation sample) and the flat-interface heuristic of part 2, H1 (|L₁∖L₂| ≤
min(b, n−b), swap chain of replace-one steps).

Consequences for Week 14 conclusions: none of the empirical results used the erroneous T_both formula
(Week 13/14 code computed T_both by simulation or with the correct hypergeometric sum); the qualitative
D1 conclusion (no rule beats random under the exchangeable null) is unaffected.
