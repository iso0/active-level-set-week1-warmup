"""GT stages G3 / G4 (PROTOCOL_GT.md section 5): own query paths of the selected geometric system GEO* with a selector, and the fresh
validation units. GEO* and its selector are read from the frozen selection files written by the registered rules
(dev/G2_SELECTION.json for G3; freeze/G4_FREEZE.json for G4). Paid outcomes and public inputs only.
  selectors  margin    argmin |P - 0.5| (P = Phi(m / sqrt(v_obs)))
             straddle  argmax 1.96 sqrt(v_lat) - |m| on the g scale (Bryan et al. 2005)
             space     the next run of the task's label-free maximin path
  startup    the task's common 8-run label-free startup (paid, counted), as C1; a GP fallback (< 3 good rows) follows the label-free path
  cross      C1 predictions on the GEO* margin path at every budget (2 x 2 decomposition, G3 only)
G4 units: C = src.ea_fwd.unit_X unchanged (C1 + margin own path) + GEO* predictions on that recorded path (model effect, secondary);
          G = GEO* + selector own path.
    python -m src.gt_own work gt-own | gt-own-smoke | gt-val
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

import src.ea_cand as CA
import src.el_cross as X
import src.gt_geo as GG
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22

OUT = RC.ROOT / "outputs" / "research_campaign_20261102" / "opus_geometry_temperature"
DEV = {"STD": tuple(range(163, 203)), "K5": tuple(range(41, 49)), "K4": tuple(range(25, 33))}
FRESH = {"STD": tuple(range(383, 463)), "K5": tuple(range(49, 57)), "K4": tuple(range(33, 41))}
NL = {"STD": 5, "K5": 5, "K4": 4}
SELECTORS = ("margin", "straddle", "space")


def choose(selector, task, rev, cands, p, m, vl):
    if selector == "margin":
        return int(cands[int(np.argmax(-np.abs(p - 0.5)))])
    if selector == "straddle":
        return int(cands[int(np.argmax(1.96 * np.sqrt(np.maximum(vl, 0.0)) - np.abs(m)))])
    if selector == "space":
        return LN.next_on_path(task, rev)
    raise ValueError(selector)


def own_geo(task, M, hid, system, selector, bmax=60, cross_c1=False):
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); te = np.asarray(task["test"]); nt = len(te); evals = []
    t0, c0 = time.time(), time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time(); rows = np.r_[te, cands]
        p, cpu, info = GG.state(task, rev, Z, rows, hid, (system,), want_m=())
        e = {"budget": b, "p": {system: LN._f32(p[system][:nt])}, "gp_fail": info["gp_fail"]}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        aux = info["aux"].get(system)
        if aux is None:
            nxt = LN.next_on_path(task, rev); how = "path_fallback"
        else:
            m, vl, _ = aux; nxt = choose(selector, task, rev, cands, p[system][nt:], m[nt:], vl[nt:]); how = selector
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    paid = list(rev.order); out = {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "system": system, "selector": selector,
                                   "paid": paid, "paid_ids": [task["ids"][i] for i in paid], "test_ids": [task["ids"][i] for i in te], "evals": evals,
                                   "seconds": time.time() - t0, "cpu_s": time.process_time() - c0}
    if cross_c1:
        cross = []
        for bb in range(P.B0, bmax + 1):
            rv = K._rev_with(task, M, paid[:bb]); t2 = time.process_time(); pc, one = CA.predict(task, rv, Z, te, CA.SYSTEMS["C1"])
            cross.append({"budget": bb, "p": {"C1": LN._f32(pc)}, "cpu_s": time.process_time() - t2, "one_class": bool(one)})
        out["cross"] = cross
    return out


def geo_on_path(task, M, hid, system, paid_rows, bmax=60):
    Z = P.zstd(task); te = np.asarray(task["test"]); ev = []
    for b in range(P.B0, bmax + 1):
        rev = K._rev_with(task, M, paid_rows[:b]); t1 = time.process_time(); p, _, _ = GG.state(task, rev, Z, te, hid, (system,), want_m=())
        ev.append({"budget": b, "p": {system: LN._f32(p[system])}, "cpu_s": time.process_time() - t1})
    return ev


def selection(job):
    f = OUT / ("dev" if job.startswith("gt-own") else "freeze") / ("G2_SELECTION.json" if job.startswith("gt-own") else "G4_FREEZE.json")
    return json.loads(f.read_text(encoding="utf-8"))


def units(job):
    if job == "gt-own":
        sel = selection(job); sels = SELECTORS if sel.get("selector_controls", True) else ("margin",)
        return [(f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}__{s}", (c, r, f, s)) for s in sels for c in DEV for r in DEV[c] for f in range(1, NL[c] + 1)]
    if job == "gt-own-smoke":
        return [("STD__r163_f1__margin", ("STD", 163, 1, "margin")), ("STD__r163_f1__straddle", ("STD", 163, 1, "straddle"))]
    if job == "gt-val":
        return [(f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}__{p}", (c, r, f, p)) for c in FRESH for r in FRESH[c] for f in range(1, NL[c] + 1) for p in ("C", "G")]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    if job == "gt-val":
        import src.gt_freeze as FZ
        FZ.check()
    sel = selection("gt-own" if job != "gt-val" else job) if job != "gt-own-smoke" else {"system": "GEO_B1"}
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f, _) in S.items()}, M)

    def fn(name):
        c, r, f, s = S[name]; task = T[(c, r, f)]; hid = GG.Hidden(task)
        if job == "gt-val":
            if s == "C":
                import src.ea_fwd as FW
                u = FW.unit_X(task, M, 60); u["geo_on_c1"] = geo_on_path(task, M, hid, sel["system"], list(u["paid"]))
                return {**u, "condition": c, "unit_kind": "C"}
            return {**own_geo(task, M, hid, sel["system"], sel["selector"]), "condition": c, "unit_kind": "G"}
        return {**own_geo(task, M, hid, sel["system"], s, cross_c1=(s == "margin" and job == "gt-own")), "condition": c}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("gt-own-smoke",)})
