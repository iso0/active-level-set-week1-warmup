"""RC19B duration evaluation: hurdle variants vs the arm's own duration GP on the SAME paid prefixes (replay), and the joint
8-output endpoint re-evaluated with only the duration prediction replaced (the other 7 outputs' recorded predictions unchanged).
Also zero/positive decisions (BA of q >= 0.5), positive-duration error, full-target R2 and 90 % interval coverage.
    python -m src.rc19b_duration_eval replay | final
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_final as F19
import src.rc19_pool as P
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
DUR = "vmax_spike_us"


def _arr(x):
    return np.asarray([np.nan if v is None else v for v in x], float)


def dur_curves(units, M, key_pred):
    """R2 / cov90 of the duration prediction `key_pred(unit, eval) -> (mean, var)` pooled over the folds of a repeat."""
    acc = {}
    for u in units:
        y = M.reindex(u["test_ids"])[DUR].to_numpy(float)
        for e in u["evals"]:
            for name, (m, v) in key_pred(u, e).items():
                a = acc.setdefault((u["model"], u["acq"], name, u["repeat"], e["budget"]), [[], [], [], 0]); a[0].append(y); a[1].append(m); a[2].append(v); a[3] += 1
    rows = []; yall = M[DUR].to_numpy(float); ybar = np.nanmean(yall)
    for (m_, a_, name, r, b), (ys, ms, vs, nf) in acc.items():
        y, m, v = np.concatenate(ys), np.concatenate(ms), np.concatenate(vs); ok = np.isfinite(y) & np.isfinite(m)
        r2 = 1 - np.sum((y[ok] - m[ok]) ** 2) / np.sum((y[np.isfinite(y)] - ybar) ** 2) if nf == 5 and ok.sum() == np.isfinite(y).sum() else np.nan
        cov = float(np.mean(np.abs(y[ok] - m[ok]) <= 1.6449 * np.sqrt(np.maximum(v[ok], 1e-12)))); pos = ok & (y > 0)
        rows.append({"model": m_, "acq": a_, "variant": name, "repeat": r, "budget": b, "R2": r2, "cov90": cov,
                     "zero_rmse": float(np.sqrt(np.mean(m[ok & (y == 0)] ** 2))) if (ok & (y == 0)).any() else np.nan,
                     "positive_rmse": float(np.sqrt(np.mean((y[pos] - m[pos]) ** 2))) if pos.any() else np.nan})
    return pd.DataFrame(rows)


def joint_with(R_other, D):
    """Joint endpoint (all 8 outputs at their RC19 levels) with the duration R2 from D (per model, acq, variant, repeat)."""
    out = []
    for (m, a, var, r), g in D.groupby(["model", "acq", "variant", "repeat"]):
        o = R_other[(R_other.model == m) & (R_other.acq == a) & (R_other.repeat == r)]
        cur = {t: dict(zip(gt.budget, gt.R2)) for t, gt in o.groupby("target")}; cur[DUR] = dict(zip(g.budget, g.R2))
        bs = sorted(cur[DUR]); joint = {b: min(cur[t].get(b, -9) - F19.LEVELS[t] for t in F19.PRIMARY_TARGETS) for b in bs}
        e = EV.endpoint(joint, 0.0); ed = EV.endpoint(cur[DUR], F19.LEVELS[DUR])
        out.append({"model": m, "acq": a, "variant": var, "repeat": r, "joint_first": e["first"], "joint_spend": e["confirm_spend"], "joint_censored": e["censored"],
                    "dur_first": ed["first"], "dur_spend": ed["confirm_spend"], "dur_censored": ed["censored"], "dur_AULC": float(np.nanmean(list(cur[DUR].values())))})
    return pd.DataFrame(out)


def replay():
    M = P.manifest(); U = EV.load_units(OUT / "b-dur-replay"); base = {}
    for u in EV.load_units(P.OUT / "final" / "final-reg"):
        base[(u["model"], u["acq"], u["repeat"], u["fold"])] = u

    def pred(u, e):
        out = {k: (_arr(v[0]), _arr(v[1])) for k, v in e["pred"].items()}
        b0 = {x["budget"]: x for x in base[(u["model"], u["acq"], u["repeat"], u["fold"])]["evals"]}[e["budget"]]["pred"][DUR]
        out["ORIG_GP"] = (_arr(b0[0]), _arr(b0[1])); return out
    D = dur_curves(U, M, pred); D.to_csv(OUT / "duration_replay_curves.csv", index=False, lineterminator="\n")
    R = pd.read_csv(P.OUT / "report" / "reg_curves.csv"); R = R[(R.budget >= P.B0) & (R.target != DUR)]
    J = joint_with(R, D); J.to_csv(OUT / "duration_replay_joint.csv", index=False, lineterminator="\n")
    S = J.groupby(["model", "acq", "variant"]).agg(dur_AULC=("dur_AULC", "mean"), dur_completed=("dur_censored", lambda c: f"{int((~c).sum())}/{len(c)}"),
                                                    dur_spend=("dur_spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x)),
                                                    joint_completed=("joint_censored", lambda c: f"{int((~c).sum())}/{len(c)}"),
                                                    joint_spend=("joint_spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()
    C = D[D.budget.isin([16, 40, 80])].groupby(["model", "acq", "variant", "budget"])[["R2", "cov90", "zero_rmse", "positive_rmse"]].mean().reset_index()
    L = ["# RC19B duration — hurdle replay (DEVELOPMENT on RC19 final repeats 3–10; same paid prefixes, other 7 outputs unchanged)", "",
         f"Duration level R2 ≥ {F19.LEVELS[DUR]}; joint = all 8 outputs at their RC19 levels; spend = b + 4 of the first confirmed pair (total revealed simulations).", "",
         md(S, 3), "", "Duration accuracy at matched budgets (mean over repeats; zero_rmse = error on true zeros, positive_rmse = error on positive durations, µs):", "", md(C, 3), ""]
    (OUT / "DURATION_REPLAY.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:15000])


def final(U=None, write=True):
    """Final regression units -> (R: 8-output curves, D: duration curves of the arm's own GP and of the hurdle, J: joint endpoints
    with either duration). U defaults to the b-final-reg caches; write=False leaves file output to the caller (src.rc19b_report)."""
    M = P.manifest(); U = EV.load_units(OUT / "b-final-reg") if U is None else U

    def pred(u, e):
        out = {"ORIG_GP": (_arr(e["pred"][DUR][0]), _arr(e["pred"][DUR][1])) if e["pred"].get(DUR) else None,
               "HURDLE": (_arr(e["pred"][DUR + "__hurdle"][0]), _arr(e["pred"][DUR + "__hurdle"][1]))}
        return {k: v for k, v in out.items() if v is not None}
    D = dur_curves(U, M, pred); X = []
    for u in U:
        X.append({**u, "evals": [{"budget": e["budget"], "pred": {k: v for k, v in e["pred"].items() if k in P.TARGETS}} for e in u["evals"]]})
    R = EV.reg_curves(X, M); J = joint_with(R[(R.budget >= P.B0) & (R.target != DUR)], D)
    if write:
        R.to_csv(OUT / "reg_final_curves.csv", index=False, lineterminator="\n"); D.to_csv(OUT / "duration_final_curves.csv", index=False, lineterminator="\n")
        J.to_csv(OUT / "duration_final_joint.csv", index=False, lineterminator="\n")
    return R, D, J


if __name__ == "__main__":
    {"replay": replay, "final": final}[sys.argv[1]]()
