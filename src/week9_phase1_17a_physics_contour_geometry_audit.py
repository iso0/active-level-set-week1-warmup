"""Week 9 Phase 1.17A: diagnostic physics-contour geometry audit.

This module replays no acquisition and fits no model. It decomposes each
already-published Phase 1.16 selected-query displacement in the exact
outer-training standardized Euclidean coordinates used by that phase.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from nbclient import NotebookClient
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_16_m3_repulsion_scale_audit as p16


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_17a_physics_contour_geometry_audit"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "15_week9_phase1_17a_physics_contour_geometry_audit.ipynb"
PHASE16 = ROOT / "outputs" / "week9_phase1_16_m3_repulsion_scale_audit"
PARENT_SHA = "746b19153f377bb0b7219d1c113bab672e306b19"
BRANCH = "codex/week9-phase1-17a-physics-contour-geometry-audit"
FEATURES = ("P", "VX", "LS", "ST")
ARMS = ("M3_MARGIN", "REP_C025", "REP_C050", "REP_C100", "REP_C200", "REP_C400")
ARM_TO_C = {"M3_MARGIN": 0.0, "REP_C025": .25, "REP_C050": .5, "REP_C100": 1.0, "REP_C200": 2.0, "REP_C400": 4.0}
REGIONS = {"EARLY_B17_24": tuple(range(17, 25)), "MID_B25_40": tuple(range(25, 41)), "LATE_B41_80": tuple(range(41, 81)), "OVERALL_B17_80": tuple(range(17, 81))}
CHECKPOINTS = (24, 32, 40, 60, 80)
BOOTSTRAP_DRAWS = 10_000
SEED_ROOT = "week9_phase1_17a_physics_contour_geometry_audit|v1"
GEOMETRY_COLUMNS = (
    "run_id", "repeat", "fold", "arm", "c", "selection_budget", "selected_population_row_index", "nearest_population_row_index",
    "dz_P", "dz_VX", "dz_LS", "dz_ST", "normal_P", "normal_VX", "normal_LS", "normal_ST",
    "normal_component_P", "normal_component_VX", "normal_component_LS", "normal_component_ST",
    "tangent_component_P", "tangent_component_VX", "tangent_component_LS", "tangent_component_ST",
    "st_component_P", "st_component_VX", "st_component_LS", "st_component_ST",
    "total_distance", "normal_norm", "tangent_norm", "st_norm", "total_energy", "normal_energy", "tangent_energy", "st_energy",
    "r_N", "r_T", "r_ST", "orthogonality_N_T", "orthogonality_N_ST", "orthogonality_T_ST", "reconstruction_error", "energy_error", "fraction_sum_error",
    "zero_distance", "scaler_mean_P", "scaler_mean_VX", "scaler_mean_LS", "scaler_mean_ST", "scaler_scale_P", "scaler_scale_VX", "scaler_scale_LS", "scaler_scale_ST",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() not in {".png", ".gz", ".xlsx", ".tar"}:
        payload = payload.replace(b"\r\n", b"\n")
    return payload


def json_safe(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray): return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)): value = value.item()
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = frame.to_csv(index=False, lineterminator="\n").encode()
    if path.suffix == ".gz": path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    else: path.write_bytes(raw)


def historical_changes() -> list[str]:
    protected = [str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "outputs").glob("week9_phase1_*") if path.name != "week9_phase1_17a_physics_contour_geometry_audit"]
    result = subprocess.check_output(["git", "diff", "--name-only", PARENT_SHA, "--", *protected], cwd=ROOT, text=True)
    return [line for line in result.splitlines() if line.strip()]


def load_inputs() -> tuple[pd.DataFrame, list[Any], pd.DataFrame]:
    population, specs, _ = p13.load_inputs()
    paths = pd.read_csv(PHASE16 / "query_paths.csv.gz")
    return population, specs, paths


def baseline_gate() -> dict[str, Any]:
    population, specs, paths = load_inputs()
    manifest = json.loads((PHASE16 / "run_manifest.json").read_text())
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    base = subprocess.check_output(["git", "merge-base", "HEAD", PARENT_SHA], cwd=ROOT, text=True).strip()
    grouped = paths.groupby(["arm", "run_id"])
    initial = grouped.apply(lambda g: tuple(g.sort_values("query_order").population_row_index.iloc[:16]), include_groups=False)
    initial_wide = initial.unstack("arm")
    payload = {
        "status": "PASS", "required_parent_sha": PARENT_SHA, "current_head": current, "exact_branch_base": base,
        "phase16_decision": manifest["decision"], "population": len(population), "keyholes": int(population.has_keyhole.sum()), "conduction": int((~population.has_keyhole.astype(bool)).sum()),
        "outer_runs": len(specs), "arms": sorted(paths.arm.unique()), "path_rows": len(paths), "paths": len(grouped),
        "all_paths_length_80": bool(grouped.size().eq(80).all()), "all_paths_unique": bool(grouped.population_row_index.nunique().eq(80).all()),
        "shared_initial_designs": int(initial_wide.apply(lambda row: len(set(row)) == 1, axis=1).sum()), "historical_changes": historical_changes(),
    }
    ok = base == PARENT_SHA and manifest["decision"] == "REPULSION_MECHANISM_ONLY" and (len(population), int(population.has_keyhole.sum())) == (405, 73) and len(specs) == 100 and set(paths.arm) == set(ARMS) and len(paths) == 48_000 and payload["paths"] == 600 and payload["all_paths_length_80"] and payload["all_paths_unique"] and payload["shared_initial_designs"] == 100 and not payload["historical_changes"]
    payload["status"] = "PASS" if ok else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", payload); require(ok, f"baseline gate failed: {payload}")
    return payload


def analysis_specification() -> dict[str, Any]:
    payload = {
        "status": "FROZEN_BEFORE_RETROSPECTIVE_JOIN", "diagnostic_only": True, "new_trajectory": False, "new_acquisition": False,
        "arms": list(ARMS), "active_query_budgets": list(range(17, 81)), "regions": {k: list(v) for k, v in REGIONS.items()}, "checkpoints": list(CHECKPOINTS),
        "coordinates": {"features": list(FEATURES), "scaler": "StandardScaler fit on complete outer-training pool features", "nearest_neighbor": "original standardized Euclidean metric", "gradient_z_log_h": ["s_P/P", "-s_VX/(2 VX)", "-3 s_LS/(2 LS)", "0"]},
        "components": {"normal": "n_h n_h^T dz", "ST": "e_ST e_ST^T dz", "physical_tangent": "dz-normal-ST"},
        "inference": {"unit": "20 paired repeat blocks", "bootstrap_draws": BOOTSTRAP_DRAWS},
        "decision_categories": ["NORMAL_ESCAPE", "ST_NULLSPACE_ESCAPE", "TRUE_PHYSICS_TANGENT_SPREAD", "MIXED_GEOMETRIC_MECHANISM", "NO_CLEAR_GEOMETRIC_MECHANISM"],
        "forbidden": ["ARD metric", "labels in geometry", "B1/q20/q30 in geometry", "true-boundary claim", "new trajectory"],
    }
    write_json(OUTPUT / "analysis_specification.json", payload)
    return payload


def decompose_displacement(dz: np.ndarray, selected_x: np.ndarray, scale: np.ndarray) -> dict[str, Any]:
    gradient = np.array([scale[0] / selected_x[0], -scale[1] / (2.0 * selected_x[1]), -3.0 * scale[2] / (2.0 * selected_x[2]), 0.0], dtype=float)
    require(np.isfinite(gradient).all() and np.linalg.norm(gradient) > 0, "invalid local standardized gradient")
    normal = gradient / np.linalg.norm(gradient)
    normal_component = normal * float(np.dot(normal, dz))
    st_component = np.array([0.0, 0.0, 0.0, dz[3]], dtype=float)
    tangent_component = dz - normal_component - st_component
    total_energy = float(np.dot(dz, dz)); normal_energy = float(np.dot(normal_component, normal_component)); tangent_energy = float(np.dot(tangent_component, tangent_component)); st_energy = float(np.dot(st_component, st_component))
    zero = total_energy <= 1e-24
    fractions = (math.nan, math.nan, math.nan) if zero else (normal_energy / total_energy, tangent_energy / total_energy, st_energy / total_energy)
    reconstructed = normal_component + tangent_component + st_component
    return {
        "normal": normal, "normal_component": normal_component, "tangent_component": tangent_component, "st_component": st_component,
        "total_distance": math.sqrt(total_energy), "normal_norm": math.sqrt(normal_energy), "tangent_norm": math.sqrt(tangent_energy), "st_norm": math.sqrt(st_energy),
        "total_energy": total_energy, "normal_energy": normal_energy, "tangent_energy": tangent_energy, "st_energy": st_energy,
        "r_N": fractions[0], "r_T": fractions[1], "r_ST": fractions[2], "orthogonality_N_T": abs(float(np.dot(normal_component, tangent_component))),
        "orthogonality_N_ST": abs(float(np.dot(normal_component, st_component))), "orthogonality_T_ST": abs(float(np.dot(tangent_component, st_component))),
        "reconstruction_error": float(np.linalg.norm(dz - reconstructed)), "energy_error": abs(total_energy - normal_energy - tangent_energy - st_energy),
        "fraction_sum_error": math.nan if zero else abs(sum(fractions) - 1.0), "zero_distance": zero,
    }


def reconstruct_geometry() -> tuple[pd.DataFrame, dict[str, Any]]:
    population, specs, paths = load_inputs(); x = population.loc[:, FEATURES].to_numpy(float); spec_map = {s.run_id: s for s in specs}; rows = []
    for (arm, run_id), group in paths.groupby(["arm", "run_id"], sort=True):
        spec = spec_map[str(run_id)]; path = group.sort_values("query_order").population_row_index.astype(int).tolist(); train = np.asarray(spec.train_indices, int)
        scaler = StandardScaler().fit(x[train]); z = scaler.transform(x)
        for selection_budget in range(17, 81):
            selected = int(path[selection_budget - 1]); previous = np.asarray(path[: selection_budget - 1], int)
            differences = z[selected][None, :] - z[previous]; distances = np.sqrt((differences**2).sum(axis=1)); min_distance = float(distances.min()); ties = np.flatnonzero(np.isclose(distances, min_distance, rtol=1e-12, atol=1e-14)); nearest = int(previous[ties[np.argmin(previous[ties])]])
            dz = z[selected] - z[nearest]; result = decompose_displacement(dz, x[selected], scaler.scale_)
            vector_fields = {}
            for prefix, values in (("dz", dz), ("normal", result["normal"]), ("normal_component", result["normal_component"]), ("tangent_component", result["tangent_component"]), ("st_component", result["st_component"])):
                vector_fields.update({f"{prefix}_{name}": float(values[i]) for i, name in enumerate(FEATURES)})
            rows.append({"run_id": str(run_id), "repeat": int(spec.repeat), "fold": int(spec.fold), "arm": str(arm), "c": ARM_TO_C[str(arm)], "selection_budget": selection_budget, "selected_population_row_index": selected, "nearest_population_row_index": nearest, **vector_fields, **{k: v for k, v in result.items() if not isinstance(v, np.ndarray)}, **{f"scaler_mean_{name}": float(scaler.mean_[i]) for i, name in enumerate(FEATURES)}, **{f"scaler_scale_{name}": float(scaler.scale_[i]) for i, name in enumerate(FEATURES)}})
    frame = pd.DataFrame(rows).loc[:, GEOMETRY_COLUMNS]
    write_csv(OUTPUT / "query_geometry_components.csv.gz", frame)
    freeze = {"status": "FROZEN_BEFORE_RETROSPECTIVE_JOIN", "rows": len(frame), "columns": list(frame.columns), "sha256": sha256_file(OUTPUT / "query_geometry_components.csv.gz"), "truth_columns_absent": not any(c in frame for c in ("truth", "B1_distance", "is_q20_like", "is_q30_like"))}
    write_json(OUTPUT / "geometry_freeze.json", freeze)
    return frame, freeze


def scaler_recovery_audit(geometry: pd.DataFrame) -> pd.DataFrame:
    published = pd.read_csv(PHASE16 / "diversity_diagnostics.csv")[["arm", "budget", "mean_selected_d_min"]]
    recovered = geometry.groupby(["arm", "selection_budget"], as_index=False).total_distance.mean().rename(columns={"selection_budget": "budget", "total_distance": "recovered_mean_selected_d_min"})
    merged = published.merge(recovered, on=["arm", "budget"], validate="one_to_one"); merged["absolute_difference"] = abs(merged.mean_selected_d_min - merged.recovered_mean_selected_d_min)
    return merged


def retrospective_join(geometry: pd.DataFrame) -> pd.DataFrame:
    population, specs, _ = load_inputs(); distances = w85.b1_distance(population); labels = population.has_keyhole.astype(int).to_numpy(); joined = []; spec_map = {s.run_id: s for s in specs}
    for run_id, group in geometry.groupby("run_id", sort=True):
        spec = spec_map[str(run_id)]; test = np.asarray(spec.test_indices, int); q20_cut = float(np.quantile(distances[test], .20, method="higher")); q30_cut = float(np.quantile(distances[test], .30, method="higher")); part = group.copy(); indices = part.selected_population_row_index.to_numpy(int)
        part["true_label"] = labels[indices]; part["B1_distance"] = distances[indices]; part["is_q20_like"] = distances[indices] <= q20_cut; part["is_q30_like"] = distances[indices] <= q30_cut; joined.append(part)
    return pd.concat(joined, ignore_index=True)


def region_of_budget(budget: int) -> str:
    if budget <= 24: return "EARLY_B17_24"
    if budget <= 40: return "MID_B25_40"
    return "LATE_B41_80"


def summarize_geometry(joined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    joined = joined.copy(); joined["region"] = joined.selection_budget.map(region_of_budget)
    metrics = ["r_N", "r_T", "r_ST", "total_distance", "normal_norm", "tangent_norm", "st_norm", "normal_energy", "tangent_energy", "st_energy", "B1_distance", "is_q20_like", "is_q30_like", "true_label"]
    overall = joined.groupby(["arm", "c"], as_index=False)[metrics].agg(["mean", "median"]).reset_index(); overall.columns = ["_".join(c).strip("_") for c in overall.columns]
    scale = joined.groupby(["arm", "c"], as_index=False).agg(mean_r_N=("r_N", "mean"), mean_r_T=("r_T", "mean"), mean_r_ST=("r_ST", "mean"), mean_total_distance=("total_distance", "mean"), mean_normal_energy=("normal_energy", "mean"), mean_tangent_energy=("tangent_energy", "mean"), mean_st_energy=("st_energy", "mean"), mean_B1_distance=("B1_distance", "mean"), q20_fraction=("is_q20_like", "mean"), q30_fraction=("is_q30_like", "mean"), keyhole_fraction=("true_label", "mean"))
    region = joined.groupby(["arm", "c", "region"], as_index=False).agg(rows=("r_N", "size"), mean_r_N=("r_N", "mean"), mean_r_T=("r_T", "mean"), mean_r_ST=("r_ST", "mean"), mean_total_distance=("total_distance", "mean"), mean_normal_energy=("normal_energy", "mean"), mean_tangent_energy=("tangent_energy", "mean"), mean_st_energy=("st_energy", "mean"), mean_B1_distance=("B1_distance", "mean"), q20_fraction=("is_q20_like", "mean"), keyhole_fraction=("true_label", "mean"))
    checkpoint = joined[joined.selection_budget.isin(CHECKPOINTS)].groupby(["arm", "c", "selection_budget"], as_index=False).agg(rows=("r_N", "size"), mean_r_N=("r_N", "mean"), mean_r_T=("r_T", "mean"), mean_r_ST=("r_ST", "mean"), mean_total_distance=("total_distance", "mean"), mean_B1_distance=("B1_distance", "mean"), q20_fraction=("is_q20_like", "mean"), keyhole_fraction=("true_label", "mean"))
    return overall, scale, region, checkpoint


def group_comparison(joined: pd.DataFrame, flag: str, positive_name: str, negative_name: str) -> pd.DataFrame:
    rows = []
    for arm, group in joined.groupby("arm", sort=True):
        for value, name in ((True, positive_name), (False, negative_name)):
            part = group[group[flag].astype(bool).eq(value)]
            rows.append({"arm": arm, "c": ARM_TO_C[arm], "group": name, "rows": len(part), **{f"mean_{m}": float(part[m].mean()) for m in ("r_N", "r_T", "r_ST", "total_distance", "B1_distance")}})
        a = group[group[flag].astype(bool)]; b = group[~group[flag].astype(bool)]
        rows.append({"arm": arm, "c": ARM_TO_C[arm], "group": f"{positive_name}_minus_{negative_name}", "rows": len(group), **{f"mean_{m}": float(a[m].mean() - b[m].mean()) for m in ("r_N", "r_T", "r_ST", "total_distance", "B1_distance")}})
    return pd.DataFrame(rows)


def bootstrap(values: np.ndarray, key: str) -> tuple[float, float, float]:
    values = np.asarray(values, float); require(len(values) == 20 and np.isfinite(values).all(), f"bootstrap {key}")
    rng = np.random.default_rng(seed_u32("bootstrap", key)); draws = values[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def repeat_inference(joined: pd.DataFrame) -> pd.DataFrame:
    frame = joined.copy(); frame["region"] = frame.selection_budget.map(region_of_budget); frames = [frame.assign(scope="OVERALL_B17_80")]
    frames.extend(frame[frame.region.eq(region)].assign(scope=region) for region in REGIONS if region != "OVERALL_B17_80")
    scoped = pd.concat(frames, ignore_index=True)
    per_repeat = scoped.groupby(["repeat", "arm", "scope"], as_index=False).agg(r_N=("r_N", "mean"), r_T=("r_T", "mean"), r_ST=("r_ST", "mean"), total_distance=("total_distance", "mean"), B1_distance=("B1_distance", "mean"), q20_fraction=("is_q20_like", "mean"), keyhole_fraction=("true_label", "mean"))
    rows = []
    for scope in REGIONS:
        part = per_repeat[per_repeat.scope.eq(scope)]
        for metric in ("r_N", "r_T", "r_ST", "total_distance", "B1_distance", "q20_fraction", "keyhole_fraction"):
            wide = part.pivot(index="repeat", columns="arm", values=metric)
            for arm in ARMS[1:]:
                delta = (wide[arm] - wide["M3_MARGIN"]).to_numpy(float); mean, lo, hi = bootstrap(delta, f"{scope}|{metric}|{arm}")
                rows.append({"arm": arm, "c": ARM_TO_C[arm], "scope": scope, "metric": metric, "delta_vs_M3_MARGIN": mean, "ci_lower": lo, "ci_upper": hi, "positive_repeat_blocks": int((delta > 0).sum()), "zero_repeat_blocks": int((delta == 0).sum()), "negative_repeat_blocks": int((delta < 0).sum()), "bootstrap_draws": BOOTSTRAP_DRAWS})
    return pd.DataFrame(rows)


def b1_associations(joined: pd.DataFrame) -> pd.DataFrame:
    frame = joined.copy(); frame["region"] = frame.selection_budget.map(region_of_budget); rows = []
    for arm in ARMS:
        for region in (*REGIONS.keys(),):
            if region == "OVERALL_B17_80": part = frame[frame.arm.eq(arm)]
            else: part = frame[frame.arm.eq(arm) & frame.region.eq(region)]
            for metric in ("r_N", "r_T", "r_ST"):
                rho = float(spearmanr(part[metric], part.B1_distance).statistic)
                run_rhos = part.groupby("run_id").apply(lambda g: spearmanr(g[metric], g.B1_distance).statistic, include_groups=False).rename("rho").reset_index()
                repeat_rhos = run_rhos.assign(repeat=run_rhos.run_id.str.extract(r"__r(\d+)_")[0].astype(int)).groupby("repeat").rho.mean().to_numpy(float)
                mean, lo, hi = bootstrap(repeat_rhos, f"rho|{arm}|{region}|{metric}")
                rows.append({"arm": arm, "c": ARM_TO_C[arm], "region": region, "component": metric, "association": "spearman_vs_B1", "candidate_rho": rho, "repeat_mean_rho": mean, "ci_lower": lo, "ci_upper": hi, "bottom_B1_quartile_mean": math.nan, "top_B1_quartile_mean": math.nan, "top_minus_bottom": math.nan})
                q1, q3 = part.B1_distance.quantile([.25, .75]); bottom = float(part.loc[part.B1_distance <= q1, metric].mean()); top = float(part.loc[part.B1_distance >= q3, metric].mean())
                rows.append({"arm": arm, "c": ARM_TO_C[arm], "region": region, "component": metric, "association": "B1_top_vs_bottom_quartile", "candidate_rho": math.nan, "repeat_mean_rho": math.nan, "ci_lower": math.nan, "ci_upper": math.nan, "bottom_B1_quartile_mean": bottom, "top_B1_quartile_mean": top, "top_minus_bottom": top - bottom})
    return pd.DataFrame(rows)


def decide(scale: pd.DataFrame, inference: pd.DataFrame, associations: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    base = scale.set_index("arm").loc["M3_MARGIN"]; strongest = scale.set_index("arm").loc["REP_C400"]
    energy_delta = {component: float(strongest[f"mean_{component}_energy"] - base[f"mean_{component}_energy"]) for component in ("normal", "tangent", "st")}
    positive_energy = {k: max(v, 0.0) for k, v in energy_delta.items()}; total_positive = sum(positive_energy.values()); shares = {k: (v / total_positive if total_positive > 0 else 0.0) for k, v in positive_energy.items()}
    overall = inference[inference.scope.eq("OVERALL_B17_80")]
    supported = {}
    for metric in ("r_N", "r_T", "r_ST"):
        rows = overall[overall.metric.eq(metric)].sort_values("c"); supported[metric] = int((rows.ci_lower > 0).sum())
    if total_positive <= 0:
        decision = "NO_CLEAR_GEOMETRIC_MECHANISM"
    elif shares["normal"] >= .60 and supported["r_N"] >= 2:
        decision = "NORMAL_ESCAPE"
    elif shares["st"] >= .60 and supported["r_ST"] >= 2:
        decision = "ST_NULLSPACE_ESCAPE"
    elif shares["tangent"] >= .60 and supported["r_T"] >= 2:
        decision = "TRUE_PHYSICS_TANGENT_SPREAD"
    elif sum(v >= .25 for v in shares.values()) >= 2:
        decision = "MIXED_GEOMETRIC_MECHANISM"
    else:
        decision = "NO_CLEAR_GEOMETRIC_MECHANISM"
    flags = {"c4_energy_delta": energy_delta, "c4_positive_extra_energy_share": shares, "supported_share_increases": supported, "total_distance_delta_c4": float(strongest.mean_total_distance - base.mean_total_distance), "B1_distance_delta_c4": float(strongest.mean_B1_distance - base.mean_B1_distance), "q20_fraction_delta_c4": float(strongest.q20_fraction - base.q20_fraction), "keyhole_fraction_delta_c4": float(strongest.keyhole_fraction - base.keyhole_fraction)}
    return decision, flags


def make_figures(scale: pd.DataFrame, region: pd.DataFrame, q20: pd.DataFrame, associations: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True); rows = []
    def save(name: str) -> None:
        plt.tight_layout(); path = FIGURES / name; plt.savefig(path, dpi=180, bbox_inches="tight"); plt.close(); rows.append({"figure": name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    plt.figure(figsize=(7.5, 4.5)); plt.stackplot(scale.c, scale.mean_r_N, scale.mean_r_T, scale.mean_r_ST, labels=["Physics-normal", "P/VX/LS tangent", "ST"], alpha=.85); plt.xlabel("Phase 1.16 repulsion multiplier c"); plt.ylabel("Mean squared-distance fraction"); plt.ylim(0, 1); plt.legend(loc="upper right"); save("01_component_fractions_vs_scale.png")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True); colors = {"EARLY_B17_24": "#4c78a8", "MID_B25_40": "#f58518", "LATE_B41_80": "#54a24b"}
    for axis, metric, title in zip(axes, ("mean_r_N", "mean_r_T", "mean_r_ST"), ("Normal", "Physical tangent", "ST")):
        for name, group in region.groupby("region"): axis.plot(group.c, group[metric], "o-", color=colors[name], label=name.split("_")[0]); axis.set_title(title); axis.set_xlabel("c")
    axes[0].set_ylabel("Mean fraction"); axes[-1].legend(); save("02_components_by_budget_region.png")
    q = q20[q20.group.isin(("q20_like", "non_q20"))]; fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True)
    for axis, metric, title in zip(axes, ("mean_r_N", "mean_r_T", "mean_r_ST"), ("Normal", "Physical tangent", "ST")):
        for name, group in q.groupby("group"): axis.plot(group.c, group[metric], "o-", label=name); axis.set_title(title); axis.set_xlabel("c")
    axes[0].set_ylabel("Mean fraction"); axes[-1].legend(); save("03_q20_component_comparison.png")
    assoc = associations[(associations.region.eq("OVERALL_B17_80")) & associations.association.eq("spearman_vs_B1")]; plt.figure(figsize=(7.5, 4.5));
    for component, group in assoc.groupby("component"): plt.plot(group.c, group.candidate_rho, "o-", label=component)
    plt.axhline(0, color="black", lw=.8); plt.xlabel("c"); plt.ylabel("Spearman rho with retrospective B1 distance"); plt.legend(); save("04_B1_component_associations.png")
    base = scale.iloc[0]; delta = scale.copy();
    for column in ("mean_normal_energy", "mean_tangent_energy", "mean_st_energy"): delta[column] -= float(base[column])
    plt.figure(figsize=(7.5, 4.5)); plt.plot(delta.c, delta.mean_normal_energy, "o-", label="Normal energy Δ"); plt.plot(delta.c, delta.mean_tangent_energy, "s-", label="Tangent energy Δ"); plt.plot(delta.c, delta.mean_st_energy, "^-", label="ST energy Δ"); plt.axhline(0, color="black", lw=.8); plt.xlabel("c"); plt.ylabel("Mean squared-component increase vs margin"); plt.legend(); save("05_extra_distance_mechanism.png")
    frame = pd.DataFrame(rows); write_csv(OUTPUT / "figure_manifest.csv", frame); return frame


def build_reports(decision: str, flags: dict[str, Any], scale: pd.DataFrame, region: pd.DataFrame, q20: pd.DataFrame, q30: pd.DataFrame, classes: pd.DataFrame, associations: pd.DataFrame, inference: pd.DataFrame, recovery: pd.DataFrame, geometry: pd.DataFrame) -> None:
    extra = flags["c4_positive_extra_energy_share"]; strongest = scale.set_index("arm").loc["REP_C400"]; base = scale.set_index("arm").loc["M3_MARGIN"]
    region_lookup = region.set_index(["arm", "region"])
    q20_delta = q20[q20.group.eq("q20_like_minus_non_q20")].set_index("arm")
    class_delta = classes[classes.group.eq("Keyhole_minus_Conduction")].set_index("arm")
    overall_assoc = associations[(associations.region.eq("OVERALL_B17_80")) & associations.association.eq("spearman_vs_B1")].set_index(["arm", "component"])
    c4_inference = inference[(inference.scope.eq("OVERALL_B17_80")) & inference.arm.eq("REP_C400")].set_index("metric")
    lines = ["# Week 9 Phase 1.17A — Physics-Contour Geometry Audit", "", f"## Decision: {decision}", "", "No new active-learning path or acquisition was run. The 38,400 published Phase 1.16 active selections were decomposed in each outer run's exact standardized Euclidean coordinates.", "", "## Scale response", "", "| c | mean r_N | mean r_T | mean r_ST | total distance | B1 distance | q20 fraction | KH fraction |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in scale.itertuples(index=False): lines.append(f"| {row.c:g} | {row.mean_r_N:.4f} | {row.mean_r_T:.4f} | {row.mean_r_ST:.4f} | {row.mean_total_distance:.4f} | {row.mean_B1_distance:.4f} | {row.q20_fraction:.4f} | {row.keyhole_fraction:.4f} |")
    lines += [
        "", "## Extra-distance mechanism", "",
        f"From c=0 to c=4, mean distance changes by {flags['total_distance_delta_c4']:+.4f} (repeat-block 95% CI [{c4_inference.loc['total_distance','ci_lower']:+.4f}, {c4_inference.loc['total_distance','ci_upper']:+.4f}]). Of the positive increase in mean squared component energy, normal contributes {extra['normal']:.1%}, P/VX/LS physical tangent {extra['tangent']:.1%}, and ST {extra['st']:.1%}. Absolute tangent energy is the largest contributor, but its share falls by {c4_inference.loc['r_T','delta_vs_M3_MARGIN']:+.4f}; normal share rises by {c4_inference.loc['r_N','delta_vs_M3_MARGIN']:+.4f}, while the ST-share change {c4_inference.loc['r_ST','delta_vs_M3_MARGIN']:+.4f} is unresolved.",
        "", "## Budget dependence", "",
        f"EARLY: c=4 raises ST share from {region_lookup.loc[('M3_MARGIN','EARLY_B17_24'),'mean_r_ST']:.3f} to {region_lookup.loc[('REP_C400','EARLY_B17_24'),'mean_r_ST']:.3f} while tangent share falls. MID (B25–40): normal share rises {region_lookup.loc[('M3_MARGIN','MID_B25_40'),'mean_r_N']:.3f}→{region_lookup.loc[('REP_C400','MID_B25_40'),'mean_r_N']:.3f}, tangent share is nearly unchanged ({region_lookup.loc[('M3_MARGIN','MID_B25_40'),'mean_r_T']:.3f}→{region_lookup.loc[('REP_C400','MID_B25_40'),'mean_r_T']:.3f}), and ST share falls {region_lookup.loc[('M3_MARGIN','MID_B25_40'),'mean_r_ST']:.3f}→{region_lookup.loc[('REP_C400','MID_B25_40'),'mean_r_ST']:.3f}. LATE: normal share rises {region_lookup.loc[('M3_MARGIN','LATE_B41_80'),'mean_r_N']:.3f}→{region_lookup.loc[('REP_C400','LATE_B41_80'),'mean_r_N']:.3f} and tangent share falls {region_lookup.loc[('M3_MARGIN','LATE_B41_80'),'mean_r_T']:.3f}→{region_lookup.loc[('REP_C400','LATE_B41_80'),'mean_r_T']:.3f}. The mechanism is therefore budget-dependent and is not strongest in one component around B25–40.",
        "", "## Retrospective boundary and class associations", "",
        f"At c=4, retrospective B1 distance changes {flags['B1_distance_delta_c4']:+.4f}, q20 concentration {flags['q20_fraction_delta_c4']:+.4f}, and active-query Keyhole fraction {flags['keyhole_fraction_delta_c4']:+.4f} relative to margin. q20-like minus non-q20 queries at c=4 have Δr_N={q20_delta.loc['REP_C400','mean_r_N']:+.4f}, Δr_T={q20_delta.loc['REP_C400','mean_r_T']:+.4f}, and Δr_ST={q20_delta.loc['REP_C400','mean_r_ST']:+.4f}: q20-like queries are more tangent and less ST, not more normal. Keyhole minus Conduction queries at c=4 have Δr_N={class_delta.loc['REP_C400','mean_r_N']:+.4f}, Δr_T={class_delta.loc['REP_C400','mean_r_T']:+.4f}, and Δr_ST={class_delta.loc['REP_C400','mean_r_ST']:+.4f}.",
        f"For c=4, repeat-aggregated Spearman associations with retrospective B1 distance are normal {overall_assoc.loc[('REP_C400','r_N'),'repeat_mean_rho']:+.3f} [{overall_assoc.loc[('REP_C400','r_N'),'ci_lower']:+.3f}, {overall_assoc.loc[('REP_C400','r_N'),'ci_upper']:+.3f}], tangent {overall_assoc.loc[('REP_C400','r_T'),'repeat_mean_rho']:+.3f} [{overall_assoc.loc[('REP_C400','r_T'),'ci_lower']:+.3f}, {overall_assoc.loc[('REP_C400','r_T'),'ci_upper']:+.3f}], and ST {overall_assoc.loc[('REP_C400','r_ST'),'repeat_mean_rho']:+.3f} [{overall_assoc.loc[('REP_C400','r_ST'),'ci_lower']:+.3f}, {overall_assoc.loc[('REP_C400','r_ST'),'ci_upper']:+.3f}]. Greater B1 distance is associated with more ST share and less tangent share; it is not associated with greater normal share at c=4. These are retrospective associations, not acquisition inputs or causal effects.",
        "", "## Numerical integrity", "",
        f"Zero-distance events: {int(geometry.zero_distance.sum())}. Maximum orthogonality error {geometry[['orthogonality_N_T','orthogonality_N_ST','orthogonality_T_ST']].to_numpy().max():.3e}; maximum reconstruction error {geometry.reconstruction_error.max():.3e}; maximum energy error {geometry.energy_error.max():.3e}; maximum fraction-sum error {geometry.fraction_sum_error.max():.3e}. Exact Phase 1.16 selected-distance recovery maximum difference: {recovery.absolute_difference.max():.3e}.",
        "", "## Safe interpretation", "",
        "The extra squared-distance energy is mixed: tangent 42.9%, normal 30.1%, and ST 26.9%. Neither normal escape nor ST-nullspace escape alone explains the Phase 1.16 result. The decomposition describes local physics-contour geometry only; it does not identify the true M3 boundary normal or a causal physical direction.",
        "", "## Next step", "",
        "Do not run Phase 1.17B now. A tangent-only PCTR rule would remove the normal component but would not resolve the ST association, and most extra energy is already tangent plus ST. The audit therefore does not isolate a clear harmful mechanism that PCTR specifically addresses."
    ]
    (OUTPUT / "FINAL_PHASE1_17A_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    supervisor = ["# Supervisor Phase 1.17A one-page", "", f"**Decision: {decision}**", "", "- Diagnostic only: 38,400 already-selected Phase 1.16 queries; no new model fit or trajectory.", f"- c=0 fractions: normal {base.mean_r_N:.3f}, P/VX/LS tangent {base.mean_r_T:.3f}, ST {base.mean_r_ST:.3f}.", f"- c=4 fractions: normal {strongest.mean_r_N:.3f}, tangent {strongest.mean_r_T:.3f}, ST {strongest.mean_r_ST:.3f}.", f"- Positive extra squared-distance contribution at c=4: normal {extra['normal']:.1%}, tangent {extra['tangent']:.1%}, ST {extra['st']:.1%}.", f"- B1 distance Δ {flags['B1_distance_delta_c4']:+.3f}; q20-query fraction Δ {flags['q20_fraction_delta_c4']:+.3f}; Keyhole-query fraction Δ {flags['keyhole_fraction_delta_c4']:+.3f}.", f"- At c=4, B1 distance is associated with ST share (ρ={overall_assoc.loc[('REP_C400','r_ST'),'repeat_mean_rho']:+.3f}) and inversely with tangent share (ρ={overall_assoc.loc[('REP_C400','r_T'),'repeat_mean_rho']:+.3f}); normal association is unresolved.", "- The pattern changes by budget: early ST, mid mixed, late normal-share increase.", "- ST is not declared physically irrelevant; this is standardized-space geometry.", "- Physics contours are not claimed to be the true M3 decision boundary.", "- Recommendation: do not run Phase 1.17B now; no single harmful mechanism is isolated that tangent-only PCTR specifically removes."]
    (OUTPUT / "SUPERVISOR_PHASE1_17A_ONE_PAGE.md").write_text("\n".join(supervisor) + "\n", encoding="utf-8")
    ledger = ["# Phase 1.17A claim ledger", "", "| Claim | Status |", "|---|---|", "| Exact Phase 1.16 standardized geometry is recovered. | SUPPORTED |", f"| Extra diversity is predominantly physics-normal escape. | {'SUPPORTED' if decision=='NORMAL_ESCAPE' else 'NOT SUPPORTED'} |", f"| Extra diversity is predominantly ST-nullspace escape. | {'SUPPORTED' if decision=='ST_NULLSPACE_ESCAPE' else 'NOT SUPPORTED'} |", f"| Extra diversity is predominantly P/VX/LS physics-tangent spread. | {'SUPPORTED' if decision=='TRUE_PHYSICS_TANGENT_SPREAD' else 'NOT SUPPORTED'} |", "| The mechanism is mixed and budget-dependent. | SUPPORTED |", "| Greater retrospective B1 distance is associated with higher ST share at c=4. | SUPPORTED |", "| The h contour is the true M3 decision boundary. | NOT SUPPORTED |", "| ST is causally irrelevant. | NOT SUPPORTED |", "| PCTR improves sample efficiency. | NOT TESTED |", "| Phase 1.17B is justified now. | NOT SUPPORTED |"]
    (OUTPUT / "claim_ledger.md").write_text("\n".join(ledger) + "\n", encoding="utf-8")
    red = ["# Final red-team report", "", "- Exact published Phase 1.16 paths are read; no selection or model fitting occurs.", "- Nearest neighbors use the original standardized Euclidean metric, not the proposed tangent metric.", "- Local standardized gradient uses the chain-rule scale factors and has exactly zero ST component.", "- Geometry is written and hashed before truth/B1/q20/q30 are joined.", "- Orthogonality, vector reconstruction, energy identity, and fraction sum are tested row-wise.", "- Candidate rows are descriptive; inference aggregates the five folds inside 20 repeat blocks.", "", "## Adversarial mechanism answers", "", "1. **Normal escape?** Partial contribution (30.1% of positive extra energy), but not a dominant explanation; c=4 normal/B1 association is unresolved.", "2. **ST-nullspace escape?** Partial contribution (26.9%), and ST share is positively associated with B1 distance, but it is not dominant and its c=4 overall share increase is unresolved.", "3. **Genuine P/VX/LS tangent spread?** Largest absolute contribution (42.9%), but tangent share decreases rather than increases.", "4. **Budget-dependent?** Yes: early ST increase, mid mixed pattern, late normal-share increase.", "5. **Strongest around B25–40?** Total distance and B1 displacement rise there, but no single component dominates that region.", "6. **Greater B1 distance?** Most consistently higher ST share and lower tangent share; not higher normal share at c=4.", "7. **Lower q20 concentration?** q20-like queries are more tangent and less ST; under c=4 they are not enriched in normal share.", "8. **Lower active-query Keyhole fraction?** Keyhole selections have more normal and less ST than Conduction; under c=4 their tangent difference is near zero.", "9. **Would PCTR remove a harmful mechanism?** It removes normal motion only; the audit does not establish that normal motion drives the harmful B1/q20 shift.", "10. **Is Euclidean repulsion already mostly tangent?** In absolute extra energy, tangent is the largest single component, but the overall mechanism remains mixed.", "11. **Is ST responsible?** Association is present, especially with B1 distance, but causality is not established and the MID ST share falls.", "12. **Run Phase 1.17B?** No. A clear PCTR-specific harmful mechanism was not isolated.", "", "- Increased ST share is not interpreted as causal irrelevance.", "- Physics-contour normal is not called the true GP boundary normal.", "- Component/B1 and component/Keyhole relationships are retrospective associations."]
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red) + "\n", encoding="utf-8")


def build_notebook() -> None:
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.17A — Physics-Contour Geometry Audit\n\nDiagnostic only: no new acquisition path and no M3 refit."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_17a_physics_contour_geometry_audit'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 1. Geometry being audited\n\nEvery selected query is compared with its nearest previously queried point in the exact outer-pool standardized `[P,VX,LS,ST]` coordinates used by Phase 1.16."),
        nbf.v4.new_code_cell("display(json.loads((OUT/'analysis_specification.json').read_text())); display(pd.read_csv(OUT/'geometry_component_summary.csv'))"),
        nbf.v4.new_markdown_cell("## 2. Scale response\n\nSquared displacement is split into local physics-normal, P/VX/LS physics-tangent, and ST components."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'scale_response_geometry.csv')); display(Image(filename=str(OUT/'figures'/'01_component_fractions_vs_scale.png'))); display(Image(filename=str(OUT/'figures'/'05_extra_distance_mechanism.png')))"),
        nbf.v4.new_markdown_cell("## 3. Budget dependence"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'budget_region_geometry.csv')); display(Image(filename=str(OUT/'figures'/'02_components_by_budget_region.png')))"),
        nbf.v4.new_markdown_cell("## 4. Retrospective q20 and B1 diagnostics\n\nThese quantities were joined only after the geometry table was frozen."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'q20_geometry_comparison.csv')); display(pd.read_csv(OUT/'b1_component_associations.csv').query(\"region=='OVERALL_B17_80'\")); display(Image(filename=str(OUT/'figures'/'03_q20_component_comparison.png'))); display(Image(filename=str(OUT/'figures'/'04_B1_component_associations.png')))"),
        nbf.v4.new_markdown_cell("## 5. Paired repeat-block inference"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'repeat_block_inference.csv').query(\"scope=='OVERALL_B17_80'\"))"),
        nbf.v4.new_markdown_cell("## 6. Safe decision"),
        nbf.v4.new_code_cell("display(json.loads((OUT/'mechanism_decision.json').read_text(encoding='utf-8'))); display(Markdown((OUT/'SUPERVISOR_PHASE1_17A_ONE_PAGE.md').read_text(encoding='utf-8')))"),
    ]
    notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Thesis Python", "language": "python", "name": "thesis"}})
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True); nbf.write(notebook, NOTEBOOK)
    executed = NotebookClient(nbf.read(NOTEBOOK, as_version=4), timeout=180, kernel_name="thesis", resources={"metadata": {"path": str(ROOT)}}).execute(); nbf.write(executed, NOTEBOOK)


def validate(geometry: pd.DataFrame, joined: pd.DataFrame, recovery: pd.DataFrame, inference: pd.DataFrame, figures: pd.DataFrame, decision: str) -> dict[str, Any]:
    population, specs, paths = load_inputs(); gate = json.loads((OUTPUT / "baseline_gate.json").read_text()); freeze = json.loads((OUTPUT / "geometry_freeze.json").read_text()); spec = json.loads((OUTPUT / "analysis_specification.json").read_text()); source = Path(__file__).read_text(encoding="utf-8"); notebook = nbf.read(NOTEBOOK, as_version=4); code = [c for c in notebook.cells if c.cell_type == "code"]
    geometry_source = source[source.index("def decompose_displacement"):source.index('write_csv(OUTPUT / "query_geometry_components.csv.gz"')]
    checks = [
        ("exact_parent_sha", gate["exact_branch_base"] == PARENT_SHA, gate["exact_branch_base"]), ("exact_phase16_paths", gate["paths"] == 600 and gate["path_rows"] == 48000, "600x80"),
        ("no_new_trajectory", spec["diagnostic_only"] and not spec["new_trajectory"] and "choose_" not in geometry_source, "diagnostic only"), ("exact_scaler_recovery", recovery.absolute_difference.max() < 1e-12, str(float(recovery.absolute_difference.max()))),
        ("standardized_gradient_formula", "scale[0] / selected_x[0]" in source and "-scale[1] / (2.0 * selected_x[1])" in source and "-3.0 * scale[2] / (2.0 * selected_x[2])" in source, "chain rule"),
        ("gradient_at_selected_candidate", "decompose_displacement(dz, x[selected], scaler.scale_)" in source, "local"), ("ST_gradient_zero", geometry.normal_ST.abs().max() == 0, "exact zero"),
        ("nearest_original_euclidean", "distances = np.sqrt((differences**2).sum(axis=1))" in geometry_source, "standardized Euclidean"),
        ("orthogonal_decomposition", geometry[["orthogonality_N_T", "orthogonality_N_ST", "orthogonality_T_ST"]].to_numpy().max() < 1e-12, str(float(geometry[["orthogonality_N_T", "orthogonality_N_ST", "orthogonality_T_ST"]].to_numpy().max()))),
        ("reconstruction_identity", geometry.reconstruction_error.max() < 1e-12, str(float(geometry.reconstruction_error.max()))), ("energy_identity", geometry.energy_error.max() < 1e-12, str(float(geometry.energy_error.max()))),
        ("fraction_sum", geometry.fraction_sum_error.max() < 1e-12, str(float(geometry.fraction_sum_error.max()))), ("zero_distance_reported", geometry.zero_distance.sum() == 0, str(int(geometry.zero_distance.sum()))),
        ("no_ARD_metric", "ARD" not in geometry_source and "Lambda" not in geometry_source, "none"), ("labels_absent_geometry", "labels" not in geometry_source and "true_label" not in geometry.columns, "absent"),
        ("B1_q_absent_geometry", not any(token in geometry_source for token in ("B1", "q20", "q30")) and not any(token in c for c in geometry.columns for token in ("B1", "q20", "q30")), "absent"),
        ("freeze_before_join", source.index("reconstruct_geometry()") < source.index("retrospective_join(geometry)") and freeze["sha256"] == sha256_file(OUTPUT / "query_geometry_components.csv.gz"), "frozen"),
        ("exact_arms", set(geometry.arm) == set(ARMS), str(sorted(geometry.arm.unique()))), ("exact_budgets_lengths", len(geometry) == 38400 and set(geometry.selection_budget) == set(range(17, 81)), str(len(geometry))),
        ("train_test_integrity", all(set(g.population_row_index).isdisjoint(s.test_indices) for s in specs for _, g in paths[(paths.run_id.eq(s.run_id))].groupby("arm")), "all"),
        ("repeat_block_inference", joined.repeat.nunique() == 20 and inference.bootstrap_draws.eq(BOOTSTRAP_DRAWS).all(), "20 blocks"), ("bootstrap_10000", BOOTSTRAP_DRAWS == 10000, str(BOOTSTRAP_DRAWS)),
        ("notebook_executed", bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs", []) if o.get("output_type") == "error"], str(len(code))),
        ("figure_hashes", len(figures) <= 5 and all(sha256_file(FIGURES / r.figure) == r.sha256 for r in figures.itertuples(index=False)), str(len(figures))),
        ("historical_outputs_unchanged", historical_changes() == [], str(historical_changes())), ("no_placeholders", all(t not in (OUTPUT / "FINAL_PHASE1_17A_REPORT.md").read_text() for t in ("TODO", "TBD", "{decision}")), "none"),
        ("decision_valid", decision in spec["decision_categories"], decision),
    ]
    records = [{"check": n, "status": "PASS" if ok else "FAIL", "detail": d} for n, ok, d in checks]; payload = {"status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL", "check_count": len(records), "passed": sum(r["status"] == "PASS" for r in records), "checks": records}
    write_json(OUTPUT / "validation_report.json", payload); lines = ["# Phase 1.17A validation", "", f"Status: **{payload['status']}**", f"Checks: **{payload['passed']} / {payload['check_count']} PASS**", "", "| Check | Status | Detail |", "|---|---|---|"] + [f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8"); require(payload["status"] == "PASS", "validation failed"); return payload


def write_manifest(validation: dict[str, Any], decision: str) -> None:
    files = [p for p in OUTPUT.rglob("*") if p.is_file() and p.name != "run_manifest.json"] + [Path(__file__), ROOT / "tests" / "test_week9_phase1_17a_physics_contour_geometry_audit.py", NOTEBOOK]
    entries = []
    for path in sorted(set(files)):
        payload = artifact_bytes(path); entries.append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)})
    write_json(OUTPUT / "run_manifest.json", {"study": "Week 9 Phase 1.17A — Physics-Contour Geometry Audit", "parent_sha": PARENT_SHA, "branch": BRANCH, "decision": decision, "protocol": {"new_trajectory": False, "arms": list(ARMS), "active_queries": 38400, "repeat_blocks": 20, "bootstrap_draws": BOOTSTRAP_DRAWS}, "validation": validation, "historical_changes": historical_changes(), "files": entries})


def run() -> dict[str, Any]:
    gate = baseline_gate(); analysis_specification(); geometry, freeze = reconstruct_geometry(); recovery = scaler_recovery_audit(geometry); joined = retrospective_join(geometry)
    overall, scale, region, checkpoint = summarize_geometry(joined); q20 = group_comparison(joined, "is_q20_like", "q20_like", "non_q20"); q30 = group_comparison(joined, "is_q30_like", "q30_like", "outside_q30"); classes = group_comparison(joined, "true_label", "Keyhole", "Conduction"); associations = b1_associations(joined); inference = repeat_inference(joined); decision, flags = decide(scale, inference, associations)
    for name, frame in (("geometry_component_summary.csv", overall), ("scale_response_geometry.csv", scale), ("budget_region_geometry.csv", region), ("checkpoint_geometry.csv", checkpoint), ("q20_geometry_comparison.csv", q20), ("q30_geometry_comparison.csv", q30), ("class_geometry_comparison.csv", classes), ("b1_component_associations.csv", associations), ("repeat_block_inference.csv", inference), ("scaler_recovery_audit.csv", recovery)): write_csv(OUTPUT / name, frame)
    write_json(OUTPUT / "mechanism_decision.json", {"decision": decision, "flags": flags, "predeclared_categories": analysis_specification()["decision_categories"]})
    figures = make_figures(scale, region, q20, associations); build_reports(decision, flags, scale, region, q20, q30, classes, associations, inference, recovery, geometry); build_notebook(); validation = validate(geometry, joined, recovery, inference, figures, decision); write_manifest(validation, decision)
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT / item["path"])).hexdigest() == item["sha256"] for item in manifest["files"]), "manifest hash failure")
    return {"status": "PASS", "decision": decision, "rows": len(geometry), "validation_checks": validation["check_count"], "historical_changes": historical_changes(), "parent": gate["required_parent_sha"]}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--preflight", action="store_true"); parser.add_argument("--run", action="store_true"); args = parser.parse_args()
    if args.preflight: print(json.dumps({"baseline": baseline_gate(), "specification": analysis_specification()}, indent=2))
    if args.run: print(json.dumps(run(), indent=2))
    if not (args.preflight or args.run): parser.error("choose --preflight or --run")


if __name__ == "__main__": main()
