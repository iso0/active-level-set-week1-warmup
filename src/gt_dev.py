"""GT stage G2 (PROTOCOL_GT.md section 5): every system of section 4 on the RECORDED C1 + margin paid prefixes (same opened runs, same
startups), every budget 8..60. Reference = the recorded C1 predictions (EA validation, ea-fwd X units); C1 is also recomputed at every
budget as the reuse check (V4). Paid outcomes and public inputs only; test outcomes are never read here.
    python -m src.gt_dev work gt-dev | gt-dev-smoke
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.el_cross as X
import src.gt_geo as GG
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22

OUT = RC.ROOT / "outputs" / "research_campaign_20261102" / "opus_geometry_temperature"
EA_UNITS = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "ea-fwd" / "units"
DEV = {"STD": tuple(range(163, 203)), "K5": tuple(range(41, 49)), "K4": tuple(range(25, 33))}
NL = {"STD": 5, "K5": 5, "K4": 4}


def recorded(cond, r, f):
    name = f"STD__r{r}_f{f}__X.json.gz" if cond == "STD" else f"{cond}__s{r}_b{f}__X.json.gz"
    return RC.read_json_gz(EA_UNITS / name)


def dev_unit(task, uX, M, hid, budgets=tuple(range(8, 61)), which=GG.ALL):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in uX["paid_ids"]]; te = np.asarray(task["test"])
    if [task["ids"][i] for i in te] != list(uX["test_ids"]):
        raise RuntimeError("recorded test set differs from the task")
    v5 = bool(list(paid_all[:P.B0]) == [int(i) for i in task["path"][:P.B0]])
    rec = {e["budget"]: np.asarray(e["p"]["C1"], float) for e in uX["evals"]}; ev = []
    for b in budgets:
        rev = K._rev_with(task, M, paid_all[:b]); t0 = time.process_time()
        p, cpu, info = GG.state(task, rev, Z, te, hid, which)
        e = {"budget": b, "p": {k: LN._f32(v) for k, v in p.items()}, "cpu_s": cpu, "one_class": info["one_class"], "gp_fail": info["gp_fail"],
             "gp_fits": info["gp_fits"], "fallback": info["fallback"], "wall_cpu_s": time.process_time() - t0}
        for s in ("GEO_A1", "GEO_B1"):
            if f"m_{s}" in info:
                e[f"m_{s}"] = LN._f32(info[f"m_{s}"])
        if "C1" in p:
            e["c1_vs_recorded_maxabs"] = float(np.max(np.abs(np.asarray(LN._f32(p["C1"]), float) - rec[b])))
        ev.append(e)
    return {"evals": ev, "startup_is_task_path": v5, "paid_ids": uX["paid_ids"][:60], "test_ids": uX["test_ids"]}


def units(job):
    if job == "gt-dev":
        return [(f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}", (c, r, f)) for c in DEV for r in DEV[c] for f in range(1, NL[c] + 1)]
    if job == "gt-dev-smoke":
        return [("STD__r163_f1", ("STD", 163, 1)), ("K5__s41_b1", ("K5", 41, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f) in S.items()}, M)

    def fn(name):
        c, r, f = S[name]; task = T[(c, r, f)]; uX = recorded(c, r, f); hid = GG.Hidden(task)
        res = dev_unit(task, uX, M, hid, budgets=(8, 12, 20) if job.endswith("smoke") else tuple(range(8, 61)))
        return {"condition": c, "repeat": r, "fold": f, **res}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("gt-dev", "gt-dev-smoke")})
