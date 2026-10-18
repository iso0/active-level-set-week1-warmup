"""RC18 report part 2: addenda A1-A3 and D2 (reads frozen units; only M0 full-pool references are fitted for target levels).
Appends to report/RESULTS_TABLE.md (section 7+) and writes CSVs/figures.
    python -m src.rc18_report2 all
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_eval as E

REP = RC.CAMP / "report"
FIN = C.OUT / "final"
from src.rc18_report import md  # noqa: E402  (markdown helper; formatting only)


def a1(L):
    import src.rc18_robust as RB
    full = {p: C.full_r2(p, RB.REPEATS) for p in ("NEW", "OLD")}
    R = E.eval_reg(RB.D, ("NEW", "OLD"), RB.REPEATS, full=full)
    d = R[(R["pop"] == "NEW") & R.target.isin(C.PRIMARY["NEW"])]
    a = d[d.model == "M0"].set_index(["target", "repeat"]).budget_to_target; b = d[d.model == "TRSQ"].set_index(["target", "repeat"]).budget_to_target
    S = a - b
    L += ["## 7. Addendum A1 — robustness on DEV repeats 3-4 (exploratory)", "",
          f"NEW, TRSQ vs M0 under MAXIMIN: mean queries saved **{S.mean():.1f}** (per repeat {S.groupby('repeat').mean().round(2).to_dict()}; "
          f"per target {S.groupby('target').mean().round(1).to_dict()}).", "",
          "| pop | model | R2-AULC | budget-to-target | R2 B0 | R2 B8 | R2 B24 |", "|---|---|---|---|---|---|---|"]
    for pop in ("NEW", "OLD"):
        g0 = R[(R["pop"] == pop) & R.target.isin(C.PRIMARY[pop])]
        for m, g in g0.groupby("model"):
            L.append(f"| {pop} | {m} | {g.R2_AULC.mean():.3f} | {g.budget_to_target.mean():.1f} | {g.R2_B0.mean():.3f} | {g.R2_B8.mean():.3f} | {g.R2_B24.mean():.3f} |")
    L.append(""); R.drop(columns=["curve"]).to_csv(REP / "A1_r34_endpoints.csv", index=False, lineterminator="\n")
    return S


def a2(L, full):
    import src.rc18_transfer_design as TD
    A = E.eval_reg(TD.D, ("NEW",), (5, 6, 7, 8), full=full)
    M = E.eval_reg(FIN / "reg-new-maximin", ("NEW",), (5, 6, 7, 8), full=full); M = M[M.model == "TRSQ"].copy(); M["acq"] = "MAXIMIN0"
    R = pd.concat([A, M], ignore_index=True); R = R[R.target.isin(C.PRIMARY["NEW"])].copy()
    R["AULC_0_24"] = [float(np.trapezoid([c[b] for b in range(0, 25)]) / 24) if all(b in c for b in range(25)) else np.nan for c in R.curve]
    R["bt95"] = [E.sustained(c, lev / 0.9 * 0.95, list(range(0, 25, 4)), 28) for c, lev in zip(R.curve, R.level)]
    import src.jdl_physical_pilot as PP
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); hi_share = {}
    for p in TD.D.joinpath("units").glob("*.json.gz"):
        u = RC.read_json_gz(p); hi_share.setdefault(u["acq"], []).append(float(np.mean(W.loc[u["paid_ids"][:8]].ST > 400)))
    for p in (FIN / "reg-new-maximin" / "units").glob("*TRSQ__MAXIMIN.json.gz"):
        u = RC.read_json_gz(p); hi_share.setdefault("MAXIMIN0", []).append(float(np.mean(W.loc[u["paid_ids"][:8]].ST > 400)))
    L += ["## 8. Addendum A2 — which first NEW simulations to buy once transfer exists (TRSQ; exploratory)", "",
          "| design | R2-AULC B0-B24 | R2 B4 | R2 B8 | R2 B16 | R2 B24 | budget to 0.95 x R2_full (cens. 28) | share of first 8 paid with ST > 400 K |", "|---|---|---|---|---|---|---|---|"]
    for a, g in R.groupby("acq"):
        L.append(f"| {a} | {g.AULC_0_24.mean():.3f} | {g.R2_B4.mean():.3f} | {g.R2_B8.mean():.3f} | {g.R2_B16.mean():.3f} | {g.R2_B24.mean():.3f} | {g.bt95.mean():.1f} | "
                 f"{np.mean(hi_share.get(a, [np.nan])):.2f} |")
    pr = R.groupby(["acq", "repeat"]).AULC_0_24.mean().unstack(0)
    L += ["", "Per-repeat R2-AULC B0-B24 (mean of primary targets):", "", md(pr.round(3)), ""]
    R.drop(columns=["curve"]).to_csv(REP / "A2_transfer_design.csv", index=False, lineterminator="\n")
    return R


def a3(L):
    import src.rc18_physlabel as PL
    B1 = E.eval_label(FIN / "label", (5, 6, 7, 8)); B2 = E.eval_label(PL.D, (5, 6, 7, 8), bmax=40)
    # PHYS_TR_MAXIMIN also has B0-B7: evaluate them with the same metric code
    B0 = _label_b0(PL.D)
    B = pd.concat([B1, B2, B0], ignore_index=True)
    L += ["## 9. Addendum A3 — physics-mediated cross-campaign label model vs the final label arm (NEW; exploratory)", "",
          "| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (a, b), g in B[B.budget.isin([0, 4, 8, 16, 24, 40])].groupby(["arm", "budget"]):
        L.append(f"| {a} | {b} | {g.BA.mean():.3f} | {g.sensitivity.mean():.3f} | {g.specificity.mean():.3f} | {g.q20.mean():.3f} | {g.shortK_captured.mean():.1f}/{int(g.shortK_total.iloc[0])} | "
                 f"{g.brier.mean():.3f} | {g.log_loss.mean():.3f} | {g.AUC.mean():.3f} |")
    au = B[(B.budget >= 8) & (B.budget <= 40)].groupby(["arm", "repeat"]).BA.mean().unstack(0)
    L += ["", "BA-AULC over B8-B40 per repeat (mean BA):", "", md(au.round(3)), ""]
    B.to_csv(REP / "A3_label_endpoints.csv", index=False, lineterminator="\n")
    return B


def _label_b0(d):
    import src.jdl_evaluate as EV
    import src.jdl_stage_m as SMM
    T = C.tasks("NEW", (5, 6, 7, 8)); ids = np.asarray(T[0]["ids"]).astype(str); y = np.asarray(T[0]["y"], int)
    sk = np.isin(ids, list(SMM.shortk(SMM.inputs_table()))); U = E._units(d, "NEW"); rows = []
    for r in (5, 6, 7, 8):
        fold = np.zeros(len(ids), int); q20 = np.zeros(len(ids), bool)
        for t in T:
            if t["repeat"] == r:
                fold[t["test"]] = t["fold"]; q20[t["test"]] = t["q20"]
        for b in range(0, 8):
            p = np.full(len(ids), np.nan)
            for t in T:
                if t["repeat"] != r:
                    continue
                u = U.get((None, "PHYS_TR_MAXIMIN", r, t["fold"])); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                if e is not None:
                    p[t["test"]] = e["p"]
            av = np.isfinite(p)
            if not av.any():
                continue
            m = EV.wmetrics(np.where(av, p, 0.5), av, y, sk, q20, fold, np.ones((1, len(ids))))
            rows.append({"arm": "PHYS_TR_MAXIMIN", "repeat": r, "budget": b, **{k: float(v[0]) for k, v in m.items()},
                         "shortK_captured": int(np.sum((np.where(av, p, 0.5) >= 0.5) & sk)), "shortK_total": int(sk.sum())})
    return pd.DataFrame(rows)


def d2(L):
    import src.rc18_gp as G
    import src.rc18_temporal as TP
    rows = []
    for pop in ("NEW", "OLD"):
        F = TP.feature_table(pop); U = E._units(TP.OUT / "final" / "features", pop)
        T = {(t["repeat"], t["fold"]): t for t in C.tasks(pop, TP.D2_REPEATS)}
        # M0 full-pool reference R2 per feature and repeat
        full = {}
        for (r, f), t in T.items():
            ids = np.asarray(t["ids"]).astype(str); Z = C.zstd(t); Y = F.reindex(ids)[TP.FEATS].to_numpy(float)
            fits = C.fit_model("M0", Z, Y, np.asarray(t["pool"]), TP.FEATS)
            for k, c in enumerate(TP.FEATS):
                if fits.get(c) is None:
                    continue
                m = fits[c].predict(t["test"])[0]; yv = Y[t["test"], k]; ok = np.isfinite(yv); full.setdefault((c, r), []).extend(zip(yv[ok], m[ok]))
        ref = {c: float(np.nanmean(F[c])) for c in TP.FEATS}
        r2f = {}
        for (c, r), z in full.items():
            yy, pp = np.array([a for a, _ in z]), np.array([b for _, b in z]); r2f[(c, r)] = 1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref[c]) ** 2)
        for m in sorted({k[0] for k in U}):
            for c in TP.FEATS:
                lev = 0.9 * np.mean([r2f[(c, r)] for r in TP.D2_REPEATS if (c, r) in r2f])
                for r in TP.D2_REPEATS:
                    curve = {}
                    for b in range(0, C.B1 + 1):
                        yy, pp = [], []
                        for f in (1, 2, 3, 4, 5):
                            u = U.get((m, "MAXIMIN", r, f)); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                            if e is None or e["pred"].get(c) is None:
                                break
                            yv = F.reindex(u["test_ids"])[c].to_numpy(float); ok = np.isfinite(yv); yy += list(yv[ok]); pp += list(np.asarray(e["pred"][c][0])[ok])
                        else:
                            yy, pp = np.asarray(yy), np.asarray(pp); curve[b] = float(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref[c]) ** 2))
                    if curve:
                        rows.append({"pop": pop, "model": m, "feature": c, "repeat": r, "R2_full_M0": r2f.get((c, r)), "level": lev,
                                     "budget_to_target": E.sustained(curve, lev, list(range(0, C.B1 + 1, 4)), 64),
                                     **{f"R2_B{b}": curve.get(b) for b in (0, 8, 16, 24, 40, 60)}})
    Fe = pd.DataFrame(rows); Fe.to_csv(REP / "D2_feature_curves.csv", index=False, lineterminator="\n")
    L += ["## 10. D2 — native-time phase features: learning curves on the MAXIMIN design (exploratory)", "",
          "| pop | feature | R2_full M0 | M0 budget-to-target | RICH budget-to-target | M0 R2 B8 | RICH R2 B0 | RICH R2 B8 | M0 R2 B40 | RICH R2 B40 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (pop, c), g in Fe.groupby(["pop", "feature"]):
        a, b = g[g.model == "M0"], g[g.model != "M0"]
        L.append(f"| {pop} | {c} | {a.R2_full_M0.mean():.3f} | {a.budget_to_target.mean():.1f} | {b.budget_to_target.mean():.1f} | {a.R2_B8.mean():.3f} | "
                 f"{b.R2_B0.mean() if b.R2_B0.notna().any() else float('nan'):.3f} | {b.R2_B8.mean():.3f} | {a.R2_B40.mean():.3f} | {b.R2_B40.mean():.3f} |")
    # curve models
    cr = []
    for p in (TP.OUT / "final" / "curves" / "units").glob("*.json.gz"):
        u = RC.read_json_gz(p); cr += u["rows"]
    Cv = pd.DataFrame(cr)
    if not Cv.empty:
        for nm in ("KRONn", "PHASE", "PHASE_PCA"):
            if f"sse_{nm}" in Cv:
                Cv[f"R2c_{nm}"] = 1 - Cv[f"sse_{nm}"] / Cv["sse_MEAN"]
        Cv.to_csv(REP / "D2_curve_models.csv", index=False, lineterminator="\n")
        L += ["", "Native early-horizon curves (0-0.25 ms after onset): R2_curve vs the mean curve and peak errors (mean over folds and repeats):", "",
              "| pop | channel | model | budget | R2c KRONn | R2c PHASE | R2c PHASE_PCA | peak-time err KRONn / PHASE / PCA / scalar (ms) | peak err KRONn / scalar |", "|---|---|---|---|---|---|---|---|---|"]
        for (pop, ch, m, b), g in Cv.groupby(["population", "channel", "model", "budget"]):
            L.append(f"| {pop} | {ch} | {m} | {b} | {g.get('R2c_KRONn', pd.Series([np.nan])).mean():.3f} | {g.get('R2c_PHASE', pd.Series([np.nan])).mean():.3f} | "
                     f"{g.get('R2c_PHASE_PCA', pd.Series([np.nan])).mean():.3f} | {g.peakms_err_KRONn.mean():.4f} / {g.get('peakms_err_PHASE', pd.Series([np.nan])).mean():.4f} / "
                     f"{g.get('peakms_err_PHASE_PCA', pd.Series([np.nan])).mean():.4f} / {g.get('scalar_epeak_ms_abs_err', pd.Series([np.nan])).mean():.4f} | "
                     f"{g.peak_err_KRONn.mean():.3f} / {g.get('scalar_epeak_abs_err', pd.Series([np.nan])).mean():.3f} |")
    L.append("")
    return Fe, Cv


def figures(B=None):
    """Thesis figures: label BA curves (incl. PHYS_TR), primary budget-to-target bars, OLD->NEW transfer scatter."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6"})
    REP.mkdir(parents=True, exist_ok=True)
    if B is not None and len(B):
        COL = {"G3_MARGIN": "#555555", "ACTIVE_E1_STRADDLE": "#0072B2", "ACTIVE_E1_MAXIMIN": "#56B4E9", "TR_E1_STRADDLE": "#E69F00",
               "TR_E1_MAXIMIN": "#F0C987", "PHYS_TR_MAXIMIN": "#D55E00", "PHYS_TR_MARGIN": "#CC79A7"}
        fig, axes = plt.subplots(1, 3, figsize=(14, 3.9))
        for ax, met, lab in zip(axes, ("BA", "AUC", "log_loss"), ("balanced accuracy (p >= 0.5)", "AUC", "log loss (lower is better)")):
            for a, g in B.groupby("arm"):
                m = g.groupby("budget")[met].mean(); ax.plot(m.index, m.values, color=COL.get(a, "k"), lw=1.6 if "PHYS" in a or "STRADDLE" in a else 1.1,
                                                             ls="--" if a.endswith("MAXIMIN") else "-", label=a)
            ax.set_xlabel("paid NEW simulations"); ax.set_title(lab, fontsize=9.5)
        axes[0].legend(frameon=False, fontsize=7.5); fig.suptitle("NEW Keyhole label, DEV r5-8 (mean of 4 repeats): PHYS_TR uses OLD outputs + transferred NEW predictions; budget 0 = no NEW simulation",
                                                                  x=0.01, ha="left", fontsize=10)
        fig.tight_layout(); fig.savefig(REP / "label_curves.png", dpi=160); plt.close(fig)
    P = pd.read_csv(REP / "primary_saved_queries.csv") if (REP / "primary_saved_queries.csv").exists() else None
    R = pd.read_csv(REP / "regression_endpoints.csv") if (REP / "regression_endpoints.csv").exists() else None
    if R is not None:
        d = R[(R["pop"] == "NEW") & (R.acq == "MAXIMIN") & R.target.isin(C.PRIMARY["NEW"])]
        models = ["M0", "M0Q", "SHQ", "TRQ", "TRSQ"]; COLm = {"M0": "#999999", "M0Q": "#56B4E9", "SHQ": "#009E73", "TRQ": "#E69F00", "TRSQ": "#D55E00"}
        tg = C.PRIMARY["NEW"]; x = np.arange(len(tg)); w = 0.16
        fig, ax = plt.subplots(figsize=(11, 3.8))
        for k, m in enumerate(models):
            g = d[d.model == m].groupby("target").budget_to_target; mu = g.mean().reindex(tg); lo = g.min().reindex(tg); hi = g.max().reindex(tg)
            ax.bar(x + (k - 2) * w, mu.values, w * 0.92, color=COLm[m], label=m, yerr=[mu.values - lo.values, hi.values - mu.values], capsize=2, error_kw={"lw": 0.8})
            for xi, v in zip(x + (k - 2) * w, mu.values):
                if v == 0:
                    ax.text(xi, 0.6, "0", ha="center", va="bottom", fontsize=7.5, color=COLm[m], fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels(tg, fontsize=8.5); ax.set_ylabel("NEW simulations to the sustained level\n(mean, range over 4 repeats; 64 = never)")
        ax.legend(frameon=False, ncol=5, fontsize=8); ax.set_title("PRIMARY (DEV r5-8): simulations needed to reach 0.9 x R2_full(M0), MAXIMIN design ('0' = reached with no NEW simulation)", fontsize=10)
        fig.tight_layout(); fig.savefig(REP / "budget_to_target_NEW.png", dpi=160); plt.close(fig)
    # transfer scatter
    Tn = C.targets("NEW"); Em = C.emulator_at(Tn.index); sh = C.qa_short(np.asarray(Tn.index))
    fig, axes = plt.subplots(2, 3, figsize=(12, 7)); axes = axes.ravel()
    for ax, c in zip(axes, C.PRIMARY["NEW"]):
        y, m = Tn[c].to_numpy(float), Em[f"{c}__mu"].to_numpy(float); ok = np.isfinite(y) & np.isfinite(m)
        ax.scatter(m[ok & ~sh], y[ok & ~sh], s=10, color="#0072B2", alpha=0.75, label="NEW run")
        ax.scatter(m[ok & sh], y[ok & sh], s=22, marker="x", color="#D55E00", label="truncated record (Q rule)")
        lo, hi = np.nanmin(np.r_[m[ok], y[ok]]), np.nanmax(np.r_[m[ok], y[ok]]); ax.plot([lo, hi], [lo, hi], color="#999999", lw=0.8)
        r2 = 1 - np.sum((y[ok & ~sh] - m[ok & ~sh]) ** 2) / np.sum((y[ok & ~sh] - y[ok & ~sh].mean()) ** 2)
        ax.set_title(f"{c}  (R2 = {r2:.2f} without truncated records)", fontsize=9); ax.set_xlabel("OLD-campaign emulator prediction"); ax.set_ylabel("NEW observed")
    axes[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("Zero-simulation transfer: a GP fitted on the 405 OLD runs predicts the 136 NEW runs (DEV, descriptive)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "transfer_scatter_NEW.png", dpi=160); plt.close(fig)


def main():
    RC.limit_threads(1); L = []
    full = {"NEW": C.full_r2("NEW", (5, 6, 7, 8))}
    parts = {}
    for name, fn in (("A1", lambda: a1(L)), ("A2", lambda: a2(L, full)), ("A3", lambda: a3(L)), ("D2", lambda: d2(L))):
        try:
            parts[name] = fn()
        except Exception as ex:
            L += [f"## {name}: not available ({type(ex).__name__}: {ex})", ""]
    with open(REP / "RESULTS_TABLE.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(L) + "\n")
    figures(parts.get("A3"))
    print("\n".join(L[:80]))


if __name__ == "__main__":
    {"all": main}[sys.argv[1]]()
