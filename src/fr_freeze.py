"""FR freeze: SHA-256 manifest of the candidate, unit, evaluation code, the data manifest and the protocols. Every worker of the registered
fresh job (fr-fresh) verifies it before its first unit; a changed file stops the worker.
    python -m src.fr_freeze manifest | check <job>
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness"
MANIFEST = OUT / "freeze" / "FR_MANIFEST.json"
FILES = ["src/fr_gate.py", "src/fr_eval.py", "src/fr_freeze.py", "src/fr_gain.py", "src/fr_dev_eval.py", "src/fr_inventory.py",
         "src/ea_fwd.py", "src/ea_cand.py", "src/ea_cand_eval.py", "src/ea_diag.py", "src/ea_diag2.py", "src/el_mix.py", "src/el_eval.py", "src/el_cross.py",
         "src/rc24_pac.py", "src/rc24p_final.py", "src/rc24p_models.py", "src/rc23_common.py", "src/rc22_common.py", "src/rc21_phr.py", "src/rc20_attr.py", "src/rc20_gp.py",
         "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week13_synthetic_al.py",
         "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv",
         "outputs/research_campaign_20261029/opus_final_robustness/GAIN_AREA_PROTOCOL.md",
         "outputs/research_campaign_20261029/opus_final_robustness/PROTOCOL_FR_DEV.md",
         "outputs/research_campaign_20261029/opus_final_robustness/PROTOCOL_FR_FRESH.md",
         "outputs/research_campaign_20261029/opus_final_robustness/gain/GAIN_AREA.json",
         "outputs/research_campaign_20261029/opus_final_robustness/dev/DEV_GATE.json",
         "outputs/research_campaign_20261029/opus_final_robustness/dev/SMOKE.json",
         "outputs/research_campaign_20261029/opus_final_robustness/freeze/ID_INVENTORY.json"]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "files": {f: _sha(f) for f in FILES}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(job=None):
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"FR frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(manifest(), indent=1)[:400])
    elif sys.argv[1] == "check":
        print(check(sys.argv[2] if len(sys.argv) > 2 else None))
