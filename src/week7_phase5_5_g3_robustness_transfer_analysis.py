"""Week 7 Phase 5.5: G3 robustness, partition transfer, and stress tests.

This module is deliberately limited to scalar physical-proxy diagnostics.  It
does not fit a predictive model, alter a label, estimate a level set, or choose
an acquisition.  The corrected Phase 2 target table is refreshed at the exact
merged ``sph_v2`` revision by re-extracting only the 55 experiments whose raw
monitor inputs changed; all other rows are retained only after a Git-tree audit
proves their inputs are byte-identical between the pinned and merged revisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
)

from src.week7_phase2_sph_v2_physical_target_extraction import (
    REQUIRED_MONITORS,
    extract_one,
)
from src.week7_phase5_keyhole_physical_proxy_analysis import (
    CANDIDATES,
    MAIN_CANDIDATES,
    choose_threshold,
    deterministic_seed,
    threshold_cv_analysis,
)
from src.week7_sph_v2_common import (
    WEEK6_RAW_ROOT,
    git_blob_sha1,
    load_partition_labels,
    output_manifest,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
SMOKE_DIR = OUTPUT_DIR / "smoke"
FIGURE_DIRNAME = "figures"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "05_5_g3_robustness_transfer_analysis.ipynb"

PHASE5_COMMIT_SHA = "3367f4c9b5af2def802f72a65258f5cc01896bac"
PHASE5_BRANCH = "codex/week7-phase5-keyhole-physical-proxy-analysis"
PHASE55_BRANCH = "codex/week7-phase5-5-g3-robustness-transfer"
DATASET_REPO_ID = "ioandanielc/sph_v2"
DATASET_GIT_URL = f"https://huggingface.co/datasets/{DATASET_REPO_ID}.git"
PINNED_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"
CURRENT_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
HF_AUDIT_REPO = ROOT / "data" / "cache" / "week7_phase55_hf_git_audit"
TARGET_REFRESH_CACHE = ROOT / "data" / "cache" / "week7_phase55_current_target_refresh"

PHASE1_DIR = ROOT / "outputs" / "week7_01_sph_v2_audit"
PHASE2_DIR = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
PHASE4_DIR = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"
PHASE5_DIR = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
ORIGINAL_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis")

FULL_BOOTSTRAP_RESAMPLES = 5_000
SMOKE_BOOTSTRAP_RESAMPLES = 300
BASE_POPULATIONS = ["new-data", "old-data-local", "old-data-remote-clean"]
ANALYSIS_POPULATIONS = [*BASE_POPULATIONS, "all-old", "all-combined"]
TRANSFER_ROUTES = [
    ("new-data", "old-data-local", "new_to_old_local"),
    ("new-data", "old-data-remote-clean", "new_to_old_remote"),
    ("new-data", "all-old", "new_to_all_old"),
    ("all-old", "new-data", "all_old_to_new"),
    ("old-data-local", "new-data", "old_local_to_new"),
    ("old-data-remote-clean", "new-data", "old_remote_to_new"),
    ("all-combined", "all-combined", "pooled_descriptive"),
]
PRIMARY_CANDIDATES = ["G3", "R3", "max_depth", "T0_depth"]
SECONDARY_CANDIDATES = ["R0", "T0_kinetic_energy", "T0_total_height", "T0_width"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.astype("string").fillna("false").str.strip().str.lower().isin({"true", "1", "yes"})


def run_git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True,
        text=True, encoding="utf-8",
    ).stdout.strip()


def git_preflight() -> dict[str, Any]:
    branch = run_git("branch", "--show-current")
    head = run_git("rev-parse", "HEAD")
    require(branch == PHASE55_BRANCH, f"Unexpected Phase 5.5 branch: {branch}")
    require(head == PHASE5_COMMIT_SHA, f"Phase 5.5 parent changed: {head}")
    phase5_remote = run_git("ls-remote", "--heads", "origin", f"refs/heads/{PHASE5_BRANCH}")
    require(phase5_remote.split("\t")[0] == PHASE5_COMMIT_SHA, "Remote Phase 5 SHA differs")
    original_status = run_git("status", "--porcelain=v1", cwd=ORIGINAL_WORKTREE).splitlines()
    protected_baseline_path = ROOT / "outputs" / "week6_01_melt_pool_data_audit" / "original_worktree_baseline.json"
    protected = []
    if protected_baseline_path.is_file():
        payload = json.loads(protected_baseline_path.read_text(encoding="utf-8"))
        records = payload.get("protected_dirty_files") or payload.get("dirty_files") or []
        for record in records:
            rel = record["path"]
            live = ORIGINAL_WORKTREE / rel
            expected = str(record.get("sha256", record.get("expected_sha256", ""))).lower()
            actual = sha256_file(live).lower() if live.is_file() else ""
            protected.append({"path": rel, "expected_sha256": expected, "actual_sha256": actual, "matches": actual == expected})
    return {
        "captured_at_utc": utc_now(),
        "phase55_branch": branch,
        "phase55_parent": head,
        "phase5_remote_sha": phase5_remote.split("\t")[0],
        "phase5_remote_verified": True,
        "original_worktree": {
            "path": str(ORIGINAL_WORKTREE),
            "branch": run_git("branch", "--show-current", cwd=ORIGINAL_WORKTREE),
            "head": run_git("rev-parse", "HEAD", cwd=ORIGINAL_WORKTREE),
            "git_status_short": original_status,
            "protected_dirty_files": protected,
            "protected_hashes_match": bool(protected) and all(item["matches"] for item in protected),
        },
        "scope": {
            "predictive_models_fitted": False,
            "classifiers_fitted": False,
            "active_learning_run": False,
            "level_set_estimated": False,
            "labels_modified": False,
            "simulations_removed": False,
            "phase55_commit_or_push_authorized": False,
        },
    }


def ensure_hf_audit_repo() -> None:
    HF_AUDIT_REPO.parent.mkdir(parents=True, exist_ok=True)
    if not (HF_AUDIT_REPO / ".git").is_dir():
        subprocess.run(
            ["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", DATASET_GIT_URL, str(HF_AUDIT_REPO)],
            check=True,
        )
    else:
        subprocess.run(["git", "fetch", "--quiet", "origin", "main"], cwd=HF_AUDIT_REPO, check=True)


def parse_tree_entry(revision: str, relative_path: str) -> dict[str, Any]:
    text = run_git("ls-tree", "-l", revision, "--", relative_path, cwd=HF_AUDIT_REPO)
    if not text:
        return {"exists": False, "blob_id": "", "size_bytes": math.nan}
    metadata, path = text.split("\t", 1)
    mode, kind, blob_id, size = metadata.split()
    require(kind == "blob" and path == relative_path, f"Unexpected Git-tree entry for {relative_path}")
    return {"exists": True, "blob_id": blob_id, "size_bytes": int(size), "mode": mode}


def audit_hf_changes(registry: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    ensure_hf_audit_repo()
    live = run_git("ls-remote", DATASET_GIT_URL, "refs/heads/main").split("\t")[0]
    require(live == CURRENT_REVISION, f"HF main moved: expected {CURRENT_REVISION}, found {live}")
    diff = run_git("diff", "--name-status", PINNED_REVISION, CURRENT_REVISION, cwd=HF_AUDIT_REPO)
    rows: list[dict[str, Any]] = []
    partition_map = registry.set_index("experiment_name")["partition"].to_dict()
    for line in diff.splitlines():
        status, relative_path = line.split("\t", 1)
        parts = relative_path.split("/")
        experiment_name = parts[0]
        filename = parts[-1]
        entry = parse_tree_entry(CURRENT_REVISION, relative_path)
        rows.append({
            "status": status,
            "relative_path": relative_path,
            "experiment_name": experiment_name,
            "partition": partition_map.get(experiment_name, "unmapped"),
            "filename": filename,
            "current_git_blob_id": entry["blob_id"],
            "current_size_bytes": entry["size_bytes"],
        })
    frame = pd.DataFrame(rows).sort_values(["experiment_name", "filename"]).reset_index(drop=True)
    expected_path = frame["relative_path"].str.match(r"^[^/]+/monitor/(time|kinetic-energy_melt)\.dat$")
    audit = {
        "repository": DATASET_REPO_ID,
        "pinned_revision": PINNED_REVISION,
        "current_revision": CURRENT_REVISION,
        "live_main_revision": live,
        "live_main_matches_current": live == CURRENT_REVISION,
        "change_record_count": int(len(frame)),
        "status_counts": frame["status"].value_counts().to_dict(),
        "changed_experiment_count": int(frame["experiment_name"].nunique()),
        "filename_counts": frame["filename"].value_counts().to_dict(),
        "partition_experiment_counts": frame.groupby("partition")["experiment_name"].nunique().to_dict(),
        "only_expected_monitor_additions": bool(
            len(frame) == 110
            and frame["status"].eq("A").all()
            and expected_path.all()
            and frame["experiment_name"].nunique() == 55
            and frame["filename"].value_counts().to_dict() == {"kinetic-energy_melt.dat": 55, "time.dat": 55}
            and set(frame["partition"]) == {"old-data-local"}
        ),
        "new_data_paths_changed": bool(frame["partition"].eq("new-data").any()),
        "label_paths_changed": bool(frame["relative_path"].str.contains("label", case=False).any()),
        "geometry_paths_changed": bool(frame["filename"].eq("position-bounds_melt.dat").any()),
        "iteration_paths_changed": bool(frame["filename"].eq("iter.dat").any()),
        "modified_or_deleted_paths": int((~frame["status"].eq("A")).sum()),
        "audit_method": "Git tree name-status diff plus current blob IDs and byte sizes",
    }
    require(audit["only_expected_monitor_additions"], "HF revision diff exceeds the authorized restoration")
    return audit, frame


def load_inputs() -> dict[str, pd.DataFrame]:
    paths = {
        "registry": PHASE1_DIR / "experiment_registry.csv",
        "sequences": PHASE1_DIR / "experiment_label_sequences.csv",
        "targets": PHASE2_DIR / "sph_v2_simulation_level_targets.parquet",
        "name_map": PHASE2_DIR / "week6_exact_identifier_map.csv",
        "phase4_hard_cases": PHASE4_DIR / "depth_consensus_hard_cases.csv",
        "phase5_discordant": PHASE5_DIR / "physical_proxy_discordant_cases.csv",
        "phase5_folds": PHASE5_DIR / "physical_proxy_threshold_fold_predictions.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    require(not missing, f"Missing Phase 5.5 inputs: {missing}")
    result: dict[str, pd.DataFrame] = {}
    for key, path in paths.items():
        result[key] = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    return result


def build_current_plan(
    changed_experiments: Iterable[str],
    registry: pd.DataFrame,
    name_map: pd.DataFrame,
) -> pd.DataFrame:
    old_lookup = name_map.set_index("experiment_name")["week6_simulation_id"].to_dict()
    partition_lookup = registry.set_index("experiment_name")["partition"].to_dict()
    rows: list[dict[str, Any]] = []
    for experiment_name in sorted(changed_experiments):
        old_sim = str(old_lookup.get(experiment_name, ""))
        require(old_sim, f"Restored experiment lacks an exact Week 6 mapping: {experiment_name}")
        for filename in REQUIRED_MONITORS:
            relative = f"{experiment_name}/monitor/{filename}"
            entry = parse_tree_entry(CURRENT_REVISION, relative)
            local_path = WEEK6_RAW_ROOT / old_sim / "monitor" / filename
            local_blob = git_blob_sha1(local_path) if local_path.is_file() else ""
            verified = bool(entry["exists"] and local_path.is_file() and local_blob == entry["blob_id"] and local_path.stat().st_size == entry["size_bytes"])
            require(verified, f"Current monitor bytes do not match the exact Week 6 cache: {relative}")
            rows.append({
                "experiment_name": experiment_name,
                "partition": partition_lookup[experiment_name],
                "week6_simulation_id": old_sim,
                "monitor_file": filename,
                "sph_v2_relative_path": relative,
                "remote_exists": True,
                "remote_size_bytes": entry["size_bytes"],
                "remote_git_blob_id": entry["blob_id"],
                "local_path": str(local_path),
                "source_mode": "week6_cache_verified_against_current_sph_v2_git_blob",
                "local_git_blob_id": local_blob,
                "local_blob_matches_pinned_sph_v2": True,
                "exact_revision": CURRENT_REVISION,
            })
    return pd.DataFrame(rows).sort_values(["experiment_name", "monitor_file"]).reset_index(drop=True)


def refresh_targets(
    inputs: dict[str, pd.DataFrame],
    changed_paths: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline = inputs["targets"].copy()
    changed = sorted(changed_paths["experiment_name"].unique())
    failed_local = baseline[
        baseline["partition"].eq("old-data-local")
        & ~bool_series(baseline["physical_target_extraction_success"])
    ]
    require(len(failed_local) == 56, f"Expected 56 pinned old-data-local failures, found {len(failed_local)}")
    require(set(changed).issubset(set(failed_local["experiment_name"])), "A restored experiment was not a pinned target failure")
    plan = build_current_plan(changed, inputs["registry"], inputs["name_map"])
    cache_signature_payload = {
        "current_revision": CURRENT_REVISION,
        "pinned_target_sha256": sha256_file(PHASE2_DIR / "sph_v2_simulation_level_targets.parquet"),
        "label_sequence_sha256": sha256_file(PHASE1_DIR / "experiment_label_sequences.csv"),
        "monitor_bundle": plan[["sph_v2_relative_path", "remote_git_blob_id", "local_git_blob_id"]].to_dict(orient="records"),
    }
    cache_signature = hashlib.sha256(
        json.dumps(cache_signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    cache_targets = TARGET_REFRESH_CACHE / "targets.parquet"
    cache_metadata = TARGET_REFRESH_CACHE / "metadata.json"
    if cache_targets.is_file() and cache_metadata.is_file():
        metadata = json.loads(cache_metadata.read_text(encoding="utf-8"))
        if metadata.get("cache_signature") == cache_signature:
            refreshed = pd.read_parquet(cache_targets)
            require(
                len(refreshed) == 407
                and int(bool_series(refreshed["physical_target_extraction_success"]).sum()) == 405,
                "Cached current-revision targets failed integrity checks",
            )
            audit_rows = baseline[["experiment_name", "partition", "physical_target_extraction_success", "extraction_failure_reasons"]].copy()
            audit_rows = audit_rows.rename(columns={
                "physical_target_extraction_success": "pinned_success",
                "extraction_failure_reasons": "pinned_failure_reasons",
            }).merge(
                refreshed[["experiment_name", "physical_target_extraction_success", "extraction_failure_reasons", "phase55_refresh_action", "phase55_changed_monitor_count"]].rename(columns={
                    "physical_target_extraction_success": "current_success",
                    "extraction_failure_reasons": "current_failure_reasons",
                }), on="experiment_name", how="left", validate="one_to_one",
            )
            audit_rows["status_changed"] = bool_series(audit_rows["pinned_success"]) != bool_series(audit_rows["current_success"])
            print("Current-revision target refresh: verified cache hit", flush=True)
            return refreshed.sort_values(["partition", "experiment_name"]).reset_index(drop=True), plan, audit_rows
    lookup = {(row.experiment_name, row.monitor_file): row._asdict() for row in plan.itertuples(index=False)}
    registry_lookup = inputs["registry"].set_index("experiment_name", drop=False)
    sequence_lookup = inputs["sequences"].set_index("experiment_name", drop=False)
    all_labels = load_partition_labels(workers=1)
    reextracted: list[dict[str, Any]] = []
    compatibility: list[dict[str, Any]] = []
    for position, experiment_name in enumerate(changed, start=1):
        item = registry_lookup.loc[experiment_name]
        seq = sequence_lookup.loc[experiment_name]
        label_rows = all_labels[all_labels["experiment_name"].eq(experiment_name)]
        old_sim = str(inputs["name_map"].set_index("experiment_name").loc[experiment_name, "week6_simulation_id"])
        target, monitor_rows, _ = extract_one(item, seq, label_rows, lookup, old_sim)
        require(bool(target["physical_target_extraction_success"]), f"Restored target still failed: {experiment_name}: {target['extraction_failure_reasons']}")
        reextracted.append(target)
        compatibility.extend(monitor_rows)
        if position % 10 == 0 or position == len(changed):
            print(f"Current-revision target refresh: {position}/{len(changed)}", flush=True)
    refreshed_rows = pd.DataFrame(reextracted)
    refreshed = baseline.set_index("experiment_name", drop=False)
    for row in refreshed_rows.to_dict(orient="records"):
        name = row["experiment_name"]
        for column, value in row.items():
            if column not in refreshed.columns:
                refreshed[column] = np.nan
            refreshed.at[name, column] = value
    refreshed = refreshed.reset_index(drop=True)
    refreshed["phase2_pinned_revision"] = PINNED_REVISION
    refreshed["exact_sph_v2_revision"] = CURRENT_REVISION
    refreshed["phase55_refresh_action"] = np.where(
        refreshed["experiment_name"].isin(changed),
        "reextracted_from_current_verified_monitor_bundle",
        "reused_after_git_diff_proved_all_inputs_unchanged",
    )
    refreshed["phase55_changed_monitor_count"] = refreshed["experiment_name"].map(
        changed_paths.groupby("experiment_name").size()
    ).fillna(0).astype(int)
    require(len(refreshed) == 407 and refreshed["experiment_name"].is_unique, "Refreshed population lost or duplicated rows")
    require(int(bool_series(refreshed["physical_target_extraction_success"]).sum()) == 405, "Unexpected current-revision target-ready count")
    audit_rows = baseline[["experiment_name", "partition", "physical_target_extraction_success", "extraction_failure_reasons"]].copy()
    audit_rows = audit_rows.rename(columns={
        "physical_target_extraction_success": "pinned_success",
        "extraction_failure_reasons": "pinned_failure_reasons",
    }).merge(
        refreshed[["experiment_name", "physical_target_extraction_success", "extraction_failure_reasons", "phase55_refresh_action", "phase55_changed_monitor_count"]].rename(columns={
            "physical_target_extraction_success": "current_success",
            "extraction_failure_reasons": "current_failure_reasons",
        }), on="experiment_name", how="left", validate="one_to_one",
    )
    audit_rows["status_changed"] = bool_series(audit_rows["pinned_success"]) != bool_series(audit_rows["current_success"])
    TARGET_REFRESH_CACHE.mkdir(parents=True, exist_ok=True)
    refreshed.to_parquet(cache_targets, index=False, compression="zstd")
    write_json(cache_metadata, {
        "cache_signature": cache_signature,
        "cache_signature_payload": cache_signature_payload,
        "created_at_utc": utc_now(),
        "row_count": len(refreshed),
        "physical_target_ready_count": int(bool_series(refreshed["physical_target_extraction_success"]).sum()),
        "reextracted_experiment_count": len(changed),
    })
    return refreshed.sort_values(["partition", "experiment_name"]).reset_index(drop=True), plan, audit_rows


def build_population(targets: pd.DataFrame, sequences: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    label_columns = [
        "experiment_name", "partition", "collapsed_physical_sequence", "has_conduction", "has_keyhole",
        "keyhole_frame_count", "keyhole_segment_count", "maximum_keyhole_segment_frames",
        "keyhole_transient_by_sequence", "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes", "first_keyhole_timestep", "last_keyhole_timestep",
        "label_sequence_sha256",
    ]
    labels = sequences[label_columns].rename(columns={
        "has_keyhole": "has_keyhole_phase1",
        "has_conduction": "has_conduction_phase1",
        "keyhole_frame_count": "keyhole_frame_count_phase1",
        "keyhole_segment_count": "keyhole_segment_count_phase1",
    })
    registry_columns = ["experiment_name", "P", "VX", "LS", "ST", "parameters_sha256", "frames_csv_sha256"]
    population = targets.merge(labels.drop(columns="partition"), on="experiment_name", how="left", validate="one_to_one")
    population = population.merge(registry[registry_columns], on="experiment_name", how="left", validate="one_to_one", suffixes=("", "_registry"))
    require(len(population) == 407, "Population merge changed row count")
    for column in [
        "has_keyhole", "has_keyhole_phase1", "has_conduction", "has_conduction_phase1",
        "physical_target_extraction_success", "geometry_target_ready", "kinetic_energy_target_ready",
        "source_label_modified", "simulation_silently_removed", "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame", "repeated_keyhole_episodes",
    ]:
        population[column] = bool_series(population[column])
    require(population["has_keyhole"].equals(population["has_keyhole_phase1"]), "Phase 1/2 Keyhole semantics disagree")
    require(population["has_conduction"].equals(population["has_conduction_phase1"]), "Phase 1/2 Conduction semantics disagree")
    require(not population["source_label_modified"].any(), "A source label was modified")
    require(not population["simulation_silently_removed"].any(), "A simulation was silently removed")
    population["R0_T0_depth_over_width"] = np.where(
        pd.to_numeric(population["T0_width_um"], errors="coerce") > 0,
        pd.to_numeric(population["T0_depth_um"], errors="coerce") / pd.to_numeric(population["T0_width_um"], errors="coerce"),
        np.nan,
    )
    base_ready = population["physical_target_extraction_success"] & population["geometry_target_ready"]
    for spec in CANDIDATES:
        value = pd.to_numeric(population[spec["value_column"]], errors="coerce")
        ready = base_ready & np.isfinite(value)
        if spec["candidate_id"] == "T0_kinetic_energy":
            ready &= population["kinetic_energy_target_ready"]
        if spec["candidate_id"] == "R0":
            ready &= pd.to_numeric(population["T0_width_um"], errors="coerce") > 0
        population[f"ready__{spec['candidate_id']}"] = ready
        population[f"value__{spec['candidate_id']}"] = value.where(ready)
    population["keyhole_persistence_group"] = np.select(
        [
            ~population["has_keyhole"],
            population["keyhole_transient_by_sequence"],
            population["keyhole_persistent_to_last_physical_frame"],
        ],
        ["Keyhole-negative", "transient Keyhole", "persistent Keyhole"],
        default="Keyhole-positive other",
    )
    population["repeated_episode_group"] = np.select(
        [~population["has_keyhole"], population["repeated_keyhole_episodes"]],
        ["Keyhole-negative", "repeated Keyhole episodes"],
        default="single Keyhole episode",
    )
    population["keyhole_timing_group"] = np.where(
        population["has_keyhole"], population["keyhole_timing_relative_to_T0"], "no_Keyhole"
    )
    population["P_plot"] = pd.to_numeric(population.get("P_W", population["P"]), errors="coerce")
    population["VX_plot"] = pd.to_numeric(population.get("VX_m_per_s", population["VX"]), errors="coerce")
    return population.sort_values(["partition", "experiment_name"]).reset_index(drop=True)


def population_subset(population: pd.DataFrame, name: str) -> pd.DataFrame:
    if name in BASE_POPULATIONS:
        return population[population["partition"].eq(name)].copy()
    if name == "all-old":
        return population[population["partition"].isin(["old-data-local", "old-data-remote-clean"])].copy()
    if name == "all-combined":
        return population.copy()
    raise KeyError(name)


def readiness_tables(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    readiness_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    availability_rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        ready = subset["physical_target_extraction_success"]
        readiness_rows.append({
            "population": name,
            "experiment_count": len(subset),
            "physical_target_ready_count": int(ready.sum()),
            "physical_target_ineligible_count": int((~ready).sum()),
            "physical_target_ready_fraction": float(ready.mean()),
            "label_ready_count": int(subset["has_keyhole"].notna().sum()),
            "retained_row_count": len(subset),
            "simulations_removed": 0,
        })
        label_rows.append({
            "population": name,
            "experiment_count": len(subset),
            "keyhole_positive_count": int(subset["has_keyhole"].sum()),
            "keyhole_negative_count": int((~subset["has_keyhole"]).sum()),
            "keyhole_positive_fraction": float(subset["has_keyhole"].mean()),
            "conduction_positive_count": int(subset["has_conduction"].sum()),
            "target_ready_keyhole_positive_count": int((ready & subset["has_keyhole"]).sum()),
            "target_ready_keyhole_negative_count": int((ready & ~subset["has_keyhole"]).sum()),
        })
        for spec in CANDIDATES:
            available = subset[f"ready__{spec['candidate_id']}"]
            availability_rows.append({
                "population": name,
                "candidate_id": spec["candidate_id"],
                "candidate_name": spec["candidate_name"],
                "unit": spec["unit"],
                "available_count": int(available.sum()),
                "unavailable_count": int((~available).sum()),
                "availability_fraction": float(available.mean()),
                "available_keyhole_positive_count": int((available & subset["has_keyhole"]).sum()),
                "available_keyhole_negative_count": int((available & ~subset["has_keyhole"]).sum()),
            })
    return pd.DataFrame(readiness_rows), pd.DataFrame(label_rows), pd.DataFrame(availability_rows)


def group_descriptives(population: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        for spec in CANDIDATES:
            ready = subset[f"ready__{spec['candidate_id']}"]
            for label, label_value in [("Keyhole-negative", False), ("Keyhole-positive", True)]:
                values = subset.loc[
                    ready & subset["has_keyhole"].eq(label_value),
                    f"value__{spec['candidate_id']}",
                ].to_numpy(float)
                rows.append({
                    "population": name, "candidate_id": spec["candidate_id"], "unit": spec["unit"],
                    "label_group": label, "n": len(values), "mean": float(np.mean(values)),
                    "std": float(np.std(values, ddof=1)) if len(values) > 1 else math.nan,
                    "minimum": float(np.min(values)), "q25": float(np.quantile(values, .25)),
                    "median": float(np.median(values)), "q75": float(np.quantile(values, .75)),
                    "maximum": float(np.max(values)),
                })
    return pd.DataFrame(rows)


def separation_tables(population: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        for spec in CANDIDATES:
            ready = subset[f"ready__{spec['candidate_id']}"]
            x = subset.loc[ready, f"value__{spec['candidate_id']}"] .to_numpy(float)
            y = subset.loc[ready, "has_keyhole"].astype(int).to_numpy()
            raw_auc = float(roc_auc_score(y, x))
            sign = 1.0 if raw_auc >= .5 else -1.0
            scores = sign * x
            neg = scores[y == 0]
            pos = scores[y == 1]
            rows.append({
                "population": name, "candidate_id": spec["candidate_id"], "unit": spec["unit"],
                "n": len(x), "positive_n": int(y.sum()), "negative_n": int((1-y).sum()),
                "direction": "higher" if sign > 0 else "lower", "raw_roc_auc": raw_auc,
                "direction_adjusted_roc_auc": float(roc_auc_score(y, scores)),
                "direction_adjusted_average_precision": float(average_precision_score(y, scores)),
                "negative_extreme_toward_positive": float(np.max(neg)),
                "positive_extreme_toward_negative": float(np.min(pos)),
                "class_gap_in_positive_direction": float(np.min(pos) - np.max(neg)),
                "complete_rank_separation": bool(np.min(pos) > np.max(neg)),
            })
    return pd.DataFrame(rows).sort_values(["population", "direction_adjusted_roc_auc"], ascending=[True, False])


def within_population_thresholds(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries: list[pd.DataFrame] = []
    folds: list[pd.DataFrame] = []
    stabilities: list[pd.DataFrame] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        summary, detail, stability = threshold_cv_analysis(subset)
        for frame in (summary, detail, stability):
            frame.insert(0, "population", name)
        summaries.append(summary)
        folds.append(detail)
        stabilities.append(stability)
        print(f"Within-population LOO complete: {name}", flush=True)
    summary = pd.concat(summaries, ignore_index=True)
    detail = pd.concat(folds, ignore_index=True)
    stability = pd.concat(stabilities, ignore_index=True)
    stability.insert(1, "record_type", "within_population_loo")
    return summary, detail, stability


def classification_metrics(y: np.ndarray, prediction: np.ndarray) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "sensitivity": float(recall_score(y, prediction, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else math.nan,
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp),
    }


def cross_population_transfer(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for train_name, test_name, route_id in TRANSFER_ROUTES:
        train_pop = population_subset(population, train_name)
        test_pop = population_subset(population, test_name)
        overlap = set(train_pop["experiment_name"]) & set(test_pop["experiment_name"])
        descriptive = route_id == "pooled_descriptive"
        require(descriptive or not overlap, f"Transfer route leaks simulations: {route_id}")
        for spec in CANDIDATES:
            candidate = spec["candidate_id"]
            train = train_pop.loc[train_pop[f"ready__{candidate}"], ["experiment_name", "has_keyhole", f"value__{candidate}"]]
            test = test_pop.loc[test_pop[f"ready__{candidate}"], ["experiment_name", "partition", "has_keyhole", f"value__{candidate}"]]
            selected = choose_threshold(train[f"value__{candidate}"].to_numpy(float), train["has_keyhole"].astype(int).to_numpy())
            threshold = float(selected["threshold"])
            direction = str(selected["direction"])
            x = test[f"value__{candidate}"].to_numpy(float)
            y = test["has_keyhole"].astype(int).to_numpy()
            prediction = (x >= threshold).astype(int) if direction == "higher" else (x <= threshold).astype(int)
            signed_margin = x - threshold if direction == "higher" else threshold - x
            metrics = classification_metrics(y, prediction)
            summaries.append({
                "route_id": route_id, "train_population": train_name, "test_population": test_name,
                "candidate_id": candidate, "unit": spec["unit"], "evaluation_type": "pooled_descriptive_not_held_out" if descriptive else "cross_population_transfer",
                "train_n": len(train), "test_n": len(test), "train_test_overlap_n": len(overlap),
                "training_selected_direction": direction, "training_selected_threshold": threshold,
                "training_descriptive_balanced_accuracy": float(selected["balanced_accuracy"]),
                **metrics,
                "threshold_fitted_without_test_population": not descriptive,
            })
            for row, pred, margin in zip(test.itertuples(index=False), prediction, signed_margin):
                details.append({
                    "route_id": route_id, "train_population": train_name, "test_population": test_name,
                    "candidate_id": candidate, "held_out_experiment_name": row.experiment_name,
                    "held_out_partition": row.partition, "held_out_has_keyhole": int(row.has_keyhole),
                    "held_out_value": float(getattr(row, f"value__{candidate}")),
                    "training_selected_direction": direction, "training_selected_threshold": threshold,
                    "held_out_prediction": int(pred), "held_out_correct": bool(pred == int(row.has_keyhole)),
                    "held_out_signed_margin": float(margin),
                    "evaluation_type": "pooled_descriptive_not_held_out" if descriptive else "cross_population_transfer",
                    "leakage_guard": "disjoint train/test populations" if not descriptive else "not held out; descriptive pooled reference only",
                })
        print(f"Transfer complete: {route_id}", flush=True)
    return pd.DataFrame(summaries), pd.DataFrame(details)


def stratified_sample_indices(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    neg = np.flatnonzero(y == 0)
    pos = np.flatnonzero(y == 1)
    return np.concatenate([rng.choice(neg, len(neg), replace=True), rng.choice(pos, len(pos), replace=True)])


def vectorized_stratified_rank_bootstrap(
    y: np.ndarray,
    scores: np.ndarray,
    *,
    resamples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact stratified bootstrap for tie-aware ROC AUC and average precision.

    Sampling simulations with replacement within each label class is equivalent
    to drawing multinomial counts over the observed unique score levels.  This
    representation avoids repeated metric-library calls while retaining exact
    ties and the requested simulation-level bootstrap distribution.
    """

    levels = np.unique(scores)[::-1]
    positive = scores[y == 1]
    negative = scores[y == 0]
    positive_prob = np.array([(positive == level).sum() for level in levels], dtype=float)
    negative_prob = np.array([(negative == level).sum() for level in levels], dtype=float)
    positive_prob /= positive_prob.sum()
    negative_prob /= negative_prob.sum()
    positive_counts = rng.multinomial(len(positive), positive_prob, size=resamples)
    negative_counts = rng.multinomial(len(negative), negative_prob, size=resamples)

    negative_below = len(negative) - np.cumsum(negative_counts, axis=1)
    auc = (
        positive_counts * (negative_below + 0.5 * negative_counts)
    ).sum(axis=1) / (len(positive) * len(negative))

    cumulative_positive = np.cumsum(positive_counts, axis=1)
    cumulative_total = cumulative_positive + np.cumsum(negative_counts, axis=1)
    precision = np.divide(
        cumulative_positive,
        cumulative_total,
        out=np.zeros_like(cumulative_positive, dtype=float),
        where=cumulative_total > 0,
    )
    average_precision = (precision * positive_counts).sum(axis=1) / len(positive)
    return auc, average_precision


def vectorized_stratified_confusion_bootstrap(
    y: np.ndarray,
    prediction: np.ndarray,
    *,
    resamples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    positive = y == 1
    negative = y == 0
    n_positive = int(positive.sum())
    n_negative = int(negative.sum())
    sensitivity = rng.binomial(
        n_positive, float(prediction[positive].mean()), size=resamples
    ) / n_positive
    specificity = rng.binomial(
        n_negative, float((prediction[negative] == 0).mean()), size=resamples
    ) / n_negative
    return (sensitivity + specificity) / 2.0, sensitivity, specificity


def bootstrap_uncertainty(
    population: pd.DataFrame,
    within_folds: pd.DataFrame,
    transfer_summary: pd.DataFrame,
    transfer_details: pd.DataFrame,
    *,
    resamples: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        for candidate in PRIMARY_CANDIDATES:
            ready = subset[f"ready__{candidate}"]
            x = subset.loc[ready, f"value__{candidate}"].to_numpy(float)
            y = subset.loc[ready, "has_keyhole"].astype(int).to_numpy()
            raw_auc = roc_auc_score(y, x)
            scores = x if raw_auc >= .5 else -x
            fold = within_folds[(within_folds["population"].eq(name)) & (within_folds["candidate_id"].eq(candidate))]
            fold = fold.set_index("held_out_experiment_name").loc[subset.loc[ready, "experiment_name"]]
            prediction = fold["held_out_prediction"].to_numpy(int)
            rng = np.random.default_rng(deterministic_seed("phase55", name, candidate, resamples))
            auc_samples, ap_samples = vectorized_stratified_rank_bootstrap(
                y, scores, resamples=resamples, rng=rng
            )
            ba_samples, sensitivity_samples, specificity_samples = (
                vectorized_stratified_confusion_bootstrap(
                    y, prediction, resamples=resamples, rng=rng
                )
            )
            samples = {
                "roc_auc": auc_samples,
                "average_precision": ap_samples,
                "loo_balanced_accuracy": ba_samples,
                "loo_sensitivity": sensitivity_samples,
                "loo_specificity": specificity_samples,
            }
            estimates = {
                "roc_auc": roc_auc_score(y, scores),
                "average_precision": average_precision_score(y, scores),
                **{f"loo_{k}" if k == "balanced_accuracy" else f"loo_{k}": v for k, v in classification_metrics(y, prediction).items() if k in {"balanced_accuracy", "sensitivity", "specificity"}},
            }
            for metric, values in samples.items():
                rows.append({
                    "analysis_type": "within_population", "population_or_route": name,
                    "train_population": name, "test_population": name, "candidate_id": candidate,
                    "metric": metric, "estimate": float(estimates[metric]),
                    "ci_low": float(np.quantile(values, .025)), "ci_high": float(np.quantile(values, .975)),
                    "bootstrap_resamples": resamples, "bootstrap_unit": "simulation",
                    "bootstrap_scheme": "stratified by Keyhole label",
                })
    non_descriptive = transfer_summary[transfer_summary["evaluation_type"].eq("cross_population_transfer")]
    for summary in non_descriptive.itertuples(index=False):
        if summary.candidate_id not in PRIMARY_CANDIDATES:
            continue
        detail = transfer_details[(transfer_details["route_id"].eq(summary.route_id)) & (transfer_details["candidate_id"].eq(summary.candidate_id))]
        y = detail["held_out_has_keyhole"].to_numpy(int)
        prediction = detail["held_out_prediction"].to_numpy(int)
        rng = np.random.default_rng(deterministic_seed("phase55-transfer", summary.route_id, summary.candidate_id, resamples))
        ba_samples, sensitivity_samples, specificity_samples = (
            vectorized_stratified_confusion_bootstrap(
                y, prediction, resamples=resamples, rng=rng
            )
        )
        metrics_arrays = {
            "balanced_accuracy": ba_samples,
            "sensitivity": sensitivity_samples,
            "specificity": specificity_samples,
        }
        for metric, values in metrics_arrays.items():
            rows.append({
                "analysis_type": "cross_population_transfer", "population_or_route": summary.route_id,
                "train_population": summary.train_population, "test_population": summary.test_population,
                "candidate_id": summary.candidate_id, "metric": f"transfer_{metric}",
                "estimate": float(getattr(summary, metric)), "ci_low": float(np.quantile(values, .025)),
                "ci_high": float(np.quantile(values, .975)), "bootstrap_resamples": resamples,
                "bootstrap_unit": "simulation", "bootstrap_scheme": "stratified test-population resampling; training threshold fixed",
            })
    return pd.DataFrame(rows)


def threshold_margin_diagnostics(
    population: pd.DataFrame,
    within_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        for candidate in PRIMARY_CANDIDATES:
            spec = next(item for item in CANDIDATES if item["candidate_id"] == candidate)
            ready = subset[f"ready__{candidate}"]
            frame = subset.loc[ready, ["experiment_name", "has_keyhole", f"value__{candidate}"]].copy()
            info = within_summary[(within_summary["population"].eq(name)) & (within_summary["candidate_id"].eq(candidate))].iloc[0]
            threshold = float(info["full_data_descriptive_threshold"])
            direction = str(info["full_data_descriptive_direction"])
            sign = 1.0 if direction == "higher" else -1.0
            frame["score"] = sign * frame[f"value__{candidate}"]
            score_threshold = sign * threshold
            neg = frame[~frame["has_keyhole"]]
            pos = frame[frame["has_keyhole"]]
            neg_edge = float(neg["score"].max())
            pos_edge = float(pos["score"].min())
            below = frame[frame["score"] < score_threshold].sort_values("score", ascending=False)
            above = frame[frame["score"] >= score_threshold].sort_values("score")
            bands = [0.02, 0.05, 0.10] if spec["unit"] == "dimensionless" else [2.0, 5.0, 10.0]
            for band in bands:
                close = frame[np.abs(frame["score"] - score_threshold) <= band]
                rows.append({
                    "population": name, "candidate_id": candidate, "unit": spec["unit"],
                    "descriptive_direction": direction, "descriptive_threshold": threshold,
                    "band_half_width": band, "band_semantics": "ratio analogue" if spec["unit"] == "dimensionless" else "micrometre band",
                    "within_band_count": len(close), "within_band_keyhole_positive_count": int(close["has_keyhole"].sum()),
                    "within_band_keyhole_negative_count": int((~close["has_keyhole"]).sum()),
                    "negative_edge_score": neg_edge, "positive_edge_score": pos_edge,
                    "class_gap_in_positive_direction": pos_edge - neg_edge,
                    "empty_class_gap": bool(pos_edge > neg_edge),
                    "threshold_inside_empty_gap": bool(neg_edge < score_threshold < pos_edge),
                    "nearest_below_experiment": "" if below.empty else str(below.iloc[0]["experiment_name"]),
                    "nearest_below_value": math.nan if below.empty else float(below.iloc[0][f"value__{candidate}"]),
                    "nearest_below_distance": math.nan if below.empty else float(score_threshold - below.iloc[0]["score"]),
                    "nearest_above_experiment": "" if above.empty else str(above.iloc[0]["experiment_name"]),
                    "nearest_above_value": math.nan if above.empty else float(above.iloc[0][f"value__{candidate}"]),
                    "nearest_above_distance": math.nan if above.empty else float(above.iloc[0]["score"] - score_threshold),
                })
    return pd.DataFrame(rows)


def subgroup_table(population: pd.DataFrame, group_column: str, subgroup_type: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        for candidate in PRIMARY_CANDIDATES:
            ready = subset[f"ready__{candidate}"]
            for group, frame in subset[ready].groupby(group_column, dropna=False):
                values = frame[f"value__{candidate}"].to_numpy(float)
                rows.append({
                    "population": name, "subgroup_type": subgroup_type, "subgroup": str(group),
                    "candidate_id": candidate, "n": len(frame), "keyhole_positive_n": int(frame["has_keyhole"].sum()),
                    "mean": float(np.mean(values)), "median": float(np.median(values)),
                    "q25": float(np.quantile(values, .25)), "q75": float(np.quantile(values, .75)),
                    "minimum": float(np.min(values)), "maximum": float(np.max(values)),
                })
    return pd.DataFrame(rows)


def process_map_summary(population: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in ANALYSIS_POPULATIONS:
        subset = population_subset(population, name)
        g3 = subset.loc[subset["ready__G3"], "value__G3"]
        rows.append({
            "population": name, "experiment_count": len(subset),
            "P_min_W": float(subset["P_plot"].min()), "P_median_W": float(subset["P_plot"].median()), "P_max_W": float(subset["P_plot"].max()),
            "VX_min_m_per_s": float(subset["VX_plot"].min()), "VX_median_m_per_s": float(subset["VX_plot"].median()), "VX_max_m_per_s": float(subset["VX_plot"].max()),
            "LS_min_um": float(pd.to_numeric(subset.get("LS_um", subset["LS"] * 1e6), errors="coerce").min()),
            "LS_max_um": float(pd.to_numeric(subset.get("LS_um", subset["LS"] * 1e6), errors="coerce").max()),
            "ST_min_K": float(pd.to_numeric(subset.get("ST_K", subset["ST"]), errors="coerce").min()),
            "ST_max_K": float(pd.to_numeric(subset.get("ST_K", subset["ST"]), errors="coerce").max()),
            "keyhole_positive_fraction": float(subset["has_keyhole"].mean()),
            "G3_available_n": len(g3), "G3_median_um": float(g3.median()), "G3_iqr_um": float(g3.quantile(.75) - g3.quantile(.25)),
        })
    return pd.DataFrame(rows)


def hard_case_linkage(
    population: pd.DataFrame,
    phase4: pd.DataFrame,
    phase5: pd.DataFrame,
    within_folds: pd.DataFrame,
) -> pd.DataFrame:
    phase4_flags = phase4[["experiment_name", "consensus_hard_case", "consensus_mean_residual_rank", "mean_absolute_residual_across_models"]].copy()
    phase5_flags = (
        phase5[["experiment_name", "review_candidate", "error_type", "diagnostic_review_outcome"]]
        .groupby("experiment_name", as_index=False)
        .agg({
            "review_candidate": lambda values: ";".join(sorted(set(map(str, values)))),
            "error_type": lambda values: ";".join(sorted(set(map(str, values)))),
            "diagnostic_review_outcome": lambda values: ";".join(sorted(set(map(str, values)))),
        })
    )
    base = population[population["partition"].eq("new-data")][[
        "experiment_name", "has_keyhole", "value__G3", "value__R3", "value__max_depth", "value__T0_depth",
        "keyhole_persistence_group", "keyhole_timing_group",
    ]]
    result = base.merge(phase4_flags, on="experiment_name", how="left").merge(phase5_flags, on="experiment_name", how="left")
    for candidate in PRIMARY_CANDIDATES:
        fold = within_folds[(within_folds["population"].eq("new-data")) & (within_folds["candidate_id"].eq(candidate))][[
            "held_out_experiment_name", "held_out_prediction", "held_out_correct", "held_out_signed_margin"
        ]].rename(columns={
            "held_out_experiment_name": "experiment_name",
            "held_out_prediction": f"loo_prediction__{candidate}",
            "held_out_correct": f"loo_correct__{candidate}",
            "held_out_signed_margin": f"loo_signed_margin__{candidate}",
        })
        result = result.merge(fold, on="experiment_name", how="left", validate="one_to_one")
    result["consensus_hard_case"] = bool_series(result["consensus_hard_case"])
    result["phase5_discordant_review_case"] = result["review_candidate"].notna()
    return result.sort_values(["consensus_hard_case", "phase5_discordant_review_case", "experiment_name"], ascending=[False, False, True])


def scorecard_tables(
    separation: pd.DataFrame,
    within: pd.DataFrame,
    stability: pd.DataFrame,
    transfer: pd.DataFrame,
    availability: pd.DataFrame,
    subgroup_persistence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    heldout_transfer = transfer[transfer["evaluation_type"].eq("cross_population_transfer")]
    for candidate in [*PRIMARY_CANDIDATES, *SECONDARY_CANDIDATES]:
        sep = separation[separation["candidate_id"].eq(candidate)]
        cv = within[within["candidate_id"].eq(candidate)]
        stab = stability[stability["candidate_id"].eq(candidate)]
        trans = heldout_transfer[heldout_transfer["candidate_id"].eq(candidate)]
        avail = availability[availability["candidate_id"].eq(candidate)]
        persistent = subgroup_persistence[(subgroup_persistence["candidate_id"].eq(candidate)) & subgroup_persistence["subgroup"].isin(["transient Keyhole", "persistent Keyhole"])]
        direction_agreement = float(cv["full_data_descriptive_direction"].value_counts(normalize=True).iloc[0])
        normalized_stability = pd.to_numeric(stab["threshold_iqr_over_candidate_iqr"], errors="coerce")
        rows.append({
            "candidate_id": candidate,
            "mean_direction_adjusted_roc_auc": float(sep["direction_adjusted_roc_auc"].mean()),
            "minimum_direction_adjusted_roc_auc": float(sep["direction_adjusted_roc_auc"].min()),
            "mean_within_population_loo_balanced_accuracy": float(cv["balanced_accuracy"].mean()),
            "minimum_within_population_loo_balanced_accuracy": float(cv["balanced_accuracy"].min()),
            "mean_cross_population_transfer_balanced_accuracy": float(trans["balanced_accuracy"].mean()),
            "minimum_cross_population_transfer_balanced_accuracy": float(trans["balanced_accuracy"].min()),
            "mean_transfer_sensitivity": float(trans["sensitivity"].mean()),
            "mean_transfer_specificity": float(trans["specificity"].mean()),
            "descriptive_direction_agreement_fraction": direction_agreement,
            "median_normalized_loo_threshold_iqr": float(normalized_stability.median()),
            "minimum_candidate_availability_fraction": float(avail["availability_fraction"].min()),
            "subgroup_rows_evaluated": len(persistent),
        })
    score = pd.DataFrame(rows)
    for column in [
        "mean_direction_adjusted_roc_auc", "mean_within_population_loo_balanced_accuracy",
        "mean_cross_population_transfer_balanced_accuracy", "descriptive_direction_agreement_fraction",
        "minimum_candidate_availability_fraction",
    ]:
        score[f"rank__{column}"] = score[column].rank(ascending=False, method="min")
    score["aggregate_rank_sum"] = score.filter(like="rank__").sum(axis=1)
    score = score.sort_values(["aggregate_rank_sum", "mean_cross_population_transfer_balanced_accuracy"], ascending=[True, False]).reset_index(drop=True)
    decision_rows = []
    for row in score[score["candidate_id"].isin(PRIMARY_CANDIDATES)].itertuples(index=False):
        candidate_transfer = heldout_transfer[heldout_transfer["candidate_id"].eq(row.candidate_id)]
        minimum_transfer_sensitivity = float(candidate_transfer["sensitivity"].min())
        minimum_transfer_specificity = float(candidate_transfer["specificity"].min())
        robust = (
            row.minimum_cross_population_transfer_balanced_accuracy >= .90
            and minimum_transfer_sensitivity >= .80
            and minimum_transfer_specificity >= .80
            and row.descriptive_direction_agreement_fraction == 1.0
        )
        transferable_with_shift = (
            row.minimum_cross_population_transfer_balanced_accuracy >= .75
            and row.descriptive_direction_agreement_fraction == 1.0
        )
        decision_rows.append({
            "candidate_id": row.candidate_id,
            "robust_across_predeclared_transfer_routes": robust,
            "transferable_with_partition_shift_caveat": transferable_with_shift and not robust,
            "decision": (
                "ROBUST CROSS-PARTITION SCALAR COMPANION"
                if robust
                else "TRANSFERABLE WITH PARTITION-SHIFT CAVEAT"
                if transferable_with_shift
                else "PARTITION-SENSITIVE SCALAR COMPANION"
            ),
            "mean_within_loo_balanced_accuracy": row.mean_within_population_loo_balanced_accuracy,
            "worst_transfer_balanced_accuracy": row.minimum_cross_population_transfer_balanced_accuracy,
            "worst_transfer_sensitivity": minimum_transfer_sensitivity,
            "worst_transfer_specificity": minimum_transfer_specificity,
            "direction_agreement_fraction": row.descriptive_direction_agreement_fraction,
            "label_replacement_authorized": False,
            "interpretation": "Physical association and threshold stress test only; manual morphology label remains authoritative.",
        })
    decisions = pd.DataFrame(decision_rows).sort_values("worst_transfer_balanced_accuracy", ascending=False)
    g3 = decisions[decisions["candidate_id"].eq("G3")].iloc[0]
    recommendation = pd.DataFrame([{
        "recommended_boundary_formulation": "retain binary has_keyhole reference; do not universalize the new-data G3 threshold; carry G3 with max-depth as a comparator only under a separately approved Phase 6 protocol",
        "universal_fixed_G3_threshold_recommended": bool(g3["robust_across_predeclared_transfer_routes"]),
        "phase6_candidate": "compare unchanged binary Keyhole boundary with continuous G3 and max-depth benchmarks under a separately approved protocol",
        "reason": f"G3 worst held-out transfer balanced accuracy={g3['worst_transfer_balanced_accuracy']:.4f}, worst transfer sensitivity={g3['worst_transfer_sensitivity']:.4f}, and direction agreement={g3['direction_agreement_fraction']:.3f}; the scalar association transfers, but its threshold location shifts materially by partition.",
        "labels_modified": False,
        "new_target_declared": False,
        "hard_stop": "No predictive modelling, active learning, acquisition, level-set estimation, or relabelling in Phase 5.5.",
    }])
    return score, decisions, recommendation


def add_footer(fig: plt.Figure, *, population: str, units: str, method: str, caveat: str) -> None:
    fig.text(.01, .01, f"Population: {population} | Units: {units} | Method: {method} | Caveat: {caveat}", fontsize=7, color="#444444")


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def distribution_plot(population: pd.DataFrame, candidate: str, path: Path) -> None:
    spec = next(item for item in CANDIDATES if item["candidate_id"] == candidate)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    rng = np.random.default_rng(deterministic_seed("dist", candidate))
    for ax, partition in zip(axes, BASE_POPULATIONS):
        subset = population[(population["partition"].eq(partition)) & population[f"ready__{candidate}"]]
        groups = [subset.loc[~subset["has_keyhole"], f"value__{candidate}"].to_numpy(float), subset.loc[subset["has_keyhole"], f"value__{candidate}"].to_numpy(float)]
        ax.boxplot(groups, tick_labels=["negative", "positive"], showfliers=False)
        for x_pos, values, color in [(1, groups[0], "#4477AA"), (2, groups[1], "#CC3311")]:
            ax.scatter(x_pos + rng.uniform(-.08, .08, len(values)), values, s=10, alpha=.45, color=color)
        ax.set_title(partition)
        ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel(f"{spec['candidate_name']} ({spec['unit']})")
    fig.suptitle(f"{candidate}: label distributions by base partition")
    add_footer(fig, population="three audited base partitions", units=spec["unit"], method="simulation-level boxplots and points", caveat="descriptive; labels are manual morphology annotations")
    fig.tight_layout(rect=(0, .05, 1, .94))
    save_figure(fig, path)


def generate_figures(
    destination: Path,
    population: pd.DataFrame,
    readiness: pd.DataFrame,
    labels: pd.DataFrame,
    within: pd.DataFrame,
    transfer: pd.DataFrame,
    stability: pd.DataFrame,
    margins: pd.DataFrame,
    scorecard: pd.DataFrame,
) -> pd.DataFrame:
    figure_dir = destination / FIGURE_DIRNAME
    figure_dir.mkdir(parents=True, exist_ok=True)
    files: list[tuple[str, str]] = []

    base_ready = readiness[readiness["population"].isin(BASE_POPULATIONS)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(base_ready))
    ax.bar(x, base_ready["experiment_count"], label="retained", color="#B7C9E2")
    ax.bar(x, base_ready["physical_target_ready_count"], label="physically usable", color="#2A9D8F")
    ax.set_xticks(x, base_ready["population"], rotation=15); ax.set_ylabel("simulations"); ax.set_title("Current-revision population readiness"); ax.legend()
    add_footer(fig, population="407 retained simulations", units="count", method="exact current-revision target refresh", caveat="two ineligible rows remain visible")
    save_figure(fig, figure_dir / "01_partition_overview.png"); files.append(("01_partition_overview.png", "How many simulations are retained and physically usable?"))

    base_labels = labels[labels["population"].isin(BASE_POPULATIONS)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x, base_labels["keyhole_negative_count"], label="negative", color="#4477AA")
    ax.bar(x, base_labels["keyhole_positive_count"], bottom=base_labels["keyhole_negative_count"], label="positive", color="#CC3311")
    ax.set_xticks(x, base_labels["population"], rotation=15); ax.set_ylabel("simulations"); ax.set_title("Manual Keyhole label composition"); ax.legend()
    add_footer(fig, population="three base partitions", units="count", method="validated Phase 1 has_keyhole semantics", caveat="not a scalar-threshold label")
    save_figure(fig, figure_dir / "02_label_composition.png"); files.append(("02_label_composition.png", "Does label prevalence differ by partition?"))

    for number, candidate in zip(range(3, 7), ["G3", "R3", "max_depth", "T0_depth"]):
        filename = f"{number:02d}_{candidate}_distributions.png"
        distribution_plot(population, candidate, figure_dir / filename)
        files.append((filename, f"How does {candidate} separate labels across partitions?"))

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, candidate in zip(axes.ravel(), PRIMARY_CANDIDATES):
        subset = population[population[f"ready__{candidate}"]].sort_values(f"value__{candidate}").reset_index(drop=True)
        colors = np.where(subset["has_keyhole"], "#CC3311", "#4477AA")
        ax.scatter(np.arange(len(subset)), subset[f"value__{candidate}"], c=colors, s=10, alpha=.65)
        for name, linestyle in [("new-data", "-"), ("all-old", "--")]:
            info = within[(within["population"].eq(name)) & (within["candidate_id"].eq(candidate))].iloc[0]
            ax.axhline(info["full_data_descriptive_threshold"], linestyle=linestyle, lw=1.2, label=name)
        ax.set_title(candidate); ax.set_xlabel("sorted simulations"); ax.legend(fontsize=7)
    fig.suptitle("Sorted scalar values and descriptive new/old thresholds")
    add_footer(fig, population="all combined", units="candidate-specific", method="sorted values; descriptive full-population thresholds", caveat="horizontal lines are not held-out performance")
    fig.tight_layout(rect=(0, .04, 1, .95)); save_figure(fig, figure_dir / "07_sorted_values_thresholds.png"); files.append(("07_sorted_values_thresholds.png", "Do candidate thresholds shift between new and old data?"))

    g3_margin = margins[(margins["candidate_id"].eq("G3")) & (margins["band_half_width"].eq(2.0))]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(g3_margin["population"], g3_margin["class_gap_in_positive_direction"], color=np.where(g3_margin["class_gap_in_positive_direction"] > 0, "#2A9D8F", "#E76F51"))
    ax.axhline(0, color="black", lw=1); ax.set_ylabel("G3 class gap (um)"); ax.set_title("G3 gap between nearest negative and positive cases"); ax.tick_params(axis="x", rotation=20)
    add_footer(fig, population="five analysis populations", units="um", method="nearest class-edge gap in positive direction", caveat="a positive empty gap may still be sample-specific")
    fig.tight_layout(rect=(0, .06, 1, 1)); save_figure(fig, figure_dir / "08_threshold_gap_margin.png"); files.append(("08_threshold_gap_margin.png", "Is there an empty G3 margin between classes?"))

    fig, axes = plt.subplots(1, 5, figsize=(19, 4), sharex=True, sharey=True)
    for ax, name in zip(axes, ANALYSIS_POPULATIONS):
        subset = population_subset(population, name)
        for candidate in PRIMARY_CANDIDATES:
            ready = subset[f"ready__{candidate}"]; y = subset.loc[ready, "has_keyhole"].astype(int).to_numpy(); xval = subset.loc[ready, f"value__{candidate}"].to_numpy(float)
            if roc_auc_score(y, xval) < .5: xval = -xval
            fpr, tpr, _ = roc_curve(y, xval); ax.plot(fpr, tpr, label=candidate)
        ax.plot([0,1],[0,1], color="#888", ls=":"); ax.set_title(name, fontsize=9); ax.set_aspect("equal")
    axes[0].set_ylabel("TPR"); axes[2].set_xlabel("FPR"); axes[-1].legend(fontsize=7)
    fig.suptitle("Direction-adjusted ROC curves by population")
    add_footer(fig, population="five analysis populations", units="rate", method="descriptive rank curves", caveat="curves do not provide a deployable threshold")
    fig.tight_layout(rect=(0, .04, 1, .93)); save_figure(fig, figure_dir / "09_roc_by_population.png"); files.append(("09_roc_by_population.png", "Does rank separation persist across populations?"))

    fig, axes = plt.subplots(1, 5, figsize=(19, 4), sharex=True, sharey=True)
    for ax, name in zip(axes, ANALYSIS_POPULATIONS):
        subset = population_subset(population, name)
        for candidate in PRIMARY_CANDIDATES:
            ready = subset[f"ready__{candidate}"]; y = subset.loc[ready, "has_keyhole"].astype(int).to_numpy(); xval = subset.loc[ready, f"value__{candidate}"].to_numpy(float)
            if roc_auc_score(y, xval) < .5: xval = -xval
            precision, recall, _ = precision_recall_curve(y, xval); ax.plot(recall, precision, label=candidate)
        ax.set_title(name, fontsize=9)
    axes[0].set_ylabel("precision"); axes[2].set_xlabel("recall"); axes[-1].legend(fontsize=7)
    fig.suptitle("Precision-recall curves by population")
    add_footer(fig, population="five analysis populations", units="rate", method="descriptive rank curves", caveat="prevalence differs by partition")
    fig.tight_layout(rect=(0, .04, 1, .93)); save_figure(fig, figure_dir / "10_pr_by_population.png"); files.append(("10_pr_by_population.png", "Does precision-recall separation persist under prevalence shift?"))

    matrix = within[within["candidate_id"].isin(PRIMARY_CANDIDATES)].pivot(index="population", columns="candidate_id", values="balanced_accuracy").reindex(index=ANALYSIS_POPULATIONS, columns=PRIMARY_CANDIDATES)
    fig, ax = plt.subplots(figsize=(7, 5)); im=ax.imshow(matrix, vmin=.5, vmax=1, cmap="YlGn")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns); ax.set_yticks(range(len(matrix.index)), matrix.index)
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)): ax.text(j,i,f"{matrix.iloc[i,j]:.2f}",ha="center",va="center",fontsize=8)
    fig.colorbar(im, ax=ax, label="LOO balanced accuracy"); ax.set_title("Within-population exact LOO thresholds")
    add_footer(fig, population="five analysis populations", units="balanced accuracy", method="threshold selected without held-out simulation", caveat="within-population validation is not domain transfer")
    fig.tight_layout(rect=(0, .05, 1, 1)); save_figure(fig, figure_dir / "11_within_population_performance.png"); files.append(("11_within_population_performance.png", "How well do within-population thresholds generalize?"))

    transfer_main = transfer[(transfer["candidate_id"].isin(PRIMARY_CANDIDATES)) & transfer["evaluation_type"].eq("cross_population_transfer")]
    matrix = transfer_main.pivot(index="route_id", columns="candidate_id", values="balanced_accuracy").reindex(columns=PRIMARY_CANDIDATES)
    fig, ax = plt.subplots(figsize=(8, 6)); im=ax.imshow(matrix, vmin=.5, vmax=1, cmap="YlOrRd")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns); ax.set_yticks(range(len(matrix.index)), matrix.index)
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)): ax.text(j,i,f"{matrix.iloc[i,j]:.2f}",ha="center",va="center",fontsize=8)
    fig.colorbar(im, ax=ax, label="transfer balanced accuracy"); ax.set_title("Cross-population fixed-threshold transfer")
    add_footer(fig, population="six disjoint train/test routes", units="balanced accuracy", method="threshold fitted on source population only", caveat="no process-feature model is fitted")
    fig.tight_layout(rect=(0, .05, 1, 1)); save_figure(fig, figure_dir / "12_cross_population_transfer.png"); files.append(("12_cross_population_transfer.png", "Which scalar thresholds transfer between domains?"))

    g3_stab = stability[stability["candidate_id"].eq("G3")].set_index("population").reindex(ANALYSIS_POPULATIONS)
    fig, ax = plt.subplots(figsize=(9, 4.8)); ax.errorbar(np.arange(len(g3_stab)), g3_stab["threshold_median"], yerr=[g3_stab["threshold_median"]-g3_stab["threshold_q25"],g3_stab["threshold_q75"]-g3_stab["threshold_median"]], fmt="o", capsize=5)
    ax.set_xticks(range(len(g3_stab)), g3_stab.index, rotation=20); ax.set_ylabel("G3 threshold (um)"); ax.set_title("G3 LOO training-threshold stability")
    add_footer(fig, population="five analysis populations", units="um", method="median and IQR across LOO training folds", caveat="between-population shifts remain scientifically relevant")
    fig.tight_layout(rect=(0, .06, 1, 1)); save_figure(fig, figure_dir / "13_threshold_stability.png"); files.append(("13_threshold_stability.png", "Are G3 training thresholds stable within and between populations?"))

    for number, group_col, title in [(14, "keyhole_persistence_group", "Transient and persistent Keyhole"), (15, "keyhole_timing_group", "Keyhole timing relative to T0")]:
        fig, ax = plt.subplots(figsize=(11, 5)); ready=population["ready__G3"]; groups=list(population.loc[ready,group_col].dropna().unique()); data=[population.loc[ready & population[group_col].eq(g),"value__G3"].to_numpy(float) for g in groups]
        ax.boxplot(data, tick_labels=groups, showfliers=False); ax.set_ylabel("G3 (um)"); ax.set_title(title); ax.tick_params(axis="x", rotation=25)
        add_footer(fig, population="all combined", units="um", method="simulation-level subgroup boxplots", caveat="subgroups come from saved-frame label sequences")
        fig.tight_layout(rect=(0, .06, 1, 1)); filename=f"{number:02d}_{'persistence' if number==14 else 't0_timing'}_subgroups.png"; save_figure(fig, figure_dir/filename); files.append((filename, f"Does G3 remain informative for {title.lower()}?"))

    for number, color_mode in [(16, "label"), (17, "G3")]:
        fig, axes=plt.subplots(1,3,figsize=(14,4.5),sharex=True,sharey=True)
        for ax, part in zip(axes,BASE_POPULATIONS):
            sub=population[population["partition"].eq(part)]
            if color_mode=="label": c=np.where(sub["has_keyhole"],"#CC3311","#4477AA"); sc=ax.scatter(sub["VX_plot"],sub["P_plot"],c=c,s=25,alpha=.75)
            else:
                sub=sub[sub["ready__G3"]]; sc=ax.scatter(sub["VX_plot"],sub["P_plot"],c=sub["value__G3"],cmap="viridis",s=25,alpha=.8)
            ax.set_title(part); ax.set_xlabel("VX (m/s)"); ax.grid(alpha=.2)
        axes[0].set_ylabel("P (W)")
        if color_mode=="G3": fig.colorbar(sc,ax=axes,label="G3 (um)")
        fig.suptitle(f"Process-map context colored by {color_mode}")
        add_footer(fig,population="three base partitions",units="P W; VX m/s",method="descriptive process map",caveat="domain context, not a fitted process boundary")
        fig.tight_layout(rect=(0,.05,1,.93)); filename=f"{number:02d}_process_map_{color_mode}.png"; save_figure(fig,figure_dir/filename); files.append((filename,f"How do partitions and {color_mode} occupy the P-VX domain?"))

    for number, other in [(18,"R3"),(19,"max_depth")]:
        ready=population["ready__G3"] & population[f"ready__{other}"]; sub=population[ready]
        fig,ax=plt.subplots(figsize=(7,5)); ax.scatter(sub["value__G3"],sub[f"value__{other}"],c=np.where(sub["has_keyhole"],"#CC3311","#4477AA"),s=20,alpha=.6)
        ax.set_xlabel("G3 (um)"); ax.set_ylabel(f"{other} ({'dimensionless' if other=='R3' else 'um'})"); ax.set_title(f"G3 versus {other}, colored by manual label")
        add_footer(fig,population="all combined",units="candidate-specific",method="simulation-level scatter",caveat="association does not prove causal equivalence")
        fig.tight_layout(rect=(0,.05,1,1)); filename=f"{number:02d}_G3_vs_{other}.png"; save_figure(fig,figure_dir/filename); files.append((filename,f"How does G3 relate to {other} across labels?"))

    main_score=scorecard[scorecard["candidate_id"].isin(PRIMARY_CANDIDATES)].set_index("candidate_id").reindex(PRIMARY_CANDIDATES)
    fig,ax=plt.subplots(figsize=(9,5)); width=.25; xi=np.arange(len(main_score)); ax.bar(xi-width,main_score["mean_within_population_loo_balanced_accuracy"],width,label="mean within LOO"); ax.bar(xi,main_score["mean_cross_population_transfer_balanced_accuracy"],width,label="mean transfer"); ax.bar(xi+width,main_score["minimum_cross_population_transfer_balanced_accuracy"],width,label="worst transfer"); ax.set_xticks(xi,main_score.index); ax.set_ylim(.45,1.02); ax.set_ylabel("balanced accuracy"); ax.set_title("Phase 5.5 scalar-proxy decision evidence"); ax.legend()
    add_footer(fig,population="five populations and six held-out routes",units="balanced accuracy",method="predeclared scalar threshold stress tests",caveat="binary morphology label remains unchanged")
    fig.tight_layout(rect=(0,.05,1,1)); save_figure(fig,figure_dir/"20_phase55_decision_summary.png"); files.append(("20_phase55_decision_summary.png","Which scalar is most robust, and what should Phase 6 carry forward?"))

    rows=[]
    for filename, question in files:
        path=figure_dir/filename
        rows.append({"figure":f"{FIGURE_DIRNAME}/{filename}","question":question,"sha256":sha256_file(path),"bytes":path.stat().st_size,"population_units_method_caveat_in_figure":True})
    require(len(rows)>=20,"Fewer than 20 Phase 5.5 figures were created")
    return pd.DataFrame(rows)


def input_provenance(preflight: dict[str, Any], hf_audit: dict[str, Any]) -> dict[str, Any]:
    paths = [
        PHASE1_DIR / "experiment_registry.csv", PHASE1_DIR / "experiment_label_sequences.csv",
        PHASE2_DIR / "sph_v2_simulation_level_targets.parquet", PHASE2_DIR / "week6_exact_identifier_map.csv",
        PHASE4_DIR / "depth_consensus_hard_cases.csv", PHASE5_DIR / "physical_proxy_discordant_cases.csv",
        ROOT / "src" / "week7_phase2_sph_v2_physical_target_extraction.py",
        ROOT / "src" / "week7_phase5_keyhole_physical_proxy_analysis.py",
    ]
    return {
        "created_at_utc": utc_now(), "phase55_parent": PHASE5_COMMIT_SHA,
        "dataset_repository": DATASET_REPO_ID, "pinned_revision": PINNED_REVISION,
        "analysis_revision": CURRENT_REVISION, "hf_change_audit": hf_audit,
        "inputs": [{"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in paths],
        "candidate_ids": [item["candidate_id"] for item in CANDIDATES],
        "primary_candidates": PRIMARY_CANDIDATES, "secondary_candidates": SECONDARY_CANDIDATES,
        "analysis_populations": ANALYSIS_POPULATIONS, "transfer_routes": [route[2] for route in TRANSFER_ROUTES],
        "label_semantics": "has_keyhole means at least one valid saved physical frame was manually labelled Keyhole",
        "target_refresh_rule": "re-extract exactly the 55 changed monitor bundles; reuse 352 rows only after exact Git-tree proof of unchanged inputs",
        "preflight_original_worktree": preflight["original_worktree"],
    }


def core_validation(
    preflight: dict[str, Any], hf_audit: dict[str, Any], targets: pd.DataFrame,
    readiness: pd.DataFrame, within: pd.DataFrame, transfer: pd.DataFrame,
    bootstrap: pd.DataFrame, figures: pd.DataFrame,
) -> pd.DataFrame:
    checks = [
        ("V01", "exact Phase 5 parent", preflight["phase55_parent"] == PHASE5_COMMIT_SHA, preflight["phase55_parent"]),
        ("V02", "exact current HF revision", hf_audit["live_main_matches_current"], hf_audit["live_main_revision"]),
        ("V03", "only 110 authorized monitor additions", hf_audit["only_expected_monitor_additions"], str(hf_audit["filename_counts"])),
        ("V04", "no new-data, label, geometry, or iteration change", not any([hf_audit["new_data_paths_changed"],hf_audit["label_paths_changed"],hf_audit["geometry_paths_changed"],hf_audit["iteration_paths_changed"]]), "all protected path classes unchanged"),
        ("V05", "407 rows retained", len(targets) == 407 and targets["experiment_name"].is_unique, f"rows={len(targets)}"),
        ("V06", "405 physical targets usable", int(bool_series(targets["physical_target_extraction_success"]).sum()) == 405, f"usable={int(bool_series(targets['physical_target_extraction_success']).sum())}"),
        ("V07", "partition readiness exact", readiness.set_index("population").loc["new-data","physical_target_ready_count"] == 164 and readiness.set_index("population").loc["old-data-local","physical_target_ready_count"] == 178 and readiness.set_index("population").loc["old-data-remote-clean","physical_target_ready_count"] == 63, "164/165; 178/179; 63/63"),
        ("V08", "all five within-population LOO analyses present", set(within["population"]) == set(ANALYSIS_POPULATIONS), f"rows={len(within)}"),
        ("V09", "transfer train/test disjoint except pooled descriptive", transfer.loc[transfer["evaluation_type"].eq("cross_population_transfer"),"train_test_overlap_n"].eq(0).all(), "held-out routes overlap=0"),
        ("V10", "bootstrap is simulation-level with requested full count", bootstrap["bootstrap_unit"].eq("simulation").all() and int(bootstrap["bootstrap_resamples"].min()) in {SMOKE_BOOTSTRAP_RESAMPLES,FULL_BOOTSTRAP_RESAMPLES}, f"resamples={int(bootstrap['bootstrap_resamples'].min())}"),
        ("V11", "at least 20 explanatory figures", len(figures) >= 20 and figures["population_units_method_caveat_in_figure"].all(), f"figures={len(figures)}"),
        ("V12", "original dirty checkout still matches preflight", preflight["original_worktree"]["branch"] == "main" and preflight["original_worktree"]["head"] == "6fd6be57e5341e083a7023a3ae29e65b7b326bbd" and preflight["original_worktree"]["protected_hashes_match"], f"status_lines={len(preflight['original_worktree']['git_status_short'])}"),
        ("V13", "scope hard stop recorded", not any(preflight["scope"][key] for key in ["predictive_models_fitted","classifiers_fitted","active_learning_run","level_set_estimated","labels_modified","simulations_removed"]), "all prohibited actions false"),
    ]
    return pd.DataFrame([{"check_id":cid,"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for cid,name,ok,detail in checks])


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    items = [
        ("R01", "Exact Phase 5 parent and isolated Phase 5.5 branch", ["V01"]),
        ("R02", "Merged Hugging Face revision and exact change audit", ["V02","V03","V04"]),
        ("R03", "Current-revision target population rebuilt without row loss", ["V05","V06","V07"]),
        ("R04", "Five within-population LOO threshold analyses", ["V08"]),
        ("R05", "Disjoint cross-population transfer tests", ["V09"]),
        ("R06", "Simulation-level bootstrap uncertainty", ["V10"]),
        ("R07", "At least twenty explanatory figures", ["V11"]),
        ("R08", "Original dirty checkout protected", ["V12"]),
        ("R09", "No modelling, relabelling, acquisition, or level-set expansion", ["V13"]),
    ]
    lookup = validation.set_index("check_id")["status"].to_dict()
    return pd.DataFrame([{"requirement_id":rid,"requirement":text,"status":"PASS" if all(lookup[c]=="PASS" for c in checks) else "FAIL","validation_checks":";".join(checks)} for rid,text,checks in items])


def results_markdown(summary: dict[str, Any], scorecard: pd.DataFrame, decisions: pd.DataFrame) -> str:
    g3 = scorecard[scorecard["candidate_id"].eq("G3")].iloc[0]
    ordered = decisions.sort_values("worst_transfer_balanced_accuracy", ascending=False)
    lines = [
        "# Week 7 Phase 5.5 — G3 robustness and transfer stress test", "",
        "## Evidence boundary", "",
        f"Phase 5.5 starts from exact Phase 5 commit `{PHASE5_COMMIT_SHA}` and analyses the current merged `sph_v2` revision `{CURRENT_REVISION}`. The Git-tree audit found exactly 110 additions: 55 `time.dat` and 55 `kinetic-energy_melt.dat`, all in old-data-local. No label, new-data, position-bounds, or iteration path changed.", "",
        "The 55 affected targets were re-extracted with the unchanged corrected Phase 2 definitions. The other 352 rows were reused only because their scientific inputs are unchanged in the exact revision diff. All 407 simulations remain present; two are explicitly physical-target-ineligible.", "",
        "## Current usable population", "",
        f"- new-data: **{summary['readiness']['new-data']['physical_target_ready_count']}/165**", f"- old-data-local: **{summary['readiness']['old-data-local']['physical_target_ready_count']}/179**", f"- old-data-remote-clean: **{summary['readiness']['old-data-remote-clean']['physical_target_ready_count']}/63**", f"- all old: **{summary['readiness']['all-old']['physical_target_ready_count']}/242**", f"- all combined: **{summary['readiness']['all-combined']['physical_target_ready_count']}/407**", "",
        "## Transfer result", "",
        f"G3 mean within-population LOO balanced accuracy is **{g3['mean_within_population_loo_balanced_accuracy']:.4f}**. Its mean held-out cross-population transfer balanced accuracy is **{g3['mean_cross_population_transfer_balanced_accuracy']:.4f}**, and its worst predeclared transfer result is **{g3['minimum_cross_population_transfer_balanced_accuracy']:.4f}**. Descriptive threshold directions agree across populations at **{g3['descriptive_direction_agreement_fraction']:.3f}**.", "",
        "Candidate stress-test ordering (worst transfer balanced accuracy):", "",
    ]
    for row in ordered.itertuples(index=False):
        lines.append(f"- `{row.candidate_id}`: {row.worst_transfer_balanced_accuracy:.4f} — {row.decision}")
    lines += ["", "## Scientific interpretation", "", "G3 is evaluated as a continuous physical companion to the manual morphology label. A stable threshold does not retroactively define the label, and a partition-sensitive threshold is not silently promoted to a universal boundary. The Phase 6 recommendation therefore retains the unchanged binary `has_keyhole` reference and, if separately approved, compares it with continuous G3 under an explicit modelling protocol.", "", "## Hard stop", "", "No classifier, Gaussian process, regression surrogate, active learning, acquisition, level-set estimation, relabelling, or new target definition was performed. Phase 5.5 is intentionally left uncommitted and unpushed.", ""]
    return "\n".join(lines)


def run_analysis(*, smoke: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    resamples = SMOKE_BOOTSTRAP_RESAMPLES if smoke else FULL_BOOTSTRAP_RESAMPLES
    preflight = git_preflight()
    inputs = load_inputs()
    hf_audit, changed_paths = audit_hf_changes(inputs["registry"])
    targets, current_plan, refresh_audit = refresh_targets(inputs, changed_paths)
    population = build_population(targets, inputs["sequences"], inputs["registry"])
    readiness, labels, availability = readiness_tables(population)
    groups = group_descriptives(population)
    separation = separation_tables(population)
    within, within_folds, stability = within_population_thresholds(population)
    transfer, transfer_details = cross_population_transfer(population)
    margins = threshold_margin_diagnostics(population, within)
    bootstrap = bootstrap_uncertainty(population, within_folds, transfer, transfer_details, resamples=resamples)
    persistence = pd.concat([
        subgroup_table(population, "keyhole_persistence_group", "transient_persistent"),
        subgroup_table(population, "repeated_episode_group", "repeated_episode"),
    ], ignore_index=True)
    timing = subgroup_table(population, "keyhole_timing_group", "T0_timing")
    process_map = process_map_summary(population)
    hard_cases = hard_case_linkage(population, inputs["phase4_hard_cases"], inputs["phase5_discordant"], within_folds)
    scorecard, decisions, recommendation = scorecard_tables(separation, within, stability, transfer, availability, persistence)
    figures = generate_figures(destination, population, readiness, labels, within, transfer, stability, margins, scorecard)

    write_json(destination / "phase55_preflight.json", preflight)
    write_json(destination / "input_provenance.json", input_provenance(preflight, hf_audit))
    write_json(destination / "hf_change_audit.json", hf_audit)
    write_csv(destination / "hf_changed_paths.csv", changed_paths)
    write_csv(destination / "current_revision_monitor_source_plan.csv", current_plan)
    write_csv(destination / "current_revision_target_refresh_audit.csv", refresh_audit)
    write_csv(destination / "current_revision_simulation_level_targets.csv", targets)
    targets.to_parquet(destination / "current_revision_simulation_level_targets.parquet", index=False, compression="zstd")
    write_csv(destination / "physical_proxy_population_reference.csv", population)
    write_csv(destination / "population_readiness_by_partition.csv", readiness)
    write_csv(destination / "label_composition_by_partition.csv", labels)
    write_csv(destination / "candidate_availability_by_partition.csv", availability)
    write_csv(destination / "candidate_group_descriptives_by_partition.csv", groups)
    write_csv(destination / "candidate_univariate_separation_by_partition.csv", separation)
    write_csv(destination / "threshold_within_population_summary.csv", within)
    write_csv(destination / "threshold_within_population_fold_details.csv", within_folds)
    write_csv(destination / "threshold_cross_population_transfer_summary.csv", transfer)
    write_csv(destination / "threshold_cross_population_fold_details.csv", transfer_details)
    write_csv(destination / "threshold_stability_summary.csv", stability)
    write_csv(destination / "threshold_margin_diagnostics.csv", margins)
    write_csv(destination / "proxy_bootstrap_uncertainty_summary.csv", bootstrap)
    write_csv(destination / "subgroup_transient_persistent_summary.csv", persistence)
    write_csv(destination / "subgroup_t0_timing_summary.csv", timing)
    write_csv(destination / "process_map_partition_summary.csv", process_map)
    write_csv(destination / "phase4_phase5_hard_case_transfer_context.csv", hard_cases)
    write_csv(destination / "phase55_boundary_formulation_recommendation.csv", recommendation)
    write_csv(destination / "g3_vs_r3_vs_max_vs_t0_transfer_decision.csv", decisions)
    write_csv(destination / "phase55_scorecard.csv", scorecard)
    write_csv(destination / "figure_manifest.csv", figures)

    readiness_lookup = readiness.set_index("population").to_dict(orient="index")
    summary = {
        "phase": "Week 7 Phase 5.5", "mode": "smoke" if smoke else "full",
        "phase5_parent": PHASE5_COMMIT_SHA, "phase55_branch": PHASE55_BRANCH,
        "dataset_repository": DATASET_REPO_ID, "pinned_revision": PINNED_REVISION,
        "analysis_revision": CURRENT_REVISION, "hf_change_audit": hf_audit,
        "readiness": readiness_lookup, "bootstrap_resamples": resamples,
        "analysis_populations": ANALYSIS_POPULATIONS, "transfer_routes": [route[2] for route in TRANSFER_ROUTES],
        "top_scorecard_candidate": str(scorecard.iloc[0]["candidate_id"]),
        "g3_scorecard": scorecard[scorecard["candidate_id"].eq("G3")].iloc[0].to_dict(),
        "recommendation": recommendation.iloc[0].to_dict(),
        "scope": preflight["scope"], "runtime_seconds": time.perf_counter() - started,
    }
    validation = core_validation(preflight, hf_audit, targets, readiness, within, transfer, bootstrap, figures)
    checklist = requirement_checklist(validation)
    summary["validation"] = validation["status"].value_counts().to_dict()
    summary["requirements"] = checklist["status"].value_counts().to_dict()
    write_csv(destination / "validation_results.csv", validation)
    write_csv(destination / "requirement_checklist.csv", checklist)
    write_json(destination / "summary.json", summary)
    (destination / "results_summary.md").write_text(results_markdown(summary, scorecard, decisions), encoding="utf-8")
    write_csv(destination / "output_manifest.csv", output_manifest(destination))
    print(f"Phase 5.5 {'smoke' if smoke else 'full'} complete in {summary['runtime_seconds']:.1f}s; validation={summary['validation']}", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_analysis(smoke=args.smoke)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
