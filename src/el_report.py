"""EL study report tables and exports (after the frozen decision; nothing here changes the rule or its inputs).
    python -m src.el_report final      -> final/FINAL_COMPARISON.md (+ tables already written by src.el_decide)
    python -m src.el_report exports    -> exports/<stage>_<condition>/ (all four systems' predictions, every paid simulation id of both
                                          paths) + EXPORT_ACCEPTANCE.json from the independent recomputation (src.el_export)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.el_decide as DC
import src.el_dev as DV
import src.el_eval as EV
import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

OUT = DC.OUT
NAMES = {"A": "HA_LEAN selects / HA_LEAN predicts", "B": "HA_TREND selects / HA_TREND predicts", "C": "HA_TREND selects / HA_LEAN predicts",
         "D": "HA_LEAN selects / HA_TREND predicts"}


def f(r, k=4):
    return EV.fmt(r, k)


def summary_table(S):
    L = ["| system | BA-AULC B8–B24 indiv. (pooled) | B8–B60 indiv. (pooled) | BA b8 / b12 / b16 / b24 / b40 / b60 | Keyhole recall B8–B24 | conduction recall B8–B24 | log loss B8–B60 | Brier B8–B60 |",
         "|---|---|---|---|---|---|---|---|"]
    for _, s in S.iterrows():
        L.append(f"| {s.system}: {NAMES[s.system]} | {s.BA_B8_B24:.4f} ({s.pooled_BA_B8_B24:.4f}) | {s.BA_B8_B60:.4f} ({s.pooled_BA_B8_B60:.4f}) | "
                 + " / ".join(f"{s[f'BA_b{b}']:.3f}" for b in EV.AT_B) + f" | {s.sens_B8_B24:.3f} | {s.spec_B8_B24:.3f} | {s.ll_B8_B60:.4f} | {s.brier_B8_B60:.4f} |")
    return L


def target_table(S, con):
    L = ["| system | target | attained (indiv.) | first (attainers) | spend b+4 (attainers) | restricted-mean spend | maintenance | kept | lost | median spend | pooled attained / restricted mean |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, s in S.iterrows():
        for tau in EV.TAUS:
            med = con.get(s.system, {}).get(f"median_spend_{tau}", {}).get("x") if s.system != "A" else con["D"][f"median_spend_{tau}"]["a"]
            L.append(f"| {s.system} | {tau} | {s[f'attained_{tau}']} | {s[f'first_mean_attainers_{tau}']:.2f} | {s[f'spend_mean_attainers_{tau}']:.2f} | {s[f'rms_{tau}']:.2f} | "
                     f"{s[f'maintenance_{tau}']:.3f} | {s[f'kept_{tau}']} | {int(s[f'lost_{tau}'])} | {'–' if med is None else f'{med:.0f}'} | {s[f'pooled_attained_{tau}']} / {s[f'pooled_rms_{tau}']:.2f} |")
    return L


def contrast_rows(con, ref="A"):
    L = ["| X − " + ref + " | ΔBA-AULC B8–B24 | ΔBA-AULC B8–B60 | RMS saving 0.90 | RMS saving 0.93 | RMS saving 0.95 | Δattain 0.95 | Δkept 0.95 | Δlog loss B8–B60 | ΔBrier B8–B60 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for x, c in con.items():
        L.append(f"| {x} | {f(c['dBA_B8_B24'])} | {f(c['dBA_B8_B60'])} | {f(c['rms_saving_0.9'], 2)} | {f(c['rms_saving_0.93'], 2)} | {f(c['rms_saving_0.95'], 2)} | "
                 f"{f(c['d_attain_0.95'], 3)} | {f(c['d_kept_0.95'], 3)} | {f(c['dll_B8_B60'])} | {f(c['dbrier_B8_B60'])} |")
    return L


def attain_rows(con):
    L = ["| X vs A | target | both | X only | A only | neither | both-attained mean saving (conditional) | cumulative attainment X / A at b = 16, 24, 40, 60 |", "|---|---|---|---|---|---|---|---|"]
    for x, c in con.items():
        for tau in (0.93, 0.95):
            t = c[f"attain_table_{tau}"]; cu = c[f"cum_attain_{tau}"]
            cs = ", ".join(f"{cu[k]['x']:.2f}/{cu[k]['a']:.2f}" for k in sorted(cu, key=int))
            L.append(f"| {x} | {tau} | {t['both']} | {t['x_only']} | {t['a_only']} | {t['neither']} | {t['both_attained_mean_saving']:+.2f} | {cs} |")
    return L


def decomp_rows(dec):
    L = ["| effect | ΔBA-AULC B8–B24 | ΔBA-AULC B8–B60 | RMS saving 0.93 | RMS saving 0.95 |", "|---|---|---|---|---|"]
    for nm, d in dec.items():
        L.append(f"| {nm} | {f(d['dBA_B8_B24'])} | {f(d['dBA_B8_B60'])} | {f(d['rms_saving_0.93'], 2)} | {f(d['rms_saving_0.95'], 2)} |")
    return L


def final():
    res = json.loads((OUT / "final" / "FINAL_DECISION.json").read_text(encoding="utf-8")); dec = res["decision"]; std = res["STD"]
    S = pd.DataFrame(std["summary"])
    L = ["# EL forward validation — final comparison (fresh STD repeats 83–122, K5 startups 25–32, K4 startups 9–16)", "",
         "Frozen before any run: `PROTOCOL_EL_FINAL.md`, manifest `freeze/EL_FINAL_MANIFEST.json`. DEV evidence (same 541-run pool), not independent physical validation.",
         "Individual learners are the primary unit; pooled values are shown beside. Bounds are one-sided 95 % over clusters (repeats / startups) [LCB, UCB].", "",
         f"## Decision (registered rule): **{dec['primary']['verdict']}** for D = {NAMES['D']} against A = {NAMES['A']}", ""]
    p = dec["primary"]
    L += [f"* E1 early gain shown: {p['E1_early_gain_shown']} — ΔBA-AULC B8–B24 {f(p['E1'])}",
          f"* E2 savings: 0.93 → {p['E2']['0.93']} ({f(p['E2_values']['0.93'], 2)}), 0.95 → {p['E2']['0.95']} ({f(p['E2_values']['0.95'], 2)})",
          f"* E3 reliability not worse: 0.93 {p['E3_reliability_not_worse']['0.93']}, 0.95 {p['E3_reliability_not_worse']['0.95']} — Δattain / Δkept 0.93: {f(p['E3_values']['0.93']['d_attain'], 3)} / {f(p['E3_values']['0.93']['d_kept'], 3)}; 0.95: {f(p['E3_values']['0.95']['d_attain'], 3)} / {f(p['E3_values']['0.95']['d_kept'], 3)}",
          f"* E4 guardrails ok: {p['E4']['ok']} — ΔLL {p['E4']['dLL_B8_B60']:+.4f}, ΔBrier {p['E4']['dBrier_B8_B60']:+.4f}, CPU ratio {p['E4']['cpu_ratio']:.2f}", "",
          "Secondary (same rule against A): " + "; ".join(f"{x} = {NAMES[x]} → **{v['verdict']}**" for x, v in dec["secondary"].items()), "",
          "Robustness warnings (per-region BA-AULC B8–B60 LCB < −0.02 against A; not part of the verdict): "
          + "; ".join(f"{c}: " + ", ".join(f"{x} {w['mean']:+.4f} [LCB {w['lcb']:+.4f}]{' WARNING' if w['warning'] else ''}" for x, w in d.items()) for c, d in dec["robustness_warning"].items()), "",
          f"## 1. STD — {std['learners']} individual learners in {std['clusters']} repeat clusters", ""]
    L += summary_table(S) + ["", "### Targets (confirmed at b and b + 4; spend = b + 4 including the 8 startup simulations; restricted-mean spend = horizon 60, non-attainer = 61, neither a cost nor a bound)", ""]
    L += target_table(S, std["contrasts_vs_A"]) + ["", "### Paired against A (cluster means; one-sided 95 % bounds; + = better than A; RMS + = fewer simulations)", ""]
    L += contrast_rows(std["contrasts_vs_A"]) + ["", "### Attainment tables and cumulative attainment", ""] + attain_rows(std["contrasts_vs_A"])
    L += ["", "### D against B (secondary, no verdict)", ""] + contrast_rows({"D": std["contrasts_vs_B"]["D"]}, ref="B")
    L += ["", "### BA by budget, D − A and B − A", "", "| budget | D − A | B − A |", "|---|---|---|"]
    for b in EV.AT_B:
        L.append(f"| {b} | {f(std['BA_at_budgets_vs_A']['D'][str(b)]['diff'])} | {f(std['BA_at_budgets_vs_A']['B'][str(b)]['diff'])} |")
    L += ["", "### Model effect and path effect (2×2 on identical startups)", ""] + decomp_rows(std["decomposition"])
    L += ["", f"CPU per decision step (process s): " + ", ".join(f"{k} {v:.3f}" for k, v in std["cpu_mean_per_step"].items()) + f". Code checks: {std['checks']}.", ""]
    for cond in ("K5", "K4"):
        r = res[cond]; S2 = pd.DataFrame(r["summary"])
        L += [f"## 2. Robustness — {cond} ({r['learners']} learners, {r['clusters']} startups; individual = per region, BA undefined for a one-class region)", ""]
        L += summary_table(S2) + [""] + contrast_rows(r["contrasts_vs_A"]) + [""]
        L += ["Pooled BA-AULC B8–B60 against A: " + ", ".join(f"{x} {f(r['pooled_vs_A'][x]['B8_B60'])}" for x in ("B", "C", "D")), ""]
    (OUT / "final" / "FINAL_COMPARISON.md").write_text("\n".join(L) + "\n", encoding="utf-8"); return L


def exports():
    M = P.manifest(); base = OUT / "exports"; acc = {}
    for cond in ("STD", "K5", "K4"):
        E, CPU, PATHS = DV.load(cond); rows = []
        for (c, r, f_), v in PATHS.items():
            for nm, sysn in (("L", "A,D"), ("T", "B,C")):
                hw = v[f"{nm}_how"]
                for q, s in enumerate(v[f"{nm}_path"], 1):
                    rows.append({"path": "HA_LEAN-selected" if nm == "L" else "HA_TREND-selected", "systems": sysn, "condition": c, "cluster": r, "learner": f_, "query": q, "sim_id": s,
                                 "rule": "startup" if q <= 8 else (hw[q - 9] or "margin")})
        d = base / f"dev_{cond.lower()}"; n = EX.export_set(d, {(k[0], k[1], k[2], k[3]): v for k, v in E.items()}, rows)
        D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
        acc[d.name] = {**EX.compare(d, M, Ai, Ei, cond), "keys": n}
    for cond in ("STD", "K5", "K4"):
        E, CPU, PATHS, CHK = DC.load_units(cond)
        d = base / f"final_{cond.lower()}"; n = EX.export_set(d, E, PATHS.to_dict(orient="records"))
        Ai = pd.read_csv(OUT / "final" / f"{cond.lower()}_ai.csv"); Ei = pd.read_csv(OUT / "final" / f"{cond.lower()}_ei.csv")
        acc[d.name] = {**EX.compare(d, M, Ai, Ei, cond), "keys": n}
    (base / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); print(json.dumps(acc, indent=1)); return acc


if __name__ == "__main__":
    {"final": final, "exports": exports}[sys.argv[1]]()
