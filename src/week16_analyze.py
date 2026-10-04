"""Week 16 analysis: summary tables and the P1-P5 decisions exactly as defined in PREDICTIONS.md."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "outputs/week16_theory_meets_data"
PHYS_LIKE = ("dev", "curvedMono", "rough")
PAIRS = [("Vref", "Vt_ham_ref"), ("Vpool", "Vt_ham_pool"), ("Vref", "Vt_err_dense"), ("Vref", "Vt_nsd")]


def boot_ci(x, n=4000, seed=0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    b = np.random.default_rng(seed).choice(x, (n, len(x))).mean(1)
    return tuple(np.quantile(b, [.025, .975]))


def headroom_tables(S):
    rows = []
    for keys, g in [(("family",), None), (("family", "sigma"), None), (("family", "pool"), None), (("family", "budget"), None), (("cell",), None)]:
        for k, h in S.groupby(list(keys), dropna=False):
            ns = h[~h.saturated_ref]
            r = {"grouping": "+".join(keys), "group": "|".join(map(str, k if isinstance(k, tuple) else (k,))), "states": len(h),
                 "saturated_ref_share": float(h.saturated_ref.mean()), "median_r_model_ref": float(ns.r_model_ref.median()),
                 "decoy_share_ref": float((ns.r_model_ref < .5).mean()), "median_r_model_pool": float(h[~h.saturated_pool].r_model_pool.median())}
            for vm, vt in PAIRS:
                H, A = h[f"H|{vm}|{vt}"], h[f"A|{vm}|{vt}"]
                r[f"sumA/sumH|{vm}|{vt}"] = float(A.sum() / H.sum()) if H.sum() > 0 else np.nan
                r[f"median_rho|{vm}|{vt}"] = float(h[f"rho|{vm}|{vt}"].median())
                r[f"mean_H|{vt}"] = float(H.mean()); r[f"mean_A|{vm}|{vt}"] = float(A.mean())
                cr = h[f"vtmargin|{vt}"] / h[f"vtmax|{vt}"].where(h[f"vtmax|{vt}"] > 0)
                r[f"median_true_ratio_margin|{vt}"] = float(cr.median())
            rows.append(r)
    return pd.DataFrame(rows)


def p1_p2(S):
    phys = S[S.family.isin(PHYS_LIKE) & ~S.saturated_ref]
    p1_val = float(phys.r_model_ref.median())
    p2 = {}
    for fam in ("dev", "curvedMono", "branin4d", "rough"):
        h = S[S.family == fam]
        p2[fam] = float(h["A|Vref|Vt_ham_ref"].sum() / h["H|Vref|Vt_ham_ref"].sum())
    g = S[S.family == "gpworld"]
    p2_gp = float(g["A|Vref|Vt_ham_ref"].sum() / g["H|Vref|Vt_ham_ref"].sum())
    return ({"P1_median_r_model_ref_physics_like": p1_val, "P1_states_non_saturated": int(len(phys)), "P1_holds": p1_val >= .8},
            {"P2_sumA_over_sumH": p2, "P2_gpworld": p2_gp, "P2_holds": all(v < .25 for v in p2.values())})


def p3(S, D):
    phys = S[S.family.isin(PHYS_LIKE) & ~S.saturated_ref].copy()
    phys["dist_ratio"] = phys.margin_dist_labelled / phys.median_dist_cand_labelled
    dec, non = phys[phys.r_model_ref < .5], phys[phys.r_model_ref >= .5]
    out = {"decoys": int(len(dec)), "decoy_outside_hull_share": float(dec.margin_outside_hull.mean()),
           "decoy_median_dist_ratio": float(dec.dist_ratio.median()), "nondecoy_outside_hull_share": float(non.margin_outside_hull.mean()),
           "nondecoy_median_dist_ratio": float(non.dist_ratio.median()), "decoy_median_abs_latent": float(dec.margin_abs_latent.median()),
           "nondecoy_median_abs_latent": float(non.margin_abs_latent.median())}
    d = D[D.family.isin(PHYS_LIKE)]
    share = {v: float((g.r_model_ref.dropna() < .5).mean()) for v, g in d.groupby("variant")}
    vt = {v: float(g.Vt_ham_ref_margin.mean()) for v, g in d.groupby("variant")}
    vn = {v: float(g.Vt_nsd_margin.mean()) for v, g in d.groupby("variant")}
    out.update({"decoy_share_by_mean_variant": share, "mean_Vtrue_ham_ref_of_margin_pick_by_variant": vt,
                "mean_Vtrue_nsd_of_margin_pick_by_variant": vn})
    out["P3_holds"] = bool(out["decoy_outside_hull_share"] >= .6 and out["decoy_median_dist_ratio"] >= 1.5 and
                           share.get("mean_ml2", 1) < share["mean_base"] and share.get("mean_physics", 1) < share["mean_base"])
    return out


def partial_spearman(x, y, z):
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))
    def res(a, b):
        b1 = np.c_[np.ones(len(b)), b]; return a - b1 @ np.linalg.lstsq(b1, a, rcond=None)[0]
    r = stats.pearsonr(res(rx, rz), res(ry, rz))
    n = len(x); t = r.statistic * np.sqrt((n - 3) / max(1 - r.statistic ** 2, 1e-12))
    return float(r.statistic), float(2 * stats.t.sf(abs(t), n - 3))


def p4(Cal):
    sc = Cal[Cal.kind == "score"].groupby(["cell", "variant", "rep"])[["LL", "Brier", "JLL_near", "JBrier_near", "DE_near", "JLL_rand", "DE_rand"]].mean()
    au = Cal.groupby(["cell", "variant", "rep"])[["NSD_AULC", "BA_AULC"]].first()
    rg = Cal[Cal.kind == "regret"].groupby(["cell", "variant", "rep"])[["H_ham_ref", "H_nsd"]].mean()
    M = sc.join(au).join(rg).groupby(["cell", "variant"]).mean().reset_index()
    per_cell = []
    for cell, g in M.groupby("cell"):
        if g.NSD_AULC.nunique() < 3:
            continue
        r = {"cell": cell, "n_variants": len(g)}
        for s in ("LL", "Brier", "JLL_near", "JBrier_near", "DE_near", "JLL_rand"):
            r[f"rho_{s}_NSD"] = stats.spearmanr(-g[s], g.NSD_AULC).statistic
            r[f"rho_{s}_BA"] = stats.spearmanr(-g[s], g.BA_AULC).statistic
            r[f"rho_{s}_negH"] = stats.spearmanr(-g[s], -g.H_ham_ref).statistic
        per_cell.append(r)
    P = pd.DataFrame(per_cell)
    R = M.copy()
    for c in ("LL", "JLL_near", "DE_near", "NSD_AULC", "BA_AULC", "H_ham_ref"):
        R[c + "_rk"] = R.groupby("cell")[c].rank()
    pr, pp = partial_spearman(R.JLL_near_rk.values, R.NSD_AULC_rk.values, R.LL_rk.values)
    prd, ppd = partial_spearman(R.DE_near_rk.values, R.NSD_AULC_rk.values, R.LL_rk.values)
    diff = float((P.rho_JLL_near_NSD - P.rho_LL_NSD).mean())
    out = {"cells": int(len(P)), "mean_within_cell_rho_negLL_NSD": float(P.rho_LL_NSD.mean()),
           "mean_within_cell_rho_negJLLnear_NSD": float(P.rho_JLL_near_NSD.mean()), "mean_difference": diff,
           "partial_rho_JLLnear_NSD_given_LL": pr, "partial_p": pp, "partial_rho_DEnear_NSD_given_LL": prd, "partial_p_DE": ppd,
           "mean_within_cell_rho_negLL_BA": float(P.rho_LL_BA.mean()), "mean_within_cell_rho_negJLLnear_BA": float(P.rho_JLL_near_BA.mean()),
           "mean_within_cell_rho_negLL_negH": float(P.rho_LL_negH.mean()), "mean_within_cell_rho_negJLLnear_negH": float(P.rho_JLL_near_negH.mean()),
           "corr_LL_JLLnear_within_cell_ranks": float(stats.spearmanr(R.LL_rk, R.JLL_near_rk).statistic)}
    out["P4_holds"] = bool(diff >= .1 and abs(pr) >= .2 and pp < .05)
    return out, P, M


def p5(E):
    e = E[~E.whole_campaign]
    share = e.groupby(["campaign", "M"]).enriched.mean()
    return {"enriched_share": {f"{c}_M{m}": float(v) for (c, m), v in share.items()}, "P5_holds": bool((share >= .9).all())}


def real_tables(R, D):
    rows = []
    for (camp,), h in R.groupby(["campaign"]):
        r = {"campaign": camp, "states": len(h), "median_r_model_ref": float(h.r_model_ref.median()), "saturated_share": float(h.r_model_ref.isna().mean()),
             "decoy_share": float((h.r_model_ref.dropna() < .5).mean()),
             "decoy_outside_hull_share": float(h[h.r_model_ref < .5].margin_outside_hull.mean())}
        for vm in ("Vref", "Vpool"):
            for vt in ("Vt_BA_test", "Vt_err_all", "Vt_DCBD_all"):
                H, A = h[f"H|{vm}|{vt}"], h[f"A|{vm}|{vt}"]
                r[f"sumA/sumH|{vm}|{vt}"] = float(A.sum() / H.sum()) if H.sum() > 0 else np.nan
                r[f"mean_A|{vm}|{vt}"] = float(A.mean()); r[f"median_rho|{vm}|{vt}"] = float(h[f"rho|{vm}|{vt}"].median())
        rows.append(r)
    dv = D.groupby(["campaign", "variant"]).agg(decoy_share=("r_model_ref", lambda x: float((x.dropna() < .5).mean())),
                                               outside_hull=("margin_outside_hull", "mean"), Vt_BA=("Vt_BA_test_margin", "mean"),
                                               Vt_DCBD=("Vt_DCBD_all_margin", "mean")).reset_index()
    return pd.DataFrame(rows), dv


def real_p4(Pool):
    au = Pool.groupby(["campaign", "repeat", "variant"]).apply(
        lambda g: pd.Series({**{c: np.trapezoid(g.sort_values("budget")[c], g.sort_values("budget").budget) / 64 for c in ("BA_pooled", "q20_meanfold", "DCBD_pooled")},
                             **{c: g[c].mean() for c in ("LL", "JLL_near", "DE_near", "JLL_rand")}}), include_groups=False).reset_index()
    rows = []
    for (camp, rep), g in au.groupby(["campaign", "repeat"]):
        r = {"campaign": camp, "repeat": rep}
        for s in ("LL", "JLL_near", "DE_near"):
            for y in ("BA_pooled", "q20_meanfold", "DCBD_pooled"):
                r[f"rho_{s}_{y}"] = stats.spearmanr(-g[s], g[y]).statistic
        rows.append(r)
    return au, pd.DataFrame(rows).groupby("campaign").mean(numeric_only=True).drop(columns="repeat").reset_index()


def main():
    S = pd.read_csv(W / "headroom/states.csv"); D = pd.read_csv(W / "headroom/decoy_variants.csv")
    T = headroom_tables(S); T.to_csv(W / "headroom/summary.csv", index=False)
    v1, v2 = p1_p2(S); v3 = p3(S, D)
    verdict = {"P1": v1, "P2": v2, "P3": v3}
    dev = S[S.family == "dev"]
    verdict["argmax_Vmodel_vs_margin_dev"] = {
        "mean_A_ham_ref": float(dev["A|Vref|Vt_ham_ref"].mean()), "ci": boot_ci(dev.groupby(["cell", "rep"])["A|Vref|Vt_ham_ref"].mean().values),
        "mean_A_nsd": float(dev["A|Vref|Vt_nsd"].mean()), "ci_nsd": boot_ci(dev.groupby(["cell", "rep"])["A|Vref|Vt_nsd"].mean().values),
        "share_states_A_pos_ham": float((dev["A|Vref|Vt_ham_ref"] > 0).mean()), "share_states_A_neg_ham": float((dev["A|Vref|Vt_ham_ref"] < 0).mean())}
    if (W / "calibration/calibration.csv").exists():
        Cal = pd.read_csv(W / "calibration/calibration.csv")
        v4, P, M = p4(Cal); verdict["P4"] = v4
        P.to_csv(W / "calibration/within_cell_spearman.csv", index=False); M.to_csv(W / "calibration/cell_variant_means.csv", index=False)
    if (W / "discovery/tail_enrichment.csv").exists():
        verdict["P5"] = p5(pd.read_csv(W / "discovery/tail_enrichment.csv"))
    if (W / "real_data/states.csv").exists():
        rt, dv = real_tables(pd.read_csv(W / "real_data/states.csv"), pd.read_csv(W / "real_data/decoy_variants.csv"))
        rt.to_csv(W / "real_data/summary.csv", index=False); dv.to_csv(W / "real_data/decoy_summary.csv", index=False)
        if (W / "real_data/calibration_pooled.csv").exists():
            au, rp = real_p4(pd.read_csv(W / "real_data/calibration_pooled.csv"))
            au.to_csv(W / "real_data/calibration_aulc.csv", index=False); rp.to_csv(W / "real_data/calibration_spearman.csv", index=False)
    (W / "VERDICTS.json").write_text(json.dumps(verdict, indent=2, default=float))
    print(json.dumps(verdict, indent=1, default=float))


if __name__ == "__main__":
    main()
