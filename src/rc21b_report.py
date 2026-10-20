"""RC21B report: runs the FROZEN RC21 report code (src.rc21_report.final / export, unchanged file) with the RC21B constants
(src.rc21b_final: arms, repeats 35-42, Q1 / Q2, secondary contrasts, targets, spend rule) and the RC21B directories.
    python -m src.rc21b_report all [final|smoke]
"""
from __future__ import annotations

import sys

import src.rc18_common as RC
import src.rc21_report as R
import src.rc21b_final as FB

DIRS = {"final": {"job": "e-final", "rep": "b_final_report", "exp": "b_final_export"}, "smoke": {"job": "e-smoke", "rep": "b_smoke_report", "exp": "b_smoke_export"}}


def run(stage):
    R.F = FB                                                              # constants only; every function body is the frozen RC21 code
    R.use = lambda s: R.CFG.update(DIRS[s])
    V = R.final(stage)
    p = R.OUT / DIRS[stage]["rep"] / "FINAL.md"; t = p.read_text(encoding="utf-8")
    t = t.replace("# RC21 sequential stage", "# RC21B confirmation stage (PHR_NRMAP)", 1).replace("frozen protocol PROTOCOL_RC21_FINAL.md", "frozen protocol PROTOCOL_RC21B.md", 1)
    p.write_text(t, encoding="utf-8"); return V


if __name__ == "__main__":
    RC.limit_threads(1); run(sys.argv[2] if len(sys.argv) > 2 else "final")
