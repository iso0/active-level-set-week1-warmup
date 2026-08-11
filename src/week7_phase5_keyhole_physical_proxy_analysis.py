"""Week 7 Phase 5: manual Keyhole label versus continuous physical proxies.

The analysis is intentionally univariate.  It reuses Ioan's manual frame labels,
the validated Phase 1 experiment semantics, and the corrected Phase 2 scalar
targets.  It does not fit a Keyhole classifier, refit a depth model, perform
active learning, or run a level-set experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

MODULE_ROOT = Path(__file__).resolve().parents[1]

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


ROOT = MODULE_ROOT
OUTPUT_DIR = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
SMOKE_DIR = OUTPUT_DIR / "smoke"
FIGURE_DIR_NAME = "figures"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "05_keyhole_physical_proxy_analysis.ipynb"

PHASE4_COMMIT_SHA = "5b7004017cadc5ecd0eb128f2031f9148ed70900"
PHASE5_BRANCH = "codex/week7-phase5-keyhole-physical-proxy-analysis"
DATASET_REPO_ID = "ioandanielc/sph_v2"
PINNED_DATASET_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"
CURRENT_DATASET_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
DATASET_GIT_URL = f"https://huggingface.co/datasets/{DATASET_REPO_ID}.git"

PHASE1_DIR = ROOT / "outputs" / "week7_01_sph_v2_audit"
PHASE2_DIR = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
PHASE4_DIR = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"

BASE_SEED = 7505
FULL_BOOTSTRAP_RESAMPLES = 5_000
SMOKE_BOOTSTRAP_RESAMPLES = 300
PRIMARY_POPULATION = "new-data"
LABEL_DEFINITION = (
    "has_keyhole: at least one valid saved physical frame was manually labelled Keyhole"
)
IOAN_LABEL_STATEMENT = (
    "I did it by hand. So almost qualitatively. Usually the existence of cavities "
    "directly under the meltpool determined my decision for keyhole."
)

CANDIDATES: list[dict[str, Any]] = [
    {
        "candidate_id": "T0_depth",
        "candidate_name": "T0 penetration depth",
        "value_column": "T0_depth_um",
        "unit": "um",
        "definition": "Median penetration depth in the unchanged Phase 2 T0 window.",
        "source": "corrected Phase 2 T0_depth_um",
        "physical_interpretability": "high",
        "role": "primary late-active depth baseline",
    },
    {
        "candidate_id": "max_depth",
        "candidate_name": "Maximum penetration depth",
        "value_column": "max_depth_um",
        "unit": "um",
        "definition": "Maximum valid penetration depth over the complete observed monitor track.",
        "source": "corrected Phase 2 max_depth_um",
        "physical_interpretability": "high_with_spike_caveat",
        "role": "spike-sensitive depth diagnostic",
    },
    {
        "candidate_id": "G3",
        "candidate_name": "G3 persistent depth",
        "value_column": "G3_persistent_depth_um",
        "unit": "um",
        "definition": "Maximum trailing 50 um rolling-median depth in the validated active interior.",
        "source": "corrected Phase 2 G3_persistent_depth_um; unchanged Week 6 G3 definition",
        "physical_interpretability": "high",
        "role": "predefined persistent-depth candidate",
    },
    {
        "candidate_id": "R3",
        "candidate_name": "R3 persistent aspect ratio",
        "value_column": "R3_persistent_depth_width_ratio",
        "unit": "dimensionless",
        "definition": "Maximum trailing 50 um rolling-median depth/width ratio in the validated active interior.",
        "source": "corrected Phase 2 R3_persistent_depth_width_ratio; unchanged Week 6 R3 definition",
        "physical_interpretability": "high_with_ratio_caveat",
        "role": "predefined persistent geometry candidate",
    },
    {
        "candidate_id": "T0_width",
        "candidate_name": "T0 width",
        "value_column": "T0_width_um",
        "unit": "um",
        "definition": "Median transverse melt-pool width in the unchanged Phase 2 T0 window.",
        "source": "corrected Phase 2 T0_width_um",
        "physical_interpretability": "high",
        "role": "late-active geometry diagnostic",
    },
    {
        "candidate_id": "T0_total_height",
        "candidate_name": "T0 total height",
        "value_column": "T0_total_height_um",
        "unit": "um",
        "definition": "Median total vertical melt height in the unchanged Phase 2 T0 window.",
        "source": "corrected Phase 2 T0_total_height_um",
        "physical_interpretability": "moderate",
        "role": "late-active geometry diagnostic",
    },
    {
        "candidate_id": "T0_kinetic_energy",
        "candidate_name": "T0 kinetic energy",
        "value_column": "T0_kinetic_energy_nJ",
        "unit": "nJ",
        "definition": "Median whole-domain liquid-particle kinetic energy in the unchanged Phase 2 T0 window.",
        "source": "corrected Phase 2 T0_kinetic_energy_nJ",
        "physical_interpretability": "moderate",
        "role": "late-active energetic diagnostic",
    },
    {
        "candidate_id": "R0",
        "candidate_name": "R0 T0 aspect ratio",
        "value_column": "R0_T0_depth_over_width",
        "unit": "dimensionless",
        "definition": "T0 penetration depth divided by T0 width, a predefined Week 6 diagnostic.",
        "source": "predefined Week 6 R0 family, evaluated from corrected Phase 2 T0 depth and width scalars",
        "physical_interpretability": "high_with_ratio_caveat",
        "role": "predefined T0 geometry diagnostic; not introduced after label inspection",
    },
]

MAIN_CANDIDATES = ["T0_depth", "max_depth", "G3", "R3"]
PAIRWISE_COMPARISONS = [
    ("T0_depth", "max_depth"),
    ("T0_depth", "G3"),
    ("T0_depth", "R3"),
    ("max_depth", "G3"),
    ("max_depth", "R3"),
    ("G3", "R3"),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_seed(*parts: Any) -> int:
    token = "|".join(str(part) for part in (BASE_SEED, *parts))
    return int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")


def write_csv(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def git_output(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def git_preflight() -> dict[str, Any]:
    head = git_output("rev-parse", "HEAD")
    branch = git_output("branch", "--show-current")
    require(head == PHASE4_COMMIT_SHA, f"Phase 5 parent drifted: {head}")
    require(branch == PHASE5_BRANCH, f"Unexpected Phase 5 branch: {branch}")
    return {
        "phase5_branch": branch,
        "phase5_parent_sha": head,
        "working_tree_status_at_preflight": git_output("status", "--short"),
        "checked_at_utc": utc_now(),
    }


def audit_current_dataset_revision(registry: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    remote = git_output("ls-remote", DATASET_GIT_URL, "refs/heads/main")
    remote_sha = remote.split()[0] if remote else ""
    require(remote_sha == CURRENT_DATASET_REVISION, f"Hugging Face main drifted: {remote_sha}")

    with tempfile.TemporaryDirectory(prefix="week7-phase5-hf-audit-") as temp_name:
        bare = Path(temp_name) / "repo.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(bare), "remote", "add", "origin", DATASET_GIT_URL],
            check=True,
            capture_output=True,
        )
        for revision in (PINNED_DATASET_REVISION, CURRENT_DATASET_REVISION):
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(bare),
                    "-c",
                    "protocol.version=2",
                    "fetch",
                    "--no-tags",
                    "--filter=blob:none",
                    "origin",
                    revision,
                ],
                check=True,
                capture_output=True,
            )
        diff_text = subprocess.run(
            [
                "git",
                "-C",
                str(bare),
                "diff",
                "--name-status",
                PINNED_DATASET_REVISION,
                CURRENT_DATASET_REVISION,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        commit_subject = subprocess.run(
            ["git", "-C", str(bare), "show", "-s", "--format=%s", CURRENT_DATASET_REVISION],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    partition_map = registry.set_index("experiment_name")["partition"].to_dict()
    rows: list[dict[str, Any]] = []
    for line in diff_text.splitlines():
        if not line.strip():
            continue
        status, relative_path = line.split("\t", 1)
        parts = relative_path.split("/")
        experiment_name = parts[0]
        file_name = parts[-1]
        rows.append(
            {
                "status": status,
                "relative_path": relative_path,
                "experiment_name": experiment_name,
                "file_name": file_name,
                "registry_partition": partition_map.get(experiment_name, "unmapped"),
                "accepted_restoration_file": status == "A"
                and file_name in {"time.dat", "kinetic-energy_melt.dat"},
                "touches_new_data": partition_map.get(experiment_name) == PRIMARY_POPULATION,
                "touches_label_or_geometry": file_name in {"frames.csv", "position-bounds_melt.dat"},
            }
        )
    audit = pd.DataFrame(rows).sort_values(["experiment_name", "file_name"]).reset_index(drop=True)
    experiment_count = int(audit["experiment_name"].nunique())
    restoration_exact = (
        len(audit) == 110
        and experiment_count == 55
        and set(audit["status"]) == {"A"}
        and set(audit["file_name"]) == {"time.dat", "kinetic-energy_melt.dat"}
        and set(audit["registry_partition"]) == {"old-data-local"}
        and bool(audit["accepted_restoration_file"].all())
        and not bool(audit["touches_new_data"].any())
        and not bool(audit["touches_label_or_geometry"].any())
    )
    require(restoration_exact, "Current sph_v2 diff is not the accepted 55-experiment restoration")
    summary = {
        "dataset_repo_id": DATASET_REPO_ID,
        "pinned_scientific_revision": PINNED_DATASET_REVISION,
        "current_main_revision": remote_sha,
        "current_commit_subject": commit_subject,
        "changed_path_count": int(len(audit)),
        "changed_experiment_count": experiment_count,
        "status_counts": audit["status"].value_counts().sort_index().to_dict(),
        "file_name_counts": audit["file_name"].value_counts().sort_index().to_dict(),
        "partition_counts": audit.groupby("registry_partition")["experiment_name"].nunique().to_dict(),
        "new_data_changed_path_count": int(audit["touches_new_data"].sum()),
        "label_or_geometry_changed_path_count": int(audit["touches_label_or_geometry"].sum()),
        "accepted_old_data_monitor_restoration_only": restoration_exact,
        "new_data_scientific_content_unchanged_by_git_tree_diff": restoration_exact,
        "evidence_boundary": (
            "Git tree comparison proves that every path outside the 55 old-data-local monitor "
            "restorations, including all new-data labels and monitors, retains the pinned blob content."
        ),
        "audited_at_utc": utc_now(),
    }
    return summary, audit


def input_paths() -> dict[str, Path]:
    return {
        "phase1_registry": PHASE1_DIR / "experiment_registry.csv",
        "phase1_label_sequences": PHASE1_DIR / "experiment_label_sequences.csv",
        "phase1_structure": PHASE1_DIR / "experiment_structure_summary.csv",
        "phase2_targets": PHASE2_DIR / "sph_v2_simulation_level_targets.csv",
        "phase2_depth_ambiguity": PHASE2_DIR / "flagged_depth_ambiguity.csv",
        "phase4_hard_cases": PHASE4_DIR / "depth_consensus_hard_cases.csv",
    }


def load_inputs() -> dict[str, pd.DataFrame]:
    paths = input_paths()
    for name, path in paths.items():
        require(path.exists(), f"Missing required {name}: {path}")
    return {name: pd.read_csv(path) for name, path in paths.items()}


def build_population(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    targets = tables["phase2_targets"].query("partition == @PRIMARY_POPULATION").copy()
    labels = tables["phase1_label_sequences"].query("partition == @PRIMARY_POPULATION").copy()
    registry = tables["phase1_registry"].query("partition == @PRIMARY_POPULATION").copy()
    structure = tables["phase1_structure"].query("partition == @PRIMARY_POPULATION").copy()
    for name, frame in {
        "targets": targets,
        "labels": labels,
        "registry": registry,
        "structure": structure,
    }.items():
        require(len(frame) == 165, f"{name} new-data population is {len(frame)}, expected 165")
        require(frame["experiment_name"].is_unique, f"{name} experiment names are not unique")

    label_columns = [
        "experiment_name",
        "labelled_frame_count",
        "distinct_label_count",
        "label_change_count",
        "collapsed_label_sequence",
        "collapsed_physical_sequence",
        "first_physical_label",
        "last_physical_label",
        "has_conduction",
        "has_keyhole",
        "first_conduction_frame_index",
        "first_conduction_timestep",
        "first_keyhole_frame_index",
        "first_keyhole_timestep",
        "last_keyhole_frame_index",
        "last_keyhole_timestep",
        "keyhole_frame_count",
        "relevant_physical_frame_count",
        "keyhole_fraction_of_relevant_physical_frames",
        "keyhole_segment_count",
        "maximum_keyhole_segment_frames",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
        "label_sequence_sha256",
    ]
    labels = labels[label_columns].rename(
        columns={
            "has_keyhole": "has_keyhole_phase1",
            "has_conduction": "has_conduction_phase1",
            "keyhole_frame_count": "keyhole_frame_count_phase1",
            "first_keyhole_timestep": "first_keyhole_timestep_phase1",
        }
    )
    registry_columns = [
        "experiment_name",
        "parameters_sha256",
        "frames_csv_sha256",
        "frames_csv_path",
    ]
    structure_columns = ["experiment_name", "side_png_count", "gif_count"]
    population = targets.merge(labels, on="experiment_name", how="left", validate="one_to_one")
    population = population.merge(
        registry[registry_columns], on="experiment_name", how="left", validate="one_to_one"
    )
    population = population.merge(
        structure[structure_columns], on="experiment_name", how="left", validate="one_to_one"
    )
    require(len(population) == 165, "Population merge silently changed row count")
    require(population["frames_csv_sha256"].notna().all(), "A new-data label hash is missing")

    for column in [
        "has_keyhole",
        "has_keyhole_phase1",
        "has_conduction",
        "has_conduction_phase1",
        "physical_target_extraction_success",
        "geometry_target_ready",
        "kinetic_energy_target_ready",
        "source_label_modified",
        "simulation_silently_removed",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
    ]:
        population[column] = bool_series(population[column])
    require(
        population["has_keyhole"].equals(population["has_keyhole_phase1"]),
        "Phase 2 has_keyhole disagrees with validated Phase 1 semantics",
    )
    require(
        population["has_conduction"].equals(population["has_conduction_phase1"]),
        "Phase 2 has_conduction disagrees with validated Phase 1 semantics",
    )
    population["has_conduction"] = population["has_conduction_phase1"]
    require(not population["source_label_modified"].any(), "A source label was modified")
    require(not population["simulation_silently_removed"].any(), "A simulation was silently removed")
    require(
        population["keyhole_frame_count"].fillna(-1).astype(int).equals(
            population["keyhole_frame_count_phase1"].fillna(-1).astype(int)
        ),
        "Phase 1/2 Keyhole frame counts disagree",
    )

    population["R0_T0_depth_over_width"] = np.where(
        pd.to_numeric(population["T0_width_um"], errors="coerce") > 0,
        pd.to_numeric(population["T0_depth_um"], errors="coerce")
        / pd.to_numeric(population["T0_width_um"], errors="coerce"),
        np.nan,
    )
    base_geometry_ready = population["physical_target_extraction_success"] & population[
        "geometry_target_ready"
    ]
    for spec in CANDIDATES:
        value = pd.to_numeric(population[spec["value_column"]], errors="coerce")
        ready = base_geometry_ready & np.isfinite(value)
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
    population["keyhole_timing_group"] = np.where(
        population["has_keyhole"], population["keyhole_timing_relative_to_T0"], "no_Keyhole"
    )
    return population.sort_values("experiment_name").reset_index(drop=True)


def population_reference(population: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "experiment_name",
        "partition",
        "exact_sph_v2_revision",
        "P_W",
        "VX_m_per_s",
        "LS_um",
        "ST_K",
        "has_conduction",
        "has_keyhole",
        "keyhole_frame_count",
        "keyhole_segment_count",
        "keyhole_timing_relative_to_T0",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
        "keyhole_persistence_group",
        "physical_target_extraction_success",
        "extraction_status",
        "extraction_failure_reasons",
        "geometry_target_ready",
        "kinetic_energy_target_ready",
        "source_label_modified",
        "simulation_silently_removed",
        "parameters_sha256",
        "frames_csv_sha256",
        "frames_csv_path",
        "side_png_count",
        "gif_count",
    ]
    for spec in CANDIDATES:
        columns.extend([f"ready__{spec['candidate_id']}", f"value__{spec['candidate_id']}"])
    return population[columns].copy()


def candidate_definitions(population: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spec in CANDIDATES:
        ready = population[f"ready__{spec['candidate_id']}"]
        rows.append(
            {
                **spec,
                "primary_population_total": int(len(population)),
                "ready_n": int(ready.sum()),
                "missing_n": int((~ready).sum()),
                "readiness_fraction": float(ready.mean()),
                "readiness_rule": (
                    "physical_target_extraction_success AND geometry_target_ready AND finite exact source scalar"
                    + (
                        " AND kinetic_energy_target_ready"
                        if spec["candidate_id"] == "T0_kinetic_energy"
                        else ""
                    )
                ),
                "higher_value_predeclared_as_more_keyhole_like": True,
                "post_hoc_candidate": False,
            }
        )
    return pd.DataFrame(rows)


def label_audit(population: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "experiment_name",
        "has_keyhole",
        "has_conduction",
        "labelled_frame_count",
        "relevant_physical_frame_count",
        "keyhole_frame_count",
        "keyhole_fraction_of_relevant_physical_frames",
        "keyhole_segment_count",
        "maximum_keyhole_segment_frames",
        "keyhole_transient_by_sequence",
        "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
        "keyhole_timing_relative_to_T0",
        "keyhole_persistence_group",
        "collapsed_physical_sequence",
        "frames_csv_sha256",
        "label_sequence_sha256",
    ]
    result = population[columns].copy()
    result["keyhole_negative_contains_conduction"] = (~result["has_keyhole"]) & result[
        "has_conduction"
    ]
    result["keyhole_negative_without_conduction"] = (~result["has_keyhole"]) & ~result[
        "has_conduction"
    ]
    return result


def rank_biserial(pos: np.ndarray, neg: np.ndarray) -> float:
    if len(pos) == 0 or len(neg) == 0:
        return math.nan
    u = mannwhitneyu(pos, neg, alternative="two-sided", method="auto").statistic
    return float(2.0 * u / (len(pos) * len(neg)) - 1.0)


def bootstrap_distribution_metrics(
    pos: np.ndarray, neg: np.ndarray, *, candidate_id: str, resamples: int
) -> dict[str, float]:
    rng = np.random.default_rng(deterministic_seed("effect", candidate_id, resamples))
    median_diffs = np.empty(resamples, dtype=float)
    effects = np.empty(resamples, dtype=float)
    for index in range(resamples):
        pos_sample = rng.choice(pos, size=len(pos), replace=True)
        neg_sample = rng.choice(neg, size=len(neg), replace=True)
        median_diffs[index] = np.median(pos_sample) - np.median(neg_sample)
        effects[index] = rank_biserial(pos_sample, neg_sample)
    return {
        "median_difference_ci_low": float(np.quantile(median_diffs, 0.025)),
        "median_difference_ci_high": float(np.quantile(median_diffs, 0.975)),
        "rank_biserial_ci_low": float(np.quantile(effects, 0.025)),
        "rank_biserial_ci_high": float(np.quantile(effects, 0.975)),
    }


def group_and_effect_analysis(
    population: pd.DataFrame, *, resamples: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    descriptive_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []
    for spec in CANDIDATES:
        candidate_id = spec["candidate_id"]
        subset = population.loc[
            population[f"ready__{candidate_id}"], ["has_keyhole", f"value__{candidate_id}"]
        ].copy()
        subset = subset.rename(columns={f"value__{candidate_id}": "value"})
        for label_value, group_name in [(False, "Keyhole-negative"), (True, "Keyhole-positive")]:
            values = subset.loc[subset["has_keyhole"].eq(label_value), "value"].to_numpy(float)
            descriptive_rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": spec["candidate_name"],
                    "unit": spec["unit"],
                    "group": group_name,
                    "n": int(len(values)),
                    "median": float(np.median(values)),
                    "q25": float(np.quantile(values, 0.25)),
                    "q75": float(np.quantile(values, 0.75)),
                    "mean": float(np.mean(values)),
                    "standard_deviation": float(np.std(values, ddof=1)),
                    "minimum": float(np.min(values)),
                    "maximum": float(np.max(values)),
                }
            )
        pos = subset.loc[subset["has_keyhole"], "value"].to_numpy(float)
        neg = subset.loc[~subset["has_keyhole"], "value"].to_numpy(float)
        test = mannwhitneyu(pos, neg, alternative="two-sided", method="auto")
        median_difference = float(np.median(pos) - np.median(neg))
        effect = rank_biserial(pos, neg)
        intervals = bootstrap_distribution_metrics(
            pos, neg, candidate_id=candidate_id, resamples=resamples
        )
        effect_rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": spec["candidate_name"],
                "unit": spec["unit"],
                "n_keyhole_positive": int(len(pos)),
                "n_keyhole_negative": int(len(neg)),
                "median_difference_keyhole_minus_negative": median_difference,
                **intervals,
                "rank_biserial_effect_size": effect,
                "mann_whitney_u": float(test.statistic),
                "mann_whitney_two_sided_pvalue": float(test.pvalue),
                "bootstrap_resamples": int(resamples),
                "bootstrap_level": 0.95,
                "inference_note": "Effect size and overlap are primary; p-value is secondary.",
            }
        )
    return pd.DataFrame(descriptive_rows), pd.DataFrame(effect_rows)


def stratified_bootstrap_indices(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    return np.concatenate(
        [
            rng.choice(positive, size=len(positive), replace=True),
            rng.choice(negative, size=len(negative), replace=True),
        ]
    )


def separation_analysis(population: pd.DataFrame, *, resamples: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in CANDIDATES:
        candidate_id = spec["candidate_id"]
        subset = population.loc[
            population[f"ready__{candidate_id}"], ["has_keyhole", f"value__{candidate_id}"]
        ]
        y = subset["has_keyhole"].astype(int).to_numpy()
        x = subset[f"value__{candidate_id}"].to_numpy(float)
        raw_auc = float(roc_auc_score(y, x))
        direction = "higher_is_more_keyhole_like" if raw_auc >= 0.5 else "lower_is_more_keyhole_like"
        sign = 1.0 if raw_auc >= 0.5 else -1.0
        adjusted_x = sign * x
        adjusted_auc = float(roc_auc_score(y, adjusted_x))
        raw_ap = float(average_precision_score(y, x))
        adjusted_ap = float(average_precision_score(y, adjusted_x))
        rng = np.random.default_rng(deterministic_seed("separation", candidate_id, resamples))
        raw_auc_boot = np.empty(resamples)
        adjusted_auc_boot = np.empty(resamples)
        raw_ap_boot = np.empty(resamples)
        adjusted_ap_boot = np.empty(resamples)
        for index in range(resamples):
            sampled = stratified_bootstrap_indices(y, rng)
            raw_auc_boot[index] = roc_auc_score(y[sampled], x[sampled])
            adjusted_auc_boot[index] = roc_auc_score(y[sampled], adjusted_x[sampled])
            raw_ap_boot[index] = average_precision_score(y[sampled], x[sampled])
            adjusted_ap_boot[index] = average_precision_score(y[sampled], adjusted_x[sampled])
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": spec["candidate_name"],
                "unit": spec["unit"],
                "n": int(len(y)),
                "keyhole_positive_n": int(y.sum()),
                "keyhole_negative_n": int((1 - y).sum()),
                "keyhole_prevalence": float(y.mean()),
                "physical_direction": direction,
                "raw_roc_auc_higher_value_positive": raw_auc,
                "raw_roc_auc_ci_low": float(np.quantile(raw_auc_boot, 0.025)),
                "raw_roc_auc_ci_high": float(np.quantile(raw_auc_boot, 0.975)),
                "direction_adjusted_roc_auc": adjusted_auc,
                "direction_adjusted_roc_auc_ci_low": float(
                    np.quantile(adjusted_auc_boot, 0.025)
                ),
                "direction_adjusted_roc_auc_ci_high": float(
                    np.quantile(adjusted_auc_boot, 0.975)
                ),
                "raw_average_precision_higher_value_positive": raw_ap,
                "raw_average_precision_ci_low": float(np.quantile(raw_ap_boot, 0.025)),
                "raw_average_precision_ci_high": float(np.quantile(raw_ap_boot, 0.975)),
                "direction_adjusted_average_precision": adjusted_ap,
                "direction_adjusted_average_precision_ci_low": float(
                    np.quantile(adjusted_ap_boot, 0.025)
                ),
                "direction_adjusted_average_precision_ci_high": float(
                    np.quantile(adjusted_ap_boot, 0.975)
                ),
                "bootstrap_resamples": int(resamples),
                "bootstrap_unit": "simulation",
                "class_imbalance_baseline_average_precision": float(y.mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["direction_adjusted_roc_auc", "direction_adjusted_average_precision"],
        ascending=False,
    ).reset_index(drop=True)


def paired_auc_analysis(population: pd.DataFrame, *, resamples: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for baseline, comparator in PAIRWISE_COMPARISONS:
        valid = population[f"ready__{baseline}"] & population[f"ready__{comparator}"]
        subset = population.loc[
            valid,
            ["has_keyhole", f"value__{baseline}", f"value__{comparator}"],
        ]
        y = subset["has_keyhole"].astype(int).to_numpy()
        x_a = subset[f"value__{baseline}"].to_numpy(float)
        x_b = subset[f"value__{comparator}"].to_numpy(float)
        raw_a = float(roc_auc_score(y, x_a))
        raw_b = float(roc_auc_score(y, x_b))
        sign_a = 1.0 if raw_a >= 0.5 else -1.0
        sign_b = 1.0 if raw_b >= 0.5 else -1.0
        auc_a = float(roc_auc_score(y, sign_a * x_a))
        auc_b = float(roc_auc_score(y, sign_b * x_b))
        delta = auc_b - auc_a
        rng = np.random.default_rng(
            deterministic_seed("paired", baseline, comparator, resamples)
        )
        deltas = np.empty(resamples)
        for index in range(resamples):
            sampled = stratified_bootstrap_indices(y, rng)
            deltas[index] = roc_auc_score(y[sampled], sign_b * x_b[sampled]) - roc_auc_score(
                y[sampled], sign_a * x_a[sampled]
            )
        ci_low = float(np.quantile(deltas, 0.025))
        ci_high = float(np.quantile(deltas, 0.975))
        rows.append(
            {
                "baseline_candidate": baseline,
                "comparator_candidate": comparator,
                "common_complete_n": int(len(y)),
                "keyhole_positive_n": int(y.sum()),
                "keyhole_negative_n": int((1 - y).sum()),
                "baseline_direction_adjusted_roc_auc": auc_a,
                "comparator_direction_adjusted_roc_auc": auc_b,
                "delta_roc_auc_comparator_minus_baseline": delta,
                "delta_roc_auc_ci_low": ci_low,
                "delta_roc_auc_ci_high": ci_high,
                "material_improvement_predeclared_rule": "point delta >= 0.02 and 95% CI lower bound > 0",
                "material_improvement": bool(delta >= 0.02 and ci_low > 0),
                "paired_stratified_bootstrap": True,
                "bootstrap_unit": "simulation",
                "bootstrap_resamples": int(resamples),
            }
        )
    return pd.DataFrame(rows)


def threshold_candidates(values: np.ndarray) -> np.ndarray:
    unique = np.unique(np.asarray(values, dtype=float))
    if len(unique) == 1:
        scale = max(abs(float(unique[0])), 1.0)
        return np.array([unique[0] - scale * 1e-12, unique[0] + scale * 1e-12])
    middle = (unique[:-1] + unique[1:]) / 2.0
    scale = max(float(np.ptp(unique)), float(np.max(np.abs(unique))), 1.0)
    epsilon = scale * 1e-12
    return np.concatenate([[unique[0] - epsilon], middle, [unique[-1] + epsilon]])


def choose_threshold(values: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    thresholds = threshold_candidates(values)
    candidates: list[dict[str, Any]] = []
    value_scale = max(float(np.std(values)), 1e-12)
    value_median = float(np.median(values))
    for direction in ("higher", "lower"):
        predictions = (
            values[:, None] >= thresholds[None, :]
            if direction == "higher"
            else values[:, None] <= thresholds[None, :]
        )
        positives = labels == 1
        negatives = labels == 0
        sensitivity = predictions[positives].mean(axis=0)
        specificity = (~predictions[negatives]).mean(axis=0)
        accuracy = (predictions == labels[:, None]).mean(axis=0)
        balanced = (sensitivity + specificity) / 2.0
        for index, threshold in enumerate(thresholds):
            candidates.append(
                {
                    "threshold": float(threshold),
                    "direction": direction,
                    "balanced_accuracy": float(balanced[index]),
                    "sensitivity": float(sensitivity[index]),
                    "specificity": float(specificity[index]),
                    "minimum_class_recall": float(min(sensitivity[index], specificity[index])),
                    "accuracy": float(accuracy[index]),
                    "standardized_distance_from_training_median": float(
                        abs(threshold - value_median) / value_scale
                    ),
                }
            )
    ranked = pd.DataFrame(candidates).sort_values(
        [
            "balanced_accuracy",
            "minimum_class_recall",
            "accuracy",
            "standardized_distance_from_training_median",
            "direction",
            "threshold",
        ],
        ascending=[False, False, False, True, True, True],
        kind="mergesort",
    )
    return ranked.iloc[0].to_dict()


def threshold_cv_analysis(
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []
    for spec in CANDIDATES:
        candidate_id = spec["candidate_id"]
        subset = population.loc[
            population[f"ready__{candidate_id}"],
            ["experiment_name", "has_keyhole", f"value__{candidate_id}"],
        ].reset_index(drop=True)
        y = subset["has_keyhole"].astype(int).to_numpy()
        x = subset[f"value__{candidate_id}"].to_numpy(float)
        for holdout in range(len(subset)):
            train_mask = np.ones(len(subset), dtype=bool)
            train_mask[holdout] = False
            selected = choose_threshold(x[train_mask], y[train_mask])
            threshold = float(selected["threshold"])
            direction = str(selected["direction"])
            prediction = int(x[holdout] >= threshold if direction == "higher" else x[holdout] <= threshold)
            margin = float(x[holdout] - threshold if direction == "higher" else threshold - x[holdout])
            fold_rows.append(
                {
                    "candidate_id": candidate_id,
                    "fold_id": holdout + 1,
                    "held_out_experiment_name": subset.loc[holdout, "experiment_name"],
                    "training_n": int(train_mask.sum()),
                    "held_out_value": float(x[holdout]),
                    "held_out_has_keyhole": int(y[holdout]),
                    "training_selected_direction": direction,
                    "training_selected_threshold": threshold,
                    "training_balanced_accuracy": float(selected["balanced_accuracy"]),
                    "training_sensitivity": float(selected["sensitivity"]),
                    "training_specificity": float(selected["specificity"]),
                    "held_out_prediction": prediction,
                    "held_out_correct": bool(prediction == y[holdout]),
                    "held_out_signed_margin": margin,
                    "prediction_semantics": "1=Keyhole-positive",
                    "leakage_guard": "threshold and direction selected without held-out simulation",
                }
            )
        candidate_folds = pd.DataFrame(
            [row for row in fold_rows if row["candidate_id"] == candidate_id]
        )
        true = candidate_folds["held_out_has_keyhole"].to_numpy(int)
        predicted = candidate_folds["held_out_prediction"].to_numpy(int)
        tn, fp, fn, tp = confusion_matrix(true, predicted, labels=[0, 1]).ravel()
        full_threshold = choose_threshold(x, y)
        summary_rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": spec["candidate_name"],
                "unit": spec["unit"],
                "cv_scheme": "exact_leave_one_simulation_out",
                "cv_n": int(len(true)),
                "balanced_accuracy": float(balanced_accuracy_score(true, predicted)),
                "sensitivity_keyhole_recall": float(recall_score(true, predicted, zero_division=0)),
                "specificity": float(tn / (tn + fp)),
                "precision": float(precision_score(true, predicted, zero_division=0)),
                "f1": float(f1_score(true, predicted, zero_division=0)),
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
                "full_data_descriptive_direction": full_threshold["direction"],
                "full_data_descriptive_threshold": float(full_threshold["threshold"]),
                "full_data_descriptive_balanced_accuracy": float(
                    full_threshold["balanced_accuracy"]
                ),
                "full_data_threshold_is_predictive_performance": False,
            }
        )
        thresholds = candidate_folds["training_selected_threshold"].to_numpy(float)
        directions = candidate_folds["training_selected_direction"]
        q25, median, q75 = np.quantile(thresholds, [0.25, 0.5, 0.75])
        value_iqr = float(np.quantile(x, 0.75) - np.quantile(x, 0.25))
        normalized_iqr = float((q75 - q25) / value_iqr) if value_iqr > 0 else math.nan
        majority_direction_fraction = float(directions.value_counts(normalize=True).iloc[0])
        stability_rows.append(
            {
                "candidate_id": candidate_id,
                "unit": spec["unit"],
                "fold_n": int(len(thresholds)),
                "majority_direction": directions.mode().iloc[0],
                "majority_direction_fraction": majority_direction_fraction,
                "threshold_minimum": float(np.min(thresholds)),
                "threshold_q25": float(q25),
                "threshold_median": float(median),
                "threshold_q75": float(q75),
                "threshold_maximum": float(np.max(thresholds)),
                "threshold_iqr": float(q75 - q25),
                "candidate_value_iqr": value_iqr,
                "threshold_iqr_over_candidate_iqr": normalized_iqr,
                "threshold_unique_count": int(pd.Series(thresholds).nunique()),
                "stability_class": (
                    "stable"
                    if majority_direction_fraction >= 0.95 and normalized_iqr <= 0.50
                    else "moderately_stable"
                    if majority_direction_fraction >= 0.90 and normalized_iqr <= 1.00
                    else "unstable"
                ),
                "stability_rule": (
                    "stable: direction>=0.95 and threshold IQR/value IQR<=0.50; "
                    "moderate: direction>=0.90 and ratio<=1.00"
                ),
            }
        )
    return (
        pd.DataFrame(summary_rows).sort_values("balanced_accuracy", ascending=False),
        pd.DataFrame(fold_rows),
        pd.DataFrame(stability_rows),
    )


def subgroup_analysis(
    population: pd.DataFrame,
    fold_predictions: pd.DataFrame,
    *,
    group_column: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base_columns = ["experiment_name", "has_keyhole", group_column]
    for spec in CANDIDATES:
        candidate_id = spec["candidate_id"]
        folds = fold_predictions.query("candidate_id == @candidate_id").merge(
            population[base_columns],
            left_on="held_out_experiment_name",
            right_on="experiment_name",
            how="left",
            validate="one_to_one",
        )
        for group, frame in folds.groupby(group_column, dropna=False, sort=True):
            values = frame["held_out_value"].to_numpy(float)
            positives = frame["held_out_has_keyhole"].eq(1)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": spec["candidate_name"],
                    "unit": spec["unit"],
                    "grouping": group_column,
                    "group": str(group),
                    "n": int(len(frame)),
                    "keyhole_positive_n": int(positives.sum()),
                    "median": float(np.median(values)),
                    "q25": float(np.quantile(values, 0.25)),
                    "q75": float(np.quantile(values, 0.75)),
                    "mean": float(np.mean(values)),
                    "cv_predicted_keyhole_fraction": float(frame["held_out_prediction"].mean()),
                    "cv_sensitivity_within_positive_group": (
                        float(frame.loc[positives, "held_out_prediction"].mean())
                        if positives.any()
                        else math.nan
                    ),
                    "cv_false_positive_rate_within_negative_group": (
                        float(frame.loc[~positives, "held_out_prediction"].mean())
                        if (~positives).any()
                        else math.nan
                    ),
                    "definitions_reused": True,
                }
            )
    return pd.DataFrame(rows)


def candidate_correlations(population: pd.DataFrame) -> pd.DataFrame:
    ready = np.logical_and.reduce(
        [population[f"ready__{spec['candidate_id']}"] for spec in CANDIDATES]
    )
    columns = [f"value__{spec['candidate_id']}" for spec in CANDIDATES]
    common = population.loc[ready, columns].copy()
    common.columns = [spec["candidate_id"] for spec in CANDIDATES]
    rows: list[dict[str, Any]] = []
    for left in common.columns:
        for right in common.columns:
            result = spearmanr(common[left], common[right])
            rows.append(
                {
                    "candidate_left": left,
                    "candidate_right": right,
                    "common_complete_n": int(len(common)),
                    "spearman_rho": float(result.statistic),
                    "two_sided_pvalue": float(result.pvalue),
                    "descriptive_only": True,
                }
            )
    return pd.DataFrame(rows)


def subgroup_sensitivity(
    folds: pd.DataFrame, population: pd.DataFrame, candidate_id: str, group: str
) -> float:
    merged = folds.query("candidate_id == @candidate_id").merge(
        population[["experiment_name", "keyhole_persistence_group"]],
        left_on="held_out_experiment_name",
        right_on="experiment_name",
        how="left",
        validate="one_to_one",
    )
    selected = merged["keyhole_persistence_group"].eq(group)
    if not selected.any():
        return math.nan
    return float(merged.loc[selected, "held_out_prediction"].mean())


def score_candidates(
    definitions: pd.DataFrame,
    effects: pd.DataFrame,
    separation: pd.DataFrame,
    cv_summary: pd.DataFrame,
    stability: pd.DataFrame,
    fold_predictions: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    score = definitions.merge(effects, on=["candidate_id", "candidate_name", "unit"])
    score = score.merge(
        separation[
            [
                "candidate_id",
                "direction_adjusted_roc_auc",
                "direction_adjusted_roc_auc_ci_low",
                "direction_adjusted_roc_auc_ci_high",
                "direction_adjusted_average_precision",
                "direction_adjusted_average_precision_ci_low",
                "direction_adjusted_average_precision_ci_high",
            ]
        ],
        on="candidate_id",
    )
    score = score.merge(
        cv_summary[
            [
                "candidate_id",
                "balanced_accuracy",
                "sensitivity_keyhole_recall",
                "specificity",
                "precision",
                "f1",
                "false_positive",
                "false_negative",
            ]
        ],
        on="candidate_id",
    )
    score = score.merge(
        stability[
            [
                "candidate_id",
                "majority_direction_fraction",
                "threshold_iqr_over_candidate_iqr",
                "stability_class",
            ]
        ],
        on="candidate_id",
    )
    score["transient_keyhole_cv_sensitivity"] = score["candidate_id"].map(
        lambda candidate: subgroup_sensitivity(
            fold_predictions, population, candidate, "transient Keyhole"
        )
    )
    score["persistent_keyhole_cv_sensitivity"] = score["candidate_id"].map(
        lambda candidate: subgroup_sensitivity(
            fold_predictions, population, candidate, "persistent Keyhole"
        )
    )

    def classify(row: pd.Series) -> str:
        strong = (
            row["direction_adjusted_roc_auc"] >= 0.85
            and row["direction_adjusted_roc_auc_ci_low"] >= 0.75
            and row["balanced_accuracy"] >= 0.75
            and row["sensitivity_keyhole_recall"] >= 0.65
            and row["specificity"] >= 0.65
            and row["majority_direction_fraction"] >= 0.90
            and row["threshold_iqr_over_candidate_iqr"] <= 0.75
            and row["readiness_fraction"] >= 0.95
            and row["transient_keyhole_cv_sensitivity"] >= 0.65
        )
        moderate = (
            row["direction_adjusted_roc_auc"] >= 0.70
            and row["balanced_accuracy"] >= 0.65
            and row["readiness_fraction"] >= 0.90
        )
        return (
            "STRONG PROXY CANDIDATE"
            if strong
            else "MODERATE PROXY CANDIDATE"
            if moderate
            else "WEAK PROXY CANDIDATE"
        )

    score["proxy_classification"] = score.apply(classify, axis=1)
    score["classification_rule"] = (
        "Strong requires AUC>=0.85, AUC CI low>=0.75, held-out balanced accuracy>=0.75, "
        "sensitivity/specificity>=0.65, direction>=0.90, normalized threshold IQR<=0.75, "
        "readiness>=0.95, and transient sensitivity>=0.65; moderate requires AUC>=0.70, "
        "held-out balanced accuracy>=0.65, readiness>=0.90."
    )
    class_order = {
        "STRONG PROXY CANDIDATE": 0,
        "MODERATE PROXY CANDIDATE": 1,
        "WEAK PROXY CANDIDATE": 2,
    }
    score["_class_order"] = score["proxy_classification"].map(class_order)
    score = score.sort_values(
        ["_class_order", "balanced_accuracy", "direction_adjusted_roc_auc"],
        ascending=[True, False, False],
    ).drop(columns="_class_order")
    score["overall_rank"] = np.arange(1, len(score) + 1)
    score["association_not_causation"] = True
    return score


def discordant_cases(
    population: pd.DataFrame,
    fold_predictions: pd.DataFrame,
    scorecard: pd.DataFrame,
    ambiguity: pd.DataFrame,
) -> pd.DataFrame:
    top_candidates = scorecard.head(3)["candidate_id"].tolist()
    candidate_value_columns = [f"value__{candidate}" for candidate in MAIN_CANDIDATES]
    base_columns = [
        "experiment_name",
        "P_W",
        "VX_m_per_s",
        "LS_um",
        "ST_K",
        "has_keyhole",
        "keyhole_frame_count",
        "keyhole_segment_count",
        "keyhole_timing_relative_to_T0",
        "keyhole_persistence_group",
        "T0_start_row_index",
        "T0_end_row_index",
        "T0_start_time_s",
        "T0_end_time_s",
        "max_depth_um",
        "G3_persistent_depth_um",
        "R3_persistent_depth_width_ratio",
        "flag_primary_window_unstable_week6_rule",
        "flag_depth_bounding_box_ambiguity_candidate",
        "depth_ambiguity_score",
        "side_png_count",
        "gif_count",
        *candidate_value_columns,
    ]
    ambiguity_fields = [
        "experiment_name",
        "gif_path_in_repository",
        "side_frame_path_in_repository",
        "visual_review_status",
        "visual_review_note",
    ]
    available_ambiguity = ambiguity[
        [column for column in ambiguity_fields if column in ambiguity.columns]
    ].copy()
    available_ambiguity = available_ambiguity.drop_duplicates("experiment_name")
    rows: list[pd.DataFrame] = []
    for candidate in top_candidates:
        folds = fold_predictions.query("candidate_id == @candidate").copy()
        folds["error_type"] = np.select(
            [
                folds["held_out_has_keyhole"].eq(1) & folds["held_out_prediction"].eq(0),
                folds["held_out_has_keyhole"].eq(0) & folds["held_out_prediction"].eq(1),
            ],
            ["false_negative", "false_positive"],
            default="correct",
        )
        folds = folds.query("error_type != 'correct'")
        selected_parts = []
        for error_type in ["false_negative", "false_positive"]:
            part = folds.query("error_type == @error_type").sort_values(
                ["held_out_signed_margin", "held_out_experiment_name"], ascending=[True, True]
            )
            selected_parts.append(part.head(3))
        selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else folds.head(0)
        selected["review_candidate"] = candidate
        rows.append(selected)
    if rows:
        review = pd.concat(rows, ignore_index=True)
    else:
        review = pd.DataFrame(columns=list(fold_predictions.columns) + ["error_type", "review_candidate"])
    review = review.merge(
        population[base_columns],
        left_on="held_out_experiment_name",
        right_on="experiment_name",
        how="left",
        validate="many_to_one",
    )
    review = review.merge(
        available_ambiguity, on="experiment_name", how="left", validate="many_to_one"
    )
    review["side_gif_reference"] = review["gif_path_in_repository"].fillna(
        review["experiment_name"].astype(str) + "/gif_files/animation_ss_side.gif"
    )
    review["media_reference_supported_by_phase1_structure"] = review["gif_count"].fillna(0).gt(0)

    def diagnostic(row: pd.Series) -> str:
        if row["error_type"] == "false_negative" and row["keyhole_persistence_group"] == "transient Keyhole":
            return "brief morphology-defined Keyhole missed by scalar threshold"
        if row["error_type"] == "false_positive" and bool(
            row.get("flag_depth_bounding_box_ambiguity_candidate", False)
        ):
            return "possible target-quality/geometry issue; label unchanged"
        if row["error_type"] == "false_positive":
            return "large physical response without manual cavity label"
        if row["error_type"] == "false_negative" and row["keyhole_persistence_group"] == "persistent Keyhole":
            return "persistent morphology label missed by scalar; inconclusive diagnostic"
        return "inconclusive"

    review["diagnostic_review_outcome"] = review.apply(diagnostic, axis=1)
    review["label_changed"] = False
    review["review_is_ground_truth"] = False
    keep = [
        "review_candidate",
        "error_type",
        "experiment_name",
        "P_W",
        "VX_m_per_s",
        "LS_um",
        "ST_K",
        "has_keyhole",
        "held_out_value",
        "training_selected_direction",
        "training_selected_threshold",
        "held_out_prediction",
        "held_out_signed_margin",
        "keyhole_frame_count",
        "keyhole_segment_count",
        "keyhole_timing_relative_to_T0",
        "keyhole_persistence_group",
        "value__T0_depth",
        "value__max_depth",
        "value__G3",
        "value__R3",
        "T0_start_row_index",
        "T0_end_row_index",
        "T0_start_time_s",
        "T0_end_time_s",
        "flag_primary_window_unstable_week6_rule",
        "flag_depth_bounding_box_ambiguity_candidate",
        "depth_ambiguity_score",
        "side_gif_reference",
        "side_frame_path_in_repository",
        "media_reference_supported_by_phase1_structure",
        "visual_review_status",
        "visual_review_note",
        "diagnostic_review_outcome",
        "label_changed",
        "review_is_ground_truth",
    ]
    return review.reindex(columns=keep).sort_values(
        ["review_candidate", "error_type", "held_out_signed_margin", "experiment_name"]
    )


def phase4_hard_case_linkage(
    population: pd.DataFrame,
    hard_cases: pd.DataFrame,
    fold_predictions: pd.DataFrame,
    scorecard: pd.DataFrame,
) -> pd.DataFrame:
    require(hard_cases["experiment_name"].is_unique, "Phase 4 hard cases are not unique")
    columns = [
        "experiment_name",
        "has_keyhole",
        "keyhole_frame_count",
        "keyhole_timing_relative_to_T0",
        "keyhole_persistence_group",
        "value__T0_depth",
        "value__max_depth",
        "value__G3",
        "value__R3",
        "flag_depth_bounding_box_ambiguity_candidate",
    ]
    linked = hard_cases.merge(
        population[columns],
        on="experiment_name",
        how="left",
        validate="one_to_one",
        suffixes=("_phase4", "_phase5"),
    )
    require(linked["value__T0_depth"].notna().all(), "A Phase 4 hard case failed Phase 5 join")
    for candidate in scorecard.head(3)["candidate_id"]:
        folds = fold_predictions.query("candidate_id == @candidate")[[
            "held_out_experiment_name",
            "held_out_prediction",
            "held_out_correct",
            "held_out_signed_margin",
        ]].rename(
            columns={
                "held_out_experiment_name": "experiment_name",
                "held_out_prediction": f"cv_prediction__{candidate}",
                "held_out_correct": f"cv_correct__{candidate}",
                "held_out_signed_margin": f"cv_margin__{candidate}",
            }
        )
        linked = linked.merge(folds, on="experiment_name", how="left", validate="one_to_one")
    linked["any_top3_proxy_cv_discordance"] = linked.filter(regex=r"^cv_correct__").eq(False).any(axis=1)
    linked["phase5_interpretation"] = np.select(
        [
            linked["any_top3_proxy_cv_discordance"],
            linked["has_keyhole_phase5"].astype(bool),
        ],
        [
            "Phase 4 hard case also crosses at least one held-out proxy decision",
            "Phase 4 hard case is a clearly proxy-positive manual Keyhole case",
        ],
        default="Phase 4 hard case is manual Keyhole-negative",
    )
    linked["phase4_models_refit"] = False
    return linked


def target_formulation_decision(scorecard: pd.DataFrame) -> pd.DataFrame:
    top = scorecard.iloc[0]
    strong = top["proxy_classification"] == "STRONG PROXY CANDIDATE"
    robust_transient = top["transient_keyhole_cv_sensitivity"] >= 0.80
    stable = top["stability_class"] == "stable"
    near_complete = top["balanced_accuracy"] >= 0.95
    if strong and robust_transient and stable and near_complete:
        decision = "CONTINUOUS PROXY CANDIDATE"
        rationale = (
            f"{top['candidate_id']} combines strong rank separation, near-complete held-out threshold "
            "performance, stable thresholds, high readiness, and robustness to transient Keyhole."
        )
        phase6_target = (
            f"Carry {top['candidate_id']} as the predefined continuous candidate and compare its "
            "threshold/level-set formulation against the unchanged binary has_keyhole reference."
        )
    elif strong:
        decision = "HYBRID / UNRESOLVED"
        rationale = (
            f"{top['candidate_id']} is strongly informative but an important subgroup or threshold "
            "stability criterion remains unresolved."
        )
        phase6_target = (
            f"Carry both continuous {top['candidate_id']} and binary has_keyhole formulations into a "
            "controlled comparison."
        )
    else:
        decision = "BINARY LABEL PRIMARY"
        rationale = "No single scalar satisfies the predeclared multi-evidence strong-proxy criteria."
        phase6_target = "Use binary has_keyhole probability / latent boundary as the primary target."
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "selected_continuous_candidate": top["candidate_id"] if strong else "none",
                "selected_candidate_name": top["candidate_name"] if strong else "none",
                "rationale": rationale,
                "phase6_target_formulation": phase6_target,
                "manual_label_remains_reference_annotation": True,
                "labels_replaced": False,
                "causal_claim": False,
                "next_step_is_recommendation_not_executed": True,
            }
        ]
    )


def main_candidate_decisions(
    scorecard: pd.DataFrame,
    pairwise: pd.DataFrame,
    formulation: pd.DataFrame,
    hard_link: pd.DataFrame,
) -> pd.DataFrame:
    indexed = scorecard.set_index("candidate_id")

    def metric(candidate: str, column: str) -> float:
        return float(indexed.loc[candidate, column])

    def pair(base: str, comp: str) -> pd.Series:
        return pairwise.query(
            "baseline_candidate == @base and comparator_candidate == @comp"
        ).iloc[0]

    transient_best = scorecard.sort_values(
        ["transient_keyhole_cv_sensitivity", "balanced_accuracy"], ascending=False
    ).iloc[0]
    persistent_best = scorecard.sort_values(
        ["persistent_keyhole_cv_sensitivity", "balanced_accuracy"], ascending=False
    ).iloc[0]
    top = scorecard.iloc[0]
    hard_only = hard_link.loc[bool_series(hard_link["consensus_hard_case"])]
    questions = [
        (
            "Q1",
            "Does T0 depth separate manual Keyhole from non-Keyhole?",
            "Yes, strongly but not perfectly.",
            f"AUC={metric('T0_depth','direction_adjusted_roc_auc'):.3f}; held-out balanced accuracy={metric('T0_depth','balanced_accuracy'):.3f}.",
        ),
        (
            "Q2",
            "Does maximum depth improve materially over T0 depth?",
            "Yes." if bool(pair("T0_depth", "max_depth")["material_improvement"]) else "Not under the predeclared paired-bootstrap rule.",
            f"Paired AUC delta={pair('T0_depth','max_depth')['delta_roc_auc_comparator_minus_baseline']:.3f}.",
        ),
        (
            "Q3",
            "Does G3 improve materially over T0 depth?",
            "Yes." if bool(pair("T0_depth", "G3")["material_improvement"]) else "Not under the predeclared paired-bootstrap rule.",
            f"Paired AUC delta={pair('T0_depth','G3')['delta_roc_auc_comparator_minus_baseline']:.3f}.",
        ),
        (
            "Q4",
            "Does R3 improve materially over T0 depth?",
            "Yes." if bool(pair("T0_depth", "R3")["material_improvement"]) else "Not under the predeclared paired-bootstrap rule.",
            f"Paired AUC delta={pair('T0_depth','R3')['delta_roc_auc_comparator_minus_baseline']:.3f}.",
        ),
        (
            "Q5",
            "Which metric works best for brief/transient Keyhole events?",
            str(transient_best["candidate_id"]),
            f"Held-out transient sensitivity={transient_best['transient_keyhole_cv_sensitivity']:.3f}.",
        ),
        (
            "Q6",
            "Which works best for persistent Keyhole?",
            str(persistent_best["candidate_id"]),
            f"Held-out persistent sensitivity={persistent_best['persistent_keyhole_cv_sensitivity']:.3f}.",
        ),
        (
            "Q7",
            "Does a single stable threshold exist for any main candidate?",
            f"Yes: {top['candidate_id']}." if top["stability_class"] == "stable" else "No fully stable main threshold.",
            f"Top stability={top['stability_class']}; held-out balanced accuracy={top['balanced_accuracy']:.3f}.",
        ),
        (
            "Q8",
            "Which metric is most physically interpretable as a level-set quantity?",
            "G3 persistent depth",
            "It is a dimensional depth with an explicit physical-distance persistence window; max depth is spike-sensitive and R3 couples depth with width.",
        ),
        (
            "Q9",
            "Does any metric fail precisely because the label is morphological rather than scalar?",
            "Some discordance remains for weaker summaries; it is diagnostic, not proof that labels are wrong.",
            "Manual cavity morphology was not assigned from a reported scalar threshold.",
        ),
        (
            "Q10",
            "Which target should Phase 6 carry forward?",
            str(formulation.iloc[0]["phase6_target_formulation"]),
            f"Final Phase 5 decision={formulation.iloc[0]['decision']}; Phase 4 consensus hard cases with top-proxy discordance={int(hard_only['any_top3_proxy_cv_discordance'].sum())}/{len(hard_only)}.",
        ),
    ]
    return pd.DataFrame(
        [
            {"question_id": qid, "question": question, "answer": answer, "evidence": evidence}
            for qid, question, answer, evidence in questions
        ]
    )


def add_figure_footer(
    fig: plt.Figure, *, population: str, units: str, method: str, caveat: str
) -> None:
    text = (
        f"Population: {population} | Units: {units} | Label: {LABEL_DEFINITION}\n"
        f"Method: {method} | Caveat: {caveat}"
    )
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=7, color="#374151")


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def distribution_figure(population: pd.DataFrame, spec: dict[str, Any], path: Path) -> None:
    candidate = spec["candidate_id"]
    negative = population.loc[
        population[f"ready__{candidate}"] & ~population["has_keyhole"],
        f"value__{candidate}",
    ].to_numpy(float)
    positive = population.loc[
        population[f"ready__{candidate}"] & population["has_keyhole"],
        f"value__{candidate}",
    ].to_numpy(float)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    parts = axes[0].violinplot([negative, positive], positions=[0, 1], showmedians=True)
    for body, color in zip(parts["bodies"], ["#4C78A8", "#E45756"]):
        body.set_facecolor(color)
        body.set_alpha(0.35)
    axes[0].boxplot([negative, positive], positions=[0, 1], widths=0.20, showfliers=False)
    for index, (values, color) in enumerate([(negative, "#4C78A8"), (positive, "#E45756")]):
        rng = np.random.default_rng(deterministic_seed("jitter", candidate, index))
        axes[0].scatter(
            index + rng.normal(0, 0.035, size=len(values)), values, s=14, alpha=0.55, color=color
        )
    axes[0].set_xticks([0, 1], ["Keyhole-negative", "Keyhole-positive"])
    axes[0].set_ylabel(f"{spec['candidate_name']} ({spec['unit']})")
    axes[0].set_title("Distribution and overlap")
    for values, color, label in [
        (negative, "#4C78A8", "Keyhole-negative"),
        (positive, "#E45756", "Keyhole-positive"),
    ]:
        sorted_values = np.sort(values)
        axes[1].step(sorted_values, np.arange(1, len(values) + 1) / len(values), where="post", color=color, label=label)
    axes[1].set_xlabel(f"{spec['candidate_name']} ({spec['unit']})")
    axes[1].set_ylabel("ECDF")
    axes[1].set_title("Empirical cumulative distributions")
    axes[1].legend(frameon=False)
    fig.suptitle(f"Manual Keyhole label vs {spec['candidate_name']}", fontsize=14, fontweight="bold")
    add_figure_footer(
        fig,
        population="new-data; all machine-ready rows for this scalar",
        units=spec["unit"],
        method="descriptive violin/box/points and ECDF",
        caveat="overlap is shown; association is not causation and the label is manual morphology",
    )
    fig.subplots_adjust(bottom=0.18, top=0.84)
    save_figure(fig, path)


def generate_figures(
    destination: Path,
    population: pd.DataFrame,
    separation: pd.DataFrame,
    cv_summary: pd.DataFrame,
    stability: pd.DataFrame,
    timing: pd.DataFrame,
    persistence: pd.DataFrame,
    correlations: pd.DataFrame,
    discordant: pd.DataFrame,
    hard_link: pd.DataFrame,
    scorecard: pd.DataFrame,
) -> None:
    figure_dir = destination / FIGURE_DIR_NAME
    for number, candidate in enumerate(MAIN_CANDIDATES, start=1):
        spec = next(item for item in CANDIDATES if item["candidate_id"] == candidate)
        distribution_figure(
            population, spec, figure_dir / f"{number:02d}_{candidate}_keyhole_distribution.png"
        )

    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    for candidate in MAIN_CANDIDATES:
        valid = population[f"ready__{candidate}"]
        y = population.loc[valid, "has_keyhole"].astype(int).to_numpy()
        x = population.loc[valid, f"value__{candidate}"].to_numpy(float)
        raw = roc_auc_score(y, x)
        x = x if raw >= 0.5 else -x
        fpr, tpr, _ = roc_curve(y, x)
        ax.plot(fpr, tpr, lw=2, label=f"{candidate} (AUC {roc_auc_score(y, x):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="#6B7280", lw=1)
    ax.set(xlabel="False-positive rate", ylabel="True-positive rate", title="Direction-adjusted ROC curves")
    ax.legend(frameon=False, loc="lower right")
    add_figure_footer(
        fig,
        population="new-data; candidate-specific machine-ready rows",
        units="candidate-specific",
        method="descriptive rank separation; sign adjustment is explicitly reported",
        caveat="ROC does not establish a deployable threshold",
    )
    fig.subplots_adjust(bottom=0.18)
    save_figure(fig, figure_dir / "05_main_candidate_roc_curves.png")

    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    for candidate in MAIN_CANDIDATES:
        valid = population[f"ready__{candidate}"]
        y = population.loc[valid, "has_keyhole"].astype(int).to_numpy()
        x = population.loc[valid, f"value__{candidate}"].to_numpy(float)
        raw = roc_auc_score(y, x)
        x = x if raw >= 0.5 else -x
        precision, recall, _ = precision_recall_curve(y, x)
        ax.plot(recall, precision, lw=2, label=f"{candidate} (AP {average_precision_score(y, x):.3f})")
    prevalence = float(population["has_keyhole"].mean())
    ax.axhline(prevalence, ls="--", color="#6B7280", lw=1, label=f"prevalence {prevalence:.3f}")
    ax.set(xlabel="Recall", ylabel="Precision", title="Direction-adjusted precision-recall curves")
    ax.legend(frameon=False, loc="lower left")
    add_figure_footer(
        fig,
        population="new-data; candidate-specific machine-ready rows",
        units="candidate-specific",
        method="descriptive precision-recall separation",
        caveat="manual Keyhole prevalence is 63/165; AP complements rather than replaces ROC AUC",
    )
    fig.subplots_adjust(bottom=0.18)
    save_figure(fig, figure_dir / "06_main_candidate_precision_recall_curves.png")

    ordered = separation.sort_values("direction_adjusted_roc_auc")
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    xerr = np.vstack(
        [
            ordered["direction_adjusted_roc_auc"] - ordered["direction_adjusted_roc_auc_ci_low"],
            ordered["direction_adjusted_roc_auc_ci_high"] - ordered["direction_adjusted_roc_auc"],
        ]
    )
    ax.errorbar(
        ordered["direction_adjusted_roc_auc"], ordered["candidate_id"], xerr=xerr, fmt="o", capsize=4, color="#2563EB"
    )
    ax.axvline(0.5, ls="--", color="#6B7280")
    ax.set(xlim=(0.45, 1.02), xlabel="Direction-adjusted ROC AUC (95% bootstrap CI)", title="Scalar-proxy rank separation")
    add_figure_footer(
        fig,
        population="new-data; 5,000 simulation-level stratified bootstrap resamples in full run",
        units="AUC",
        method="descriptive AUC with bootstrap uncertainty",
        caveat="candidate-specific missingness is reported; paired comparisons use common rows",
    )
    fig.subplots_adjust(bottom=0.18, left=0.22)
    save_figure(fig, figure_dir / "07_scalar_proxy_auc_intervals.png")

    ordered_cv = cv_summary.sort_values("balanced_accuracy")
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    ax.barh(ordered_cv["candidate_id"], ordered_cv["balanced_accuracy"], color="#59A14F", alpha=0.8)
    ax.axvline(0.5, ls="--", color="#6B7280")
    ax.set(xlim=(0.45, 1.02), xlabel="Held-out balanced accuracy", title="Exact leave-one-simulation-out scalar thresholds")
    add_figure_footer(
        fig,
        population="new-data; each candidate's machine-ready simulations",
        units="balanced accuracy",
        method="threshold and direction selected on training folds only",
        caveat="full-data descriptive thresholds are not shown as predictive performance",
    )
    fig.subplots_adjust(bottom=0.18, left=0.20)
    save_figure(fig, figure_dir / "08_threshold_cv_performance.png")

    ordered_stability = stability.sort_values("threshold_iqr_over_candidate_iqr")
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    stability_values = ordered_stability["threshold_iqr_over_candidate_iqr"].to_numpy(float)
    y_positions = np.arange(len(ordered_stability))
    ax.barh(
        y_positions,
        stability_values,
        color="#F28E2B",
        alpha=0.8,
        edgecolor="#9A5A10",
    )
    ax.scatter(stability_values, y_positions, color="#9A5A10", s=28, zorder=3)
    for y_position, value in zip(y_positions, stability_values):
        ax.text(max(value + 0.008, 0.008), y_position, f"{value:.3f}", va="center", fontsize=8)
    ax.set_yticks(y_positions, ordered_stability["candidate_id"])
    ax.axvline(0.5, ls="--", color="#6B7280", label="stable-rule upper bound")
    ax.set(
        xlim=(-0.012, 0.53),
        xlabel="Threshold IQR / candidate-value IQR",
        title="Training-threshold stability across LOO folds",
    )
    ax.legend(frameon=False)
    add_figure_footer(
        fig,
        population="new-data; exact leave-one-simulation-out folds",
        units="normalized IQR",
        method="fold-selected training thresholds",
        caveat="normalization makes unlike physical units comparable; it does not create a new proxy",
    )
    fig.subplots_adjust(bottom=0.18, left=0.20)
    save_figure(fig, figure_dir / "09_threshold_stability.png")

    timing_main = timing[timing["candidate_id"].isin(MAIN_CANDIDATES)].copy()
    timing_order = ["no_Keyhole", "before_T0", "spans_multiple_T0_regions"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    for ax, candidate in zip(axes.ravel(), MAIN_CANDIDATES):
        part = timing_main.query("candidate_id == @candidate").set_index("group").reindex(timing_order).dropna(subset=["median"])
        ax.bar(range(len(part)), part["median"], color=["#4C78A8", "#F28E2B", "#E45756"][: len(part)])
        ax.set_xticks(range(len(part)), [value.replace("_", "\n") for value in part.index], fontsize=8)
        ax.set_title(candidate)
        ax.set_ylabel(str(part["unit"].iloc[0]) if len(part) else "")
    fig.suptitle("T0 timing groups: median physical proxy values", fontsize=14, fontweight="bold")
    add_figure_footer(
        fig,
        population="new-data; validated Phase 2 Keyhole timing categories",
        units="candidate-specific",
        method="descriptive group medians",
        caveat="only timing categories actually present are shown; no new frame-time alignment is invented",
    )
    fig.subplots_adjust(bottom=0.20, top=0.88, hspace=0.40)
    save_figure(fig, figure_dir / "10_keyhole_timing_main_candidates.png")

    persistence_main = persistence[persistence["candidate_id"].isin(MAIN_CANDIDATES)].copy()
    persistence_order = ["Keyhole-negative", "transient Keyhole", "persistent Keyhole"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    for ax, candidate in zip(axes.ravel(), MAIN_CANDIDATES):
        part = persistence_main.query("candidate_id == @candidate").set_index("group").reindex(persistence_order).dropna(subset=["median"])
        ax.bar(range(len(part)), part["median"], color=["#4C78A8", "#F28E2B", "#E45756"][: len(part)])
        ax.set_xticks(range(len(part)), [value.replace(" ", "\n") for value in part.index], fontsize=8)
        ax.set_title(candidate)
        ax.set_ylabel(str(part["unit"].iloc[0]) if len(part) else "")
    fig.suptitle("Transient versus persistent manual Keyhole", fontsize=14, fontweight="bold")
    add_figure_footer(
        fig,
        population="new-data; unchanged Phase 1 transient/persistent definitions",
        units="candidate-specific",
        method="descriptive group medians",
        caveat="persistence is label-sequence semantics, not a relabelled physical threshold",
    )
    fig.subplots_adjust(bottom=0.20, top=0.88, hspace=0.40)
    save_figure(fig, figure_dir / "11_transient_persistent_main_candidates.png")

    matrix = correlations.pivot(index="candidate_left", columns="candidate_right", values="spearman_rho")
    matrix = matrix.reindex(index=[item["candidate_id"] for item in CANDIDATES], columns=[item["candidate_id"] for item in CANDIDATES])
    fig, ax = plt.subplots(figsize=(9, 7.5))
    image = ax.imshow(matrix.to_numpy(float), vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, label="Spearman rho")
    ax.set_title("Candidate redundancy on common-complete new-data rows")
    add_figure_footer(
        fig,
        population=f"new-data; common-complete n={int(correlations['common_complete_n'].iloc[0])}",
        units="Spearman rho",
        method="descriptive pairwise rank correlation on one common population",
        caveat="correlation is not automatic feature selection and no multivariate classifier is fitted",
    )
    fig.subplots_adjust(bottom=0.22)
    save_figure(fig, figure_dir / "12_candidate_correlation_heatmap.png")

    counts = discordant.groupby(["review_candidate", "error_type"]).size().unstack(fill_value=0)
    counts = counts.reindex(
        index=scorecard.head(3)["candidate_id"].tolist(),
        columns=["false_negative", "false_positive"],
        fill_value=0,
    )
    fig, ax = plt.subplots(figsize=(9, 6.5))
    counts.plot(kind="bar", ax=ax, color=["#E45756", "#F28E2B"])
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=3, fontsize=8)
    ax.set(xlabel="Top scalar candidate", ylabel="Deterministic review cases", title="Held-out threshold discordant-case review set")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="CV error", frameon=False)
    add_figure_footer(
        fig,
        population="new-data; up to three most extreme false negatives and false positives per top candidate",
        units="case count",
        method="cross-validated threshold errors ranked by signed held-out margin",
        caveat="review notes are diagnostic; no manual label is changed",
    )
    fig.subplots_adjust(bottom=0.18)
    save_figure(fig, figure_dir / "13_discordant_case_summary.png")

    hard_only = hard_link.loc[bool_series(hard_link["consensus_hard_case"])]
    hard_counts = pd.Series(
        {
            "Phase 4 consensus hard cases": len(hard_only),
            "manual Keyhole": int(bool_series(hard_only["has_keyhole_phase5"]).sum()),
            "any top-3 proxy discordance": int(bool_series(hard_only["any_top3_proxy_cv_discordance"]).sum()),
            "geometry ambiguity flag": int(bool_series(hard_only["flag_depth_bounding_box_ambiguity_candidate_phase5"]).sum()),
        }
    )
    fig, ax = plt.subplots(figsize=(9, 6.5))
    bars = ax.bar(hard_counts.index, hard_counts.values, color=["#4C78A8", "#E45756", "#F28E2B", "#B279A2"])
    ax.bar_label(bars, labels=[str(int(value)) for value in hard_counts.values], padding=3)
    ax.set(ylabel="Experiment count", title="Phase 4 depth hard cases versus Phase 5 proxy structure")
    ax.tick_params(axis="x", rotation=20)
    add_figure_footer(
        fig,
        population="Phase 4 saved consensus hard-case table joined one-to-one to new-data",
        units="case count",
        method="reuse of saved Phase 4 LOO diagnostics; no model refit",
        caveat="overlap diagnoses shared difficulty but does not prove a causal mechanism",
    )
    fig.subplots_adjust(bottom=0.27)
    save_figure(fig, figure_dir / "14_phase4_hard_case_overlap.png")

    display = scorecard.set_index("candidate_id")[[
        "direction_adjusted_roc_auc",
        "balanced_accuracy",
        "transient_keyhole_cv_sensitivity",
        "persistent_keyhole_cv_sensitivity",
        "readiness_fraction",
    ]]
    fig, ax = plt.subplots(figsize=(10.5, 7))
    image = ax.imshow(display.to_numpy(float), vmin=0, vmax=1, cmap="YlGn")
    ax.set_xticks(range(len(display.columns)), ["ROC AUC", "CV balanced\naccuracy", "transient\nsensitivity", "persistent\nsensitivity", "readiness"], rotation=25, ha="right")
    ax.set_yticks(range(len(display.index)), display.index)
    for i in range(len(display.index)):
        for j in range(len(display.columns)):
            ax.text(j, i, f"{display.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label="0 to 1 score")
    ax.set_title("Multi-evidence physical-proxy scorecard")
    add_figure_footer(
        fig,
        population="new-data; all candidate-specific machine-ready rows",
        units="unitless evidence scores",
        method="predeclared multi-evidence scorecard; classification is not AUC-only",
        caveat="manual cavity morphology remains the reference annotation even for a strong proxy",
    )
    fig.subplots_adjust(bottom=0.25, left=0.20)
    save_figure(fig, figure_dir / "15_proxy_scorecard_decision.png")


def figure_manifest(destination: Path) -> pd.DataFrame:
    questions = {
        "01": "Does T0 depth differ by manual Keyhole status?",
        "02": "Does maximum depth differ by manual Keyhole status?",
        "03": "Does G3 differ by manual Keyhole status?",
        "04": "Does R3 differ by manual Keyhole status?",
        "05": "How well do main scalars rank Keyhole cases?",
        "06": "How does precision-recall separation compare?",
        "07": "How uncertain are scalar AUCs?",
        "08": "Can training-selected scalar thresholds generalize?",
        "09": "Are fold-selected thresholds stable?",
        "10": "How do candidate values vary with Keyhole timing?",
        "11": "How do transient and persistent Keyhole differ?",
        "12": "How redundant are physical candidates?",
        "13": "Which held-out cases disagree with top scalar thresholds?",
        "14": "Do Phase 4 hard cases overlap proxy discordance?",
        "15": "Which candidate wins the multi-evidence scorecard?",
    }
    rows = []
    for path in sorted((destination / FIGURE_DIR_NAME).glob("*.png")):
        prefix = path.name.split("_", 1)[0]
        rows.append(
            {
                "figure_file": path.name,
                "relative_path": path.relative_to(ROOT).as_posix(),
                "question": questions.get(prefix, "Phase 5 physical-proxy question"),
                "population": "new-data only (or saved Phase 4 new-data hard cases for figure 14)",
                "label_definition": LABEL_DEFINITION,
                "major_caveat": "manual morphology association, not causal proof or label replacement",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return pd.DataFrame(rows)


def build_summary(
    *,
    preflight: dict[str, Any],
    dataset_audit: dict[str, Any],
    population: pd.DataFrame,
    definitions: pd.DataFrame,
    effects: pd.DataFrame,
    separation: pd.DataFrame,
    pairwise: pd.DataFrame,
    cv_summary: pd.DataFrame,
    stability: pd.DataFrame,
    scorecard: pd.DataFrame,
    hard_link: pd.DataFrame,
    formulation: pd.DataFrame,
    resamples: int,
    smoke: bool,
) -> dict[str, Any]:
    top_auc = separation.iloc[0]
    top_ap = separation.sort_values("direction_adjusted_average_precision", ascending=False).iloc[0]
    top_cv = cv_summary.iloc[0]
    top_score = scorecard.iloc[0]
    hard_only = hard_link.loc[bool_series(hard_link["consensus_hard_case"])]
    labels = {
        "new_data_total": int(len(population)),
        "keyhole_positive": int(population["has_keyhole"].sum()),
        "keyhole_negative": int((~population["has_keyhole"]).sum()),
        "keyhole_negative_with_conduction": int(
            ((~population["has_keyhole"]) & population["has_conduction"]).sum()
        ),
        "keyhole_negative_without_conduction": int(
            ((~population["has_keyhole"]) & ~population["has_conduction"]).sum()
        ),
        "target_ready": int(population["physical_target_extraction_success"].sum()),
        "target_ineligible_but_retained": int(
            (~population["physical_target_extraction_success"]).sum()
        ),
        "transient_keyhole": int(population["keyhole_transient_by_sequence"].sum()),
        "persistent_keyhole": int(population["keyhole_persistent_to_last_physical_frame"].sum()),
        "repeated_keyhole": int(population["repeated_keyhole_episodes"].sum()),
        "timing_counts": population.loc[
            population["has_keyhole"], "keyhole_timing_relative_to_T0"
        ].value_counts().to_dict(),
    }
    return {
        "phase": "Week 7 Phase 5 manual Keyhole label to continuous physical proxy analysis",
        "mode": "smoke" if smoke else "full",
        "generated_at_utc": utc_now(),
        "phase5_preflight": preflight,
        "dataset_revision_audit": dataset_audit,
        "label_provenance": {
            "ioan_statement": IOAN_LABEL_STATEMENT,
            "manual_qualitative": True,
            "primary_visual_cue": "cavities directly under the melt pool",
            "reported_deterministic_scalar_threshold": False,
            "association_not_causation": True,
            "manual_label_remains_reference": True,
        },
        "population": labels,
        "candidate_count": int(len(definitions)),
        "candidate_readiness": definitions.set_index("candidate_id")[["ready_n", "missing_n"]].to_dict("index"),
        "bootstrap_resamples": int(resamples),
        "top_rank_effect_candidate": str(
            effects.sort_values("rank_biserial_effect_size", ascending=False).iloc[0]["candidate_id"]
        ),
        "highest_roc_auc_candidate": str(top_auc["candidate_id"]),
        "highest_roc_auc": float(top_auc["direction_adjusted_roc_auc"]),
        "highest_average_precision_candidate": str(top_ap["candidate_id"]),
        "highest_average_precision": float(top_ap["direction_adjusted_average_precision"]),
        "best_threshold_cv_candidate": str(top_cv["candidate_id"]),
        "best_threshold_cv_balanced_accuracy": float(top_cv["balanced_accuracy"]),
        "top_scorecard_candidate": str(top_score["candidate_id"]),
        "top_scorecard_class": str(top_score["proxy_classification"]),
        "top_threshold_stability": str(top_score["stability_class"]),
        "phase4_linked_population_count": int(len(hard_link)),
        "phase4_consensus_hard_case_count": int(len(hard_only)),
        "phase4_consensus_hard_case_keyhole_count": int(
            bool_series(hard_only["has_keyhole_phase5"]).sum()
        ),
        "phase4_consensus_hard_case_top3_proxy_discordant_count": int(
            bool_series(hard_only["any_top3_proxy_cv_discordance"]).sum()
        ),
        "final_target_formulation": formulation.iloc[0].to_dict(),
        "hard_stop": {
            "final_keyhole_classifier_trained": False,
            "gp_classifier_fitted": False,
            "new_gp_regression_fitted": False,
            "active_learning_performed": False,
            "level_set_estimation_performed": False,
            "labels_altered": False,
            "old_new_pooled_for_model": False,
        },
    }


def results_summary_markdown(summary: dict[str, Any], scorecard: pd.DataFrame, pairwise: pd.DataFrame) -> str:
    population = summary["population"]
    top = scorecard.iloc[0]
    decision = summary["final_target_formulation"]
    lines = [
        "# Week 7 Phase 5 results: manual Keyhole label and continuous physical proxies",
        "",
        "## Scope and evidence boundary",
        "",
        f"Phase 5 starts from exact Phase 4 commit `{PHASE4_COMMIT_SHA}` and uses only the `{PRIMARY_POPULATION}` population for primary science. The current Hugging Face main revision is `{CURRENT_DATASET_REVISION}`. Its only changes from the pinned revision are 110 added old-data monitor files (55 `time.dat` and 55 `kinetic-energy_melt.dat`); no new-data path, label, geometry monitor, or sentinel file changed.",
        "",
        "## How the Keyhole labels were made",
        "",
        f"> {IOAN_LABEL_STATEMENT}",
        "",
        "The labels are therefore manual morphology annotations, usually guided by cavities directly below the melt pool. They were not reported as a deterministic threshold on depth, G3, R3, width, or kinetic energy. This analysis tests physical association and consistency; it neither changes the labels nor establishes causality.",
        "",
        "## Population",
        "",
        f"All {population['new_data_total']} new-data experiments remain in the audit interface: {population['keyhole_positive']} Keyhole-positive and {population['keyhole_negative']} Keyhole-negative. All {population['keyhole_negative']} negatives contain at least one Conduction frame; {population['keyhole_negative_without_conduction']} negatives lack Conduction. Machine-derived physical targets are ready for {population['target_ready']}/165; the one file-missing case is retained and explicitly unavailable rather than silently removed.",
        "",
        "## Main result",
        "",
        f"`{top['candidate_id']}` is the leading scalar. Its direction-adjusted ROC AUC is {top['direction_adjusted_roc_auc']:.4f}, average precision is {top['direction_adjusted_average_precision']:.4f}, and exact leave-one-simulation-out threshold balanced accuracy is {top['balanced_accuracy']:.4f}. The threshold-stability class is `{top['stability_class']}`. It is classified as **{top['proxy_classification']}** under the predeclared multi-evidence rule.",
        "",
        "T0 depth is informative but weaker than the transient/persistence-aware depth quantities. Pairwise common-complete bootstrap comparisons, not separate-population point estimates, determine whether max depth, G3, and R3 materially improve on T0 depth.",
        "",
        "## Transient and persistent Keyhole",
        "",
        f"For the leading scalar, held-out sensitivity is {top['transient_keyhole_cv_sensitivity']:.4f} for transient Keyhole and {top['persistent_keyhole_cv_sensitivity']:.4f} for persistent-to-last-frame Keyhole. These groups reuse the validated Phase 1 sequence definitions; no new morphology rule was created.",
        "",
        "## Phase 4 hard cases",
        "",
        f"The saved Phase 4 linkage table covers {summary['phase4_linked_population_count']} target-ready experiments and marks {summary['phase4_consensus_hard_case_count']} consensus hard cases. Of those hard cases, {summary['phase4_consensus_hard_case_keyhole_count']} are manual Keyhole cases and {summary['phase4_consensus_hard_case_top3_proxy_discordant_count']} cross any top-three held-out proxy decision. This linkage reuses saved Phase 4 residuals and does not refit any regression model.",
        "",
        "## Target-formulation decision",
        "",
        f"**{decision['decision']}**. {decision['rationale']}",
        "",
        f"Phase 6 recommendation: {decision['phase6_target_formulation']}",
        "",
        "Even a strong continuous association does not replace Ioan's manual cavity-based label. The binary annotation remains the reference against which a continuous formulation must be tested.",
        "",
        "## Hard stop",
        "",
        "No final Keyhole classifier, GP classifier, new GP regression, active learning, level-set estimation, acquisition comparison, label correction, or old/new pooled model was run.",
    ]
    return "\n".join(lines)


def label_provenance_markdown() -> str:
    return "\n".join(
        [
            "# Keyhole label provenance",
            "",
            "Supervisor statement (Ioan):",
            "",
            f"> {IOAN_LABEL_STATEMENT}",
            "",
            "Phase 5 interpretation:",
            "",
            "- The frame labels were assigned manually and qualitatively.",
            "- Cavities directly beneath the melt pool were the usual visual cue for Keyhole.",
            "- Ioan did not report a deterministic scalar-monitor threshold as the labelling rule.",
            "- Physical scalar associations are plausible because cavity morphology and melt geometry are related, but the analysis is associational rather than causal.",
            "- The source labels and the validated Phase 1 `has_keyhole` semantics are unchanged.",
            "- Discordant-case notes never relabel an experiment and are not new ground truth.",
        ]
    )


def input_provenance_payload(dataset_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase4_parent_sha": PHASE4_COMMIT_SHA,
        "phase5_branch": PHASE5_BRANCH,
        "dataset": dataset_audit,
        "inputs": {
            name: {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for name, path in input_paths().items()
        },
        "primary_population": PRIMARY_POPULATION,
        "candidate_sources": [
            {
                "candidate_id": item["candidate_id"],
                "value_column": item["value_column"],
                "source": item["source"],
            }
            for item in CANDIDATES
        ],
        "new_data_content_recomputed_from_current_restored_old_data": False,
        "scientific_scalar_source_revision": PINNED_DATASET_REVISION,
        "current_repository_provenance_revision": CURRENT_DATASET_REVISION,
    }


def validation_table(destination: Path, *, notebook_required: bool = True) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(check_id: str, description: str, passed: bool, evidence: str) -> None:
        rows.append(
            {
                "check_id": check_id,
                "description": description,
                "status": "PASS" if passed else "FAIL",
                "evidence": evidence,
            }
        )

    preflight = json.loads((destination / "phase5_preflight.json").read_text(encoding="utf-8"))
    provenance = json.loads((destination / "input_provenance.json").read_text(encoding="utf-8"))
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    population = pd.read_csv(destination / "physical_proxy_population_reference.csv")
    definitions = pd.read_csv(destination / "physical_proxy_candidate_definitions.csv")
    labels = pd.read_csv(destination / "experiment_level_label_audit.csv")
    separation = pd.read_csv(destination / "physical_proxy_univariate_separation.csv")
    pairwise = pd.read_csv(destination / "physical_proxy_pairwise_auc_comparison.csv")
    cv_summary = pd.read_csv(destination / "physical_proxy_threshold_cv_summary.csv")
    folds = pd.read_csv(destination / "physical_proxy_threshold_fold_predictions.csv")
    hard_link = pd.read_csv(destination / "phase4_depth_hard_cases_vs_phase5_proxy.csv")
    discordant = pd.read_csv(destination / "physical_proxy_discordant_cases.csv")
    figures = pd.read_csv(destination / "figure_manifest.csv")
    diff = pd.read_csv(destination / "current_revision_diff_audit.csv")

    add("V01", "Exact Phase 4 parent commit", preflight["phase5_parent_sha"] == PHASE4_COMMIT_SHA, preflight["phase5_parent_sha"])
    add("V02", "Exact Phase 5 branch", preflight["phase5_branch"] == PHASE5_BRANCH, preflight["phase5_branch"])
    add("V03", "Current HF revision recorded", provenance["dataset"]["current_main_revision"] == CURRENT_DATASET_REVISION, provenance["dataset"]["current_main_revision"])
    add("V04", "Pinned-to-current diff audited", bool(provenance["dataset"]["accepted_old_data_monitor_restoration_only"]), f"{len(diff)} paths")
    add("V05", "Only accepted restored file names changed", set(diff["file_name"]) == {"time.dat", "kinetic-energy_melt.dat"}, str(diff["file_name"].value_counts().to_dict()))
    add("V06", "All changed experiments are old-data-local", set(diff["registry_partition"]) == {"old-data-local"} and diff["experiment_name"].nunique() == 55, f"{diff['experiment_name'].nunique()} experiments")
    add("V07", "No restored file enters primary analysis", not bool(bool_series(diff["touches_new_data"]).any()), "0 new-data changed paths")
    add("V08", "New-data labels and monitors unchanged by tree diff", not bool(bool_series(diff["touches_label_or_geometry"]).any()) and provenance["dataset"]["new_data_changed_path_count"] == 0, "no new-data path changed")
    add("V09", "Primary analysis is new-data only", set(population["partition"]) == {PRIMARY_POPULATION}, f"n={len(population)}")
    add("V10", "No experiment silently removed", len(population) == 165 and not bool(bool_series(population["simulation_silently_removed"]).any()), "165/165 represented")
    add("V11", "Source labels unchanged", not bool(bool_series(population["source_label_modified"]).any()) and labels["frames_csv_sha256"].notna().all(), "0 modified; hashes present")
    add("V12", "has_keyhole uses Phase 1 semantics", int(bool_series(population["has_keyhole"]).sum()) == 63 and summary["population"]["keyhole_positive"] == 63, "63 positive, 102 negative")
    add("V13", "Negative label composition audited", int(bool_series(labels["keyhole_negative_without_conduction"]).sum()) == 0, "102/102 negatives contain Conduction")
    add("V14", "Candidate quantities use exact saved definitions", len(definitions) == 8 and not bool(bool_series(definitions["post_hoc_candidate"]).any()), "; ".join(definitions["candidate_id"]))
    add("V15", "T0 unchanged", definitions.query("candidate_id == 'T0_depth'")["value_column"].iloc[0] == "T0_depth_um", "Phase 2 T0_depth_um")
    add("V16", "Maximum depth unchanged", definitions.query("candidate_id == 'max_depth'")["value_column"].iloc[0] == "max_depth_um", "Phase 2 max_depth_um")
    add("V17", "G3 unchanged", definitions.query("candidate_id == 'G3'")["value_column"].iloc[0] == "G3_persistent_depth_um", "Phase 2 G3")
    add("V18", "R3 unchanged", definitions.query("candidate_id == 'R3'")["value_column"].iloc[0] == "R3_persistent_depth_width_ratio", "Phase 2 R3")
    add("V19", "No post-hoc ratio introduced", set(definitions.query("unit == 'dimensionless'")["candidate_id"]) == {"R0", "R3"}, "only predefined R0/R3")
    add("V20", "Group counts reconcile", summary["population"]["keyhole_positive"] + summary["population"]["keyhole_negative"] == 165, "63+102=165")

    auc_ok = True
    ap_ok = True
    for row in separation.itertuples():
        ready = bool_series(population[f"ready__{row.candidate_id}"])
        y = bool_series(population.loc[ready, "has_keyhole"]).astype(int).to_numpy()
        x = population.loc[ready, f"value__{row.candidate_id}"].to_numpy(float)
        sign = 1.0 if row.physical_direction == "higher_is_more_keyhole_like" else -1.0
        auc_ok &= np.isclose(roc_auc_score(y, sign * x), row.direction_adjusted_roc_auc, atol=1e-12)
        ap_ok &= np.isclose(average_precision_score(y, sign * x), row.direction_adjusted_average_precision, atol=1e-12)
    add("V21", "ROC AUC reconciles from raw rows", bool(auc_ok), f"{len(separation)}/{len(separation)}")
    add("V22", "PR AUC reconciles from raw rows", bool(ap_ok), f"{len(separation)}/{len(separation)}")
    add("V23", "Bootstrap unit is simulation", set(separation["bootstrap_unit"]) == {"simulation"}, f"{int(separation['bootstrap_resamples'].min())} resamples")
    add("V24", "Pairwise comparisons are common-complete and paired", bool(bool_series(pairwise["paired_stratified_bootstrap"]).all()) and pairwise["common_complete_n"].min() > 0, f"{len(pairwise)} comparisons")

    cv_ok = True
    for row in cv_summary.itertuples():
        subset = folds.query("candidate_id == @row.candidate_id")
        cv_ok &= len(subset) == row.cv_n
        cv_ok &= subset["held_out_experiment_name"].nunique() == row.cv_n
        cv_ok &= subset["leakage_guard"].str.contains("without held-out").all()
        cv_ok &= np.isclose(
            balanced_accuracy_score(subset["held_out_has_keyhole"], subset["held_out_prediction"]),
            row.balanced_accuracy,
        )
    add("V25", "Threshold performance is genuinely held out", bool(cv_ok), "exact LOO folds reconcile")
    add("V26", "In-sample threshold not mislabelled predictive", not bool(bool_series(cv_summary["full_data_threshold_is_predictive_performance"]).any()), "descriptive only")
    add("V27", "Transient/persistent definitions reused", set(labels["keyhole_persistence_group"]) <= {"Keyhole-negative", "transient Keyhole", "persistent Keyhole", "Keyhole-positive other"}, "Phase 1 fields")
    add("V28", "Phase 4 hard-case join reconciles", hard_link["experiment_name"].is_unique and hard_link["value__T0_depth"].notna().all() and not bool(bool_series(hard_link["phase4_models_refit"]).any()), f"{len(hard_link)} saved cases")
    add("V29", "Discordant review changes no labels", not bool(bool_series(discordant["label_changed"]).any()), f"{len(discordant)} diagnostic rows")
    add("V30", "No multivariate or GP classifier fitted", not summary["hard_stop"]["final_keyhole_classifier_trained"] and not summary["hard_stop"]["gp_classifier_fitted"], "univariate scalars only")
    add("V31", "No new GP regression fitted", not summary["hard_stop"]["new_gp_regression_fitted"], "saved Phase 4 residuals only")
    add("V32", "No active learning or level-set experiment", not summary["hard_stop"]["active_learning_performed"] and not summary["hard_stop"]["level_set_estimation_performed"], "hard stop respected")
    add("V33", "All 15 required figures exist and hash-match", len(figures) == 15 and all((ROOT / path).exists() and sha256_file(ROOT / path) == digest for path, digest in zip(figures["relative_path"], figures["sha256"])), f"{len(figures)}/15")

    notebook_ok = True
    notebook_evidence = "not required for smoke"
    if notebook_required:
        if not NOTEBOOK_PATH.exists():
            notebook_ok = False
            notebook_evidence = "notebook missing"
        else:
            notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
            code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
            errors = [output for cell in code_cells for output in cell.get("outputs", []) if output.get("output_type") == "error"]
            counts = [cell.get("execution_count") for cell in code_cells]
            notebook_ok = bool(code_cells) and not errors and all(value is not None for value in counts)
            notebook_evidence = f"{len(code_cells)} executed code cells; {len(errors)} errors"
    add("V34", "Teaching notebook executes without stored errors", notebook_ok, notebook_evidence)
    add("V35", "Manual label remains reference", bool(summary["label_provenance"]["manual_label_remains_reference"]), "no label replacement")
    required_artifacts = [
        "phase5_preflight.json",
        "input_provenance.json",
        "label_provenance.md",
        "experiment_level_label_audit.csv",
        "physical_proxy_population_reference.csv",
        "physical_proxy_candidate_definitions.csv",
        "physical_proxy_group_descriptives.csv",
        "physical_proxy_effect_sizes.csv",
        "physical_proxy_univariate_separation.csv",
        "physical_proxy_pairwise_auc_comparison.csv",
        "physical_proxy_threshold_cv_summary.csv",
        "physical_proxy_threshold_fold_predictions.csv",
        "physical_proxy_threshold_stability.csv",
        "physical_proxy_by_keyhole_timing.csv",
        "physical_proxy_by_keyhole_persistence.csv",
        "physical_proxy_candidate_correlations.csv",
        "physical_proxy_discordant_cases.csv",
        "phase4_depth_hard_cases_vs_phase5_proxy.csv",
        "physical_proxy_candidate_scorecard.csv",
        "t0_vs_max_vs_g3_vs_r3_decision.csv",
        "phase5_target_formulation_decision.csv",
        "summary.json",
        "results_summary.md",
        "figure_manifest.csv",
    ]
    present_required = sum((destination / name).exists() for name in required_artifacts)
    add(
        "V36",
        "Required output artifact set is structurally ready for manifesting",
        present_required == len(required_artifacts),
        f"{present_required}/{len(required_artifacts)} required pre-manifest artifacts present",
    )
    return pd.DataFrame(rows)


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    requirements = [
        ("R01", "Exact Phase 4 parent and isolated Phase 5 branch", ["V01", "V02"]),
        ("R02", "Current HF restoration audited without new-data drift", ["V03", "V04", "V05", "V06", "V07", "V08"]),
        ("R03", "Primary population and labels preserved", ["V09", "V10", "V11", "V12", "V13"]),
        ("R04", "Eight predefined scalar candidates with machine readiness", ["V14", "V15", "V16", "V17", "V18", "V19"]),
        ("R05", "Experiment-level label composition and groups reconcile", ["V20", "V27"]),
        ("R06", "Univariate ROC and PR separation with bootstrap", ["V21", "V22", "V23"]),
        ("R07", "Fair paired/common-complete AUC comparison", ["V24"]),
        ("R08", "Leakage-free scalar threshold cross-validation", ["V25", "V26"]),
        ("R09", "Discordant cases are diagnostic and labels unchanged", ["V29", "V35"]),
        ("R10", "Phase 4 linkage reuses saved hard cases", ["V28", "V31"]),
        ("R11", "No prohibited classifier, active learning, or level set", ["V30", "V31", "V32"]),
        ("R12", "Fifteen figures are present and verified", ["V33"]),
        ("R13", "Teaching notebook executes cleanly", ["V34"]),
        ("R14", "Output manifest generated and verifiable", ["V36"]),
    ]
    status = validation.set_index("check_id")["status"].to_dict()
    rows = []
    for requirement_id, description, checks in requirements:
        passed = all(status.get(check) == "PASS" for check in checks)
        rows.append(
            {
                "requirement_id": requirement_id,
                "description": description,
                "status": "PASS" if passed else "FAIL",
                "supporting_validation_checks": ";".join(checks),
            }
        )
    return pd.DataFrame(rows)


def output_manifest(destination: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        if path == destination / "output_manifest.csv":
            continue
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return pd.DataFrame(rows)


def verify_output_manifest(destination: Path) -> tuple[int, int, list[str]]:
    manifest = pd.read_csv(destination / "output_manifest.csv")
    failures: list[str] = []
    for row in manifest.itertuples():
        path = ROOT / row.relative_path
        if not path.exists():
            failures.append(f"missing:{row.relative_path}")
        elif path.stat().st_size != row.size_bytes:
            failures.append(f"size:{row.relative_path}")
        elif sha256_file(path) != row.sha256:
            failures.append(f"hash:{row.relative_path}")
    return len(manifest), len(manifest) - len(failures), failures


def refresh_validation(*, smoke: bool = False, notebook_required: bool = True) -> dict[str, Any]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    validation = validation_table(destination, notebook_required=notebook_required)
    write_csv(destination / "validation_results.csv", validation)
    requirements = requirement_checklist(validation)
    write_csv(destination / "requirement_checklist.csv", requirements)
    write_csv(destination / "output_manifest.csv", output_manifest(destination))
    manifest_total, manifest_verified, failures = verify_output_manifest(destination)
    require(not failures, "Output-manifest failures: " + "; ".join(failures[:5]))
    require((validation["status"] == "PASS").all(), "One or more validation checks failed")
    require((requirements["status"] == "PASS").all(), "One or more requirements failed")
    return {
        "validation_passed": int((validation["status"] == "PASS").sum()),
        "validation_total": int(len(validation)),
        "requirement_passed": int((requirements["status"] == "PASS").sum()),
        "requirement_total": int(len(requirements)),
        "manifest_verified": manifest_verified,
        "manifest_total": manifest_total,
    }


def run_phase5(*, smoke: bool = False) -> dict[str, Any]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    (destination / FIGURE_DIR_NAME).mkdir(parents=True, exist_ok=True)
    resamples = SMOKE_BOOTSTRAP_RESAMPLES if smoke else FULL_BOOTSTRAP_RESAMPLES

    preflight = git_preflight()
    tables = load_inputs()
    dataset_audit, diff_audit = audit_current_dataset_revision(tables["phase1_registry"])
    population = build_population(tables)
    definitions = candidate_definitions(population)
    labels = label_audit(population)
    descriptives, effects = group_and_effect_analysis(population, resamples=resamples)
    separation = separation_analysis(population, resamples=resamples)
    pairwise = paired_auc_analysis(population, resamples=resamples)
    cv_summary, folds, stability = threshold_cv_analysis(population)
    timing = subgroup_analysis(population, folds, group_column="keyhole_timing_group")
    persistence = subgroup_analysis(population, folds, group_column="keyhole_persistence_group")
    correlations = candidate_correlations(population)
    scorecard = score_candidates(
        definitions, effects, separation, cv_summary, stability, folds, population
    )
    discordant = discordant_cases(
        population, folds, scorecard, tables["phase2_depth_ambiguity"]
    )
    hard_link = phase4_hard_case_linkage(
        population, tables["phase4_hard_cases"], folds, scorecard
    )
    formulation = target_formulation_decision(scorecard)
    main_decisions = main_candidate_decisions(scorecard, pairwise, formulation, hard_link)

    write_json(destination / "phase5_preflight.json", preflight)
    write_json(destination / "dataset_revision_audit.json", dataset_audit)
    write_csv(destination / "current_revision_diff_audit.csv", diff_audit)
    write_json(destination / "input_provenance.json", input_provenance_payload(dataset_audit))
    write_text(destination / "label_provenance.md", label_provenance_markdown())
    write_csv(destination / "experiment_level_label_audit.csv", labels)
    write_csv(destination / "physical_proxy_population_reference.csv", population_reference(population))
    write_csv(destination / "physical_proxy_candidate_definitions.csv", definitions)
    write_csv(destination / "physical_proxy_group_descriptives.csv", descriptives)
    write_csv(destination / "physical_proxy_effect_sizes.csv", effects)
    write_csv(destination / "physical_proxy_univariate_separation.csv", separation)
    write_csv(destination / "physical_proxy_pairwise_auc_comparison.csv", pairwise)
    write_csv(destination / "physical_proxy_threshold_cv_summary.csv", cv_summary)
    write_csv(destination / "physical_proxy_threshold_fold_predictions.csv", folds)
    write_csv(destination / "physical_proxy_threshold_stability.csv", stability)
    write_csv(destination / "physical_proxy_by_keyhole_timing.csv", timing)
    write_csv(destination / "physical_proxy_by_keyhole_persistence.csv", persistence)
    write_csv(destination / "physical_proxy_candidate_correlations.csv", correlations)
    write_csv(destination / "physical_proxy_discordant_cases.csv", discordant)
    write_csv(destination / "phase4_depth_hard_cases_vs_phase5_proxy.csv", hard_link)
    write_csv(destination / "physical_proxy_candidate_scorecard.csv", scorecard)
    write_csv(destination / "t0_vs_max_vs_g3_vs_r3_decision.csv", main_decisions)
    write_csv(destination / "phase5_target_formulation_decision.csv", formulation)

    generate_figures(
        destination,
        population,
        separation,
        cv_summary,
        stability,
        timing,
        persistence,
        correlations,
        discordant,
        hard_link,
        scorecard,
    )
    write_csv(destination / "figure_manifest.csv", figure_manifest(destination))
    summary = build_summary(
        preflight=preflight,
        dataset_audit=dataset_audit,
        population=population,
        definitions=definitions,
        effects=effects,
        separation=separation,
        pairwise=pairwise,
        cv_summary=cv_summary,
        stability=stability,
        scorecard=scorecard,
        hard_link=hard_link,
        formulation=formulation,
        resamples=resamples,
        smoke=smoke,
    )
    write_json(destination / "summary.json", summary)
    write_text(destination / "results_summary.md", results_summary_markdown(summary, scorecard, pairwise))
    validation_result = refresh_validation(
        smoke=smoke, notebook_required=False if smoke else NOTEBOOK_PATH.exists()
    )
    return {**summary, "validation": validation_result}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Use 300 bootstrap resamples")
    parser.add_argument(
        "--refresh-validation", action="store_true", help="Refresh validation and manifest only"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_validation:
        result = refresh_validation(smoke=args.smoke, notebook_required=not args.smoke)
    else:
        result = run_phase5(smoke=args.smoke)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
