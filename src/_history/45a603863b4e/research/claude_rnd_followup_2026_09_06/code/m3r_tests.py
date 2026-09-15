"""Section 7: M3R (label-flip-robust M3) same-path tests.

M3R definition: identical Stage-1 physics mean (frozen logistic on standardised log h of the
revealed rows) and identical Stage-2 ARD Matern-3/2 kernel; Stage-2 likelihood replaced by the
symmetric contamination mixture  p(y=1|f) = eps + (1-2 eps) sigma(f)  (Kim & Ghahramani 2008 form
with a logistic link).  For a deterministic simulator eps is NOT physical noise; it is a global
prior probability that a revealed label is inconsistent with the smooth latent (annotation /
provenance / model-discrepancy contamination).  Mode = "fixedhyper": kernel hyperparameters taken
from the M3 fit at the same state (same posterior geometry, only the likelihood changes);
mode = "ml2": hyperparameters re-optimised under the robust likelihood (checkpoint budgets only).
Paths: A0 (Phase 1.8), P1 (M3-margin), oracle paths (8 runs), full-324 fits.
"""
import sys, json, math, time, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd")
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler
from core import *
from m3r import M3R

d = Data(); pop = d.population; y = d.labels; lh = d.logh; x4 = d.x4
per = pd.read_csv("/home/claude/rnd/results/diag_fulltrain_pointwise.csv").set_index("idx"); exc = set(per[per.err >= .5].index)
paths = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz")
P1 = {r: g.sort_values("query_order").population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq("P1")].groupby("run_id")}
ORA = {p["run_id"]: p["path"] for p in json.load(open("/home/claude/rnd/results/oracle_greedy_paths.json"))}
EPS = (0.0, 0.02, 0.05, 0.1)
MODE = sys.argv[1] if len(sys.argv) > 1 else "fixedhyper"


def m3r_from_m3(m3fit, X, mean_tr, yy, eps, optimize=False):
    k = m3fit.gp.kernel_; var = float(k.k1.constant_value); ls = np.ravel(k.k2.length_scale).astype(float)
    m = M3R(eps=max(eps, 1e-9), optimize=optimize)
    if not optimize:
        m.theta = np.r_[0.5 * math.log(var), np.log(ls)]
        m.X, m.mean_, m.y = X, mean_tr, yy; m.K = m._K(X, X, m.theta) + 1e-8 * np.eye(len(yy))
        m.f, m.alpha, m.w, m.sw, m.L, m.lml = m._mode(m.K, mean_tr, yy, return_all=True)
        return m
    m.init = (math.sqrt(var), 1.0); return m.fit(X, mean_tr, yy)


def evaluate(spec, revealed, b, eps_list, optimize):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    rev = np.asarray(revealed, int); m3 = M3(d, spec).fit(rev, b); fit = m3.fit_
    X = fit.x_scaler.transform(x4); mean_all = fit.physics.latent(lh)
    out = []
    p_m3 = m3.proba(te)
    for eps in eps_list:
        m = m3r_from_m3(fit, X[rev], mean_all[rev], y[rev], eps, optimize); pr = m.proba(X[te], mean_all[te])
        row = {"budget": b, "eps": eps}
        for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", fl["B1_q20"]), ("B1_q30", fl["B1_q30"])):
            mv = metric_values(y[te][flag], pr[flag]); row.update({f"{subset}_{k}": v for k, v in mv.items() if k in ("accuracy", "balanced_accuracy", "keyhole_recall")})
        ex = np.array([t in exc for t in te]); row["exception_acc"] = float(((pr[ex] >= .5) == y[te][ex]).mean()) if ex.any() else np.nan; row["ordinary_acc"] = float(((pr[~ex] >= .5) == y[te][~ex]).mean())
        row["brier_full"] = float(np.mean((pr - y[te]) ** 2)); row["agree_with_m3_decisions"] = float(((pr >= .5) == (p_m3 >= .5)).mean())
        if optimize: row["sd"] = math.exp(m.theta[0]); row["ls"] = np.exp(m.theta[1:]).round(3).tolist()
        out.append(row)
    return out


def run_paths(spec):
    rows = []
    for name, path in (("A0", d.a0[spec.run_id]), ("P1", P1[spec.run_id])):
        for b in BUDGETS:
            for r in evaluate(spec, path[:b], b, EPS, False): rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "path": name, **r})
    if spec.run_id in ORA:
        for b in BUDGETS:
            for r in evaluate(spec, ORA[spec.run_id][:b], b, EPS, False): rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "path": "ORACLE", **r})
    for r in evaluate(spec, np.asarray(spec.train_indices), 324, EPS, False): rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "path": "FULL324", **r})
    return rows


def run_ml2(spec):
    rows = []
    for b in (16, 24, 32, 40, 60, 80):
        for r in evaluate(spec, P1[spec.run_id][:b], b, (0.0, 0.05), True): rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "path": "P1", **r})
    return rows


if __name__ == "__main__":
    t0 = time.time()
    if MODE == "fixedhyper":
        out = Parallel(n_jobs=2, verbose=5)(delayed(run_paths)(s) for s in d.specs)
        pd.DataFrame([r for rows in out for r in rows]).to_csv("/home/claude/rnd/followup/results/m3r_fixedhyper.csv.gz", index=False)
    else:
        specs = [s for s in d.specs if s.fold == ((s.repeat - 1) % 5) + 1]
        out = Parallel(n_jobs=2, verbose=5)(delayed(run_ml2)(s) for s in specs)
        pd.DataFrame([r for rows in out for r in rows]).to_csv("/home/claude/rnd/followup/results/m3r_ml2.csv.gz", index=False)
    print("elapsed", time.time() - t0)
