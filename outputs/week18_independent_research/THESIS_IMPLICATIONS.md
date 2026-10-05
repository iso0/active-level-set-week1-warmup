# What Week 18 changes in the thesis

Evidence labels as in CLAIM_LEDGER.md. Nothing here changes a frozen earlier verdict. Where an earlier conclusion
is re-framed, it is marked as a re-reading or an erratum.

## 1. The headline result changes from "no improvement over G3 + margin" to a scoped improvement
- **New main empirical claim (SPLIT-CONFIRMATION + SEMI-SYNTHETIC).** When each paid simulation reports its
  continuous output (max melt-pool depth), learning the level set {depth ≥ u} of that output with a depth GP and
  straddle acquisition (E1) needs far fewer simulations than the binary G3 + margin endpoint. On the confirmation
  block it reached G3's B80 accuracy after 30 instead of 88 runs (R3_OLD), with +0.029 BA AULC [0.010, 0.047]. Fresh
  digital-twin seeds gave +0.08 NSD AULC. The method itself is Week 7's formulation. What is new is a pre-registered
  confirmation on the redesigned benchmark, a queries-to-target endpoint, the mechanism (§3), and stated scope limits.
- **Scope (state it in the abstract and conclusion).** The result holds only where every run reports depth. That is
  OLD-type data in this repository: the NEW runs are labels-only here (their monitors exist upstream, owner decision D1).
  With partial depth, the depth GP is worse than G3 on POOLED (DEVELOPMENT −0.037). The historical q20 endpoint does
  not improve (R3_OLD −0.003 n.s., R2rev −0.024).
- **For binary-only data the endpoint stays G3 + margin.** Week 18 found no binary model or acquisition rule that
  clears its kill criteria on the real DEV tasks (portfolio results in ATTEMPT_LEDGER.md).

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
1. Decide D1: with the NEW monitors (depth for the 136 NEW runs), E1 can be tested on NEW and POOLED. The
   remaining confirmation blocks C2/C3 are unused and available for exactly that test.
2. Write the depth-level-set result as the main positive contribution, with its scope and the q20 caveat.
3. Keep G3 + margin as the binary-label baseline and recommendation.
