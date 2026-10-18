"""PHYS_DISCOVERY v1.1 (RC18 fix A1, prospective): SD_MAXVAR with the corrected surprise denominator.

The frozen v1.0 rule (src/jdl_phys_discovery.py:92-93) computed z = (y - m) / sqrt(sd^2 + noise) although sklearn's predictive
sd already contains the white noise (HAND_CHECK.json), so the noise was counted twice. v1.1 uses z = (y - m) / sd, the
protocol's formula (latent + noise). Everything else (GP, start, base selector, local rule, QC, budgets, tasks, families,
evaluator, bootstrap) is the frozen v1.0 code path; the v1.0 results are kept unchanged.

validate: run_traj(..., z_rule="frozen") must reproduce the cached v1.0 SD_MAXVAR paths and z exactly (all 20 trajectories).
work:     z_rule="corrected" for the 20 SD_MAXVAR trajectories (NEW, OLD x r3-4 x f1-5).
evaluate: paired family-AUDC contrasts SD_MAXVAR_v11 - MAXVAR (v1.0, unchanged; the registered verdict rule) and
          SD_MAXVAR_v11 - SD_MAXVAR_v1.0 (effect of the repair); 10 pairs, 2000 draws, seed 20261017 (as v1.0).
    python -m src.rc18_phys_discovery_v11 validate | manifest | work | evaluate
"""
from __future__ import annotations

import gzip
import json
import sys
import time

import numpy as np
import pandas as pd

import src.jdl_phys_al as PAL
import src.jdl_phys_discovery as PD
import src.rc18_common as RC
import src.jdl_stage_m as SMM

OUT = RC.CAMP / "fixes" / "A1_variance_contract" / "v11"
CACHE = OUT / "units"
MANIFEST = OUT / "PHYS_DISCOVERY_V11_MANIFEST.json"
CODE = ("src/rc18_phys_discovery_v11.py", "src/jdl_phys_discovery.py", "src/jdl_phys_al.py", "src/rc18_common.py")


def run_traj(task, pop, arm, Tt, qc, z_rule="corrected"):
    X, ids, pool, test = task["X"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[test] = std(X[test])
    y = Tt.reindex(ids)[PD.RESPONSE].to_numpy(float); q = qc.reindex(ids).fillna(False).to_numpy(bool)
    rng = np.random.default_rng(41000 + 100 * task["repeat"] + task["fold"] + (17 if pop == "OLD" else 0))
    L = [int(i) for i in task["path"][:PD.B0]]; seeds, last_local, log, evals = [], False, [], []; t0 = time.time()
    for b in range(PD.B0, PD.B1 + 1):
        ok = np.isfinite(y[L]); Lj = np.asarray(L)[ok]; g = PAL.gp_fit(Z[Lj], y[Lj]) if len(Lj) >= 3 else None
        evals.append({"budget": b, "pred": None if g is None else g.predict(Z[test]).tolist()})
        if b == PD.B1:
            break
        unpaid = np.setdiff1d(pool, L); nxt = None; how = None
        if arm == "SD_MAXVAR":
            while seeds and seeds[0][1] <= 0:
                seeds.pop(0)
            if seeds and not last_local:
                s = seeds[0][0]; d = np.linalg.norm(Z[unpaid] - Z[s], axis=1); nxt = int(unpaid[np.lexsort((ids[unpaid], d))[0]]); seeds[0][1] -= 1; how = "local"
        if nxt is None:
            if arm == "RANDOM":
                nxt = int(rng.choice(unpaid)); how = "random"
            elif arm == "MAXIMIN" or g is None:
                nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path"
            else:
                sd = g.predict(Z[unpaid], return_std=True)[1]; nxt = int(unpaid[int(np.argmax(sd))]); how = "maxvar"
        last_local = how == "local"
        if arm == "SD_MAXVAR" and g is not None:
            m, s_ = g.predict(Z[[nxt]], return_std=True); noise = float(np.exp(g.kernel_.theta[-1])) * float(g._y_train_std) ** 2
            if not np.isfinite(y[nxt]):
                zval = None
            elif z_rule == "frozen":
                zval = float((y[nxt] - m[0]) / np.sqrt(s_[0] ** 2 + noise))
            else:                                                            # observation sd = sqrt(latent + noise)
                zval = float((y[nxt] - m[0]) / s_[0])
            event = "QC_EVENT" if (not q[nxt] or zval is None) else ("SURPRISE" if abs(zval) >= PD.Z_SURPRISE else "none")
            log.append({"budget": b + 1, "selected": ids[nxt], "how": how, "z": zval, "event": event,
                        "m": float(m[0]), "sd_observation": float(s_[0]), "noise": noise})
            if event == "SURPRISE":
                seeds.append([int(nxt), PD.M_LOCAL])
        L.append(nxt)
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "z_rule": z_rule, "paid": L,
            "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test], "evals": evals, "sd_log": log, "status": "ok",
            "seconds": time.time() - t0}


def _tasks(pop):
    return {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}


def validate():
    RC.limit_threads(1); checks = {}
    for pop in ("NEW", "OLD"):
        Tt, qc = PAL.targets(pop), PD.qc_table(pop)
        for (r, f), t in sorted(_tasks(pop).items()):
            c = json.loads(gzip.decompress((PD.CACHE / f"{pop}__r{r}_f{f}__SD_MAXVAR.json.gz").read_bytes()))
            a = run_traj(t, pop, "SD_MAXVAR", Tt, qc, z_rule="frozen")
            checks[f"{pop}_r{r}_f{f}"] = a["paid"] == c["paid"] and all(
                (x["z"] is None) == (y["z"] is None) and (x["z"] is None or abs(x["z"] - y["z"]) <= 1e-9 * max(1, abs(y["z"]))) for x, y in zip(a["sd_log"], c["sd_log"]))
    res = {"status": "PASS" if all(checks.values()) else "FAIL", "frozen_rule_reproduces_v10": checks, "utc": RC.utc(),
           "module_sha256": SMM.sha256(SMM.ROOT / "src" / "rc18_phys_discovery_v11.py")}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "VALIDATION.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"status": res["status"], "n": len(checks), "pass": sum(checks.values())})); return res


def write_manifest():
    val = json.loads((OUT / "VALIDATION.json").read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "rc18_phys_discovery_v11.py"):
        raise SystemExit("validation must PASS with this module before the freeze")
    man = {"study": "PHYS_DISCOVERY_V11", "status": "FROZEN BEFORE ANY V1.1 OUTCOME", "written_utc": RC.utc(), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "change": "surprise z denominator: sd_observation (latent + noise) instead of sqrt(sd_observation^2 + noise)",
           "units": "SD_MAXVAR x {NEW, OLD} x r3-4 x f1-5 (20)", "comparators": "MAXVAR v1.0 (unchanged, registered verdict rule); SD_MAXVAR v1.0 (fix effect)",
           "verdict_rule": "DISCOVERY GAIN (DEV) iff SD_v11 - MAXVAR family AUDC > 0, its 10-pair bootstrap interval > 0, and R2-AULC not lower by > 0.02 (as v1.0)",
           "validation": {"status": val["status"], "sha256": SMM.sha256(OUT / "VALIDATION.json")}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}))


def work():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the v1.1 freeze")
    RC.limit_threads(1)
    for pop in ("NEW", "OLD"):
        Tt, qc = PAL.targets(pop), PD.qc_table(pop); T = _tasks(pop)
        names = [f"{pop}__r{r}_f{f}__SD_MAXVAR_v11" for (r, f) in sorted(T)]
        def fn(name, Tt=Tt, qc=qc, T=T, pop=pop):
            r, f = int(name.split("__")[1][1]), int(name.split("__")[1][4])
            return run_traj(T[(r, f)], pop, "SD_MAXVAR", Tt, qc, z_rule="corrected")
        RC.run_units(names, fn, CACHE, OUT / "locks", OUT / "failed", log=lambda s: print(s, flush=True))


def evaluate():
    rng = np.random.default_rng(20261017); res = {}
    for pop in ("NEW", "OLD"):
        Tt = PAL.targets(pop); yall = Tt[PD.RESPONSE].dropna(); hi = yall.quantile(0.9); fam = set(yall[yall >= hi].index)
        T = _tasks(pop); rows = []
        for (r, f), t in sorted(T.items()):
            pool_ids = set(np.asarray(t["ids"]).astype(str)[t["pool"]]); nh = len(fam & pool_ids)
            src = {"SD_MAXVAR_v11": RC.read_json_gz(CACHE / f"{pop}__r{r}_f{f}__SD_MAXVAR_v11.json.gz"),
                   "SD_MAXVAR_v10": json.loads(gzip.decompress((PD.CACHE / f"{pop}__r{r}_f{f}__SD_MAXVAR.json.gz").read_bytes())),
                   "MAXVAR_v10": json.loads(gzip.decompress((PD.CACHE / f"{pop}__r{r}_f{f}__MAXVAR.json.gz").read_bytes()))}
            for arm, u in src.items():
                ch = [len(fam & set(u["paid_ids"][:b])) / max(1, nh) for b in range(PD.B0, PD.B1 + 1)]
                rows.append({"pop": pop, "repeat": r, "fold": f, "arm": arm, "AUDC": float(np.trapezoid(ch) / (PD.B1 - PD.B0)),
                             "surprises": sum(x["event"] == "SURPRISE" for x in u.get("sd_log", [])), "same_path_as_v10": None if arm != "SD_MAXVAR_v11" else
                             src["SD_MAXVAR_v10"]["paid"] == u["paid"]})
        D = pd.DataFrame(rows); out = {"arm_means": D.groupby("arm")[["AUDC", "surprises"]].mean().round(4).to_dict(orient="index"),
                                      "v11_paths_identical_to_v10": int(D[D.arm == "SD_MAXVAR_v11"].same_path_as_v10.sum())}
        for a, b in (("SD_MAXVAR_v11", "MAXVAR_v10"), ("SD_MAXVAR_v11", "SD_MAXVAR_v10")):
            m = D[D.arm == a].set_index(["repeat", "fold"]).AUDC - D[D.arm == b].set_index(["repeat", "fold"]).AUDC
            d = m.to_numpy(); bs = [np.mean(rng.choice(d, len(d))) for _ in range(2000)]
            out[f"{a}-{b}"] = {"diff": float(d.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "pairs": len(d)}
        out["verdict"] = "DISCOVERY GAIN (DEV)" if out["SD_MAXVAR_v11-MAXVAR_v10"]["diff"] > 0 and out["SD_MAXVAR_v11-MAXVAR_v10"]["lo"] > 0 else "NO DISCOVERY GAIN ESTABLISHED"
        res[pop] = out
        D.to_csv(OUT / f"v11_per_trajectory_{pop}.csv", index=False, lineterminator="\n")
    (OUT / "V11_RESULTS.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1)); return res


if __name__ == "__main__":
    {"validate": validate, "manifest": write_manifest, "work": work, "evaluate": evaluate}[sys.argv[1]]()
