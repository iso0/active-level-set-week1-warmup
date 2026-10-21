"""RC24 DEV diagnostic (used repeats 59-66 of Stage A, after its frozen evaluation; development only): HA_TREND evaluated on the
recorded Stage A HONLY_MARGIN and HA_LEAN_MARGIN paths (matched), to separate "anchored model" from "physics-margin path".
    python -m src.rc24_dev_paths work d-paths
"""
from __future__ import annotations

import sys

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
MB = tuple(range(8, 61, 4))


def units(job):
    return [(f"{a}__r{r}_f{f}", (a, r, f)) for r in range(59, 67) for f in range(1, 6) for a in ("HONLY_MARGIN", "HA_LEAN_MARGIN")]


def work(job):
    RC.limit_threads(1); U = units(job); S = dict(U); M = P.manifest(); C22.set_manifest(M); T = {(t["repeat"], t["fold"]): t for t in P.tasks(range(59, 67))}

    def fn(name):
        a, r, f = S[name]; t = T[(r, f)]; u = RC.read_json_gz(OUT / "a-own" / "units" / f"{a}__r{r}_f{f}.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}
        paid = [pos[s] for s in u["paid_ids"]]; Z = P.zstd(t); ev = []
        for b in MB:
            rv = K._rev_with(t, M, paid[:b]); o, _ = PC.state(t, rv, Z, np.asarray(t["test"]), ("HA_TREND",)); ev.append({"budget": b, "p": {"HA_TREND": LN._f32(o["HA_TREND"])}})
        return {"repeat": r, "fold": f, "path_of": a, "paid_ids": u["paid_ids"][:60], "test_ids": u["test_ids"], "evals": ev}
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    work(sys.argv[2])
