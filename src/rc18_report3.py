"""RC18 report part 3 (reads frozen units only; each mode appends one section to report/RESULTS_TABLE.md, so run each once):
    python -m src.rc18_report3 all       # section 11: addendum A4 next to A3 and the final label arm; A4 CSVs; label_curves.png
    python -m src.rc18_report3 d2rules   # section 12: the two pre-registered D2 rules (+ x-independent MEAN-curve diagnostic)
    python -m src.rc18_report3 fcp       # section 13: false confidence as worded in PROTOCOL_20261018 section 5
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_eval as E

REP = RC.CAMP / "report"
from src.rc18_report import md  # noqa: E402  (markdown helper; formatting only)

REPEATS = (5, 6, 7, 8)


def _b0(d, arm):
    """B0..B7 for a label-free-path arm, with the same metric code as rc18_eval.eval_label (which starts at the common B8)."""
    import src.jdl_evaluate as EV
    import src.jdl_stage_m as SMM
    T = C.tasks("NEW", REPEATS); ids = np.asarray(T[0]["ids"]).astype(str); y = np.asarray(T[0]["y"], int)
    sk = np.isin(ids, list(SMM.shortk(SMM.inputs_table()))); U = E._units(d, "NEW"); rows = []
    for r in REPEATS:
        fold = np.zeros(len(ids), int); q20 = np.zeros(len(ids), bool)
        for t in T:
            if t["repeat"] == r:
                fold[t["test"]] = t["fold"]; q20[t["test"]] = t["q20"]
        for b in range(0, C.B0):
            p = np.full(len(ids), np.nan); ok = True
            for t in T:
                if t["repeat"] != r:
                    continue
                u = U.get((None, arm, r, t["fold"])); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                if e is None:
                    ok = False; break
                p[t["test"]] = e["p"]
            if not ok:
                continue
            av = np.isfinite(p); m = EV.wmetrics(np.where(av, p, 0.5), av, y, sk, q20, fold, np.ones((1, len(ids))))
            rows.append({"arm": arm, "repeat": r, "budget": b, **{k: float(v[0]) for k, v in m.items()},
                         "shortK_captured": int(np.sum((np.where(av, p, 0.5) >= 0.5) & sk)), "shortK_total": int(sk.sum())})
    return pd.DataFrame(rows)


def a4(L):
    import src.rc18_physgpc as PG
    A3 = pd.read_csv(REP / "A3_label_endpoints.csv")
    B4 = pd.concat([E.eval_label(PG.D, REPEATS, bmax=40), _b0(PG.D, "PHYS_GPC_MAXIMIN")], ignore_index=True)
    B = pd.concat([A3, B4], ignore_index=True)
    st = []
    for u in E._units(PG.D, "NEW").values():
        for x in u["evals"]:
            st.append({"arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"], "budget": x["budget"], "status": x["status"]})
    S = pd.DataFrame(st); S.to_csv(REP / "A4_gpc_status.csv", index=False, lineterminator="\n")
    fails = S[S.status == "gpc_failed_prior_used"]
    L += ["## 11. Addendum A4 — PHYS_TR prior + NEW-label residual GPC (NEW; exploratory; registered before it ran)", "",
          f"GPC fits: {int((S.status == 'gpc').sum())} succeeded, {len(fails)} failed (prior used at that budget), "
          f"{int((S.status == 'prior_only').sum())} prior-only evaluations (no paid label: PHYS_GPC_MAXIMIN at B0).", "",
          "| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |", "|---|---|---|---|---|---|---|---|---|---|"]
    keep = ["G3_MARGIN", "ACTIVE_E1_STRADDLE", "PHYS_TR_MAXIMIN", "PHYS_TR_MARGIN", "PHYS_GPC_MAXIMIN", "PHYS_GPC_MARGIN"]
    for (a, b), g in B[B.budget.isin([0, 4, 8, 16, 24, 32, 40]) & B.arm.isin(keep)].groupby(["arm", "budget"]):
        L.append(f"| {a} | {b} | {g.BA.mean():.3f} | {g.sensitivity.mean():.3f} | {g.specificity.mean():.3f} | {g.q20.mean():.3f} | "
                 f"{g.shortK_captured.mean():.1f}/{int(g.shortK_total.iloc[0])} | {g.brier.mean():.3f} | {g.log_loss.mean():.3f} | {g.AUC.mean():.3f} |")
    au = B[(B.budget >= 8) & (B.budget <= 40)].groupby(["arm", "repeat"]).BA.mean().unstack(0)
    L += ["", "BA-AULC over B8-B40 per repeat (mean BA), all label arms:", "", md(au.round(3)), ""]
    d = au.sub(au["ACTIVE_E1_STRADDLE"], axis=0).drop(columns="ACTIVE_E1_STRADDLE")
    L += ["Difference to ACTIVE_E1_STRADDLE (the final label arm's best) per repeat:", "", md(d.round(3)), ""]
    B4.to_csv(REP / "A4_label_endpoints.csv", index=False, lineterminator="\n")
    return B


def _us(df):
    df = df.copy(); t = df.quantity == "early peak time"
    df.loc[t, ["curve_err", "scalar_err"]] = df.loc[t, ["curve_err", "scalar_err"]] * 1000.0
    return df


def d2_rules(L):
    """The two pre-registered D2 rules (temporal/TEMPORAL_PHASE_PROTOCOL.md), computed from report/D2_curve_models.csv.
    Per repeat: curve RMSE = sqrt(sum SSE / (sum n_test x 50 blocks)); errors = n_test-weighted mean over the 5 folds."""
    C2 = pd.read_csv(REP / "D2_curve_models.csv"); C2["budget"] = C2["budget"].astype(str); key = ["population", "channel", "model"]
    W = C2[C2.budget == "full"].groupby(key + ["repeat"])[[c for c in C2.columns if c.startswith("sse_")] + ["n_test"]].sum()
    for m in ("KRONn", "PHASE", "PHASE_PCA"):
        W["rmse_" + m] = np.sqrt(W["sse_" + m] / (W.n_test * 50))
    W["win"] = np.minimum(W.rmse_PHASE, W.rmse_PHASE_PCA) <= 0.95 * W.rmse_KRONn
    P = W.groupby(key).agg(repeats_won=("win", "sum"), rmse_KRONn=("rmse_KRONn", "mean"), rmse_PHASE=("rmse_PHASE", "mean"), rmse_PHASE_PCA=("rmse_PHASE_PCA", "mean")).reset_index()
    P["verdict"] = np.where(P.repeats_won >= 3, "PHASE BEATS KRONn", "no")
    L += ["## 12. D2 — the two pre-registered rules (computed; exploratory)", "",
          "**Rule 1 — PHASE BEATS KRONn** (PHASE or PHASE_PCA early-horizon RMSE <= 0.95 x KRONn in >= 3 of 4 repeats, whole pool):", "", md(P.round(4)), ""]
    rows = []
    for (pop, ch, mod, b), g in C2.groupby(key + ["budget"]):
        for r, h in g.groupby("repeat"):
            w = h.n_test.to_numpy(float)
            for cm in ("MEAN", "KRONn", "PHASE", "PHASE_PCA"):
                for q, ce, se in (("early peak time", f"peakms_err_{cm}", "scalar_epeak_ms_abs_err"), ("early peak amplitude", f"peak_err_{cm}", "scalar_epeak_abs_err")):
                    e = float(np.sum(w * h[ce]) / w.sum()); sv = float(np.sum(w * h[se]) / w.sum())
                    rows.append({"population": pop, "channel": ch, "model": mod, "budget": b, "curve_model": cm, "quantity": q, "repeat": r,
                                 "curve_err": e, "scalar_err": sv, "win": e <= 0.95 * sv})
    T2 = pd.DataFrame(rows); T2.to_csv(REP / "D2_rule2_per_repeat.csv", index=False, lineterminator="\n")
    S2 = T2.groupby(["population", "channel", "model", "quantity", "curve_model", "budget"]).agg(repeats_won=("win", "sum"), curve_err=("curve_err", "mean"), scalar_err=("scalar_err", "mean")).reset_index()
    S2["verdict"] = np.where(S2.repeats_won >= 3, "TEMPORAL BEATS SCALAR", "no")
    S2.to_csv(REP / "D2_rule2_summary.csv", index=False, lineterminator="\n")
    k5 = ["population", "channel", "model", "quantity", "budget"]
    mean_meets = S2[S2.curve_model == "MEAN"].set_index(k5).repeats_won >= 3
    S2["MEAN_curve_also_meets"] = [bool(mean_meets.get(tuple(r[k] for k in k5), False)) for _, r in S2.iterrows()]
    S2.to_csv(REP / "D2_rule2_summary.csv", index=False, lineterminator="\n")
    won = S2[(S2.repeats_won >= 3) & (S2.curve_model != "MEAN")]
    inf = won[~won.MEAN_curve_also_meets]
    L += ["**Rule 2 — TEMPORAL BEATS SCALAR** (curve-derived error <= 0.95 x the direct scalar GP error in >= 3 of 4 repeats). The protocol does not single out one curve model "
          "or budget, so every curve model and budget is evaluated (full table: report/D2_rule2_summary.csv). Diagnostic added at reporting time: whether the "
          "x-independent MEAN curve (mean paid curve) also meets the rule in the same cell; if it does, the cell says the scalar GP is poor, not that the curve model learned x-dependence.", "",
          f"Curve-model cells meeting the rule: {len(won)} of {int((S2.curve_model != 'MEAN').sum())}; of these, {int(won.MEAN_curve_also_meets.sum())} are also met by the MEAN curve. "
          "Cells met by a curve model but NOT by the MEAN curve:", "",
          md(_us(inf.drop(columns=["MEAN_curve_also_meets"])).round(3).reset_index(drop=True)) if len(inf) else "(none)", "",
          "Units in this table: µs for peak times; K (temperature) or log nJ (KE) for amplitudes (the CSV keeps ms).", ""]
    return P, S2


def false_conf_protocol(L):
    """False confidence exactly as PROTOCOL_20261018 §5 words it: the share of test runs outside the 90 % observation interval
    at the budget where an arm first claims the level. The claim budget is the learner-side self-R2 stopping rule of
    rc18_report.false_confidence (committed 3cdfc91a before any final result); runs pooled over the 5 folds of a repeat."""
    import src.rc18_report as R1
    FC = pd.read_csv(REP / "false_confidence.csv"); FIN = C.OUT / "final"; rows = []
    for job, pop in (("reg-new-maximin", "NEW"), ("reg-old-maximin", "OLD")):
        U = E._units(FIN / job, pop); Tt = C.targets(pop)
        for _, r in FC[(FC["pop"] == pop) & FC.stopped].iterrows():
            b = int(r.stop_budget); out = n = 0
            for f in (1, 2, 3, 4, 5):
                u = U[(r["model"], "MAXIMIN", int(r["repeat"]), f)]; e = {x["budget"]: x for x in u["evals"]}[b]
                mu, ov = np.asarray(e["pred"][r["target"]][0], float), np.asarray(e["pred"][r["target"]][2], float)
                y = Tt.reindex(u["test_ids"])[r["target"]].to_numpy(float); ok = np.isfinite(y)
                out += int(np.sum(np.abs(y[ok] - mu[ok]) > 1.6448536 * np.sqrt(ov[ok]))); n += int(ok.sum())
            rows.append({"pop": pop, "model": r["model"], "target": r["target"], "repeat": int(r["repeat"]), "claim_budget": b, "share_outside_90": out / n, "n_test": n})
    T = pd.DataFrame(rows); T.to_csv(REP / "false_confidence_protocol.csv", index=False, lineterminator="\n")
    S = T.groupby(["pop", "model"]).agg(trajectories=("share_outside_90", "size"), claim_budget=("claim_budget", "mean"),
                                         share_outside_90_mean=("share_outside_90", "mean"), share_outside_90_max=("share_outside_90", "max")).reset_index()
    L += ["## 13. False confidence as worded in PROTOCOL_20261018 §5 (exploratory)", "",
          "Share of test runs outside the 90 % observation interval at the budget where the arm first claims the level (claim = the learner-side "
          "self-R2 rule of section 5b, committed before any final result). Nominal value 0.10. Section 5b reports a different, trajectory-level "
          "measure (true R2 still below the level at the claim); both are kept.", "", md(S.round(3)), ""]
    return T


def figure(B):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6"})
    COL = {"G3_MARGIN": "#555555", "ACTIVE_E1_STRADDLE": "#0072B2", "ACTIVE_E1_MAXIMIN": "#56B4E9", "TR_E1_STRADDLE": "#E69F00",
           "TR_E1_MAXIMIN": "#F0C987", "PHYS_TR_MAXIMIN": "#D55E00", "PHYS_TR_MARGIN": "#CC79A7",
           "PHYS_GPC_MAXIMIN": "#009E73", "PHYS_GPC_MARGIN": "#004D40"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    for ax, met, lab in zip(axes, ("BA", "AUC", "log_loss"), ("balanced accuracy (p >= 0.5)", "AUC", "log loss (lower is better)")):
        for a, g in B.groupby("arm"):
            m = g.groupby("budget")[met].mean()
            ax.plot(m.index, m.values, color=COL.get(a, "k"), lw=1.7 if ("PHYS" in a or "STRADDLE" in a) else 1.1,
                    ls="--" if a.endswith("MAXIMIN") else "-", label=a)
        ax.set_xlabel("paid NEW simulations"); ax.set_title(lab, fontsize=9.5)
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=5, frameon=False, fontsize=8)
    fig.suptitle("NEW Keyhole label, DEV r5-8 (mean of 4 repeats). PHYS_* use OLD outputs + transferred NEW predictions; "
                 "PHYS_GPC adds a NEW-label residual GPC. Budget 0 = no NEW simulation", x=0.01, ha="left", fontsize=9.5)
    fig.tight_layout(rect=(0, 0.11, 1, 1)); fig.savefig(REP / "label_curves.png", dpi=160); plt.close(fig)


def main():
    RC.limit_threads(1); L = []
    B = a4(L)
    with open(REP / "RESULTS_TABLE.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(L) + "\n")
    figure(B)
    print("\n".join(L))


def main_d2():
    L = []; d2_rules(L)
    with open(REP / "RESULTS_TABLE.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(L) + "\n")
    print("\n".join(L))


def main_fcp():
    L = []; false_conf_protocol(L)
    with open(REP / "RESULTS_TABLE.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    {"all": main, "d2rules": main_d2, "fcp": main_fcp}[sys.argv[1]]()
