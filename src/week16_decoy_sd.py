"""Week 16 item 2 follow-up — are low-value margin picks aleatoric (W16-1)?  For every item-1 state, the
posterior latent sd at the margin pick and at PEER's argmax, and the self-information ratio
rho_self = s / sqrt(s^2 + 8/pi) (W16-1: margin's self value = arcsin(rho_self)/pi at p = 1/2)."""
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.week16_cells import ALL_CELLS, build, cell_key, margin_states, pars
from src.week16_headroom import BUDGETS16
from src.week16_peer import Model, NOISE_VAR

W = Path(__file__).resolve().parents[1] / "outputs/week16_theory_meets_data/headroom"


def one(fam, cfg, rep, P, S):
    c = build(fam, cfg, rep, P); m = Model.from_hyp(c["hyp"])
    states, _ = margin_states(c, BUDGETS16, m, ())
    key = cell_key(fam, cfg); rows = []
    for b, L in states.items():
        st = S[(S.cell == key) & (S.rep == rep) & (S.budget == b)].iloc[0]
        post = m.fit(c["z_pool"][L], c["y_pool"][L])
        cands = np.setdiff1d(np.arange(len(c["z_pool"])), L)
        _, v = post.mean_var(c["z_pool"][cands]); s = np.sqrt(v)
        idx = {int(k): i for i, k in enumerate(cands)}
        sm, sa = s[idx[int(st.margin)]], s[idx[int(st.argmax_ref)]]
        rows.append({"cell": key, "rep": rep, "budget": b, "family": fam, "r_model_ref": st.r_model_ref, "s_margin": sm, "s_argmax": sa,
                     "s_median_cand": float(np.median(s)), "rho_self_margin": sm / np.sqrt(sm ** 2 + NOISE_VAR),
                     "rho_self_argmax": sa / np.sqrt(sa ** 2 + NOISE_VAR), "margin_abs_latent": st.margin_abs_latent})
    return rows


if __name__ == "__main__":
    S = pd.read_csv(W / "states.csv"); P = pars()
    res = Parallel(n_jobs=4)(delayed(one)(f, c, r, P, S) for f, c in ALL_CELLS for r in range(8))
    D = pd.DataFrame([x for r in res for x in r]); D.to_csv(W / "decoy_sd.csv", index=False)
    D["decoy"] = D.r_model_ref < .5
    print(D.groupby(["family", "decoy"])[["s_margin", "s_argmax", "s_median_cand", "rho_self_margin", "rho_self_argmax"]].median().round(3).to_string())
    print("spearman r_model vs rho_self_margin:", D[["r_model_ref", "rho_self_margin"]].corr("spearman").iloc[0, 1].round(3))
