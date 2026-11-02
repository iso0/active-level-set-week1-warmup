"""GT QT-B (PROTOCOL_GT.md section 5): can the first part of a STARTED run predict its label, and does temperature add beyond the known
settings and the early depth? Run-level analysis, separate from the active learner. Every feature is causal (rows with time <= t only;
src.gt_data GT_EARLY); the first K frame and the label are evaluator-only.

Population: runs with valid bounds AND the maximum-temperature channel (485 of 541; exclusions listed). Seeded label-stratified split
(numpy default_rng([20261102, 7])): DEV half (5 x 10-fold run-level CV, seeds [20261102, 8, rep]); VAL half opened only if the
registered benefit rule passes on DEV. Models (L2 logistic, C = 1, standardised on the training folds only):
  S      z_h (settings)                        S+T    + Tmax, Tnow (kK)
  S+D    + log1p Dmax, log1p Dnow              S+D+T  + both
  C1p    C1's classifier on [z_h, D_hat], D_hat from C1's depth GP fitted on the training runs only (inner honest K = 10 OOF; repeat 1)
TB-INFO at t_c in {0.50, 0.75, 1.00} ms. TB-TIME: alarm at the first 25-us grid time with P_t > pi_hi, pi_hi chosen inside each training
fold by nested 5-fold CV so that at most 5 % (secondary 2 %) of the fold's conduction runs ever alarm over ALL grid times up to their end.
    python -m src.gt_tb dev | val
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import concurrent.futures
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

import src.gt_data as GD
import src.rc18_common as RC
import src.rc19_pool as P

OUT = GD.OUT / "temporal"
TC = (0.50, 0.75, 1.00)
MODELS = ("S", "S+T", "S+D", "S+D+T")
REPS = 5; FOLDS = 10; INNER = 5; FAR = (0.05, 0.02); B_BOOT = 2000


def population():
    M = P.manifest(); R = GD.runs().reindex(M.index); E = GD.early()
    ok = (R.T_status == "ok").to_numpy() & (R.failure.fillna("") == "").to_numpy()
    ex = pd.DataFrame({"batch": M.source_batch, "y": M.y, "T_status": R.T_status.fillna("NA"), "failure": R.failure.fillna("")})[~ok]
    excl = {"n": int((~ok).sum()), "by_batch_label": ex.groupby(["batch", "y"]).size().rename("n").reset_index().to_dict("records"),
            "reasons": ex.T_status.value_counts().to_dict()}
    idx = np.flatnonzero(ok); y = M.y.to_numpy(int)[idx]
    rng = np.random.default_rng([20261102, 7]); dev = np.zeros(len(idx), bool)
    for c in (0, 1):
        k = np.flatnonzero(y == c); k = k[rng.permutation(len(k))]; dev[k[: len(k) // 2]] = True
    lx = np.log(M[list(P.INPUTS)].to_numpy(float)); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]
    pos = {str(s): i for i, s in enumerate(E["ids"])}; ei = np.array([pos[str(s)] for s in M.index[idx]])
    D = {"ids": M.index.to_numpy(str)[idx], "y": y, "h": h[idx], "dev": dev, "TE": M.TE_ms.to_numpy(float)[idx], "firstK": R.first_K_ms.to_numpy(float)[idx],
         "shortK": M.shortK_pooled.to_numpy(bool)[idx], "newcond": ((M.source_batch == "NEW") & (M.y == 0)).to_numpy()[idx],
         "batch": M.source_batch.to_numpy(str)[idx], "Z": None, "row": idx}
    for f in GD.FEATS:
        D[f] = E[f][ei]
    D["grid"] = E["grid_ms"]
    return D, excl


def feats(D, k, model, rows):
    h = D["h"][rows][:, None]
    if model == "S":
        return h
    T = np.c_[D["Tmax"][rows, k], np.where(np.isfinite(D["Tnow"][rows, k]), D["Tnow"][rows, k], D["Tmax"][rows, k])] / 1000.0
    Dd = np.c_[np.log1p(D["Dmax"][rows, k]), np.log1p(D["Dnow"][rows, k])]
    return {"S+T": np.c_[h, T], "S+D": np.c_[h, Dd], "S+D+T": np.c_[h, Dd, T]}[model]


def fit_pred(Xtr, ytr, Xte):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Xtr = (Xtr - mu) / sd; Xte = (Xte - mu) / sd
    Xtr = np.where(np.isfinite(Xtr), Xtr, 0.0); Xte = np.where(np.isfinite(Xte), Xte, 0.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LogisticRegression(C=1.0, max_iter=2000).fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1]


def folds_of(y, k, seed):
    rng = np.random.default_rng(seed); f = np.empty(len(y), int)
    for c in (0, 1):
        i = np.flatnonzero(y == c); i = i[rng.permutation(len(i))]; f[i] = np.arange(len(i)) % k
    return f


def available(D, rows, k):
    return (D["grid"][k] <= D["TE"][rows] + 1e-9) & (D["avail"][rows, k] > 0.5)


def series(D, model, tr, te):
    """P_t for rows te at every grid time from a model fitted on tr at the same time (NaN after a run's end)."""
    G = len(D["grid"]); out = np.full((G, len(te)), np.nan)
    for k in range(G):
        a_tr = tr[available(D, tr, k)]; a_te = available(D, te, k)
        if model == "S":
            if k == 0:
                p = fit_pred(feats(D, 0, "S", tr), D["y"][tr], feats(D, 0, "S", te)); out[:] = p[None, :]
            break
        if len(set(D["y"][a_tr])) < 2 or not a_te.any():
            continue
        out[k, a_te] = fit_pred(feats(D, k, model, a_tr), D["y"][a_tr], feats(D, k, model, te[a_te]))
    if model == "S":
        for k in range(G):
            out[k, ~available(D, te, k)] = np.nan
    return out


def threshold(maxp_cond, far):
    v = np.sort(maxp_cond[np.isfinite(maxp_cond)])
    if not len(v):
        return 1.0
    return float(np.quantile(v, 1.0 - far, method="higher"))


def alarm_job(args):
    D, model, rep = args
    rows = np.flatnonzero(D["dev"]); y = D["y"][rows]; f = folds_of(y, FOLDS, [20261102, 8, rep]); G = len(D["grid"])
    Pfull = np.full((G, len(rows)), np.nan); thr = {far: np.full(len(rows), np.nan) for far in FAR}
    for j in range(FOLDS):
        tr, te = rows[f != j], rows[f == j]
        Pfull[:, f == j] = series(D, model, tr, te)
        fi = folds_of(D["y"][tr], INNER, [20261102, 9, rep, j]); Pin = np.full((G, len(tr)), np.nan)
        for i in range(INNER):
            Pin[:, fi == i] = series(D, model, tr[fi != i], tr[fi == i])
        mx = np.nanmax(np.where(np.isfinite(Pin), Pin, -np.inf), axis=0); cond = D["y"][tr] == 0
        for far in FAR:
            thr[far][f == j] = threshold(mx[cond], far)
    return {"model": model, "rep": rep, "P": Pfull, "thr": thr, "rows": rows}


def c1p_job(args):
    """C1's classifier on [z_h, D_hat] with C1's depth GP fitted on the training runs (inner honest K = 10 OOF), repeat 1, all t (static)."""
    D, rep = args
    import src.ea_cand as CA
    import src.ea_diag as DG
    rows = np.flatnonzero(D["dev"]); y = D["y"][rows]; f = folds_of(y, FOLDS, [20261102, 8, rep]); out = np.full(len(rows), np.nan)
    M = P.manifest(); task = {"ids": M.index.to_numpy(str), "X": M[list(P.INPUTS)].to_numpy(float), "pool": D["row"][rows]}
    Z = P.zstd(task); lx = np.log(task["X"]); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; hz = (h - h[task["pool"]].mean()) / h[task["pool"]].std()
    logA = M.log_A_um.to_numpy(float); W = np.where(M.short_record.to_numpy(bool), 1e4, 1.0)
    for j in range(FOLDS):
        tr, te = D["row"][rows[f != j]], D["row"][rows[f == j]]; ytr = D["y"][rows[f != j]]
        trg = tr[np.isfinite(logA[tr])]; fi = np.arange(len(trg)) % 10; F = np.full(len(tr), np.nan); Fmap = {}
        for i in range(10):
            a, b_ = trg[fi != i], trg[fi == i]
            g = CA.gp_fit(Z[a], logA[a], hz[a][:, None], W[a], "phys", True, CA.STARTS); Fmap.update(dict(zip(b_, g.predict(Z[b_], Hs=hz[b_][:, None])[0])))
        g = CA.gp_fit(Z[trg], logA[trg], hz[trg][:, None], W[trg], "phys", True, CA.STARTS)
        for i_, r in enumerate(tr):
            F[i_] = Fmap.get(r, g.predict(Z[[r]], Hs=hz[[r]][:, None])[0][0])
        Ete = g.predict(Z[te], Hs=hz[te][:, None])[0]
        out[f == j] = DG.lin(F, hz[tr], ytr, Ete, hz[te])
    return {"rep": rep, "p": out}


def metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6); ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    se = float(((p >= 0.5) & (y == 1)).sum() / max(1, (y == 1).sum())); sp = float(((p < 0.5) & (y == 0)).sum() / max(1, (y == 0).sum()))
    auc = float(roc_auc_score(y, p)) if len(set(y)) == 2 else np.nan
    return {"n": int(len(y)), "ll": ll, "auc": auc, "BA": 0.5 * (se + sp), "sens": se, "spec": sp, "brier": float(np.mean((p - y) ** 2))}


def boot_diff(a, b, seed=2024):
    d = np.asarray(a, float) - np.asarray(b, float); d = d[np.isfinite(d)]; rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B_BOOT, len(d)))].mean(1)
    return {"mean": float(d.mean()), "lo95": float(np.quantile(m, 0.025)), "hi95": float(np.quantile(m, 0.975)), "n": int(len(d))}


def run_dev(workers=6):
    RC.limit_threads(1); t0 = time.time(); D, excl = population()
    jobs = [(D, m, r) for m in MODELS for r in range(REPS)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        fut_c1 = ex.submit(c1p_job, (D, 0)); res = list(ex.map(alarm_job, jobs)); c1 = fut_c1.result()
    rows = res[0]["rows"]; y = D["y"][rows]; G = D["grid"]; kc = {t: int(np.flatnonzero(np.isclose(G, t))[0]) for t in TC}
    PR = {m: np.stack([r["P"] for r in sorted([r for r in res if r["model"] == m], key=lambda r: r["rep"])]) for m in MODELS}   # (rep, time, run)
    P_ = {m: np.nanmean(PR[m], 0) for m in MODELS}
    out = {"utc": RC.utc(), "population": {"n_runs": int(len(D["y"])), "dev": int(D["dev"].sum()), "val_closed": int((~D["dev"]).sum()),
                                           "dev_keyhole": int(y.sum()), "excluded": excl}, "info": {}, "time": {},
           "note": "INFO metrics = mean over the 5 CV repeats; run-level contrasts = per-run log loss averaged over repeats; C1p = repeat 1"}

    def rep_metrics(m, k, msk):
        if m == "C1p":
            return metrics(y[msk], c1["p"][msk])
        per = [metrics(y[msk], PR[m][r, k][msk]) for r in range(PR[m].shape[0])]
        return {key: (float(np.nanmean([q[key] for q in per])) if key != "n" else per[0]["n"]) for key in per[0]}
    # ---------------- TB-INFO
    for t, k in kc.items():
        avail = np.all(np.isfinite(PR["S+D+T"][:, k]), 0) & np.all(np.isfinite(PR["S+D"][:, k]), 0)
        blk = {m: rep_metrics(m, k, avail) for m in MODELS + ("C1p",)}

        def rll(m):
            p = np.clip(PR[m][:, k][:, avail], 1e-6, 1 - 1e-6); yy = y[avail][None, :]; return (-(yy * np.log(p) + (1 - yy) * np.log(1 - p))).mean(0)
        blk["d_ll_SDT_minus_SD"] = boot_diff(rll("S+D+T"), rll("S+D")); blk["d_ll_ST_minus_S"] = boot_diff(rll("S+T"), rll("S")); blk["d_ll_SD_minus_S"] = boot_diff(rll("S+D"), rll("S"))
        fk = D["firstK"][rows]; ps = P_["S"][k]
        near = avail & (np.abs(ps - 0.5) <= np.nanquantile(np.abs(ps[avail] - 0.5), 0.20))
        strata = {"keyhole_K_before_tc": avail & (y == 1) & (fk <= t), "keyhole_K_after_tc": avail & (y == 1) & ~(fk <= t),
                  "shortK": avail & D["shortK"][rows] & (y == 1), "NEW_conduction": avail & D["newcond"][rows], "near_boundary_20pct": near,
                  "TE_1.25": avail & (D["TE"][rows] < 2)}
        blk["strata"] = {s: ({m: rep_metrics(m, k, msk) for m in MODELS + ("C1p",)} if msk.sum() >= 3 else {"n": int(msk.sum())}) for s, msk in strata.items()}
        out["info"][f"{t:.2f}"] = blk
    out["info_rule"] = {"passes_at_times": [t for t in out["info"] if out["info"][t]["d_ll_SDT_minus_SD"]["mean"] <= -0.010 and out["info"][t]["d_ll_SDT_minus_SD"]["hi95"] < 0]}
    out["info_rule"]["pass"] = bool(len(out["info_rule"]["passes_at_times"]) >= 2)
    # ---------------- TB-TIME (alarms)
    TE = D["TE"][rows]; fK = D["firstK"][rows]; ifr = D["ifrac"][rows]; per_run = {}
    for far in FAR:
        blk = {}
        for m in MODELS:
            tr_runs = []
            for r in [r for r in res if r["model"] == m]:
                Pm, th = r["P"], r["thr"][far]; hit = np.where(np.isfinite(Pm), Pm > th[None, :], False)
                first = np.where(hit.any(0), hit.argmax(0), -1)
                ta = np.where(first >= 0, np.where(m == "S", 0.0, G[np.maximum(first, 0)]), np.nan)
                frac = np.where(first >= 0, ta / TE, 1.0)
                itf = np.where(first >= 0, np.where(m == "S", 0.0, ifr[np.arange(len(rows)), np.maximum(first, 0)]), 1.0)
                tr_runs.append({"alarm": first >= 0, "t_alarm": ta, "frac": frac, "ifrac": itf})
            al = np.mean([x["alarm"] for x in tr_runs], 0); fr = np.mean([x["frac"] for x in tr_runs], 0); itf = np.nanmean([x["ifrac"] for x in tr_runs], 0)
            ta_med = np.nanmedian(np.stack([x["t_alarm"] for x in tr_runs]), 0)
            warn = fK - ta_med; kh = y == 1
            blk[m] = {"capture": float(al[kh].mean()), "false_alarm": float(al[~kh].mean()), "time_read_all": float(fr.mean()), "time_read_keyhole": float(fr[kh].mean()),
                      "iter_read_all": float(np.nanmean(itf)), "warning_ms_median": float(np.nanmedian(warn[kh & np.isfinite(warn)])) if (kh & np.isfinite(warn)).any() else np.nan,
                      "warning_ms_q25_q75": [float(np.nanquantile(warn[kh & np.isfinite(warn)], q)) for q in (0.25, 0.75)] if (kh & np.isfinite(warn)).any() else None,
                      "alarm_before_first_K_share_of_captured": float(np.mean(warn[kh & np.isfinite(warn)] > 0)) if (kh & np.isfinite(warn)).any() else np.nan,
                      "shortK_capture": float(al[kh & D["shortK"][rows]].mean()) if (kh & D["shortK"][rows]).any() else np.nan,
                      "missed_keyhole_firstK_ms": sorted([float(v) for v in fK[kh & (al < 0.5)] if np.isfinite(v)]),
                      "NEW_conduction_false_alarm": float(al[D["newcond"][rows]].mean()) if D["newcond"][rows].any() else np.nan}
            per_run[(far, m)] = fr
        blk["d_time_read_SDT_minus_SD"] = boot_diff(per_run[(far, "S+D+T")], per_run[(far, "S+D")])
        blk["d_time_read_ST_minus_S"] = boot_diff(per_run[(far, "S+T")], per_run[(far, "S")])
        out["time"][f"FAR_{far}"] = blk
    b5 = out["time"]["FAR_0.05"]
    out["time_rule"] = {"pass": bool(b5["d_time_read_SDT_minus_SD"]["mean"] <= -0.03 and b5["d_time_read_SDT_minus_SD"]["hi95"] < 0
                                     and b5["S+D+T"]["capture"] >= b5["S+D"]["capture"] - 0.02 and b5["S+D+T"]["false_alarm"] <= 0.05 and b5["S+D"]["false_alarm"] <= 0.05)}
    out["benefit"] = bool(out["info_rule"]["pass"] or out["time_rule"]["pass"])
    out["decision"] = "TEMPERATURE-B: EXTRA BENEFIT ON DEV -> VAL half opened" if out["benefit"] else "TEMPERATURE-B: NO EXTRA BENEFIT (VAL closed; no time-model campaign)"
    out["seconds"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TB_DEV_RESULT.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    np.savez_compressed(OUT / "TB_DEV_PREDICTIONS.npz", ids=np.asarray(D["ids"][rows], str), y=y, grid_ms=G, c1p=c1["p"],
                        **{f"P_{m.replace('+', '')}": P_[m].astype(np.float32) for m in MODELS})
    print(json.dumps({"info_rule": out["info_rule"], "time_rule": out["time_rule"], "decision": out["decision"], "seconds": out["seconds"]}, indent=1))


if __name__ == "__main__":
    {"dev": run_dev}[sys.argv[1]]()
