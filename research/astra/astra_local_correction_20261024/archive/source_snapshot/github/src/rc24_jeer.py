"""RC24 Stage B prototype P2 - JEER: joint expected error reduction under the PAC model (two observations per query).

Measured inadequacy: on fresh repeats 59-66 HA_LEAN + margin spends 45 % of its post-startup queries in the fast-scan corner that holds
7 % of the pool and whose labels are interleaved; the corner errors barely fall. Margin rewards the queried point's OWN label
uncertainty, which is largest exactly where labels are interleaved.
Mechanism: value a query by what its two observations (depth a_c and label y_c) are expected to do to the classification of the OTHER
candidate inputs, under the PAC joint model; the queried point's own label resolution is excluded (the test points are never queried).
  E      = unpaid candidate-pool inputs other than c (public inputs only; no test membership)
  r(p)   = min(p, 1 - p)  (expected 0-1 loss of the 0.5 decision)
  JEER(c) = sum_{x in E} r(p(x)) - E_{a_c, y_c}[ sum_{x in E} r(p'(x)) ]
  fantasy  a_c ~ N(m(c), v(c) + sn2)  (3-node Gauss-Hermite, exact to degree 5);  y_c | a_c ~ Bernoulli(sum_g w_g sigmoid(m_g(z_h(c), a_c)))
  update   depth: exact rank-1 GP conditioning of the latent at E on (c, a_c) (fixed hyperparameters):
             m'(x) = m(x) + k(x, c) (a_c - m(c)) / (v(c) + sn2),  v'(x) = v(x) - k(x, c)^2 / (v(c) + sn2)
           label: the classifier's training set gains (z_h(c), a_c, y_c); every grid configuration's Laplace mode and marginal
             likelihood are recomputed (standardisation of the features kept at the current paid rows - stated approximation);
           p'(x) = errors-in-variables PAC probability with (m', v') and the updated classifier.
Candidates: the 30 candidates with the smallest |p - 0.5| (deterministic screen; ties by index). Selection argmax JEER (first index).
Fantasy classifiers use the grid configurations that carry 99 % of the current posterior weight (largest first; their weights are
re-estimated among themselves after the fantasy); the current probabilities p use the full grid.
Ablation JEER_LABEL: the same with the depth update switched off (a_c enters only the classifier) -> isolates the depth observation's value.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.special import expit

import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc24_pac as PC

N_SCREEN = 30
FX, FW = np.polynomial.hermite_e.hermegauss(3)
FW = FW / FW.sum()


def _gram(Ha, Hb):
    U0, U1 = np.zeros((len(Ha), 1)), np.zeros((len(Hb), 1)); return PH.Gram(Ha, Hb, U0, U1)


def _family(Htr, y, Hev, cfg):
    """Laplace mode per configuration on standardised features; returns weights, plug-in latent means at Hev, depth coefficient."""
    Gtt = _gram(Htr, Htr); Get = _gram(Hev, Htr); logw = np.empty(len(cfg)); Mm = np.empty((len(cfg), len(Hev))); cA = np.empty(len(cfg))
    for g, (tf, th) in enumerate(cfg):
        mode = PH.laplace(Gtt.K(tf, th, 0.0, None), y); logw[g] = mode["logZ"]; Mm[g] = Get.K(tf, th, 0.0, None) @ mode["grad"]
        cA[g] = tf ** 2 * float(Htr[:, 1] @ mode["grad"])
    w = np.exp(logw - logw.max()); w /= w.sum(); return w, Mm, cA


def _eiv(w, Mm, cA, s):
    P = np.zeros(Mm.shape[1])
    for g in range(len(w)):
        P += w[g] * (expit(Mm[g][:, None] + (cA[g] * s)[:, None] * PC.GH_X[None, :]) @ PC.GH_W)
    return P


def scores(task, rev, Z, cands, depth_update=True, n_screen=N_SCREEN):
    """JEER scores on the screened candidates (others -inf), the PAC probabilities on cands, and diagnostics."""
    L = rev.paid; y = rev.paid_y()[L].astype(float); h = A.hcol(task); f = PC.depth_fit(task, rev, Z, "phys")
    if f is None:
        return None
    g = f["g"]; mt, _ = PC.depth_predict(f, Z, L); mc, vc = PC.depth_predict(f, Z, cands)
    Xtr = np.c_[h[L], mt]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr = (Xtr - mu) / sd; Hc = (np.c_[h[cands], mc] - mu) / sd
    cfg = [(tf, th) for tf in PH.TAU_F for th in PH.TAU_H]; w, Mm, cA = _family(Htr, y, Hc, cfg); s = np.sqrt(np.maximum(vc, 0)) / sd[1]
    p = _eiv(w, Mm, cA, s); r = np.minimum(p, 1 - p)
    top = np.argsort(-w, kind="stable"); top = top[:int(np.searchsorted(np.cumsum(w[top]), 0.99) + 1)]; cfg_f = [cfg[k] for k in top]
    wf, Mf, cf_ = w[top] / w[top].sum(), Mm[top], cA[top]
    order = np.argsort(np.abs(p - 0.5), kind="stable")[:min(n_screen, len(cands))]
    H = f["H"]; Zc = Z[cands]; Hb = None if H is None else H[cands]
    Kpost = g.post_cov(Zc, Hb, Zc[order], None if Hb is None else Hb[order])            # latent posterior covariance cands x screened
    sn2 = g.noise; out = np.full(len(cands), -np.inf); diag = []
    for jj, i in enumerate(order):
        keep = np.ones(len(cands), bool); keep[i] = False; R0 = float(r[keep].sum()); vobs = vc[i] + sn2; ER = 0.0
        for xk, wk in zip(FX, FW):
            a = mc[i] + np.sqrt(vobs) * xk
            if depth_update:
                m2 = mc + Kpost[:, jj] * (a - mc[i]) / vobs; v2 = np.maximum(vc - Kpost[:, jj] ** 2 / vobs, 0.0)
            else:
                m2, v2 = mc, vc
            Hc2 = (np.c_[h[cands], m2] - mu) / sd; s2 = np.sqrt(v2) / sd[1]; hn = (np.array([h[cands[i]], a]) - mu) / sd
            Htr2 = np.vstack([Htr, hn]); p1 = float(wf @ expit(Mf[:, i] + cf_ * (a - mc[i]) / sd[1]))
            for yv, py in ((1.0, p1), (0.0, 1.0 - p1)):
                w2, M2, c2 = _family(Htr2, np.r_[y, yv], Hc2, cfg_f); pp = _eiv(w2, M2, c2, s2); ER += wk * py * float(np.minimum(pp, 1 - pp)[keep].sum())
        out[i] = R0 - ER; diag.append((int(cands[i]), float(p[i]), out[i]))
    return {"score": out, "p": p, "screened": [int(cands[i]) for i in order], "best_gain": float(np.max(out)), "gain_spread": float(np.ptp(out[order])), "n_cfg_fantasy": len(cfg_f)}
