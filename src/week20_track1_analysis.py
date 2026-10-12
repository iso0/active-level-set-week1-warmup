"""Week 20 Track 1 analysis: curves, Week 18 AULC/contrast/QTT, fidelity to the historical caches, threshold mechanism.

Reads the per-run caches written by src.week20_track1_al (the frozen runner is not modified).  No model is fitted.
Steps: python -m src.week20_track1_analysis
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.week20_track1_al import ARMS, BMAX, CACHE, HIGH_U, LATE_NEG, OUT, REPEATS, T1, TASKS, W18, build_tasks, cache_path, grid, short, shortk_ids

SHORT = {"WHOLE_E1_STRADDLE": "WHOLE E1", "ACTIVE_E1_STRADDLE": "ACTIVE E1", "G3_MARGIN": "G3"}


def _w(df, name):
    T1.mkdir(parents=True, exist_ok=True)
    df.to_csv(T1 / name, index=False, lineterminator="\n")


def load_all():
    tasks = build_tasks()
    led, fits, preds, metas = [], [], [], []
    for t in tasks:
        for a in ARMS:
            r = json.loads(gzip.decompress(cache_path(t, a).read_bytes()))
            metas.append(r["meta"]); led += r["ledger"]; fits += r["fits"]
            test = np.asarray(r["meta"]["test"])
            for p in r["preds"]:
                preds.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "arm": a, "budget": p["budget"], "rows": test, "p": np.asarray(p["p"]),
                              "latent_mean": np.asarray(p["latent_mean"])})
    return tasks, pd.DataFrame(led), pd.DataFrame(fits), preds, pd.DataFrame(metas)


def curves(tasks, preds):
    """Per (task, arm, repeat, budget), pooled over the folds present at that budget (Week 18 real_curves construction)."""
    tk = {(t["task"], t["repeat"], t["fold"]): t for t in tasks}
    sk = shortk_ids()
    acc = {}
    for p in preds:
        t = tk[(p["task"], p["repeat"], p["fold"])]
        acc.setdefault((p["task"], p["arm"], p["repeat"], p["budget"]), []).append((t, p))
    rows = []
    from sklearn.metrics import roc_auc_score
    for (task, arm, rep, b), lst in acc.items():
        yy = np.concatenate([t["y"][p["rows"]] for t, p in lst]); pp = np.concatenate([p["p"] for t, p in lst])
        ids = np.concatenate([t["ids"][p["rows"]] for t, p in lst])
        yh = (pp >= .5).astype(int)
        sens = float(np.mean(yh[yy == 1] == 1)) if (yy == 1).any() else np.nan; spec = float(np.mean(yh[yy == 0] == 0)) if (yy == 0).any() else np.nan
        skm = np.isin(ids, list(sk))
        qa = []
        for t, p in lst:
            q = np.asarray(t["q20"], bool)
            if q.any():
                qa.append(float(np.mean((p["p"][q] >= .5) == t["y"][p["rows"]][q])))
        rows.append({"task": task, "arm": arm, "repeat": rep, "budget": b, "folds": len(lst), "BA": 0.5 * (sens + spec), "sensitivity": sens, "specificity": spec,
                     "shortK_sensitivity": float(np.mean(yh[skm] == 1)) if skm.any() else np.nan, "n_shortK": int(skm.sum()),
                     "brier": float(np.mean((pp - yy) ** 2)), "AUC": float(roc_auc_score(yy, pp)) if len(set(yy)) == 2 else np.nan, "q20": float(np.mean(qa)) if qa else np.nan})
    return pd.DataFrame(rows).sort_values(["task", "arm", "repeat", "budget"]).reset_index(drop=True)


def on_grid(c):
    return c[[b in grid(t) for t, b in zip(c.task, c.budget)]]


def aulc_table(c):
    from src.week18_metrics import aulc
    g = on_grid(c).copy()
    out = None
    for key in ("BA", "q20", "specificity", "sensitivity", "shortK_sensitivity", "brier", "AUC"):
        a = aulc(g, key)
        out = a if out is None else out.merge(a, on=["task", "repeat", "arm"])
    return out


def contrasts(au):
    from src.week18_metrics import contrast
    rows = []
    for key in ("BA_AULC", "q20_AULC", "specificity_AULC", "sensitivity_AULC", "shortK_sensitivity_AULC", "brier_AULC", "AUC_AULC"):
        for arm, ref in (("ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"), ("WHOLE_E1_STRADDLE", "G3_MARGIN")):
            c = contrast(au, key, arm, ref)
            if len(c):
                rows.append(c)
    return pd.concat(rows, ignore_index=True)


def qtt_table(c):
    from src.week18_metrics import qtt
    g = on_grid(c).copy()
    q = qtt(g, "BA", "G3_MARGIN", at=(40, 80))
    q["reached"] = np.isfinite(q.qtt)
    return q


def fidelity(tasks, preds):
    """Arms A and C against the historical Week 18 DEV caches at every grid budget <= 80."""
    hist = {"WHOLE_E1_STRADDLE": ("phase3/depth3/cache_real", ("GPR_depth", "mlii", "straddle")), "G3_MARGIN": ("phase2/cache_real", ("G3", "mlii", "margin"))}
    pk = {(p["task"], p["repeat"], p["fold"], p["arm"], p["budget"]): p for p in preds}
    rows = []
    for t in tasks:
        for arm, (sub, key) in hist.items():
            f = W18 / sub / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json"
            for r in json.loads(f.read_text()):
                if (r["model"], r["hyper"], r["rule"]) != key or int(r["budget"]) > BMAX:
                    continue
                b = int(r["budget"]); p = pk.get((t["task"], t["repeat"], t["fold"], arm, b))
                hp = np.array(r["p"].split(","), float)
                rows.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "arm": arm, "budget": b,
                             "rows_equal": p is not None and r["rows"] == ",".join(map(str, p["rows"])),
                             "max_abs_dp": float(np.abs(hp - p["p"]).max()) if p is not None else np.nan,
                             "hist_u_um": float(r["u"]) if r.get("u") not in (None, "", "nan") else np.nan})
    return pd.DataFrame(rows)


def thresholds(led, fits, tasks):
    """Learned-threshold trajectories for the E1 arms and the paid composition before the first u >= 200 um step."""
    f = fits[fits.arm.isin(["WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE"])].copy()
    tk = {(t["task"], t["repeat"], t["fold"]): t for t in tasks}
    runs = []
    for (task, rep, fold, arm), g in f.groupby(["task", "repeat", "fold", "arm"]):
        g = g.sort_values("budget"); hi = g[g.u_um >= HIGH_U]
        l = led[(led.task == task) & (led.repeat == rep) & (led.fold == fold) & (led.arm == arm)].sort_values("query_index")
        lq = l[l.sim_id == LATE_NEG].query_index
        row = {"task": task, "repeat": rep, "fold": fold, "arm": arm, "u_max_um": float(g.u_um.max()), "u_final_um": float(g.u_um.iloc[-1]),
               "steps_u_ge_200": int(len(hi)), "late_negative_paid_at": int(lq.iloc[0]) if len(lq) else np.nan,
               "late_negative_in_test": LATE_NEG in set(tk[(task, rep, fold)]["ids"][tk[(task, rep, fold)]["test"]]),
               "slope_nonpositive_steps": int(g.slope_nonpositive.astype(bool).sum()), "root_outside_steps": int(g.root_outside_paid_range.astype(bool).sum())}
        if len(hi):
            b0 = int(hi.budget.iloc[0]); paid = l[l.query_index <= b0]
            negs = paid[paid.label == 0]
            row.update({"first_high_budget": b0, "u_at_first_high_um": float(hi.u_um.iloc[0]), "branch_at_first_high": hi.threshold_branch.iloc[0],
                        "slope_at_first_high": float(hi.b.iloc[0]), "paid_neg_at_first_high": int(len(negs)), "paid_pos_at_first_high": int((paid.label == 1).sum()),
                        "paid_negatives_with_response": "; ".join(f"{h}:{v:.1f}" for h, v in zip(negs.H, negs.response_value_um)),
                        "deepest_paid_negative_um": float(negs.response_value_um.max()) if len(negs) else np.nan,
                        "late_negative_paid_before_first_high": bool(len(lq) and lq.iloc[0] <= b0),
                        "queries_before_first_high": "; ".join(f"{q}:{h}({lab})" for q, h, lab in zip(paid.query_index.tail(4), paid.H.tail(4), paid.label.tail(4)))})
        runs.append(row)
    return pd.DataFrame(runs)


def episodes(led, fits):
    """POST-HOC (added after results): u >= 200 um episodes of the E1 arms, the queries chosen during them, what
    ended them, and a step-level algorithmic attribution: the same threshold rule recomputed on the same paid pairs with
    only the late negative's whole value replaced by its A value (110.755 um).  This is a 1-D threshold computation,
    not a learner refit or an AL re-run; it does not establish downstream acquisition effects."""
    from src.week20_track1_al import threshold_details
    rows = []
    f = fits[fits.arm.isin(["WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE"])]
    for (task, rep, fold, arm), g in f.groupby(["task", "repeat", "fold", "arm"]):
        g = g.sort_values("budget"); hi = (g.u_um >= HIGH_U).to_numpy(); b = g.budget.to_numpy()
        if not hi.any():
            continue
        lr = led[(led.task == task) & (led.arm == arm) & (led.repeat == rep) & (led.fold == fold)].set_index("query_index").sort_index()
        i = 0
        while i < len(b):
            if not hi[i]:
                i += 1; continue
            j = i
            while j + 1 < len(b) and hi[j + 1]:
                j += 1
            s, e = int(b[i]), int(b[j]); gg = g[(g.budget >= s) & (g.budget <= e)]
            chosen = lr.loc[s + 1:min(e, BMAX - 1)]                      # queries selected inside the episode
            end_q = lr.loc[e + 1] if (e + 1) in lr.index and e < BMAX else None
            paid = lr.loc[:s]
            ok = np.isfinite(paid.response_value_um)
            t_ = np.log(paid.response_value_um[ok].to_numpy()); y_ = paid.label[ok].to_numpy()
            cf = paid.response_value_um.copy()
            if LATE_NEG in set(paid.sim_id):
                cf[paid.sim_id == LATE_NEG] = 110.755
                okc = np.isfinite(cf); tdc = threshold_details(np.log(cf[okc].to_numpy()), paid.label[okc].to_numpy())
                u_cf = float(np.exp(tdc["log_u"])) if np.isfinite(tdc["log_u"]) else np.nan; br_cf = tdc["threshold_branch"]; b_cf = tdc["b"]
            else:
                u_cf = br_cf = b_cf = np.nan
            rows.append({"task": task, "arm": arm, "repeat": rep, "fold": fold, "episode_start": s, "episode_end": e, "steps": e - s + 1,
                         "u_min_um": float(gg.u_um.min()), "u_max_um": float(gg.u_um.max()), "slope_min": float(gg.b.min()), "slope_max": float(gg.b.max()),
                         "paid_neg_at_start": int((paid.label == 0).sum()), "late_negative_only_paid_negative": bool(set(paid[paid.label == 0].sim_id) == {LATE_NEG}),
                         "queries_inside_episode": int(len(chosen) + (end_q is not None)), "negatives_revealed_inside": int((chosen.label == 0).sum()),
                         "median_whole_um_of_queries_inside": float(chosen.whole_um.median()) if len(chosen) else np.nan,
                         "ended_by": f"q{e + 1} {end_q.H} label {int(end_q.label)} whole {end_q.whole_um:.1f}" if end_q is not None else "not ended by B80",
                         "POSTHOC_u_with_late_negative_at_A_um": u_cf, "POSTHOC_branch": br_cf, "POSTHOC_slope": b_cf})
            i = j + 1
    return pd.DataFrame(rows)


def qtt_sustained(c):
    """POST-HOC sensitivity (added after results): first grid budget from which the repeat-pooled BA stays >= target
    at every later grid budget up to B80; QTT at the first grid point is left-censored (<= 16)."""
    g = on_grid(c)
    rows = []
    for task, h in g.groupby("task"):
        for at in (40, 80):
            target = h[(h.arm == "G3_MARGIN") & (h.budget == at)].BA.mean()
            for (rep, arm), k in h.groupby(["repeat", "arm"]):
                k = k.sort_values("budget"); ok = (k.BA >= target - 1e-12).to_numpy(); bb = k.budget.to_numpy()
                idx = [i for i in range(len(bb)) if ok[i:].all()]
                q = int(bb[idx[0]]) if idx else np.nan
                rows.append({"task": task, "target_at": at, "target": float(target), "repeat": rep, "arm": arm, "qtt_sustained": q,
                             "reached": bool(idx), "left_censored_at_grid_start": bool(idx and idx[0] == 0)})
    return pd.DataFrame(rows)


def path_overlap(led):
    rows = []
    for (task, rep, fold), g in led.groupby(["task", "repeat", "fold"]):
        sets = {a: set(h.sim_id) for a, h in g.groupby("arm")}
        st = g[g.rule == "startup_maximin"].groupby("arm").query_index.max()
        r = {"task": task, "repeat": rep, "fold": fold, "startup": int(st.iloc[0]), "startup_identical": len(set(st)) == 1}
        for a, b in (("ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"), ("ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("WHOLE_E1_STRADDLE", "G3_MARGIN")):
            r[f"jaccard_B80_{SHORT[a]}_vs_{SHORT[b]}"] = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
        for a, h in g.groupby("arm"):
            r[f"neg_frac_paid_B80_{SHORT[a]}"] = float((h.label == 0).mean())
        rows.append(r)
    return pd.DataFrame(rows)


def figures(c, th, fits):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"WHOLE_E1_STRADDLE": "#4477AA", "ACTIVE_E1_STRADDLE": "#CC3311", "G3_MARGIN": "#666666"}
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, task in zip(axs, TASKS):
        for arm in ARMS:
            g = c[(c.task == task) & (c.arm == arm)].groupby("budget").BA.agg(["mean", "min", "max"]).reset_index()
            g = g[g.budget >= 16]
            ax.plot(g.budget, g["mean"], color=col[arm], lw=1.4, label=SHORT[arm]); ax.fill_between(g.budget, g["min"], g["max"], color=col[arm], alpha=.12, lw=0)
        ax.set_title(f"{task}: BA by paid queries (mean, range over repeats 1–4)", loc="left", fontsize=8); ax.set_xlabel("paid simulations")
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("balanced accuracy"); axs[0].legend(fontsize=7, frameon=False)
    (T1 / "figures").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(T1 / "figures/track1_BA_curves.png", dpi=160); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    f = fits[(fits.task == "R3_NEW") & fits.arm.isin(["WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE"])]
    top = 400.0
    for ax, arm in zip(axs, ["WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE"]):
        for (rep, fold), g in f[f.arm == arm].groupby(["repeat", "fold"]):
            hi = (g.u_um >= HIGH_U).any()
            ax.plot(g.budget, np.minimum(g.u_um, top), color=col[arm] if hi else "#BBBBBB", lw=1.0 if hi else 0.7, alpha=.9)
            off = g[g.u_um > top]
            ax.scatter(off.budget, np.full(len(off), top), marker="^", color="black", s=14, zorder=3)
        ax.axhline(HIGH_U, color="#666666", ls="--", lw=.7); ax.set_ylim(0, top * 1.05)
        ax.set_title(f"R3_NEW {SHORT[arm]}: learned threshold u per paid query\n(coloured: runs reaching 200 µm; ▲ off-scale values, up to 1.5e119 µm)", loc="left", fontsize=8)
        ax.set_xlabel("paid simulations"); ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("learned threshold u (µm)")
    fig.tight_layout(); fig.savefig(T1 / "figures/track1_NEW_threshold_trajectories.png", dpi=160); plt.close(fig)


def main():
    tasks, led, fits, preds, metas = load_all()
    _w(led, "ledger_all_queries.csv.gz"); _w(fits, "fit_diagnostics_all.csv.gz"); _w(metas.drop(columns=["test"]), "run_meta.csv")
    c = curves(tasks, preds); _w(c, "curves_every_step.csv")
    gp = pd.DataFrame([{"task": p["task"], "repeat": p["repeat"], "fold": p["fold"], "arm": p["arm"], "budget": p["budget"], "row": int(r), "p": float(v)}
                       for p in preds if p["budget"] in grid(p["task"]) for r, v in zip(p["rows"], p["p"])])
    _w(gp, "predictions_grid.csv.gz")
    au = aulc_table(c); _w(au, "aulc_per_repeat.csv")
    ct = contrasts(au); _w(ct, "contrasts.csv")
    q = qtt_table(c); _w(q, "qtt.csv")
    fid = fidelity(tasks, preds); _w(fid, "fidelity_vs_week18_caches.csv")
    th = thresholds(led, fits, tasks); _w(th, "threshold_mechanism_runs.csv")
    po = path_overlap(led); _w(po, "path_overlap.csv")
    ep = episodes(led, fits); _w(ep, "POSTHOC_threshold_episodes.csv")
    qs = qtt_sustained(c); _w(qs, "POSTHOC_qtt_sustained.csv")
    figures(c, th, fits)
    print(au.groupby(["task", "arm"])[["BA_AULC", "q20_AULC"]].mean().round(4))
    print(ct[ct.metric.isin(["BA_AULC", "q20_AULC"])].round(4).to_string())
    print("fidelity max |dp|:", fid.groupby("arm").max_abs_dp.max().to_dict(), "rows equal:", bool(fid.rows_equal.all()), "n", len(fid))
    return c, au, ct, q, fid, th, po


if __name__ == "__main__":
    main()
