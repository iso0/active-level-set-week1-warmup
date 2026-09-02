# Candidate acquisition designs

No trajectory was generated in Phase 1.15A. All quantities below are available before revealing a candidate label.

## A0 — frozen baseline

\[A_0(x)=1-2|p_{M3}(x)-0.5|.\]

Purpose: ordinary M3 classifier-margin uncertainty. It is parameter-free and remains the mandatory comparator. Its limitation is that it discards whether M3 materially corrected the physics prior.

## A1 — boundary-correction product

\[A_1(x)=\bigl(1-2|p_{M3}(x)-0.5|\bigr)\,|p_{M3}(x)-p_H(x)|.\]

Purpose: require both final boundary relevance and a material physics-to-M3 correction. No tuning parameter is present. It is closest in spirit to physics-residual acquisition (Polanska et al.) and discrepancy-aware design (Yang et al.), while retaining the classification-boundary gate of margin/LSE methods. Failure modes: large corrections can be confidently wrong; the product can ignore useful high-uncertainty points when the current residual is still small; repeated bound hits may distort correction magnitude.

## A2 — Keyhole-directed boundary correction

\[A_2(x)=\bigl(1-2|p_{M3}(x)-0.5|\bigr)\,\max\{p_{M3}(x)-p_H(x),0\}.\]

Purpose: test the specific Phase 1.14 early missed-Keyhole failure mode by prioritizing boundary candidates where the residual moves probability toward Keyhole. It has no tuned weight. Failure modes: it is deliberately asymmetric, may create false positives, and can miss important corrections toward Conduction. It should be a backup diagnostic, not the default recommendation.

## Recommendation

**No Phase 1.15B replay yet.** Decision: `CORRECTION_SIGNAL_PARTIAL`. Top-quintile net-fix CI lower bound is -0.0006; q20-like enrichment CI lower bound is 2.753; early net-fix CI lower bound is -0.0027. Under a partial result, boundary enrichment can be explained largely by ordinary margin redundancy and does not justify a new trajectory by itself. If stronger independent evidence appears later, A1 is the preferred simple rule; A2 remains a mechanism sensitivity only.
