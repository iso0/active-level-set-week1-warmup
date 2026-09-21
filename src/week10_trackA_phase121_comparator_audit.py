"""Locked Week 10 audit of the two missing Phase 1.21 acquisition comparators.

This module does not edit the frozen Phase 1.20/1.21 implementation or outputs.
It adds only:
  * early8__margin, to separate the early-start effect from coverage acquisition;
  * a live recreation of the historical Week 8.5 Binary-GPC margin policy,
    with every resulting prefix evaluated by the same frozen M3 evaluator.

The audit is a post-result attribution study on the same 405 simulations.  It is
not external validation and not a second independent replication.
"""
from __future__ import annotations

import os

# Freeze numerical threading before NumPy/scikit-learn are imported.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
import tarfile
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import sklearn
from joblib import Parallel, delayed

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_20_early_start as early
from src import week9_phase1_21_simplification_replication as p121


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week10_trackA_phase120_122_audit" / "phase121_comparator_audit"
PROTOCOL = OUT / "AUDIT_PROTOCOL.json"
PROTOCOL_SHA = "512f470c0611ba38bc68d1c36d0d3e77ef926ed9e1d639933f8180fd5600709e"
EXECUTION_FREEZE = OUT / "EXECUTION_FREEZE.json"
PREFLIGHT = OUT / "preflight_validation.json"
STORED_VALIDATION = OUT / "stored_arm_validation.json"
A0_PARITY = OUT / "a0_recreation_parity.json"
LEAKAGE_GATES = OUT / "invariance_and_leakage_gates.json"
CHECKPOINTS = OUT / "checkpoints"
A0_SELECTOR = OUT / "a0_selector_checkpoints"
PARITY_SELECTOR = OUT / "a0_parity_checkpoints"
GATE_CHECKPOINTS = OUT / "runner_gate_checkpoints"
RUNNER_GATE = OUT / "early16_runner_gate.json"
LOG = OUT / "EXECUTION_LOG.md"
A0_BUNDLE = ROOT / "outputs" / "week8_5_frozen_confirmation" / "week8_5_checkpoint_bundle.tar.gz"
A0_BUNDLE_PUBLISHED_SHA256 = "1004fc299e00db6f1b2b89e4407f5ac8b2c4815d1169bcaad43dacdebacf72a9"
P121_INVARIANCE = ROOT / "outputs" / "week9_phase1_21_simplification_replication" / "invariance_audit.json"
W85_VALIDATION = ROOT / "outputs" / "week8_5_frozen_confirmation" / "validation_report.json"
P121_REPLICATION = ROOT / "outputs" / "week9_phase1_21_simplification_replication" / "REPLICATION_RESULT.json"
W85_PROTOCOL_ORIGINAL = ROOT / "outputs" / "week8_5_frozen_confirmation" / "preregistered_protocol.json"
W85_PROTOCOL_SHA_RECORD = ROOT / "outputs" / "week8_5_frozen_confirmation" / "protocol_sha256.txt"
W85_PROTOCOL_CANONICAL = OUT / "week8_5_preregistered_protocol_canonical.json"
W85_PROTOCOL_COMPATIBILITY = OUT / "week8_5_protocol_canonicalization.json"

EARLY8_MARGIN = "early8__margin"
A0_LIVE = "historical_binary_A0_live"
MARGIN = "margin"
CANDIDATE_A = "coverage_then_margin_B40"
CANDIDATE_B = "early8__coverage_then_margin_B40"
REPEATS = tuple(range(61, 121))
PRIMARY_DRAWS = 20_000
SIGN_FLIP_DRAWS = 100_000
NEW_PRIMARY_CONTRASTS = ("B_minus_early8_margin_new", "A_minus_historical_binary_A0_live_new")
ANALYSIS_ENDPOINTS = (
    ("B1_q20", "accuracy", 80),
    ("B1_q20", "accuracy", 40),
    ("B1_q20", "balanced_accuracy", 80),
    ("B1_q20", "balanced_accuracy", 40),
    ("B1_q30", "accuracy", 80),
    ("B1_q30", "accuracy", 40),
    ("B1_q30", "balanced_accuracy", 80),
    ("B1_q30", "balanced_accuracy", 40),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def atomic_gzip_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(json_safe(payload), sort_keys=True) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(gzip.compress(blob, compresslevel=6, mtime=0))
    temporary.replace(path)


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def read_gzip_json(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


def append_log(text: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")


def protocol_payload() -> dict[str, Any]:
    require(PROTOCOL.is_file(), "AUDIT_PROTOCOL.json is missing")
    require(sha256_file(PROTOCOL) == PROTOCOL_SHA, "audit protocol hash drift")
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    require(payload["protocol_id"] == "week10_trackA_phase121_comparator_audit/v1.0.0", "protocol id drift")
    return payload


def validate_pinned_sources(protocol: dict[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in protocol["pinned_sha256"].items():
        path = ROOT / relative
        require(path.is_file(), f"missing pinned input: {relative}")
        observed[relative] = sha256_file(path)
        require(observed[relative] == expected, f"pinned hash drift: {relative}")
    return observed


def split_hash(spec: Any, role: str) -> str:
    indices = spec.train_indices if role == "train" else spec.test_indices
    return hashlib.sha256((",".join(map(str, indices)) + "\n").encode()).hexdigest()


def population_hash(population: pd.DataFrame) -> str:
    columns = ["experiment_name", "input_tuple_sha256", "P", "VX", "LS", "ST", "has_keyhole", "max_depth_um"]
    require(set(columns).issubset(population.columns), "population fingerprint columns missing")
    blob = population.loc[:, columns].to_csv(index=False, lineterminator="\n", float_format="%.17g").encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_context() -> tuple[pd.DataFrame, list[Any], search.Arrays, np.ndarray]:
    population, specs = p121.load_all_specs()
    selected = [spec for spec in specs if spec.repeat in REPEATS]
    require(len(selected) == 300, "expected 300 Phase 1.21 outer runs")
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73, "population drift")
    require(all(len(spec.train_indices) == 324 and len(spec.test_indices) == 81 for spec in selected), "split size drift")
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    return population, selected, arrays, distances


def expected_split_record(spec: Any) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "repeat": int(spec.repeat),
        "fold": int(spec.fold),
        "train_sha256": split_hash(spec, "train"),
        "test_sha256": split_hash(spec, "test"),
    }


def validate_metrics(metrics: list[dict[str, Any]], spec: Any, policy: str) -> None:
    run_id = spec.run_id
    require(len(metrics) == 195, f"{policy}/{run_id}: expected 195 metric rows")
    frame = pd.DataFrame(metrics)
    required = {"policy", "run_id", "repeat", "fold", "budget", "subset", "accuracy",
                "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative",
                "false_positive", "true_negative", "true_positive", "row_count"}
    require(required.issubset(frame.columns), f"{policy}/{run_id}: metric schema drift")
    require(set(frame["policy"].astype(str)) == {policy}, f"{policy}/{run_id}: metric policy drift")
    require(set(frame["run_id"].astype(str)) == {run_id}, f"{policy}/{run_id}: metric run id drift")
    require(set(frame["repeat"].astype(int)) == {int(spec.repeat)}, f"{policy}/{run_id}: repeat drift")
    require(set(frame["fold"].astype(int)) == {int(spec.fold)}, f"{policy}/{run_id}: fold drift")
    require(set(frame["budget"].astype(int)) == set(range(16, 81)), f"{policy}/{run_id}: budget grid drift")
    require(set(frame["subset"].astype(str)) == {"full81", "B1_q30", "B1_q20"}, f"{policy}/{run_id}: subset drift")
    counts = frame.groupby(["budget", "subset"]).size()
    require(counts.eq(1).all() and len(counts) == 195, f"{policy}/{run_id}: duplicate/missing metrics")
    expected_rows = {"full81": 81, "B1_q30": 25, "B1_q20": 17}
    for subset, row_count in expected_rows.items():
        require(set(frame.loc[frame.subset.eq(subset), "row_count"].astype(int)) == {row_count},
                f"{policy}/{run_id}: {subset} row count drift")
    for name in ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall",
                 "false_negative", "false_positive", "true_negative", "true_positive", "row_count"):
        require(np.isfinite(pd.to_numeric(frame[name], errors="coerce")).all(), f"{policy}/{run_id}: non-finite {name}")


def validate_m3_payload(payload: dict[str, Any], policy: str, spec: Any, population: pd.DataFrame) -> None:
    require(bool(payload.get("complete")), f"{policy}/{spec.run_id}: incomplete")
    require(payload.get("policy") == policy, f"{policy}/{spec.run_id}: policy drift")
    require(payload.get("run_id") == spec.run_id, f"{policy}/{spec.run_id}: run id drift")
    queried = [int(value) for value in payload["queried_indices"]]
    require(len(queried) == 80 and len(set(queried)) == 80, f"{policy}/{spec.run_id}: invalid path length/duplicates")
    require(set(queried).issubset(set(spec.train_indices)), f"{policy}/{spec.run_id}: query outside training pool")
    require(set(queried).isdisjoint(set(spec.test_indices)), f"{policy}/{spec.run_id}: test query")
    validate_metrics(list(payload["metrics"]), spec, policy)
    frozen16 = w85.initial_design(spec, population)
    if policy in (MARGIN, CANDIDATE_A, A0_LIVE):
        require(queried[:16] == frozen16, f"{policy}/{spec.run_id}: B16 seed drift")
    if policy in (CANDIDATE_B, EARLY8_MARGIN):
        expected = early.seed_prefix(frozen16, population.has_keyhole.astype(int).to_numpy(), 8)
        require(queried[: len(expected)] == expected, f"{policy}/{spec.run_id}: early seed drift")


def stored_checkpoint(policy: str, run_id: str) -> Path:
    return p121.CHECKPOINTS / policy / f"{run_id}.json.gz"


def validate_stored_arms(population: pd.DataFrame, specs: Sequence[Any]) -> dict[str, Any]:
    by_id = {spec.run_id: spec for spec in specs}
    hashes: list[dict[str, str]] = []
    payloads: dict[tuple[str, str], dict[str, Any]] = {}
    for policy in (MARGIN, CANDIDATE_A, CANDIDATE_B):
        paths = sorted((p121.CHECKPOINTS / policy).glob("*.json.gz"))
        selected_paths = [path for path in paths if path.stem.split(".")[0] in by_id]
        require(len(selected_paths) == 300, f"stored {policy}: expected 300 checkpoints")
        for path in selected_paths:
            payload = read_gzip_json(path)
            spec = by_id[str(payload.get("run_id"))]
            validate_m3_payload(payload, policy, spec, population)
            payloads[(policy, spec.run_id)] = payload
            hashes.append({"policy": policy, "run_id": spec.run_id, "sha256": sha256_file(path)})
    for spec in specs:
        margin = payloads[(MARGIN, spec.run_id)]
        candidate_a = payloads[(CANDIDATE_A, spec.run_id)]
        candidate_b = payloads[(CANDIDATE_B, spec.run_id)]
        require(margin["queried_indices"][:16] == candidate_a["queried_indices"][:16], f"A/margin seed mismatch {spec.run_id}")
        seed_size = int(candidate_b["seed_size"])
        expected = early.seed_prefix(w85.initial_design(spec, population), population.has_keyhole.astype(int).to_numpy(), 8)
        require(seed_size == len(expected), f"B seed size mismatch {spec.run_id}")
    result = {
        "status": "PASS",
        "policies": [MARGIN, CANDIDATE_A, CANDIDATE_B],
        "runs_per_policy": 300,
        "stored_checkpoint_count": 900,
        "same_B16_A_vs_margin": True,
        "candidate_B_early_seed_valid": True,
    }
    atomic_json(STORED_VALIDATION, result)
    atomic_csv(OUT / "stored_checkpoint_manifest.csv", pd.DataFrame(hashes))
    return result


def stored_checkpoint_set_hash(specs: Sequence[Any]) -> str:
    digest = hashlib.sha256()
    for policy in (MARGIN, CANDIDATE_A, CANDIDATE_B):
        for spec in sorted(specs, key=lambda item: item.run_id):
            path = stored_checkpoint(policy, spec.run_id)
            require(path.is_file(), f"stored checkpoint missing: {policy}/{spec.run_id}")
            record = f"{policy}\0{spec.run_id}\0{sha256_file(path)}\n".encode("utf-8")
            digest.update(record)
    return digest.hexdigest()


def artifact_tree_hash(root: Path) -> dict[str, Any]:
    require(root.is_dir(), f"artifact directory missing: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    require(files, f"artifact directory empty: {root}")
    digest = hashlib.sha256()
    for path in files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        digest.update(f"{relative}\0{sha256_file(path)}\n".encode("utf-8"))
    return {"file_count": len(files), "tree_sha256": digest.hexdigest()}


def preflight_evidence_hashes() -> dict[str, Any]:
    files = (STORED_VALIDATION, OUT / "stored_checkpoint_manifest.csv", A0_PARITY,
             OUT / "a0_recreation_parity_detail.csv", RUNNER_GATE, LEAKAGE_GATES,
             W85_PROTOCOL_CANONICAL, W85_PROTOCOL_COMPATIBILITY)
    for path in files:
        require(path.is_file(), f"preflight evidence missing: {path.name}")
    return {
        "files": {path.name: sha256_file(path) for path in files},
        "a0_parity_selector_tree": artifact_tree_hash(PARITY_SELECTOR),
        "early16_runner_gate_tree": artifact_tree_hash(GATE_CHECKPOINTS),
    }


def load_stored_a0_paths() -> dict[str, list[int]]:
    """Read the original Week 8.5 checkpoint bundle without materialising or rewriting it."""
    require(A0_BUNDLE.is_file(), "authoritative Week 8.5 checkpoint bundle missing")
    require(sha256_file(A0_BUNDLE) == A0_BUNDLE_PUBLISHED_SHA256,
            "authoritative Week 8.5 checkpoint bundle hash drift")
    result: dict[str, list[int]] = {}
    with tarfile.open(A0_BUNDLE, "r:gz") as archive:
        members = [member for member in archive.getmembers()
                   if member.isfile() and member.name.endswith("__binary_margin__c01.json")]
        require(len(members) == 100, "authoritative A0 bundle member count drift")
        for member in members:
            handle = archive.extractfile(member)
            require(handle is not None, f"cannot read A0 bundle member {member.name}")
            payload = json.loads(handle.read().decode("utf-8"))
            identity = payload.get("identity", {})
            run_id = str(identity.get("run_id"))
            require(payload.get("complete") is True and identity.get("arm") == "binary_margin",
                    f"invalid A0 bundle member {member.name}")
            queried = [int(value) for value in payload["queried_indices"][:80]]
            require(len(queried) == 80 and len(set(queried)) == 80, f"invalid A0 path {run_id}")
            require(run_id not in result, f"duplicate A0 bundle run {run_id}")
            result[run_id] = queried
    require(len(result) == 100, "stored A0 bundle run count drift")
    return result


def prepare_canonical_w85_protocol() -> dict[str, Any]:
    """Materialise the semantic Week 8.5 protocol with its recorded LF canonical bytes.

    The checked-out historical file has CRLF bytes on Windows, while the frozen Week 8.5
    implementation deliberately accepts only sorted, LF canonical JSON.  This audit-local
    copy changes no JSON value and lets the unchanged historical implementation enforce its
    original recorded digest.
    """
    require(W85_PROTOCOL_ORIGINAL.is_file() and W85_PROTOCOL_SHA_RECORD.is_file(),
            "Week 8.5 protocol provenance is incomplete")
    parsed = json.loads(W85_PROTOCOL_ORIGINAL.read_text(encoding="utf-8"))
    canonical = w85.canonical_protocol_bytes(parsed)
    recorded = W85_PROTOCOL_SHA_RECORD.read_text(encoding="utf-8").split()[0]
    canonical_sha = hashlib.sha256(canonical).hexdigest()
    require(canonical_sha == recorded, "Week 8.5 semantic protocol does not match its recorded hash")
    atomic_bytes(W85_PROTOCOL_CANONICAL, canonical)
    require(json.loads(W85_PROTOCOL_CANONICAL.read_text(encoding="utf-8")) == parsed,
            "canonical Week 8.5 protocol changed semantic content")
    result = {
        "status": "PASS",
        "reason": "Windows checkout has CRLF bytes; audit-local copy restores recorded LF canonical serialization",
        "original_checkout_sha256": sha256_file(W85_PROTOCOL_ORIGINAL),
        "canonical_sha256": canonical_sha,
        "recorded_sha256": recorded,
        "semantic_json_equal": True,
        "historical_source_modified": False,
    }
    atomic_json(W85_PROTOCOL_COMPATIBILITY, result)
    return result


def preflight_artifact_provenance(spec: Any, purpose: str, population: pd.DataFrame) -> dict[str, Any]:
    return {
        "protocol_sha256": PROTOCOL_SHA,
        "runner_sha256": sha256_file(Path(__file__)),
        "population_sha256": population_hash(population),
        "purpose": purpose,
        "pinned_sources": validate_pinned_sources(protocol_payload()),
        **expected_split_record(spec),
    }


def recreate_a0_selector(spec: Any, population: pd.DataFrame, distances: np.ndarray, root: Path,
                         purpose: str) -> dict[str, Any]:
    require(W85_PROTOCOL_CANONICAL.is_file(), "audit-local canonical Week 8.5 protocol missing")
    w85.PROTOCOL_PATH = W85_PROTOCOL_CANONICAL
    checkpoint = root / w85.checkpoint_path(spec, "binary_margin", 1).name
    expected = preflight_artifact_provenance(spec, purpose, population)
    if validate_sidecar(checkpoint, expected):
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    else:
        payload = w85.run_trajectory(spec, "binary_margin", 1, 80, population, distances, checkpoint_dir=root)
        bind_checkpoint(checkpoint, expected)
    require(payload.get("complete") is True, f"A0 selector incomplete {spec.run_id}")
    require(payload.get("identity") == w85.trajectory_identity(spec, "binary_margin", 1),
            f"A0 selector identity drift {spec.run_id}")
    queried = [int(value) for value in payload["queried_indices"][:80]]
    require(len(queried) == 80 and len(set(queried)) == 80, f"A0 selector path drift {spec.run_id}")
    return payload


def run_a0_parity(population: pd.DataFrame, all_specs: Sequence[Any], distances: np.ndarray, workers: int) -> dict[str, Any]:
    stored = load_stored_a0_paths()
    specs = [spec for spec in all_specs if spec.repeat <= 20]
    require(len(specs) == 100, "canonical A0 parity spec count drift")
    outputs = Parallel(n_jobs=workers)(delayed(recreate_a0_selector)(spec, population, distances, PARITY_SELECTOR,
                                                                    "canonical_A0_parity") for spec in specs)
    details = []
    for spec, payload in zip(specs, outputs):
        path = [int(value) for value in payload["queried_indices"][:80]]
        exact = path == stored[spec.run_id]
        details.append({"run_id": spec.run_id, "exact_full_path_match": exact})
    matched = sum(row["exact_full_path_match"] for row in details)
    result = {
        "status": "PASS" if matched == 100 else "FAIL",
        "canonical_runs": 100,
        "exact_full_path_matches": int(matched),
        "policy": "historical Week 8.5 isotropic Binary-GPC binary_margin",
    }
    atomic_json(A0_PARITY, result)
    atomic_csv(OUT / "a0_recreation_parity_detail.csv", pd.DataFrame(details))
    require(matched == 100, "historical A0 live recreation failed canonical 100/100 parity")
    return result


def run_early16_gate(population: pd.DataFrame, specs: Sequence[Any], arrays: search.Arrays, distances: np.ndarray) -> dict[str, Any]:
    cases = [specs[0], specs[147], specs[-1]]
    alias = "audit_early16__margin"
    p121.POLICIES[alias] = (16, search.pol_margin)
    rows = []
    for spec in cases:
        checkpoint = GATE_CHECKPOINTS / alias / f"{spec.run_id}.json.gz"
        expected_binding = preflight_artifact_provenance(spec, "early16_margin_runner_gate", population)
        if not validate_sidecar(checkpoint, expected_binding):
            p121.run_spec(alias, spec, population, arrays, distances, GATE_CHECKPOINTS)
            bind_checkpoint(checkpoint, expected_binding)
        generated = read_gzip_json(checkpoint)
        validate_m3_payload(generated, alias, spec, population)
        stored = read_gzip_json(stored_checkpoint(MARGIN, spec.run_id))
        path_match = generated["queried_indices"] == stored["queried_indices"]
        left = pd.DataFrame(generated["metrics"]).drop(columns=["policy"]).sort_values(["budget", "subset"]).reset_index(drop=True)
        right = pd.DataFrame(stored["metrics"]).drop(columns=["policy"]).sort_values(["budget", "subset"]).reset_index(drop=True)
        metric_match = left.equals(right)
        rows.append({"run_id": spec.run_id, "path_match": path_match, "metric_match": metric_match})
    passed = all(row["path_match"] and row["metric_match"] for row in rows)
    result = {"status": "PASS" if passed else "FAIL", "cases": rows, "thread_environment": "single-thread BLAS"}
    atomic_json(RUNNER_GATE, result)
    require(passed, "audit runner does not reproduce stored M3 margin")
    return result


def m3_margin_one_step(spec: Any, arrays: search.Arrays, revealed: Sequence[int]) -> tuple[int, np.ndarray]:
    train = np.asarray(spec.train_indices, dtype=int)
    revealed_array = np.asarray(revealed, dtype=int)
    budget = len(revealed_array)
    physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed_array,
                                   p13.seed_u32("shared_physics", spec.run_id, budget))
    fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed_array, train, physics, "M3",
                         search.LENGTH_UPPER)
    candidates = np.setdiff1d(train, revealed_array, assume_unique=False)
    comp = p13.components(fit, arrays.x4[candidates], arrays.logh[candidates])
    state = search.State(run_id=spec.run_id, budget=budget, revealed=revealed_array, candidates=candidates,
                         seen_label=np.full(len(arrays.labels), -1, dtype=int),
                         seen_logdepth=np.full(len(arrays.labels), np.nan),
                         x_scaled=np.zeros_like(arrays.x4), z_scaled=np.zeros_like(arrays.orth),
                         logh=arrays.logh, p_cand=comp["probability"], mean_cand=comp["final_latent"],
                         var_cand=comp["latent_variance"], fit=fit,
                         rng=np.random.default_rng(p13.seed_u32("random", spec.run_id, budget)),
                         x4=arrays.x4, train=train, cache={}, leaky_rank=None)
    state.seen_label[revealed_array] = arrays.labels[revealed_array]
    state.seen_logdepth[revealed_array] = arrays.logdepth[revealed_array]
    return search.pol_margin(state), np.asarray(comp["probability"], dtype=float)


def binary_a0_one_step(spec: Any, population: pd.DataFrame, labels: np.ndarray,
                       revealed: Sequence[int]) -> tuple[int, np.ndarray]:
    train = np.asarray(spec.train_indices, dtype=int)
    revealed_array = np.asarray(revealed, dtype=int)
    x = population.loc[:, w85.FEATURES].to_numpy(float)
    scaler = w85.StandardScaler().fit(x[train])
    x_scaled = scaler.transform(x)
    budget = len(revealed_array)
    fit = w85.p6.fit_gpc(x[revealed_array], labels[revealed_array], scaler=scaler,
                         seed=w85.seed_u32(w85.fit_seed_key(spec, "binary_margin", 1, budget)), restarts=0)
    candidates = np.setdiff1d(train, revealed_array, assume_unique=False)
    probabilities = w85.p6.predict_gpc(fit, x[candidates])
    chosen, _ = w85.p6.choose_binary_candidate(method="binary_margin", candidate_indices=candidates,
                                                probabilities=probabilities, pool_scaled=x_scaled,
                                                queried_indices=list(map(int, revealed_array)))
    return int(chosen), np.asarray(probabilities, dtype=float)


def hidden_label_invariance_gates(population: pd.DataFrame, specs: Sequence[Any], arrays: search.Arrays) -> dict[str, Any]:
    """Execute one-step counterfactual tests after changing every unrevealed label."""
    rows: list[dict[str, Any]] = []
    for spec in (specs[0], specs[len(specs) // 2], specs[-1]):
        frozen16 = w85.initial_design(spec, population)
        early_revealed = early.seed_prefix(frozen16, arrays.labels, 8)
        hidden = np.ones(len(arrays.labels), dtype=bool)
        hidden[np.asarray(early_revealed, dtype=int)] = False
        changed_labels = arrays.labels.copy()
        changed_labels[hidden] = 1 - changed_labels[hidden]
        require(early.seed_prefix(frozen16, changed_labels, 8) == early_revealed,
                f"early seed depends on unrevealed labels {spec.run_id}")
        changed_arrays = search.Arrays(x4=arrays.x4, logh=arrays.logh, labels=changed_labels,
                                       logdepth=arrays.logdepth, orth=arrays.orth)
        m3_original, m3_prob_original = m3_margin_one_step(spec, arrays, early_revealed)
        m3_changed, m3_prob_changed = m3_margin_one_step(spec, changed_arrays, early_revealed)

        a0_revealed = frozen16
        a0_changed_labels = arrays.labels.copy()
        a0_hidden = np.ones(len(arrays.labels), dtype=bool)
        a0_hidden[np.asarray(a0_revealed, dtype=int)] = False
        a0_changed_labels[a0_hidden] = 1 - a0_changed_labels[a0_hidden]
        a0_original, a0_prob_original = binary_a0_one_step(spec, population, arrays.labels, a0_revealed)
        a0_changed, a0_prob_changed = binary_a0_one_step(spec, population, a0_changed_labels, a0_revealed)
        row = {
            "run_id": spec.run_id,
            "m3_margin_choice_original": m3_original,
            "m3_margin_choice_after_hidden_label_flip": m3_changed,
            "m3_margin_max_probability_change": float(np.max(np.abs(m3_prob_original - m3_prob_changed))),
            "binary_A0_choice_original": a0_original,
            "binary_A0_choice_after_hidden_label_flip": a0_changed,
            "binary_A0_max_probability_change": float(np.max(np.abs(a0_prob_original - a0_prob_changed))),
        }
        row["pass"] = bool(m3_original == m3_changed and a0_original == a0_changed
                           and row["m3_margin_max_probability_change"] == 0.0
                           and row["binary_A0_max_probability_change"] == 0.0)
        rows.append(row)
    require(all(row["pass"] for row in rows), "hidden-label counterfactual invariance failed")
    return {"status": "PASS", "method": "flip every unrevealed label and repeat one live acquisition step",
            "cases": rows}


def additional_input_hashes() -> dict[str, str]:
    inputs = (A0_BUNDLE, P121_INVARIANCE, W85_VALIDATION, P121_REPLICATION,
              W85_PROTOCOL_ORIGINAL, W85_PROTOCOL_SHA_RECORD)
    for path in inputs:
        require(path.is_file(), f"missing audit input: {path.relative_to(ROOT)}")
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in inputs}


def build_execution_freeze(protocol: dict[str, Any], sources: dict[str, str], population: pd.DataFrame, specs: Sequence[Any]) -> dict[str, Any]:
    runner = ROOT / "src" / "week10_trackA_phase121_comparator_audit.py"
    test = ROOT / "src" / "tests" / "test_week10_trackA_phase121_comparator_audit.py"
    payload = {
        "protocol_sha256": PROTOCOL_SHA,
        "runner_sha256": sha256_file(runner),
        "test_sha256": sha256_file(test) if test.is_file() else None,
        "pinned_sources": sources,
        "additional_input_sha256": additional_input_hashes(),
        "stored_phase121_checkpoint_set_sha256": stored_checkpoint_set_hash(specs),
        "preflight_evidence": preflight_evidence_hashes(),
        "population_sha256": population_hash(population),
        "splits": [expected_split_record(spec) for spec in specs],
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "sklearn": sklearn.__version__,
            "thread_variables": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
        },
        "new_policies": {
            EARLY8_MARGIN: "early.seed_prefix(k=8) then search.pol_margin",
            A0_LIVE: "w85 binary_margin selector run live; identical M3 evaluator on every prefix",
        },
    }
    if EXECUTION_FREEZE.is_file():
        require(json.loads(EXECUTION_FREEZE.read_text(encoding="utf-8")) == payload, "execution freeze drift")
    else:
        atomic_json(EXECUTION_FREEZE, payload)
    return payload


def validate_execution_freeze_current(population: pd.DataFrame, specs: Sequence[Any]) -> dict[str, Any]:
    require(EXECUTION_FREEZE.is_file(), "execution freeze is missing")
    payload = json.loads(EXECUTION_FREEZE.read_text(encoding="utf-8"))
    require(payload["protocol_sha256"] == PROTOCOL_SHA, "execution freeze protocol drift")
    require(payload["runner_sha256"] == sha256_file(Path(__file__)), "runner changed after execution freeze")
    test = ROOT / "src" / "tests" / "test_week10_trackA_phase121_comparator_audit.py"
    expected_test = sha256_file(test) if test.is_file() else None
    require(payload["test_sha256"] == expected_test, "test file changed after execution freeze")
    require(payload["population_sha256"] == population_hash(population), "population changed after execution freeze")
    require(payload["splits"] == [expected_split_record(spec) for spec in specs], "split manifest changed after execution freeze")
    protocol = protocol_payload()
    require(payload["pinned_sources"] == validate_pinned_sources(protocol), "pinned sources changed after execution freeze")
    require(payload["additional_input_sha256"] == additional_input_hashes(), "additional audit input changed after execution freeze")
    require(payload["stored_phase121_checkpoint_set_sha256"] == stored_checkpoint_set_hash(specs),
            "stored Phase 1.21 checkpoint set changed after execution freeze")
    require(payload["preflight_evidence"] == preflight_evidence_hashes(),
            "preflight evidence changed after execution freeze")
    for name, value in payload["environment"]["thread_variables"].items():
        require(os.environ.get(name) == value == "1", f"thread environment drift: {name}")
    return payload


def preflight(workers: int) -> dict[str, Any]:
    started = time.time()
    protocol = protocol_payload()
    sources = validate_pinned_sources(protocol)
    population, all_specs = p121.load_all_specs()
    specs = [spec for spec in all_specs if spec.repeat in REPEATS]
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    stored = validate_stored_arms(population, specs)
    protocol_compatibility = prepare_canonical_w85_protocol()
    parity = run_a0_parity(population, all_specs, distances, workers)
    runner_gate = run_early16_gate(population, specs, arrays, distances)
    live_invariance = hidden_label_invariance_gates(population, specs, arrays)
    p121_invariance = json.loads(P121_INVARIANCE.read_text(encoding="utf-8"))
    w85_validation = json.loads(W85_VALIDATION.read_text(encoding="utf-8"))
    w85_flow = [row for row in w85_validation["checks"] if row["check_id"] == "information_flow_saved_artifact_and_source"]
    require(p121_invariance.get("status") == "PASS" and int(p121_invariance.get("mismatches", -1)) == 0,
            "stored Phase 1.21 invariance gate failed")
    require(len(w85_flow) == 1 and w85_flow[0]["status"] == "PASS", "stored Week 8.5 information-flow gate failed")
    leakage = {
        "status": "PASS",
        "selector_contracts": {
            EARLY8_MARGIN: "search.pol_margin receives State built from training-pool candidates, M3 candidate probabilities, queried-only labels/depths and training-pool scaling",
            A0_LIVE: "w85.run_trajectory chooser receives method, candidate_indices, probabilities, pool_scaled and queried_indices only",
        },
        "held_out_rows_available_to_selector": False,
        "hidden_candidate_labels_available_to_selector": False,
        "q20_q30_or_B1_available_to_selector": False,
        "early_seed_extension": "reads labels only along the already selected frozen maximin prefix",
        "live_hidden_label_counterfactual": live_invariance,
        "stored_phase121_invariance": {
            "status": p121_invariance["status"],
            "mismatches": p121_invariance["mismatches"],
            "static_check_no_unmasked_access_in_policy_code": p121_invariance["static_check_no_unmasked_access_in_policy_code"],
            "sha256": sha256_file(P121_INVARIANCE),
        },
        "stored_week85_information_flow": {
            "status": w85_flow[0]["status"],
            "evidence": w85_flow[0]["evidence"],
            "sha256": sha256_file(W85_VALIDATION),
        },
    }
    atomic_json(LEAKAGE_GATES, leakage)
    freeze = build_execution_freeze(protocol, sources, population, specs)
    result = {
        "status": "PASS",
        "elapsed_seconds": time.time() - started,
        "protocol_sha256": PROTOCOL_SHA,
        "execution_freeze_sha256": sha256_file(EXECUTION_FREEZE),
        "stored_arms": stored,
        "week85_protocol_compatibility": protocol_compatibility,
        "a0_parity": parity,
        "runner_gate": runner_gate,
        "leakage": leakage,
        "population_sha256": freeze["population_sha256"],
    }
    atomic_json(PREFLIGHT, result)
    append_log(f"- Preflight PASS in {result['elapsed_seconds']:.1f} s; A0 parity 100/100; stored arms 900/900.")
    return result


def validate_preflight_authorization() -> dict[str, Any]:
    require(PREFLIGHT.is_file(), "preflight result missing")
    result = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    require(result.get("status") == "PASS", "preflight PASS required")
    require(result.get("execution_freeze_sha256") == sha256_file(EXECUTION_FREEZE),
            "preflight is stale relative to execution freeze")
    require(result.get("stored_arms", {}).get("status") == "PASS"
            and result["stored_arms"].get("stored_checkpoint_count") == 900,
            "stored-arm preflight gate is not PASS")
    require(result.get("week85_protocol_compatibility", {}).get("status") == "PASS"
            and result["week85_protocol_compatibility"].get("semantic_json_equal") is True,
            "Week 8.5 protocol compatibility gate is not PASS")
    require(result.get("a0_parity", {}).get("status") == "PASS"
            and result["a0_parity"].get("exact_full_path_matches") == 100,
            "A0 parity preflight gate is not 100/100 PASS")
    require(result.get("runner_gate", {}).get("status") == "PASS", "early16 runner gate is not PASS")
    leakage = result.get("leakage", {})
    require(leakage.get("status") == "PASS"
            and leakage.get("live_hidden_label_counterfactual", {}).get("status") == "PASS",
            "leakage preflight gate is not PASS")
    return result


def sidecar_path(checkpoint: Path) -> Path:
    return checkpoint.with_suffix(checkpoint.suffix + ".provenance.json")


def worker_provenance(spec: Any, policy: str, population_sha: str, execution_sha: str) -> dict[str, Any]:
    return {
        "protocol_sha256": PROTOCOL_SHA,
        "execution_freeze_sha256": execution_sha,
        "population_sha256": population_sha,
        "policy": policy,
        **expected_split_record(spec),
    }


def validate_sidecar(checkpoint: Path, expected: dict[str, Any]) -> bool:
    sidecar = sidecar_path(checkpoint)
    require(checkpoint.is_file() == sidecar.is_file(), f"partial checkpoint/sidecar pair: {checkpoint}")
    if not checkpoint.is_file():
        return False
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    require(payload["binding"] == expected, f"checkpoint provenance drift: {checkpoint}")
    require(payload["checkpoint_sha256"] == sha256_file(checkpoint), f"checkpoint payload hash drift: {checkpoint}")
    return True


def bind_checkpoint(checkpoint: Path, expected: dict[str, Any]) -> None:
    atomic_json(sidecar_path(checkpoint), {"binding": expected, "checkpoint_sha256": sha256_file(checkpoint)})


def run_early8_worker(spec: Any, population: pd.DataFrame, arrays: search.Arrays, distances: np.ndarray,
                      population_sha: str, execution_sha: str) -> dict[str, Any]:
    checkpoint = CHECKPOINTS / EARLY8_MARGIN / f"{spec.run_id}.json.gz"
    expected = worker_provenance(spec, EARLY8_MARGIN, population_sha, execution_sha)
    if validate_sidecar(checkpoint, expected):
        validate_m3_payload(read_gzip_json(checkpoint), EARLY8_MARGIN, spec, population)
        return {"run_id": spec.run_id, "reused": True}
    p121.POLICIES[EARLY8_MARGIN] = (8, search.pol_margin)
    p121.run_spec(EARLY8_MARGIN, spec, population, arrays, distances, CHECKPOINTS)
    validate_m3_payload(read_gzip_json(checkpoint), EARLY8_MARGIN, spec, population)
    bind_checkpoint(checkpoint, expected)
    return {"run_id": spec.run_id, "reused": False}


def evaluate_m3_path(spec: Any, queried: Sequence[int], population: pd.DataFrame, arrays: search.Arrays,
                     distances: np.ndarray) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    test = np.asarray(spec.test_indices, dtype=int)
    train = np.asarray(spec.train_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    metrics: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for budget in range(16, 81):
        revealed = np.asarray(queried[:budget], dtype=int)
        physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                       p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics, "M3", search.LENGTH_UPPER)
        probability = p13.components(fit, arrays.x4[test], arrays.logh[test])["probability"]
        diagnostics.append({"policy": A0_LIVE, "run_id": spec.run_id, "repeat": spec.repeat,
                            "fold": spec.fold, "budget": budget, **p13.fit_diagnostic(fit)})
        for subset in search.SUBSETS:
            flag = flags[subset]
            metrics.append({"policy": A0_LIVE, "run_id": spec.run_id, "repeat": spec.repeat,
                            "fold": spec.fold, "budget": budget, "subset": subset,
                            **p17.metric_values(arrays.labels[test][flag], probability[flag])})
    return metrics, diagnostics


def run_a0_worker(spec: Any, population: pd.DataFrame, arrays: search.Arrays, distances: np.ndarray,
                  population_sha: str, execution_sha: str) -> dict[str, Any]:
    checkpoint = CHECKPOINTS / A0_LIVE / f"{spec.run_id}.json.gz"
    expected = worker_provenance(spec, A0_LIVE, population_sha, execution_sha)
    if validate_sidecar(checkpoint, expected):
        validate_m3_payload(read_gzip_json(checkpoint), A0_LIVE, spec, population)
        return {"run_id": spec.run_id, "reused": True}
    selector = recreate_a0_selector(spec, population, distances, A0_SELECTOR,
                                    f"live_A0_selector/{execution_sha}")
    require(bool(selector.get("complete")), f"A0 selector incomplete {spec.run_id}")
    require(selector["identity"] == w85.trajectory_identity(spec, "binary_margin", 1), f"A0 selector identity drift {spec.run_id}")
    queried = [int(value) for value in selector["queried_indices"][:80]]
    require(len(queried) == 80 and len(set(queried)) == 80, f"A0 selector invalid path {spec.run_id}")
    require(set(queried).issubset(set(spec.train_indices)) and set(queried).isdisjoint(set(spec.test_indices)),
            f"A0 selector leakage {spec.run_id}")
    metrics, diagnostics = evaluate_m3_path(spec, queried, population, arrays, distances)
    selector_file = A0_SELECTOR / w85.checkpoint_path(spec, "binary_margin", 1).name
    payload = {
        "complete": True,
        "policy": A0_LIVE,
        "run_id": spec.run_id,
        "seed_size": 16,
        "queried_indices": queried,
        "metrics": metrics,
        "diagnostics": diagnostics,
        "selector_checkpoint_sha256": sha256_file(selector_file),
        "selector_definition": "frozen Week 8.5 isotropic Binary-GPC binary_margin run live",
        "evaluator": "frozen M3 at every B16-B80 prefix",
    }
    atomic_gzip_json(checkpoint, payload)
    validate_m3_payload(payload, A0_LIVE, spec, population)
    bind_checkpoint(checkpoint, expected)
    return {"run_id": spec.run_id, "reused": False}


def run_new_arms(workers: int) -> dict[str, Any]:
    protocol_payload()
    population, specs, arrays, distances = load_context()
    validate_execution_freeze_current(population, specs)
    validate_preflight_authorization()
    population_sha = population_hash(population)
    execution_sha = sha256_file(EXECUTION_FREEZE)
    started = time.time()
    early_results = Parallel(n_jobs=workers)(
        delayed(run_early8_worker)(spec, population, arrays, distances, population_sha, execution_sha) for spec in specs
    )
    early_elapsed = time.time() - started
    append_log(f"- early8__margin complete: 300 runs, reused {sum(r['reused'] for r in early_results)}, {early_elapsed:.1f} s.")
    started_a0 = time.time()
    a0_results = Parallel(n_jobs=workers)(
        delayed(run_a0_worker)(spec, population, arrays, distances, population_sha, execution_sha) for spec in specs
    )
    a0_elapsed = time.time() - started_a0
    append_log(f"- historical_binary_A0_live + M3 complete: 300 runs, reused {sum(r['reused'] for r in a0_results)}, {a0_elapsed:.1f} s.")
    result = {
        "status": "PASS",
        "workers": workers,
        "early8_margin": {"runs": 300, "reused": sum(r["reused"] for r in early_results), "elapsed_seconds": early_elapsed},
        "historical_binary_A0_live": {"runs": 300, "reused": sum(r["reused"] for r in a0_results), "elapsed_seconds": a0_elapsed},
    }
    atomic_json(OUT / "execution_summary.json", result)
    return result


def load_policy_payloads(policy: str, specs: Sequence[Any], population: pd.DataFrame) -> list[dict[str, Any]]:
    root = p121.CHECKPOINTS if policy in (MARGIN, CANDIDATE_A, CANDIDATE_B) else CHECKPOINTS
    result = []
    population_sha = population_hash(population)
    execution_sha = sha256_file(EXECUTION_FREEZE)
    for spec in specs:
        checkpoint = root / policy / f"{spec.run_id}.json.gz"
        if policy in (EARLY8_MARGIN, A0_LIVE):
            require(validate_sidecar(checkpoint, worker_provenance(spec, policy, population_sha, execution_sha)),
                    f"new checkpoint missing validated sidecar {policy}/{spec.run_id}")
        payload = read_gzip_json(checkpoint)
        validate_m3_payload(payload, policy, spec, population)
        result.append(payload)
    return result


def metrics_frame(policies: Sequence[str], specs: Sequence[Any], population: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy in policies:
        for payload in load_policy_payloads(policy, specs, population):
            rows.extend(payload["metrics"])
    frame = pd.DataFrame(rows)
    require(len(frame) == len(policies) * 300 * 195, "combined metric row count drift")
    return frame


def aulc_table(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (policy, run_id, repeat, fold, subset), group in metrics.groupby(["policy", "run_id", "repeat", "fold", "subset"], sort=True):
        ordered = group.sort_values("budget")
        for metric in ("accuracy", "balanced_accuracy"):
            for end in (40, 80):
                window = ordered[ordered.budget.between(16, end)]
                require(window.budget.astype(int).tolist() == list(range(16, end + 1)), f"AULC grid drift {policy}/{run_id}")
                value = float(np.trapezoid(window[metric].to_numpy(float), window.budget.to_numpy(float)) / (end - 16))
                rows.append({"policy": policy, "run_id": run_id, "repeat": int(repeat), "fold": int(fold),
                             "subset": subset, "metric": metric, "end_budget": end, "aulc": value})
    return pd.DataFrame(rows)


def bootstrap_interval(differences: np.ndarray, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differences), size=(PRIMARY_DRAWS, len(differences)))
    means = differences[indices].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def sign_flip_p(differences: np.ndarray, seed: int) -> float:
    observed = abs(float(differences.mean()))
    rng = np.random.default_rng(seed)
    extreme = 0
    completed = 0
    while completed < SIGN_FLIP_DRAWS:
        count = min(10_000, SIGN_FLIP_DRAWS - completed)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(count, len(differences)))
        values = np.abs((signs * differences).mean(axis=1))
        extreme += int(np.sum(values >= observed - 1e-15))
        completed += count
    return float((extreme + 1) / (SIGN_FLIP_DRAWS + 1))


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * value))
        adjusted[name] = running
    return adjusted


def checkpoint_repeat_difference(metrics: pd.DataFrame, treatment: str, control: str, subset: str,
                                 metric: str, budget: int) -> np.ndarray:
    selected = metrics[(metrics.subset == subset) & (metrics.budget == budget)]
    per_repeat = selected.groupby(["policy", "repeat"], as_index=False)[metric].mean()
    pivot = per_repeat.pivot(index="repeat", columns="policy", values=metric)
    return (pivot[treatment] - pivot[control]).to_numpy(float)


def compare(aulc: pd.DataFrame, metrics: pd.DataFrame, contrast: str, treatment: str, control: str,
            subset: str, metric: str, end: int) -> dict[str, Any]:
    selected = aulc[(aulc.subset == subset) & (aulc.metric == metric) & (aulc.end_budget == end)]
    per_repeat = selected.groupby(["policy", "repeat"], as_index=False).aulc.mean()
    pivot = per_repeat.pivot(index="repeat", columns="policy", values="aulc")
    require(treatment in pivot and control in pivot and len(pivot) == 60, f"contrast pairing drift {contrast}")
    differences = (pivot[treatment] - pivot[control]).to_numpy(float)
    seed = p13.seed_u32("week10_p121_comparator", contrast, subset, metric, end)
    low, high = bootstrap_interval(differences, seed)
    pvalue = sign_flip_p(differences, seed ^ 0x5A17)
    result = {
        "contrast": contrast,
        "treatment": treatment,
        "control": control,
        "subset": subset,
        "metric": metric,
        "window": f"B16-B{end}",
        "mean_difference": float(differences.mean()),
        "ci_lower": low,
        "ci_upper": high,
        "positive_repeats": int(np.sum(differences > 0)),
        "zero_repeats": int(np.sum(differences == 0)),
        "repeat_count": 60,
        "sign_flip_p": pvalue,
        "bootstrap_draws": PRIMARY_DRAWS,
        "sign_flip_draws": SIGN_FLIP_DRAWS,
    }
    if subset == "B1_q20" and metric == "accuracy" and end == 80:
        recall = checkpoint_repeat_difference(metrics, treatment, control, "B1_q20", "keyhole_recall", 40)
        final_accuracy = checkpoint_repeat_difference(metrics, treatment, control, "full81", "accuracy", 80)
        result.update({
            "B40_q20_keyhole_recall_difference": float(recall.mean()),
            "B80_full81_accuracy_difference": float(final_accuracy.mean()),
            "recall_guard_pass": bool(recall.mean() >= -0.03),
            "final_accuracy_guard_pass": bool(final_accuracy.mean() >= -0.01),
        })
    return result


def path_overlap(policies: Sequence[str], specs: Sequence[Any], population: pd.DataFrame) -> pd.DataFrame:
    payloads = {policy: {item["run_id"]: item for item in load_policy_payloads(policy, specs, population)} for policy in policies}
    pairs = [
        (CANDIDATE_A, MARGIN),
        (CANDIDATE_B, EARLY8_MARGIN),
        (EARLY8_MARGIN, MARGIN),
        (CANDIDATE_A, A0_LIVE),
    ]
    rows = []
    for left, right in pairs:
        for budget in (16, 24, 40, 80):
            values = []
            different = 0
            for spec in specs:
                a = payloads[left][spec.run_id]["queried_indices"][:budget]
                b = payloads[right][spec.run_id]["queried_indices"][:budget]
                values.append(len(set(a) & set(b)) / len(set(a) | set(b)))
                different += int(a != b)
            rows.append({"left": left, "right": right, "budget": budget,
                         "mean_prefix_jaccard": float(np.mean(values)),
                         "different_sequence_fraction": different / len(specs)})
    return pd.DataFrame(rows)


def analyse() -> dict[str, Any]:
    require((OUT / "execution_summary.json").is_file(), "new-arm execution is incomplete")
    population, specs, _, _ = load_context()
    validate_execution_freeze_current(population, specs)
    validate_preflight_authorization()
    policies = (MARGIN, CANDIDATE_A, CANDIDATE_B, EARLY8_MARGIN, A0_LIVE)
    metrics = metrics_frame(policies, specs, population)
    aulc = aulc_table(metrics)
    atomic_csv(OUT / "all_arm_AULC.csv", aulc)
    contrasts = [
        ("A_minus_M3_margin_known", CANDIDATE_A, MARGIN),
        ("B_minus_early8_margin_new", CANDIDATE_B, EARLY8_MARGIN),
        ("A_minus_historical_binary_A0_live_new", CANDIDATE_A, A0_LIVE),
        ("early8_margin_minus_M3_margin", EARLY8_MARGIN, MARGIN),
        ("B_minus_M3_margin_known", CANDIDATE_B, MARGIN),
        ("M3_margin_minus_historical_binary_A0_live", MARGIN, A0_LIVE),
        ("B_minus_historical_binary_A0_live", CANDIDATE_B, A0_LIVE),
    ]
    rows = [compare(aulc, metrics, name, treatment, control, subset, metric, end)
            for name, treatment, control in contrasts for subset, metric, end in ANALYSIS_ENDPOINTS]
    primary = [row for row in rows if row["contrast"] in NEW_PRIMARY_CONTRASTS and row["subset"] == "B1_q20"
               and row["metric"] == "accuracy" and row["window"] == "B16-B80"]
    adjusted = holm_adjust({row["contrast"]: float(row["sign_flip_p"]) for row in primary})
    for row in rows:
        row["in_new_primary_family"] = row in primary
        row["holm_p"] = adjusted.get(row["contrast"]) if row in primary else None
        if row in primary:
            guards = bool(row["recall_guard_pass"] and row["final_accuracy_guard_pass"])
            row["statistical_superiority"] = bool(row["ci_lower"] > 0 and row["holm_p"] < 0.05 and guards)
            row["practical_replacement"] = bool(row["statistical_superiority"] and row["mean_difference"] >= 0.01)
        else:
            row["statistical_superiority"] = None
            row["practical_replacement"] = None
    contrasts_frame = pd.DataFrame(rows)
    atomic_csv(OUT / "repeat_block_contrasts.csv", contrasts_frame)
    overlaps = path_overlap(policies, specs, population)
    atomic_csv(OUT / "query_path_overlap.csv", overlaps)

    def primary_row(name: str) -> dict[str, Any]:
        matches = [row for row in rows if row["contrast"] == name and row["in_new_primary_family"]]
        require(len(matches) == 1, f"primary result missing {name}")
        return matches[0]

    b_early = primary_row("B_minus_early8_margin_new")
    a_a0 = primary_row("A_minus_historical_binary_A0_live_new")
    known_a_recomputed = next(row for row in rows if row["contrast"] == "A_minus_M3_margin_known" and row["subset"] == "B1_q20"
                              and row["metric"] == "accuracy" and row["window"] == "B16-B80")
    replication = json.loads(P121_REPLICATION.read_text(encoding="utf-8"))
    pinned_matches = [row for row in replication["primary_tests"]
                      if row["policy"] == CANDIDATE_A and row["window"] == "16-80"]
    require(len(pinned_matches) == 1, "pinned Candidate A primary result missing")
    pinned = pinned_matches[0]
    require(abs(float(pinned["mean"]) - known_a_recomputed["mean_difference"]) < 1e-15,
            "known Candidate A mean does not reproduce")
    require(int(pinned["positive_blocks"]) == known_a_recomputed["positive_repeats"],
            "known Candidate A positive-repeat count does not reproduce")
    known_a = {
        **known_a_recomputed,
        "mean_difference": float(pinned["mean"]),
        "ci_lower": float(pinned["ci_low"]),
        "ci_upper": float(pinned["ci_high"]),
        "positive_repeats": int(pinned["positive_blocks"]),
        "sign_flip_p": float(pinned["signflip_p"]),
        "holm_p": float(pinned["holm_p"]),
        "reported_values_source": "pinned Phase 1.21 REPLICATION_RESULT.json",
    }
    known_parity = {
        "status": "PASS",
        "source_sha256": sha256_file(P121_REPLICATION),
        "pinned": pinned,
        "recomputed_mean": known_a_recomputed["mean_difference"],
        "recomputed_positive_repeats": known_a_recomputed["positive_repeats"],
        "audit_bootstrap_interval_not_substituted_for_pinned_interval": [known_a_recomputed["ci_lower"],
                                                                         known_a_recomputed["ci_upper"]],
    }
    atomic_json(OUT / "known_phase121_result_parity.json", known_parity)
    total_b = next(row for row in rows if row["contrast"] == "B_minus_M3_margin_known" and row["subset"] == "B1_q20"
                   and row["metric"] == "accuracy" and row["window"] == "B16-B80")
    seed = next(row for row in rows if row["contrast"] == "early8_margin_minus_M3_margin" and row["subset"] == "B1_q20"
                and row["metric"] == "accuracy" and row["window"] == "B16-B80")
    closure = float(total_b["mean_difference"] - (b_early["mean_difference"] + seed["mean_difference"]))
    require(abs(closure) < 1e-12, "effect decomposition does not close")
    result = {
        "status": "PASS",
        "classification": {
            "candidate_A_vs_M3_margin": "statistically positive internal acquisition effect" if known_a["ci_lower"] > 0 else "unresolved",
            "candidate_A_practical_replacement": bool(known_a["mean_difference"] >= 0.01 and known_a["ci_lower"] > 0),
            "coverage_given_early8": "supported" if b_early["statistical_superiority"] else "not supported under locked rule",
            "candidate_A_vs_historical_binary_A0": "supported" if a_a0["statistical_superiority"] else "not supported under locked rule",
            "any_incumbent_replacement": bool(known_a["mean_difference"] >= 0.01 and known_a["ci_lower"] > 0),
        },
        "primary_results": {"B_minus_early8_margin": b_early, "A_minus_historical_binary_A0_live": a_a0},
        "known_A_minus_M3_margin": known_a,
        "known_A_minus_M3_margin_parity": known_parity,
        "known_B_minus_M3_margin": total_b,
        "effect_decomposition": {
            "coverage_given_early8": b_early["mean_difference"],
            "early_start_given_margin": seed["mean_difference"],
            "total_B_minus_margin": total_b["mean_difference"],
            "closure_error": closure,
        },
        "scope": "same 405-simulation population; post-result attribution; not external validation",
    }
    atomic_json(OUT / "effect_decomposition.json", result)
    write_report(result)
    append_log("- Analysis PASS; repeat-block contrasts, decomposition and final report written.")
    return result


def fmt_result(row: dict[str, Any]) -> str:
    return (f"{row['mean_difference']:+.6f} [{row['ci_lower']:+.6f}, {row['ci_upper']:+.6f}], "
            f"positive repeats {row['positive_repeats']}/60, Holm p={row.get('holm_p'):.6g}")


def write_report(result: dict[str, Any]) -> None:
    b = result["primary_results"]["B_minus_early8_margin"]
    a0 = result["primary_results"]["A_minus_historical_binary_A0_live"]
    known = result["known_A_minus_M3_margin"]
    replacement = result["classification"]["any_incumbent_replacement"]
    lines = [
        "# Week 10 Track A — Phase 1.21 comparator audit",
        "",
        "## Executive verdict",
        "",
        f"- Candidate A vs current M3-margin (known matched B16 result): {known['mean_difference']:+.6f} "
        f"[{known['ci_lower']:+.6f}, {known['ci_upper']:+.6f}].",
        f"- Coverage effect with the early-8 start held fixed: {fmt_result(b)}.",
        f"- Candidate A vs live recreation of historical Binary-A0: {fmt_result(a0)}.",
        f"- Practical incumbent replacement at +0.01: {'PASS' if replacement else 'FAIL'}.",
        "- These are internal OLD-405 results, not external validation.",
        "",
        "## What was tested",
        "",
        "Candidate A and the current M3-margin incumbent share the frozen B16 start, so their difference is a pure acquisition comparison. "
        "Candidate B was compared with a new early8__margin control that shares the identical early-start rule, isolating coverage. "
        "Candidate A was also compared with the frozen Week 8.5 Binary-GPC margin policy recreated live on the same repeats; every path was evaluated by M3.",
        "",
        "## Primary results",
        "",
        "| Contrast | q20 accuracy AULC B16-B80 | Statistical superiority | Practical replacement |",
        "|---|---:|---:|---:|",
        f"| Candidate B - early8 margin | {b['mean_difference']:+.6f} [{b['ci_lower']:+.6f},{b['ci_upper']:+.6f}] | "
        f"{'PASS' if b['statistical_superiority'] else 'FAIL'} | {'PASS' if b['practical_replacement'] else 'FAIL'} |",
        f"| Candidate A - historical Binary-A0 live | {a0['mean_difference']:+.6f} [{a0['ci_lower']:+.6f},{a0['ci_upper']:+.6f}] | "
        f"{'PASS' if a0['statistical_superiority'] else 'FAIL'} | {'PASS' if a0['practical_replacement'] else 'FAIL'} |",
        "",
        "## Acquisition decomposition",
        "",
        f"- Coverage contribution given early start: {result['effect_decomposition']['coverage_given_early8']:+.6f}.",
        f"- Early-start contribution under margin: {result['effect_decomposition']['early_start_given_margin']:+.6f}.",
        f"- Total Candidate B minus M3-margin: {result['effect_decomposition']['total_B_minus_margin']:+.6f}.",
        f"- Algebraic closure error: {result['effect_decomposition']['closure_error']:.3e}.",
        "",
        "## Plain-language interpretation",
        "",
        "Phase 1.21 does not replace the M3 model; it uses M3 and changes only which simulation is queried. "
        "A statistically positive difference therefore means a better query order on this fixed population. "
        "Replacement still requires a gain of at least +0.01 over the full primary window, plus the frozen guardrails. "
        "Even a passing internal comparison cannot establish performance on Ioan's future independent batch.",
        "",
        "## Evidence files",
        "",
        "- `AUDIT_PROTOCOL.json` and `EXECUTION_FREEZE.json`",
        "- `preflight_validation.json` and `a0_recreation_parity.json`",
        "- `repeat_block_contrasts.csv`",
        "- `effect_decomposition.json`",
        "- `query_path_overlap.csv`",
    ]
    (OUT / "FINAL_COMPARATOR_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run", "analyze", "all"), default="all")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    require(args.workers >= 1, "workers must be positive")
    OUT.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        LOG.write_text("# Phase 1.21 comparator audit execution log\n\n", encoding="utf-8")
    append_log(f"- Invocation mode={args.mode}, workers={args.workers}, epoch={time.time():.3f}.")
    if args.mode in ("preflight", "all"):
        preflight(args.workers)
    if args.mode in ("run", "all"):
        run_new_arms(args.workers)
    if args.mode in ("analyze", "all"):
        analyse()


if __name__ == "__main__":
    main()
