"""RC24 post-audit (owner instruction 2026-10-22): pooled vs per-region evaluation of the geometry-block condition, with metrics
recomputed INDEPENDENTLY from the exported float32 predictions (no unit file, no src.rc22_eval metric code is used here).

Facts fixed by the code (src/rc22_common.blocks / block_tasks): the five geometry blocks are ONE k-means partition (k = 5, seed 2222)
of the public standardised log inputs. A "block seed" only changes the label-free startup / maximin path, so RC23 seeds 1-8 and
RC24 Stage C seeds 9-16 are new STARTUPS on the SAME five regions, not new geometry and not independent data.

Definitions (threshold 0.5, every budget 8..60, AULC = mean over the window's budgets):
  pooled      the 5 block learners of one seed concatenated (each run predicted once, by the learner that never saw its block)
  individual  one learner = one block; BA is UNDEFINED when the block holds one class (block 3: 0 Keyhole) - reported as NaN with
              the present class's recall; small minorities (block 1: 1 Keyhole, block 2: 4 conduction) get exact binomial intervals
  decomposition  pooled BA = 1 - (FN / n1 + FP / n0) / 2, so a pooled BA difference splits additively over blocks and classes:
              dBA = - sum_b (dFN_b / n1 + dFP_b / n0) / 2
    python -m src.rc24p_audit blocks | std
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import beta

import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
AUD = OUT / "post_audit"
WIN = {"B8_B24": range(8, 25), "B8_B60": range(8, 61)}


def load_export(d):
    Z = np.load(d / "predictions_f32.npz", allow_pickle=False); out = {}
    for i, k in enumerate(Z["keys"]):
        arm, rep, f = str(k).rsplit("|", 2); out[(arm, int(rep[1:]), int(f[1:]))] = (Z[f"budgets_{i}"].astype(int), Z[f"pred_{i}"].astype(float), Z[f"test_ids_{i}"].astype(str))
    return out


def cp(k, n, a=0.05):
    """Exact (Clopper-Pearson) 95 % interval for k successes of n."""
    if n == 0:
        return (np.nan, np.nan)
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1); hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k); return (float(lo), float(hi))


def rows_from(E, y_of):
    """One row per (arm, repeat, fold, budget): confusion counts on the learner's own test set."""
    R = []
    for (arm, rep, f), (bs, Pm, ids) in E.items():
        y = y_of.reindex(ids).to_numpy(int)
        for j, b in enumerate(bs):
            hat = Pm[j] >= 0.5; R.append({"arm": arm, "repeat": rep, "fold": f, "budget": int(b), "n1": int((y == 1).sum()), "n0": int((y == 0).sum()),
                                          "tp": int((hat & (y == 1)).sum()), "tn": int((~hat & (y == 0)).sum()),
                                          "ll": float(-np.mean(y * np.log(np.clip(Pm[j], 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - Pm[j], 1e-6, 1))))})
    D = pd.DataFrame(R); D["fn"] = D.n1 - D.tp; D["fp"] = D.n0 - D.tn
    D["sens"] = np.where(D.n1 > 0, D.tp / D.n1.clip(lower=1), np.nan); D["spec"] = np.where(D.n0 > 0, D.tn / D.n0.clip(lower=1), np.nan)
    D["BA"] = np.where((D.n1 > 0) & (D.n0 > 0), 0.5 * (D.sens + D.spec), np.nan); return D


def pooled(D):
    g = D.groupby(["arm", "repeat", "budget"])[["n1", "n0", "tp", "tn", "fn", "fp"]].sum().reset_index(); nl = D.groupby(["arm", "repeat", "budget"]).size().values
    g["learners"] = nl; g["sens"] = g.tp / g.n1; g["spec"] = g.tn / g.n0; g["BA"] = 0.5 * (g.sens + g.spec); return g


def aulc(T, by, cols=("BA", "sens", "spec")):
    out = []
    for w, bs in WIN.items():
        a = T[T.budget.isin(list(bs))].groupby(list(by))[list(cols)].mean().reset_index(); a["window"] = w; out.append(a)
    return pd.concat(out, ignore_index=True)


def decomposition(G, a, b):
    """Additive split of the pooled BA difference a - b over blocks (fold) and classes, per budget, then AULC."""
    D = G.copy(); n1 = D.groupby(["arm", "repeat", "budget"]).n1.transform("sum"); n0 = D.groupby(["arm", "repeat", "budget"]).n0.transform("sum")
    D["cK"] = -D.fn / n1 / 2; D["cC"] = -D.fp / n0 / 2
    X = D[D.arm == a].set_index(["repeat", "fold", "budget"])[["cK", "cC"]] - D[D.arm == b].set_index(["repeat", "fold", "budget"])[["cK", "cC"]]
    X = X.reset_index(); out = []
    for w, bs in WIN.items():
        s = X[X.budget.isin(list(bs))].groupby(["repeat", "fold"])[["cK", "cC"]].mean().reset_index().groupby("fold")[["cK", "cC"]].mean()
        s["window"] = w; out.append(s.reset_index())
    return pd.concat(out, ignore_index=True)


def block_report(E, M, label):
    y = M.y; D = rows_from(E, y); G = pooled(D); A_pool = aulc(G, ("arm", "repeat")); A_ind = aulc(D, ("arm", "repeat", "fold"))
    arms = sorted(D.arm.unique()); res = {"label": label, "arms": arms}
    # class counts per block
    cnt = D[D.budget == 8].groupby("fold")[["n1", "n0"]].first().reset_index(); res["class_counts"] = cnt.to_dict(orient="records")
    # pooled and individual means
    pm = A_pool.groupby(["window", "arm"]).BA.mean().unstack(); im = A_ind.groupby(["window", "arm"]).BA.mean().unstack()
    res["pooled_BA_AULC"] = pm.round(4).to_dict(); res["individual_mean_BA_AULC_defined_blocks"] = im.round(4).to_dict()
    # per block x arm: BA (if defined), Keyhole recall, conduction specificity AULC; mean over startups
    pb = A_ind.groupby(["window", "fold", "arm"])[["BA", "sens", "spec"]].mean().reset_index()
    # minority-class counts at B24 / B60 (summed over startups) with exact intervals
    mins = []
    for (f, arm), g in D[D.budget.isin([24, 60])].groupby(["fold", "arm"]):
        for b, gb in g.groupby("budget"):
            n1, n0 = int(gb.n1.sum()), int(gb.n0.sum()); tp, tn = int(gb.tp.sum()), int(gb.tn.sum())
            mins.append({"fold": f, "arm": arm, "budget": b, "keyhole_hit": f"{tp}/{n1}", "keyhole_recall": tp / n1 if n1 else np.nan, "keyhole_CI": cp(tp, n1),
                         "conduction_hit": f"{tn}/{n0}", "conduction_spec": tn / n0 if n0 else np.nan, "conduction_CI": cp(tn, n0)})
    M2 = pd.DataFrame(mins)
    # wins / losses per block (paired by startup) for the first arm pair of interest
    W = []
    for w in WIN:
        for f in sorted(D.fold.unique()):
            P_ = A_ind[(A_ind.window == w) & (A_ind.fold == f)].pivot_table(index="repeat", columns="arm", values="BA")
            for a in arms:
                for b in arms:
                    if a < b and a in P_ and b in P_:
                        d = (P_[a] - P_[b]).dropna(); W.append({"window": w, "fold": f, "contrast": f"{a} − {b}", "n": len(d), "mean": d.mean() if len(d) else np.nan,
                                                                "pos": int((d > 0).sum()), "neg": int((d < 0).sum())})
    W = pd.DataFrame(W)
    dec = {f"{a} − {b}": decomposition(G.merge(D.groupby(["arm", "repeat", "fold", "budget"])[["n1", "n0"]].first().reset_index(), how="left") if False else D, a, b).round(5).to_dict(orient="records")
           for a in arms for b in arms if a != b and "HA_LEAN" in b}
    return res, D, G, A_pool, A_ind, pb, M2, W, dec


def run_blocks():
    AUD.mkdir(parents=True, exist_ok=True); M = P.manifest(); out = {}
    E = load_export(OUT / "stage_c" / "export_block"); res, D, G, Ap, Ai, pb, M2, W, dec = block_report(E, M, "Stage C BLOCK startups 9-16 (fixed k-means blocks)")
    for nm, T in (("pooled_curves", G), ("learner_curves", D), ("pooled_aulc", Ap), ("individual_aulc", Ai), ("per_block_aulc", pb), ("minority_counts", M2), ("block_wins", W)):
        T.to_csv(AUD / f"stagec_block_{nm}.csv", index=False)
    res["decomposition_of_pooled_difference"] = dec; out["stage_c_block"] = res
    (AUD / "BLOCK_AUDIT.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("decomposition_of_pooled_difference",)}, indent=1, default=str)[:4000])
    return out


# ======================================================================================== target attainment (spend) - independent
TARGETS = (0.80, 0.90, 0.93, 0.95)
LOWER_BOUND_CENSORED = 61        # a curve not confirmed by B60 can confirm at the earliest at b = 57 (needs 57 and 61) -> spend >= 61


def endpoints(T, by):
    """Per curve: first budget with BA >= level; confirmation = first b with BA(b) >= level and BA(b + 4) >= level; spend = b + 4 paid
    simulations INCLUDING the 8 startup runs; maintenance = share of budgets >= b with BA >= level; held_to_60 = BA(60) >= level."""
    out = []
    for key, g in T.groupby(list(by)):
        cur = dict(zip(g.budget, g.BA)); bs = sorted(cur)
        for lev in TARGETS:
            row = dict(zip(by, key)); row["target"] = lev
            if any(not np.isfinite(cur[b]) for b in bs):
                row.update({"defined": False}); out.append(row); continue
            first = next((b for b in bs if cur[b] >= lev), None); conf = next((b for b in bs if b + 4 in cur and cur[b] >= lev and cur[b + 4] >= lev), None)
            row.update({"defined": True, "first": first, "confirmed_b": conf, "spend": None if conf is None else conf + 4, "attained": conf is not None,
                        "maintenance": float(np.mean([cur[b] >= lev for b in bs if b >= conf])) if conf is not None else np.nan,
                        "held_to_60": bool(cur[max(bs)] >= lev) if conf is not None else False})
            out.append(row)
    return pd.DataFrame(out)


def spend_compare(Ep, a, b, by="repeat"):
    from scipy.stats import t as tdist
    rows = []
    for lev in TARGETS:
        e = Ep[(Ep.target == lev) & (Ep.defined == True)]; x = e[e.arm == a].set_index(by); y = e[e.arm == b].set_index(by)  # noqa: E712
        j = x.join(y, lsuffix="_a", rsuffix="_b", how="inner")
        if not len(j):
            rows.append({"target": lev, "contrast": f"{a} − {b}", "units": 0}); continue
        att_a, att_b = j.attained_a.astype(bool), j.attained_b.astype(bool); both = att_a & att_b
        d = (j.spend_a.astype(float) - j.spend_b.astype(float))[both]; n = int(both.sum())
        dl = np.where(att_a, j.spend_a.astype(float), LOWER_BOUND_CENSORED) - np.where(att_b, j.spend_b.astype(float), LOWER_BOUND_CENSORED)
        ub = float(d.mean() + tdist.ppf(0.95, n - 1) * d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
        rows.append({"target": lev, "contrast": f"{a} − {b}", "units": len(j), "attained_a": int(att_a.sum()), "attained_b": int(att_b.sum()),
                     "spend_mean_attainers_a": float(j.spend_a[att_a].astype(float).mean()) if att_a.any() else np.nan,
                     "spend_mean_attainers_b": float(j.spend_b[att_b].astype(float).mean()) if att_b.any() else np.nan,
                     "both_attained": n, "diff_both_attained_mean": float(d.mean()) if n else np.nan, "diff_both_attained_upper95": ub,
                     "first_mean_a": float(j.first_a.astype(float).mean()), "first_mean_b": float(j.first_b.astype(float).mean()),
                     "maintenance_mean_a": float(j.maintenance_a.astype(float).mean()), "maintenance_mean_b": float(j.maintenance_b.astype(float).mean()),
                     "held_to_60_a": int(j.held_to_60_a.astype(bool).sum()), "held_to_60_b": int(j.held_to_60_b.astype(bool).sum()),
                     "lower_bound_imputed_diff_mean": float(np.mean(dl))})
    return pd.DataFrame(rows)


def run_std():
    AUD.mkdir(parents=True, exist_ok=True); M = P.manifest(); res = {}
    for part, d in (("stagec_std", OUT / "stage_c" / "export_std"), ("stagec_block", OUT / "stage_c" / "export_block"), ("stagea_std", OUT / "stage_a" / "export")):
        D = rows_from(load_export(d), M.y); G = pooled(D)
        Ap = aulc(G, ("arm", "repeat")); Ai = aulc(D, ("arm", "repeat", "fold")); Ep = endpoints(G, ("arm", "repeat")); Ei = endpoints(D, ("arm", "repeat", "fold"))
        Ll = aulc(D.assign(BA=D.ll), ("arm", "repeat", "fold"), cols=("BA",)).rename(columns={"BA": "ll"})
        for nm, T in (("pooled_aulc", Ap), ("individual_aulc", Ai), ("endpoints_pooled", Ep), ("endpoints_learners", Ei), ("learner_logloss", Ll)):
            T.to_csv(AUD / f"{part}_{nm}.csv", index=False)
        arms = sorted(G.arm.unique()); ref = "HA_LEAN_MARGIN"
        S = pd.concat([spend_compare(Ep, a, ref) for a in arms if a != ref]); S.to_csv(AUD / f"{part}_spend_vs_HA_LEAN.csv", index=False)
        Ei2 = Ei.copy(); Ei2["unit"] = Ei2.repeat.astype(str) + "_" + Ei2.fold.astype(str)
        SL = pd.concat([spend_compare(Ei2, a, ref, by="unit") for a in arms if a != ref]); SL.to_csv(AUD / f"{part}_spend_vs_HA_LEAN_learners.csv", index=False)
        res[part] = {"pooled": Ap.groupby(["window", "arm"])[["BA", "sens", "spec"]].mean().round(4).reset_index().to_dict(orient="records"),
                     "individual": Ai.groupby(["window", "arm"])[["BA", "sens", "spec"]].mean().round(4).reset_index().to_dict(orient="records")}
    (AUD / "STD_AND_SPEND_AUDIT.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print("ok")
    return res


if __name__ == "__main__":
    {"blocks": run_blocks, "std": run_std}[sys.argv[1]]()
