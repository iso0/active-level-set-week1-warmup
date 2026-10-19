"""RC19 report generator (pooled from scratch). Reads the frozen final units only; computes the three pre-registered primaries
of PROTOCOL_RC19.md and every exploratory table. Committed before any final outcome is read.
    python -m src.rc19_report all          -> opus_pooled/report/RESULTS_TABLE.md, CSVs, figures
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

REP = P.OUT / "report"
FIN = P.OUT / "final"


def md(df, digits=3):
    df = df.copy()
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join((f"{v:.{digits}f}" if isinstance(v, (float, np.floating)) and np.isfinite(v) else ("–" if isinstance(v, (float, np.floating)) else str(v))) for v in r.values) + " |")
    return "\n".join(out)


def verdict(delta_by_repeat, margin):
    """BETTER iff mean >= margin and Delta > 0 in >= F.MIN_POSITIVE of the 8 repeats; WORSE iff mean <= -margin and Delta < 0 in
    >= F.MIN_POSITIVE repeats; else NOT DIFFERENT."""
    d = np.asarray(list(delta_by_repeat.values()), float); m = float(np.mean(d))
    if len(d) < len(P.FINAL_REPEATS):
        return f"INCOMPLETE ({len(d)} of {len(P.FINAL_REPEATS)} repeats)", m
    if m >= margin and np.sum(d > 0) >= F.MIN_POSITIVE:
        return "BETTER (DEV)", m
    if m <= -margin and np.sum(d < 0) >= F.MIN_POSITIVE:
        return "WORSE (DEV)", m
    return "NOT DIFFERENT (DEV; within the practical margin or not consistent across repeats)", m


def paired(T, key_a, key_b, col, by="repeat"):
    a = T[key_a].groupby(by)[col].mean(); b = T[key_b].groupby(by)[col].mean(); return (a - b).dropna().to_dict()


# ======================================================================================== regression
def regression(L, M):
    U = EV.load_units(FIN / "final-reg"); R = EV.reg_curves(U, M); R.to_csv(REP / "reg_curves.csv", index=False, lineterminator="\n")
    PT = list(F.PRIMARY_TARGETS); R = R[R.budget >= P.B0]
    A = R[R.target.isin(PT)].groupby(["model", "acq", "repeat"]).R2.mean().rename("AULC").reset_index()          # mean over budgets and primary targets
    E = EV.reg_endpoints(R, F.LEVELS, PT); E.to_csv(REP / "reg_endpoints.csv", index=False, lineterminator="\n")
    sel = lambda m, a: (A.model == m) & (A.acq == a)
    d = paired(A, sel("SHQ", "MAXIMIN"), sel("M0", "MAXIMIN"), "AULC"); v, mean = verdict(d, F.MARGIN["reg"])
    L += ["## A. Physical outputs (pooled, from scratch)", "", f"**PRIMARY A — SHQ vs M0, matched MAXIMIN, R²-AULC over B{P.B0}–B{F.H['reg']} (mean over the primary outputs): {v}**",
          f"Δ per repeat: {json.dumps({int(k): round(x, 4) for k, x in d.items()})}; mean {mean:+.4f}; practical margin {F.MARGIN['reg']}.", ""]
    rows = []
    for name, (ma, aa), (mb, ab) in (("quality: M0Q − M0", ("M0Q", "MAXIMIN"), ("M0", "MAXIMIN")), ("sharing: SHQ − M0Q", ("SHQ", "MAXIMIN"), ("M0Q", "MAXIMIN")),
                                     ("MOIVR − MAXIMIN given SHQ", ("SHQ", "MOIVR"), ("SHQ", "MAXIMIN")), ("RANDOM − MAXIMIN given SHQ", ("SHQ", "RANDOM"), ("SHQ", "MAXIMIN")),
                                     ("MOIVR − MAXIMIN given M0Q", ("M0Q", "MOIVR"), ("M0Q", "MAXIMIN")), ("RANDOM − MAXIMIN given M0Q", ("M0Q", "RANDOM"), ("M0Q", "MAXIMIN")),
                                     ("SHQ − M0Q given MOIVR", ("SHQ", "MOIVR"), ("M0Q", "MOIVR"))):
        if not (sel(ma, aa).any() and sel(mb, ab).any()):
            continue
        dd = paired(A, sel(ma, aa), sel(mb, ab), "AULC"); rows.append({"contrast": name, "mean": float(np.mean(list(dd.values()))),
                                                                     "per_repeat": json.dumps({int(k): round(x, 4) for k, x in dd.items()}), "positive_repeats": f"{sum(x > 0 for x in dd.values())}/{len(dd)}"})
    L += ["Exploratory contrasts (R²-AULC, mean over primary outputs; all repeats shown):", "", md(pd.DataFrame(rows), 4), ""]
    J = E[E.target == "JOINT"].copy(); J["status"] = np.where(J.censored, "not reached by B" + J.horizon.astype(str), "confirmed")
    S = J.groupby(["model", "acq"]).agg(completed=("censored", lambda s: f"{int((~s).sum())}/{len(s)}"), first_qualifying=("first", lambda s: ",".join("–" if pd.isna(x) else str(int(x)) for x in s)),
                                       confirmed=("confirmed", lambda s: ",".join("–" if pd.isna(x) else str(int(x)) for x in s))).reset_index()
    L += [f"Joint campaign endpoint (all primary outputs at their absolute levels {json.dumps(F.LEVELS)} simultaneously; confirmed = also at b+4; per repeat; '–' = not reached, censored):", "", md(S), ""]
    P1 = E[E.target != "JOINT"].groupby(["model", "acq", "target"]).agg(completed=("censored", lambda s: f"{int((~s).sum())}/{len(s)}"),
                                                                      confirmed=("confirmed", lambda s: ",".join("–" if pd.isna(x) else str(int(x)) for x in s)), AULC=("AULC", "mean")).reset_index()
    L += ["Per-output endpoints (confirmed budget per repeat; '–' = censored at the horizon):", "", md(P1), ""]
    C = R[R.target.isin(PT) & R.budget.isin([16, 40, F.H["reg"]])].groupby(["model", "acq", "budget"])[["R2", "cov90", "nlpd"]].mean().reset_index()
    L += ["Accuracy and calibration at matched budgets (mean over primary outputs and repeats):", "", md(C), ""]
    A.to_csv(REP / "reg_aulc.csv", index=False, lineterminator="\n")
    return R, E


# ======================================================================================== region
def region(L, M):
    U = EV.load_units(FIN / "final-region"); G = EV.region_curves(U, M, F.TAU); G.to_csv(REP / "region_curves.csv", index=False, lineterminator="\n")
    Cl = EV.region_collection(U, M, F.TAU); Cl.to_csv(REP / "region_collection.csv", index=False, lineterminator="\n")
    A = G[G.budget >= P.B0].groupby(["model", "acq", "repeat"]).BA.mean().rename("AULC").reset_index()
    sel = lambda m, a: (A.model == m) & (A.acq == a)
    d = paired(A, sel("SHQ", "STRADDLE"), sel("SHQ", "MAXIMIN"), "AULC"); v, mean = verdict(d, F.MARGIN["region"])
    L += ["## B. Velocity-spike region {spike log-ratio ≥ log 2} (pooled, from scratch)", "",
          f"**PRIMARY B — STRADDLE vs MAXIMIN under SHQ, BA-AULC over B{P.B0}–B{F.H['region']}: {v}**",
          f"Δ per repeat: {json.dumps({int(k): round(x, 4) for k, x in d.items()})}; mean {mean:+.4f}; practical margin {F.MARGIN['region']}.", ""]
    rows = []
    for name, (ma, aa), (mb, ab) in (("same model SHQ: TRUVAR − STRADDLE", ("SHQ", "TRUVAR"), ("SHQ", "STRADDLE")), ("same model SHQ: RANDOM − MAXIMIN", ("SHQ", "RANDOM"), ("SHQ", "MAXIMIN")),
                                     ("same model M0: STRADDLE − MAXIMIN", ("M0", "STRADDLE"), ("M0", "MAXIMIN")), ("same model M0: TRUVAR − STRADDLE", ("M0", "TRUVAR"), ("M0", "STRADDLE")),
                                     ("same selector STRADDLE: SHQ − M0", ("SHQ", "STRADDLE"), ("M0", "STRADDLE")), ("same selector MAXIMIN: SHQ − M0", ("SHQ", "MAXIMIN"), ("M0", "MAXIMIN"))):
        dd = paired(A, sel(ma, aa), sel(mb, ab), "AULC"); rows.append({"contrast": name, "mean": float(np.mean(list(dd.values()))),
                                                                     "per_repeat": json.dumps({int(k): round(x, 4) for k, x in dd.items()}), "positive_repeats": f"{sum(x > 0 for x in dd.values())}/{len(dd)}"})
    L += ["Exploratory contrasts (BA-AULC):", "", md(pd.DataFrame(rows), 4), ""]
    E = []
    for (m, a, r), g in G.groupby(["model", "acq", "repeat"]):
        E.append({"model": m, "acq": a, "repeat": r, **EV.endpoint(dict(zip(g.budget, g.BA)), F.BA_LEVEL["region"])})
    E = pd.DataFrame(E)
    T = G[G.budget.isin([16, 24, 40, F.H["region"]])].groupby(["model", "acq", "budget"])[["BA", "recall_in", "recall_out"]].mean().reset_index()
    coll = Cl.groupby(["model", "acq"])[["band_share_paid", "in_region_paid_share", "invalid_paid_share"]].mean().reset_index()
    ES = E.groupby(["model", "acq"]).agg(completed=("censored", lambda s: f"{int((~s).sum())}/{len(s)}"), confirmed=("confirmed", lambda s: ",".join("–" if pd.isna(x) else str(int(x)) for x in s))).reset_index()
    L += ["Both recalls at matched budgets (mean over repeats):", "", md(T), "",
          f"Queries to BA ≥ {F.BA_LEVEL['region']} (confirmed: BA ≥ level at b and at b+4; per repeat; '–' = censored at the horizon):", "", md(ES), "",
          "Collection (where the post-startup paid runs fall; paid truth) — collection is not learning:", "", md(coll), ""]
    A.to_csv(REP / "region_aulc.csv", index=False, lineterminator="\n")
    return G


# ======================================================================================== label
def label(L, M):
    U = EV.load_units(FIN / "final-label"); B = EV.label_metrics(U, M); B.to_csv(REP / "label_metrics.csv", index=False, lineterminator="\n")
    A = B[B.budget >= P.B0].groupby(["arm", "repeat"]).agg(AULC=("BA", "mean"), LL=("log_loss", "mean")).reset_index()
    sel = lambda a: A.arm == a
    d = paired(A, sel(F.PRIMARY_C[0]), sel(F.PRIMARY_C[1]), "AULC"); v, mean = verdict(d, F.MARGIN["label"])
    L += ["## C. Keyhole label (pooled, from scratch)", "", f"**PRIMARY C — {F.PRIMARY_C[0]} vs {F.PRIMARY_C[1]}, BA-AULC over B{P.B0}–B{F.H['label']}: {v}**",
          f"Δ per repeat: {json.dumps({int(k): round(x, 4) for k, x in d.items()})}; mean {mean:+.4f}; practical margin {F.MARGIN['label']}.", ""]
    rows = []
    for a in sorted(set(B.arm)):
        for ref in (F.PRIMARY_C[1], "G3_MARGIN"):
            if a == ref:
                continue
            dd = paired(A, sel(a), sel(ref), "AULC"); dl = paired(A, sel(a), sel(ref), "LL")
            rows.append({"arm": a, "vs": ref, "dBA_AULC": float(np.mean(list(dd.values()))), "BA_positive_repeats": f"{sum(x > 0 for x in dd.values())}/{len(dd)}",
                         "dLogLoss": float(np.mean(list(dl.values()))), "LL_lower_repeats": f"{sum(x < 0 for x in dl.values())}/{len(dl)}"})
    L += ["Exploratory paired contrasts (BA-AULC and mean log loss over B8–B60):", "", md(pd.DataFrame(rows), 4), ""]
    cols = ["BA", "sensitivity", "specificity", "AUC", "brier", "log_loss", "q20_BA", "shortK_pooled_captured", "shortK_pooled_total", "shortK_NEW_captured", "shortK_NEW_total",
            "BA_OLD", "spec_NEW", "sens_NEW", "one_class_folds", "failed_fits"]
    T = B[B.budget.isin([8, 16, 24, 40, F.H["label"]])].groupby(["arm", "budget"])[cols].mean().reset_index()
    E = []
    for (a, r), g in B.groupby(["arm", "repeat"]):
        E.append({"arm": a, "repeat": r, **EV.endpoint(dict(zip(g.budget, g.BA)), F.BA_LEVEL["label"], step=4)})
    ES = pd.DataFrame(E).groupby("arm").agg(completed=("censored", lambda s: f"{int((~s).sum())}/{len(s)}"), confirmed=("confirmed", lambda s: ",".join("–" if pd.isna(x) else str(int(x)) for x in s))).reset_index()
    L += ["Matched budgets (mean over repeats). spec_NEW = conduction recall on the NEW-batch test runs (the fast-scan corner; evaluator-only diagnostic):", "", md(T), "",
          f"Queries to BA ≥ {F.BA_LEVEL['label']} (confirmed: BA ≥ level at b and at b+4; per repeat; '–' = censored):", "", md(ES), ""]
    A.to_csv(REP / "label_aulc.csv", index=False, lineterminator="\n")
    return B


def temporal(L, M):
    """Bounded D: early-horizon (0-0.25 ms after onset) peak amplitude of KE (log) and of max temperature; curve-derived
    (KRONn / PHASE / PHASE_PCA) vs the direct scalar GP (M0Q) of the same endpoint vs the x-independent MEAN curve."""
    rows = [dict(r, repeat=u["repeat"]) for u in EV.load_units(FIN / "final-temporal") for r in u["rows"]]
    T = pd.DataFrame(rows); T.to_csv(REP / "temporal_rows.csv", index=False, lineterminator="\n")
    out = []
    for (ch, b, r), g in T.groupby(["channel", "budget", "repeat"]):
        w = g.n_test.to_numpy(float); e = lambda c: float(np.sum(w * g[c]) / w.sum()) if c in g and g[c].notna().all() else np.nan
        out.append({"channel": ch, "budget": b, "repeat": r, "KRONn": e("peak_err_KRONn"), "PHASE": e("peak_err_PHASE"), "PHASE_PCA": e("peak_err_PHASE_PCA"),
                    "MEAN": e("peak_err_MEAN"), "scalar": e("scalar_epeak_abs_err")})
    E = pd.DataFrame(out); E.to_csv(REP / "temporal_peak_errors.csv", index=False, lineterminator="\n")
    V = []
    for (ch, b), g in E.groupby(["channel", "budget"]):
        for cm in ("KRONn", "PHASE", "PHASE_PCA"):
            win = (g[cm] <= 0.95 * g.scalar) & (g[cm] <= 0.95 * g.MEAN)
            V.append({"channel": ch, "budget": b, "curve_model": cm, "repeats_won": int(win.sum()), "curve_err": float(g[cm].mean()), "scalar_err": float(g.scalar.mean()),
                      "mean_curve_err": float(g.MEAN.mean()), "verdict": "TEMPORAL BEATS SCALAR (DEV)" if win.sum() >= F.MIN_POSITIVE else "no"})
    L += ["## D. Time structure (bounded; exploratory)", "",
          "Endpoint: early-horizon peak amplitude (0–0.25 ms after the run's own onset; log nJ for KE, K for temperature), MAXIMIN paid path, M0Q. "
          "Rule: a curve model beats the scalar GP iff its error ≤ 0.95 × the scalar GP error AND ≤ 0.95 × the x-independent mean-curve error in ≥ 7 of 8 repeats. "
          "This is an early-horizon endpoint, not the full trajectory.", "", md(pd.DataFrame(V), 4), ""]


def costs(L):
    rows = []
    for job in ("final-reg", "final-region", "final-label", "final-temporal"):
        for p in sorted((FIN / job / "units").glob("*.json.gz")):
            u = RC.read_json_gz(p); rows.append({"job": job, "arm": u.get("model", u.get("arm")), "design": u.get("acq", ""), "seconds": u.get("seconds", np.nan), "queries": u.get("queries")})
    Cs = pd.DataFrame(rows, columns=["job", "arm", "design", "seconds", "queries"]); Cs.to_csv(REP / "costs_units.csv", index=False, lineterminator="\n")
    if Cs.empty:
        L += ["## Costs", "", "*(no final units yet)*", ""]; return
    S = Cs.groupby(["job", "arm", "design"]).agg(trajectories=("seconds", "size"), cpu_s_mean=("seconds", "mean"), cpu_s_total=("seconds", "sum"), queries=("queries", "max")).reset_index()
    L += ["## Costs", "", "Simulation cost = total revealed queries per trajectory (startup included; one simulation reveals every output, counted once). Modelling CPU is separate.", "", md(S, 1), "",
          f"Total modelling CPU of the final programme: {Cs.seconds.sum() / 3600:.2f} h.", ""]


def main():
    RC.limit_threads(1); REP.mkdir(parents=True, exist_ok=True); M = P.manifest()
    L = ["# RC19 pooled from-scratch benchmark — single results table (DEV; final repeats 3–10; frozen protocol PROTOCOL_RC19.md)", "",
         "One pool of 541 inspected SPH simulations; every revealed simulation counts, startup included; learners refit on all revealed rows after each query.", ""]
    for fn in (regression, region, label, temporal):
        try:
            fn(L, M)
        except FileNotFoundError as ex:
            L += [f"*({fn.__name__}: units not available yet — {ex})*", ""]
    costs(L)
    (REP / "RESULTS_TABLE.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L[:60]))


if __name__ == "__main__":
    {"all": main}[sys.argv[1]]()
