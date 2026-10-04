# Astra round-1 note (received 2026-10-04, pasted by the author into the Week 16 session)

Provenance: external collaborator note ("Astra"), produced read-only against the repository at the Week 12
state; computation by Astra was confined to external scratch space. Stored verbatim here so that the Week 16
tests (`src/tests/test_week16_astra.py`) can cite exact equation numbers. The note's claims are Astra's; the
Week 16 verification status of each is recorded in `outputs/week16_theory_meets_data/CLAIM_LEDGER.md`.

---

The strongest result is a **sharp characterization of what marginal class probabilities can—and cannot—tell us about query value**.

There are two proved statements:

- Exact margin sampling can achieve only \(1/(N-1)\) of the best one-query reduction in full-pool classification error. This factor is sharp.
- When every marginal probability is \(1/2\), uniform random selection is minimax among selectors that know only those marginals. Its exact guarantee can be calculated for **every pool size \(N\)** and is of order \(N^{-1/2}\).

Together with an explicit prediction–acquisition counterexample and a q20 pathology, these give a defensible theoretical addition to the thesis. **Their correctness is supported by proofs and independent checks; publication novelty remains unverified.**

The repository was inspected read-only. Computation was confined to external temporary scratch space.

## 1. Mathematical abstraction

Let
\[
X=\{x_1,\ldots,x_N\},\qquad Y=(Y_1,\ldots,Y_N)\in\{0,1\}^N.
\]

A simulation reveals one coordinate \(Y_j\) exactly.

Although the simulator is deterministic, a probability distribution over \(Y\) represents uncertainty about which fixed labeling is the true one. It does **not** represent fresh observation noise. Everything below may be conditioned on an already observed history.

Three different objectives arise:

1. **Discovery:** observe both labels.
2. **Prediction:** accurately classify the pool or a target population.
3. **Boundary recovery:** locate the separating set geometrically.

Their query utilities need not agree.

For the central theorem, use fixed, equally weighted, full-pool Hamming loss:
\[
L(Y,\widehat Y)=\frac1N\sum_{i=1}^N
\mathbf1\{Y_i\ne\widehat Y_i\}.
\]

Write
\[
p_i=P(Y_i=1),\qquad
u_i=\min(p_i,1-p_i).
\]
The current Bayes risk is
\[
R=\frac1N\sum_i u_i.
\]

Define the value of querying \(j\) by
\[
\Delta_j
=
R-\mathbb E_{Y_j}\left[
\min_{\widehat Y}
\mathbb E[L(Y,\widehat Y)\mid Y_j]
\right].
\]

All query rules receive the same ideal Bayesian update after the query. This isolates **selection quality** from differences in model fitting.

Crucially, the evaluation set remains fixed and includes the queried point. The resulting approximation guarantees do not automatically apply to disjoint held-out targets, historical q20 AULC, or Hausdorff loss.

## 2. Candidate theorem map

| Direction | Result of the investigation | Recommended priority |
|---|---|---|
| Better prediction versus better acquisition | Strict superiority in Brier score, log loss and overall classification risk can coexist with arbitrarily worse margin-induced query value | Central counterexample |
| Exact margin sampling | Sharp \(1/(N-1)\) approximation guarantee for one-query full-pool Hamming reduction | Central theorem |
| Selection using only marginals | Exact minimax guarantee for uniform selection when all marginals are \(1/2\) | Strongest publication candidate |
| q20 under imbalance | Explicit reversal between q20 accuracy and boundary localization, matching the implemented construction | Central methodological proposition |
| Finite-pool boundary metric | Hausdorff distance between geometric cut edges, with an approximation lemma under coverage and boundary regularity | Useful metric |
| Rare-class discovery | Exact distribution, minimax baseline, and a necessary-and-sufficient tail-enrichment condition | Supporting propositions |
| Discovery versus refinement | Full-history decomposition and a stopping-transcript information bound | Supporting lemma |
| Physics prior under shift | Exact regularized-regression example reproducing the qualitative empirical pattern | Explanatory example |
| Coverage from binary signs | Lipschitz or RKHS norm upper bounds alone do not restrict finite-pool sign patterns | Important negative result |

The first four directions deserve most of the thesis space. The others explain assumptions and prevent stronger but false interpretations.

## 3. Strongest theorem/result

### Theorem 1: exact query value and the sharp margin bound

Define spins and their moments:
\[
S_i=2Y_i-1,\qquad
m_i=\mathbb E S_i,\qquad
c_{ij}=\mathbb E[S_iS_j].
\]

Here \(c_{ij}\) is an **uncentered second moment**, not generally a covariance.

Then
\[
\boxed{
\Delta_j
=
\frac1{2N}\sum_{i=1}^N
\bigl(|c_{ij}|-|m_i|\bigr)_+.
}
\tag{1}
\]

Let \(j_{\mathrm{mar}}\) maximize \(u_j\), equivalently minimize \(|p_j-1/2|\), and let
\[
\Delta^\star=\max_j\Delta_j.
\]
For every joint distribution of binary labels and \(N\ge2\),
\[
\boxed{
\Delta_{j_{\mathrm{mar}}}
\ge
\frac{\Delta^\star}{N-1}.
}
\tag{2}
\]

The constant is sharp. For \(N=2\), exact margin sampling is always optimal. For \(N\ge3\), sharpness can be approached with a unique margin maximizer.

Equation (1) is a binary specialization of established expected-error-reduction reasoning. The precise sharp comparison in (2) is the more promising contribution.

### Theorem 2: exact minimax value of marginal-only selection

Suppose
\[
p_i=\frac12\qquad\text{for every }i.
\]

This means balanced **posterior marginals**, not necessarily balanced realized class counts.

Let \(\mathcal P_N\) contain all joint binary distributions with these marginals. A selector sees the marginals but not the dependence structure, so it chooses a distribution \(q=(q_1,\ldots,q_N)\) over queries. Its performance is evaluated using the true joint-posterior Bayes utilities \(\Delta_j(P)\).

Put \(M=N-1\). Define
\[
a=\max\{z\in\mathbb Z_{\ge0}:z\le\sqrt M,\ z\equiv M\pmod2\},
\qquad b=a+2,
\]
and
\[
\tau_M=\frac{M+ab}{a+b},
\qquad
\kappa_N=\frac{N+2\tau_M}{N(1+\tau_M)}.
\]

Then
\[
\boxed{
\sup_q\inf_{P\in\mathcal P_N}
\frac{\sum_jq_j\Delta_j(P)}{\Delta^\star(P)}
=
\kappa_N.
}
\tag{3}
\]

**Uniform selection attains this minimax value for every \(N\ge2\).**

Some exact values are:

| \(N\) | 2 | 3 | 4 | 5 | 6 | 7 | 10 | 17 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| \(\kappa_N\) | \(1\) | \(5/6\) | \(7/10\) | \(3/5\) | \(5/9\) | \(1/2\) | \(2/5\) | \(5/17\) |

A simpler consequence is
\[
\boxed{
\kappa_N\ge\frac{1+\sqrt{N-1}}N
\sim N^{-1/2}.
}
\tag{4}
\]
Equality in (4) holds when \(N-1\) is a square.

The exact extremal distributions can be chosen so that **every possible labeling contains both classes**.

The information restriction concerns query selection only. This is not a claim that a learner can perform joint Bayesian updating from marginal probabilities alone. The minimax statement also permits the adversary to permute the dependence structure across the fixed coordinates; it assumes no informative geometry–label relationship.

## 4. Proof

### 4.1 Exact one-query value

Let \(e_{i\mid j}\) be the expected Bayes classification error at coordinate \(i\) after revealing \(S_j\).

For \(s\in\{-1,+1\}\),
\[
\mathbb E[S_i\mathbf1\{S_j=s\}]
=\frac{m_i+s c_{ij}}2.
\]

For each outcome \(S_j=s\), the optimal classification error is the smaller joint probability of \(S_i=+1\) and \(S_i=-1\). Summing over the query outcomes gives
\[
e_{i\mid j}
=
\frac12\left[
1-\frac{|m_i+c_{ij}|+|m_i-c_{ij}|}{2}
\right].
\]

Using
\[
|x+y|+|x-y|=2\max\{|x|,|y|\},
\]
we obtain
\[
e_{i\mid j}
=
\frac{1-\max\{|m_i|,|c_{ij}|\}}2.
\]

Because
\[
u_i=\frac{1-|m_i|}2,
\]
the error reduction at \(i\) is
\[
u_i-e_{i\mid j}
=
\frac12\bigl(|c_{ij}|-|m_i|\bigr)_+.
\]
Summing proves (1). The derivation also handles degenerate query probabilities because it uses joint, rather than divided conditional, probabilities.

### 4.2 The margin approximation factor

Write
\[
v_{i\leftarrow j}=u_i-e_{i\mid j},
\qquad
G_j=N\Delta_j=\sum_i v_{i\leftarrow j}.
\]

These quantities satisfy
\[
0\le v_{i\leftarrow j}\le u_i,
\qquad
v_{j\leftarrow j}=u_j.
\]

Let \(a\) be a margin maximizer and \(b\ne a\). Since \(u_a\ge u_b\),
\[
|m_a|\le |m_b|.
\]
The formula above, together with \(c_{ab}=c_{ba}\), gives
\[
e_{b\mid a}\le e_{a\mid b}.
\]
Therefore
\[
u_b+v_{a\leftarrow b}
\le
u_a+v_{b\leftarrow a}.
\]

It follows that
\[
\begin{aligned}
G_b
&=u_b+v_{a\leftarrow b}
+\sum_{i\notin\{a,b\}}v_{i\leftarrow b}\\
&\le u_a+v_{b\leftarrow a}
+\sum_{i\notin\{a,b\}}u_i\\
&\le G_a+(N-2)u_a\\
&\le (N-1)G_a.
\end{aligned}
\]
The last step uses \(G_a\ge u_a\). Taking \(b\) to be optimal proves (2).

### 4.3 Sharpness of the margin bound

Take one independent decoy
\[
D\sim\operatorname{Bernoulli}(1/2)
\]
and \(M=N-1\) identical labels
\[
Y_1=\cdots=Y_M=Z,
\qquad
Z\sim\operatorname{Bernoulli}(1/2+\eta),
\]
where \(0<\eta<1/8\).

Exact margin uniquely chooses \(D\). Its gain is
\[
\Delta_D=\frac1{2N}.
\]

Querying any cluster point reveals all \(M\) cluster labels:
\[
\Delta_{\mathrm{cluster}}
=\frac{M(1/2-\eta)}N.
\]
Hence
\[
\frac{\Delta_D}{\Delta_{\mathrm{cluster}}}
=
\frac1{M(1-2\eta)}
\longrightarrow\frac1{N-1}
\quad\text{as }\eta\downarrow0.
\]

For \(N\ge3\), the cluster query is strictly better. Together with optimality at \(N=2\), this makes **three points the smallest strict counterexample** under the stated objective.

### 4.4 The exact lower bound for uniform selection

Now suppose every \(m_i=0\). Equation (1) becomes
\[
\Delta_j=\frac{s_j}{2N},
\qquad
s_j=\sum_i|c_{ij}|.
\]

Choose a maximizing column \(k\). Put
\[
t=s_k-1,\qquad A=\sum_j s_j.
\]
For a uniform query \(J\),
\[
\frac{\mathbb E\Delta_J}{\Delta^\star}
=\frac{A}{N(1+t)}.
\tag{5}
\]

The diagonal contributes \(N\), and the off-diagonal entries touching \(k\) contribute \(2t\). Therefore
\[
A\ge N+2t.
\tag{6}
\]

For \(i\ne k\), choose \(\sigma_i=\operatorname{sign}(c_{ik})\), assigning either sign when the entry is zero, and define
\[
W=\sum_{i\ne k}\sigma_i S_iS_k.
\]
Then
\[
\mathbb EW=t.
\]

Because \(W\) is a sum of \(M\) signs,
\[
W\in\{-M,-M+2,\ldots,M\}.
\]
The integers \(a,b\) in the theorem are adjacent on this lattice. Thus every possible \(W\) satisfies
\[
(W-a)(W-b)\ge0,
\]
which yields
\[
\mathbb EW^2\ge(a+b)t-ab.
\tag{7}
\]

Expanding the square,
\[
\mathbb EW^2
=
M+
\sum_{\substack{i,j\ne k\\i\ne j}}
\sigma_i\sigma_jc_{ij}.
\]
Consequently, the sum of absolute off-diagonal entries away from \(k\) is at least \(\mathbb EW^2-M\). Combining this with the diagonal and the entries touching \(k\),
\[
A\ge1+(2+a+b)t-ab.
\tag{8}
\]

Equations (5), (6), and (8) imply
\[
\frac{\mathbb E\Delta_J}{\Delta^\star}
\ge
\max\left\{
\frac{N+2t}{N(1+t)},
\frac{1+(2+a+b)t-ab}{N(1+t)}
\right\}.
\]

For \(N>2\), the first expression decreases with \(t\). The second increases, since its derivative has positive numerator
\[
(a+1)(b+1).
\]
Their intersection is
\[
t=\frac{M+ab}{a+b}=\tau_M.
\]
The maximum is therefore at least its value at this intersection, namely \(\kappa_N\).

For \(N=2\), the first expression is identically one, and the same conclusion holds.

### 4.5 A genuine binary distribution attaining equality

Let \(R\) be a fair sign. Independently draw
\[
W\in\{a,b\},
\qquad
P(W=b)=\frac{M-a^2}{b^2-a^2}.
\]

Conditional on \(W\), choose uniformly an \(M\)-vector of signs
\[
(V_1,\ldots,V_M)
\quad\text{with}\quad
\sum_iV_i=W.
\]
The parity condition ensures that such sign vectors exist for every value receiving positive probability.

Define the root and leaves by
\[
S_0=R,\qquad S_i=-RV_i.
\]

All marginals are fair. Direct calculation gives
\[
\mathbb EW=\tau_M,\qquad \mathbb EW^2=M.
\]
Exchangeability implies
\[
\mathbb E[S_0S_i]=-\frac{\tau_M}{M}.
\]

For \(M\ge2\),
\[
M=\mathbb E\left(\sum_iV_i\right)^2
=M+M(M-1)\mathbb E[V_1V_2],
\]
so distinct leaves have zero correlation.

Thus
\[
s_{\mathrm{root}}=1+\tau_M,
\qquad
s_{\mathrm{leaf}}=1+\frac{\tau_M}{M},
\]
and
\[
A=N+2\tau_M.
\]
Substitution into (5) gives equality.

For \(M=1\), the construction simply gives two opposite signs and the result is immediate.

Because \(W\ge0\), at least one \(V_i=+1\). That leaf has sign opposite to the root. Hence every world contains both labels.

### 4.6 Minimax optimality

Consider any marginal-only selector \(q\). All coordinate marginals are identical, and the hidden root can be placed at a coordinate selected with probability
\[
p\le\frac1N.
\]

Under the equality distribution, the selector's ratio is
\[
\frac{
p(1+\tau_M)+(1-p)(1+\tau_M/M)
}{
1+\tau_M
}.
\]
This increases with \(p\), so it is at most its value at \(p=1/N\), which is \(\kappa_N\).

Uniform selection guarantees \(\kappa_N\), while every marginal-only selector has a distribution on which it achieves at most \(\kappa_N\). This proves (3).

### 4.7 Checks performed

The proofs were supplemented by:

- Exhaustive finite probability grids for \(N=2,3\), comprising 8,206 joint distributions, for the margin theorem.
- Further random joint-law checks.
- 2,400 additional binary correlation laws for the refined all-\(N\) bound.
- Enumeration of the equality construction's complete sign support through \(N=14\) in an independent audit.
- Exact finite checks of the q20 construction below.

These checks are supporting evidence; the proofs establish the results.

## 5. Counterexamples

### 5.1 A strictly better predictor can induce an arbitrarily worse query

Use the decoy–cluster distribution from the sharpness proof.

Predictor \(A\) reports the exact probabilities:
\[
p_A(D)=\frac12,\qquad
p_A(Y_i)=\frac12+\eta.
\]

Define predictor \(B\) by
\[
p_B(D)=\frac12+2\eta,
\]
\[
p_B(Y_1)=\frac12-\frac\eta2,
\qquad
p_B(Y_i)=\frac12+\frac{3\eta}{2}\quad(i\ge2).
\]

Then:

- \(A\) uniquely selects the decoy.
- \(B\) uniquely selects cluster point \(Y_1\).
- \(A\) has strictly smaller expected Brier score and log loss at **every coordinate**.
- With the usual positive tie decision at \(1/2\), \(A\) also has strictly smaller overall expected classification error.

The probability vectors can be arbitrarily close:
\[
\|p_A-p_B\|_\infty=2\eta.
\]

For average Brier loss,
\[
R_{\mathrm{Br}}(B)-R_{\mathrm{Br}}(A)
=
\frac{\eta^2(M+24)}{4(M+1)}>0.
\]
For classification error,
\[
R_{01}(B)-R_{01}(A)
=\frac{2\eta}{M+1}>0.
\]
The log-loss excess is the average of strictly positive Bernoulli KL divergences and tends to zero with \(\eta\).

Yet
\[
\frac{\Delta_{\mathrm{query}(A)}}
{\Delta_{\mathrm{query}(B)}}
=
\frac1{M(1-2\eta)}.
\]

Therefore, for every \(\varepsilon>0\) and \(\gamma>0\), we can choose \(M,\eta\) so that:

- the predictors are within \(\varepsilon\);
- their Brier and log-loss differences are positive but below \(\varepsilon\);
- \(A\) is also better in classification risk;
- \(A\)'s selected query has less than \(\gamma\) times the value of \(B\)'s.

For \(M=100,\eta=0.01\):

| Quantity | Value |
|---|---:|
| Brier disadvantage of \(B\) | \(0.0000306931\) |
| Classification disadvantage of \(B\) | \(0.000198020\) |
| Query gain induced by \(A\) | \(0.00495050\) |
| Query gain induced by \(B\) | \(0.485149\) |

The worse predictor selects a query with **98 times the expected Hamming-risk reduction**.

This is an expected-risk comparison over fixed possible worlds. It does not claim that \(A\) predicts every realized label better.

### 5.2 The full-pool guarantee disappears for disjoint held-out targets

Let the candidate pool contain:

- a fair decoy independent of every test label;
- a less uncertain candidate whose label determines all test labels.

Exact margin selects the decoy. Its held-out gain is zero, while the other candidate has positive gain.

Thus no positive approximation factor follows in this setting.

This directly prevents interpreting Theorem 1 as a guarantee for the thesis's held-out q20 endpoint.

### 5.3 q20 can reverse geometric boundary quality

The inspected q20 implementation (`src/external_validation/analysis.py:20`) standardizes the full evaluation batch, computes nearest-opposite-class distances there, and retains the closest 20% of test points.

Fix \(m\ge4\) and \(0<\varepsilon<1/(5m)\). Take the \(5m\)-point test set
\[
T=\{-2,-\varepsilon,\varepsilon,2\varepsilon,\ldots,(5m-2)\varepsilon\},
\]
with
\[
y(x)=\mathbf1\{x>0\}.
\]
Add training points \(-R,+R\), \(R>4\). Embed the construction in four dimensions by holding the other coordinates constant.

Standardization multiplies all relevant distances by a common positive factor. Before scaling,
\[
d_{\mathrm{opp}}(-2)=2+\varepsilon,
\]
\[
d_{\mathrm{opp}}(-\varepsilon)=2\varepsilon,
\qquad
d_{\mathrm{opp}}(j\varepsilon)=(j+1)\varepsilon.
\]

Therefore
\[
S_{20}=\{-\varepsilon,\varepsilon,\ldots,(m-1)\varepsilon\}.
\]
The selection cutoff is strict, so tie-breaking does not affect the result.

Compare thresholds
\[
\widehat y_A(x)=\mathbf1\{x>-1\},
\qquad
\widehat y_B(x)=\mathbf1\{x>(m-\tfrac32)\varepsilon\}.
\]

Their scores are:

| Estimator | q20 accuracy | Boundary Hausdorff error |
|---|---:|---:|
| \(A\) | \((m-1)/m\) | \(1\) |
| \(B\) | \(2/m\) | \((m-\tfrac32)\varepsilon\) |

Taking
\[
\varepsilon_m=\frac1{100m^2}
\]
gives
\[
\operatorname{Acc}_{q20}(A)\to1,\qquad
\operatorname{Acc}_{q20}(B)\to0,
\]
while \(A\)'s localization error stays at one and \(B\)'s tends to zero.

Both estimators have nonempty boundaries. The q20 subset contains both classes.

At \(m=100\), the accuracies are \(0.99\) and \(0.02\), while the localization errors are \(1\) and \(0.0000985\).

This proves failure over unrestricted sampling designs. It does not assert inconsistency under every fixed sampling distribution with suitable density and regularity assumptions.

### 5.4 Equal discovery times do not imply equal refinement states

Let \(\Theta\) be a fair bit and define
\[
(Y_a,Y_b,Y_c,Y_d)=(0,1,\Theta,1-\Theta).
\]

Querying \(a,b\) discovers both classes at \(T=2\) but learns nothing about \(\Theta\). The remaining full-pool Bayes risk is \(1/4\).

Querying \(c,d\) also gives \(T=2\), but determines every label. Its remaining risk is zero.

Thus \(T\) alone cannot summarize the information supplied by initialization.

## 6. Corollaries and supporting results

### 6.1 Conditions under which acquisition guarantees become possible

**Pairwise independence makes exact margin optimal.** If labels are pairwise independent, then
\[
c_{ij}=m_im_j\qquad(i\ne j).
\]
Hence \(|c_{ij}|\le|m_i|\), all off-diagonal terms in (1) vanish, and
\[
\Delta_j=\frac{u_j}{N}.
\]

A more general sufficient condition concerns estimation of the joint moments.

Suppose estimates satisfy
\[
\max_i|\widehat m_i-m_i|\le\epsilon_m,
\qquad
\max_{i,j}|\widehat c_{ij}-c_{ij}|\le\epsilon_c.
\]
Construct \(\widehat\Delta_j\) using (1). Since absolute value and positive part are 1-Lipschitz,
\[
|\widehat\Delta_j-\Delta_j|
\le\frac{\epsilon_m+\epsilon_c}{2}.
\]
If \(\widehat j\) maximizes the estimated utility, then
\[
\boxed{
\Delta^\star-\Delta_{\widehat j}
\le\epsilon_m+\epsilon_c.
}
\]

This supplies a meaningful sufficient condition: control of marginal probabilities **and pairwise dependence** controls one-step acquisition regret. Marginal predictive accuracy alone does not.

There is also an objective-specific reversal. For noiseless revelation,
\[
I(Y;Y_j)=H(Y_j).
\]
Exact margin therefore maximizes the one-query reduction in **joint label entropy**. Its failure for Hamming loss does not make it suboptimal for every information objective.

### 6.2 Exact finite-pool class-discovery complexity

Suppose the pool contains \(n_0,n_1\ge1\), with \(N=n_0+n_1\), and is queried in uniformly random order. Let \(T\) be the first time both classes have appeared.

For \(k\ge1\),
\[
\boxed{
P(T>k)
=
\frac{\binom{n_0}{k}+\binom{n_1}{k}}{\binom Nk},
}
\tag{9}
\]
where impossible binomial coefficients are zero. Separately, \(P(T>0)=1\).

The two terms correspond to all queried labels being zero or all being one.

Let \(D_c\) be the first position of class \(c\). Since one class appears at position one,
\[
T=D_0+D_1-1.
\]
The \(n_c+1\) gaps around the uniformly positioned class-\(c\) points have equal expected size, giving
\[
\mathbb ED_c=\frac{N+1}{n_c+1}.
\]
Thus
\[
\boxed{
\mathbb ET
=
\frac{N+1}{n_0+1}
+
\frac{N+1}{n_1+1}
-1.
}
\tag{10}
\]

The exact \(1-\delta\) discovery budget is the smallest integer \(k\) for which (9) is at most \(\delta\).

For a designated rare class of size \(r\), its first-hit time \(D\) satisfies
\[
P(D>k)
=
\frac{\binom{N-r}{k}}{\binom Nk}
=
\frac{\binom{N-k}{r}}{\binom Nr}
\le
\min\left\{
(1-r/N)^k,\ (1-k/N)^r
\right\},
\]
and
\[
\mathbb ED=\frac{N+1}{r+1}.
\]
The geometric approximation \(N/r\) overstates this mean by
\[
\frac{N-r}{r(r+1)}.
\]

For fixed \(r\) and \(N\to\infty\),
\[
T/N\Rightarrow\operatorname{Beta}(1,r).
\]
If instead \(r\to\infty\) while \(r/N\to0\),
\[
(r/N)T\Rightarrow\operatorname{Exp}(1).
\]
These are different rare-class asymptotic regimes.

For the **whole** \(136\)-point pool with counts \(12,124\), uniform sampling gives:

| Quantity | Exact-formula value |
|---|---:|
| \(\mathbb ET\) | \(10.63446\) |
| \(P(T>9)\) | \(0.42394\) |
| \(P(T>16)\) | \(0.20787\) |
| 95% discovery budget | \(29\) |
| 99% discovery budget | \(42\) |

These are whole-pool reference calculations, not estimates for the historical folds.

**Minimax implication.** Without assumptions connecting features to labels, these uniform-order formulas are also the optimal worst-case randomized guarantees over label assignments with fixed counts.

To see this, place a uniform prior over all assignments with those counts. After any adaptive history, labels on the remaining coordinates are exchangeable. No selection rule changes the next-label distribution. This gives a lower bound for every policy. A uniformly random ordering attains the same distribution for every fixed assignment, proving minimax optimality.

### 6.3 Tail enrichment is exactly the right assumption for first-hit improvement

Let a predefined score tail \(A\subseteq X\) have size \(M\) and contain \(s\ge1\) rare labels. Let the whole pool contain \(r\) rare labels.

Let \(D_A\) and \(D_X\) be first-rare-hit times under uniform sampling without replacement from the tail and full pool respectively. Then
\[
\boxed{
D_A\le_{\mathrm{st}}D_X
\quad\Longleftrightarrow\quad
\frac{s}{M}\ge\frac rN.
}
\tag{11}
\]

Necessity follows by comparing first-query success probabilities.

For sufficiency, after \(j\) failures the success hazards are
\[
\frac{s}{M-j}
\quad\text{and}\quad
\frac r{N-j}.
\]
Their comparison reduces to
\[
sN-rM+j(r-s)\ge0,
\]
which holds because of enrichment and \(s\le r\). Multiplying failure probabilities proves stochastic dominance.

Also,
\[
\mathbb ED_A=\frac{M+1}{s+1}.
\]

This theorem concerns the first observation of a designated class. It becomes a two-class result if a common-class anchor is already known. A tail containing only rare labels would otherwise fail to discover both classes.

**Weak global prediction can coexist with large discovery gains.**

Take \(N=r^2\), \(r\ge4\), and a score identifying a three-point tail containing one rare and two common points. Place the other \(r-1\) rare points outside.

Both score-conditioned rare probabilities are below \(1/2\). Consequently, the score's Bayes classifier is still the constant common-class classifier: it provides no classification-error improvement.

Its rare-oriented AUC is
\[
\frac12+\frac12\left(\frac1r-\frac2{N-r}\right)\to\frac12.
\]
Its improvement over the constant-prevalence predictor in Brier risk is
\[
\frac{(N-3r)^2}{3N^2(N-3)}\to0.
\]
Its log-loss improvement also tends to zero, since it is at most the entropy of the tail indicator, \(h_2(3/N)\).

Nevertheless, querying the tail discovers both classes by three queries, with
\[
\mathbb ET_{\mathrm{tail}}=\frac73,
\]
whereas full-pool uniform discovery has \(\mathbb ET\sim r\).

The discovery speedup is unbounded even though global classification improvement is zero and AUC approaches chance.

The assumption is that the score tail is specified without inspecting the unseen labels. This construction does not establish that any particular empirical \(\log h\) threshold satisfies it.

### 6.4 Discovery/refinement decomposition and a nontrivial information bound

For any integrable terminal loss \(L_B\),
\[
\mathbb EL_B
=
\mathbb E[L_B\mathbf1\{T>B\}]
+
\sum_{t=2}^B
P(T=t)\,
\mathbb E[L_B\mid T=t].
\]

This is exact but elementary. A constant \(R_{\mathrm{fail}}\) is justified only if the specified fallback actually has constant conditional risk.

The refinement state is the **full history \(H_T\)**. Section 5.4 proves that \(T\) is insufficient.

A more useful consequence follows from the restricted form of a discovery transcript.

Let a finite random hypothesis \(\Theta\) determine the entire labeling, with distinct hypotheses identifiable by labels. Assume every hypothesis contains both classes. Let \(U\) encode independent policy randomization. Suppose \(Q\ge T\) is the number of queries used for zero-error identification of \(\Theta\).

Conditional on \(U\), the labels observed through discovery are completely specified by:

- the first label \(Y_1\);
- the stopping time \(T\).

All labels before \(T\) equal \(Y_1\), and the last is its opposite. Query locations are then reconstructed from the policy.

Therefore
\[
I(\Theta;H_T\mid U)
=
H(Y_1,T\mid U)
\le1+H(T).
\]

After discovery, a binary decision tree identifying the remaining hypothesis requires expected depth at least its conditional entropy. Hence
\[
\boxed{
\mathbb EQ
\ge
\mathbb ET+H(\Theta)-I(\Theta;H_T\mid U)
\ge
\mathbb ET+H(\Theta)-1-H(T).
}
\tag{12}
\]

All entropies are in bits.

In particular, if \(T\le b\), the discovery transcript contains at most
\[
\log_2[2(b-1)]
\]
bits. If \(T\) is deterministic, it contains at most one bit.

This makes the separation precise: fast, reliable discovery can leave nearly all of a complex boundary-identification problem unresolved.

### 6.5 A useful finite-pool boundary metric

Fix a geometric graph \(G=(V,E)\). Define its cut under labeling \(y\):
\[
C_y=\{\{u,v\}\in E:y_u\ne y_v\}.
\]

First, an important limitation. If
\[
A=\{v:y_v\ne\widehat y_v\},
\]
then
\[
\boxed{
C_y\triangle C_{\widehat y}=\delta_G(A).
}
\tag{13}
\]
This follows by taking the XOR of endpoint errors.

Thus cut disagreement measures the graph boundary of the classification-error set. For an unweighted graph,
\[
|C_y\triangle C_{\widehat y}|
\le d_{\max}\min\{|A|,|A^c|\}.
\]

But on a path with one true cut and one displaced predicted cut, symmetric difference equals two for **every nonzero displacement**. It does not measure how far the boundary moved.

A better geometric object is the following endpoint-matching distance between edges:
\[
\rho(\{u,v\},\{a,b\})
=
\min\left\{
\max(\|x_u-x_a\|,\|x_v-x_b\|),
\max(\|x_u-x_b\|,\|x_v-x_a\|)
\right\}.
\]
With distinct feature vectors, this is a metric: endpoint matchings compose, which proves the triangle inequality.

Define the Hausdorff distance between cut sets:
\[
H_\rho(C,D)=
\max\left\{
\max_{e\in C}\min_{f\in D}\rho(e,f),
\max_{f\in D}\min_{e\in C}\rho(e,f)
\right\}.
\]

For empty cuts, set the distance to a nonempty cut equal to a fixed \(D_0\) at least the edge-space diameter, and set empty-to-empty distance to zero.

This construction has useful properties:

- It is a metric on cut sets.
- On a connected graph, zero distance identifies the labeling up to global complement.
- One correctly matched anchor per connected component removes the orientation ambiguity.
- On an equally spaced path with single cut edges \(e_i,e_j\),
  \[
  H_\rho(\{e_i\},\{e_j\})=|i-j|h,
  \]
  exactly the spatial displacement.
- Class prevalence is not used as a normalization. Nevertheless, changing the sampling design or graph can change the metric; it is not universally imbalance invariant.

There is also a geometric approximation guarantee.

Suppose \(X\) is an \(\varepsilon\)-net of a bounded convex domain. Join all pairs within \(6\varepsilon\). Suppose the true and predicted boundaries are compact interior boundaries with two-sided tubular neighborhoods wider than \(2\varepsilon\). Then
\[
\boxed{
\left|
H_\rho(C_y,C_{\widehat y})
-d_H(\Gamma,\widehat\Gamma)
\right|
\le12\varepsilon.
}
\tag{14}
\]

**Proof.** At each boundary point, normal offsets of length \(2\varepsilon\) have opposite signs. The net supplies sample points within \(\varepsilon\) of each offset, hence within \(3\varepsilon\) of the boundary point. Their connecting edge is a cut edge of length at most \(6\varepsilon\).

Conversely, every cut edge crosses the boundary, so its midpoint is within \(3\varepsilon\) of it. Thus each cut-midpoint set approximates its continuous boundary within \(3\varepsilon\).

The Hausdorff distances between the two midpoint sets and between the two boundaries consequently differ by at most \(6\varepsilon\). For edges of length at most \(6\varepsilon\),
\[
\|m_e-m_f\|\le\rho(e,f)\le\|m_e-m_f\|+6\varepsilon.
\]
Combining these inequalities proves (14).

For the thesis, report geometric distance and orientation or rare-class performance separately. NEW-136 does not establish the coverage or tubular-neighborhood assumptions needed for (14).

### 6.6 A physics-prior example reproducing the transfer pattern

Consider a two-location noiseless regression surrogate. At location \(i\), there are \(n_i\) source observations with value \(f_i\). Fit
\[
\widehat f_\mu
=
\arg\min_g
\sum_i n_i(g_i-f_i)^2+\lambda\sum_i(g_i-\mu_i)^2.
\]
This is ridge regression with identity kernel and prior mean \(\mu\). Its solution satisfies
\[
\widehat f_{\mu,i}-f_i
=
\frac{\lambda}{n_i+\lambda}(\mu_i-f_i).
\]

For target weights \(q_i\),
\[
R_Q(\widehat f_\mu)-R_Q(\widehat f_0)
=
\sum_i q_i
\left(\frac{\lambda}{n_i+\lambda}\right)^2
(\mu_i^2-2\mu_if_i).
\tag{15}
\]

Take
\[
f=(10,1),\quad \mu=(10,3),\quad
n=(9,1),\quad \lambda=1,
\]
with source weights \(P=(0.9,0.1)\) and target weights \(Q=(0.1,0.9)\).

The resulting squared risks are:

| Model | Source risk | Target risk |
|---|---:|---:|
| Physics mean alone | \(0.400\) | \(3.600\) |
| Physics mean plus regularized correction | \(0.100\) | \(0.900\) |
| Generic zero-mean fit | \(0.925\) | \(0.325\) |

The correction improves physics-only prediction in both domains. The physics-informed fit wins on the source, while the generic fit wins on the target.

The mechanism is explicit: target mass shifts toward a region with prior bias and weaker source coverage. This is an explanatory regression example, not a theorem about the fitted M3 classifier.

## 7. Interpretation

The central distinction is between **uncertainty at a point** and **the effect of revealing that point on decisions elsewhere**.

Equation (1) makes this concrete:
\[
\text{query value}
=
\text{self-error removed}
+
\text{error removed elsewhere}.
\]

Margin sampling optimizes the first component. Predictive proper scores assess marginal probabilities. Neither automatically measures the second component.

The exact minimax theorem adds a stronger statement. Even when all marginal probabilities are perfectly known, the most useful point can be hidden in the dependence structure. Randomization provides a sharp guarantee, but its worst-case fraction still decreases as \(N^{-1/2}\).

For geometric objectives, the information requirements can increase further. Current expected graph-cut loss depends on pairwise label probabilities, but its one-query value can require third-order dependence.

For example, three independent fair bits and a distribution uniform on
\[
000,\ 011,\ 101,\ 110
\]
have identical one- and two-variable marginals. On a triangle, both have current Bayes cut-disagreement risk \(3/2\). After one query, the independent model retains risk \(3/2\); the parity model has risk \(1\), since the opposite edge becomes known.

Thus even accurate pairwise information for current boundary risk need not determine boundary-acquisition value. This is a specialization of an established parity-based limitation, rather than a separate novelty claim.

## 8. Connection to the empirical findings

The read-only Week 12 report (`outputs/week12_startup_and_transfer_development/COMPREHENSIVE_REPORT.md`) supports the motivating distinctions.

| Empirical observation | What the mathematics establishes |
|---|---|
| Adaptive physics startup improves discovery reliability | Tail enrichment can improve first-hit distributions without a strong global classifier |
| Downstream q20 changes little after improved startup | Discovery time does not determine the information remaining after startup |
| Better prediction does not consistently improve acquisition | Strict predictive-risk dominance can coexist with arbitrarily worse margin-induced query value |
| Always-Keyhole has mean-fold q20 accuracy \(0.6850\), above every complete protocol's mean primary endpoint | Nearest-opposite-distance subsets need not balance classes or preserve geometric boundary rankings |
| Physics plus discrepancy improves physics-only prediction, while generic models transfer better | Regularized correction can leave localized prior bias that becomes more costly under target reweighting |

The report gives the adaptive-startup contrast against matched margin8 as \(-0.000313\) in q20 AULC, with almost identical full balanced-accuracy AULCs. That is compatible with the discovery/refinement separation.

These theorems establish possible mechanisms and rule out universal implications. They do **not** identify which mechanism caused the observed campaign results, estimate causal contributions, or reopen the closed confirmatory run.

## 9. Novelty audit

The literature search covered expected error reduction, uncertainty sampling, graph active learning, discovery/search, Bernoulli level-set estimation, geometric losses, covariate shift, and extremal binary dependence.

### Expected-error reduction and uncertainty sampling

Roy and McCallum, 2001 (https://groups.csail.mit.edu/rrg/papers/icml01.pdf), already explain that highly uncertain outliers can be poor queries and formulate expected future-error reduction.

**Assessment: LOW novelty** for the general claim that uncertainty is not query value.

Mussmann et al., *Active Learning with Expected Error Reduction* (https://arxiv.org/abs/2211.09283), explicitly derive criteria from pairwise label marginals. Their discussion also explains why zero-one error reduction requires posterior decisions to change, and their appendix gives parity examples of limitations from restricted joint information.

**Assessment: LOW novelty** for equation (1) as an EER specialization and for the general moment-information distinction. The precise \(1/(N-1)\) sharp bound was not located in the reviewed material.

### Exact marginal-only minimax theorem

The closest additional mathematical connection is to extremal moments of partially independent binary variables. Pass and Spektor (https://arxiv.org/abs/1708.08775) study sharp Khintchine-type inequalities and exchangeable extremal Rademacher constructions.

Their problem differs from the one-query utility ratio here, but their work prevents treating exchangeable binary moment constructions themselves as new.

**Assessment: HIGHLY UNCERTAIN BUT PROMISING** for the exact acquisition minimax formulation, its all-\(N\) constant, and its attaining distribution. No equivalent theorem was found in the sources examined. That is not a priority determination.

### Discovery versus learning

Hospedales, Gong and Xiang, 2012 (https://homepages.inf.ed.ac.uk/thospeda/papers/hospedales2012dpea.pdf), directly study joint active discovery and learning.

Dasarathy, Nowak and Zhu's \(S^2\), 2015 (https://proceedings.mlr.press/v40/Dasarathy15.pdf), separates discovery of monochromatic components from boundary refinement. Its component balancedness is more specific than overall class prevalence.

**Assessment: LOW novelty** for the two-stage architecture, exact random-order calculations, and elementary entropy consequences. The tailored statements remain useful thesis exposition.

### Weak ranking and early discovery

The distinction between global ranking performance and early retrieval is established in the early-recognition literature, including Truchon and Bayly, 2007 (https://doi.org/10.1021/ci600426e).

**Assessment: LOW novelty** for the phenomenon; **MODERATE** for the value of the particular finite-pool separation as a thesis proposition, rather than as a standalone publication claim.

### Boundary losses and metrics

Singh, Scott and Nowak (https://arxiv.org/abs/0908.3593) study Hausdorff level-set estimation and the geometric assumptions needed for it. Kervadec et al. (https://proceedings.mlr.press/v102/kervadec19a.html) address the mismatch between regional losses and contour quality under imbalance.

**Assessment: LOW novelty** for Hausdorff boundary evaluation and the need for regularity. The exact q20 counterexample is valuable because it targets the actual evaluator, not because accuracy–geometry disagreement is unknown.

### Existing level-set acquisition theory

Letham et al., 2022 (https://proceedings.mlr.press/v151/letham22a.html), derive look-ahead acquisition functions for Bernoulli level-set estimation.

**Assessment: LOW novelty** for proposing look-ahead binary level-set acquisition. The present contribution should be framed around sharp limitations and information requirements, not as the invention of that approach.

### Physics priors and coverage

Covariate-shift effects in regularized kernel regression are established; see Ma, Pathak and Wainwright (https://arxiv.org/abs/2205.02986). The two-location example is an elementary illustration.

The norm-versus-sign issue also has close classical precedent, including the bounded-norm Gaussian-RBF classification discussion in Smola's thesis (https://alex.smola.org/papers/1998/Smola98.pdf).

**Assessment: LOW novelty** for these supporting examples.

## 10. Thesis usability

I recommend the following precise roles:

| Result | Thesis role |
|---|---|
| Exact utility formula | Lemma, explicitly connected to established EER |
| Sharp \(1/(N-1)\) margin bound | Main theorem |
| Exact marginal-only minimax value \(\kappa_N\) | Main theorem; strongest theoretical contribution candidate |
| Proper-score and classification dominance counterexample | Proposition following the main theorem |
| q20/Hausdorff reversal | Proposition in the evaluation methodology section |
| Geometric cut Hausdorff distance | Methodological definition with approximation lemma |
| Discovery distribution and enrichment condition | Supporting propositions |
| Stopping-transcript information bound | Supporting lemma |
| Physics-prior shift example | Worked example in the discussion |

A suitable chapter focus would be **"Prediction, Query Value, and Boundary Evaluation in Finite-Pool Active Learning."**

Historical q20 results should remain reported under their original definition. The geometric metric belongs in a separately identified theoretical or synthetic investigation.

## 11. Publication potential

The most credible paper direction is the theorem family on **sharp limits of query selection from marginal information**.

Before a publication claim, it needs:

1. **A focused priority audit** of the exact approximation ratios, including equivalent correlation-matrix and binary moment formulations.
2. **Independent mathematical review**, especially of the minimax information restriction and the role of evaluating queried points.
3. **A small robustness study** showing which conclusions persist when dependence is imperfect and marginals are slightly unbalanced.
4. **A clear treatment of target weighting and held-out evaluation.** The zero-ratio counterexample is already an important limitation.
5. **A disciplined separation between one-step guarantees and sequential performance.**

A further extension might make the paper more substantial, but it should follow from the theorem rather than begin another heuristic search.

No new real simulation campaign is required for this route. The LPBF experiments provide motivation and an application context; they do not supply external validation of the abstract worst-case models.

If the exact sharp bounds are already known, this remains a strong MSc theoretical chapter, but the standalone publication case would weaken substantially.

## 12. Best next theoretical experiment

The next experiment should test **robustness of the separation**, since the exact extremal examples have already been checked.

Use a single controlled finite-world study with two families.

**Family A: an imperfectly dependent cluster.**

Take one independent fair decoy and \(M\) labels
\[
Y_i=Z\oplus E_i,
\]
where
\[
Z\sim\operatorname{Bernoulli}(1/2+\eta),
\qquad E_i\overset{\mathrm{iid}}{\sim}\operatorname{Bernoulli}(\delta).
\]
Draw the whole world once; all subsequent observations are noiseless.

Fix
\[
M\in\{2,4,16,64,256\},
\quad
\eta\in\{0.003,0.01,0.03,0.1\},
\quad
\delta\in\{0,0.01,0.05,0.1,0.2\}.
\]

Compute exact marginal risks and one-query Bayes gains. Compare exact margin, uniform selection, and oracle EER. Use the perturbed predictor construction from Section 5 with the adjusted cluster marginal.

The question is whether tiny predictive differences still coexist with large acquisition differences after removing perfect label duplication.

**Family B: the exact minimax distributions.**

Use every \(N=2,\ldots,20\), plus \(N=50,100\). Generate the root-and-leaf distributions analytically. Record:

- uniform utility ratio;
- the proved \(\kappa_N\);
- deterministic tie-breaking under every possible root location;
- the corresponding oracle utility.

The purpose is to make the sharp result transparent and independently reproducible.

Keep the objectives separate: full-pool Hamming gain, disjoint held-out gain, and joint entropy reduction. No GP fitting or method tuning is needed. A disagreement with a claimed identity is a reason to repair the theorem or implementation, not to select a favorable metric.

## 13. Rejected ideas

- **"Discovery time is a sufficient state for refinement."** False: equal \(T\) can leave different posterior information.
- **"A better calibrated or lower-loss predictor must yield better margin queries."** False even when the better predictor reports exact probabilities.
- **"Margin is universally inferior as an information rule."** False: it is one-step optimal for joint-label entropy in the noiseless setting.
- **"A geometric q20 subset balances classes."** False: its majority prevalence can approach one while both classes remain represented.
- **"Cut-edge disagreement measures displacement."** False: on a path, every nonzero single-boundary displacement gives the same symmetric difference.
- **"Lipschitz continuity alone makes binary-sign coverage informative."** False on a finite pool. If the minimum point separation is \(d_{\min}>0\), every sign pattern can be assigned values \(\pm a\) with \(2a\le Ld_{\min}\), then extended to an \(L\)-Lipschitz function. A known lower bound on latent amplitude would change the problem, but binary labels alone do not supply it.
- **"A worst-case theorem explains the actual M3 acquisition path."** Unsupported. It establishes a possible failure mechanism, not an empirical causal diagnosis.
- **"A useful new acquisition algorithm follows immediately."** Unsupported. The proved result identifies the missing information and sharp limits; estimating that information reliably is a separate problem.
