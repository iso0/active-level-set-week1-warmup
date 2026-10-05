# Week 18 theory track

Every result: statement · proof or counterexample · check · literature · status · falsifiable prediction run in
the benchmark. Code: `src/week18_theory.py`; tests `src/tests/test_week18_theory.py`.

## T18-1 Binary vs censored-continuous threshold localization (1-D finite pool)
**Setting.** Pool x₁ < … < x_N; increasing conduction branch c; label yᵢ = 1[c(xᵢ) ≥ u]; boundary index
k* = min{i : c(xᵢ) ≥ u} (k* = N + 1 if none). *Censored observation*: yᵢ always; c(xᵢ) only when yᵢ = 0
(a Keyhole run reveals only that the branch has crossed — the max-depth structure found in DATA_AUDIT §2).

**(a) Binary labels.** Every (adaptive, possibly randomized) algorithm that always identifies k* needs
⌈log₂(N + 1)⌉ queries on some input; bisection attains this. *Proof.* N + 1 outcomes, each query returns one
bit, so a decision tree of depth < log₂(N + 1) has fewer leaves than outcomes. **KNOWN** (binary search).

**(b) Censored, affine branch.** If c(x) = α + βx with unknown α, β > 0, two queries always suffice.
*Proof.* Query x₁, x₂. If either is Keyhole, k* ∈ {1, 2}. Otherwise both values are observed, which determines
α and β and hence k*. **PROVED** (elementary). Checked exactly for N ∈ {16, …, 4096}.

**(c) Censored, smooth branch.** For c with c′ > 0 and bounded curvature, the Keyhole side never returns a value,
so bracketing methods that rely on function values on both sides of the root (regula falsi / Illinois,
Dowell & Jarratt 1971) do not apply. One-sided extrapolation from conduction values (secant through the last two,
quadratic through the last three; bisection safeguard when the extrapolation leaves the bracket or stalls)
gives, on random smooth monotone branches (400 per N):

| N | bisection (mean / worst-case bound) | censored secant mean | censored quadratic mean |
|---:|---|---:|---:|
| 16 | 4.05 / 5 | 5.76 | 5.75 |
| 64 | 6.05 / 7 | 6.63 | 6.48 |
| 256 | 8.06 / 9 | 7.64 | 7.15 |
| 1024 | 10.04 / 11 | 9.43 | 7.98 |
| 4096 | 12.05 / 13 | 10.66 | 8.44 |

**NUMERICALLY CHECKED.** Continuous (censored) information helps 1-D localization only when the pool is fine
relative to the branch curvature (≈ 30% fewer queries at N = 4096, none at N ≤ 64); one-sided censoring removes
the superlinear convergence two-sided methods enjoy.

**Prediction P-T18-1 (to be tested in Phase 3, E2).** Our pools hold only a handful of points along any line
through the boundary, so a depth-aware learner cannot win by 1-D localization. If it wins on the 4-D tasks, the
gain must come from depth information shared across the boundary surface, and it should then appear already at
small budgets, mostly in tasks where conduction runs are plentiful (OLD-like, pooled); it should be small on
NEW-like pools (≈ 9% conduction runs).

## T18-2 Finite-pool floor and saturation budget (deterministic labels)
**Setting.** Pool $P_N=\{x_1,\dots,x_N\}$ i.i.d. with density $p$ on $[0,1]^d$, $0<p_{\min}\le p\le p_{\max}$;
labels $y=\mathbf 1[x\in S]$ with no noise; boundary-fragment class
$\mathcal G_{\alpha,L}=\{S=\{x: x_d>g(x_{1:d-1})\}: g\in\mathrm{H\ddot older}(\alpha,L)\}$; error
$\lambda(\hat S\triangle S)$ on the continuous domain (the population analogue of NSD / dense BA).

**(a) Floor (KNOWN).** Even with all $N$ pool labels,
$\inf_{\hat S}\sup_{\mathcal G_{\alpha,L}}\mathbb E\,\lambda(\hat S\triangle S)\asymp N^{-\alpha/(\alpha+d-1)}$
(noise-free boundary-fragment rate; Korostelev & Tsybakov 1993, Tsybakov 2004). Every learner that only sees
pool labels is limited by this floor; models differ only through how they interpolate between pool points.

**(b) Saturation budget (DERIVED from KNOWN rates).** With noise-free labels the active minimax rate after $n$
queries is $n^{-\alpha/(d-1)}$ (Castro & Nowak 2008, $\kappa=1$). Equating with the floor, an optimal active
learner reaches the pool floor after
$$n_{\rm sat}\asymp N^{(d-1)/(\alpha+d-1)}$$
queries, and no algorithm can reach it with fewer (adversary argument: $\asymp N^{(d-1)/(\alpha+d-1)}$ columns of
the boundary each contain a pool point whose label can be flipped by a bump that leaves every other pool label
unchanged, so each must be queried). For a single-index boundary $\{\varphi(x)>c\}$ with known $\varphi$,
$n_{\rm sat}=\lceil\log_2(N+1)\rceil$ (T18-1a).

| Pool $N$ | $\alpha=1$, $d=4$: $N^{3/4}$ | $\alpha=2$, $d=4$: $N^{3/5}$ | single index: $\log_2(N+1)$ |
|---:|---:|---:|---:|
| 108 (NEW-like) | 33 | 17 | 7 |
| 324 (OLD-like) | 76 | 32 | 9 |
| 433 (pooled) | 95 | 38 | 9 |

**Prediction P-T18-2.** (i) Learning curves of margin-type rules approach the full-pool ceiling at budgets of the
order of the table (between the $\alpha=2$ and $\alpha=1$ columns); (ii) on NEW-like pools (108) the curves are
saturated well before B80, so rules can only differ at small budgets; (iii) at $B_{\max}$ a better model can add
at most the difference of full-pool ceilings, and a better acquisition rule at most the gap between the arm's
$B_{\max}$ value and its own ceiling. Test: `src/week18_headroom.py` (full-pool fits) against the DEV curves.

## T18-3 What a binary-labelled source campaign can transfer
**Setting.** Source latent $f_A$, target latent $f_B=f_A+\delta$ ($\delta$ an unknown constant: the "level shift"),
labels $y=\mathbf 1[f>0]$ in both campaigns, target pool of $N_B$ points.

**(a) Non-identifiability (PROVED).** Binary source labels, even on the whole domain, determine only
$S_A=\{f_A>0\}$. For $\delta>0$ and any open $S'$ with $\overline{S_A}\subset S'$ there is an $f_A$ consistent with
the source labels such that $\{f_A+\delta>0\}=S'$. *Proof.* Take a continuous $w$ with $w>1$ on $S_A$, $w=1$ on
$\partial S_A$, $0<w<1$ on $S'\setminus\overline{S_A}$ and $w\le0$ off $S'$ (Urysohn), and set $f_A=\delta(w-1)$. Then
$f_A>0\iff x\in S_A$ and $f_A+\delta>0\iff x\in S'$. $\square$ So the source constrains the target boundary only by
nesting ($S_A\subset S_B$ for $\delta>0$); in the worst case the target still faces the T18-2 complexity on
$S'\setminus S_A$.

**(b) Index structure (PROVED, corollary of T18-1a).** If $f_A=\kappa(\varphi(x)-c)$ with known $\varphi$, then
$S_B=\{\varphi>c-\delta/\kappa\}$ is one unknown scalar: $\lceil\log_2(N_B+1)\rceil$ target queries suffice and are
necessary in the worst case.

**(c) Continuous source values (PROVED).** If the source reveals $f_A$ (or a known strictly monotone transform,
e.g. conduction depth below the Keyhole threshold) then $S_B=\{f_A>-\delta\}$ is again a one-scalar family ordered
by $f_A$: the source ranks the target pool exactly and only the threshold must be searched.

**Consequences / predictions.** Binary priors transfer *ordering* to the extent the boundary has index-like
structure, but not the threshold. Observed (POST-HOC): the OLD prior raises NEW ranking quality strongly
(AUC AULC 0.819 → 0.909, R3_NEW → R2) while BA rises only +0.011; and Phase 1 found no campaign offset
($\delta\approx0$, +0.001 nats), so pooling is the right treatment of OLD + NEW and a hierarchical level-shift model
has nothing to estimate (portfolio B). P-T18-3: in the S2 two-campaign world ($\delta=0.6$) the prior lifts AUC far
more than BA.

## T18-4 Information per query: binary labels vs continuous outputs
**Statement (KNOWN facts; application PROVED).** With probit link and latent margin $m$ (in noise-scale units) the
Fisher information that one binary label carries about the latent at the queried point is
$$I_{\rm bin}(m)=\frac{\varphi(m)^2}{\Phi(m)\Phi(-m)}:\quad 0.637,\ 0.439,\ 0.131,\ 0.015,\ 0.0006\ \text{ at } m=0,1,2,3,4,$$
and for the logistic Laplace GPC the precision a label adds at the mode is $W_i=\sigma(\hat f_i)(1-\sigma(\hat f_i))\le
e^{-|\hat f_i|}$. A Gaussian depth observation with noise sd $\sigma_d$ carries $1/\sigma_d^2$ whatever its distance
from the boundary; a censored (Keyhole) observation carries the binary information about the threshold.
Consequences: (i) under deterministic labels, binary information is concentrated in an $O(1)$-latent band around
the boundary — startup / space-filling points far from it are nearly wasted for a GPC, which is why random
refinement loses on every large pool (Phase 2) and margin selection dominates; (ii) a conduction-depth observation is
informative anywhere on the conduction side, and the kernel carries it to the boundary — the mechanism behind
P-T18-1: a depth learner's gain should be largest at small budgets and in conduction-rich pools (OLD-like, pooled),
and small on NEW-like pools (≈ 9% conduction runs).

## T18-5 ML-II hyperparameters under boundary-concentrated designs (CONJECTURE → numerical check)
**Conjecture.** With deterministic labels, ML-II on a margin-type design (all points near the boundary, both
classes interleaved) selects shorter length-scales and a larger amplitude than on a random design of the same size,
but the resulting classifier near the pool is insensitive to this (the decision is driven by the nearest
opposite-label pairs), so margin is not hyperparameter-limited, whereas random designs depend on ML-II adapting
length-scales to the target region. This is the explanation offered for Phase 0 item (a): margin ≈ 0.66 under fixed
OLD and per-step ML-II hyperparameters, random gains +0.023–0.026 from ML-II. Check: `src/week18_mlii_design.py`
(idealized boundary design = the $b$ pool points with smallest $|f|$ vs uniform random; cross-refits with the other
design's hyperparameters).

## Astra Round 3 (received 2026-10-05) — integrated as hypotheses
Source: `outputs/astra_round3/` (verbatim copy of the owner-supplied package, 25 files matching its SHA-256 manifest;
Astra inspected HEAD 1ded7f43 read-only). Round 3 audits **Week 16** (PEER, oracle headroom, calibration); it does not
evaluate Week 18 methods. Per the Week 18 brief its claims are hypotheses here; no freeze is changed (none exists yet
for Week 18; earlier weeks' frozen verdicts stand). Astra's PROVED statements are Astra's proofs (appendix
`ROUND3_THEOREM_APPENDIX.tex`, 60 statements); "checked" below means re-derived independently from the statements
(`src/week18_astra3_checks.py`, no Astra code imported or executed).

| Astra item | Our status | Relation to Week 18 |
|---|---|---|
| L3: centred Gaussian/probit self-value arctan(s/τ)/π | **checked** (quadrature vs closed form, max error 1e-16) | — |
| C10: coherent plug-in edge EBR = −1/9 | **checked** (exact rationals) | Week 15/16 negative EBR ≠ proof of incoherent updating (erratum E18-4) |
| R5: optimized ratio-of-expectations Dice risk rises by 1/210 | **checked** (exact) | same |
| P5: attenuating the whole physics mean never moves its zero threshold | **checked** (trivial) | Week 17 M3 vs M3_Cfree: level changes need an intercept/discrepancy, not attenuation |
| D4: first rare rank D ≤ 1 + ⌊V/r⌋ | **checked on real data**: OLD D = 1 ≤ 4, NEW D = 2 ≤ 18, POOLED 1 ≤ 5 (log-h order; `phase4/astra3_D4_real.csv`) | the physics order is a strong rare-class ranker (AUC 0.99 OLD, 0.86 NEW) |
| P6: OLD data + unlabelled NEW inputs cannot identify a NEW threshold shift | agrees with **T18-3(a)** (stronger premise there: all source labels identify only nesting) | transfer of thresholds needs target labels or continuous outputs (T18-3(c)) |
| P1–P4: order-only threshold search, ⌈log₂(N+1)⌉ | = **T18-1(a)** / **T18-3(b)** | — |
| G2: value of observing a real-valued boundary height = conditional variance; "substituting a binary label for an observed height invalidates the experiment" | formal counterpart of **T18-4** | mechanism behind E1/E3: a depth query observes a real value |
| C2: positive rescaling of the latent preserves every sign and the boundary; latent sd is no geometric certificate | accepted (elementary) | sharpens **T18-5**: with deterministic labels the latent amplitude is weakly identified by ML-II; amplitude/length-scale drift under margin designs need not change the classifier |
| §10 conjecture "level shifts, order survives" | **tested (POST-HOC)**: order survives within campaigns (AUC above); 1-D threshold shift +0.17 [0.03, 0.29] overall, +0.01 [−0.14, 0.28] in the overlap → shift vs region effect **not decidable**; flexible GPC needs no offset | erratum E18-3 to our own DATA_AUDIT; B1 (hierarchical) stays killed (offset adds +0.001 nats) |
| §1/§14 Week 16 interpretation ("remaining gap = model information") | **accepted** as a correction | erratum E18-4; THESIS_IMPLICATIONS uses the narrower wording |
| §8 numerical audit (martingale "max 4.3"; saturation illustration) | **verified** from saved tables | erratum E18-5 |
| §10 top-priority test: same-state factorial separating latent law, channel and updater on Week 16 states | **deferred** — needs the Week 16 posterior states with full target–candidate covariances (not saved; `headroom/candidates.csv.gz` holds per-candidate summaries only) and concerns PEER, which is not a Week 18 candidate | listed in OPEN items; the deterministic-vs-stochastic channel distinction is built into E3 (σ is a working likelihood scale absorbing model misfit; the simulator is deterministic) |
| O2/O5: campaign intercept / robust prior over level | covered by B1 (killed, premise unsupported on our data) and E18-3 | — |

**What Round 3 changes in Week 18's reporting.** (i) Effects are reported as absolute differences with intervals,
QTT alongside AULC; no ratio-only claims. (ii) "Deterministic simulator, stochastic working likelihood" is stated
for every model (G3/LT/M3 logistic, E3 Gaussian σ on log depth). (iii) Startup and refinement stay separate
(unchanged design: startup is identical across arms). (iv) No claim that the remaining gap to an oracle is "model
information".
