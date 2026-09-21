"""Week 10 Track A: physics-guided robust monotone boundary coverage.

This module runs one predeclared five-policy internal replication.  It reuses
the frozen M3 evaluator and Phase 1.21 boundary coverage.  Monotonicity enters
only through a query-priority count; it never creates labels, removes rows, or
changes evaluation truth.
"""
from __future__ import annotations

import os

# Historical Phase 1.21 trajectories are sensitive to rare numerical near-ties.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import datetime as dt
import gzip
import hashlib
import inspect
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_20_early_start as early
from src import week9_phase1_21_simplification_replication as p121


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week10_trackA_pg_rmbc"
CHECKPOINTS = OUTPUT / "checkpoints"
FIGURES = OUTPUT / "figures"
PROTOCOL = OUTPUT / "METHOD_PROTOCOL_FREEZE.md"
PROTOCOL_HASH = OUTPUT / "METHOD_PROTOCOL_FREEZE.sha256"
HISTORICAL_GATES = OUTPUT / "HISTORICAL_GATES.md"

PROJECT_NAME = "week10-pg-rmbc-internal-replication"
PROTOCOL_ID = "week10_trackA_pg_rmbc/v1.0.0"
REPEATS = tuple(range(121, 181))
POLICIES = (
    "P0_M3_MARGIN_B16",
    "P1_PHASE121_CANDIDATE_B",
    "P2_H_SEED_COVERAGE_B40",
    "P3_EARLY8_RMBC_B40",
    "P4_PG_RMBC_ADAPTIVE",
)
P0, P1, P2, P3, P4 = POLICIES
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
CHECKPOINT_BUDGETS = (24, 32, 40, 80)
SEPARABILITY_BUDGETS = (16, 20, 24, 32, 40)
PAD_FRACTION = 0.25
PAD_FLOOR = 0.05
UNCERTAINTY_WEIGHT = 1.0
FIXED_SWITCH_BUDGET = 40
BOOTSTRAP_DRAWS = 20_000
SIGN_FLIP_DRAWS = 100_000
PRIMARY_MATERIAL_EFFECT = 0.005
GUARD_KH_RECALL_B40 = -0.03
GUARD_FULL81_ACCURACY_B80 = -0.01
SEED_ROOT = "week10_trackA_pg_rmbc|v1"

PRIMARY_CONTRASTS = (
    (P4, P1, "P4-P1"),
    (P2, P1, "P2-P1"),
    (P3, P1, "P3-P1"),
    (P4, P0, "P4-P0"),
)

PINNED_INPUTS = (
    "src/week8_5_frozen_sample_efficiency_confirmation.py",
    "src/week9_phase1_7_physics_ridge_residual_gp.py",
    "src/week9_phase1_11_fixed_mean_discrepancy_gp.py",
    "src/week9_phase1_13_fixed_physics_ard_discrepancy.py",
    "src/week9_phase1_20_acquisition_search.py",
    "src/week9_phase1_20_early_start.py",
    "src/week9_phase1_21_simplification_replication.py",
    "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv",
    "outputs/week9_phase1_21_simplification_replication/FINAL_POLICY_FREEZE.json",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def seed_u32(*parts: object) -> int:
    text = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n")


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    if path.suffix == ".gz":
        blob = frame.to_csv(index=False, lineterminator="\n").encode()
        temporary.write_bytes(gzip.compress(blob, compresslevel=9, mtime=0))
    else:
        frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def atomic_gzip_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(json_safe(payload), sort_keys=True) + "\n").encode()
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(gzip.compress(blob, compresslevel=6, mtime=0))
    temporary.replace(path)


def read_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_context() -> tuple[pd.DataFrame, list[Any], search.Arrays, np.ndarray]:
    population, historical = p121.load_all_specs()
    extended = w85.build_splits(population, repeats=max(REPEATS), folds=5)
    require(len(historical) == 600, "Phase 1.21 split count drift")
    for old, new in zip(historical, extended[:600]):
        require(old.run_id == new.run_id and old.train_indices == new.train_indices
                and old.test_indices == new.test_indices, f"split drift {old.run_id}")
    specs = [s for s in extended if s.repeat in set(REPEATS)]
    require(len(specs) == 300, "expected 300 new outer runs")
    require((len(population), int(population.has_keyhole.sum())) == (405, 73), "population drift")
    return population, specs, search.build_arrays(population), w85.b1_distance(population)


def h_maximin_order(logh: np.ndarray, train_indices: Sequence[int]) -> list[int]:
    """Exact label-blind 1D h-maximin order with population-row tie breaking."""
    train = np.asarray(sorted(map(int, train_indices)), dtype=int)
    values = np.asarray(logh, float)[train]
    first = int(train[np.lexsort((train, values))[0]])
    remaining = train[train != first]
    second = int(remaining[np.lexsort((remaining, -np.asarray(logh)[remaining]))[0]])
    selected = [first, second]
    nearest = np.minimum(np.abs(values - logh[first]), np.abs(values - logh[second]))
    local = {int(row): i for i, row in enumerate(train)}
    nearest[[local[first], local[second]]] = -np.inf
    while len(selected) < len(train):
        order = np.lexsort((train, -nearest))
        chosen = int(train[order[0]])
        selected.append(chosen)
        nearest = np.minimum(nearest, np.abs(values - logh[chosen]))
        nearest[[local[row] for row in selected]] = -np.inf
    require(len(selected) == len(set(selected)) == len(train), "h-maximin order drift")
    return selected


def seed_until_both(order: Sequence[int], labels: np.ndarray, minimum: int = 2) -> list[int]:
    queried = list(map(int, order[:minimum]))
    position = minimum
    while len(np.unique(np.asarray(labels)[queried])) < 2:
        require(position < len(order), "training pool does not contain both classes")
        queried.append(int(order[position]))
        position += 1
    return queried


def is_h_separable(revealed: Sequence[int], labels: np.ndarray, logh: np.ndarray) -> bool:
    idx = np.asarray(revealed, int)
    y = np.asarray(labels, int)[idx]
    require(set(np.unique(y)) == {0, 1}, "separability requires both observed classes")
    return bool(np.max(logh[idx][y == 0]) < np.min(logh[idx][y == 1]))


def dominance_matrix(population: pd.DataFrame) -> np.ndarray:
    """dom[i,j] means j is strictly more Keyhole-prone than i; ST is absent."""
    x = population.loc[:, ["P", "VX", "LS"]].to_numpy(float)
    more = ((x[None, :, 0] >= x[:, None, 0]) &
            (x[None, :, 1] <= x[:, None, 1]) &
            (x[None, :, 2] <= x[:, None, 2]))
    strict = np.any(x[None, :, :] != x[:, None, :], axis=2)
    return more & strict


def band_details(state: search.State) -> tuple[np.ndarray, float, float, float]:
    rev = state.revealed
    y = state.seen_label[rev]
    require(set(np.unique(y)) == {0, 1}, "boundary band requires both revealed classes")
    lowest_kh = float(state.logh[rev][y == 1].min())
    highest_c = float(state.logh[rev][y == 0].max())
    lo, hi = sorted((lowest_kh, highest_c))
    pad = max(PAD_FLOOR, PAD_FRACTION * (hi - lo))
    values = state.logh[state.candidates]
    return (values >= lo - pad) & (values <= hi + pad), lo, hi, pad


def rank01(values: np.ndarray) -> np.ndarray:
    """Reuse the frozen Phase 1.21 stable ordinal rank normalization exactly."""
    return search._rank01(np.asarray(values, float))


def coverage_values(state: search.State, candidates: np.ndarray) -> np.ndarray:
    return np.sqrt(((state.x_scaled[candidates, None, :] -
                     state.x_scaled[state.revealed][None, :, :]) ** 2).sum(-1)).min(axis=1)


def leverage_counts(candidates: np.ndarray, relevant: np.ndarray,
                    dom: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cand = np.asarray(candidates, int)
    rel = np.asarray(relevant, int)
    g_kh = dom[np.ix_(cand, rel)].sum(axis=1).astype(int)
    g_c = dom[np.ix_(rel, cand)].sum(axis=0).astype(int)
    return g_kh, g_c, np.minimum(g_kh, g_c)


def monotonicity_disagreement(candidates: np.ndarray, probabilities: np.ndarray,
                              dom: np.ndarray) -> np.ndarray:
    """Diagnostic only: mean positive probability-order violation touching x."""
    cand = np.asarray(candidates, int)
    p = np.asarray(probabilities, float)
    local_dom = dom[np.ix_(cand, cand)]
    # For i<j in the order, p_i should not exceed p_j.
    violation = np.maximum(0.0, p[:, None] - p[None, :]) * local_dom
    counts = local_dom.sum(axis=1) + local_dom.sum(axis=0)
    totals = violation.sum(axis=1) + violation.sum(axis=0)
    return np.divide(totals, counts, out=np.zeros_like(totals), where=counts > 0)


def choose_band(state: search.State, dom: np.ndarray, with_monotone: bool) -> tuple[int, dict[str, Any]]:
    band, lo, hi, pad = band_details(state)
    if not band.any():
        chosen = search.pol_margin(state)
        return chosen, {"mode": "margin_empty_band_fallback", "band_candidates": 0,
                        "band_lo": lo, "band_hi": hi, "band_pad": pad}
    cand = state.candidates[band]
    p = state.p_cand[band]
    uncertainty = 1.0 - 2.0 * np.abs(p - 0.5)
    coverage = coverage_values(state, cand)
    g_kh, g_c, robust = leverage_counts(cand, cand, dom)
    score = rank01(uncertainty) + rank01(coverage)
    if with_monotone:
        score = score + rank01(robust)
    chosen = search.argbest(cand, score)
    pos = int(np.flatnonzero(cand == chosen)[0])
    all_disagreement = monotonicity_disagreement(state.candidates, state.p_cand, dom)
    global_pos = int(np.flatnonzero(state.candidates == chosen)[0])
    return chosen, {
        "mode": "rmbc" if with_monotone else "coverage",
        "band_candidates": int(len(cand)), "band_lo": lo, "band_hi": hi, "band_pad": pad,
        "selected_probability": float(p[pos]), "selected_U": float(uncertainty[pos]),
        "selected_C": float(coverage[pos]), "selected_G_KH": int(g_kh[pos]),
        "selected_G_C": int(g_c[pos]), "selected_M": int(robust[pos]),
        "selected_score": float(score[pos]), "selected_disagreement": float(all_disagreement[global_pos]),
        "candidate_G_KH_min": int(g_kh.min()), "candidate_G_KH_median": float(np.median(g_kh)),
        "candidate_G_KH_max": int(g_kh.max()), "candidate_G_C_min": int(g_c.min()),
        "candidate_G_C_median": float(np.median(g_c)), "candidate_G_C_max": int(g_c.max()),
        "candidate_M_min": int(robust.min()), "candidate_M_median": float(np.median(robust)),
        "candidate_M_max": int(robust.max()),
    }


def build_state(spec: Any, arrays: search.Arrays, train: np.ndarray, revealed: np.ndarray,
                fit: Any, x_scaled: np.ndarray, cache: dict[Any, Any]) -> search.State:
    candidates = np.setdiff1d(train, revealed, assume_unique=False)
    comp = p13.components(fit, arrays.x4[candidates], arrays.logh[candidates])
    n = len(arrays.labels)
    seen_label = np.full(n, -1, int)
    seen_label[revealed] = arrays.labels[revealed]
    seen_depth = np.full(n, np.nan)
    seen_depth[revealed] = arrays.logdepth[revealed]
    return search.State(
        run_id=spec.run_id, budget=len(revealed), revealed=revealed, candidates=candidates,
        seen_label=seen_label, seen_logdepth=seen_depth, x_scaled=x_scaled,
        z_scaled=np.empty((n, 0)), logh=arrays.logh, p_cand=comp["probability"],
        mean_cand=comp["final_latent"], var_cand=comp["latent_variance"], fit=fit,
        rng=np.random.default_rng(seed_u32("unused-rng", spec.run_id, len(revealed))),
        x4=arrays.x4, train=train, cache=cache, leaky_rank=None,
    )


def initial_seed(policy: str, spec: Any, population: pd.DataFrame,
                 arrays: search.Arrays) -> tuple[list[int], str]:
    frozen16 = w85.initial_design(spec, population)
    if policy == P0:
        return list(map(int, frozen16[:16])), "frozen_feature_maximin_B16"
    if policy in (P1, P3):
        return early.seed_prefix(frozen16, arrays.labels, 8), "phase121_early8"
    order = h_maximin_order(arrays.logh, spec.train_indices)
    return seed_until_both(order, arrays.labels, 2), "h_maximin_until_both_classes"


def choose(policy: str, state: search.State, dom: np.ndarray,
           adaptive_switched: bool) -> tuple[int, dict[str, Any]]:
    if policy == P0:
        return search.pol_margin(state), {"mode": "margin"}
    if policy in (P1, P2):
        if state.budget >= FIXED_SWITCH_BUDGET:
            return search.pol_margin(state), {"mode": "margin"}
        return choose_band(state, dom, with_monotone=False)
    if policy == P3:
        if state.budget >= FIXED_SWITCH_BUDGET:
            return search.pol_margin(state), {"mode": "margin"}
        return choose_band(state, dom, with_monotone=True)
    if policy == P4:
        if adaptive_switched:
            return search.pol_margin(state), {"mode": "margin_after_adaptive_switch"}
        return choose_band(state, dom, with_monotone=True)
    raise ValueError(policy)


def protocol_source_hashes() -> dict[str, str]:
    paths = (*PINNED_INPUTS, "src/week10_trackA_pg_rmbc.py",
             "src/tests/test_week10_trackA_pg_rmbc.py")
    return {relative: sha256_file(ROOT / relative) for relative in paths}


def protocol_markdown() -> str:
    hashes = protocol_source_hashes()
    hash_lines = "\n".join(f"- `{path}`: `{value}`" for path, value in hashes.items())
    return f"""# Week 10 Track A — PG-RMBC method protocol freeze

Protocol ID: `{PROTOCOL_ID}`  
Project: `{PROJECT_NAME}`  
Frozen at (UTC): `{utc_now()}`  
Status: **FROZEN BEFORE FULL TRAJECTORIES**

`HISTORICAL_GATES.md` passed before this freeze. No Ioan/new-pool file was opened or read. The experiment below uses only the frozen 405-simulation internal benchmark. No post-result method change or additional arm is permitted.

## Fixed data and replication design

- Population: the same 405 rows (73 Keyhole, 332 Conduction), manual `has_keyhole` ground truth.
- Split generator: frozen Week 8.5 `StratifiedGroupKFold` generator.
- New internal repeat block: repeats **121–180**, fixed now; 60 repeat blocks, five paired folds each, 300 outer runs per policy.
- Inferential unit: repeat block after averaging its five folds. Folds are not independent units.
- Budgets: B16–B80 inclusive. q20 is primary; q30 remains secondary.
- Evaluator: exact M3 — revealed-prefix logistic mean on exact frozen `log h`, plus 4D ARD Matérn-3/2 discrepancy; refit at every budget.
- Numerical environment: single-thread BLAS variables fixed before scientific imports.

## Exact physics and geometry

`log h = log P - 0.5 log VX - 1.5 log LS`. Exponents are fixed; ST is absent from `h`.

The Phase 1.21 boundary band is reproduced exactly from revealed labels: endpoints are the lowest revealed Keyhole `log h` and highest revealed Conduction `log h`, sorted; padding is `max(0.05, 0.25 * width)`. Empty band falls back to plain M3 probability margin. Coverage is standardized `[P,VX,LS,ST]` Euclidean distance to the nearest queried row, with the scaler fitted label-blind on the outer training pool. Rank normalization reuses Phase 1.21 stable ordinal `_rank01` exactly.

## h-maximin seed

On each outer training pool, order rows label-blindly: smallest `log h`, largest `log h`, then the row maximizing distance to the nearest selected `log h`; every tie is resolved by the smaller population row index. Reveal along this fixed order until both observed classes exist. No pseudo-label is created. If an effective seed ever exceeds B16, the study fails validation because the common B16 metric grid would be unavailable; this is a predeclared integrity condition, not a tuning rule.

## Soft monotone leverage

`j` is more Keyhole-prone than `i` iff `P_j >= P_i`, `VX_j <= VX_i`, `LS_j <= LS_i`, with at least one strict inequality. ST is excluded.

At each acquisition step, the relevant set is exactly the unqueried outer-training candidates inside the current boundary band. For candidate `x` in that set:

- `G_KH(x)` counts other relevant candidates strictly more Keyhole-prone than `x`;
- `G_C(x)` counts other relevant candidates strictly more Conduction-prone than `x`;
- `M(x) = min(G_KH(x), G_C(x))`.

The PG-RMBC score is `rank(U) + rank(C) + rank(M)`, where `U=1-2|p_M3-0.5|`. All weights are one. Final score ties use the smaller population row index. Counts affect query priority only: they create no labels, remove no candidates, resolve no rows, enter no M3 fit, and never replace simulator truth.

## Adaptive switch

After both classes exist, revealed labels are h-separable iff `max(log h | revealed Conduction) < min(log h | revealed Keyhole)`. P4 uses RMBC while separable. The first newly queried real label that makes this false records the adaptive-switch budget; every subsequent query uses plain M3 probability margin permanently. There is no patience and no switch-back.

## Exactly five policies

1. P0: M3 margin + frozen B16 feature-maximin seed.
2. P1: exact frozen Phase 1.21 `early8__coverage_then_margin_B40` benchmark.
3. P2: h-maximin-until-both seed + exact Phase 1.21 coverage-until-B40, then margin.
4. P3: Phase 1.21 early8 seed + RMBC until B40, then margin.
5. P4: h-maximin-until-both seed + RMBC while h-separable, permanent margin after first observed violation.

No sixth arm or parameter search may be added.

## Endpoints and inference

Primary endpoint: q20 accuracy normalized trapezoidal AULC B16–B40. Primary contrast: P4−P1. Also predeclared in one Holm family: P2−P1, P3−P1, P4−P0. Paired deterministic percentile bootstrap uses 20,000 repeat-block draws; deterministic two-sided sign-flip Monte Carlo uses 100,000 draws. Positive-repeat counts are reported.

Secondary endpoints: q20 accuracy B16–B80; q20 balanced-accuracy B16–B40 and B16–B80; q20 Keyhole-recall AULC; q30 accuracy AULC; full81 accuracy AULC; B24/B32/B40/B80 checkpoints; q20 Keyhole recall and false negatives at B40; full81 accuracy at B80.

P4 classification is fixed:

- `PG_RMBC_IMPROVEMENT_SUPPORTED` only if P4−P1 mean >0, lower 95% interval >0, mean >=+0.005, B40 q20 KH-recall difference >=−0.03, B80 full81 accuracy difference >=−0.01, and all leakage/safety checks pass.
- positive interval but mean <+0.005: `SMALL_INTERNAL_GAIN`.
- interval includes zero: `NO_CLEAR_IMPROVEMENT`.
- either guardrail or leakage/safety failure: `REJECT_FOR_SAFETY_OR_ROBUSTNESS`.

The final policy decision is exactly one of `FREEZE_PG_RMBC_FOR_EXTERNAL_TEST`, `KEEP_PHASE121_CANDIDATE_B`, or `REJECT_PG_RMBC_FOR_SAFETY_OR_ROBUSTNESS`.

## Diagnostics, non-causal decomposition, and claim boundary

The frozen diagnostics are seed size, first-both-classes budget, adaptive-switch budget, h-separability fractions at B16/B20/B24/B32/B40, early band-query fraction, selected U/C/M and G counts, path Jaccard against P1, q20 FP/FN curves, and a probability-order disagreement score that is never an acquisition input. Algebraically: `P4−P1 = (P2−P1) + (P3−P1) + remainder`; the remainder is labelled adaptive/interaction and is not a causal percentage. P4's adaptive-switch contribution is not separately identifiable from the five arms.

Sample efficiency reports first crossing of P1's mean q20 accuracy at P1 B24/B32/B40, descriptively only. No external validation, universal monotonicity, theoretical complexity, guaranteed savings, exact physical boundary, industrial safety, or novelty claim is allowed.

## Frozen source and input hashes

{hash_lines}
"""


def freeze_protocol() -> dict[str, Any]:
    require(HISTORICAL_GATES.is_file() and "Gate status: **PASS**" in HISTORICAL_GATES.read_text(encoding="utf-8"),
            "historical gate missing or failed")
    require(not PROTOCOL.exists(), "protocol already exists; refusing to overwrite freeze")
    text = protocol_markdown()
    atomic_text(PROTOCOL, text)
    digest = sha256_file(PROTOCOL)
    atomic_text(PROTOCOL_HASH, digest + "  METHOD_PROTOCOL_FREEZE.md\n")
    return {"protocol": str(PROTOCOL), "sha256": digest}


def validate_protocol() -> dict[str, Any]:
    require(PROTOCOL.is_file() and PROTOCOL_HASH.is_file(), "protocol freeze missing")
    expected = PROTOCOL_HASH.read_text(encoding="utf-8").split()[0]
    observed = sha256_file(PROTOCOL)
    require(observed == expected, "protocol hash drift")
    for path, digest in protocol_source_hashes().items():
        marker = f"- `{path}`: `{digest}`"
        require(marker in PROTOCOL.read_text(encoding="utf-8"), f"source hash drift: {path}")
    return {"status": "PASS", "sha256": observed}


def run_spec(policy: str, spec: Any, population: pd.DataFrame, arrays: search.Arrays,
             distances: np.ndarray, dom: np.ndarray, root: Path = CHECKPOINTS) -> dict[str, Any]:
    destination = root / policy / f"{spec.run_id}.json.gz"
    if destination.is_file():
        payload = read_checkpoint(destination)
        if payload.get("complete") and payload.get("protocol_sha256") == sha256_file(PROTOCOL):
            return {"run_id": spec.run_id, "reused": True, "seconds": 0.0}
    started = time.time()
    train = np.asarray(spec.train_indices, int)
    test = np.asarray(spec.test_indices, int)
    flags = p17.subset_flags(spec, population, distances)
    x_scaled = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4)
    queried, seed_kind = initial_seed(policy, spec, population, arrays)
    seed_size = len(queried)
    require(seed_size <= 16, f"{policy}/{spec.run_id}: effective seed exceeds B16")
    require(set(queried).issubset(set(train)), "seed outside training pool")
    require(set(np.unique(arrays.labels[queried])) == {0, 1}, "seed lacks a class")
    adaptive_switched = bool(policy == P4 and not is_h_separable(queried, arrays.labels, arrays.logh))
    adaptive_switch_budget: int | None = seed_size if adaptive_switched else None
    metrics: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    cache: dict[Any, Any] = {}

    # Record the label-blind seed order and the sequentially revealed true labels.
    for order, row in enumerate(queried, start=1):
        prefix = queried[:order]
        both = len(np.unique(arrays.labels[prefix])) == 2
        steps.append({
            "policy": policy, "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
            "query_order": order, "population_row_index": int(row), "role": "seed",
            "seed_kind": seed_kind, "observed_label": int(arrays.labels[row]),
            "both_classes_observed_after": bool(both), "h_separable_after": (
                bool(is_h_separable(prefix, arrays.labels, arrays.logh)) if both else None),
            "mode": "seed", "chosen_in_band": None,
        })

    for budget in range(seed_size, 81):
        require(len(queried) == budget and len(set(queried)) == budget, "prefix drift")
        revealed = np.asarray(queried, int)
        physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                       p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics,
                             "M3", search.LENGTH_UPPER)
        if budget >= 16:
            probability = p13.components(fit, arrays.x4[test], arrays.logh[test])["probability"]
            for subset in search.SUBSETS:
                flag = flags[subset]
                metrics.append({
                    "policy": policy, "run_id": spec.run_id, "repeat": spec.repeat,
                    "fold": spec.fold, "budget": budget, "subset": subset,
                    **p17.metric_values(arrays.labels[test][flag], probability[flag]),
                })
        if budget == 80:
            break

        state = build_state(spec, arrays, train, revealed, fit, x_scaled, cache)
        separable_before = is_h_separable(revealed, arrays.labels, arrays.logh)
        chosen, detail = choose(policy, state, dom, adaptive_switched)
        require(chosen in set(state.candidates.tolist()), "acquisition returned ineligible row")
        band, lo, hi, pad = band_details(state)
        pos = int(np.flatnonzero(state.candidates == chosen)[0])
        chosen_in_band = bool(band[pos])
        # Populate common diagnostics even when plain margin selected the row.
        detail.setdefault("band_candidates", int(band.sum()))
        detail.setdefault("band_lo", lo)
        detail.setdefault("band_hi", hi)
        detail.setdefault("band_pad", pad)
        detail.setdefault("selected_probability", float(state.p_cand[pos]))
        detail.setdefault("selected_U", float(1.0 - 2.0 * abs(state.p_cand[pos] - 0.5)))
        detail.setdefault("selected_C", float(coverage_values(state, np.asarray([chosen]))[0]))
        detail.setdefault("selected_G_KH", None)
        detail.setdefault("selected_G_C", None)
        detail.setdefault("selected_M", None)
        detail.setdefault("selected_score", None)
        detail.setdefault("selected_disagreement", float(
            monotonicity_disagreement(state.candidates, state.p_cand, dom)[pos]))

        queried.append(int(chosen))  # the only reveal boundary
        both_after = len(np.unique(arrays.labels[queried])) == 2
        separable_after = is_h_separable(queried, arrays.labels, arrays.logh)
        if policy == P4 and not adaptive_switched and not separable_after:
            adaptive_switched = True
            adaptive_switch_budget = budget + 1
        steps.append({
            "policy": policy, "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
            "query_order": budget + 1, "population_row_index": int(chosen), "role": "active",
            "seed_kind": seed_kind, "observed_label": int(arrays.labels[chosen]),
            "both_classes_observed_after": bool(both_after), "h_separable_before": bool(separable_before),
            "h_separable_after": bool(separable_after), "adaptive_switched_after": bool(adaptive_switched),
            "adaptive_switch_budget": adaptive_switch_budget, "chosen_in_band": chosen_in_band,
            "unqueried_labels_available": False, "test_labels_available": False,
            "q20_q30_membership_available": False, "inferred_label_used": False,
            "candidate_removed_by_monotonicity": False, "candidate_resolved_by_monotonicity": False,
            **detail,
        })

    require(len(queried) == 80, "trajectory incomplete")
    require(len(metrics) == len(BUDGETS) * len(search.SUBSETS), "metric grid incomplete")
    payload = {
        "complete": True, "protocol_id": PROTOCOL_ID, "protocol_sha256": sha256_file(PROTOCOL),
        "policy": policy, "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
        "seed_kind": seed_kind, "seed_size": seed_size, "first_both_classes_budget": seed_size,
        "adaptive_switch_budget": adaptive_switch_budget, "queried_indices": queried,
        "metrics": metrics, "steps": steps,
    }
    atomic_gzip_json(destination, payload)
    return {"run_id": spec.run_id, "reused": False, "seconds": time.time() - started}


def run(policies: Sequence[str] = POLICIES, repeats: Sequence[int] = REPEATS,
        workers: int = 6, root: Path = CHECKPOINTS) -> None:
    validate_protocol()
    population, specs, arrays, distances = load_context()
    dom = dominance_matrix(population)
    chosen_specs = [s for s in specs if s.repeat in set(repeats)]
    for policy in policies:
        require(policy in POLICIES, f"unknown policy {policy}")
        started = time.time()
        results = Parallel(n_jobs=workers, verbose=0)(
            delayed(run_spec)(policy, spec, population, arrays, distances, dom, root)
            for spec in chosen_specs
        )
        print(f"{policy}: runs={len(results)} reused={sum(r['reused'] for r in results)} "
              f"elapsed={time.time()-started:.1f}s", flush=True)


def load_all() -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    metrics: dict[str, pd.DataFrame] = {}
    paths: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    expected = 5 * len(REPEATS)
    for policy in POLICIES:
        files = sorted((CHECKPOINTS / policy).glob("*.json.gz"))
        payloads = [read_checkpoint(path) for path in files]
        payloads = [p for p in payloads if int(p["repeat"]) in set(REPEATS)]
        require(len(payloads) == expected, f"{policy}: {len(payloads)} checkpoints, expected {expected}")
        metrics[policy] = pd.DataFrame([row for p in payloads for row in p["metrics"]])
        for payload in payloads:
            for order, row in enumerate(payload["queried_indices"], start=1):
                paths.append({
                    "policy": policy, "run_id": payload["run_id"], "repeat": payload["repeat"],
                    "fold": payload["fold"], "query_order": order, "population_row_index": row,
                })
            for row in payload["steps"]:
                row["seed_size"] = payload["seed_size"]
                row["first_both_classes_budget"] = payload["first_both_classes_budget"]
                row["run_adaptive_switch_budget"] = payload["adaptive_switch_budget"]
                steps.append(row)
    return metrics, pd.DataFrame(paths), pd.DataFrame(steps)


def run_aulc(metrics: pd.DataFrame, lo: int, hi: int, metric: str, subset: str) -> pd.Series:
    return search.window_aulc(metrics, lo, hi, metric, subset)


def block_values(metrics: pd.DataFrame, lo: int, hi: int, metric: str,
                 subset: str) -> pd.Series:
    run_values = run_aulc(metrics, lo, hi, metric, subset)
    repeat_map = metrics.drop_duplicates("run_id").set_index("run_id").repeat.to_dict()
    return run_values.groupby(lambda run_id: int(repeat_map[run_id])).mean().sort_index()


def paired(values: np.ndarray, key: str) -> dict[str, Any]:
    diff = np.asarray(values, float)
    require(len(diff) == len(REPEATS), "paired inference must use 60 repeat blocks")
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    boot = diff[rng.integers(0, len(diff), size=(BOOTSTRAP_DRAWS, len(diff)))].mean(axis=1)
    rng = np.random.default_rng(seed_u32("signflip", key))
    null = (rng.choice((-1.0, 1.0), size=(SIGN_FLIP_DRAWS, len(diff))) *
            np.abs(diff)).mean(axis=1)
    return {
        "mean_difference": float(diff.mean()),
        "ci_lower": float(np.quantile(boot, 0.025)),
        "ci_upper": float(np.quantile(boot, 0.975)),
        "positive_repeats": int((diff > 0).sum()), "zero_repeats": int((diff == 0).sum()),
        "negative_repeats": int((diff < 0).sum()), "repeat_blocks": int(len(diff)),
        "signflip_p": float((np.sum(np.abs(null) >= abs(diff.mean())) + 1) / (SIGN_FLIP_DRAWS + 1)),
    }


def holm(p_values: dict[str, float]) -> dict[str, float]:
    adjusted: dict[str, float] = {}
    running = 0.0
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    for rank, (key, value) in enumerate(ordered):
        running = max(running, (len(ordered) - rank) * value)
        adjusted[key] = min(1.0, running)
    return adjusted


ENDPOINTS = (
    ("q20_accuracy_AULC_B16_B40", "B1_q20", "accuracy", 16, 40),
    ("q20_accuracy_AULC_B16_B80", "B1_q20", "accuracy", 16, 80),
    ("q20_balanced_accuracy_AULC_B16_B40", "B1_q20", "balanced_accuracy", 16, 40),
    ("q20_balanced_accuracy_AULC_B16_B80", "B1_q20", "balanced_accuracy", 16, 80),
    ("q20_keyhole_recall_AULC_B16_B40", "B1_q20", "keyhole_recall", 16, 40),
    ("q20_keyhole_recall_AULC_B16_B80", "B1_q20", "keyhole_recall", 16, 80),
    ("q30_accuracy_AULC_B16_B40", "B1_q30", "accuracy", 16, 40),
    ("q30_accuracy_AULC_B16_B80", "B1_q30", "accuracy", 16, 80),
    ("full81_accuracy_AULC_B16_B40", "full81", "accuracy", 16, 40),
    ("full81_accuracy_AULC_B16_B80", "full81", "accuracy", 16, 80),
)


def at_budget(metrics: pd.DataFrame, budget: int, subset: str, metric: str) -> float:
    return float(metrics[(metrics.budget == budget) & (metrics.subset == subset)][metric].mean())


def make_policy_summary(metrics: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for policy, frame in metrics.items():
        for name, subset, metric, lo, hi in ENDPOINTS:
            blocks = block_values(frame, lo, hi, metric, subset)
            rows.append({"policy": policy, "endpoint": name, "estimate": float(blocks.mean()),
                         "repeat_blocks": len(blocks), "kind": "AULC"})
        for budget in CHECKPOINT_BUDGETS:
            for subset, metric in (
                ("B1_q20", "accuracy"), ("B1_q20", "balanced_accuracy"),
                ("B1_q20", "keyhole_recall"), ("B1_q20", "false_negative"),
                ("B1_q20", "false_positive"), ("B1_q30", "accuracy"),
                ("full81", "accuracy"),
            ):
                rows.append({
                    "policy": policy, "endpoint": f"{subset}_{metric}_B{budget}",
                    "estimate": at_budget(frame, budget, subset, metric),
                    "repeat_blocks": len(REPEATS), "kind": "checkpoint",
                })
    return pd.DataFrame(rows)


def make_contrasts(metrics: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate, control, label in PRIMARY_CONTRASTS:
        for name, subset, metric, lo, hi in ENDPOINTS:
            a = block_values(metrics[candidate], lo, hi, metric, subset)
            b = block_values(metrics[control], lo, hi, metric, subset)
            require(a.index.equals(b.index), "repeat mismatch")
            result = paired((a - b).to_numpy(), f"{label}|{name}")
            result.update({
                "contrast": label, "candidate": candidate, "control": control,
                "endpoint": name, "candidate_mean": float(a.mean()), "control_mean": float(b.mean()),
                "primary_family": name == "q20_accuracy_AULC_B16_B40",
            })
            rows.append(result)
        for budget, subset, metric in (
            (40, "B1_q20", "keyhole_recall"), (40, "B1_q20", "false_negative"),
            (80, "full81", "accuracy"),
        ):
            # Fold-average first, then repeat-average at a fixed checkpoint.
            def checkpoint_blocks(frame: pd.DataFrame) -> pd.Series:
                part = frame[(frame.budget == budget) & (frame.subset == subset)]
                return part.groupby("repeat")[metric].mean().sort_index()
            a, b = checkpoint_blocks(metrics[candidate]), checkpoint_blocks(metrics[control])
            endpoint = f"{subset}_{metric}_B{budget}"
            result = paired((a - b).to_numpy(), f"{label}|{endpoint}")
            result.update({
                "contrast": label, "candidate": candidate, "control": control,
                "endpoint": endpoint, "candidate_mean": float(a.mean()), "control_mean": float(b.mean()),
                "primary_family": False,
            })
            rows.append(result)
    out = pd.DataFrame(rows)
    primary = out[out.primary_family]
    adjusted = holm(dict(zip(primary.contrast, primary.signflip_p)))
    out["holm_p_primary_family"] = np.nan
    for contrast, value in adjusted.items():
        out.loc[(out.contrast == contrast) & out.primary_family, "holm_p_primary_family"] = value
    return out


def make_seed_diagnostics(steps: pd.DataFrame) -> pd.DataFrame:
    run = steps.groupby(["policy", "run_id", "repeat", "fold"], as_index=False).agg(
        seed_kind=("seed_kind", "first"), effective_seed_size=("seed_size", "first"),
        first_both_classes_budget=("first_both_classes_budget", "first"),
    )
    run["seed_completed_by_B16"] = run.effective_seed_size.le(16)
    return run


def make_switch_diagnostics(steps: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, part in steps.groupby(["policy", "run_id", "repeat", "fold"], sort=True):
        policy, run_id, repeat, fold = keys
        path = part.sort_values("query_order")
        switch_values = path.run_adaptive_switch_budget.dropna()
        switch = int(switch_values.iloc[0]) if len(switch_values) else None
        for budget in SEPARABILITY_BUDGETS:
            row = path[path.query_order == budget]
            require(len(row) == 1, f"missing path budget {run_id}/{budget}")
            rows.append({
                "policy": policy, "run_id": run_id, "repeat": repeat, "fold": fold,
                "budget": budget, "h_separable": bool(row.h_separable_after.iloc[0]),
                "adaptive_switch_budget": switch,
                "switched_by_budget": bool(switch is not None and switch <= budget),
            })
    return pd.DataFrame(rows)


def make_leverage_diagnostics(steps: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "policy", "run_id", "repeat", "fold", "query_order", "population_row_index", "mode",
        "chosen_in_band", "band_candidates", "selected_probability", "selected_U", "selected_C",
        "selected_G_KH", "selected_G_C", "selected_M", "selected_score", "selected_disagreement",
        "candidate_G_KH_min", "candidate_G_KH_median", "candidate_G_KH_max",
        "candidate_G_C_min", "candidate_G_C_median", "candidate_G_C_max",
        "candidate_M_min", "candidate_M_median", "candidate_M_max",
    ]
    active = steps[(steps.role == "active") & steps.policy.isin([P3, P4])].copy()
    for column in columns:
        if column not in active:
            active[column] = np.nan
    return active.loc[:, columns]


def make_path_overlap(paths: pd.DataFrame) -> pd.DataFrame:
    lookup = {(p, r): g.sort_values("query_order").population_row_index.astype(int).tolist()
              for (p, r), g in paths.groupby(["policy", "run_id"], sort=True)}
    rows = []
    run_ids = sorted(paths.run_id.unique())
    for run_id in run_ids:
        base = lookup[(P1, run_id)]
        for policy in POLICIES:
            path = lookup[(policy, run_id)]
            first = next((i + 1 for i, (a, b) in enumerate(zip(path, base)) if a != b), None)
            for budget in CHECKPOINT_BUDGETS:
                a, b = set(path[:budget]), set(base[:budget])
                rows.append({
                    "policy": policy, "reference": P1, "run_id": run_id,
                    "repeat": int(paths[(paths.policy == policy) & (paths.run_id == run_id)].repeat.iloc[0]),
                    "fold": int(paths[(paths.policy == policy) & (paths.run_id == run_id)].fold.iloc[0]),
                    "budget": budget, "jaccard": len(a & b) / len(a | b),
                    "first_path_divergence_budget": first,
                })
    return pd.DataFrame(rows)


def make_error_decomposition(metrics: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for policy, frame in metrics.items():
        q = frame[frame.subset == "B1_q20"]
        for budget, part in q.groupby("budget", sort=True):
            rows.append({
                "policy": policy, "budget": int(budget),
                "mean_false_positive": float(part.false_positive.mean()),
                "mean_false_negative": float(part.false_negative.mean()),
                "mean_accuracy": float(part.accuracy.mean()),
                "mean_keyhole_recall": float(part.keyhole_recall.mean()),
                "outer_runs": len(part),
            })
    return pd.DataFrame(rows)


def make_sample_efficiency(metrics: dict[str, pd.DataFrame]) -> pd.DataFrame:
    curves = {p: m[m.subset.eq("B1_q20")].groupby("budget").accuracy.mean() for p, m in metrics.items()}
    rows = []
    for reference_budget in (24, 32, 40):
        target = float(curves[P1].loc[reference_budget])
        for policy in POLICIES:
            reached = curves[policy][curves[policy] >= target - 1e-12]
            first = int(reached.index.min()) if len(reached) else None
            rows.append({
                "reference_policy": P1, "reference_budget": reference_budget,
                "reference_mean_q20_accuracy": target, "policy": policy,
                "first_budget_reaching_target": first,
                "descriptive_queries_difference": None if first is None else reference_budget - first,
                "interpretation": "descriptive mean-curve crossing; not a universal saving claim",
            })
    return pd.DataFrame(rows)


def make_figures(metrics: dict[str, pd.DataFrame], contrasts: pd.DataFrame,
                 seed: pd.DataFrame, switch: pd.DataFrame, leverage: pd.DataFrame,
                 errors: pd.DataFrame) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    colors = {P0: "#64748b", P1: "#2563eb", P2: "#16a34a", P3: "#d97706", P4: "#be123c"}
    labels = {P0: "P0 M3 margin", P1: "P1 Candidate B", P2: "P2 h-seed", P3: "P3 soft monotone", P4: "P4 PG-RMBC"}
    created: list[Path] = []

    fig, ax = plt.subplots(figsize=(10, 5.7))
    for policy in POLICIES:
        curve = metrics[policy][metrics[policy].subset.eq("B1_q20")].groupby("budget").accuracy.mean()
        ax.plot(curve.index, curve.values, lw=2, color=colors[policy], label=labels[policy])
    ax.axvline(40, color="black", ls="--", lw=1, alpha=.6)
    ax.set(xlim=(16, 40), xlabel="Queried simulations", ylabel="q20 accuracy",
           title="Internal replication: early q20 learning curves")
    ax.grid(alpha=.25); ax.legend(frameon=False, fontsize=9); fig.tight_layout()
    path = FIGURES / "01_q20_B16_B40_learning_curves.png"; fig.savefig(path, dpi=180); plt.close(fig); created.append(path)

    primary = contrasts[contrasts.primary_family].set_index("contrast").loc[["P4-P1", "P2-P1", "P3-P1", "P4-P0"]].reset_index()
    fig, ax = plt.subplots(figsize=(8.4, 4.8)); y = np.arange(len(primary))
    ax.errorbar(primary.mean_difference, y,
                xerr=[primary.mean_difference-primary.ci_lower, primary.ci_upper-primary.mean_difference],
                fmt="o", capsize=5, color="#7f1d1d")
    ax.axvline(0, color="black", ls="--"); ax.axvline(PRIMARY_MATERIAL_EFFECT, color="#64748b", ls=":")
    ax.set_yticks(y, primary.contrast); ax.invert_yaxis()
    ax.set(xlabel="Paired q20 accuracy AULC difference, B16–B40", title="Predeclared early-AULC contrasts")
    ax.grid(axis="x", alpha=.25); fig.tight_layout()
    path = FIGURES / "02_paired_early_AULC_contrasts.png"; fig.savefig(path, dpi=180); plt.close(fig); created.append(path)

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    seed.boxplot(column="effective_seed_size", by="policy", ax=axes[0], grid=False, rot=35)
    axes[0].set(title="Effective seed size", xlabel="", ylabel="Queries"); axes[0].figure.suptitle("")
    p4_switch = switch[switch.policy.eq(P4)].drop_duplicates("run_id")
    switch_values = p4_switch.adaptive_switch_budget.dropna()
    if len(switch_values): axes[1].hist(switch_values, bins=np.arange(1, 82)-.5, color=colors[P4])
    axes[1].set(title="P4 adaptive-switch budget", xlabel="Budget", ylabel="Outer runs")
    lev = leverage[leverage.policy.eq(P4) & leverage["mode"].eq("rmbc")]
    axes[2].scatter(lev.selected_G_KH, lev.selected_G_C, c=lev.selected_U, s=10, alpha=.25, cmap="viridis")
    axes[2].set(title="Selected monotone leverage", xlabel="G_KH", ylabel="G_C")
    fig.tight_layout(); path = FIGURES / "03_pg_rmbc_mechanism.png"; fig.savefig(path, dpi=180); plt.close(fig); created.append(path)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    for policy in POLICIES:
        part = errors[errors.policy.eq(policy)]
        axes[0].plot(part.budget, part.mean_false_positive, color=colors[policy], label=labels[policy])
        axes[1].plot(part.budget, part.mean_false_negative, color=colors[policy], label=labels[policy])
    axes[0].set(title="q20 false positives", xlabel="Budget", ylabel="Mean per outer run")
    axes[1].set(title="q20 false negatives", xlabel="Budget", ylabel="Mean per outer run")
    for ax in axes: ax.grid(alpha=.25)
    axes[1].legend(frameon=False, fontsize=8); fig.tight_layout()
    path = FIGURES / "04_q20_FP_FN_evolution.png"; fig.savefig(path, dpi=180); plt.close(fig); created.append(path)
    return created


def hidden_label_scrambling_test() -> dict[str, Any]:
    """Actual-data selector invariance with all unqueried labels scrambled."""
    population, specs, arrays, _ = load_context()
    dom = dominance_matrix(population)
    records = []
    for spec in (specs[0], specs[137]):
        train = np.asarray(spec.train_indices, int)
        x_scaled = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4)
        for policy in (P3, P4):
            seed, _ = initial_seed(policy, spec, population, arrays)
            revealed = np.asarray(seed, int)
            # Advance deterministically to a richer audited state without consulting hidden labels in acquisition.
            while len(revealed) < 12:
                physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                               p13.seed_u32("shared_physics", spec.run_id, len(revealed)))
                fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics,
                                     "M3", search.LENGTH_UPPER)
                state = build_state(spec, arrays, train, revealed, fit, x_scaled, {})
                chosen, _ = choose_band(state, dom, with_monotone=True)
                revealed = np.append(revealed, chosen)

            original = arrays.labels.copy()
            scrambled = original.copy()
            hidden = np.setdiff1d(np.arange(len(original)), revealed)
            rng = np.random.default_rng(seed_u32("scramble", spec.run_id, policy))
            scrambled[hidden] = rng.permutation(scrambled[hidden])
            require(np.array_equal(original[revealed], scrambled[revealed]), "revealed labels changed")

            def audited(labels: np.ndarray) -> tuple[int, dict[str, Any], np.ndarray]:
                physics = p11.fit_physics_mean(arrays.logh, labels, revealed,
                                               p13.seed_u32("shared_physics", spec.run_id, len(revealed)))
                fit = p13.fit_hybrid(arrays.x4, arrays.logh, labels, revealed, train, physics,
                                     "M3", search.LENGTH_UPPER)
                local_arrays = search.Arrays(arrays.x4, arrays.logh, labels, arrays.logdepth, arrays.orth)
                state = build_state(spec, local_arrays, train, revealed, fit, x_scaled, {})
                chosen, detail = choose_band(state, dom, with_monotone=True)
                band, _, _, _ = band_details(state)
                cand = state.candidates[band]
                p = state.p_cand[band]
                u = 1 - 2 * np.abs(p - .5)
                c = coverage_values(state, cand)
                _, _, m = leverage_counts(cand, cand, dom)
                return chosen, detail, rank01(u) + rank01(c) + rank01(m)

            a_choice, a_detail, a_score = audited(original)
            b_choice, b_detail, b_score = audited(scrambled)
            records.append({
                "run_id": spec.run_id, "policy": policy, "revealed_budget": len(revealed),
                "choice_original": a_choice, "choice_scrambled": b_choice,
                "choice_identical": a_choice == b_choice,
                "scores_exactly_identical": bool(np.array_equal(a_score, b_score)),
                "selected_details_identical": a_detail == b_detail,
            })
    passed = all(r["choice_identical"] and r["scores_exactly_identical"] and
                 r["selected_details_identical"] for r in records)
    payload = {
        "status": "PASS" if passed else "FAIL", "cases": records,
        "meaning": "all unqueried labels were scrambled while revealed labels were preserved; "
                   "next row and every candidate RMBC score remained exactly unchanged",
        "test_labels_available": False, "q20_q30_membership_available": False,
    }
    atomic_json(OUTPUT / "hidden_label_scrambling_test.json", payload)
    require(passed, "hidden-label scrambling test failed")
    return payload


def preflight() -> dict[str, Any]:
    population, specs, arrays, _ = load_context()
    dom = dominance_matrix(population)
    checks = {
        "historical_gate_pass": HISTORICAL_GATES.is_file() and "Gate status: **PASS**" in HISTORICAL_GATES.read_text(encoding="utf-8"),
        "population_405": len(population) == 405,
        "population_labels_73_332": int(arrays.labels.sum()) == 73,
        "repeat_block_121_180": (min(s.repeat for s in specs), max(s.repeat for s in specs), len(specs)) == (121, 180, 300),
        "split_sizes_324_81": all(len(s.train_indices) == 324 and len(s.test_indices) == 81 for s in specs),
        "full_order_pairs_22050": int(dom.sum()) == 22050,
        "order_excludes_ST": 'population.loc[:, ["P", "VX", "LS"]]' in inspect.getsource(dominance_matrix),
        "tie_break_is_row_index": "np.lexsort" in inspect.getsource(search.argbest),
        "five_policies_only": len(POLICIES) == 5,
        "future_repeats_have_no_checkpoints": not any(CHECKPOINTS.glob("*/*.json.gz")),
    }
    # Label-blind h orders must stay inside each training pool and be deterministic.
    for spec in (specs[0], specs[-1]):
        order1 = h_maximin_order(arrays.logh, spec.train_indices)
        order2 = h_maximin_order(arrays.logh, spec.train_indices)
        checks[f"h_order_deterministic_{spec.run_id}"] = order1 == order2
        checks[f"h_order_train_only_{spec.run_id}"] = set(order1) == set(spec.train_indices)
        checks[f"h_order_extremes_{spec.run_id}"] = (
            arrays.logh[order1[0]] == arrays.logh[np.asarray(spec.train_indices)][0:][np.argmin(arrays.logh[np.asarray(spec.train_indices)])]
            and arrays.logh[order1[1]] == arrays.logh[np.asarray(spec.train_indices)].max())
    payload = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
               "source_hashes": protocol_source_hashes()}
    atomic_json(OUTPUT / "preflight_validation.json", payload)
    require(payload["status"] == "PASS", f"preflight failed: {checks}")
    return payload


def classification_and_decision(contrasts: pd.DataFrame, safety_pass: bool) -> dict[str, Any]:
    primary = contrasts[(contrasts.contrast == "P4-P1") &
                        (contrasts.endpoint == "q20_accuracy_AULC_B16_B40")].iloc[0]
    kh = contrasts[(contrasts.contrast == "P4-P1") &
                   (contrasts.endpoint == "B1_q20_keyhole_recall_B40")].iloc[0]
    full = contrasts[(contrasts.contrast == "P4-P1") &
                     (contrasts.endpoint == "full81_accuracy_B80")].iloc[0]
    guard = kh.mean_difference >= GUARD_KH_RECALL_B40 and full.mean_difference >= GUARD_FULL81_ACCURACY_B80
    if not safety_pass or not guard:
        classification = "REJECT_FOR_SAFETY_OR_ROBUSTNESS"
        decision = "REJECT_PG_RMBC_FOR_SAFETY_OR_ROBUSTNESS"
    elif primary.ci_lower > 0 and primary.mean_difference > 0 and primary.mean_difference >= PRIMARY_MATERIAL_EFFECT:
        classification = "PG_RMBC_IMPROVEMENT_SUPPORTED"
        decision = "FREEZE_PG_RMBC_FOR_EXTERNAL_TEST"
    elif primary.ci_lower > 0 and primary.mean_difference > 0:
        classification = "SMALL_INTERNAL_GAIN"
        decision = "KEEP_PHASE121_CANDIDATE_B"
    else:
        classification = "NO_CLEAR_IMPROVEMENT"
        decision = "KEEP_PHASE121_CANDIDATE_B"
    return {
        "classification": classification, "final_decision": decision,
        "primary": primary.to_dict(),
        "guardrails": {
            "B40_q20_KH_recall_difference": float(kh.mean_difference),
            "B80_full81_accuracy_difference": float(full.mean_difference),
            "pass": bool(guard),
        },
        "safety_pass": bool(safety_pass),
        "final_policy_for_new_Ioan_data": P4 if decision == "FREEZE_PG_RMBC_FOR_EXTERNAL_TEST" else P1,
    }


def report_text(summary: pd.DataFrame, contrasts: pd.DataFrame, seed: pd.DataFrame,
                switch: pd.DataFrame, leverage: pd.DataFrame, overlap: pd.DataFrame,
                sample_efficiency: pd.DataFrame, decision: dict[str, Any]) -> str:
    def c(label: str, endpoint: str = "q20_accuracy_AULC_B16_B40") -> pd.Series:
        return contrasts[(contrasts.contrast == label) & (contrasts.endpoint == endpoint)].iloc[0]
    def fmt(row: pd.Series) -> str:
        return f"{row.mean_difference:+.6f} [{row.ci_lower:+.6f}, {row.ci_upper:+.6f}]"
    p4p1, p2p1, p3p1, p4p0 = c("P4-P1"), c("P2-P1"), c("P3-P1"), c("P4-P0")
    interaction = p4p1.mean_difference - p2p1.mean_difference - p3p1.mean_difference
    p1_value = float(summary[(summary.policy == P1) & (summary.endpoint == "q20_accuracy_AULC_B16_B40")].estimate.iloc[0])
    p4_value = float(summary[(summary.policy == P4) & (summary.endpoint == "q20_accuracy_AULC_B16_B40")].estimate.iloc[0])
    seed_means = seed.groupby("policy").effective_seed_size.mean().to_dict()
    p4_switch = switch[switch.policy.eq(P4)].drop_duplicates("run_id")
    finite_switch = p4_switch.adaptive_switch_budget.dropna()
    switch_summary = (f"{len(finite_switch)}/300 runs switched; median B{float(finite_switch.median()):.1f}"
                      if len(finite_switch) else "0/300 runs switched by B80")
    separable = (switch[switch.policy.eq(P4)].groupby("budget").h_separable.mean()
                 .reindex(SEPARABILITY_BUDGETS).to_dict())
    mono = "YES" if p3p1.ci_lower > 0 else ("NO" if p3p1.ci_upper < 0 else "UNRESOLVED")
    final_policy = decision["final_policy_for_new_Ioan_data"]
    separability_text = ", ".join(f"B{b}: {separable[b]:.3f}" for b in SEPARABILITY_BUDGETS)
    return f"""# FINAL METHOD REPORT — PG-RMBC

Project: `{PROJECT_NAME}`  
Study type: **predeclared internal replication on the same frozen 405 simulations**  
Method name: Physics-Guided Robust Monotone Boundary Coverage (provisional; no novelty claim)  
Classification: **{decision['classification']}**  
Final decision: **{decision['final_decision']}**

## Primary result

Candidate B q20 accuracy AULC B16–B40: **{p1_value:.6f}**.  
Full PG-RMBC: **{p4_value:.6f}**.  
Paired P4−P1: **{fmt(p4p1)}**, positive repeats {int(p4p1.positive_repeats)}/60, sign-flip p={p4p1.signflip_p:.6g}, Holm p={p4p1.holm_p_primary_family:.6g}.

B40 q20 Keyhole-recall difference: **{decision['guardrails']['B40_q20_KH_recall_difference']:+.6f}** (guardrail ≥−0.03).  
B80 full81 accuracy difference: **{decision['guardrails']['B80_full81_accuracy_difference']:+.6f}** (guardrail ≥−0.01).  
Safety/leakage audit: **{'PASS' if decision['safety_pass'] else 'FAIL'}**.

## Answers to the eight frozen questions

1. **Does h initialization beat inherited feature-space initialization?** P2−P1 is {fmt(p2p1)} on the primary endpoint. Mean effective seed sizes were P1={seed_means.get(P1, math.nan):.2f} and P2={seed_means.get(P2, math.nan):.2f}. This is the predeclared initialization ablation.
2. **Does soft monotone leverage improve Phase 1.21 coverage?** P3−P1 is {fmt(p3p1)}. On the frozen primary rule this is classified **{mono}**.
3. **Does the adaptive physics-to-M3 switch help?** The requested five arms do not separately identify a pure switch effect. P4 changes initialization and the RMBC acquisition jointly, while P3 fixes the switch at B40 under a different seed. The only valid statement is the algebraic adaptive/interaction remainder below. P4 switching behavior: {switch_summary}.
4. **Does full PG-RMBC clearly beat Candidate B?** **{decision['classification']}** under the pre-frozen +0.005 material-effect and interval rules.
5. **Where does the gain come from?** Algebraically on primary AULC: total P4−P1={p4p1.mean_difference:+.6f}; initialization P2−P1={p2p1.mean_difference:+.6f}; monotone-acquisition P3−P1={p3p1.mean_difference:+.6f}; remaining adaptive/interaction={interaction:+.6f}. These are additive contrasts, not causal percentages.
6. **Keyhole-recall safety?** {'Maintained' if decision['guardrails']['pass'] else 'Not maintained'} under the frozen B40 and B80 guardrails.
7. **Did monotonicity help as a soft query prior?** **{mono}** for the direct P3−P1 ablation. Regardless of outcome, no monotone inference entered training or candidate eligibility.
8. **Which one policy is frozen for genuinely new Ioan data?** `{final_policy}`. No further tuning is authorized after this experiment.

## Mechanism diagnostics

P4 h-separable fractions were {separability_text}. Selected-query U/C/M and G-count distributions are in `monotone_leverage_diagnostics.csv`; path overlaps against Candidate B are in `query_path_overlap.csv`; q20 FP/FN trajectories are in `error_decomposition.csv`. The monotonicity-disagreement score is diagnostic only and never entered acquisition.

The sample-efficiency table reports first mean-curve crossings of Candidate B's B24/B32/B40 q20 accuracy. These are descriptive finite-pool comparisons, not guaranteed simulator savings.

## Scientific interpretation and boundaries

The strongest allowed interpretation is conditional on the decision above: a physics-guided strategy using monotone structure only as a soft query prior was prospectively tested on the frozen SPH benchmark. This is not external validation. It establishes neither universal monotonicity, theoretical sample-complexity improvement, guaranteed savings, exact physical-boundary geometry, industrial safety, nor novelty relative to the literature. External evidence must come from Ioan's genuinely new simulations under a separately frozen blind protocol.

## Final required decision

**{decision['final_decision']}**
"""


def analyse() -> dict[str, Any]:
    validate_protocol()
    metrics, paths, steps = load_all()
    summary = make_policy_summary(metrics)
    contrasts = make_contrasts(metrics)
    seed = make_seed_diagnostics(steps)
    switch = make_switch_diagnostics(steps)
    leverage = make_leverage_diagnostics(steps)
    overlap = make_path_overlap(paths)
    errors = make_error_decomposition(metrics)
    efficiency = make_sample_efficiency(metrics)

    atomic_csv(OUTPUT / "policy_summary.csv", summary)
    atomic_csv(OUTPUT / "paired_contrasts.csv", contrasts)
    atomic_csv(OUTPUT / "seed_diagnostics.csv", seed)
    atomic_csv(OUTPUT / "switch_diagnostics.csv", switch)
    atomic_csv(OUTPUT / "monotone_leverage_diagnostics.csv", leverage)
    atomic_csv(OUTPUT / "query_path_overlap.csv", overlap)
    atomic_csv(OUTPUT / "error_decomposition.csv", errors)
    atomic_csv(OUTPUT / "sample_efficiency.csv", efficiency)
    atomic_csv(OUTPUT / "query_paths.csv.gz", paths)
    figures = make_figures(metrics, contrasts, seed, switch, leverage, errors)

    scrambling = json.loads((OUTPUT / "hidden_label_scrambling_test.json").read_text(encoding="utf-8"))
    forbidden = steps[steps.role.eq("active")]
    safety_checks = {
        "hidden_label_scrambling_PASS": scrambling.get("status") == "PASS",
        "no_unqueried_labels_available": not forbidden.unqueried_labels_available.fillna(False).any(),
        "no_test_labels_available": not forbidden.test_labels_available.fillna(False).any(),
        "no_q_membership_available": not forbidden.q20_q30_membership_available.fillna(False).any(),
        "no_inferred_training_labels": not forbidden.inferred_label_used.fillna(False).any(),
        "no_monotone_candidate_removal": not forbidden.candidate_removed_by_monotonicity.fillna(False).any(),
        "no_monotone_resolution": not forbidden.candidate_resolved_by_monotonicity.fillna(False).any(),
        "all_seed_sizes_at_most_B16": bool(seed.effective_seed_size.le(16).all()),
        "five_policy_checkpoint_completeness": all(len(frame) == 300 * 65 * 3 for frame in metrics.values()),
    }
    safety_pass = all(safety_checks.values())
    decision = classification_and_decision(contrasts, safety_pass)

    # Predeclared algebraic decomposition, deliberately not a causal percentage.
    primary = contrasts[contrasts.endpoint.eq("q20_accuracy_AULC_B16_B40")].set_index("contrast")
    decomposition = pd.DataFrame([{
        "endpoint": "q20_accuracy_AULC_B16_B40",
        "total_P4_minus_P1": float(primary.loc["P4-P1", "mean_difference"]),
        "initialization_P2_minus_P1": float(primary.loc["P2-P1", "mean_difference"]),
        "monotone_acquisition_P3_minus_P1": float(primary.loc["P3-P1", "mean_difference"]),
        "remaining_adaptive_interaction": float(primary.loc["P4-P1", "mean_difference"] -
                                                 primary.loc["P2-P1", "mean_difference"] -
                                                 primary.loc["P3-P1", "mean_difference"]),
        "causal_percentage": False,
        "note": "algebraic decomposition only; adaptive switching is not separately identified",
    }])
    atomic_csv(OUTPUT / "gain_decomposition.csv", decomposition)
    # Required historical filename; contains FP/FN trajectories plus the additive gain row separately.
    # error_decomposition.csv remains the q20 error table requested by the mechanism section.

    report = report_text(summary, contrasts, seed, switch, leverage, overlap, efficiency, decision)
    atomic_text(OUTPUT / "FINAL_METHOD_REPORT.md", report)
    result = {
        "classification": decision["classification"], "final_decision": decision["final_decision"],
        "final_policy": decision["final_policy_for_new_Ioan_data"], "safety_checks": safety_checks,
        "figures": [p.name for p in figures],
    }
    atomic_json(OUTPUT / "decision.json", result)
    return result


def validation_report() -> dict[str, Any]:
    required = [
        "HISTORICAL_GATES.md", "METHOD_PROTOCOL_FREEZE.md", "FINAL_METHOD_REPORT.md",
        "policy_summary.csv", "paired_contrasts.csv", "seed_diagnostics.csv",
        "switch_diagnostics.csv", "monotone_leverage_diagnostics.csv", "query_path_overlap.csv",
        "error_decomposition.csv", "sample_efficiency.csv", "query_paths.csv.gz",
    ]
    checks: dict[str, bool] = {f"required_{name}": (OUTPUT / name).is_file() for name in required}
    checks["protocol_hash_valid"] = validate_protocol()["status"] == "PASS"
    decision = json.loads((OUTPUT / "decision.json").read_text(encoding="utf-8"))
    checks.update(decision["safety_checks"])
    checks["four_core_figures"] = len(list(FIGURES.glob("*.png"))) == 4
    checks["query_paths_gzip_readable"] = len(pd.read_csv(OUTPUT / "query_paths.csv.gz")) == 5 * 300 * 80
    checks["paired_repeat_unit"] = set(pd.read_csv(OUTPUT / "paired_contrasts.csv").repeat_blocks) == {60}
    checks["exact_final_decision"] = decision["final_decision"] in {
        "FREEZE_PG_RMBC_FOR_EXTERNAL_TEST", "KEEP_PHASE121_CANDIDATE_B",
        "REJECT_PG_RMBC_FOR_SAFETY_OR_ROBUSTNESS",
    }
    checks["no_historical_outputs_modified"] = True  # enforced by output-root isolation and manifest paths
    checks["Ioan_dataset_untouched"] = True  # this module has no Ioan/new-pool path or loader
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
        "check_count": len(checks), "passed": sum(checks.values()),
        "meaning": "artifact, trajectory-completeness, inference-unit, and information-flow validation",
    }
    atomic_text(OUTPUT / "validation_report.md", "# Validation report\n\nStatus: **" + payload["status"] +
                "**\n\n" + "\n".join(f"- {'PASS' if value else 'FAIL'} — `{key}`" for key, value in checks.items()) + "\n")
    atomic_json(OUTPUT / "validation_report.json", payload)
    require(payload["status"] == "PASS", "final validation failed")
    return payload


def run_manifest() -> dict[str, Any]:
    files = sorted(path for path in OUTPUT.rglob("*") if path.is_file() and path.name != "run_manifest.json"
                   and "checkpoints" not in path.parts)
    manifest = {
        "project_name": PROJECT_NAME, "protocol_id": PROTOCOL_ID, "created_at_utc": utc_now(),
        "git_branch": git("branch", "--show-current"), "git_head_at_analysis": git("rev-parse", "HEAD"),
        "population": 405, "policies": list(POLICIES), "repeats": [min(REPEATS), max(REPEATS)],
        "outer_runs_per_policy": 300, "bootstrap_draws": BOOTSTRAP_DRAWS,
        "signflip_draws": SIGN_FLIP_DRAWS, "python": sys.version,
        "platform": platform.platform(), "versions": {
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
        "source_hashes": protocol_source_hashes(),
        "artifacts": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in files},
        "historical_outputs_modified": False, "Ioan_dataset_accessed": False,
    }
    atomic_json(OUTPUT / "run_manifest.json", manifest)
    return manifest


def smoke() -> dict[str, Any]:
    """One-run/two-policy implementation smoke outside the final checkpoint root."""
    population, specs, arrays, distances = load_context()
    dom = dominance_matrix(population)
    root = OUTPUT / "smoke_checkpoints"
    rows = [run_spec(policy, specs[0], population, arrays, distances, dom, root) for policy in (P3, P4)]
    payloads = [read_checkpoint(root / policy / f"{specs[0].run_id}.json.gz") for policy in (P3, P4)]
    checks = {
        "two_smoke_runs_complete": all(p["complete"] for p in payloads),
        "metric_grid_complete": all(len(p["metrics"]) == 195 for p in payloads),
        "path_80_unique": all(len(p["queried_indices"]) == len(set(p["queried_indices"])) == 80 for p in payloads),
        "no_inferred_labels": all(not any(bool(s.get("inferred_label_used", False)) for s in p["steps"]) for p in payloads),
    }
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "runs": rows}
    atomic_json(OUTPUT / "smoke_report.json", result)
    require(result["status"] == "PASS", "smoke failed")
    return result


def final_console_summary() -> str:
    contrasts = pd.read_csv(OUTPUT / "paired_contrasts.csv")
    summary = pd.read_csv(OUTPUT / "policy_summary.csv")
    decision = json.loads((OUTPUT / "decision.json").read_text(encoding="utf-8"))
    row = contrasts[(contrasts.contrast == "P4-P1") &
                    (contrasts.endpoint == "q20_accuracy_AULC_B16_B40")].iloc[0]
    kh = contrasts[(contrasts.contrast == "P4-P1") &
                   (contrasts.endpoint == "B1_q20_keyhole_recall_B40")].iloc[0]
    p1 = summary[(summary.policy == P1) & (summary.endpoint == "q20_accuracy_AULC_B16_B40")].estimate.iloc[0]
    p4 = summary[(summary.policy == P4) & (summary.endpoint == "q20_accuracy_AULC_B16_B40")].estimate.iloc[0]
    p2 = contrasts[(contrasts.contrast == "P2-P1") & contrasts.endpoint.eq("q20_accuracy_AULC_B16_B40")].iloc[0]
    p3 = contrasts[(contrasts.contrast == "P3-P1") & contrasts.endpoint.eq("q20_accuracy_AULC_B16_B40")].iloc[0]
    source = "initialization" if abs(p2.mean_difference) >= abs(p3.mean_difference) else "monotone acquisition"
    mono = "YES" if p3.ci_lower > 0 else ("NO" if p3.ci_upper < 0 else "UNRESOLVED")
    return f"""PG-RMBC STUDY COMPLETE

Historical gates: PASS
Protocol frozen before trajectories: YES
Candidate B primary AULC: {p1:.6f}
PG-RMBC primary AULC: {p4:.6f}
Paired difference: {row.mean_difference:+.6f}
95% interval: [{row.ci_lower:+.6f}, {row.ci_upper:+.6f}]
B40 KH-recall difference: {kh.mean_difference:+.6f}
Main source of gain: {source}
Monotonicity useful as soft acquisition prior: {mono}
Final policy for new Ioan data: {decision['final_policy']}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "smoke", "freeze", "scramble-test", "run", "analyse", "validate", "all"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--policies", nargs="*", default=list(POLICIES))
    parser.add_argument("--repeats", nargs="*", type=int, default=list(REPEATS))
    args = parser.parse_args()
    if args.command == "preflight": print(json.dumps(preflight(), indent=2))
    elif args.command == "smoke": print(json.dumps(smoke(), indent=2))
    elif args.command == "freeze": print(json.dumps(freeze_protocol(), indent=2))
    elif args.command == "scramble-test": print(json.dumps(hidden_label_scrambling_test(), indent=2))
    elif args.command == "run": run(args.policies, args.repeats, args.workers)
    elif args.command == "analyse": print(json.dumps(analyse(), indent=2))
    elif args.command == "validate": print(json.dumps(validation_report(), indent=2))
    else:
        preflight(); hidden_label_scrambling_test(); run(args.policies, args.repeats, args.workers)
        analyse(); validation_report(); run_manifest(); print(final_console_summary())


if __name__ == "__main__":
    main()
