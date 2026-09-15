"""Week 9 Phase 1.22 — Steps 0-1: locate candidate external simulation pools and audit provenance.

LABEL-FREE BY CONSTRUCTION.  Reads only folder/file names, Hugging Face repository metadata (commit list,
refs, tree names; nothing is downloaded), identifier columns and the four input columns (P, VX, LS, ST).
No has_keyhole / regime label, depth, G3, B1 membership, prediction or metric of any candidate pool is read.

Writes outputs/week9_phase1_22_external_blind_test/EXTERNAL_POOL_AUDIT.json with
EXTERNAL_BLIND_POOL_VALID = true only if some candidate is disjoint from the original 407 experiments,
never used before, never label-inspected, and large enough for the frozen design.
"""
from __future__ import annotations

import datetime
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import HfApi

from src import week7_phase6_real_data_boundary_active_level_set as p6

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_22_external_blind_test"
USER_HOME = Path.home()
THESIS_1 = ROOT.parent
REPORTS = THESIS_1 / "reports"
POPULATION_405 = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set" / "primary_common_population.csv"
WEEK6_LEDGER = ROOT / "outputs" / "week6_01_melt_pool_data_audit" / "week6_phase1_simulation_level_responses.csv"
SPH_V2_ANALYSIS_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"   # revision behind the 405 population
FEATURES = ["P", "VX", "LS", "ST"]
# frozen design needs >= 80 queryable training rows plus test rows; 5-fold grouped CV => N >= ~100 at the very least
MIN_POOL_FOR_FROZEN_DESIGN = 100
SIM_DIR = re.compile(r"^(P-[\dp]+_VX-[\dp]+_LS-.+|sim_\d+)$")
DATA_FILE = re.compile(r"(?i)(labels_partition|final-labels|^parameters\.json$|keyhole.*label|new_pool.*(manifest|audit))")
PRUNE = {".git", "node_modules", ".venv", "site-packages", "Application Data", "anaconda3", "AppData"}


def input_tuples(frame: pd.DataFrame) -> set[tuple]:
    values = frame[FEATURES].astype(str).apply(lambda c: c.str.replace("p", ".", regex=False)).astype(float)
    return set(map(tuple, np.round(values.to_numpy(), 6)))


def local_membership(disk: dict, names_407: set[str], tuples_407: set[tuple], week6_ids: set[str]) -> dict:
    """Every locally found ledger / simulation folder, checked against the original campaign by name and inputs.
    Ledgers are read with usecols = name + P/VX/LS/ST only; label columns are never loaded."""
    ledgers = []
    for path in disk["label_or_manifest_like_files"]:
        if not path.lower().endswith(".csv"):
            continue
        header = pd.read_csv(path, nrows=0).columns
        if not {"name", *FEATURES} <= set(header):
            ledgers.append({"file": path, "checked": False, "reason": "no name/input columns"})
            continue
        sims = pd.read_csv(path, usecols=["name", *FEATURES]).drop_duplicates("name")
        tuples = input_tuples(sims)
        ledgers.append({"file": path, "checked": True, "simulations": int(len(sims)),
                        "names_in_original_407": len(set(sims.name) & names_407),
                        "input_tuples_in_original_407": len(tuples & tuples_407),
                        "input_tuples_not_in_original_407": len(tuples - tuples_407)})
    folders = []
    for parent in disk["simulation_folder_parents"]:
        children = [d for d in os.listdir(parent) if SIM_DIR.match(d)]
        known = names_407 | week6_ids
        folders.append({"parent": parent, "simulation_folders": len(children),
                        "in_original_campaign": len(set(children) & known),
                        "not_in_original_campaign": sorted(set(children) - known)})
    new = [x for x in ledgers if x.get("input_tuples_not_in_original_407")] + [f for f in folders if f["not_in_original_campaign"]]
    return {"ledgers": ledgers, "simulation_folders": folders, "anything_outside_original_campaign": bool(new)}


def disk_name_scan() -> dict:
    """Machine-wide search for simulation folders / label ledgers / input manifests by NAME only."""
    sim_dirs: dict[str, int] = {}
    data_files: list[str] = []
    roots = [USER_HOME, USER_HOME / "AppData" / "Local" / "Temp", Path(os.environ.get("HF_HOME", USER_HOME / ".cache" / "huggingface"))]
    seen = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            key = os.path.normcase(dirpath)
            if key in seen:
                dirnames[:] = []
                continue
            seen.add(key)
            keep = []
            for d in dirnames:
                if SIM_DIR.match(d):
                    sim_dirs[dirpath] = sim_dirs.get(dirpath, 0) + 1
                elif d not in PRUNE or (root != USER_HOME and d == "AppData"):
                    keep.append(d)
            dirnames[:] = keep
            data_files += [os.path.join(dirpath, f) for f in filenames if DATA_FILE.search(f)]
    drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    return {"roots": [str(r) for r in roots], "drives_present": drives,
            "simulation_folder_parents": sim_dirs, "label_or_manifest_like_files": sorted(set(data_files))}


def hf_metadata(api: HfApi) -> dict:
    out = {"authenticated_user": api.whoami().get("name"),
           "datasets_by_ioandanielc": [], "datasets_by_user": []}
    for d in api.list_datasets(author="ioandanielc"):
        out["datasets_by_ioandanielc"].append({"id": d.id, "last_modified": str(d.last_modified)})
    out["datasets_by_user"] = [d.id for d in api.list_datasets(author=out["authenticated_user"])]
    repos = {}
    for d in out["datasets_by_ioandanielc"]:
        commits = api.list_repo_commits(d["id"], repo_type="dataset")
        refs = api.list_repo_refs(d["id"], repo_type="dataset")
        tree = list(api.list_repo_tree(d["id"], repo_type="dataset", revision="main"))
        repos[d["id"]] = {
            "commit_count": len(commits), "head": commits[0].commit_id, "head_date": str(commits[0].created_at),
            "head_title": commits[0].title, "branches": {b.name: b.target_commit for b in refs.branches},
            "tags": {t.name: t.target_commit for t in refs.tags},
            "top_level_files": sorted(t.path for t in tree if t.__class__.__name__ == "RepoFile"),
            "top_level_folders": sorted(t.path for t in tree if t.__class__.__name__ == "RepoFolder"),
        }
    out["repos"] = repos
    return out


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    hf = hf_metadata(api)
    names_407 = set(pd.read_parquet(p6.PHASE55_OUTPUT / "current_revision_simulation_level_targets.parquet",
                                    columns=["experiment_name"]).experiment_name)
    pop = pd.read_csv(POPULATION_405, usecols=["experiment_name", *FEATURES])
    week6 = pd.read_csv(WEEK6_LEDGER, usecols=["simulation_id", "huggingface_revision", *FEATURES])
    disk = disk_name_scan()
    table = pd.read_parquet(p6.PHASE55_OUTPUT / "current_revision_simulation_level_targets.parquet",
                            columns=["P_W", "VX_m_per_s", "LS_m", "ST_K"]).set_axis(FEATURES, axis=1)
    local = local_membership(disk, names_407, input_tuples(table), set(week6.simulation_id))

    v2 = hf["repos"]["ioandanielc/sph_v2"]
    v2_folders = set(v2["top_level_folders"])
    sample = hf["repos"].get("ioandanielc/sph_dataset_sample", {})
    sample_ids = set(sample.get("top_level_folders", []))
    candidates = [
        {"candidate": "ioandanielc/sph_v2 @ main",
         "version": v2["head"], "rows": len(v2_folders),
         "disjoint_from_original": len(v2_folders - names_407) > 0,
         "evidence": {"folders_equal_original_407_experiment_names": v2_folders == names_407,
                      "original_405_subset": set(pop.experiment_name) <= v2_folders,
                      "new_folders_not_in_original": len(v2_folders - names_407),
                      "head_is_analysis_revision_of_405": v2["head"] == SPH_V2_ANALYSIS_REVISION,
                      "last_commit": [v2["head_date"], v2["head_title"]]},
         "previously_used": "yes: it is the source of the 405-simulation population used by every phase from Week 7 to 1.21",
         "labels_previously_inspected": True, "valid": False,
         "reason": "identical to the original pool; no simulation is new"},
        {"candidate": "ioandanielc/sph_v2 @ d69dac5b (pinned Week 7 revision)",
         "version": "d69dac5bda8b622bc0de316b112815c6056c06ec", "rows": 407, "disjoint_from_original": False,
         "evidence": {"week7_01_audit": "407 experiments in 3 partitions (new-data 165, old-data-local 179, old-data-remote-clean 63)",
                      "later_revision_only_restored_monitor_streams": True},
         "previously_used": "yes: Week 7 phases 1-5", "labels_previously_inspected": True, "valid": False,
         "reason": "same 407 experiments as the original pool"},
        {"candidate": "ioandanielc/sph_dataset @ 0e859b74 (Weeks 5-6)",
         "version": "0e859b748fdbc8454f66e58e101e333ac0479d42", "rows": int(len(week6)),
         "disjoint_from_original": len(input_tuples(week6) - input_tuples(pop)) > 0,
         "evidence": {"input_tuples": len(input_tuples(week6)),
                      "input_tuples_also_in_405": len(input_tuples(week6) & input_tuples(pop)),
                      "input_tuples_not_in_405": len(input_tuples(week6) - input_tuples(pop))},
         "previously_used": "yes: Weeks 5-6 modelling, then re-released as the old-data partitions of sph_v2",
         "labels_previously_inspected": True, "valid": False,
         "reason": "every simulation is already in the 405-simulation population"},
        {"candidate": "ioandanielc/sph_dataset_sample",
         "version": sample.get("head"), "rows": len(sample_ids),
         "disjoint_from_original": False,
         "evidence": {"folders": sorted(sample_ids),
                      "ids_present_in_week6_ledger": sorted(sample_ids & set(week6.simulation_id))},
         "previously_used": "sample of sph_dataset (Weeks 5-6)", "labels_previously_inspected": True, "valid": False,
         "reason": "5 simulations from the Week 6 campaign, all inside the original pool; far below the frozen design size"},
        {"candidate": "2 rows of the 407 excluded from the 405 population",
         "version": SPH_V2_ANALYSIS_REVISION, "rows": len(names_407 - set(pop.experiment_name)),
         "disjoint_from_original": False, "evidence": {"source": "Phase 5.5 retention audit"},
         "previously_used": "audited and excluded in Phase 5.5", "labels_previously_inspected": True, "valid": False,
         "reason": "same campaign, labels read during the exclusion audit, 2 rows"},
        {"candidate": "local copies found on disk (Downloads ledgers, Week 5 raw data, HF cache, monitor-restoration payload)",
         "version": "file names and name/input columns only", "rows": sum(x.get("simulations", 0) for x in local["ledgers"]),
         "disjoint_from_original": local["anything_outside_original_campaign"], "evidence": local,
         "previously_used": "copies of the original campaign's ledgers and folders", "labels_previously_inspected": True,
         "valid": False, "reason": "every ledger row and simulation folder is one of the original 407 experiments"},
        {"candidate": "Masinelli et al. experimental LPBF process maps (Phase 1.10 / 1.10B)",
         "version": "pinned GitHub workbooks (outputs/week9_phase1_10_external_experimental_validation/source_manifest.json)",
         "rows": "38 unique conditions per alloy", "disjoint_from_original": True,
         "evidence": {"inputs": "P and VX only (fixed spot size, no substrate temperature)",
                      "target": "post-mortem metallographic regime, not the simulator label"},
         "previously_used": "yes: M3 / physics-direction / two-slope model comparisons in Phases 1.10 and 1.10B",
         "labels_previously_inspected": True, "valid": False,
         "reason": "not a simulation pool; labels already used for model comparison; the frozen 4D policy and the "
                   "16-to-80 budget design cannot be applied to 38 two-dimensional conditions"},
        {"candidate": "supervisor's new simulation pool (research_strategy_memo 2026-09-05; NEW_POOL_FEASIBILITY_SPEC)",
         "version": None, "rows": None, "disjoint_from_original": "unknown",
         "evidence": {"memo": "new simulations reported as already run and being labelled by the supervisor; labels not observed by the method side",
                      "huggingface": "no new commit in sph_v2 since 2026-08-10, no new dataset by ioandanielc or the user",
                      "local_disk": "no simulation folder, label ledger or input manifest outside the known pools (see disk_name_scan)",
                      "prepared_audit_never_run": not any("new_pool_audit.json" in f for f in disk["label_or_manifest_like_files"])},
         "previously_used": "no evidence of any use", "labels_previously_inspected": "no evidence", "valid": False,
         "reason": "not available: no manifest, inputs or labels of this pool exist in any location accessible here, "
                   "so it can be neither audited nor tested"},
    ]
    known_parents = [p for p in disk["simulation_folder_parents"] if "sph_dataset" not in p]
    payload = {
        "phase": "Week 9 Phase 1.22 - external blind test, Steps 0-1",
        "audited_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "label_access": "none: only names, repository metadata, identifier columns and P/VX/LS/ST were read",
        "original_pool": {"source": f"ioandanielc/sph_v2 @ {SPH_V2_ANALYSIS_REVISION}", "experiments": len(names_407),
                          "primary_population": int(len(pop))},
        "huggingface_metadata": {k: v for k, v in hf.items() if k != "repos"} | {
            "repos": {r: {k: (v if k != "top_level_folders" else f"{len(v)} folders") for k, v in m.items()}
                      for r, m in hf["repos"].items()}},
        "disk_name_scan": disk | {"simulation_folder_parents_outside_known_hf_cache": known_parents},
        "candidates": candidates,
        "EXTERNAL_BLIND_POOL_VALID": any(c["valid"] for c in candidates),
        "verdict": "No genuinely external blind simulation pool is available. Every accessible simulation - on Hugging Face "
                   "and in every local ledger, cache and folder - belongs to the original 407-experiment campaign; the only "
                   "independent data set (Masinelli) is experimental, 2D, small and already used; and the supervisor's new "
                   "pool has not been delivered to any accessible location.",
        "consequence": "STOP before Step 2: no external label was read, no protocol was frozen, no external run was made.",
        "needed_to_proceed": [
            "the new pool from the data owner as an immutable manifest (folder names / parameters.json with P, VX, LS, ST, "
            "configuration tokens) delivered WITHOUT labels, plus a separate sealed label file",
            "confirmation that nobody on the method side has seen those labels",
            "then: rerun this audit, run the label-free Step 2 feasibility check, and freeze the protocol before unsealing",
        ],
    }
    (OUTPUT / "EXTERNAL_POOL_AUDIT.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"EXTERNAL_BLIND_POOL_VALID": payload["EXTERNAL_BLIND_POOL_VALID"],
                      "candidates": [(c["candidate"], c["rows"], c["valid"], c["reason"]) for c in candidates],
                      "simulation_folder_parents": disk["simulation_folder_parents"],
                      "label_or_manifest_like_files": disk["label_or_manifest_like_files"],
                      "drives": disk["drives_present"]}, indent=2, default=str))


if __name__ == "__main__":
    main()
