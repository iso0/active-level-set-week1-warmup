"""Shared worker helpers for research campaign 20261018 (Opus).

Unit protocol used by every rc18 worker:
* a unit is done iff <cache>/<name>.json.gz exists (written atomically); failed iff <failed>/<name>.json exists;
* a worker claims a unit with an O_EXCL lock <locks>/<name>.lock containing its PID; the runner releases locks of dead PIDs;
* an exception inside a unit writes the failure record (traceback) and the worker moves on; a failed unit is never retried
  automatically (a repair must be recorded and the failure record moved to history/);
* no unit is claimed after RC18_DEADLINE_UTC (the campaign deadline, set by the runner and the coordination record).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import socket
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "outputs" / "research_campaign_20261018" / "opus"
COORD = ROOT / "outputs" / "joint_depth_label_development" / "pool" / "POOL_PLAN.json"


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def deadline():
    s = os.environ.get("RC18_DEADLINE_UTC")
    if not s:
        try:
            s = json.loads(COORD.read_text(encoding="utf-8-sig"))["coordination"]["campaign"]["deadline_utc"]
        except Exception:
            s = "2026-10-20T08:41:20+00:00"
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def past_deadline():
    return dt.datetime.now(dt.timezone.utc) >= deadline()


def limit_threads(n=1):
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[k] = str(n)
    try:
        from threadpoolctl import threadpool_limits
        return threadpool_limits(n)
    except Exception:
        return None


def atomic_write_json_gz(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_bytes(gzip.compress(json.dumps(obj, default=str).encode("utf-8")))
    os.replace(tmp, path)


def read_json_gz(path: Path):
    return json.loads(gzip.decompress(path.read_bytes()))


def atomic_write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def run_units(names, fn, cache: Path, locks: Path, failed: Path, log=print):
    """Claim and run units in order. fn(name) -> JSON-able result (written to cache/<name>.json.gz)."""
    cache.mkdir(parents=True, exist_ok=True); locks.mkdir(parents=True, exist_ok=True); failed.mkdir(parents=True, exist_ok=True)
    n_done = 0
    for name in names:
        if past_deadline():
            log(json.dumps({"event": "DEADLINE_STOP", "utc": utc()})); break
        out = cache / f"{name}.json.gz"
        if out.exists() or (failed / f"{name}.json").exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        t0 = time.time()
        try:
            res = fn(name)
            if isinstance(res, dict):
                res.setdefault("unit", name); res.setdefault("finished_utc", utc()); res.setdefault("seconds", time.time() - t0)
                res.setdefault("host", socket.gethostname()); res.setdefault("pid", os.getpid())
            atomic_write_json_gz(out, res); n_done += 1
            log(json.dumps({"unit": name, "status": "ok", "s": round(time.time() - t0, 2)}))
        except Exception as ex:
            atomic_write_text(failed / f"{name}.json", json.dumps({"unit": name, "error": f"{type(ex).__name__}: {ex}"[:1000],
                                                                  "traceback": traceback.format_exc()[-4000:], "utc": utc(), "pid": os.getpid()}, indent=1))
            log(json.dumps({"unit": name, "status": "FAILED", "error": f"{type(ex).__name__}: {ex}"[:300]}))
        finally:
            lock.unlink(missing_ok=True)
    return n_done
