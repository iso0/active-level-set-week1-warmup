"""GT exports (PROTOCOL_GT.md section 7): per stage, the test-row predictions of every system (float32) and the query IDs of every path.
  exports/<stage>/predictions_f32.npz   keys "<system>|<condition>|<cluster>|<learner>" -> (n_budgets x n_test) float32, plus
                                        "<...>|test_ids" and "<...>|budgets"
  exports/<stage>/paths.csv.gz          path, condition, cluster, learner, query, sim_id
    python -m src.gt_export g2 | g3 | g4
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

import src.gt_dev as DV
import src.gt_eval as GE
import src.rc18_common as RC

OUT = DV.OUT / "exports"


def write(stage, E, paths, parts=None):
    """parts: list of system groups, one npz file each (keeps every file well below the 100 MB host limit); default = one file.
    C1_recomputed is not exported: it equals the recorded C1 exactly (acceptance V4, max |diff| 0.0)."""
    d = OUT / stage; d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("predictions_f32*.npz"):
        old.unlink()
    systems = sorted({k[0] for k in E if k[0] != "C1_recomputed"}); parts = parts or [systems]; man = {"utc": RC.utc(), "stage": stage, "files": {}}
    for i, grp in enumerate(parts, 1):
        arr = {}
        for (sy, c, r, f), (bs, Pm, ids) in E.items():
            if sy not in grp:
                continue
            k = f"{sy}|{c}|{r}|{f}"; arr[k] = np.asarray(Pm, np.float32); arr[k + "|budgets"] = np.asarray(bs, np.int16); arr[k + "|test_ids"] = np.asarray(ids, str)
        name = "predictions_f32.npz" if len(parts) == 1 else f"predictions_f32_part{i}.npz"
        np.savez_compressed(d / name, **arr)
        man["files"][name] = {"systems": list(grp), "keys": len(arr) // 3, "sha256": hashlib.sha256((d / name).read_bytes()).hexdigest()}
    pd.DataFrame(paths, columns=["path", "condition", "cluster", "learner", "query", "sim_id"]).to_csv(d / "paths.csv.gz", index=False, lineterminator="\n")
    man["sha256_paths"] = hashlib.sha256((d / "paths.csv.gz").read_bytes()).hexdigest(); man["not_exported"] = "C1_recomputed (= recorded C1, V4 max |diff| 0.0)"
    (d / "EXPORT_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps(man))


def g2():
    E, _, _ = GE.load_g2(); paths = []
    for c in DV.DEV:
        for r in DV.DEV[c]:
            for f in range(1, DV.NL[c] + 1):
                for q, s in enumerate(DV.recorded(c, r, f)["paid_ids"][:60], 1):
                    paths.append(("C1-selected (recorded EA)", c, r, f, q, s))
    write("g2", E, paths, parts=[["C1", "CAL_B1", "C1_G", "C1_T", "ORACLE_T"], ["GEO_A1", "GEO_A2", "GEO_B1", "GEO_B2", "GEO_B3"]])


def g3():
    E, _, paths = GE.load_g3(); write("g3", E, paths)


def g4():
    E, _, paths = GE.load_g4(); write("g4", E, paths)


if __name__ == "__main__":
    {"g2": g2, "g3": g3, "g4": g4}[sys.argv[1]]()
