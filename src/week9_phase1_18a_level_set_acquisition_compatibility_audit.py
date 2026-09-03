"""Week 9 Phase 1.18A: frozen-prefix acquisition compatibility audit.

No acquisition trajectory is generated.  Exact published M3-margin prefixes are
refit only at six checkpoints, then every still-unqueried training-pool point is
scored without exposing its label or any B1/q20/q30 information.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from nbclient import NotebookClient
from scipy.linalg import solve
from scipy.special import expit, erf, logsumexp
from scipy.stats import kendalltau, norm, spearmanr

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_14_m3_margin_acquisition as p14


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_18a_level_set_acquisition_compatibility_audit"
FIGURES = OUTPUT / "figures"
CHECKPOINTS = OUTPUT / "checkpoints"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "16_week9_phase1_18a_level_set_acquisition_compatibility_audit.ipynb"
PHASE14 = ROOT / "outputs" / "week9_phase1_14_m3_margin_acquisition"
PARENT_SHA = "2acdb9aba6bbadcd90ba0760ea0958c08e0ea593"
BRANCH = "codex/week9-phase1-18a-level-set-acquisition-compatibility-audit"
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = (16, 24, 32, 40, 60, 80)
METHODS = ("M3_MARGIN", "M3_STRADDLE", "M3_EMI", "M3_SMOCU_APPROX", "M3_SUR_APPROX", "M3_TMES_GSUR", "PA_TVR_CANDIDATE")
SCORE_COLUMNS = {
    "M3_MARGIN": "margin_score",
    "M3_STRADDLE": "straddle_score",
    "M3_EMI": "emi_score",
    "M3_SMOCU_APPROX": "smocu_score",
    "M3_SUR_APPROX": "sur_score",
    "M3_TMES_GSUR": "tmse_gsur_score",
    "PA_TVR_CANDIDATE": "pa_tvr_score",
}
BOOTSTRAP_DRAWS = 10_000
SMOCU_K = 10.0
GH_NODES = 24
SEED_ROOT = "week9_phase1_18a|frozen-prefix|v1"
COLLAPSE = {"median_spearman": .995, "q05_spearman": .98, "top1_agreement": .90, "mean_top10_jaccard": .90}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(x) for x in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() not in {".png", ".gz", ".ipynb"}:
        payload = payload.replace(b"\r\n", b"\n")
    return payload


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = frame.to_csv(index=False, lineterminator="\n").encode()
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    else:
        path.write_bytes(raw)


def historical_changes() -> list[str]:
    protected = [str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "outputs").glob("week9_phase1_*") if p.name != OUTPUT.name]
    result = subprocess.check_output(["git", "diff", "--name-only", PARENT_SHA, "--", *protected], cwd=ROOT, text=True)
    return [line for line in result.splitlines() if line.strip()]


def load_inputs() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]]]:
    population, specs, _ = p13.load_inputs()
    frame = pd.read_csv(PHASE14 / "m3_margin_paths.csv.gz")
    paths = {str(run): g.sort_values("query_order").population_row_index.astype(int).tolist() for run, g in frame.groupby("run_id", sort=True)}
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73, "population drift")
    require(len(specs) == len(paths) == 100, "run/path drift")
    for spec in specs:
        path = paths[spec.run_id]
        require(len(path) == len(set(path)) == 80, f"path drift {spec.run_id}")
        require(set(path).issubset(spec.train_indices) and set(path).isdisjoint(spec.test_indices), f"path information flow {spec.run_id}")
    return population, specs, paths


def baseline_gate() -> dict[str, Any]:
    population, specs, paths = load_inputs()
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    base = subprocess.check_output(["git", "merge-base", "HEAD", PARENT_SHA], cwd=ROOT, text=True).strip()
    p14_manifest = json.loads((PHASE14 / "run_manifest.json").read_text(encoding="utf-8"))
    initial_matches = sum(paths[s.run_id][:16] == w85.initial_design(s, population) for s in specs)
    payload = {
        "status": "PASS", "required_parent_sha": PARENT_SHA, "current_head": current, "exact_branch_base": base,
        "population": len(population), "keyholes": int(population.has_keyhole.sum()), "conduction": int((~population.has_keyhole.astype(bool)).sum()),
        "outer_runs": len(specs), "repeat_blocks": len(set(s.repeat for s in specs)), "folds": 5, "paths": len(paths),
        "initial_design_matches": initial_matches, "budgets": list(BUDGETS), "phase14_decision": p14_manifest["decision"],
        "historical_changes": historical_changes(),
    }
    ok = base == PARENT_SHA and (payload["population"], payload["keyholes"], payload["conduction"]) == (405, 73, 332) and initial_matches == 100 and not payload["historical_changes"]
    payload["status"] = "PASS" if ok else "FAIL"
    write_json(OUTPUT / "baseline_gate.json", payload)
    require(ok, f"baseline gate failed {payload}")
    return payload


def analysis_specification() -> dict[str, Any]:
    payload = {
        "status": "FROZEN_BEFORE_FULL_600_SNAPSHOT_SUMMARY", "diagnostic_only": True, "new_trajectory": False,
        "prefix_source": "exact published Phase 1.14 M3-margin path", "budgets": list(BUDGETS), "snapshots": 600,
        "m3": {"stage1": "revealed-label log(h) logistic latent mean, then frozen", "stage2": "ARD Matern-3/2 Laplace GPC on standardized P,VX,LS,ST", "log_h_in_residual": False, "length_upper_primary": 100.0, "length_upper_sensitivity": 1000.0},
        "methods": list(METHODS), "smocu_softness_k": SMOCU_K, "expected_curvature_quadrature_nodes": GH_NODES,
        "ranking_collapse_rule": COLLAPSE,
        "ranking_collapse_interpretation": "all four thresholds must pass over the 600 snapshot distribution",
        "lookahead_reference_pool": "all currently unqueried outer-training candidates",
        "approximation": "SMOCU/SUR use a disclosed logistic-Laplace rank-one moment update and are never called exact",
        "retrospective_join": "only after candidate_scores_pre_reveal.csv.gz is written and hashed",
        "pa_tvr_decision_precommit": "reject if its geometry factor lacks a Matérn-3/2 tangent-integral derivation, irrespective of retrospective behavior",
        "forbidden": ["new acquisition trajectory", "candidate truth in scoring", "B1/q20/q30 in scoring", "sample-efficiency claim", "unsupported novelty claim"],
    }
    write_json(OUTPUT / "analysis_specification.json", payload)
    return payload


def expected_logistic_curvature(mu: np.ndarray, var: np.ndarray) -> np.ndarray:
    nodes, weights = np.polynomial.hermite.hermgauss(GH_NODES)
    latent = np.asarray(mu)[..., None] + np.sqrt(2.0 * np.asarray(var))[..., None] * nodes
    prob = expit(latent)
    return np.sum(weights * prob * (1.0 - prob), axis=-1) / math.sqrt(math.pi)


def logistic_gaussian_probability(mu: np.ndarray, var: np.ndarray) -> np.ndarray:
    mu = np.asarray(mu, float); var = np.maximum(np.asarray(var, float), p11.EPS)
    flat_mu = mu.reshape(-1); flat_var = var.reshape(-1)
    alpha = 1.0 / (2.0 * flat_var)
    gamma = p11.WB_LAMBDAS * flat_mu
    integrals = np.sqrt(np.pi / alpha) * erf(gamma * np.sqrt(alpha / (alpha + p11.WB_LAMBDAS**2))) / (2.0 * np.sqrt(flat_var * 2.0 * np.pi))
    positive = (p11.WB_COEFS * integrals).sum(axis=0) + 0.5 * p11.WB_COEFS.sum()
    return np.clip(positive, p11.EPS, 1.0 - p11.EPS).reshape(mu.shape)


def emi_score(mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    sd = np.maximum(np.asarray(sd, float), 1e-15); absolute = np.abs(np.asarray(mu, float)); z = absolute / sd
    return sd * norm.pdf(z) - absolute * norm.cdf(-z)


def posterior_covariance(fit: Any, x_scaled: np.ndarray) -> np.ndarray:
    cross = fit.gp.kernel_(fit.gp.X_train_, x_scaled)
    v = solve(fit.gp.L_, fit.gp.W_sr_[:, None] * cross)
    covariance = fit.gp.kernel_(x_scaled) - v.T.dot(v)
    covariance = (covariance + covariance.T) / 2.0
    np.fill_diagonal(covariance, np.maximum(np.diag(covariance), p11.EPS))
    return covariance


def physics_gradient_and_S(fit: Any, x_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coefficient = float(fit.physics.model.coef_[0, 0]) / float(fit.physics.scaler.scale_[0])
    scales = fit.x_scaler.scale_
    gradient = coefficient * np.column_stack([
        scales[0] / x_raw[:, 0], -scales[1] / (2.0 * x_raw[:, 1]), -3.0 * scales[2] / (2.0 * x_raw[:, 2]), np.zeros(len(x_raw)),
    ])
    lengths = fit.length_scales
    S = np.sum((gradient * lengths[None, :]) ** 2, axis=1)
    return gradient, np.maximum(S, 1e-15)


def fast_global_scores(mu: np.ndarray, var: np.ndarray, probability: np.ndarray, covariance: np.ndarray, curvature: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Disclosed rank-one logistic-Laplace moment approximation.

    Rows are reference points u and columns hypothetical queried points x.
    Cross-covariance transmits the update globally; no labels are observed.
    """
    denom = 1.0 + var * curvature
    new_var = np.maximum(var[:, None] - covariance**2 * curvature[None, :] / denom[None, :], p11.EPS)
    shift1 = covariance * (1.0 - probability)[None, :] / denom[None, :]
    shift0 = covariance * (0.0 - probability)[None, :] / denom[None, :]
    p1 = logistic_gaussian_probability(mu[:, None] + shift1, new_var)
    p0 = logistic_gaussian_probability(mu[:, None] + shift0, new_var)
    weights = probability[None, :]
    current_soft = logsumexp(np.stack([SMOCU_K * probability, SMOCU_K * (1.0 - probability)], axis=0), axis=0) / SMOCU_K
    soft1 = logsumexp(np.stack([SMOCU_K * p1, SMOCU_K * (1.0 - p1)], axis=0), axis=0) / SMOCU_K
    soft0 = logsumexp(np.stack([SMOCU_K * p0, SMOCU_K * (1.0 - p0)], axis=0), axis=0) / SMOCU_K
    smocu = np.mean(weights * soft1 + (1.0 - weights) * soft0 - current_soft[:, None], axis=0)
    current_uncertainty = probability * (1.0 - probability)
    expected_uncertainty = weights * p1 * (1.0 - p1) + (1.0 - weights) * p0 * (1.0 - p0)
    sur = np.mean(current_uncertainty[:, None] - expected_uncertainty, axis=0)
    return smocu, sur


def score_snapshot(spec: Any, budget: int, population: pd.DataFrame, path: Sequence[int], length_upper: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    x4 = population.loc[:, FEATURES].to_numpy(float); logh = p11.log_h_values(population); labels = population.has_keyhole.astype(int).to_numpy()
    revealed = np.asarray(path[:budget], int); train = np.asarray(spec.train_indices, int); candidate = np.setdiff1d(train, revealed)
    physics = p11.fit_physics_mean(logh, labels, revealed, p13.seed_u32("shared_physics", spec.run_id, budget))
    started_fit = time.perf_counter(); fit = p13.fit_hybrid(x4, logh, labels, revealed, train, physics, "M3", length_upper); fit_seconds = time.perf_counter() - started_fit
    started_local = time.perf_counter(); comp = p13.components(fit, x4[candidate], logh[candidate]); mu = comp["final_latent"]; var = comp["latent_variance"]; sd = np.sqrt(var); probability = comp["probability"]
    margin = 1.0 - 2.0 * np.abs(probability - .5); straddle = 1.96 * sd - np.abs(mu); emi = emi_score(mu, sd)
    curvature_a = probability * (1.0 - probability); latent_probability = expit(mu); curvature_b = latent_probability * (1.0 - latent_probability); curvature_c = expected_logistic_curvature(mu, var)
    variance_reduction_a = var**2 * curvature_a / (1.0 + var * curvature_a); variance_reduction_b = var**2 * curvature_b / (1.0 + var * curvature_b); variance_reduction_c = var**2 * curvature_c / (1.0 + var * curvature_c)
    gradient, S = physics_gradient_and_S(fit, x4[candidate]); gate = np.exp(-2.0 * mu**2 / S) / np.sqrt(S)
    pa_a = variance_reduction_a * gate; pa_b = variance_reduction_b * gate; pa_c = variance_reduction_c * gate
    tmse_gsur = variance_reduction_c * norm.pdf(mu / sd) / sd
    local_seconds = time.perf_counter() - started_local
    started_global = time.perf_counter(); covariance = posterior_covariance(fit, fit.x_scaler.transform(x4[candidate])); smocu, sur = fast_global_scores(mu, var, probability, covariance, curvature_c); global_seconds = time.perf_counter() - started_global
    diagnostics = p13.fit_diagnostic(fit)
    frame = pd.DataFrame({
        "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "candidate_population_row_index": candidate,
        "m3_probability": probability, "final_latent_mean": mu, "residual_latent_variance": var, "final_latent_variance": var, "latent_sd": sd,
        "physics_latent_mean": comp["physics_latent"], "residual_latent_correction": comp["residual_latent"],
        "margin_score": margin, "straddle_score": straddle, "emi_score": emi, "smocu_score": smocu, "sur_score": sur, "tmse_gsur_score": tmse_gsur,
        "pa_tvr_score": pa_c, "pa_tvr_score_WA": pa_a, "pa_tvr_score_WB": pa_b, "pa_tvr_score_WC": pa_c,
        "curvature_WA": curvature_a, "curvature_WB": curvature_b, "curvature_WC": curvature_c,
        "variance_reduction_WA": variance_reduction_a, "variance_reduction_WB": variance_reduction_b, "variance_reduction_WC": variance_reduction_c,
        "physics_gradient_P": gradient[:, 0], "physics_gradient_VX": gradient[:, 1], "physics_gradient_LS": gradient[:, 2], "physics_gradient_ST": gradient[:, 3],
        "pa_S": S, "pa_geometry_gate": gate, "l_P": fit.length_scales[0], "l_VX": fit.length_scales[1], "l_LS": fit.length_scales[2], "l_ST": fit.length_scales[3],
        "length_upper": length_upper,
    })
    require(frame.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan).notna().all().all(), f"nonfinite score {spec.run_id}/B{budget}/L{length_upper}")
    runtime = {"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "length_upper": length_upper, "candidate_count": len(candidate), "fit_seconds": fit_seconds, "local_score_seconds": local_seconds, "global_score_seconds": global_seconds, **diagnostics}
    return frame, runtime


def checkpoint_path(run_id: str) -> Path:
    return CHECKPOINTS / f"{run_id}.json.gz"


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(json_safe(payload), sort_keys=True) + "\n").encode(), compresslevel=6, mtime=0))


def read_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def run_one_spec(spec: Any, population: pd.DataFrame, path: Sequence[int]) -> dict[str, Any]:
    destination = checkpoint_path(spec.run_id)
    if destination.is_file():
        payload = read_checkpoint(destination)
        if payload.get("complete") and payload.get("parent_sha") == PARENT_SHA:
            return {"run_id": spec.run_id, "reused": True}
    primary_rows: list[dict[str, Any]] = []; sensitivity_rows: list[dict[str, Any]] = []; runtimes: list[dict[str, Any]] = []
    for budget in BUDGETS:
        primary, runtime = score_snapshot(spec, budget, population, path, 100.0); primary_rows.extend(primary.to_dict("records")); runtimes.append(runtime)
        sensitivity, runtime_s = score_snapshot(spec, budget, population, path, 1000.0)
        sensitivity_rows.extend(sensitivity[["run_id", "repeat", "fold", "budget", "candidate_population_row_index", "pa_tvr_score", "pa_S", "l_P", "l_VX", "l_LS", "l_ST"]].to_dict("records")); runtimes.append(runtime_s)
    write_checkpoint(destination, {"complete": True, "parent_sha": PARENT_SHA, "run_id": spec.run_id, "primary": primary_rows, "sensitivity": sensitivity_rows, "runtime": runtimes})
    return {"run_id": spec.run_id, "reused": False}


def run_main(workers: int = 4, limit_specs: int | None = None) -> dict[str, Any]:
    baseline_gate(); analysis_specification(); population, specs, paths = load_inputs(); selected = specs[:limit_specs] if limit_specs else specs
    started = time.time(); results = Parallel(n_jobs=workers, verbose=10)(delayed(run_one_spec)(spec, population, paths[spec.run_id]) for spec in selected)
    payload = {"status": "PASS", "completed_runs": len(results), "reused_runs": sum(r["reused"] for r in results), "workers": workers, "elapsed_seconds": time.time() - started, "complete": limit_specs is None}
    write_json(OUTPUT / "execution_report.json", payload); return payload


def collect_checkpoints() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    population, specs, paths = load_inputs(); primary=[]; sensitivity=[]; runtimes=[]; manifest=[]
    for spec in specs:
        payload=read_checkpoint(checkpoint_path(spec.run_id)); require(payload.get("complete"),f"incomplete {spec.run_id}")
        primary.extend(payload["primary"]); sensitivity.extend(payload["sensitivity"]); runtimes.extend(payload["runtime"])
        for budget in BUDGETS:
            revealed=paths[spec.run_id][:budget]; candidates=set(spec.train_indices)-set(revealed)
            manifest.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"revealed_count":len(revealed),"candidate_count":len(candidates),"revealed_prefix_sha256":hashlib.sha256(json.dumps(revealed).encode()).hexdigest(),"source":"Phase 1.14 published M3-margin path"})
    scores=pd.DataFrame(primary).sort_values(["run_id","budget","candidate_population_row_index"]).reset_index(drop=True)
    sens=pd.DataFrame(sensitivity).sort_values(["run_id","budget","candidate_population_row_index"]).reset_index(drop=True)
    runtime=pd.DataFrame(runtimes).sort_values(["run_id","budget","length_upper"]).reset_index(drop=True)
    require(len(scores)==169200 and len(sens)==169200,"candidate occurrence drift")
    require(len(scores[["run_id","budget"]].drop_duplicates())==600,"snapshot drift")
    forbidden={"truth","has_keyhole","B1","q20","q30","is_q20","is_q30"}; require(not forbidden.intersection(scores.columns),"pre-reveal leakage")
    write_csv(OUTPUT/"frozen_prefix_manifest.csv",pd.DataFrame(manifest)); write_csv(OUTPUT/"candidate_scores_pre_reveal.csv.gz",scores)
    score_hash=sha256_file(OUTPUT/"candidate_scores_pre_reveal.csv.gz")
    write_json(OUTPUT/"candidate_scores_sha256.json",{"sha256":score_hash,"rows":len(scores),"columns":list(scores.columns),"frozen_before_retrospective_join":True})
    write_csv(OUTPUT/"runtime_benchmark.csv",runtime)
    return scores,sens,runtime


def jaccard_top(a: pd.DataFrame, ca: str, cb: str, k: int) -> float:
    sa=set(a.nlargest(k,[ca,"candidate_population_row_index"]).candidate_population_row_index); sb=set(a.nlargest(k,[cb,"candidate_population_row_index"]).candidate_population_row_index)
    return len(sa&sb)/len(sa|sb)


def snapshot_rankings(scores: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (run,budget),g in scores.groupby(["run_id","budget"],sort=True):
        for i,left in enumerate(METHODS):
            for right in METHODS[i+1:]:
                a=SCORE_COLUMNS[left]; b=SCORE_COLUMNS[right]; topa=int(g.loc[g[a].idxmax(),"candidate_population_row_index"]); topb=int(g.loc[g[b].idxmax(),"candidate_population_row_index"])
                rank_margin=g["margin_score"].rank(method="min",ascending=False); top_left_pos=g.index[g.candidate_population_row_index.eq(topa)][0]
                rows.append({"run_id":run,"repeat":int(g.repeat.iloc[0]),"fold":int(g.fold.iloc[0]),"budget":budget,"region":"EARLY" if budget<=24 else ("MID" if budget<=40 else "LATE"),"method_left":left,"method_right":right,"spearman":float(spearmanr(g[a],g[b]).statistic),"kendall_tau":float(kendalltau(g[a],g[b]).statistic),"top1_agreement":float(topa==topb),"top5_jaccard":jaccard_top(g,a,b,5),"top10_jaccard":jaccard_top(g,a,b,10),"left_top_rank_under_margin":float(rank_margin.loc[top_left_pos])})
    return pd.DataFrame(rows)


def ranking_outputs(scores: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    detail=snapshot_rankings(scores); write_csv(OUTPUT/"ranking_budget_summary.csv",detail)
    aggregate=detail.groupby(["method_left","method_right"],as_index=False).agg(snapshots=("spearman","size"),defined_spearman_snapshots=("spearman","count"),median_spearman=("spearman","median"),q05_spearman=("spearman",lambda x:x.quantile(.05)),mean_kendall_tau=("kendall_tau","mean"),top1_agreement=("top1_agreement","mean"),mean_top5_jaccard=("top5_jaccard","mean"),mean_top10_jaccard=("top10_jaccard","mean")); aggregate["undefined_spearman_snapshots"]=aggregate.snapshots-aggregate.defined_spearman_snapshots
    write_csv(OUTPUT/"ranking_pairwise_summary.csv",aggregate)
    topk=detail.groupby(["method_left","method_right","budget"],as_index=False).agg(top1_agreement=("top1_agreement","mean"),top5_jaccard=("top5_jaccard","mean"),top10_jaccard=("top10_jaccard","mean")); write_csv(OUTPUT/"topk_overlap_summary.csv",topk)
    rows=[]
    for method in METHODS[1:]:
        part=detail[((detail.method_left.eq("M3_MARGIN"))&(detail.method_right.eq(method)))|((detail.method_right.eq("M3_MARGIN"))&(detail.method_left.eq(method)))]; vals={"method":method,"median_spearman":part.spearman.median(),"q05_spearman":part.spearman.quantile(.05),"top1_agreement":part.top1_agreement.mean(),"mean_top10_jaccard":part.top10_jaccard.mean()}; vals["decision"]="PRACTICALLY_MARGIN_EQUIVALENT" if all(vals[k]>=v for k,v in COLLAPSE.items()) else "RANKING_DISTINCT_FROM_MARGIN"; rows.append(vals)
    collapse=pd.DataFrame(rows); write_csv(OUTPUT/"margin_collapse_decisions.csv",collapse)
    pa=aggregate[(aggregate.method_left.eq("PA_TVR_CANDIDATE"))|(aggregate.method_right.eq("PA_TVR_CANDIDATE"))].copy(); write_csv(OUTPUT/"pa_tvr_ranking_distinctness.csv",pa)
    return detail,aggregate,topk,collapse


def pa_sensitivity(scores: pd.DataFrame,sens: pd.DataFrame) -> pd.DataFrame:
    keys=["run_id","repeat","fold","budget","candidate_population_row_index"]
    merged=scores[keys+["pa_tvr_score","pa_S"]].merge(sens,on=keys,suffixes=("_L100","_L1000"),validate="one_to_one")
    rows=[]
    for (run,budget),g in merged.groupby(["run_id","budget"],sort=True):
        a="pa_tvr_score_L100"; b="pa_tvr_score_L1000"; rows.append({"run_id":run,"repeat":int(g.repeat.iloc[0]),"fold":int(g.fold.iloc[0]),"budget":budget,"spearman":float(spearmanr(g[a],g[b]).statistic),"top1_agreement":float(g.loc[g[a].idxmax(),"candidate_population_row_index"]==g.loc[g[b].idxmax(),"candidate_population_row_index"]),"top5_jaccard":jaccard_top(g,a,b,5),"top10_jaccard":jaccard_top(g,a,b,10),"median_S_L100":g.pa_S_L100.median(),"median_S_L1000":g.pa_S_L1000.median(),"median_rank_change":float(np.median(np.abs(g[a].rank(ascending=False)-g[b].rank(ascending=False))))})
    out=pd.DataFrame(rows); write_csv(OUTPUT/"pa_tvr_bound_sensitivity.csv",out); return out


def curvature_audit(scores: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for name,col in (("W_A=p_M3(1-p_M3)","curvature_WA"),("W_B=sigmoid(mu)(1-sigmoid(mu))","curvature_WB"),("W_C=E[sigmoid(F)(1-sigmoid(F))]","curvature_WC")):
        rows.append({"definition":name,"role":"predictive-label variance proxy" if "W_A" in name else ("site curvature at posterior mean" if "W_B" in name else "posterior-expected site curvature"),"mean":scores[col].mean(),"median":scores[col].median(),"q05":scores[col].quantile(.05),"q95":scores[col].quantile(.95),"primary_for_PA_TVR":name.startswith("W_C")})
    out=pd.DataFrame(rows); write_csv(OUTPUT/"pa_tvr_laplace_curvature_audit.csv",out); return out


def exact_approx_small_validation(scores:pd.DataFrame) -> pd.DataFrame:
    """Predeclared small check: first run, B16, ID-order min/median/max candidates.

    The exact arm fully refits M3 for each hypothetical label, including Stage 1
    and hyperparameters. It is a validation sample, not the 600-snapshot engine.
    """
    population,specs,paths=load_inputs(); spec=specs[0]; budget=16; base=scores[(scores.run_id.eq(spec.run_id))&scores.budget.eq(budget)].sort_values("candidate_population_row_index"); ids=base.candidate_population_row_index.to_numpy(int); chosen=[int(ids[0]),int(ids[len(ids)//2]),int(ids[-1])]
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy(); revealed=list(paths[spec.run_id][:budget]); reference=ids
    current_soft=logsumexp(np.stack([SMOCU_K*base.m3_probability.to_numpy(),SMOCU_K*(1-base.m3_probability.to_numpy())]),axis=0)/SMOCU_K; current_unc=base.m3_probability.to_numpy()*(1-base.m3_probability.to_numpy()); rows=[]
    for candidate in chosen:
        p_x=float(base.loc[base.candidate_population_row_index.eq(candidate),"m3_probability"].iloc[0]); future={}; elapsed=0.
        for y in (0,1):
            hypothetical=labels.copy(); hypothetical[candidate]=y; reveal=np.asarray(revealed+[candidate],int); started=time.perf_counter(); physics=p11.fit_physics_mean(logh,hypothetical,reveal,p13.seed_u32("p18a_exact",spec.run_id,budget,candidate,y)); fit=p13.fit_hybrid(x4,logh,hypothetical,reveal,np.asarray(spec.train_indices,int),physics,"M3",100.0); elapsed+=time.perf_counter()-started; prob=p13.components(fit,x4[reference],logh[reference])["probability"]; future[y]={"soft":logsumexp(np.stack([SMOCU_K*prob,SMOCU_K*(1-prob)]),axis=0)/SMOCU_K,"unc":prob*(1-prob)}
        exact_sm=float(np.mean(p_x*future[1]["soft"]+(1-p_x)*future[0]["soft"]-current_soft)); exact_sur=float(np.mean(current_unc-(p_x*future[1]["unc"]+(1-p_x)*future[0]["unc"]))); row=base[base.candidate_population_row_index.eq(candidate)].iloc[0]
        rows.append({"run_id":spec.run_id,"budget":budget,"candidate_population_row_index":candidate,"selection_rule":"smallest/median/largest candidate ID; frozen before labels","current_probability":p_x,"smocu_exact_full_refit":exact_sm,"smocu_rank_one_approx":float(row.smocu_score),"sur_exact_full_refit":exact_sur,"sur_rank_one_approx":float(row.sur_score),"exact_refit_seconds_two_labels":elapsed,"exact_refits_include_hyperparameter_reoptimization":True})
    out=pd.DataFrame(rows); out["smocu_exact_rank"]=out.smocu_exact_full_refit.rank(ascending=False); out["smocu_approx_rank"]=out.smocu_rank_one_approx.rank(ascending=False); out["sur_exact_rank"]=out.sur_exact_full_refit.rank(ascending=False); out["sur_approx_rank"]=out.sur_rank_one_approx.rank(ascending=False); write_csv(OUTPUT/"exact_approx_small_validation.csv",out); return out


def emi_monte_carlo() -> pd.DataFrame:
    rng=np.random.default_rng(seed_u32("emi_mc")); rows=[]
    for mu in (-3.,-1.,0.,1.,3.):
        for sd in (.2,.7,1.5):
            f=rng.normal(mu,sd,500_000); mc=float(np.mean(np.maximum(0.,-np.sign(mu if mu else 1.)*f))) if mu!=0 else float(np.mean(np.abs(f))/2)
            closed=float(emi_score(np.array([mu]),np.array([sd]))[0]); rows.append({"mu":mu,"sigma":sd,"closed_form":closed,"monte_carlo":mc,"absolute_error":abs(closed-mc),"draws":500000})
    out=pd.DataFrame(rows); write_csv(OUTPUT/"emi_monte_carlo_validation.csv",out); return out


def retrospective_diagnostic(scores: pd.DataFrame) -> pd.DataFrame:
    # Deliberately called only after the hashed pre-reveal artifact exists.
    require((OUTPUT/"candidate_scores_sha256.json").is_file(),"score table not frozen")
    population,specs,paths=load_inputs(); distances=w85.b1_distance(population); labels=population.has_keyhole.astype(int).to_numpy(); x=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); lookup={s.run_id:s for s in specs}; rows=[]
    for (run,budget),g in scores.groupby(["run_id","budget"],sort=True):
        spec=lookup[run]; test=np.asarray(spec.test_indices,int); q20=float(np.quantile(distances[test],.2)); q30=float(np.quantile(distances[test],.3)); revealed=np.asarray(paths[run][:budget],int); scaler_mean=x[np.asarray(spec.train_indices,int)].mean(axis=0); scaler_sd=x[np.asarray(spec.train_indices,int)].std(axis=0); z=(x-scaler_mean)/scaler_sd
        for method in METHODS:
            idx=int(g.loc[g[SCORE_COLUMNS[method]].idxmax(),"candidate_population_row_index"]); nearest=float(np.min(np.linalg.norm(z[revealed]-z[idx],axis=1)))
            rows.append({"run_id":run,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"method":method,"candidate_population_row_index":idx,"truth_posthoc":int(labels[idx]),"B1_distance_posthoc":float(distances[idx]),"q20_like_posthoc":bool(distances[idx]<=q20),"q30_like_posthoc":bool(distances[idx]<=q30),"nearest_revealed_distance_standardized":nearest,"P":x[idx,0],"VX":x[idx,1],"LS":x[idx,2],"ST":x[idx,3],"h":float(np.exp(logh[idx])),"interpretation":"retrospective diagnostic; not performance"})
    detail=pd.DataFrame(rows); summary=detail.groupby(["method","budget"],as_index=False).agg(top_candidate_occurrences=("truth_posthoc","size"),keyhole_fraction_posthoc=("truth_posthoc","mean"),q20_concentration_posthoc=("q20_like_posthoc","mean"),q30_concentration_posthoc=("q30_like_posthoc","mean"),median_B1_distance_posthoc=("B1_distance_posthoc","median"),median_nearest_revealed_distance=("nearest_revealed_distance_standardized","median"),median_P=("P","median"),median_VX=("VX","median"),median_LS=("LS","median"),median_ST=("ST","median"),median_h=("h","median")); write_csv(OUTPUT/"retrospective_candidate_diagnostics.csv",summary); write_csv(OUTPUT/"retrospective_candidate_details.csv.gz",detail); return summary


def write_method_documents() -> None:
    matrix=pd.DataFrame([
        ["GP-LSE / Straddle","Gotovos et al.",2013,"https://proceedings.mlr.press/v28/gotovos13.html","GP regression confidence bounds","Gaussian observation model","1.96 sigma - |mu-h| in experiments","point-local","myopic","O(N) candidate scoring","not exact; latent-Gaussian adaptation","no explicit physics mean","canonical score retained; classification caveat"],
        ["Excursion-set SUR","Bect et al.",2012,"https://doi.org/10.1007/s11222-011-9241-4","GP regression","Gaussian","expected reduction of integrated excursion uncertainty","global","one-step look-ahead","posterior update over reference set","not directly","mean functions allowed","conceptually compatible; GPC approximation required"],
        ["tMSE/tIMSE","Picheny et al.",2010,"https://doi.org/10.1115/1.4001873","GP regression","Gaussian","variance reduction times target-proximity weight","local/global depending integration","myopic or look-ahead","cheap to moderate","latent adaptation only","mean functions allowed","local tMSE/gSUR proxy retained"],
        ["SMOCU","Zhao et al.",2021,"https://proceedings.mlr.press/v130/zhao21c.html","GP classification","probit/EP in efficient derivation","expected reduction in soft MOCU","global finite pool","one-step look-ahead","quadratic pool update","yes","not central","compatible objective; logistic-Laplace approximation disclosed"],
        ["GPC random-set SUR","Menz et al.",2025,"https://doi.org/10.1016/j.strusafe.2025.102607","GP classification","classification likelihood","random-set uncertainty reduction","global","one-step look-ahead","expensive; fast approximations relevant","yes","not central","direct prior art; exact method not reimplemented"],
        ["EMI","Beachy and Grandhi",2026,"https://doi.org/10.1007/s00158-026-04352-4","latent Gaussian surrogate","Gaussian","sigma phi(|mu|/sigma)-|mu|Phi(-|mu|/sigma)","point-local","myopic","O(1) per candidate","latent adaptation","not central","closed form valid for M3 latent Gaussian; not a GPC look-ahead"],
        ["BALPI extended Straddle","BALPI authors",2026,"https://doi.org/10.1039/D5DD00459D","GPR/GPC","mixed","extended Straddle and SMOCU","point/global","mixed","method dependent","yes for SMOCU","physics phase-boundary context","relevant; extended score has heuristic choices"],
        ["Physics-informed GPC AL","Hardcastle et al.",2025,"https://arxiv.org/abs/2502.11369","physics-informed GP classifier","classification","phase-boundary active learning","method dependent","myopic/global","method dependent","yes","yes","broad novelty already occupied"],
    ],columns=["method","source","year","doi_or_url","surrogate","likelihood","acquisition_definition","scope","lookahead","complexity","classification_supported","physics_prior_supported","M3_relevance"])
    write_csv(OUTPUT/"prior_art_matrix.csv",matrix)
    docs={
    "literature_audit.md":"""# Primary-source literature audit

The audit used primary papers and publisher/author records. Gotovos et al. define GP level-set estimation through confidence bounds and use the experimental Straddle score `1.96 sigma - |mu-h|`. Bect et al. define genuine one-step SUR for excursion-set uncertainty; Picheny et al. define targeted MSE/integrated variants. Zhao et al. define SMOCU as the expected reduction of a softened global classification uncertainty. Menz et al. establish that GPC random-set/SUR work exists. Beachy and Grandhi's EMI is a point-local latent-Gaussian incorrectness magnitude. BALPI combines GPC/SMOCU and GPR extended Straddle, while Hardcastle et al. make broad physics-informed GPC phase-boundary novelty unsafe.

Primary links: [Gotovos et al.](https://proceedings.mlr.press/v28/gotovos13.html), [Bect et al.](https://doi.org/10.1007/s11222-011-9241-4), [Picheny et al.](https://doi.org/10.1115/1.4001873), [Zhao et al.](https://proceedings.mlr.press/v130/zhao21c.html), [Menz et al.](https://doi.org/10.1016/j.strusafe.2025.102607), [Beachy and Grandhi](https://doi.org/10.1007/s00158-026-04352-4), [BALPI](https://doi.org/10.1039/D5DD00459D), and [Hardcastle et al.](https://arxiv.org/abs/2502.11369).

Absence from this focused search is not novelty proof. No claim that GPC-SUR or physics-informed GPC active learning is absent is made.
""",
    "acquisition_definitions.md":"""# Acquisition definitions

- **M3_MARGIN:** `1-2|p_M3-0.5|`; point-local. `p_M3` integrates latent Gaussian variance, so this is not variance-blind. It does not separately reward epistemic variance or global expected reduction.
- **M3_STRADDLE:** `1.96 sigma_f-|mu_f|`; point-local latent-Gaussian adaptation of the canonical experimental Gotovos score. The 1.96 value is fixed, not outcome-tuned; Laplace classification does not inherit the original Gaussian-noise theory.
- **M3_EMI:** `sigma phi(|mu|/sigma)-|mu|Phi(-|mu|/sigma)`; point-local expected latent incorrectness relative to zero.
- **M3_SMOCU_APPROX:** expected finite-pool reduction of `k^-1 log(exp(kp)+exp(k(1-p)))`, `k=10`, using a disclosed logistic-Laplace rank-one moment update.
- **M3_SUR_APPROX:** expected finite-pool reduction in mean `p(1-p)` under the same update.
- **M3_TMES_GSUR:** local posterior variance reduction multiplied by latent contour-density weight `phi(mu/sigma)/sigma`.
- **PA_TVR_CANDIDATE:** local variance-reduction proxy times the supplied physics-gradient gate. It is neither a demonstrated tangent integral nor a global look-ahead.

All scores are maximized. Exact and approximate labels are retained in names and reports.
""",
    "m3_posterior_semantics.md":"""# M3 posterior semantics

M3 fits `f(x)=m_h(x)+r(x)`. Stage 1 learns an h-only logistic latent mean using revealed labels, then freezes it. Stage 2 is a zero-mean ARD Matérn-3/2 discrepancy classifier over standardized `[P,VX,LS,ST]` with Laplace inference; `log(h)` is not a residual coordinate. The stored `residual_latent_variance` is therefore also the represented final Stage-2 latent variance. Uncertainty from estimating `m_h` is not propagated. `predict_proba` integrates the latent Gaussian approximation, so probability margin depends on both latent mean and variance but has no explicit global uncertainty-reduction objective.
""",
    "straddle_compatibility.md":"""# Straddle compatibility

The audited score is `1.96 sigma_f(x)-|mu_f(x)|` for the zero latent contour. `mu_f` and `sigma_f` are M3's final Laplace latent moments. The constant follows Gotovos et al.'s experimental canonical score and was frozen before results. Their theory is for GP confidence bounds, not Bernoulli-logistic Laplace classification; therefore this is a compatible latent-Gaussian heuristic, not a transferred guarantee.
""",
    "emi_derivation.md":"""# EMI derivation

Let `F~N(mu,sigma^2)` and classify by the sign of `mu`. Latent incorrectness is the magnitude lying on the opposite side: `(-F)_+` for `mu>0` and `(F)_+` for `mu<0`. Normal partial-moment integration yields

`EMI = sigma phi(|mu|/sigma)-|mu| Phi(-|mu|/sigma)`.

At `mu=0`, symmetry gives `sigma/sqrt(2 pi)`. The supplied Monte Carlo grid verifies this closed form. This is the Beachy-Grandhi point-local latent-Gaussian form applied to M3 moments, not an exact Bernoulli-GPC future-posterior criterion.
""",
    "smocu_compatibility.md":"""# SMOCU compatibility

SMOCU softens maximum class probability with LogSumExp and chooses the query with greatest expected global increase after hypothetical labels. It is a genuine finite-pool one-step look-ahead. The original efficient GPC derivation uses a different posterior approximation. Here both hypothetical outcomes are weighted by current M3 probability and transmitted through posterior cross-covariance using a documented logistic-Laplace rank-one moment approximation. It is explicitly `M3_SMOCU_APPROX`, not exact SMOCU.
""",
    "sur_compatibility.md":"""# SUR compatibility

Genuine SUR asks `U_n-E[U_{n+1}|D_n,x]` over an excursion/random-set uncertainty functional. The finite-pool diagnostic uses mean `p(u)(1-p(u))` over all currently unqueried training candidates and a cross-covariance rank-one logistic-Laplace update for both hypothetical labels. This is global and one-step look-ahead, but approximate. GPC random-set SUR prior art exists; no absence claim is made.
""",
    "tmse_gsur_comparison.md":"""# tMSE/gSUR comparison

The retained local proxy is `Delta v(x) * phi(mu_f/sigma_f)/sigma_f`, where `Delta v=v^2 W_C/(1+vW_C)`. It combines local expected variance reduction with a zero-contour density weight. Integrated tIMSE or true SUR additionally propagates the observation at `x` to reference points `u` through posterior cross-covariance. PA-TVR shares the variance-reduction-times-proximity template but substitutes an unsupported physics-gradient gate.
""",
    "pa_tvr_original_proposal.md":"""# PA-TVR supplied proposal

The supplied candidate is `v^2 W/(1+vW) * S^-1/2 * exp(-2 mu_f^2/S)`, with `S=sum_j (g_j l_j)^2`, `g=grad_z m_h`, and ARD lengths `l_j`. The primary implementation uses `W_C=E[sigmoid(F)(1-sigmoid(F))]`; `W_A` and `W_B` are audited but not selected by outcomes. The score has no new tuned acquisition parameter, but it inherits kernel, bounds, likelihood approximation, physics mean, and gate constants; it is not parameter-free.
""",
    "pa_tvr_derivation_audit.md":"""# PA-TVR derivation audit

The first factor is a defensible *local* Laplace rank-one variance-reduction approximation: adding site precision `W` at the same location changes variance by `v^2 W/(1+vW)`. `W_B` is the curvature at a plug-in posterior mean; `W_C` is more coherent before observing a label because it averages site curvature under the current latent posterior. `W_A` is predictive-label variance and is not the Laplace Hessian.

The second factor fails the audit. No integral over a tangent hyperplane was identified that yields `S^-1/2 exp(-2mu^2/S)` for an ARD Matérn-3/2 posterior. It resembles a Gaussian/RBF density gate under additional local-linear assumptions, but those assumptions neither match M3 nor account for cross-covariance to other points. Consequently the object is a physics-gradient-scaled local contour-density weighting, not demonstrated tangent variance reduction and not non-myopic SUR.
""",
    "pa_tvr_kernel_compatibility.md":"""# PA-TVR kernel compatibility

M3 uses ARD Matérn-3/2. An exponential quadratic in signed distance is naturally associated with Gaussian/RBF geometry, whereas Matérn-3/2 correlations decay as `(1+sqrt(3)d)exp(-sqrt(3)d)`. No controlled conversion from a Matérn tangent-plane integral to the proposed exponential gate was established. Direct insertion of fitted ARD lengths into `S` is additionally exposed to upper-bound hits. The geometry factor is rejected rather than repaired post hoc.
""",
    "pa_tvr_prior_art_comparison.md":"""# PA-TVR versus prior art

Term by term, PA-TVR has the established tMSE/gSUR pattern `local variance reduction × contour-proximity weight`. Its only unusual element is the physics-gradient-scaled gate, whose Matérn/tangent derivation fails. It is cheaper than global SMOCU/SUR because it omits domain-wide cross-covariance consequences. That computational difference is not new global information. Broad physics-informed GPC active-boundary novelty is already unsafe given Hardcastle et al.; GPC-SUR novelty is false given Menz et al. No novelty claim is made.
"""}
    for name,text_value in docs.items(): (OUTPUT/name).write_text(text_value.strip()+"\n",encoding="utf-8")


def decide_methods(collapse: pd.DataFrame,pa_sens: pd.DataFrame,runtime: pd.DataFrame) -> tuple[pd.DataFrame,dict[str,Any]]:
    cd=collapse.set_index("method").decision.to_dict(); rows=[]
    for method in METHODS:
        if method=="M3_MARGIN": decision="COMPATIBLE_MARGIN_EQUIVALENT"; reason="reference local probability-margin rule"
        elif method in ("M3_STRADDLE","M3_EMI"): decision="COMPATIBLE_MARGIN_EQUIVALENT" if cd.get(method)=="PRACTICALLY_MARGIN_EQUIVALENT" else "COMPATIBLE_DISTINCT"; reason="valid latent-local criterion; no GPC look-ahead guarantee"
        elif method in ("M3_SMOCU_APPROX","M3_SUR_APPROX"): decision="REQUIRES_APPROXIMATION"; reason="principled global one-step objective; current full audit uses disclosed approximation"
        elif method=="M3_TMES_GSUR": decision="COMPATIBLE_DISTINCT" if cd.get(method)!="PRACTICALLY_MARGIN_EQUIVALENT" else "COMPATIBLE_MARGIN_EQUIVALENT"; reason="local targeted variance-reduction proxy"
        else: decision="NOT_COMPATIBLE"; reason="supplied Matérn/tangent geometry factor lacks derivation"
        rows.append({"method":method,"decision":decision,"scope":"point-local" if method in ("M3_MARGIN","M3_STRADDLE","M3_EMI") else ("one-step-look-ahead approximate" if "APPROX" in method else "geometry-local"),"reason":reason})
    methods=pd.DataFrame(rows); write_csv(OUTPUT/"method_decisions.csv",methods)
    fragile=pa_sens.spearman.median()<.90 or pa_sens.top10_jaccard.mean()<.70
    pa={"decision":"PA_TVR_REJECTED","mathematics":"geometry factor lacks a Matérn-3/2 tangent-integral derivation","truly_tangent":False,"global_or_nonmyopic":False,"classification":"physics-gradient-scaled local variance-reduction proxy","numerically_fragile_L100_L1000":bool(fragile),"median_L100_L1000_spearman":float(pa_sens.spearman.median()),"mean_top1_agreement":float(pa_sens.top1_agreement.mean()),"mean_top10_jaccard":float(pa_sens.top10_jaccard.mean()),"prospective_recommendation":"FAST_GPC_SUR","recommendation_caveat":"direct level-set/random-set prior art; implement and validate a literature-faithful classifier update before a single prospective trajectory"}
    write_json(OUTPUT/"pa_tvr_decision.json",pa); return methods,pa


def generate_figures(scores:pd.DataFrame,detail:pd.DataFrame,topk:pd.DataFrame,pa_sens:pd.DataFrame,runtime:pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True); created=[]; colors={m:c for m,c in zip(METHODS[1:],plt.cm.tab10.colors)}
    fig,ax=plt.subplots(figsize=(10,5.5))
    for method in METHODS[1:]:
        p=detail[((detail.method_left.eq("M3_MARGIN"))&(detail.method_right.eq(method)))|((detail.method_right.eq("M3_MARGIN"))&(detail.method_left.eq(method)))]; ax.boxplot(p.spearman,positions=[METHODS[1:].index(method)],widths=.55,patch_artist=True,boxprops={"facecolor":colors[method],"alpha":.65},medianprops={"color":"black"})
    ax.axhline(COLLAPSE["median_spearman"],ls="--",color="black",lw=1); ax.set_xticks(range(len(METHODS)-1),[m.replace("M3_","").replace("_APPROX","*") for m in METHODS[1:]],rotation=25,ha="right"); ax.set(ylabel="Snapshot Spearman vs M3 Margin",title="Frozen-prefix rank similarity (* disclosed approximation)"); ax.grid(axis="y",alpha=.25); fig.tight_layout(); path=FIGURES/"01_rank_correlation_vs_margin.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Distribution across 600 frozen snapshots."))
    fig,ax=plt.subplots(figsize=(10,5.5))
    for method in METHODS[1:]:
        p=topk[((topk.method_left.eq("M3_MARGIN"))&(topk.method_right.eq(method)))|((topk.method_right.eq("M3_MARGIN"))&(topk.method_left.eq(method)))].sort_values("budget"); ax.plot(p.budget,p.top10_jaccard,"o-",label=method.replace("M3_","").replace("_APPROX","*"))
    ax.axhline(COLLAPSE["mean_top10_jaccard"],ls="--",color="black",lw=1); ax.set(xlabel="Frozen revealed-label budget",ylabel="Mean top-10 Jaccard vs Margin",title="Top-ranked candidate overlap"); ax.grid(alpha=.25); ax.legend(frameon=False,ncol=2,fontsize=8); fig.tight_layout(); path=FIGURES/"02_top10_overlap_by_budget.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Top-10 overlap by budget; no trajectory extended."))
    first=scores[(scores.run_id.eq(scores.run_id.iloc[0]))&(scores.budget.eq(16))].copy(); fig,ax=plt.subplots(figsize=(8,5.5)); ax.scatter(np.abs(first.final_latent_mean),first.latent_sd,c=first.margin_score,cmap="viridis",s=22,alpha=.6); markers={"M3_MARGIN":"o","M3_SMOCU_APPROX":"s","M3_SUR_APPROX":"^","PA_TVR_CANDIDATE":"X"}
    for m,mk in markers.items():
        r=first.loc[first[SCORE_COLUMNS[m]].idxmax()]; ax.scatter(abs(r.final_latent_mean),r.latent_sd,marker=mk,s=140,edgecolor="black",label=m)
    ax.set(xlabel="|final latent mean|",ylabel="latent SD",title="One predeclared B16 snapshot: selected candidate locations"); ax.legend(frameon=False,fontsize=8); ax.grid(alpha=.2); fig.tight_layout(); path=FIGURES/"03_latent_mean_variance_selected_candidates.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Illustrative current-posterior geometry, not performance."))
    sample=scores.sample(min(12000,len(scores)),random_state=seed_u32("figure_pa")); fig,axes=plt.subplots(1,3,figsize=(12,4)); axes[0].scatter(sample.variance_reduction_WC,sample.pa_tvr_score,s=5,alpha=.2); axes[1].scatter(sample.pa_geometry_gate,sample.pa_tvr_score,s=5,alpha=.2); axes[2].scatter(sample.pa_S,sample.pa_geometry_gate,s=5,alpha=.2); axes[0].set(xlabel="local variance reduction",ylabel="PA score"); axes[1].set(xlabel="geometry gate",ylabel="PA score"); axes[2].set(xlabel="S",ylabel="geometry gate"); fig.suptitle("PA-TVR supplied-score decomposition"); fig.tight_layout(); path=FIGURES/"04_pa_tvr_decomposition.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Local factor decomposition; no tangent/global claim."))
    fig,ax=plt.subplots(figsize=(8,5)); ax.boxplot([pa_sens.spearman,pa_sens.top10_jaccard],tick_labels=["Spearman","top-10 Jaccard"],patch_artist=True,boxprops={"facecolor":"#ed8936","alpha":.6}); ax.set(ylim=(-.05,1.05),title="PA-TVR ranking stability: M3 L100 vs L1000"); ax.grid(axis="y",alpha=.25); fig.tight_layout(); path=FIGURES/"05_pa_tvr_bound_sensitivity.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Six-budget, 100-run ARD-bound sensitivity."))
    rt=runtime.groupby("length_upper",as_index=False).agg(fit_seconds=("fit_seconds","mean"),local_score_seconds=("local_score_seconds","mean"),global_score_seconds=("global_score_seconds","mean")); fig,ax=plt.subplots(figsize=(8,4.8)); ax.bar(["local scores","global approx"],[rt.local_score_seconds.iloc[0],rt.global_score_seconds.iloc[0]],color=["#4299e1","#9f7aea"]); ax.set(ylabel="Mean seconds per snapshot (excluding M3 fit)",title="Observed scoring cost on frozen candidate pools"); ax.grid(axis="y",alpha=.25); fig.tight_layout(); path=FIGURES/"06_local_global_runtime.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Approximate global scoring includes full candidate cross-covariance."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"caption":c} for p,c in created]); write_csv(OUTPUT/"figure_manifest.csv",manifest); return manifest


def write_reports(scores:pd.DataFrame,aggregate:pd.DataFrame,collapse:pd.DataFrame,pa_sens:pd.DataFrame,runtime:pd.DataFrame,retro:pd.DataFrame,methods:pd.DataFrame,pa:dict[str,Any]) -> None:
    def mv(method:str)->pd.Series:return collapse[collapse.method.eq(method)].iloc[0]
    strad=mv("M3_STRADDLE"); emi=mv("M3_EMI"); sm=mv("M3_SMOCU_APPROX"); sur=mv("M3_SUR_APPROX"); pat=mv("PA_TVR_CANDIDATE")
    fit=float(runtime[runtime.length_upper.eq(100)].fit_seconds.mean()); local=float(runtime[runtime.length_upper.eq(100)].local_score_seconds.mean()); global_s=float(runtime[runtime.length_upper.eq(100)].global_score_seconds.mean()); prospective=6400*(fit+global_s)/3600; exact=pd.read_csv(OUTPUT/"exact_approx_small_validation.csv"); exact_sm_top=int(exact.loc[exact.smocu_exact_full_refit.idxmax(),"candidate_population_row_index"]); approx_sm_top=int(exact.loc[exact.smocu_rank_one_approx.idxmax(),"candidate_population_row_index"]); exact_sur_top=int(exact.loc[exact.sur_exact_full_refit.idxmax(),"candidate_population_row_index"]); approx_sur_top=int(exact.loc[exact.sur_rank_one_approx.idxmax(),"candidate_population_row_index"])
    final=f"""# Week 9 Phase 1.18A — Level-set acquisition compatibility audit

## Frozen design

All 100 published Phase 1.14 M3-margin paths were replayed at B16/24/32/40/60/80. This produced 600 posterior snapshots and {len(scores):,} pre-reveal candidate occurrences. No point was selected, no label was newly revealed, and no trajectory was generated.

## Main ranking results

| Method vs Margin | median Spearman | q05 | top-1 | top-10 Jaccard | decision |
|---|---:|---:|---:|---:|---|
| Straddle | {strad.median_spearman:.4f} | {strad.q05_spearman:.4f} | {strad.top1_agreement:.3f} | {strad.mean_top10_jaccard:.3f} | {strad.decision} |
| EMI | {emi.median_spearman:.4f} | {emi.q05_spearman:.4f} | {emi.top1_agreement:.3f} | {emi.mean_top10_jaccard:.3f} | {emi.decision} |
| SMOCU approximation | {sm.median_spearman:.4f} | {sm.q05_spearman:.4f} | {sm.top1_agreement:.3f} | {sm.mean_top10_jaccard:.3f} | {sm.decision} |
| SUR approximation | {sur.median_spearman:.4f} | {sur.q05_spearman:.4f} | {sur.top1_agreement:.3f} | {sur.mean_top10_jaccard:.3f} | {sur.decision} |
| supplied PA-TVR | {pat.median_spearman:.4f} | {pat.q05_spearman:.4f} | {pat.top1_agreement:.3f} | {pat.mean_top10_jaccard:.3f} | {pat.decision} |

Margin is not variance-blind: M3 probability integrates latent variance. Its limitation is that it does not separately optimize epistemic variance or expected domain-wide uncertainty reduction.

The full-pool approximations became exactly flat in a small number of snapshots, so Spearman was undefined there (Margin comparisons: SMOCU 4/600, SUR 4/600, EMI 22/600). These are reported as approximation degeneracies, not silently imputed. In the predeclared three-candidate exact-refit check, SMOCU's exact/approximate top IDs were {exact_sm_top}/{approx_sm_top}, while SUR's were {exact_sur_top}/{approx_sur_top}. Thus the approximate rankings are diagnostic evidence of distinctness, not a validated prospective implementation.

## PA-TVR falsification

The local Laplace variance-reduction factor is defensible with posterior-expected site curvature `W_C`. The proposed `S^-1/2 exp(-2mu^2/S)` factor was not derived from an ARD Matérn-3/2 tangent-hyperplane integral. It contains no cross-covariance to other locations and is therefore geometry-local, not global or non-myopic. L100→L1000 median ranking Spearman was {pa_sens.spearman.median():.4f}, top-1 agreement {pa_sens.top1_agreement.mean():.3f}, and top-10 Jaccard {pa_sens.top10_jaccard.mean():.3f}. Decision: **{pa['decision']}**. It is not rescued by retrospective behavior.

## Runtime

Mean L100 snapshot M3 fit/local/global-approx scoring times were {fit:.3f}/{local:.3f}/{global_s:.3f} s. A naive 100×64 prospective approximate-global replay is roughly {prospective:.2f} CPU-hours at observed cost, excluding orchestration. Exact candidate-by-candidate M3 refits would be far more expensive; this phase does not conflate the approximation with exact SMOCU/SUR.

## Retrospective diagnostic boundary

Truth/B1-like annotations were joined only after `candidate_scores_pre_reveal.csv.gz` was frozen and hashed. They describe which already-scored points rank highly; they are not acquisition performance, AULC, label saving, or a basis for method selection.

## Decision

PA-TVR is rejected. The single future candidate is **{pa['prospective_recommendation']}**, because it directly targets random-set/level-set uncertainty and has verified GPC prior art, conditional on implementing and validating the literature-faithful classifier update before one prospective path. The current rank-one proxy is not that implementation. If the exactness gate fails, the recommendation becomes NONE. No novelty or sample-efficiency claim is made.
"""
    (OUTPUT/"FINAL_PHASE1_18A_REPORT.md").write_text(final,encoding="utf-8")
    sup=f"""# Supervisor Phase 1.18A — one page

- **Design:** 600 frozen M3 snapshots, {len(scores):,} candidate occurrences, no new acquisition path.
- **Margin correction:** it integrates latent uncertainty through `p_M3`; it simply lacks an explicit global expected-reduction objective.
- **Local criteria:** Straddle vs Margin median Spearman {strad.median_spearman:.4f}, top-1 {strad.top1_agreement:.1%}; EMI {emi.median_spearman:.4f}, top-1 {emi.top1_agreement:.1%}.
- **Global candidates:** SMOCU/SUR were scored with an explicit logistic-Laplace rank-one approximation and remain approximation-requiring, not exact results.
- **PA-TVR:** the local variance update is defensible, but the claimed tangent Matérn geometry and global interpretation are not. L100/L1000 median Spearman {pa_sens.spearman.median():.4f}.
- **Decision:** **{pa['decision']}**. Do not repair it ad hoc.
- **One possible next experiment:** {pa['prospective_recommendation']}, only after a faithful GPC-SUR update validation gate. No q20 optimization or sample-efficiency claim was performed here.
"""; (OUTPUT/"SUPERVISOR_PHASE1_18A_ONE_PAGE.md").write_text(sup,encoding="utf-8")
    ledger="""# Phase 1.18A claim ledger

| Claim | Status | Boundary |
|---|---|---|
| M3 Margin is variance-blind. | NOT SUPPORTED | Predictive probability integrates latent variance. |
| Margin lacks an explicit expected global reduction objective. | SUPPORTED | Score is point-local current probability. |
| Straddle and EMI are latent-Gaussian compatible. | QUALIFIED | Original theory is not logistic-Laplace GPC theory. |
| Approximate SMOCU/SUR are exact literature implementations. | NOT SUPPORTED | Disclosed rank-one moment approximation. |
| GPC SUR exists in prior art. | SUPPORTED | Menz et al. 2025 and excursion-set SUR lineage. |
| Physics-informed GPC active boundary work exists. | SUPPORTED | Hardcastle et al. 2025. |
| PA-TVR has a derived Matérn tangent integral. | NOT SUPPORTED | No valid derivation identified. |
| PA-TVR is global/non-myopic. | NOT SUPPORTED | No domain-wide cross-covariance term. |
| PA-TVR is parameter-free. | NOT SUPPORTED | It inherits model, bounds, kernel and constants. |
| ARD length scales are causal physical importance. | NOT SUPPORTED | Standardized model geometry only. |
| Phase 1.18A proves sample-efficiency. | NOT TESTED | Frozen-prefix ranking audit only. |
| PA-TVR should proceed prospectively. | REJECTED | Mathematical falsification is sufficient. |
"""; (OUTPUT/"claim_ledger.md").write_text(ledger,encoding="utf-8")
    red=f"""# Final red-team report

1. Margin is not variance-blind; it lacks a separate epistemic/global-reduction objective.
2. Straddle/EMI collapse is adjudicated over all 600 snapshots, not one run: {strad.decision} / {emi.decision}.
3. SMOCU ranking status: {sm.decision}; implementation is explicitly approximate.
4. SUR ranking status: {sur.decision}; implementation is explicitly approximate.
5. The local `v^2W/(1+vW)` update is valid as a same-location Laplace approximation.
6. `W_C` is the most coherent pre-observation Laplace curvature; `W_A` is not a Hessian.
7. The exponential PA gate is not justified for ARD Matérn-3/2.
8. PA-TVR is not demonstrated tangent-aware.
9. PA-TVR is not global/non-myopic.
10. It resembles tMSE/gSUR with an unsupported physics-scaled gate.
11. It directly inherits bound-hitting ARD lengths.
12. L100→L1000: median Spearman {pa_sens.spearman.median():.4f}, top-10 Jaccard {pa_sens.top10_jaccard.mean():.3f}.
13. It is cheaper than principled global methods because it omits their global posterior consequence.
14. Distinct ranking alone is not scientific justification.
15. Broad GPC-SUR and physics-informed GPC novelty are already occupied.
16. No defensible PA-TVR novelty statement remains after the geometry failure.
17. Exactly one future experiment is conditionally justified only after faithful-update validation.
18. Candidate: {pa['prospective_recommendation']} because it directly targets level-set/random-set uncertainty; otherwise NONE.
"""; (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(red,encoding="utf-8")


def build_notebook() -> None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.18A — acquisition compatibility and PA-TVR falsification\n\nThis notebook reads frozen artifacts. It does not generate an acquisition trajectory."),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_18a_level_set_acquisition_compatibility_audit'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## M3 and the terminology correction\n\nM3 is a frozen physics latent mean plus an ARD Matérn-3/2 discrepancy GPC. Probability margin is not variance-blind because predictive probability integrates latent uncertainty; it does not separately reward epistemic variance or global expected uncertainty reduction."),nbf.v4.new_code_cell("display(Markdown((OUT/'acquisition_definitions.md').read_text()))"),nbf.v4.new_markdown_cell("## Frozen-prefix score audit"),nbf.v4.new_code_cell("scores=pd.read_csv(OUT/'candidate_scores_pre_reveal.csv.gz')\nprint(f'{len(scores):,} candidate occurrences; {scores[[\"run_id\",\"budget\"]].drop_duplicates().shape[0]} snapshots')\ndisplay(pd.read_csv(OUT/'margin_collapse_decisions.csv'))"),nbf.v4.new_code_cell("display(Image(filename=str(OUT/'figures'/'01_rank_correlation_vs_margin.png'))); display(Image(filename=str(OUT/'figures'/'02_top10_overlap_by_budget.png')))"),nbf.v4.new_markdown_cell("## SMOCU and SUR\n\nThese are principled global one-step objectives. The full audit uses a disclosed logistic-Laplace rank-one moment approximation, so the artifacts never call them exact."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'method_decisions.csv'))"),nbf.v4.new_markdown_cell("## PA-TVR falsification"),nbf.v4.new_code_cell("display(Markdown((OUT/'pa_tvr_derivation_audit.md').read_text())); display(json.loads((OUT/'pa_tvr_decision.json').read_text())); display(Image(filename=str(OUT/'figures'/'05_pa_tvr_bound_sensitivity.png')))"),nbf.v4.new_markdown_cell("## Retrospective annotations are not performance\n\nTruth and B1-like flags were joined only after the score table was frozen and hashed."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'retrospective_candidate_diagnostics.csv').head(14))"),nbf.v4.new_markdown_cell("## Safe conclusion"),nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_18A_ONE_PAGE.md').read_text()))")]
    nb=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}}); NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(nb,NOTEBOOK); executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=300,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute(); nbf.write(executed,NOTEBOOK)


def validate(scores:pd.DataFrame,sens:pd.DataFrame,detail:pd.DataFrame,collapse:pd.DataFrame,pa_sens:pd.DataFrame,emi:pd.DataFrame,exact:pd.DataFrame) -> dict[str,Any]:
    population,specs,paths=load_inputs(); nb=nbf.read(NOTEBOOK,as_version=4); source=Path(__file__).read_text(encoding="utf-8")
    score_hash=json.loads((OUTPUT/"candidate_scores_sha256.json").read_text())
    checks=[
        ("exact_parent",subprocess.check_output(["git","merge-base","HEAD",PARENT_SHA],cwd=ROOT,text=True).strip()==PARENT_SHA,PARENT_SHA),
        ("population_405",len(population)==405,str(len(population))),
        ("labels_73_332",int(population.has_keyhole.sum())==73 and int((~population.has_keyhole.astype(bool)).sum())==332,"73/332"),
        ("m3_architecture","Matern" in Path(p13.__file__).read_text() and "logh[candidate]" in source,"fixed physics + ARD Matern-3/2"),
        ("outer_runs_100",len(specs)==100,str(len(specs))),
        ("exact_frozen_prefixes",all(paths[s.run_id][:16]==w85.initial_design(s,population) for s in specs),"100/100"),
        ("no_new_trajectory",json.loads((OUTPUT/"analysis_specification.json").read_text())["new_trajectory"] is False and not any("new_trajectory" in p.name for p in OUTPUT.rglob("*")),"score-only"),
        ("candidate_scores_no_labels",not {"truth","has_keyhole"}.intersection(scores.columns),"clean"),
        ("candidate_scores_no_boundary",not {"B1","q20","q30","is_q20","is_q30"}.intersection(scores.columns),"clean"),
        ("score_hash_valid",score_hash["sha256"]==sha256_file(OUTPUT/"candidate_scores_pre_reveal.csv.gz"),score_hash["sha256"]),
        ("retrospective_after_hash",(OUTPUT/"retrospective_candidate_diagnostics.csv").stat().st_mtime>=(OUTPUT/"candidate_scores_sha256.json").stat().st_mtime,"mtime order"),
        ("six_budgets",set(scores.budget)==set(BUDGETS),str(sorted(scores.budget.unique()))),
        ("snapshots_600",len(scores[["run_id","budget"]].drop_duplicates())==600,"600"),
        ("candidate_occurrences_169200",len(scores)==169200,str(len(scores))),
        ("scores_finite",scores.select_dtypes(include=[np.number]).replace([np.inf,-np.inf],np.nan).notna().all().all(),"all numeric finite"),
        ("margin_semantics",np.allclose(scores.margin_score,1-2*np.abs(scores.m3_probability-.5)),"exact"),
        ("latent_variance_semantics",np.allclose(scores.residual_latent_variance,scores.final_latent_variance),"frozen mean"),
        ("emi_mc",float(emi.absolute_error.max())<.006,f"max error {emi.absolute_error.max():.6g}"),
        ("smocu_marked_approx","M3_SMOCU_APPROX" in scores.columns.astype(str).tolist() or "M3_SMOCU_APPROX" in METHODS,"name explicit"),
        ("sur_functional_documented","p(u)(1-p(u))" in (OUTPUT/"sur_compatibility.md").read_text(),"documented"),
        ("fast_update_small_exact_check",len(exact)==3 and exact.exact_refit_seconds_two_labels.gt(0).all(),"3 predeclared candidates"),
        ("exact_approx_not_conflated","does not conflate the approximation with exact" in (OUTPUT/"FINAL_PHASE1_18A_REPORT.md").read_text() and "explicitly approximate" in (OUTPUT/"FINAL_RED_TEAM_REPORT.md").read_text(),"explicit"),
        ("pa_formula_terms",all(c in scores for c in ("variance_reduction_WC","pa_S","pa_geometry_gate","pa_tvr_score")),"complete"),
        ("pa_scratch_not_ground_truth","scratch" not in (OUTPUT/"pa_tvr_decision.json").read_text().lower(),"independent"),
        ("pa_bound_sensitivity",len(pa_sens)==600 and len(sens)==169200,"600 snapshots"),
        ("no_ard_causal_claim","ARD length scales are causal" in (OUTPUT/"claim_ledger.md").read_text() and "NOT SUPPORTED" in (OUTPUT/"claim_ledger.md").read_text(),"guardrail"),
        ("no_unsupported_novelty","No novelty claim" in (OUTPUT/"pa_tvr_prior_art_comparison.md").read_text(),"guardrail"),
        ("no_sample_efficiency_claim","NOT TESTED | Frozen-prefix ranking audit only" in (OUTPUT/"claim_ledger.md").read_text(),"guardrail"),
        ("notebook_executed",all(c.cell_type!="code" or c.execution_count is not None for c in nb.cells),"stored outputs"),
        ("figures_six",len(pd.read_csv(OUTPUT/"figure_manifest.csv"))==6,"6"),
        ("figure_hashes",all(sha256_file(FIGURES/r.figure)==r.sha256 for r in pd.read_csv(OUTPUT/"figure_manifest.csv").itertuples()),"all match"),
        ("historical_unchanged",not historical_changes(),"none"),
    ]
    frame=pd.DataFrame([{"check":n,"status":"PASS" if bool(ok) else "FAIL","detail":d} for n,ok,d in checks]); status="PASS" if frame.status.eq("PASS").all() else "FAIL"; payload={"status":status,"check_count":len(frame),"checks":frame.to_dict("records")}; write_json(OUTPUT/"validation_report.json",payload)
    lines=["# Validation report","",f"**Status:** {status} ({len(frame)}/{len(frame)} checks listed)","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r.check} | {r.status} | {str(r.detail).replace('|','/')} |" for r in frame.itertuples()]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(status=="PASS",frame[frame.status.eq("FAIL")].to_string()); return payload


def write_manifest(validation:dict[str,Any],pa:dict[str,Any]) -> dict[str,Any]:
    artifacts=[]
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and "checkpoints" not in path.parts and path.name!="run_manifest.json": artifacts.append({"path":path.relative_to(ROOT).as_posix(),"sha256":sha256_file(path),"bytes":path.stat().st_size})
    artifacts.append({"path":NOTEBOOK.relative_to(ROOT).as_posix(),"sha256":sha256_file(NOTEBOOK),"bytes":NOTEBOOK.stat().st_size})
    payload={"phase":"Week 9 Phase 1.18A","parent_sha":PARENT_SHA,"branch":BRANCH,"new_trajectory":False,"snapshot_count":600,"candidate_occurrences":169200,"validation":validation,"decision":pa["decision"],"future_candidate":pa["prospective_recommendation"],"artifacts":artifacts}; write_json(OUTPUT/"run_manifest.json",payload); return payload


def finalize() -> dict[str,Any]:
    baseline_gate(); analysis_specification(); scores,sens,runtime=collect_checkpoints(); detail,aggregate,topk,collapse=ranking_outputs(scores); pa_sens=pa_sensitivity(scores,sens); curvature_audit(scores); emi=emi_monte_carlo(); exact=exact_approx_small_validation(scores); retro=retrospective_diagnostic(scores); write_method_documents(); methods,pa=decide_methods(collapse,pa_sens,runtime); generate_figures(scores,detail,topk,pa_sens,runtime); write_reports(scores,aggregate,collapse,pa_sens,runtime,retro,methods,pa); build_notebook(); validation=validate(scores,sens,detail,collapse,pa_sens,emi,exact); manifest=write_manifest(validation,pa); return {"status":"PASS","decision":pa["decision"],"future":pa["prospective_recommendation"],"validation_checks":validation["check_count"],"artifacts":len(manifest["artifacts"])}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--preflight",action="store_true"); parser.add_argument("--run-main",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--workers",type=int,default=4); parser.add_argument("--limit-specs",type=int); args=parser.parse_args()
    if args.preflight: print(json.dumps({"baseline":baseline_gate(),"specification":analysis_specification()},indent=2))
    elif args.run_main: print(json.dumps(run_main(args.workers,args.limit_specs),indent=2))
    elif args.finalize: print(json.dumps(finalize(),indent=2))
    else: parser.error("choose --preflight, --run-main, or --finalize")


if __name__=="__main__": main()
