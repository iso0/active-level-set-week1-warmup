"""Week 15 frozen analysis: success criteria S1-S6, verdict, ablation, metric criteria (written before results)."""
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "outputs/week15_boundary_acquisition/heldout"


def aulc(g, col):
    g = g.sort_values("budget")
    return float(np.trapezoid(g[col], g.budget) / (g.budget.max() - g.budget.min()))


def boot(d, seed=0, draws=4000):
    d = np.asarray(d, float); b = np.random.default_rng(seed).choice(d, (draws, len(d))).mean(1)
    return float(d.mean()), float(np.quantile(b, .025)), float(np.quantile(b, .975))


def acquisition():
    df = pd.read_csv(H / "al_confirm.csv.gz")
    df = df[df.budget.between(16, 80)]
    A = df.groupby(["cell", "rep", "policy"]).apply(lambda g: pd.Series({c: aulc(g, c) for c in ("NSD_0.1", "NSD_0.05", "ASSD", "q20_accuracy", "BA")}),
                                                     include_groups=False).reset_index()
    meta = df.drop_duplicates("cell").set_index("cell")
    A.to_csv(H / "aulc_confirm.csv", index=False)
    rows = []
    for cell, g in A.groupby("cell"):
        w = g.pivot(index="rep", columns="policy")
        r = {"cell": cell, "family": meta.loc[cell, "family"], "pool": int(meta.loc[cell, "cfg_pool"]),
             "sigma": float(meta.loc[cell, "cfg_sigma"]) if "cfg_sigma" in meta and not pd.isna(meta.loc[cell, "cfg_sigma"]) else np.nan,
             "box": meta.loc[cell, "cfg_box"] if "cfg_box" in meta else np.nan, "m0": meta.loc[cell, "cfg_m0"] if "cfg_m0" in meta else np.nan}
        for pol in ("random", "coverage", "bald", "ebrd", "vsur"):
            for c in ("NSD_0.1", "ASSD", "q20_accuracy", "BA"):
                m, lo, hi = boot(w[c][pol] - w[c]["margin"])
                r[f"{pol}-margin_{c}"] = m; r[f"{pol}-margin_{c}_lo"] = lo; r[f"{pol}-margin_{c}_hi"] = hi
        r["ebrd_assd_ratio"] = float(w["ASSD"]["ebrd"].mean() / w["ASSD"]["margin"].mean())
        r["ebrd-vsur_NSD_0.1"] = float((w["NSD_0.1"]["ebrd"] - w["NSD_0.1"]["vsur"]).mean())
        fl = df[(df.cell == cell) & (df.budget == 80)].groupby("policy").flipped_acquired.mean()
        r["flip_margin"], r["flip_ebrd"] = float(fl["margin"]), float(fl["ebrd"])
        st = df[df.cell == cell].groupby(["rep", "policy"]).startup_hash.first().unstack()
        r["startup_identical"] = bool((st.nunique(axis=1) == 1).all())
        for pol in ("random", "margin", "coverage", "bald", "ebrd", "vsur"):
            r[f"mean_NSD_{pol}"] = float(w["NSD_0.1"][pol].mean())
        rows.append(r)
    C = pd.DataFrame(rows)
    C.to_csv(H / "cell_contrasts.csv", index=False)
    d = C["ebrd-margin_NSD_0.1"]; da = C["ebrd-margin_ASSD"]
    noisy = (C.family.isin(["gpworld", "rough"])) | (C.sigma > 0)
    noisefree = (C.family.isin(["curvedMono", "branin4d"])) & (C.sigma == 0)
    imbal = (C.m0 == -4.0) | (C.box == "NEW") | C.family.isin(["rough", "branin4d"])
    S = {
        "S1_majority_NSD_and_ASSD": bool((d > 0).mean() > .5 and (da < 0).mean() > .5),
        "S2_no_catastrophe": bool((d >= -.05).all() and (C.ebrd_assd_ratio <= 1.5).all()),
        "S3_noise_regime": bool(d[noisy].mean() > 0 and (C.flip_margin > C.flip_ebrd)[noisy].mean() > .5),
        "S4_noisefree_comparable": bool((d[noisefree].abs() <= .01).all()),
        "S5_identical_startup": bool(C.startup_identical.all()),
        "S6_two_pools_two_imbalances": bool(d[C.pool == 108].mean() > 0 and d[C.pool == 324].mean() > 0 and d[imbal].mean() > 0 and d[~imbal].mean() > 0),
    }
    wellspec = C.family == "gpworld"
    def regime_useful(mask):
        return bool(d[mask].mean() > 0 and (C["ebrd-margin_NSD_0.1_lo"][mask] > 0).sum() >= 2)
    useful = S["S2_no_catastrophe"] and (regime_useful(wellspec) or regime_useful(noisy))
    verdict = "METHOD BREAKTHROUGH" if all(S.values()) else ("USEFUL BUT NOT DOMINANT" if useful else "NO NEW METHOD JUSTIFIED")
    summary = {**S, "useful_wellspec": regime_useful(wellspec), "useful_noisy": regime_useful(noisy), "verdict": verdict,
               "cells_ebrd_better_NSD": int((d > 0).sum()), "cells_ebrd_better_ASSD": int((da < 0).sum()), "n_cells": int(len(C)),
               "mean_ebrd_minus_margin_NSD": float(d.mean()), "mean_vsur_minus_margin_NSD": float(C["vsur-margin_NSD_0.1"].mean()),
               "mean_ebrd_minus_vsur_NSD": float(C["ebrd-vsur_NSD_0.1"].mean())}
    (H / "VERDICT.json").write_text(json.dumps(summary, indent=2))
    return C, summary


def metric():
    df = pd.read_csv(H / "metric_confirm.csv.gz")
    df = df[df.pred != "SKIPPED_single_class"]
    mets = ["q20_accuracy", "full_BA", "BEF1", "wBEF1", "BD_unweighted", "DC_BD"]
    sec = df[df.pred.isin(["sectorA", "sectorB"])].groupby(["d", "shape", "design", "n", "amount", "pred"])[mets + ["NSD"]].mean()
    sens = (sec.xs("sectorA", level="pred") - sec.xs("sectorB", level="pred")).abs().groupby(["d", "shape", "design"]).mean()
    from scipy.stats import spearmanr
    ag = []
    for key, g in df.groupby(["d", "shape", "design", "n", "rep"]):
        ag.append({**dict(zip(["d", "shape", "design", "n", "rep"], key)), **{m: spearmanr(g[m], -g.ASSD).statistic for m in mets}})
    A = pd.DataFrame(ag).groupby(["d", "shape", "design"])[mets].mean()
    smooth = [i for i in sens.index if i[2].startswith("smooth")]
    Ma = bool(all(sens.loc[i, "DC_BD"] < sens.loc[i, "BD_unweighted"] and sens.loc[i, "DC_BD"] < sens.loc[i, "q20_accuracy"] for i in smooth))
    Mb = bool(all(A.loc[i, "DC_BD"] >= A.loc[i, "q20_accuracy"] for i in A.index if not i[2].startswith("dense")))
    sens.to_csv(H / "metric_density_sensitivity.csv"); A.to_csv(H / "metric_rank_agreement.csv")
    out = {"Ma_DCBD_less_density_sensitive_smooth_cells": Ma, "Mb_DCBD_ge_q20_rank_agreement_nonband_cells": Mb}
    (H / "METRIC_VERDICT.json").write_text(json.dumps(out, indent=2))
    return sens, A, out


if __name__ == "__main__":
    import sys
    if "--metric" in sys.argv:
        s, a, o = metric(); print(s.round(3).to_string()); print(a.round(3).to_string()); print(o)
    else:
        C, s = acquisition(); pd.set_option("display.width", 250)
        print(C[["cell", "ebrd-margin_NSD_0.1", "ebrd-margin_NSD_0.1_lo", "ebrd-margin_NSD_0.1_hi", "ebrd-margin_ASSD", "vsur-margin_NSD_0.1", "flip_margin", "flip_ebrd"]].round(4).to_string())
        print(json.dumps(s, indent=1))
