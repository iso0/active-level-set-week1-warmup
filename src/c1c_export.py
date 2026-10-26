"""C1C exports and independent recomputation (after the decisions; nothing here changes any rule or input).
  exports/main_s1, exports/main_s2        C1_own, A_own, C1_on_A, D_on_A, E_on_A, A_on_C1 at every budget + both paths' paid ids
                                          (main validation split into its pre-defined subgroups 203-242 / 243-282 to keep files small)
  exports/start_rand8, exports/start_local8   the same for the startup conditions
  exports/prior_dev                       C1_S05, C1_S2 on the recorded DEV paths (the recorded C1, A, D of these paths are exported in
                                          EA exports/cand_dev_std)
Each set is checked with src.el_export.compare (per-learner BA, BA-AULC and spend recomputed from the export files only). headline():
the cluster-level headline estimates of the decision recomputed from those recomputed learner tables with its own t bounds.
    python -m src.c1c_export
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.c1c_eval as CV
import src.c1c_fwd as FW
import src.ea_cand as CA
import src.ea_export as EAX
import src.el_eval as EV
import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

BASE = FW.OUT / "exports"


def _paths(units_dir, cond, clusters):
    rows = []; cs = set(clusters)
    for fL in sorted(units_dir.glob(f"{cond}__*__L.json.gz")):
        uL = RC.read_json_gz(fL)
        if int(uL["repeat"]) not in cs:
            continue
        uX = RC.read_json_gz(fL.with_name(fL.name.replace("__L.json.gz", "__X.json.gz")))
        rows += EAX._rows_paths(uL, "HA_LEAN-selected", cond, "A_own,C1_on_A,D_on_A,E_on_A", [e.get("how") for e in uL["evals"]])
        rows += EAX._rows_paths(uX, "C1-selected", cond, "C1_own,A_on_C1", [e.get("how") for e in uX["evals"]])
    return rows


def fwd_set(name, units_dir, cond, clusters, M):
    E, CPU, CHK = CV.load(units_dir, cond, clusters); d = BASE / name; n = EX.export_set(d, E, _paths(units_dir, cond, clusters))
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, cond), "keys": n}


def prior_set(M):
    E, C = CV.prior_load(M); E = {k: v for k, v in E.items() if k[0] in ("C1_S05", "C1_S2")}; rows = []
    for r in range(123, 163):
        for f in range(1, 6):
            src = CA.dev_path_unit("STD", r, f)
            rows += EAX._rows_paths(src, "HA_LEAN-selected (recorded, EL-2 confirmation)", "STD", "C1_S05,C1_S2 (+ C1, A, D in EA cand_dev_std)", [e.get("how") for e in src["own_evals"]])
    d = BASE / "prior_dev"; n = EX.export_set(d, E, rows)
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, "STD"), "keys": n}


def _t(d):
    d = np.asarray(d, float); n = len(d); m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"mean": m, "lcb": m - q * se, "ucb": m + q * se, "n": n}


def headline(M, dec):
    """Early BA-AULC and the 0.90 / 0.93 / 0.95 restricted-mean savings of C1_own vs A_own, recomputed from the export files only."""
    out = {}
    for label, sets, key in (("main", ("main_s1", "main_s2"), ("main",)), ("RAND8", ("start_rand8",), ("start", "RAND8")), ("LOCAL8", ("start_local8",), ("start", "LOCAL8"))):
        R1 = pd.concat([EX.recompute(BASE / s, M)[0] for s in sets]); R2 = pd.concat([EX.recompute(BASE / s, M)[1] for s in sets])
        a = R1.pivot_table(index=["cluster", "learner"], columns="system", values="BA_B8_B24")
        e = (a["C1_own"] - a["A_own"]).dropna().groupby(level=0).mean(); r = {"early": _t(e.values)}
        for tau in (0.90, 0.93, 0.95):
            T = R2[R2.target == tau].pivot_table(index=["cluster", "learner"], columns="system", values="rms")
            s = (T["A_own"] - T["C1_own"]).dropna().groupby(level=0).mean(); r[f"rms_saving_{tau}"] = _t(s.values)
        node = dec
        for k in key:
            node = node[k]
        c = node["contrasts"]["C1_own-A_own"]; diffs = [abs(r["early"][q] - c["dBA_B8_B24"][q]) for q in ("mean", "lcb", "ucb")]
        for tau in (0.90, 0.93, 0.95):
            diffs += [abs(r[f"rms_saving_{tau}"][q] - c[f"rms_saving_{tau}"][q]) for q in ("mean", "lcb", "ucb")]
        r["max_abs_diff_vs_decision"] = float(max(diffs)); r["PASS"] = bool(r["max_abs_diff_vs_decision"] <= 1e-9); out[label] = r
    return out


def run():
    M = P.manifest(); acc = {}
    for g, reps in FW.SUB.items():
        acc[f"main_{g.lower()}"] = fwd_set(f"main_{g.lower()}", FW.OUT / "c1c-main" / "units", "STD", reps, M)
    for cond, reps in FW.START.items():
        acc[f"start_{cond.lower()}"] = fwd_set(f"start_{cond.lower()}", FW.OUT / "c1c-start" / "units", cond, reps, M)
    acc["prior_dev"] = prior_set(M)
    dec = json.loads((CV.OUT / "C1C_DECISION.json").read_text(encoding="utf-8")); acc["headline_recomputation"] = headline(M, dec)
    BASE.mkdir(parents=True, exist_ok=True); (BASE / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v.get("PASS") if "PASS" in v else {kk: vv["PASS"] for kk, vv in v.items()} for k, v in acc.items()}, indent=1)); return acc


if __name__ == "__main__":
    run()
