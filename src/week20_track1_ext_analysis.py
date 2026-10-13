"""Week 20 Track 1 extension — analysis (DEV repeats 5–8, plus the repeats 1–8 summary).  Reads the run caches; fits nothing.
Endpoints, hypotheses and the decision rule are frozen in track1_ext/manifest_track1_ext.json.

Step: python -m src.week20_track1_ext analyze
"""
from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd

import src.week20_track1_al as A
import src.week20_track1_analysis as N
from src.week18_metrics import contrast, qtt
from src.week20_track1_ext import BASE_ARMS, GUARD, OUTX, REPEATS_X, SHORT, build_tasks_x

E1_ARMS = ("WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE", GUARD)
ALL_ARMS = (*BASE_ARMS, GUARD)
METRICS = ("BA_AULC", "q20_AULC", "specificity_AULC", "sensitivity_AULC", "shortK_sensitivity_AULC", "brier_AULC", "AUC_AULC")
PAIRS = (("ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"), ("WHOLE_E1_STRADDLE", "G3_MARGIN"),
         (GUARD, "WHOLE_E1_STRADDLE"), ("ACTIVE_E1_STRADDLE", GUARD), (GUARD, "G3_MARGIN"))


def _w(df, name):
    OUTX.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTX / name, index=False, lineterminator="\n")


def load(tasks, arms):
    led, fits, preds, metas = [], [], [], []
    for t in tasks:
        for a in arms:
            p = A.cache_path(t, a)
            if not p.exists():
                continue
            r = json.loads(gzip.decompress(p.read_bytes()))
            metas.append(r["meta"]); led += r["ledger"]; fits += r["fits"]
            test = np.asarray(r["meta"]["test"])
            for q in r["preds"]:
                preds.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "arm": a, "budget": q["budget"], "rows": test, "p": np.asarray(q["p"]),
                              "latent_mean": np.asarray(q["latent_mean"])})
    return pd.DataFrame(led), pd.DataFrame(fits), preds, pd.DataFrame(metas)


def contrasts_x(au, label):
    rows = []
    for key in METRICS:
        for arm, ref in PAIRS:
            c = contrast(au, key, arm, ref)
            if len(c):
                rows.append(c.assign(repeats_set=label))
    return pd.concat(rows, ignore_index=True)


def guard_checks(led, fits, preds):
    """X-H3a identity (arm D vs arm A wherever A has no non-positive-slope step) and guard activations."""
    pk = {(p["task"], p["repeat"], p["fold"], p["arm"], p["budget"]): p for p in preds}
    rows = []
    for (task, rep, fold), g in fits[fits.arm == GUARD].groupby(["task", "repeat", "fold"]):
        fa = fits[(fits.task == task) & (fits.repeat == rep) & (fits.fold == fold) & (fits.arm == "WHOLE_E1_STRADDLE")]
        la = led[(led.task == task) & (led.repeat == rep) & (led.fold == fold) & (led.arm == "WHOLE_E1_STRADDLE")].sort_values("query_index").sim_id.tolist()
        ld = led[(led.task == task) & (led.repeat == rep) & (led.fold == fold) & (led.arm == GUARD)].sort_values("query_index").sim_id.tolist()
        div = next((i + 1 for i, (x, y) in enumerate(zip(la, ld)) if x != y), None)
        dp = [float(np.abs(pk[(task, rep, fold, GUARD, b)]["p"] - pk[(task, rep, fold, "WHOLE_E1_STRADDLE", b)]["p"]).max())
              for b in sorted(g.budget) if (task, rep, fold, "WHOLE_E1_STRADDLE", b) in pk]
        a_np = int(fa.slope_nonpositive.astype(bool).sum())
        trig = g.slope_nonpositive.astype(bool) & (g.u_um.round(9) == 111.0)
        rows.append({"task": task, "repeat": rep, "fold": fold, "A_nonpositive_slope_steps": a_np, "D_guard_activations": int(trig.sum()),
                     "D_first_activation_budget": int(g[trig].budget.min()) if trig.any() else np.nan,
                     "paths_identical": div is None and len(la) == len(ld), "first_divergent_query": div, "max_abs_dp_D_vs_A": float(max(dp)) if dp else np.nan,
                     "identity_expected": a_np == 0, "D_u_max_um": float(g.u_um.max()), "A_u_max_um": float(fa.u_um.max())})
    return pd.DataFrame(rows)


def thresholds_x(led, fits, tasks):
    tk = {(t["task"], t["repeat"], t["fold"]): t for t in tasks}
    rows = []
    for (task, rep, fold, arm), g in fits[fits.arm.isin(E1_ARMS)].groupby(["task", "repeat", "fold", "arm"]):
        g = g.sort_values("budget"); hi = g[g.u_um >= A.HIGH_U]
        l = led[(led.task == task) & (led.repeat == rep) & (led.fold == fold) & (led.arm == arm)].sort_values("query_index")
        lq = l[l.sim_id == A.LATE_NEG].query_index
        r = {"task": task, "repeat": rep, "fold": fold, "arm": arm, "u_max_um": float(g.u_um.max()), "u_final_um": float(g.u_um.iloc[-1]), "steps_u_ge_200": int(len(hi)),
             "late_negative_paid_at": int(lq.iloc[0]) if len(lq) else np.nan, "late_negative_in_test": A.LATE_NEG in set(tk[(task, rep, fold)]["ids"][tk[(task, rep, fold)]["test"]]),
             "slope_nonpositive_steps": int(g.slope_nonpositive.astype(bool).sum()), "root_outside_steps": int(g.root_outside_paid_range.astype(bool).sum())}
        if len(hi):
            b0 = int(hi.budget.iloc[0]); paid = l[l.query_index <= b0]; negs = paid[paid.label == 0]
            r.update({"first_high_budget": b0, "u_at_first_high_um": float(hi.u_um.iloc[0]), "branch_at_first_high": hi.threshold_branch.iloc[0], "slope_at_first_high": float(hi.b.iloc[0]),
                      "paid_neg_at_first_high": int(len(negs)), "late_negative_only_paid_negative": bool(set(negs.sim_id) == {A.LATE_NEG}),
                      "late_negative_paid_before_first_high": bool(len(lq) and lq.iloc[0] <= b0)})
        rows.append(r)
    return pd.DataFrame(rows)


def path_overlap_x(led):
    rows = []
    for (task, rep, fold), g in led.groupby(["task", "repeat", "fold"]):
        sets = {a: set(h.sim_id) for a, h in g.groupby("arm")}
        st = g[g.rule == "startup_maximin"].groupby("arm").query_index.max()
        r = {"task": task, "repeat": rep, "fold": fold, "startup": int(st.iloc[0]), "startup_identical": len(set(st)) == 1}
        for a, b in PAIRS:
            if a in sets and b in sets:
                r[f"jaccard_B80_{SHORT[a]}_vs_{SHORT[b]}"] = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
        for a, h in g.groupby("arm"):
            r[f"neg_frac_paid_B80_{SHORT[a]}"] = float((h.label == 0).mean())
        rows.append(r)
    return pd.DataFrame(rows)


def figures_x(c, fits):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"WHOLE_E1_STRADDLE": "#4477AA", "ACTIVE_E1_STRADDLE": "#CC3311", "G3_MARGIN": "#666666", GUARD: "#228833"}
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.4))
    cc = c[c.repeat.isin(REPEATS_X)]
    for ax, task in zip(axs, A.TASKS):
        for arm in ALL_ARMS:
            g = cc[(cc.task == task) & (cc.arm == arm)].groupby("budget").BA.agg(["mean", "min", "max"]).reset_index()
            g = g[g.budget >= 16]
            if not len(g):
                continue
            ax.plot(g.budget, g["mean"], color=col[arm], lw=1.4, label=SHORT[arm]); ax.fill_between(g.budget, g["min"], g["max"], color=col[arm], alpha=.10, lw=0)
        ax.set_title(f"{task}: BA by paid queries (mean, range over repeats 5–8)", loc="left", fontsize=8); ax.set_xlabel("paid simulations")
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("balanced accuracy"); axs[0].legend(fontsize=7, frameon=False)
    (OUTX / "figures").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(OUTX / "figures/ext_BA_curves_r5_8.png", dpi=160); plt.close(fig)
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.6), sharey=True)
    f = fits[(fits.task == "R3_NEW") & fits.arm.isin(E1_ARMS)]
    top = 400.0
    for ax, arm in zip(axs, ("WHOLE_E1_STRADDLE", GUARD, "ACTIVE_E1_STRADDLE")):
        for (rep, fold), g in f[f.arm == arm].groupby(["repeat", "fold"]):
            hi = (g.u_um >= A.HIGH_U).any()
            ax.plot(g.budget, np.minimum(g.u_um, top), color=col[arm] if hi else "#BBBBBB", lw=1.0 if hi else 0.7, alpha=.9)
            off = g[g.u_um > top]
            ax.scatter(off.budget, np.full(len(off), top), marker="^", color="black", s=14, zorder=3)
        ax.axhline(A.HIGH_U, color="#666666", ls="--", lw=.7); ax.axhline(111.0, color="#228833", ls=":", lw=.7); ax.set_ylim(0, top * 1.05)
        ax.set_title(f"R3_NEW {SHORT[arm]}, repeats 5–8: learned threshold u\n(coloured: runs reaching 200 µm; ▲ off-scale; dotted: 111 µm guard value)", loc="left", fontsize=8)
        ax.set_xlabel("paid simulations"); ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("learned threshold u (µm)")
    fig.tight_layout(); fig.savefig(OUTX / "figures/ext_NEW_threshold_trajectories_r5_8.png", dpi=160); plt.close(fig)


def verdicts(ct58, ct18, fid, gc, th):
    def m(ct, task, arm, ref, key="BA_AULC"):
        r = ct[(ct.task == task) & (ct.arm == arm) & (ct.ref == ref) & (ct.metric == key)]
        return r.iloc[0] if len(r) else None
    out = []
    ok0 = bool(fid.rows_equal.all() and fid.max_abs_dp.max() <= 1e-4)
    out.append({"hypothesis": "X-H0_fidelity", "verdict": "SUPPORTED" if ok0 else "FALSIFIED", "detail": f"max |dp| {fid.max_abs_dp.max():.2e} over {len(fid)} comparisons; rows equal {bool(fid.rows_equal.all())}"})
    for h, arm, ref in (("X-H1_primary_replication", "ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("X-H2_target_ablation", "ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"),
                        ("X-H3b_guard_effect", GUARD, "WHOLE_E1_STRADDLE")):
        r = m(ct58, "R3_NEW", arm, ref)
        out.append({"hypothesis": h, "verdict": "SUPPORTED" if r is not None and r["mean"] > 0 else "FALSIFIED",
                    "detail": f"R3_NEW repeats 5-8: {r['mean']:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]" if r is not None else "missing"})
    ide = gc[gc.identity_expected]
    ok3a = bool(len(ide) and ide.paths_identical.all() and (ide.max_abs_dp_D_vs_A == 0).all())
    out.append({"hypothesis": "X-H3a_guard_identity", "verdict": "SUPPORTED" if ok3a else ("FALSIFIED" if len(ide) else "NOT TESTABLE"),
                "detail": f"{len(ide)} runs without a non-positive slope in A; identical {int(ide.paths_identical.sum()) if len(ide) else 0}; max |dp| {ide.max_abs_dp_D_vs_A.max() if len(ide) else np.nan}"})
    r = m(ct58, "R3_NEW", "ACTIVE_E1_STRADDLE", GUARD)
    out.append({"hypothesis": "X-H3c_remaining_target_effect", "verdict": "DESCRIPTIVE", "detail": f"{r['mean']:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]" if r is not None else "missing"})
    o1, o2 = m(ct58, "R3_OLD", "ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"), m(ct58, "R3_OLD", "ACTIVE_E1_STRADDLE", "G3_MARGIN")
    p1, p2 = m(ct58, "R1_POOLED", "ACTIVE_E1_STRADDLE", "G3_MARGIN"), m(ct58, "R1_POOLED", "WHOLE_E1_STRADDLE", "G3_MARGIN")
    ok4 = abs(o1["mean"]) < 0.01 and o2["mean"] > 0 and p1["mean"] >= p2["mean"]
    out.append({"hypothesis": "X-H4_old_pooled", "verdict": "SUPPORTED" if ok4 else "FALSIFIED",
                "detail": f"OLD ACTIVE-WHOLE {o1['mean']:+.4f}, ACTIVE-G3 {o2['mean']:+.4f}; POOLED ACTIVE-G3 {p1['mean']:+.4f} vs WHOLE-G3 {p2['mean']:+.4f}"})
    tn = th[th.task == "R3_NEW"]
    act = tn[tn.arm == "ACTIVE_E1_STRADDLE"]; wh = tn[(tn.arm == "WHOLE_E1_STRADDLE") & (tn.steps_u_ge_200 > 0)]
    ok5 = bool(act.u_max_um.max() < A.HIGH_U and (wh.late_negative_paid_before_first_high.astype(bool).all() if len(wh) else True))
    out.append({"hypothesis": "X-H5_threshold_mechanism", "verdict": "SUPPORTED" if ok5 else "FALSIFIED",
                "detail": f"ACTIVE max u {act.u_max_um.max():.1f} um; WHOLE runs with u >= 200: {len(wh)}, late negative paid before in {int(wh.late_negative_paid_before_first_high.astype(bool).sum()) if len(wh) else 0}"})
    r18 = m(ct18, "R3_NEW", "ACTIVE_E1_STRADDLE", "G3_MARGIN"); r18w = m(ct18, "R3_NEW", "ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE")
    out.append({"hypothesis": "X-H6_eight_repeat_summary", "verdict": "DESCRIPTIVE",
                "detail": f"repeats 1-8: ACTIVE-G3 {r18['mean']:+.4f} [{r18.lo:+.4f}, {r18.hi:+.4f}]; ACTIVE-WHOLE {r18w['mean']:+.4f} [{r18w.lo:+.4f}, {r18w.hi:+.4f}]"})
    out.append({"hypothesis": "X-H7_secondary", "verdict": "DESCRIPTIVE", "detail": "see contrasts_r5_8.csv / qtt_r5_8.csv"})
    v = pd.DataFrame(out)
    h1 = v.loc[v.hypothesis == "X-H1_primary_replication", "verdict"].iloc[0] == "SUPPORTED"
    dec = {"rule": json.loads((OUTX / "manifest_track1_ext.json").read_text(encoding="utf-8"))["decision_rule"],
           "X-H1_supported": bool(h1), "repeats_1_8_ACTIVE_minus_G3": float(r18["mean"]), "repeats_1_8_interval": [float(r18.lo), float(r18.hi)],
           "decision": "C3 PROTOCOL DRAFT (not executed)" if h1 and r18["mean"] > 0 else "HOLD (no C3 protocol)"}
    return v, dec


def main():
    t58, t14 = build_tasks_x(REPEATS_X), build_tasks_x((1, 2, 3, 4))
    led, fits, preds, metas = load(t58, ALL_ARMS)
    led14, fits14, preds14, metas14 = load(t14, BASE_ARMS)
    _w(led, "ledger_all_queries.csv.gz"); _w(fits, "fit_diagnostics_all.csv.gz"); _w(metas.drop(columns=["test"]), "run_meta.csv")
    c58 = N.curves(t58, preds); _w(c58, "curves_every_step.csv")
    c14 = N.curves(t14, preds14)
    au58, au14 = N.aulc_table(c58), N.aulc_table(c14)
    old14 = pd.read_csv(A.T1 / "aulc_per_repeat.csv")
    chk = au14.merge(old14, on=["task", "repeat", "arm"], suffixes=("", "_track1"))
    repro = float(np.nanmax(np.abs(chk.BA_AULC - chk.BA_AULC_track1)))
    au18 = pd.concat([au14, au58], ignore_index=True); _w(au18, "aulc_per_repeat_r1_8.csv")
    ct58 = contrasts_x(au58, "5-8"); _w(ct58, "contrasts_r5_8.csv")
    ct18 = contrasts_x(au18[au18.arm.isin(BASE_ARMS)], "1-8"); _w(ct18, "contrasts_r1_8.csv")
    g58 = N.on_grid(c58); q58 = qtt(g58, "BA", "G3_MARGIN", at=(40, 80)); q58["reached"] = np.isfinite(q58.qtt); _w(q58, "qtt_r5_8.csv")
    fid = N.fidelity(t58, preds); _w(fid, "fidelity_vs_week18_caches.csv")
    gc = guard_checks(led, fits, preds); _w(gc, "guard_identity_and_activation.csv")
    th = thresholds_x(led, fits, t58); _w(th, "threshold_mechanism_runs.csv")
    po = path_overlap_x(led); _w(po, "path_overlap.csv")
    figures_x(c58, fits)
    v, dec = verdicts(ct58, ct18, fid, gc, th); _w(v, "hypothesis_verdicts.csv")
    dec["repeats_1_4_AULC_reproduced_max_abs_diff"] = repro
    (OUTX / "decision.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(au58.groupby(["task", "arm"])[["BA_AULC", "q20_AULC"]].mean().round(4))
    print(ct58[ct58.metric.isin(["BA_AULC", "q20_AULC"])].round(4).to_string())
    print(ct18[ct18.metric == "BA_AULC"].round(4).to_string())
    print(v.to_string()); print(json.dumps(dec, indent=1))
    print("fidelity max |dp|:", fid.groupby("arm").max_abs_dp.max().to_dict(), "rows equal:", bool(fid.rows_equal.all()), "n", len(fid), "| r1-4 AULC reproduced:", repro)
    print(gc.to_string())
    return c58, au18, ct58, ct18, fid, gc, th, v, dec


if __name__ == "__main__":
    main()
