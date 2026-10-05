"""Week 18 Phase 4 — independent checks of selected Astra Round 3 claims (outputs/astra_round3/), written from the
statements only (no Astra code imported or executed).

1. L3   centred Gaussian/probit self-value V_self = arctan(s/τ)/π (closed form and bivariate-normal quadrature).
2. C10  coherent plug-in edge EBR = −1/9 (exact rational arithmetic).
3. R5   optimized ratio-of-expectations Dice risk increases by 1/210 under a coherent observation (exact).
4. P5   whole-mean attenuation λ(b0 + b1 h) never moves the zero threshold (trivial; asserted).
5. D4   rank-inversion discovery bound D ≤ 1 + ⌊V / r⌋ = 1 + ⌊(1 − AUC)(N − r)⌋ on the real campaigns, physics score log h.
6. "Level shifts, order survives" (CONJECTURE, Astra §10): per-campaign log-h thresholds with bootstrap intervals,
   overall and inside the campaign overlap, and within-campaign AUC / inversion counts of the log-h order.
Labels: 1–4 THEOREM checks (exact / numerical), 5–6 POST-HOC on real labels.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase4"


def check_L3():
    rows = []
    for s, tau in ((.1, 1.), (.5, 1.), (1., 1.), (2., 1.), (1., np.sqrt(8 / np.pi))):
        g = np.sqrt(s * s + tau * tau); rho = s / g
        c = 4 * multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]]).cdf([0, 0]) - 1     # E[T O], m = 0
        rows.append({"s": s, "tau": tau, "V_quadrature": c / 2, "V_closed_form": np.arctan(s / tau) / np.pi})
    d = pd.DataFrame(rows); d["abs_err"] = (d.V_quadrature - d.V_closed_form).abs()
    return d


def check_C10():
    P = {"00": Fr(2, 9), "01": Fr(2, 9), "10": Fr(2, 9), "11": Fr(3, 9)}
    def edge_risk(p):
        tot = sum(p.values()); m1 = sum(v for k, v in p.items() if k[0] == "1") / tot; m2 = sum(v for k, v in p.items() if k[1] == "1") / tot
        pred = int(m1 > Fr(1, 2)) ^ int(m2 > Fr(1, 2))
        return sum(v for k, v in p.items() if (int(k[0]) ^ int(k[1])) != pred) / tot
    prior = edge_risk(P)
    p1 = P["01"]; post = p1 * edge_risk({"01": P["01"]}) + (1 - p1) * edge_risk({k: v for k, v in P.items() if k != "01"})
    return {"prior_edge_risk": prior, "expected_post_risk": post, "EBR": prior - post}


def check_R5():
    def ratio_risk(p):     # edge 1 always cut, edge 2 cut w.p. p; actions: predict {1}, {2}, {1,2} (or none)
        best = None
        for pred in ((1, 0), (0, 1), (1, 1)):
            tp = pred[0] * 1 + pred[1] * p; npred = sum(pred); ntrue = 1 + p
            r = 1 - Fr(2) * tp / (npred + ntrue)
            best = r if best is None or r < best else best
        return best
    prior = ratio_risk(Fr(3, 4)); post = Fr(1, 2) * ratio_risk(Fr(1, 2)) + Fr(1, 2) * ratio_risk(Fr(1))
    return {"prior_ratio_risk": prior, "expected_post_risk": post, "reduction": prior - post}


def check_P5():
    h = np.linspace(-3, 3, 7); b0, b1 = .7, -1.3
    zs = [h[np.argmin(np.abs(lam * (b0 + b1 * h)))] for lam in (.01, .5, 1, 7)]
    return {"zero_threshold": -b0 / b1, "attenuation_invariant": bool(np.all(np.isclose([-b0 / b1] * 4, [-(lam * b0) / (lam * b1) for lam in (.01, .5, 1, 7)])))}


def _logh(D):
    return np.log(D.P) - .5 * np.log(D.VX) - 1.5 * np.log(D.LS)


def check_D4():
    import src.week18_data_audit as A
    D = A.load(); out = []
    for name, m in (("OLD", D.campaign == 0), ("NEW", D.campaign == 1), ("POOLED", np.ones(len(D), bool))):
        d = D[m]; y = d.y.to_numpy(int); s = _logh(d).to_numpy()
        rare = int(y.mean() < .5)                       # NEW: non-Keyhole rare; OLD/POOLED: Keyhole rare
        score = s if rare == 1 else -s                  # rank most rare-prone first
        order = np.lexsort((d.sim_id.to_numpy(object), -score))
        lab = (y[order] == rare).astype(int); N, r = len(lab), int(lab.sum())
        common_before = np.cumsum(1 - lab); V = int(common_before[lab == 1].sum())
        Dfirst = int(np.argmax(lab == 1)) + 1
        auc = roc_auc_score(lab, -np.arange(N))         # rank-based AUC of the ordering for the rare class
        out.append({"campaign": name, "N": N, "rare": "KH" if rare == 1 else "non-KH", "r": r, "V_inversions": V, "AUC": auc,
                    "D_first_rare": Dfirst, "bound_V": 1 + V // r, "bound_AUC": 1 + int(np.floor((1 - auc) * (N - r) + 1e-9)),
                    "holds": Dfirst <= 1 + V // r})
    return pd.DataFrame(out)


def _threshold(s, y):
    lr = LogisticRegression(C=1e6, max_iter=10000).fit(s[:, None], y)
    return float(-lr.intercept_[0] / lr.coef_[0, 0])


def check_level_shift(B=2000, seed=0):
    import src.week18_data_audit as A
    D = A.load(); s = _logh(D).to_numpy(); y = D.y.to_numpy(int); c = D.campaign.to_numpy()
    X = D[["P", "VX", "LS", "ST"]].to_numpy(float)
    lo_o, hi_o = X[c == 0].min(0), X[c == 0].max(0); lo_n, hi_n = X[c == 1].min(0), X[c == 1].max(0)
    in_old_box = np.all((X >= lo_o) & (X <= hi_o), 1); in_new_box = np.all((X >= lo_n) & (X <= hi_n), 1)
    groups = {"OLD": c == 0, "NEW": c == 1, "NEW in OLD box": (c == 1) & in_old_box, "OLD in NEW box": (c == 0) & in_new_box}
    rng = np.random.default_rng(seed); rows = []
    for g, m in groups.items():
        ss, yy = s[m], y[m]; th = _threshold(ss, yy); bs = []
        for _ in range(B):
            i = rng.integers(len(ss), size=len(ss))
            if len(set(yy[i])) == 2:
                bs.append(_threshold(ss[i], yy[i]))
        bs = np.array(bs)
        rows.append({"group": g, "n": int(m.sum()), "KH": int(yy.sum()), "threshold": th, "lo": float(np.quantile(bs, .025)), "hi": float(np.quantile(bs, .975)),
                     "AUC_logh": float(roc_auc_score(yy, ss)) if len(set(yy)) == 2 else np.nan})
    d = pd.DataFrame(rows)
    # paired difference of the overlap thresholds (independent bootstrap of the two groups)
    a, b = groups["NEW in OLD box"], groups["OLD in NEW box"]
    diffs = []
    for _ in range(B):
        ia = rng.choice(np.flatnonzero(a), a.sum()); ib = rng.choice(np.flatnonzero(b), b.sum())
        if len(set(y[ia])) == 2 and len(set(y[ib])) == 2:
            diffs.append(_threshold(s[ia], y[ia]) - _threshold(s[ib], y[ib]))
    diffs = np.array(diffs)
    return d, {"overlap_diff": float(d.threshold.iloc[2] - d.threshold.iloc[3]), "lo": float(np.quantile(diffs, .025)), "hi": float(np.quantile(diffs, .975))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    l3 = check_L3(); c10 = check_C10(); r5 = check_R5(); p5 = check_P5(); d4 = check_D4(); ls, od = check_level_shift()
    l3.to_csv(OUT / "astra3_L3.csv", index=False); d4.to_csv(OUT / "astra3_D4_real.csv", index=False); ls.to_csv(OUT / "astra3_level_shift.csv", index=False)
    summ = {"L3_max_abs_err": float(l3.abs_err.max()), "C10": {k: str(v) for k, v in c10.items()}, "R5": {k: str(v) for k, v in r5.items()},
            "P5": p5, "D4_holds_all": bool(d4.holds.all()),
            "level_shift": "per-group bootstrap thresholds are unstable (OLD in NEW box has 2 non-Keyhole runs: quasi-separation); "
                           "use the shared-slope profile-likelihood intervals (campaign_offset_profile, astra3_campaign_offset_profile.json)",
            "campaign_offset_profile": [campaign_offset_profile("all"), campaign_offset_profile("overlap")]}
    import json
    (OUT / "astra3_checks.json").write_text(json.dumps(summ, indent=1, default=str))
    return l3, c10, r5, p5, d4, ls, od



def campaign_offset_profile(subset="all"):
    """Shared-slope logistic y ~ a + b·log h + δ·NEW; profile-likelihood 95% interval for the threshold shift
    −δ/b (log-h units) on all runs or inside the campaign overlap (NEW in OLD box ∪ OLD in NEW box)."""
    from scipy.optimize import minimize
    from scipy.special import expit, log_expit
    from scipy.stats import chi2
    import src.week18_data_audit as A
    D = A.load(); s = _logh(D).to_numpy(); y = D.y.to_numpy(int); c = D.campaign.to_numpy().astype(float)
    if subset == "overlap":
        X = D[["P", "VX", "LS", "ST"]].to_numpy(float); m0, m1 = c == 0, c == 1
        lo_o, hi_o = X[m0].min(0), X[m0].max(0); lo_n, hi_n = X[m1].min(0), X[m1].max(0)
        keep = (m1 & np.all((X >= lo_o) & (X <= hi_o), 1)) | (m0 & np.all((X >= lo_n) & (X <= hi_n), 1))
        s, y, c = s[keep], y[keep], c[keep]
    sc = s - s.mean()
    def nll(p, shift=None):
        a, b = p[0], p[1]; d = p[2] if shift is None else -shift * b      # shift = −δ/b fixed
        z = a + b * sc + d * c
        return -np.sum(y * log_expit(z) + (1 - y) * log_expit(-z))
    best = minimize(nll, [0., 5., 0.], method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 20000})
    shift_hat = -best.x[2] / best.x[1]
    grid = np.linspace(-1.5, 1.5, 301); prof = []
    for sh in grid:
        r = minimize(lambda p: nll(p, sh), best.x[:2], method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 20000})
        prof.append(r.fun)
    prof = np.array(prof); ok = prof - best.fun <= chi2.ppf(.95, 1) / 2
    return {"subset": subset, "n": int(len(y)), "NEW_n": int(c.sum()), "NEW_nonKH": int(((c == 1) & (y == 0)).sum()), "OLD_nonKH": int(((c == 0) & (y == 0)).sum()),
            "shift_hat_logh": float(shift_hat), "lo": float(grid[ok].min()), "hi": float(grid[ok].max()),
            "interval_hits_grid_edge": bool(ok[0] or ok[-1]), "slope": float(best.x[1])}


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    for x in main():
        print(x if not isinstance(x, pd.DataFrame) else x.round(4).to_string())
