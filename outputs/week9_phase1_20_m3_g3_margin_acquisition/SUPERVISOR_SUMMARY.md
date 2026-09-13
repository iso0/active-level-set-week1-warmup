# Phase 1.20 — discussion with Ioan

**Question:** Can standalone G3 select better queries while M3 remains the evaluator?

**Controlled comparison:** 405 frozen simulations; 100 identical grouped outer splits; shared 16-point starts. P0 = historical isotropic-GPC path; P1 = M3-margin path; P2 = new sequential ARD G3-margin path. All paths use the exact M3 evaluator.

**Primary, q20 balanced-accuracy AULC B16–B40:** P2−P1 = -0.002560 (95% repeat-block interval [-0.010570, +0.005446]); 9/20 repeat blocks positive.

**Full B16–B80:** P2−P1 = -0.007014 (95% repeat-block interval [-0.011681, -0.002494]); 7/20 repeat blocks positive.

**Historical control:** early P2−P0 = -0.005724 (95% repeat-block interval [-0.012324, +0.000581]); 7/20 repeat blocks positive.

**Decision:** G3_SELECTOR_SMALL_OR_UNRESOLVED. Retain M3-margin; this result does not justify replacing it.

The practical threshold (0.01 AULC) was frozen before P2 results. Earlier reported Phase 1.14 numbers were accuracy, not balanced accuracy. This is evidence about offline acquisition paths, not prospective simulation savings or G3 predictive superiority.
