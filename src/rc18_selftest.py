"""Runner machinery self-test (no model fits): 3 units that sleep briefly; one raises on purpose when RC18_SELFTEST_FAIL=1.
    python -m src.rc18_selftest work --threads 1
"""
import os
import sys
import time

import src.rc18_common as RC

CACHE = RC.CAMP / "runner" / "selftest" / "done"
LOCKS = RC.CAMP / "runner" / "selftest" / "locks"
FAILED = RC.CAMP / "runner" / "selftest" / "failed"


def unit(name):
    time.sleep(3)
    if name == "u3" and os.environ.get("RC18_SELFTEST_FAIL") == "1":
        raise RuntimeError("deliberate self-test failure")
    return {"ok": True, "name": name}


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step == "work":
        RC.limit_threads(1); RC.run_units(["u1", "u2", "u3"], unit, CACHE, LOCKS, FAILED, log=lambda s: print(s, flush=True))
    elif step == "crash":                      # worker-level crash path: exits non-zero without writing anything
        time.sleep(2); raise SystemExit(3)
