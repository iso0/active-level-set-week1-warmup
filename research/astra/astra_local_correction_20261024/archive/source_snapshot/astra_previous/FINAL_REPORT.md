# Independent judgment: representation and bounded planning

21 October 2026. Final scientific review of the frozen continuation.

**Kısa Türkçe sonuç.** Bu kez yalnız yazılım testi yapılmadı: 336 bağımsız
sentetik dünyada 4.093 öğrenme yolu ve 352 ayrı arama yolu tamamlandı. Üç öğrenme
yolu dosya erişim hatasıyla eksik kaldı; sonuçlardan silinmedi. Eklediğim yerel
bileşen ve iki adımlı planlama genel bir kazanım göstermedi. En sağlam olumlu
bulgu, uzunluk ölçeklerini öğrenen GP'nin aynı satın alınmış veride daha iyi
tahmin yapması. Bu, yeni planlayıcının başarısı değil. Büyük adalarda ucuz tek
adımlı risk seçimi için yararlı ikincil kanıt var; küçük adalarda zarar da var.
Hiçbir sistem genel sorgu tasarrufu ölçütünü karşılamadı. Önerim pahalı iki
adımlı yöntemi uygulamaya taşımamak; güçlü modeli ve ucuz seçim kontrollerini
korumak, yerel yapının neden bastırıldığını ayrı bir hipotez olarak sınamak.

## What was actually tested

The independent TEST was frozen at `06359f9`, before its realizations were
generated. Its 336 four-dimensional worlds cover eleven families, with 128 small
and 64 large islands and 16 realizations per other family. Inference weights
families equally. There are 4,096 scheduled learned paths, not 4,096 independent
replications: 2,688 common B32-to-B48 prefix paths and 1,408 B8-to-B48 end-to-end
paths. All startup, search and missing-channel queries cost one. The 352 pure
RANDOM/MAXIMIN paths measure search only. Forty DEV paths and the previous
13,065-path campaign remain development/history, not added TEST replication.

The target is uniform latent-monitor sign error at zero, not Keyhole BA, a rare
region recall objective, or a physical regime boundary. Actual decisions use
finite-mixture sign probabilities. The factorial comparison changes one coherent
compact additive GP representation and bounded Gaussian-moment h1 versus h2
planning, sharing startup, shortlist and exploration schedule. The one allowed
additional mechanism, mixture-aware h1, was also frozen prospectively. It changes
the distributional approximation, not solely component-weight updating.
Equations, missingness assumptions and approximation limits are in
[METHOD_DESIGN.md](METHOD_DESIGN.md), [TEST_PROTOCOL.md (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-8f2991cc7ad4584f) and
[MIXTURE_ATTRIBUTION_NOTE.md (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-c881fb58381b2eda).

**Execution is complete with preserved failures.** Three paths stopped on a
PermissionError reading the shared allocation record: w081 e2e existing/h2 at
29 paid observations; w175 prefix existing/h2 and w211 prefix local/h2 at 36.
They were not retried or assigned B48 outcomes. Their partial losses, costs,
attempts and immutable path hashes are portable. All other planned paths and
all seven finishing stages completed. This is not a model-induced numerical
failure, but the registered any-incomplete-unit rule prevents a clean primary
pass. No settings were repaired from scientific TEST scores.

## The primary comparison does not support either proposed gain

Let E denote error, E1/E2 the existing model with h1/h2, and L1/L2 the local model.
The registered contrasts are R=(L1−E1+L2−E2)/2,
H=(E2−E1+L2−L1)/2 and I=(L2−L1)−(E2−E1).
Negative R/H favors the proposed factor; I measures effect modification.

| B48 contrast | Complete-world estimate | Approximate simultaneous 95% interval | Full scheduled missing-outcome bounds |
|---|---:|---:|---:|
| Global error R | −0.000089 | [−0.000429, +0.000252] | [−0.002838, +0.000713] |
| Global error H | −0.000424 | [−0.001289, +0.000441] | [−0.000593, +0.002958] |
| Global error I | −0.000409 | [−0.000774, −0.000045] | [−0.005909, +0.001194] |
| Conditional island error R | 0 | degenerate, no inferential pass | [−0.005433, +0.003826] |
| Conditional island error H | +0.000718 | [−0.001760, +0.003197] | [−0.004741, +0.004518] |
| Conditional island error I | 0 | degenerate, no inferential pass | [−0.010866, +0.007652] |

There are 334 complete factorial worlds. The conditional island comparison has
only six small-island and 26 large-island complete worlds with a valid common
prefix hit; 27 large-island worlds were eligible before the missing result.
The six intervals use 10,000 stratified whole-world resamples and a joint
max-standardized deviation; 9,975 had defined conditional denominators. They
assume independent realizations within these fixed families and bootstrap
approximation. Degenerate empirical zeros are not equivalence evidence.
Missing-outcome bounds use the [0,1] loss range and are sensitivity bounds,
not confidence intervals. The small negative interaction does not establish
a benefit and does not survive arbitrary allowed missing outcomes.
Source: [PRIMARY_CONTRASTS.json (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-2fc6ff7658b762e8).

Mixture-aware h1 did not rescue the result. Its paired global error difference
from moment h1 is +0.000137 [−0.000650,+0.000893] with the existing model and
+0.000032 [−0.000753,+0.000785] with the local model. The corresponding h2 minus
mixture-h1 differences are −0.000307 [−0.001321,+0.000678] and
−0.000641 [−0.001635,+0.000325]. These are pointwise secondary intervals.
Neither exact future mixture weights nor a longer horizon is demonstrated to
be the missing general solution.

## What explains the result, and what useful evidence survives

The local representation was usually suppressed, rather than actively repairing
an island. Under local/h1 its mean local posterior weight fell from 0.00278 to
0.000023 in small islands, and 0.00343 to 0.000031 in large islands between B32
and B48. Local/h1 and existing/h1 bought identical full sequences in 318/336
prefix worlds. Both local representations gave identical island classifications
to their corresponding existing model on complete pairs. These observations
support **ineffective representation under this prior**, not a universal claim
that local information is useless. In the rotated family the component retained
substantial weight (mean 0.217), yet sign error stayed near 0.5: activation alone
was insufficient. The additive covariance is stationary with constant marginal
variance; compact correlation support is not a spatially gated variance prior.

The planner was also often numerically indifferent. Existing/local prefix h2
used the moment-h1 fallback within unresolved sets on 2,784/4,020 and
2,763/4,020 risk decisions. Their unaccepted-refinement counts were 294 and 289;
fallback is not synonymous with integration failure. Yet h2 changed full paths
in 143/335 and 146/335 paired worlds, so the result cannot be dismissed as
literally never trying another path. This rejects a useful gain for the
deployed bounded rule; it does not rule out longer exact planning with a better
posterior. [FINAL_REVIEW_FACTS.json (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-e3d8ede98926c98f)
contains the cached path/weight diagnostics.

**The stronger positive result is model fitting, visible before acquisition
diverged.** At common B32, learned ARD minus existing-mixture error was −0.03487
[−0.03811,−0.03173]; boundary error −0.08319; positive and negative recall rose
by 0.05007 and 0.03188. Local minus existing error was essentially zero
(−0.000004 [−0.000105,+0.000091]), despite a modest Brier improvement of
0.000621. These are paired descriptive controls, not the primary promotion gate.
ARD learns amplitude and noise as well as axis lengthscales, so this is a model
package effect, not an isolated causal effect of ARD lengthscales alone.

At B48 the learned-ARD/straddle system has global error 0.06896 versus 0.07932
for existing/h1 (paired difference −0.01036 [−0.01212,−0.00839]). Positive/negative
recalls are 0.9000/0.9357 versus 0.8847/0.9258; Brier 0.04770 versus 0.08789 and
log loss 0.18505 versus 0.31471. Undefined class metrics retain their own family
denominators; averaged BA is not reconstructed from these two aggregate recalls.
This is a complete-system comparison after B32. The same-path B32 result is the
cleaner evidence for model value. No dominance claim follows: rotated error is
0.5017 versus 0.4960, coherent-corruption error 0.01224 versus 0.00720, and
small-island recall remains only 0.0121. Every family, both recalls and proper
scores are retained in [ALL_FAMILIES_REVIEW.md (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-b0e89c462b3b609b).

There is a useful **secondary same-model selector effect** on large islands:
in 16 end-to-end worlds, ARD/h1 versus ARD/full-pool straddle improves island
recall by 0.2622 [0.0908,0.4478], with 9/16 versus 3/16 first hits and 7/16 versus
3/16 third hits. It is a one-step versus full-pool system contrast, including
shortlist differences, not evidence for h2. Overall global error difference is
uncertain (−0.00140 [−0.00388,+0.00092]); small-island boundary error worsens by
0.03991 [0.02104,0.06042] and both class recalls fall. Preserve this tradeoff
instead of selecting a universal winner from the best regional number.

Search remains a distinct bottleneck. Common B32 found valid island observations
in only 6/128 small-island worlds; three pools contained no island candidate.
In the 16 end-to-end small-island worlds RANDOM/MAXIMIN found 4/16 and 3/16,
versus zero for ARD/h1 and ARD/straddle. The missing existing/h2 path makes its
2/15 completed hits a scheduled B48 fraction bounded by 2/16 and 3/16.
Large-island RANDOM/MAXIMIN each found 12/16. These small descriptive search
counts do not establish a universal ranking. An unseen region cannot be learned
from a free planted hit, and learning the main boundary can reduce global error
while leaving a small island nearly entirely wrong.

## Cost and numerical credibility

No overall system reached the frozen 80% joint-target attainment needed for
query-saving language. In the prefix panel ARD/straddle attains 57.81% under
equal family weighting (104/336 raw worlds), against 20.45% for existing/h1
(36/336). Restricted burdens 42.81 and 45.75 are therefore **not demonstrated
query savings**. End-to-end ARD/h1 and ARD/straddle attain 114/176 and 111/176;
their paired restricted-burden difference is +0.114 [−0.841,+1.023].

| Prefix system | Mean decision CPU s | Mean total CPU s | Weighted target attainment |
|---|---:|---:|---:|
| Existing / h1 | 1.420 | 2.930 | 20.45% |
| Existing / h2 | 8.373 | 9.938 | 21.06% |
| Local / h1 | 4.662 | 7.840 | 20.45% |
| Local / h2 | 11.738 | 15.015 | 21.02% |
| Local / mixture h1 | 15.513 | 19.714 | 21.02% |
| Learned ARD / straddle | 0.318 | 2.230 | 57.81% |

At the frozen five-second decision-CPU cap, h2 has *higher* paired global error
than h1: +0.00898 [0.00691,0.01119] existing and +0.01330 [0.01136,0.01531] local,
335 common-available worlds each. It simply makes less progress by that compute
budget. Full tables include all arms, censored/failed counts, both panels,
uncertainty and peak memory: [SAME_TARGET_QUERY_COST.md (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-71548672c3a1f46d).
CPU excludes imports/world construction/supervisor; interruptions can under-record
pre-checkpoint CPU. No physical simulation time was measured.

The 4,093 completed TEST paths report 103,349 model fit requests and 4,364,338
factorizations, including 2,278,238 optimizer evaluations. Reservations for the
whole campaign remain higher and retain interruptions/DEV: 116,752 controlled
fit requests, 4,590,464 controlled factorizations, 128 reference fits and 5,888
reference factorizations. Total fantasy reservations are 14,487,368. No ceiling
was crossed. All 5,552 chosen ARD refits reported optimizer success; 20/82,592
individual starts did not. Success flags do not prove global optima.

Integrity inspected 99,256 immutable pre-query snapshots across all 4,093 complete
paths; the only retained issues were the three missing results. All 84 fixed
slice reconstructions matched cached metrics exactly. Twenty-four registered
numerical replays were inspected: maximum cached-to-refined score differences
were 5.36e−5 for h2 and 6.73e−5 for mixture-h1. Three h2 deterministic tie choices
differed, all with zero gap to the refined maximum. Effective quadrature nodes
were 11.1–18.2 with maximum mass error 2.91e−9; they are not iid ESS. Replays refine
the same approximation, not an exact posterior. Independent dense/toy references
and deterministic disk continuation checks remain separate evidence.

## Judgment and the next discriminator

Do not promote the new local bank or two-step rule. Preserve learned model
calibration and cheap h1/straddle controls as the practical baseline, with explicit
regional reporting. The useful contribution is a working, audited discriminator
that separates prediction, search, conditional refinement and computation; it
does not deliver a new universally superior acquisition.

A falsifiable **post hoc** explanation is that selecting a constant-variance
compact component through global marginal likelihood penalizes a sparse local
anomaly at all paid points. [MECHANISM_INTERPRETATION.md](MECHANISM_INTERPRETATION.md)
derives the penalty in a restricted Gaussian example. The strongest competing
explanation is the uniform loss and shortlist: a tiny region can be worth little
even with a useful posterior. Neither is uniquely identified here.

The next discriminating experiment, **not executed or authorized as a new
campaign here**, should compare the present prior with one prospectively fixed,
coherent localized-variance representation on identical lawful paid prefixes,
using fresh realizations and the same cheap h1 loss/selector. First test predictions
before any new query; then conditional post-hit learning. Better local prediction
without useful query allocation would implicate the objective/shortlist rather
than a need for more planning depth. No matched prediction gain would mean the
representation problem remains. Noise/corruption and no-hit controls must remain;
neither truth-selected anchors nor more threshold/prior sweeps are justified.

The scalar posterior-agnostic adapter is delivered with validated paid accounting,
but Opus's classifier marginals are not its required joint observation law.
Canonical label prediction, loss-optimal decisions and physical boundaries remain
different targets. This campaign supplies no new physical data, Keyhole BA result,
C4, Stage A or SPH superiority. The fixed 541-run application, labels, exclusions,
q20 and all earlier frozen decisions remain unchanged. The local handoff is
[OPUS_INTEGRATION_HANDOFF.md (PENDING_ARCHIVE)](../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-4318b9f650225ba7); nothing was sent externally.
