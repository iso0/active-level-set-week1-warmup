"""EA stage 1, amendment 1 diagnostics (PROTOCOL_EA_HYPOTHESES_AMENDMENT1.md, registered before they were computed).
  D2 (evaluator-only)  hyperparameter oracle: HA_LEAN's depth GP (src.rc24_pac flat = HA_LEAN emulator) with its hyperparameters FIXED at
                       the full-pool ML-II values, conditioned on the b paid depths only (honest K = 10 OOF + full fit, same fixed values);
                       the HA_LEAN classifier on top.
  D3 (deployable)      linear-in-z_h emulator: OLS of the good paid log depths on z_h, honest K = 10 OOF + full fit; same classifier.
  D4 (evaluator-defined region, diagnostic only)  corner-capped margin: an own HA_LEAN margin path from the same startup where candidates in
                       the RC21 fast-scan corner (VX > 0.85, P > 330) are removed once 4 corner runs are paid (4 = proportional share).
On the recorded HA_LEAN paths of STD repeats 83-122 (same startups and test folds as the ladder).
    python -m src.ea_diag2 work ea-theta | ea-diag2
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np

import src.ea_diag as DG
import src.el_cross as X
import src.rc18_campaign as C18
import src.rc18_common as RC
import src.rc18_gp as G
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_pac as PC

OUT = DG.OUT; DCOL = PC.DEPTH_COL; CAP = 4


def theta_full(M):
    ids = M.index.to_numpy(str); Xall = M[list(P.INPUTS)].to_numpy(float); n = len(ids)
    task = {"repeat": 0, "fold": 0, "ids": ids, "X": Xall, "pool": np.arange(n), "test": np.arange(0), "path": np.arange(n)}
    Z = P.zstd(task); rev = K._rev_with(task, M, np.arange(n)); f = PC.depth_fit(task, rev, Z, "flat")
    return {"theta": f["g"].theta.tolist(), "opt": f["g"].opt, "n": int(len(f["rows"]))}


def depth_fit_fixed(rev, Z, theta, rows):
    L = np.asarray(rows); Y = rev.paid_Y()[:, DCOL]; W = np.where(rev.paid_short(), C18.W_SHORT, 1.0); Lu = L[np.isfinite(Y[L])]
    if (W[Lu] <= 100).sum() < 3:
        return None
    g = G.GP(H_cols=0, b=PC.B_TREND).fit(Z[Lu], Y[Lu], H=None, w=W[Lu], theta0=np.asarray(theta, float), optimize=False)
    return {"g": g, "H": None, "rows": Lu}


def cf_generic(rev, Z, rows, fitter, predictor, Kf=A.KF):
    paid = rev.paid; Y = rev.paid_Y()[:, DCOL]; fold, k = K.folds(len(paid), Kf); F = np.full(len(paid), np.nan)
    for j in range(k):
        tr = paid[fold != j]; f = fitter(tr)
        if f is None:
            v = Y[tr]; v = v[np.isfinite(v)]; F[fold == j] = float(np.mean(v)) if len(v) else 0.0
        else:
            F[fold == j] = predictor(f, paid[fold == j])
    full = fitter(paid); E = predictor(full, rows) if full is not None else np.full(len(rows), np.nanmean(Y[paid]))
    return F, E


def linh_fit(rev, h, rows):
    L = np.asarray(rows); Y = rev.paid_Y()[:, DCOL]; good = np.isfinite(Y[L]) & ~rev.paid_short()[L]; L = L[good]
    if len(L) < 3:
        return None
    c = np.polyfit(h[L], Y[L], 1); return c


def run_capped(task, M, cap=CAP, bmax=60):
    corner = ((M.VX > 0.85) & (M.P > 330)).reindex(list(task["ids"])).to_numpy(bool)
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); nt = len(task["test"]); ev = []
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid)
        if corner[rev.paid].sum() >= cap:
            cands = cands[~corner[cands]]
        out, info = C23.state(task, rev, Z, np.r_[task["test"], cands], which=("HA_LEAN",)); e = {"budget": b, "p": LN._f32(out["HA_LEAN"][:nt]), "corner_paid": int(corner[rev.paid].sum())}
        ev.append(e)
        if b >= bmax:
            break
        nxt = LN.next_on_path(task, rev) if info["one_class"] else int(cands[int(np.argmax(-np.abs(out["HA_LEAN"][nt:] - 0.5)))]); rev.reveal(nxt)
    return {"evals": ev, "paid_ids": [task["ids"][i] for i in rev.order]}


def learner(task, unit, M, theta, budgets=DG.BUDS):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in unit["paid_ids"]]; te = np.asarray(task["test"]); h = A.hcol(task)
    recA = {e["budget"]: e["p"]["HA_LEAN"] for e in unit["evals"]}; out = []
    for b in budgets:
        t0 = time.process_time(); rev = K._rev_with(task, M, paid_all[:b]); L = rev.paid; y_p = rev.paid_y(); y = y_p[L]; A_p = rev.paid_A()
        usable = np.isfinite(A_p[L]); one = len(set(y_p[L][usable].tolist())) < 2; e = {"budget": b, "one_class": bool(one)}
        if one:
            c = np.full(len(te), float(np.mean(y))); e["p"] = {"D2_hp_oracle": LN._f32(c), "D3_lin_h": LN._f32(c)}
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                F2, E2 = cf_generic(rev, Z, te, lambda r: depth_fit_fixed(rev, Z, theta, r), lambda f, idx: PC.depth_predict(f, Z, idx)[0])
                F3, E3 = cf_generic(rev, Z, te, lambda r: linh_fit(rev, h, r), lambda c, idx: np.polyval(c, h[idx]))
                e["p"] = {"D2_hp_oracle": LN._f32(DG.lin(F2, h[L], y, E2, h[te])), "D3_lin_h": LN._f32(DG.lin(F3, h[L], y, E3, h[te]))}
                e["E2"] = LN._f32(E2); e["E3"] = LN._f32(E3)
        e["cpu_s"] = time.process_time() - t0; out.append(e)
    cap = run_capped(task, M)
    chk_start = cap["paid_ids"][:8] == unit["paid_ids"][:8]
    chk_same_until_cap = None
    return {"evals": out, "D4_capped": cap, "check_same_startup": bool(chk_start)}


def units(job):
    if job == "ea-theta":
        return [("THETA", ("theta",))]
    if job == "ea-diag2":
        return [(f"STD__r{r}_f{f}", ("diag2", "STD", r, f)) for r in range(83, 123) for f in range(1, 6)]
    if job == "ea-smoke2":
        return [("STD__r83_f1", ("smoke", "STD", 83, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    if job == "ea-theta":
        def fn(name):
            return theta_full(M)
    else:
        th = RC.read_json_gz(OUT / "ea-theta" / "units" / "THETA.json.gz")["theta"]; T = X.tasks_for({n: (None, v[1], v[2], v[3]) for n, v in S.items()}, M)

        def fn(name):
            kind, c, r, f = S[name]; task = T[(c, r, f)]; u = DG.path_unit(c, r, f)
            res = learner(task, u, M, th, budgets=(8, 12) if kind == "smoke" else DG.BUDS)
            return {"condition": c, "repeat": r, "fold": f, "test_ids": u["test_ids"], **res}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
