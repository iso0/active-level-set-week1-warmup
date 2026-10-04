# Week 14 counterexamples and failure modes

Each entry: claim it refutes, construction, evidence (exact / synthetic / real), consequence.

### C1 — q20 accuracy prefers erasing the boundary to displacing it toward the minority
*Refutes:* "a higher q20 accuracy means a better boundary."
*Construction:* correct-shape predictors with displaced level f + δ (Week 13 displaced family, NEW-like,
σ = 1): δ = +1.5 (boundary essentially erased, NSD 0.006) scores q20 accuracy 0.589; δ = −1.5 (boundary
displaced into the minority, NSD 0.128) scores 0.550. BEF1 0.004 vs 0.306. CONTROLLED SYNTHETIC.
*Consequence:* q20 accuracy is not monotone in boundary error under imbalance (Theorem E1 explains why).

### C2 — band and cut-edge recall are blind to spurious regions far from the boundary
*Construction:* predictor equal to truth except a spurious class-0 island away from Γ (Study 3, all
densities, d = 2, 4): q20 accuracy = 1.000 and BER = 1.000 for every island size; BEF1 0.80–0.99 and NSD
0.77–0.93 detect it. CONTROLLED SYNTHETIC. *Consequence:* recall-type boundary metrics must be paired with
a precision term (BEF1) or a global term.

### C3 — every finite-pool boundary metric is density-weighted (rank reversal by sampling alone)
*Construction:* two predictors with identical geometry (displacement on the left vs right half of Γ) scored
on pools concentrated near the left or right half (Study 3): Gabriel BER 0.27 vs 0.93 under dense-left
and the reverse under dense-right; q20 accuracy, BA and BEF1 reverse too; true NSD/ASSD are equal.
CONTROLLED SYNTHETIC; mechanism Theorem E2 (p² weighting for r-graphs, p^{(d−1)/d} for kNN). Length weighting
reduces but does not remove the effect (Study 3b, C3 confirmatory). *Consequence:* boundary scores from
two campaigns with different densities (OLD vs NEW) are not comparable as boundary quality.

### C4 — under label noise the observed cut set is not the boundary
*Construction:* Bayes boundary scored against noisy evaluation labels (Week 13 displaced family, NEW-like,
σ = 1): BER = 0.345, BEF1 = 0.401 at δ = 0. CONTROLLED SYNTHETIC. *Consequence:* absolute values of finite
boundary metrics are attenuated; only comparisons on the same pool are interpretable.

### C5 — farthest-first is not a safe default for rare discovery
*Construction:* rare islands centred at density-proportional random points (Study 1 `islands`, held-out
`twoislands_skew`): mean T_both MAXI 18.8 vs RAND 14.4 (development), 16.9 vs 14.6 (held-out; 22.3/17.9 vs
14.8 at d = 4). Farthest-first starts on the convex-hull periphery. CONTROLLED SYNTHETIC; consistent with
the coreset "outlier" effect (Yehuda et al. 2022). *Consequence:* the Week 11 B16 maximin contract worked on
OLD because the rare class (Keyhole) sat at an extreme of the physics order, not because coverage is
generally safe (Theorem D2).

### C6 — acquisition rules need not become indistinguishable as b → n
*Construction:* 1-NN learner, a single isolated minority pool case controlling a test region of mass α:
at b = n − 1 the rule that omits it and the rule that omits a majority case differ by α in minority recall
(α ∈ (0, 1]). EXACT. Empirically, replace-one sensitivity bounds (Prop. H1) were vacuous for GPCs
(Study 4: mean-swap bound 0.03–0.47 and max-swap bound > 1 versus observed gaps ≤ 0.12).
*Consequence:* "late-budget indistinguishability" requires a sensitivity bound; it is not automatic.

### C7 — the full-pool model is not a ceiling for acquisition
*Construction:* greedy oracle that maximizes evaluation-pool BA (Study 4): BA 0.95 vs full-pool 0.86
(NEW-like), 0.97 vs 0.93 (OLD-like). CONTROLLED SYNTHETIC. *Consequence:* the Week 13 "0.014 window" is a
model-specific reference gap, not an upper bound on achievable gain.

### C8 — optimizing the finite-pool metric does not improve the true boundary
*Construction:* the same evaluation-BA oracle has *lower* dense-truth NSD than margin (BAL 0.86 vs 0.92;
OLD 0.80 vs 0.86; NEW 0.81 vs 0.82), while an oracle that maximizes the true NSD exceeds margin by
+0.05 / +0.07 / +0.10 NSD (Study 4b). CONTROLLED SYNTHETIC. *Consequence:* acquisition headroom on the
estimand exists but is not identifiable from finite-pool metrics with noisy labels.

### C9 — no unique additive attribution of discovery, model and acquisition effects
*Construction:* any 2×2 design with interaction, e.g. AULC(M3, bad start) = 0.60, (M3, good start) = 0.61,
(G3, bad) = 0.62, (G3, good) = 0.70: the discovery effect is 0.01 under M3 and 0.08 under G3, so sequential
attributions disagree (Shapley splits the interaction). EXACT arithmetic. *Consequence:* report a
reference ledger (THEORY Part L), not a decomposition.

### C10 — strict monotone GP priors can hurt
*Construction:* monotone GPC with probit virtual derivative observations and small scale (Study 2
development): BA 0.693 vs 0.799 for the unconstrained GP (twoRegime target80), with the same bias when
labels are noise-free (0.842 vs 0.860). Mechanism: a small probit scale imposes a minimum slope, wrong where
the latent saturates. CONTROLLED SYNTHETIC. *Consequence:* "physics as order" must be encoded as a
non-strict, transparent constraint (closure) rather than a strict derivative prior.

### C11 — monotone closure inherits order violations
*Construction:* when labels depend on ST but the order ignores ST (stShift development), closure-implied
labels are wrong for comparable pairs with opposite ST effects; BA still rose but NSD fell in the transfer
cell (0.885 → 0.831 for GRC vs GR). CONTROLLED SYNTHETIC. *Consequence:* the order must be validated on
source data (as on OLD: 3 violations in 22,050 pairs) and implied labels should be reported with their
coverage and error counts.
