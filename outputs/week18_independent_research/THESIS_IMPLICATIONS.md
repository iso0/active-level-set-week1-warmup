# What Week 18 changes in the thesis

Evidence labels as in CLAIM_LEDGER.md. Nothing here changes a frozen earlier verdict. Where an earlier conclusion
is re-framed, it is marked as a re-reading or an erratum.

## 1. The headline result changes from "no improvement over G3 + margin" to a scoped, replicated-in-direction improvement
- **Main empirical claim (SPLIT-CONFIRMATION + SEMI-SYNTHETIC).** When each paid simulation reports its continuous
  output (max melt-pool depth) *and the regime label is a threshold of that output*, learning the level set
  {depth ≥ u} with a depth GP and straddle acquisition (E1) beats the binary G3 + margin endpoint:
  - BA AULC +0.021 (DEV), +0.029 [0.010, 0.047] (C1), +0.016 [0.013, 0.020] (C2) on R3_OLD; fresh twins +0.08 NSD AULC;
  - simulations to G3's B80 accuracy: −66% in C1 but only −12% in C2, so quote the range, not the C1 number alone;
  - the pre-registered size bar (+0.02) was met in C1 and missed in C2. State this explicitly.
  The method is Week 7's formulation. What is new is the pre-registered confirmation, the queries-to-target endpoint,
  the mechanism (§3) and the scope analysis.
- **Scope (abstract and conclusion).** OLD-type data only. After obtaining the NEW monitors (D1): on NEW the label is
  not a max-depth threshold (AUC 0.891; fast scans), and with depth for every run E1 ≈ G3 on POOLED (C2 +0.004) and is
  worse on NEW (C2 −0.022). The historical q20 endpoint does not improve (C2 R3_OLD −0.028).
- **For binary-only data the endpoint stays G3 + margin.** Week 18 found no binary model or acquisition rule that
  clears its kill criteria: log inputs, nested-start LT and an exploration mixture were all within ±0.011 BA AULC.
  At the end of the budget G3 + margin already equals its own full-pool ceiling (T18-2 check). For binary labels the
  frontier is explained, not moved.

## 2. Re-readings of earlier chapters
- **Week 7 (depth GPR, "HYBRID / NO CLEAR WINNER").** This is now superseded for BA and queries-to-target on full-depth
  tasks by the round-1 split-confirmation. q20 stays neutral-to-worse. Keep the Week 7 verdict as historical and cite
  Week 18 for the update.
- **Week 12–17 NEW results.** The NEW "exploration beats margin" exception is an interaction between ML-II and random
  designs, plus seed noise (POST-HOC, phase0/). It is not a rare-pocket effect that margin misses. NEW BA endpoints
  rest on ≈ 12 rare runs, and the real tasks do not even agree on a ranking of baselines (Kendall τ 0.00).
- **Week 17 held-out synthetic conclusions.** "M3 ≪ G3" holds on NEW but not on OLD/POOLED. Synthetic families,
  including Week 17's cells, do not validate as proxies for the real ranking (twins τ 0.22, Week 17 cells 0.16 with real
  tasks). Present the held-out synthetic results as robustness evidence, not as predictions of real performance.
- **OLD/NEW relation.** Pooling is legitimate for a flexible GP: the NEW offset adds +0.001 nats and labels agree in
  the overlap. Whether the 1-D log-h threshold difference (+0.17 [0.03, 0.29] overall) is a campaign shift or a
  region effect cannot be decided (overlap +0.01 [−0.14, 0.28]; erratum E18-3). Do not write "level shift" as a fact.
- **Week 16 (PEER, oracle headroom).** Replace "the remaining gap is model information" with the narrower
  attribution statement (erratum E18-4; Astra Round 3). Correct the two numerical statements (E18-5).

## 3. Theory chapter additions (THEORY_WEEK18.md)
- T18-4: information per query. A binary probit label carries Fisher information φ(m)²/(Φ(m)Φ(−m)) about the
  latent. That is 0.64 at the boundary and 0.015 at three noise units. An observed depth carries 1/σ² anywhere. This
  explains why the depth gain is concentrated at small budgets and in conduction-rich pools (confirmed shape), and
  why random refinement loses on large pools.
- T18-1: the 1-D censored-search result. Continuous outputs help 1-D localization only on fine pools, so the 4-D gain
  must come from information shared across the surface (prediction held).
- T18-3: binary source labels transfer ordering but cannot identify a threshold shift. This explains why the OLD prior
  raises NEW AUC much more than NEW BA. It agrees with Astra Round 3 P6.
- T18-2: finite-pool floor and saturation budget (known rates). It frames why acquisition differences shrink by B80
  on 108-run pools.
- Astra Round 3: cite it as the decision-theoretic audit of Week 16. Several statements were independently
  re-checked (THEORY_WEEK18.md, last section).

## 4. Integrity notes for the methods chapter
- Every GPC/GP fit records its fixed-point error. Week 18 added a fixed-point stopping rule for large-kernel Laplace
  fits and rewrote the censored-GP solver (analytic gradients, round-off-relative stopping).
- Digital-twin truths are frozen code (a solver change had silently moved one truth; caught by a reproduction check).
- Development and confirmation data were separated before method work. The freeze was pushed before round 1, and
  every attempt is in ATTEMPT_LEDGER.md (multiplicity visible).

## 5. What to do next (for the thesis)
1. Write the depth-level-set result as the main positive contribution: three blocks, direction stable, size
   C1 > C2, and the stated scope (label must be a threshold of the observed output). Draft:
   `thesis_draft/sec_depth_level_set.tex`.
2. Keep G3 + margin as the binary-label baseline and recommendation, including for NEW.
3. Treat the NEW depth–label disagreement as a physics/labelling finding: fast scans reach keyhole-like depths
   transiently without being labelled Keyhole. Candidate explanations to discuss: transient depth peaks, the
   frame-based label definition, end-of-domain effects.
4. C3 is the last unused block. Use it only for a new, separately justified candidate, for example a depth model with
   a scan-speed-dependent threshold developed on DEV. Its motivation would be post-hoc with respect to the NEW labels.
