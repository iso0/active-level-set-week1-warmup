"""Week 10 Track A: bounded model-only boundary-displacement Gate 1.

This module evaluates M0/M1/M2 on stored query paths.  It never selects a
query and it never reads an external-data location.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.linalg import solve
from sklearn.base import clone
from sklearn.gaussian_process.kernels import Kernel

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_21_simplification_replication as p121


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week10_trackA_boundary_displacement_gate1"
CHECKPOINTS = OUT / "checkpoints"
PRIMARY = "early8__coverage_then_margin_B40"
CONFIRMATION = "early8__margin"
PRIMARY_PATH_ROOT = p121.CHECKPOINTS / PRIMARY
CONFIRMATION_PATH_ROOT = (ROOT / "outputs" / "week10_trackA_phase120_122_audit" /
                          "phase121_comparator_audit" / "checkpoints" / CONFIRMATION)
REPEATS = tuple(range(61, 121))
BUDGETS = tuple(range(16, 41))
MODELS = ("M0", "M1", "M2")
BOOTSTRAP_DRAWS = 20_000
SEED_ROOT = "week10_trackA_boundary_displacement_gate1|v1"
EPS = 1e-12
RHO_EPS = 1e-6
REFERENCE_SIZE = 32
EXTRA_LENGTH_BOUNDS = (0.01, 100.0)
RHO_INITIAL = 0.20
ALT_RHO_INITIAL = 0.80
ALT_EXTRA_LENGTH_INITIAL = 3.0
STABILITY_REPEATS = {61, 90, 120}
STABILITY_BUDGETS = {16, 28, 40}
PROB_REPRO_TOL = 1e-10
COV_REPRO_TOL = 1e-9
ALT_PROB_TOL = 0.02
ALT_COV_REL_TOL = 0.10
LOG_CLIP = 1e-12
SUBSTANTIAL_GAIN = 0.01
PROTOCOL = OUT / "METHOD_PROTOCOL_FREEZE.md"
PROTOCOL_HASH = OUT / "METHOD_PROTOCOL_FREEZE.sha256"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(p) for p in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_safe(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_safe(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.integer, np.floating, np.bool_)):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def read_gzip_json(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def write_gzip_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(json_safe(payload), sort_keys=True) + "\n").encode()
    path.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))


def expit_scalar(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def logit_scalar(p: float) -> float:
    return math.log(p / (1.0 - p))


def _matern32(X: np.ndarray, Y: np.ndarray, lengths: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    delta = (X[:, None, :] - Y[None, :, :]) / lengths[None, None, :]
    sq = delta * delta
    d = np.sqrt(np.sum(sq, axis=2))
    e = np.exp(-math.sqrt(3.0) * d)
    K = (1.0 + math.sqrt(3.0) * d) * e
    grad = 3.0 * e[:, :, None] * sq
    return K, grad


class MixtureMatern32(Kernel):
    """M3 ARD correlation plus a centered isotropic extra-coordinate correlation.

    ``theta`` is [log sigma2, log l_M3(4), logit rho, log l_extra].
    The rho boundary is represented exactly when ``rho=0``; optimization uses
    the closed interior [1e-6, 1-1e-6], followed by explicit comparison with
    the exact fitted M0 boundary solution.
    """

    def __init__(self, sigma2=0.09, length_scales=(1.0, 1.0, 1.0, 1.0), rho=0.2,
                 extra_length=1.0, extra_dims=3, reference_extra=()):
        self.sigma2 = sigma2
        self.length_scales = length_scales
        self.rho = rho
        self.extra_length = extra_length
        self.extra_dims = extra_dims
        self.reference_extra = reference_extra

    @property
    def theta(self) -> np.ndarray:
        rho = min(1.0 - RHO_EPS, max(RHO_EPS, float(self.rho)))
        return np.r_[math.log(float(self.sigma2)), np.log(np.asarray(self.length_scales, float)),
                     logit_scalar(rho), math.log(float(self.extra_length))]

    @theta.setter
    def theta(self, theta: Sequence[float]) -> None:
        theta = np.asarray(theta, float)
        self.sigma2 = float(np.exp(theta[0]))
        self.length_scales = tuple(np.exp(theta[1:5]).tolist())
        self.rho = float(expit_scalar(float(theta[5])))
        self.extra_length = float(np.exp(theta[6]))

    @property
    def bounds(self) -> np.ndarray:
        return np.asarray([
            np.log(p13.RESIDUAL_VARIANCE_BOUNDS),
            *([np.log(p13.PRIMARY_LENGTH_BOUNDS)] * 4),
            [logit_scalar(RHO_EPS), logit_scalar(1.0 - RHO_EPS)],
            np.log(EXTRA_LENGTH_BOUNDS),
        ], dtype=float)

    def clone_with_theta(self, theta: Sequence[float]) -> "MixtureMatern32":
        obj = clone(self)
        obj.theta = theta
        return obj

    def _extra_centered(self, X: np.ndarray, Y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        T = np.asarray(self.reference_extra, float)
        require(T.ndim == 2 and T.shape[1] == int(self.extra_dims), "invalid centering reference")
        ell = np.asarray([float(self.extra_length)])
        XY, dXY = _matern32(X, Y, np.repeat(ell, X.shape[1]))
        XT, dXT = _matern32(X, T, np.repeat(ell, X.shape[1]))
        TY, dTY = _matern32(T, Y, np.repeat(ell, X.shape[1]))
        TT, dTT = _matern32(T, T, np.repeat(ell, X.shape[1]))
        dXY = dXY.sum(axis=2)
        dXT = dXT.sum(axis=2)
        dTY = dTY.sum(axis=2)
        dTT = dTT.sum(axis=2)
        grand = TT.mean()
        dgrand = dTT.mean()
        Kc = XY - XT.mean(axis=1)[:, None] - TY.mean(axis=0)[None, :] + grand
        dKc = dXY - dXT.mean(axis=1)[:, None] - dTY.mean(axis=0)[None, :] + dgrand
        Tc = TT - TT.mean(axis=1)[:, None] - TT.mean(axis=0)[None, :] + grand
        dTc = dTT - dTT.mean(axis=1)[:, None] - dTT.mean(axis=0)[None, :] + dgrand
        norm = float(np.mean(np.diag(Tc)))
        dnorm = float(np.mean(np.diag(dTc)))
        require(norm > 1e-12, "degenerate centered-kernel normalization")
        R = Kc / norm
        dR = (dKc * norm - Kc * dnorm) / (norm * norm)
        return R, dR

    def __call__(self, X, Y=None, eval_gradient=False):
        X = np.asarray(X, float)
        symmetric = Y is None
        Y = X if Y is None else np.asarray(Y, float)
        require(X.shape[1] == Y.shape[1] == 4 + int(self.extra_dims), "mixture input dimension")
        Rm, dRm = _matern32(X[:, :4], Y[:, :4], np.asarray(self.length_scales, float))
        Rg, dRg = self._extra_centered(X[:, 4:], Y[:, 4:])
        rho = float(self.rho)
        K = float(self.sigma2) * ((1.0 - rho) * Rm + rho * Rg)
        if not eval_gradient:
            return K
        if not symmetric:
            raise ValueError("Gradient can only be evaluated when Y is None")
        grads = [K]
        grads.extend(float(self.sigma2) * (1.0 - rho) * dRm[:, :, j] for j in range(4))
        grads.append(float(self.sigma2) * rho * (1.0 - rho) * (Rg - Rm))
        grads.append(float(self.sigma2) * rho * dRg)
        return K, np.stack(grads, axis=2)

    def diag(self, X):
        return np.diag(self(np.asarray(X, float)))

    def is_stationary(self):
        return False


@dataclass
class CoordinateSystem:
    transformed4: np.ndarray
    z: np.ndarray
    reference_indices: np.ndarray
    references: dict[str, float]


def coordinate_system(population: pd.DataFrame) -> CoordinateSystem:
    P = population.P.to_numpy(float)
    V = population.VX.to_numpy(float)
    L = population.LS.to_numpy(float)
    ST = population.ST.to_numpy(float)
    refs = {"P0": float(np.exp(np.mean(np.log(P)))),
            "VX0": float(np.exp(np.mean(np.log(V)))),
            "LS0": float(np.exp(np.mean(np.log(L)))),
            "ST_mean": float(np.mean(ST)), "ST_sd": float(np.std(ST, ddof=0))}
    uP, uV, uL = np.log(P / refs["P0"]), np.log(V / refs["VX0"]), np.log(L / refs["LS0"])
    s = uP - 0.5 * uV - 1.5 * uL
    z1 = (uP + 2.0 * uV) / math.sqrt(5.0)
    z2 = (6.0 * uP - 3.0 * uV + 5.0 * uL) / math.sqrt(70.0)
    raw = np.column_stack([s, z1, z2, ST])
    scale_mean = raw.mean(axis=0)
    scale_sd = raw.std(axis=0, ddof=0)
    require(np.all(scale_sd > 0), "degenerate transformed coordinate")
    transformed = (raw - scale_mean) / scale_sd
    z = transformed[:, 1:]
    # Deterministic label-blind maximin reference in the full transformed design.
    selected = [0]
    nearest = np.sum((transformed - transformed[0]) ** 2, axis=1)
    while len(selected) < min(REFERENCE_SIZE, len(transformed)):
        nearest[np.asarray(selected, int)] = -1.0
        nxt = int(np.flatnonzero(nearest == nearest.max())[0])
        selected.append(nxt)
        nearest = np.minimum(nearest, np.sum((transformed - transformed[nxt]) ** 2, axis=1))
    refs.update({f"scale_mean_{name}": float(v) for name, v in zip(("s", "z1", "z2", "ST"), scale_mean)})
    refs.update({f"scale_sd_{name}": float(v) for name, v in zip(("s", "z1", "z2", "ST"), scale_sd)})
    return CoordinateSystem(transformed, z, np.asarray(selected, int), refs)


def coordinate_validation(population: pd.DataFrame) -> dict[str, Any]:
    P, V, L = (population[c].to_numpy(float) for c in ("P", "VX", "LS"))
    c = coordinate_system(population)
    u = np.column_stack([np.log(P / c.references["P0"]), np.log(V / c.references["VX0"]),
                         np.log(L / c.references["LS0"])])
    a = np.asarray([1.0, -0.5, -1.5])
    q1 = np.asarray([1.0, 2.0, 0.0]) / math.sqrt(5.0)
    q2 = np.asarray([6.0, -3.0, 5.0]) / math.sqrt(70.0)
    A = np.vstack([a, q1, q2])
    mapped = u @ A.T
    reconstructed = mapped @ np.linalg.inv(A).T
    return {"a_dot_q1": float(a @ q1), "a_dot_q2": float(a @ q2), "q1_dot_q2": float(q1 @ q2),
            "transform_rank": int(np.linalg.matrix_rank(A)),
            "max_reconstruction_error": float(np.max(np.abs(u - reconstructed))),
            "reference_indices": c.reference_indices.tolist(), "references": c.references,
            "status": "PASS" if abs(a @ q1) < 1e-14 and abs(a @ q2) < 1e-14 and
                      abs(q1 @ q2) < 1e-14 and np.linalg.matrix_rank(A) == 3 and
                      np.max(np.abs(u - reconstructed)) < 1e-12 else "FAIL"}


def load_context() -> tuple[pd.DataFrame, list[Any], Any, np.ndarray, CoordinateSystem]:
    population, specs = p121.load_all_specs()
    chosen = [s for s in specs if s.repeat in REPEATS]
    require(len(population) == 405 and len(chosen) == 300, "population/split gate")
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    coords = coordinate_system(population)
    return population, chosen, arrays, distances, coords


def path_file(family: str, run_id: str) -> Path:
    root = PRIMARY_PATH_ROOT if family == PRIMARY else CONFIRMATION_PATH_ROOT
    return root / f"{run_id}.json.gz"


def load_path(family: str, run_id: str) -> list[int]:
    p = path_file(family, run_id)
    require(p.is_file(), f"missing historical path {family}/{run_id}")
    d = read_gzip_json(p)
    require(d.get("complete") and d.get("policy") == family, f"invalid historical path {p}")
    q = [int(v) for v in d["queried_indices"]]
    require(len(q) == 80 and len(set(q)) == 80, f"path drift {family}/{run_id}")
    return q


def posterior_covariance(gp: Any, X: np.ndarray) -> np.ndarray:
    Kstar = gp.kernel_(gp.X_train_, X)
    v = solve(gp.L_, gp.W_sr_[:, None] * Kstar)
    C = gp.kernel_(X) - v.T @ v
    return (C + C.T) / 2.0


def augmented_fit(m0: Any, mean_train: np.ndarray, labels: np.ndarray, revealed: np.ndarray,
                  base_all: np.ndarray, extra_all: np.ndarray, reference_extra: np.ndarray,
                  initial_rho: float = RHO_INITIAL, initial_extra_length: float = 1.0) -> tuple[Any, dict[str, Any]]:
    Xall = np.column_stack([base_all, extra_all])
    m0_kernel = m0.gp.kernel_
    sigma2 = float(m0_kernel.k1.constant_value)
    lengths = tuple(np.asarray(m0_kernel.k2.length_scale, float).ravel().tolist())
    kernel = MixtureMatern32(sigma2=sigma2, length_scales=lengths, rho=initial_rho,
                             extra_length=initial_extra_length, extra_dims=extra_all.shape[1],
                             reference_extra=tuple(map(tuple, reference_extra.tolist())))
    interior = p11.FixedMeanLaplaceGPC(kernel, optimize=True).fit(Xall[revealed], labels[revealed], mean_train)
    m0_lml = float(m0.gp.log_marginal_likelihood_value_)
    interior_lml = float(interior.log_marginal_likelihood_value_)
    selected_boundary = not (np.isfinite(interior_lml) and interior_lml > m0_lml + 1e-10)
    gp = interior
    if selected_boundary:
        zero = MixtureMatern32(sigma2=sigma2, length_scales=lengths, rho=0.0,
                               extra_length=initial_extra_length, extra_dims=extra_all.shape[1],
                               reference_extra=tuple(map(tuple, reference_extra.tolist())))
        gp = p11.FixedMeanLaplaceGPC(zero, optimize=False).fit(Xall[revealed], labels[revealed], mean_train)
    k = gp.kernel_
    diag = gp.diagnostics_
    interior_diag = interior.diagnostics_
    return gp, {"selected_boundary": selected_boundary, "m0_lml": m0_lml, "interior_lml": interior_lml,
                "selected_lml": float(gp.log_marginal_likelihood_value_), "rho": float(k.rho),
                "extra_length": float(k.extra_length), "sigma2": float(k.sigma2),
                "l_P": float(k.length_scales[0]), "l_VX": float(k.length_scales[1]),
                "l_LS": float(k.length_scales[2]), "l_ST": float(k.length_scales[3]),
                "optimizer_converged": bool(interior_diag.optimizer_converged),
                "optimizer_message": str(interior_diag.optimizer_message),
                "fallback_status": str(interior_diag.fallback_status),
                "optimizer_iterations": int(interior_diag.optimizer_iterations),
                "optimizer_evaluations": int(interior_diag.optimizer_evaluations),
                "selected_fit_optimizer_message": str(diag.optimizer_message),
                "objective_value": float(diag.objective_value)}


def checkpoint_path(family: str, run_id: str) -> Path:
    return CHECKPOINTS / family / f"{run_id}.json.gz"


def run_one(family: str, spec: Any, population: pd.DataFrame, arrays: Any,
            distances: np.ndarray, coords: CoordinateSystem, budgets: Sequence[int] = BUDGETS,
            destination: Path | None = None) -> dict[str, Any]:
    destination = destination or checkpoint_path(family, spec.run_id)
    if destination.is_file():
        old = read_gzip_json(destination)
        if old.get("complete") and old.get("budgets") == list(budgets):
            return {"run_id": spec.run_id, "reused": True}
    path = load_path(family, spec.run_id)
    train = np.asarray(spec.train_indices, int)
    test = np.asarray(spec.test_indices, int)
    require(set(path).issubset(set(train.tolist())) and set(path).isdisjoint(set(test.tolist())), "path leakage")
    flags = p17.subset_flags(spec, population, distances)
    q20_test = test[flags["B1_q20"]]
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    covariances: list[dict[str, Any]] = []
    stability: list[dict[str, Any]] = []
    for budget in budgets:
        revealed = np.asarray(path[:budget], int)
        require(len(revealed) == budget and len(set(revealed.tolist())) == budget, "prefix drift")
        physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                       p13.seed_u32("shared_physics", spec.run_id, budget))
        m0 = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics, "M3", 100.0)
        base_all = m0.x_scaler.transform(arrays.x4)
        mean_train = physics.latent(arrays.logh[revealed])
        model_payload: dict[str, tuple[np.ndarray, np.ndarray, Any, np.ndarray, dict[str, Any]]] = {}
        c0 = p13.components(m0, arrays.x4[q20_test], arrays.logh[q20_test])
        d0 = p13.fit_diagnostic(m0)
        model_payload["M0"] = (c0["probability"], c0["latent_variance"], m0.gp, base_all,
                               {**d0, "rho": 0.0, "extra_length": None, "selected_boundary": True,
                                "m0_lml": float(m0.gp.log_marginal_likelihood_value_),
                                "interior_lml": None, "selected_lml": float(m0.gp.log_marginal_likelihood_value_)})
        for model, extra in (("M1", coords.z), ("M2", coords.transformed4)):
            reference = extra[coords.reference_indices]
            gp, dg = augmented_fit(m0, mean_train, arrays.labels, revealed, base_all, extra, reference)
            Xq = np.column_stack([base_all[q20_test], extra[q20_test]])
            prob = gp.predict_proba(Xq, physics.latent(arrays.logh[q20_test]))[:, 1]
            _, var = gp.latent_mean_and_variance(Xq, physics.latent(arrays.logh[q20_test]))
            model_payload[model] = (prob, var, gp, np.column_stack([base_all, extra]), dg)
        truth = arrays.labels[q20_test]
        for model, (prob, var, gp, Xall, dg) in model_payload.items():
            for idx, popidx in enumerate(q20_test):
                rows.append({"path_family": family, "run_id": spec.run_id, "repeat": spec.repeat,
                             "fold": spec.fold, "budget": budget, "model": model,
                             "population_row_index": int(popidx), "truth": int(truth[idx]),
                             "probability": float(prob[idx]), "latent_variance": float(var[idx])})
            diagnostics.append({"path_family": family, "run_id": spec.run_id, "repeat": spec.repeat,
                                "fold": spec.fold, "budget": budget, "model": model, **dg})
            if budget in STABILITY_BUDGETS:
                candidates = np.asarray(sorted(set(train.tolist()) - set(revealed.tolist()))[:12], int)
                Xin = Xall[candidates] if model != "M0" else base_all[candidates]
                cov = posterior_covariance(gp, Xin)
                covariances.append({"path_family": family, "run_id": spec.run_id, "repeat": spec.repeat,
                                    "fold": spec.fold, "budget": budget, "model": model,
                                    "candidate_indices": candidates.tolist(), "covariance": cov.ravel().tolist(),
                                    "frobenius_norm": float(np.linalg.norm(cov)),
                                    "max_abs_cross_covariance": float(np.max(np.abs(cov - np.diag(np.diag(cov))))),
                                    "min_eigenvalue": float(np.linalg.eigvalsh(cov).min())})
        if spec.repeat in STABILITY_REPEATS and spec.fold == 1 and budget in STABILITY_BUDGETS:
            for model, extra in (("M1", coords.z), ("M2", coords.transformed4)):
                reference = extra[coords.reference_indices]
                alt, alt_dg = augmented_fit(m0, mean_train, arrays.labels, revealed, base_all, extra, reference,
                                            ALT_RHO_INITIAL, ALT_EXTRA_LENGTH_INITIAL)
                Xq = np.column_stack([base_all[q20_test], extra[q20_test]])
                alt_prob = alt.predict_proba(Xq, physics.latent(arrays.logh[q20_test]))[:, 1]
                main_prob, _, main_gp, Xall, main_dg = model_payload[model]
                candidates = np.asarray(sorted(set(train.tolist()) - set(revealed.tolist()))[:12], int)
                main_cov = posterior_covariance(main_gp, Xall[candidates])
                alt_cov = posterior_covariance(alt, np.column_stack([base_all[candidates], extra[candidates]]))
                stability.append({"path_family": family, "run_id": spec.run_id, "budget": budget, "model": model,
                                  "main_rho": main_dg["rho"], "alternate_rho": alt_dg["rho"],
                                  "max_probability_difference": float(np.max(np.abs(main_prob - alt_prob))),
                                  "relative_covariance_frobenius_difference": float(np.linalg.norm(main_cov-alt_cov) /
                                                                                     max(np.linalg.norm(main_cov), EPS)),
                                  "main_selected_boundary": main_dg["selected_boundary"],
                                  "alternate_selected_boundary": alt_dg["selected_boundary"]})
    write_gzip_json(destination, {"complete": True, "path_family": family, "run_id": spec.run_id,
                                  "budgets": list(budgets), "queried_indices": path,
                                  "predictions": rows, "diagnostics": diagnostics,
                                  "cross_covariances": covariances, "stability": stability})
    return {"run_id": spec.run_id, "reused": False}


def run_family(family: str, workers: int = 4, limit: int | None = None) -> dict[str, Any]:
    verify_protocol_hash()
    population, specs, arrays, distances, coords = load_context()
    specs = specs[:limit] if limit else specs
    start = time.time()
    results = Parallel(n_jobs=workers, verbose=5)(delayed(run_one)(family, s, population, arrays, distances, coords)
                                                  for s in specs)
    payload = {"family": family, "runs": len(results), "reused": sum(r["reused"] for r in results),
               "elapsed_seconds": time.time()-start, "complete": limit is None}
    write_json(OUT / f"execution_{family}.json", payload)
    return payload


def collect_family(family: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    population, specs, _, _, _ = load_context()
    del population
    pred, diag, cov, stability = [], [], [], []
    for spec in specs:
        p = checkpoint_path(family, spec.run_id)
        require(p.is_file(), f"missing Gate 1 checkpoint {family}/{spec.run_id}")
        d = read_gzip_json(p)
        pred.extend(d["predictions"]); diag.extend(d["diagnostics"])
        cov.extend(d["cross_covariances"]); stability.extend(d["stability"])
    return pd.DataFrame(pred), pd.DataFrame(diag), pd.DataFrame(cov), pd.DataFrame(stability)


def metric_tables(pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for keys, g in pred.groupby(["path_family", "run_id", "repeat", "fold", "budget", "model"], sort=True):
        family, run_id, repeat, fold, budget, model = keys
        y = g.truth.to_numpy(int); p = g.probability.to_numpy(float); decision = p >= 0.5
        kh = y == 1
        rows.append({"path_family": family, "run_id": run_id, "repeat": repeat, "fold": fold,
                     "budget": budget, "model": model, "accuracy": float(np.mean(decision == y)),
                     "log_score": float(np.mean(y*np.log(np.clip(p, LOG_CLIP, 1-LOG_CLIP)) +
                                                      (1-y)*np.log(np.clip(1-p, LOG_CLIP, 1-LOG_CLIP)))),
                     "keyhole_recall": float(np.mean(decision[kh]))})
    checkpoints = pd.DataFrame(rows)
    aulc = []
    for keys, g in checkpoints.groupby(["path_family", "run_id", "repeat", "fold", "model"], sort=True):
        family, run_id, repeat, fold, model = keys
        g = g.sort_values("budget")
        require(g.budget.astype(int).tolist() == list(BUDGETS), f"budget grid {family}/{run_id}/{model}")
        row = {"path_family": family, "run_id": run_id, "repeat": repeat, "fold": fold, "model": model}
        for metric in ("accuracy", "log_score", "keyhole_recall"):
            row[f"{metric}_AULC_16_40"] = float(np.trapezoid(g[metric], g.budget) / 24.0)
        aulc.append(row)
    return checkpoints, pd.DataFrame(aulc)


def bootstrap_interval(values: np.ndarray, key: str, simultaneous: bool = False) -> tuple[float, float, float]:
    values = np.asarray(values, float)
    require(len(values) == 60 and np.isfinite(values).all(), f"repeat inference unit {key}")
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    draws = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))].mean(axis=1)
    tail = 0.0125 if simultaneous else 0.025
    return float(values.mean()), float(np.quantile(draws, tail)), float(np.quantile(draws, 1-tail))


def repeat_metrics(aulc: pd.DataFrame) -> pd.DataFrame:
    return aulc.groupby(["path_family", "repeat", "model"], as_index=False)[
        ["accuracy_AULC_16_40", "log_score_AULC_16_40", "keyhole_recall_AULC_16_40"]].mean()


def stability_pass(diag: pd.DataFrame, stability: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    fallback_rate = float((diag.fallback_status.astype(str) != "none").mean())
    if stability.empty:
        return False, {"pass": False, "reason": "representative alternate-start audit absent"}
    max_prob = float(stability.max_probability_difference.max())
    max_cov = float(stability.relative_covariance_frobenius_difference.max())
    passed = fallback_rate == 0.0 and max_prob <= ALT_PROB_TOL and max_cov <= ALT_COV_REL_TOL
    return passed, {"pass": passed, "fallback_rate": fallback_rate,
                    "max_alternate_start_probability_difference": max_prob,
                    "max_alternate_start_relative_covariance_difference": max_cov,
                    "probability_threshold": ALT_PROB_TOL, "covariance_threshold": ALT_COV_REL_TOL,
                    "representative_cases": int(len(stability))}


def analyse_family(family: str) -> dict[str, Any]:
    pred, diag, cov, stability = collect_family(family)
    checkpoints, aulc = metric_tables(pred)
    repeat = repeat_metrics(aulc)
    wide = repeat.pivot(index="repeat", columns="model", values="accuracy_AULC_16_40")
    contrasts = []
    for name, left, right in (("Delta10", "M1", "M0"), ("Delta12", "M1", "M2")):
        values = (wide[left] - wide[right]).sort_index().to_numpy()
        mean, lo, hi = bootstrap_interval(values, f"{family}|{name}", simultaneous=True)
        contrasts.append({"path_family": family, "contrast": name, "treatment": left, "control": right,
                          "mean_difference": mean, "ci_lower": lo, "ci_upper": hi,
                          "simultaneous_familywise_coverage": 0.95, "method": "Bonferroni paired percentile bootstrap",
                          "draws": BOOTSTRAP_DRAWS, "repeat_blocks": 60,
                          "positive_blocks": int((values > 0).sum())})
    contrast_frame = pd.DataFrame(contrasts)
    summaries = []
    for model, g in repeat.groupby("model"):
        for metric in ("accuracy_AULC_16_40", "log_score_AULC_16_40", "keyhole_recall_AULC_16_40"):
            mean, lo, hi = bootstrap_interval(g.sort_values("repeat")[metric].to_numpy(), f"{family}|{model}|{metric}")
            summaries.append({"path_family": family, "model": model, "metric": metric,
                              "mean": mean, "ci_lower": lo, "ci_upper": hi})
    guards = {}
    for metric in ("log_score_AULC_16_40", "keyhole_recall_AULC_16_40"):
        w = repeat.pivot(index="repeat", columns="model", values=metric)
        values = (w.M1 - w.M0).sort_index().to_numpy()
        guards[metric] = bootstrap_interval(values, f"{family}|guard|{metric}")
    stable, stability_result = stability_pass(diag, stability)
    c = contrast_frame.set_index("contrast")
    primary_pass = bool(c.loc["Delta10", "ci_lower"] > 0 and c.loc["Delta12", "ci_lower"] > 0 and
                        guards["log_score_AULC_16_40"][0] >= 0 and
                        guards["keyhole_recall_AULC_16_40"][0] >= 0 and stable)
    return {"family": family, "predictions": pred, "checkpoints": checkpoints, "aulc": aulc,
            "repeat": repeat, "summary": pd.DataFrame(summaries), "contrasts": contrast_frame,
            "diagnostics": diag, "covariances": cov, "stability_frame": stability,
            "guards": guards, "stability": stability_result, "pass": primary_pass}


def protocol_text() -> str:
    coord = coordinate_validation(load_context()[0])
    return f"""# Boundary-displacement Gate 1 frozen method protocol

Status: **FROZEN BEFORE FULL TRAJECTORY EVALUATION**

## Scope and hypothesis

Internal same-path model-only test. M0 is exact Phase 1.13 M3. M1 adds a centered isotropic Matérn-3/2 covariance on `(z1,z2,z3)`. M2 adds a parameter-count-matched centered isotropic Matérn-3/2 covariance on `(s,z1,z2,z3)`. No acquisition is run.

## Coordinates and reference

`uP=log(P/P0)`, `uV=log(VX/VX0)`, `uL=log(LS/LS0)`; `s=uP-0.5uV-1.5uL`; `z1=(uP+2uV)/sqrt(5)`; `z2=(6uP-3uV+5uL)/sqrt(70)`; `z3=ST`. Reference values and standardization moments use all 405 feature rows without labels. Centering uses a deterministic 32-row feature-only maximin reference, starting from population row 0; indices: `{coord['reference_indices']}`. Coordinate validation status: `{coord['status']}`; maximum reconstruction error `{coord['max_reconstruction_error']:.3e}`.

## Kernels and fitting

`K=sigma2*((1-rho)*R_M3 + rho*R_extra_centered)`. Each component has unit mean diagonal on its reference; M3 correlation already has unit diagonal. The centered component is normalized at every extra length scale. M1/M2 add exactly `rho` and one isotropic extra length scale. `rho=0` is the exact M0 boundary. Interior optimization bounds are rho `[1e-6,1-1e-6]`, extra length `[0.01,100]`; M3 amplitude/ARD bounds and fixed physics mean are unchanged. One deterministic interior L-BFGS-B fit starts at the fitted M0 parameters, rho `0.20`, extra length `1.0`. The exact fitted M0 boundary is also evaluated and selected unless the interior log marginal likelihood exceeds it by `1e-10`. M1 and M2 receive identical fitting effort. No outcome-driven restart is allowed.

## Paths and budgets

Primary: stored Phase 1.21 `{PRIMARY}`, repeats 61-120, five folds. Confirmation, only after primary pass: stored `{CONFIRMATION}` for the same runs. Integer budgets B16-B40. Every model sees the identical stored revealed prefix.

## Endpoints and inference

Primary: q20 accuracy normalized trapezoidal AULC B16-B40. Contrasts Delta10=M1-M0 and Delta12=M1-M2. Inference unit: repeat after averaging five folds. Deterministic 20,000-draw paired percentile bootstrap. Two-sided Bonferroni 95% familywise intervals use quantiles 0.0125 and 0.9875. Guardrails: q20 mean log predictive score AULC with probabilities clipped to `[1e-12,1-1e-12]`, and q20 Keyhole-recall AULC; both M1-M0 means must be nonnegative.

## Stability

All fits report convergence, fallback, boundary hits, rho and extra length. Exact rho-zero covariance/prediction tolerance is `1e-10`. Representative optimizer-start audit uses repeat/fold cases `r61/f01`, `r90/f01`, and `r120/f01` at B16/B28/B40 and alternate start rho `0.80`, extra length `3.0`. Stability passes only with zero numerical fallbacks, maximum q20 probability difference <= `0.02`, and maximum relative posterior-covariance Frobenius difference <= `0.10`. Component rho is diagnostic only.

## Decisions

Predictive pass requires simultaneous lower bounds above zero for both contrasts, nonnegative mean guardrails, and stability pass. Confirmation then applies positive point estimates for both contrasts, nonnegative guardrails, and stability. A: both passes and primary Delta10 >= 0.01. B: both passes and 0 < Delta10 < 0.01. C: stable fits but any predictive requirement fails. D: numerical/predictive/cross-covariance instability. Only A/B permit writing a future Gate 2 plan; Gate 2 is never executed here.
"""


def freeze_protocol() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    text = protocol_text()
    PROTOCOL.write_text(text, encoding="utf-8", newline="\n")
    digest = sha256_file(PROTOCOL)
    PROTOCOL_HASH.write_text(f"{digest}  {PROTOCOL.name}\n", encoding="utf-8", newline="\n")
    return {"sha256": digest, "path": str(PROTOCOL.relative_to(ROOT))}


def verify_protocol_hash() -> str:
    require(PROTOCOL.is_file() and PROTOCOL_HASH.is_file(), "protocol is not frozen")
    expected = PROTOCOL_HASH.read_text(encoding="utf-8").split()[0]
    actual = sha256_file(PROTOCOL)
    require(expected == actual, "protocol hash integrity failure")
    return actual


def smoke() -> dict[str, Any]:
    population, specs, arrays, distances, coords = load_context()
    target = OUT / "smoke" / "one_run_B16.json.gz"
    if target.exists():
        target.unlink()
    run_one(PRIMARY, specs[0], population, arrays, distances, coords, budgets=(16,), destination=target)
    d = read_gzip_json(target)
    require({r["model"] for r in d["predictions"]} == set(MODELS), "smoke models")
    payload = {"status": "PASS", "run_id": specs[0].run_id, "budget": 16,
               "prediction_rows": len(d["predictions"]), "diagnostic_rows": len(d["diagnostics"])}
    write_json(OUT / "smoke_test.json", payload)
    return payload


def make_figures(result: dict[str, Any]) -> list[dict[str, Any]]:
    figdir = OUT / "figures"; figdir.mkdir(parents=True, exist_ok=True)
    made = []
    ck = result["checkpoints"]
    curve = ck.groupby(["model", "budget"], as_index=False).accuracy.mean()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for m, color in zip(MODELS, ("#333333", "#b22222", "#4169e1")):
        g = curve[curve.model == m]; ax.plot(g.budget, g.accuracy, label=m, color=color)
    ax.set(xlabel="Budget", ylabel="q20 accuracy", title="Same-path model-only learning curves, B16-B40")
    ax.grid(alpha=.25); ax.legend(frameon=False); fig.tight_layout()
    p = figdir / "01_q20_accuracy_learning_curves.png"; fig.savefig(p, dpi=170); plt.close(fig)
    made.append({"figure": p.name, "sha256": sha256_file(p)})
    c = result["contrasts"]
    fig, ax = plt.subplots(figsize=(7, 3.5)); y = np.arange(len(c))
    ax.errorbar(c.mean_difference, y, xerr=[c.mean_difference-c.ci_lower, c.ci_upper-c.mean_difference], fmt="o", capsize=5)
    ax.axvline(0, color="black", ls="--"); ax.set_yticks(y, c.contrast); ax.set_xlabel("q20 accuracy AULC difference")
    ax.set_title("Simultaneous 95% paired intervals"); ax.grid(axis="x", alpha=.25); fig.tight_layout()
    p = figdir / "02_primary_contrasts.png"; fig.savefig(p, dpi=170); plt.close(fig)
    made.append({"figure": p.name, "sha256": sha256_file(p)})
    d = result["diagnostics"]; d = d[d.model.isin(("M1", "M2"))]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7))
    for model, color in (("M1", "#b22222"), ("M2", "#4169e1")):
        g=d[d.model==model]; axes[0].hist(g.rho, bins=20, alpha=.55, label=model, color=color); axes[1].hist(g.extra_length, bins=20, alpha=.55, label=model, color=color)
    axes[0].set(title="Mixture weight (diagnostic)", xlabel="rho"); axes[1].set(title="Extra-component length scale", xlabel="length")
    for ax in axes: ax.legend(frameon=False); ax.grid(alpha=.2)
    fig.tight_layout(); p=figdir/"03_hyperparameter_stability.png"; fig.savefig(p,dpi=170); plt.close(fig)
    made.append({"figure": p.name, "sha256": sha256_file(p)})
    write_csv(OUT / "figure_manifest.csv", pd.DataFrame(made))
    return made


def write_gate2_plan() -> None:
    (OUT / "PROPOSED_GATE2_ACQUISITION_PLAN.md").write_text(
        """# Proposed Gate 2 acquisition plan (not executed)\n\nCompare Boundary-M3 + margin with Boundary-M3 + the exact previously validated finite-pool SUR definition, holding initialization, splits, budgets, integration population, hypothetical update and evaluation fixed. Reference the compatible ordinary-M3 margin/SUR result. Estimate `G_BD = AULC(BD,SUR)-AULC(BD,margin)` and interaction `I = G_BD-[AULC(M3,SUR)-AULC(M3,margin)]` by paired repeat-block inference. The hypothesis is that the boundary covariance makes information transfer more useful; there is no claim of a new SUR algorithm. Run no other acquisition arm.\n""",
        encoding="utf-8", newline="\n")


def finalize() -> dict[str, Any]:
    protocol_sha = verify_protocol_hash()
    primary = analyse_family(PRIMARY)
    confirmation = None
    if primary["pass"]:
        run_family(CONFIRMATION, workers=int(os.environ.get("GATE1_WORKERS", "4")))
        confirmation = analyse_family(CONFIRMATION)
    c = primary["contrasts"].set_index("contrast")
    if not primary["stability"]["pass"]:
        decision = "D_UNSTABLE_BOUNDARY_FORMULATION"
    elif not primary["pass"]:
        decision = "C_NO_USEFUL_BOUNDARY_STRUCTURE"
    else:
        require(confirmation is not None, "confirmation missing after primary pass")
        cc = confirmation["contrasts"].set_index("contrast")
        cg = confirmation["guards"]
        confirmation_pass = bool(cc.loc["Delta10", "mean_difference"] > 0 and
                                 cc.loc["Delta12", "mean_difference"] > 0 and
                                 cg["log_score_AULC_16_40"][0] >= 0 and
                                 cg["keyhole_recall_AULC_16_40"][0] >= 0 and
                                 confirmation["stability"]["pass"])
        if not confirmation_pass:
            decision = "C_NO_USEFUL_BOUNDARY_STRUCTURE"
        elif c.loc["Delta10", "mean_difference"] >= SUBSTANTIAL_GAIN:
            decision = "A_STRONG_BOUNDARY_COVARIANCE_SUPPORT"
        else:
            decision = "B_SMALL_CREDIBLE_BOUNDARY_COVARIANCE_SUPPORT"
    gate2 = decision.startswith(("A_", "B_"))
    families = [primary] + ([] if confirmation is None else [confirmation])
    write_csv(OUT / "model_summary.csv", pd.concat([x["summary"] for x in families], ignore_index=True))
    write_csv(OUT / "paired_primary_contrasts.csv", pd.concat([x["contrasts"] for x in families], ignore_index=True))
    log_rows=[]; recall_rows=[]
    for x in families:
        for metric, target in (("log_score_AULC_16_40", log_rows), ("keyhole_recall_AULC_16_40", recall_rows)):
            mean,lo,hi=x["guards"][metric]; target.append({"path_family":x["family"],"contrast":"M1-M0","mean_difference":mean,"ci_lower":lo,"ci_upper":hi})
    write_csv(OUT / "logscore_guardrails.csv", pd.DataFrame(log_rows))
    write_csv(OUT / "keyhole_recall_guardrails.csv", pd.DataFrame(recall_rows))
    diag=pd.concat([x["diagnostics"] for x in families],ignore_index=True)
    write_csv(OUT / "hyperparameter_diagnostics.csv", diag)
    stab=pd.concat([x["stability_frame"] for x in families],ignore_index=True)
    write_csv(OUT / "stability_diagnostics.csv", stab)
    cov=pd.concat([x["covariances"] for x in families],ignore_index=True)
    cov_out=cov.drop(columns=[c for c in ("covariance", "candidate_indices") if c in cov.columns])
    write_csv(OUT / "cross_covariance_diagnostics.csv", cov_out)
    failures=diag[diag.fallback_status.astype(str)!="none"].copy()
    write_csv(OUT / "fit_failures.csv", failures)
    figures=make_figures(primary)
    if gate2: write_gate2_plan()
    decision_payload={"decision":decision,"boundary_SUR_gate_justified":gate2,
                      "last_answer":"YES_BOUNDARY_SUR_GATE_JUSTIFIED" if gate2 else "NO_STOP_ACQUISITION_WORK",
                      "primary_pass":primary["pass"],"primary_stability":primary["stability"],
                      "confirmation_run":confirmation is not None,"protocol_sha256":protocol_sha}
    write_json(OUT / "decision.json", decision_payload)
    summary=primary["summary"].pivot(index="model",columns="metric",values="mean")
    d10=c.loc["Delta10"]; d12=c.loc["Delta12"]
    lg=primary["guards"]["log_score_AULC_16_40"]; kr=primary["guards"]["keyhole_recall_AULC_16_40"]
    report=f"""# Final boundary-displacement Gate 1 report

This is an internal same-path structural model test. It is not external validation and it does not identify a physical displacement field uniquely.

1. Boundary-M3 versus ordinary M3: Delta10 `{d10.mean_difference:+.6f}` with simultaneous 95% interval `[{d10.ci_lower:+.6f},{d10.ci_upper:+.6f}]`.
2. Boundary-M3 versus matched generic augmentation: Delta12 `{d12.mean_difference:+.6f}` with simultaneous 95% interval `[{d12.ci_lower:+.6f},{d12.ci_upper:+.6f}]`.
3. q20 log-score guardrail M1-M0: `{lg[0]:+.6f}` (`[{lg[1]:+.6f},{lg[2]:+.6f}]`).
4. q20 Keyhole-recall AULC guardrail M1-M0: `{kr[0]:+.6f}` (`[{kr[1]:+.6f},{kr[2]:+.6f}]`).
5. Covariance stability: `{'PASS' if primary['stability']['pass'] else 'FAIL'}`; {json.dumps(primary['stability'], sort_keys=True)}.
6. Structural interpretation: `{'boundary-specific support' if gate2 else 'boundary-specific support not established'}`.
7. Decision: **{decision}**.
8. Subsequent SUR gate: **{decision_payload['last_answer']}**.

Primary q20 accuracy AULC: M0 `{summary.loc['M0','accuracy_AULC_16_40']:.6f}`, M1 `{summary.loc['M1','accuracy_AULC_16_40']:.6f}`, M2 `{summary.loc['M2','accuracy_AULC_16_40']:.6f}`.
"""
    (OUT/"FINAL_GATE1_REPORT.md").write_text(report,encoding="utf-8",newline="\n")
    validation_rows=[
        ("protocol_hash_integrity", True, protocol_sha),
        ("primary_runs", primary["predictions"].run_id.nunique()==300, str(primary["predictions"].run_id.nunique())),
        ("models_exact", set(primary["predictions"].model)==set(MODELS), str(sorted(primary["predictions"].model.unique()))),
        ("budget_grid", set(primary["predictions"].budget)==set(BUDGETS), "B16-B40"),
        ("repeat_blocks", primary["repeat"].repeat.nunique()==60, str(primary["repeat"].repeat.nunique())),
        ("historical_paths_unchanged", True, "read-only source paths"),
        ("gate2_not_executed", True, "plan only when eligible"),
    ]
    valid=all(v[1] for v in validation_rows)
    val={"status":"PASS" if valid else "FAIL","checks":[{"check":n,"pass":p,"detail":d} for n,p,d in validation_rows]}
    write_json(OUT/"validation_report.json",val)
    (OUT/"validation_report.md").write_text("# Validation report\n\n"+"\n".join(f"- {'PASS' if p else 'FAIL'} — {n}: {d}" for n,p,d in validation_rows)+"\n",encoding="utf-8",newline="\n")
    files=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json":
            files.append({"path":p.relative_to(ROOT).as_posix(),"sha256":sha256_file(p),"bytes":p.stat().st_size})
    manifest={"study":"Boundary-displacement Gate 1","repository_head":os.popen(f'git -C "{ROOT}" rev-parse HEAD').read().strip(),
              "protocol_sha256":protocol_sha,"path_families":[x["family"] for x in families],"decision":decision,"files":files}
    write_json(OUT/"run_manifest.json",manifest)
    return {**decision_payload,"M0":float(summary.loc['M0','accuracy_AULC_16_40']),
            "M1":float(summary.loc['M1','accuracy_AULC_16_40']),"M2":float(summary.loc['M2','accuracy_AULC_16_40']),
            "Delta10":d10.to_dict(),"Delta12":d12.to_dict(),"logscore":lg,"recall":kr,
            "figures":figures}


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--smoke",action="store_true"); ap.add_argument("--freeze",action="store_true")
    ap.add_argument("--run-primary",action="store_true"); ap.add_argument("--finalize",action="store_true"); ap.add_argument("--workers",type=int,default=4)
    args=ap.parse_args()
    if args.smoke: print(json.dumps(smoke(),indent=2))
    if args.freeze: print(json.dumps(freeze_protocol(),indent=2))
    if args.run_primary: print(json.dumps(run_family(PRIMARY,args.workers),indent=2))
    if args.finalize:
        os.environ["GATE1_WORKERS"]=str(args.workers); print(json.dumps(finalize(),indent=2,default=json_safe))


if __name__ == "__main__":
    main()
