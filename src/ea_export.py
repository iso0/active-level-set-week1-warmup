"""EA exports and independent recomputation (after the decisions; nothing here changes any rule or input).
  exports/ladder_<cond>   every rung (and the amendment diagnostics D2, D3, D2T) on the ladder grid (8..24 every budget, 28..60 every 4),
                          COMMON test rows only (rows with a recorded depth), + the recorded HA_LEAN path ids; independent check of the
                          per-learner early (8..24) and late (28..60 grid) BA means against diagnosis/*.csv
  exports/d4_std          the corner-capped margin paths (diagnostic) every budget + their paid ids; check with src.el_export
  exports/cand_dev_<cond> C1, C1a, C1b, A, D, E on the recorded HA_LEAN paths, every budget; check with src.el_export
  exports/validation_<cond>  C1_own, A_own, C1_on_A, D_on_A, E_on_A, A_on_C1 every budget + both paths' paid ids; check with src.el_export
    python -m src.ea_export
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.ea_cand as CA
import src.ea_diag as DG
import src.el_eval as EV
import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

BASE = DG.OUT / "exports"


def _rows_paths(u, label, cond, systems, hows=None):
    out = []
    for q, s in enumerate(u["paid_ids"][:60], 1):
        out.append({"path": label, "systems": systems, "condition": cond, "cluster": u["repeat"], "learner": u["fold"], "query": q, "sim_id": s,
                    "rule": "startup" if q <= 8 else ((hows[q - 9] if hows and q - 9 < len(hows) and hows[q - 9] else "margin"))})
    return out


def ladder(cond, M):
    E = {}; paths = []
    for fp in sorted((DG.OUT / "ea-diag" / "units").glob(f"{cond}__*.json.gz")):
        u = RC.read_json_gz(fp); r, f = int(u["repeat"]), int(u["fold"]); ok = np.asarray(u["test_has_depth"], bool); ids = np.asarray(u["test_ids"], str)[ok]
        bs = np.array([e["budget"] for e in u["evals"]], int)
        for k in DG.RUNGS:
            E[(k, cond, r, f)] = (bs, np.array([np.asarray(e["p"][k], float)[ok] for e in u["evals"]]), ids)
        if cond == "STD":
            d2 = RC.read_json_gz(DG.OUT / "ea-diag2" / "units" / fp.name); d2t = RC.read_json_gz(DG.OUT / "ea-d2t" / "units" / fp.name)
            for k in ("D2_hp_oracle", "D3_lin_h"):
                E[(k, cond, r, f)] = (bs, np.array([np.asarray(e["p"][k], float)[ok] for e in d2["evals"]]), ids)
            E[("D2T_trend_hp_oracle", cond, r, f)] = (bs, np.array([np.asarray(e["p"], float)[ok] for e in d2t["evals"]]), ids)
        src = DG.path_unit(cond, r, f); paths += _rows_paths(src, "HA_LEAN-selected (recorded, EL-1 forward)", cond, "all rungs", [e.get("how") for e in src["evals"]])
    d = BASE / f"ladder_{cond.lower()}"; n = EX.export_set(d, E, paths)
    # independent recomputation on the ladder grid
    Z = EX.load(d); y_all = dict(zip(M.index.astype(str), M.y.astype(int))); rec = []
    for (sy, c, cl, l), (bs, Pm, ids) in Z.items():
        y = np.array([y_all[s] for s in ids], int); ba = []
        for j in range(len(bs)):
            hat = Pm[j] >= 0.5; ba.append(0.5 * (hat[y == 1].mean() + (~hat[y == 0]).mean()) if (y == 1).any() and (y == 0).any() else np.nan)
        ba = dict(zip(bs, ba)); rec.append({"rung": sy, "cluster": cl, "learner": l, "early": np.mean([ba[b] for b in bs if b <= 24]), "late": np.mean([ba[b] for b in bs if b >= 28])})
    R = pd.DataFrame(rec)
    W = pd.read_csv(DG.OUT / "diagnosis" / f"{cond.lower()}_window_individual.csv.gz").pivot_table(index=["rung", "cluster", "learner"], columns="window", values="BA").reset_index()
    j = R.merge(W, on=["rung", "cluster", "learner"], how="inner")
    acc = {"condition": cond, "curves": int(len(R)), "compared": int(len(j)), "max_abs_diff_early": float(np.nanmax(np.abs(j.early - j.early_B8_B24))) if len(j) else np.nan,
           "max_abs_diff_late": float(np.nanmax(np.abs(j.late - j.late_B28_B60))) if len(j) else np.nan, "keys": n}
    acc["PASS"] = bool(acc["compared"] > 0 and acc["max_abs_diff_early"] <= 1e-9 and acc["max_abs_diff_late"] <= 1e-9)
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); return acc


def d4(M):
    E = {}; paths = []
    for fp in sorted((DG.OUT / "ea-diag2" / "units").glob("STD__*.json.gz")):
        u = RC.read_json_gz(fp); r, f = int(u["repeat"]), int(u["fold"]); ids = np.asarray(u["test_ids"], str); cap = u["D4_capped"]
        E[("D4_corner_capped", "STD", r, f)] = (np.array([e["budget"] for e in cap["evals"]], int), np.array([e["p"] for e in cap["evals"]], float), ids)
        ref = DG.path_unit("STD", r, f); E[("A_margin_recorded", "STD", r, f)] = (np.array([e["budget"] for e in ref["evals"]], int), np.array([e["p"]["HA_LEAN"] for e in ref["evals"]], float), np.asarray(ref["test_ids"], str))
        paths += _rows_paths({"paid_ids": cap["paid_ids"], "repeat": r, "fold": f}, "corner-capped margin (diagnostic)", "STD", "D4_corner_capped")
    d = BASE / "d4_std"; n = EX.export_set(d, E, paths)
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, "STD"), "keys": n}


def cand_dev(cond, M):
    import src.ea_cand_eval as CE
    E, CPU = CE.load(cond); paths = []
    for fp in sorted((CA.OUT / "ea-cand-dev" / "units").glob(f"{cond}__*.json.gz")):
        u = RC.read_json_gz(fp); src = CA.dev_path_unit(cond, int(u["repeat"]), int(u["fold"]))
        paths += _rows_paths(src, "HA_LEAN-selected (recorded, EL-2 confirmation)", cond, "A,D,E,C1,C1a,C1b", [e.get("how") for e in src["own_evals"]])
    d = BASE / f"cand_dev_{cond.lower()}"; n = EX.export_set(d, E, paths)
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, cond), "keys": n}


def validation(cond, M):
    import src.ea_fwd_eval as FE
    E, CPU, CHK = FE.load(cond); paths = []
    for fL in sorted((CA.OUT / "ea-fwd" / "units").glob(f"{cond}__*__L.json.gz")):
        uL = RC.read_json_gz(fL); uX = RC.read_json_gz(fL.with_name(fL.name.replace("__L.json.gz", "__X.json.gz")))
        paths += _rows_paths(uL, "HA_LEAN-selected", cond, "A_own,C1_on_A,D_on_A,E_on_A", [e.get("how") for e in uL["evals"]])
        paths += _rows_paths(uX, "C1-selected", cond, "C1_own,A_on_C1", [e.get("how") for e in uX["evals"]])
    d = BASE / f"validation_{cond.lower()}"; n = EX.export_set(d, E, paths)
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, cond), "keys": n}


def run(which=("ladder", "d4", "cand_dev", "validation")):
    M = P.manifest(); acc = {}
    if "ladder" in which:
        for c in ("STD", "K5", "K4"):
            acc[f"ladder_{c.lower()}"] = ladder(c, M)
    if "d4" in which:
        acc["d4_std"] = d4(M)
    if "cand_dev" in which:
        for c in ("STD", "K5", "K4"):
            acc[f"cand_dev_{c.lower()}"] = cand_dev(c, M)
    if "validation" in which:
        for c in ("STD", "K5", "K4"):
            acc[f"validation_{c.lower()}"] = validation(c, M)
    old = json.loads((BASE / "EXPORTS_ACCEPTANCE.json").read_text(encoding="utf-8")) if (BASE / "EXPORTS_ACCEPTANCE.json").exists() else {}
    old.update(acc); (BASE / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(old, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v.get("PASS") for k, v in old.items()}, indent=1)); return old


if __name__ == "__main__":
    import sys
    run(tuple(sys.argv[1:]) if len(sys.argv) > 1 else ("ladder", "d4", "cand_dev", "validation"))
