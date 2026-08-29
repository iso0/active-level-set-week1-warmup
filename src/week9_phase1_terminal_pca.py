"""Week 9 Phase 1 terminal-performance and PCA analysis.

This module is deliberately separate from the frozen Week 8.5 analysis.  It
reads those artifacts but never writes into their directory.  Two input paths
are supported for the terminal analysis:

* per-test prediction rows saved by the post-hoc H=320 extension; and
* exact deterministic refits from the ordered ``queried_indices`` in a saved
  checkpoint JSON directory or ``.tar.gz`` bundle.

Random continuations remain nested within an outer repeat/fold.  They are
averaged within the fold before point aggregation, while bootstrap uncertainty
resamples repeat blocks and Random continuations at their proper levels.

PCA is visualization-only: StandardScaler and PCA are fitted to the four
physical feature columns, never to labels, B1, q20/q30, predictions, or query
history.  The classifier contour is explicitly a PC1-PC2 slice of the fitted
four-dimensional GPC with PC3 and PC4 held at zero.
"""

from __future__ import annotations

import argparse
import json
import math
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import ConvexHull, distance
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "week9_phase1_close_week8" / "dev_terminal_pca"
DEFAULT_CHECKPOINT_BUNDLE = (
    ROOT
    / "outputs"
    / "week8_5_frozen_confirmation"
    / "week8_5_checkpoint_bundle.tar.gz"
)
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = (40, 80, 160, 320)
SUBSETS = ("full81", "B1_q30", "B1_q20")
METRICS = (
    "accuracy",
    "balanced_accuracy",
    "keyhole_recall",
    "specificity",
    "false_negative",
    "false_positive",
)
ARMS = ("binary_margin", "binary_random")
PREDICTION_KEY = (
    "run_id",
    "arm",
    "continuation_id",
    "budget",
    "population_row_index",
)
TRAJECTORY_KEY = ("run_id", "arm", "continuation_id")
FIGURE_FILENAMES = {
    "population": "05_pca_full_population.png",
    "boundary": "06_pca_boundary_subsets_representative_fold.png",
    "trajectory": "07_pca_active_learning_trajectory.png",
    "slice": "08_pca_plane_gpc_slice.png",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else math.nan


def classification_metrics(truth: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    """Return the requested metrics with Keyhole as the positive class."""

    y = np.asarray(truth, dtype=int)
    p = np.asarray(probability, dtype=float)
    require(y.ndim == p.ndim == 1 and len(y) == len(p), "Truth/probability shape mismatch")
    require(len(y) > 0, "Cannot score an empty evaluation subset")
    require(set(np.unique(y)).issubset({0, 1}), "Manual labels must be binary")
    require(np.isfinite(p).all() and ((0.0 <= p) & (p <= 1.0)).all(), "Invalid probability")
    pred = (p >= 0.5).astype(int)
    tn = int(np.sum((y == 0) & (pred == 0)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    tp = int(np.sum((y == 1) & (pred == 1)))
    recall = _safe_divide(tp, tp + fn)
    specificity = _safe_divide(tn, tn + fp)
    balanced = float(np.nanmean([recall, specificity])) if not (math.isnan(recall) and math.isnan(specificity)) else math.nan
    return {
        "accuracy": float((tn + tp) / len(y)),
        "balanced_accuracy": balanced,
        "keyhole_recall": recall,
        "specificity": specificity,
        "false_negative": float(fn),
        "false_positive": float(fp),
        "true_negative": float(tn),
        "true_positive": float(tp),
        "row_count": float(len(y)),
    }


def _checkpoint_members(source: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    """Yield checkpoint payloads from a directory, JSON file, or tar bundle."""

    source = Path(source)
    require(source.exists(), f"Checkpoint source does not exist: {source}")
    if source.is_dir():
        for path in sorted(source.glob("*.json")):
            yield str(path), json.loads(path.read_text(encoding="utf-8"))
        return
    if source.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(source, "r:gz") as archive:
            members = sorted(
                (
                    member
                    for member in archive.getmembers()
                    if member.isfile()
                    and member.name.endswith(".json")
                    and "checkpoints/" in member.name.replace("\\", "/")
                ),
                key=lambda member: member.name,
            )
            for member in members:
                handle = archive.extractfile(member)
                require(handle is not None, f"Could not read {member.name} from {source}")
                yield f"{source}!{member.name}", json.loads(handle.read().decode("utf-8"))
        return
    require(source.suffix == ".json", f"Unsupported checkpoint source: {source}")
    yield str(source), json.loads(source.read_text(encoding="utf-8"))


def _payload_identity(payload: Mapping[str, Any]) -> tuple[str, str, int]:
    identity = payload.get("identity", {})
    return (
        str(identity.get("run_id", "")),
        str(identity.get("arm", "")),
        int(identity.get("continuation_id", -1)),
    )


def normalize_checkpoint_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Expose a common effective ``horizon`` for frozen and Week 9 payloads."""

    result = dict(payload)
    historical = result.get("horizon")
    extension = result.get("target_horizon")
    require(historical is not None or extension is not None, "Checkpoint has no horizon or target_horizon")
    if historical is not None and extension is not None:
        require(int(historical) == int(extension), "Checkpoint horizon/target_horizon conflict")
    effective = int(extension if extension is not None else historical)
    result["horizon"] = effective
    result["effective_horizon_source"] = "target_horizon" if extension is not None else "horizon"
    if extension is not None:
        source_horizon = int(result.get("source_horizon", -1))
        require(16 <= source_horizon < effective, "Invalid Week 9 source_horizon/target_horizon")
        require(isinstance(result.get("extension_rows", []), list), "Week 9 extension_rows must be a list")
        require(isinstance(result.get("terminal_prediction_rows", []), list), "Week 9 terminal_prediction_rows must be a list")
    return result


def validate_checkpoint_payload(payload: Mapping[str, Any], source: str = "checkpoint") -> None:
    identity = payload.get("identity", {})
    required_identity = {"run_id", "repeat", "fold", "arm", "continuation_id"}
    require(required_identity.issubset(identity), f"{source}: incomplete identity")
    require(identity["arm"] in ARMS, f"{source}: unsupported arm {identity['arm']}")
    queried = [int(value) for value in payload.get("queried_indices", [])]
    horizon = int(payload.get("horizon", -1))
    require(bool(payload.get("complete")), f"{source}: checkpoint is not complete")
    require(horizon >= 16 and len(queried) == horizon, f"{source}: ordered queried sequence must equal effective horizon")
    require(len(queried) == len(set(queried)), f"{source}: duplicate queried index")


def _verify_payload_prefix(shorter: Mapping[str, Any], longer: Mapping[str, Any], identity: tuple[str, str, int]) -> None:
    short_q = [int(value) for value in shorter["queried_indices"]]
    long_q = [int(value) for value in longer["queried_indices"]]
    require(
        long_q[: len(short_q)] == short_q,
        f"Trajectory prefix drift for {identity}: higher-horizon queries do not reproduce history",
    )


def load_checkpoint_payloads(
    sources: Sequence[Path | str],
    *,
    arms: Sequence[str] = ARMS,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Load and merge payloads, preferring the validated highest horizon."""

    allowed = set(arms)
    chosen: dict[tuple[str, str, int], dict[str, Any]] = {}
    for source_value in sources:
        for name, raw_payload in _checkpoint_members(Path(source_value)):
            payload = normalize_checkpoint_payload(raw_payload)
            identity = payload.get("identity", {})
            if identity.get("arm") not in allowed:
                continue
            validate_checkpoint_payload(payload, name)
            key = _payload_identity(payload)
            if key not in chosen:
                chosen[key] = payload
                continue
            previous = chosen[key]
            previous_h = int(previous["horizon"])
            new_h = int(payload["horizon"])
            if new_h >= previous_h:
                _verify_payload_prefix(previous, payload, key)
                chosen[key] = payload
            else:
                _verify_payload_prefix(payload, previous, key)
    require(chosen, "No Margin/Random checkpoint payloads were found")
    return chosen


def embedded_terminal_prediction_rows(
    payloads: Mapping[tuple[str, str, int], Mapping[str, Any]],
) -> pd.DataFrame:
    """Collect terminal predictions embedded by the Week 9 horizon extension."""

    rows: list[dict[str, Any]] = []
    for key in sorted(payloads):
        payload = payloads[key]
        for raw in payload.get("terminal_prediction_rows", []):
            row = dict(raw)
            expected_identity = {
                "run_id": key[0],
                "arm": key[1],
                "continuation_id": key[2],
                "repeat": int(payload["identity"]["repeat"]),
                "fold": int(payload["identity"]["fold"]),
                "budget": int(payload["horizon"]),
            }
            for field, expected in expected_identity.items():
                if field in row:
                    require(str(row[field]) == str(expected), f"Embedded terminal prediction {field} drift for {key}")
            row.setdefault("run_id", key[0])
            row.setdefault("arm", key[1])
            row.setdefault("continuation_id", key[2])
            row.setdefault("repeat", int(payload["identity"]["repeat"]))
            row.setdefault("fold", int(payload["identity"]["fold"]))
            row.setdefault("budget", int(payload["horizon"]))
            row["source_horizon"] = int(payload["horizon"])
            row["prediction_source"] = "embedded_week9_terminal_prediction"
            rows.append(row)
    return normalize_prediction_rows(pd.DataFrame(rows)) if rows else pd.DataFrame()


def _spec_lookup(specs: Sequence[w85.SplitSpec]) -> dict[str, w85.SplitSpec]:
    lookup = {spec.run_id: spec for spec in specs}
    require(len(lookup) == len(specs), "Duplicate split run_id")
    return lookup


def _validate_payload_against_split(
    payload: Mapping[str, Any], spec: w85.SplitSpec, population: pd.DataFrame
) -> None:
    identity = payload["identity"]
    require(int(identity["repeat"]) == spec.repeat, f"{spec.run_id}: repeat drift")
    require(int(identity["fold"]) == spec.fold, f"{spec.run_id}: fold drift")
    queried = [int(value) for value in payload["queried_indices"]]
    train = set(spec.train_indices)
    require(set(queried).issubset(train), f"{spec.run_id}: checkpoint query outside training pool")
    expected_initial = w85.initial_design(spec, population)
    require(queried[:16] == expected_initial, f"{spec.run_id}: frozen initial-design prefix drift")


def _prediction_rows_for_fit(
    payload: Mapping[str, Any],
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    distances: np.ndarray,
    budget: int,
) -> list[dict[str, Any]]:
    identity = payload["identity"]
    arm = str(identity["arm"])
    continuation = int(identity["continuation_id"])
    queried = np.asarray(payload["queried_indices"][:budget], dtype=int)
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x = population.loc[:, FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    scaler = StandardScaler().fit(x[train])
    seed = w85.seed_u32(w85.fit_seed_key(spec, arm, continuation, budget))
    fit = p6.fit_gpc(x[queried], labels[queried], scaler=scaler, seed=seed, restarts=0)
    probability = p6.predict_gpc(fit, x[test])
    flags = w85.boundary_flags(spec, population, distances)
    rows: list[dict[str, Any]] = []
    for position, row_index in enumerate(test):
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "arm": arm,
                "continuation_id": continuation,
                "budget": int(budget),
                "population_row_index": int(row_index),
                "experiment_name": str(population.iloc[row_index]["experiment_name"]),
                "manual_has_keyhole": int(labels[row_index]),
                "probability_keyhole": float(probability[position]),
                "predicted_has_keyhole": int(probability[position] >= 0.5),
                "is_full81": True,
                "is_B1_q30": bool(flags["B1_q30"][position]),
                "is_B1_q20": bool(flags["B1_q20"][position]),
                "fit_seed_u32": seed,
                "fit_status": fit.fit_status,
                "kernel": fit.kernel,
                "source_horizon": int(payload["horizon"]),
                "prediction_source": "deterministic_checkpoint_prefix_refit",
            }
        )
    return rows


def prediction_rows_from_checkpoints(
    payloads: Mapping[tuple[str, str, int], Mapping[str, Any]],
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
    *,
    budgets: Sequence[int] = BUDGETS,
    n_jobs: int = 1,
) -> pd.DataFrame:
    """Deterministically refit missing terminal models from query prefixes."""

    require(tuple(FEATURES) == tuple(w85.FEATURES), "Feature contract drift")
    lookup = _spec_lookup(specs)
    distances = w85.b1_distance(population)
    jobs: list[tuple[Mapping[str, Any], w85.SplitSpec, int]] = []
    for key in sorted(payloads):
        payload = payloads[key]
        spec = lookup.get(key[0])
        require(spec is not None, f"Unknown checkpoint run_id {key[0]}")
        _validate_payload_against_split(payload, spec, population)
        for budget in sorted(set(map(int, budgets))):
            if budget <= int(payload["horizon"]):
                jobs.append((payload, spec, budget))
    require(jobs, "No requested budget is available in the checkpoint payloads")
    nested = Parallel(n_jobs=n_jobs, backend="loky", verbose=5)(
        delayed(_prediction_rows_for_fit)(payload, spec, population, distances, budget)
        for payload, spec, budget in jobs
    )
    frame = pd.DataFrame([row for group in nested for row in group])
    validate_prediction_rows(frame, population, specs)
    return frame.sort_values(list(PREDICTION_KEY)).reset_index(drop=True)


def _read_prediction_file(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    require(path.is_file(), f"Prediction input does not exist: {path}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def normalize_prediction_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize the minimal H320 extension prediction schema."""

    result = frame.copy()
    aliases = {
        "truth": "manual_has_keyhole",
        "has_keyhole": "manual_has_keyhole",
        "truth_has_keyhole": "manual_has_keyhole",
        "probability": "probability_keyhole",
        "test_probability": "probability_keyhole",
        "probability_has_keyhole": "probability_keyhole",
        "row_index": "population_row_index",
    }
    for old, new in aliases.items():
        if new not in result and old in result:
            result = result.rename(columns={old: new})
    required = set(PREDICTION_KEY) | {"repeat", "fold", "manual_has_keyhole", "probability_keyhole"}
    require(required.issubset(result.columns), f"Prediction rows missing {sorted(required - set(result.columns))}")
    for column in ("repeat", "fold", "continuation_id", "budget", "population_row_index", "manual_has_keyhole"):
        result[column] = result[column].astype(int)
    result["probability_keyhole"] = result["probability_keyhole"].astype(float)
    if "predicted_has_keyhole" not in result:
        result["predicted_has_keyhole"] = (result["probability_keyhole"] >= 0.5).astype(int)
    if "prediction_source" not in result:
        result["prediction_source"] = "external_prediction_table"
    return result


def add_evaluation_flags(
    frame: pd.DataFrame, population: pd.DataFrame, specs: Sequence[w85.SplitSpec]
) -> pd.DataFrame:
    """Attach frozen fold-local full81/q30/q20 membership to prediction rows."""

    result = normalize_prediction_rows(frame)
    distances = w85.b1_distance(population)
    lookup = _spec_lookup(specs)
    flag_maps: dict[str, dict[int, tuple[bool, bool]]] = {}
    for run_id in result["run_id"].unique():
        spec = lookup.get(str(run_id))
        require(spec is not None, f"Unknown run_id in predictions: {run_id}")
        flags = w85.boundary_flags(spec, population, distances)
        flag_maps[str(run_id)] = {
            int(index): (bool(flags["B1_q30"][position]), bool(flags["B1_q20"][position]))
            for position, index in enumerate(spec.test_indices)
        }
    memberships = [flag_maps[str(run_id)].get(int(index)) for run_id, index in result[["run_id", "population_row_index"]].itertuples(index=False, name=None)]
    require(all(value is not None for value in memberships), "Prediction row is not in its declared test fold")
    result["is_full81"] = True
    result["is_B1_q30"] = [bool(value[0]) for value in memberships if value is not None]
    result["is_B1_q20"] = [bool(value[1]) for value in memberships if value is not None]
    return result


def validate_prediction_rows(
    frame: pd.DataFrame,
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
) -> None:
    required = set(PREDICTION_KEY) | {
        "repeat",
        "fold",
        "manual_has_keyhole",
        "probability_keyhole",
        "is_full81",
        "is_B1_q30",
        "is_B1_q20",
    }
    require(required.issubset(frame.columns), f"Prediction schema missing {sorted(required - set(frame.columns))}")
    require(not frame.duplicated(list(PREDICTION_KEY)).any(), "Duplicate per-test prediction key")
    require(frame["arm"].isin(ARMS).all(), "Unsupported terminal arm")
    require(np.isfinite(frame["probability_keyhole"]).all(), "Non-finite terminal probability")
    require(frame["probability_keyhole"].between(0.0, 1.0).all(), "Probability outside [0,1]")
    lookup = _spec_lookup(specs)
    truth = population["has_keyhole"].astype(int)
    for keys, group in frame.groupby(list(TRAJECTORY_KEY) + ["budget"], sort=False):
        run_id = str(keys[0])
        spec = lookup.get(run_id)
        require(spec is not None, f"Unknown prediction run_id {run_id}")
        expected = set(map(int, spec.test_indices))
        observed = set(group["population_row_index"].astype(int))
        require(observed == expected, f"{keys}: predictions do not cover exactly the 81-row test fold")
        require(len(group) == 81, f"{keys}: expected 81 per-test predictions")
        require(int(group["is_B1_q20"].sum()) == 17, f"{keys}: q20 must contain 17 rows")
        require(int(group["is_B1_q30"].sum()) == 25, f"{keys}: q30 must contain 25 rows")
        expected_truth = truth.loc[group["population_row_index"].astype(int)].to_numpy()
        require(np.array_equal(expected_truth, group["manual_has_keyhole"].astype(int).to_numpy()), f"{keys}: manual label drift")


def merge_prediction_rows(
    frames: Sequence[pd.DataFrame],
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
) -> pd.DataFrame:
    """Merge sources; duplicate predictions must agree numerically."""

    require(frames, "No prediction frames supplied")
    normalized = [add_evaluation_flags(frame, population, specs) for frame in frames]
    combined = pd.concat(normalized, ignore_index=True, sort=False)
    duplicate_mask = combined.duplicated(list(PREDICTION_KEY), keep=False)
    if duplicate_mask.any():
        for key, group in combined[duplicate_mask].groupby(list(PREDICTION_KEY), sort=False):
            require(group["manual_has_keyhole"].nunique() == 1, f"Truth conflict for prediction {key}")
            require(np.ptp(group["probability_keyhole"].to_numpy(float)) <= 1e-12, f"Probability conflict for prediction {key}")
    priority = combined.get("prediction_source", pd.Series("external_prediction_table", index=combined.index)).astype(str).eq("external_prediction_table")
    combined = combined.assign(_priority=priority.astype(int)).sort_values(list(PREDICTION_KEY) + ["_priority"])
    combined = combined.drop_duplicates(list(PREDICTION_KEY), keep="last").drop(columns="_priority")
    validate_prediction_rows(combined, population, specs)
    return combined.sort_values(list(PREDICTION_KEY)).reset_index(drop=True)


def terminal_metrics_from_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute path-level full81/q30/q20 metrics from validated predictions."""

    rows: list[dict[str, Any]] = []
    keys = ["run_id", "repeat", "fold", "arm", "continuation_id", "budget"]
    for identity, group in predictions.groupby(keys, sort=True):
        base = dict(zip(keys, identity))
        for subset in SUBSETS:
            selected = group[group[f"is_{subset}"].astype(bool)]
            metrics = classification_metrics(
                selected["manual_has_keyhole"].to_numpy(int),
                selected["probability_keyhole"].to_numpy(float),
            )
            rows.append({**base, "subset": subset, **metrics})
    result = pd.DataFrame(rows)
    require(not result.duplicated(keys + ["subset"]).any(), "Duplicate path-level terminal metric")
    return result.sort_values(keys + ["subset"]).reset_index(drop=True)


def fold_level_terminal_metrics(path_metrics: pd.DataFrame) -> pd.DataFrame:
    """Average Random continuations within each outer fold before aggregation."""

    values = list(METRICS) + ["true_negative", "true_positive", "row_count"]
    keys = ["repeat", "fold", "run_id", "arm", "budget", "subset"]
    result = path_metrics.groupby(keys, as_index=False)[values].mean()
    counts = path_metrics.groupby(keys).size()
    for key, count in counts.items():
        expected = 30 if key[3] == "binary_random" else 1
        require(int(count) == expected, f"{key}: expected {expected} continuations, found {count}")
    result["continuations_averaged_within_fold"] = result["arm"].map({"binary_margin": 1, "binary_random": 30})
    return result


def _terminal_arrays(path_metrics: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[tuple[int, str, str]], list[int]]:
    repeats = sorted(path_metrics["repeat"].astype(int).unique().tolist())
    folds = sorted(path_metrics["fold"].astype(int).unique().tolist())
    require(folds == list(range(1, len(folds) + 1)), "Fold IDs must be consecutive")
    targets = sorted(
        {(int(row.budget), str(row.subset), metric) for row in path_metrics.itertuples() for metric in METRICS}
    )
    margin = np.full((len(repeats), len(folds), len(targets)), np.nan)
    random = np.full((len(repeats), len(folds), 30, len(targets)), np.nan)
    rep_pos = {value: index for index, value in enumerate(repeats)}
    target_pos = {value: index for index, value in enumerate(targets)}
    for row in path_metrics.itertuples(index=False):
        r = rep_pos[int(row.repeat)]
        f = int(row.fold) - 1
        c = int(row.continuation_id) - 1
        for metric in METRICS:
            t = target_pos[(int(row.budget), str(row.subset), metric)]
            if row.arm == "binary_margin":
                margin[r, f, t] = float(getattr(row, metric))
            elif row.arm == "binary_random":
                require(0 <= c < 30, "Random continuation_id must be 1..30")
                random[r, f, c, t] = float(getattr(row, metric))
    require(np.isfinite(margin).all(), "Incomplete Margin terminal metric cube")
    require(np.isfinite(random).all(), "Incomplete Random terminal metric cube")
    return margin, random, targets, repeats


def hierarchical_terminal_summary(
    path_metrics: pd.DataFrame,
    *,
    draws: int = 2000,
    seed: int = 902_001,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Point estimates and hierarchy-preserving intervals for terminal metrics."""

    margin, random, targets, repeats = _terminal_arrays(path_metrics)
    random_fold_mean = random.mean(axis=2)
    point_margin = margin.mean(axis=(0, 1))
    point_random = random_fold_mean.mean(axis=(0, 1))
    draw_margin = np.empty((draws, len(targets)), dtype=float)
    draw_random = np.empty((draws, len(targets)), dtype=float)
    rng = np.random.default_rng(seed)
    for draw in range(draws):
        sampled_repeats = rng.integers(0, len(repeats), size=len(repeats))
        margin_values: list[np.ndarray] = []
        random_values: list[np.ndarray] = []
        for repeat_index in sampled_repeats:
            for fold_index in range(margin.shape[1]):
                continuation_pick = rng.integers(0, 30, size=30)
                margin_values.append(margin[repeat_index, fold_index])
                random_values.append(random[repeat_index, fold_index, continuation_pick].mean(axis=0))
        draw_margin[draw] = np.mean(margin_values, axis=0)
        draw_random[draw] = np.mean(random_values, axis=0)

    summary_rows: list[dict[str, Any]] = []
    draw_rows: list[dict[str, Any]] = []
    for index, (budget, subset, metric) in enumerate(targets):
        for arm, point, samples in (
            ("binary_margin", point_margin[index], draw_margin[:, index]),
            ("binary_random", point_random[index], draw_random[:, index]),
            ("margin_minus_random", point_margin[index] - point_random[index], draw_margin[:, index] - draw_random[:, index]),
        ):
            summary_rows.append(
                {
                    "budget": budget,
                    "subset": subset,
                    "metric": metric,
                    "estimand": arm,
                    "point_estimate": float(point),
                    "two_sided_95pct_lower": float(np.quantile(samples, 0.025)),
                    "two_sided_95pct_upper": float(np.quantile(samples, 0.975)),
                    "bootstrap_draws": int(draws),
                    "random_aggregation": "30 continuations averaged within each repeat/fold",
                    "bootstrap_hierarchy": "repeat blocks; five folds kept; Random continuations resampled within fold",
                }
            )
        for draw in range(draws):
            draw_rows.append(
                {
                    "draw": draw + 1,
                    "budget": budget,
                    "subset": subset,
                    "metric": metric,
                    "binary_margin": float(draw_margin[draw, index]),
                    "binary_random": float(draw_random[draw, index]),
                    "margin_minus_random": float(draw_margin[draw, index] - draw_random[draw, index]),
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(draw_rows)


@dataclass
class PCAResult:
    scaler: StandardScaler
    pca: PCA
    scores: pd.DataFrame
    loadings: pd.DataFrame
    explained_variance: pd.DataFrame


def fit_feature_only_pca(population: pd.DataFrame) -> PCAResult:
    """Fit standardized 4D PCA without consulting labels or evaluation fields."""

    require(set(FEATURES).issubset(population.columns), "Population lacks P/VX/LS/ST")
    x = population.loc[:, FEATURES].to_numpy(float)
    require(np.isfinite(x).all(), "PCA features contain non-finite values")
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    pca = PCA(n_components=4, svd_solver="full").fit(z)
    # Resolve arbitrary component signs deterministically for stable figures.
    for index in range(pca.components_.shape[0]):
        pivot = int(np.argmax(np.abs(pca.components_[index])))
        if pca.components_[index, pivot] < 0:
            pca.components_[index] *= -1.0
    transformed = pca.transform(z)
    pc_names = [f"PC{index}" for index in range(1, 5)]
    scores = pd.DataFrame(transformed, columns=pc_names, index=population.index)
    scores.insert(0, "population_row_index", population.index.astype(int))
    if "experiment_name" in population:
        scores.insert(1, "experiment_name", population["experiment_name"].astype(str).to_numpy())
    loadings = pd.DataFrame(pca.components_.T, index=FEATURES, columns=pc_names).rename_axis("feature").reset_index()
    explained = pd.DataFrame(
        {
            "component": pc_names,
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance_ratio": np.cumsum(pca.explained_variance_ratio_),
        }
    )
    require(np.allclose(z.mean(axis=0), 0.0, atol=1e-12), "PCA scaling did not center features")
    require(np.allclose(z.std(axis=0), 1.0, atol=1e-12), "PCA scaling did not unit-scale features")
    return PCAResult(scaler=scaler, pca=pca, scores=scores, loadings=loadings, explained_variance=explained)


def representative_fold_table(
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
) -> tuple[pd.DataFrame, w85.SplitSpec]:
    """Choose a fold by median static q20 difficulty, never by visual appeal.

    The score combines robustly scaled distance from the across-fold median of
    q20 mean B1 and q20 Keyhole fraction.  Both quantities are evaluation-only;
    they do not affect PCA fitting, model fitting, or acquisition.
    """

    distances = w85.b1_distance(population)
    labels = population["has_keyhole"].astype(int).to_numpy()
    rows: list[dict[str, Any]] = []
    for spec in specs:
        test = np.asarray(spec.test_indices, dtype=int)
        flags = w85.boundary_flags(spec, population, distances)
        q20 = flags["B1_q20"]
        q30 = flags["B1_q30"]
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "q20_mean_B1": float(np.mean(distances[test][q20])),
                "q20_keyhole_fraction": float(np.mean(labels[test][q20])),
                "q30_mean_B1": float(np.mean(distances[test][q30])),
                "q20_rows": int(q20.sum()),
                "q30_rows": int(q30.sum()),
            }
        )
    frame = pd.DataFrame(rows)
    components: list[np.ndarray] = []
    for column in ("q20_mean_B1", "q20_keyhole_fraction"):
        values = frame[column].to_numpy(float)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        scale = mad if mad > 0 else float(np.std(values))
        scale = scale if scale > 0 else 1.0
        components.append((values - median) / scale)
    frame["representative_score"] = np.sqrt(components[0] ** 2 + components[1] ** 2)
    frame["selection_rule"] = "minimum robust distance to median q20 mean-B1 and q20 Keyhole fraction; run_id tie-break"
    chosen_row = frame.sort_values(["representative_score", "run_id"], kind="mergesort").iloc[0]
    lookup = _spec_lookup(specs)
    return frame.sort_values("run_id").reset_index(drop=True), lookup[str(chosen_row["run_id"])]


def _pc_axis_label(result: PCAResult, component: int) -> str:
    ratio = result.pca.explained_variance_ratio_[component - 1]
    return f"PC{component} ({ratio:.1%} variance)"


def plot_full_population_pca(
    population: pd.DataFrame,
    result: PCAResult,
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    labels = population["has_keyhole"].astype(int).to_numpy()
    pc = result.scores
    figure, axes = plt.subplots(1, 2, figsize=(12.0, 5.2), gridspec_kw={"width_ratios": [1.45, 1.0]})
    colors = {0: "#2f6f9f", 1: "#c44e52"}
    names = {0: "Conduction", 1: "Keyhole"}
    for label in (0, 1):
        mask = labels == label
        axes[0].scatter(pc.loc[mask, "PC1"], pc.loc[mask, "PC2"], s=28, alpha=0.72, c=colors[label], label=f"{names[label]} (n={int(mask.sum())})", edgecolors="none")
    axes[0].axhline(0, color="#999999", lw=0.7, zorder=0)
    axes[0].axvline(0, color="#999999", lw=0.7, zorder=0)
    axes[0].set_xlabel(_pc_axis_label(result, 1))
    axes[0].set_ylabel(_pc_axis_label(result, 2))
    axes[0].set_title("All 405 simulations; color is manual has_keyhole")
    axes[0].legend(frameon=False)

    loadings = result.loadings.set_index("feature")
    for index, feature in enumerate(FEATURES):
        x = float(loadings.loc[feature, "PC1"])
        y = float(loadings.loc[feature, "PC2"])
        axes[1].arrow(0, 0, x, y, width=0.008, head_width=0.055, length_includes_head=True, color=plt.cm.tab10(index))
        axes[1].text(x * 1.10, y * 1.10, feature, fontsize=11, ha="center", va="center")
    axes[1].axhline(0, color="#999999", lw=0.7)
    axes[1].axvline(0, color="#999999", lw=0.7)
    axes[1].set_xlim(-1.05, 1.05)
    axes[1].set_ylim(-1.05, 1.05)
    axes[1].set_aspect("equal", adjustable="box")
    axes[1].set_xlabel("PC1 loading")
    axes[1].set_ylabel("PC2 loading")
    axes[1].set_title("Feature loadings (P, VX, LS, ST)")
    figure.suptitle("Standardized four-feature PCA (labels never entered the fit)", fontsize=14)
    figure.tight_layout()
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_boundary_subsets(
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
    representative: w85.SplitSpec,
    result: PCAResult,
    output: Path,
) -> Path:
    del specs  # representative carries the exact split; retained for a stable public signature.
    output.parent.mkdir(parents=True, exist_ok=True)
    distances = w85.b1_distance(population)
    flags = w85.boundary_flags(representative, population, distances)
    test = np.asarray(representative.test_indices, dtype=int)
    labels = population["has_keyhole"].astype(int).to_numpy()[test]
    xy = result.scores.set_index("population_row_index").loc[test]
    figure, axis = plt.subplots(figsize=(7.5, 6.2))
    for label, color, name in ((0, "#2f6f9f", "Conduction"), (1, "#c44e52", "Keyhole")):
        mask = labels == label
        axis.scatter(
            xy.loc[mask, "PC1"],
            xy.loc[mask, "PC2"],
            c=color,
            s=28,
            alpha=0.42,
            edgecolors="none",
            label=f"{name} held-out rows (n={int(mask.sum())})",
        )
    q30 = flags["B1_q30"]
    q20 = flags["B1_q20"]
    axis.scatter(xy.loc[q30, "PC1"], xy.loc[q30, "PC2"], facecolors="none", edgecolors="#f0a202", linewidths=1.5, s=88, label="Fold-B1-q30 (25 rows)")
    axis.scatter(xy.loc[q20, "PC1"], xy.loc[q20, "PC2"], facecolors="none", edgecolors="#6a3d9a", linewidths=2.0, s=145, label="Fold-B1-q20 (17 rows)")
    axis.set_xlabel(_pc_axis_label(result, 1))
    axis.set_ylabel(_pc_axis_label(result, 2))
    axis.set_title(f"Deterministic representative fold: {representative.run_id}\nRings are evaluation-only B1 subsets; colors are manual labels")
    axis.legend(frameon=False, loc="best")
    figure.tight_layout()
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return output


def _representative_margin_payload(
    payloads: Mapping[tuple[str, str, int], Mapping[str, Any]],
    representative: w85.SplitSpec,
) -> Mapping[str, Any]:
    key = (representative.run_id, "binary_margin", 1)
    require(key in payloads, f"No Margin checkpoint for representative fold {representative.run_id}")
    return payloads[key]


def plot_active_learning_trajectory(
    population: pd.DataFrame,
    representative: w85.SplitSpec,
    payload: Mapping[str, Any],
    result: PCAResult,
    output: Path,
    snapshots: Sequence[int] = (16, 40, 80, 160, 320),
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    queried = np.asarray(payload["queried_indices"], dtype=int)
    available = [int(value) for value in snapshots if int(value) <= len(queried)]
    require(available, "No requested trajectory snapshot is available")
    pool = np.asarray(representative.train_indices, dtype=int)
    pc = result.scores.set_index("population_row_index")
    columns = len(available) if len(available) <= 4 else 3
    rows = int(math.ceil(len(available) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(5.0 * columns, 4.4 * rows), squeeze=False, sharex=True, sharey=True)
    for axis, budget in zip(axes.ravel(), available):
        axis.scatter(pc.loc[pool, "PC1"], pc.loc[pool, "PC2"], c="#d8d8d8", s=16, alpha=0.65, edgecolors="none", label="324-row query pool")
        initial = queried[:16]
        later = queried[16:budget]
        axis.scatter(pc.loc[initial, "PC1"], pc.loc[initial, "PC2"], c="#111111", marker="s", s=40, label="Initial 16")
        if len(later):
            order = np.arange(17, budget + 1)
            scatter = axis.scatter(pc.loc[later, "PC1"], pc.loc[later, "PC2"], c=order, cmap="viridis", s=35, alpha=0.88, edgecolors="white", linewidths=0.25, label="Margin acquisitions")
            figure.colorbar(scatter, ax=axis, shrink=0.72, label="Query number")
        axis.set_title(f"Budget {budget}")
        axis.set_xlabel(_pc_axis_label(result, 1))
        axis.set_ylabel(_pc_axis_label(result, 2))
    for axis in axes.ravel()[len(available):]:
        axis.set_visible(False)
    axes.ravel()[0].legend(frameon=False, fontsize=9)
    figure.suptitle(f"Binary Margin query locations in PCA projection: {representative.run_id}\nPCA and labels did not enter acquisition", fontsize=14)
    figure.tight_layout()
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return output


def fit_representative_gpc(
    population: pd.DataFrame,
    representative: w85.SplitSpec,
    payload: Mapping[str, Any],
    budget: int,
) -> p6.FitResult:
    require(budget <= int(payload["horizon"]), "Requested slice budget exceeds checkpoint horizon")
    x = population.loc[:, FEATURES].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    train = np.asarray(representative.train_indices, dtype=int)
    queried = np.asarray(payload["queried_indices"][:budget], dtype=int)
    scaler = StandardScaler().fit(x[train])
    seed = w85.seed_u32(w85.fit_seed_key(representative, "binary_margin", 1, budget))
    return p6.fit_gpc(x[queried], labels[queried], scaler=scaler, seed=seed, restarts=0)


def pca_plane_probability_grid(
    population: pd.DataFrame,
    result: PCAResult,
    fit: p6.FitResult,
    *,
    grid_size: int = 150,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate a PC1-PC2 slice, holding PC3=PC4=0, inside projected hull."""

    scores = result.scores[["PC1", "PC2"]].to_numpy(float)
    padding = 0.04 * np.ptp(scores, axis=0)
    x_axis = np.linspace(scores[:, 0].min() - padding[0], scores[:, 0].max() + padding[0], grid_size)
    y_axis = np.linspace(scores[:, 1].min() - padding[1], scores[:, 1].max() + padding[1], grid_size)
    xx, yy = np.meshgrid(x_axis, y_axis)
    pc_grid = np.zeros((xx.size, 4), dtype=float)
    pc_grid[:, 0] = xx.ravel()
    pc_grid[:, 1] = yy.ravel()
    standardized = result.pca.inverse_transform(pc_grid)
    original_features = result.scaler.inverse_transform(standardized)
    probability = p6.predict_gpc(fit, original_features).reshape(xx.shape)
    hull = ConvexHull(scores)
    inside = MplPath(scores[hull.vertices]).contains_points(np.column_stack([xx.ravel(), yy.ravel()]), radius=1e-10).reshape(xx.shape)
    return xx, yy, np.where(inside, probability, np.nan), inside


def plot_pca_plane_slice(
    population: pd.DataFrame,
    result: PCAResult,
    fit: p6.FitResult,
    budget: int,
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    xx, yy, probability, inside = pca_plane_probability_grid(population, result, fit)
    labels = population["has_keyhole"].astype(int).to_numpy()
    pc = result.scores
    figure, axis = plt.subplots(figsize=(8.0, 6.4))
    levels = np.linspace(0.0, 1.0, 11)
    surface = axis.contourf(xx, yy, probability, levels=levels, cmap="RdBu_r", alpha=0.72, extend="neither")
    if np.nanmin(probability) <= 0.5 <= np.nanmax(probability):
        contour = axis.contour(xx, yy, probability, levels=[0.5], colors="#111111", linewidths=2.0)
        axis.clabel(contour, fmt={0.5: "P(Keyhole)=0.5"}, inline=True, fontsize=9)
    for label, color, name in ((0, "#2f6f9f", "Conduction"), (1, "#c44e52", "Keyhole")):
        mask = labels == label
        axis.scatter(pc.loc[mask, "PC1"], pc.loc[mask, "PC2"], c=color, s=22, alpha=0.64, edgecolors="white", linewidths=0.25, label=name)
    figure.colorbar(surface, ax=axis, label="GPC P(Keyhole) on PC3=PC4=0 slice")
    axis.set_xlabel(_pc_axis_label(result, 1))
    axis.set_ylabel(_pc_axis_label(result, 2))
    axis.set_title(f"PCA-plane slice of the 4D Binary Margin GPC at budget {budget}\nPC3=PC4=0; masked outside projected data hull; not the full physical boundary")
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    require(bool(inside.any()), "PCA slice hull mask is empty")
    return output


def _dominant_loading(loadings: pd.DataFrame, component: str) -> dict[str, Any]:
    indexed = loadings.set_index("feature")[component]
    feature = str(indexed.abs().idxmax())
    return {"feature": feature, "loading": float(indexed.loc[feature])}


def pca_interpretation_diagnostics(
    population: pd.DataFrame,
    result: PCAResult,
    representative: w85.SplitSpec,
    payload: Mapping[str, Any],
    *,
    neighbours: int = 10,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Quantify class mixing and query placement in the 2D projection.

    These are after-the-fact visualization diagnostics.  Manual labels and B1
    enter this interpretation only; they did not enter scaling, PCA, model
    fitting, or acquisition.
    """

    xy = result.scores[["PC1", "PC2"]].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    require(0 < neighbours < len(population), "Invalid PCA mixing-neighbour count")
    pairwise = distance.cdist(xy, xy)
    np.fill_diagonal(pairwise, np.inf)
    nearest = np.argsort(pairwise, axis=1, kind="stable")[:, :neighbours]
    mixing = np.mean(labels[nearest] != labels[:, None], axis=1)
    frame = result.scores[[column for column in result.scores if column in {"population_row_index", "experiment_name", "PC1", "PC2"}]].copy()
    frame["manual_has_keyhole"] = labels
    frame[f"opposite_label_fraction_{neighbours}nn_in_pc1_pc2"] = mixing
    frame["representative_test_role"] = "not_in_representative_test"
    distances = w85.b1_distance(population)
    flags = w85.boundary_flags(representative, population, distances)
    test = np.asarray(representative.test_indices, dtype=int)
    frame.loc[test, "representative_test_role"] = "held_out_non_q30"
    frame.loc[test[flags["B1_q30"]], "representative_test_role"] = "B1_q30_only"
    frame.loc[test[flags["B1_q20"]], "representative_test_role"] = "B1_q20"
    query_number = {int(index): number for number, index in enumerate(payload["queried_indices"], start=1)}
    frame["margin_query_number"] = frame["population_row_index"].map(query_number)

    def stage(value: float) -> str:
        if pd.isna(value):
            return "not_queried_by_available_horizon"
        number = int(value)
        if number <= 16:
            return "initial_1_16"
        for lower, upper in ((17, 40), (41, 80), (81, 160), (161, 320)):
            if lower <= number <= upper:
                return f"acquired_{lower}_{upper}"
        return "acquired_after_320"

    frame["margin_query_stage"] = frame["margin_query_number"].map(stage)
    centroids = {
        name: {
            "PC1": float(xy[labels == label, 0].mean()),
            "PC2": float(xy[labels == label, 1].mean()),
        }
        for label, name in ((0, "Conduction"), (1, "Keyhole"))
    }
    centroid_distance = float(
        np.linalg.norm(
            np.array(list(centroids["Conduction"].values()))
            - np.array(list(centroids["Keyhole"].values()))
        )
    )
    mixing_column = f"opposite_label_fraction_{neighbours}nn_in_pc1_pc2"
    mixing_by_role = {
        str(role): float(group[mixing_column].mean())
        for role, group in frame.groupby("representative_test_role", sort=True)
    }
    mixing_by_query_stage = {
        str(stage_name): float(group[mixing_column].mean())
        for stage_name, group in frame.groupby("margin_query_stage", sort=True)
    }
    summary = {
        "diagnostic_status": "after-the-fact 2D projection interpretation only",
        "neighbours_for_mixing": neighbours,
        "class_centroids_pc1_pc2": centroids,
        "class_centroid_distance_pc1_pc2": centroid_distance,
        "mean_opposite_label_fraction_by_representative_test_role": mixing_by_role,
        "mean_opposite_label_fraction_by_margin_query_stage": mixing_by_query_stage,
        "caveat": "2D neighbour mixing can hide separation or overlap along PC3/PC4 and is not a physical-boundary metric",
    }
    return frame, summary


def run_pca_suite(
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
    payloads: Mapping[tuple[str, str, int], Mapping[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """Create the complete, scientifically labelled PCA analysis suite."""

    output_dir = Path(output_dir)
    figure_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = fit_feature_only_pca(population)
    fold_table, representative = representative_fold_table(population, specs)
    payload = _representative_margin_payload(payloads, representative)
    _validate_payload_against_split(payload, representative, population)
    interpretation_frame, interpretation = pca_interpretation_diagnostics(
        population, result, representative, payload
    )
    slice_budget = max(value for value in BUDGETS if value <= int(payload["horizon"]))
    fit = fit_representative_gpc(population, representative, payload, slice_budget)
    figures = {
        "population": str(plot_full_population_pca(population, result, figure_dir / FIGURE_FILENAMES["population"])),
        "boundary": str(plot_boundary_subsets(population, specs, representative, result, figure_dir / FIGURE_FILENAMES["boundary"])),
        "trajectory": str(plot_active_learning_trajectory(population, representative, payload, result, figure_dir / FIGURE_FILENAMES["trajectory"])),
        "slice": str(plot_pca_plane_slice(population, result, fit, slice_budget, figure_dir / FIGURE_FILENAMES["slice"])),
    }
    result.scores.to_csv(output_dir / "pca_population_scores.csv", index=False, lineterminator="\n")
    result.loadings.to_csv(output_dir / "pca_feature_loadings.csv", index=False, lineterminator="\n")
    result.explained_variance.to_csv(output_dir / "pca_explained_variance.csv", index=False, lineterminator="\n")
    fold_table.to_csv(output_dir / "pca_representative_fold_selection.csv", index=False, lineterminator="\n")
    interpretation_frame.to_csv(output_dir / "pca_interpretation_diagnostics.csv", index=False, lineterminator="\n")
    summary = {
        "pca_fit_columns_only": list(FEATURES),
        "standardization": "StandardScaler fitted on all 405 rows of P/VX/LS/ST for visualization only",
        "labels_used_in_pca_fit": False,
        "pca_used_in_model_training_or_acquisition": False,
        "pc1_explained_variance": float(result.pca.explained_variance_ratio_[0]),
        "pc2_explained_variance": float(result.pca.explained_variance_ratio_[1]),
        "pc1_plus_pc2_explained_variance": float(result.pca.explained_variance_ratio_[:2].sum()),
        "pc1_dominant_loading": _dominant_loading(result.loadings, "PC1"),
        "pc2_dominant_loading": _dominant_loading(result.loadings, "PC2"),
        "representative_run_id": representative.run_id,
        "representative_selection_rule": "minimum robust distance to median q20 mean-B1 and q20 Keyhole fraction; run_id tie-break",
        "representative_selection_is_label_informed": True,
        "representative_selection_label_use_scope": "Manual labels enter only this deterministic evaluation/visualization choice; they do not enter PCA fitting or acquisition.",
        "representative_selection_used_visual_appearance": False,
        "slice_budget": slice_budget,
        "slice_definition": "PC1-PC2 grid; PC3=PC4=0; inverse transformed to four physical features; masked outside projected data hull",
        "slice_caveat": "Two-dimensional PCA-plane classifier slice masked only by the PC1-PC2 projected convex hull. Setting PC3=PC4=0 does not establish occupancy on the observed four-dimensional data manifold; this is not the true empirical or physical boundary.",
        "interpretation_diagnostics": interpretation,
        "figures": figures,
    }
    (output_dir / "pca_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _write_frame(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-source", action="append", default=[], help="Checkpoint directory, JSON, or .tar.gz; repeatable")
    parser.add_argument("--prediction-input", action="append", default=[], help="Per-test CSV[.gz] or Parquet prediction table; repeatable")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--budgets", nargs="+", type=int, default=list(BUDGETS))
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--pca-only", action="store_true", help="Generate PCA suite without the all-trajectory terminal refits")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    sources = [Path(value) for value in args.checkpoint_source] or [DEFAULT_CHECKPOINT_BUNDLE]
    population = w85.load_population()
    specs = w85.build_splits(population)
    require(len(population) == 405, "Frozen population row count drift")
    require(int(population["has_keyhole"].sum()) == 73, "Frozen manual-label count drift")
    payloads = load_checkpoint_payloads(sources)
    pca_summary = run_pca_suite(population, specs, payloads, args.output_dir)
    if args.pca_only:
        print(json.dumps({"mode": "pca_only", "pca": pca_summary}, indent=2))
        return

    prediction_frames = [_read_prediction_file(path) for path in args.prediction_input]
    embedded = embedded_terminal_prediction_rows(payloads)
    if not embedded.empty:
        prediction_frames.append(embedded)
    available_external = set()
    for frame in prediction_frames:
        normalized = normalize_prediction_rows(frame)
        available_external.update(
            tuple(value) for value in normalized[list(TRAJECTORY_KEY) + ["budget"]].drop_duplicates().itertuples(index=False, name=None)
        )
    missing_payloads: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    missing_budgets_by_payload: dict[tuple[str, str, int], list[int]] = {}
    for key, payload in payloads.items():
        needed = [budget for budget in args.budgets if budget <= int(payload["horizon"]) and (*key, int(budget)) not in available_external]
        if needed:
            missing_payloads[key] = payload
            missing_budgets_by_payload[key] = needed
    # Group by budget set so no trajectory is refitted when an external row exists.
    for budget_tuple in sorted({tuple(value) for value in missing_budgets_by_payload.values()}):
        subset = {key: missing_payloads[key] for key, value in missing_budgets_by_payload.items() if tuple(value) == budget_tuple}
        prediction_frames.append(
            prediction_rows_from_checkpoints(subset, population, specs, budgets=budget_tuple, n_jobs=args.n_jobs)
        )
    predictions = merge_prediction_rows(prediction_frames, population, specs)
    path_metrics = terminal_metrics_from_predictions(predictions)
    fold_metrics = fold_level_terminal_metrics(path_metrics)
    summary, draws = hierarchical_terminal_summary(path_metrics, draws=args.bootstrap_draws)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "terminal_predictions.csv.gz", index=False, compression="gzip", lineterminator="\n")
    _write_frame(args.output_dir / "terminal_path_metrics.csv", path_metrics)
    _write_frame(args.output_dir / "terminal_fold_metrics_random_averaged.csv", fold_metrics)
    _write_frame(args.output_dir / "terminal_metric_summary.csv", summary)
    draws.to_csv(
        args.output_dir / "terminal_hierarchical_bootstrap_draws.csv.gz",
        index=False,
        compression="gzip",
        lineterminator="\n",
    )
    print(json.dumps({"prediction_rows": len(predictions), "path_metric_rows": len(path_metrics), "summary_rows": len(summary), "pca": pca_summary}, indent=2))


if __name__ == "__main__":
    main()
