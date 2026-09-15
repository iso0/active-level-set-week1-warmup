"""Exact, post-hoc Week 8.5 horizon continuation from H=160 to H=320.

The frozen Week 8.5 protocol and its H=160 checkpoints are immutable inputs.
This module validates those inputs, then continues ``binary_margin`` and all 30
``binary_random`` trajectories per outer run on the original training pools.
Extension evaluations are made at budgets 164, 168, ..., 320.  Outputs live in
a separate Week 9 directory and never modify a Week 8/8.5 artifact.

This is a post-hoc closing analysis, not an amendment to the preregistered
Week 8.5 protocol, whose declared stopping horizon remains H=160.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tarfile
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85


ROOT = Path(__file__).resolve().parents[1]
FROZEN_OUTPUT = ROOT / "outputs" / "week8_5_frozen_confirmation"
FROZEN_ARCHIVE = FROZEN_OUTPUT / "week8_5_checkpoint_bundle.tar.gz"
DEFAULT_OUTPUT = ROOT / "outputs" / "week9_phase1_close_week8" / "dev_horizon"
FROZEN_EXTRACTED = DEFAULT_OUTPUT / "_frozen_h160" / "checkpoints"
EXTENSION_CHECKPOINTS = DEFAULT_OUTPUT / "checkpoints"

FROZEN_COMMIT = "6487722fe5e60d951ab929d8539e0793f9bed366"
FROZEN_PROTOCOL_ID = "week8_5_frozen_confirmation_protocol/v1.0.0"
FROZEN_PROTOCOL_SHA256 = "bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66"
FROZEN_ARCHIVE_SHA256 = "1004fc299e00db6f1b2b89e4407f5ac8b2c4815d1169bcaad43dacdebacf72a9"
FROZEN_SOURCE_HASHES = {
    "phase6_source.py": "23797dcbc706f891cf1cd0f560299c64ed903d82f146248d13708d051d841479",
    "phase7_source.py": "d5a331c60bab373adfc63344cc5eb3b88e1ca7ce41e4ffd0717196edeb2c00df",
    "primary_common_population.csv": "c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7",
    "protocol.json": FROZEN_PROTOCOL_SHA256,
}

EXTENSION_PROTOCOL_ID = "week9_phase1_posthoc_horizon_extension/v1.0.0"
EXTENSION_SCHEMA_VERSION = "1.0.0"
SOURCE_HORIZON = 160
TARGET_HORIZON = 320
EXTENSION_ARMS = ("binary_margin", "binary_random")
EXPECTED_TRAJECTORIES = 100 * (1 + 30)
RANDOM_EVALUATION_POLICY_ID = "evaluate_until_persistent_crossing_then_terminal/v1"
PRIMARY_METRIC = "B1_q20_accuracy"
PRIMARY_TARGET = 0.80
FROZEN_RANDOM_CONFIRMED = 2493
FROZEN_RANDOM_UNRESOLVED = 507
PLANNED_MARGIN_FITS = 100 * (TARGET_HORIZON - SOURCE_HORIZON + 1)
PLANNED_RANDOM_FITS_UPPER_BOUND = FROZEN_RANDOM_CONFIRMED + FROZEN_RANDOM_UNRESOLVED * len(
    range(SOURCE_HORIZON + 4, TARGET_HORIZON + 1, 4)
)
PLANNED_TOTAL_FITS_UPPER_BOUND = PLANNED_MARGIN_FITS + PLANNED_RANDOM_FITS_UPPER_BOUND


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def extension_budgets(
    source_horizon: int = SOURCE_HORIZON,
    target_horizon: int = TARGET_HORIZON,
    step: int = 4,
) -> list[int]:
    """Return the declared post-hoc evaluation grid after the source horizon."""

    require(source_horizon >= 16, "Source horizon must include the 16-query initial design")
    require(target_horizon > source_horizon, "Target horizon must exceed source horizon")
    require(step > 0, "Checkpoint step must be positive")
    require(source_horizon + step <= target_horizon, "Target contains no extension checkpoint")
    require((target_horizon - source_horizon) % step == 0, "Target must lie on the extension grid")
    return list(range(source_horizon + step, target_horizon + 1, step))


def extension_checkpoint_path(
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    checkpoint_root: Path = EXTENSION_CHECKPOINTS,
) -> Path:
    return checkpoint_root / f"w9p1__{spec.run_id}__{arm}__c{continuation:02d}.json"


def frozen_checkpoint_name(spec: w85.SplitSpec, arm: str, continuation: int) -> str:
    return w85.checkpoint_path(spec, arm, continuation).name


def expected_identity(spec: w85.SplitSpec, arm: str, continuation: int) -> dict[str, Any]:
    return w85.trajectory_identity(spec, arm, continuation)


def validate_frozen_environment(*, check_archive: bool = True) -> dict[str, Any]:
    """Fail closed if any byte-pinned Week 8.5 scientific input has drifted."""

    protocol = json.loads(w85.PROTOCOL_PATH.read_text(encoding="utf-8"))
    canonical_protocol_hash = hashlib.sha256(w85.canonical_protocol_bytes(protocol)).hexdigest()
    current_hashes = {
        "phase6_source.py": sha256_file(ROOT / "src" / "week7_phase6_real_data_boundary_active_level_set.py"),
        "phase7_source.py": sha256_file(ROOT / "src" / "week7_phase7_final_boundary_hybrid_benchmark.py"),
        "primary_common_population.csv": sha256_file(w85.SOURCE_POPULATION),
        "protocol.json": canonical_protocol_hash,
    }
    require(current_hashes == FROZEN_SOURCE_HASHES, f"Frozen source hash drift: {current_hashes}")
    require(canonical_protocol_hash == FROZEN_PROTOCOL_SHA256, "Frozen canonical protocol hash drift")
    archive_hash = None
    if check_archive:
        require(FROZEN_ARCHIVE.is_file(), f"Missing frozen checkpoint archive: {FROZEN_ARCHIVE}")
        archive_hash = sha256_file(FROZEN_ARCHIVE)
        require(archive_hash == FROZEN_ARCHIVE_SHA256, "Frozen checkpoint archive SHA-256 drift")
    return {
        "frozen_commit": FROZEN_COMMIT,
        "frozen_protocol_id": FROZEN_PROTOCOL_ID,
        "frozen_protocol_sha256": FROZEN_PROTOCOL_SHA256,
        "frozen_archive_sha256": archive_hash,
        "frozen_source_hashes": current_hashes,
    }


def _safe_archive_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = [member for member in archive.getmembers() if member.isfile()]
    expected_prefix = "checkpoints/"
    for member in members:
        normalized = member.name.replace("\\", "/")
        require(normalized.startswith(expected_prefix), f"Unexpected archive member: {member.name}")
        relative = Path(normalized).relative_to("checkpoints")
        require(len(relative.parts) == 1, f"Nested or unsafe archive member: {member.name}")
        require(relative.suffix == ".json", f"Non-JSON checkpoint archive member: {member.name}")
    require(len(members) == 3200, f"Frozen archive contains {len(members)} files, expected 3200")
    return members


def extract_frozen_checkpoints(destination: Path = FROZEN_EXTRACTED) -> dict[str, Any]:
    """Extract the pinned archive, reusing only byte-identical members."""

    provenance = validate_frozen_environment(check_archive=True)
    destination.mkdir(parents=True, exist_ok=True)
    extracted = 0
    reused = 0
    with tarfile.open(FROZEN_ARCHIVE, "r:gz") as archive:
        members = _safe_archive_members(archive)
        member_hashes: dict[str, str] = {}
        for member in members:
            target = destination / Path(member.name.replace("\\", "/")).name
            source = archive.extractfile(member)
            require(source is not None, f"Cannot read archive member: {member.name}")
            with source:
                archive_bytes = source.read()
            require(len(archive_bytes) == member.size, f"Truncated archive member: {member.name}")
            archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
            member_hashes[target.name] = archive_sha256
            if target.is_file() and sha256_file(target) == archive_sha256:
                reused += 1
                continue
            temporary = target.with_suffix(target.suffix + f".{os.getpid()}.tmp")
            temporary.write_bytes(archive_bytes)
            require(temporary.stat().st_size == member.size, f"Truncated extraction: {member.name}")
            temporary.replace(target)
            extracted += 1
    files = list(destination.glob("*.json"))
    require(len(files) == 3200, f"Extracted checkpoint count {len(files)} != 3200")
    report = {
        **provenance,
        "destination": str(destination),
        "checkpoint_count": len(files),
        "extracted_now": extracted,
        "reused_by_sha256": reused,
        "member_hash_manifest_sha256": sha256_json(member_hashes),
    }
    atomic_json(destination.parent / "extraction_report.json", report)
    return report


def _expected_random_sequence(
    spec: w85.SplitSpec,
    continuation: int,
    population: pd.DataFrame,
    target_horizon: int,
) -> list[int]:
    train = np.asarray(spec.train_indices, dtype=int)
    initial = w85.initial_design(spec, population)
    remaining = np.setdiff1d(train, np.asarray(initial, dtype=int), assume_unique=False)
    rng = np.random.default_rng(w85.seed_u32(w85.random_order_key(spec, continuation)))
    order = remaining[rng.permutation(len(remaining))].astype(int).tolist()
    return initial + order[: target_horizon - 16]


def validate_frozen_payload(
    payload: dict[str, Any],
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    population: pd.DataFrame,
    *,
    source_horizon: int = SOURCE_HORIZON,
) -> dict[str, Any]:
    """Validate historical identity and information flow without refitting models."""

    require(arm in EXTENSION_ARMS, f"Unsupported extension arm: {arm}")
    if arm != "binary_random":
        require(continuation == 1, "binary_margin has exactly one continuation")
    identity = expected_identity(spec, arm, continuation)
    require(payload.get("protocol_id") == FROZEN_PROTOCOL_ID, "Historical protocol ID drift")
    require(payload.get("protocol_sha256") == FROZEN_PROTOCOL_SHA256, "Historical protocol hash drift")
    require(payload.get("identity") == identity, "Historical trajectory identity drift")
    require(payload.get("complete") is True, "Historical checkpoint is incomplete")
    require(int(payload.get("horizon", -1)) == source_horizon, "Historical checkpoint horizon drift")

    queried = [int(value) for value in payload.get("queried_indices", [])]
    initial = w85.initial_design(spec, population)
    train = set(int(value) for value in spec.train_indices)
    test = set(int(value) for value in spec.test_indices)
    require(len(queried) == source_horizon, "Historical queried count does not equal source horizon")
    require(len(set(queried)) == len(queried), "Historical queried indices are not unique")
    require(queried[:16] == initial, "Historical initial-design prefix drift")
    require(set(queried).issubset(train), "Historical acquisition left the training pool")
    require(set(queried).isdisjoint(test), "Historical acquisition touched the test fold")
    if arm == "binary_random":
        expected = _expected_random_sequence(spec, continuation, population, source_horizon)
        require(queried == expected, "Historical random order is not an exact seeded prefix")

    rows = payload.get("rows", [])
    expected_budgets = w85.declared_budgets(source_horizon)
    require([int(row["budget"]) for row in rows] == expected_budgets, "Historical evaluation-grid drift")
    for row in rows:
        budget = int(row["budget"])
        row_identity = {key: row[key] for key in identity}
        require(row_identity == identity, f"Historical metric identity drift at budget {budget}")
        key = w85.fit_seed_key(spec, arm, continuation, budget)
        require(row.get("fit_seed_key") == key, f"Historical fit-seed key drift at budget {budget}")
        require(int(row.get("fit_seed_u32", -1)) == w85.seed_u32(key), f"Historical fit seed drift at {budget}")

    mechanism = payload.get("mechanism", [])
    expected_selections = list(range(17, source_horizon + 1))
    require(
        [int(row["selection_budget"]) for row in mechanism] == expected_selections,
        "Historical acquisition-grid drift",
    )
    labels = population["has_keyhole"].astype(int).to_numpy()
    expected_acquisition = "predeclared_random_pool_order" if arm == "binary_random" else "classifier_margin"
    seen = set(initial)
    for row, budget in zip(mechanism, expected_selections):
        row_identity = {key: row[key] for key in identity}
        require(row_identity == identity, f"Historical mechanism identity drift at budget {budget}")
        selected = int(row["selected_population_row_index"])
        require(selected == queried[budget - 1], f"Historical queried/mechanism mismatch at budget {budget}")
        require(selected in train and selected not in seen, f"Historical invalid acquisition at budget {budget}")
        require(int(row["selected_label_revealed_after_selection"]) == int(labels[selected]), "Label audit drift")
        require(row.get("acquisition_definition") == expected_acquisition, "Acquisition method drift")
        require(row.get("candidate_pool_role") == "outer_training_pool_only", "Candidate-pool role drift")
        require(row.get("test_rows_available_to_acquisition") is False, "Test rows leaked to acquisition")
        require(row.get("hidden_pool_labels_available_to_acquisition") is False, "Hidden labels leaked")
        require(row.get("B1_available_to_acquisition") is False, "B1 leaked to acquisition")
        seen.add(selected)

    return {
        "identity": identity,
        "queried_count": len(queried),
        "row_count": len(rows),
        "mechanism_count": len(mechanism),
        "queried_prefix_sha256": sha256_json(queried),
    }


def _validate_extension_payload(
    payload: dict[str, Any],
    source_payload: dict[str, Any],
    source_checkpoint_sha256: str,
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    checkpoints: Sequence[int],
    target_horizon: int,
) -> None:
    identity = expected_identity(spec, arm, continuation)
    require(payload.get("extension_protocol_id") == EXTENSION_PROTOCOL_ID, "Extension protocol ID drift")
    require(payload.get("schema_version") == EXTENSION_SCHEMA_VERSION, "Extension schema drift")
    require(payload.get("frozen_protocol_sha256") == FROZEN_PROTOCOL_SHA256, "Extension frozen protocol drift")
    require(payload.get("source_checkpoint_sha256") == source_checkpoint_sha256, "Source checkpoint drift")
    require(payload.get("identity") == identity, "Extension trajectory identity drift")
    require(int(payload.get("source_horizon", -1)) == int(source_payload["horizon"]), "Source horizon drift")
    require(int(payload.get("target_horizon", -1)) == target_horizon, "Target horizon drift")
    require(payload.get("declared_extension_budgets") == list(checkpoints), "Extension grid drift")
    source_queried = [int(value) for value in source_payload["queried_indices"]]
    queried = [int(value) for value in payload.get("queried_indices", [])]
    require(queried[: len(source_queried)] == source_queried, "Historical queried prefix changed")
    require(len(queried) == len(set(queried)), "Extension queried indices are not unique")
    rows = payload.get("extension_rows", [])
    require(not rows or [int(row["budget"]) for row in rows] == sorted({int(row["budget"]) for row in rows}), "Extension rows are not unique and ordered")
    require(set(int(row["budget"]) for row in rows).issubset(set(checkpoints)), "Off-grid extension metric row")
    mechanism = payload.get("extension_mechanism", [])
    require(
        len(queried) == int(source_payload["horizon"]) + len(mechanism),
        "Extension queried/mechanism length drift",
    )
    require(
        [int(row["selection_budget"]) for row in mechanism]
        == list(range(int(source_payload["horizon"]) + 1, len(queried) + 1)),
        "Extension acquisition-grid drift",
    )
    if arm == "binary_random":
        require(
            payload.get("random_evaluation_policy_id") == RANDOM_EVALUATION_POLICY_ID,
            "Random checkpoint predates the selective evaluation policy",
        )


def validate_completed_extension_payload(
    payload: dict[str, Any],
    source_payload: dict[str, Any],
    source_checkpoint_sha256: str,
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    population: pd.DataFrame,
    *,
    checkpoints: Sequence[int] | None = None,
    target_horizon: int = TARGET_HORIZON,
) -> dict[str, Any]:
    """Fail closed on identity, acquisition flow, labels, and terminal coverage."""

    declared = list(checkpoints) if checkpoints is not None else extension_budgets(
        int(source_payload["horizon"]), target_horizon
    )
    _validate_extension_payload(
        payload,
        source_payload,
        source_checkpoint_sha256,
        spec,
        arm,
        continuation,
        declared,
        target_horizon,
    )
    require(payload.get("complete") is True, "Extension checkpoint is not complete")
    identity = expected_identity(spec, arm, continuation)
    source_horizon = int(source_payload["horizon"])
    queried = [int(value) for value in payload["queried_indices"]]
    train = set(int(value) for value in spec.train_indices)
    test = [int(value) for value in spec.test_indices]
    test_set = set(test)
    labels = population["has_keyhole"].astype(int).to_numpy()
    require(len(queried) == target_horizon, "Completed queried count does not equal target horizon")
    require(set(queried).issubset(train), "Extension acquisition left the training pool")
    require(set(queried).isdisjoint(test_set), "Extension acquisition touched the test fold")

    mechanism = payload.get("extension_mechanism", [])
    require(len(mechanism) == target_horizon - source_horizon, "Completed mechanism count drift")
    expected_acquisition = "predeclared_random_pool_order" if arm == "binary_random" else "classifier_margin"
    seen = set(int(value) for value in source_payload["queried_indices"])
    for row, budget in zip(mechanism, range(source_horizon + 1, target_horizon + 1)):
        require({key: row.get(key) for key in identity} == identity, f"Extension mechanism identity drift at {budget}")
        selected = int(row["selected_population_row_index"])
        require(int(row["selection_budget"]) == budget, f"Extension selection-budget drift at {budget}")
        require(selected == queried[budget - 1], f"Extension queried/mechanism mismatch at {budget}")
        require(selected in train and selected not in seen, f"Invalid extension acquisition at {budget}")
        require(int(row["selected_label_revealed_after_selection"]) == int(labels[selected]), f"Extension label audit drift at {budget}")
        require(row.get("acquisition_definition") == expected_acquisition, f"Extension acquisition method drift at {budget}")
        require(row.get("candidate_pool_role") == "outer_training_pool_only", f"Extension pool role drift at {budget}")
        require(row.get("test_rows_available_to_acquisition") is False, f"Test leakage flag at {budget}")
        require(row.get("hidden_pool_labels_available_to_acquisition") is False, f"Hidden-label leakage flag at {budget}")
        require(row.get("B1_available_to_acquisition") is False, f"B1 leakage flag at {budget}")
        seen.add(selected)

    if arm == "binary_random":
        require(
            queried == _expected_random_sequence(spec, continuation, population, target_horizon),
            "Completed random continuation differs from its seeded order",
        )

    rows = payload.get("extension_rows", [])
    for row in rows:
        budget = int(row["budget"])
        require({key: row.get(key) for key in identity} == identity, f"Extension metric identity drift at {budget}")
        key = w85.fit_seed_key(spec, arm, continuation, budget)
        require(row.get("fit_seed_key") == key, f"Extension fit-seed key drift at {budget}")
        require(int(row.get("fit_seed_u32", -1)) == w85.seed_u32(key), f"Extension fit seed drift at {budget}")

    predictions = payload.get("terminal_prediction_rows", [])
    require(len(predictions) == len(test), "Terminal prediction row count drift")
    require([int(row["population_row_index"]) for row in predictions] == test, "Terminal prediction fold coverage drift")
    for row, index in zip(predictions, test):
        require({key: row.get(key) for key in identity} == identity, "Terminal prediction identity drift")
        require(int(row.get("budget", -1)) == target_horizon, "Terminal prediction budget drift")
        require(str(row.get("experiment_name")) == str(population.iloc[index]["experiment_name"]), "Terminal prediction experiment identity drift")
        require(int(row.get("truth_has_keyhole", -1)) == int(labels[index]), "Terminal prediction truth drift")
        probability = float(row.get("probability_has_keyhole", math.nan))
        require(math.isfinite(probability) and 0.0 <= probability <= 1.0, "Invalid terminal probability")

    recomputed = persistent_crossing_evidence([*source_payload["rows"], *rows], source_horizon=source_horizon)
    recomputed = finalize_crossing_classification(recomputed, rows, target_horizon=target_horizon)
    saved = payload.get("persistent_crossing", {})
    for key in ("observed", "start_budget", "confirmation_budget", "final_classification"):
        require(saved.get(key) == recomputed.get(key), f"Persistent crossing metadata drift: {key}")
    return {
        "identity": identity,
        "queried_count": len(queried),
        "mechanism_count": len(mechanism),
        "terminal_prediction_count": len(predictions),
        "source_checkpoint_sha256": source_checkpoint_sha256,
        "extension_checkpoint_sha256": sha256_json(payload),
    }


def persistent_crossing_evidence(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str = PRIMARY_METRIC,
    target: float = PRIMARY_TARGET,
    source_horizon: int = SOURCE_HORIZON,
) -> dict[str, Any]:
    """Return both the crossing start and its third-checkpoint confirmation.

    The start budget is the historical Q definition.  The confirmation budget
    is required for correct horizon-specific censoring: a triple beginning at
    196 and completed at 204 is not yet observed at H=200.
    """

    ordered = sorted(rows, key=lambda row: int(row["budget"]))
    budgets = [int(row["budget"]) for row in ordered]
    require(len(budgets) == len(set(budgets)), "Duplicate budgets in crossing evidence")
    values = [float(row[metric]) for row in ordered]
    for index in range(len(values) - 2):
        if all(value >= target for value in values[index : index + 3]):
            start = budgets[index]
            confirmation = budgets[index + 2]
            return {
                "metric": metric,
                "target": target,
                "observed": True,
                "start_budget": start,
                "confirmation_budget": confirmation,
                "confirming_checkpoint_budgets": budgets[index : index + 3],
                "confirmed_in": "frozen_h160" if confirmation <= source_horizon else "week9_extension",
            }
    return {
        "metric": metric,
        "target": target,
        "observed": False,
        "start_budget": None,
        "confirmation_budget": None,
        "confirming_checkpoint_budgets": [],
        "confirmed_in": None,
    }


def finalize_crossing_classification(
    evidence: dict[str, Any],
    extension_rows: Sequence[dict[str, Any]],
    *,
    target_horizon: int,
) -> dict[str, Any]:
    result = dict(evidence)
    confirmation = result.get("confirmation_budget")
    result["observed_by_horizon"] = {
        str(horizon): bool(result["observed"] and int(confirmation) <= horizon)
        for horizon in (200, 240, 280, 320)
        if horizon <= target_horizon
    }
    terminal = [row for row in extension_rows if int(row["budget"]) == target_horizon]
    if not terminal:
        result.update(
            {
                "terminal_accuracy": None,
                "terminal_accuracy_below_target": None,
                "guaranteed_Q_gt_target_horizon": None,
                "final_classification": "in_progress",
            }
        )
    elif result["observed"]:
        result.update(
            {
                "terminal_accuracy": float(terminal[0][PRIMARY_METRIC]),
                "terminal_accuracy_below_target": float(terminal[0][PRIMARY_METRIC]) < PRIMARY_TARGET,
                "guaranteed_Q_gt_target_horizon": False,
                "final_classification": "persistent_crossing_confirmed",
            }
        )
    else:
        terminal_accuracy = float(terminal[0][PRIMARY_METRIC])
        below = terminal_accuracy < PRIMARY_TARGET
        result.update(
            {
                "terminal_accuracy": terminal_accuracy,
                "terminal_accuracy_below_target": below,
                "guaranteed_Q_gt_target_horizon": below,
                "final_classification": (
                    f"unresolved_terminal_below_target_guarantees_Q_gt_{target_horizon}"
                    if below
                    else "unresolved_terminal_at_or_above_target_Q_not_identified"
                ),
            }
        )
    return result


def continue_trajectory(
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    source_payload: dict[str, Any],
    source_checkpoint_sha256: str,
    population: pd.DataFrame,
    distances: np.ndarray,
    *,
    target_horizon: int = TARGET_HORIZON,
    checkpoint_step: int = 4,
    checkpoint_root: Path = EXTENSION_CHECKPOINTS,
    save_every: int = 5,
    save_terminal_predictions: bool = True,
) -> dict[str, Any]:
    """Continue one validated trajectory, atomically checkpointing progress."""

    source_horizon = int(source_payload["horizon"])
    checkpoints = extension_budgets(source_horizon, target_horizon, checkpoint_step)
    validate_frozen_payload(
        source_payload,
        spec,
        arm,
        continuation,
        population,
        source_horizon=source_horizon,
    )
    identity = expected_identity(spec, arm, continuation)
    checkpoint = extension_checkpoint_path(spec, arm, continuation, checkpoint_root)
    source_crossing = persistent_crossing_evidence(
        source_payload["rows"],
        source_horizon=source_horizon,
    )
    if checkpoint.is_file():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        restart_random = arm == "binary_random" and payload.get("random_evaluation_policy_id") != RANDOM_EVALUATION_POLICY_ID
        if restart_random:
            # Interrupted/complete pilot outputs used the superseded uniform
            # random grid. Random acquisition is seed-order-only, so restarting
            # from the immutable H=160 prefix is exact and avoids mixing policies.
            queried = [int(value) for value in source_payload["queried_indices"]]
            rows = []
            mechanism = []
            predictions = []
            crossing = source_crossing
        else:
            _validate_extension_payload(
                payload,
                source_payload,
                source_checkpoint_sha256,
                spec,
                arm,
                continuation,
                checkpoints,
                target_horizon,
            )
            if payload.get("complete") is True:
                refreshed = finalize_crossing_classification(
                    persistent_crossing_evidence(
                        [*source_payload["rows"], *payload.get("extension_rows", [])],
                        source_horizon=source_horizon,
                    ),
                    payload.get("extension_rows", []),
                    target_horizon=target_horizon,
                )
                if payload.get("persistent_crossing") != refreshed:
                    payload["persistent_crossing"] = refreshed
                    atomic_json(checkpoint, payload)
                validate_completed_extension_payload(
                    payload,
                    source_payload,
                    source_checkpoint_sha256,
                    spec,
                    arm,
                    continuation,
                    population,
                    checkpoints=checkpoints,
                    target_horizon=target_horizon,
                )
                return payload
            queried = [int(value) for value in payload["queried_indices"]]
            rows = list(payload.get("extension_rows", []))
            mechanism = list(payload.get("extension_mechanism", []))
            predictions = list(payload.get("terminal_prediction_rows", []))
            crossing = dict(payload.get("persistent_crossing", source_crossing))
    else:
        queried = [int(value) for value in source_payload["queried_indices"]]
        rows = []
        mechanism = []
        predictions = []
        crossing = source_crossing

    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    train_set = set(train.tolist())
    x = population.loc[:, w85.FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    scaler = StandardScaler().fit(x[train])
    x_scaled = scaler.transform(x)
    flags = w85.boundary_flags(spec, population, distances)
    completed = {int(row["budget"]) for row in rows}
    if arm == "binary_random":
        random_sequence = _expected_random_sequence(spec, continuation, population, target_horizon)
    else:
        random_sequence = []

    started_budget = len(queried)
    require(source_horizon <= started_budget <= target_horizon, "Invalid extension resume position")
    for budget in range(started_budget, target_horizon + 1):
        on_grid = budget in checkpoints and budget not in completed
        if arm == "binary_random":
            evaluate = on_grid and (budget == target_horizon or not crossing["observed"])
        else:
            evaluate = on_grid
        needs_acquisition = budget < target_horizon
        needs_fit = evaluate or (needs_acquisition and arm == "binary_margin")
        fit = None
        if needs_fit:
            key = w85.fit_seed_key(spec, arm, continuation, budget)
            fit = p6.fit_gpc(
                x[np.asarray(queried, dtype=int)],
                labels[np.asarray(queried, dtype=int)],
                scaler=scaler,
                seed=w85.seed_u32(key),
                restarts=0,
            )

        if evaluate:
            probability = p6.predict_gpc(fit, x[test])
            record: dict[str, Any] = {
                **identity,
                "budget": budget,
                "horizon": target_horizon,
                "analysis_status": (
                    "posthoc_selective_random_horizon_extension"
                    if arm == "binary_random"
                    else "posthoc_uniform_margin_horizon_extension"
                ),
                "fit_seed_key": w85.fit_seed_key(spec, arm, continuation, budget),
                "fit_seed_u32": w85.seed_u32(w85.fit_seed_key(spec, arm, continuation, budget)),
                "fit_status": fit.fit_status,
                "kernel": fit.kernel,
                "queried_keyhole_count": int(labels[np.asarray(queried, dtype=int)].sum()),
                "queried_non_keyhole_count": int(len(queried) - labels[np.asarray(queried, dtype=int)].sum()),
            }
            for name, flag in flags.items():
                for metric, value in w85.compute_metrics(labels[test], probability, flag).items():
                    record[f"{name}_{metric}"] = value
            rows.append(record)
            completed.add(budget)
            if not crossing["observed"]:
                crossing = persistent_crossing_evidence(
                    [*source_payload["rows"], *rows],
                    source_horizon=source_horizon,
                )
            if save_terminal_predictions and budget == target_horizon and not predictions:
                predictions = _format_prediction_rows(
                    spec,
                    arm,
                    continuation,
                    budget,
                    test,
                    labels[test],
                    probability,
                    population,
                )

        if needs_acquisition:
            if arm == "binary_random":
                next_index = int(random_sequence[budget])
                info = {"acquisition_definition": "predeclared_random_pool_order"}
            else:
                candidate = np.setdiff1d(train, np.asarray(queried, dtype=int), assume_unique=False)
                probabilities = p6.predict_gpc(fit, x[candidate])
                next_index, info = p6.choose_binary_candidate(
                    method=arm,
                    candidate_indices=candidate,
                    probabilities=probabilities,
                    pool_scaled=x_scaled,
                    queried_indices=queried,
                )
            require(next_index in train_set, "Extension acquisition selected outside training pool")
            require(next_index not in queried, "Extension acquisition repeated a queried row")
            mechanism.append(
                {
                    **identity,
                    "selection_budget": budget + 1,
                    "selected_population_row_index": next_index,
                    "selected_experiment_name": str(population.iloc[next_index]["experiment_name"]),
                    "selected_label_revealed_after_selection": int(labels[next_index]),
                    "candidate_pool_role": "outer_training_pool_only",
                    "test_rows_available_to_acquisition": False,
                    "hidden_pool_labels_available_to_acquisition": False,
                    "B1_available_to_acquisition": False,
                    **info,
                }
            )
            queried.append(next_index)

        should_save = budget == target_horizon or budget % save_every == 0 or evaluate
        if should_save:
            atomic_json(
                checkpoint,
                {
                    "extension_protocol_id": EXTENSION_PROTOCOL_ID,
                    "schema_version": EXTENSION_SCHEMA_VERSION,
                    "analysis_status": "posthoc_not_preregistered",
                    "frozen_commit": FROZEN_COMMIT,
                    "frozen_protocol_id": FROZEN_PROTOCOL_ID,
                    "frozen_protocol_sha256": FROZEN_PROTOCOL_SHA256,
                    "source_checkpoint_name": frozen_checkpoint_name(spec, arm, continuation),
                    "source_checkpoint_sha256": source_checkpoint_sha256,
                    "source_queried_prefix_sha256": sha256_json(source_payload["queried_indices"]),
                    "identity": identity,
                    "source_horizon": source_horizon,
                    "target_horizon": target_horizon,
                    "declared_extension_budgets": checkpoints,
                    "random_evaluation_policy_id": (
                        RANDOM_EVALUATION_POLICY_ID if arm == "binary_random" else None
                    ),
                    "persistent_crossing": finalize_crossing_classification(
                        crossing,
                        rows,
                        target_horizon=target_horizon,
                    ),
                    "queried_indices": queried,
                    "extension_rows": rows,
                    "extension_mechanism": mechanism,
                    "terminal_prediction_rows": predictions,
                    "complete": budget == target_horizon,
                },
            )

    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    _validate_extension_payload(
        payload,
        source_payload,
        source_checkpoint_sha256,
        spec,
        arm,
        continuation,
        checkpoints,
        target_horizon,
    )
    require(payload.get("complete") is True, "Extension trajectory did not complete")
    require(len(payload["queried_indices"]) == target_horizon, "Final queried count drift")
    actual_budgets = [int(row["budget"]) for row in payload["extension_rows"]]
    if arm == "binary_margin":
        require(actual_budgets == checkpoints, "Missing Margin checkpoints")
    else:
        evidence = payload["persistent_crossing"]
        confirmation = evidence.get("confirmation_budget")
        if evidence["observed"] and int(confirmation) <= source_horizon:
            expected_random_budgets = [target_horizon]
        elif evidence["observed"]:
            expected_random_budgets = [budget for budget in checkpoints if budget <= int(confirmation)]
            if target_horizon not in expected_random_budgets:
                expected_random_budgets.append(target_horizon)
        else:
            expected_random_budgets = list(checkpoints)
        require(actual_budgets == expected_random_budgets, "Selective Random checkpoint-grid drift")
    require(
        [int(row["selection_budget"]) for row in payload["extension_mechanism"]]
        == list(range(source_horizon + 1, target_horizon + 1)),
        "Missing extension acquisitions",
    )
    if arm == "binary_random":
        require(
            payload["queried_indices"] == _expected_random_sequence(spec, continuation, population, target_horizon),
            "Final random continuation differs from its seeded order",
        )
    if save_terminal_predictions:
        require(len(payload.get("terminal_prediction_rows", [])) == len(test), "Missing terminal predictions")
        validate_completed_extension_payload(
            payload,
            source_payload,
            source_checkpoint_sha256,
            spec,
            arm,
            continuation,
            population,
            checkpoints=checkpoints,
            target_horizon=target_horizon,
        )
    return payload


def _format_prediction_rows(
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    budget: int,
    test_indices: np.ndarray,
    truth: np.ndarray,
    probability: np.ndarray,
    population: pd.DataFrame,
) -> list[dict[str, Any]]:
    identity = expected_identity(spec, arm, continuation)
    return [
        {
            **identity,
            "budget": int(budget),
            "population_row_index": int(index),
            "experiment_name": str(population.iloc[int(index)]["experiment_name"]),
            "truth_has_keyhole": int(label),
            "probability_has_keyhole": float(probability_value),
        }
        for index, label, probability_value in zip(test_indices, truth, probability)
    ]


def generate_prediction_rows(
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
    budget: int,
    source_payload: dict[str, Any],
    source_checkpoint_sha256: str,
    population: pd.DataFrame,
    *,
    extension_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically recover full-81 predictions at H=40/80/160/320.

    The H=320 rows are returned directly from a completed extension checkpoint
    when available.  Historical budgets are refit once using their original
    queried prefix, scaler, fit-seed key, and zero-restart GPC contract.
    """

    require(budget in (40, 80, 160, 320), "Prediction budget must be one of 40, 80, 160, 320")
    validate_frozen_payload(source_payload, spec, arm, continuation, population)
    if budget == 320:
        require(extension_payload is not None, "H=320 predictions require an extension payload")
        validate_completed_extension_payload(
            extension_payload,
            source_payload,
            source_checkpoint_sha256,
            spec,
            arm,
            continuation,
            population,
        )
        saved = extension_payload.get("terminal_prediction_rows", [])
        if saved:
            require(len(saved) == len(spec.test_indices), "Saved terminal prediction count drift")
            return list(saved)
        queried = [int(value) for value in extension_payload["queried_indices"][:budget]]
    else:
        queried = [int(value) for value in source_payload["queried_indices"][:budget]]

    require(len(queried) == budget, f"Queried prefix unavailable for budget {budget}")
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x = population.loc[:, w85.FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    scaler = StandardScaler().fit(x[train])
    key = w85.fit_seed_key(spec, arm, continuation, budget)
    fit = p6.fit_gpc(
        x[np.asarray(queried, dtype=int)],
        labels[np.asarray(queried, dtype=int)],
        scaler=scaler,
        seed=w85.seed_u32(key),
        restarts=0,
    )
    probability = p6.predict_gpc(fit, x[test])
    return _format_prediction_rows(
        spec,
        arm,
        continuation,
        budget,
        test,
        labels[test],
        probability,
        population,
    )


def trajectory_jobs(specs: Sequence[w85.SplitSpec]) -> list[tuple[w85.SplitSpec, str, int]]:
    jobs: list[tuple[w85.SplitSpec, str, int]] = []
    for spec in specs:
        jobs.append((spec, "binary_margin", 1))
        jobs.extend((spec, "binary_random", continuation) for continuation in range(1, 31))
    require(len(jobs) == EXPECTED_TRAJECTORIES if len(specs) == 100 else True, "Trajectory count drift")
    return jobs


def _load_source_payload(
    source_root: Path,
    spec: w85.SplitSpec,
    arm: str,
    continuation: int,
) -> tuple[dict[str, Any], str]:
    path = source_root / frozen_checkpoint_name(spec, arm, continuation)
    require(path.is_file(), f"Missing historical checkpoint: {path}")
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _run_job(
    job: tuple[w85.SplitSpec, str, int],
    population: pd.DataFrame,
    distances: np.ndarray,
    source_root: Path,
    checkpoint_root: Path,
) -> dict[str, Any]:
    spec, arm, continuation = job
    source_payload, source_sha = _load_source_payload(source_root, spec, arm, continuation)
    started = time.perf_counter()
    payload = continue_trajectory(
        spec,
        arm,
        continuation,
        source_payload,
        source_sha,
        population,
        distances,
        checkpoint_root=checkpoint_root,
    )
    return {
        "run_id": spec.run_id,
        "arm": arm,
        "continuation_id": continuation,
        "complete": bool(payload["complete"]),
        "elapsed_seconds": time.perf_counter() - started,
    }


def validate_all_historical(
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
    source_root: Path = FROZEN_EXTRACTED,
    jobs: Iterable[tuple[w85.SplitSpec, str, int]] | None = None,
) -> dict[str, Any]:
    selected = list(jobs) if jobs is not None else trajectory_jobs(specs)
    counts = {"binary_margin": 0, "binary_random": 0}
    started = time.perf_counter()
    for spec, arm, continuation in selected:
        payload, _ = _load_source_payload(source_root, spec, arm, continuation)
        validate_frozen_payload(payload, spec, arm, continuation, population)
        counts[arm] += 1
    report = {
        "status": "PASS",
        "frozen_protocol_sha256": FROZEN_PROTOCOL_SHA256,
        "frozen_archive_sha256": FROZEN_ARCHIVE_SHA256,
        "validated_trajectories": len(selected),
        "counts_by_arm": counts,
        "elapsed_seconds": time.perf_counter() - started,
    }
    atomic_json(source_root.parent / "historical_validation_report.json", report)
    return report


def refresh_completed_metadata(
    *,
    source_root: Path = FROZEN_EXTRACTED,
    checkpoint_root: Path = EXTENSION_CHECKPOINTS,
) -> dict[str, Any]:
    """Recompute crossing metadata and fully validate all completed paths."""

    population = w85.load_population()
    specs = w85.build_splits(population)
    changed = 0
    validated = 0
    for spec, arm, continuation in trajectory_jobs(specs):
        source, source_sha = _load_source_payload(source_root, spec, arm, continuation)
        path = extension_checkpoint_path(spec, arm, continuation, checkpoint_root)
        payload = json.loads(path.read_text(encoding="utf-8"))
        refreshed = finalize_crossing_classification(
            persistent_crossing_evidence(
                [*source["rows"], *payload.get("extension_rows", [])],
                source_horizon=int(source["horizon"]),
            ),
            payload.get("extension_rows", []),
            target_horizon=TARGET_HORIZON,
        )
        if payload.get("persistent_crossing") != refreshed:
            payload["persistent_crossing"] = refreshed
            atomic_json(path, payload)
            changed += 1
        validate_completed_extension_payload(
            payload,
            source,
            source_sha,
            spec,
            arm,
            continuation,
            population,
        )
        validated += 1
    report = {"status": "PASS", "validated": validated, "crossing_metadata_refreshed": changed}
    atomic_json(checkpoint_root.parent / "completed_payload_validation_report.json", report)
    return report


def run_extension(
    *,
    workers: int,
    source_root: Path = FROZEN_EXTRACTED,
    checkpoint_root: Path = EXTENSION_CHECKPOINTS,
    limit_jobs: int | None = None,
) -> dict[str, Any]:
    validate_frozen_environment(check_archive=False)
    population = w85.load_population()
    specs = w85.build_splits(population)
    distances = w85.b1_distance(population)
    jobs = trajectory_jobs(specs)
    if limit_jobs is not None:
        require(limit_jobs > 0, "--limit-jobs must be positive")
        jobs = jobs[:limit_jobs]
    started = time.perf_counter()
    results = Parallel(n_jobs=workers, backend="loky", verbose=10)(
        delayed(_run_job)(job, population, distances, source_root, checkpoint_root) for job in jobs
    )
    elapsed = time.perf_counter() - started
    complete = sum(bool(result["complete"]) for result in results)
    report = {
        "extension_protocol_id": EXTENSION_PROTOCOL_ID,
        "analysis_status": "posthoc_not_preregistered",
        "source_horizon": SOURCE_HORIZON,
        "target_horizon": TARGET_HORIZON,
        "declared_extension_budgets": extension_budgets(),
        "workers": workers,
        "requested_trajectories": len(jobs),
        "complete_trajectories": complete,
        "full_design_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_margin_fit_count": PLANNED_MARGIN_FITS,
        "planned_random_fit_count_upper_bound": PLANNED_RANDOM_FITS_UPPER_BOUND,
        "planned_total_fit_count_upper_bound": PLANNED_TOTAL_FITS_UPPER_BOUND,
        "elapsed_seconds": elapsed,
        "per_job_results": results,
    }
    checkpoint_root.parent.mkdir(parents=True, exist_ok=True)
    name = "execution_report.json" if limit_jobs is None else f"execution_report_first_{limit_jobs}.json"
    atomic_json(checkpoint_root.parent / name, report)
    require(complete == len(jobs), "Not every requested extension trajectory completed")
    return report


def status(checkpoint_root: Path = EXTENSION_CHECKPOINTS) -> dict[str, Any]:
    files = sorted(checkpoint_root.glob("*.json"))
    complete = 0
    by_arm = {"binary_margin": 0, "binary_random": 0}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("complete") is True:
            complete += 1
            by_arm[str(payload["identity"]["arm"])] += 1
    return {
        "checkpoint_files": len(files),
        "complete_trajectories": complete,
        "complete_by_arm": by_arm,
        "expected_trajectories": EXPECTED_TRAJECTORIES,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "extract", "validate", "run", "status", "refresh"))
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--limit-jobs", type=int)
    args = parser.parse_args()
    if args.command == "preflight":
        print(json.dumps(validate_frozen_environment(check_archive=True), indent=2))
        return
    if args.command == "extract":
        print(json.dumps(extract_frozen_checkpoints(), indent=2))
        return
    if args.command == "status":
        print(json.dumps(status(), indent=2))
        return
    if not FROZEN_EXTRACTED.is_dir():
        extract_frozen_checkpoints()
    if args.command == "validate":
        population = w85.load_population()
        specs = w85.build_splits(population)
        jobs = trajectory_jobs(specs)
        if args.limit_jobs is not None:
            jobs = jobs[: args.limit_jobs]
        print(json.dumps(validate_all_historical(population, specs, jobs=jobs), indent=2))
        return
    if args.command == "refresh":
        print(json.dumps(refresh_completed_metadata(), indent=2))
        return
    print(json.dumps(run_extension(workers=args.workers, limit_jobs=args.limit_jobs), indent=2))


if __name__ == "__main__":
    main()
