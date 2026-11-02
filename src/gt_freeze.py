"""GT freeze before G4 (PROTOCOL_GT.md section 5): records GEO*, the selector and the SHA-256 of every code file a G4 unit or the G4
evaluation executes; the G4 workers call check() and refuse to run if any file changed. Written only when G3's registered transition
rule says go.
    python -m src.gt_freeze write | check
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import src.gt_dev as DV
import src.rc18_common as RC

FILES = ["src/gt_own.py", "src/gt_geo.py", "src/gt_data.py", "src/gt_eval.py", "src/gt_recompute.py", "src/gt_export.py", "src/ea_cand.py", "src/ea_fwd.py",
         "src/ea_diag.py", "src/ea_diag2.py", "src/rc18_gp.py", "src/rc18_common.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19b_keyhole.py",
         "src/rc20_attr.py", "src/rc21_phr.py", "src/rc22_common.py", "src/rc23_common.py", "src/rc24_pac.py", "src/el_cross.py", "src/el_eval.py",
         "src/ea_fwd_eval.py", "src/ea_cand_eval.py", "src/el_mix.py"]
F = DV.OUT / "freeze" / "G4_FREEZE.json"


def digest():
    return {f: hashlib.sha256((RC.ROOT / f).read_bytes()).hexdigest() for f in FILES}


def write():
    g3 = json.loads((DV.OUT / "dev" / "G3_RESULT.json").read_text(encoding="utf-8")); tr = g3["transition"]
    if not tr["go_to_G4"]:
        raise SystemExit("G3 transition rule says STOP: no G4 freeze")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=RC.ROOT).stdout.strip()
    obj = {"utc": RC.utc(), "system": g3["GEO_star"], "selector": tr["selector"], "git_head_at_freeze": head, "files_sha256": digest(),
           "fresh_ids": {"STD": "383-462", "K5": "49-56", "K4": "33-40"}, "rule": "PROTOCOL_GT section 5 G4"}
    F.parent.mkdir(parents=True, exist_ok=True); F.write_text(json.dumps(obj, indent=1), encoding="utf-8"); print(json.dumps(obj, indent=1))


def check():
    obj = json.loads(F.read_text(encoding="utf-8")); now = digest(); bad = [f for f in FILES if obj["files_sha256"].get(f) != now[f]]
    if bad:
        raise RuntimeError(f"frozen code changed: {bad}")
    return True


if __name__ == "__main__":
    {"write": write, "check": lambda: print(check())}[sys.argv[1]]()
