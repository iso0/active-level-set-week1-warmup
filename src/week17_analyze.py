"""Week 17 decisive analysis — implements PREDICTIONS_AND_FREEZE.md exactly (committed with the freeze)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "outputs/week17_model_and_acquisition"
CELLS_MISLEADING = ("H07_theta60", "H08_theta90_physics_useless", "H09_order_violation")


def boot(d, n=4000, seed=0):
    d = np.asarray(d, float); d = d[~np.isnan(d)]
    if len(d) < 2:
        return (np.nan, np.nan)
    b = np.random.default_rng(seed).choice(d, (n, len(d))).mean(1)
    return float(np.quantile(b, .025)), float(np.quantile(b, .975))


# ----------------------------------------------------------------------------- synthetic held-out
def synthetic(df):
    a = df[df.kind == "aulc"]
    w = a.pivot_table(index=["cell", "rep"], columns=["model", "rule"], values="NSD_0.1_AULC")
    def cell_diff(x, y):
        d = (w[x] - w[y]); return d.groupby(level=0).mean(), d
    out = {}
    lt_g3, d_all = cell_diff(("LT", "margin"), ("G3", "margin"))
    out["M1_mean_LT_minus_G3"] = float(lt_g3.mean()); out["M1_ci_over_paths"] = boot(d_all.values)
    out["M2_cells_LT_gt_G3"] = int((lt_g3 > 0).sum())
    out["M3_min_cell_LT_minus_G3"] = float(lt_g3.min()); out["M3_min_cell"] = str(lt_g3.idxmin())
    lt_m3, _ = cell_diff(("LT", "margin"), ("M3", "margin")); lt_ab, _ = cell_diff(("LT", "margin"), ("M3_Cfree", "margin"))
    out["M4_cells_LT_gt_M3"] = int((lt_m3 > 0).sum()); out["M4_cells_LT_gt_M3_Cfree"] = int((lt_ab > 0).sum())
    out["per_cell_LT_minus_G3"] = lt_g3.round(4).to_dict()
    out["per_cell_M3_minus_G3"] = cell_diff(("M3", "margin"), ("G3", "margin"))[0].round(4).to_dict()
    out["per_cell_M3_Cfree_minus_G3"] = cell_diff(("M3_Cfree", "margin"), ("G3", "margin"))[0].round(4).to_dict()
    out["per_cell_LT_minus_M3_Cfree"] = lt_ab.round(4).to_dict()
    acq = {}
    for model in ("G3", "M3", "LT", "M3_Cfree"):
        for rule in ("peer", "coverage", "random"):
            c, d = cell_diff((model, rule), (model, "margin"))
            acq[f"{model}|{rule}-margin"] = {"mean": float(c.mean()), "cells_pos": int((c > 0).sum()), "min_cell": float(c.min()), "ci": boot(d.values)}
    out["acquisition"] = acq
    out["M_pass"] = bool(out["M1_mean_LT_minus_G3"] >= .015 and out["M2_cells_LT_gt_G3"] >= 8 and out["M3_min_cell_LT_minus_G3"] >= -.03)
    def a_pass(model, rule):
        r = acq[f"{model}|{rule}-margin"]; return bool(r["mean"] >= .01 and r["cells_pos"] >= 8 and r["min_cell"] >= -.03)
    out["A1_peer_LT"] = a_pass("LT", "peer"); out["A2_peer_G3"] = a_pass("G3", "peer"); out["A3_coverage_LT"] = a_pass("LT", "coverage")
    # secondary endpoints under margin
    sec = {}
    for k in ("ASSD_AULC", "dense_BA_AULC", "q20_accuracy_AULC", "finite_BA_AULC", "NSD_0.05_AULC"):
        ww = a.pivot_table(index=["cell", "rep"], columns=["model", "rule"], values=k)
        for m in ("M3", "LT", "M3_Cfree"):
            sec[f"{k}|{m}-G3"] = float((ww[(m, "margin")] - ww[("G3", "margin")]).groupby(level=0).mean().mean())
    out["secondary_margin_vs_G3"] = sec
    # q20 vs NSD agreement in sign across cells for LT - G3
    q = a.pivot_table(index=["cell", "rep"], columns=["model", "rule"], values="q20_accuracy_AULC")
    dq = (q[("LT", "margin")] - q[("G3", "margin")]).groupby(level=0).mean()
    out["q20_NSD_sign_agreement_LT_vs_G3"] = float(np.mean(np.sign(dq) == np.sign(lt_g3)))
    # oracle decomposition
    o = df[df.kind == "oracle"]
    dec = o.groupby("model")[["H_nsd", "A_nsd", "rho_nsd", "margin_nsd", "peer_nsd", "rand_nsd", "max_nsd", "H_ham", "A_ham", "rho_ham"]].mean()
    out["oracle_by_model"] = dec.round(5).to_dict(orient="index")
    hc = o.groupby(["cell", "model"]).H_nsd.mean().unstack()
    out["cells_H_LT_lt_H_G3"] = int((hc["LT"] < hc["G3"]).sum())
    pf = o.groupby("cell").apply(lambda g: float((g.peer_abs_f > g.margin_abs_f).mean()), include_groups=False)
    out["cells_peer_pick_farther_than_margin_majority"] = int((pf > .5).sum()); out["peer_farther_share_by_cell"] = pf.round(3).to_dict()
    # common-design model quality
    qq = df[df.kind == "quality"]
    out["quality"] = qq.groupby(["model", "n"])[["NSD_0.1", "dense_BA", "sign_logloss_ref", "q20_accuracy", "finite_BA"]].mean().round(4).reset_index().to_dict(orient="records")
    out["max_fp_err"] = float(a.max_fp_err.max())
    return out


# ----------------------------------------------------------------------------- real AL
def real(pred):
    from src.week17_audit import campaigns
    from src.week15_metric import dc_boundary_dice
    from src.week12_development_common import load_new, load_old
    C = campaigns()
    zev = {"NEW": StandardScaler().fit_transform(load_new()[["P", "VX", "LS", "ST"]]), "OLD": StandardScaler().fit_transform(load_old()[["P", "VX", "LS", "ST"]])}
    rows = []
    for (camp, rep, model, rule, b), g in pred.groupby(["campaign", "repeat", "model", "rule", "budget"]):
        y = C[camp][2]; mino = 0 if camp == "NEW" else 1
        idx = np.concatenate([np.array(r.split(","), int) for r in g.rows]); p = np.concatenate([np.array(r.split(","), float) for r in g.p])
        qa = []
        for r in g.itertuples():
            ii = np.array(r.rows.split(","), int); pp = np.array(r.p.split(","), float); qq = np.array(r.q20.split(","), int).astype(bool)
            if qq.any():
                qa.append(np.mean((pp[qq] >= .5) == y[ii][qq]))
        yh = (p >= .5).astype(int); yy = y[idx]
        full = np.full(len(y), -1); full[idx] = yh
        ok = full >= 0
        rows.append({"campaign": camp, "repeat": rep, "model": model, "rule": rule, "budget": b,
                     "BA": float((np.mean(yh[yy == 1] == 1) + np.mean(yh[yy == 0] == 0)) / 2), "minority_recall": float(np.mean(yh[yy == mino] == mino)),
                     "AUC": float(roc_auc_score(yy, p)), "q20": float(np.mean(qa)),
                     "DCBD": dc_boundary_dice(zev[camp][ok], y[ok], full[ok])["DC_BD"]})
    R = pd.DataFrame(rows)
    au = R.groupby(["campaign", "repeat", "model", "rule"]).apply(
        lambda g: pd.Series({**{f"{k}_AULC": np.trapezoid(g.sort_values("budget")[k], g.sort_values("budget").budget) / 64 for k in ("BA", "q20", "DCBD")},
                             "minority_recall_B80": float(g[g.budget == 80].minority_recall.iloc[0]), "AUC_B80": float(g[g.budget == 80].AUC.iloc[0])}),
        include_groups=False).reset_index()
    out = {}
    for camp, g in au.groupby("campaign"):
        res = {}
        w = g.pivot_table(index="repeat", columns=["model", "rule"], values=["BA_AULC", "q20_AULC", "DCBD_AULC", "minority_recall_B80", "AUC_B80"])
        for k in ("BA_AULC", "q20_AULC", "DCBD_AULC", "minority_recall_B80", "AUC_B80"):
            for m in ("M3", "LT", "M3_Cfree"):
                d = (w[k][(m, "margin")] - w[k][("G3", "margin")]).values
                res[f"{k}|{m}-G3 (margin)"] = {"mean": float(d.mean()), "ci": boot(d)}
            for m in ("G3", "M3", "LT", "M3_Cfree"):
                for rule in ("candB", "peer", "random"):
                    d = (w[k][(m, rule)] - w[k][(m, "margin")]).values
                    res[f"{k}|{m}:{rule}-margin"] = {"mean": float(d.mean()), "ci": boot(d)}
        res["levels_margin"] = g[g.rule == "margin"].groupby("model")[["BA_AULC", "q20_AULC", "DCBD_AULC", "minority_recall_B80", "AUC_B80"]].mean().round(4).to_dict(orient="index")
        out[camp] = res
    return out, R, au


def verdict(syn, rea):
    new = rea.get("NEW", {})
    m5 = (new.get("BA_AULC|LT-G3 (margin)", {}).get("mean", -1) >= -.02 and new.get("q20_AULC|LT-G3 (margin)", {}).get("mean", -1) >= -.02
          and rea.get("OLD", {}).get("BA_AULC|LT-G3 (margin)", {}).get("mean", -1) >= 0)
    model_bt = bool(syn["M_pass"] and m5)
    acq_rule = None
    for rule, flag in (("peer", syn["A1_peer_LT"]), ("coverage", syn["A3_coverage_LT"])):
        if flag:
            key = "peer" if rule == "peer" else "candB"
            r1 = new.get(f"q20_AULC|LT:{key}-margin", {}).get("mean", -1); r2 = new.get(f"BA_AULC|LT:{key}-margin", {}).get("mean", -1)
            if r1 >= 0 and r2 >= 0:
                acq_rule = rule
    mech = bool(np.mean([syn["per_cell_M3_minus_G3"].get(c, 0) < 0 for c in CELLS_MISLEADING]) >= 2 / 3
                and abs(syn["per_cell_LT_minus_G3"].get("H08_theta90_physics_useless", 1)) <= .015
                and all(syn["acquisition"][f"{m}|peer-margin"]["mean"] < 0 for m in ("G3", "LT"))
                and syn["cells_peer_pick_farther_than_margin_majority"] >= 10)
    if model_bt and acq_rule:
        v = "MODEL + ACQUISITION BREAKTHROUGH"
    elif model_bt:
        v = "MODEL BREAKTHROUGH ONLY"
    elif mech:
        v = "MECHANISM RESOLVED"
    else:
        v = "NO CHANGE JUSTIFIED"
    return {"M5_real_noninferiority": bool(m5), "model_breakthrough": model_bt, "acquisition_rule": acq_rule, "mechanism_criteria": mech, "verdict": v}


def main():
    out = {}
    syn = synthetic(pd.read_csv(W / "heldout/heldout_results.csv.gz")); out["synthetic"] = syn
    rea, R, au = real(pd.read_csv(W / "real_al/real_al_predictions.csv.gz")); out["real"] = rea
    R.to_csv(W / "real_al/real_al_pooled_by_budget.csv", index=False); au.to_csv(W / "real_al/real_al_aulc_by_repeat.csv", index=False)
    out["verdict"] = verdict(syn, rea)
    (W / "VERDICT.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out["verdict"], indent=1))


if __name__ == "__main__":
    main()
