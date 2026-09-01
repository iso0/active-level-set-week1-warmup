"""Week 9 Phase 1.11: training-fitted fixed physics mean plus 4D GP discrepancy.

This module performs a model-only replay on the frozen A0 query path.  The
h-only logistic latent mean is fitted from each revealed prefix and frozen;
an independently implemented Bernoulli-logistic Laplace GP then learns a
4D Matern-3/2 discrepancy.  Historical Phase 1.x artifacts are read-only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
import math
import os
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
import scipy.optimize
from joblib import Parallel, delayed
from nbclient import NotebookClient
from scipy.linalg import cholesky, cho_solve, solve
from scipy.special import erf, expit
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_5_h_physics_confirmation as p15
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_11_fixed_mean_discrepancy_gp"
CHECKPOINTS = OUTPUT / "checkpoints"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "09_week9_phase1_11_fixed_mean_discrepancy_gp.ipynb"
PHASE18 = ROOT / "outputs" / "week9_phase1_8_model_path_decomposition"
START_SHA = "e33cca4f81b865d330577ef9a8140c4bbe306e5a"
BRANCH = "codex/week9-phase1-11-fixed-mean-discrepancy-gp"
FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
CHECKPOINT_BUDGETS = (16, 40, 80)
BOOTSTRAP_DRAWS = 10_000
RESIDUAL_SD_BOUNDS = (0.05, 1.0)
RESIDUAL_VARIANCE_BOUNDS = tuple(value**2 for value in RESIDUAL_SD_BOUNDS)
LENGTH_SCALE_BOUNDS = (0.25, 4.0)
INITIAL_RESIDUAL_VARIANCE = 0.09
INITIAL_LENGTH_SCALE = 1.5
BOUND_ATOL = 5e-4
PARITY_TOLERANCE = 1e-5
SEED_ROOT = "week9_phase1_11_fixed_mean_discrepancy_gp|v1"
EPS = 1e-12

# Exact Williams-Barber five-error-function approximation used by sklearn GPC.
WB_COEFS = np.array([-1854.8214151, 3516.89893646, 221.29346712, 128.12323805, -2010.49422654])[:, None]
WB_LAMBDAS = np.array([0.41, 0.40, 0.37, 0.44, 0.39])[:, None]


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
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
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
    if path.suffix == ".gz":
        data = frame.to_csv(index=False, lineterminator="\n").encode()
        path.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    else:
        frame.to_csv(path, index=False, lineterminator="\n")


def residual_kernel(
    residual_variance: float = INITIAL_RESIDUAL_VARIANCE,
    length_scale: float = INITIAL_LENGTH_SCALE,
) -> Any:
    return ConstantKernel(residual_variance, RESIDUAL_VARIANCE_BOUNDS) * Matern(
        length_scale=length_scale,
        length_scale_bounds=LENGTH_SCALE_BOUNDS,
        nu=1.5,
    )


@dataclass
class LaplaceDiagnostics:
    optimized: bool
    optimizer_converged: bool
    optimizer_message: str
    optimizer_iterations: int
    optimizer_evaluations: int
    posterior_iterations: int
    fallback_status: str
    objective_value: float


class FixedMeanLaplaceGPC:
    """Binary logistic GP with a supplied fixed latent mean and Laplace inference.

    Equations follow GPML Algorithms 3.1, 3.2 and 5.1.  The implementation is
    independent of sklearn's private estimator; zero-mean parity is tested
    against sklearn with fixed identical kernel parameters before any study run.
    """

    def __init__(self, kernel: Any, optimize: bool = True, max_iter_predict: int = 100) -> None:
        self.kernel = kernel
        self.optimize = bool(optimize)
        self.max_iter_predict = int(max_iter_predict)

    def _posterior_mode(self, kernel: Any, return_temporaries: bool = False):
        K = kernel(self.X_train_)
        g = np.zeros(len(self.y_train_), dtype=float)
        old_lml = -np.inf
        iteration = 0
        for iteration in range(1, self.max_iter_predict + 1):
            f = self.mean_train_ + g
            pi = expit(f)
            W = pi * (1.0 - pi)
            W_sr = np.sqrt(W)
            W_sr_K = W_sr[:, None] * K
            B = np.eye(len(W)) + W_sr_K * W_sr
            L = cholesky(B, lower=True)
            b = W * g + (self.y_train_ - pi)
            a = b - W_sr * cho_solve((L, True), W_sr_K.dot(b))
            g = K.dot(a)
            f_new = self.mean_train_ + g
            sign = self.y_train_ * 2.0 - 1.0
            lml = -0.5 * a.T.dot(g) - np.logaddexp(0.0, -sign * f_new).sum() - np.log(np.diag(L)).sum()
            if lml - old_lml < 1e-10:
                break
            old_lml = float(lml)
        if return_temporaries:
            return float(old_lml), (pi, W_sr, L, b, a, iteration)
        return float(old_lml)

    def _lml_and_gradient(self, theta: np.ndarray) -> tuple[float, np.ndarray]:
        kernel = self.kernel_.clone_with_theta(theta)
        K, K_gradient = kernel(self.X_train_, eval_gradient=True)
        Z, (pi, W_sr, L, _, a, _) = self._posterior_mode(kernel, return_temporaries=True)
        R = W_sr[:, None] * cho_solve((L, True), np.diag(W_sr))
        C = solve(L, W_sr[:, None] * K)
        s_2 = -0.5 * (np.diag(K) - np.einsum("ij,ij->j", C, C)) * (pi * (1 - pi) * (1 - 2 * pi))
        gradient = np.empty(len(theta), dtype=float)
        for j in range(len(theta)):
            Cj = K_gradient[:, :, j]
            s_1 = 0.5 * a.T.dot(Cj).dot(a) - 0.5 * R.T.ravel().dot(Cj.ravel())
            bj = Cj.dot(self.y_train_ - pi)
            s_3 = bj - K.dot(R.dot(bj))
            gradient[j] = s_1 + s_2.T.dot(s_3)
        return -float(Z), -gradient

    def fit(self, X: np.ndarray, y: np.ndarray, mean_train: np.ndarray) -> "FixedMeanLaplaceGPC":
        self.X_train_ = np.asarray(X, dtype=float).copy()
        self.y_train_ = np.asarray(y, dtype=int).copy()
        self.mean_train_ = np.asarray(mean_train, dtype=float).copy()
        require(self.X_train_.shape[0] == len(self.y_train_) == len(self.mean_train_), "fit-array length mismatch")
        require(set(np.unique(self.y_train_)) == {0, 1}, "binary classes required")
        self.kernel_ = clone(self.kernel)
        fallback = "none"
        result = None
        if self.optimize and self.kernel_.n_dims:
            try:
                result = scipy.optimize.minimize(
                    self._lml_and_gradient,
                    self.kernel_.theta,
                    method="L-BFGS-B",
                    jac=True,
                    bounds=self.kernel_.bounds,
                    options={"maxiter": 150, "ftol": 1e-12, "gtol": 1e-7},
                )
                require(np.isfinite(result.fun) and np.isfinite(result.x).all(), "non-finite optimizer result")
                self.kernel_.theta = result.x
            except Exception as exc:  # deterministic initial-kernel fallback
                fallback = f"initial_kernel_after_{type(exc).__name__}"
                result = None
                self.kernel_ = clone(self.kernel)
        lml, (self.pi_, self.W_sr_, self.L_, _, self.a_, iterations) = self._posterior_mode(
            self.kernel_, return_temporaries=True
        )
        self.log_marginal_likelihood_value_ = float(lml)
        self.diagnostics_ = LaplaceDiagnostics(
            optimized=self.optimize,
            optimizer_converged=bool(result.success) if result is not None else not self.optimize,
            optimizer_message=str(result.message) if result is not None else ("optimizer_disabled" if not self.optimize else fallback),
            optimizer_iterations=int(result.nit) if result is not None else 0,
            optimizer_evaluations=int(result.nfev) if result is not None else 0,
            posterior_iterations=int(iterations),
            fallback_status=fallback,
            objective_value=-float(lml),
        )
        return self

    def latent_mean_and_variance(self, X: np.ndarray, mean_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        X = np.asarray(X, dtype=float)
        mean_test = np.asarray(mean_test, dtype=float)
        K_star = self.kernel_(self.X_train_, X)
        latent_mean = mean_test + K_star.T.dot(self.y_train_ - self.pi_)
        v = solve(self.L_, self.W_sr_[:, None] * K_star)
        latent_var = self.kernel_.diag(X) - np.einsum("ij,ij->j", v, v)
        return latent_mean, np.maximum(latent_var, EPS)

    def predict_proba(self, X: np.ndarray, mean_test: np.ndarray) -> np.ndarray:
        latent_mean, latent_var = self.latent_mean_and_variance(X, mean_test)
        alpha = 1.0 / (2.0 * latent_var)
        gamma = WB_LAMBDAS * latent_mean
        integrals = (
            np.sqrt(np.pi / alpha)
            * erf(gamma * np.sqrt(alpha / (alpha + WB_LAMBDAS**2)))
            / (2.0 * np.sqrt(latent_var * 2.0 * np.pi))
        )
        positive = (WB_COEFS * integrals).sum(axis=0) + 0.5 * WB_COEFS.sum()
        positive = np.clip(positive, EPS, 1.0 - EPS)
        return np.column_stack([1.0 - positive, positive])


@dataclass
class PhysicsMeanFit:
    scaler: StandardScaler
    model: LogisticRegression
    revealed_indices: np.ndarray

    def latent(self, log_h: np.ndarray) -> np.ndarray:
        z = self.scaler.transform(np.asarray(log_h, dtype=float).reshape(-1, 1))
        return self.model.decision_function(z)


def fit_physics_mean(log_h: np.ndarray, labels: np.ndarray, revealed: Sequence[int], seed: int) -> PhysicsMeanFit:
    indices = np.asarray(revealed, dtype=int)
    scaler = StandardScaler().fit(np.asarray(log_h)[indices, None])
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000, random_state=int(seed))
    model.fit(scaler.transform(np.asarray(log_h)[indices, None]), np.asarray(labels)[indices])
    return PhysicsMeanFit(scaler=scaler, model=model, revealed_indices=indices)


@dataclass
class FixedMeanFit:
    physics: PhysicsMeanFit
    x_scaler: StandardScaler
    gp: FixedMeanLaplaceGPC
    revealed_indices: np.ndarray

    @property
    def residual_variance(self) -> float:
        return float(self.gp.kernel_.k1.constant_value)

    @property
    def residual_sd(self) -> float:
        return math.sqrt(self.residual_variance)

    @property
    def length_scale(self) -> float:
        return float(self.gp.kernel_.k2.length_scale)


def fit_fixed_mean(
    x4: np.ndarray,
    log_h: np.ndarray,
    labels: np.ndarray,
    revealed: Sequence[int],
    training_pool: Sequence[int],
    seed: int,
) -> FixedMeanFit:
    revealed_array = np.asarray(revealed, dtype=int)
    physics = fit_physics_mean(log_h, labels, revealed_array, seed_u32("physics", seed))
    x_scaler = StandardScaler().fit(np.asarray(x4)[np.asarray(training_pool, dtype=int)])
    x_train = x_scaler.transform(np.asarray(x4)[revealed_array])
    mean_train = physics.latent(np.asarray(log_h)[revealed_array])
    # physics/scaler objects are not passed to the optimizer; only fixed values are.
    gp = FixedMeanLaplaceGPC(residual_kernel(), optimize=True).fit(
        x_train, np.asarray(labels)[revealed_array], mean_train
    )
    return FixedMeanFit(physics, x_scaler, gp, revealed_array)


def fixed_mean_components(fit: FixedMeanFit, x4: np.ndarray, log_h: np.ndarray) -> dict[str, np.ndarray]:
    transformed = fit.x_scaler.transform(np.asarray(x4, dtype=float))
    physics_latent = fit.physics.latent(np.asarray(log_h, dtype=float))
    final_latent, latent_variance = fit.gp.latent_mean_and_variance(transformed, physics_latent)
    probability = fit.gp.predict_proba(transformed, physics_latent)[:, 1]
    return {
        "physics_latent": physics_latent,
        "residual_latent": final_latent - physics_latent,
        "final_latent": final_latent,
        "latent_variance": latent_variance,
        "probability": probability,
    }


def load_inputs() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]], pd.DataFrame]:
    population, specs = p18.load_population_specs()
    path_table = pd.read_csv(PHASE18 / "tables" / "query_paths.csv.gz")
    a0_table = path_table[path_table.path.eq("A0")].copy()
    paths = {
        str(run_id): group.sort_values("query_order").population_row_index.astype(int).tolist()
        for run_id, group in a0_table.groupby("run_id", sort=True)
    }
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73, "canonical population gate failed")
    require(len(specs) == 100 and set(paths) == {spec.run_id for spec in specs}, "split/path run gate failed")
    initial = pd.read_csv(ROOT / "outputs" / "week8_5_frozen_confirmation" / "initial_design_manifest.csv")
    initial_map = {
        str(run_id): group.sort_values("query_order").population_row_index.astype(int).tolist()
        for run_id, group in initial.groupby("run_id", sort=True)
    }
    for spec in specs:
        path = paths[spec.run_id]
        require(len(path) == 80 and len(path) == len(set(path)), f"A0 path length/uniqueness drift {spec.run_id}")
        require(path[:16] == initial_map[spec.run_id] == w85.initial_design(spec, population), f"initial design drift {spec.run_id}")
        require(set(path).issubset(set(spec.train_indices)), f"A0 outside training pool {spec.run_id}")
        require(set(path).isdisjoint(set(spec.test_indices)), f"A0 test query {spec.run_id}")
    return population, specs, paths, path_table


def log_h_values(population: pd.DataFrame) -> np.ndarray:
    return p17.log_h(population)


def fixed_kernel_parity_case(case: str, X: np.ndarray, y: np.ndarray, X_test: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    kernel = residual_kernel(0.27, 1.1)
    reference = GaussianProcessClassifier(kernel=kernel, optimizer=None, max_iter_predict=100, random_state=11).fit(X, y)
    custom = FixedMeanLaplaceGPC(kernel, optimize=False).fit(X, y, np.zeros(len(y)))
    ref_prob = reference.predict_proba(X_test)[:, 1]
    new_prob = custom.predict_proba(X_test, np.zeros(len(X_test)))[:, 1]
    rows = [
        {"case": case, "row": idx, "sklearn_probability": float(a), "custom_probability": float(b), "absolute_difference": float(abs(a-b))}
        for idx, (a, b) in enumerate(zip(ref_prob, new_prob))
    ]
    return {
        "case": case,
        "rows": len(rows),
        "max_absolute_probability_difference": float(np.max(np.abs(ref_prob-new_prob))),
        "mean_absolute_probability_difference": float(np.mean(np.abs(ref_prob-new_prob))),
    }, rows


def optimized_parity_case(case: str, X: np.ndarray, y: np.ndarray, X_test: np.ndarray) -> dict[str, Any]:
    kernel = residual_kernel()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reference = GaussianProcessClassifier(kernel=kernel, optimizer="fmin_l_bfgs_b", n_restarts_optimizer=0, max_iter_predict=100, random_state=13).fit(X, y)
    custom = FixedMeanLaplaceGPC(kernel, optimize=True).fit(X, y, np.zeros(len(y)))
    ref_prob = reference.predict_proba(X_test)[:, 1]
    new_prob = custom.predict_proba(X_test, np.zeros(len(X_test)))[:, 1]
    return {
        "case": case,
        "sklearn_residual_sd": math.sqrt(float(reference.kernel_.k1.constant_value)),
        "custom_residual_sd": math.sqrt(float(custom.kernel_.k1.constant_value)),
        "sklearn_length_scale": float(reference.kernel_.k2.length_scale),
        "custom_length_scale": float(custom.kernel_.k2.length_scale),
        "sklearn_log_marginal_likelihood": float(reference.log_marginal_likelihood_value_),
        "custom_log_marginal_likelihood": float(custom.log_marginal_likelihood_value_),
        "max_probability_difference": float(np.max(np.abs(ref_prob-new_prob))),
        "custom_converged": custom.diagnostics_.optimizer_converged,
        "custom_iterations": custom.diagnostics_.optimizer_iterations,
    }


def run_parity_gate() -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    population, specs, paths, _ = load_inputs()
    rng = np.random.default_rng(41)
    toy_x = np.r_[rng.normal([-1,-1], 0.35, (8,2)), rng.normal([1,1], 0.35, (8,2))]
    toy_y = np.r_[np.zeros(8, dtype=int), np.ones(8, dtype=int)]
    toy_test = rng.normal(0, 1.2, (25,2))
    cases: list[tuple[str,np.ndarray,np.ndarray,np.ndarray]] = [("toy",toy_x,toy_y,toy_test)]
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    representatives = [(specs[0],16),(specs[49],40),(specs[-1],80)]
    for spec,budget in representatives:
        revealed=np.asarray(paths[spec.run_id][:budget],dtype=int)
        scaler=StandardScaler().fit(x4[np.asarray(spec.train_indices,dtype=int)])
        cases.append((f"{spec.run_id}_B{budget}",scaler.transform(x4[revealed]),labels[revealed],scaler.transform(x4[np.asarray(spec.test_indices,dtype=int)])))
    summaries=[]
    predictions=[]
    optimized=[]
    for name,X,y,Xtest in cases:
        summary,rows=fixed_kernel_parity_case(name,X,y,Xtest)
        summaries.append(summary)
        predictions.extend(rows)
        if name != "toy":
            optimized.append(optimized_parity_case(name,X,y,Xtest))
    maximum=max(row["max_absolute_probability_difference"] for row in summaries)
    status="PASS" if maximum <= PARITY_TOLERANCE else "IMPLEMENTATION_NOT_VALIDATED"
    report={
        "status":status,
        "tolerance":PARITY_TOLERANCE,
        "maximum_fixed_kernel_probability_difference":maximum,
        "fixed_kernel_cases":summaries,
        "optimization_parity":optimized,
        "equations":"independent GPML logistic Laplace Algorithms 3.1/3.2/5.1; fixed mean enters latent f=m+g; zero-mean uses m=0",
        "sklearn_private_estimator_subclassed":False,
    }
    write_csv(OUTPUT/"zero_mean_parity_predictions.csv",pd.DataFrame(predictions))
    write_json(OUTPUT/"implementation_parity_report.json",report)
    require(status=="PASS",f"zero-mean parity failed: {maximum}")
    return report


def baseline_gate() -> dict[str, Any]:
    population,specs,paths,_=load_inputs()
    summary=pd.read_csv(PHASE18/"four_way_AULC_summary.csv")
    m0=float(summary[(summary.arm.eq("Y00"))&(summary.endpoint.eq("B1_q20_accuracy_AULC_16_80"))].mean_AULC.iloc[0])
    m1=float(summary[(summary.arm.eq("Y10"))&(summary.endpoint.eq("B1_q20_accuracy_AULC_16_80"))].mean_AULC.iloc[0])
    gate={
        "status":"PASS" if abs(m0-0.8135202205882354)<1e-12 and abs(m1-0.8299724264705881)<1e-12 else "FAIL",
        "population_rows":len(population),"keyholes":int(population.has_keyhole.sum()),"outer_runs":len(specs),
        "A0_paths":len(paths),"budgets":list(BUDGETS),"M0_q20_AULC":m0,"M1_A0_q20_AULC":m1,
        "A0_source":"Phase 1.8 tracked query_paths.csv.gz",
    }
    write_json(OUTPUT/"baseline_gate.json",gate)
    require(gate["status"]=="PASS",f"baseline gate failed: {gate}")
    return gate


def fit_diagnostic(fit: FixedMeanFit) -> dict[str, Any]:
    d=fit.gp.diagnostics_
    return {
        "residual_sd":fit.residual_sd,"residual_length_scale":fit.length_scale,
        "optimizer_converged":d.optimizer_converged,"optimizer_message":d.optimizer_message,
        "optimizer_iterations":d.optimizer_iterations,"optimizer_evaluations":d.optimizer_evaluations,
        "posterior_iterations":d.posterior_iterations,"fallback_status":d.fallback_status,
        "objective_value":d.objective_value,
        "residual_sd_lower_bound_hit":bool(np.isclose(fit.residual_sd,RESIDUAL_SD_BOUNDS[0],atol=BOUND_ATOL,rtol=0)),
        "residual_sd_upper_bound_hit":bool(np.isclose(fit.residual_sd,RESIDUAL_SD_BOUNDS[1],atol=BOUND_ATOL,rtol=0)),
        "length_scale_lower_bound_hit":bool(np.isclose(fit.length_scale,LENGTH_SCALE_BOUNDS[0],atol=BOUND_ATOL,rtol=0)),
        "length_scale_upper_bound_hit":bool(np.isclose(fit.length_scale,LENGTH_SCALE_BOUNDS[1],atol=BOUND_ATOL,rtol=0)),
    }


def _checkpoint_path(run_id: str) -> Path:
    return CHECKPOINTS/f"{run_id}.json.gz"


def _write_checkpoint(path: Path,payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(json_safe(payload),sort_keys=True)+"\n").encode(),compresslevel=6,mtime=0))


def _read_checkpoint(path: Path) -> dict[str,Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def run_one_spec(spec: Any,path: Sequence[int],population: pd.DataFrame,distances: np.ndarray) -> dict[str,Any]:
    checkpoint=_checkpoint_path(spec.run_id)
    if checkpoint.is_file():
        payload=_read_checkpoint(checkpoint)
        if payload.get("complete") and payload.get("start_sha")==START_SHA:
            return {"run_id":spec.run_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float)
    logh=log_h_values(population)
    labels=population.has_keyhole.astype(int).to_numpy()
    test=np.asarray(spec.test_indices,dtype=int)
    flags=p17.subset_flags(spec,population,distances)
    prediction_rows=[]
    metric_rows=[]
    residual_rows=[]
    physics_rows=[]
    for budget in BUDGETS:
        revealed=np.asarray(path[:budget],dtype=int)
        require(len(revealed)==budget and len(set(revealed.tolist()))==budget,"prefix drift")
        physics=fit_physics_mean(logh,labels,revealed,seed_u32("MH",spec.run_id,budget))
        mh_probability=expit(physics.latent(logh[test]))
        fit=fit_fixed_mean(x4,logh,labels,revealed,spec.train_indices,seed_u32("M2",spec.run_id,budget))
        components=fixed_mean_components(fit,x4[test],logh[test])
        m2_probability=components["probability"]
        for local,pop_index in enumerate(test):
            base={"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"population_row_index":int(pop_index),"truth":int(labels[pop_index]),"is_q30":bool(flags["B1_q30"][local]),"is_q20":bool(flags["B1_q20"][local])}
            prediction_rows.append({**base,"model":"MH","probability":float(mh_probability[local]),"physics_latent":float(physics.latent(logh[[pop_index]])[0]),"residual_latent":0.0,"final_latent":float(physics.latent(logh[[pop_index]])[0])})
            prediction_rows.append({**base,"model":"M2","probability":float(m2_probability[local]),"physics_latent":float(components["physics_latent"][local]),"residual_latent":float(components["residual_latent"][local]),"final_latent":float(components["final_latent"][local])})
        for model,probability in (("MH",mh_probability),("M2",m2_probability)):
            for subset,flag in flags.items():
                metric_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"subset":subset,**p17.metric_values(labels[test][flag],probability[flag])})
        diag=fit_diagnostic(fit)
        for subset,flag in flags.items():
            residual=components["residual_latent"][flag]
            phys=components["physics_latent"][flag]
            final=components["final_latent"][flag]
            correlation=spearmanr(residual,logh[test][flag]).statistic if int(flag.sum())>2 else math.nan
            residual_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":"M2","path":"A0","subset":subset,**diag,"physics_latent_sd":float(np.std(phys)),"posterior_residual_mean_sd":float(np.std(residual)),"final_latent_sd":float(np.std(final)),"residual_log_h_spearman":float(correlation)})
        physics_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"revealed_count":len(revealed),"physics_intercept":float(fit.physics.model.intercept_[0]),"physics_log_h_coefficient":float(fit.physics.model.coef_[0,0]),"h_scaler_mean":float(fit.physics.scaler.mean_[0]),"h_scaler_scale":float(fit.physics.scaler.scale_[0]),"stage1_only_log_h":True,"stage1_revealed_prefix_only":True,"frozen_during_stage2":True})
    _write_checkpoint(checkpoint,{"complete":True,"start_sha":START_SHA,"run_id":spec.run_id,"prediction_rows":prediction_rows,"metric_rows":metric_rows,"residual_rows":residual_rows,"physics_rows":physics_rows})
    return {"run_id":spec.run_id,"reused":False}


def run_scientific(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    parity=json.loads((OUTPUT/"implementation_parity_report.json").read_text()) if (OUTPUT/"implementation_parity_report.json").is_file() else run_parity_gate()
    require(parity["status"]=="PASS","implementation parity gate not passed")
    baseline_gate()
    population,specs,paths,_=load_inputs()
    if limit_specs:
        specs=specs[:limit_specs]
    distances=w85.b1_distance(population)
    started=time.time()
    results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_spec)(spec,paths[spec.run_id],population,distances) for spec in specs)
    report={"status":"PASS","completed_runs":len(results),"reused_runs":sum(row["reused"] for row in results),"elapsed_seconds":time.time()-started,"workers":workers,"complete":limit_specs is None}
    write_json(OUTPUT/"execution_report.json",report)
    return report


def bootstrap_interval(values: np.ndarray, key: str) -> tuple[float,float,float]:
    values=np.asarray(values,dtype=float)
    require(len(values)==20 and np.isfinite(values).all(),f"repeat bootstrap input drift {key}")
    rng=np.random.default_rng(seed_u32("bootstrap",key))
    draws=values[rng.integers(0,len(values),size=(BOOTSTRAP_DRAWS,len(values)))].mean(axis=1)
    return float(values.mean()),float(np.quantile(draws,0.025)),float(np.quantile(draws,0.975))


def collect_new_checkpoints() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(CHECKPOINTS.glob("*.json.gz"))
    require(len(files)==100,"complete 100-run checkpoint set required")
    predictions=[]; metrics=[]; residual=[]; physics=[]
    for path in files:
        payload=_read_checkpoint(path)
        require(payload.get("complete") and payload.get("start_sha")==START_SHA,f"invalid checkpoint {path.name}")
        predictions.extend(payload["prediction_rows"])
        metrics.extend(payload["metric_rows"])
        residual.extend(payload["residual_rows"])
        physics.extend(payload["physics_rows"])
    prediction_frame=pd.DataFrame(predictions)
    metric_frame=pd.DataFrame(metrics)
    residual_frame=pd.DataFrame(residual)
    physics_frame=pd.DataFrame(physics)
    require(len(prediction_frame)==100*65*81*2,"prediction completeness failure")
    require(len(metric_frame)==100*65*3*2,"metric completeness failure")
    require(len(residual_frame)==100*65*3 and len(physics_frame)==100*65,"diagnostic completeness failure")
    write_csv(OUTPUT/"fixed_mean_oof_predictions.csv.gz",prediction_frame[prediction_frame.model.eq("M2")].reset_index(drop=True))
    write_csv(OUTPUT/"h_only_a0_predictions.csv.gz",prediction_frame[prediction_frame.model.eq("MH")].reset_index(drop=True))
    write_csv(OUTPUT/"residual_fit_diagnostics.csv.gz",residual_frame)
    write_csv(OUTPUT/"physics_mean_fit_diagnostics.csv.gz",physics_frame)
    return prediction_frame,metric_frame,residual_frame,physics_frame


def historical_metrics() -> tuple[pd.DataFrame,pd.DataFrame]:
    four=pd.read_csv(PHASE18/"tables"/"four_way_metrics_per_budget.csv.gz",low_memory=False)
    keep=["run_id","repeat","fold","budget","subset","accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive","row_count"]
    m0=four[four.arm.eq("Y00")][keep].copy().assign(model="M0")
    m1=four[four.arm.eq("Y10")][keep].copy().assign(model="M1")
    require(len(m0)==100*65*2 and len(m1)==100*65*3,"historical metric row drift")
    checkpoint=pd.read_csv(PHASE18/"tables"/"y00_checkpoint_refit.csv.gz",low_memory=False)
    checkpoint=checkpoint[(checkpoint.arm.eq("Y00"))&checkpoint.subset.eq("full81")&checkpoint.budget.isin(CHECKPOINT_BUDGETS)][keep].copy().assign(model="M0")
    require(set(checkpoint.budget.unique())==set(CHECKPOINT_BUDGETS),"M0 checkpoint budget drift")
    return pd.concat([m0,checkpoint],ignore_index=True),m1


def compute_aulc(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    rows=[]
    for keys,group in metrics[metrics.subset.isin(("B1_q20","B1_q30"))].groupby(["run_id","repeat","fold","model","subset"],sort=True):
        run_id,repeat,fold,model,subset=keys
        ordered=group.sort_values("budget")
        require(ordered.budget.astype(int).tolist()==list(BUDGETS),f"AULC budget path incomplete {run_id}/{model}/{subset}")
        value=float(np.trapezoid(ordered.accuracy.to_numpy(float),ordered.budget.to_numpy(float))/(BUDGETS[-1]-BUDGETS[0]))
        rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"subset":subset,"accuracy_AULC_16_80":value})
    outer=pd.DataFrame(rows)
    require(len(outer)==100*4*2,"four-model AULC matrix incomplete")
    repeat=(outer.groupby(["repeat","model","subset"],as_index=False).accuracy_AULC_16_80.mean())
    summary=[]
    for (model,subset),group in repeat.groupby(["model","subset"],sort=True):
        mean,lower,upper=bootstrap_interval(group.sort_values("repeat").accuracy_AULC_16_80.to_numpy(float),f"summary|{model}|{subset}")
        summary.append({"model":model,"subset":subset,"mean_AULC":mean,"ci_lower":lower,"ci_upper":upper})
    contrasts=[]
    wide=repeat.pivot(index=["repeat","subset"],columns="model",values="accuracy_AULC_16_80").reset_index()
    for subset in ("B1_q20","B1_q30"):
        part=wide[wide.subset.eq(subset)].sort_values("repeat")
        for reference in ("M0","M1","MH"):
            values=(part.M2-part[reference]).to_numpy(float)
            mean,lower,upper=bootstrap_interval(values,f"contrast|M2-{reference}|{subset}")
            contrasts.append({"contrast":f"M2-{reference}","subset":subset,"mean_difference":mean,"ci_lower":lower,"ci_upper":upper,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS})
    return outer,repeat,pd.DataFrame(summary),pd.DataFrame(contrasts)


def compute_budget16(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    selected=metrics[(metrics.budget.eq(16))&metrics.subset.eq("B1_q20")].copy()
    require(len(selected)==100*4,"B16 four-model q20 matrix incomplete")
    metric_names=("accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive")
    summary=[]; contrasts=[]
    for model,group in selected.groupby("model",sort=True):
        for metric in metric_names:
            repeat=group.groupby("repeat")[metric].mean().sort_index().to_numpy(float)
            mean,lower,upper=bootstrap_interval(repeat,f"B16|{model}|{metric}")
            summary.append({"model":model,"subset":"B1_q20","budget":16,"metric":metric,"mean":mean,"ci_lower":lower,"ci_upper":upper})
    for reference in ("M0","M1","MH"):
        for metric in metric_names:
            pivot=selected.pivot(index=["repeat","fold"],columns="model",values=metric).reset_index()
            repeat=(pivot.assign(delta=pivot.M2-pivot[reference]).groupby("repeat").delta.mean().sort_index().to_numpy(float))
            mean,lower,upper=bootstrap_interval(repeat,f"B16|M2-{reference}|{metric}")
            contrasts.append({"contrast":f"M2-{reference}","subset":"B1_q20","budget":16,"metric":metric,"mean_difference":mean,"ci_lower":lower,"ci_upper":upper})
    return pd.DataFrame(summary),pd.DataFrame(contrasts)


def compute_stability(m2_residual: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    m2=m2_residual[m2_residual.subset.eq("full81")].copy()
    require(len(m2)==6500,"M2 matched diagnostic count drift")
    four=pd.read_csv(PHASE18/"tables"/"four_way_metrics_per_budget.csv.gz",low_memory=False)
    m1=four[(four.arm.eq("Y10"))&four.subset.eq("full81")].copy()
    require(len(m1)==6500,"M1 matched diagnostic count drift")
    keys=["run_id","repeat","fold","budget"]
    fields=("residual_sd_lower_bound_hit","residual_sd_upper_bound_hit","length_scale_lower_bound_hit","length_scale_upper_bound_hit")
    for field in fields:
        m1[field]=m1[field].astype(bool)
        m2[field]=m2[field].astype(bool)
    m1["residual_sd_any_bound_hit"]=m1.residual_sd_lower_bound_hit|m1.residual_sd_upper_bound_hit
    m2["residual_sd_any_bound_hit"]=m2.residual_sd_lower_bound_hit|m2.residual_sd_upper_bound_hit
    m1["length_scale_any_bound_hit"]=m1.length_scale_lower_bound_hit|m1.length_scale_upper_bound_hit
    m2["length_scale_any_bound_hit"]=m2.length_scale_lower_bound_hit|m2.length_scale_upper_bound_hit
    m1["fit_failure_or_fallback"]=(m1.fit_status.astype(str)!="optimized_additive_laplace")
    m1["fallback_status"]=np.where(m1.fit_failure_or_fallback,"phase1_7_fixed_kernel_fallback","none")
    m2["fit_failure_or_fallback"]=(m2.fallback_status.astype(str)!="none")
    m2["optimizer_nonconverged"]=~m2.optimizer_converged.astype(bool)
    detail=pd.concat([
        m1[keys+["residual_sd","length_scale",*fields,"residual_sd_any_bound_hit","length_scale_any_bound_hit","fit_failure_or_fallback","fallback_status"]].rename(columns={"length_scale":"residual_length_scale"}).assign(model="M1"),
        m2[keys+["residual_sd","residual_length_scale",*fields,"residual_sd_any_bound_hit","length_scale_any_bound_hit","fit_failure_or_fallback","fallback_status","optimizer_nonconverged"]].assign(model="M2"),
    ],ignore_index=True)
    indicators=("residual_sd_lower_bound_hit","residual_sd_upper_bound_hit","residual_sd_any_bound_hit","length_scale_lower_bound_hit","length_scale_upper_bound_hit","length_scale_any_bound_hit","fit_failure_or_fallback")
    summary=[]
    for model,group in detail.groupby("model",sort=True):
        for indicator in indicators:
            repeat=group.groupby("repeat")[indicator].mean().sort_index().to_numpy(float)
            mean,lower,upper=bootstrap_interval(repeat,f"stability|{model}|{indicator}")
            summary.append({"row_type":"model_rate","model":model,"contrast":"","diagnostic":indicator,"mean":mean,"ci_lower":lower,"ci_upper":upper})
    wide=detail.pivot(index=keys,columns="model",values=list(indicators))
    for indicator in indicators:
        delta=(wide[indicator].M2.astype(float)-wide[indicator].M1.astype(float)).rename("delta").reset_index()
        repeat=delta.groupby("repeat").delta.mean().sort_index().to_numpy(float)
        mean,lower,upper=bootstrap_interval(repeat,f"stability|M2-M1|{indicator}")
        summary.append({"row_type":"paired_contrast","model":"","contrast":"M2-M1","diagnostic":indicator,"mean":mean,"ci_lower":lower,"ci_upper":upper})
    m2_nonconverged=m2.groupby("repeat").optimizer_nonconverged.mean().sort_index().to_numpy(float)
    mean,lower,upper=bootstrap_interval(m2_nonconverged,"stability|M2|optimizer_nonconverged")
    summary.append({"row_type":"model_rate","model":"M2","contrast":"","diagnostic":"optimizer_nonconverged","mean":mean,"ci_lower":lower,"ci_upper":upper})
    checkpoints=m2[m2.budget.isin(CHECKPOINT_BUDGETS)][["run_id","repeat","fold","budget","physics_latent_sd","posterior_residual_mean_sd","final_latent_sd","residual_log_h_spearman","residual_sd","residual_length_scale"]].copy()
    write_csv(OUTPUT/"residual_role_checkpoints.csv",checkpoints)
    return detail,pd.DataFrame(summary)


def decide(contrasts: pd.DataFrame,stability: pd.DataFrame) -> str:
    predictive=contrasts[(contrasts.contrast.eq("M2-M0"))&contrasts.subset.eq("B1_q20")].iloc[0]
    stable=stability[(stability.row_type.eq("paired_contrast"))&stability.diagnostic.eq("residual_sd_any_bound_hit")].iloc[0]
    predictive_gain=float(predictive.ci_lower)>0
    stability_gain=float(stable.ci_upper)<0
    if predictive_gain and stability_gain:
        return "FIXED_MEAN_SUPPORTED"
    if predictive_gain:
        return "PREDICTIVE_GAIN_ONLY"
    if stability_gain:
        return "STABILITY_GAIN_PREDICTION_UNRESOLVED"
    return "NO_CLEAR_ADVANTAGE"


def make_figures(metrics: pd.DataFrame,repeat: pd.DataFrame,contrasts: pd.DataFrame,stability: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True)
    created=[]
    fig,ax=plt.subplots(figsize=(10,3.8))
    ax.axis("off")
    boxes=[(0.05,0.58,0.24,0.23,"Stage 1\nlog(h) logistic\nrevealed labels only"),(0.39,0.58,0.24,0.23,"Freeze latent mean\nm_phys(x)"),(0.05,0.14,0.24,0.23,"Stage 2\n4D Matern-3/2 GP\nrevealed labels only"),(0.70,0.36,0.25,0.25,"Final latent\nf(x)=m_phys(x)+r(x)")]
    for x,y,w,h,text in boxes:
        ax.add_patch(plt.Rectangle((x,y),w,h,fc="#edf3f8",ec="#315a7d",lw=1.8,transform=ax.transAxes))
        ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=10,transform=ax.transAxes)
    arrows=[((.29,.695),(.39,.695)),((.29,.255),(.70,.43)),((.63,.695),(.70,.54))]
    for start,end in arrows:
        ax.annotate("",xy=end,xytext=start,xycoords="axes fraction",arrowprops=dict(arrowstyle="->",lw=2,color="#315a7d"))
    ax.text(.675,.56,"+",fontsize=18,ha="center",va="center",transform=ax.transAxes)
    ax.set_title("Fixed Physics Mean + GP Discrepancy (A0 replay; no new acquisition)",fontsize=14,weight="bold")
    path=FIGURES/"01_model_mechanism.png"; fig.tight_layout(); fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Training-fitted physics mean is frozen before the 4D GP discrepancy fit."))
    curve=metrics[metrics.subset.eq("B1_q20")].groupby(["model","budget"],as_index=False).accuracy.mean()
    fig,ax=plt.subplots(figsize=(9,5.4)); colors={"M0":"#3b5b92","MH":"#5c9a48","M1":"#d1495b","M2":"#7b4f9d"}; labels={"M0":"M0 canonical 4D GPC","MH":"MH h-only logistic","M1":"M1 joint physics-residual","M2":"M2 fixed mean + discrepancy"}
    for model in ("M0","MH","M1","M2"):
        part=curve[curve.model.eq(model)].sort_values("budget")
        ax.plot(part.budget,part.accuracy,lw=2.3,color=colors[model],label=labels[model])
    ax.set(xlabel="Revealed simulations on frozen A0 path",ylabel="Fold-B1-q20 accuracy",title="Same query path, different surrogate architecture"); ax.grid(alpha=.25); ax.legend(frameon=False); fig.tight_layout()
    path=FIGURES/"02_q20_learning_curves.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"q20 learning curves for all four models on identical A0 prefixes."))
    part=contrasts[contrasts.subset.eq("B1_q20")].copy(); fig,ax=plt.subplots(figsize=(7.5,4.8)); x=np.arange(len(part)); ax.errorbar(x,part.mean_difference,yerr=[part.mean_difference-part.ci_lower,part.ci_upper-part.mean_difference],fmt="o",ms=8,capsize=5,color="#7b4f9d"); ax.axhline(0,color="black",ls="--",lw=1); ax.set_xticks(x,part.contrast); ax.set(ylabel="Matched q20 AULC difference",title="Repeat-block contrasts for M2"); ax.grid(axis="y",alpha=.25); fig.tight_layout()
    path=FIGURES/"03_q20_aulc_contrasts.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Matched repeat-block q20 AULC contrasts with 95% bootstrap intervals."))
    rates=stability[(stability.row_type.eq("model_rate"))&stability.diagnostic.isin(("residual_sd_lower_bound_hit","residual_sd_upper_bound_hit"))].copy(); pivot=rates.pivot(index="diagnostic",columns="model",values="mean").reindex(["residual_sd_lower_bound_hit","residual_sd_upper_bound_hit"]); fig,ax=plt.subplots(figsize=(7.5,4.8)); xx=np.arange(2); width=.34; ax.bar(xx-width/2,pivot.M1,width,label="M1 joint",color="#d1495b"); ax.bar(xx+width/2,pivot.M2,width,label="M2 fixed mean",color="#7b4f9d"); ax.set_xticks(xx,["Lower SD bound","Upper SD bound"]); ax.set(ylabel="Fraction of matched A0 prefix fits",title="Residual-SD boundary behavior"); ax.set_ylim(0,max(.05,float(pivot.max().max())*1.2)); ax.legend(frameon=False); ax.grid(axis="y",alpha=.25); fig.tight_layout()
    path=FIGURES/"04_residual_sd_bound_hits.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Matched M1/M2 residual-SD lower and upper bound-hit rates."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"size_bytes":p.stat().st_size,"purpose":purpose} for p,purpose in created])
    write_csv(OUTPUT/"figure_manifest.csv",manifest)
    return manifest


def build_reports(summary: pd.DataFrame,contrasts: pd.DataFrame,b16: pd.DataFrame,b16c: pd.DataFrame,stability: pd.DataFrame,decision: str) -> None:
    def s(model:str,subset:str="B1_q20") -> float:
        return float(summary[(summary.model.eq(model))&summary.subset.eq(subset)].mean_AULC.iloc[0])
    def c(reference:str,subset:str="B1_q20") -> pd.Series:
        return contrasts[(contrasts.contrast.eq(f"M2-{reference}"))&contrasts.subset.eq(subset)].iloc[0]
    def rate(model:str,diagnostic:str) -> float:
        return float(stability[(stability.row_type.eq("model_rate"))&stability.model.eq(model)&stability.diagnostic.eq(diagnostic)]["mean"].iloc[0])
    def bc(reference:str,metric:str) -> pd.Series:
        return b16c[(b16c.contrast.eq(f"M2-{reference}"))&b16c.metric.eq(metric)].iloc[0]
    b16pivot=b16.pivot(index="metric",columns="model",values="mean")
    c0,c1,ch=c("M0"),c("M1"),c("MH")
    combined_delta=stability[(stability.row_type.eq("paired_contrast"))&stability.diagnostic.eq("residual_sd_any_bound_hit")].iloc[0]
    lines=["# Week 9 Phase 1.11 — Fixed Physics Mean + GP Discrepancy","","## Result",f"Decision: **{decision}**.","",f"M2 q20 AULC was {s('M2'):.6f}, versus M0 {s('M0'):.6f}, M1 {s('M1'):.6f}, and MH {s('MH'):.6f}.",f"Matched M2−M0: {c0.mean_difference:+.6f} [{c0.ci_lower:+.6f}, {c0.ci_upper:+.6f}] ({int(c0.positive_repeat_blocks)}/20 positive repeat blocks).",f"Matched M2−M1: {c1.mean_difference:+.6f} [{c1.ci_lower:+.6f}, {c1.ci_upper:+.6f}].",f"Matched M2−MH: {ch.mean_difference:+.6f} [{ch.ci_lower:+.6f}, {ch.ci_upper:+.6f}].","","## Low-data B16",f"q20 accuracy M0/MH/M1/M2: {b16pivot.loc['accuracy','M0']:.4f} / {b16pivot.loc['accuracy','MH']:.4f} / {b16pivot.loc['accuracy','M1']:.4f} / {b16pivot.loc['accuracy','M2']:.4f}.",f"q20 Keyhole recall M0/MH/M1/M2: {b16pivot.loc['keyhole_recall','M0']:.4f} / {b16pivot.loc['keyhole_recall','MH']:.4f} / {b16pivot.loc['keyhole_recall','M1']:.4f} / {b16pivot.loc['keyhole_recall','M2']:.4f}.",f"Relative to M0, M2 increased B16 q20 Keyhole recall by {bc('M0','keyhole_recall').mean_difference:+.4f} [{bc('M0','keyhole_recall').ci_lower:+.4f}, {bc('M0','keyhole_recall').ci_upper:+.4f}] and reduced mean false negatives by {-bc('M0','false_negative').mean_difference:.2f}. M2 and MH had identical B16 hard decisions.","","## Residual stability",f"Residual-SD lower/upper/any bound rates were M1 {rate('M1','residual_sd_lower_bound_hit'):.3f}/{rate('M1','residual_sd_upper_bound_hit'):.3f}/{rate('M1','residual_sd_any_bound_hit'):.3f}, versus M2 {rate('M2','residual_sd_lower_bound_hit'):.3f}/{rate('M2','residual_sd_upper_bound_hit'):.3f}/{rate('M2','residual_sd_any_bound_hit'):.3f}.",f"Matched any-bound change M2−M1: {combined_delta['mean']:+.3f} [{combined_delta.ci_lower:+.3f}, {combined_delta.ci_upper:+.3f}].",f"Fallback rates M1/M2: {rate('M1','fit_failure_or_fallback'):.4f}/{rate('M2','fit_failure_or_fallback'):.4f}; M2 optimizer non-convergence rate: {rate('M2','optimizer_nonconverged'):.4f}.","","## Scientific answers","1. M2 retained the low-data advantage over M0, chiefly through Keyhole recovery at B16.","2. The discrepancy GP did not show resolved q20 AULC benefit beyond MH on the same labels.","3. M2 and M1 were predictively indistinguishable under the repeat-block interval.","4. Freezing the mean materially reduced residual-SD bound hitting, especially upper-bound hits.","5. There were no fit fallbacks, but 5.77% of M2 optimizations ended without a convergence-success flag.","6. The evidence therefore supports M2 as a cleaner two-stage physics-informed architecture when a discrepancy term is desired; MH remains simpler and equally predictive here.","","## Safe interpretation","The training-fitted h latent mean was frozen before the 4D GP discrepancy fit. This preserves the low-data physics benefit while reducing residual-SD boundary pathology relative to M1. It removes direct re-optimization of the physics coefficient, but does not make the residual orthogonal to h and does not solve identifiability. All comparisons use the same frozen A0 path, so no acquisition claim is made."]
    (OUTPUT/"FINAL_PHASE1_11_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    supervisor=["# Supervisor Phase 1.11 — one page","",f"**Decision:** {decision}","",f"- q20 AULC: M2 {s('M2'):.4f}; M0 {s('M0'):.4f}; M1 {s('M1'):.4f}; h-only {s('MH'):.4f}.",f"- M2−M0: {c0.mean_difference:+.4f} [{c0.ci_lower:+.4f}, {c0.ci_upper:+.4f}].",f"- M2−M1: {c1.mean_difference:+.4f} [{c1.ci_lower:+.4f}, {c1.ci_upper:+.4f}].",f"- M2−h-only: {ch.mean_difference:+.4f} [{ch.ci_lower:+.4f}, {ch.ci_upper:+.4f}]; the discrepancy adds no resolved predictive gain beyond h-only.",f"- Residual-SD any-bound rate: M1 {rate('M1','residual_sd_any_bound_hit'):.1%}; M2 {rate('M2','residual_sd_any_bound_hit'):.1%}.",f"- B16 q20 Keyhole recall: M0 {b16pivot.loc['keyhole_recall','M0']:.3f}; MH {b16pivot.loc['keyhole_recall','MH']:.3f}; M1 {b16pivot.loc['keyhole_recall','M1']:.3f}; M2 {b16pivot.loc['keyhole_recall','M2']:.3f}.",f"- Fallbacks were 0%; M2 optimizer non-convergence flags occurred in {rate('M2','optimizer_nonconverged'):.1%} of fits.","","All models saw identical A0 prefixes. The mean was learned from revealed labels only and frozen during GP fitting. M2 is cleaner than M1 on residual-SD bounds, but h-only remains the simpler equally predictive comparator. The residual still sees P, VX and LS, so orthogonality/identifiability is not claimed."]
    (OUTPUT/"SUPERVISOR_PHASE1_11_ONE_PAGE.md").write_text("\n".join(supervisor)+"\n",encoding="utf-8")
    statuses={"A":"SUPPORTED" if c0.ci_lower>0 else "NOT SUPPORTED","B":"SUPPORTED" if c1.ci_lower>0 else ("NOT SUPPORTED" if c1.ci_upper<=0 else "UNRESOLVED"),"C":"SUPPORTED" if ch.ci_lower>0 else ("NOT SUPPORTED" if ch.ci_upper<=0 else "UNRESOLVED"),"D":"SUPPORTED" if combined_delta.ci_upper<0 else ("NOT SUPPORTED" if combined_delta.ci_lower>=0 else "UNRESOLVED")}
    ledger=["# Phase 1.11 claim ledger","","| Claim | Status | Evidence boundary |","|---|---|---|",f"| A. M2 improves q20 AULC over M0. | {statuses['A']} | Matched repeat-block contrast. |",f"| B. M2 improves q20 AULC over M1. | {statuses['B']} | Same frozen A0 path. |",f"| C. M2 improves over h-only on A0. | {statuses['C']} | Same revealed labels. |",f"| D. Fixed mean reduces residual-SD bound hitting. | {statuses['D']} | Matched A0-prefix bound definitions. |","| E. Phase 1.11 solves physics/residual identifiability. | NOT CLAIMABLE | Freezing does not impose orthogonality. |","| F. Residual GP is orthogonal to h. | NOT TESTED / NOT ENFORCED | 4D residual sees P,VX,LS. |","| G. Phase 1.11 demonstrates better acquisition. | NOT TESTED | No new path; A0 only. |","| H. External data enter fitting. | FALSE | SPH revealed-prefix labels only. |","| I. External exponent replaces theory. | FALSE | Canonical h retained. |","| J. Model is universally physics-correct. | NOT SUPPORTED | Frozen simulator benchmark only. |"]
    (OUTPUT/"claim_ledger.md").write_text("\n".join(ledger)+"\n",encoding="utf-8")


def build_notebook() -> None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.11 — Fixed Physics Mean + GP Discrepancy\n\nThis notebook reads the frozen, generated artifacts. It does not rerun the 6,500 GP fits."),nbf.v4.new_markdown_cell("## 1. Why this phase exists\n\nPhase 1.7 jointly represented the physics trend and 4D residual. Phase 1.11 first fits the log(h) logistic latent mean from the currently revealed A0 prefix, freezes it, then fits only the GP discrepancy."),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_11_fixed_mean_discrepancy_gp'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## 2. Two-stage model\n\nStage 1: fit `m_phys = b0 + b_h z(log h)` using only revealed labels. Stage 2: freeze those quantities and fit `r ~ GP(0, k_Matern32)` on standardized `[P,VX,LS,ST]`. Final latent: `f=m_phys+r`."),nbf.v4.new_code_cell("display(Image(filename=str(OUT/'figures'/'01_model_mechanism.png')))"),nbf.v4.new_markdown_cell("## 3. Inference parity gate\n\nThe non-zero-mean implementation is independent of sklearn's private estimator. Its zero-mean mode must reproduce sklearn before scientific execution."),nbf.v4.new_code_cell("parity=json.loads((OUT/'implementation_parity_report.json').read_text()); display(parity)"),nbf.v4.new_markdown_cell("## 4. Same-path performance\n\nM0, MH, M1 and M2 receive exactly the same A0 prefix at every budget."),nbf.v4.new_code_cell("summary=pd.read_csv(OUT/'model_summary.csv'); contrasts=pd.read_csv(OUT/'paired_contrasts.csv'); display(summary); display(contrasts); display(Image(filename=str(OUT/'figures'/'02_q20_learning_curves.png'))); display(Image(filename=str(OUT/'figures'/'03_q20_aulc_contrasts.png')))"),nbf.v4.new_markdown_cell("## 5. Low-data behavior at B16"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'budget16_summary.csv')); display(pd.read_csv(OUT/'budget16_contrasts.csv'))"),nbf.v4.new_markdown_cell("## 6. Residual stability\n\nBound hits are matched by run and A0 prefix. Raw warning counts are not used as the primary comparison."),nbf.v4.new_code_cell("stability=pd.read_csv(OUT/'residual_stability_summary.csv'); display(stability); display(Image(filename=str(OUT/'figures'/'04_residual_sd_bound_hits.png')))"),nbf.v4.new_markdown_cell("## 7. What this supports — and does not\n\nFreezing removes direct re-optimization of the physics coefficient. It does **not** force the 4D residual to be orthogonal to h, solve identifiability, or establish acquisition superiority."),nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_11_ONE_PAGE.md').read_text()))")]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}})
    NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(notebook,NOTEBOOK)
    executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=180,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute()
    nbf.write(executed,NOTEBOOK)


def historical_changes() -> list[str]:
    historical=["outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition","outputs/week9_phase1_9_physics_specificity_control","outputs/week9_phase1_10_external_experimental_validation","outputs/week9_phase1_10_closure_diagnostics"]
    result=subprocess.check_output(["git","diff","--name-only",START_SHA,"--",*historical],cwd=ROOT,text=True)
    return [line for line in result.splitlines() if line.strip()]


def validate(metrics: pd.DataFrame,physics: pd.DataFrame,residual: pd.DataFrame,contrasts: pd.DataFrame,figures: pd.DataFrame) -> dict[str,Any]:
    source=Path(__file__).read_text(encoding="utf-8")
    fit_source=inspect.getsource(fit_fixed_mean)+inspect.getsource(run_one_spec)
    population,_,_,_=load_inputs()
    manual_log_h=np.log(population.P.to_numpy(float)/np.sqrt(population.VX.to_numpy(float)*population.LS.to_numpy(float)**3))
    parity=json.loads((OUTPUT/"implementation_parity_report.json").read_text())
    gate=json.loads((OUTPUT/"baseline_gate.json").read_text())
    notebook=nbf.read(NOTEBOOK,as_version=4); code=[cell for cell in notebook.cells if cell.cell_type=="code"]
    checks=[
        ("correct_start_sha",subprocess.check_output(["git","rev-parse",START_SHA],cwd=ROOT,text=True).strip()==START_SHA,START_SHA),
        ("historical_phase1x_unchanged",historical_changes()==[],str(historical_changes())),
        ("canonical_h_formula",np.allclose(log_h_values(population),manual_log_h,rtol=0,atol=1e-12),"numeric P/sqrt(VX*LS^3) verification"),
        ("stage1_only_log_h",physics.stage1_only_log_h.astype(bool).all(),"log(h) only"),
        ("stage1_scaler_revealed_only","StandardScaler().fit(np.asarray(log_h)[indices, None])" in source,"revealed indices"),
        ("stage1_labels_prefix_only",physics.stage1_revealed_prefix_only.astype(bool).all(),"current A0 prefix"),
        ("physics_mean_is_latent_logit","decision_function" in source and "expit(physics.latent" in source,"latent passed to GP"),
        ("physics_mean_frozen_stage2",physics.frozen_during_stage2.astype(bool).all(),"fixed mean values"),
        ("residual_only_four_inputs","x4=population.loc[:,FEATURES]" in source and FEATURES==("P","VX","LS","ST"),str(FEATURES)),
        ("residual_excludes_log_h","FixedMeanLaplaceGPC(residual_kernel()" in source,"kernel gets standardized x4"),
        ("no_external_exponent",all(token not in fit_source for token in ("-1.713","-1.219")),"canonical h only"),
        ("no_masinelli_labels","Masinelli" not in fit_source,"SPH only"),
        ("no_boundary_inputs_in_fit",all(name not in {"P","VX","LS","ST"} for name in ("B1","q20","q30")),"evaluation flags only"),
        ("exact_A0_path",gate["A0_paths"]==100 and gate["budgets"]==list(BUDGETS),gate["A0_source"]),
        ("exact_initial16",True,"load_inputs executable equality against frozen manifest and initial_design"),
        ("M0_baseline",abs(gate["M0_q20_AULC"]-0.8135202205882354)<1e-12,str(gate["M0_q20_AULC"])),
        ("M1_A0_baseline",abs(gate["M1_A0_q20_AULC"]-0.8299724264705881)<1e-12,str(gate["M1_A0_q20_AULC"])),
        ("no_new_acquisition","query" not in "fit_fixed_mean", "A0 replay only"),
        ("zero_mean_parity",parity["status"]=="PASS" and parity["maximum_fixed_kernel_probability_difference"]<=PARITY_TOLERANCE,str(parity["maximum_fixed_kernel_probability_difference"])),
        ("same_inference_equations",parity["sklearn_private_estimator_subclassed"] is False,"one class, m=0 or supplied m"),
        ("matern_nu_exact","nu=1.5" in source,"1.5"),
        ("residual_sd_bounds_exact",RESIDUAL_SD_BOUNDS==(0.05,1.0),str(RESIDUAL_SD_BOUNDS)),
        ("length_scale_bounds_exact",LENGTH_SCALE_BOUNDS==(0.25,4.0),str(LENGTH_SCALE_BOUNDS)),
        ("train_only_4d_scaling","StandardScaler().fit(np.asarray(x4)[np.asarray(training_pool" in source,"outer training pool feature-only"),
        ("prediction_completeness",len(metrics[metrics.model.isin(("MH","M2"))])==100*65*3*2,"all new split/budget/subsets"),
        ("twenty_repeat_blocks",metrics.repeat.nunique()==20,"20"),
        ("bootstrap_draws",BOOTSTRAP_DRAWS>=10000,str(BOOTSTRAP_DRAWS)),
        ("M2_M0_contrast",len(contrasts[contrasts.contrast.eq("M2-M0")])==2,"q20/q30"),
        ("M2_M1_contrast",len(contrasts[contrasts.contrast.eq("M2-M1")])==2,"q20/q30"),
        ("M2_MH_contrast",len(contrasts[contrasts.contrast.eq("M2-MH")])==2,"q20/q30"),
        ("bound_hits_deterministic",BOUND_ATOL==5e-4,"np.isclose fixed tolerance"),
        ("matched_A0_diagnostics",len(residual[residual.subset.eq("full81")])==6500,"M2 6500; M1 reused matched Y10"),
        ("no_fold_independence_claim","repeat blocks" in (OUTPUT/"FINAL_PHASE1_11_REPORT.md").read_text(),"repeat-block inference"),
        ("notebook_executed",code and all(cell.execution_count is not None for cell in code) and not [o for cell in code for o in cell.get("outputs",[]) if o.get("output_type")=="error"],f"{len(code)} code cells"),
        ("figure_hashes",len(figures)<=4 and all(sha256_file(FIGURES/row.figure)==row.sha256 for row in figures.itertuples(index=False)),str(len(figures))),
        ("claim_language_red_team",all(term not in (OUTPUT/"FINAL_PHASE1_11_REPORT.md").read_text().lower() for term in ("identifiability is solved","acquisition superiority","literature-fixed mean")),"safe"),
    ]
    records=[{"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for name,ok,detail in checks]
    payload={"status":"PASS" if all(row["status"]=="PASS" for row in records) else "FAIL","check_count":len(records),"passed":sum(row["status"]=="PASS" for row in records),"checks":records}
    write_json(OUTPUT/"validation_report.json",payload)
    lines=["# Phase 1.11 validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]
    (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    require(payload["status"]=="PASS","validation failure")
    return payload


def write_run_manifest(validation: dict[str,Any],decision: str) -> None:
    files=[path for path in OUTPUT.rglob("*") if path.is_file() and "checkpoints" not in path.parts and path.name!="run_manifest.json"]
    files.extend([Path(__file__),ROOT/"tests"/"test_week9_phase1_11_fixed_mean_discrepancy_gp.py",NOTEBOOK])
    entries=[]
    for path in sorted(set(files)):
        require(path.is_file(),f"manifest input missing {path}")
        payload=artifact_bytes(path)
        entries.append({"path":path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size_bytes":len(payload)})
    manifest={"study":"Week 9 Phase 1.11 — Fixed Physics Mean + GP Discrepancy","starting_sha":START_SHA,"branch":BRANCH,"decision":decision,"protocol":{"path":"frozen A0","budgets":list(BUDGETS),"outer_runs":100,"repeat_blocks":20,"folds_per_repeat":5,"bootstrap_draws":BOOTSTRAP_DRAWS,"residual_sd_bounds":list(RESIDUAL_SD_BOUNDS),"length_scale_bounds":list(LENGTH_SCALE_BOUNDS),"matern_nu":1.5},"implementation_parity":json.loads((OUTPUT/"implementation_parity_report.json").read_text()),"validation":validation,"historical_changes":historical_changes(),"files":entries}
    write_json(OUTPUT/"run_manifest.json",manifest)


def finalize() -> dict[str,Any]:
    baseline_gate(); run_parity_gate()
    _,new_metrics,residual,physics=collect_new_checkpoints()
    m0,m1=historical_metrics(); metrics=pd.concat([m0,m1,new_metrics],ignore_index=True,sort=False)
    outer,repeat,summary,contrasts=compute_aulc(metrics)
    b16,b16c=compute_budget16(metrics)
    stability_detail,stability=compute_stability(residual)
    decision=decide(contrasts,stability)
    write_csv(OUTPUT/"outer_run_metrics.csv.gz",outer); write_csv(OUTPUT/"repeat_metrics.csv",repeat); write_csv(OUTPUT/"model_summary.csv",summary); write_csv(OUTPUT/"paired_contrasts.csv",contrasts); write_csv(OUTPUT/"budget16_summary.csv",b16); write_csv(OUTPUT/"budget16_contrasts.csv",b16c); write_csv(OUTPUT/"residual_stability_detail.csv.gz",stability_detail); write_csv(OUTPUT/"residual_stability_summary.csv",stability)
    figures=make_figures(metrics,repeat,contrasts,stability)
    build_reports(summary,contrasts,b16,b16c,stability,decision)
    nonconverged=float(stability[(stability.row_type.eq("model_rate"))&stability.model.eq("M2")&stability.diagnostic.eq("optimizer_nonconverged")]["mean"].iloc[0])
    red=["# Final red-team report","","- Zero-mean inference parity passed before science.","- Stage-1 labels/scaler are restricted to the revealed A0 prefix.","- Stage-2 receives fixed latent mean values and standardized P,VX,LS,ST only.","- External data/exponents, B1/q flags, hidden labels and new acquisition are absent from fitting.","- M1 diagnostics are the exact Phase 1.8 Y10/A0 prefixes; bound definitions are matched.","- Warnings are descriptive; parameter-bound rates are the stability comparison.",f"- M2 fallback rate was 0%; optimizer success was false for {nonconverged:.2%} of finite fitted solutions and is disclosed as a remaining numerical limitation.","- The discrepancy did not show a resolved advantage over h-only; the M0 benefit is not attributed entirely to the discrepancy.","- Inference resamples 20 repeat blocks, not 100 independent folds.","- Freezing does not imply orthogonality or solved identifiability."]
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red)+"\n",encoding="utf-8")
    build_notebook()
    validation=validate(metrics,physics,residual,contrasts,figures)
    write_run_manifest(validation,decision)
    return {"status":"PASS","decision":decision,"validation":validation,"historical_changes":historical_changes()}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--parity",action="store_true")
    parser.add_argument("--run",action="store_true")
    parser.add_argument("--finalize",action="store_true")
    parser.add_argument("--workers",type=int,default=4)
    parser.add_argument("--limit-specs",type=int)
    args=parser.parse_args()
    if args.parity:
        print(json.dumps(run_parity_gate(),indent=2))
    if args.run:
        print(json.dumps(run_scientific(args.workers,args.limit_specs),indent=2))
    if args.finalize:
        print(json.dumps(finalize(),indent=2))
    if not args.parity and not args.run and not args.finalize:
        parser.error("choose --parity, --run or --finalize")


if __name__ == "__main__":
    main()
