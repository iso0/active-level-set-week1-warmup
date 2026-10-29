"""FR candidate GATE (PROTOCOL_FR_DEV.md, registered before any DEV gate result): a support-dependent trust combination of C1 and HA_LEAN
learned only from PAID runs and public inputs.

  p_GATE(x) = w(x) p_C1(x) + (1 - w(x)) p_A(x),   w(x) = sigmoid(a + c u(x)),   u(x) = clip(log(d(x, L) / s_L), -2, 2)
    p_C1 = src.ea_cand SYSTEMS["C1"] (unchanged), p_A = HA_LEAN (src.rc23_common.state, unchanged), both fitted on the full paid set L;
    d(x, L) = distance (public standardised log inputs, src.rc19_pool.zstd) from x to its nearest paid run; s_L = median nearest-neighbour
    spacing of the paid runs.
  (a, c) = MAP under a ~ N(0, 1.5^2), c ~ N(0, 1) of the Bernoulli likelihood of the paid labels under q_i = w_i p1_i + (1 - w_i) p2_i,
    with p1_i, p2_i NESTED out-of-fold predictions: the paid runs are split into G = 4 spatial groups (k-means on their public inputs,
    n_init 4, seed 0); for each group the FULL C1 and HA_LEAN pipelines (their own inner K = 10 cross-fits included) are refitted on the other
    groups only, so neither the label nor the depth nor any output of a held-out run enters its prediction; u_i uses the distance to those
    training runs and s_L.
  Refits at b = 16, 20, ..., 60; the latest fit is reused until the next refit (u(x) always from the current paid set).
  Data-insufficient rule: b < 16 or fewer than 4 depth-usable paid runs of either class at the refit -> w = 1 (C1 unchanged).
  One-class rule: both pipelines return the paid mean, so p_GATE is the same constant; margin then follows the label-free path (as C1).
  Missing depth: handled inside the unchanged pipelines (usable = finite depth) in every refit.
  AVG (control) = fixed w = 0.5. Reduction: force_w = 1 gives C1 exactly, force_w = 0 gives HA_LEAN exactly.
No test label, unopened output, campaign id, short-Keyhole or hard-group membership is read here.
    python -m src.fr_gate work <job> | list | smoke
"""
from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

import src.ea_cand as CA
import src.el_cross as X
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22
import src.rc23_common as C23

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness"
EA = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "exports"
G_OUT, B_GATE0, EVERY, MIN_CLASS, UCLIP = 4, 16, 4, 4, 2.0
PA, PC = (0.0, 1.5), (0.0, 1.0)
BUD = tuple(range(8, 61))


# ======================================================================================== the candidate
def spacing(Z, L):
    D = np.linalg.norm(Z[L][:, None, :] - Z[L][None, :, :], axis=2); np.fill_diagonal(D, np.inf); return float(np.median(D.min(1)))


def support(Z, L, rows, s):
    d = np.linalg.norm(Z[np.asarray(rows)][:, None, :] - Z[np.asarray(L)][None, :, :], axis=2).min(1)
    return np.clip(np.log(np.maximum(d, 1e-9) / s), -UCLIP, UCLIP)


def base(task, rev, Z, rows):
    """The two unchanged pipelines on one paid state."""
    p1, one1 = CA.predict(task, rev, Z, rows, CA.SYSTEMS["C1"]); o, info = C23.state(task, rev, Z, rows, which=("HA_LEAN",))
    return np.asarray(p1, float), np.asarray(o["HA_LEAN"], float), bool(one1 or info["one_class"])


def map_fit(p1, p2, u, y):
    p1 = np.clip(p1, 1e-6, 1 - 1e-6); p2 = np.clip(p2, 1e-6, 1 - 1e-6); y = np.asarray(y, float)

    def f(th):
        a, c = th; w = expit(a + c * u); q = np.clip(w * p1 + (1 - w) * p2, 1e-9, 1 - 1e-9)
        nll = -np.sum(y * np.log(q) + (1 - y) * np.log(1 - q)) + 0.5 * ((a - PA[0]) / PA[1]) ** 2 + 0.5 * ((c - PC[0]) / PC[1]) ** 2
        dq = -(y / q - (1 - y) / (1 - q)); dw = (p1 - p2) * w * (1 - w)
        return nll, np.array([np.sum(dq * dw) + (a - PA[0]) / PA[1] ** 2, np.sum(dq * dw * u) + (c - PC[0]) / PC[1] ** 2])
    r = minimize(f, np.zeros(2), jac=True, method="L-BFGS-B")
    return float(r.x[0]), float(r.x[1]), float(r.fun), bool(r.success)


def _ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _ba(p, y):
    h = p >= 0.5; return float(0.5 * (h[y == 1].mean() + (~h[y == 0]).mean())) if (y == 1).any() and (y == 0).any() else None


def gate_fit(task, rev, Z, M):
    L = np.asarray(rev.paid); y = rev.paid_y()[L].astype(int); usable = np.isfinite(rev.paid_A()[L]); b = len(L)
    n1, n0 = int(((y == 1) & usable).sum()), int(((y == 0) & usable).sum())
    if b < B_GATE0 or min(n1, n0) < MIN_CLASS:
        return {"status": "insufficient", "b": b, "n1_usable": n1, "n0_usable": n0}
    from sklearn.cluster import KMeans
    g = KMeans(n_clusters=G_OUT, n_init=4, random_state=0).fit_predict(Z[L]); s = spacing(Z, L)
    p1, p2, u = np.empty(b), np.empty(b), np.empty(b); one = 0
    for k in range(G_OUT):
        te = np.flatnonzero(g == k); tr = np.flatnonzero(g != k)
        if not len(te):
            continue
        rv = K._rev_with(task, M, L[tr])                       # only the other groups' paid runs are revealed to the refit
        a1, a2, o = base(task, rv, Z, L[te]); p1[te], p2[te] = a1, a2; one += int(o); u[te] = support(Z, L[tr], L[te], s)
    a, c, nll, ok = map_fit(p1, p2, u, y)
    return {"status": "fit", "b": b, "a": a, "c": c, "nll": nll, "converged": ok, "s": s, "groups": np.bincount(g, minlength=G_OUT).tolist(), "oof_one_class_groups": one,
            "u_min": float(u.min()), "u_max": float(u.max()), "oof_ll_C1": _ll(p1, y), "oof_ll_A": _ll(p2, y), "oof_ba_C1": _ba(p1, y), "oof_ba_A": _ba(p2, y),
            "n_disagree": int(((p1 >= 0.5) != (p2 >= 0.5)).sum()), "n1_usable": n1, "n0_usable": n0}


def gate_w(Z, L, rows, gp):
    if gp is None or gp.get("status") != "fit":
        return np.ones(len(rows))
    return expit(gp["a"] + gp["c"] * support(Z, L, rows, spacing(Z, L)))


def refit_due(b):
    return b >= B_GATE0 and (b - B_GATE0) % EVERY == 0


def _f32(a):
    return LN._f32(a)


def run_gate(task, M, bmax=60, force_w=None, M_hidden=None):
    """GATE + margin own path. force_w (1 / 0) = reduction check; M_hidden = an alternative hidden table (shadow test)."""
    Mh = M if M_hidden is None else M_hidden
    rev = K._rev_with(task, Mh, []); Z = P.zstd(task); C22.startup(task, rev); te = np.asarray(task["test"]); nt = len(te); evals, gates = [], []; gp = None
    t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); rows = np.r_[te, cands]; t1 = time.process_time(); cg = 0.0
        if force_w is None and refit_due(b):
            tg = time.process_time(); gp = gate_fit(task, rev, Z, Mh); cg = time.process_time() - tg; gp["cpu_s"] = cg; gates.append(gp)
        p1, p2, one = base(task, rev, Z, rows)
        w = np.full(len(rows), float(force_w)) if force_w is not None else gate_w(Z, rev.paid, rows, gp)
        p = w * p1 + (1.0 - w) * p2
        e = {"budget": b, "p": {"GATE": _f32(p[:nt]), "C1": _f32(p1[:nt]), "A": _f32(p2[:nt]), "AVG": _f32(0.5 * p1[:nt] + 0.5 * p2[:nt])},
             "w_test": _f32(w[:nt]), "one_class": one, "gate_fit_b": gp["b"] if gp else None, "gate_status": gp["status"] if gp else "insufficient", "cpu_gate_s": cg}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if one:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(p[nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    paid = list(rev.order)
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "construction": "GATE", "path": "GATE", "force_w": force_w, "paid": paid,
            "paid_ids": [task["ids"][i] for i in paid], "test_ids": [task["ids"][i] for i in te], "evals": evals, "gates": gates,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0}


def gate_on_path(task, M, paid_ids, budgets=BUD):
    """DEV model effect: the gate weights at the test runs along a RECORDED paid path (the base probabilities are the recorded ones)."""
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in paid_ids]; te = np.asarray(task["test"]); gp = None; ev, gates = [], []
    for b in budgets:
        rev = K._rev_with(task, M, paid[:b]); cg = 0.0
        if refit_due(b):
            tg = time.process_time(); gp = gate_fit(task, rev, Z, M); cg = time.process_time() - tg; gp["cpu_s"] = cg; gates.append(gp)
        ev.append({"budget": b, "w_test": _f32(gate_w(Z, rev.paid, te, gp)), "cpu_gate_s": cg})
    return {"evals": ev, "gates": gates}


# ======================================================================================== DEV replay units (recorded paths)
DEV_SRC = {("STD", "A"): ("validation_std", "HA_LEAN-selected"), ("STD", "C"): ("validation_std", "C1-selected"),
           ("K5", "A", "cand"): ("cand_dev_k5", "HA_LEAN-selected"), ("K5", "A"): ("validation_k5", "HA_LEAN-selected"), ("K5", "C"): ("validation_k5", "C1-selected"),
           ("K4", "A", "cand"): ("cand_dev_k4", "HA_LEAN-selected"), ("K4", "A"): ("validation_k4", "HA_LEAN-selected"), ("K4", "C"): ("validation_k4", "C1-selected")}


def dev_source(cond, cl, tag):
    if cond == "K5" and cl <= 40 or cond == "K4" and cl <= 24:
        return DEV_SRC[(cond, tag, "cand")]
    return DEV_SRC[(cond, tag)]


_PATHS = {}


def recorded_paid(cond, cl, l, tag):
    d, pre = dev_source(cond, cl, tag)
    if d not in _PATHS:
        _PATHS[d] = pd.read_csv(EA / d / "paths.csv.gz")
    T = _PATHS[d]; T = T[T.path.str.startswith(pre) & (T.cluster == cl) & (T.learner == l)].sort_values("query")
    if pre == "HA_LEAN-selected":
        T = T[~T.path.str.startswith("C1")]
    ids = T.sim_id.tolist()
    if len(ids) != 60:
        raise RuntimeError(f"recorded path {cond} {cl}/{l} {tag}: {len(ids)} ids")
    return ids


def dev_units():
    M = P.manifest(); y = M.y
    U = [(f"STD__r{r}_f{f}__{t}", ("STD", r, f, t)) for r in range(163, 183) for f in range(1, 6) for t in ("A", "C")]
    import src.rc24p_final as F
    lab5 = C22.blocks(M, 5); lab4 = F.blocks_k4(M)                 # public k-means regions; label check only skips one-class (BA-undefined) test regions
    two5 = [b for b in range(5) if y.to_numpy()[lab5 == b].min() != y.to_numpy()[lab5 == b].max()]
    two4 = [b for b in range(4) if y.to_numpy()[lab4 == b].min() != y.to_numpy()[lab4 == b].max()]
    U += [(f"K5__s{s}_b{b + 1}__{t}", ("K5", s, b + 1, t)) for s in range(33, 49) for b in two5 for t in (("A",) if s <= 40 else ("A", "C"))]
    U += [(f"K4__s{s}_b{b + 1}__{t}", ("K4", s, b + 1, t)) for s in range(17, 33) for b in two4 for t in (("A",) if s <= 24 else ("A", "C"))]
    return U


# ======================================================================================== fresh-test units (PROTOCOL_FR_FRESH.md)
FRESH_STD = tuple(range(383, 407)); FRESH_K5 = tuple(range(49, 61)); FRESH_K4 = tuple(range(33, 45))


def unit_L(task, M, bmax=60):
    """A = HA_LEAN + margin own path (src.rc23_common.run_arm, unchanged); on it at every budget D = HA_TREND (ML-II) via
    src.el_mix.mix_state p_T (the registered EL / EA definition of D_on_A), with the EA check that its p_L equals A's own predictions."""
    import src.el_mix as MX
    u = C23.run_arm(task, "HA_LEAN", M, bmax=bmax); Z = P.zstd(task); te = np.asarray(task["test"]); paid = list(u["paid"]); ev = []; chk = 0.0
    own = {e["budget"]: e["p"]["HA_LEAN"] for e in u["evals"]}
    for b in range(8, bmax + 1):
        rev = K._rev_with(task, M, paid[:b]); t0 = time.process_time(); s = MX.mix_state(task, rev, Z, te); c = time.process_time() - t0
        chk = max(chk, float(np.max(np.abs(np.asarray(LN._f32(s["p_L"]), float) - np.asarray(own[b], float)))))
        ev.append({"budget": b, "p": {"D": LN._f32(s["p_T"])}, "cpu_D": c, "one_class": bool(s["one_class"])})
    u["cross"] = ev; u["check_pL_vs_own_A_maxabs"] = chk; u["path"] = "HA_LEAN"; return u


def fresh_units(std=FRESH_STD, k5=FRESH_K5, k4=FRESH_K4):
    return ([(f"STD__r{r}_f{f}__{p}", ("STD", r, f, p)) for r in std for f in range(1, 6) for p in ("G", "X", "L")]
            + [(f"K5__s{s}_b{b}__{p}", ("K5", s, b, p)) for s in k5 for b in range(1, 6) for p in ("G", "X", "L")]
            + [(f"K4__s{s}_b{b}__{p}", ("K4", s, b, p)) for s in k4 for b in range(1, 5) for p in ("G", "X", "L")])


def units(job):
    if job == "fr-dev":
        return dev_units()
    if job == "fr-fresh":
        return fresh_units()
    if job == "fr-evalsmoke":                      # DEV IDs (already examined): evaluator dry run and unit cost; never part of a verdict
        return fresh_units((163,), (41,), (25,))
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    import src.ea_fwd as EF
    if job == "fr-fresh":
        import src.fr_freeze as FZ
        FZ.check(job)
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f, t) in S.items()}, M)

    def fn(name):
        c, r, f, t = S[name]; task = T[(c, r, f)]
        if job == "fr-dev":
            ids = recorded_paid(c, r, f, t); t0 = time.process_time(); res = gate_on_path(task, M, ids)
            return {"condition": c, "cluster": r, "learner": f, "path": t, "paid_ids": ids, "test_ids": [task["ids"][i] for i in task["test"]], **res, "cpu_s": time.process_time() - t0}
        u = run_gate(task, M, 60) if t == "G" else EF.unit_X(task, M, 60) if t == "X" else unit_L(task, M, 60)
        return {**u, "condition": c, "unit_kind": t}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


# ======================================================================================== smoke: reduction, shadow, cost
def smoke():
    import json
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); res = {}
    T = X.tasks_for({"a": (None, "STD", 163, 1), "b": (None, "K5", 41, 2)}, M); task = T[("STD", 163, 1)]
    uX = RC.read_json_gz(RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "ea-fwd" / "units" / "STD__r163_f1__X.json.gz")
    uL = RC.read_json_gz(RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "ea-fwd" / "units" / "STD__r163_f1__L.json.gz")
    r1 = run_gate(task, M, 60, force_w=1.0)
    res["reduce_w1_path_equals_C1_own"] = r1["paid_ids"] == uX["paid_ids"]
    res["reduce_w1_max_abs_p_vs_C1_own"] = float(max(np.max(np.abs(np.asarray(e["p"]["GATE"], float) - np.asarray(o["p"]["C1"], float))) for e, o in zip(r1["evals"], uX["evals"])))
    r0 = run_gate(task, M, 60, force_w=0.0)
    res["reduce_w0_path_equals_A_own"] = r0["paid_ids"] == uL["paid_ids"]
    res["reduce_w0_max_abs_p_vs_A_own"] = float(max(np.max(np.abs(np.asarray(e["p"]["GATE"], float) - np.asarray(o["p"]["HA_LEAN"], float))) for e, o in zip(r0["evals"], uL["evals"])))
    g = run_gate(task, M, 28); paid_set = set(g["paid"])
    Ms = M.copy(); rng = np.random.default_rng(7); hid = np.array([i not in paid_set for i in range(len(Ms))])
    Ms.loc[hid, "y"] = 1 - Ms.loc[hid, "y"].to_numpy(int)
    for col in ("A_um",) + tuple(P.TARGETS):
        if col in Ms.columns:
            v = Ms.loc[hid, col].to_numpy(float); Ms.loc[hid, col] = v[rng.permutation(len(v))] * 1.3 + 0.1
    gs = run_gate(task, M, 28, M_hidden=Ms)
    res["shadow_path_identical"] = gs["paid_ids"] == g["paid_ids"]
    res["shadow_max_abs_p"] = float(max(np.max(np.abs(np.asarray(a["p"]["GATE"], float) - np.asarray(b_["p"]["GATE"], float))) for a, b_ in zip(g["evals"], gs["evals"])))
    res["shadow_gate_params_identical"] = [(x.get("a"), x.get("c")) for x in g["gates"]] == [(x.get("a"), x.get("c")) for x in gs["gates"]]
    full = run_gate(task, M, 60); res["cost_STD_gate_own_path_cpu_s"] = full["cpu_s"]; res["gates_STD"] = full["gates"]
    tb = T[("K5", 41, 2)]; fb = run_gate(tb, M, 60); res["cost_K5_gate_own_path_cpu_s"] = fb["cpu_s"]; res["gates_K5"] = fb["gates"]
    d = OUT / "dev"; d.mkdir(parents=True, exist_ok=True)
    RC.atomic_write_json_gz(d / "SMOKE_runs.json.gz", {"w1": r1, "w0": r0, "shadow_ref": g, "shadow": gs, "own_std": full, "own_k5": fb})
    (d / "SMOKE.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(json.dumps({k: v for k, v in res.items() if not k.startswith("gates")}, indent=1, default=float))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("fr-dev",)})
    elif sys.argv[1] == "smoke":
        smoke()
