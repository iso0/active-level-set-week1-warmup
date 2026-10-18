"""RC18 evaluators (read unit caches; fit only the M0 full-pool references that define target levels).

Regression (per population x model x design x target x repeat; test predictions pooled over the 5 folds of a repeat):
  R2(b) = 1 - SSE/SSE_ref (population-mean reference), RMSE, 90 % observation coverage, NLPD; R2-AULC over B8-B60;
  sustained budget-to-target on the grid {0, 4, ..., 56} (R2 >= level at b and b+4), censored at 64; level = 0.9 x R2_full
  of M0 with the whole fold pool paid (mean over the repeats evaluated) — the PHYS_AL rule.
Region (level set {response >= tau}):
  learning: BA of (mean >= tau) vs (truth >= tau) on test runs with a finite response, both recalls, error; BA-AULC B8-B40;
  sustained budget-to-target BA >= 0.95 x BA_full(M0) on {8, 12, ..., 36}, censored at 44;
  collection: share of paid post-start runs inside the boundary band |y - tau| <= 0.25 (finite paid responses), and share
  of the pool's minority-side runs paid by B40. Learning and collection are reported separately.
Label: BA at p >= 0.5, sensitivity, specificity, q20 accuracy (fold mean), short-K captured / total (the ten frozen NEW
  short-K runs), Brier, log loss, AUC — src/jdl_evaluate.wmetrics with unit weights (no bootstrap here).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_campaign as C
import src.rc18_common as RC

BAND = 0.25


def _units(d, pop):
    U = {}
    for p in (d / "units").glob(f"{pop}__*.json.gz"):
        u = RC.read_json_gz(p); U[(u.get("model"), u.get("acq", u.get("arm")), u["repeat"], u["fold"])] = u
    return U


def sustained(curve, level, grid, censor):
    for i, g in enumerate(grid[:-1]):
        if curve.get(g, -9) >= level and curve.get(grid[i + 1], -9) >= level:
            return g
    return censor


def eval_reg(d, pops, repeats, full=None):
    rows = []
    for pop in pops:
        Tt = C.targets(pop); ref = {c: float(np.nanmean(Tt[c])) for c in C.ALL_T}
        R2F = full[pop] if full else C.full_r2(pop, repeats)
        U = _units(d, pop); combos = sorted({(m, a) for (m, a, _, _) in U})
        for (m, a) in combos:
            for c in C.ALL_T:
                lev = 0.9 * np.mean([R2F[(c, r)] for r in repeats if (c, r) in R2F])
                for r in repeats:
                    curve, aux = {}, {}
                    for b in range(0, C.B1 + 1):
                        yy, pp, ov = [], [], []
                        for f in (1, 2, 3, 4, 5):
                            u = U.get((m, a, r, f)); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                            if e is None or e["pred"].get(c) is None:
                                break
                            yv = Tt.reindex(u["test_ids"])[c].to_numpy(float); ok = np.isfinite(yv); P = e["pred"][c]
                            yy += list(yv[ok]); pp += list(np.asarray(P[0])[ok]); ov += list(np.asarray(P[2])[ok])
                        else:
                            yy, pp, ov = map(np.asarray, (yy, pp, ov))
                            curve[b] = float(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref[c]) ** 2))
                            aux[b] = (float(np.sqrt(np.mean((yy - pp) ** 2))), float(np.mean(np.abs(yy - pp) <= 1.645 * np.sqrt(ov))),
                                      float(np.mean(0.5 * np.log(2 * np.pi * ov) + 0.5 * (yy - pp) ** 2 / ov)))
                    if not curve:
                        continue
                    aulc = float(np.trapezoid([curve[b] for b in range(C.B0, C.B1 + 1)]) / (C.B1 - C.B0)) if all(b in curve for b in range(C.B0, C.B1 + 1)) else np.nan
                    rows.append({"pop": pop, "model": m, "acq": a, "target": c, "repeat": r, "level": lev, "R2_full_M0": R2F.get((c, r)),
                                 "R2_AULC": aulc, "budget_to_target": sustained(curve, lev, list(range(0, C.B1 + 1, 4)), 64),
                                 **{f"R2_B{b}": curve.get(b) for b in (0, 4, 8, 12, 16, 24, 40, 60)},
                                 **{f"RMSE_B{b}": aux[b][0] for b in (8, 24, 60) if b in aux}, **{f"cov90_B{b}": aux[b][1] for b in (8, 24, 60) if b in aux},
                                 **{f"nlpd_B{b}": aux[b][2] for b in (8, 24, 60) if b in aux}, "curve": curve})
    return pd.DataFrame(rows)


def eval_region(d, pops, repeats, response="vmax_spike_logratio", tau=C.SPIKE_TAU, bmax=40):
    rows = []
    for pop in pops:
        Tt = C.targets(pop); U = _units(d, pop); combos = sorted({(m, a) for (m, a, _, _) in U})
        TK = {(t["repeat"], t["fold"]): t for t in C.tasks(pop, repeats)}           # built once
        # BA_full of M0 (whole pool) per repeat
        full = {}
        for t in TK.values():
            ids = np.asarray(t["ids"]).astype(str); y = Tt.reindex(ids)[response].to_numpy(float); Z = C.zstd(t)
            L = t["pool"][np.isfinite(y[t["pool"]])]; g = C.G.GP().fit(Z[L], y[L]); m = g.predict(Z[t["test"]])[0]
            full.setdefault(t["repeat"], []).append((y[t["test"]], m))
        bafull = {}
        for r, z in full.items():
            yy = np.concatenate([a for a, _ in z]); mm = np.concatenate([b for _, b in z]); ok = np.isfinite(yy); tr = yy[ok] >= tau; pr = mm[ok] >= tau
            bafull[r] = 0.5 * (np.mean(pr[tr]) + np.mean(~pr[~tr]))
        lev = 0.95 * np.mean([bafull[r] for r in repeats if r in bafull])
        for (m, a) in combos:
            for r in repeats:
                curve, rec = {}, {}
                band_share, minority_paid = [], []
                for b in range(C.B0, bmax + 1):
                    yy, pp = [], []
                    for f in (1, 2, 3, 4, 5):
                        u = U.get((m, a, r, f)); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                        if e is None:
                            break
                        yv = Tt.reindex(u["test_ids"])[response].to_numpy(float); ok = np.isfinite(yv)
                        yy += list(yv[ok]); pp += list(np.asarray(e["mean"])[ok])
                    else:
                        yy, pp = np.asarray(yy), np.asarray(pp); tr, pr = yy >= tau, pp >= tau
                        curve[b] = float(0.5 * (np.mean(pr[tr]) + np.mean(~pr[~tr]))); rec[b] = (float(np.mean(pr[tr])), float(np.mean(~pr[~tr])), float(np.mean(pr != tr)))
                for f in (1, 2, 3, 4, 5):
                    u = U.get((m, a, r, f))
                    if u is None:
                        continue
                    yp = Tt.reindex(u["paid_ids"][C.B0:])[response].to_numpy(float); yp = yp[np.isfinite(yp)]
                    band_share.append(float(np.mean(np.abs(yp - tau) <= BAND)) if len(yp) else np.nan)
                    t = TK[(r, f)]; ids = np.asarray(t["ids"]).astype(str)
                    yall = Tt.reindex(ids[t["pool"]])[response].to_numpy(float); side = (yall >= tau) if np.nanmean(yall >= tau) < 0.5 else (yall < tau)
                    mem = set(ids[t["pool"]][side & np.isfinite(yall)]); minority_paid.append(len(mem & set(u["paid_ids"])) / max(1, len(mem)))
                if not curve:
                    continue
                rows.append({"pop": pop, "model": m, "acq": a, "repeat": r, "BA_full_M0": bafull.get(r), "level": lev,
                             "BA_AULC": float(np.trapezoid([curve[b] for b in range(C.B0, bmax + 1)]) / (bmax - C.B0)) if len(curve) == bmax - C.B0 + 1 else np.nan,
                             "budget_to_target": sustained(curve, lev, list(range(C.B0, bmax, 4)), bmax + 4),
                             **{f"BA_B{b}": curve.get(b) for b in (8, 12, 16, 24, 32, 40)},
                             **{f"recall_in_B{b}": rec[b][0] for b in (16, 40) if b in rec}, **{f"recall_out_B{b}": rec[b][1] for b in (16, 40) if b in rec},
                             "band_share_paid": float(np.nanmean(band_share)), "minority_paid_share_B40": float(np.mean(minority_paid)), "curve": curve})
    return pd.DataFrame(rows)


def eval_label(d, repeats, bmax=40):
    import src.jdl_evaluate as EV
    import src.jdl_stage_m as SMM
    pop = "NEW"; T = C.tasks(pop, repeats); ids = np.asarray(T[0]["ids"]).astype(str); y = np.asarray(T[0]["y"], int)
    sk = np.isin(ids, list(SMM.shortk(SMM.inputs_table()))); U = _units(d, pop); arms = sorted({a for (_, a, _, _) in U})
    rows = []
    for a in arms:
        for r in repeats:
            fold = np.zeros(len(ids), int); q20 = np.zeros(len(ids), bool)
            for t in T:
                if t["repeat"] == r:
                    fold[t["test"]] = t["fold"]; q20[t["test"]] = t["q20"]
            for b in range(C.B0, bmax + 1):
                p = np.full(len(ids), np.nan); okb = True
                for t in T:
                    if t["repeat"] != r:
                        continue
                    u = U.get((None, a, r, t["fold"]))
                    if u is None:
                        okb = False; break
                    e = {x["budget"]: x for x in u["evals"]}.get(b)
                    if e is None:
                        okb = False; break
                    p[t["test"]] = e["p"]
                if not okb:
                    continue
                av = np.isfinite(p); m = EV.wmetrics(np.where(av, p, 0.5), av, y, sk, q20, fold, np.ones((1, len(ids))))
                rows.append({"arm": a, "repeat": r, "budget": b, **{k: float(v[0]) for k, v in m.items()},
                             "shortK_captured": int(np.sum((np.where(av, p, 0.5) >= 0.5) & sk)), "shortK_total": int(sk.sum())})
    return pd.DataFrame(rows)
