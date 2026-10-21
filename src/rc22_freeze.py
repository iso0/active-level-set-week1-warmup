"""RC22 freezes: F1 (robustness + ingredients + audit; jobs g-ingr, g-miss, g-start, g-block) and F2 (acquisition; job g-acq).
Each manifest hashes the protocol and every code file the stage uses; workers verify it before any unit.
    python -m src.rc22_freeze manifest F1|F2 | check F1|F2
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
BASE = ["src/rc22_common.py", "src/rc22_jobs.py", "src/rc22_eval.py", "src/rc21_phr.py", "src/rc21_attr.py", "src/rc20_attr.py", "src/rc20_gp.py",
        "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py", "src/rc18_campaign.py", "src/rc18_gp.py",
        "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py",
        "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv",
        "outputs/research_campaign_20261021/opus_rc22/PROTOCOL_RC22.md"]
FILES = {"F1": BASE, "F2": BASE + ["src/rc22_decisions.py", "outputs/research_campaign_20261021/opus_rc22/PROTOCOL_RC22_ACQ.md"]}


def stage_of(job):
    return {"g-acq": "F2", "g-smoke": None}.get(job, "F1")


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def path(stage):
    return OUT / "freeze" / f"RC22_{stage}_MANIFEST.json"


def manifest(stage):
    path(stage).parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "stage": stage, "files": {f: _sha(f) for f in FILES[stage]}}
    path(stage).write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(stage):
    if stage is None:
        return True
    m = json.loads(path(stage).read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC22 {stage} frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(manifest(sys.argv[2]), indent=1)[:2000])
    else:
        print("RC22", sys.argv[2], "manifest check:", check(sys.argv[2]))
