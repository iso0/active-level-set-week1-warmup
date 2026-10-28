"""Read completed DEV costs and outcomes under the owned analysis allocation."""
import collections
import gzip
import json
import statistics
from coordination import ROOT, Slot
from ledger import atomic_json

with Slot():
    rows = []
    for file in sorted((ROOT / "results/DEV").glob("*.json.gz")):
        with gzip.open(file, "rt", encoding="utf-8") as f:
            r = json.load(f)
        infos = [json.loads(p.read_text()) for p in (ROOT/r["prequery_records"]).glob("*.pre.json")]
        risk_infos = [i["details"] for i in infos if i["mode"] == "risk_h2"]
        rows.append({**r["unit"], "costs": r["costs"], "counters": r["counters"],
                     "final": r["final"], "risk_h2_decisions": len(risk_infos),
                     "unresolved_integrations": sum(not i["integration_accepted"] for i in risk_infos),
                     "numerical_fallbacks": sum(i.get("numerical_ambiguity", False) for i in risk_infos),
                     "rank_changes": sum(i["rank_changed"] for i in risk_infos),
                     "ard_chosen_nonconvergence": sum(not a["chosen_success"] for a in r["optimizer_log"])})
    assert len(rows) == 24
    summary = []
    for model, selector in sorted({(r["model"], r["selector"]) for r in rows}):
        group = [r for r in rows if (r["model"], r["selector"]) == (model, selector)]
        summary.append({"model": model, "selector": selector, "paths": len(group),
             "mean_cpu": statistics.mean(r["costs"]["total_cpu"] for r in group),
             "mean_wall": statistics.mean(r["costs"]["wall"] for r in group),
             "mean_decision_cpu": statistics.mean(r["costs"]["decision_cpu"] for r in group),
             "mean_factorizations": statistics.mean(r["counters"]["factorizations"] for r in group),
             "mean_fantasy_states": statistics.mean(r["counters"]["planning_states"] for r in group),
             "h2_decisions": sum(r["risk_h2_decisions"] for r in group),
             "numerical_fallbacks": sum(r["numerical_fallbacks"] for r in group),
             "unresolved_integrations": sum(r["unresolved_integrations"] for r in group),
             "ard_chosen_nonconvergence": sum(r["ard_chosen_nonconvergence"] for r in group)})
    output = {"phase": "EXPOSED_DEVELOPMENT_NOT_TEST", "units": rows, "cost_summary": summary,
              "method_selection": "Retain the single fixed local model and the matched bounded planner. No scientific-score tuning.",
              "timing_scope": "Four DEV worlds, B8-B32, one thread per trajectory; not a guaranteed runtime forecast."}
    atomic_json(ROOT / "results/DEVELOPMENT_READOUT.json", output)
    print(json.dumps(summary, indent=2))
