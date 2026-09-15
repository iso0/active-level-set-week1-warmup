# WORLD_SPACE_RND — active elimination of physically plausible hidden-label worlds

Development data only (old 405 cases). No new-pool label or input. No modification of M3-margin; no GP-posterior score. Code: `code/worlds.py` (world sampler + world-space acquisitions), `code/world_replay.py` (prospective replay), `code/ref_worlds.py` (exact reference-world enumeration), `code/ref_info.py` (reference information rate). Results: `results/ref_worlds.csv`, `results/ref_info.csv.gz`, `results/world_*_metrics.csv.gz`, `results/world_*_steps.csv.gz`. Disk growth: these files only (< 5 MB); no clone, no worktree.

---

## 1. Physics-constrained version space

A **world** is a labeling $y\in\{0,1\}^U$ of the 405-row pool (training pool and outer test inputs; inputs are label-free and available). Structure used, all available before each query:

| Element | Type | Definition |
|---|---|---|
| Frozen partial order $\preceq$ (Phase 1.19A) | hard constraint (λ = ∞) or soft penalty (finite λ) | $j\succeq i$ iff $P_j\ge P_i$, $VX_j\le VX_i$, $LS_j\le LS_i$, one strict; ST ignored. Monotone world: $y_i=1\Rightarrow y_j=1$ for $j\succeq i$. Directed comparability 13.5 % of ordered pairs. Truth: 3 violations / 22,050 comparable pairs. |
| Violation budget | soft penalty | world weight $\propto\exp(-\lambda\cdot\#\text{violated pairs})$; enumeration uses exact budgets $v\in\{0,1,3,5,10\}$ |
| Physics coordinate $\log h$ | learned prior | product prior $p_u=\sigma(a\log h_u+b)$ with $(a,b)$ a regularised logistic ($C=1$) fitted on the revealed labels only; $\log h$ is order-consistent ($j\succeq i\Rightarrow h_j\ge h_i$), so any threshold labeling in $\log h$ is monotone |
| Uniform prior | ablation | $p_u=\tfrac12$: uniform over admissible worlds ("remove $\log h$") |
| Band / configuration | restriction | world restricted to band rows or main configuration; rows outside fixed at the prior decision |
| Class balance, transition width | **not used** | would require the evaluation labels or the full-pool truth |
| Outer-test labels | **never used** in any prior or acquisition; used only as the hidden truth for evaluation and for the counterfactual enumeration of §3 |

Posterior over worlds given revealed labels: $\pi(y)\propto\prod_u p_u^{y_u}(1-p_u)^{1-y_u}\exp(-\lambda\,\mathrm{viol}(y))$ with revealed rows fixed. Sampled by single-site Gibbs on the up-set lattice (irreducible under single flips; the conditional at $u$ is $\mathrm{logit}\,p_u-\lambda(\#\{j\succeq u:y_j=0\}-\#\{i\preceq u:y_i=1\})$; for $\lambda=\infty$ forced by any dominating 0 / dominated 1). 100 samples, burn-in 60 sweeps (20 with warm start), 0.7 s per state. Sanity: at B24 the world-posterior classifier reaches 0.955 accuracy on unrevealed rows with the $\log h$ prior and 0.816 with the uniform prior; mean violations per sampled world 0 (λ = ∞) and 0.6 (λ = 2).

## 2. Acquisitions on the world space (recognisably not margin/SUR/TV)

- **WH — robust version-space halving**: $\arg\min_x|p_W(x)-\tfrac12|$, $p_W$ = fraction of posterior worlds with $y_x=1$ (generalised binary search on the constrained world posterior).
- **WE — expected boundary-entropy reduction**: $\arg\max_x\ \sum_{u\in T}H(p_W(u))-\mathbb E_{y_x}\sum_{u\in T}H(p_W(u\mid y_x))$, $T$ = unrevealed band rows; computed by conditioning the world sample on $y_x$.
- **WM — minimax undetermined set**: $\arg\min_x\max_{y\in\{0,1\}}|\{u\in T:\delta\le p_W(u\mid y_x=y)\le1-\delta\}|$, $\delta=0.1$ (robust version-space diameter surrogate).
- **B — antichain/bisection** $\max_x\min(|\uparrow x\cap U_n|,|\downarrow x\cap U_n|)$ with $U_n$ the propagation-undetermined set: **not re-run** — this is Phase 1.19B arm P2 (with candidate removal), which lost by −0.013 BA-AULC and −0.021 q20; the mathematical fact behind it is recorded in §5.
- Predictors evaluated on every path: M3 (path effect) and the world-posterior classifier $\hat y=\mathbb 1[p_W\ge\tfrac12]$ (model effect).

## 3. Finite-pool combinatorics: exact enumeration of reference worlds (theorem attack, Part 4)

$|R|=17$ q20 rows; all $2^{17}=131{,}072$ labelings of $R$ enumerated for each of the 80 states; violations counted within $R$ and against the revealed labels (label-blind); worlds weighted by the uniform, the $\log h$ ($C=1$) and the M3-marginal prior; candidate values $V(x;w)=-\tfrac1{17}\sum_{u\in F_{y_x}(x)}e_u(w)$ with the realised flip sets (candidate labels known — the candidate-side oracle, an *upper bound* on what any label-blind rule can identify).

| Violation budget $v$ | admissible worlds (median over 80 states) | effective number ($\log h$ prior) | truth admissible |
|---|---|---|---|
| 0 (hard monotone) | 4,160 (min 112, max 37,632) — 12.0 bits of 17 | 1,265 | 70 % |
| 1 | 14,300 | 3,902 | 90 % |
| 3 | 50,272 | 11,099 | 100 % |
| 5 | 87,812 | 17,303 | 100 % |
| 10 | 128,896 | 22,474 | 100 % |

Ranking ambiguity under the hard-monotone world space ($v=0$, $\log h$ prior; uniform prior in brackets), mean over states:

| Quantity | Value |
|---|---|
| $P_W$(margin pick is oracle-optimal) | 0.043 [0.041] |
| $P_W$(true oracle-best is optimal) | 0.138 [0.164] |
| $\max_x P_W(x$ optimal$)$ (best identifiable candidate) | 0.212 [0.237] |
| entropy of the argmax distribution | 3.16 nats ≈ 24 effective candidates [3.01] |
| surviving twin mass $P_W(V(x_m)\ge V(x^\star))$, 58 states with $x^\star\succ x_m$ | 0.55 [0.50]; ≥ 0.5 in 71 % [62 %] of these states |
| by budget (16/24/32/40): admissible worlds | 14,933 / 11,886 / 6,755 / 2,827; max $P_W$(optimal) 0.12 / 0.22 / 0.26 / 0.26 |
| world-Bayes pick (argmax $\mathbb E_WV$, candidate label known), realised value | +0.004 ($\log h$), +0.029 (uniform), vs oracle +0.062 and margin −0.004 |

Hard monotonicity removes five bits of the 17-bit reference space and the truth itself is inadmissible in 30 % of states (the three known violation pairs enter $R$ or the revealed set); a budget of 3 restores the truth everywhere and leaves 15.6 bits. Under every budget and prior the margin pick is optimal in ≈ 4 % of admissible worlds, the best-identifiable candidate in ≈ 21–26 %, and the margin pick is at least as good as the true best in about half of the admissible mass. **The structural prior does not break the ranking ambiguity.**

**Reference information rate** (`ref_info.py`; full-pool monotone posterior, 300 worlds per state, 5,815 candidates): bits about the 17 reference labels transferred by one query, $\iota_R(x)=\sum_{u\in R}I(y_x;y_u)$: mean 0.035, median 0.016, max 0.55; bits about the rows the query would actually flip, $\iota_F(x)$: mean 0.0018 (0.006 over non-empty flip sets), best candidate per state 0.057, margin pick 0.002, oracle-best 0.014; $I(y_x;\mathrm{sign}\,V)$ mean 0.001. A reference row is comparable with the median candidate in 2 of 17 cases. Under the strongest structural prior, one query carries on the order of $10^{-2}$ bits about the labels that decide its own value.

## 4. Prospective replay (development, 40 outer runs = 8 repeat blocks × 5 folds, budgets 16–40, matched B16 designs)

Incumbent: M3 + probability margin on the committed P1 paths (q20 AULC 16–32 = 0.8150, 16–40 = 0.8232 on the same 40 runs). Random: not re-run (repository: margin > Random).

| Arm | predictor | q20 AULC 16–32 | 16–40 | Δ vs incumbent 16–40 [paired repeat-block 95 %] | blocks +/− |
|---|---|---|---|---|---|
| WE (entropy reduction, λ = ∞, $\log h$ prior) | M3 | 0.8206 | 0.8278 | +0.0045 [−0.0058, +0.0124] | 6/2 |
| WE | world classifier | 0.7983 | 0.8082 | −0.0150 [−0.0256, −0.0046] | 1/7 |
| WH (halving, λ = ∞, $\log h$ prior) | M3 | 0.8155 | 0.8135 | −0.0097 [−0.0175, +0.0000] | 3/5 |
| WH | world classifier | 0.8137 | 0.8201 | −0.0031 [−0.0152, +0.0096] | 4/4 |

WE is not margin under another name: it selects the margin pick in 5.8 % of steps, its picks have mean M3 margin 0.62 and world-posterior $p_W\approx0.50$. Path effect: +0.0045, below the +0.010 gate, interval containing zero; model effect of the world classifier: −0.015 (harm). q30 and full-fold AULC of M3@WE: 0.869 / 0.958 (16–40).

WH selects the margin pick in 8.2 % of steps (mean M3 margin of its picks 0.57); its path effect on M3 is negative (−0.0097). WM was not run (queued behind WH; killed on the user's instruction to finalise).

Falsification tests executed: violation budgets 0/1/3/5/10 (enumeration; §3), $\log h$ removed (uniform prior; §3, §4 sampler sanity), M3-marginal prior (§3), budgets 16–32 and 16–40, leave-repeat-block paired bootstrap, seeded world sampler. Not executed for lack of a surviving candidate: WM arm, main-configuration-only worlds, band-only worlds, misspecified order, class-imbalance perturbation, warm-start sensitivity, 16–80, synthetic counterexamples. Under kill criterion "q20 gain < +0.01 or interval includes zero" the direction is closed before those tests are needed.

## 5. The mathematical object (Part 5) — what is clean and what it says

**Monotone version space.** With hard monotonicity the compatible worlds form the up-set lattice of the undetermined sub-poset $U_n$ (rows not forced by propagation from revealed labels). It has a least and a greatest element, so its Hamming diameter is exactly $|U_n|$ — the **partial-order boundary width** $w_n=|U_n|$ — and a query $x$ reduces it in the worst case by $\min(|\uparrow x\cap U_n|,|\downarrow x\cap U_n|)$; greedy worst-case width reduction is the poset bisection rule (Phase 1.19B P2), and $\log_2|\text{up-sets}(U_n)|$ is the GBS lower bound on the number of queries needed to certify the boundary (a **finite-pool boundary certificate** is reached when $w_n=0$; 19B reached it after 86 queries on average). These are clean and known (learning an up-set of a poset by membership queries).

**Why the object does not transfer to the thesis endpoint.** The endpoint is 0-1 accuracy on 17 never-queried rows. The width $w_n$ and the certificate concern the training pool; the reference rows are tied to it only through comparabilities (2 of 17 for a typical candidate) and the $\log h$ prior. The exact enumeration shows that after removing every world inconsistent with the frozen order, the admissible reference space still has $\approx 12$ bits, and the information a query carries about its own flip rows is $\approx 10^{-2}$ bits. The relation to sample efficiency is therefore the negative one: the structural prior identifies the *training-pool* boundary cheaply (19B) but leaves the *reference-side* correctness signs — the quantity that decides the q20 endpoint (flip-set identity of the theorem round) — essentially unconstrained.

## 6. Literature (after derivation)
Generalised binary search and version-space halving (Dasgupta 2004/05; Nowak 2011; Golovin–Krause adaptive submodularity 2011); learning monotone functions / up-sets of a poset with membership queries and the width/antichain bounds (Hansel 1966; Sokolov 1982; Gainanov 1984; Torvik–Triantaphyllou 2002 "guided inference of monotone Boolean functions"); isotonic classification (Kotlowski & Slowinski 2013); active learning under shape constraints and monotone AL on posets (Auer & Ortner; "Active learning of monotone functions"); robust Bayesian experimental design (Berger; minimax design); transductive AL with target sets (Hübotter et al. 2024). The world sampler is a constrained Gibbs sampler over up-sets with a product prior — a standard construction (uniform up-set sampling is #P-hard to count but easy to sample by MCMC). Nothing in §2 is new as a method; §3's exact enumeration of the admissible reference space and the reference information rate are, to my knowledge, not stated elsewhere for this problem class, and are dataset-specific.

## 7. Kill criteria applied
- world space too symmetric for query rankings to stabilise: **yes** ($P_W$(margin optimal) 4 %, best identifiable 21–26 %, argmax entropy ≈ 3 nats, twin mass ≈ 0.5) → direction killed on this criterion alone;
- q20 gain < +0.01 with interval including zero: **yes** (WE +0.0045 [−0.006, +0.012]);
- nearly rank-equivalent to margin: no (5.8 % same pick);
- gains depend on one violation budget: not reached;
- requires information unavailable before querying: the world-Bayes pick that reaches +0.029 needs the candidate's own label — unavailable.

## Final verdict: **STRUCTURAL RESULT ONLY**

What was learned: the melt-pool problem *is* a partial-order boundary-learning problem on the training pool — hard monotonicity removes five of seventeen bits from the reference space, the truth violates it in 30 % of states so a budget of ≥ 3 is needed, and a constrained world posterior classifies unrevealed rows at 0.955 accuracy from 24 labels — but the thesis endpoint is not that problem. The q20 value of a query is a signed count over reference rows that no query touches, a typical candidate is order-comparable with 2 of the 17 reference rows, one query carries ≈ 0.01 bits about the rows it would flip, and after exact elimination of every order-inconsistent world the margin pick remains at least as good as the true oracle-best in about half of the admissible mass; the remaining ambiguity is not concentrated in the known exceptions (the truth is inadmissible in 30 % of states because of them, but the twin mass is 0.5–0.55 with or without them). World-space acquisitions built on this structure (halving, expected boundary-entropy reduction, minimax undetermined set) are recognisably different from margin, produce a small positive but non-significant path effect (+0.0045 q20 AULC 16–40 on 40 runs) and a negative model effect (−0.015), and do not meet the +0.010 gate; the direction is closed, and the frozen external challenger (M3 + TV) and protocol are unchanged.
