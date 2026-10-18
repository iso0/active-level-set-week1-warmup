"""RC18 final report generator (reads the frozen final units; the only fits are the M0 full-pool references that define the
pre-registered target levels). Writes outputs/research_campaign_20261018/opus/report/:
  RESULTS_TABLE.md / RESULTS_TABLE.csv     the single results table (primary verdict + every exploratory contrast)
  learning curves (PNG), region and label curves, D2 summaries, COSTS.csv, interactive boundary view data (boundary_view.json)
    python -m src.rc18_report all
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_eval as E

FIN = C.OUT / "final"
REP = RC.CAMP / "report"
REPEATS = (5, 6, 7, 8)
GRID = list(range(0, C.B1 + 1, 4))


def _concat_reg(full):
    parts = []
    for job in ("reg-new-maximin", "reg-old-maximin", "reg-designs"):
        d = FIN / job
        if (d / "units").exists():
            pops = ("NEW",) if job == "reg-new-maximin" else (("OLD",) if job == "reg-old-maximin" else ("NEW", "OLD"))
            parts.append(E.eval_reg(d, pops, REPEATS, full=full))
    return pd.concat(parts, ignore_index=True)


def primary(R):
    """NEW, TRSQ vs M0 under MAXIMIN: queries saved to the sustained level over the 6 primary targets x 4 repeats."""
    d = R[(R["pop"] == "NEW") & (R.acq == "MAXIMIN") & R.target.isin(C.PRIMARY["NEW"])]
    a = d[d.model == "M0"].set_index(["target", "repeat"]).budget_to_target
    b = d[d.model == "TRSQ"].set_index(["target", "repeat"]).budget_to_target
    S = (a - b).rename("saved").reset_index()
    per_rep = S.groupby("repeat").saved.mean(); per_t = S.groupby("target").saved.mean(); mean = float(S.saved.mean())
    au = (d[d.model == "TRSQ"].set_index(["target", "repeat"]).R2_AULC - d[d.model == "M0"].set_index(["target", "repeat"]).R2_AULC)
    ok = mean >= 8 and bool((per_rep > 0).all()) and bool((per_t >= -4).all())
    return {"verdict": "FEWER SIMULATIONS (DEV)" if ok else "NOT ESTABLISHED", "mean_saved": mean, "per_repeat": per_rep.round(2).to_dict(),
            "per_target": per_t.round(2).to_dict(), "M0_budget_mean_per_target": a.groupby("target").mean().round(1).to_dict(),
            "TRSQ_budget_mean_per_target": b.groupby("target").mean().round(1).to_dict(), "R2_AULC_diff_mean": float(au.mean()),
            "R2_AULC_diff_per_repeat": au.groupby("repeat").mean().round(4).to_dict(), "table": S}


def contrast(R, pop, targets, m1, a1, m2, a2, metric):
    d = R[(R["pop"] == pop) & R.target.isin(targets)]
    x = d[(d.model == m1) & (d.acq == a1)].set_index(["target", "repeat"])[metric]
    y = d[(d.model == m2) & (d.acq == a2)].set_index(["target", "repeat"])[metric]
    z = (x - y).dropna(); pr = z.groupby("repeat").mean()
    return {"mean": float(z.mean()), "per_repeat": [round(float(v), 4) for v in pr.values], "min_rep": float(pr.min()), "max_rep": float(pr.max()),
            "positive_repeats": int((pr > 0).sum()), "n": int(len(z))}


def reg_section(R, L):
    P = primary(R)
    L += ["## 1. PRIMARY — NEW physical outputs, model effect under the identical MAXIMIN design (TRSQ vs M0)", "",
          f"**Verdict: {P['verdict']}.** Mean queries saved to the sustained target level: **{P['mean_saved']:.1f}** "
          f"(per repeat {P['per_repeat']}). R²-AULC difference {P['R2_AULC_diff_mean']:+.3f} (per repeat {P['R2_AULC_diff_per_repeat']}).", "",
          "| target | M0 budget-to-target (mean of 4 repeats) | TRSQ budget-to-target | saved |", "|---|---|---|---|"]
    for t in C.PRIMARY["NEW"]:
        L.append(f"| {t} | {P['M0_budget_mean_per_target'].get(t)} | {P['TRSQ_budget_mean_per_target'].get(t)} | {P['per_target'].get(t)} |")
    L += ["", "Rule: FEWER SIMULATIONS (DEV) iff mean saved >= 8, every repeat mean > 0, no target mean < -4 (PROTOCOL_20261018 §5).", ""]
    rows = []
    def add(name, pop, tg, m1, a1, m2, a2):
        for met in ("R2_AULC", "budget_to_target"):
            c = contrast(R, pop, tg, m1, a1, m2, a2, met); rows.append({"contrast": name, "population": pop, "metric": met, **c})
    NP, OP = C.PRIMARY["NEW"], C.PRIMARY["OLD"]
    add("E1 QA (M0Q - M0), MAXIMIN", "NEW", NP, "M0Q", "MAXIMIN", "M0", "MAXIMIN")
    add("E1 sharing (SHQ - M0Q), MAXIMIN", "NEW", NP, "SHQ", "MAXIMIN", "M0Q", "MAXIMIN")
    add("E1 transfer (TRQ - M0Q), MAXIMIN", "NEW", NP, "TRQ", "MAXIMIN", "M0Q", "MAXIMIN")
    add("E1 sharing given transfer (TRSQ - TRQ)", "NEW", NP, "TRSQ", "MAXIMIN", "TRQ", "MAXIMIN")
    add("E2 OLD rich (SHQ - M0), MAXIMIN", "OLD", OP, "SHQ", "MAXIMIN", "M0", "MAXIMIN")
    for pop, rich, tg in (("NEW", "TRSQ", NP), ("OLD", "SHQ", OP)):
        for m in ("M0", rich):
            add(f"E3 acquisition MOIVR - MAXIMIN ({m})", pop, tg, m, "MOIVR", m, "MAXIMIN")
            add(f"E3 design RANDOM - MAXIMIN ({m})", pop, tg, m, "RANDOM", m, "MAXIMIN")
        add(f"E3 rich vs simple under MOIVR ({rich} - M0)", pop, tg, rich, "MOIVR", "M0", "MOIVR")
    T = pd.DataFrame(rows)
    L += ["## 2. Exploratory regression contrasts (no correction; all 4 per-repeat values shown)", "",
          "| contrast | pop | metric | mean | per-repeat | positive repeats |", "|---|---|---|---|---|---|"]
    for _, r in T.iterrows():
        L.append(f"| {r.contrast} | {r.population} | {r.metric} | {r['mean']:+.3f} | {r.per_repeat} | {r.positive_repeats}/4 |")
    # calibration
    L += ["", "**E4 calibration** (mean over primary targets and repeats, MAXIMIN design):", "", "| pop | model | cov90 B8 | cov90 B24 | NLPD B24 | R2 B0 | R2 B8 | R2 B24 | R2 B60 |", "|---|---|---|---|---|---|---|---|---|"]
    for pop in ("NEW", "OLD"):
        d = R[(R["pop"] == pop) & (R.acq == "MAXIMIN") & R.target.isin(C.PRIMARY[pop])]
        for m, g in d.groupby("model"):
            L.append(f"| {pop} | {m} | {g.cov90_B8.mean():.3f} | {g.cov90_B24.mean():.3f} | {g.nlpd_B24.mean():.3f} | {g.R2_B0.mean():.3f} | {g.R2_B8.mean():.3f} | {g.R2_B24.mean():.3f} | {g.R2_B60.mean():.3f} |")
    L.append("")
    return P, T


def region_section(L):
    G = E.eval_region(FIN / "region", ("NEW", "OLD"), REPEATS)
    L += ["## 3. Region learning: {velocity spike log-ratio >= log 2} (exploratory)", "",
          "| pop | model | acquisition | BA-AULC | budget-to-target (cens. 44) | BA B8 | BA B16 | BA B24 | BA B40 | band share paid | minority side paid B40 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (pop, m, a), g in G.groupby(["pop", "model", "acq"]):
        L.append(f"| {pop} | {m} | {a} | {g.BA_AULC.mean():.3f} | {g.budget_to_target.mean():.1f} | {g.BA_B8.mean():.3f} | {g.BA_B16.mean():.3f} | {g.BA_B24.mean():.3f} | "
                 f"{g.BA_B40.mean():.3f} | {g.band_share_paid.mean():.3f} | {g.minority_paid_share_B40.mean():.3f} |")
    rows = []
    for pop in ("NEW", "OLD"):
        rich = C.RICH[pop]
        for nm, (m1, a1, m2, a2) in {"(a) STRADDLE - MAXIMIN, M0": ("M0", "STRADDLE", "M0", "MAXIMIN"), f"(a) STRADDLE - MAXIMIN, {rich}": (rich, "STRADDLE", rich, "MAXIMIN"),
                                     "(a) TRUVAR - STRADDLE, M0": ("M0", "TRUVAR", "M0", "STRADDLE"), f"(a) TRUVAR - STRADDLE, {rich}": (rich, "TRUVAR", rich, "STRADDLE"),
                                     f"(b) {rich} - M0 under STRADDLE": (rich, "STRADDLE", "M0", "STRADDLE"), f"(b) {rich} - M0 under MAXIMIN": (rich, "MAXIMIN", "M0", "MAXIMIN"),
                                     "(c) local on - off (ASTRA), M0": ("M0", "ASTRA_SURPRISE", "M0", "ASTRA_STRADDLE_GLOBAL"),
                                     f"(c) local on - off (ASTRA), {rich}": (rich, "ASTRA_SURPRISE", rich, "ASTRA_STRADDLE_GLOBAL")}.items():
            for met in ("BA_AULC", "budget_to_target", "band_share_paid"):
                x = G[(G["pop"] == pop) & (G.model == m1) & (G.acq == a1)].set_index("repeat")[met]
                y = G[(G["pop"] == pop) & (G.model == m2) & (G.acq == a2)].set_index("repeat")[met]
                z = (x - y).dropna(); rows.append({"population": pop, "contrast": nm, "metric": met, "mean": float(z.mean()), "per_repeat": [round(float(v), 4) for v in z.values],
                                                   "positive_repeats": int((z > 0).sum())})
    T = pd.DataFrame(rows)
    L += ["", "| pop | contrast | metric | mean | per-repeat | positive repeats |", "|---|---|---|---|---|---|"]
    for _, r in T.iterrows():
        L.append(f"| {r.population} | {r.contrast} | {r.metric} | {r['mean']:+.3f} | {r.per_repeat} | {r.positive_repeats}/4 |")
    L.append("")
    return G, T


def label_section(L):
    B = E.eval_label(FIN / "label", REPEATS)
    L += ["## 4. Keyhole label arm (NEW; exploratory)", "", "| arm | budget | BA | sensitivity | specificity | q20 | short-K captured/total | Brier | log loss | AUC |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (a, b), g in B[B.budget.isin([8, 16, 24, 40])].groupby(["arm", "budget"]):
        L.append(f"| {a} | {b} | {g.BA.mean():.3f} | {g.sensitivity.mean():.3f} | {g.specificity.mean():.3f} | {g.q20.mean():.3f} | {g.shortK_captured.mean():.1f}/{int(g.shortK_total.iloc[0])} | "
                 f"{g.brier.mean():.3f} | {g.log_loss.mean():.3f} | {g.AUC.mean():.3f} |")
    au = B[(B.budget >= 8) & (B.budget <= 40)].groupby(["arm", "repeat"]).BA.mean().unstack(0)
    L += ["", "BA-AULC (mean BA over B8-B40) per repeat:", "", au.round(3).to_markdown() if hasattr(au, "to_markdown") else au.round(3).to_string(), ""]
    return B


def costs(L):
    rows = []
    for job in ("reg-new-maximin", "reg-old-maximin", "reg-designs", "region", "label"):
        for p in (FIN / job / "units").glob("*.json.gz"):
            u = RC.read_json_gz(p); rows.append({"job": job, "population": u["population"], "model": u.get("model"), "acq": u.get("acq", u.get("arm")),
                                                 "seconds": u["seconds"], "paid": len(u["paid_ids"])})
    Cst = pd.DataFrame(rows); REP.mkdir(parents=True, exist_ok=True); Cst.to_csv(REP / "COSTS.csv", index=False, lineterminator="\n")
    s = Cst.groupby(["job", "population", "model", "acq"]).agg(trajectories=("seconds", "size"), cpu_s_mean=("seconds", "mean"), cpu_s_total=("seconds", "sum"),
                                                                 simulations=("paid", "mean")).round(2)
    L += ["## 6. Cost breakdown", "", "Simulation cost = paid queries (one simulation yields every monitor output; counted once). Output reading: 0.84 s per "
          "simulation (all channels, RC18 extraction). Modelling CPU per trajectory below; the OLD emulators were a one-off 5 s on historical runs.", "",
          s.to_markdown() if hasattr(s, "to_markdown") else s.to_string(), "", f"Total modelling CPU of the final programme: {Cst.seconds.sum() / 3600:.2f} h.", ""]
    return Cst


def curves_figure(R):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    COL = {"M0": "#999999", "M0Q": "#56B4E9", "SHQ": "#009E73", "TRQ": "#E69F00", "TRSQ": "#D55E00"}
    for pop in ("NEW", "OLD"):
        tg = C.PRIMARY[pop]; d = R[(R["pop"] == pop) & (R.acq == "MAXIMIN")]
        fig, axes = plt.subplots(2, 4, figsize=(14, 6.4), sharex=True); axes = axes.ravel()
        for ax, t in zip(axes, tg):
            for m, g in d[d.target == t].groupby("model"):
                cur = [g_ for g_ in g.curve]; bs = sorted(set().union(*[c.keys() for c in cur])); bs = [b for b in bs if all(b in c for c in cur)]
                M = np.array([[c[b] for b in bs] for c in cur]); ax.plot(bs, M.mean(0), color=COL.get(m, "k"), lw=1.6, label=m)
                ax.fill_between(bs, M.min(0), M.max(0), color=COL.get(m, "k"), alpha=0.12, lw=0)
            lev = d[d.target == t].level.iloc[0]; ax.axhline(lev, color="#CC79A7", ls=":", lw=1)
            ax.set_title(t, fontsize=9.5); ax.set_ylim(max(-0.3, ax.get_ylim()[0]), 1.0); ax.grid(True, color="#e6e6e6")
        for ax in axes[len(tg):]:
            ax.axis("off")
        axes[0].legend(frameon=False, fontsize=8)
        fig.suptitle(f"RC18 final (DEV r5-8): out-of-fold R2 vs paid simulations, MAXIMIN design, {pop} (line = mean of 4 repeats, band = range; dotted = target level)",
                     x=0.01, ha="left", fontsize=10.5)
        fig.tight_layout(); REP.mkdir(parents=True, exist_ok=True); fig.savefig(REP / f"learning_curves_{pop}.png", dpi=160); plt.close(fig)


def region_figure(G):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    COL = {"MAXIMIN": "#000000", "RANDOM": "#999999", "STRADDLE": "#0072B2", "TRUVAR": "#E69F00", "ASTRA_SURPRISE": "#D55E00", "ASTRA_STRADDLE_GLOBAL": "#009E73"}
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
    for ax, (pop, m) in zip(axes, [("OLD", "M0"), ("OLD", "SHQ"), ("NEW", "M0"), ("NEW", "TRSQ")]):
        for a, g in G[(G["pop"] == pop) & (G.model == m)].groupby("acq"):
            cur = list(g.curve); bs = sorted(cur[0]); M = np.array([[c[b] for b in bs] for c in cur])
            ax.plot(bs, M.mean(0), color=COL[a], lw=1.5, ls="--" if a == "MAXIMIN" else "-", label=a)
        ax.set_title(f"{pop}, model {m}", fontsize=9.5); ax.grid(True, color="#e6e6e6"); ax.set_xlabel("paid simulations")
    axes[0].set_ylabel("region BA on test (mean of 4 repeats)"); axes[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("RC18 final: learning the velocity-spike region {spike log-ratio >= log 2}", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "region_curves.png", dpi=160); plt.close(fig)


def boundary_view(pop="OLD", repeat=5):
    """Data for the interactive boundary view: every run of the population is a test point exactly once per repeat."""
    import src.jdl_physical_pilot as PP
    Tt = C.targets(pop); W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); U = E._units(FIN / "region", pop)
    T = {t["fold"]: t for t in C.tasks(pop, (repeat,))}; ids = np.asarray(T[1]["ids"]).astype(str)
    w = W.loc[ids]; logh = np.log(w.P) - 0.5 * np.log(w.VX) - 1.5 * np.log(w.LS_um_radius * 1e-6)
    y = Tt.reindex(ids)["vmax_spike_logratio"].to_numpy(float)
    out = {"population": pop, "repeat": repeat, "tau": C.SPIKE_TAU, "ids": ids.tolist(), "logh": np.round(logh.to_numpy(), 4).tolist(),
           "logVX": np.round(np.log(w.VX.to_numpy()), 4).tolist(), "truth": [None if not np.isfinite(v) else round(float(v), 4) for v in y], "arms": {}}
    pos = {s: i for i, s in enumerate(ids)}
    for (m, a, r, f), u in U.items():
        if r != repeat:
            continue
        key = f"{m}|{a}"; A = out["arms"].setdefault(key, {"pred": {}, "paid": {}})
        for e in u["evals"]:
            b = e["budget"]; P = A["pred"].setdefault(str(b), [None] * len(ids))
            for s, v in zip(u["test_ids"], e["mean"]):
                P[pos[s]] = round(float(v), 4)
        A["paid"][str(f)] = [pos[s] for s in u["paid_ids"]]
    REP.mkdir(parents=True, exist_ok=True); (REP / "boundary_view.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def main():
    RC.limit_threads(1); REP.mkdir(parents=True, exist_ok=True)
    full = {p: C.full_r2(p, REPEATS) for p in ("NEW", "OLD")}
    L = ["# RC18 final programme — single results table (DEV; final repeats 5-8; frozen protocol PROTOCOL_20261018.md)", "",
         "Every number below is computed by `src/rc18_report.py` from the frozen final units (manifest main/final/RC18_FINAL_MANIFEST.json). "
         "DEV evidence on previously inspected simulations; no C3/C4/Stage A.", ""]
    R = _concat_reg(full); P, T = reg_section(R, L)
    G, TG = region_section(L) if (FIN / "region" / "units").exists() else (None, None)
    B = label_section(L) if (FIN / "label" / "units").exists() else None
    Cst = costs(L)
    R.drop(columns=["curve"]).to_csv(REP / "regression_endpoints.csv", index=False, lineterminator="\n")
    T.to_csv(REP / "regression_contrasts.csv", index=False, lineterminator="\n"); P["table"].to_csv(REP / "primary_saved_queries.csv", index=False, lineterminator="\n")
    if G is not None:
        G.drop(columns=["curve"]).to_csv(REP / "region_endpoints.csv", index=False, lineterminator="\n"); TG.to_csv(REP / "region_contrasts.csv", index=False, lineterminator="\n")
        region_figure(G); boundary_view()
    if B is not None:
        B.to_csv(REP / "label_endpoints.csv", index=False, lineterminator="\n")
    curves_figure(R)
    (REP / "RESULTS_TABLE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({k: v for k, v in P.items() if k != "table"}, open(REP / "PRIMARY.json", "w"), indent=1, default=str)
    print("\n".join(L[:30]))


if __name__ == "__main__":
    {"all": main}[sys.argv[1]]()
