"""Week 16 items 1-3 on real data (descriptive only: NEW-136 = POST-HOC, OLD-405 = HISTORICAL).

Model and splits as in the Week 15 replays (`src/week15_real.py`): fixed G3 hyperparameters fitted on OLD-405,
features standardized with the OLD scaler, maximin startup with continuation, margin refinement, seeds
[15, 10·repeat + fold] (NEW) and [16, 10·repeat + fold] (OLD Week 8.5 repeats 1-4).

Item 1 per state (budgets 16, 24, 32, 48, 64, 80): PEER r_model for the reference cloud (uniform in the
training-pool box) and the pool; V_true(j) = *realized* improvement after adding (j, y_j) — labels are
deterministic simulation outcomes — in held-out fold BA, in error rate over all campaign points and in DC-BD
over all campaign points.  Item 2: margin pick under zero mean, ML-II constant mean and physics mean (log h).
Item 3: model variants with their own margin paths; pooled out-of-fold endpoints per repeat as in Week 15.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from src.week13_synthetic_al import maximin_order
from src.week15_metric import default_radius, dc_boundary_dice, knn_density
from src.week15_real import F, W12
from src.week16_cells import margin_pick
from src.week16_headroom import outside_hull, ratio
from src.week16_peer import Model, peer_values

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week16_theory_meets_data/real_data"
HYP = json.loads((ROOT / "outputs/week15_boundary_acquisition/real_data/hyperparameters.json").read_text())["OLD_G3_ML2"]
BUDGETS16 = (16, 24, 32, 48, 64, 80)
TRACE = tuple(range(16, 81, 4))
CAP = 120
NOISE = 8 / np.pi


def campaigns():
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv"); new = pd.read_csv(W12 / "audit/new136.csv")
    sc = StandardScaler().fit(old[F])
    out = {}
    for name, df in (("NEW", new), ("OLD", old)):
        z = sc.transform(df[F]); y = df.has_keyhole.to_numpy().astype(int)
        z_eval = StandardScaler().fit_transform(df[F])
        out[name] = {"z": z, "y": y, "z_eval": z_eval, "r": default_radius(z_eval), "dens": knn_density(z_eval), "df": df}
    out["phys"] = lambda Z: (lambda R: np.log(R[:, 0]) - .5 * np.log(R[:, 1]) - 1.5 * np.log(R[:, 2]))(sc.inverse_transform(np.asarray(Z)))
    return out


def splits(C):
    S = []
    for s in json.loads((W12 / "audit/original_splits.json").read_text()):
        S.append({"campaign": "NEW", "repeat": s["repeat"], "fold": s["fold"], "train": np.asarray(s["train_indices"]),
                  "test": np.asarray(s["test_indices"]), "seed": [15, s["repeat"] * 10 + s["fold"]]})
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "repeat", "fold", "role", "population_row_index"])
    for _, g in man[man.repeat <= 4].groupby("run_id"):
        rep, fold = int(g.repeat.iloc[0]), int(g.fold.iloc[0])
        S.append({"campaign": "OLD", "repeat": rep, "fold": fold, "train": g[g.role == "training_pool"].population_row_index.to_numpy(),
                  "test": g[g.role == "untouched_test"].population_row_index.to_numpy(), "seed": [16, rep * 10 + fold]})
    return S


def q20_masks(C, S):
    """Historical q20 flags per split (NEW: Week 12 stored flags; OLD: Week 8.5 b1 distance), as in Week 15."""
    q = pd.read_csv(W12 / "active_learning/predictions.csv.gz", usecols=["split_id", "arm", "budget", "row_index", "q20"])
    q = q[(q.arm == "M3_margin__maximin16_continue") & (q.budget == 80)]
    qm = {(r.split_id, r.row_index): r.q20 for r in q.itertuples()}
    sid = {(s["repeat"], s["fold"]): s["split_id"] for s in json.loads((W12 / "audit/original_splits.json").read_text())}
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    old = C["OLD"]["df"]
    dist = w85.b1_distance(old.rename(columns={"sim_id": "experiment_name"}))
    for s in S:
        te = s["test"]
        if s["campaign"] == "NEW":
            s["q20"] = np.array([bool(qm[(sid[(s["repeat"], s["fold"])], int(r))]) for r in te])
        else:
            order = np.lexsort((old.sim_id.to_numpy(object)[te], dist[te]))
            m = np.zeros(len(te), bool); m[order[:math.ceil(.2 * len(te))]] = True
            s["q20"] = m
    return S


def start(z, y, seed):
    order = maximin_order(z, np.random.default_rng([seed[0], seed[1], 2]))
    L = list(order[:8]); k = 8
    while len(set(y[L])) < 2:
        L.append(int(order[k])); k += 1
    return L


def path(model, z, y, L0, budgets, trace=None):
    L = list(L0); states, posts = {}, {}
    while True:
        b = len(L)
        post = model.fit(z[L], y[L])
        if b in budgets:
            states[b] = list(L)
        if trace is not None and b in trace:
            posts[b] = post
        if b >= 80:
            return states, posts
        L.append(margin_pick(post, z, np.setdiff1d(np.arange(len(z)), L)))


def metrics_all(C, camp, post, tr, te):
    c = C[camp]
    yh = (post.latent_mean(c["z"]) > 0).astype(int)
    yt = c["y"][te]; ht = yh[te]
    ba = np.nanmean([np.mean(ht[yt == k] == k) if (yt == k).any() else np.nan for k in (0, 1)])
    return {"BA_test": float(ba), "err_all": float(np.mean(yh != c["y"])),
            "DCBD_all": dc_boundary_dice(c["z_eval"], c["y"], yh, r=c["r"], density=c["dens"])["DC_BD"]}


def item12(s, C):
    camp = s["campaign"]; c = C[camp]
    tr, te = s["train"], s["test"]; z, y = c["z"][tr], c["y"][tr]
    lo, hi = z.min(0), z.max(0)
    Zref = lo + (hi - lo) * np.random.default_rng([15, 97]).random((400, 4))
    base_m = Model(HYP["ls"], HYP["var"])
    L0 = start(z, y, s["seed"])
    states, _ = path(base_m, z, y, L0, BUDGETS16)
    rng = np.random.default_rng([16, 11, s["seed"][1], len(tr)])
    S, D = [], []
    meta = {"campaign": camp, "repeat": s["repeat"], "fold": s["fold"]}
    for b, L in states.items():
        post = base_m.fit(z[L], y[L]); cands = np.setdiff1d(np.arange(len(z)), L)
        m = margin_pick(post, z, cands)
        Vref = peer_values(post, Zref, z[cands]); Vpool = peer_values(post, z, z[cands]); im = int(np.flatnonzero(cands == m)[0])
        base = metrics_all(C, camp, post, tr, te)
        keep = {m, int(cands[np.argmax(Vref)]), int(cands[np.argmax(Vpool)])}
        sub = cands if len(cands) <= CAP else np.sort(np.r_[list(keep), rng.choice([k for k in cands if k not in keep], CAP - len(keep), replace=False)]).astype(int)
        rows = []
        for j in sub:
            k = int(np.flatnonzero(cands == j)[0])
            e = metrics_all(C, camp, base_m.fit(z[np.r_[L, j]], np.r_[y[L], y[j]]), tr, te)
            rows.append({"cand": j, "Vref": Vref[k], "Vpool": Vpool[k], "is_margin": j == m,
                         "Vt_BA_test": e["BA_test"] - base["BA_test"], "Vt_err_all": base["err_all"] - e["err_all"],
                         "Vt_DCBD_all": e["DCBD_all"] - base["DCBD_all"]})
        Cd = pd.DataFrame(rows)
        st = {**meta, "budget": b, "n_cands": len(cands), "subsampled": len(sub) < len(cands),
              "r_model_ref": ratio(Vref[im], Vref.max()), "r_model_pool": ratio(Vpool[im], Vpool.max()),
              "margin_dist_labelled": float(np.linalg.norm(z[L] - z[m], axis=1).min()),
              "median_dist_cand_labelled": float(np.median(np.linalg.norm(z[cands][:, None] - z[L][None], axis=2).min(1))),
              "margin_outside_hull": bool(outside_hull(z[L], z[m])), "margin_label": int(y[m]),
              **{f"base_{k}": v for k, v in base.items()}}
        for vm in ("Vref", "Vpool"):
            jm = Cd[vm].idxmax()
            for vt in ("Vt_BA_test", "Vt_err_all", "Vt_DCBD_all"):
                vmarg = float(Cd.loc[Cd.is_margin, vt].iloc[0])
                st[f"H|{vm}|{vt}"] = float(Cd[vt].max() - vmarg); st[f"A|{vm}|{vt}"] = float(Cd.loc[jm, vt] - vmarg)
                st[f"rho|{vm}|{vt}"] = float(spearmanr(Cd[vm], Cd[vt]).statistic) if Cd[vt].nunique() > 1 else np.nan
        S.append(st)
        for name, mdl in (("mean_zero", base_m), ("mean_ml2", Model(HYP["ls"], HYP["var"], mean="ml2")),
                          ("mean_physics", Model(HYP["ls"], HYP["var"], mean="physics", phys=C["phys"]))):
            pv = mdl.fit(z[L], y[L]); mv = margin_pick(pv, z, cands)
            Vr = peer_values(pv, Zref, z[cands]); iv = int(np.flatnonzero(cands == mv)[0])
            e0 = metrics_all(C, camp, pv, tr, te); e1 = metrics_all(C, camp, mdl.fit(z[np.r_[L, mv]], np.r_[y[L], y[mv]]), tr, te)
            D.append({**meta, "budget": b, "variant": name, "r_model_ref": ratio(Vr[iv], Vr.max()),
                      "margin_dist_labelled": float(np.linalg.norm(z[L] - z[mv], axis=1).min()),
                      "margin_outside_hull": bool(outside_hull(z[L], z[mv])),
                      "Vt_BA_test_margin": e1["BA_test"] - e0["BA_test"], "Vt_DCBD_all_margin": e1["DCBD_all"] - e0["DCBD_all"]})
    return S, D


def real_variants():
    ls, var = np.asarray(HYP["ls"], float), float(HYP["var"])
    return {"base": Model(ls, var), "ls_x0.5": Model(ls * .5, var), "ls_x2": Model(ls * 2, var), "var_x0.25": Model(ls, var * .25),
            "var_x4": Model(ls, var * 4), "mean_ml2": Model(ls, var, mean="ml2"), "mean_physics": None}


def label_pair_scores(post, Zt, yt, pairs):
    mu, v = post.mean_var(Zt); sg = np.sqrt(v + NOISE); C = post.cross_cov(Zt, Zt)
    from src.week16_calibration import pair_probs
    p = ndtr(mu / sg)
    ll = -np.log(np.clip(np.where(yt == 1, p, 1 - p), 1e-12, 1))
    out = {"LL": float(ll.mean()), "Brier": float(((p - yt) ** 2).mean())}
    if len(pairs):
        i, k = pairs[:, 0], pairs[:, 1]
        P = pair_probs(mu[i] / sg[i], mu[k] / sg[k], np.clip(C[i, k] / (sg[i] * sg[k]), -.999999, .999999))
        obs = np.select([(yt[i] == a) & (yt[k] == b) for a, b in P], [P[key] for key in P])
        jll = -np.log(np.clip(obs, 1e-12, 1))
        out.update({"JLL": float(jll.mean()), "DE": float((jll - ll[i] - ll[k]).mean())})
    return out


def item3(s, C):
    camp = s["campaign"]; c = C[camp]
    tr, te = s["train"], s["test"]; z, y = c["z"][tr], c["y"][tr]; zt, yt = c["z"][te], c["y"][te]
    from scipy.spatial import cKDTree
    _, nn = cKDTree(c["z_eval"][te]).query(c["z_eval"][te], k=min(5, len(te)))
    near = np.unique(np.sort(np.c_[np.repeat(np.arange(len(te)), nn.shape[1] - 1), nn[:, 1:].ravel()], 1), axis=0)
    allp = np.array([(i, k) for i in range(len(te)) for k in range(i + 1, len(te))])
    rnd = allp[np.random.default_rng([16, 56, s["seed"][1]]).choice(len(allp), min(500, len(allp)), replace=False)]
    L0 = start(z, y, s["seed"])
    rows = []
    for name, mdl in real_variants().items():
        if mdl is None:
            mdl = Model(HYP["ls"], HYP["var"], mean="physics", phys=C["phys"])
        _, posts = path(mdl, z, y, L0, (), TRACE)
        for b, post in posts.items():
            sn = label_pair_scores(post, zt, yt, near); sr = label_pair_scores(post, zt, yt, rnd)
            rows.append({"campaign": camp, "repeat": s["repeat"], "fold": s["fold"], "variant": name, "budget": b,
                         "prob": post.proba(zt).tolist(), "LL": sn["LL"], "Brier": sn["Brier"], "JLL_near": sn.get("JLL"),
                         "DE_near": sn.get("DE"), "JLL_rand": sr.get("JLL"), "DE_rand": sr.get("DE")})
    return rows


def pooled_endpoints(R, C, S):
    """Week 15 real endpoints per (campaign, repeat, variant, budget) from the item-3 rows."""
    q20 = {(s["campaign"], s["repeat"], s["fold"]): (s["test"], s["q20"]) for s in S}
    out = []
    for (camp, rep, var, b), g in R.groupby(["campaign", "repeat", "variant", "budget"]):
        c = C[camp]; n = len(c["y"])
        pr = np.full(n, np.nan); qa = []
        for r in g.itertuples():
            te, qm = q20[(camp, rep, r.fold)]
            p = np.asarray(r.prob); pr[te] = p
            if qm.any():
                qa.append(np.mean((p[qm] >= .5).astype(int) == c["y"][te][qm]))
        ok = ~np.isnan(pr); yh = (pr[ok] >= .5).astype(int); yy = c["y"][ok]
        out.append({"campaign": camp, "repeat": rep, "variant": var, "budget": b,
                    "BA_pooled": float((np.mean(yh[yy == 1] == 1) + np.mean(yh[yy == 0] == 0)) / 2),
                    "q20_meanfold": float(np.mean(qa)),
                    "DCBD_pooled": dc_boundary_dice(c["z_eval"][ok], yy, yh)["DC_BD"],
                    **{k: float(g[k].mean()) for k in ("LL", "Brier", "JLL_near", "DE_near", "JLL_rand", "DE_rand")}})
    return pd.DataFrame(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C = campaigns(); S = q20_masks(C, splits(C))
    res = Parallel(n_jobs=7, verbose=5)(delayed(item12)(s, C) for s in S)
    pd.DataFrame([x for r in res for x in r[0]]).to_csv(OUT / "states.csv", index=False)
    pd.DataFrame([x for r in res for x in r[1]]).to_csv(OUT / "decoy_variants.csv", index=False)
    res3 = Parallel(n_jobs=7, verbose=5)(delayed(item3)(s, C) for s in S)
    R = pd.DataFrame([x for r in res3 for x in r])
    R.drop(columns=["prob"]).to_csv(OUT / "calibration_split_scores.csv.gz", index=False)
    pooled_endpoints(R, C, S).to_csv(OUT / "calibration_pooled.csv", index=False)


if __name__ == "__main__":
    main()
