# EXTERNAL_PROTOCOL_REVIEW — does the frozen protocol change?

Reviewed: `claude_rnd_2026_09_05/EXTERNAL_CONFIRMATION_PROTOCOL.md` and `external_confirmation_protocol.json`. The previous files are not modified; this document records the review and the only additions (in `followup_protocol_addendum.json`).

| Element | Audit | Decision |
|---|---|---|
| Primary contrast C − A (M3+TV vs M3+margin) with B′ (M3 + T-margin) as the mechanistic control | The follow-up produced no attainable oracle signal, no model that beats M3, and no acquisition that beats margin on the development gate; M3+TV remains the only non-redundant, non-harmful candidate. C − A is the thesis-relevant contrast (does the challenger beat the incumbent); C − B′ isolates the leverage term. Development values: C − A +0.0025 (F7) / −0.0037 (tight), C − B′ +0.0058 / +0.0041. | **RETAIN** primary C − A, secondary C − B′. |
| Primary window AULC 16–40 | Justified by headroom and power (previous package). The follow-up strengthens it: all corrected XSUR forms, TV, and the oracle's gains are early-confined; the all-label level is reached by B60. | **RETAIN** |
| Success threshold mean ≥ +0.010 with lower bound > 0 | Unchanged rationale (one third of the old early headroom; power table). The oracle's +0.095 does not change the threshold: it is not attainable label-blind. | **RETAIN** |
| KH-recall guard (−0.02 non-inferiority) | The M3R audit shows KH recall is the metric most easily sacrificed by a model change; the guard is more important, not less. | **RETAIN** |
| Feasibility gates (K/H rule; band ≥ 24 / 45 per training pool; uncertain ≥ 12; support; N ≥ 200 for power) | Unchanged. | **RETAIN** |
| Blinding / hash / oracle procedure | Unchanged; the follow-up used no new inputs or labels. | **RETAIN** |
| Model arms | No model replaces M3 (T killed previously; M3R killed now; no local model justified). | **RETAIN M3 in all arms** |
| Prediction study | P1 wording (all-label level, not ceiling); P1b added (band-restricted vs all-label fit); P9 rewritten (selection sensitivity; oracle run after unblinding, evaluation-only). | **ADD to the prediction study only**; no effect on the acquisition arms |
| Terminology | "exact Bayes-optimal" → "coherent under semantics S2"; XSUR is not an arm and is not affected. | wording only |

## Two items that must be true before unblinding

1. The follow-up directory (this package) is committed together with the previous package and the freeze block of `external_confirmation_protocol.json` is filled by a second commit **before** any label file is opened; the addendum JSON's SHA-256 is recorded alongside.
2. `code/new_pool_audit.py` has been run on the input-only manifest and its gate level recorded. It has not been run yet (no manifest was available; none was requested in this task).

## Exact final recommendation for the unseen pool

Run the four-path replay as frozen (A: M3+margin; B′: M3 + T-margin; C: M3+TV; D: Random), primary endpoint Fold-B1-q20 accuracy AULC 16–40, primary contrast C − A, success rule unchanged; run the prediction study (P1, P1b, P2–P9) after unblinding; report both together. Expected outcome for the acquisition contrast, stated for the record: unresolved (probability of meeting the success rule ≈ 0.10–0.15). Expected outcome for the prediction study: informative in every case.
