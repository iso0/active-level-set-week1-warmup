"""RC19B (RC19 continuation) cache-level repairs of RC19 reporting and exports. No learner is refitted; RC19 files are kept.

  endpoints : corrected endpoint tables. For every trajectory, three separate quantities (total revealed simulations,
              startup included): first qualifying budget (first recorded b at the level), the first budget b of the
              confirmed pair (level at b and at b+4; RC19's endpoint definition, unchanged) and the CONFIRMATION SPEND
              b+4 (what confirmation actually costs). RC19's report printed the second as if it were the third.
  joint     : joint 8-output completion for EVERY arm, with per-repeat success / censoring.
  export    : float32 re-export of every final per-budget prediction from the unit caches (RC19's float16 exports were
              lossy), followed by an acceptance check that recomputes every reported metric cell from the export with the
              evaluator's own code and compares it with the RC19 CSVs.
    python -m src.rc19b_repair endpoints | joint | export | all
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_final as F
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
REP1 = P.OUT / "report"                    # RC19 report (kept unchanged)
REPAIR = OUT / "repair"


def _ends(df, keys, metric, level):
    rows = []
    for k, g in df.groupby(keys):
        e = EV.endpoint(dict(zip(g.budget, g[metric])), level, step=4)
        rows.append({**dict(zip(keys, k if isinstance(k, tuple) else (k,))), "first_qualifying": e["first"], "confirmed_pair_b": e["confirmed"],
                     "confirmation_spend": e["confirm_spend"], "censored": e["censored"], "horizon": e["horizon"]})
    return pd.DataFrame(rows)


def _summ(E, by):
    def s(x):
        x = x.dropna()
        return "–" if x.empty else f"{x.mean():.3f} (median {x.median():.1f}; {x.min():.0f}–{x.max():.0f})"
    return E.groupby(by).agg(completed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), first_qualifying=("first_qualifying", s),
                             confirmation_spend=("confirmation_spend", s), spend_per_repeat=("confirmation_spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()


def endpoints():
    REPAIR.mkdir(parents=True, exist_ok=True); L = ["## Corrected endpoint tables (total revealed simulations, startup included)", "",
         "first_qualifying = first recorded budget at the level; confirmation_spend = b + 4 for the first b with the level at b and b + 4 "
         "(the simulations actually spent to confirm). Mean (median; range) over the repeats that reached it; '–' = censored at the horizon.", ""]
    G = pd.read_csv(REP1 / "region_curves.csv"); ER = _ends(G, ["model", "acq", "repeat"], "BA", F.BA_LEVEL["region"]); ER.to_csv(REPAIR / "region_endpoints_v2.csv", index=False, lineterminator="\n")
    L += [f"### Region: BA ≥ {F.BA_LEVEL['region']}", "", md(_summ(ER, ["model", "acq"])), ""]
    B = pd.read_csv(REP1 / "label_metrics.csv"); EL = _ends(B, ["arm", "repeat"], "BA", F.BA_LEVEL["label"]); EL.to_csv(REPAIR / "label_endpoints_v2.csv", index=False, lineterminator="\n")
    L += [f"### Keyhole label: BA ≥ {F.BA_LEVEL['label']}", "", md(_summ(EL, ["arm"])), ""]
    rows = []
    for a, b in (("PHYSCF_ATS_MARGIN", "E1_STRADDLE"), ("PHYSCF_ATS_MARGIN", "G3_MARGIN"), ("E1_STRADDLE", "G3_MARGIN"), ("PHYSMC_ATS_MARGIN", "E1_STRADDLE"), ("PHYSCF_A_MARGIN", "E1_STRADDLE")):
        x = EL[EL.arm == a].set_index("repeat").confirmation_spend; y = EL[EL.arm == b].set_index("repeat").confirmation_spend; d = (x - y)
        both = d.dropna()
        rows.append({"contrast": f"{a} − {b}", "pairs_observed": f"{len(both)}/{len(d)}", "mean_spend_difference": float(both.mean()) if len(both) else np.nan,
                     "fewer/equal/more": f"{int((both < 0).sum())}/{int((both == 0).sum())}/{int((both > 0).sum())}"})
    L += ["Paired confirmation-spend differences (label; exploratory; only pairs where both arms confirmed):", "", md(pd.DataFrame(rows)), ""]
    R = pd.read_csv(REP1 / "reg_curves.csv"); R = R[R.budget >= P.B0]; rows = []
    for (m, a, r), g in R.groupby(["model", "acq", "repeat"]):
        cur = {t: dict(zip(gt.budget, gt.R2)) for t, gt in g.groupby("target")}
        for t in F.PRIMARY_TARGETS:
            e = EV.endpoint(cur[t], F.LEVELS[t]); rows.append({"model": m, "acq": a, "repeat": r, "target": t, "first_qualifying": e["first"], "confirmed_pair_b": e["confirmed"],
                                                               "confirmation_spend": e["confirm_spend"], "censored": e["censored"], "horizon": e["horizon"]})
        bs = sorted(cur[F.PRIMARY_TARGETS[0]]); joint = {b: min(cur[t][b] - F.LEVELS[t] for t in F.PRIMARY_TARGETS) for b in bs}; e = EV.endpoint(joint, 0.0)
        rows.append({"model": m, "acq": a, "repeat": r, "target": "JOINT", "first_qualifying": e["first"], "confirmed_pair_b": e["confirmed"], "confirmation_spend": e["confirm_spend"],
                     "censored": e["censored"], "horizon": e["horizon"]})
    EG = pd.DataFrame(rows); EG.to_csv(REPAIR / "reg_endpoints_v2.csv", index=False, lineterminator="\n")
    L += ["### Physical outputs: per-output and JOINT (all 8 at their levels at the same budget)", "", md(_summ(EG, ["model", "acq", "target"])), ""]
    return L, ER, EL, EG


def joint(EG=None):
    EG = pd.read_csv(REPAIR / "reg_endpoints_v2.csv") if EG is None else EG; J = EG[EG.target == "JOINT"].copy()
    J["status"] = np.where(J.censored, "censored at B80", "confirmed")
    T = J.pivot_table(index=["model", "acq"], columns="repeat", values="confirmation_spend", aggfunc="first")
    S = J.groupby(["model", "acq"]).agg(confirmed=("censored", lambda c: int((~c).sum())), censored=("censored", lambda c: int(c.sum())), n=("censored", "size")).reset_index()
    first = J.groupby(["model", "acq"]).first_qualifying.apply(lambda x: f"{int(x.notna().sum())}/{len(x)} reached at least once").reset_index(name="ever_qualified")
    S = S.merge(first, on=["model", "acq"])
    L = ["### Joint 8-output completion, every arm (confirmation spend per repeat; NaN = censored at B80)", "", md(S), "", md(T.reset_index(), 0), ""]
    return L


# ======================================================================================== float32 export + acceptance
def export():
    exp = OUT / "export"; exp.mkdir(parents=True, exist_ok=True); M = P.manifest(); rows_paths = []; acc = {}
    for job, kind in (("final-label", "label"), ("final-region", "region"), ("final-reg", "reg")):
        U = EV.load_units(P.OUT / "final" / job); keys, arrays, tids, buds = [], [], [], []
        for u in U:
            arm = u.get("arm", u.get("model")); acq = u.get("acq", "")
            for q, s in enumerate(u["paid_ids"], 1):
                rows_paths.append({"workstream": kind, "arm": arm, "design": acq, "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s})
            b = [e["budget"] for e in u["evals"]]
            if kind == "label":
                a = np.asarray([[np.nan if v is None else v for v in e["p"]] for e in u["evals"]], np.float32)
            elif kind == "region":
                a = np.asarray([[[np.nan if v is None else v for v in (e["mean"] or [None] * len(u["test_ids"]))],
                                 [np.nan if v is None else v for v in (e["lat"] or [None] * len(u["test_ids"]))]] for e in u["evals"]], np.float32)
            else:
                a = np.full((len(b), len(P.TARGETS), 2, len(u["test_ids"])), np.nan, np.float32)
                for i, e in enumerate(u["evals"]):
                    for k, c in enumerate(P.TARGETS):
                        pr = e["pred"].get(c)
                        if pr is not None:
                            a[i, k, 0] = [np.nan if v is None else v for v in pr[0]]; a[i, k, 1] = [np.nan if v is None else v for v in pr[1]]
            keys.append(f"{arm}|{acq}|r{u['repeat']}|f{u['fold']}"); arrays.append(a); tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray(b, np.int16))
        np.savez_compressed(exp / f"predictions_{kind}_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrays)},
                            **{f"test_ids_{i}": t for i, t in enumerate(tids)}, **{f"budgets_{i}": t for i, t in enumerate(buds)},
                            schema=np.asarray([json.dumps({"label": "pred[budget, test] = P(Keyhole), float32 (identical to the unit cache)",
                                                           "region": "pred[budget, {mean, latent var}, test] of the spike log-ratio, float32",
                                                           "reg": "pred[budget, target, {mean, observation var}, test], float32; targets = " + ",".join(P.TARGETS)}[kind])]))
        acc[kind] = check_export(kind, exp / f"predictions_{kind}_f32.npz", U, M)
    pd.DataFrame(rows_paths).to_csv(exp / "paths.csv.gz", index=False, compression="gzip")
    (exp / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); return acc


def _units_from_export(kind, path, U):
    Z = np.load(path, allow_pickle=False); keys = list(Z["keys"]); out = []
    for i, k in enumerate(keys):
        arm, acq, r, f = k.split("|"); u = {"repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"])}
        bud = Z[f"budgets_{i}"].tolist(); a = Z[f"pred_{i}"]; to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        if kind == "label":
            u.update(arm=arm, evals=[{"budget": b, "p": to(a[j])} for j, b in enumerate(bud)])
        elif kind == "region":
            u.update(model=arm, acq=acq, evals=[{"budget": b, "mean": to(a[j, 0]), "lat": to(a[j, 1])} for j, b in enumerate(bud)])
        else:
            u.update(model=arm, acq=acq, evals=[{"budget": b, "pred": {c: [to(a[j, kk, 0]), to(a[j, kk, 1])] for kk, c in enumerate(P.TARGETS)}} for j, b in enumerate(bud)])
        out.append(u)
    # identity checks against the caches: same units, same test IDs, same budgets
    src = {(x.get("arm", x.get("model")), x.get("acq", ""), x["repeat"], x["fold"]): x for x in U}
    for u in out:
        s = src[(u.get("arm", u.get("model")), u.get("acq", ""), u["repeat"], u["fold"])]
        assert u["test_ids"] == list(s["test_ids"]) and [e["budget"] for e in u["evals"]] == [e["budget"] for e in s["evals"]]
    return out


def check_export(kind, path, U, M):
    X = _units_from_export(kind, path, U)
    if kind == "label":
        a, b = EV.label_metrics(X, M), pd.read_csv(REP1 / "label_metrics.csv"); key = ["arm", "repeat", "budget"]
        cols = ["BA", "sensitivity", "specificity", "AUC", "brier", "log_loss", "q20_BA", "shortK_pooled_captured", "shortK_NEW_captured", "BA_OLD", "BA_NEW", "spec_NEW", "sens_NEW"]
    elif kind == "region":
        a, b = EV.region_curves(X, M, F.TAU), pd.read_csv(REP1 / "region_curves.csv"); key = ["model", "acq", "repeat", "budget"]; cols = ["BA", "recall_in", "recall_out"]
    else:
        a, b = EV.reg_curves(X, M), pd.read_csv(REP1 / "reg_curves.csv"); key = ["model", "acq", "repeat", "target", "budget"]; cols = ["R2", "cov90", "nlpd"]
    j = a.merge(b, on=key, suffixes=("_export", "_csv"))
    res = {"cells_compared": int(len(j)), "cells_in_csv": int(len(b))}
    for c in cols:
        d = np.abs(j[f"{c}_export"].to_numpy(float) - j[f"{c}_csv"].to_numpy(float)); d = d[np.isfinite(d)]
        res[c] = {"max_abs_diff": float(d.max()) if len(d) else 0.0, "cells_differing_gt_1e-12": int((d > 1e-12).sum())}
    res["PASS"] = bool(res["cells_compared"] == res["cells_in_csv"] and all(v["cells_differing_gt_1e-12"] == 0 for k, v in res.items() if isinstance(v, dict)))
    return res


def old_export_discrepancy():
    """Reproduce the auditor's finding on RC19's float16 exports (label / region)."""
    M = P.manifest(); out = {}
    for kind, job in (("label", "final-label"), ("region", "final-region")):
        Z = np.load(REP1 / f"predictions_{kind}.npz", allow_pickle=False); U = EV.load_units(P.OUT / "final" / job); src = {}
        for u in U:
            src[f"{u.get('arm', u.get('model'))}|{u.get('acq', '')}|r{u['repeat']}|f{u['fold']}"] = u
        X = []
        for i, k in enumerate(Z["keys"]):
            u = src[k]; a = Z[f"pred_{i}"].astype(np.float64); to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
            if kind == "label":
                X.append({"arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"], "evals": [{"budget": e["budget"], "p": to(a[j])} for j, e in enumerate(u["evals"])]})
            else:
                X.append({"model": u["model"], "acq": u["acq"], "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                          "evals": [{"budget": e["budget"], "mean": to(a[j, 0]), "lat": to(a[j, 1])} for j, e in enumerate(u["evals"])]})
        if kind == "label":
            a_, b_ = EV.label_metrics(X, M), pd.read_csv(REP1 / "label_metrics.csv"); key = ["arm", "repeat", "budget"]
        else:
            a_, b_ = EV.region_curves(X, M, F.TAU), pd.read_csv(REP1 / "region_curves.csv"); key = ["model", "acq", "repeat", "budget"]
        j = a_.merge(b_, on=key, suffixes=("_f16", "_csv")); d = np.abs(j.BA_f16 - j.BA_csv)
        out[kind] = {"cells": int(len(j)), "BA_cells_changed": int((d > 1e-12).sum()), "BA_max_abs_diff": float(d.max())}
        if kind == "label":
            dl = np.abs(j.log_loss_f16 - j.log_loss_csv); out[kind]["log_loss_max_abs_diff"] = float(dl.max())
            w = j.loc[d.idxmax(), key + ["BA_f16", "BA_csv"]].to_dict(); out[kind]["worst_cell"] = {k: (float(v) if not isinstance(v, str) else v) for k, v in w.items()}
    return out


def md(df, digits=3):
    from src.rc19_report import md as _md
    return _md(df, digits)


def main(what):
    RC.limit_threads(1); OUT.mkdir(parents=True, exist_ok=True); REPAIR.mkdir(parents=True, exist_ok=True); L = []
    if what in ("endpoints", "all"):
        L1, ER, EL, EG = endpoints(); L += L1 + joint(EG)
    if what in ("export", "all"):
        old = old_export_discrepancy(); acc = export()
        L += ["## Export repair", "", f"RC19 float16 exports reproduced: {json.dumps(old)}", "", f"float32 re-export acceptance (every metric cell recomputed from the export vs the RC19 CSVs): {json.dumps(acc)}", ""]
        (REPAIR / "OLD_EXPORT_DISCREPANCY.json").write_text(json.dumps(old, indent=1), encoding="utf-8")
    (REPAIR / f"REPAIR_{what}.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:12000])


if __name__ == "__main__":
    main(sys.argv[1])
