"""RC21 Stage 1 evaluation (matched paths; PROTOCOL_RC21_STAGE1.md section 4) with the unchanged RC19 evaluator (src.rc19_eval).
Constructions on the SAME paid prefixes of the 200 RC19B final paths: PHR / PHR_NR / PHR_FX / PHR_FXMAP (d-replay, recomputed),
SHQ_ATS_H and SHQ_ATS_X (RC20 c-replay-x cache, NOT recomputed), E1RAW / E1CAL / ATSAPPROX / G3 (RC19B caches).
AULC over B8-B24 and B8-B60 per (construction, path, repeat); all-path means paired by repeat; contrasts S1-S4 with the
MATERIAL rule; the development-choice rule and the justification gate; posterior diagnostics; the hard corner.
    python -m src.rc21_eval stage1
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

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"
CX = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20" / "c-replay-x" / "units"
CONTROLS = ("E1RAW", "E1CAL", "ATSAPPROX", "G3")
CACHED20 = ("SHQ_ATS_H", "SHQ_ATS_X")
NEWC = ("PHR", "PHR_NR", "PHR_FX", "PHR_FXMAP")
PATHS = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
W_ALL = tuple(range(8, 61, 4)); W_SMALL = (8, 12, 16, 20, 24)
S_LIST = [("S1 new combination vs RC20 candidate", "PHR", "SHQ_ATS_H"),
          ("S2a intercept prior (nesting, expect 0)", "PHR_FXMAP", "SHQ_ATS_H"), ("S2b latent integration", "PHR_FX", "PHR_FXMAP"),
          ("S2c learned regularisation", "PHR_NR", "PHR_FX"), ("S2d transverse residual", "PHR", "PHR_NR"),
          ("S3a new vs generic exact inputs", "PHR", "SHQ_ATS_X"), ("S3b generic inputs vs h (RC20 control, cached)", "SHQ_ATS_X", "SHQ_ATS_H"),
          ("S4a vs ATSAPPROX", "PHR", "ATSAPPROX"), ("S4b vs E1CAL", "PHR", "E1CAL"), ("S4c vs E1RAW", "PHR", "E1RAW"), ("S4d vs G3", "PHR", "G3"),
          ("ref: no-residual model vs RC20 candidate", "PHR_NR", "SHQ_ATS_H")]


def as_units(U):
    out = []
    for u in U:
        key = (u["repeat"], u["fold"], u["path_of"]); budgets = [e["budget"] for e in u["evals"]]
        src = RC.read_json_gz(B19 / f"r{key[0]}_f{key[1]}__{key[2]}.json.gz"); c19 = {e["budget"]: e["p_all"] for e in src["evals"] if "p_all" in e}
        c20 = {e["budget"]: e["p"] for e in RC.read_json_gz(CX / f"r{key[0]}_f{key[1]}__{key[2]}.json.gz")["evals"]}
        for c in NEWC:
            out.append({"arm": f"{c}@{key[2]}", "repeat": key[0], "fold": key[1], "test_ids": u["test_ids"],
                        "evals": [{"budget": e["budget"], "p": e["p"][c], "status": "ok"} for e in u["evals"]]})
        for c in CACHED20:
            out.append({"arm": f"{c}@{key[2]}", "repeat": key[0], "fold": key[1], "test_ids": u["test_ids"],
                        "evals": [{"budget": b, "p": c20[b][c], "status": "cached"} for b in budgets if b in c20]})
        for c in CONTROLS:
            out.append({"arm": f"{c}@{key[2]}", "repeat": key[0], "fold": key[1], "test_ids": u["test_ids"],
                        "evals": [{"budget": b, "p": c19[b][c], "status": "cached"} for b in budgets if b in c19]})
    return out


def aulc(B, window):
    g = B[B.budget.isin(window)].groupby(["arm", "repeat"]).agg(LL=("log_loss", "mean"), BA=("BA", "mean"), Brier=("brier", "mean"), AUC=("AUC", "mean"),
                                                                 sens=("sensitivity", "mean"), spec=("specificity", "mean"), q20_BA=("q20_BA", "mean")).reset_index()
    g["cons"] = g.arm.str.split("@").str[0]; g["path"] = g.arm.str.split("@").str[1]; return g


def allpath(A, metric):
    return A.groupby(["cons", "repeat"])[metric].mean().unstack("repeat")


def contrast(A, a, b, metric, lower):
    X = allpath(A, metric); d = (X.loc[a] - X.loc[b]).dropna(); n = len(d); good = (d < 0) if lower else (d > 0); bad = (d > 0) if lower else (d < 0); m = float(d.mean())
    if (m <= -0.010 if lower else m >= 0.010) and good.sum() >= 7:
        lab = "MATERIAL"
    elif (m >= 0.010 if lower else m <= -0.010) and bad.sum() >= 7:
        lab = "MATERIAL HARM"
    else:
        lab = "NOT MATERIAL"
    per_path = {p: float((A[(A.cons == a) & (A.path == p)].set_index("repeat")[metric] - A[(A.cons == b) & (A.path == p)].set_index("repeat")[metric]).mean()) for p in PATHS}
    return {"contrast": f"{a} − {b}", "metric": metric, "mean": m, "se": float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan, "min": float(d.min()), "max": float(d.max()),
            "repeats_favourable": f"{int(good.sum())}/{n}", "label": lab, **{f"path_{p}": v for p, v in per_path.items()}}


def stage1():
    M = P.manifest(); U = EV.load_units(OUT / "d-replay"); X = as_units(U); B = EV.label_metrics(X, M)
    R = OUT / "stage1"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "stage1_metrics.csv", index=False, lineterminator="\n")
    chk = [e["check_SHQ_ATS_H_vs_rc20"] for u in U for e in u["evals"] if e.get("check_SHQ_ATS_H_vs_rc20") is not None]
    A_all, A_small = aulc(B, W_ALL), aulc(B, W_SMALL); A_all.to_csv(R / "stage1_aulc_B8_B60.csv", index=False, lineterminator="\n"); A_small.to_csv(R / "stage1_aulc_B8_B24.csv", index=False, lineterminator="\n")
    rows = []
    for c in sorted(A_all.cons.unique()):
        r = {"construction": c}
        for nm, A in (("B8–B24", A_small), ("B8–B60", A_all)):
            for met in ("LL", "BA", "sens", "spec", "Brier", "q20_BA"):
                r[f"{met} {nm}"] = float(allpath(A, met).loc[c].mean())
        rows.append(r)
    S = pd.DataFrame(rows).sort_values("LL B8–B24")
    C1 = []
    for title, a, b in S_LIST:
        for win, A in (("B8–B24", A_small), ("B8–B60", A_all)):
            for met, low in (("LL", True), ("BA", False), ("sens", False), ("spec", False), ("Brier", True)):
                C1.append({"contrast_id": title, "window": win, **contrast(A, a, b, met, low)})
    C1 = pd.DataFrame(C1); C1.to_csv(R / "stage1_contrasts.csv", index=False, lineterminator="\n")
    # development-choice rule and justification gate (section 4)
    g = lambda a, b, met, A: float((allpath(A, met).loc[a] - allpath(A, met).loc[b]).mean())
    res_ba, res_ll = g("PHR", "PHR_NR", "BA", A_small), g("PHR", "PHR_NR", "LL", A_small)
    new = "PHR_NR" if (res_ba <= -0.003 or res_ll >= 0.003) else "PHR"
    gate = {met: contrast(A_small, new, "SHQ_ATS_H", met, met == "LL")["label"] for met in ("LL", "BA")}
    carried = new if all(v != "MATERIAL HARM" for v in gate.values()) else None
    dec = {"rule": "NEW = PHR unless mean (PHR - PHR_NR) BA-AULC B8-B24 <= -0.003 or LL-AULC B8-B24 >= +0.003 (then PHR_NR); not carried if MATERIAL HARM vs SHQ_ATS_H (LL or BA, B8-B24)",
           "residual_delta_BA_B8_B24": res_ba, "residual_delta_LL_B8_B24": res_ll, "choice": new, "gate_vs_SHQ_ATS_H": gate, "NEW": carried}
    (R / "STAGE1_DECISION.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    # posterior diagnostics by budget, hard corner, reliability
    post = pd.DataFrame([{"budget": e["budget"], **{k: v for k, v in e["info"].get("phr", {}).items() if not isinstance(v, list)}} for u in U for e in u["evals"] if e["info"].get("phr")])
    PD = post.groupby("budget").mean(numeric_only=True).round(3).reset_index() if len(post) else pd.DataFrame()
    import src.rc19b_keyhole_eval as KE
    Rel = KE.reliability(X, M); Rel.to_csv(R / "stage1_reliability.csv", index=False, lineterminator="\n")
    Rel["cons"] = Rel.arm.str.split("@").str[0]
    HC = Rel[Rel.budget.isin([24, 60])].groupby(["cons", "budget"]).agg(cal_slope=("cal_slope", "mean"), ECE=("ECE", "mean"), corner_errors=("hard_NEW_conduction_errors", "sum"),
                                                                        corner_n=("hard_NEW_conduction_n", "sum")).reset_index()
    MB = B.assign(cons=B.arm.str.split("@").str[0])[B.budget.isin([8, 12, 16, 20, 24, 40, 60])].groupby(["cons", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "q20_BA", "spec_NEW"]].mean().reset_index()
    cpu = pd.DataFrame([{"budget": e["budget"], "cpu_s": e["cpu_s"]} for u in U for e in u["evals"]]).groupby("budget").cpu_s.agg(["mean", "max"]).round(3).reset_index()
    L = ["# RC21 Stage 1 — matched-path model contribution (DEV; the 200 RC19B final paths; budgets 8–60 every 4)", "",
         f"Recomputed SHQ_ATS_H vs the RC20 c-replay cache on every replayed budget: max |Δ| = {max(chk) if chk else float('nan'):.2e} ({len(chk)} checks). "
         "SHQ_ATS_X and SHQ_ATS_H in the tables are the RC20 caches (not recomputed); E1RAW / E1CAL / ATSAPPROX / G3 are the RC19B caches.", "",
         f"**Development choice (pre-registered rule): NEW = {carried}** (residual Δ BA-AULC B8–B24 {res_ba:+.4f}, Δ LL-AULC {res_ll:+.4f}; gate vs SHQ_ATS_H: {gate}).", "",
         "## All-path means (mean over the 5 path types, then over 8 repeats)", "", md(S, 4), "",
         "## Contrasts (MATERIAL iff mean Δ ≤ −0.010 in LL / Brier, ≥ +0.010 in BA / recalls, favourable in ≥ 7/8 repeats)", "",
         md(C1[["contrast_id", "window", "contrast", "metric", "mean", "se", "min", "max", "repeats_favourable", "label"] + [c for c in C1.columns if c.startswith("path_")]], 4), "",
         "## Matched budgets (mean over paths and repeats)", "", md(MB, 3), "",
         "## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over paths and repeats) and calibration", "", md(HC, 3), "",
         "## PHR posterior diagnostics by budget (means over paths and repeats)", "", md(PD, 3), "", "## CPU per paid state (s, all RC21 constructions)", "", md(cpu, 3), ""]
    (R / "STAGE1.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:30000]); print(json.dumps(dec, indent=1)); return dec


if __name__ == "__main__":
    RC.limit_threads(1); {"stage1": stage1}[sys.argv[1]]()
