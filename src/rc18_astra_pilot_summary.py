"""Descriptive summary of Astra's frozen pilot astra_monitor_discovery_20261016 (run once on 2026-10-18 from a verbatim copy).

Reads pilot/CONTROLLED_RESULTS.json only; applies the manifest's own target definitions (discovery target confirmed at two
consecutive budgets, counted at the second; unreached by B24 = right-censored). No fits.
    python -m src.rc18_astra_pilot_summary
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "outputs" / "research_campaign_20261018" / "astra_pilot" / "astra_monitor_discovery_20261016"
OUT = ROOT / "outputs" / "research_campaign_20261018" / "astra_pilot" / "PILOT_SUMMARY.md"


def f(x, d=3, sign=False):
    return "n/a" if x is None else (f"{x:+.{d}f}" if sign else f"{x:.{d}f}")


def d(r, b, k, n=3):
    return "n/a" if r[k] is None or b[k] is None else f"{r[k] - b[k]:+.{n}f}"


def confirmed(recs, key):
    ok = [r["metrics"][key] for r in recs]
    for i in range(1, len(ok)):
        if ok[i - 1] and ok[i]:
            return recs[i]["budget"]
    return None


def main():
    R = json.loads((PKG / "pilot" / "CONTROLLED_RESULTS.json").read_text(encoding="utf-8"))
    M = json.loads((PKG / "FROZEN_MANIFEST.json").read_text(encoding="utf-8"))
    rows = []
    for o in R["outcomes"]:
        recs = sorted(o["records"], key=lambda r: r["budget"]); last = recs[-1]["metrics"]
        nq = [r.get("next_query") or {} for r in recs]
        reasons = defaultdict(int)
        for q in nq:
            if q:
                reasons[q.get("reason", "?")] += 1
        rows.append({"world": o["world"], "seed": o["seed"], "mode": o["mode"], "status": o["status"],
                     "BA24": last["BA"], "err24": last["error"], "RMSE24": last["RMSE"], "island_recall24": last["island_recall"],
                     "island_bnd_err24": last["island_boundary_error"], "first_disc": last["first_discovery_query"],
                     "paid_island": last["paid_island_count"], "invalid_paid": last["invalid_paid_count"],
                     "target_B": confirmed(recs, "discovery_target_met"), "triggers": sum(1 for q in nq if q.get("triggered")),
                     "reasons": dict(reasons),
                     "aux_RMSE24": last.get("aux_RMSE"), "obs_cov24": last["observation_90_coverage"]})
    L = ["# Astra's frozen pilot `astra_monitor_discovery_20261016` — run once on 2026-10-18", "",
         f"Status **{R['status']}**, code digest `{R['code_digest'][:16]}…` (= FROZEN_MANIFEST). Resources: "
         + json.dumps(json.loads((PKG / 'pilot' / 'RESOURCES.json').read_text())) + ". Independent dense references: "
         + json.loads((PKG / 'pilot' / 'NUMERICAL_REFERENCES.json').read_text())["status"] + ".", "",
         f"Scope (manifest): {M['claim_scope']}. {R['warning']}.", "",
         "Discovery target (manifest): " + M["targets"]["discovery"] + "; confirmed at two consecutive budgets (counted at the second); "
         "`—` = not reached by B24 (right-censored).", "",
         "| world | seed | arm | BA@24 | error@24 | island recall@24 | island-boundary error@24 | first discovery (query) | paid island runs | invalid paid | triggers | target reached at B | query reasons |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {m: i for i, m in enumerate(M["experiment"]["core_arms"] + M["experiment"]["aux_arms"])}
    for r in sorted(rows, key=lambda r: (r["world"], r["seed"], order.get(r["mode"], 99))):
        L.append(f"| {r['world']} | {r['seed']} | {r['mode']} | {f(r['BA24'])} | {f(r['err24'])} | {f(r['island_recall24'], 2)} | {f(r['island_bnd_err24'], 2)} | "
                 f"{r['first_disc'] if r['first_disc'] is not None else '—'} | {r['paid_island']} | {r['invalid_paid']} | {r['triggers']} | "
                 f"{r['target_B'] if r['target_B'] is not None else '—'} | {', '.join(f'{k} {v}' for k, v in sorted(r['reasons'].items()))} |")
    # decisive paired comparison: surprise vs straddle_global (same schedule), per world and seed
    L += ["", "**Decisive paired comparison (same GP, decision, startup and global schedule): surprise − straddle_global at B24**", "",
          "| world | seed | ΔBA | Δerror | Δisland recall | Δisland-boundary error |", "|---|---|---|---|---|---|"]
    idx = {(r["world"], r["seed"], r["mode"]): r for r in rows}
    for (w, s, m), r in sorted(idx.items()):
        if m != "surprise" or (w, s, "straddle_global") not in idx:
            continue
        b = idx[(w, s, "straddle_global")]
        L.append(f"| {w} | {s} | {d(r, b, 'BA24')} | {d(r, b, 'err24')} | {d(r, b, 'island_recall24', 2)} | "
                 f"{d(r, b, 'island_bnd_err24', 2)} |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); print(OUT); print("\n".join(L[-12:]))


if __name__ == "__main__":
    main()
