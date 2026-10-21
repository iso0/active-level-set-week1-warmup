"""RC24 pilot evaluation (DEV, already-used repeats; exploratory - informs whether a prototype goes to a frozen confirmatory test).
    python -m src.rc24_pilot_eval p1 | p2
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc22_common as C22
import src.rc22_eval as E22
import src.rc23_eval as E23
import src.rc24_eval as E
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"


def _own_cons(u):
    return [(list(u["evals"][0]["p"].keys())[0], u.get("arm") or list(u["evals"][0]["p"].keys())[0])]


def _tables(U, M, T, cmap=_own_cons):
    rows = E22.learner_rows(U, M, T, cons_map=cmap); B = E22.pooled_metrics(rows); X = E.extra_pooled(rows, M); B = B.merge(X, on=["arm", "repeat", "budget"], how="left")
    A = {w: E22.aulc(B, w, cols=("BA", "log_loss", "sensitivity", "specificity", "AUC", "BA_hard_group")) for w in ("small", "all")}; return B, A


def _summ(T):
    return T.groupby("arm")[[c for c in ("BA", "log_loss", "sensitivity", "specificity", "BA_hard_group") if c in T]].mean().reset_index()


def _contr(A, a, refs):
    out = []
    for b in refs:
        for w in ("small", "all"):
            r = E22.contrast(A[w], a, b, "BA", 0.020, "higher"); out.append({"window": w, "contrast": r["contrast"], "mean": r["mean"], "good": r["good"], "verdict": r["verdict"]})
            r = E22.contrast(A[w], a, b, "log_loss", 0.010, "lower"); out.append({"window": w, "contrast": r["contrast"] + " [LL]", "mean": r["mean"], "good": r["good"], "verdict": r["verdict"]})
    return pd.DataFrame(out)


def p1():
    M = P.manifest(); C22.set_manifest(M); d = OUT / "pilot_p1"; d.mkdir(parents=True, exist_ok=True); Ub = EV.load_units(OUT / "b-pilot"); res = {}; L = ["# RC24 pilot P1 (DEV, used repeats; exploratory)", ""]
    for part, ref_dir, names in (("std", R23 / "h-std", "STD__"), ("block", R23 / "h-block", "s")):
        own = [u for u in Ub if u.get("arm") == "PAC_MARGIN" and ((u.get("block") is None) == (part == "std"))]
        refs = [u for u in EV.load_units(ref_dir) if u["arm"] in ("HA_LEAN", "HONLY_LR")]
        if part == "std":
            T = {(t["repeat"], t["fold"]): t for t in P.tasks(range(51, 59))}
        else:
            T = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(range(1, 9), M)}
        B, A = _tables(own + refs, M, T)
        q = pd.DataFrame([{"arm": u["arm"], "corner_share": float(E22.CORNER(M.reindex(u["paid_ids"][8:])).mean()), "cpu": np.mean([e.get("cpu_s", np.nan) for e in u["evals"]])} for u in own + refs]).groupby("arm").mean().reset_index()
        att = E23.attainment_table(E23.endpoints(B))
        C = _contr(A, "PAC_MARGIN", ("HA_LEAN", "HONLY_LR"))
        hard = B[B.budget == 60].groupby("arm")[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group"]].mean().reset_index() if part == "std" else None
        # matched: PAC family on HA_LEAN's own paths
        mt = [u for u in Ub if u.get("path_of") is not None and ((u.get("block") is None) == (part == "std"))]
        Bm, Am = _tables(mt, M, T, cmap=lambda u: [(k, f"{k}@HA_LEAN_path") for k in u["evals"][0]["p"].keys()]) if mt else (None, None)
        refm = [u for u in refs if u["arm"] == "HA_LEAN"]
        Br, Ar = _tables(refm, M, T, cmap=lambda u: [("HA_LEAN", "HA_LEAN@HA_LEAN_path")])
        if Am is not None:
            Am = {w: pd.concat([Am[w], E22.aulc(Br[Br.budget.isin(E.WIN_MB[w])], E.WIN_MB[w], cols=("BA", "log_loss", "AUC"))]) for w in ("small", "all")}
            Am = {w: E22.aulc(pd.concat([Bm, Br]), E.WIN_MB[w], cols=("BA", "log_loss", "AUC", "BA_hard_group")) for w in ("small", "all")}
        L += [f"## {part}", "", "Own query, fold-pooled AULC (B8–B24 / B8–B60):", "", md(_summ(A["small"]), 4), "", md(_summ(A["all"]), 4), "", md(C, 4), "", "Attainment:", "", md(att, 2), "",
              "Queries in the corner (post-startup share) and CPU s per step:", "", md(q, 3), ""]
        if hard is not None:
            L += ["Hard group at B60:", "", md(hard, 3), ""]
        if Am is not None:
            L += ["Matched on HA_LEAN's own paths (step-4 grid):", "", md(_summ(Am["small"]), 4), "", md(_summ(Am["all"]), 4), ""]
            for k in ("PAC", "PAC_PLUG", "PAC_FLAT", "PAC_GEN", "HA_TREND"):
                for w in ("small", "all"):
                    r = E22.contrast(Am[w], f"{k}@HA_LEAN_path", "HA_LEAN@HA_LEAN_path", "BA", 0.020, "higher"); L.append(f"- matched {k} − HA_LEAN [{w}] BA {r['mean']:+.4f} ({r['good']}) {r['verdict']}")
            L.append("")
        res[part] = {"contrasts": C.to_dict(orient="records")}
    (d / "PILOT_P1.md").write_text("\n".join(L) + "\n", encoding="utf-8"); (d / "PILOT_P1.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print("\n".join(L))


def p2():
    M = P.manifest(); C22.set_manifest(M); d = OUT / "pilot_p2"; d.mkdir(parents=True, exist_ok=True)
    U = [u for u in EV.load_units(OUT / "b-pilot2")] + [u for u in EV.load_units(OUT / "b-pilot") if u.get("arm") == "PAC_MARGIN" and u.get("block") is None]
    refs = [u for u in EV.load_units(R23 / "h-std") if u["arm"] in ("HA_LEAN", "HONLY_LR")]
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(range(51, 59))}
    B, A = _tables(U + refs, M, T)
    C = pd.concat([_contr(A, "PAC_JEER", ("PAC_MARGIN", "HA_LEAN", "HONLY_LR")), _contr(A, "PAC_JEER_LABEL", ("PAC_MARGIN",)), _contr(A, "PAC_JEER", ("PAC_JEER_LABEL",))])
    q = pd.DataFrame([{"arm": u["arm"], "corner_share": float(E22.CORNER(M.reindex(u["paid_ids"][8:])).mean()), "cpu": np.mean([e.get("cpu_s", np.nan) for e in u["evals"]])} for u in U + refs]).groupby("arm").mean().reset_index()
    aud = pd.DataFrame([{"arm": u["arm"], **e["audit"]} for u in U for e in u["evals"] if e.get("audit")]).groupby("arm").mean(numeric_only=True).reset_index()
    att = E23.attainment_table(E23.endpoints(B)); hard = B[B.budget == 60].groupby("arm")[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group"]].mean().reset_index()
    L = ["# RC24 pilot P2 (DEV, used repeats 51–58; exploratory)", "", md(_summ(A["small"]), 4), "", md(_summ(A["all"]), 4), "", md(C, 4), "", md(att, 2), "", md(q, 3), "", md(aud, 3), "", md(hard, 3)]
    (d / "PILOT_P2.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    RC.limit_threads(1); {"p1": p1, "p2": p2}[sys.argv[1]]()
