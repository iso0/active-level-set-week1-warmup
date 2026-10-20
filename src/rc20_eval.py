"""RC20 evaluation of the matched-path replays (stage 1) — metrics from the unchanged RC19 evaluator (src.rc19_eval).
  pilot : the pre-registered remedy rule (per-unit test log loss at B12-B24, remedy minus SHQ_ATS) and the mechanism diagnostics
  replay: every construction (recomputed) and every RC19B system control (cached p_all on the same paid prefixes) on the 200
          RC19B final paths; AULC over B8-B60 and B8-B24 per (construction, path type, repeat); all-path means paired by repeat;
          pre-registered contrasts H1-H7 with the MATERIAL rule; 2x2 factorial decomposition in both orders.
    python -m src.rc20_eval pilot | replay
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"
CONTROLS = ("E1RAW", "E1CAL", "ATSCF", "DEPTHCF", "ATSAPPROX", "G3")
PATHS = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
W_ALL = tuple(range(8, 61, 4)); W_SMALL = (8, 12, 16, 20, 24)


def _arr(x):
    return np.asarray([np.nan if v is None else v for v in x], float)


def _ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ======================================================================================== pilot (remedy rule)
def pilot():
    M = P.manifest(); U = EV.load_units(OUT / "c-pilot"); rows = []; diag = []
    for u in U:
        y = M.reindex(u["test_ids"]).y.to_numpy(int)
        for e in u["evals"]:
            p = e["p"]; row = {"path": u["path_of"], "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], "seconds": e["seconds"]}
            for c in ("SHQ_ATS", "SHQ_ATS_FD", "SHQM_ATS", "SHQ_A", "SHQT_ATS", "SHQ_ATS_H", "M0Q_A"):
                if c in p:
                    row[c] = _ll(_arr(p[c]), y)
            rows.append(row)
            d = e["info"].get("diag")
            if d:
                diag.append({"path": u["path_of"], "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"],
                             **{f"rms_oof_vs_approx_{k}": v for k, v in zip("ATS", d["rms_oof_minus_approx_over_sd"])},
                             **{f"rms_oof_vs_insample_{k}": v for k, v in zip("ATS", d["rms_oof_minus_insample_over_sd"])},
                             **{f"rms_approx_vs_insample_{k}": v for k, v in zip("ATS", d["rms_approx_minus_insample_over_sd"])},
                             "coef_norm_honest": d["coef_norm_honest"], "coef_norm_approx": d["coef_norm_approx"],
                             "fold_logell_sd": d["fold_logell_sd"], "fold_logell_absdev_from_full": d["fold_logell_absdev_from_full"]})
    D = pd.DataFrame(rows); G = pd.DataFrame(diag); (OUT / "pilot").mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT / "pilot" / "pilot_unit_logloss.csv", index=False, lineterminator="\n"); G.to_csv(OUT / "pilot" / "pilot_diagnostics.csv", index=False, lineterminator="\n")
    S = D[D.budget.isin([12, 16, 20, 24])]
    delta = {"FD": float((S.SHQ_ATS_FD - S.SHQ_ATS).mean()), "MAP": float((S.SHQM_ATS - S.SHQ_ATS).mean())}
    better = {"FD": int(((S.SHQ_ATS_FD - S.SHQ_ATS) < 0).sum()), "MAP": int(((S.SHQM_ATS - S.SHQ_ATS) < 0).sum()), "n": int(len(S))}
    best = min(delta, key=delta.get); other = "MAP" if best == "FD" else "FD"
    if delta[best] > -0.005:
        choice = "NONE"
    elif abs(delta[best] - delta[other]) <= 0.002:
        choice = "FD"
    else:
        choice = best
    timing = D.groupby("budget").seconds.agg(["mean", "max"]).round(2).reset_index()
    gs = G.groupby("budget").mean(numeric_only=True).drop(columns=["repeat", "fold"]).round(4).reset_index() if len(G) else pd.DataFrame()
    res = {"rule": "mean per-unit test log loss over budgets 12-24, remedy minus SHQ_ATS; carry the more negative if <= -0.005; ties <= 0.002 -> FD",
           "delta": delta, "units_budgets_better": better, "choice": choice}
    L = ["# RC20 pilot — remedy selection (pre-registered rule, PROTOCOL_RC20_STAGE1.md section 5) and timing", "",
         f"**Rule outcome: {choice}.** Δ(FD) = {delta['FD']:+.4f} (better in {better['FD']}/{better['n']} unit-budgets), Δ(MAP) = {delta['MAP']:+.4f} "
         f"(better in {better['MAP']}/{better['n']}).", "",
         "Mean per-unit test log loss by budget (pilot units; DEV):", "", md(D.groupby("budget")[[c for c in ("SHQ_ATS", "SHQ_ATS_FD", "SHQM_ATS", "SHQ_A", "M0Q_A", "SHQ_ATS_H", "SHQT_ATS") if c in D]].mean().reset_index(), 4), "",
         "Mechanism diagnostics (means over pilot units): RMS differences of the training features, in units of the feature SD; honest = out-of-fold "
         "(refitted hyperparameters), approx = RC19 closed-form LOO of the full fit, in-sample = the full fit at the paid runs; classifier coefficient norms; "
         "spread of the fold models' log lengthscales and their mean absolute deviation from the full fit:", "", md(gs, 3), "",
         "Seconds per budget (all constructions incl. both remedy candidates and diagnostics):", "", md(timing, 2), ""]
    (OUT / "pilot" / "PILOT.md").write_text("\n".join(L) + "\n", encoding="utf-8"); (OUT / "pilot" / "PILOT_DECISION.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\n".join(L)); return res


# ======================================================================================== replay (stage 1)
def as_units(U):
    """Recomputed constructions + cached RC19B controls on the same paid prefixes -> rc19_eval label units, arm = c@path."""
    out = []; cache = {}
    for u in U:
        key = (u["repeat"], u["fold"], u["path_of"])
        if key not in cache:
            src = RC.read_json_gz(B19 / f"r{u['repeat']}_f{u['fold']}__{u['path_of']}.json.gz"); cache[key] = {e["budget"]: e["p_all"] for e in src["evals"] if "p_all" in e}
        budgets = [e["budget"] for e in u["evals"]]
        for c in u["evals"][0]["p"]:
            out.append({"arm": f"{c}@{u['path_of']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                        "evals": [{"budget": e["budget"], "p": e["p"][c], "status": "ok"} for e in u["evals"]]})
        for c in CONTROLS:
            out.append({"arm": f"{c}@{u['path_of']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                        "evals": [{"budget": b, "p": cache[key][b][c], "status": "cached"} for b in budgets if b in cache[key]]})
    return out


def aulc(B, window):
    g = B[B.budget.isin(window)].groupby(["arm", "repeat"]).agg(LL=("log_loss", "mean"), BA=("BA", "mean"), Brier=("brier", "mean"), AUC=("AUC", "mean"),
                                                                 sens=("sensitivity", "mean"), spec=("specificity", "mean")).reset_index()
    g["cons"] = g.arm.str.split("@").str[0]; g["path"] = g.arm.str.split("@").str[1]; return g


def allpath(A, metric):
    return A.groupby(["cons", "repeat"])[metric].mean().unstack("repeat")


def contrast(A, a, b, metric="LL", lower=True):
    X = allpath(A, metric); d = (X.loc[a] - X.loc[b]).dropna(); n = len(d)
    good = (d < 0) if lower else (d > 0); m = float(d.mean())
    if (m <= -0.010 if lower else m >= 0.010) and good.sum() >= 7:
        lab = "MATERIAL"
    elif (m >= 0.010 if lower else m <= -0.010) and (~good & (d != 0)).sum() >= 7:
        lab = "MATERIAL HARM"
    else:
        lab = "NOT MATERIAL"
    per_path = {p: float((A[(A.cons == a) & (A.path == p)].set_index("repeat")[metric] - A[(A.cons == b) & (A.path == p)].set_index("repeat")[metric]).mean()) for p in PATHS}
    return {"contrast": f"{a} − {b}", "metric": metric, "mean": m, "se": float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan, "min": float(d.min()), "max": float(d.max()),
            "repeats_favourable": f"{int(good.sum())}/{n}", "label": lab, **{f"path_{p}": v for p, v in per_path.items()}}


H_LIST = [("H1 T/S beyond depth, identical SHQ upstream (DECISIVE)", "SHQ_ATS", "SHQ_A"), ("H1b T/S beyond depth under M0Q", "M0Q_ATS", "M0Q_A"),
          ("H2a upstream sharing, A only", "SHQ_A", "M0Q_A"), ("H2b upstream sharing, ATS", "SHQ_ATS", "M0Q_ATS"),
          ("H3 E1 probability map", "E1CAL", "E1RAW"), ("H4 depth representation (calibrated)", "M0Q_A", "E1CAL"),
          ("H5 approximation vs honest", "ATSAPPROX", "SHQ_ATS"), ("H6 V1 log h in the classifier (ATS)", "SHQ_ATS_H", "SHQ_ATS"),
          ("H6 V1 log h in the classifier (A only)", "SHQ_A_H", "SHQ_A"), ("H7 V2 log-h mean emulators (ATS)", "SHQT_ATS", "SHQ_ATS"),
          ("H7 V2 log-h mean emulators (A only)", "SHQT_A", "SHQ_A"), ("ref: RC19B confounded ATSCF − DEPTHCF", "SHQ_ATS", "M0Q_A"),
          ("ref: h only vs E1RAW", "HONLY", "E1RAW"), ("ref: SHQ_A vs E1RAW", "SHQ_A", "E1RAW")]


def replay():
    M = P.manifest(); U = EV.load_units(OUT / "c-replay"); X = as_units(U); B = EV.label_metrics(X, M)
    R = OUT / "stage1"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "stage1_metrics.csv", index=False, lineterminator="\n")
    chk = [v for u in U for e in u["evals"] for v in e.get("check_vs_cache", {}).values()]
    A_all, A_small = aulc(B, W_ALL), aulc(B, W_SMALL); A_all.to_csv(R / "stage1_aulc_B8_B60.csv", index=False, lineterminator="\n"); A_small.to_csv(R / "stage1_aulc_B8_B24.csv", index=False, lineterminator="\n")
    cons = sorted(A_all.cons.unique()); rows = []
    for c in cons:
        r = {"construction": c}
        for nm, A in (("B8–B60", A_all), ("B8–B24", A_small)):
            for met in ("LL", "BA", "Brier", "AUC", "sens", "spec"):
                r[f"{met} {nm}"] = float(allpath(A, met).loc[c].mean())
        rows.append(r)
    S = pd.DataFrame(rows).sort_values("LL B8–B60")
    C1 = []
    for title, a, b in H_LIST:
        if a in cons and b in cons:
            for win, A in (("B8–B60", A_all), ("B8–B24", A_small)):
                for met, low in (("LL", True), ("Brier", True), ("BA", False)):
                    C1.append({"hypothesis": title, "window": win, **contrast(A, a, b, met, low)})
    C1 = pd.DataFrame(C1); C1.to_csv(R / "stage1_contrasts.csv", index=False, lineterminator="\n")
    # 2x2 factorial (LL B8-B60, all-path means per repeat)
    X1 = allpath(A_all, "LL"); f = {k: X1.loc[k] for k in ("M0Q_A", "M0Q_ATS", "SHQ_A", "SHQ_ATS")}
    tot = (f["SHQ_ATS"] - f["M0Q_A"]); order1 = {"upstream|A": f["SHQ_A"] - f["M0Q_A"], "features|SHQ": f["SHQ_ATS"] - f["SHQ_A"]}
    order2 = {"features|M0Q": f["M0Q_ATS"] - f["M0Q_A"], "upstream|ATS": f["SHQ_ATS"] - f["M0Q_ATS"]}
    inter = f["SHQ_ATS"] - f["SHQ_A"] - f["M0Q_ATS"] + f["M0Q_A"]
    FAC = pd.DataFrame([{"term": k, "mean": float(v.mean()), "se": float(v.std(ddof=1) / np.sqrt(len(v))), "repeats_negative": f"{int((v < 0).sum())}/{len(v)}"}
                        for k, v in {"total ATSCF − DEPTHCF (SHQ_ATS − M0Q_A)": tot, **order1, **order2, "interaction": inter,
                                     "main effect features (avg of orders)": 0.5 * (order1["features|SHQ"] + order2["features|M0Q"]),
                                     "main effect upstream (avg of orders)": 0.5 * (order1["upstream|A"] + order2["upstream|ATS"])}.items()])
    FAC.to_csv(R / "stage1_factorial.csv", index=False, lineterminator="\n")
    Rel = None
    try:
        import src.rc19b_keyhole_eval as KE
        Rel = KE.reliability(X, M); Rel.to_csv(R / "stage1_reliability.csv", index=False, lineterminator="\n")
    except Exception as ex:
        print("reliability skipped", ex)
    L = ["# RC20 Stage 1 — matched-path attribution and log-h variants (DEV; the 200 RC19B final paths; budgets 8–60 every 4)", "",
         f"Recomputed SHQ_ATS / M0Q_A vs the cached ATSCF / DEPTHCF on every replayed budget: max |Δ| = {max(chk) if chk else float('nan'):.2e} ({len(chk)} checks).", "",
         "## All-path means (mean over the 5 path types, then over 8 repeats)", "", md(S, 4), "",
         "## Pre-registered contrasts (MATERIAL iff mean Δ ≤ −0.010 in log loss / Brier, or ≥ +0.010 in BA, and favourable in ≥ 7/8 repeats)", "",
         md(C1[["hypothesis", "window", "contrast", "metric", "mean", "se", "min", "max", "repeats_favourable", "label"] + [c for c in C1.columns if c.startswith("path_")]], 4), "",
         "## 2×2 decomposition of the RC19B contrast ATSCF − DEPTHCF (LL-AULC B8–B60, all-path means per repeat)", "", md(FAC, 4), ""]
    (R / "STAGE1.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:25000]); return S, C1, FAC


if __name__ == "__main__":
    {"pilot": pilot, "replay": replay}[sys.argv[1]]()
