"""Week 14 order (dominance) utilities for finite-pool active level-set estimation.

A sign vector s in {+1, -1, 0}^d defines the "class-1-favouring" preorder:
    u <= v   iff   s_k (v_k - u_k) >= 0 for every k with s_k != 0.
Labels are *monotone* when u <= v implies y(u) <= y(v).  For LPBF the physically
motivated signs are (P +, VX -, LS -) and optionally ST + (Gan et al.'s keyhole
number increases with substrate temperature).

Everything here is label-free unless a function takes ``y`` explicitly.
"""
from __future__ import annotations

import numpy as np

SIGNS_O3 = np.array([1, -1, -1, 0])   # (P, VX, LS, ST): ST ignored (Phase 1.19A order)
SIGNS_O4 = np.array([1, -1, -1, 1])   # ST increasing (keyhole-number direction)


def dominance(x, signs):
    """D[i, j] = True iff x_i <= x_j in the signed order and i != j (ties in all used coords excluded)."""
    x = np.asarray(x, float)
    s = np.asarray(signs)
    use = s != 0
    z = x[:, use] * s[use]
    ge = (z[None, :, :] >= z[:, None, :]).all(axis=2)      # j >= i coordinatewise
    eq = (z[None, :, :] == z[:, None, :]).all(axis=2)
    return ge & ~eq


def minimal(D, subset=None):
    """Indices (into the full array) of elements of ``subset`` with no strict predecessor in ``subset``."""
    idx = np.arange(D.shape[0]) if subset is None else np.asarray(subset, int)
    sub = D[np.ix_(idx, idx)]
    return idx[~sub.any(axis=0)]


def maximal(D, subset=None):
    idx = np.arange(D.shape[0]) if subset is None else np.asarray(subset, int)
    sub = D[np.ix_(idx, idx)]
    return idx[~sub.any(axis=1)]


def violations(D, y):
    """Number of comparable ordered pairs (i <= j) with y_i = 1 and y_j = 0."""
    y = np.asarray(y, int)
    return int((D & (y[:, None] == 1) & (y[None, :] == 0)).sum())


def closure_labels(D, labelled, y_labelled):
    """Dominance-closure inference.  Returns array with 1/0 for implied labels, -1 unknown, -2 conflict.

    u is implied 1 if some labelled v with y_v = 1 has v <= u; implied 0 if some labelled w with
    y_w = 0 has u <= w.  Labelled points keep their own label.
    """
    n = D.shape[0]
    lab = np.asarray(labelled, int)
    yl = np.asarray(y_labelled, int)
    ones = lab[yl == 1]
    zeros = lab[yl == 0]
    imp1 = D[ones].any(axis=0) if len(ones) else np.zeros(n, bool)
    imp0 = D[:, zeros].any(axis=1) if len(zeros) else np.zeros(n, bool)
    out = np.full(n, -1)
    out[imp1 & ~imp0] = 1
    out[imp0 & ~imp1] = 0
    out[imp0 & imp1] = -2
    out[lab] = yl
    return out


def front_discovery_order(D, pool, score=None):
    """Label-blind order alternating minimal and maximal elements of ``pool``.

    Minimal elements are sorted by ascending ``score`` (least class-1-like first) and maximal
    elements by descending score; ties by index.  Under monotone labels the first |Min| + |Max|
    queries of this order are guaranteed to contain both classes whenever both occur in the pool.
    """
    pool = np.asarray(pool, int)
    mn = minimal(D, pool)
    mx = maximal(D, pool)
    if score is not None:
        sc = np.asarray(score, float)
        mn = mn[np.lexsort((mn, sc[mn]))]
        mx = mx[np.lexsort((mx, -sc[mx]))]
    order, seen = [], set()
    for k in range(max(len(mn), len(mx))):
        for arr in (mn, mx):
            if k < len(arr) and arr[k] not in seen:
                order.append(int(arr[k]))
                seen.add(int(arr[k]))
    return np.asarray(order, int), mn, mx


def interleave(*orders):
    """Round-robin merge of query orders, skipping repeats (the hedging construction)."""
    out, seen = [], set()
    its = [list(o) for o in orders]
    k = 0
    while any(k < len(o) for o in its):
        for o in its:
            if k < len(o) and o[k] not in seen:
                out.append(int(o[k]))
                seen.add(int(o[k]))
        k += 1
    return np.asarray(out, int)


def first_hit(order, y, cls):
    """1-based position of the first element of ``order`` with label ``cls`` (inf if none)."""
    y = np.asarray(y, int)
    hits = np.nonzero(y[np.asarray(order, int)] == cls)[0]
    return int(hits[0]) + 1 if len(hits) else np.inf


def first_both(order, y):
    y = np.asarray(y, int)[np.asarray(order, int)]
    for b in range(1, len(y) + 1):
        if 0 in y[:b] and 1 in y[:b]:
            return b
    return np.inf
