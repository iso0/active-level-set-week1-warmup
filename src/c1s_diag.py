"""C1 stability (C1S) DEV diagnosis, part 1: anatomy of the BA regressions of C1 + margin from the RECORDED C1C predictions.

DEV only: STD repeats 203-282 of the C1C main validation (exports main_s1 / main_s2; already evaluated, now re-used for diagnosis).
Test outcomes, the corner (VX > 0.85 m/s and P > 330 W) and the hard group (short-Keyhole NEW + NEW conduction) are read here ONLY,
as evaluator-side descriptors; nothing here is a deployable rule. Oracle quantities (best-so-far envelope) are marked ORACLE.

Per learner, system and step b -> b+1 (b = 8..59):
  dBA, flips of the 0.5 decision split into harmful (correct -> wrong) / helpful by class (Keyhole: new FN / FN removed; conduction:
  new FP / FP removed), the pre-flip margin |p - 0.5|, the share of flipped points in the corner / hard group, and the position of
  the flipped points relative to the run queried at that step (distance rank among the test points in standardised log inputs;
  whether the new prediction equals the new run's label).
Per learner: the proposed stability metric S95 = mean over b = 24..60 of max(0, 0.95 - BA(b)), total variation, regression counts,
  oscillating test points (>= 3 flips in B24-B60), ORACLE envelope shortfall.
    python -m src.c1s_diag anatomy
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_c1_stability"
C1C = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
SYSTEMS = ("C1_own", "A_own", "C1_on_A", "A_on_C1", "D_on_A")
PATH_OF = {"C1_own": "C1-selected", "A_on_C1": "C1-selected", "A_own": "HA_LEAN-selected", "C1_on_A": "HA_LEAN-selected", "D_on_A": "HA_LEAN-selected"}
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330)).to_numpy()


def ba_curve(Pm, y):
    hat = Pm >= 0.5; pos = y == 1; neg = ~pos
    tpr = hat[:, pos].mean(1); tnr = (~hat[:, neg]).mean(1); return 0.5 * (tpr + tnr), hat


def s_short(ba, bs, tau=0.95, lo=24, hi=60):
    m = (bs >= lo) & (bs <= hi); return float(np.mean(np.maximum(0.0, tau - ba[m])))


def anatomy():
    M = P.manifest(); y_all = M.y.astype(int); corner = pd.Series(CORNER(M), index=M.index)
    hard = pd.Series(M.shortK_NEW_original.astype(bool).to_numpy() | ((M.source_batch == "NEW") & (M.y == 0)).to_numpy(), index=M.index)
    E = {}; paths = []
    for s in ("main_s1", "main_s2"):
        E.update(EX.load(C1C / "exports" / s)); paths.append(pd.read_csv(C1C / "exports" / s / "paths.csv.gz"))
    paths = pd.concat(paths, ignore_index=True)
    reps = sorted({k[2] for k in E}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    steps, learners, osc = [], [], []
    for (sy, cond, c, l), (bs, Pm, ids) in sorted(E.items()):
        if sy not in SYSTEMS:
            continue
        task = T[(c, l)]; Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}
        y = y_all.reindex(ids).to_numpy(int); cr = corner.reindex(ids).to_numpy(bool); hd = hard.reindex(ids).to_numpy(bool)
        tz = Z[[pos[s] for s in ids]]
        pth = paths[(paths.path == PATH_OF[sy]) & (paths.cluster == c) & (paths.learner == l)].sort_values("query")
        qid = pth.sim_id.to_numpy(str)
        ba, hat = ba_curve(Pm, y); corr = hat == (y == 1)[None, :]; n1, n0 = int((y == 1).sum()), int((y == 0).sum())
        for j in range(len(bs) - 1):
            b = int(bs[j]); fl = hat[j + 1] != hat[j]
            harm = corr[j] & ~corr[j + 1]; helpf = ~corr[j] & corr[j + 1]
            qn = qid[b] if b < len(qid) else None                    # the run opened at query number b + 1 (0-based index b)
            if qn is not None:
                zq = Z[pos[qn]]; d = np.linalg.norm(tz - zq, axis=1); rk = d.argsort().argsort() / max(1, len(d) - 1); yq = int(y_all[qn])
            else:
                rk = np.full(len(y), np.nan); yq = -1
            steps.append((sy, c, l, b, float(ba[j + 1] - ba[j]), int(fl.sum()),
                          int((harm & (y == 1)).sum()), int((harm & (y == 0)).sum()), int((helpf & (y == 1)).sum()), int((helpf & (y == 0)).sum()),
                          float(np.median(np.abs(Pm[j, fl] - 0.5))) if fl.any() else np.nan,
                          int((fl & cr).sum()), int((fl & hd).sum()), float(np.mean(rk[fl] <= 0.25)) if fl.any() else np.nan,
                          float(np.mean(hat[j + 1, fl] == (yq == 1))) if (fl.any() and yq >= 0) else np.nan, yq,
                          bool(corner.get(qn, False)) if qn is not None else False))
        m = (bs >= 24) & (bs <= 60); flips_late = (hat[1:] != hat[:-1])[m[1:] & m[:-1]].sum(0)
        o = flips_late >= 3
        env = np.maximum.accumulate(ba)                                        # ORACLE: best-so-far version (uses test labels)
        att = next((int(bs[k]) for k in range(len(bs)) if bs[k] + 4 <= 60 and ba[k] >= 0.95 and ba[k + 4] >= 0.95), None)
        learners.append({"system": sy, "cluster": c, "learner": l, "S95": s_short(ba, bs), "S93": s_short(ba, bs, 0.93), "S95_oracle_envelope": s_short(env, bs),
                         "TV_24_60": float(np.abs(np.diff(ba[m])).sum()), "n_reg_steps_24_60": int((np.diff(ba[m]) < 0).sum()),
                         "drawdown_max_24_60": float(np.max(np.maximum.accumulate(ba[m]) - ba[m])), "BA_B8_B24": float(ba[(bs >= 8) & (bs <= 24)].mean()),
                         "BA_B24_B60": float(ba[m].mean()), "BA60": float(ba[-1]), "n1": n1, "n0": n0, "confirmed_095": att,
                         "below_095_after_conf": int(np.sum(ba[bs >= att] < 0.95)) if att is not None else None,
                         "osc_points": int(o.sum()), "osc_corner": int((o & cr).sum()), "osc_hard": int((o & hd).sum()), "osc_K": int((o & (y == 1)).sum())})
        for i in np.flatnonzero(o):
            osc.append({"system": sy, "cluster": c, "learner": l, "sim_id": ids[i], "y": int(y[i]), "corner": bool(cr[i]), "hard": bool(hd[i]), "flips_24_60": int(flips_late[i]),
                        "frac_correct_24_60": float(corr[m, i].mean()), "p_mean_24_60": float(Pm[m, i].mean())})
    S = pd.DataFrame(steps, columns=["system", "cluster", "learner", "b", "dBA", "n_flip", "harm_K", "harm_C", "help_K", "help_C", "flip_margin_med", "flip_corner",
                                     "flip_hard", "flip_local_q25", "flip_to_new_label", "y_new", "new_in_corner"])
    Lr = pd.DataFrame(learners); O = pd.DataFrame(osc)
    d = OUT / "diag"; d.mkdir(parents=True, exist_ok=True)
    S.to_csv(d / "steps.csv.gz", index=False, compression="gzip"); Lr.to_csv(d / "learners.csv.gz", index=False, compression="gzip"); O.to_csv(d / "oscillating_points.csv.gz", index=False, compression="gzip")
    return S, Lr, O


def summarise(S, Lr, O):
    res = {}
    for sy in SYSTEMS:
        s = S[S.system == sy]; late = s[s.b >= 24]; reg = late[late.dBA < 0]
        lr = Lr[Lr.system == sy]
        res[sy] = {
            "steps_24_60": int(len(late)), "regression_share": float((late.dBA < 0).mean()), "mean_dBA_regression": float(reg.dBA.mean()),
            "flips_per_step_24_60": float(late.n_flip.mean()), "harmful_per_step_24_60": float((late.harm_K + late.harm_C).mean()),
            "helpful_per_step_24_60": float((late.help_K + late.help_C).mean()),
            "regression_steps_with_le2_harmful": float(((reg.harm_K + reg.harm_C) <= 2).mean()),
            "harmful_K_share": float(late.harm_K.sum() / max(1, (late.harm_K + late.harm_C).sum())),
            "BA_loss_share_K": float((late.harm_K / late.n1_ if "n1_" in late else 0).sum()) if False else None,
            "flip_margin_median": float(late.flip_margin_med.median()), "flip_corner_share": float(late.flip_corner.sum() / max(1, late.n_flip.sum())),
            "flip_hard_share": float(late.flip_hard.sum() / max(1, late.n_flip.sum())),
            "flip_local_q25_mean": float(late.flip_local_q25.mean()), "flip_to_new_label_mean": float(late.flip_to_new_label.mean()),
            "new_query_in_corner_share": float(late.new_in_corner.mean()),
            "S95_mean": float(lr.S95.mean()), "S95_median": float(lr.S95.median()), "S95_zero_share": float((lr.S95 == 0).mean()), "S95_oracle_envelope_mean": float(lr.S95_oracle_envelope.mean()),
            "S93_mean": float(lr.S93.mean()), "TV_24_60_mean": float(lr.TV_24_60.mean()), "drawdown_mean": float(lr.drawdown_max_24_60.mean()),
            "osc_points_mean": float(lr.osc_points.mean()), "osc_corner_share": float(lr.osc_corner.sum() / max(1, lr.osc_points.sum())),
            "osc_hard_share": float(lr.osc_hard.sum() / max(1, lr.osc_points.sum())), "osc_K_share": float(lr.osc_K.sum() / max(1, lr.osc_points.sum())),
            "BA_B8_B24_mean": float(lr.BA_B8_B24.mean()), "BA_B24_B60_mean": float(lr.BA_B24_B60.mean())}
    # BA-weighted loss by class in regression steps: a Keyhole flip costs 1/(2 n1), a conduction flip 1/(2 n0)
    j = S.merge(Lr[["system", "cluster", "learner", "n1", "n0"]], on=["system", "cluster", "learner"])
    late = j[(j.b >= 24)]
    for sy in SYSTEMS:
        x = late[late.system == sy]; lk = (x.harm_K / (2 * x.n1)).sum(); lc = (x.harm_C / (2 * x.n0)).sum(); gk = (x.help_K / (2 * x.n1)).sum(); gc = (x.help_C / (2 * x.n0)).sum()
        res[sy]["BA_loss_from_K_flips_share"] = float(lk / max(1e-12, lk + lc)); res[sy]["BA_gain_from_K_flips_share"] = float(gk / max(1e-12, gk + gc))
        res[sy]["net_BA_K_24_60_per_learner"] = float((gk - lk) / x.groupby(["cluster", "learner"]).ngroups); res[sy]["net_BA_C_24_60_per_learner"] = float((gc - lc) / x.groupby(["cluster", "learner"]).ngroups)
    pool_corner = None
    (OUT / "diag" / "ANATOMY_SUMMARY.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


if __name__ == "__main__":
    if sys.argv[1] == "anatomy":
        S, Lr, O = anatomy(); r = summarise(S, Lr, O); print(json.dumps(r, indent=1, default=float))
