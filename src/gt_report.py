"""GT report tables, generated from the saved result files only (no new computation): REPORT_TABLES.md.
    python -m src.gt_report
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.gt_data as GD

OUT = GD.OUT


def f(x, d=4, sign=True):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def ci(c, d=4):
    return f"{f(c['mean'], d)} [{f(c['lcb'], d)}, {f(c['ucb'], d)}]" if c and c.get("n", 0) else "–"


def summary_table(path, systems, title):
    S = pd.read_csv(path).set_index("system"); rows = [f"**{title}**", "",
                                                       "| system | BA-AULC B8–B24 | B8–B60 | B28–B60 | BA B8 | B12 | B16 | B24 | B40 | B60 | Keyhole recall B8–B24 | conduction recall B8–B24 | log loss B8–B60 | Brier B8–B60 |",
                                                       "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in systems:
        if s not in S.index:
            continue
        r = S.loc[s]
        rows.append(f"| {s} | {r.BA_B8_B24:.4f} | {r.BA_B8_B60:.4f} | {r.BA_B28_B60:.4f} | " + " | ".join(f"{r[f'BA_b{b}']:.4f}" for b in (8, 12, 16, 24, 40, 60))
                    + f" | {r.sens_B8_B24:.4f} | {r.spec_B8_B24:.4f} | {r.ll_B8_B60:.4f} | {r.brier_B8_B60:.4f} |")
    return "\n".join(rows) + "\n"


def target_table(path, systems, title):
    S = pd.read_csv(path).set_index("system"); rows = [f"**{title}**", "",
                                                       "| system | τ | attained | rate | never reached | first b (mean, reached) | confirmed b (mean, att.) | spend mean / median (att.) | median spend (all; ∞ = not reached) | restricted mean (61-capped) | kept (B60 ≥ τ) | sustained |",
                                                       "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in systems:
        if s not in S.index:
            continue
        r = S.loc[s]
        for tau in (0.8, 0.9, 0.93, 0.95):
            g = lambda k: r.get(f"{k}_{tau}", np.nan)  # noqa: E731
            rows.append(f"| {s} | {tau:.2f} | {g('attained')} | {float(g('attain_rate')):.3f} | {int(g('never_reached'))} | {float(g('first_mean_reached')):.2f} | {float(g('confirmed_b_mean_att')):.2f} | "
                        f"{float(g('spend_mean_att')):.2f} / {float(g('spend_median_att')):.1f} | {g('spend_median_all')} | {float(g('rms61')):.2f} | {g('kept')} | {g('sustained')} |")
    return "\n".join(rows) + "\n"


def contrast_table(R, cond, keys, ref_label):
    C = R["contrasts"][cond]; rows = [f"**Paired differences against {ref_label} ({cond}; mean [one-sided 95 % LCB, UCB] over clusters)**", "",
                                      "| system | ΔBA-AULC B8–B24 | ΔBA-AULC B8–B60 | ΔBA B28–B60 | Δ Keyhole recall B8–B24 | Δ conduction recall B8–B24 | Δ log loss B8–B60 | saving 0.90 | saving 0.93 | saving 0.95 | Δ attain 0.95 | Δ kept 0.95 |",
                                      "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        if k not in C:
            continue
        c = C[k]
        rows.append(f"| {k} | {ci(c['dBA_B8_B24'])} | {ci(c['dBA_B8_B60'])} | {ci(c['dBA_B28_B60'])} | {ci(c['dsens_B8_B24'])} | {ci(c['dspec_B8_B24'])} | {ci(c['dll_B8_B60'])} | "
                    f"{ci(c['rms_saving_0.9'], 2)} | {ci(c['rms_saving_0.93'], 2)} | {ci(c['rms_saving_0.95'], 2)} | {ci(c['d_attain_0.95'], 3)} | {ci(c['d_kept_0.95'], 3)} |")
    return "\n".join(rows) + "\n"


def g2_tables():
    R = json.loads((OUT / "dev" / "G2_RESULT.json").read_text(encoding="utf-8")); out = ["## G2 (DEV, matched on the recorded C1 paths)", ""]
    systems = ["C1", "GEO_A1", "GEO_A2", "GEO_B1", "GEO_B2", "GEO_B3", "CAL_B1", "C1_G", "C1_T", "ORACLE_T"]
    out.append(f"Acceptance: {json.dumps(R['acceptance'])}\n\nSelection: {json.dumps(R['selection'], default=str)}\n")
    for cond in ("STD", "K5", "K4"):
        out.append(summary_table(OUT / "dev" / f"G2_summary_{cond}.csv", systems, f"Levels, {cond}"))
        out.append(contrast_table(R, cond, systems[1:], "C1 (recorded)"))
    out.append(target_table(OUT / "dev" / "G2_summary_STD.csv", systems, "Targets, STD (200 learners)"))
    rows = ["**Per-region block contrasts (B8–B60; mean over startups of the region-mean difference; warning if LCB < −0.02)**", "", "| system | K5 | K4 |", "|---|---|---|"]
    for s in systems[1:]:
        rows.append(f"| {s} | {ci(R['per_region']['K5'][s])}{' WARNING' if R['per_region']['K5'][s].get('warning') else ''} | {ci(R['per_region']['K4'][s])}{' WARNING' if R['per_region']['K4'][s].get('warning') else ''} |")
    out.append("\n".join(rows) + "\n")
    rows = ["**Near the boundary: q20 BA, STD (mean; Δ vs C1 [LCB, UCB])**", "", "| system | B8–B24 | Δ | B8–B60 | Δ |", "|---|---|---|---|---|"]
    for s in systems[1:]:
        q = R["q20"][s]; a, b = q.get("STD|B8_B24", {}), q.get("STD|B8_B60", {})
        rows.append(f"| {s} | {f(a.get('x_mean'), 4, False)} (C1 {f(a.get('a_mean'), 4, False)}) | {ci(a)} | {f(b.get('x_mean'), 4, False)} | {ci(b)} |")
    out.append("\n".join(rows) + "\n")
    rows = ["**Subgroups, STD (recall of the group's true class; mean over learners; Δ vs C1 [LCB, UCB])**", "", "| system | group | window | value | C1 | Δ |", "|---|---|---|---|---|---|"]
    for s in ("GEO_A1", "GEO_B1", R["selection"]["GEO_star"], "C1_G", "C1_T"):
        for g in ("shortK_pooled", "shortK_NEW", "NEW_conduction", "ceiling_keyhole", "keyhole_below_ceiling", "conduction", "corner_keyhole", "corner_conduction"):
            for w in ("B8_B24", "B24_B60"):
                c = R["subgroups"][s].get(f"STD|{g}|{w}")
                if c:
                    rows.append(f"| {s} | {g} (n/learner {c['runs_per_learner_median']:.0f}) | {w} | {c['x_mean']:.3f} | {c['a_mean']:.3f} | {ci(c, 3)} |")
    out.append("\n".join(rows) + "\n")
    out.append(f"Ceiling share association (descriptive, STD): {json.dumps(R['ceiling_share'])}\n")
    cpu = pd.read_csv(OUT / "dev" / "G2_cpu.csv"); keys = [c for c in cpu.columns if c not in ("condition", "cluster", "learner")]
    out.append("**CPU per decision state on the test rows (process s, mean; G2 matched; GEO_A excludes the shared depth fit here)**: "
               + ", ".join(f"{k} {cpu[k].mean():.3f}" for k in keys) + "\n")
    return "\n".join(out)


def tb_tables():
    p = OUT / "temporal" / "TB_DEV_RESULT.json"
    if not p.exists():
        return ""
    R = json.loads(p.read_text(encoding="utf-8")); out = ["## QT-B (DEV half, run-level)", "", f"Population: {json.dumps(R['population'])}", ""]
    rows = ["| model | " + " | ".join(f"{t} ms LL / AUC / BA" for t in sorted(R["info"], key=float)) + " |", "|---|" + "---|" * len(R["info"])]
    for m in ("S", "S+T", "S+D", "S+D+T", "C1p"):
        rows.append(f"| {m} | " + " | ".join(f"{R['info'][t][m]['ll']:.4f} / {R['info'][t][m]['auc']:.4f} / {R['info'][t][m]['BA']:.4f}" for t in sorted(R["info"], key=float)) + " |")
    out.append("\n".join(rows) + "\n")
    for t in sorted(R["info"], key=float):
        b = R["info"][t]; out.append(f"- {t} ms: Δ(S+D+T − S+D) {b['d_ll_SDT_minus_SD']}; Δ(S+T − S) {b['d_ll_ST_minus_S']}; Δ(S+D − S) {b['d_ll_SD_minus_S']}")
    for far, b in R["time"].items():
        out.append(f"\n**Alarms {far}**\n\n| model | capture | false alarm | time read (all) | time read (Keyhole) | iterations read | warning median (ms) | alarm before first K | short-K capture | NEW conduction false alarm | missed Keyhole |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for m in ("S", "S+T", "S+D", "S+D+T"):
            x = b[m]
            out.append(f"| {m} | {x['capture']:.3f} | {x['false_alarm']:.3f} | {x['time_read_all']:.3f} | {x['time_read_keyhole']:.3f} | {x['iter_read_all']:.3f} | {x['warning_ms_median']:.3f} | "
                       f"{x['alarm_before_first_K_share_of_captured']:.3f} | {x['shortK_capture']:.2f} | {x['NEW_conduction_false_alarm']:.2f} | {len(x['missed_keyhole_firstK_ms'])} |")
        out.append(f"\nΔ time read (S+D+T − S+D): {b['d_time_read_SDT_minus_SD']}; (S+T − S): {b['d_time_read_ST_minus_S']}")
    out.append(f"\nRules: info {R['info_rule']}; time {R['time_rule']}; decision: {R['decision']}\n")
    return "\n".join(out)


def g3_tables():
    p = OUT / "dev" / "G3_RESULT.json"
    if not p.exists():
        return ""
    R = json.loads(p.read_text(encoding="utf-8")); out = ["## G3 (DEV own paths)", "", f"Transition: {json.dumps(R['transition'], default=str)}", ""]
    systems = ["C1_own", "GEO_margin_own", "GEO_straddle_own", "GEO_space_own", "GEO_on_C1", "C1_on_GEO"]
    for cond in ("STD", "K5", "K4"):
        out.append(summary_table(OUT / "dev" / f"G3_summary_{cond}.csv", systems, f"Levels, {cond}"))
        out.append(contrast_table(R, cond, list(R["contrasts"][cond]), "the second system of each pair"))
    out.append(target_table(OUT / "dev" / "G3_summary_STD.csv", systems, "Targets, STD"))
    if "interaction_B8_B24" in R:
        out.append(f"Interaction (B8–B24): {json.dumps(R['interaction_B8_B24'])}\n")
    return "\n".join(out)


def g4_tables():
    p = OUT / "validation" / "G4_RESULT.json"
    if not p.exists():
        return ""
    R = json.loads(p.read_text(encoding="utf-8")); out = ["## G4 (fresh validation)", "", f"Decision: {R['decision']}", ""]
    for cond in ("STD", "K5", "K4"):
        out.append(summary_table(OUT / "validation" / f"G4_summary_{cond}.csv", ["C1_own", "GEO_own", "GEO_on_C1"], f"Levels, {cond}"))
        out.append(contrast_table(R, cond, list(R["contrasts"][cond]), "C1_own"))
    out.append(target_table(OUT / "validation" / "G4_summary_STD.csv", ["C1_own", "GEO_own", "GEO_on_C1"], "Targets, STD"))
    out.append(f"Verdicts: {json.dumps({k: v for k, v in R['verdicts'].items() if isinstance(v, str)})}\n")
    return "\n".join(out)


def main():
    txt = "# GT report tables (generated by src/gt_report.py from the saved result files)\n\n" + "\n".join(x for x in (g2_tables(), g3_tables(), g4_tables(), tb_tables()) if x)
    (OUT / "REPORT_TABLES.md").write_text(txt, encoding="utf-8"); print("written", OUT / "REPORT_TABLES.md")


if __name__ == "__main__":
    main()
