"""Regression gate of the thesis repository (finalization 2026-11-02): the Weeks 12+ suite = src/tests without the
historical test_week1 ... test_week11 files (those check old layouts and rewrite three tracked Week 9 outputs; run them
only in a scratch worktree). BLAS threads stay at the machine default unless --threads is given; the T_TOBIT test pins
its own freeze-time setting (8 threads).

    python tools/run_regression_gate.py [--threads N] [--log path]
Expected on the final tree: 219 passed, 2 skipped, 0 failed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = re.compile(r"^test_week([1-9]|10|11)(_|\.|[a-z])")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=None, help="set OMP/OPENBLAS/MKL threads (default: machine default)")
    ap.add_argument("--log", default=None, help="write the full pytest output here")
    a = ap.parse_args()
    env = dict(os.environ)
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        if a.threads is None:
            env.pop(k, None)
        else:
            env[k] = str(a.threads)
    files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "src" / "tests").glob("test_*.py") if not OLD.match(p.name))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    head = f"# regression gate: {len(files)} files, BLAS threads={a.threads or 'default'}, {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n"
    if a.log:
        Path(a.log).write_text(head + r.stdout + r.stderr, encoding="utf-8")
    print(head.strip())
    print("\n".join(r.stdout.strip().splitlines()[-4:]))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
