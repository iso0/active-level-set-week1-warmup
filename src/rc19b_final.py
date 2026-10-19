"""RC19B final programme: frozen job lists, pre-declared contrasts and the start-up hash check of every final worker.
Fresh DEV repeats 11-18 (never run before this freeze); the RC19 information contract and splits rule (seed [1919, r]).
    python -m src.rc19b_final manifest | check
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
MANIFEST = OUT / "final" / "RC19B_FINAL_MANIFEST.json"
PROTOCOL = "outputs/research_campaign_20261018/opus_rc19b/PROTOCOL_RC19B.md"
REPEATS = (11, 12, 13, 14, 15, 16, 17, 18)
FROZEN = ["src/rc19b_keyhole.py", "src/rc19b_duration.py", "src/rc19b_jobs.py", "src/rc19b_final.py", "src/rc19b_keyhole_eval.py", "src/rc19b_duration_eval.py",
          "src/rc19b_repair.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py", "src/rc19_final.py", "src/rc18_campaign.py",
          "src/rc18_gp.py", "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py",
          "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", PROTOCOL]

# ---- set from the development stage (replays on RC19 final repeats 3-10) and frozen with PROTOCOL_RC19B.md
KEYHOLE_ARMS = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
KEYHOLE_PRIMARY = ("ATSCF_MARGIN", "E1CAL+straddle", "LL_AULC", "lower", 0.02)       # (arm, reference, metric, direction, margin)
KEYHOLE_PAIRS = [("ATSCF_MARGIN", "E1CAL+straddle"), ("ATSCF_MARGIN", "DEPTHCF_MARGIN"), ("DEPTHCF_MARGIN", "E1CAL+straddle"), ("E1CAL+straddle", "E1RAW+straddle"),
                 ("ATSCF_MARGIN", "ATSAPPROX_MARGIN"), ("ATSCF_MARGIN", "G3_MARGIN"), ("ATSCF_MARGIN", "E1RAW+straddle")]
MIN_BETTER = 7
DURATION_VARIANT = "QS_LOG"
REG_ARMS = (("SHQ", "RANDOM"), ("M0Q", "MOIVR"), ("SHQ", "MOIVR"), ("SHQ", "MOIVRB"))


def units(job):
    if job == "b-final-label":
        return [(f"r{r}_f{f}__{a}", ("label", a, r, f)) for r in REPEATS for f in range(1, 6) for a in KEYHOLE_ARMS]
    if job == "b-final-reg":
        return [(f"r{r}_f{f}__{m}__{a}", ("reg", (m, a), r, f)) for r in REPEATS for f in range(1, 6) for (m, a) in REG_ARMS]
    raise ValueError(job)


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def write_manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "repeats": list(REPEATS), "files": {f: _sha(f) for f in FROZEN},
         "constants": {"KEYHOLE_ARMS": KEYHOLE_ARMS, "KEYHOLE_PRIMARY": KEYHOLE_PRIMARY, "KEYHOLE_PAIRS": KEYHOLE_PAIRS, "MIN_BETTER": MIN_BETTER,
                       "DURATION_VARIANT": DURATION_VARIANT, "REG_ARMS": REG_ARMS},
         "units": {j: len(units(j)) for j in ("b-final-label", "b-final-reg")}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC19B frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(write_manifest(), indent=1)[:3000])
    elif sys.argv[1] == "check":
        print("RC19B manifest check:", check())
