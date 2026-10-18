"""Single coordination record of research campaign 20261018 (shared by Opus and Astra).

The record is outputs/joint_depth_label_development/pool/POOL_PLAN.json. It is the one machine-readable record; COORDINATION.md
is its human-readable log. Update protocol (both parties): create pool/COORDINATION.lock exclusively (a lock older than 120 s
is stale and may be removed), read the JSON, change only your own share/jobs, write a temporary file in the same directory,
os.replace() it over the record, then delete the lock.  Never edit the other party's share.

    python -m src.rc18_coord show
    python -m src.rc18_coord set-jobs --owner Opus --jobs-json '[...]'
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "outputs" / "joint_depth_label_development" / "pool" / "POOL_PLAN.json"
LOCK = RECORD.parent / "COORDINATION.lock"
STALE_S = 120


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def locked(timeout_s=60):
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "utc": utc()}).encode()); os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - LOCK.stat().st_mtime > STALE_S:
                    LOCK.unlink(missing_ok=True); continue
            except FileNotFoundError:
                continue
            if time.time() - t0 > timeout_s:
                raise TimeoutError("coordination record is locked")
            time.sleep(0.5)
    try:
        yield
    finally:
        LOCK.unlink(missing_ok=True)


def read():
    return json.loads(RECORD.read_text(encoding="utf-8-sig"))


def write(rec):
    tmp = RECORD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, RECORD)


def update(fn):
    """Apply fn(record) -> None under the lock, atomically."""
    with locked():
        rec = read(); fn(rec); rec.setdefault("coordination", {})["last_update_utc"] = utc(); write(rec)
        return rec


def set_jobs(owner, jobs):
    def fn(rec):
        for s in rec["coordination"]["shares"]:
            if s["owner"] == owner:
                s["jobs"] = jobs; s["jobs_updated_utc"] = utc(); return
        raise KeyError(owner)
    return update(fn)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        print(json.dumps(read().get("coordination"), indent=1))
    elif cmd == "set-jobs":
        owner = sys.argv[sys.argv.index("--owner") + 1]; jobs = json.loads(sys.argv[sys.argv.index("--jobs-json") + 1])
        set_jobs(owner, jobs); print("ok")
