"""Phase 7: choose the primary budget window by an old-data power analysis.

Noise model: the empirical paired per-run q20-accuracy difference curves between two
M3 arms (P1 = M3-margin path, P0 = M3 on the A0 path; committed Phase 1.13/1.14
predictions), centred per budget.  Effect model: an early-window gain
  delta(b) = delta0 * max(0, (Bs - b) / (Bs - 16)),  Bs in {40, 48},
which is zero after Bs (the region with no headroom, RESEARCH_DIAGNOSIS §2).
Power = fraction of block-bootstrap resamples of the 20 repeat blocks whose
paired 95% interval lower bound is > 0 (the frozen success rule).
"""
import numpy as np, pandas as pd
acc = pd.read_csv("results/p13_p14_q20_curves.csv")
piv = acc.pivot_table(index=["run_id", "repeat"], columns=["model", "budget"], values="correct")
runs = piv.index; rep = piv.index.get_level_values("repeat").to_numpy()
B = np.arange(16, 81)
D = piv["P1"][B].to_numpy() - piv["P0"][B].to_numpy()          # 100 x 65 paired differences
E = D - D.mean(0, keepdims=True)                                # centred noise curves
WINDOWS = [(16, 32), (16, 40), (16, 48), (16, 60), (16, 80)]
rng = np.random.default_rng(7)


def aulc(rows, a, b):
    m = (B >= a) & (B <= b); return np.trapezoid(rows[:, m], B[m], axis=1) / (b - a)


def power(delta0, Bs, n_sim=2000, draws=400):
    shape = np.maximum(0, (Bs - B) / (Bs - 16)); eff = delta0 * shape
    out = {}
    for a, b in WINDOWS:
        hits = 0
        for _ in range(n_sim):
            blocks = rng.integers(1, 21, 20)                     # resample repeat blocks
            rows = np.concatenate([np.flatnonzero(rep == k) for k in blocks])
            Y = E[rows] + eff
            v = aulc(Y, a, b); r = rep[rows]
            bm = pd.Series(v).groupby(r).mean().to_numpy()
            boots = bm[rng.integers(0, len(bm), (draws, len(bm)))].mean(1)
            hits += np.quantile(boots, .025) > 0
        out[f"{a}-{b}"] = hits / n_sim
    return out


if __name__ == "__main__":
    rows = []
    for Bs in (40, 48):
        for d0 in (0.0, 0.01, 0.02, 0.03, 0.04):
            p = power(d0, Bs, n_sim=600, draws=300); rows.append({"Bs": Bs, "delta0": d0, **p}); print(rows[-1])
    pd.DataFrame(rows).to_csv("results/window_power.csv", index=False)
    # half-widths of the empirical paired CIs per window
    for a, b in WINDOWS:
        v = aulc(D, a, b); bm = pd.Series(v).groupby(rep).mean().to_numpy()
        boots = bm[rng.integers(0, 20, (10000, 20))].mean(1)
        print(f"window {a}-{b}: paired half-width {np.subtract(*np.quantile(boots,[.975,.025]))/2:.4f}, block sd {bm.std(ddof=1):.4f}")
