"""Read-only provenance snapshot; write metadata ONLY inside this package.

Standard library only. No model imports, simulations, downloads or messages.
Run once before freeze. Retains a fixed snapshot, not a live status monitor.
"""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MAIN = Path("C:/Users/ozgur/Documents/thesis")
OPUS = MAIN/".claude/worktrees/joint-depth-label-dev"
WORKSPACE = HERE.parent.parent
BASE = "outputs/joint_depth_label_development/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_snapshot(root, names):
    rows = []
    for name in names:
        p = root/name
        rows.append({"path": str(p), "exists": p.is_file(),
                     "sha256": sha(p) if p.is_file() else None,
                     "bytes": p.stat().st_size if p.is_file() else None})
    return rows


def head(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")


def main():
    if (HERE/"SOURCE_SNAPSHOT.json").exists() or (HERE/"FROZEN_MANIFEST.json").exists():
        raise SystemExit("Snapshot already exists; preserve it. Do not refresh a frozen historical record.")
    now = datetime.now(timezone.utc).isoformat()
    main_names = ["outputs/week6_01_melt_pool_data_audit/monitor_data_dictionary.csv",
                  "outputs/week6_04_new_outputs_feature_effects/kinetic_energy_monitor_audit.csv",
                  "outputs/week6_04_new_outputs_feature_effects/results_summary.md",
                  "outputs/week7_03_new_data_physical_model_stability/phase3_results_summary.md"]
    opus_names = ["src/week19_sources.py", "src/week19_series.py", "src/jdl_physical_data.py",
                  "src/jdl_physical_pilot.py", "src/jdl_temporal_functional.py",
                  "src/jdl_phys_discovery.py", "src/jdl_phys_al.py",
                  BASE+"physical/PHYSICAL_PROTOCOL.md", BASE+"physical/physical_summaries.csv",
                  BASE+"physical/provenance/DOWNLOAD_SUMMARY.json",
                  BASE+"pool/POOL_PLAN.json", BASE+"surprise_discovery/SURPRISE_PROTOCOL.md",
                  BASE+"phys_discovery/PHYS_DISCOVERY_PROTOCOL.md", BASE+"phys_al/PHYS_AL_PROTOCOL.md",
                  BASE+"temporal_vel/TEMPORAL_VEL_PROTOCOL.md", BASE+"temporal_struct/TEMPORAL_STRUCT_PROTOCOL.md"]
    sources = read_snapshot(MAIN, main_names)+read_snapshot(OPUS, opus_names)
    sources += read_snapshot(MAIN/".venv/Lib/site-packages", [
        "sklearn/gaussian_process/_gpr.py", "sklearn/gaussian_process/kernels.py"])
    expected = {
        "joint_model_v2.py": "2cd25a8eb330b2d6b3a6e3d61c1e97b04972da92b52bbf23b1f8a07e291142a1",
        "v1_reference.py": "558b966a604cf512483d654c78e7dea0fc14084923f58174e2054126bacdbf59",
        "CONTROLLED_RESULTS.json": "59d3cea2856458ad05a2ad9dca98084b260661bd417a08b1c4a3c5e84b4cbc07"}
    preservation = []
    for name, expected_sha in expected.items():
        p = WORKSPACE/"outputs/astra_joint_model_v2"/name
        actual = sha(p)
        preservation.append({"path": str(p), "initial_sha256": expected_sha,
                             "current_sha256": actual, "identical": actual == expected_sha})
    if not all(r["identical"] for r in preservation):
        raise RuntimeError("Preservation mismatch; review, do not overwrite historical files")
    choice = json.loads((HERE/"METHOD_CHOICE_RECORD.json").read_text(encoding="utf-8-sig"))
    unchanged = {name: sha(HERE/name) == choice["code_hashes"][name]
                 for name in ("discovery.py", "synthetic.py", "monitor_support.py", "check_numerics.py")}
    if not all(unchanged.values()):
        raise RuntimeError("Chosen scientific core differs from the prior choice record")
    coord = OPUS/(BASE+"pool/POOL_PLAN.json")
    plan = json.loads(coord.read_text(encoding="utf-8-sig"))
    reservations = [r for r in (plan.get("external_reservations") or [])
                    if r.get("job") == "astra_monitor_discovery_20261016"]
    prior_copy = OPUS/"outputs/astra_monitor_discovery_20261016"
    prior_rows = read_snapshot(prior_copy, [p.name for p in prior_copy.iterdir() if p.is_file()])
    snapshot = {"recorded_utc": now, "host": socket.gethostname(), "python_executable": sys.executable,
        "python_version": sys.version, "versions_metadata_only": {n: version(n) for n in
            ("numpy", "scipy", "scikit-learn", "threadpoolctl")},
        "main_head": head(MAIN), "opus_head": head(OPUS), "sources": sources,
        "old_v2_preservation": preservation, "scientific_core_unchanged_since_choice": unchanged,
        "coordination_record": str(coord), "reservations_for_this_job": reservations,
        "older_snapshot_in_opus_checkout": prior_rows,
        "physical_source_pin": "ioandanielc/sph_v2@2e1eec9c98fd57609d2815f174586336ab59da07",
        "quality_scope": {"nonfinite_KE_by_run": {"H374c2f82c8": 364, "Hce04be44b1": 931, "H6dae2a1270": 63},
            "aligned_run_total": 1358, "early_ended_unavailable_run": "He7dbd8e5ce",
            "unavailable_run_counts": None, "warning": "931 is part of 1358; row-mismatch run counts are blank, not zero"},
        "exposure": {"method_choice_record": "METHOD_CHOICE_RECORD.json",
            "later_incidental_aggregate_results_in_commit_body": "6fe4e9d439a8bf5bacdcd42e3b28fba58786bea3",
            "method_tuned_to_these_results": False, "new_result_tables_opened_for_selection": False},
        "filesystem_incident": {"initial_action": "accidental empty directory in Opus output path; no source/result written in that operation",
            "attempted_cleanup": "automatic approval review rejected deletion: blocked by policy; not retried",
            "latest_observation": "directory now contains an earlier package snapshot; final package does not modify it",
            "snapshot_origin": "not independently established"},
        "literature_access_window_utc": ["2026-10-16", "2026-10-17"],
        "primary_sources": [
            {"date": "1990", "url": "https://doi.org/10.1080/01621459.1990.10474975"},
            {"date": "2013", "url": "https://www.ijcai.org/Proceedings/13/Papers/202.pdf"},
            {"date": "2024", "url": "https://arxiv.org/html/2401.05579v1"},
            {"date": "2025-03-27 preprint", "url": "https://arxiv.org/html/2503.21095v1"},
            {"date": "2026 indexed journal", "url": "https://www.sciencedirect.com/science/article/pii/S1568494626009117",
             "access": "publisher full text inaccessible; method comparison uses accessible 2025 preprint"},
            {"date": "2008", "url": "https://www2.stat.duke.edu/courses/Spring14/sta961.01/ref/HigdGattWillRigh2008.pdf"},
            {"date": "2016", "url": "https://doi.org/10.1016/j.actamat.2016.02.014",
             "accessible_preprint": "https://arxiv.org/abs/1512.02593"},
            {"date": "2017-06-22", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5481335/"},
            {"date": "live official documentation", "url": "https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.kernels.WhiteKernel.html"}]}
    write("SOURCE_SNAPSHOT.json", snapshot)
    checks = json.loads((HERE/"FITFREE_CHECKS.json").read_text())
    status = {"status": "PREPARED_NOT_RUN", "utc": now,
        "authoritative_package_directory": str(HERE), "fitfree_checks": checks,
        "controlled_fit_requests_started": 0, "GP_component_solves_started": 0,
        "independent_numerical_reference_fits_started": 0, "real_data_fits_started": 0,
        "scientific_results": None, "reason": "No explicit Opus reservation in the sole coordination record",
        "dry_run": "run after freeze; see FINAL_VERIFICATION.json",
        "numerical_execution_owner": "Opus", "budget_threads": 1, "budget_wall_s": 1200,
        "future_result_path": "pilot/CONTROLLED_RESULTS.json", "BA_RISK_resumed": False,
        "paid_compute": False, "outbound_messages_sent": False, "push_or_merge": False}
    write("RUN_STATUS.json", status)
    events = [{"utc": now, "kind": "CONTRACT_CHECKS", "status": checks["status"],
               "tests": checks["tests"], "actual_GP_fits": 0},
              {"utc": now, "kind": "NUMERICAL_PILOT", "status": "NOT_LAUNCHED_NO_RESERVATION",
               "actual_GP_fits": 0}]
    (HERE/"HANDOFF_LEDGER.jsonl").write_text("".join(json.dumps(e)+"\n" for e in events), encoding="utf-8")
    print(json.dumps({"snapshot_sources": len(sources), "missing": [r["path"] for r in sources if not r["exists"]],
                      "scientific_core_unchanged": all(unchanged.values()), "v2_preserved": True,
                      "reservation_count": len(reservations), "numerical_fits": 0}))


if __name__ == "__main__":
    main()
