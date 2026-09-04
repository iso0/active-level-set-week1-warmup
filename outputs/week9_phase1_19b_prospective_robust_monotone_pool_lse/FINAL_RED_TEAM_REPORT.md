# Final red-team report

1. **Does monotonicity reduce simulator queries prospectively?** It reaches full structural coverage with 86.35 mean true P3 queries, but statistically supported BA-threshold label saving is absent: **LABEL_SAVING_NOT_SUPPORTED**.
2. **Is any gain merely easy far-from-boundary inference?** There is no primary gain. P3 loses 0.008525 AULC to P0; easy structural coverage does not compensate for changed querying and implication errors.
3. **Does full-pool improvement coexist with no q20 improvement?** No full-pool improvement exists, and q20 also worsens by -0.0213 AULC.
4. **How many inferred labels are wrong?** P3 has 2.45 mean wrong inferred labels at B120, 0.7689% of inferred labels.
5. **Are errors KH- or C-concentrated?** They lean toward missed KH: 1.80 KH-as-C versus 0.65 C-as-KH per repeat.
6. **Do the three violations explain the mistakes?** Yes descriptively: P3 has 2.45 unique incorrectly inferred violation targets, matching its 2.45 final wrong inferred labels on average. This is finite-pool accounting, not causal proof.
7. **Can removing inferred points hide a boundary region?** It can. The dedicated q20 result is worse by -0.0213. The association is consistent with lost boundary opportunities but is not causal identification.
8. **Does poset bisection beat ordinary margin?** No. P2-P0 is -0.013237, CI [-0.017733,-0.008987].
9. **Does expected gain beat pure poset bisection?** Descriptively P3 exceeds P2 by +0.004712 AULC, but this contrast was not a primary inferential test and P3 still loses to P0.
10. **Does the M3-monotone hybrid beat canonical M3 Margin?** No: P3-P0=-0.008525, CI [-0.011908,-0.005265], Holm p=0.
11. **Is the result robust on main configuration?** Yes in direction: main-364 P3-P0=-0.011109, CI [-0.014682,-0.007587].
12. **Are label-saving CIs supported?** No. BA 0.95: P0-P3=-1.80 queries, paired N=20, CI [-4.35,+0.50]; BA 0.97: P0-P3=-3.20 queries, paired N=20, CI [-6.55,-0.05]; BA 0.98: P0-P3=+3.00 queries, paired N=11, CI [+1.00,+4.91]. The only positive BA-0.98 saving uses 11 paired attainments, below 14/20.
13. **Is propagation safe enough to recommend?** It passes the frozen <=1% structural safety gate, but should not replace P0 because it harms the primary recovery curve and misses more KH than C.
14. **What is the contribution's domain?** Strictly prospective finite-pool LSE on the frozen SPH design; it is not continuous-domain or universal physical monotonicity.
15. **Narrowest defensible claim:** Near-monotone implications can resolve most of this finite pool with few true queries and sub-1% inference error, but hard candidate removal/expected-gain querying significantly reduces balanced-accuracy AULC relative to canonical M3 margin and does not establish label saving at frozen BA thresholds.

Leakage audit: acquisition receives features, M3 probabilities, queried-label-derived state, and dominance geometry—but no unrevealed truth or q20/q30/B1. The pre-truth event table was hashed before target truth was joined. Inferred labels never enter M3. Holm covers all three monotone-vs-P0 tests. No rescue arm or tuning was added.

Final decisions: **MONOTONE_POOL_HARM**, **MONOTONE_PROPAGATION_SAFE_ENOUGH**, **LABEL_SAVING_NOT_SUPPORTED**.
