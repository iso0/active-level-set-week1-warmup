"""RC24 reports (presentation layer; every metric, verdict, status and decision comes from the frozen src/rc24_eval.py,
src/rc22_eval.py, src/rc23_eval.py and src/rc24_correction.py).
    python -m src.rc24_report stage_a
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc23_eval as E23
import src.rc24_eval as E
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"


def _summ(T, cols):
    cols = [c for c in cols if c in T]
    S = T.groupby("arm")[cols].agg(["mean", lambda x: x.std(ddof=1) / np.sqrt(len(x))]); S.columns = [f"{a}_{'se' if b == '<lambda_0>' else b}" for a, b in S.columns]
    return S.reset_index()


def stage_a():
    M = P.manifest(); d = OUT / "stage_a"; d.mkdir(parents=True, exist_ok=True)
    U = EV.load_units(OUT / "a-own"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    rows = E.own_rows(U, M, T); B, LB, A, AL = E.tables(rows, M); EP = E23.endpoints(B); EPL = E23.endpoints(LB, by=("arm", "repeat", "fold"))
    B.to_csv(d / "own_pooled_metrics.csv", index=False); LB.to_csv(d / "own_learner_metrics.csv", index=False); EP.to_csv(d / "own_endpoints_pooled.csv", index=False)
    EPL.to_csv(d / "own_endpoints_learners.csv", index=False)
    cols = ("BA", "sensitivity", "specificity", "log_loss", "brier", "AUC", "BA_hard_group", "q20_BA")
    S = {w: _summ(A[w], cols) for w in ("small", "all")}; SL = {w: _summ(AL[w], ("BA", "sensitivity", "specificity", "log_loss")) for w in ("small", "all")}
    C = []
    for a in E.COMPARATORS + ("E1S_RAW",):
        C += [{"comparator": a, **r} for r in E.contrasts(A, EP, a)]
    C = pd.DataFrame(C); C.to_csv(d / "own_contrasts_vs_HA_LEAN_MARGIN.csv", index=False)
    att = E23.attainment_table(EP); att.to_csv(d / "own_attainment_pooled.csv", index=False); attL = E23.attainment_table(EPL); attL.to_csv(d / "own_attainment_learners.csv", index=False)
    q1 = E.decide_q1(A, EP); q2 = {a: E.decide_vs_ref(A, EP, a) for a in ("M3_MARGIN", "E1S", "G3_MARGIN", "E1S_RAW")}; q3 = E.decide_vs_ref(A, EP, "HA_LEAN_STRADDLE")
    aud = E.straddle_audit([u for u in U if u["arm"] == "HA_LEAN_STRADDLE"])
    hard = B[B.budget.isin([24, 40, 60])].groupby(["arm", "budget"])[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled", "corner_cond_errors", "corner_key_errors"]].mean().reset_index()
    hard.to_csv(d / "own_hard_region.csv", index=False)
    cpu = pd.DataFrame([{"arm": u["arm"], "cpu_s_per_step": np.mean([e.get("cpu_s", np.nan) for e in u["evals"]])} for u in U]).groupby("arm").cpu_s_per_step.agg(["mean", "median"]).reset_index()
    # matched matrix
    UM = EV.load_units(OUT / "a-match"); dec, chk = {}, []
    if UM:
        rm = E.match_rows(UM, M, T); Bm = E22_pooled(rm, M); Bm.to_csv(d / "match_pooled_metrics.csv", index=False)
        for u in UM:
            for e in u["evals"]:
                chk += list(e.get("check_vs_own", {}).values())
        for a in ("HONLY_MARGIN", "M3_MARGIN", "E1S", "G3_MARGIN", "HA_LEAN_STRADDLE"):
            dec[a] = {w: E.decomposition(Bm, a, w) for w in ("small", "all")}
        AM = {w: __import__("src.rc22_eval", fromlist=["aulc"]).aulc(Bm, E.WIN_MB[w], cols=("BA", "AUC", "BA_oracle_threshold", "log_loss", "sensitivity", "specificity", "BA_hard_group")) for w in ("small", "all")}
        MM = {w: _summ(AM[w], ("BA", "AUC", "BA_oracle_threshold", "log_loss", "BA_hard_group")) for w in ("small", "all")}
        for w in ("small", "all"):
            MM[w].to_csv(d / f"match_aulc_{w}.csv", index=False)
        hardm = Bm[Bm.budget.isin([40, 60])].groupby(["arm", "budget"])[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled"]].mean().reset_index()
        hardm.to_csv(d / "match_hard_region.csv", index=False)
    res = {"utc": RC.utc(), "units_own": len(U), "units_match": len(UM), "Q1": q1, "Q2": q2, "Q3": q3, "straddle_audit": aud, "Q4": dec,
           "match_reproduction_max_abs_vs_own": float(max(chk)) if chk else None, "match_reproduction_checks": len(chk)}
    (d / "STAGE_A_DECISIONS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    L = ["# RC24 Stage A — strong comparisons (fresh DEV repeats 59–66, 40 tasks per arm)", "",
         f"Own-query units {len(U)}; matched units {len(UM)}; matched reproduction of own-path probabilities: max |Δ| = {res['match_reproduction_max_abs_vs_own']} ({len(chk)} checks).", "",
         "## Fold-pooled AULC, own query (mean and SE over 8 repeats)", "", "B8–B24:", "", md(S["small"], 4), "", "B8–B60:", "", md(S["all"], 4), "",
         "## Individual learners (AULC averaged over 40 learners)", "", "B8–B24:", "", md(SL["small"], 4), "", "B8–B60:", "", md(SL["all"], 4), "",
         "## Contrasts against HA_LEAN + margin (RC23 D1)", "", md(C, 4), "",
         "## Target attainment (fold-pooled)", "", md(att, 3), "", "## Target attainment (individual learners)", "", md(attL, 3), "",
         "## Pre-registered decisions", "", f"- **Q1 (h alone sufficient?)** {q1[0]} — {json.dumps(q1[1], default=str)}",
         *[f"- **Q2 {a}** {v[0]} — {json.dumps(v[1], default=str)}" for a, v in q2.items()], f"- **Q3 (straddle vs margin on HA_LEAN)** {q3[0]} — {json.dumps(q3[1], default=str)}",
         f"- Straddle discriminability audit: {json.dumps(aud)}", "", "## Q4 decomposition (matched matrix, BA-AULC on the step-4 grid)", ""]
    for a, v in dec.items():
        for w, r in v.items():
            L.append(f"- {a} [{w}]: total {r['total_own_query']['mean']:+.4f} = model on X path {r['order1_model_on_X_path']['mean']:+.4f} + path for HA_LEAN {r['order1_path_for_HA_LEAN']['mean']:+.4f}; "
                     f"model on HA_LEAN path {r['order2_model_on_HA_LEAN_path']['mean']:+.4f}, path for X {r['order2_path_for_X']['mean']:+.4f}, interaction {r['interaction']['mean']:+.4f}")
    L += ["", "## Hard region (own query; evaluator-only memberships)", "", md(hard, 3), "", "## Compute (CPU s per step)", "", md(cpu, 3), ""]
    (d / "STAGE_A.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:12000])


def E22_pooled(rows, M):
    import src.rc22_eval as E22
    Bm = E22.pooled_metrics(rows); X = E.extra_pooled(rows, M); return Bm.merge(X, on=["arm", "repeat", "budget"], how="left")


if __name__ == "__main__":
    RC.limit_threads(1); {"stage_a": stage_a}[sys.argv[1]]()
