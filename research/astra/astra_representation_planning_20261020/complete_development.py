"""Close all forty development trajectories, summarizing only numerical/cost gates."""
import collections
import gzip
import json
import statistics
from coordination import ROOT, Slot, now
from ledger import atomic_json, sha256


def main():
    target = ROOT / "results/COMPLETE_DEVELOPMENT_AUDIT.json"
    if target.exists():
        print(target.read_text())
        return
    with Slot():
        groups = collections.defaultdict(list)
        for file in sorted((ROOT / "results/DEV").glob("*.json.gz")):
            r = json.loads(gzip.decompress(file.read_bytes()))
            infos = [json.loads(p.read_text()) for p in (ROOT/r["prequery_records"]).glob("*.pre.json")]
            decisions = [i for i in infos if i["mode"] in ("risk_h2", "mixture_risk_h1")]
            groups[(r["unit"]["manifest"], r["unit"]["model"], r["unit"]["selector"])].append({
                "id": r["unit"]["id"], "sha256": sha256(file), "costs": r["costs"],
                "counters": r["counters"], "decision_n": len(decisions),
                "unaccepted": sum(not i["details"]["integration_accepted"] for i in decisions),
                "fallbacks": sum(bool(i["details"].get("fallback")) for i in decisions),
                "rank_changes": sum(i["details"]["rank_changed"] for i in decisions),
                "absolute_converged": sum(i["details"].get("absolute_score_converged", False) for i in decisions),
                "orders": [i["details"]["order"] for i in decisions],
                "peak_memory_bytes": r["peak_process_working_set_bytes"],
                "paid": len(r["paid_ids"]),
                "ard_chosen_nonconvergence": sum(not a["chosen_success"] for a in r["optimizer_log"]),
            })
        assert sum(map(len, groups.values())) == 40
        summary = []
        for (manifest, model, selector), rows in sorted(groups.items()):
            summary.append({
                "manifest": manifest, "model": model, "selector": selector, "n": len(rows),
                "mean_cpu": statistics.mean(r["costs"]["total_cpu"] for r in rows),
                "max_cpu": max(r["costs"]["total_cpu"] for r in rows),
                "mean_wall": statistics.mean(r["costs"]["wall"] for r in rows),
                "mean_decision_cpu": statistics.mean(r["costs"]["decision_cpu"] for r in rows),
                "mean_factorizations": statistics.mean(r["counters"]["factorizations"] for r in rows),
                "mean_fantasy_states": statistics.mean(r["counters"]["planning_states"] for r in rows),
                "decision_n": sum(r["decision_n"] for r in rows),
                "unaccepted": sum(r["unaccepted"] for r in rows),
                "fallbacks": sum(r["fallbacks"] for r in rows),
                "rank_changes": sum(r["rank_changes"] for r in rows),
                "max_memory_bytes": max(r["peak_memory_bytes"] for r in rows),
                "orders": dict(collections.Counter(o for r in rows for o in r["orders"])),
                "ard_chosen_nonconvergence": sum(r["ard_chosen_nonconvergence"] for r in rows),
            })
        output = {"status": "FORTY_DEV_COMPLETE_NO_NEW_TEST_GENERATED",
                  "utc": now().isoformat(), "summary": summary,
                  "units": [r for rows in groups.values() for r in rows],
                  "scope": "Numerical acceptance and timing only. No efficacy criterion or scientific-score tuning."}
        atomic_json(target, output)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
