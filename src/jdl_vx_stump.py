"""Depth-one scan-speed classifier trained on paid labels only (frozen rule; system control in the V2 comparison).

Feature: VX on the same frozen fold-pool scale as every other arm (standardized log VX).  The cut and its orientation are
learned from the paid labels of the checkpoint; no cut value is fixed in advance (in particular, the 0.85 m/s value of
the Week 19 inspection is never used).

Frozen rule
1. One-class paid labels: no split; constant score s = (n1 + 0.5) / (n + 1).
2. Candidate cuts: midpoints between consecutive distinct sorted paid feature values.  For each cut c and orientation
   o = +1 (x > c -> Keyhole) or o = -1 (x > c -> no Keyhole), compute the paid class-balanced accuracy
   BA(c, o) = (TPR + TNR) / 2 of that rule on the paid labels.
3. Choose the maximal BA; ties are broken by (a) the larger gap between the two paid values adjacent to the cut (largest
   margin), then (b) orientation -1 before +1, then (c) the smaller cut.  If the maximal BA is not above 0.5, the
   constant rule of step 1 is used instead (a split no better than chance on the paid data is not adopted).
4. Leaf scores are class-weighted and smoothed: s_leaf = (w1 n1 + 0.5) / (w1 n1 + w0 n0 + 1), with w_c = n / (2 n_c)
   (n_c paid labels of class c; n1, n0 paid labels of each class in the leaf).  The decision at 0.5 is the weighted
   leaf majority (s_leaf >= 0.5 iff w1 n1 >= w0 n0).

The leaf scores weight the two classes equally by construction.  They are decision scores, not population-calibrated
probabilities: Brier score and log loss of this arm are reported only for completeness, and the paid-prevalence rule
is not applied to it.
"""
from __future__ import annotations

import numpy as np

RULE_VERSION = "vx-stump-1.0"


def fit_stump(x, y):
    """x: paid feature values (1-D), y: paid labels (0/1).  Returns the frozen model as a dict."""
    x = np.asarray(x, float); y = np.asarray(y, int)
    n, n1 = len(y), int(y.sum()); n0 = n - n1
    const = {"rule": RULE_VERSION, "type": "constant", "score": (n1 + 0.5) / (n + 1), "n": n, "n1": n1, "n0": n0}
    if n1 == 0 or n0 == 0:
        return {**const, "reason": "one-class paid labels"}
    xs = np.unique(x)
    if len(xs) < 2:
        return {**const, "reason": "no distinct paid feature values"}
    best = None
    for lo, hi in zip(xs[:-1], xs[1:]):
        c, gap = (lo + hi) / 2, hi - lo
        right = x > c
        for o in (-1, +1):
            pred = right if o == +1 else ~right
            ba = 0.5 * ((pred & (y == 1)).sum() / n1 + (~pred & (y == 0)).sum() / n0)
            key = (round(ba, 12), round(gap, 12), -o, -c)                   # max BA, max gap, o=-1 first, smaller cut
            if best is None or key > best[0]:
                best = (key, c, o, ba, gap)
    _, c, o, ba, gap = best
    if ba <= 0.5 + 1e-12:
        return {**const, "reason": "no paid split better than chance", "best_paid_BA": float(ba)}
    w1, w0 = n / (2 * n1), n / (2 * n0)
    right = x > c
    leaves = {}
    for name, m in (("left", ~right), ("right", right)):
        k1, k0 = int((y[m] == 1).sum()), int((y[m] == 0).sum())
        leaves[name] = {"n1": k1, "n0": k0, "score": (w1 * k1 + 0.5) / (w1 * k1 + w0 * k0 + 1.0)}
    return {"rule": RULE_VERSION, "type": "split", "cut": float(c), "orientation": int(o), "paid_BA": float(ba), "gap": float(gap),
            "n": n, "n1": n1, "n0": n0, "class_weights": {"1": w1, "0": w0}, "leaves": leaves}


def predict_stump(model, x):
    x = np.asarray(x, float)
    if model["type"] == "constant":
        return np.full(len(x), model["score"])
    right = x > model["cut"]
    return np.where(right, model["leaves"]["right"]["score"], model["leaves"]["left"]["score"])
