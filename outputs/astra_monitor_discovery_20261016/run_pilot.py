"""One bounded local pilot; never starts a background queue.

--dry-run reads the frozen manifest only. --run requires Opus's active allocation
in the SINGLE existing coordination JSON, and a matching frozen code digest.
Numerical libraries are imported only after that gate. Checkpoints are trusted
local pickle files created by this runner; do not supply someone else's pickle.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import socket
import sys
import time

HERE = Path(__file__).resolve().parent
JOB = "astra_monitor_discovery_20261016"
MANIFEST = HERE/"FROZEN_MANIFEST.json"


def utc():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    temp.replace(path)


def load_manifest():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, digest in m["code_hashes"].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("frozen code mismatch: "+name)
    expected = hashlib.sha256(json.dumps(m["code_hashes"], sort_keys=True).encode()).hexdigest()
    if expected != m["code_digest"]:
        raise RuntimeError("manifest code digest mismatch")
    return m


def check_reservation(path, manifest):
    if path is None:
        raise RuntimeError("no coordination record: Opus must allocate one thread")
    c = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    records = [r for r in c.get("external_reservations", []) if r.get("job") == JOB
               and r.get("status") == "active"]
    if len(records) != 1:
        raise RuntimeError("no unique active Opus reservation in the coordination record")
    r = records[0]
    if not (r.get("granted_by") == "Opus" and r.get("threads") == 1
            and r.get("host") == socket.gethostname()
            and 1 <= r.get("combined_active_threads", 99) <= 4
            and r.get("code_digest") == manifest["code_digest"]):
        raise RuntimeError("reservation host/thread/owner/code mismatch")
    expires = datetime.fromisoformat(r["expires_utc"].replace("Z", "+00:00"))
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise RuntimeError("reservation expired")
    return r


class Budget:
    def __init__(self, out, caps, check_allocation):
        self.out, self.caps, self.check_allocation = out, caps, check_allocation
        self.resource_path = out/"RESOURCES.json"
        self.ledger = out/"attempt_ledger.jsonl"
        self.data = json.loads(self.resource_path.read_text()) if self.resource_path.exists() else {
            "controlled_fit_requests": 0, "component_solves": 0, "reference_fits": 0,
            "used_wall_s": 0., "unfinished": None}
        if self.data["unfinished"] is not None:
            raise RuntimeError("unfinished attempt retained; coordinator review required, no automatic retry")
        self.base_wall = self.data["used_wall_s"]
        self.started = time.perf_counter()

    def append(self, row):
        with self.ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"utc": utc(), **row}, allow_nan=False)+"\n")

    def save(self):
        self.data["used_wall_s"] = self.base_wall+time.perf_counter()-self.started
        dump(self.resource_path, self.data)

    def start(self, identity, components=1, reference=False):
        self.check_allocation()
        self.save()
        if self.data["used_wall_s"] >= self.caps["wall_seconds"]:
            raise TimeoutError("cumulative 20-minute budget reached; no automatic extension")
        key = "reference_fits" if reference else "controlled_fit_requests"
        if self.data[key]+1 > self.caps[key] or self.data["component_solves"]+components > self.caps["component_solves"]:
            raise RuntimeError("finite fit/component budget exhausted")
        self.data[key] += 1
        self.data["component_solves"] += components  # reserve BEFORE launching any solve
        self.data["unfinished"] = identity
        self.save()
        self.append({"event": "START", "identity": identity, "components_reserved": components,
                     "reference": reference})

    def finish(self, status="OK", error=None):
        self.append({"event": "END", "identity": self.data["unfinished"], "status": status, "error": error})
        # Failures stay unfinished so resuming cannot become an unrecorded rescue.
        if status == "OK":
            self.data["unfinished"] = None
        self.save()


def checkpoint(path, state):
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as fh:
        pickle.dump(state, fh, protocol=5)
    temp.replace(path)


def first_persistent(records, key):
    for a, b in zip(records, records[1:]):
        if a["metrics"].get(key, False) and b["metrics"].get(key, False):
            return b["budget"]  # second consecutive readout: confirmation is charged
    return None


def trajectory(world, mode, manifest, out, resources, auxiliary=False):
    import numpy as np
    from discovery import Predictions, SurpriseLocalDiscovery, maximin_start
    from synthetic import FixedGP
    e = manifest["experiment"]
    identity = f"{world.name}__seed{world.seed}__{mode}"
    path, result = out/(identity+".pkl"), out/(identity+".json")
    if result.exists():
        saved = json.loads(result.read_text(encoding="utf-8"))
        if saved["code_digest"] != manifest["code_digest"] or saved["features_hash"] != world.feature_hash():
            raise RuntimeError("completed trajectory provenance mismatch")
        return saved
    if path.exists():
        with path.open("rb") as fh:
            st = pickle.load(fh)
        if st["code_digest"] != manifest["code_digest"]:
            raise RuntimeError("checkpoint code mismatch")
    else:
        paid = maximin_start(world.x.tolist(), e["startup"], world.seed+100)
        ob = [world.pay(i) for i in paid]
        st = {"code_digest": manifest["code_digest"], "paid": paid,
              "values": [o.value for o, a in ob], "aux": [a for o, a in ob],
              "selector": SurpriseLocalDiscovery(world.x, paid, seed=world.seed+200, mode=mode),
              "records": [], "selection_wall_s": 0., "fit_wall_s": 0.}
        checkpoint(path, st)
    policy = st["selector"]
    # The final checkpoint may have committed before its JSON summary was written.
    # Rebuild the summary in that case without repeating the final paid fit.
    while not (st["records"] and st["records"][-1]["budget"] == e["budget"]):
        n = len(st["paid"])
        resources.start(identity+f"__B{n}", components=2 if auxiliary else 1)
        started = time.perf_counter()
        try:
            valid = [k for k, q in enumerate(st["values"]) if q is not None]
            fit_ids = [st["paid"][k] for k in valid]
            gp = FixedGP().fit(world.x[fit_ids], [st["values"][k] for k in valid])
            mu, sd = gp.predict(world.x)
            em, es = gp.predict(world.eval_x)
            aux_v = None
            aux_em = None
            if auxiliary:
                gpa = FixedGP(mean=0., length=.45).fit(world.x[st["paid"]], st["aux"])
                _, aux_s = gpa.predict(world.x)
                aux_v = aux_s**2  # both declared synthetic output scales = 1
                aux_em, _ = gpa.predict(world.eval_x)
            mult = world.reported_sd_multiplier
            sd, es = sd*mult, es*mult
            # No world name, latent truth or evaluator membership in the model identity.
            fingerprint = hashlib.sha256(json.dumps({"paid": st["paid"],
                "primary_paid": st["values"], "aux_paid": st["aux"] if auxiliary else None,
                "model": m["model"]}, sort_keys=True, allow_nan=False).encode()).hexdigest()
            pred = Predictions(fingerprint, n, mu, sd, [.08*mult]*len(mu), aux_v)
            metrics = world.evaluate(em, es, st["paid"], aux_em)
            elapsed = time.perf_counter()-started
            st["fit_wall_s"] += elapsed
            row = {"budget": n, "metrics": metrics, "fit_and_evaluation_wall_s": elapsed,
                   "posterior_hash": pred.digest()}
            st["records"].append(row)
            if n < e["budget"]:
                tic = time.perf_counter()
                choice = policy.ask(pred)
                obs, aux = world.pay(choice.index)  # the ONLY newly revealed outputs
                event = policy.tell(obs)
                st["selection_wall_s"] += time.perf_counter()-tic
                row["next_query"] = event
                st["paid"].append(choice.index)
                st["values"].append(obs.value)
                st["aux"].append(aux)
            checkpoint(path, st)
            resources.finish()
        except Exception as exc:
            resources.finish("FAILED", repr(exc))
            raise
        if n >= e["budget"]:
            break
    rows = st["records"]
    first = rows[-1]["metrics"]["first_discovery_query"]
    third = rows[-1]["metrics"]["third_island_query"]
    result_data = {"identity": identity, "world": world.name, "seed": world.seed, "mode": mode,
                   "status": "COMPLETE", "code_digest": manifest["code_digest"],
                   "features_hash": world.feature_hash(), "paid_path": st["paid"],
                   "records": rows, "events": policy.events, "first_discovery_query": first,
                   "first_discovery_censored_at": e["budget"] if first is None else None,
                   "additional_queries_to_third_island": third-first if third and first else None,
                   "discovery_target_confirmed_at": first_persistent(rows, "discovery_target_met"),
                   "regression_target_confirmed_at": first_persistent(rows, "regression_target_met"),
                   "selection_wall_s": st["selection_wall_s"], "fit_wall_s": st["fit_wall_s"],
                   "trigger_count": sum(v["triggered"] for v in policy.events),
                   "corroboration_count": sum(v["corroborated_now"] for v in policy.events)}
    dump(result, result_data)
    return result_data


def run(args, m):
    reservation = check_reservation(args.coordination_record, m)
    out = HERE/"pilot"
    out.mkdir(exist_ok=True)
    lock = out/"RUNNING.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError("runner lock exists; do not duplicate or remove an active run")
    os.write(fd, json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "utc": utc()}).encode())
    os.close(fd)
    budget = None
    try:
        # Override only this process before importing numerical libraries.
        for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[key] = "1"
        import numpy as np
        import scipy
        from threadpoolctl import threadpool_info, threadpool_limits
        from synthetic import SyntheticWorld
        from check_numerics import run_reference_checks
        with threadpool_limits(limits=1):
            info = threadpool_info()
            if any(p["num_threads"] > 1 for p in info):
                raise RuntimeError("thread cap was not applied")
            budget = Budget(out, m["caps"], lambda: check_reservation(args.coordination_record, m))
            dump(out/"RUN_ENVIRONMENT.json", {"utc": utc(), "python": sys.version, "numpy": np.__version__,
                 "scipy": scipy.__version__, "threadpools": info, "reservation": reservation,
                 "coordination_record": str(Path(args.coordination_record).resolve()), "code_digest": m["code_digest"]})
            reference_file = out/"NUMERICAL_REFERENCES.json"
            if not reference_file.exists():
                previous = [False]
                def before_fit(n):
                    if previous[0]:
                        budget.finish()
                    budget.start("reference_"+str(n), reference=True)
                    previous[0] = True
                refs = run_reference_checks(before_fit)
                budget.finish()
                dump(reference_file, {"status": "PASS", "checks": refs})
            results = []
            # Seed-major round-robin worlds: no arm gets all seeds before another starts.
            for seed in m["experiment"]["seeds"]:
                for name in m["experiment"]["worlds"]:
                    world = SyntheticWorld(name, seed, m["experiment"]["pool_size"], m["experiment"]["eval_size"])
                    for mode in m["experiment"]["core_arms"]:
                        results.append(trajectory(world, mode, m, out, budget))
            for seed in m["experiment"]["seeds"]:
                world = SyntheticWorld("island", seed, m["experiment"]["pool_size"], m["experiment"]["eval_size"])
                for mode in m["experiment"]["aux_arms"]:
                    results.append(trajectory(world, mode, m, out, budget, auxiliary=True))
            dump(out/"CONTROLLED_RESULTS.json", {"status": "COMPLETE", "code_digest": m["code_digest"],
                 "warning": "Two seeds per world: descriptive feasibility, not general superiority or SPH evidence",
                 "outcomes": results, "resources": budget.data})
    except Exception as exc:
        if budget:
            budget.save()
        dump(out/"EXECUTION_STOP.json", {"status": "STOPPED", "reason": repr(exc), "utc": utc(),
             "interpretation": "Preserve checkpoints. Incomplete comparisons are not negative scientific evidence."})
        raise
    finally:
        if budget:
            budget.save()
        lock.unlink()  # only this process's own lock, acquired above


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--run", action="store_true")
    p.add_argument("--coordination-record", type=Path)
    args = p.parse_args()
    m = load_manifest()
    if args.dry_run:
        print(json.dumps({"status": "PREPARED_NOT_RUN", "job": JOB, "experiment": m["experiment"],
                          "caps": m["caps"], "code_digest": m["code_digest"],
                          "numerical_imports": False}, indent=2))
        return
    run(args, m)


if __name__ == "__main__":
    main()
