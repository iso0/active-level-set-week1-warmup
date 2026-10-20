"""RC21 sequential-stage report (frozen with PROTOCOL_RC21_FINAL.md before any final outcome): the co-primary questions (decision
accuracy BA-AULC B8-B24; paid simulations to a confirmed BA >= 0.93), every pre-declared secondary contrast, learning curves,
both recalls, target attainment and confirmation spend (second checkpoint b + 4), censoring, reliability, the fast-scan corner,
the matched-path decomposition on the physical arms' own paths (model on the same queries vs path change), decision CPU
separately from the paid-simulation count, float32 exports of every per-budget prediction and paid path, and an acceptance check
recomputing every metric cell.
    python -m src.rc21_report all [final|smoke]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc21_final as F
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
WIN = {"small": tuple(range(8, 25)), "all": tuple(range(8, 61))}
CFG = {"job": "d-final", "rep": "final_report", "exp": "final_export"}
METS = ["log_loss", "BA", "brier", "AUC", "sensitivity", "specificity", "q20_BA"]


def use(stage):
    CFG.update({"final": {"job": "d-final", "rep": "final_report", "exp": "final_export"}, "smoke": {"job": "d-smoke", "rep": "smoke_report", "exp": "smoke_export"}}[stage])


def _se(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan


def verdict(d, margin, direction, n_req=8):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; m = float(d.mean()) if len(d) else np.nan
    good = (d < 0) if direction == "lower" else (d > 0); bad = (d > 0) if direction == "lower" else (d < 0)
    if len(d) < n_req:
        return f"INCOMPLETE ({len(d)}/{n_req})", m, int(good.sum())
    if (m <= -margin if direction == "lower" else m >= margin) and good.sum() >= F.MIN_GOOD:
        return "BETTER (DEV)", m, int(good.sum())
    if (m >= margin if direction == "lower" else m <= -margin) and bad.sum() >= F.MIN_GOOD:
        return "WORSE (DEV)", m, int(good.sum())
    return "NOT DIFFERENT (DEV)", m, int(good.sum())


def endpoints(B, metric, level, direction):
    rows = []
    for (arm, r), g in B.groupby(["arm", "repeat"]):
        cur = dict(zip(g.budget, g[metric] if direction == "higher" else -g[metric]))
        e = EV.endpoint(cur, level if direction == "higher" else -level, step=4)
        rows.append({"arm": arm, "repeat": r, "target": f"{metric} {'>=' if direction == 'higher' else '<='} {level}", "first": e["first"],
                     "confirmed_b": e["confirmed"], "spend": e["confirm_spend"], "censored": e["censored"]})
    return pd.DataFrame(rows)


def spend_pairs(E, pairs, horizon=60):
    out = []; thr, k = F.SPEND_RULE
    for a, b in pairs:
        if not ((E.arm == a).any() and (E.arm == b).any()):
            continue
        j = E[E.arm == a].set_index("repeat")[["spend", "censored"]].join(E[E.arm == b].set_index("repeat")[["spend", "censored"]], lsuffix="_a", rsuffix="_b", how="inner")
        imp = lambda s, c: np.where(c, horizon + 4, s)                   # censored -> 64, a LOWER bound (restricted score)
        d = imp(j.spend_a, j.censored_a) - imp(j.spend_b, j.censored_b); both = (~j.censored_a) & (~j.censored_b)
        fewer = (d < 0).sum(); verdict_ = "FEWER SIMULATIONS (DEV)" if (np.mean(d) <= -thr and fewer >= k and j.censored_a.sum() <= j.censored_b.sum()) else (
            "MORE SIMULATIONS (DEV)" if (np.mean(d) >= thr and (d > 0).sum() >= k and j.censored_a.sum() >= j.censored_b.sum()) else "NO CLEAR DIFFERENCE (DEV)")
        out.append({"contrast": f"{a} − {b}", "restricted_mean_difference(censored=64)": float(np.mean(d)), "fewer/equal/more": f"{int(fewer)}/{int((d == 0).sum())}/{int((d > 0).sum())}",
                    "both_confirmed": int(both.sum()), "observed_mean_difference_both_confirmed": float(np.mean(d[both])) if both.any() else np.nan,
                    "censored_first/second": f"{int(j.censored_a.sum())}/{int(j.censored_b.sum())}",
                    "per_repeat": ";".join(f"{'–' if ca else int(sa)}/{'–' if cb else int(sb)}" for sa, ca, sb, cb in zip(j.spend_a, j.censored_a, j.spend_b, j.censored_b)),
                    "verdict": verdict_})
    return pd.DataFrame(out)


def byproduct_units(U):
    """Every RC21 construction on each physical arm's own paid prefixes: arm label 'construction@arm'."""
    XP = []
    for u in U:
        if u["arm"] in F.PHYS_ARMS:
            for c in u["evals"][0]["p_all"]:
                XP.append({"arm": f"{c}@{u['arm']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                           "evals": [{"budget": e["budget"], "p": e["p_all"][c], "status": "ok"} for e in u["evals"]]})
    return XP


def final(stage="final"):
    import src.rc19b_keyhole_eval as KE
    use(stage); REP = OUT / CFG["rep"]; REP.mkdir(parents=True, exist_ok=True); M = P.manifest(); U = EV.load_units(OUT / CFG["job"]); X = KE.as_units(U, key="__none__")
    B = EV.label_metrics(X, M); Rl = KE.reliability(X, M); B.to_csv(REP / "final_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(REP / "final_reliability.csv", index=False, lineterminator="\n")
    A = {w: B[B.budget.isin(b)].groupby(["arm", "repeat"])[METS].mean().reset_index() for w, b in WIN.items()}
    n_req = len(F.REPEATS) if stage == "final" else 1; V = []
    for c in [F.Q1] + F.SECONDARY:
        role, a, b, met, win, direction, margin = c; T = A[win]
        x = T[T.arm == a].set_index("repeat")[met]; y = T[T.arm == b].set_index("repeat")[met]; d = (x - y).dropna()
        if not len(x) or not len(y):
            continue
        v, m, g = verdict(d.values, margin, direction, n_req)
        V.append({"role": role, "contrast": f"{a} − {b}", "metric": met, "window": win, "direction": direction, "margin": margin, "mean": m, "se": _se(d.values),
                  "min": float(d.min()) if len(d) else np.nan, "max": float(d.max()) if len(d) else np.nan, "repeats_good": f"{g}/{len(d)}", "verdict": v})
    V = pd.DataFrame(V); V.to_csv(REP / "final_verdicts.csv", index=False, lineterminator="\n")
    S = {w: T.groupby("arm")[METS].agg(["mean", _se]) for w, T in A.items()}
    for w in S:
        S[w].columns = [f"{a}_{'se' if b == '_se' else b}" for a, b in S[w].columns]
    E = pd.concat([endpoints(B, met, lev, dirn) for met, lev, dirn in F.TARGETS]); E.to_csv(REP / "final_endpoints.csv", index=False, lineterminator="\n")
    ES = E.groupby(["target", "arm"]).agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), censored=("censored", "sum"), first_mean=("first", "mean"),
                                         spend_mean=("spend", "mean"), spend_median=("spend", "median"), spend_min=("spend", "min"), spend_max=("spend", "max"),
                                         spend_per_repeat=("spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()
    SP = pd.concat([spend_pairs(E[E.target == t], F.SPEND_PAIRS).assign(target=t) for t in E.target.unique()]); SP.to_csv(REP / "final_spend_pairs.csv", index=False, lineterminator="\n")
    q2 = SP[(SP.target == "BA >= 0.93") & (SP.contrast == f"{F.Q2[1]} − {F.Q2[2]}")]
    MB = B[B.budget.isin([8, 12, 16, 20, 24, 32, 40, 60])].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "brier", "AUC", "q20_BA", "spec_NEW"]].mean().reset_index()
    MB.to_csv(REP / "final_matched_budgets.csv", index=False, lineterminator="\n")
    HC = Rl[Rl.budget.isin([24, 40, 60])].groupby(["arm", "budget"]).agg(cal_slope=("cal_slope", "mean"), ECE=("ECE", "mean"), corner_errors=("hard_NEW_conduction_errors", "sum"),
                                                                         corner_n=("hard_NEW_conduction_n", "sum")).reset_index()
    SK = B[B.budget.isin([24, 60])].groupby(["arm", "budget"]).agg(shortK_captured=("shortK_pooled_captured", "sum"), shortK_total=("shortK_pooled_total", "sum")).reset_index()
    cpu = []
    for u in U:
        steps = [e.get("cpu_s") for e in u["evals"] if e.get("cpu_s") is not None]
        cpu.append({"arm": u["arm"], "unit_cpu_s": float(u.get("cpu_s", u.get("seconds", np.nan))), "decision_cpu_s_per_step": float(np.mean(steps)) if steps else np.nan,
                    "paid_simulations": int(u.get("queries", len(u.get("paid_ids", []))))})
    CPU = pd.DataFrame(cpu).groupby("arm").agg(trajectories=("unit_cpu_s", "size"), cpu_s_mean=("unit_cpu_s", "mean"), cpu_s_total=("unit_cpu_s", "sum"),
                                               decision_cpu_s_per_step=("decision_cpu_s_per_step", "mean"), paid_simulations_per_trajectory=("paid_simulations", "mean")).reset_index()
    CPU.to_csv(REP / "final_cpu.csv", index=False, lineterminator="\n")
    # matched-path decomposition on the physical arms' own paths (exploratory): same queries, different model; same model, different path
    XP = byproduct_units(U); BP = EV.label_metrics(XP, M) if XP else pd.DataFrame(); DEC = pd.DataFrame(); MPm = pd.DataFrame()
    if len(BP):
        BP.to_csv(REP / "final_matched_byproducts.csv", index=False, lineterminator="\n")
        AP = {w: BP[BP.budget.isin(b)].groupby(["arm", "repeat"])[METS].mean().reset_index() for w, b in WIN.items()}
        MPm = AP["small"].groupby("arm")[["log_loss", "BA", "sensitivity", "specificity"]].mean().add_suffix(" B8–B24").join(
            AP["all"].groupby("arm")[["log_loss", "BA", "sensitivity", "specificity"]].mean().add_suffix(" B8–B60")).reset_index()
        new = F.construction("NEW_MARGIN") if "NEW_MARGIN" in set(u["arm"] for u in U) else None; rows = []
        pairs = [(f"SHQ_ATS_X@{p}", f"SHQ_ATS_H@{p}", f"model on {p}'s queries: X − H") for p in F.PHYS_ARMS] + [("SHQ_ATS_H@X_MARGIN", "SHQ_ATS_H@H_MARGIN", "path: H model on X's vs H's queries")]
        if new:
            pairs = [(f"{new}@{p}", f"SHQ_ATS_H@{p}", f"model on {p}'s queries: NEW − H") for p in F.PHYS_ARMS] + [
                (f"SHQ_ATS_H@NEW_MARGIN", "SHQ_ATS_H@H_MARGIN", "path: H model on NEW's vs H's queries"),
                (f"{new}@NEW_MARGIN", f"{new}@H_MARGIN", "path: NEW model on NEW's vs H's queries")] + pairs
        for a, b, lab in pairs:
            for w in ("small", "all"):
                for met, dirn in (("BA", "higher"), ("log_loss", "lower"), ("sensitivity", "higher"), ("specificity", "higher")):
                    T = AP[w]; x = T[T.arm == a].set_index("repeat")[met]; y = T[T.arm == b].set_index("repeat")[met]; d = (x - y).dropna()
                    if len(d):
                        rows.append({"decomposition": lab, "contrast": f"{a} − {b}", "window": w, "metric": met, "mean": float(d.mean()), "se": _se(d.values),
                                     "repeats_good": f"{int(((d > 0) if dirn == 'higher' else (d < 0)).sum())}/{len(d)}"})
        DEC = pd.DataFrame(rows); DEC.to_csv(REP / "final_matched_decomposition.csv", index=False, lineterminator="\n")
    post = pd.DataFrame([{"arm": u["arm"], "budget": e["budget"], **{k: v for k, v in e["info"].get("phr", {}).items() if not isinstance(v, list)}}
                         for u in U if u["arm"] in F.PHYS_ARMS for e in u["evals"] if e.get("info", {}).get("phr")])
    PD = post[post.budget.isin([8, 12, 16, 24, 40, 60])].groupby(["arm", "budget"]).mean(numeric_only=True).round(3).reset_index() if len(post) else pd.DataFrame()
    q1 = V.iloc[0]; q2v = q2.iloc[0] if len(q2) else None
    ans = "YES" if (q1.verdict.startswith("BETTER") or (q2v is not None and q2v.verdict.startswith("FEWER"))) else "NO"
    L = [f"# RC21 sequential stage — {stage} (fresh DEV repeats {F.REPEATS[0]}–{F.REPEATS[-1]}; frozen protocol PROTOCOL_RC21_FINAL.md)", "",
         f"**{q1.role} — {q1.contrast}, BA-AULC over the {q1.window} window (margin {q1.margin}): {q1.verdict}** (mean Δ {q1['mean']:+.4f} ± {q1.se:.4f} SE; better in {q1.repeats_good} repeats)", "",
         (f"**{F.Q2[0]} — {q2v.contrast}: {q2v.verdict}** (restricted mean difference {q2v['restricted_mean_difference(censored=64)']:+.2f} simulations; fewer/equal/more {q2v['fewer/equal/more']}; "
          f"censored {q2v['censored_first/second']})" if q2v is not None else f"**{F.Q2[0]}: not available**"), "",
         f"**Answer to the main question (better decisions OR fewer paid simulations to the same BA target than the previous strongest model): {ans} (DEV).** "
         "Probability-only improvements (log loss / Brier) are reported below and are not decision superiority.", "",
         "## Pre-declared contrasts", "", md(V, 4), "",
         "## AULC, B8–B24 (mean and SE over repeats)", "", md(S["small"].reset_index(), 4), "", "## AULC, B8–B60", "", md(S["all"].reset_index(), 4), "",
         "## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.", "",
         md(ES, 2), "", "Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):", "", md(SP, 2), "",
         "## Matched budgets (mean over repeats): both recalls, q20 and the NEW-batch conduction recall (corner diagnostic)", "", md(MB, 3), "",
         "## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over repeats) and calibration", "", md(HC, 3), "",
         "## Short-Keyhole capture (diagnostic)", "", md(SK, 0), "",
         "## Compute: decision CPU (seconds, single thread) separately from the paid-simulation count", "", md(CPU, 2), ""]
    if len(MPm):
        L += ["## Matched-path by-products on the physical arms' own paths (every budget; exploratory)", "", md(MPm, 4), "",
              "Decomposition (paired by repeat): 'model on P's queries' = same paid prefixes, different classifier; 'path' = same classifier, different query paths.", "", md(DEC, 4), ""]
    if len(PD):
        L += ["## PHR posterior diagnostics along the physical arms' paths (means)", "", md(PD, 3), ""]
    (REP / "FINAL.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    acc = export(U, X, B, XP, REP)
    print("\n".join(L)[:30000]); print("export acceptance", json.dumps(acc)); return V


def export(U, X, B, XP, REP):
    exp = OUT / CFG["exp"]; exp.mkdir(parents=True, exist_ok=True); keys, arrs, tids, buds, paths = [], [], [], [], []
    for u in list(X) + list(XP):
        keys.append(f"{u['arm']}|r{u['repeat']}|f{u['fold']}"); arrs.append(np.asarray([[np.nan if v is None else v for v in e["p"]] for e in u["evals"]], np.float32))
        tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray([e["budget"] for e in u["evals"]], np.int16))
    for u in U:
        hows = [e.get("how") for e in u["evals"]]
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s,
                          "rule": "startup" if q <= P.B0 else (hows[q - P.B0 - 1] if q - P.B0 - 1 < len(hows) and hows[q - P.B0 - 1] else "arm selector")})
    np.savez_compressed(exp / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)},
                        schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32 (identical to the unit cache)", "key": "arm|repeat|fold; 'construction@arm' = matched-path by-product on that arm's own path"})]))
    pd.DataFrame(paths).to_csv(exp / "paths.csv.gz", index=False, compression="gzip")
    Z = np.load(exp / "predictions_f32.npz", allow_pickle=False); Xe = []
    for i, k in enumerate(Z["keys"]):
        arm, r, f = k.split("|")
        if "@" in arm:
            continue
        to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        Xe.append({"arm": arm, "repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"]),
                   "evals": [{"budget": int(b), "p": to(Z[f"pred_{i}"][j])} for j, b in enumerate(Z[f"budgets_{i}"])]})
    a = EV.label_metrics(Xe, P.manifest()); j = a.merge(B, on=["arm", "repeat", "budget"], suffixes=("_export", "_csv")); res = {"cells_compared": int(len(j)), "cells_in_csv": int(len(B))}
    for c in ("BA", "sensitivity", "specificity", "AUC", "brier", "log_loss", "q20_BA", "spec_NEW"):
        d = np.abs(j[f"{c}_export"].to_numpy(float) - j[f"{c}_csv"].to_numpy(float)); d = d[np.isfinite(d)]
        res[c] = {"max_abs_diff": float(d.max()) if len(d) else 0.0, "cells_differing_gt_1e-12": int((d > 1e-12).sum())}
    res["PASS"] = bool(res["cells_compared"] == res["cells_in_csv"] and all(v["cells_differing_gt_1e-12"] == 0 for v in res.values() if isinstance(v, dict)))
    (exp / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


if __name__ == "__main__":
    RC.limit_threads(1); final(sys.argv[2] if len(sys.argv) > 2 else "final")
