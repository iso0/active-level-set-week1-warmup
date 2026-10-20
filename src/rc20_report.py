"""RC20 sequential-stage report (frozen with PROTOCOL_RC20_FINAL.md before any final outcome): every pre-declared contrast,
learning curves, target attainment and confirmation spend (second checkpoint b + 4), censoring, reliability, the fast-scan
corner, decision CPU separately from the paid-simulation count, the matched-path by-products on the candidate's own paths,
float32 exports of every per-budget prediction and paid path, and an acceptance check recomputing every metric cell.
    python -m src.rc20_report all [final|smoke]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc20_final as F
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
WIN = {"small": tuple(range(8, 25)), "all": tuple(range(8, 61))}
CFG = {"job": "c-final", "rep": "final_report", "exp": "final_export"}


def use(stage):
    CFG.update({"final": {"job": "c-final", "rep": "final_report", "exp": "final_export"}, "smoke": {"job": "c-smoke", "rep": "smoke_report", "exp": "smoke_export"}}[stage])


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


def load():
    import src.rc19b_keyhole_eval as KE
    U = EV.load_units(OUT / CFG["job"]); X = KE.as_units(U, key="__none__")
    for x in X:                                                           # candidate arms keep their arm name (not the construction)
        pass
    return U, X


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


def final(stage="final"):
    import src.rc19b_keyhole_eval as KE
    use(stage); REP = OUT / CFG["rep"]; REP.mkdir(parents=True, exist_ok=True); M = P.manifest(); U, X = load()
    B = EV.label_metrics(X, M); Rl = KE.reliability(X, M); B.to_csv(REP / "final_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(REP / "final_reliability.csv", index=False, lineterminator="\n")
    A = {w: B[B.budget.isin(b)].groupby(["arm", "repeat"])[["log_loss", "BA", "brier", "AUC", "sensitivity", "specificity"]].mean().reset_index() for w, b in WIN.items()}
    n_req = len(F.REPEATS) if stage == "final" else 1; V = []
    for c in [F.PRIMARY] + F.SECONDARY:
        role, a, b, met, win, direction, margin = c; T = A[win]
        x = T[T.arm == a].set_index("repeat")[met]; y = T[T.arm == b].set_index("repeat")[met]; d = (x - y).dropna()
        v, m, g = verdict(d.values, margin, direction, n_req)
        V.append({"role": role, "contrast": f"{a} − {b}", "metric": met, "window": win, "direction": direction, "margin": margin, "mean": m, "se": _se(d.values),
                  "min": float(d.min()) if len(d) else np.nan, "max": float(d.max()) if len(d) else np.nan, "repeats_good": f"{g}/{len(d)}", "verdict": v})
    V = pd.DataFrame(V); V.to_csv(REP / "final_verdicts.csv", index=False, lineterminator="\n")
    S = {w: T.groupby("arm")[["log_loss", "BA", "brier", "AUC", "sensitivity", "specificity"]].agg(["mean", _se]) for w, T in A.items()}
    for w in S:
        S[w].columns = [f"{a}_{'se' if b == '_se' else b}" for a, b in S[w].columns]
    E = pd.concat([endpoints(B, met, lev, dirn) for met, lev, dirn in F.TARGETS]); E.to_csv(REP / "final_endpoints.csv", index=False, lineterminator="\n")
    ES = E.groupby(["target", "arm"]).agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), censored=("censored", "sum"), first_mean=("first", "mean"),
                                         spend_mean=("spend", "mean"), spend_median=("spend", "median"), spend_min=("spend", "min"), spend_max=("spend", "max"),
                                         spend_per_repeat=("spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()
    SP = pd.concat([spend_pairs(E[E.target == t], F.SPEND_PAIRS).assign(target=t) for t in E.target.unique()])
    MB = B[B.budget.isin([8, 12, 16, 20, 24, 40, 60])].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "brier", "AUC", "q20_BA", "spec_NEW"]].mean().reset_index()
    cpu = []
    for u in U:
        steps = [e.get("cpu_s") for e in u["evals"] if e.get("cpu_s") is not None]
        cpu.append({"arm": u["arm"], "unit_cpu_s": float(u.get("seconds", np.nan)), "decision_cpu_s_per_step": float(np.mean(steps)) if steps else np.nan,
                    "paid_simulations": int(u.get("queries", len(u.get("paid_ids", []))))})
    CPU = pd.DataFrame(cpu).groupby("arm").agg(trajectories=("unit_cpu_s", "size"), cpu_s_mean=("unit_cpu_s", "mean"), cpu_s_total=("unit_cpu_s", "sum"),
                                               decision_cpu_s_per_step=("decision_cpu_s_per_step", "mean"), paid_simulations_per_trajectory=("paid_simulations", "mean")).reset_index()
    # matched-path by-products on the candidate's own paths (exploratory): candidate vs SHQ_ATS vs SHQ_A, same paid prefixes
    XP = []
    for u in U:
        ev = [e for e in u["evals"] if "p_all" in e]
        if u["arm"] in F.CAND_ARMS and ev:
            for c in [u["cand"]] + list(ev[0]["p_all"].keys()):
                XP.append({"arm": f"{c}@{u['arm']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                           "evals": [{"budget": e["budget"], "p": (e["p"][c] if c == u["cand"] else e["p_all"][c]), "status": "ok"} for e in ev]})
    BP = EV.label_metrics(XP, M) if XP else pd.DataFrame(); MP = pd.DataFrame()
    if len(BP):
        BP.to_csv(REP / "final_matched_byproducts.csv", index=False, lineterminator="\n")
        MP = BP.groupby(["arm"])[["log_loss", "BA", "brier"]].mean().reset_index()
    prim = V.iloc[0]
    L = [f"# RC20 sequential stage — {stage} (fresh DEV repeats {F.REPEATS[0]}–{F.REPEATS[-1]}; frozen protocol PROTOCOL_RC20_FINAL.md)", "",
         f"**{prim.role} — {prim.contrast}, {prim.metric} AULC over the {prim.window} window ({prim.direction} is better, margin {prim.margin}): {prim.verdict}** "
         f"(mean Δ {prim['mean']:+.4f} ± {prim.se:.4f} SE; good direction in {prim.repeats_good} repeats)", "",
         "## Pre-declared contrasts", "", md(V, 4), "",
         "## AULC, B8–B24 (mean and SE over repeats)", "", md(S["small"].reset_index(), 4), "", "## AULC, B8–B60", "", md(S["all"].reset_index(), 4), "",
         "## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at the second checkpoint b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.", "",
         md(ES, 2), "", "Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):", "", md(SP, 2), "",
         "## Matched budgets (mean over repeats)", "", md(MB, 3), "",
         "## Compute: GP / decision CPU (seconds) separately from the paid-simulation count", "", md(CPU, 2), ""]
    if len(MP):
        L += ["## Exploratory: same paid prefixes on the candidate's own paths (recorded every 4 budgets)", "", md(MP, 4), ""]
    (REP / "FINAL.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    acc = export(U, X, B, REP, stage)
    print("\n".join(L)[:20000]); print("export acceptance", json.dumps(acc)); return V


def export(U, X, B, REP, stage):
    exp = OUT / CFG["exp"]; exp.mkdir(parents=True, exist_ok=True); keys, arrs, tids, buds, paths = [], [], [], [], []
    for u in X:
        keys.append(f"{u['arm']}|r{u['repeat']}|f{u['fold']}"); arrs.append(np.asarray([[np.nan if v is None else v for v in e["p"]] for e in u["evals"]], np.float32))
        tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray([e["budget"] for e in u["evals"]], np.int16))
    for u in U:
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s})
    np.savez_compressed(exp / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32 (identical to the unit cache)"})]))
    pd.DataFrame(paths).to_csv(exp / "paths.csv.gz", index=False, compression="gzip")
    Z = np.load(exp / "predictions_f32.npz", allow_pickle=False); Xe = []
    for i, k in enumerate(Z["keys"]):
        arm, r, f = k.split("|"); to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
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
