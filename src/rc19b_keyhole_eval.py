"""RC19B Keyhole evaluation: matched-path replay (development) and the final adaptive comparison.
Metrics per (construction, repeat, budget), test runs pooled over the 5 folds of a repeat (rc19_eval.label_metrics, unchanged)
plus reliability diagnostics computed from the same predictions: calibration-in-the-large (mean p - mean y), calibration
intercept/slope (logistic regression of y on logit p; slope 1 / intercept 0 = calibrated), ECE (10 equal-width bins), and the
hard fast-scan / high-power corner reported as error COUNTS (NEW-batch conduction runs called Keyhole; evaluator-only).
    python -m src.rc19b_keyhole_eval replay | final
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.special import logit

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"


def as_units(units, key="path_of"):
    """Replay/adaptive units -> rc19_eval-style label units, one per construction."""
    out = []
    for u in units:
        cons = list(u["evals"][0]["p"].keys())
        for c in cons:
            arm = f"{c}@{u[key]}" if key in u else (c if u.get("arm") != "E1S" else c + "+straddle")
            if key not in u:
                arm = {"E1RAW": "E1RAW+straddle", "E1CAL": "E1CAL+straddle"}.get(c, u["arm"])
            out.append({"arm": arm, "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                        "evals": [{"budget": e["budget"], "p": e["p"][c], "status": "ok"} for e in u["evals"]]})
    return out


def reliability(units, M):
    acc = {}
    for u in units:
        y = M.reindex(u["test_ids"]).y.to_numpy(int); hard = M.reindex(u["test_ids"]); hard_cond = ((hard.source_batch == "NEW") & (hard.y == 0)).to_numpy()
        for e in u["evals"]:
            a = acc.setdefault((u["arm"], u["repeat"], e["budget"]), [[], [], []]); a[0].append(np.asarray(e["p"], float)); a[1].append(y); a[2].append(hard_cond)
    rows = []
    from sklearn.linear_model import LogisticRegression
    for (arm, r, b), (ps, ys, hs) in acc.items():
        p = np.clip(np.concatenate(ps), 1e-6, 1 - 1e-6); y = np.concatenate(ys); h = np.concatenate(hs); z = logit(p)
        try:
            lr = LogisticRegression(C=1e6, max_iter=5000).fit(z[:, None], y); slope, icpt = float(lr.coef_[0, 0]), float(lr.intercept_[0])
        except Exception:
            slope = icpt = np.nan
        bins = np.minimum((p * 10).astype(int), 9); ece = float(sum(np.abs(p[bins == k].mean() - y[bins == k].mean()) * (bins == k).mean() for k in range(10) if (bins == k).any()))
        rows.append({"arm": arm, "repeat": r, "budget": b, "cal_in_large": float(p.mean() - y.mean()), "cal_slope": slope, "cal_intercept": icpt, "ECE": ece,
                     "hard_NEW_conduction_n": int(h.sum()), "hard_NEW_conduction_errors": int(np.sum(h & (p >= 0.5)))})
    return pd.DataFrame(rows)


def summarise(B, Rl, title, pairs, budgets_note):
    L = [f"## {title}", ""]
    A = B[B.budget >= P.B0].groupby(["arm", "repeat"]).agg(BA_AULC=("BA", "mean"), LL_AULC=("log_loss", "mean"), Brier_AULC=("brier", "mean"), AUC_AULC=("AUC", "mean")).reset_index()
    S = A.groupby("arm")[["BA_AULC", "LL_AULC", "Brier_AULC", "AUC_AULC"]].agg(["mean", "min", "max"]).round(4)
    S.columns = [f"{a}_{b}" for a, b in S.columns]; L += [f"AULC over {budgets_note} (mean, min, max over repeats):", "", md(S.reset_index(), 4), ""]
    rows = []
    for a, b in pairs:
        for met in ("BA_AULC", "LL_AULC", "Brier_AULC"):
            x = A[A.arm == a].set_index("repeat")[met]; y = A[A.arm == b].set_index("repeat")[met]; d = (x - y).dropna()
            better = (d > 0).sum() if met == "BA_AULC" else (d < 0).sum()
            rows.append({"contrast": f"{a} − {b}", "metric": met, "mean": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else np.nan,
                         "min": float(d.min()), "max": float(d.max()), "repeats_better": f"{int(better)}/{len(d)}"})
    L += ["Paired contrasts (per repeat; 'better' = higher BA or lower loss):", "", md(pd.DataFrame(rows), 4), ""]
    E = []
    for (arm, r), g in B.groupby(["arm", "repeat"]):
        e = EV.endpoint(dict(zip(g.budget, g.BA)), 0.93, step=4); E.append({"arm": arm, "repeat": r, "first": e["first"], "spend": e["confirm_spend"], "censored": e["censored"]})
    E = pd.DataFrame(E)
    ES = E.groupby("arm").agg(completed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), first_mean=("first", "mean"), spend_mean=("spend", "mean"),
                              spend_per_repeat=("spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()
    L += ["BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):", "", md(ES, 2), ""]
    R = Rl[Rl.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"]).agg(cal_in_large=("cal_in_large", "mean"), cal_slope=("cal_slope", "mean"), ECE=("ECE", "mean"),
                                                                            hard_errors=("hard_NEW_conduction_errors", "sum"), hard_n=("hard_NEW_conduction_n", "sum")).reset_index()
    T = B[B.budget.isin([16, 24, 40, 60])].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "AUC", "brier", "log_loss", "q20_BA", "shortK_pooled_captured", "spec_NEW"]].mean().reset_index()
    L += ["Matched budgets (mean over repeats):", "", md(T, 3), "",
          "Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):", "", md(R, 3), ""]
    return L, A, E


def replay():
    M = P.manifest(); U = EV.load_units(OUT / "b-replay"); X = as_units(U); B = EV.label_metrics(X, M); Rl = reliability(X, M)
    B.to_csv(OUT / "keyhole_replay_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(OUT / "keyhole_replay_reliability.csv", index=False, lineterminator="\n")
    L = ["# RC19B Keyhole — matched-path replay (DEVELOPMENT on RC19 final repeats 3–10; every construction on the same paid prefixes)", ""]
    for src in ("E1_STRADDLE", "PHYSCF_ATS_MARGIN", "E1_MAXIMIN"):
        Bs = B[B.arm.str.endswith("@" + src)].copy(); Rs = Rl[Rl.arm.str.endswith("@" + src)].copy()
        pairs = [(f"ATSCF@{src}", f"E1CAL@{src}"), (f"ATSCF@{src}", f"DEPTHCF@{src}"), (f"DEPTHCF@{src}", f"E1CAL@{src}"), (f"E1CAL@{src}", f"E1RAW@{src}"),
                 (f"ATSCF@{src}", f"ATSAPPROX@{src}"), (f"ATSCF@{src}", f"G3@{src}")]
        L1, _, _ = summarise(Bs, Rs, f"Paths of {src}", pairs, "B8–B60 (every 4)"); L += L1
    (OUT / "KEYHOLE_REPLAY.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:20000])


def replay_k():
    """Fold-size factor (K = 5, 10, exact refit-LOO) on the same label-free (E1_MAXIMIN) paid prefixes."""
    M = P.manifest(); U5 = [u for u in EV.load_units(OUT / "b-replay") if u["path_of"] == "E1_MAXIMIN"]; UK = EV.load_units(OUT / "b-replay-k")
    ren = {"ATSCF": "ATSCF5", "DEPTHCF": "DEPTHCF5", "E1CAL": "E1CAL5"}
    for u in U5:
        for e in u["evals"]:
            e["p"] = {ren.get(k, k): v for k, v in e["p"].items()}
    X = as_units(U5 + UK); B = EV.label_metrics(X, M); Rl = reliability(X, M)
    B.to_csv(OUT / "keyhole_replayk_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(OUT / "keyhole_replayk_reliability.csv", index=False, lineterminator="\n")
    s = "@E1_MAXIMIN"
    pairs = [(f"ATSCFLOO{s}", f"ATSCF5{s}"), (f"ATSCF10{s}", f"ATSCF5{s}"), (f"ATSCFLOO{s}", f"ATSAPPROX{s}"), (f"ATSCFLOO{s}", f"E1CALLOO{s}"), (f"ATSCFLOO{s}", f"DEPTHCFLOO{s}"),
             (f"DEPTHCFLOO{s}", f"E1CALLOO{s}"), (f"E1CALLOO{s}", f"E1RAW{s}"), (f"E1CALLOO{s}", f"E1CAL5{s}"), (f"ATSCFLOO{s}", f"E1RAW{s}")]
    L, _, _ = summarise(B, Rl, "Fold-size factor on the label-free paths (E1_MAXIMIN; same paid prefixes; DEVELOPMENT on RC19 repeats 3–10)", pairs, "B8–B60 (every 4)")
    (OUT / "KEYHOLE_REPLAY_K.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:20000])


def final():
    import src.rc19b_final as F
    M = P.manifest(); U = EV.load_units(OUT / "b-final-label"); X = as_units(U, key="__none__"); B = EV.label_metrics(X, M); Rl = reliability(X, M)
    B.to_csv(OUT / "keyhole_final_metrics.csv", index=False, lineterminator="\n"); Rl.to_csv(OUT / "keyhole_final_reliability.csv", index=False, lineterminator="\n")
    L = ["# RC19B Keyhole — final adaptive comparison (fresh DEV repeats 11–18; frozen protocol)", ""]
    L1, A, E = summarise(B, Rl, "Final adaptive arms", F.KEYHOLE_PAIRS, "B8–B60 (every budget)")
    prim = F.KEYHOLE_PRIMARY; x = A[A.arm == prim[0]].set_index("repeat")[prim[2]]; y = A[A.arm == prim[1]].set_index("repeat")[prim[2]]; d = (x - y).dropna()
    good = (d < 0) if prim[3] == "lower" else (d > 0); m = float(d.mean())
    ok = (m <= -prim[4] if prim[3] == "lower" else m >= prim[4]) and int(good.sum()) >= F.MIN_BETTER
    bad = (m >= prim[4] if prim[3] == "lower" else m <= -prim[4]) and int((~good & (d != 0)).sum()) >= F.MIN_BETTER
    v = "BETTER (DEV)" if ok else ("WORSE (DEV)" if bad else "NOT DIFFERENT (DEV; within the practical margin or inconsistent)")
    L = L[:2] + [f"**PRIMARY — {prim[0]} vs {prim[1]}, {prim[2]}: {v}** (mean Δ {m:+.4f}; better in {int(good.sum())}/{len(d)} repeats; margin {prim[4]})", ""] + L1
    (OUT / "KEYHOLE_FINAL.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:20000])


if __name__ == "__main__":
    {"replay": replay, "replayk": replay_k, "final": final}[sys.argv[1]]()
