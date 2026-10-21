"""RC23 freeze: the protocol and every code file the RC23 jobs and the evaluation use; workers verify it before any unit.
    python -m src.rc23_freeze manifest | check
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
MANIFEST = OUT / "freeze" / "RC23_MANIFEST.json"
FILES = ["src/rc23_common.py", "src/rc23_jobs.py", "src/rc23_eval.py", "src/rc22_common.py", "src/rc22_eval.py", "src/rc21_phr.py", "src/rc20_attr.py",
         "src/rc20_gp.py", "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py", "src/rc18_campaign.py",
         "src/rc18_gp.py", "src/rc18_common.py", "src/week13_synthetic_al.py", "src/external_validation/analysis.py",
         "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", "outputs/research_campaign_20261021/opus_rc23/PROTOCOL_RC23.md"]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "files": {f: _sha(f) for f in FILES}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(job=None):
    if job == "h-smoke":
        return True
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC23 frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=1)[:1500] if sys.argv[1] == "manifest" else f"RC23 manifest check: {check()}")
