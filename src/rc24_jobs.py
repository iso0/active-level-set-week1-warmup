"""RC24 Stage A unit lists (queue src/rc24_runner.ps1, plan opus_rc24/runner/PLAN.json).
  a-own    own-query trajectories on FRESH repeats 59-66 (never run: RC19 1-10, RC19B 11-18, RC20 19-26, RC21 27-34, RC21B 35-42,
           RC22 43-50, RC23 51-58), standard startup, budgets 8..60, six arms:
             HA_LEAN_MARGIN   RC23 D1 learner (src.rc23_common.run_arm, unchanged)
             HONLY_MARGIN     learned-regularisation h-only classifier + margin (src.rc23_common.run_arm, unchanged)
             M3_MARGIN        faithful historical M3 (src.rc24_models) + margin
             E1S              Week 18 E1 (depth GP + threshold from the paid depth-label pairs) + straddle on E1's latent, records
                              E1RAW and E1CAL (src.rc22_common.run_e1s, unchanged; K = 10)
             G3_MARGIN        Week 18 G3 direct GP classifier + margin
             HA_LEAN_STRADDLE HA_LEAN probabilities, pre-registered straddle 1.96 s - |eta| (src.rc24_models); the margin choice on
                              the same state is recorded for the discriminability audit
  a-match  matched (cross-path) evaluation: on every a-own path (six path types x 40 tasks) all constructions
           HA_LEAN, HONLY_LR, M3, M3_C1, E1RAW, E1CAL, G3 at the path's paid prefixes, budgets 8..60 step 4
  a-smoke  every arm on DEV repeat 1 fold 1 to budget 16 + one matched unit
    python -m src.rc24_jobs work <job> [--threads 1]
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_models as MD

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
MB = tuple(range(8, 61, 4))
REP_A = tuple(range(59, 67))
ARMS = ("HA_LEAN_MARGIN", "HONLY_MARGIN", "M3_MARGIN", "E1S", "G3_MARGIN", "HA_LEAN_STRADDLE")
OWN_CONS = {"HA_LEAN_MARGIN": "HA_LEAN", "HONLY_MARGIN": "HONLY_LR", "M3_MARGIN": "M3", "E1S": "E1CAL", "G3_MARGIN": "G3", "HA_LEAN_STRADDLE": "HA_LEAN"}


def _f(a):
    return LN._f32(a)


def run_margin(task, cons, M, bmax=60):
    """Margin trajectory of a src.rc24_models construction (M3 or G3); only that construction is computed."""
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time(); rows = np.r_[task["test"], cands]
        out, info = MD.state(task, rev, Z, rows, (cons,)); one = len(set(rev.paid_y()[rev.paid].tolist())) < 2
        e = {"budget": b, "p": {cons: _f(out[cons][:nt])}, "info": {k: v for k, v in info.get(cons, {}).items() if k != "lengthscales"} if isinstance(info.get(cons), dict) else {}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if one:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(out[cons][nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "construction": cons, "paid": rev.order,
            "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def run_straddle(task, M, bmax=60):
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time(); rows = np.r_[task["test"], cands]
        mom = MD.ha_lean_moments(task, rev, Z, rows)
        e = {"budget": b, "p": {"HA_LEAN": _f(mom["p"][:nt])}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if mom["one_class"]:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            sc = MD.straddle_score(mom)[nt:]; mg = -np.abs(mom["p"][nt:] - 0.5); i_s = int(np.argmax(sc)); i_m = int(np.argmax(mg))
            srt = np.sort(sc); gap = float(srt[-1] - srt[-2]) if len(srt) > 1 else np.nan
            e["audit"] = {"same_as_margin": bool(i_s == i_m), "margin_choice": int(cands[i_m]), "top2_gap": gap, "score_range": float(srt[-1] - srt[0]),
                          "s_at_choice": float(np.sqrt(max(mom["s2"][nt + i_s], 0.0))), "abs_eta_at_choice": float(abs(mom["eta"][nt + i_s])),
                          "s_median": float(np.median(np.sqrt(np.maximum(mom["s2"][nt:], 0.0)))), "excess_depth_share": float(np.mean(mom["sig2"][nt:] > 0)),
                          "mse_oof": mom["mse_oof"]}
            nxt = int(cands[i_s]); how = "straddle"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "construction": "HA_LEAN", "paid": rev.order,
            "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def run_own(task, arm, M, bmax=60):
    if arm in ("HA_LEAN_MARGIN", "HONLY_MARGIN"):
        u = C23.run_arm(task, OWN_CONS[arm], M, bmax=bmax)
    elif arm in ("M3_MARGIN", "G3_MARGIN"):
        u = run_margin(task, OWN_CONS[arm], M, bmax=bmax)
    elif arm == "E1S":
        u = C22.run_e1s(task, M, bmax=bmax)
    elif arm == "HA_LEAN_STRADDLE":
        u = run_straddle(task, M, bmax=bmax)
    else:
        raise ValueError(arm)
    u["arm"] = arm; return u


def match_unit(task, unit, M, budgets=MB):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; nt = len(task["test"]); evals = []; t0 = time.time()
    own = {e["budget"]: e["p"] for e in unit["evals"]}
    for b in budgets:
        if b > len(paid):
            break
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time()
        out, info = MD.state(task, rev, Z, np.asarray(task["test"]), MD.STAGEA_CONS)
        chk = {k: float(np.nanmax(np.abs(np.asarray(out[k], float).astype(np.float32).astype(float) - np.asarray(own[b][k], float)))) for k in own.get(b, {}) if k in out}
        evals.append({"budget": b, "p": {k: _f(v) for k, v in out.items()}, "cpu_s": time.process_time() - t1, "check_vs_own": chk})
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(budgets)], "test_ids": unit["test_ids"], "evals": evals,
            "seconds": time.time() - t0}


def units(job):
    if job == "a-own":
        return [(f"{a}__r{r}_f{f}", ("own", a, r, f)) for r in REP_A for f in range(1, 6) for a in ARMS]
    if job == "a-match":
        return [(f"PATH_{a}__r{r}_f{f}", ("match", a, r, f)) for r in REP_A for f in range(1, 6) for a in ARMS]
    if job == "a-smoke":
        return [(f"{a}__r1_f1", ("own_smoke", a, 1, 1)) for a in ARMS] + [("PATH_HA_LEAN_MARGIN__r1_f1", ("match_smoke", "HA_LEAN_MARGIN", 1, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    import src.rc24_freeze as FR
    FR.check(job)
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({s[2] for s in S.values()}))}

    def fn(name):
        kind, a, r, f = S[name]; task = T[(r, f)]
        if kind == "own":
            return run_own(task, a, M)
        if kind == "own_smoke":
            return run_own(task, a, M, bmax=16)
        if kind == "match":
            return match_unit(task, RC.read_json_gz(OUT / "a-own" / "units" / f"{a}__r{r}_f{f}.json.gz"), M)
        if kind == "match_smoke":
            return match_unit(task, RC.read_json_gz(OUT / "a-smoke" / "units" / f"{a}__r{r}_f{f}.json.gz"), M, budgets=(8, 12, 16))
        raise ValueError(kind)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("a-own", "a-match", "a-smoke")})
