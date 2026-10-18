"""RC18 step B0 — results-independent data inspection used to choose the model directions (no AL / model comparison).

Uses the existing physical targets (PHYS_AL definitions) and the Week 19 table on ALL runs (DEV, inspected before). It only
describes the data: input ranges, how much of each output a fixed physics coordinate explains (5-fold CV linear fits), which
outputs separate the regime label, whether residual spread depends on the regime (heteroskedasticity), and whether NEW's low
attainable R^2 is reproduced by OLD restricted to NEW's input box at NEW's sample size (matched-range / matched-n control).
    python -m src.rc18_inspect
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

import src.jdl_phys_al as PAL
import src.jdl_physical_pilot as PP
import src.rc18_common as RC

OUT = RC.CAMP / "inspection"
T_MELT = 1928.0           # K, Ti-6Al-4V liquidus (only used for the optional preheat term log(T_m - ST))


def table(pop):
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); T = PAL.targets(pop)
    D = T.join(W[["y", "P", "VX", "LS_um_radius", "ST", "descriptor", "frac_K_FCK"]], how="left")
    D["logP"], D["logV"], D["logR"] = np.log(D.P), np.log(D.VX), np.log(D.LS_um_radius * 1e-6)
    D["logh"] = D.logP - 0.5 * D.logV - 1.5 * D.logR
    D["logh_ST"] = D.logh - np.log(T_MELT - D.ST)
    return D


def cv_r2(X, y, seed=0):
    ok = np.isfinite(y) & np.isfinite(X).all(1); X, y = X[ok], y[ok]; p = np.zeros_like(y)
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(X):
        p[te] = LinearRegression().fit(X[tr], y[tr]).predict(X[te])
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)), y - p


def main():
    OUT.mkdir(parents=True, exist_ok=True); res = {}; tabs = {}
    targets = list(PAL.PRIMARY) + list(PAL.SECONDARY)
    for pop in ("NEW", "OLD"):
        D = table(pop); tabs[pop] = D
        r = {"n": int(len(D)), "keyhole": int(D.y.sum()),
             "inputs": {c: {"min": float(D[c].min()), "max": float(D[c].max())} for c in ("P", "VX", "LS_um_radius", "ST", "logh")}, "targets": {}}
        for c in targets:
            y = D[c].to_numpy(float); e = {"n_finite": int(np.isfinite(y).sum()), "sd": float(np.nanstd(y))}
            for name, cols in (("logh", ["logh"]), ("logh_ST", ["logh_ST"]), ("logh+logV", ["logh", "logV"]), ("linear_4_log_inputs", ["logP", "logV", "logR", "ST"])):
                e[f"cvR2_{name}"], res_ = cv_r2(D[cols].to_numpy(float), y)
            # regime separation and regime-dependent residual spread (linear-in-log-inputs residuals)
            ok = np.isfinite(y)
            yy, lab = y[ok], D.y.to_numpy()[ok]
            if 0 < lab.sum() < len(lab):
                e["AUC_for_label"] = float(roc_auc_score(lab, yy))
                _, rr = cv_r2(D[["logP", "logV", "logR", "ST"]].to_numpy(float), y)
                e["resid_sd_keyhole"] = float(np.std(rr[lab == 1])); e["resid_sd_no_keyhole"] = float(np.std(rr[lab == 0]))
                fast = D.VX.to_numpy()[ok] > np.median(D.VX)
                e["resid_sd_fast_half"] = float(np.std(rr[fast])); e["resid_sd_slow_half"] = float(np.std(rr[~fast]))
            r["targets"][c] = e
        res[pop] = r
    # matched control: OLD restricted to NEW's input box, subsampled to NEW's size, vs NEW (same linear predictors)
    N, O = tabs["NEW"], tabs["OLD"]
    box = np.ones(len(O), bool)
    for c in ("P", "VX", "LS_um_radius", "ST"):
        box &= (O[c] >= N[c].min()) & (O[c] <= N[c].max())
    res["matched_box"] = {"OLD_in_NEW_box": int(box.sum()), "note": "OLD runs inside NEW's min-max box on all four inputs"}
    if box.sum() >= 30:
        Ob = O[box]; m = {}
        for c in targets:
            y = Ob[c].to_numpy(float)
            m[c] = {"sd_OLD_box": float(np.nanstd(y)), "sd_NEW": float(np.nanstd(N[c])), "sd_OLD_all": float(np.nanstd(O[c])),
                    "cvR2_linear_OLD_box": cv_r2(Ob[["logP", "logV", "logR", "ST"]].to_numpy(float), y)[0]}
        res["matched_box"]["targets"] = m
    (OUT / "DATA_INSPECTION.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = ["# Data inspection for model-direction choice (RC18 B0; all DEV runs; descriptive, no AL comparison)", ""]
    for pop in ("NEW", "OLD"):
        r = res[pop]
        L += [f"## {pop}: n = {r['n']}, Keyhole {r['keyhole']}", "", "Inputs: " + "; ".join(f"{k} {v['min']:.4g}–{v['max']:.4g}" for k, v in r["inputs"].items()), "",
              "| target | n | SD | CV R² log h | CV R² log h(ST) | CV R² log h + log VX | CV R² linear 4 log inputs | AUC for label | resid SD K / noK | resid SD fast / slow half |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for c, e in r["targets"].items():
            L.append(f"| {c} | {e['n_finite']} | {e['sd']:.3g} | {e['cvR2_logh']:.2f} | {e['cvR2_logh_ST']:.2f} | {e['cvR2_logh+logV']:.2f} | {e['cvR2_linear_4_log_inputs']:.2f} | "
                     f"{e.get('AUC_for_label', float('nan')):.2f} | {e.get('resid_sd_keyhole', float('nan')):.3g} / {e.get('resid_sd_no_keyhole', float('nan')):.3g} | "
                     f"{e.get('resid_sd_fast_half', float('nan')):.3g} / {e.get('resid_sd_slow_half', float('nan')):.3g} |")
        L.append("")
    mb = res["matched_box"]; L += [f"## Matched range: OLD runs inside NEW's input box: {mb['OLD_in_NEW_box']}", ""]
    if "targets" in mb:
        L += ["| target | SD NEW | SD OLD (all) | SD OLD (in NEW box) | CV R² linear, OLD in box |", "|---|---|---|---|---|"]
        for c, e in mb["targets"].items():
            L.append(f"| {c} | {e['sd_NEW']:.3g} | {e['sd_OLD_all']:.3g} | {e['sd_OLD_box']:.3g} | {e['cvR2_linear_OLD_box']:.2f} |")
    (OUT / "DATA_INSPECTION.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
