# When a local verification has value: a finite, exact example

Registered 19 October 2026 while the frozen v2 TEST is running. No v2 DEV or
TEST scientific endpoints were inspected to construct this check. This is an
analytical diagnostic, not another method, generator sweep, or confirmatory
comparison. It changes none of the running experiments. The earlier v1.1 failure
is the motivation: a surprise gate and a useful spatial representation are
different mechanisms.

Consider a known region R with reference mass w. Its sign is a common latent
H~Bernoulli(q); two distinct available points in R give conditionally independent
binary observations of H, each flipped with probability eta<1/2. Elsewhere are
two independent regions, each with mass g and sign Bernoulli(1/2), each learned
without error by one query. Remaining mass has a known negative sign. The loss
is reference-weighted latent sign error, not the number of positive observations.
These known regions are a finite analytical construction; the campaign selector
does not receive the synthetic island's location or membership.

For one local observation, posterior expected error on R is

    w [min(q(1-eta), (1-q)eta) + min(q eta, (1-q)(1-eta))]
      = w min(q, 1-q, eta).

Consequently its one-step value is w[min(q,1-q)-eta]_+. A global query has value
g/2. A local query is preferred exactly when the former exceeds the latter.
This proves a restricted, conditional statement: coherent regional mass,
posterior uncertainty and observation quality matter together. Locality alone
does not provide value. Unknown geometry or unreliable neighborhood sharing
violates this toy's assumptions; the equation is not a guarantee for the GP.

A two-query example shows why the one-step comparison is incomplete. Set
q=.01, w=.5, eta=.05, g=.003. A single local query has zero sign-error reduction,
whereas a global query reduces error by .0015. But after a positive local
observation (probability .059), the regional posterior becomes .0095/.059.
The optimal second query is another local observation; after a negative one,
query a global region instead. Expected total reduction is

    .003275 + .941*.0015 = .0046865,

versus .003 for two global queries. Initial risk is .008, so exact two-step risk
is .0033135, compared with greedy risk .005. This is a horizon effect under a
correct model, not a violation of the earlier one-step set-inclusion inequality.
It gives a possible reason for paying for corroboration, but does not prove that
our six-query local heuristic approximates this Bellman policy well.

Two counterexamples preserve the same setup. Raising eta to .30 makes the
global/global policy optimal (risk .005); reducing w to .01 also makes it optimal
(risk .0001). An uncertain coherent case, q=.5, w=.1, eta=.05, g=.06, instead
has a greedy preference for a local query followed by a global query (risk .035).
For the exact two-step optimum, global then local attains the same risk. Thus both
blind local spending and a universal preference for global one-step selection
have limited scope. A posterior assigning exactly zero probability to H=1 can
never recover it by Bayesian conditioning: structural support/calibration must
be repaired before an acquisition rule can value that possibility. Our GP's
nondegenerate probabilities do not literally equal zero; this is a limiting
example, not a diagnosis inferred from the running results.

`local_value_reference.py` checks these numbers in two independent ways: exact
rational enumeration of all 32 latent/noise atoms per case and a binary Bayes-risk
formula. It also solves the two-step finite Bellman problem and the greedy policy.
Four fixed cases, 128 prior atoms, horizon two, no GP fits or component solves.
It claims one coordinated Astra slot before running and retains any failed
assertion. No tolerance or scientific setting is selected from its result.

This is established Bayesian decision theory illustrated for this project's
mechanism question, not claimed as a new theorem. The discriminating empirical
evidence remains the frozen representation, gated/global and equal-local-share
comparisons. A local gain without calibrated sharing, or a gain only in auxiliary
prediction, does not establish better primary-boundary learning.

**Documentation erratum, 20 October 2026:** the original uncertain-coherent
example incorrectly asserted a unique category of optimal first action at
horizon two. Both categories tie; the one-step greedy preference remains local.
The minimum risk .035 is unchanged. The failed assertion and original sources
are preserved; see FINISHING_AUDITS_REPAIR_02.md. No experimental endpoint,
numerical tolerance or substantive example was replaced.
