# Joint empirical-Bayes gate mixture: fixed-data mechanism test

Prospective, 26 October 2026; written before this campaign's numerical outcomes.
The old V2 is the starting local structure. It integrated a coherent coefficient
at general-GP parameters learned under the null. We change only that parameter
learning objective, preserving gates, amplitude, data and posterior calculation.

For paid observations y_i=f(x_i)+epsilon_i, use independent Gaussian working
noise with SD sigma. The target is latent 1{f>=0}, not noisy sign or recorded
Keyhole. Uniform finite reference inputs define the evaluation distribution.
Fixed p>=.5 minimizes equal-cost pointwise sign error under the model, but need
not maximize BA under imbalance. It remains identical in all arms.

Let C0(theta)=K_Matern32_ARD(theta)+sigma² I (plus numerical jitter 1e-10).
theta contains log four length scales, log amplitude and log noise SD. Gate
a_jr(x)=exp(-||x-c_j||²/[2(r/2)²]), with the same 32 feature-only candidate
centers (seed91612), r=.45,.9. A single unknown component j is active, not a
simultaneous sum of64 corrections. Conditional on it, f=g+a_j beta_j,
beta_j~N(0,.36). The null prior is .5; each gate has .5/64. The coefficient and
component are integrated, rather than selecting a region from hidden truth.

For u_j=C0^-1 a_Dj, q_j=a_Dj' u_j, b_j=a_Dj' C0^-1 y,
v_j=.36/(1+.36q_j),

    ell_j = ell_0 - .5 log(1+.36q_j) + .5 v_j b_j²
    L(theta) = logsumexp(log prior_j + ell_j(theta))
    w_j = softmax(log prior_j + ell_j(theta))

Fixed-background local uses theta_N maximizing ell_0. Joint local uses theta_J
maximizing L, so lengths, amplitude and noise can respond to local explanation.
This is shared-hyperparameter empirical Bayes with conditional exact finite
mixture averaging. It is NOT integration over theta or a full Bayesian fit.
An optimized training objective is not held-out evidence of model benefit.

For D_k=partial C0/partial theta_k and alpha_j=C_j^-1 y,

    partial L/partial theta_k = .5 sum_j w_j
        tr[(alpha_j alpha_j' - C_j^-1) D_k].

One base Cholesky plus64 rank-one updates evaluates this gradient. Cost per
objective is O(n³+64n²), with six parameters; no64 separate optimizations.
For prediction residual r_j=a_*j-K_*D u_j,

    mu_j=mu_0+r_j v_j b_j; V_j=V_0+v_j r_j r_j'.

Average means and V_j+mu_j mu_j' then subtract the mixture mean outer product;
retain within AND between-component variance. p is the weighted Gaussian sign
probability, not a normal approximation to mixture moments. Observation variance
adds sigma² once; latent variance excludes it. The background and beta have
posterior covariance -K_*D u_j v_j; total f and beta covariance is r_j v_j.
Thus a correction can also reattribute the background outside the gate.

## Controls and identifiability

Six arms: original strong GP; fixed old coherent correction; extra-optimized
strong GP; fixed coherent correction at extra-optimized null theta; joint local;
joint trace-matched rank-one component (.36 mean_reference(a_j²), constant basis).
Last control has same integrated added prior variance and identical joint
inference but lacks spatial localization. All receive only public features and
current paid values. Evaluator truths are outside model inputs.

Each refresh uses old14 structural starts plus paid-only base/warm starts, same
bounds and tolerances. Strong extra control gets the same starts as joint, plus
deterministic additional starts until its optimization CPU reaches the joint
optimization CPU, with a prospectively fixed128-total-start cap. It also receives
the joint optimum as an extra null-objective start, a deliberately strong
data-only control. Its cost includes that assistance separately; it is a
diagnostic, not a cheaper deployable algorithm. Record actual CPU and any cap.
Candidate includes the fresh baseline-fit cost that supplies its warm start.
No setting is selected by scientific held-out performance.

At tau²=0 every component and objective reduces to the strong GP at the same
theta. Optimization may still find a different numerical optimum; the limit
test compares functions/derivatives/predictions at fixed theta. Multiple local
locations and background scales can be weakly identified. If C0=B+kappa aa',
a'C0^-1a=q0/(1+kappa q0)<=1/kappa: decomposition uncertainty need not vanish,
even if the sum predicts well. Shared-theta mixture fitting may remain dominated
by the null and includes neither full hyperparameter uncertainty nor multiple
simultaneous anomalies. These are stated restrictions, not rescue arguments.

Log theta shifts, bound hits, objective gains, null weight, gate entropy,
lambda=.36q, whitened residual b/sqrt(q), coefficient variance, and label flips.
Compare their changes with actual sign error. Lower noise alone does not prove
the old model had mistaken physical structure for noise. An outlier or monitor
bias can also be shared coherently. True f=g+delta and biased monitor z=g+delta+e
with true f=g are observationally identical for this channel; no algorithm can
resolve that ambiguity without information or assumptions beyond these data.

## Literature and contribution boundary

Ba–Joseph, Composite Gaussian Process Models for Emulating Expensive Functions,
§3.2 Theorem1 and §4 Eqs20–23, explicitly discuss interactions and simultaneous
global/local estimation: [Reference (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-6b3efe42d1e3571b) . Davis–Hans–Santner,
Prediction Using a Bayesian Heteroscedastic Composite Gaussian Process,
[Reference (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-1bc5577cf87fae38) uses a richer hierarchical composite model and
MCMC. Our finite discrete gate mixture and plug-in theta are a constrained
implementation, not a new composite-GP invention. Derivatives and conditioning
are established GP calculus (GPML Chapters2,5). The experiment tests whether
joint fitting explains a particular previous failure under fair paid-data and
optimization controls, and whether any benefit survives cost/generalization.
