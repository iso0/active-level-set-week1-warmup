"""FR step 1: gain-area diagnosis (outputs/research_campaign_20261029/opus_final_robustness/GAIN_AREA_PROTOCOL.md, registered in 4dced919
before any number was computed). EVALUATOR ONLY: reads recorded exports (EA validation and cand-DEV, C1C main) and the manifest labels;
opens no run and is never imported by a learner.

Pairs of C1 and HA_LEAN (A) probabilities at IDENTICAL paid prefixes (budgets 8..60):
  A's path: (C1_on_A, A_own) [EA cand-DEV: (C1, A)];  C1's path: (C1_own, A_on_C1)
Per learner-path, budget b and test run j (threshold 0.5, BA weights 1/(2 n1), 1/(2 n0)):
  R = C1 wrong & A right, L = C1 right & A wrong, W = both wrong (same side), OK = both right
  GA = sum_R w = BA_oracle - BA_C1  (pointwise oracle selection: the best any input-dependent convex weight can reach; ORACLE ONLY)
  AVG = decision of (p_C1 + p_A) / 2 (fixed-weight control)
  META = leave-cluster-out logistic "is A right" on disagreement points (label-informed DIAGNOSTIC, not a method; protocol section 3)
    python -m src.fr_gain
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness" / "gain"
EA = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "exports"
C1C = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation" / "exports"
BOTH = [("A", "C1_on_A", "A_own", "HA_LEAN-selected"), ("C", "C1_own", "A_on_C1", "C1-selected")]
SETS = [(EA / "validation_std", "STD", BOTH), (C1C / "main_s1", "STD", BOTH), (C1C / "main_s2", "STD", BOTH),
        (EA / "validation_k5", "K5", BOTH), (EA / "validation_k4", "K4", BOTH),
        (EA / "cand_dev_k5", "K5", [("A", "C1", "A", "HA_LEAN-selected")]), (EA / "cand_dev_k4", "K4", [("A", "C1", "A", "HA_LEAN-selected")])]
BUD = np.arange(8, 61)
WINS = {"B8_B24": tuple(range(8, 25)), "B25_B60": tuple(range(25, 61)), "B8_B60": tuple(range(8, 61))}
FEATS = ("lp1", "lp2", "adiff", "logb", "logd", "logdr")
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330)).to_numpy()


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4); return np.log(p) - np.log1p(-p)


def collect(M):
    """Per learner-path-budget table LB and the disagreement-point table DIS (features, target, weights, flags)."""
    ids_all = M.index.to_numpy(str); pos = {s: i for i, s in enumerate(ids_all)}; LX = np.log(M[list(P.INPUTS)].to_numpy(float))
    y_all = M.y.to_numpy(int); sk_all = M.shortK_NEW_original.astype(bool).to_numpy(); cn_all = ((M.source_batch == "NEW") & (M.y == 0)).to_numpy(); co_all = CORNER(M)
    LB, DIS = [], []
    for si, (d, cond, pairs) in enumerate(SETS):
        z = np.load(d / "predictions_f32.npz"); keys = [str(k) for k in z["keys"]]; kidx = {k: i for i, k in enumerate(keys)}
        paths = pd.read_csv(d / "paths.csv.gz"); learners = sorted({(int(k.split("|")[2]), int(k.split("|")[3])) for k in keys})
        for tag, s1, s2, pre in pairs:
            Pp = paths[paths.path.str.startswith(pre)]
            if pre == "HA_LEAN-selected":
                Pp = Pp[~Pp.path.str.startswith("C1")]
            seqs = {k: g.sort_values("query").sim_id.tolist() for k, g in Pp.groupby(["cluster", "learner"])}
            for (c, l) in learners:
                i1, i2 = kidx[f"{s1}|{cond}|{c}|{l}"], kidx[f"{s2}|{cond}|{c}|{l}"]
                if not (np.array_equal(z[f"budgets_{i1}"], BUD) and np.array_equal(z[f"budgets_{i2}"], BUD)):
                    raise RuntimeError("budgets are not 8..60")
                t1, t2 = z[f"test_ids_{i1}"].astype(str), z[f"test_ids_{i2}"].astype(str)
                if not np.array_equal(t1, t2):
                    raise RuntimeError(f"{d.name} {c}/{l}: the two systems do not share the test set")
                te = np.array([pos[s] for s in t1]); paid = np.array([pos[s] for s in seqs[(c, l)]])
                if len(paid) != 60 or np.intersect1d(paid, te).size:
                    raise RuntimeError("paid path malformed or overlaps the test set")
                pool = np.setdiff1d(np.arange(len(ids_all)), te); mu, sd = LX[pool].mean(0), LX[pool].std(0); Z = (LX - mu) / sd
                Dtp = np.linalg.norm(Z[te][:, None, :] - Z[paid][None, :, :], axis=2); Dnn = np.minimum.accumulate(Dtp, axis=1)
                Dpp = np.linalg.norm(Z[paid][:, None, :] - Z[paid][None, :, :], axis=2); np.fill_diagonal(Dpp, np.inf)
                p1 = np.asarray(z[f"pred_{i1}"], float); p2 = np.asarray(z[f"pred_{i2}"], float); y = y_all[te]
                n1, n0 = int((y == 1).sum()), int((y == 0).sum())
                if n1 == 0 or n0 == 0:
                    LB.append({"set": si, "condition": cond, "path": tag, "cluster": c, "learner": l, "budget": -1, "defined": False}); continue
                w = np.where(y == 1, 1.0 / (2 * n1), 1.0 / (2 * n0)); yk = y == 1
                h1, h2 = p1 >= 0.5, p2 >= 0.5; c1, c2 = h1 == yk, h2 == yk; ha = (p1 + p2) / 2 >= 0.5; ca = ha == yk
                R, Lm, Wm = ~c1 & c2, c1 & ~c2, ~c1 & ~c2
                sk, cn, co = sk_all[te], cn_all[te], co_all[te]; nan = np.full(len(BUD), np.nan)
                sb = np.array([float(np.median(np.min(Dpp[:b, :b], axis=1))) for b in BUD])
                mean_on = lambda A_, m: A_[:, m].mean(1) if m.any() else nan
                fr = pd.DataFrame({"set": si, "condition": cond, "path": tag, "cluster": c, "learner": l, "budget": BUD, "defined": True, "n1": n1, "n0": n0,
                                   "BA_C1": c1 @ w, "BA_A": c2 @ w, "BA_AVG": ca @ w, "GA": R @ w, "LA": Lm @ w, "WA": Wm @ w,
                                   "nR": R.sum(1), "nL": Lm.sum(1), "nW": Wm.sum(1), "nT": len(te),
                                   "GA_corner": (R & co) @ w, "GA_hard": (R & (sk | cn)) @ w, "GA_k": (R & yk) @ w, "n_sk": int(sk.sum()), "n_cn": int(cn.sum()),
                                   "sk_C1": mean_on(c1, sk), "sk_A": mean_on(c2, sk), "sk_O": mean_on(c1 | c2, sk), "sk_AVG": mean_on(ca, sk),
                                   "cn_C1": mean_on(c1, cn), "cn_A": mean_on(c2, cn), "cn_O": mean_on(c1 | c2, cn), "cn_AVG": mean_on(ca, cn)})
                fr["BA_O"] = fr.BA_C1 + fr.GA; LB.append(fr)
                jj, dd = np.nonzero(h1 != h2)
                if jj.size:
                    bb = BUD[jj]; dn = Dnn[dd, bb - 1]
                    DIS.append(pd.DataFrame({"set": si, "condition": cond, "path": tag, "cluster": c, "learner": l, "budget": bb,
                                             "lp1": _logit(p1[jj, dd]), "lp2": _logit(p2[jj, dd]), "adiff": np.abs(p1[jj, dd] - p2[jj, dd]), "logb": np.log(bb),
                                             "logd": np.log(dn + 1e-3), "logdr": np.log(dn / sb[jj] + 1e-3), "dnn": dn, "t": c2[jj, dd].astype(int), "w": w[dd],
                                             "y": y[dd], "sk": sk[dd], "cn": cn[dd], "corner": co[dd], "n_sk": int(sk.sum()), "n_cn": int(cn.sum()),
                                             "pickA_avg": (ha[jj, dd] == h2[jj, dd]).astype(int)}))
    LB = pd.concat([x if isinstance(x, pd.DataFrame) else pd.DataFrame([x]) for x in LB], ignore_index=True)
    LB["defined"] = LB["defined"].astype(bool)
    return LB, pd.concat(DIS, ignore_index=True)


def meta(DIS):
    """Leave-cluster-out (GroupKFold 10 over (condition, cluster)) weighted L2 logistic; scaling fitted inside the training folds."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    X = DIS[list(FEATS)].to_numpy(float); t = DIS.t.to_numpy(int); w = DIS.w.to_numpy(float); g = (DIS.condition + "_" + DIS.cluster.astype(str)).to_numpy()
    q = np.full(len(DIS), np.nan)
    for tr, te in GroupKFold(n_splits=10).split(X, t, g):
        sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X[tr]), t[tr], sample_weight=w[tr]); q[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    sc = StandardScaler().fit(X); full = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X), t, sample_weight=w)
    info = {"cv_auc_weighted": float(roc_auc_score(t, q, sample_weight=w)), "cv_auc_unweighted": float(roc_auc_score(t, q)),
            "share_A_right_weighted": float(w @ t / w.sum()), "full_fit_coef_standardised": dict(zip(FEATS, map(float, full.coef_[0]))), "full_fit_intercept": float(full.intercept_[0])}
    return q, info


def add_meta(LB, DIS, q):
    DIS = DIS.assign(q=q, pickA=(q > 0.5).astype(int)); DIS["dm"] = DIS.w * (2 * DIS.t - 1) * DIS.pickA
    DIS["dsk"] = np.where(DIS.sk, (2 * DIS.t - 1) * DIS.pickA, 0) / DIS.n_sk.clip(lower=1); DIS["dcn"] = np.where(DIS.cn, (2 * DIS.t - 1) * DIS.pickA, 0) / DIS.n_cn.clip(lower=1)
    k = ["set", "path", "cluster", "learner", "budget"]; agg = DIS.groupby(k)[["dm", "dsk", "dcn"]].sum().reset_index()
    LB = LB.merge(agg, on=k, how="left").fillna({"dm": 0.0, "dsk": 0.0, "dcn": 0.0})
    LB["BA_META"] = LB.BA_C1 + LB.dm; LB["sk_META"] = LB.sk_C1 + LB.dsk; LB["cn_META"] = LB.cn_C1 + LB.dcn
    return LB, DIS


def windows(LB):
    T = LB[LB.defined].copy(); out = []
    cols = ["BA_C1", "BA_A", "BA_O", "BA_AVG", "BA_META", "GA", "LA", "WA", "GA_corner", "GA_hard", "GA_k", "sk_C1", "sk_A", "sk_O", "sk_AVG", "sk_META", "cn_C1", "cn_A", "cn_O", "cn_AVG", "cn_META", "nR", "nL", "nW", "nT"]
    for wn, bs in WINS.items():
        a = T[T.budget.isin(bs)].groupby(["condition", "set", "path", "cluster", "learner"])[cols].mean().reset_index(); a["window"] = wn; out.append(a)
    return pd.concat(out, ignore_index=True)


def cluster_table(Wt, cond_set, win, col_x, col_a="BA_C1"):
    """Per cluster (STD: repeat; blocks: (design, startup) per region) mean over learners and paths of col_x - col_a; t bounds over clusters."""
    T = Wt[(Wt.window == win) & Wt.condition.isin(cond_set)]
    d = (T[col_x] - T[col_a]) if col_a else T[col_x]
    cm = d.groupby([T.condition, T.cluster]).mean(); r = EV.tstats(cm.values); r.update(EV.boot(cm.values)); r["clusters"] = int(len(cm)); return r


def run():
    RC.limit_threads(1); t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True); M = P.manifest()
    LB, DIS = collect(M); q, info = meta(DIS); LB, DIS = add_meta(LB, DIS, q); Wt = windows(LB)
    CONDS = {"STD": ("STD",), "K5": ("K5",), "K4": ("K4",), "GEOMETRIC": ("K5", "K4")}
    res = {"protocol": "GAIN_AREA_PROTOCOL.md (registered 4dced919 before any number)", "evidence": "DEV (already evaluated records; no new run)",
           "learner_paths": {c: int(LB[(LB.budget == 8) & LB.condition.isin(cs)].shape[0]) for c, cs in CONDS.items()},
           "undefined_learner_paths (one-class test set)": int((~LB.defined).sum()), "disagreement_points": int(len(DIS)), "meta": info, "levels": {}, "contrasts": {}}
    for c, cs in CONDS.items():
        for wn in WINS:
            T = Wt[(Wt.window == wn) & Wt.condition.isin(cs)]
            res["levels"][f"{c}|{wn}"] = {k: float(T.groupby(["condition", "cluster"])[k].mean().mean()) for k in
                                          ["BA_C1", "BA_A", "BA_O", "BA_AVG", "BA_META", "GA", "LA", "WA", "GA_corner", "GA_hard", "GA_k", "nR", "nL", "nW", "nT"]}
            res["contrasts"][f"{c}|{wn}"] = {x: cluster_table(Wt, cs, wn, x) for x in ("BA_A", "BA_O", "BA_AVG", "BA_META")}
            for tag in ("A", "C"):
                Tp = Wt[Wt.path == tag]
                if len(Tp[(Tp.window == wn) & Tp.condition.isin(cs)]):
                    res["contrasts"][f"{c}|{wn}|path_{tag}"] = {x: cluster_table(Tp, cs, wn, x) for x in ("BA_A", "BA_O", "BA_AVG", "BA_META")}
    for c, cs in CONDS.items():
        for wn in ("B8_B60", "B25_B60"):
            T = Wt[(Wt.window == wn) & Wt.condition.isin(cs)]
            res["levels"][f"{c}|{wn}|hard"] = {k: float(T.groupby(["condition", "cluster"])[k].mean().mean()) for k in
                                               ["sk_C1", "sk_A", "sk_O", "sk_AVG", "sk_META", "cn_C1", "cn_A", "cn_O", "cn_AVG", "cn_META"]}
    # where the gain area sits (disagreement points with A right), by distance quartile of the pooled geometric points
    G = DIS[DIS.condition.isin(("K5", "K4")) & (DIS.t == 1)]; S = DIS[(DIS.condition == "STD") & (DIS.t == 1)]
    qs = np.quantile(DIS.dnn, [0.25, 0.5, 0.75]); res["dnn_quartiles_all_disagreements"] = list(map(float, qs))
    for nm, X_ in (("GEOMETRIC", G), ("STD", S)):
        bins = np.digitize(X_.dnn, qs); res[f"GA_share_by_dnn_quartile|{nm}"] = {int(k): float(X_.w[bins == k].sum() / X_.w.sum()) for k in range(4)}
        res[f"GA_share_keyhole|{nm}"] = float(X_.w[X_.y == 1].sum() / X_.w.sum()); res[f"GA_share_corner|{nm}"] = float(X_.w[X_.corner].sum() / X_.w.sum())
    lv = res["levels"]; ct = res["contrasts"]
    g1 = lv["GEOMETRIC|B8_B60"]["GA"]; gm = ct["GEOMETRIC|B8_B60"]["BA_META"]; se = ct["STD|B8_B24"]["BA_META"]
    res["gate"] = {"G1_geometric_GA_B8_B60": g1, "G1_pass": bool(g1 >= 0.030),
                   "G2_META_minus_C1_geometric_B8_B60": gm, "G2_STD_META_minus_C1_B8_B24_mean": se["mean"],
                   "G2_pass": bool(gm["mean"] >= 0.010 and gm["lcb"] > 0 and se["mean"] >= -0.003)}
    res["gate"]["decision"] = ("PROCEED_TO_DEVELOPMENT" if res["gate"]["G1_pass"] and res["gate"]["G2_pass"] else
                               "CLOSE: gain area too small (G1)" if not res["gate"]["G1_pass"] else "CLOSE: gain only under the oracle selection (G2)")
    res["seconds"] = time.time() - t0
    LB.to_csv(OUT / "gain_learner_budget.csv.gz", index=False, compression="gzip"); Wt.to_csv(OUT / "gain_windows.csv.gz", index=False, compression="gzip")
    DIS.to_csv(OUT / "gain_disagreements.csv.gz", index=False, compression="gzip")
    (OUT / "GAIN_AREA.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    r = run(); print(json.dumps(r["gate"], indent=1, default=float)); print(json.dumps(r["meta"], indent=1)); print(round(r["seconds"], 1), "s")
