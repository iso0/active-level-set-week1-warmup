"""RC24 worker-layout timing trial (owner authorisation 2026-10-21: all local cores; host 4 physical / 8 logical cores).

One fixed workload (HA_LEAN and HONLY_LR paid states of repeat 35 fold 1 at budgets 16 / 40 / 60, the RC23 timing states) is run
by k concurrent worker processes for k in {1, 2, 4, 6, 8} with ONE BLAS / OpenMP thread each, and by 4 workers x 2 threads and
2 workers x 4 threads. Throughput = k x workload / compute wall time of the slowest worker (imports excluded; the end-to-end wall including the
process start is also recorded); the layout with the highest throughput is the RC24 runner layout (layouts within 5 % of the
best -> the one using fewer logical CPUs). No evaluation metric is computed. (A first run with a 2-repetition workload was
dominated by process start-up, about 2.7 s against 0.9 s of compute, and is superseded by this 8-repetition run.)
    python -m src.rc24_timing trial
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24" / "timing"
LAYOUTS = ((1, 1), (2, 1), (4, 1), (6, 1), (8, 1), (4, 2), (2, 4))


def worker():
    import numpy as np
    import src.rc19_pool as P
    import src.rc19b_keyhole as K
    import src.rc22_common as C22
    import src.rc23_common as C23
    M = P.manifest(); C22.set_manifest(M); t = {(x["repeat"], x["fold"]): x for x in P.tasks([35])}[(35, 1)]; pos = {s: i for i, s in enumerate(t["ids"])}
    gi = RC.read_json_gz(RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22" / "g-ingr" / "units" / "r35_f1__H_MARGIN.json.gz"); Z = P.zstd(t)
    t0 = time.perf_counter(); c0 = time.process_time()
    for b in (16, 40, 60):
        rv = K._rev_with(t, M, [pos[s] for s in gi["paid_ids"][:b]]); rw = np.r_[t["test"], np.setdiff1d(t["pool"], rv.paid)]
        for _ in range(8):
            C23.state(t, rv, Z, rw, which=("HA_LEAN", "HONLY_LR"))
    print(json.dumps({"wall_s": time.perf_counter() - t0, "cpu_s": time.process_time() - c0}), flush=True)


def trial():
    OUT.mkdir(parents=True, exist_ok=True); rows = []
    for k, th in LAYOUTS:
        env = {**os.environ, "OMP_NUM_THREADS": str(th), "MKL_NUM_THREADS": str(th), "OPENBLAS_NUM_THREADS": str(th), "NUMEXPR_NUM_THREADS": str(th), "PYTHONIOENCODING": "utf-8"}
        t0 = time.perf_counter()
        ps = [subprocess.Popen([sys.executable, "-m", "src.rc24_timing", "worker"], cwd=str(RC.ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(k)]
        outs = [p.communicate() for p in ps]; wall = time.perf_counter() - t0
        res = [json.loads(o[0].strip().splitlines()[-1]) for o in outs]
        rows.append({"workers": k, "threads_per_worker": th, "logical_cpus_used": k * th, "wall_s_slowest": wall, "worker_wall_s": [round(r["wall_s"], 2) for r in res],
                     "worker_cpu_s": [round(r["cpu_s"], 2) for r in res], "workloads_per_minute": 60.0 * k / max(r["wall_s"] for r in res), "end_to_end_workloads_per_minute": 60.0 * k / wall})
        print(rows[-1], flush=True)
    best = max(r["workloads_per_minute"] for r in rows)
    choice = min((r for r in rows if r["workloads_per_minute"] >= 0.95 * best), key=lambda r: (r["logical_cpus_used"], r["workers"]))
    res = {"utc": RC.utc(), "host": {"cpu": "Intel Core i5-10300H", "physical_cores": 4, "logical_cpus": 8, "ram_gb": 31.8}, "layouts": rows,
           "rule": "highest workloads/minute (compute wall of the slowest worker); layouts within 5 % of the best -> the one using fewer logical CPUs", "choice": choice}
    (OUT / "TIMING.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print("CHOICE", choice)


if __name__ == "__main__":
    {"worker": worker, "trial": trial}[sys.argv[1]]()
