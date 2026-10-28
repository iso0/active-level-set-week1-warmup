"""Descriptive presentation only; no fits, new tests, model or oracle imports."""
import csv
import hashlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from coordination import HERE, Slot, now
import ledger


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def avg(rows, key):
    values = [float(r[key]) for r in rows if r.get(key) not in ("", None)]
    return statistics.mean(values) if values else None


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        out = csv.DictWriter(handle, fields)
        out.writeheader()
        out.writerows(rows)


def fmt(value, digits=3):
    return "N/A" if value is None else f"{value:.{digits}f}"


def main():
    start = time.monotonic()
    destination = HERE / "results" / "final_readout"
    if destination.exists():
        raise RuntimeError("Final readout already exists; retain, do not repeat.")
    source = HERE / "results" / "final_tables"
    inputs = [source / name for name in (
        "all_family_metrics_and_mechanisms.csv",
        "same_target_queries_and_full_horizon_cost.csv",
        "per_world_matched_paths_and_gates.csv",
        "existing_paired_query_burden_contrasts.csv")]
    inputs += [HERE / "FINAL_PRESENTATION_PLAN.md", Path(__file__).resolve()]
    input_hashes = {str(p.relative_to(HERE)): sha(p) for p in inputs}
    with Slot() as slot:
        ledger.event(None, None, "FINAL_PRESENTATION_START",
                     {"fits": 0, "new_tests": 0, "source_hashes": input_hashes})
        rows, costs, paths = (read_csv(p) for p in inputs[:3])
        groups, cost_groups, path_groups = defaultdict(list), defaultdict(list), defaultdict(list)
        for row in rows:
            groups[(row["phase"], row["model"], row["selector"])].append(row)
        for row in costs:
            cost_groups[(row["phase"], row["model"], row["selector"])].append(row)
        for row in paths:
            path_groups[row["contrast"]].append(row)
        metrics = ("error", "boundary_error", "island_recall", "BA", "recall_positive",
                   "recall_negative", "brier", "log_loss", "RMSE",
                   "reported_channel_RMSE", "coverage90", "aux_RMSE",
                   "aux_coverage90", "positive_paid_count", "paid_island_count",
                   "mixture_effective_components", "near_ties")
        summaries = []
        for key, members in sorted(groups.items()):
            cr = cost_groups[key]
            item = dict(zip(("phase", "model", "selector"), key))
            item.update(families=len(members), worlds=sum(int(r["n"]) for r in members))
            for metric in metrics:
                item[metric] = avg(members, metric + "_mean")
                item[metric + "_defined_families"] = sum(
                    r.get(metric + "_mean") not in ("", None) for r in members)
            item.update(
                confirmed=sum(int(r["confirmed_n"]) for r in cr),
                censored=sum(int(r["censored_n"]) for r in cr),
                restricted_queries=avg(cr, "horizon_restricted_query_burden_mean"),
                full_B64_wall_seconds=avg(cr, "full_horizon_wall_seconds_mean"),
                full_B64_cpu_seconds=avg(cr, "full_horizon_cpu_seconds_mean"),
                full_B64_selection_seconds=avg(cr, "full_horizon_selection_seconds_mean"),
                worker_lifetime_peak_RSS_bytes=max(int(r["worker_lifetime_peak_RSS_max_bytes"]) for r in cr),
                active_gate_worlds=sum(int(r["gate_active_worlds"]) for r in members),
                local_queries=sum(float(r["local_queries_mean"]) * int(r["n"]) for r in members),
            )
            summaries.append(item)
        path_summary = []
        for name, members in sorted(path_groups.items()):
            path_summary.append({
                "contrast": name, "paired_worlds": len(members),
                "identical_full_paths": sum(r["identical_full_paid_path"] == "True" for r in members),
                "A_gate_active_worlds": sum(float(r["A_triggers"]) > 0 for r in members),
                "B_gate_active_worlds": sum(float(r["B_triggers"]) > 0 for r in members),
                "A_local_queries": sum(float(r["A_local_queries"]) for r in members),
                "B_local_queries": sum(float(r["B_local_queries"]) for r in members),
            })
        index = {(r["family"], r["model"], r["selector"]): r
                 for r in rows if r["phase"] == "TEST"}
        family_rows = []
        for family in sorted({r["family"] for r in rows}):
            s = index[(family, "simple", "boundary_regional")]
            a = index[(family, "structure", "boundary_regional")]
            b = index[(family, "structure", "sur_global")]
            c = next(r for r in costs if r["phase"] == "TEST" and
                     (r["family"], r["model"], r["selector"]) ==
                     (family, "structure", "boundary_regional"))
            family_rows.append({
                "family": family, "worlds": int(a["n"]),
                "simple_boundary_error_mass": float(s["error_mean"]),
                "structure_global_error_mass": float(b["error_mean"]),
                "structure_boundary_error_mass": float(a["error_mean"]),
                "structure_minus_simple_error": float(a["error_mean"]) - float(s["error_mean"]),
                **{k: a[k + "_mean"] for k in (
                    "boundary_error", "island_recall", "recall_positive", "recall_negative",
                    "BA", "brier", "log_loss", "coverage90")},
                "gate_active_worlds": int(a["gate_active_worlds"]),
                "first_hit_worlds": int(a["first_hit_worlds"]),
                "third_hit_worlds": int(a["third_hit_worlds"]),
                "no_pool_island_worlds": int(a["no_pool_island_worlds"]),
                "no_eval_island_worlds": int(a["no_eval_island_worlds"]),
                "confirmed": int(c["confirmed_n"]), "censored": int(c["censored_n"]),
                "restricted_queries": float(c["horizon_restricted_query_burden_mean"]),
            })
        slot.check()
        assert time.monotonic() - start < 600
        destination.mkdir()
        write_csv(destination / "ALL_ARMS_SUMMARY.csv", summaries)
        write_csv(destination / "ALL_FAMILY_REVIEW.csv", family_rows)
        write_csv(destination / "MATCHED_PATH_SUMMARY.csv", path_summary)
        table = [
            "# Same frozen target: queries and computation", "",
            "All 14 families remain, 24 worlds each. Each arm runs to B64. Confirmation",
            "requires the unchanged joint target at two adjacent readouts and charges",
            "the second. Nonattainment is right-censored at 64, not called a numerical",
            "failure. Restricted queries are mean min(T,64); they do not estimate",
            "uncensored mean time to success. Full B64 compute is a separate quantity.",
            "Actual compute time at T and physical simulation hours were not recorded.", "",
            "| Model / selector | Families | Confirmed / worlds | Censored | Restricted queries | B64 error | B64 wall s | B64 CPU s | Selection s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in summaries:
            table.append(f"| {r['phase']}: {r['model']} / {r['selector']} | {r['families']} | "
                         f"{r['confirmed']}/{r['worlds']} | {r['censored']} | "
                         f"{fmt(r['restricted_queries'],2)} | {fmt(r['error'],5)} | "
                         f"{fmt(r['full_B64_wall_seconds'],2)} | {fmt(r['full_B64_cpu_seconds'],2)} | "
                         f"{fmt(r['full_B64_selection_seconds'],2)} |")
        table += ["",
            "The three-family sur_primary rows concern only multi-output worlds; do not",
            "compare their aggregate with a 14-family row. Equal-share controls use the",
            "same 336 TEST worlds, not another independent test sample. Pure straddle,",
            "margin, RANDOM and literature adaptations have their declared baseline",
            "schedules; complete-system comparisons are not isolated criterion effects.",
            "",
            "No frozen paired query-savings flag passes. All four primary comparisons",
            "have joint attainment below the frozen 80% requirement. H4 improves overall",
            "error but increases restricted query burden by 2.607 [1.560,3.631]; its",
            "attainment is 148/336 versus 164/336. These are different endpoints.",
            "See ../final_tables/existing_paired_query_burden_contrasts.csv for every",
            "registered paired interval, attainment fraction and operational flag.",
            "",
            "Costs are saved trajectory accumulators, excluding setup and separate audits;",
            "selection includes posterior/reference construction. Concurrent host load and",
            "run order can affect timing. Largest recorded worker-lifetime RSS is "
            f"{max(r['worker_lifetime_peak_RSS_bytes'] for r in summaries)/1e6:.1f} MB "
            "(not isolated-path memory or a total-host peak).",
            "",
            "Intervals in the underlying analysis are pointwise, with the sign-flip",
            "exchangeability/symmetry qualification in INFERENCE_AND_COMPLETION_AUDIT.md.",
        ]
        (destination / "SAME_TARGET_QUERY_COST_TABLE.md").write_text(
            "\n".join(table) + "\n", encoding="utf-8", newline="\n")
        output_hashes = {p.name: sha(p) for p in destination.iterdir() if p.is_file()}
        completion = {
            "utc": now().isoformat(), "status": "COMPLETE", "fits": 0,
            "components": 0, "new_inferential_tests": 0,
            "input_hashes": input_hashes, "output_hashes": output_hashes,
            "elapsed_seconds": time.monotonic() - start,
            "scientific_results_already_exposed": True,
            "all_families_retained": True,
        }
        ledger.atomic_json(destination / "COMPLETE.json", completion)
        ledger.event(None, None, "FINAL_PRESENTATION_COMPLETE", completion)
        print(json.dumps({"status": "COMPLETE", "arms": len(summaries),
                          "families": len(family_rows), "fits": 0}))


if __name__ == "__main__":
    main()
