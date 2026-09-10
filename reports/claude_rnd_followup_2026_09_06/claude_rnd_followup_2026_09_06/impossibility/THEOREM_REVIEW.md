# THEOREM_REVIEW — hostile audit of IMPOSSIBILITY_THEOREM.md

Scope: validation and calibration only. No new acquisition, no benchmark tuning, no new refits (all checks re-read `results/twin_worlds_flips.csv.gz` and the frozen repository outputs). Code: `code/review_twins.py`; results: `results/review_recheck.json`, `results/review_local_twins.csv`. Disk: no growth beyond these two files (rnd directory 771 MB before and after).

---

## 1. Theorem-by-theorem audit

### Theorem 1 (global form)
- **Correct as stated, but its content is thin.** With $\Omega_n=\{0,1\}^{U\setminus D_n}$ the reversal $\rho_R$ is trivially compatible, and the statement reduces to: a quantity that is a non-constant function of hidden labels is not a function of the observed data. The only non-trivial input is identity (0.1) (value = signed flip count), which is what makes the *local* form small.
- Quantifiers: "for every deterministic $A$ there is $\omega'\in\{\omega,\rho_R\omega\}$" — correct given (A4). (A4) must be stated for the *true* $\omega$ (it is).
- **Missing assumption (A1′):** the learner's decisions on $R$ must depend on labels only through $y_{D_n}$ (and hypothetical $y_x$). True for M3 and for any supervised learner, false for a learner that peeks at $y_R$; add it explicitly.
- **Compatibility set (A5):** "$\Omega_n$ unconstrained" makes the global form vacuous under any physical prior. Repaired statement uses only the local reversal and states admissibility as a checkable condition (§2).

### Theorem 1 (local form)
- Counting argument verified: $D\le a$ (available rows) and $k=\lfloor D/2\rfloor+1\le a$ for $D\ge1$; numerically confirmed for 58/58 pairs with an arbitrary choice of $k$ available rows.
- Correct. This is the substantive statement.

### Corollary 1 (any horizon, AULC)
- $\mathrm{acc}_t(\pi;\rho_R\omega)=1-\mathrm{acc}_t(\pi;\omega)$ holds for any decision vector; a label-blind adaptive policy produces the same query sequence in both worlds because $I_{n+t}$ never contains a label of $R$. AULC of accuracy maps to (window − AULC); gains and all *contrasts between policies* change sign. Valid.
- Requires: the policy queries only in $Q$ (true for the frozen protocol and for the repository's test-label oracle) and non-degeneracy over paths. Valid, but it is the same one-line symmetry, not an extension with new content.
- Wording "invariant-undetermined by the entire query process" is correct only for reversals inside $R$; it must not be read as "no information about $y_R$ can ever be gained" — the model *does* update its beliefs about $y_R$ from queries in $Q$; what is fixed is the truth of $y_R$, and the theorem says nothing about how well the posterior tracks it. Rewrite.

### Theorem 2
- (a) Correct: $r(A;\omega)+r(A;\rho_R\omega)=\Delta(\omega)$.
- (b) Correct for the two-point prior, **but "least-favourable prior" is wrong.** Counterexample: three candidates with disjoint singleton flip sets, adversary sets one helpful and two harmful signs; the minimax (randomised, uniform) regret is $4/(3|R|)>\Delta/2=1/|R|$. The two-point prior gives a valid lower bound that is not tight in general. Also the Bayes regret under $P_{\rm sym}$ is $\mathbb E_{\rm sym}[\max_xV]$ for every rule (each $\mathbb E V(x)=0$), a second, generally different lower bound (empirically 0.0535 vs $\Delta/2=0.054$). Repaired statement gives both bounds and drops "least-favourable".
- (c) $P(x_A$ unique argmax$)\le\tfrac12$: proof valid (odd gap, measure-preserving involution). **Exchangeable case mis-stated:** with $m$ exchangeable candidates $P(x_A\text{ is the unique maximiser})\le1/m$, but $P(x_A\in X^*)\ge1/m$ (ties). Repaired.
- The prior invariance must hold for the conditional law of $y_R$ given $(I_n,y_Q)$; add explicitly.

### Theorem 3
- (a) Correct as a worst-case statement; the parenthetical about asymmetric priors is necessary and is kept (empirically the candidate-label oracle recovers 25 % of the headroom).
- (b) Correct.
- (c) The $2q-1$ identity needs **all** of: $e_u$ i.i.d. uniform (not just $\rho_S$-invariant — the identity $s\overset{d}{=}e$ needs full product symmetry); $\xi_u$ i.i.d., independent of $(I_n,\omega,y_Q)$, with the same $q$ for every row; $y_Q$ known; ties in $\arg\max\tilde V$ broken independently of $s$. The stated version omitted "same $q$ for every row" and "independent of $\omega$" (a low-fidelity simulator's errors are *not* independent of where the high-fidelity threshold lies — they concentrate at the same near-threshold rows). Repaired; the physical proxy reading is now conditional.
- (d) Correct under $\rho_S$-invariant priors; must not be read as "no function of $I_n$ carries information" under the actual prior.

### Lemma 4
- Correct (standard MOCU/EVSI). Note that the "model-Bayes" rule in §E is (1.2) restricted to $R$ and uses M3's *marginal* $p_{n+1}$; it is an approximation of the joint one-step expectation, consistent with the rest of the follow-up (XSUR-S3).

**Counterexamples sought and not found** for the local form, Corollary 1 and Theorem 2(a),(c). Counterexamples found for the "least-favourable" wording (2b), the exchangeable-bound direction (2c), and the unstated independence conditions in 3(c).

---

## 2. Physical compatibility of the local twins

Constraints imposed (all frozen before the reference labels, from Phase 1.19A and the physics band): monotone partial order "$j$ more keyhole-favouring than $i$ iff $P_j\ge P_i$, $VX_j\le VX_i$, $LS_j\le LS_i$, one strict; ST ignored" (3 violations in 22,050 comparable directed pairs on the full 405); physical band $\log h\in[20.3621,21.2533]$; main configuration group; M3 uncertainty at the flipped row. A twin is admissible at a level if *some* choice of the $k$ reversed rows (joint check: reversing them together creates no new violation) satisfies it.

| Level | Constraint on the $k$ reversed reference rows | Admissible / 58 |
|---|---|---|
| L0 | none | 58 |
| L1 | no new dominance violation against the **revealed** labels $y_{D_n}$ (label-blind check) | 55 |
| L2 | L1 and inside the physical band | 55 |
| L3 | no new dominance violation against **all** other 404 true labels (twin labeling exactly as monotone as the truth) | 42 |
| L4 | L3 and inside the band | 42 |
| L5 | L4 and main configuration and $\lvert2p_n-1\rvert\le0.5$ at every reversed row | 23 |

Every available reversal row lies inside the physical band (100 %); 73 % of available rows are individually consistent with all 404 other labels. By budget, L3 admissibility is 11/16, 9/14, 12/14, 10/14 at B16/24/32/40. Of the 58 chosen reversals, 22 involve a row where M3 is confident ($|2p_n-1|>0.6$); in 20 of these M3 is wrong there (rows of the persistent-exception type), so the reversal *removes* an empirical anomaly and is physically among the most plausible twins, not the least. Class balance changes by at most 3 of 73 keyholes. Campaign structure: the L5 count (23) is the number of twins that are simultaneously monotone-consistent, in-band, main-configuration and model-uncertain.

**Conclusion:** the local reversal survives the strongest structural prior available before unblinding: in 42/58 states (72 %) a world exists that is observationally identical, as monotone as the truth, in-band, and differs in 1–3 reference labels. The result does not disappear; the *global* twin ($\rho_R$) should be dropped from the thesis as physically vacuous.

---

## 3. What the result is about

| Reading | Supported? |
|---|---|
| A. General active-learning limitation | **No.** For inductive AL with a hypothesis class or prior, active learning provably helps; the symmetry here needs a fixed, never-queried reference set. Nothing in the result bounds generalisation error or label complexity. |
| B. Transductive limitation: 0-1 accuracy on a fixed hidden reference set disjoint from the query pool | **Yes.** This is the exact content: the value of any query on $R$ is a signed count over $R$'s hidden correctness signs, and no query touches them. |
| C. Specific to the q20 construction | Only through $|R|=17$ (granularity $1/17$, small flip sets, few-label twins). Any fixed reference set gives the same statement. |
| D. Property of the test-label hindsight oracle | **Yes.** The oracle ranks by $V$, a function of $y_R$; the theorem formalises why its gain is the value of $y_R$ and not a property of the inputs. |

**Answer to the key question.** The result explains why no label-blind acquisition can reproduce the +0.095 hindsight-oracle gain *uniformly* (Theorem 1) and why, averaged over a reversal-symmetric prior on $y_R$, every acquisition is equal (Theorem 2b). It does **not** imply that another label-blind acquisition cannot beat M3-margin on the actual labeling, on the new pool, or in expectation under the actual (asymmetric) label distribution. The truth is one fixed labeling; Theorem 2(b) averages over two. Empirically the per-query values of margin, model-Bayes and random are within 0.007 of each other, which is *consistent* with a near-symmetric flip-row prior, but that is an observation on 49 distinct reference rows, not a consequence of the theorem. The previous document's sentence "the saturation of label-blind acquisition at the margin level is the structural situation" overreaches and is withdrawn.

---

## 4. Empirical re-check (independent code, `review_twins.py`)

| Quantity | Original | Re-check | Status |
|---|---|---|---|
| Flip-set identity, max deviation | 1.1e-16 | 1.1e-16 | confirmed |
| States where oracle-best > margin pick | 58/80 | 58/80 | confirmed |
| Local-twin $k$ = 1 / 2 / 3 | 36 / 20 / 2 | 36 / 20 / 2 | confirmed |
| Oracle / margin / model-Bayes / random per-query value | .0618 / −.0044 / −.0015 / +.0026 | same | confirmed |
| Regrets margin / model-Bayes / random; $\Delta/2$ | .066 / .063 / .059; .054 | same | confirmed |
| Proxy curve ($y_x$ known), $q$ = .5/.6/.7/.8/.9/1 | .009/.020/.031/.041/.052/.062 | .009/.019/.030/.041/.052/.062 | confirmed (independent RNG) |
| $P(e=-1\mid$ flip row, $\lvert2p-1\rvert\le.1)$ | 0.504, "$n=1{,}156$" | 0.504 over 1,156 **(candidate,row) pairs**; the same reference row is counted once per candidate that flips it. Unique (state,row) pairs: **206**; unique with conf ≤ 0.1: **43**, frequency **0.465, 95 % CI [0.31, 0.62]**; distinct population rows carrying any flip: **49** | **overstated precision; corrected** |
| "M3 assigns the twin probability 0.71; prefers it in 84 % of states" | 0.71 / 84 % | For $k=1$ (36 states) the number is exact-marginal: mean 0.66, median 0.63, ≥ 0.5 in 30/36. For $k\ge2$ it is a **product of marginal predictive probabilities** (independence across rows; the Laplace latent posterior is correlated). More importantly the number is **tautological**: for a helpful-row reversal, $W_2$ is by construction the world in which M3's current decision at that row is correct, and its marginal probability is $\max(p_n,1-p_n)\ge\tfrac12$ by definition. | **claim rewritten** |
| "model's posterior probability that margin ≥ oracle-best is 0.64" | 0.64 | Same independence approximation over the symmetric difference (median size 1, so exact in most states); same tautological content | rewritten |
| "least-favourable prior is the empirical truth" | asserted | consistent with 0.5 but CI ±0.15 on 43 unique rows; the 58/42 overall figure (206 unique rows: 0.53) is likewise imprecise | **downgraded to "not rejected"** |

Precise rewrite of the plausibility claim: "In every local twin, the reversed rows are rows where M3's current decision is wrong (helpful rows of $x^\star$) or right (harmful rows of $x_m$). Reversing a helpful row produces the world in which M3 is right there; M3's marginal predictive probability of that world is $\max(p_n,1-p_n)$, which is $\ge\tfrac12$ by definition and on average 0.66 for the 36 single-row twins. The number measures M3's confidence at the reversed row, not independent evidence for the twin."

---

## 5. Novelty

Searched: NFL (Wolpert 1996), Dasgupta "Two faces of active learning" (2011) and greedy/coarse bounds (2004/05), Castro–Nowak minimax (2008), Hanneke minimax (2015), Balcan–Hanneke–Vaughan (2010), Tosh–Dasgupta diameter (2017), Roy–McCallum EER (2001), MOCU (Yoon–Dougherty–Qian 2013), Konyushkova et al. LAL (2017), Hübotter et al. "Transductive active learning: theory and applications" (NeurIPS 2024), Yu–Bi–Tresp transductive experimental design (2006), Lindley/Chaloner–Verdinelli Bayesian design.

| Component | Classification |
|---|---|
| Reversal symmetry ⇒ all label-blind rules equal under a symmetric prior | **1. Classical mechanism** (Wolpert 1996; the "unstructured version space" remark in Dasgupta 2011 — without structure no active learner beats passive/random). |
| Minimax regret ≥ Δ/2; probability of the oracle-best ≤ ½ | **2. Straightforward corollary** of the symmetry. |
| Corollary 1 (any horizon / AULC) | **2. Straightforward corollary.** |
| One-step value on a fixed reference set is a signed count over $I_n$-computable flip sets (0.1); hence a reversing twin needs only $\lfloor D/2\rfloor+1$ labels inside the symmetric difference of two flip sets | **4. Formulation specific to this setting**; elementary but not found stated. Closest: Hübotter et al. 2024 separate reducible from *irreducible* target uncertainty for targets outside the sample space — the same structural fact in a GP-regression setting; MOCU/EER give (1.2) but not its realised-value counterpart. |
| $2q-1$ recovery fraction for a reference-side proxy under the symmetric prior | **2/4.** Immediate from linearity, but the quantitative reading (accuracy needed at near-threshold rows) is specific. |
| 42/58 physically admissible few-label twins; near-chance correctness at flip rows (CI [0.31, 0.62]) | **3. Dataset-specific empirical observation**, with limited precision. |

Defensible contribution: the flip-set identity, the few-label local twin with its admissibility count, and the proxy fraction — as a *proposition plus diagnostic*, not a theorem about active learning.

---

## 6. Verdict

### DOWNGRADE TO PROPOSITION / DIAGNOSTIC

The mathematics is correct after the repairs in §1; the mechanism is classical; the global form is vacuous under any physical prior; the local form and its empirical admissibility are protocol-specific but real; the plausibility and "symmetric prior realised" claims were overstated and are recalibrated. Presented as a central theorem it would invite the objection "this is Wolpert's argument for a quantity defined through hidden labels"; presented as a proposition that pins down *what* the hindsight-oracle gap measures, with the local-twin diagnostic, it is defensible and useful.

---

## 7. Deliverables

### 7.1 Strongest safe formal statement

**Proposition (non-identifiability of the hindsight query value on a fixed reference set).** Let $U$ be a finite pool with a fixed unknown labeling $y\in\{0,1\}^U$, $D_n\subset U$ the revealed rows, $R\subseteq U\setminus D_n$ a reference set and $Q=U\setminus(D_n\cup R)$ the candidates. Let $L$ be a learner whose decision rule on $R$ depends on labels only through the labels it is given, $\hat y_n=L(D_n)$, and define for $x\in Q$, $y\in\{0,1\}$ the flip set $F_y(x)=\{u\in R:L(D_n\cup\{(x,y)\})(u)\ne\hat y_n(u)\}$ and the value $V(x)=\mathrm{acc}_R(L(D_n\cup\{(x,y_x)\}))-\mathrm{acc}_R(\hat y_n)$. Then:

(i) $V(x)=-|R|^{-1}\sum_{u\in F_{y_x}(x)}e_u$ with $e_u=+1$ if $\hat y_n(u)=y_u$ and $-1$ otherwise.

(ii) For any two candidates $x^\star,x'$ with $D:=|R|(V(x^\star)-V(x'))\ge1$ there is a set $S\subseteq F_{y_{x^\star}}(x^\star)\triangle F_{y_{x'}}(x')$ with $|S|=\lfloor D/2\rfloor+1$ such that the labeling $y^S$ obtained by negating $y_u$ for $u\in S$ satisfies: $y^S$ agrees with $y$ on $D_n\cup Q$; every function of $(\{x_u,z_u\}_{u\in U},D_n,y_{D_n})$ — in particular every fitted model, every flip set and every label-blind acquisition — takes the same value under $y$ and $y^S$; and $V^S(x')>V^S(x^\star)$.

(iii) Consequently, if $V$ is not constant on $Q$, no deterministic label-blind acquisition selects a maximiser of $V$ under both $y$ and $y^S$; the same holds for any fixed query horizon and any window-weighted accuracy functional (AULC), with $S=R$.

(iv) If $P$ is a probability law for $y_R$ given $(I_n,y_Q)$ that is invariant under negation on $S=F(x_A)\triangle F(x')$ for the pick $x_A$ of a label-blind rule and some $x'$ with a different realised flip set, then $P(x_A$ is the unique maximiser$)\le\tfrac12$, and $\mathbb E_P[V(x_A)]=0$ whenever $P$ is invariant under negation on $F(x_A)$. Under the two-point law $\tfrac12(\delta_y+\delta_{y^R})$ every rule, randomised or not, has regret $\tfrac12(\max_xV-\min_xV)$; under the product-uniform law on $e_R$ every rule has regret $\mathbb E[\max_xV]$. Both are lower bounds on the minimax regret; neither is tight in general.

(v) Let $s_u=e_u\xi_u$ with $(\xi_u)$ i.i.d., $P(\xi_u=1)=q$, independent of $(I_n,y)$, under the product-uniform law on $e_R$ and with $y_Q$ known. Then $\mathbb E[V(x)\mid s]=(2q-1)\tilde V(x)$ for $\tilde V(x)=-|R|^{-1}\sum_{u\in F_{y_x}(x)}s_u$, and the rule $\arg\max\tilde V$ (ties independent of $s$) attains expected value $(2q-1)\,\mathbb E[\max_xV]$.

### 7.2 Assumptions (next to the statement)
(a) Labels fixed (deterministic simulator); (b) $R\cap D_n=\emptyset$, candidates in $Q$, no query reveals a label in $R$; (c) the learner is supervised in the sense above; (d) non-degeneracy: $V$ non-constant (for (iii)); (e) for (iv): invariance of the conditional law of $y_R$ under the stated negation; for (v): product-uniform $e_R$, i.i.d. proxy noise independent of everything, constant $q$, $y_Q$ known. No assumption on model class, kernel, calibration or acquisition family. The compatibility set is the set of labelings agreeing with $y_{D_n}$ on $D_n$; physical admissibility of $y^S$ is an empirical statement (§2), not part of the proposition.

### 7.3 Proof (MSc length)
(i) A row $u\in R$ changes the accuracy by $-e_u/|R|$ if its decision flips and by 0 otherwise. (ii) Write $F^\star=F_{y_{x^\star}}(x^\star)$, $F'=F_{y_{x'}}(x')$. By (i), $D=-\sum_{F^\star\setminus F'}e_u+\sum_{F'\setminus F^\star}e_u$. Call $u$ *available* if $u\in F^\star\setminus F'$ with $e_u=-1$ or $u\in F'\setminus F^\star$ with $e_u=+1$; each row of the symmetric difference contributes $+1$ to $D$ if available and $-1$ otherwise, so the number $a$ of available rows satisfies $a\ge D$. Negating $y_u$ at an available row changes $e_u$ to $-e_u$, leaves both flip sets unchanged (they depend on $y_{D_n}$ and the hypothetical label only), and lowers $D$ by 2. Negating $k=\lfloor D/2\rfloor+1\le a$ available rows gives $D-2k<0$. Every function of $(\{x_u,z_u\},D_n,y_{D_n})$ is unchanged because no negated row is in $D_n$. (iii) A deterministic rule returns the same $x_A$ under $y$ and $y^S$; apply (ii) with $x^\star=x_A$ and any $x'$ with $V(x')<V(x_A)$, or with $x'=x_A$ and $x^\star$ a maximiser. For a horizon $t$ and $S=R$: every decision vector has accuracy $1-\mathrm{acc}$ under $y^R$, and a label-blind policy produces the same decisions in both worlds. (iv) $V(x_A)-V(x')$ is an odd function of $(e_u)_{u\in S}$; negation on $S$ is a measure-preserving involution mapping $\{V(x_A)>V(x')\}$ onto $\{V(x_A)<V(x')\}$, so the two events have equal probability, each $\le\tfrac12$. Under the two-point law $\mathbb E V(x)=0$ for all $x$ and $\mathbb E\max V=\tfrac12(\max V-\min V)$; under the product-uniform law $\mathbb E V(x)=0$ and the regret is $\mathbb E\max V$. (v) $e_u$ uniform and $\xi_u$ independent give $\mathbb E[e_u\mid s_u]=(2q-1)s_u$; linearity of (i) gives the conditional expectation; $(s_u)$ has the same law as $(e_u)$, so $\max\tilde V\overset{d}{=}\max V$. $\square$

### 7.4 Empirical proposition (405-case benchmark, development data)
On the 80 states of the committed M3-margin paths (20 runs × B ∈ {16,24,32,40}), reference set = 17 Fold-B1-q20 rows: (a) the oracle-best candidate strictly beats the margin pick in 58 states, by 1–5 reference rows ($D$); (b) a reversing twin exists with $k$ = 1/2/3 negated reference labels in 36/20/2 states, all negated rows inside the physical band, and in 42 states the twin creates no new violation of the frozen monotone partial order against all 404 other labels (23 states additionally main-configuration and $|2p_n-1|\le0.5$); (c) per-query values: oracle +0.062, margin −0.004, model-Bayes −0.001, random +0.003 (repeat-block s.d. 0.02–0.03); (d) at the 43 distinct (state,row) flip rows with $|2p_n-1|\le0.1$ the current decision is wrong with frequency 0.465, 95 % CI [0.31, 0.62] — the symmetric law of (iv) is not rejected; (e) a reference-side proxy of accuracy $q$ with the candidate label known attains $0.009+(2q-1)\times0.053$ per query (Monte-Carlo), i.e. 0.031 at $q=0.7$.

### 7.5 Figure/table design (local twin result)
One figure, two panels, from `results/review_local_twins.csv` and `twin_worlds_pairs.csv`. **Left:** 58 states on the x-axis sorted by $D$; stacked bars showing $V(x^\star)$ (positive) and $V(x_m)$ (≤ 0) in units of reference rows; a marker at $k$ (number of negated labels) coloured by admissibility level (L1 / L3 / L5 / none). **Right:** the admissibility staircase — a horizontal bar per level L0…L5 with the count (58, 55, 55, 42, 42, 23), annotated with the constraint text. Caption states that every reversal row lies in the physical band and that the reversed rows are rows where M3 is wrong (helpful rows) or right (harmful rows), so "M3's probability of the twin" equals its confidence at those rows. Table alternative: the L0–L5 table of §2 plus the $k$ distribution.

### 7.6 What the result does NOT imply
It does not imply that no label-blind acquisition can beat M3-margin on the actual labeling or on the new pool; the truth is a single labeling and the symmetry statement averages over two. It does not bound generalisation error, label complexity, or any inductive quantity. It does not say the model cannot learn about $y_R$ from queries in $Q$; it says the *truth* of $y_R$ is untouched, so the hindsight value cannot be identified. It does not show that the flip-row prior is symmetric — that is an empirical observation on 43–49 rows with a wide interval. It does not make the +0.095 oracle gain unattainable in principle: a reference-side measurement of accuracy $q$ recovers a fraction $2q-1$ of it under the stated conditions. It does not apply to loss functions that are not linear in per-row correctness (Brier, log-loss, boundary-location errors) without modification.

### 7.7 Novelty paragraph (conservative)
The mechanism — averaging over labelings the data do not constrain makes all label-blind procedures equivalent — is the no-free-lunch argument of Wolpert (1996) and the unstructured-version-space remark in Dasgupta (2011). What is specific here is the object to which it is applied: the realised one-step value of a query on a fixed, never-queried reference set under 0-1 loss, which decomposes exactly into computable flip sets and hidden correctness signs, so that a reversing twin needs only $\lfloor D/2\rfloor+1$ labels inside the symmetric difference of two flip sets. Hübotter et al. (2024) make the related distinction between reducible and irreducible target uncertainty in transductive active learning; expected-error-reduction and MOCU compute the posterior expectation of the same quantity. The proposition, the local-twin construction, the proxy fraction $2q-1$ and the admissibility count on the melt-pool benchmark are, to the author's knowledge, not stated elsewhere, but they are elementary consequences of the classical argument and are presented as such.

### 7.8 Recommended place in the thesis
End of the acquisition chapter, as "Proposition X (what the hindsight-oracle gap measures)" with proof in an appendix and the local-twin figure in the main text; one paragraph in the discussion linking it to the external-protocol design (why the oracle gain is a prediction study, P9, and not an acquisition target) and to multi-fidelity as the only route to the reference-side signal. Not in the introduction, not as a chapter.

### 7.9 Two-minute explanation for Ioan
"The test-label oracle gains +0.095 because it chooses queries knowing which test rows the current model gets wrong. I wrote down what a query is actually worth: it is a signed count — the number of test rows whose decision the refit flips, each counted +1 if the old decision was wrong and −1 if it was right. Which rows would flip is computable before the query; whether the old decisions there were right is exactly what the test labels tell you and nothing else does. So if you change one to three test labels at the flipped rows, every model, every score and every acquisition sees the same data, but the best query becomes a bad one. On our 405 cases that alternative world is inside the physical band and as monotone as the truth in 42 of 58 states. The consequence is not that acquisition cannot be improved — it is that the oracle's gap is the value of the test labels, and a label-blind rule can only close it to the extent the model's errors at those rows are predictable. At the rows where flips land, the old decision is wrong about half the time, so there is little to predict. This is a known kind of argument; the specific form and the numbers are ours. It tells us to treat the oracle as a prediction study, and that a multi-fidelity signal at near-threshold points, not a new acquisition, is what would move the early window."

### 7.10 Examiner objections and responses
1. *"This is Wolpert's no-free-lunch theorem restated; a quantity defined through hidden labels is trivially not identifiable from data that excludes them."* — Agreed on the mechanism, and the thesis says so. The content is the decomposition (i): the value depends on the hidden labels only through the signs at $I_n$-computable flip sets, so the indistinguishable world is a change of 1–3 labels at model-uncertain, in-band, monotone-consistent rows (42/58), not an arbitrary relabeling. That is what makes the statement bite for a physically constrained simulator.
2. *"Under the physical prior the reversed world is implausible, so the symmetric-prior bounds do not apply."* — The global reversal is indeed excluded and is not used. The local twins survive the strongest frozen structural constraint in 72 % of states. The symmetric law is not assumed to hold; at the 43 most uncertain flip rows the empirical error frequency is 0.465 [0.31, 0.62], so it is not rejected, and every bound is stated as conditional on the law of $y_R$.
3. *"Then why do you conclude anything about acquisition? Another rule could still beat M3-margin."* — The proposition concludes nothing about that, and the thesis wording is restricted to the hindsight gap. What it changes is the interpretation of the +0.095: it is the value of reference-side information, so it enters the external protocol as a prediction (P9) and not as a target, and it identifies the accuracy a reference-side proxy would need. The acquisition contrast is decided by the frozen external test, not by this proposition.

---

## Claim table

| Claim | Status | Reason | Safe wording |
|---|---|---|---|
| Flip-set identity (0.1) | KEEP | exact; verified 1e-16 | "The one-step value on $R$ equals $-\lvert R\rvert^{-1}\sum_{u\in F_{y_x}(x)}e_u$." |
| Global reversal $\rho_R$ makes every label-blind rule fail in one of two worlds | KEEP (math) / DROP (thesis) | correct but vacuous under any physical prior | mention only as the $S=R$ case of the local statement |
| Local twin with $\lfloor D/2\rfloor+1$ labels reverses any pair | KEEP | proof and 58/58 check | as in 7.1(ii) |
| Corollary 1 (any horizon, AULC) | KEEP, reworded | valid symmetry; "undetermined by the query process" over-read | "no query in $Q$ changes $y_R$; the sign reversal holds at every budget and for every window functional" |
| Minimax regret ≥ Δ/2 | KEEP | correct | as in 7.1(iv) |
| "Least-favourable prior; every rule equals random" | REPAIR | two-point prior is not least favourable (3-candidate counterexample); statement true only under that prior | "under the two-point law every rule has regret Δ/2; under the product-uniform law every rule has regret $\mathbb E\max V$" |
| $P(\text{oracle-best})\le\tfrac12$; $=1/m$ exchangeable | REPAIR | inequality direction for ties | "$\le\tfrac12$ under negation-invariant laws; $P(\text{unique maximiser})\le1/m$ under exchangeability" |
| $2q-1$ proxy fraction | KEEP with added assumptions | needs product-uniform $e$, i.i.d. noise independent of $\omega$, constant $q$, $y_Q$ known | as in 7.1(v); physical reading conditional |
| Candidate-side information cannot break the ambiguity | KEEP (worst case) | true under symmetric laws; empirically 25 % via asymmetry | "does not break the ambiguity under any negation-invariant law" |
| "M3 assigns the twin probability 0.71 / prefers it in 84 % of states" | REWRITE | product of marginals ($k\ge2$); tautological for helpful-row reversals | "M3's marginal probability of the single-row twin is its confidence at that row, $\max(p_n,1-p_n)$, mean 0.66 over 36 states" |
| "Least-favourable prior is the empirical truth (0.504, n = 1,156)" | DOWNGRADE | pseudo-replication; 43 unique rows, CI [0.31, 0.62] | "the symmetric law is not rejected at the most uncertain flip rows (0.465, 95 % CI 0.31–0.62, 43 rows)" |
| "Saturation at the margin level is the structural situation" | WITHDRAW | not implied; theorem is about the hindsight gap | "the hindsight-oracle gap measures the value of the reference labels" |
| Theorem explains why no acquisition can beat M3-margin | NOT SUPPORTED | averages over two labelings; truth is one | never claim; external test decides |
| Physical admissibility of local twins | KEEP (new) | 42/58 under full monotone consistency, 23/58 with model-uncertainty | as in §2 |
| Novelty | CALIBRATE | mechanism classical; formulation specific | as in 7.7 |

## Final verdict: **DOWNGRADE TO PROPOSITION / DIAGNOSTIC**
