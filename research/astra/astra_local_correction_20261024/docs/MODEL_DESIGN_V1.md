# Local correction v1: one finite, shrinkable gate mixture

## Observation and decision target

For public x in [0,1]^4, observe z=f(x)+epsilon at unit query cost. The working
likelihood is independent Gaussian epsilon with learned SD sigma. Evaluation
truth is the latent sign Y=1{f>=0}; it is not the sign of noisy z or a manually
recorded Keyhole label. Outlier, heteroscedastic and corruption worlds deliberately
violate this likelihood. Latent posterior variance excludes sigma^2; pre-query
innovation variance adds it once. Both moments are saved before revealing z.

All four models use probability p=P(f>=0|paid), with decision p>=0.5. This is a
fixed latent-boundary decision, Bayes-optimal for equal error costs under the
working posterior. BA is the primary evaluation metric; 0.5 is not generally its
population-optimal probability threshold under imbalance. Holding this rule fixed
isolates representation. We do not tune thresholds from evaluator class totals.

## Conditional Gaussian model and legitimate location learning

The baseline is the preceding strong Matérn-3/2 ARD GP. Its amplitude, four scales
and noise SD are estimated only from current paid observations, with the same
14 structural starts and a previous-fit warm start on refresh. Parameters refresh
at B8,12,16,20,24. All models on a common path use exactly this fitted background.
This deliberately isolates a covariance contribution before any joint re-fitting.

Let j index 32 candidate centers selected by a fixed feature-only random subset
of the public candidate inputs, and r in {0.45,0.9}. No outcomes select centers.
Use a_jr(x)=exp(-||x-c_j||^2/(2(r/2)^2)) and the historical compact correlation
W_r(x,x'). The alternatives are:

    strong:      K_theta
    compact:     K_theta + 0.36 W_r
    gated:       K_theta + 0.36 a_jr(x) a_jr(x') W_r
    trace_match: K_theta + 0.36 m_jr W_r,

where m_jr is the mean of a_jr(x)^2 over the fixed public reference inputs.
Thus each gated/trace pair has exactly the same integrated prior extra variance
on the evaluation distribution. Their posterior variances need not match.
Compact, gated and trace models each put mass 1/2 on the strong component and
divide the remaining 1/2 uniformly over their alternatives (two or 64).

Given the shared theta, w_j proportional to prior_j N(z;0,C_j), C_j=K_j+sigma^2 I.
All paid observations enter this likelihood once. The gate location is learned by
these weights, not by selecting a surprising label then pretending that selected
location had prior probability one. The fixed candidate bank is an approximation
to an unknown location prior; the log multiplicity cost is real. Posterior means,
variances and probabilities retain both within- and between-component uncertainty.
There is no ad hoc trigger, hard local activation or free true-region anchor.

This is exact finite-mixture conditioning **conditional on shared plug-in theta**,
not an exact hierarchical Bayesian posterior. Learning theta under the strong
null can absorb a local anomaly as noise. We will log this competing mechanism;
failure cannot establish that every jointly fitted nonstationary GP fails.

## Analytical discriminator and limits

For known background, independent noise variance s^2 and well-separated paid
points, a constant local variance t^2 gives

    log BF10 = -n log(1+r)/2 + r ||e||^2/[2(1+r)s^2],  r=t^2/s^2.

If one residual has mean A, E log BF10 > 0 requires
A^2/s^2 > n[(1+r)log(1+r)/r - 1]. A *known* one-location correction pays the
one-location penalty instead; an unknown uniform location mixture pays a
multiplicity penalty and averages likelihoods, not log likelihoods. This is a
restricted analytical example, not the historical explanation proved.

PSD follows v' D K D v=(Dv)' K(Dv)>=0. At a(x)=0, the correction's marginal
variance and cross-covariance vanish. As its amplitude tends to zero, every
alternative reduces to the same strong GP. If all gates equal one, gated and
compact coincide. A single outlier can still increase local posterior weight;
Bayesian shrinkage is not an outlier guarantee. A coherent monitor artifact and
a true local regime with the same z law are unidentifiable without another
legitimate channel. A badly covered center bank can miss a real structure.

## Acquisition boundary

The first stage changes no selector across the four models. It evaluates the
same feature-only maximin paths and, separately, paths chosen by the strong GP's
probability margin. All eight initial queries and subsequent hits are charged.
No free island initialization or truth-defined follow-up is provided. These are
matched-data model comparisons; local-model query efficiency is not yet tested.
Only a meaningful pilot prediction signal permits a frozen independent test and
a later cheap one-step selector. Two-step planning is excluded.
