"""RC19 final programme (pooled from scratch): frozen job list, code/data manifest and the start-up check of every worker.

    python -m src.rc19_final manifest      # writes opus_pooled/final/RC19_FINAL_MANIFEST.json (run once, then commit)
    python -m src.rc19_final check         # verifies every frozen hash; workers call this before claiming a unit
Workers: python -m src.rc19_jobs work <final job> --threads 1   (refuse to start if any frozen hash changed)
"""
from __future__ import annotations

import hashlib
import json
import sys

import src.rc18_common as RC
import src.rc19_pool as P

MANIFEST = P.OUT / "final" / "RC19_FINAL_MANIFEST.json"
FROZEN = ["src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_jobs.py", "src/rc19_final.py", "src/rc19_eval.py", "src/rc18_campaign.py", "src/rc18_gp.py",
          "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py",
          "src/external_validation/analysis.py", "src/rc18_temporal.py", "src/jdl_temporal_vel.py", "src/jdl_stage_m.py",
          "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv",
          "outputs/research_campaign_20261018/opus/temporal/FEATURES.csv", "outputs/research_campaign_20261018/opus/temporal/CURVES.npz"]

# (kind, model-or-arm, design, horizon); set from the development stage (ledger RC19-DEV) and frozen with the protocol
JOBS = {
    "final-label": [("label", a, None, 60) for a in ("E1_STRADDLE", "PHYSCF_ATS_MARGIN", "G3_MARGIN", "E1_MAXIMIN", "PHYSCF_A_MARGIN",
                                                     "PHYSMC_ATS_MARGIN", "PHYSCF_ATS_MAXIMIN")],
    "final-region": [("region", m, a, 60) for m in ("SHQ", "M0") for a in ("STRADDLE", "MAXIMIN", "RANDOM", "TRUVAR")],
    "final-reg": [("reg", m, "MAXIMIN", 80) for m in ("SHQ", "M0", "M0Q")] + [("reg", m, a, 80) for m in ("SHQ", "M0Q") for a in ("RANDOM", "MOIVR")],
    "final-temporal": [("temporal", "M0Q", "PATH", 40)],
}
# pre-declared endpoints (PROTOCOL_RC19.md section 4); levels from the development full-pool attainable R2 (0.9 x attainable,
# rounded down to 0.05), never from final outcomes
PRIMARY_TARGETS = ("log_A_um", "log_ke_T0_nJ", "vmax_spike_logratio", "vmax_spike_us", "laser_T0_W", "tmax_T0_K", "log_etot_T0_J", "log_npart_T0")
LEVELS = {"log_A_um": 0.85, "log_ke_T0_nJ": 0.85, "vmax_spike_logratio": 0.80, "vmax_spike_us": 0.60, "laser_T0_W": 0.85, "tmax_T0_K": 0.85,
          "log_etot_T0_J": 0.80, "log_npart_T0": 0.80}
H = {"reg": 80, "region": 60, "label": 60}
MARGIN = {"reg": 0.02, "region": 0.02, "label": 0.02}
MIN_POSITIVE = 7                               # of the 8 final repeats, for BETTER / WORSE
TAU = 0.6931471805599453                       # log 2
BA_LEVEL = {"region": 0.95, "label": 0.93}
PRIMARY_C = ("PHYSCF_ATS_MARGIN", "E1_STRADDLE")


def _sha(path):
    return hashlib.sha256((RC.ROOT / path).read_bytes()).hexdigest()


def write_manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "protocol": "outputs/research_campaign_20261018/opus_pooled/PROTOCOL_RC19.md", "repeats": list(P.FINAL_REPEATS),
         "files": {f: _sha(f) for f in FROZEN + ["outputs/research_campaign_20261018/opus_pooled/PROTOCOL_RC19.md"]},
         "jobs": {k: [list(map(str, s)) for s in v] for k, v in JOBS.items()}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC19 frozen files changed since the manifest: {bad}")
    if {k: [list(map(str, s)) for s in v] for k, v in JOBS.items()} != m["jobs"]:
        raise SystemExit("RC19 job list differs from the frozen manifest")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(write_manifest(), indent=1)[:2000])
    elif sys.argv[1] == "check":
        print("RC19 final manifest check:", check())
