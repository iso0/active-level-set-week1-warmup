"""RC19B final report: every table of the frozen final comparison, float32 exports with an acceptance check, and compute cost.
Reads the final unit caches only (b-final-label, b-final-reg). Frozen with PROTOCOL_RC19B.md BEFORE any final outcome exists.

Verdict rule (all pre-declared contrasts): paired per repeat (8 fresh repeats). BETTER iff the mean paired difference is at least
the metric's margin in the good direction AND the difference is in the good direction in >= MIN_BETTER of the 8 repeats; WORSE
symmetrically; otherwise NOT DIFFERENT. Every verdict is DEV evidence (all simulations were inspected before; new splits are not
new physical data).
    python -m src.rc19b_report keyhole | duration | export | cost | all     -> opus_rc19b/report/
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_final as F19
import src.rc19_pool as P
import src.rc19b_final as F
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
DUR = "vmax_spike_us"
HZ = {"label": 60, "reg": 80}
STAGES = {"final": ("b-final-label", "b-final-reg", "report", "export_final"), "smoke": ("b-smoke-label", "b-smoke-reg", "report_smoke", "export_smoke")}
CFG = {}
REP = OUT / "report"


def use(stage):
    """final = the frozen comparison; smoke = the same code on one seen DEV task (code-path test before the freeze, no claim)."""
    global REP
    CFG.update(zip(("label", "reg", "rep", "exp"), STAGES[stage])); REP = OUT / CFG["rep"]


use("final")


def verdict(d, margin, direction):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; m = float(d.mean()) if len(d) else np.nan
    good = (d < 0) if direction == "lower" else (d > 0); bad = (d > 0) if direction == "lower" else (d < 0)
    if len(d) < len(F.REPEATS):
        return f"INCOMPLETE ({len(d)}/{len(F.REPEATS)})", m, int(good.sum())
    if (m <= -margin if direction == "lower" else m >= margin) and good.sum() >= F.MIN_BETTER:
        return "BETTER (DEV)", m, int(good.sum())
    if (m >= margin if direction == "lower" else m <= -margin) and bad.sum() >= F.MIN_BETTER:
        return "WORSE (DEV)", m, int(good.sum())
    return "NOT DIFFERENT (DEV)", m, int(good.sum())


def _se(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return float(c - h), float(c + h)


def _spend_str(x):
    return ",".join("–" if pd.isna(v) else str(int(v)) for v in x)


# ======================================================================================== Keyhole
def label_units():
    import src.rc19b_keyhole_eval as KE
    U = EV.load_units(OUT / CFG["label"]); return U, KE.as_units(U, key="__none__")


def as_units_all(U):
    """Matched-path decomposition on the final paths: every construction recorded at REC_ALL budgets on each arm's own path."""
    out = []
    for u in U:
        ev = [e for e in u["evals"] if "p_all" in e]
        for c in (ev[0]["p_all"].keys() if ev else []):
            out.append({"arm": f"{c}@{u['arm']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                        "evals": [{"budget": e["budget"], "p": e["p_all"][c], "status": "ok"} for e in ev]})
    return out


def decomposition(U, M):
    import src.rc19b_keyhole_eval as KE
    X = as_units_all(U); B = EV.label_metrics(X, M); Rl = KE.reliability(X, M)
    B.to_csv(REP / "keyhole_final_decomposition_metrics.csv", index=False, lineterminator="\n"); L = []
    for arm in F.KEYHOLE_ARMS:
        s = f"@{arm}"; Bs = B[B.arm.str.endswith(s)]; Rs = Rl[Rl.arm.str.endswith(s)]
        if Bs.empty:
            continue
        L1, _, _ = KE.summarise(Bs, Rs, f"Matched-path decomposition on the paths of {arm} (fresh repeats; every construction on the same paid prefixes)",
                                [(a + s, b + s) for a, b in F.DECOMP_PAIRS], "B8–B60 (every 4)")
        L += L1
    return L


def reliability_bins(X, M, budgets=(16, 24, 40, 60)):
    """Reliability diagram data pooled over repeats and folds (10 equal-width bins) with Wilson 95 % intervals."""
    acc = {}
    for u in X:
        y = M.reindex(u["test_ids"]).y.to_numpy(int)
        for e in u["evals"]:
            if e["budget"] in budgets:
                a = acc.setdefault((u["arm"], e["budget"]), [[], []]); a[0].append(np.asarray([np.nan if v is None else v for v in e["p"]], float)); a[1].append(y)
    rows = []
    for (arm, b), (ps, ys) in sorted(acc.items()):
        p = np.concatenate(ps); y = np.concatenate(ys); ok = np.isfinite(p); p, y = p[ok], y[ok]; k = np.minimum((p * 10).astype(int), 9)
        for j in range(10):
            s = k == j
            if s.any():
                lo, hi = wilson(int(y[s].sum()), int(s.sum()))
                rows.append({"arm": arm, "budget": b, "bin": f"{j / 10:.1f}-{(j + 1) / 10:.1f}", "n": int(s.sum()), "mean_p": float(p[s].mean()),
                             "observed": float(y[s].mean()), "wilson95_lo": lo, "wilson95_hi": hi, "mean_p_inside_CI": bool(lo <= p[s].mean() <= hi)})
    return pd.DataFrame(rows)


def spend_pairs(E, pairs):
    """Paired confirmation-spend differences (total revealed simulations), with censoring kept separate."""
    rows = []
    for a, b in pairs:
        j = E[E.arm == a].set_index("repeat")[["spend", "censored"]].join(E[E.arm == b].set_index("repeat")[["spend", "censored"]], lsuffix="_a", rsuffix="_b", how="inner")
        both = j[~j.censored_a & ~j.censored_b]; d = both.spend_a - both.spend_b
        rows.append({"contrast": f"{a} − {b}", "both_confirmed": int(len(both)), "mean_difference": float(d.mean()) if len(d) else np.nan,
                     "fewer/equal/more": f"{int((d < 0).sum())}/{int((d == 0).sum())}/{int((d > 0).sum())}",
                     "only_first_censored": int((j.censored_a & ~j.censored_b).sum()), "only_second_censored": int((~j.censored_a & j.censored_b).sum()),
                     "both_censored": int((j.censored_a & j.censored_b).sum()),
                     "per_repeat_first/second": ";".join(f"{'–' if pd.isna(x) else int(x)}/{'–' if pd.isna(y) else int(y)}" for x, y in zip(j.spend_a, j.spend_b))})
    return pd.DataFrame(rows)


def keyhole():
    import src.rc19b_keyhole_eval as KE
    REP.mkdir(parents=True, exist_ok=True); M = P.manifest(); U, X = label_units(); B = EV.label_metrics(X, M); Rl = KE.reliability(X, M)
    B.to_csv(REP / "keyhole_final_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(REP / "keyhole_final_reliability.csv", index=False, lineterminator="\n")
    L1, A, E = KE.summarise(B, Rl, "Final adaptive arms (every arm on its own path; E1RAW and E1CAL share E1's straddle path)", F.KEYHOLE_PAIRS, "B8–B60 (every budget)")
    A2 = B[B.budget >= P.B0].groupby(["arm", "repeat"]).agg(sens_AULC=("sensitivity", "mean"), spec_AULC=("specificity", "mean")).reset_index()
    A = A.merge(A2, on=["arm", "repeat"]); A.to_csv(REP / "keyhole_final_aulc.csv", index=False, lineterminator="\n"); E.to_csv(REP / "keyhole_final_endpoints.csv", index=False, lineterminator="\n")
    V = []
    for i, (a, b, met, direction, margin) in enumerate([F.KEYHOLE_PRIMARY] + [(a, b, m_, F.METRIC_DIRECTION[m_], F.MARGINS[m_]) for a, b in F.KEYHOLE_PAIRS for m_ in F.MARGINS]):
        x = A[A.arm == a].set_index("repeat")[met]; y = A[A.arm == b].set_index("repeat")[met]; d = (x - y).dropna()
        v, m, g = verdict(d.values, margin, direction)
        V.append({"role": "PRIMARY" if i == 0 else "secondary", "contrast": f"{a} − {b}", "metric": met, "direction": direction, "margin": margin, "mean": m,
                  "se": _se(d.values), "min": float(d.min()) if len(d) else np.nan, "max": float(d.max()) if len(d) else np.nan, "repeats_good": f"{g}/{len(d)}", "verdict": v})
    V = pd.DataFrame(V); V.to_csv(REP / "keyhole_final_verdicts.csv", index=False, lineterminator="\n")
    prim = V.iloc[0]
    RB = reliability_bins(X, M); RB.to_csv(REP / "keyhole_final_reliability_bins.csv", index=False, lineterminator="\n")
    g = Rl[Rl.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"])
    CS = g.agg(cal_slope=("cal_slope", "mean"), cal_slope_se=("cal_slope", _se), cal_intercept=("cal_intercept", "mean"), cal_intercept_se=("cal_intercept", _se),
               ECE=("ECE", "mean"), ECE_se=("ECE", _se), cal_in_large=("cal_in_large", "mean"), cal_in_large_se=("cal_in_large", _se)).reset_index()
    RB2 = RB.groupby(["arm", "budget"]).agg(bins=("n", "size"), bins_mean_p_inside_Wilson95=("mean_p_inside_CI", "sum")).reset_index()
    CS = CS.merge(RB2, on=["arm", "budget"], how="left")
    SP = spend_pairs(E, F.KEYHOLE_PAIRS)
    HC = B[B.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"]).agg(spec_NEW_mean=("spec_NEW", "mean"), spec_NEW_min=("spec_NEW", "min"), spec_NEW_max=("spec_NEW", "max")).reset_index()
    HC = HC.merge(Rl[Rl.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"]).agg(hard_errors=("hard_NEW_conduction_errors", "sum"), hard_n=("hard_NEW_conduction_n", "sum")).reset_index(), on=["arm", "budget"])
    SEC = B[B.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"]).agg(q20_BA=("q20_BA", "mean"), shortK_pooled_captured=("shortK_pooled_captured", "mean"),
                                                                           shortK_pooled_total=("shortK_pooled_total", "mean"), shortK_NEW_captured=("shortK_NEW_captured", "mean"),
                                                                           shortK_NEW_total=("shortK_NEW_total", "mean")).reset_index()
    ES = E.groupby("arm").agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), censored=("censored", "sum"), first_mean=("first", "mean"),
                              first_median=("first", "median"), spend_mean=("spend", "mean"), spend_median=("spend", "median"), spend_min=("spend", "min"), spend_max=("spend", "max"),
                              spend_per_repeat=("spend", _spend_str)).reset_index()
    AS = A.groupby("arm")[["BA_AULC", "sens_AULC", "spec_AULC", "LL_AULC", "Brier_AULC", "AUC_AULC"]].agg(["mean", _se]); AS.columns = [f"{a}_{'se' if b == '_se' else b}" for a, b in AS.columns]
    Lk = ["# RC19B Keyhole — final paired adaptive comparison (fresh DEV repeats 11–18; frozen protocol PROTOCOL_RC19B.md)", "",
          f"**PRIMARY — {prim.contrast}, {prim.metric} ({prim.direction} is better, margin {prim.margin}): {prim.verdict}** "
          f"(mean Δ {prim['mean']:+.4f} ± {prim.se:.4f} SE; good direction in {prim.repeats_good} repeats)", "",
          "## Pre-declared contrasts (verdict rule: mean beyond the margin AND ≥ 7 of 8 repeats in the same direction)", "", md(V, 4), "",
          "## AULC over B8–B60 (mean and SE over the 8 repeats)", "", md(AS.reset_index(), 4), "",
          "## BA ≥ 0.93: first qualifying budget and confirmation spend (b + 4 of the first confirmed pair; total revealed simulations, startup included)", "", md(ES, 2), "",
          "Paired confirmation-spend differences (both confirmed; censoring counted separately):", "", md(SP, 2), "",
          "## Reliability with uncertainty", "",
          "Calibration slope / intercept (logistic recalibration of y on logit p; 1 / 0 = calibrated), ECE and calibration-in-the-large: mean and SE over repeats; "
          "bins_mean_p_inside_Wilson95 = reliability bins (pooled over repeats and folds) whose mean prediction lies inside the Wilson 95 % interval of the observed frequency.", "",
          md(CS, 3), "", "Reliability-diagram bins: report/keyhole_final_reliability_bins.csv.", "",
          "## Hard fast-scan corner (NEW-batch conduction test runs; evaluator-only diagnostic): conduction recall and error COUNTS summed over repeats", "", md(HC, 3), "",
          "## Secondary: q20 boundary BA and short-K capture", "", md(SEC, 2), ""] + L1[2:]
    (REP / "KEYHOLE_FINAL.md").write_text("\n".join(Lk) + "\n", encoding="utf-8")
    Ld = ["# RC19B Keyhole — matched-path decomposition on the final paths (exploratory; same paid prefixes, recorded every 4 budgets)", ""] + decomposition(U, M)
    (REP / "KEYHOLE_FINAL_DECOMPOSITION.md").write_text("\n".join(Ld) + "\n", encoding="utf-8"); return Lk


# ======================================================================================== duration / joint
def duration():
    import src.rc19b_duration_eval as DE
    REP.mkdir(parents=True, exist_ok=True); M = P.manifest(); U = EV.load_units(OUT / CFG["reg"])
    R, D, J = DE.final(U, write=False)
    E0 = EV.reg_endpoints(R[R.budget >= P.B0], F19.LEVELS, F19.PRIMARY_TARGETS); E0.to_csv(REP / "reg_final_endpoints.csv", index=False, lineterminator="\n")
    chk = J[J.variant == "ORIG_GP"].merge(E0[E0.target == "JOINT"][["model", "acq", "repeat", "confirmed", "censored"]], on=["model", "acq", "repeat"])
    consistency = int(((chk.joint_spend.fillna(-1) - (chk.confirmed + 4).fillna(-1)).abs() > 0).sum())
    J.to_csv(REP / "duration_final_joint.csv", index=False, lineterminator="\n"); D.to_csv(REP / "duration_final_curves.csv", index=False, lineterminator="\n")
    R.to_csv(REP / "reg_final_curves.csv", index=False, lineterminator="\n")
    JS = J.groupby(["model", "acq", "variant"]).agg(joint_confirmed=("joint_censored", lambda c: f"{int((~c).sum())}/{len(c)}"), joint_censored=("joint_censored", "sum"),
                                                     joint_ever_qualified=("joint_first", lambda x: f"{int(x.notna().sum())}/{len(x)}"),
                                                     joint_spend_mean=("joint_spend", "mean"), joint_spend_per_repeat=("joint_spend", _spend_str),
                                                     dur_confirmed=("dur_censored", lambda c: f"{int((~c).sum())}/{len(c)}"), dur_spend_per_repeat=("dur_spend", _spend_str),
                                                     dur_R2_AULC=("dur_AULC", "mean")).reset_index()
    # pre-declared duration contrasts
    V = []
    for m, a in F.REG_ARMS:
        g = J[(J.model == m) & (J.acq == a)].pivot_table(index="repeat", columns="variant", values="dur_AULC", dropna=False).reindex(columns=["ORIG_GP", "HURDLE"])
        d = (g["HURDLE"] - g["ORIG_GP"]).dropna(); v, mu, good = verdict(d.values, F.DUR_MARGIN, "higher")
        V.append({"role": "D1 duration R2-AULC, matched path", "arm": f"{m}+{a}", "contrast": "HURDLE − own GP duration", "mean": mu, "se": _se(d.values), "repeats_good": f"{good}/{len(d)}", "verdict": v})
        jj = J[(J.model == m) & (J.acq == a)].pivot_table(index="repeat", columns="variant", values="joint_censored", aggfunc="first", dropna=False).reindex(columns=["ORIG_GP", "HURDLE"]).fillna(True)
        ch, cg = int((~jj["HURDLE"].astype(bool)).sum()), int((~jj["ORIG_GP"].astype(bool)).sum()); lost = int(((~jj["ORIG_GP"].astype(bool)) & jj["HURDLE"].astype(bool)).sum())
        jv = "IMPROVED" if (ch - cg >= F.JOINT_GAIN and lost == 0) else ("WORSE" if (cg - ch >= F.JOINT_GAIN) else "NO CLEAR CHANGE")
        jv = f"INCOMPLETE ({len(jj)}/{len(F.REPEATS)})" if len(jj) < len(F.REPEATS) else f"{jv} (DEV)"
        V.append({"role": "D2 joint completion by B80, matched path", "arm": f"{m}+{a}", "contrast": "HURDLE vs own GP duration", "mean": float(ch - cg), "se": np.nan,
                  "repeats_good": f"{ch}/{len(jj)} vs {cg}/{len(jj)} (lost {lost})", "verdict": jv})
    ref = F.REG_REFERENCE
    for var, role in (("ORIG_GP", "D3 joint spend, own GP duration (acquisition contrast)"), ("HURDLE", "D3b joint spend, hurdle duration (secondary)")):
        Jh = J[J.variant == var].copy(); Jh["arm"] = Jh.model + "+" + Jh.acq
        Jh["spend_imp"] = Jh.joint_spend.fillna(HZ["reg"] + 4)                  # censored -> 84, a LOWER bound of the true spend
        for m, a in F.REG_ARMS:
            if (m, a) == ref:
                continue
            x = Jh[Jh.arm == f"{m}+{a}"].set_index("repeat").spend_imp; y = Jh[Jh.arm == f"{ref[0]}+{ref[1]}"].set_index("repeat").spend_imp; d = (x - y).dropna()
            v, mu, good = verdict(d.values, F.SPEND_MARGIN, "lower")
            V.append({"role": role, "arm": f"{m}+{a}", "contrast": f"− {ref[0]}+{ref[1]} (censored = 84, lower bound)", "mean": mu, "se": _se(d.values),
                      "repeats_good": f"{good}/{len(d)}", "verdict": v})
    V = pd.DataFrame(V); V.to_csv(REP / "duration_final_verdicts.csv", index=False, lineterminator="\n")
    EO = E0[E0.target != "JOINT"].groupby(["model", "acq", "target"]).agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"),
                                                                         spend_per_repeat=("confirm_spend", _spend_str), AULC=("AULC", "mean")).reset_index()
    DC = D[D.budget.isin([16, 40, 80])].groupby(["model", "acq", "variant", "budget"]).agg(R2=("R2", "mean"), R2_min=("R2", "min"), R2_max=("R2", "max"), cov90=("cov90", "mean"),
                                                                                         zero_rmse=("zero_rmse", "mean"), positive_rmse=("positive_rmse", "mean")).reset_index()
    W = []
    for u in U:
        for k, w in enumerate(u.get("weights_log") or []):
            W.append({"acq": u["acq"], "repeat": u["repeat"], "fold": u["fold"], "step": 4 * k, **w})
    WS = pd.DataFrame(W).groupby("step").mean(numeric_only=True).drop(columns=["repeat", "fold"], errors="ignore").reset_index() if W else pd.DataFrame()
    Ld = ["# RC19B physical outputs — spike-duration hurdle and bottleneck-aware acquisition (fresh DEV repeats 11–18; frozen protocol)", "",
          f"Fixed absolute targets (RC19): {json.dumps(F19.LEVELS)}; joint = all 8 at their targets at the same budget, confirmed at b and b + 4; spend = b + 4 (total revealed "
          f"simulations, startup included); horizon B80. Joint-from-dur_curves vs evaluator joint (own GP duration) mismatches: {consistency}.", "",
          "## Pre-declared contrasts", "", md(V, 3), "",
          "## Joint completion, every arm, with the arm's own GP duration (ORIG_GP) and with the hurdle duration (HURDLE)", "", md(JS, 2), "",
          "## Per-output completion (own GP models; spend per repeat)", "", md(EO, 3), "",
          "## Duration accuracy at matched budgets (mean, min, max over repeats; zero_rmse = error on true zeros, positive_rmse = error on positive durations, µs)", "", md(DC, 3), ""]
    if len(WS):
        Ld += ["## Bottleneck-aware weights (MOIVRB: w_t = max(0.05, 1 − paid LOO-R²_t); mean over trajectories; step = acquisition steps after the startup, every 4th)", "", md(WS, 3), ""]
    (REP / "DURATION_FINAL.md").write_text("\n".join(Ld) + "\n", encoding="utf-8"); return Ld


# ======================================================================================== exports + acceptance
def export():
    REP.mkdir(parents=True, exist_ok=True); exp = OUT / CFG["exp"]; exp.mkdir(parents=True, exist_ok=True); M = P.manifest(); acc = {}; paths = []
    U, X = label_units(); keys, arrs, tids, buds = [], [], [], []
    for u in X:
        keys.append(f"{u['arm']}|r{u['repeat']}|f{u['fold']}"); arrs.append(np.asarray([[np.nan if v is None else v for v in e["p"]] for e in u["evals"]], np.float32))
        tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray([e["budget"] for e in u["evals"]], np.int16))
    for u in U:
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"workstream": "label", "arm": u["arm"], "design": "", "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s})
    np.savez_compressed(exp / "predictions_label_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"label": "pred[budget, test] = P(Keyhole), float32 (identical to the unit cache)"})]))
    Z = np.load(exp / "predictions_label_f32.npz", allow_pickle=False); Xe = []
    for i, k in enumerate(Z["keys"]):
        arm, r, f = k.split("|"); to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        Xe.append({"arm": arm, "repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"]),
                   "evals": [{"budget": int(b), "p": to(Z[f"pred_{i}"][j])} for j, b in enumerate(Z[f"budgets_{i}"])]})
    a, b = EV.label_metrics(Xe, M), pd.read_csv(REP / "keyhole_final_metrics.csv"); acc["label"] = _compare(a, b, ["arm", "repeat", "budget"],
                                                                                                         ["BA", "sensitivity", "specificity", "AUC", "brier", "log_loss", "q20_BA", "spec_NEW"])
    U = EV.load_units(OUT / CFG["reg"]); keys, arrs, tids, buds = [], [], [], []; T9 = list(P.TARGETS) + [DUR + "__hurdle"]
    for u in U:
        b_ = [e["budget"] for e in u["evals"]]; arr = np.full((len(b_), len(T9), 2, len(u["test_ids"])), np.nan, np.float32)
        for i, e in enumerate(u["evals"]):
            for k, c in enumerate(T9):
                pr = e["pred"].get(c)
                if pr is not None:
                    arr[i, k, 0] = [np.nan if v is None else v for v in pr[0]]; arr[i, k, 1] = [np.nan if v is None else v for v in pr[1]]
        keys.append(f"{u['model']}|{u['acq']}|r{u['repeat']}|f{u['fold']}"); arrs.append(arr); tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray(b_, np.int16))
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"workstream": "reg", "arm": u["model"], "design": u["acq"], "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s})
    np.savez_compressed(exp / "predictions_reg_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)},
                        schema=np.asarray([json.dumps({"reg": "pred[budget, target, {mean, observation var}, test], float32; targets = " + ",".join(T9)})]))
    Z = np.load(exp / "predictions_reg_f32.npz", allow_pickle=False); Ue = []
    for i, k in enumerate(Z["keys"]):
        m, a_, r, f = k.split("|"); A_ = Z[f"pred_{i}"]; to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        Ue.append({"model": m, "acq": a_, "repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"]),
                   "evals": [{"budget": int(bb), "pred": {c: [to(A_[j, kk, 0]), to(A_[j, kk, 1])] for kk, c in enumerate(T9)}} for j, bb in enumerate(Z[f"budgets_{i}"])]})
    a = EV.reg_curves([{**u, "evals": [{"budget": e["budget"], "pred": {c: v for c, v in e["pred"].items() if c in P.TARGETS}} for e in u["evals"]]} for u in Ue], M)
    acc["reg"] = _compare(a, pd.read_csv(REP / "reg_final_curves.csv"), ["model", "acq", "repeat", "target", "budget"], ["R2", "cov90", "nlpd"])
    import src.rc19b_duration_eval as DE
    dd = DE.dur_curves(Ue, M, lambda u, e: {"ORIG_GP": (DE._arr(e["pred"][DUR][0]), DE._arr(e["pred"][DUR][1])),
                                           "HURDLE": (DE._arr(e["pred"][DUR + "__hurdle"][0]), DE._arr(e["pred"][DUR + "__hurdle"][1]))})
    acc["duration"] = _compare(dd, pd.read_csv(REP / "duration_final_curves.csv"), ["model", "acq", "variant", "repeat", "budget"], ["R2", "cov90", "zero_rmse", "positive_rmse"])
    pd.DataFrame(paths).to_csv(exp / "paths_final.csv.gz", index=False, compression="gzip")
    (exp / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); return acc


def _compare(a, b, key, cols):
    j = a.merge(b, on=key, suffixes=("_export", "_csv")); res = {"cells_compared": int(len(j)), "cells_in_csv": int(len(b))}
    for c in cols:
        d = np.abs(j[f"{c}_export"].to_numpy(float) - j[f"{c}_csv"].to_numpy(float)); nan_mismatch = int((np.isfinite(j[f"{c}_export"]) != np.isfinite(j[f"{c}_csv"])).sum())
        d = d[np.isfinite(d)]; res[c] = {"max_abs_diff": float(d.max()) if len(d) else 0.0, "cells_differing_gt_1e-12": int((d > 1e-12).sum()), "nan_pattern_mismatch": nan_mismatch}
    res["PASS"] = bool(res["cells_compared"] == res["cells_in_csv"] and all(v["cells_differing_gt_1e-12"] == 0 and v["nan_pattern_mismatch"] == 0
                                                                          for v in res.values() if isinstance(v, dict)))
    return res


# ======================================================================================== compute cost
def cost():
    REP.mkdir(parents=True, exist_ok=True); rows = []
    for job, key in ((CFG["label"], "arm"), (CFG["reg"], None)):
        for u in EV.load_units(OUT / job):
            arm = u["arm"] if key else f"{u['model']}+{u['acq']}"; q = u.get("queries", 0)
            rows.append({"job": job, "arm": arm, "seconds": float(u["seconds"]), "queries": q, "seconds_per_query_after_startup": float(u["seconds"]) / max(1, q - P.B0)})
    C_ = pd.DataFrame(rows).groupby(["job", "arm"]).agg(units=("seconds", "size"), cpu_s_mean=("seconds", "mean"), cpu_s_median=("seconds", "median"), cpu_s_max=("seconds", "max"),
                                                        cpu_s_total=("seconds", "sum"), s_per_query=("seconds_per_query_after_startup", "mean")).reset_index()
    C_.to_csv(REP / "compute_cost.csv", index=False, lineterminator="\n")
    L = ["# RC19B compute cost (single-thread wall seconds per trajectory, as recorded by each unit)", "", md(C_, 1), ""]
    (REP / "COMPUTE_COST.md").write_text("\n".join(L) + "\n", encoding="utf-8"); return L


def main(what, stage="final"):
    RC.limit_threads(1); use(stage); L = []
    if what in ("keyhole", "all"):
        L += keyhole()
    if what in ("duration", "all"):
        L += duration()
    if what in ("export", "all"):
        L += ["", "Export acceptance: " + json.dumps(export())]
    if what in ("cost", "all"):
        L += cost()
    print("\n".join(L)[:20000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "final")
