"""Tables for the three registered studies of 2026-10-17 (PHYS_AL, PHYS_DISCOVERY, TEMPORAL_STRUCT).

Formatting only: it reads the frozen result files and writes markdown tables. It fits nothing and changes no endpoint.
Steps: python -m src.jdl_studies_report
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "joint_depth_label_development"
PAL_RES = OUT / "phys_al" / "results" / "PHYS_AL_RESULTS.json"
PD_RES = OUT / "phys_discovery" / "results" / "PHYS_DISCOVERY_RESULTS.json"
TS_RES = {p: OUT / "temporal_struct" / "results" / f"TEMPORAL_STRUCT_RESULTS_{p}.json" for p in ("NEW", "OLD")}
TABLES = OUT / "STUDIES_20261017_TABLES.md"
ARMS = ("RANDOM", "MAXIMIN", "MAXVAR", "IVR", "MO_MAXVAR")


def _f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def phys_al(L):
    R = json.loads(PAL_RES.read_text(encoding="utf-8"))
    for pop, P in R.items():
        L += [f"\n### PHYS_AL — {pop} ({P['units']} units)\n",
              "| Target | R²_full (r3 / r4) | Learnable | " + " | ".join(f"{a} AULC (r3 / r4)" for a in ARMS) + " |",
              "|---|---|---|" + "---|" * len(ARMS)]
        for c, e in P["targets"].items():
            if not e.get("available", True):
                L.append(f"| {c} | unavailable | | " + " | " * len(ARMS)); continue
            rf = e["R2_full_per_repeat"]
            cells = []
            for a in ARMS:
                per = e["arms"].get(a)
                cells.append("—" if not per or any(x is None for x in per) else " / ".join(_f(x["AULC"]) for x in per))
            L.append(f"| {c} | {_f(rf['3'])} / {_f(rf['4'])} | {'yes' if e['learnable'] else 'no'} | " + " | ".join(cells) + " |")
        L += ["", "| Target | level | " + " | ".join(f"{a} B→target (r3 / r4)" for a in ARMS) + " | verdicts (MAXVAR, IVR, MO_MAXVAR) |",
              "|---|---|" + "---|" * len(ARMS) + "---|"]
        for c, e in P["targets"].items():
            if not e.get("available", True):
                continue
            cells = []
            for a in ARMS:
                per = e["arms"].get(a)
                cells.append("—" if not per or any(x is None for x in per) else " / ".join(f"{x['budget_to_target']}{'+' if x['censored'] else ''}" for x in per))
            vd = []
            for a in ("MAXVAR", "IVR", "MO_MAXVAR"):
                v = e.get(f"{a}_verdict")
                if v is None:
                    vd.append(f"{a}: —"); continue
                d = v["AULC_minus_best_nonadaptive_per_repeat"]
                tag = "SAME-BUDGET GAIN" if v["same_budget_gain"] else ("FEWER SIMS" if v["fewer_simulations"] else "no claim")
                if v["same_budget_gain"] and v["fewer_simulations"]:
                    tag = "SAME-BUDGET GAIN + FEWER SIMS"
                vd.append(f"{a}: {tag} (Δ {d[0]:+.3f} / {d[1]:+.3f})")
            L.append(f"| {c} | {_f(e['target_level'])} | " + " | ".join(cells) + " | " + "; ".join(vd) + " |")
        L.append("\n`+` = censored at 64 (level not sustained by B60). Δ = AULC minus the better of RANDOM and MAXIMIN, per repeat.")
        L += ["", "| Target | " + " | ".join(f"{a} R² at B8/16/24/40/60 (r3)" for a in ("RANDOM", "MAXVAR", "IVR", "MO_MAXVAR")) + " |", "|---|" + "---|" * 4]
        for c, e in P["targets"].items():
            if not e.get("available", True):
                continue
            cells = []
            for a in ("RANDOM", "MAXVAR", "IVR", "MO_MAXVAR"):
                per = e["arms"].get(a)
                cells.append("—" if not per or per[0] is None else " / ".join(_f(per[0]["R2_at"][str(b)], 2) for b in (8, 16, 24, 40, 60)))
            L.append(f"| {c} | " + " | ".join(cells) + " |")
        icm = P.get("icm_vs_independent")
        if icm:
            L += ["", "ICM vs independent GPs on identical paths (RMSE ratio ICM / independent, pooled over folds and both repeats).", "",
                  "| Path | Target | B8 | B16 | B24 | B40 | B60 | median over grid |", "|---|---|---|---|---|---|---|---|"]
            keys = sorted({tuple(k.split("|")[:2]) for k in icm})
            for (a, c) in keys:
                rat = {int(k.split("|")[2][1:]): v["rmse_icm"] / v["rmse_ind"] for k, v in icm.items() if k.startswith(f"{a}|{c}|") and v["rmse_ind"] > 0}
                L.append(f"| {a} | {c} | " + " | ".join(_f(rat.get(b), 2) for b in (8, 16, 24, 40, 60)) + f" | {_f(float(np.median(list(rat.values()))), 2)} |")


def phys_discovery(L):
    R = json.loads(PD_RES.read_text(encoding="utf-8"))
    for pop, P in R.items():
        L += [f"\n### PHYS_DISCOVERY — {pop} (family = top decile, threshold {P['family_hi_threshold']:.3f}, {P['n_family_hi']} members in the population)\n",
              "| Arm | family AUDC (top) | bottom-decile AUDC | top found at B60 | queries to half (cens. 64) | surprises | QC events | s / trajectory | R²-AULC (r3 / r4) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for a, m in P["arm_means"].items():
            r2 = " / ".join(_f(P["R2_AULC"].get(f"{a}|r{r}")) for r in (3, 4))
            L.append(f"| {a} | {m['family_hi_AUDC']:.3f} | {m['family_lo_AUDC']:.3f} | {m['family_hi_found_B60']:.3f} | {m['queries_to_half_hi']:.1f} | {m['surprises']:.1f} | "
                     f"{m['qc_events']:.1f} | {m['seconds']:.1f} | {r2} |")
        L += ["", "| Contrast | ΔAUDC | 95% bootstrap | pairs | ΔR²-AULC | verdict |", "|---|---|---|---|---|---|"]
        for k, v in P["contrasts"].items():
            L.append(f"| {k} | {v['family_hi_AUDC_diff']:+.4f} | [{v['lo']:+.4f}, {v['hi']:+.4f}] | {v['pairs']} | {_f(v['R2_AULC_diff'], 4)} | {v.get('verdict', '(descriptive)')} |")


def temporal(L):
    for pop, f in TS_RES.items():
        if not f.exists():
            L.append(f"\n### TEMPORAL_STRUCT — {pop}: not run\n"); continue
        R = json.loads(f.read_text(encoding="utf-8"))
        L += [f"\n### TEMPORAL_STRUCT — {pop} (wall {R['wall_seconds']:.0f} s)\n", "Curve availability: " +
              "; ".join(f"{c}: " + ", ".join(f"{k} {v}" for k, v in s.items()) for c, s in R["status"].items()), "",
              "| Channel | rep | RMSE MEAN | RMSE KRON | RMSE PCA | R²_curve KRON | R²_curve PCA | cover90 KRON | cover90 PCA | R²_sub KRON | R²_sub FULL5D | cover90 FULL5D |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c, v in R["channels"].items():
            for rep, e in v["per_repeat"].items():
                L.append(f"| {c} | {rep} | {e['MEAN']:.3f} | {e['KRON']:.3f} | {e['PCA']:.3f} | {e['R2_curve_KRON']:.3f} | {e['R2_curve_PCA']:.3f} | {e['cover90_KRON']:.2f} | "
                         f"{e['cover90_PCA']:.2f} | {_f(e.get('R2_sub_KRON'))} | {_f(e.get('R2_sub_FULL5D'))} | {_f(e.get('cover90_FULL5D'), 2)} |")
        L += ["", "| Channel | rep | T0 RMSE MEAN / KRON / PCA / SCALAR | peak RMSE MEAN / KRON / PCA / SCALAR | abs. peak-position error (bins) MEAN / KRON / PCA |", "|---|---|---|---|---|"]
        for c, v in R["channels"].items():
            for rep, e in v["per_repeat"].items():
                L.append(f"| {c} | {rep} | " + " / ".join(f"{e[f'rmse_T0_{m}']:.3f}" for m in ("MEAN", "KRON", "PCA", "SCALAR")) + " | " +
                         " / ".join(f"{e[f'rmse_peak_{m}']:.3f}" for m in ("MEAN", "KRON", "PCA", "SCALAR")) + " | " +
                         " / ".join(f"{e[f'peakpos_err_{m}']:.1f}" for m in ("MEAN", "KRON", "PCA")) + " |")
        L += ["", "| Channel | STRUCTURE HELPS (PCA ≤ 0.95 × KRON, both reps) | FULL5D beats KRON (subgrid) | TEMPORAL BEATS SCALAR: T0 | TEMPORAL BEATS SCALAR: peak |", "|---|---|---|---|---|"]
        for c, v in R["channels"].items():
            L.append(f"| {c} | {v['STRUCTURE_HELPS_PCA_over_KRON']} | {v.get('FULL5D_beats_KRON_on_subgrid', '— (not run)')} | "
                     f"{v['TEMPORAL_BEATS_SCALAR_T0']['verdict']} (best {v['TEMPORAL_BEATS_SCALAR_T0']['best_temporal']}) | "
                     f"{v['TEMPORAL_BEATS_SCALAR_peak']['verdict']} (best {v['TEMPORAL_BEATS_SCALAR_peak']['best_temporal']}) |")
        L.append("\nFit cost (s): " + "; ".join(f"{m}: median {c['median']:.2f}, total {c['sum']:.0f}" for m, c in R["cost"].items()))


def main():
    L = ["# Studies of 2026-10-17 — generated tables", "",
         "Generated by `src/jdl_studies_report.py` from the frozen result files; formatting only. DEV work on inspected simulations; NEW and OLD are never pooled.", ""]
    for name, fn, f in (("PHYS_AL", phys_al, PAL_RES), ("PHYS_DISCOVERY", phys_discovery, PD_RES)):
        L.append(f"## {name}")
        if f.exists():
            fn(L)
        else:
            L.append(f"\n{name}: result file missing.\n")
    L.append("\n## TEMPORAL_STRUCT"); temporal(L)
    TABLES.write_text("\n".join(L) + "\n", encoding="utf-8"); print(TABLES)


if __name__ == "__main__":
    main()
