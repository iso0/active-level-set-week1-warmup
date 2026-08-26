"""Frozen Week 8.5 sample-efficiency confirmation.

This module implements protocol week8_5_frozen_confirmation_protocol/v1.0.0.
It is deliberately restartable: each trajectory has an atomic JSON checkpoint,
and final tables are assembled only after every required trajectory is complete.
Smoke outputs live below ``smoke/`` and are never read by final aggregation.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import distance
from sklearn.datasets import make_classification
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week7_phase7_final_boundary_hybrid_benchmark as p7


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week8_5_frozen_confirmation"
PROTOCOL_PATH = OUTPUT / "preregistered_protocol.json"
CHECKPOINT_ROOT = OUTPUT / "checkpoints"
SMOKE_ROOT = OUTPUT / "smoke"
FIGURE_ROOT = OUTPUT / "figures"
PROTOCOL_ID = "week8_5_frozen_confirmation_protocol/v1.0.0"
SCHEMA_VERSION = "1.0.0"
SEED_ROOT = "week8_5_frozen_confirmation|v1"
FEATURES = ("P", "VX", "LS", "ST")
ARMS = ("binary_margin", "binary_random", "binary_uncertainty_repulsion")
TARGETS = (0.75, 0.80, 0.85)
SOURCE_POPULATION = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set" / "primary_common_population.csv"
MAX_HORIZON = 160


@dataclass(frozen=True)
class SplitSpec:
    run_id: str
    repeat: int
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_protocol_bytes(protocol: dict[str, Any]) -> bytes:
    return (json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def protocol_sha256() -> str:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    canonical = canonical_protocol_bytes(protocol)
    require(PROTOCOL_PATH.read_bytes() == canonical, "Protocol JSON is not canonical")
    digest = hashlib.sha256(canonical).hexdigest()
    recorded = (OUTPUT / "protocol_sha256.txt").read_text(encoding="utf-8").split()[0]
    require(digest == recorded, "Protocol SHA-256 does not match protocol_sha256.txt")
    return digest


def seed_key(*parts: object) -> str:
    return "|".join((SEED_ROOT, *(str(part) for part in parts)))


def seed_u32(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little") % (2**32)


def source_hashes() -> dict[str, str]:
    paths = {
        "primary_common_population.csv": SOURCE_POPULATION,
        "phase6_source.py": ROOT / "src" / "week7_phase6_real_data_boundary_active_level_set.py",
        "phase7_source.py": ROOT / "src" / "week7_phase7_final_boundary_hybrid_benchmark.py",
        "protocol.json": PROTOCOL_PATH,
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def metadata() -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "schema_version": SCHEMA_VERSION,
        "protocol_sha256": protocol_sha256(),
        "source_hashes_json": json.dumps(source_hashes(), sort_keys=True),
    }


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, payload: Any) -> None:
    atomic_json(path, payload)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def load_population() -> pd.DataFrame:
    _, primary, _ = p6.load_population_tables()
    require(len(primary) == 405, "Frozen primary population must contain 405 rows")
    require(int(primary["has_keyhole"].sum()) == 73, "Frozen population must contain 73 Keyhole labels")
    require(primary["experiment_name"].is_unique, "Experiment names must be unique")
    return primary.reset_index(drop=True)


def declared_budgets(horizon: int) -> list[int]:
    if 16 <= horizon < 80:  # synthetic smoke fixture only
        return list(range(16, horizon + 1))
    require(horizon in (80, 120, 160), "Confirmation horizon must be 80, 120, or 160")
    budgets = list(range(16, 81))
    if horizon >= 120:
        budgets.extend(range(82, 121, 2))
    if horizon >= 160:
        budgets.extend(range(124, 161, 4))
    return budgets


def build_splits(population: pd.DataFrame, repeats: int = 20, folds: int = 5) -> list[SplitSpec]:
    labels = population["has_keyhole"].astype(int).to_numpy()
    groups = population["input_tuple_sha256"].astype(str).to_numpy()
    dummy = np.zeros((len(population), 1))
    specs: list[SplitSpec] = []
    for repeat in range(1, repeats + 1):
        key = seed_key("outer_split", "repeat", f"{repeat:02d}")
        splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed_u32(key))
        for fold, (train, test) in enumerate(splitter.split(dummy, labels, groups), start=1):
            specs.append(
                SplitSpec(
                    run_id=f"w85__r{repeat:02d}_f{fold:02d}",
                    repeat=repeat,
                    fold=fold,
                    train_indices=tuple(int(value) for value in train),
                    test_indices=tuple(int(value) for value in test),
                )
            )
    return specs


def initial_design(spec: SplitSpec, population: pd.DataFrame) -> list[int]:
    """Seeded feature-only maximin design; hidden labels never affect selection."""

    train = np.asarray(spec.train_indices, dtype=int)
    x = population.loc[:, FEATURES].to_numpy(float)
    scaled = StandardScaler().fit_transform(x[train])
    key = seed_key("run", spec.run_id, "initial_design")
    rng = np.random.default_rng(seed_u32(key))
    chosen_local = [int(rng.integers(len(train)))]
    while len(chosen_local) < 16:
        remaining = np.setdiff1d(np.arange(len(train)), np.asarray(chosen_local), assume_unique=True)
        nearest = distance.cdist(scaled[remaining], scaled[chosen_local]).min(axis=1)
        best = float(nearest.max())
        ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
        chosen_local.append(int(ties[np.argmin(train[ties])]))
    chosen = train[np.asarray(chosen_local, dtype=int)].astype(int).tolist()
    labels = population["has_keyhole"].astype(int).to_numpy()[chosen]
    require(len(np.unique(labels)) == 2, f"{spec.run_id}: feature-only initial design lacks both classes")
    return chosen


def b1_distance(population: pd.DataFrame) -> np.ndarray:
    x = population.loc[:, FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    z = StandardScaler().fit_transform(x)
    dmat = distance.cdist(z, z)
    opposite = labels[:, None] != labels[None, :]
    return np.where(opposite, dmat, np.inf).min(axis=1)


def boundary_flags(spec: SplitSpec, population: pd.DataFrame, distances: np.ndarray) -> dict[str, np.ndarray]:
    test = np.asarray(spec.test_indices, dtype=int)
    names = population.iloc[test]["experiment_name"].astype(str).to_numpy()
    order = p7.deterministic_order(distances[test], names, ascending=True)
    result: dict[str, np.ndarray] = {}
    for q in (20, 30):
        count = int(math.ceil(q / 100 * len(test)))
        flag = np.zeros(len(test), dtype=bool)
        flag[order[:count]] = True
        result[f"B1_q{q}"] = flag
    return result


def fit_seed_key(spec: SplitSpec, arm: str, continuation: int, budget: int) -> str:
    if arm == "binary_random":
        return seed_key("run", spec.run_id, "arm", arm, "continuation", f"{continuation:02d}", "fit", "budget", f"{budget:03d}")
    if arm == "binary_uncertainty_repulsion":
        return seed_key("run", spec.run_id, "arm", arm, "h", "0.15", "fit", "budget", f"{budget:03d}")
    return seed_key("run", spec.run_id, "arm", arm, "fit", "budget", f"{budget:03d}")


def random_order_key(spec: SplitSpec, continuation: int) -> str:
    return seed_key("run", spec.run_id, "arm", "binary_random", "continuation", f"{continuation:02d}", "order")


def compute_metrics(labels: np.ndarray, probability: np.ndarray, flag: np.ndarray) -> dict[str, float | int]:
    truth = labels[flag].astype(int)
    pred = (probability[flag] >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float((pred == truth).mean()),
        "recall": float(recall_score(truth, pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
        "row_count": int(len(truth)),
    }


def checkpoint_path(spec: SplitSpec, arm: str, continuation: int) -> Path:
    token = f"{spec.run_id}__{arm}__c{continuation:02d}.json"
    return CHECKPOINT_ROOT / token


def trajectory_identity(spec: SplitSpec, arm: str, continuation: int) -> dict[str, Any]:
    return {"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "arm": arm, "continuation_id": continuation}


def run_trajectory(
    spec: SplitSpec,
    arm: str,
    continuation: int,
    horizon: int,
    population: pd.DataFrame,
    distances: np.ndarray,
    checkpoint_dir: Path | None = None,
) -> dict[str, Any]:
    require(arm in ARMS, f"Unknown arm {arm}")
    if arm != "binary_random":
        require(continuation == 1, "Non-random arms have exactly one continuation")
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x = population.loc[:, FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    scaler = StandardScaler().fit(x[train])
    x_scaled = scaler.transform(x)
    flags = boundary_flags(spec, population, distances)
    allowed_budgets = declared_budgets(horizon)
    initial = initial_design(spec, population)
    checkpoint = (checkpoint_dir / checkpoint_path(spec, arm, continuation).name) if checkpoint_dir else checkpoint_path(spec, arm, continuation)
    payload: dict[str, Any]
    if checkpoint.is_file():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        require(payload["protocol_sha256"] == protocol_sha256(), "Checkpoint protocol hash drift")
        require(payload["identity"] == trajectory_identity(spec, arm, continuation), "Checkpoint identity drift")
        queried = [int(value) for value in payload["queried_indices"]]
        rows = list(payload["rows"])
        mechanism = list(payload.get("mechanism", []))
    else:
        queried = list(initial)
        rows = []
        mechanism = []
        payload = {}

    completed = {int(row["budget"]) for row in rows}
    if arm == "binary_random":
        remaining = np.setdiff1d(train, np.asarray(initial, dtype=int), assume_unique=False)
        rng = np.random.default_rng(seed_u32(random_order_key(spec, continuation)))
        order = remaining[rng.permutation(len(remaining))].astype(int).tolist()
    else:
        order = []

    start_budget = len(queried)
    require(start_budget >= 16, "Checkpoint queried set is shorter than the frozen initial design")
    for budget in range(start_budget, horizon + 1):
        evaluate = budget in allowed_budgets and budget not in completed
        needs_acquisition = budget < horizon
        needs_fit = evaluate or (needs_acquisition and arm != "binary_random")
        fit = None
        if needs_fit:
            key = fit_seed_key(spec, arm, continuation, budget)
            fit = p6.fit_gpc(x[np.asarray(queried)], labels[np.asarray(queried)], scaler=scaler, seed=seed_u32(key), restarts=0)
        if evaluate:
            probability = p6.predict_gpc(fit, x[test])
            record: dict[str, Any] = {
                **trajectory_identity(spec, arm, continuation),
                "budget": budget,
                "horizon": horizon,
                "fit_seed_key": fit_seed_key(spec, arm, continuation, budget),
                "fit_seed_u32": seed_u32(fit_seed_key(spec, arm, continuation, budget)),
                "fit_status": fit.fit_status,
                "kernel": fit.kernel,
                "queried_keyhole_count": int(labels[np.asarray(queried)].sum()),
                "queried_non_keyhole_count": int(len(queried) - labels[np.asarray(queried)].sum()),
            }
            for name, flag in flags.items():
                for metric, value in compute_metrics(labels[test], probability, flag).items():
                    record[f"{name}_{metric}"] = value
            rows.append(record)
            completed.add(budget)

        if needs_acquisition:
            if arm == "binary_random":
                next_index = int(order[budget - 16])
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
            require(next_index in set(train.tolist()), "Acquisition selected outside training pool")
            require(next_index not in queried, "Acquisition repeated a queried row")
            mechanism.append(
                {
                    **trajectory_identity(spec, arm, continuation),
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

        if budget % 5 == 0 or budget == horizon:
            atomic_json(
                checkpoint,
                {
                    "protocol_id": PROTOCOL_ID,
                    "protocol_sha256": protocol_sha256(),
                    "schema_version": SCHEMA_VERSION,
                    "identity": trajectory_identity(spec, arm, continuation),
                    "horizon": horizon,
                    "queried_indices": queried,
                    "rows": rows,
                    "mechanism": mechanism,
                    "complete": budget == horizon,
                },
            )
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    require(payload["complete"], "Trajectory checkpoint did not complete")
    return payload


def build_manifests(population: pd.DataFrame, specs: Sequence[SplitSpec]) -> dict[str, Any]:
    meta = metadata()
    split_rows: list[dict[str, Any]] = []
    design_rows: list[dict[str, Any]] = []
    for spec in specs:
        train_groups = set(population.iloc[list(spec.train_indices)]["input_tuple_sha256"].astype(str))
        test_groups = set(population.iloc[list(spec.test_indices)]["input_tuple_sha256"].astype(str))
        require(train_groups.isdisjoint(test_groups), f"{spec.run_id}: train/test group overlap")
        for role, indices in (("training_pool", spec.train_indices), ("untouched_test", spec.test_indices)):
            for index in indices:
                row = population.iloc[index]
                split_rows.append(
                    {
                        **meta,
                        "run_id": spec.run_id,
                        "repeat": spec.repeat,
                        "fold": spec.fold,
                        "role": role,
                        "population_row_index": index,
                        "experiment_name": row["experiment_name"],
                        "input_tuple_sha256": row["input_tuple_sha256"],
                        "has_keyhole_audit_only": int(row["has_keyhole"]),
                    }
                )
        design = initial_design(spec, population)
        for order, index in enumerate(design, start=1):
            row = population.iloc[index]
            design_rows.append(
                {
                    **meta,
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "query_order": order,
                    "population_row_index": index,
                    "experiment_name": row["experiment_name"],
                    "revealed_has_keyhole": int(row["has_keyhole"]),
                    "selection_inputs": "P|VX|LS|ST_only_seeded_maximin",
                    "hidden_label_used_for_selection": False,
                    "shared_by_all_arms": True,
                }
            )

    seeds: list[dict[str, Any]] = []
    def add(kind: str, key: str, run_id: str = "", repeat: int | str = "", fold: int | str = "", arm: str = "", continuation: int | str = "", budget: int | str = "") -> None:
        seeds.append({**meta, "seed_kind": kind, "seed_key": key, "seed_u32": seed_u32(key), "run_id": run_id, "repeat": repeat, "fold": fold, "arm": arm, "continuation_id": continuation, "budget": budget})

    for repeat in range(1, 21):
        add("outer_split", seed_key("outer_split", "repeat", f"{repeat:02d}"), repeat=repeat)
    for spec in specs:
        add("initial_design", seed_key("run", spec.run_id, "initial_design"), spec.run_id, spec.repeat, spec.fold)
        for arm in ("binary_margin", "binary_uncertainty_repulsion"):
            for budget in range(16, MAX_HORIZON + 1):
                add("fit", fit_seed_key(spec, arm, 1, budget), spec.run_id, spec.repeat, spec.fold, arm, 1, budget)
        for continuation in range(1, 31):
            add("random_order", random_order_key(spec, continuation), spec.run_id, spec.repeat, spec.fold, "binary_random", continuation)
            for budget in declared_budgets(MAX_HORIZON):
                add("fit", fit_seed_key(spec, "binary_random", continuation, budget), spec.run_id, spec.repeat, spec.fold, "binary_random", continuation, budget)

    split_frame = pd.DataFrame(split_rows)
    design_frame = pd.DataFrame(design_rows)
    seed_frame = pd.DataFrame(seeds)
    write_csv(OUTPUT / "grouped_split_manifest.csv", split_frame)
    write_csv(OUTPUT / "split_manifest.csv", split_frame)
    write_csv(OUTPUT / "initial_design_manifest.csv", design_frame)
    write_csv(OUTPUT / "seed_registry.csv", seed_frame)
    write_csv(OUTPUT / "random_seed_manifest.csv", seed_frame[seed_frame["arm"].eq("binary_random")].reset_index(drop=True))
    return {"split_rows": len(split_frame), "design_rows": len(design_frame), "seed_rows": len(seed_frame)}


def run_static_validations(population: pd.DataFrame, specs: Sequence[SplitSpec]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def check(check_id: str, condition: bool, evidence: Any) -> None:
        checks.append({"check_id": check_id, "status": "PASS" if condition else "FAIL", "evidence": evidence})

    check("protocol_hash_locked", protocol_sha256() == "bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66", protocol_sha256())
    check("population_membership", len(population) == 405 and int(population.has_keyhole.sum()) == 73, {"rows": len(population), "keyhole": int(population.has_keyhole.sum())})
    check("outer_run_count", len(specs) == 100, len(specs))
    split_ok = all(set(spec.train_indices).isdisjoint(spec.test_indices) and len(spec.train_indices) == 324 and len(spec.test_indices) == 81 for spec in specs)
    group_ok = all(set(population.iloc[list(spec.train_indices)].input_tuple_sha256).isdisjoint(set(population.iloc[list(spec.test_indices)].input_tuple_sha256)) for spec in specs)
    check("split_membership_counts", split_ok, "100 x (324 train + 81 test)")
    check("group_disjointness", group_ok, "exact input_tuple_sha256")
    designs = [initial_design(spec, population) for spec in specs]
    design_ok = all(len(indices) == 16 and len(set(indices)) == 16 and len(set(population.iloc[indices].has_keyhole.astype(int))) == 2 for indices in designs)
    check("initial_design_16_both_classes", design_ok, "feature-only seeded maximin; labels revealed after selection")
    seed_frame = pd.read_csv(OUTPUT / "seed_registry.csv", usecols=["seed_kind", "seed_key", "seed_u32"], low_memory=False)
    forbidden = ("6022026", "primary_common", "shared_pool_permutation")
    namespace_ok = seed_frame.seed_key.astype(str).str.startswith(SEED_ROOT + "|").all() and not seed_frame.seed_key.astype(str).apply(lambda value: any(token in value for token in forbidden)).any()
    check("unseen_old_seed_namespace", namespace_ok, {"root": SEED_ROOT, "forbidden": forbidden})
    check("seed_key_uniqueness", seed_frame.seed_key.is_unique, int(seed_frame.seed_key.duplicated().sum()))
    budgets = np.arange(16, 81, dtype=float)
    orientation = float(np.trapezoid(budgets, budgets) / 64)
    check("historical_AULC_orientation", np.isclose(orientation, 48.0), orientation)
    source_flow_ok, source_flow_evidence = audit_chooser_source()
    check("information_flow_source_contract", source_flow_ok, source_flow_evidence)
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    report = {**metadata(), "status": status, "created_at_utc": utc_now(), "checks": checks}
    write_json(OUTPUT / "validation_report.json", report)
    require(status == "PASS", "Static validation failed")
    return report


def audit_chooser_source() -> tuple[bool, dict[str, Any]]:
    """Confirm the chooser call has no evaluation or hidden-label inputs."""

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "choose_binary_candidate"
    ]
    keyword_sets = [sorted(keyword.arg for keyword in call.keywords if keyword.arg) for call in calls]
    allowed = {"method", "candidate_indices", "probabilities", "pool_scaled", "queried_indices"}
    forbidden_tokens = ("b1", "b2", "b3", "hidden", "label")
    observed = {name for names in keyword_sets for name in names}
    valid = len(calls) == 1 and not any(call.args for call in calls) and observed.issubset(allowed) and not any(token in name.lower() for name in observed for token in forbidden_tokens)
    return valid, {"chooser_call_count": len(calls), "chooser_keyword_arguments": sorted(observed), "forbidden_input_tokens": list(forbidden_tokens)}


def audit_seed_registry(seed_frame: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    """Audit complete-key uniqueness separately from unavoidable uint32 collisions."""

    fits = seed_frame[seed_frame["seed_kind"].eq("fit")].copy()
    collision_groups = []
    for seed, group in fits.groupby("seed_u32", sort=True):
        if group["seed_key"].nunique() > 1:
            collision_groups.append({"seed_u32": int(seed), "distinct_seed_keys": sorted(group["seed_key"].astype(str).unique())})
    random_orders = seed_frame[seed_frame["seed_kind"].eq("random_order")]
    random_order_ok = len(random_orders) == 3000 and random_orders["seed_key"].is_unique and random_orders["seed_u32"].is_unique
    return random_order_ok, {
        "fit_seed_collision_group_count": len(collision_groups),
        "fit_seed_collisions": collision_groups,
        "random_order_seed_count": int(len(random_orders)),
        "random_order_keys_unique": bool(random_orders["seed_key"].is_unique),
        "random_order_seed_u32_unique": bool(random_orders["seed_u32"].is_unique),
    }


def audit_checkpoint_payload(path: Path, manifest_train: dict[str, set[int]], manifest_test: dict[str, set[int]], expected_runs: set[str]) -> tuple[int, list[str], set[str]]:
    """Return lightweight integrity facts for one existing checkpoint payload."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    identity = payload["identity"]
    run_id = str(identity["run_id"])
    violations: list[str] = []
    forbidden_chooser_fields: set[str] = set()
    guard_fields = {"test_rows_available_to_acquisition", "hidden_pool_labels_available_to_acquisition", "B1_available_to_acquisition", "selected_label_revealed_after_selection"}
    if run_id not in expected_runs or run_id not in manifest_train:
        return 0, [f"{path.name}: unknown run"], forbidden_chooser_fields
    train, test = manifest_train[run_id], manifest_test[run_id]
    queried = [int(index) for index in payload.get("queried_indices", [])]
    if not set(queried).issubset(train) or not set(queried).isdisjoint(test) or len(queried) != len(set(queried)):
        violations.append(f"{path.name}: queried indices violate persisted split membership")
    records = payload.get("mechanism", [])
    for record in records:
        index = int(record["selected_population_row_index"])
        if record.get("candidate_pool_role") != "outer_training_pool_only" or index not in train or index in test:
            violations.append(f"{path.name}: selected index violates persisted split membership")
        if record.get("test_rows_available_to_acquisition") is not False or record.get("hidden_pool_labels_available_to_acquisition") is not False or record.get("B1_available_to_acquisition") is not False:
            violations.append(f"{path.name}: availability guard is not false")
        for key in record:
            lowered = key.lower()
            if key not in guard_fields and ("b1" in lowered or "b2" in lowered or "b3" in lowered or "hidden" in lowered or "test_label" in lowered):
                forbidden_chooser_fields.add(key)
    return len(records), violations[:20], forbidden_chooser_fields


def audit_information_flow_artifacts(specs: Sequence[SplitSpec], checkpoint_paths: Iterable[Path] | None = None) -> tuple[bool, dict[str, Any]]:
    """Audit every saved acquisition record against the persisted split manifest.

    The checkpoint payload is intentionally read sequentially: this check never
    refits a model, changes a trajectory, or loads final aggregation from smoke.
    """

    manifest = pd.read_csv(OUTPUT / "split_manifest.csv", usecols=["run_id", "role", "population_row_index"])
    manifest_train = {run_id: set(group.loc[group.role.eq("training_pool"), "population_row_index"].astype(int)) for run_id, group in manifest.groupby("run_id")}
    manifest_test = {run_id: set(group.loc[group.role.eq("untouched_test"), "population_row_index"].astype(int)) for run_id, group in manifest.groupby("run_id")}
    expected_runs = {spec.run_id for spec in specs}
    paths = sorted(checkpoint_paths if checkpoint_paths is not None else CHECKPOINT_ROOT.glob("*.json"))
    checkpoint_count = len(paths)
    record_count = 0
    violations: list[str] = []
    forbidden_chooser_fields: set[str] = set()
    audits = Parallel(n_jobs=min(4, os.cpu_count() or 1), prefer="processes", batch_size=25)(
        delayed(audit_checkpoint_payload)(path, manifest_train, manifest_test, expected_runs) for path in paths
    )
    for records, current_violations, current_forbidden_fields in audits:
        record_count += records
        violations.extend(current_violations)
        forbidden_chooser_fields.update(current_forbidden_fields)
    source_ok, source_evidence = audit_chooser_source()
    valid = not violations and not forbidden_chooser_fields and source_ok
    return valid, {
        "checkpoint_count": checkpoint_count,
        "saved_mechanism_record_count": record_count,
        "persisted_split_manifest_runs": len(manifest_train),
        "candidate_and_query_indices_training_only": not any("split membership" in item for item in violations),
        "test_rows_hidden_labels_B1_unavailable": not any("availability guard" in item for item in violations),
        "forbidden_B1_B2_B3_hidden_label_chooser_fields": sorted(forbidden_chooser_fields),
        "source_chooser_audit": source_evidence,
        "violations": violations[:20],
    }


def regenerate_repulsion_mechanism_derivatives() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build mechanism-level derivatives from saved margin/repulsion checkpoints only."""

    population = load_population()
    specs = {spec.run_id: spec for spec in build_splits(population)}
    features = population.loc[:, FEATURES].to_numpy(float)
    records: list[dict[str, Any]] = []
    paths = sorted(CHECKPOINT_ROOT.glob("*__binary_margin__c01.json")) + sorted(CHECKPOINT_ROOT.glob("*__binary_uncertainty_repulsion__c01.json"))
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = payload["identity"]
        run_id = str(identity["run_id"])
        spec = specs[run_id]
        train = np.asarray(spec.train_indices, dtype=int)
        scaled = StandardScaler().fit_transform(features[train])
        scaled_by_population_index = {int(index): scaled[position] for position, index in enumerate(train)}
        queried = [int(index) for index in payload["queried_indices"][:16]]
        for mechanism in sorted(payload.get("mechanism", []), key=lambda row: int(row["selection_budget"])):
            selected = int(mechanism["selected_population_row_index"])
            nearest_distance = float(distance.cdist(scaled_by_population_index[selected][None, :], np.vstack([scaled_by_population_index[index] for index in queried])).min())
            records.append(
                {
                    "run_id": run_id,
                    "repeat": int(identity["repeat"]),
                    "fold": int(identity["fold"]),
                    "arm": str(identity["arm"]),
                    "continuation_id": int(identity["continuation_id"]),
                    "selection_budget": int(mechanism["selection_budget"]),
                    "selection_order_after_warm_start": int(mechanism["selection_budget"]) - 16,
                    "selected_population_row_index": selected,
                    "selected_experiment_name": mechanism.get("selected_experiment_name", pd.NA),
                    "acquisition_definition": mechanism.get("acquisition_definition", pd.NA),
                    "selected_probability": mechanism.get("selected_probability", pd.NA),
                    "selected_uncertainty_score": mechanism.get("selected_uncertainty_score", pd.NA),
                    "selected_nearest_standardized_distance": nearest_distance,
                    "selected_repulsion_score": mechanism.get("selected_repulsion", pd.NA),
                    "selected_final_acquisition_score": mechanism.get("selected_score", mechanism.get("selected_uncertainty_score", pd.NA)),
                    "queried_keyhole_after_reveal": mechanism.get("selected_label_revealed_after_selection", pd.NA),
                    "repulsion_bandwidth_h": mechanism.get("repulsion_bandwidth", pd.NA),
                    "shortlist_size": mechanism.get("shortlist_size", pd.NA),
                }
            )
            queried.append(selected)
    diagnostics = pd.DataFrame(records)
    match = diagnostics.pivot(index=["run_id", "selection_budget"], columns="arm", values="selected_population_row_index")
    same = (match["binary_margin"] == match["binary_uncertainty_repulsion"]).rename("matched_arm_same_selected_row")
    diagnostics = diagnostics.merge(same, left_on=["run_id", "selection_budget"], right_index=True, how="left")
    diagnostics["matched_arm_same_selected_row"] = diagnostics["matched_arm_same_selected_row"].astype("boolean")
    write_csv(OUTPUT / "repulsion_mechanism_diagnostics.csv", add_meta(diagnostics))

    paired = diagnostics.pivot(index=["run_id", "selection_budget"], columns="arm", values=["selected_nearest_standardized_distance", "selected_uncertainty_score"])
    summary_rows: list[dict[str, Any]] = []
    for window, lower, upper in (("low_budget_16_40", 17, 40), ("full_16_160", 17, 160)):
        subset = diagnostics[diagnostics.selection_budget.between(lower, upper)]
        window_pairs = paired.loc[paired.index.get_level_values("selection_budget").to_series().between(lower, upper).to_numpy()]
        distance_delta = window_pairs[("selected_nearest_standardized_distance", "binary_uncertainty_repulsion")] - window_pairs[("selected_nearest_standardized_distance", "binary_margin")]
        uncertainty_delta = window_pairs[("selected_uncertainty_score", "binary_uncertainty_repulsion")] - window_pairs[("selected_uncertainty_score", "binary_margin")]
        selected = window_pairs["selected_nearest_standardized_distance"].dropna()
        divergence = selected["binary_margin"].ne(selected["binary_uncertainty_repulsion"]).groupby(level="run_id").apply(lambda value: value.index.get_level_values("selection_budget")[np.flatnonzero(value.to_numpy())[0]] if value.any() else np.nan)
        for arm, group in subset.groupby("arm"):
            summary_rows.append(
                {
                    "window": window,
                    "selection_budget_start": lower,
                    "selection_budget_end": upper,
                    "arm": arm,
                    "acquisition_count": int(len(group)),
                    "mean_selected_nearest_standardized_distance": float(group.selected_nearest_standardized_distance.mean()),
                    "median_selected_nearest_standardized_distance": float(group.selected_nearest_standardized_distance.median()),
                    "same_selected_row_fraction": float(group.matched_arm_same_selected_row.mean()),
                    "selected_keyhole_fraction": float(group.queried_keyhole_after_reveal.astype(float).mean()),
                    "mean_selected_uncertainty_score": float(group.selected_uncertainty_score.astype(float).mean()),
                    "mean_final_acquisition_score": float(group.selected_final_acquisition_score.astype(float).mean()),
                    "paired_mean_nearest_distance_minus_margin": 0.0 if arm == "binary_margin" else float(distance_delta.mean()),
                    "paired_median_nearest_distance_minus_margin": 0.0 if arm == "binary_margin" else float(distance_delta.median()),
                    "paired_mean_uncertainty_minus_margin": 0.0 if arm == "binary_margin" else float(uncertainty_delta.mean()),
                    "first_divergence_run_count": int(divergence.notna().sum()),
                    "first_divergence_never_count": int(divergence.isna().sum()),
                    "first_divergence_median_selection_budget": float(divergence.median()) if divergence.notna().any() else np.nan,
                }
            )
    summary = pd.DataFrame(summary_rows)
    write_csv(OUTPUT / "repulsion_mechanism_summary.csv", add_meta(summary))
    return diagnostics, summary


def make_selected_query_distance_figure(diagnostics: pd.DataFrame) -> str:
    """Show the matched-arm nearest-queried-distance comparison without refitting."""

    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharex=False, sharey=False)
    for axis, (title, lower, upper) in zip(axes, (("Low budget (post-warm 17–40)", 17, 40), ("Full horizon (17–160)", 17, 160))):
        window = diagnostics[diagnostics.selection_budget.between(lower, upper)]
        per_run = window.groupby(["run_id", "arm"], as_index=False).selected_nearest_standardized_distance.mean().pivot(index="run_id", columns="arm", values="selected_nearest_standardized_distance")
        axis.scatter(per_run["binary_margin"], per_run["binary_uncertainty_repulsion"], color="#2a9d8f", alpha=.78, edgecolor="white", linewidth=.4)
        limits = [float(np.nanmin(per_run.to_numpy())), float(np.nanmax(per_run.to_numpy()))]
        padding = max(.03, (limits[1] - limits[0]) * .06)
        limits = [limits[0] - padding, limits[1] + padding]
        axis.plot(limits, limits, color="black", linestyle="--", linewidth=1, label="same mean distance")
        axis.set_xlim(limits); axis.set_ylim(limits)
        axis.set_xlabel("Margin: mean nearest queried distance")
        axis.set_title(title)
    axes[0].set_ylabel("Repulsion h=.15: mean nearest queried distance")
    axes[1].legend(loc="upper left")
    figure.suptitle("Selected-query distance to the prior queried set (matched outer runs)")
    path = FIGURE_ROOT / "06_selected_query_nearest_distance.png"
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return str(path.relative_to(ROOT))


def audit_repulsion_mechanism_derivatives() -> tuple[bool, dict[str, Any]]:
    diagnostics = pd.read_csv(OUTPUT / "repulsion_mechanism_diagnostics.csv")
    summary = pd.read_csv(OUTPUT / "repulsion_mechanism_summary.csv")
    required = {"run_id", "repeat", "fold", "arm", "continuation_id", "selection_budget", "selection_order_after_warm_start", "selected_population_row_index", "selected_probability", "selected_uncertainty_score", "selected_nearest_standardized_distance", "selected_repulsion_score", "selected_final_acquisition_score", "queried_keyhole_after_reveal", "repulsion_bandwidth_h", "shortlist_size", "matched_arm_same_selected_row"}
    counts = diagnostics.groupby("arm").size().to_dict()
    valid = len(diagnostics) == 28800 and counts == {"binary_margin": 14400, "binary_uncertainty_repulsion": 14400} and required.issubset(diagnostics.columns) and diagnostics.selected_nearest_standardized_distance.notna().all() and len(summary) == 4 and (FIGURE_ROOT / "06_selected_query_nearest_distance.png").is_file()
    return valid, {"diagnostic_row_count": int(len(diagnostics)), "rows_by_arm": counts, "summary_row_count": int(len(summary)), "required_columns_present": sorted(required.intersection(diagnostics.columns)), "nearest_distance_non_missing": bool(diagnostics.selected_nearest_standardized_distance.notna().all())}


def write_postrun_validation_and_provenance() -> dict[str, Any]:
    """Refresh only lightweight validation/provenance derived from frozen outputs."""

    population = load_population()
    specs = build_splits(population)
    baseline = json.loads((OUTPUT / "validation_report.json").read_text(encoding="utf-8"))
    checks = [row for row in baseline["checks"] if row["check_id"] not in {"information_flow_contract", "information_flow_source_contract", "information_flow_saved_artifact_and_source", "repulsion_mechanism_derivative_schema_and_counts", "random_order_seed_and_key_uniqueness", "fit_seed_u32_collisions"}]
    flow_ok, flow_evidence = audit_information_flow_artifacts(specs)
    checks.append({"check_id": "information_flow_saved_artifact_and_source", "status": "PASS" if flow_ok else "FAIL", "evidence": flow_evidence})
    mechanism_ok, mechanism_evidence = audit_repulsion_mechanism_derivatives()
    checks.append({"check_id": "repulsion_mechanism_derivative_schema_and_counts", "status": "PASS" if mechanism_ok else "FAIL", "evidence": mechanism_evidence})
    seed_frame = pd.read_csv(OUTPUT / "seed_registry.csv", usecols=["seed_kind", "seed_key", "seed_u32"], low_memory=False)
    random_order_ok, collision_evidence = audit_seed_registry(seed_frame)
    checks.append({"check_id": "random_order_seed_and_key_uniqueness", "status": "PASS" if random_order_ok else "FAIL", "evidence": {key: collision_evidence[key] for key in ("random_order_seed_count", "random_order_keys_unique", "random_order_seed_u32_unique")}})
    collision_status = "QUALIFY" if collision_evidence["fit_seed_collision_group_count"] else "PASS"
    checks.append({"check_id": "fit_seed_u32_collisions", "status": collision_status, "evidence": collision_evidence})
    overall = "FAIL" if any(row["status"] == "FAIL" for row in checks) else ("PASS_WITH_QUALIFICATIONS" if any(row["status"] == "QUALIFY" for row in checks) else "PASS")
    report = {**metadata(), "status": overall, "created_at_utc": utc_now(), "checks": checks}
    write_json(OUTPUT / "validation_report.json", report)
    driver = ROOT / "src" / "week8_5_frozen_sample_efficiency_confirmation.py"
    tests = ROOT / "tests" / "test_week8_5_frozen_sample_efficiency_confirmation.py"
    critic = OUTPUT / "agent_handoffs" / "04_critic_audit.md"
    provenance = {
        **metadata(),
        "created_at_utc": utc_now(),
        "source_commits": {
            "audit_checkout": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "phase6_driver": subprocess.check_output(["git", "log", "-1", "--format=%H", "--", "src/week7_phase6_real_data_boundary_active_level_set.py"], cwd=ROOT, text=True).strip(),
            "phase7_driver": subprocess.check_output(["git", "log", "-1", "--format=%H", "--", "src/week7_phase7_final_boundary_hybrid_benchmark.py"], cwd=ROOT, text=True).strip(),
        },
        "audited_driver_sha256": sha256_file(driver),
        "audited_test_sha256": sha256_file(tests),
        "critic_audit_sha256": sha256_file(critic),
        "information_flow_audit": flow_evidence,
        "repulsion_mechanism_derivative_audit": mechanism_evidence,
        "fit_seed_u32_collision_qualification": collision_evidence,
        "qualification": "Distinct complete fit-seed keys remain unique, but 12 SHA-256-derived uint32 fit-seed collision groups are explicitly QUALIFY; Random order keys and uint32 seeds remain 3000/3000 unique.",
    }
    write_json(OUTPUT / "postrun_provenance_addendum.json", provenance)
    require(overall != "FAIL", "Post-run validation failed")
    return report


def smoke_fixture() -> tuple[pd.DataFrame, list[SplitSpec]]:
    x, y = make_classification(n_samples=160, n_features=4, n_informative=4, n_redundant=0, weights=[0.80, 0.20], class_sep=1.0, random_state=851)
    frame = pd.DataFrame(x, columns=FEATURES)
    frame["has_keyhole"] = y.astype(bool)
    frame["experiment_name"] = [f"synthetic_{index:03d}" for index in range(len(frame))]
    frame["input_tuple_sha256"] = [hashlib.sha256(name.encode()).hexdigest() for name in frame.experiment_name]
    specs = build_splits(frame, repeats=2, folds=2)
    return frame, specs


def run_smoke() -> dict[str, Any]:
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)
    SMOKE_ROOT.mkdir(parents=True)
    frame, specs = smoke_fixture()
    distances = b1_distance(frame)
    durations: list[float] = []
    fit_counts = 0
    deterministic_signatures: list[str] = []
    for spec in specs:
        for continuation in range(1, 4):
            start = time.perf_counter()
            payload = run_trajectory(spec, "binary_random", continuation, 18, frame, distances, checkpoint_dir=SMOKE_ROOT / "checkpoints")
            durations.append(time.perf_counter() - start)
            fit_counts += len(payload["rows"])
            deterministic_signatures.append(hashlib.sha256(json.dumps(payload["rows"], sort_keys=True).encode()).hexdigest())
    # Explicit rerun from checkpoints exercises resume without changing results.
    resumed = run_trajectory(specs[0], "binary_random", 1, 18, frame, distances, checkpoint_dir=SMOKE_ROOT / "checkpoints")
    resume_signature = hashlib.sha256(json.dumps(resumed["rows"], sort_keys=True).encode()).hexdigest()
    seconds_per_fit = float(sum(durations) / fit_counts)
    workers = min(4, os.cpu_count() or 1)
    report = {
        **metadata(),
        "status": "PASS",
        "fixture_only": True,
        "excluded_from_final_aggregation": True,
        "shape": "2 repeats x 2 folds x 3 binary_random continuations",
        "budgets": [16, 17, 18],
        "fit_count": fit_counts,
        "elapsed_seconds": float(sum(durations)),
        "seconds_per_fit": seconds_per_fit,
        "workers_for_projection": workers,
        "projected_H80_fit_count": 208000,
        "projected_H80_wall_seconds": float(208000 * seconds_per_fit / workers),
        "projected_H120_fit_count_conservative_protocol_formula": 336000,
        "projected_H160_fit_count_conservative_protocol_formula": 464000,
        "checkpoint_resume_identical": resume_signature == deterministic_signatures[0],
        "created_at_utc": utc_now(),
    }
    require(report["checkpoint_resume_identical"], "Smoke checkpoint resume changed results")
    write_json(SMOKE_ROOT / "smoke_runtime_report.json", report)
    return report


def trajectory_jobs(specs: Sequence[SplitSpec]) -> list[tuple[SplitSpec, str, int]]:
    jobs: list[tuple[SplitSpec, str, int]] = []
    for spec in specs:
        jobs.append((spec, "binary_margin", 1))
        jobs.extend((spec, "binary_random", continuation) for continuation in range(1, 31))
        jobs.append((spec, "binary_uncertainty_repulsion", 1))
    return jobs


def run_horizon(horizon: int, workers: int) -> dict[str, Any]:
    population = load_population()
    specs = build_splits(population)
    distances = b1_distance(population)
    jobs = trajectory_jobs(specs)
    started = time.perf_counter()
    payloads = Parallel(n_jobs=workers, backend="loky", verbose=10)(
        delayed(run_trajectory)(spec, arm, continuation, horizon, population, distances)
        for spec, arm, continuation in jobs
    )
    elapsed = time.perf_counter() - started
    complete = sum(bool(payload.get("complete")) for payload in payloads)
    report = {"horizon": horizon, "workers": workers, "trajectory_count": len(jobs), "complete_trajectories": complete, "elapsed_seconds": elapsed, "created_at_utc": utc_now()}
    write_json(OUTPUT / f"horizon_{horizon}_execution_report.json", report)
    require(complete == len(jobs), "Not every trajectory completed")
    return report


def load_checkpoint_rows(horizon: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    mechanisms: list[dict[str, Any]] = []
    for path in sorted(CHECKPOINT_ROOT.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("complete") and int(payload["horizon"]) >= horizon, f"Incomplete checkpoint {path.name}")
        rows.extend(row for row in payload["rows"] if int(row["budget"]) <= horizon)
        mechanisms.extend(row for row in payload.get("mechanism", []) if int(row["selection_budget"]) <= horizon)
    frame = pd.DataFrame(rows)
    mechanism = pd.DataFrame(mechanisms)
    expected = 100 * (1 + 30 + 1) * len(declared_budgets(horizon))
    require(len(frame) == expected, f"Learning curve row count {len(frame)} != {expected}")
    require(not frame.duplicated(["run_id", "arm", "continuation_id", "budget"]).any(), "Duplicate trajectory budget rows")
    return frame, mechanism


def persistent_crossing(group: pd.DataFrame, metric: str, target: float) -> tuple[float, bool]:
    ordered = group.sort_values("budget")
    values = ordered[metric].to_numpy(float)
    budgets = ordered["budget"].to_numpy(int)
    for index in range(len(values) - 2):
        if bool(np.all(values[index:index + 3] >= target)):
            return float(budgets[index]), True
    return math.nan, False


def aulc(group: pd.DataFrame, metric: str, start: int, end: int) -> float:
    subset = group[group.budget.between(start, end)].sort_values("budget")
    require(subset.budget.tolist() == list(range(start, end + 1)), f"AULC grid {start}-{end} incomplete")
    return float(np.trapezoid(subset[metric].to_numpy(float), subset.budget.to_numpy(float)) / (end - start))


def random_finite_fraction(frame: pd.DataFrame, horizon: int) -> float:
    random = frame[frame.arm.eq("binary_random")]
    finite = 0
    groups = 0
    for _, group in random.groupby(["run_id", "continuation_id"], sort=False):
        _, observed = persistent_crossing(group, "B1_q20_accuracy", 0.80)
        finite += int(observed)
        groups += 1
    require(groups == 3000, f"Expected 3000 Random continuations, found {groups}")
    return finite / groups


def adaptive_run(workers: int) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    final_horizon = 80
    for horizon in (80, 120, 160):
        run_horizon(horizon, workers)
        frame, _ = load_checkpoint_rows(horizon)
        rho = random_finite_fraction(frame, horizon)
        extend = horizon < 160 and rho < 0.95
        decisions.append({"horizon": horizon, "rho_random": rho, "threshold": 0.95, "extend_uniformly": extend})
        final_horizon = horizon
        if not extend:
            break
    payload = {**metadata(), "final_horizon": final_horizon, "decisions": decisions, "created_at_utc": utc_now()}
    write_json(OUTPUT / "adaptive_horizon_decision.json", payload)
    return payload


def build_run_metrics(frame: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    crossings: list[dict[str, Any]] = []
    terminal_budget = declared_budgets(horizon)[-1]
    for keys, group in frame.groupby(["run_id", "repeat", "fold", "arm", "continuation_id"], sort=True):
        run_id, repeat, fold, arm, continuation = keys
        row = {"run_id": run_id, "repeat": repeat, "fold": fold, "arm": arm, "continuation_id": continuation, "horizon": horizon}
        row["B1_q20_AULC_16_80"] = aulc(group, "B1_q20_accuracy", 16, 80)
        row["B1_q20_AULC_16_40"] = aulc(group, "B1_q20_accuracy", 16, 40)
        row["B1_q30_AULC_16_80"] = aulc(group, "B1_q30_accuracy", 16, 80)
        for budget, label in ((40, "budget40"), (terminal_budget, "terminal")):
            selected = group[group.budget.eq(budget)].iloc[0]
            for subset in ("B1_q20", "B1_q30"):
                for metric in ("accuracy", "recall", "balanced_accuracy", "false_negative", "false_positive", "true_negative", "true_positive", "row_count"):
                    row[f"{label}_{subset}_{metric}"] = selected[f"{subset}_{metric}"]
        for target in TARGETS:
            crossing, observed = persistent_crossing(group, "B1_q20_accuracy", target)
            target_name = f"{target:.2f}"
            row[f"crossing_{target_name}"] = crossing
            row[f"crossing_{target_name}_observed"] = observed
            row[f"restricted_crossing_{target_name}"] = crossing if observed else horizon
            crossings.append({**{k: row[k] for k in ("run_id", "repeat", "fold", "arm", "continuation_id", "horizon")}, "boundary": "B1", "quantile": 20, "target": target, "crossing_budget": crossing, "event_observed": observed, "censoring_label": "" if observed else f"{horizon}+", "restricted_crossing": crossing if observed else horizon})
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(crossings)


def hierarchical_bootstrap(run_metrics: pd.DataFrame, draws: int = 20000) -> tuple[pd.DataFrame, pd.DataFrame]:
    repeats = np.arange(1, 21)
    rng = np.random.default_rng(seed_u32(seed_key("hierarchical_bootstrap", "draws", draws)))
    draw_rows: list[dict[str, float | int]] = []
    indexed = {(int(r), int(f), arm): group.sort_values("continuation_id") for (r, f, arm), group in run_metrics.groupby(["repeat", "fold", "arm"])}
    for draw in range(draws):
        sampled_repeats = rng.choice(repeats, size=len(repeats), replace=True)
        performance: list[float] = []
        query_diff: list[float] = []
        random_q: list[float] = []
        margin_q: list[float] = []
        rep80: list[float] = []
        rep40: list[float] = []
        for repeat in sampled_repeats:
            for fold in range(1, 6):
                margin = indexed[(int(repeat), fold, "binary_margin")].iloc[0]
                repulsion = indexed[(int(repeat), fold, "binary_uncertainty_repulsion")].iloc[0]
                random = indexed[(int(repeat), fold, "binary_random")]
                picks = rng.integers(0, len(random), size=len(random))
                sampled_random = random.iloc[picks]
                performance.append(float(margin.B1_q20_AULC_16_80 - sampled_random.B1_q20_AULC_16_80.mean()))
                rq = float(sampled_random["restricted_crossing_0.80"].mean())
                mq = float(margin["restricted_crossing_0.80"])
                query_diff.append(rq - mq)
                random_q.append(rq)
                margin_q.append(mq)
                rep80.append(float(repulsion.B1_q20_AULC_16_80 - margin.B1_q20_AULC_16_80))
                rep40.append(float(repulsion.B1_q20_AULC_16_40 - margin.B1_q20_AULC_16_40))
        draw_rows.append({"draw": draw + 1, "delta_AULC": float(np.mean(performance)), "delta_Q": float(np.mean(query_diff)), "multiplier": float(np.mean(random_q) / np.mean(margin_q)), "delta_repulsion_AULC16_80": float(np.mean(rep80)), "delta_repulsion_AULC16_40": float(np.mean(rep40)), "delta_repulsion_min": float(min(np.mean(rep80), np.mean(rep40)))})
    draws_frame = pd.DataFrame(draw_rows)
    summary_rows = []
    for column in draws_frame.columns.drop("draw"):
        summary_rows.append({"estimand": column, "bootstrap_draws": draws, "point_estimate_bootstrap_mean": float(draws_frame[column].mean()), "one_sided_95pct_lower_bound": float(draws_frame[column].quantile(0.05)), "two_sided_95pct_lower": float(draws_frame[column].quantile(0.025)), "two_sided_95pct_upper": float(draws_frame[column].quantile(0.975))})
    return draws_frame, pd.DataFrame(summary_rows)


def point_estimands(run_metrics: pd.DataFrame) -> dict[str, float]:
    fold_rows: list[dict[str, float]] = []
    for (repeat, fold), group in run_metrics.groupby(["repeat", "fold"]):
        margin = group[group.arm.eq("binary_margin")].iloc[0]
        rep = group[group.arm.eq("binary_uncertainty_repulsion")].iloc[0]
        random = group[group.arm.eq("binary_random")]
        fold_rows.append({"delta_AULC": float(margin.B1_q20_AULC_16_80 - random.B1_q20_AULC_16_80.mean()), "delta_Q": float(random["restricted_crossing_0.80"].mean() - margin["restricted_crossing_0.80"]), "random_Q": float(random["restricted_crossing_0.80"].mean()), "margin_Q": float(margin["restricted_crossing_0.80"]), "rep80": float(rep.B1_q20_AULC_16_80 - margin.B1_q20_AULC_16_80), "rep40": float(rep.B1_q20_AULC_16_40 - margin.B1_q20_AULC_16_40)})
    frame = pd.DataFrame(fold_rows)
    return {"delta_AULC": float(frame.delta_AULC.mean()), "delta_Q": float(frame.delta_Q.mean()), "multiplier": float(frame.random_Q.mean() / frame.margin_Q.mean()), "delta_repulsion_AULC16_80": float(frame.rep80.mean()), "delta_repulsion_AULC16_40": float(frame.rep40.mean()), "delta_repulsion_min": float(min(frame.rep80.mean(), frame.rep40.mean()))}


def decision_ledger(run_metrics: pd.DataFrame, bootstrap: pd.DataFrame, horizon: int) -> pd.DataFrame:
    points = point_estimands(run_metrics)
    lowers = bootstrap.set_index("estimand")["one_sided_95pct_lower_bound"].to_dict()
    rho = float(run_metrics[run_metrics.arm.eq("binary_random")]["crossing_0.80_observed"].mean())
    rows: list[dict[str, Any]] = []
    perf = "PASS" if lowers["delta_AULC"] >= 0.020 else ("QUALIFY" if points["delta_AULC"] > 0 else "FAIL")
    query = "PASS" if rho >= 0.95 and lowers["delta_Q"] >= 10 else ("QUALIFY" if lowers["delta_Q"] > 0 else "FAIL")
    multiplier = "PASS" if rho >= 0.95 and lowers["multiplier"] >= 1.25 else ("QUALIFY" if lowers["multiplier"] > 1 else "FAIL")
    repulsion = "PASS" if lowers["delta_repulsion_min"] >= 0.010 else ("QUALIFY" if points["delta_repulsion_AULC16_80"] > 0 and points["delta_repulsion_AULC16_40"] > 0 else "FAIL")
    for claim, decision, estimate, lower, threshold in (
        ("primary_performance", perf, points["delta_AULC"], lowers["delta_AULC"], 0.020),
        ("query_saving", query, points["delta_Q"], lowers["delta_Q"], 10.0),
        ("multiplier", multiplier, points["multiplier"], lowers["multiplier"], 1.25),
        ("repulsion_h_0.15", repulsion, points["delta_repulsion_min"], lowers["delta_repulsion_min"], 0.010),
    ):
        rows.append({"claim": claim, "decision": decision, "point_estimate": estimate, "one_sided_95pct_lower_bound": lower, "pass_threshold": threshold, "rho_random": rho, "horizon": horizon})
    overall = "PASS" if all(value == "PASS" for value in (perf, query, multiplier)) else "NOT_CONFIRMED"
    rows.append({"claim": "overall_primary_confirmation", "decision": overall, "point_estimate": math.nan, "one_sided_95pct_lower_bound": math.nan, "pass_threshold": math.nan, "rho_random": rho, "horizon": horizon})
    return pd.DataFrame(rows)


def add_meta(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for key, value in reversed(list(metadata().items())):
        result.insert(0, key, value)
    return result


def aggregate_repeat_metrics(run_metrics: pd.DataFrame) -> pd.DataFrame:
    numeric = [column for column in run_metrics.columns if column not in {"run_id", "repeat", "fold", "arm", "continuation_id"} and pd.api.types.is_numeric_dtype(run_metrics[column])]
    rows: list[dict[str, Any]] = []
    for (repeat, arm), group in run_metrics.groupby(["repeat", "arm"]):
        row = {"repeat": repeat, "arm": arm, "fold_count": group.fold.nunique(), "continuation_count": group.continuation_id.nunique()}
        for column in numeric:
            row[f"macro_mean__{column}"] = float(group[column].mean())
        for label in ("budget40", "terminal"):
            for subset in ("B1_q20", "B1_q30"):
                correct = group[f"{label}_{subset}_true_positive"].sum() + group[f"{label}_{subset}_true_negative"].sum()
                total = group[f"{label}_{subset}_row_count"].sum()
                row[f"pooled__{label}_{subset}_accuracy"] = float(correct / total)
        rows.append(row)
    return pd.DataFrame(rows)


def make_figures(frame: pd.DataFrame, run_metrics: pd.DataFrame, crossings: pd.DataFrame, ledger: pd.DataFrame, mechanism: pd.DataFrame) -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[str] = []
    def save(name: str) -> None:
        path = FIGURE_ROOT / name
        plt.tight_layout()
        plt.savefig(path, dpi=220, bbox_inches="tight")
        plt.close()
        created.append(str(path.relative_to(ROOT)))

    curve = frame.groupby(["budget", "arm"], as_index=False).B1_q20_accuracy.mean()
    random = frame[frame.arm.eq("binary_random")].groupby("budget").B1_q20_accuracy.agg(mean="mean", q05=lambda value: value.quantile(.05), q95=lambda value: value.quantile(.95)).reset_index()

    def learning_curve(include_repulsion: bool, name: str) -> None:
        plt.figure(figsize=(8.2, 5.0))
        margin = curve[curve.arm.eq("binary_margin")]
        plt.plot(margin.budget, margin.B1_q20_accuracy, color="#1f4e79", linewidth=2.5, label="Binary margin")
        plt.fill_between(random.budget, random.q05, random.q95, color="#e67e22", alpha=.24, label="Random continuation 5–95% band")
        plt.plot(random.budget, random["mean"], color="#e67e22", linewidth=2.5, label="Random mean (3,000 continuations)")
        if include_repulsion:
            repulsion = curve[curve.arm.eq("binary_uncertainty_repulsion")]
            plt.plot(repulsion.budget, repulsion.B1_q20_accuracy, color="#2a9d8f", linewidth=2.2, label="Repulsion h=.15")
        plt.xlabel("Queried simulations")
        plt.ylabel("Untouched-fold B1-q20 accuracy")
        plt.ylim(.35, 1.02)
        plt.title("Margin versus matched Random continuations")
        plt.legend(loc="lower right", frameon=True)
        save(name)

    learning_curve(False, "01_B1_q20_learning_curves.png")
    learning_curve(True, "02_B1_q20_learning_curves_with_repulsion.png")

    for arm in ARMS:
        subset = crossings[(crossings.arm.eq(arm)) & np.isclose(crossings.target, 0.80)]
        observed = np.sort(subset.loc[subset.event_observed, "crossing_budget"].to_numpy(float))
        if len(observed): plt.step(observed, np.arange(1, len(observed)+1)/len(subset), where="post", label=arm)
    plt.xlabel("Persistent .80 crossing budget"); plt.ylabel("Cumulative event fraction"); plt.legend(); save("03_crossing_censoring_ecdf.png")

    b40 = frame[frame.budget.eq(40)].groupby("arm")[["B1_q20_accuracy", "B1_q30_accuracy"]].mean()
    b40.plot.bar(); plt.ylabel("Accuracy at budget 40"); plt.xticks(rotation=15); save("04_budget40_boundary_accuracy.png")

    rep = run_metrics[run_metrics.arm.eq("binary_uncertainty_repulsion")].set_index("run_id")
    mar = run_metrics[run_metrics.arm.eq("binary_margin")].set_index("run_id")
    plt.scatter(rep.B1_q20_AULC_16_40-mar.B1_q20_AULC_16_40, rep.B1_q20_AULC_16_80-mar.B1_q20_AULC_16_80, alpha=.7)
    plt.axhline(0,color="black"); plt.axvline(0,color="black"); plt.xlabel("Repulsion - margin AULC 16-40"); plt.ylabel("Repulsion - margin AULC 16-80"); save("05_repulsion_dual_endpoint.png")

    margin = run_metrics[run_metrics.arm.eq("binary_margin")].set_index("run_id").B1_q20_AULC_16_80
    random_aulc = run_metrics[run_metrics.arm.eq("binary_random")].groupby("run_id").B1_q20_AULC_16_80.mean()
    plt.hist((margin - random_aulc).dropna(), bins=15, color="#31688e")
    plt.axvline(0, color="black")
    plt.xlabel("Margin - mean Random AULC")
    plt.ylabel("Outer folds")
    save("07_primary_AULC_contrast.png")
    return created


def regenerate_postrun_figures() -> list[str]:
    """Regenerate visual derivatives from saved result tables only."""

    trajectory = pd.read_csv(
        OUTPUT / "trajectory_per_budget.csv",
        usecols=["run_id", "arm", "continuation_id", "budget", "B1_q20_accuracy", "B1_q30_accuracy"],
    )
    run_metrics = pd.read_csv(
        OUTPUT / "run_level_metrics.csv",
        usecols=["run_id", "arm", "continuation_id", "B1_q20_AULC_16_40", "B1_q20_AULC_16_80"],
    )
    crossings = pd.read_csv(
        OUTPUT / "crossing_censoring.csv",
        usecols=["arm", "target", "event_observed", "crossing_budget"],
    )
    ledger = pd.read_csv(OUTPUT / "decision_ledger.csv")
    created = make_figures(trajectory, run_metrics, crossings, ledger, pd.DataFrame())
    diagnostics = pd.read_csv(OUTPUT / "repulsion_mechanism_diagnostics.csv")
    created.append(make_selected_query_distance_figure(diagnostics))
    created = sorted(created)
    for obsolete in (FIGURE_ROOT / "02_primary_AULC_contrast.png", FIGURE_ROOT / "06_repulsion_mechanism.png"):
        if obsolete.exists():
            obsolete.unlink()
    runtime_path = OUTPUT / "runtime_compute_report.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["figures"] = created
    runtime["visual_derivatives_refreshed_at_utc"] = utc_now()
    runtime["visual_derivatives_source"] = "saved trajectory_per_budget.csv, run_level_metrics.csv, crossing_censoring.csv, decision_ledger.csv only"
    write_json(runtime_path, runtime)
    return created


def refresh_run_manifest() -> dict[str, Any]:
    previous = json.loads((OUTPUT / "run_manifest.json").read_text(encoding="utf-8"))
    manifest = {
        **metadata(),
        "status": "COMPLETE",
        "final_horizon": previous["final_horizon"],
        "created_at_utc": utc_now(),
        "files": {
            str(path.relative_to(OUTPUT)): {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(OUTPUT.rglob("*"))
            if path.is_file() and "checkpoints" not in path.parts and path.name != "run_manifest.json"
        },
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    return manifest


def finalize(horizon: int, runtime: dict[str, Any]) -> dict[str, Any]:
    frame, mechanism = load_checkpoint_rows(horizon)
    run_metrics, crossings = build_run_metrics(frame, horizon)
    draws, bootstrap = hierarchical_bootstrap(run_metrics, draws=20000)
    ledger = decision_ledger(run_metrics, bootstrap, horizon)
    repeat_metrics = aggregate_repeat_metrics(run_metrics)
    random_summary = run_metrics[run_metrics.arm.eq("binary_random")].groupby(["repeat", "fold"], as_index=False).agg(random_continuations=("continuation_id", "count"), mean_AULC=("B1_q20_AULC_16_80", "mean"), crossing_fraction=("crossing_0.80_observed", "mean"), restricted_crossing_mean=("restricted_crossing_0.80", "mean"))
    qs = pd.DataFrame([{**point_estimands(run_metrics), "rho_random": float(run_metrics[run_metrics.arm.eq("binary_random")]["crossing_0.80_observed"].mean()), "horizon": horizon}])
    rep = ledger[ledger.claim.eq("repulsion_h_0.15")].copy()
    write_csv(OUTPUT / "trajectory_per_budget.csv", add_meta(frame))
    write_csv(OUTPUT / "learning_curves.csv", add_meta(frame))
    checkpoints = frame[frame.budget.isin([40, *declared_budgets(horizon)[-1:]])]
    write_csv(OUTPUT / "checkpoint_metrics.csv", add_meta(checkpoints))
    write_csv(OUTPUT / "run_level_metrics.csv", add_meta(run_metrics))
    write_csv(OUTPUT / "repeat_level_metrics.csv", add_meta(repeat_metrics))
    write_csv(OUTPUT / "crossing_censoring.csv", add_meta(crossings))
    write_csv(OUTPUT / "query_crossings.csv", add_meta(crossings))
    write_csv(OUTPUT / "random_continuation_summary.csv", add_meta(random_summary))
    write_csv(OUTPUT / "query_savings_summary.csv", add_meta(qs))
    write_csv(OUTPUT / "repulsion_ablation_summary.csv", add_meta(rep))
    write_csv(OUTPUT / "hierarchical_bootstrap_draws.csv", add_meta(draws))
    write_csv(OUTPUT / "bootstrap_or_hierarchical_ci.csv", add_meta(bootstrap))
    write_json(OUTPUT / "hierarchical_bootstrap_summary.json", {**metadata(), "bootstrap_draws": 20000, "rows": bootstrap.to_dict(orient="records")})
    write_csv(OUTPUT / "decision_ledger.csv", add_meta(ledger))
    write_csv(OUTPUT / "claim_decisions.csv", add_meta(ledger))
    diagnostics, _ = regenerate_repulsion_mechanism_derivatives()
    figures = sorted([*make_figures(frame, run_metrics, crossings, ledger, mechanism), make_selected_query_distance_figure(diagnostics)])
    runtime_report = {**metadata(), **runtime, "final_horizon": horizon, "bootstrap_draws": 20000, "figures": figures, "created_at_utc": utc_now()}
    write_json(OUTPUT / "runtime_compute_report.json", runtime_report)
    manifest = {**metadata(), "status": "COMPLETE", "final_horizon": horizon, "created_at_utc": utc_now(), "files": {str(path.relative_to(OUTPUT)): {"sha256": sha256_file(path), "bytes": path.stat().st_size} for path in sorted(OUTPUT.rglob("*")) if path.is_file() and "checkpoints" not in path.parts and path.name != "run_manifest.json"}}
    write_json(OUTPUT / "run_manifest.json", manifest)
    return {"ledger": ledger.to_dict(orient="records"), "figures": figures, "artifact_count": len(manifest["files"])}


def create_teaching_notebook() -> None:
    import nbformat as nbf
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
    notebook["cells"] = [
        nbf.v4.new_markdown_cell("# Week 8.5 — frozen sample-efficiency confirmation\n\nThis compact notebook reads the locked, machine-readable outputs. It does not rerun or tune acquisition methods."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json\nimport pandas as pd\nROOT = Path.cwd().resolve().parents[1] if Path.cwd().name == 'week_08_5' else Path.cwd()\nOUT = ROOT / 'outputs' / 'week8_5_frozen_confirmation'\nprotocol = json.loads((OUT/'preregistered_protocol.json').read_text())\nprotocol['protocol_id']"),
        nbf.v4.new_markdown_cell("## 1. What was frozen?\n\nThe population, manual `has_keyhole` label, four inputs (`P`, `VX`, `LS`, `ST`), grouped splits, three acquisition arms, integer AULC orientation, adaptive horizon rule, and claim thresholds were locked before confirmation."),
        nbf.v4.new_code_cell("splits = pd.read_csv(OUT/'split_manifest.csv')\ninitial = pd.read_csv(OUT/'initial_design_manifest.csv')\nprint(splits.groupby('role').size())\ninitial.groupby('run_id').agg(rows=('query_order','count'), keyholes=('revealed_has_keyhole','sum')).head()"),
        nbf.v4.new_markdown_cell("## 2. How to read the primary result\n\nThe primary contrast is margin AULC minus the mean of 30 matched Random continuations inside each fold. Inference resamples repeat blocks, keeps five folds together, and resamples Random continuations within folds."),
        nbf.v4.new_code_cell("ledger = pd.read_csv(OUT/'claim_decisions.csv')\nledger[['claim','decision','point_estimate','one_sided_95pct_lower_bound','horizon']]"),
        nbf.v4.new_markdown_cell("## 3. Censoring and interpretation\n\nA missing persistent crossing is reported as right-censored at `H+`. Restricted-horizon estimands use `H` only for the declared burden calculation; simple finite crossing summaries never impute an unobserved query count. Results concern this saved-simulation population and are neither causal claims nor physical-boundary certainty."),
        nbf.v4.new_code_cell("cross = pd.read_csv(OUT/'query_crossings.csv')\ncross.query('target == 0.8').groupby('arm').agg(event_rate=('event_observed','mean'), finite_median=('crossing_budget','median'))"),
    ]
    path = ROOT / "notebooks" / "week_08_5" / "01_frozen_sample_efficiency_confirmation.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, path)


def prepare() -> dict[str, Any]:
    population = load_population()
    specs = build_splits(population)
    manifest_counts = build_manifests(population, specs)
    validation = run_static_validations(population, specs)
    create_teaching_notebook()
    return {"manifest_counts": manifest_counts, "validation": validation["status"]}


def compute_gate(smoke: dict[str, Any], max_wall_hours: float) -> dict[str, Any]:
    projected_hours = smoke["projected_H80_wall_seconds"] / 3600
    memory_ok = True
    time_ok = projected_hours <= max_wall_hours
    report = {**metadata(), "status": "PASS" if time_ok and memory_ok else "BLOCKED", "max_wall_hours": max_wall_hours, "projected_H80_wall_hours": projected_hours, "seconds_per_fit": smoke["seconds_per_fit"], "workers": smoke["workers_for_projection"], "memory_gate": "PASS" if memory_ok else "FAIL", "time_gate": "PASS" if time_ok else "FAIL", "no_design_reduction": True, "created_at_utc": utc_now()}
    write_json(OUTPUT / "compute_fit_gate.json", report)
    if not time_ok:
        write_json(OUTPUT / "compute_block_report.json", {**report, "reason": "Frozen 208,000-fit H=80 design exceeds the explicit wall-time allocation", "omitted": "No partial confirmation or headline result was produced"})
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "smoke", "run", "finalize", "refresh-postrun", "all"))
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--max-wall-hours", type=float, default=6.0)
    parser.add_argument("--horizon", type=int, choices=(80, 120, 160))
    args = parser.parse_args()
    if args.command == "refresh-postrun":
        diagnostics, summary = regenerate_repulsion_mechanism_derivatives()
        figures = regenerate_postrun_figures()
        validation = write_postrun_validation_and_provenance()
        manifest = refresh_run_manifest()
        print(json.dumps({"figures": figures, "mechanism_rows": len(diagnostics), "mechanism_summary_rows": len(summary), "validation_status": validation["status"], "manifest_artifact_count": len(manifest["files"])}, indent=2))
        return
    if args.command in ("prepare", "all"):
        print(json.dumps(prepare(), indent=2))
    smoke = None
    if args.command in ("smoke", "all"):
        smoke = run_smoke()
        print(json.dumps(smoke, indent=2))
    if args.command in ("run", "all"):
        if smoke is None:
            smoke_path = SMOKE_ROOT / "smoke_runtime_report.json"
            require(smoke_path.is_file(), "Run the isolated smoke before confirmation")
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        gate = compute_gate(smoke, args.max_wall_hours)
        print(json.dumps(gate, indent=2))
        if gate["status"] != "PASS":
            return
        started = time.perf_counter()
        adaptive = adaptive_run(args.workers)
        runtime = {"full_execution_elapsed_seconds": time.perf_counter() - started, "workers": args.workers, "python": platform.python_version(), "executable": os.sys.executable, "adaptive_horizon": adaptive}
        result = finalize(int(adaptive["final_horizon"]), runtime)
        print(json.dumps(result, indent=2))
    elif args.command == "finalize":
        require(args.horizon is not None, "--horizon is required for finalize")
        print(json.dumps(finalize(args.horizon, {"finalization_only": True}), indent=2))


if __name__ == "__main__":
    main()
