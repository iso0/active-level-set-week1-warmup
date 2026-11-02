# Prospective v2 amendment: coherent within-gate correction

26 October 2026. Written after DEV v1, before any v2 numerical result. V1 remains
frozen and failed. This uses the one allowed mechanistic continuation; no prior,
threshold, location-bank or kernel-scale sweep is allowed afterwards.

Use all64 completed v1 paths, at the same nine paid prefixes, with their cached
global theta. The trained baseline is not refitted. Reuse the exact32 feature-only
centers, gates, variance0.36, half-null prior and location multiplicity. Replace
the compact within-gate covariance with a rank-one signed random coefficient:

    coherent: K_theta + 0.36 a_jr(x) a_jr(x')
    coherent_trace: K_theta + 0.36 m_jr.

Include cached strong and gated-v1 predictions. This isolates within-gate
correlation against v1; the trace control tests spatial placement at equal
integrated prior variance for the new correlation structure. It does not isolate
correlation and effective rank as separate factors; they change together.

For C0=K_DD+sigma^2 I, q=a_D' C0^-1 a_D, b=a_D'C0^-1 z,
s_beta^2=(1/0.36+q)^-1, and r(x)=a(x)-K_xD C0^-1 a_D,

    mu_new(x)=mu0(x)+r(x) s_beta^2 b
    var_new(x)=var0(x)+r(x)^2 s_beta^2
    log BF_new,0=[s_beta^2 b^2-log(1+0.36 q)]/2.

These identities follow Woodbury and the determinant lemma. They are conditional
on the same plug-in theta. The discrepancy alone has variance a(x)^2 s_beta^2;
the background posterior can also change outside the gate because observations
are reattributed. No guarantee of identical total predictions outside a gate is
claimed. Matrix references must verify means, variances and evidence to1e-8.

Screen: apply the SAME v1 thresholds, targets, world weighting and censoring.
Require coherent minus strong and coherent minus coherent_trace local-family
BA-AULC >=0.005, positive mean local-error reduction, and control-family BA harm
<0.01. Report the coherent minus gated-v1 contrast and both recalls/proper scores.
If the screen fails, do not create a large TEST or expensive selector queue.
If passed, freeze new independent TEST and outside-basis shapes before outcomes.

64 v2 prediction units plus one small independent numerical reference. No new
queries and no new background optimization. The original campaign ceilings remain
10,000 model requests,200,000 component solves,300,000 optimizer evaluations,
2000 reference solves. Charge each closed-form component update as a component
solve conservatively, but report actual dense factorizations separately. V1 used
77,824 reserved component solves and143,552 optimizer evaluations; v2 needs fewer
than80,000 additional component reservations and zero optimizer evaluations.
All reservations, including unused blocks, remain in the common attempt ledger.
Checkpoint completed prefix predictions; no reset of historical outcomes.

This amendment does not extend the27 October20:05:49 UTC deadline.
