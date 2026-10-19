"""RC19 evaluator (reads checkpointed units; never fits a learner). Test predictions of one repeat are pooled over its 5 folds
(every run is a test point exactly once per repeat).

Regression: R2(b) = 1 - SSE/SST over the repeat's test runs (SST around the mean of all finite truths), 90 % observation
  coverage, NLPD; R2-AULC = mean R2 over the recorded budgets B8..Bmax; target endpoints with an ABSOLUTE level L:
  first qualifying budget = first recorded b with R2(b) >= L; confirmed budget = first b with R2(b) >= L and R2(b+4) >= L (the
  confirmation spends up to b+4; the last pair of the horizon IS tested). If not reached: censored at the horizon (no number
  is imputed; completion rates are reported). Joint endpoint = the same rule applied to min over the required outputs.
Region: BA(b) of {mu >= tau} vs the test truth, both recalls, BA-AULC over B8..Bmax, target endpoints as above with an
  absolute BA level; collection = share of post-startup paid runs inside |y - tau| <= 0.25 (paid truth) and share of the
  pool's minority side paid by the horizon.
Label: BA at p >= 0.5, sensitivity (Keyhole recall), specificity (conduction recall), AUC, Brier, log loss, q20 BA,
  short-Keyhole captured/total (pooled rule and the NEW-only original set).
Diagnostics by source batch (evaluator only): the same metrics on each batch's test runs, to expose a failed corner.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P

Z90 = 1.6448536269514722


def load_units(d):
    rows = []
    for p in sorted((d / "units").glob("*.json.gz")):
        rows.append(RC.read_json_gz(p))
    return rows


def _truth(M, ids, col):
    return M.reindex(ids)[col].to_numpy(float)


# ======================================================================================== regression
def reg_curves(units, M):
    """-> DataFrame rows: model, acq, repeat, target, budget, R2, cov90, nlpd, n (pooled over the 5 folds)."""
    acc = {}
    for u in units:
        key = (u["model"], u["acq"], u["repeat"])
        for e in u["evals"]:
            for c in P.TARGETS:
                pr = e["pred"].get(c)
                y = _truth(M, u["test_ids"], c)
                m = np.full(len(y), np.nan) if pr is None else np.asarray([np.nan if v is None else v for v in pr[0]], float)
                v = np.full(len(y), np.nan) if pr is None else np.asarray([np.nan if v_ is None else v_ for v_ in pr[1]], float)
                a = acc.setdefault((key, c, e["budget"]), [[], [], [], 0])
                a[0].append(y); a[1].append(m); a[2].append(v); a[3] += 1
    rows = []
    for (key, c, b), (ys, ms, vs, nf) in acc.items():
        y, m, v = np.concatenate(ys), np.concatenate(ms), np.concatenate(vs); ok = np.isfinite(y)
        sst = np.sum((y[ok] - np.nanmean(M[c])) ** 2); pred_ok = ok & np.isfinite(m)
        r2 = 1 - np.sum((y[pred_ok] - m[pred_ok]) ** 2) / sst if pred_ok.sum() == ok.sum() and nf == 5 else np.nan
        sd = np.sqrt(np.maximum(v[pred_ok], 1e-300)); z = (y[pred_ok] - m[pred_ok]) / sd
        rows.append({"model": key[0], "acq": key[1], "repeat": key[2], "target": c, "budget": b, "folds": nf, "R2": r2,
                     "cov90": float(np.mean(np.abs(z) <= Z90)) if pred_ok.any() else np.nan,
                     "nlpd": float(np.mean(0.5 * np.log(2 * np.pi * sd ** 2) + 0.5 * z ** 2)) if pred_ok.any() else np.nan, "n": int(ok.sum())})
    return pd.DataFrame(rows).sort_values(["model", "acq", "repeat", "target", "budget"]).reset_index(drop=True)


def endpoint(curve, level, step=4):
    """curve: dict budget -> value (recorded budgets). Returns dict(first, confirmed, censored, horizon)."""
    bs = sorted(curve); hz = bs[-1]; first = next((b for b in bs if np.isfinite(curve[b]) and curve[b] >= level), None)
    conf = next((b for b in bs if b + step in curve and np.isfinite(curve[b]) and np.isfinite(curve[b + step]) and curve[b] >= level and curve[b + step] >= level), None)
    return {"first": first, "confirmed": conf, "confirm_spend": None if conf is None else conf + step, "censored": conf is None, "horizon": hz}


def reg_endpoints(R, levels, targets):
    """levels: {target: absolute R2 level}; joint endpoint over `targets` uses min_t R2_t(b) >= level_t <=> all targets."""
    out = []
    for (m, a, r), g in R.groupby(["model", "acq", "repeat"]):
        cur = {t: dict(zip(gt.budget, gt.R2)) for t, gt in g.groupby("target")}
        for t in targets:
            e = endpoint(cur[t], levels[t]); out.append({"model": m, "acq": a, "repeat": r, "target": t, "level": levels[t], **e,
                                                       "AULC": float(np.nanmean(list(cur[t].values())))})
        bs = sorted(cur[targets[0]]); joint = {b: min((cur[t][b] - levels[t]) for t in targets) for b in bs}
        e = endpoint(joint, 0.0); out.append({"model": m, "acq": a, "repeat": r, "target": "JOINT", "level": np.nan, **e,
                                              "AULC": float(np.nanmean([np.mean([cur[t][b] for t in targets]) for b in bs]))})
    return pd.DataFrame(out)


# ======================================================================================== region
def region_curves(units, M, tau):
    acc = {}
    for u in units:
        key = (u["model"], u["acq"], u["repeat"]); y = _truth(M, u["test_ids"], "vmax_spike_logratio")
        for e in u["evals"]:
            m = np.full(len(y), np.nan) if e["mean"] is None else np.asarray([np.nan if v is None else v for v in e["mean"]], float)
            a = acc.setdefault((key, e["budget"]), [[], [], 0]); a[0].append(y); a[1].append(m); a[2] += 1
    rows = []
    for (key, b), (ys, ms, nf) in acc.items():
        y, m = np.concatenate(ys), np.concatenate(ms); ok = np.isfinite(y); t = y[ok] >= tau; q = np.where(np.isfinite(m[ok]), m[ok] >= tau, ~t)  # missing prediction counts as wrong
        rin = float(np.mean(q[t])) if t.any() else np.nan; rout = float(np.mean(~q[~t])) if (~t).any() else np.nan
        rows.append({"model": key[0], "acq": key[1], "repeat": key[2], "budget": b, "folds": nf, "BA": 0.5 * (rin + rout) if nf == 5 else np.nan,
                     "recall_in": rin, "recall_out": rout, "n": int(ok.sum()), "n_in": int(t.sum())})
    return pd.DataFrame(rows).sort_values(["model", "acq", "repeat", "budget"]).reset_index(drop=True)


def region_collection(units, M, tau):
    rows = []
    for u in units:
        y = _truth(M, u["paid_ids"], "vmax_spike_logratio"); post = y[P.B0:]; ok = np.isfinite(post)
        rows.append({"model": u["model"], "acq": u["acq"], "repeat": u["repeat"], "fold": u["fold"],
                     "band_share_paid": float(np.mean(np.abs(post[ok] - tau) <= 0.25)) if ok.any() else np.nan,
                     "invalid_paid_share": float(np.mean(~np.isfinite(y))), "in_region_paid_share": float(np.mean(post[ok] >= tau)) if ok.any() else np.nan})
    return pd.DataFrame(rows)


# ======================================================================================== label
def label_metrics(units, M):
    from sklearn.metrics import roc_auc_score
    acc = {}
    for u in units:
        key = (u["arm"], u["repeat"]); ids = u["test_ids"]; H = M.reindex(ids)
        for e in u["evals"]:
            p = np.asarray([np.nan if v is None else v for v in e["p"]], float)
            a = acc.setdefault((key, e["budget"]), {"p": [], "y": [], "skp": [], "skn": [], "batch": [], "ids": [], "n": 0, "status": []})
            a["p"].append(p); a["y"].append(H.y.to_numpy(int)); a["skp"].append(H.shortK_pooled.to_numpy(bool)); a["skn"].append(H.shortK_NEW_original.to_numpy(bool))
            a["ids"].append(np.asarray(ids, str))
            a["batch"].append(H.source_batch.to_numpy(str)); a["n"] += 1; a["status"].append(e.get("status"))
    q20 = {}
    for t in P.tasks(sorted({k[1] for k, _ in acc})):
        for i, f in zip(t["test"], t["q20"]):
            q20[(t["repeat"], t["ids"][i])] = bool(f)
    rows = []
    for ((arm, r), b), a in acc.items():
        p = np.clip(np.concatenate(a["p"]), 1e-6, 1 - 1e-6); y = np.concatenate(a["y"]); hat = p >= 0.5
        sens = float(np.mean(hat[y == 1])); spec = float(np.mean(~hat[y == 0]))
        row = {"arm": arm, "repeat": r, "budget": b, "folds": a["n"], "BA": 0.5 * (sens + spec) if a["n"] == 5 else np.nan, "sensitivity": sens, "specificity": spec,
               "AUC": float(roc_auc_score(y, p)) if len(set(y)) == 2 else np.nan, "brier": float(np.mean((p - y) ** 2)),
               "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
               "shortK_pooled_captured": int(np.sum(hat & np.concatenate(a["skp"]))), "shortK_pooled_total": int(np.concatenate(a["skp"]).sum()),
               "shortK_NEW_captured": int(np.sum(hat & np.concatenate(a["skn"]))), "shortK_NEW_total": int(np.concatenate(a["skn"]).sum()),
               "one_class_folds": int(sum(s == "one_class" for s in a["status"])), "failed_fits": int(sum(str(s).startswith("fit_failed") for s in a["status"]))}
        qq = np.asarray([q20.get((r, s), False) for s in np.concatenate(a["ids"])], bool)
        if qq.any():
            s1 = np.mean(hat[qq & (y == 1)]) if (qq & (y == 1)).any() else np.nan; s0 = np.mean(~hat[qq & (y == 0)]) if (qq & (y == 0)).any() else np.nan
            row["q20_BA"] = 0.5 * (s1 + s0); row["q20_n"] = int(qq.sum())
        bt = np.concatenate(a["batch"])
        for bb in ("OLD", "NEW"):
            mm = bt == bb; s1 = np.mean(hat[mm & (y == 1)]) if (mm & (y == 1)).any() else np.nan; s0 = np.mean(~hat[mm & (y == 0)]) if (mm & (y == 0)).any() else np.nan
            row[f"BA_{bb}"] = 0.5 * (s1 + s0); row[f"sens_{bb}"] = s1; row[f"spec_{bb}"] = s0
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["arm", "repeat", "budget"]).reset_index(drop=True)
