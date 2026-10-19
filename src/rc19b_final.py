"""RC19B final programme: frozen job lists, pre-declared contrasts and the start-up hash check of every final worker.
Fresh DEV repeats 11-18 (never run before this freeze); the RC19 information contract and splits rule (seed [1919, r]).
Design choices below were made on the development replays (RC19 final repeats 3-10) with the rules recorded in the ledger row
RC19B-SELECT-RULES before those replays were read.
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
SMOKE_REPEAT = 1                                            # seen DEV repeat, used only to smoke-test the code paths before the freeze
FROZEN = ["src/rc19b_keyhole.py", "src/rc19b_duration.py", "src/rc19b_jobs.py", "src/rc19b_final.py", "src/rc19b_keyhole_eval.py", "src/rc19b_duration_eval.py",
          "src/rc19b_report.py", "src/rc19b_repair.py", "src/rc19b_validate.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py",
          "src/rc19_final.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py",
          "src/week17_audit_impact.py", "src/week13_synthetic_al.py", "src/external_validation/analysis.py",
          "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", PROTOCOL]

# ---- Keyhole (paired adaptive arms, B8 -> B60, every budget recorded)
CF_K = 10            # Rule K: ATSCF LL-AULC on the label-free replay paths LOO 0.1863, K=10 0.1870 (within 0.002 -> cheaper), K=5 0.1911
KEYHOLE_ARMS = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
KEYHOLE_PRIMARY = ("ATSCF_MARGIN", "E1CAL+straddle", "LL_AULC", "lower", 0.02)       # (arm, reference, metric, direction, margin)
KEYHOLE_PAIRS = [("ATSCF_MARGIN", "E1CAL+straddle"), ("ATSCF_MARGIN", "E1RAW+straddle"), ("ATSCF_MARGIN", "DEPTHCF_MARGIN"), ("DEPTHCF_MARGIN", "E1CAL+straddle"),
                 ("E1CAL+straddle", "E1RAW+straddle"), ("ATSCF_MARGIN", "ATSAPPROX_MARGIN"), ("ATSCF_MARGIN", "G3_MARGIN"), ("ATSAPPROX_MARGIN", "E1RAW+straddle")]
MARGINS = {"BA_AULC": 0.02, "LL_AULC": 0.02, "Brier_AULC": 0.005}
METRIC_DIRECTION = {"BA_AULC": "higher", "LL_AULC": "lower", "Brier_AULC": "lower"}
MIN_BETTER = 7
DECOMP_PAIRS = [("ATSCF", "E1CAL"), ("ATSCF", "DEPTHCF"), ("DEPTHCF", "E1CAL"), ("E1CAL", "E1RAW"), ("ATSCF", "ATSAPPROX"), ("ATSCF", "G3")]

# ---- physical outputs (B8 -> B80, recorded every 4)
DURATION_VARIANT = "QS_RAW"   # Rule V: QS_RAW 0.468 and QG3_RAW 0.467 duration R2-AULC (within 0.005), 9 vs 9 joint completions -> QS over QG3
REG_ARMS = (("SHQ", "RANDOM"), ("M0Q", "MOIVR"), ("SHQ", "MOIVR"), ("SHQ", "MOIVRB"))
REG_REFERENCE = ("SHQ", "RANDOM")
DUR_MARGIN = 0.02             # D1: duration R2-AULC, hurdle minus the arm's own GP, matched path
JOINT_GAIN = 2                # D2: IMPROVED iff >= 2 more of 8 repeats complete jointly by B80 and none is lost
SPEND_MARGIN = 4              # D3: joint confirmation spend (hurdle duration), censored = 84 (a lower bound), one recorded step


def units(job):
    if job in ("b-final-label", "b-smoke-label"):
        reps = REPEATS if job == "b-final-label" else (SMOKE_REPEAT,); folds = range(1, 6)
        return [(f"r{r}_f{f}__{a}", ("label", a, r, f)) for r in reps for f in folds for a in KEYHOLE_ARMS]
    if job in ("b-final-reg", "b-smoke-reg"):
        reps = REPEATS if job == "b-final-reg" else (SMOKE_REPEAT,); folds = range(1, 6)
        return [(f"r{r}_f{f}__{m}__{a}", ("reg", (m, a), r, f)) for r in reps for f in folds for (m, a) in REG_ARMS]
    raise ValueError(job)


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def write_manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "repeats": list(REPEATS), "files": {f: _sha(f) for f in FROZEN},
         "constants": {"CF_K": CF_K, "KEYHOLE_ARMS": KEYHOLE_ARMS, "KEYHOLE_PRIMARY": KEYHOLE_PRIMARY, "KEYHOLE_PAIRS": KEYHOLE_PAIRS, "MARGINS": MARGINS,
                       "MIN_BETTER": MIN_BETTER, "DECOMP_PAIRS": DECOMP_PAIRS, "DURATION_VARIANT": DURATION_VARIANT, "REG_ARMS": REG_ARMS,
                       "REG_REFERENCE": REG_REFERENCE, "DUR_MARGIN": DUR_MARGIN, "JOINT_GAIN": JOINT_GAIN, "SPEND_MARGIN": SPEND_MARGIN},
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
