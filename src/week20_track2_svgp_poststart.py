"""POST-START sensitivity T2-PS1 (track2/POSTSTART_DECLARATION.md): the frozen separable SVGP with 6000 instead of 2000
iterations at the five repeat-1 B40 checkpoints.  The frozen script src/week20_track2_svgp.py is imported unchanged.
Run with the project venv:  .venv/Scripts/python.exe -m src.week20_track2_svgp_poststart
"""
from __future__ import annotations

import src.week20_track2_svgp as S

NAMES = [f"ckpt_r1_f{f}_B40" for f in range(1, 6)]

if __name__ == "__main__":
    S.CONFIG["iterations"] = 6000            # the only change (train() reads this dict at call time)
    for n in NAMES:
        S.fit_checkpoint(n, tag="svgp_it6000")
