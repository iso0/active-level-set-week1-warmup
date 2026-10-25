"""EL stage-2 freeze for the confirmation of system E (workers verify the SHA-256 manifest before any non-smoke unit).
    python -m src.el2_freeze manifest | check <job>
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261024" / "opus_early_learning"
MANIFEST = OUT / "freeze" / "EL2_FINAL_MANIFEST.json"
FILES = ["src/el_mix.py", "src/el2_freeze.py", "src/el_cross.py", "src/el_eval.py", "src/el_decide.py",
         "src/rc24_pac.py", "src/rc24p_final.py", "src/rc24p_models.py", "src/rc23_common.py", "src/rc22_common.py", "src/rc21_phr.py", "src/rc20_attr.py", "src/rc20_gp.py",
         "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week13_synthetic_al.py",
         "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv",
         "outputs/research_campaign_20261024/opus_early_learning/PROTOCOL_EL_OBJECTIVES.md",
         "outputs/research_campaign_20261024/opus_early_learning/PROTOCOL_EL2_MECHANISM.md",
         "outputs/research_campaign_20261024/opus_early_learning/PROTOCOL_EL2_FINAL.md"]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "files": {f: _sha(f) for f in FILES}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(job=None):
    if job is None or job.endswith("smoke"):
        return True
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"EL2 frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=1)[:800] if sys.argv[1] == "manifest" else f"EL2 manifest check: {check(sys.argv[2])}")
