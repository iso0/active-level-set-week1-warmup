"""RC24 freeze: the stage protocol and every code file its jobs and evaluation use; workers verify the stage manifest before
any unit (smoke jobs excepted).
    python -m src.rc24_freeze manifest <stage> | check <stage>
Stages: A (src/rc24_jobs.py a-own / a-match; evaluation src/rc24_eval.py). Later stages register their own file lists.
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
COMMON = ["src/rc23_common.py", "src/rc22_common.py", "src/rc22_eval.py", "src/rc23_eval.py", "src/rc21_phr.py", "src/rc20_attr.py", "src/rc20_gp.py",
          "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py", "src/rc18_campaign.py", "src/rc18_gp.py",
          "src/rc18_common.py", "src/week18_engine.py", "src/week13_synthetic_al.py", "src/external_validation/analysis.py",
          "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv"]
STAGES = {"A": {"files": ["src/rc24_models.py", "src/rc24_jobs.py", "src/rc24_eval.py", "src/rc24_correction.py", "outputs/research_campaign_20261021/opus_rc24/PROTOCOL_RC24_STAGE_A.md"] + COMMON,
                "jobs": ("a-own", "a-match")},
          "C": {"files": ["src/rc24_confirm.py", "src/rc24_pac.py", "src/rc24_pilot.py", "src/rc24_eval_c.py", "src/rc24_eval.py", "src/rc24_correction.py", "src/rc24_jeer.py",
                          "outputs/research_campaign_20261021/opus_rc24/PROTOCOL_RC24_STAGE_C.md", "outputs/research_campaign_20261021/opus_rc24/PRIMARY.txt"] + COMMON,
                "jobs": ("c-own", "c-match")},
          "S": {"files": ["src/rc24_synth.py", "src/rc24_synth_eval.py", "src/rc24_pac.py", "src/rc24_pilot.py", "src/rc24_jeer.py",
                          "outputs/research_campaign_20261021/opus_rc24/synthetic/PREREG_SYNTHETIC_TEST.md"] + COMMON,
                "jobs": ("s-test",)}}


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def _path(stage):
    return OUT / "freeze" / f"RC24_STAGE_{stage}_MANIFEST.json"


def manifest(stage):
    p = _path(stage); p.parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "stage": stage, "files": {f: _sha(f) for f in STAGES[stage]["files"]}}
    p.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(job=None):
    if job is None or job.endswith("smoke"):
        return True
    stage = [s for s, v in STAGES.items() if job in v["jobs"]]
    if not stage:
        raise SystemExit(f"RC24 job {job} belongs to no frozen stage")
    m = json.loads(_path(stage[0]).read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC24 stage {stage[0]} frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    print(json.dumps(manifest(sys.argv[2]), indent=1)[:2000] if sys.argv[1] == "manifest" else f"RC24 manifest check: {check(sys.argv[2])}")
