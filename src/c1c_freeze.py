"""C1C freeze: SHA-256 manifest of the recipe code, the unit code, the evaluation code, the data manifest and the protocols. Every worker of a
registered job (c1c-main, c1c-start, c1c-prior) verifies it before its first unit; a changed file stops the worker.
    python -m src.c1c_freeze manifest | check <job>
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
MANIFEST = OUT / "freeze" / "C1C_MANIFEST.json"
FILES = ["src/c1c_fwd.py", "src/c1c_prior.py", "src/c1c_eval.py", "src/c1c_export.py", "src/c1c_freeze.py",
         "src/ea_fwd.py", "src/ea_fwd_eval.py", "src/ea_cand.py", "src/ea_cand_eval.py", "src/ea_diag.py", "src/ea_diag2.py", "src/ea_export.py", "src/ea_freeze.py",
         "src/el_mix.py", "src/el_eval.py", "src/el_export.py", "src/el_cross.py",
         "src/rc24_pac.py", "src/rc24p_final.py", "src/rc24p_models.py", "src/rc23_common.py", "src/rc22_common.py", "src/rc21_phr.py", "src/rc20_attr.py", "src/rc20_gp.py",
         "src/rc19b_keyhole.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week13_synthetic_al.py",
         "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv",
         "outputs/research_campaign_20261026/opus_error_attribution/PROTOCOL_EA_CANDIDATES.md",
         "outputs/research_campaign_20261026/opus_error_attribution/PROTOCOL_EA_VALIDATION.md",
         "outputs/research_campaign_20261026/opus_error_attribution/freeze/EA_VALIDATION_MANIFEST.json",
         "outputs/research_campaign_20261026/opus_c1_confirmation/PROTOCOL_C1C.md",
         "outputs/research_campaign_20261026/opus_c1_confirmation/repro/REPRO_EA_UNITS.json",
         "outputs/research_campaign_20261026/opus_c1_confirmation/repro/REPRO_STARTUPS_RC22.json",
         "outputs/research_campaign_20261026/opus_c1_confirmation/repro/REPRO_PRIOR_SCALE1.json"]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); m = {"utc": RC.utc(), "files": {f: _sha(f) for f in FILES}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check(job=None):
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"C1C frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=1)[:800] if sys.argv[1] == "manifest" else f"C1C manifest check: {check(sys.argv[2])}")
