"""Hybrid physics + GP classifiers: fixed-mean residual GPCs (M2/M2W/M3) and trend+residual GPCs.

Two families built on the keyhole coordinate ``h`` (see ``alse.physics``):

* **Fixed physics mean + residual** (``fit_hybrid``; Phase 1.11 / 1.13).  The
  h-only logistic latent ``m(log h)`` is fitted on the revealed rows and frozen;
  a zero-mean Matern-3/2 GP discrepancy ``g(z)`` on the standardised 4D inputs
  is learned by ``FixedMeanLaplaceGPC`` (latent ``f = m + g``).  ``M2`` is the
  Phase 1.11 isotropic residual (length 1.5, bounds (0.25, 4)), ``M2W`` the
  bound-matched isotropic control (length 1.0, bounds (0.01, 100)) and ``M3``
  the ARD residual (one length per feature, same bounds).
* **Trend + residual** (``fit_additive``; Phase 1.7 / 1.9).  One sklearn
  ``GaussianProcessClassifier`` whose kernel is
  ``s2 * (1 + t . t') + v * Matern32(|z - z'| / l)``: a random intercept plus a
  Bayesian linear trend on a standardised design matrix ``t`` (prior variance
  ``s2 = 25``) and a Matern-3/2 residual on the standardised 4D inputs.  With
  ``t = log h`` (one column) this is the physics-ridge model; with
  ``t = [log P, log VX, log LS, ST]`` it is the generic-trend control.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Hyperparameter, Kernel, Matern
from sklearn.preprocessing import StandardScaler

from alse.io import require
from alse.physics import FixedMeanLaplaceGPC, PhysicsMeanFit, fit_physics_mean

FEATURES = ("P", "VX", "LS", "ST")

# Residual amplitude shared by every hybrid: sd in (0.05, 1.0), start 0.09 (sd 0.3).
# frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::RESIDUAL_SD_BOUNDS,
# INITIAL_RESIDUAL_VARIANCE, BOUND_ATOL (re-exported by week9_phase1_13) and
# week9_phase1_7_physics_ridge_residual_gp.py::RESIDUAL_SD_BOUNDS (same values).
RESIDUAL_SD_BOUNDS = (0.05, 1.0)
RESIDUAL_VARIANCE_BOUNDS = tuple(value**2 for value in RESIDUAL_SD_BOUNDS)
INITIAL_RESIDUAL_VARIANCE = 0.09
BOUND_ATOL = 5e-4
# Isotropic Matern-3/2 length: start 1.5, bounds (0.25, 4).
# frozen: week9_phase1_7::MATERN_LENGTH_SCALE, LENGTH_SCALE_BOUNDS and
# week9_phase1_11::INITIAL_LENGTH_SCALE, LENGTH_SCALE_BOUNDS (the M2 residual).
MATERN_LENGTH_SCALE = 1.5
LENGTH_SCALE_BOUNDS = (0.25, 4.0)
# M2W/M3 residual: start 1.0 per dimension, bounds (0.01, upper); upper 100 primary, 1000 sensitivity.
# frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::INITIAL_LENGTH_SCALE,
# PRIMARY_LENGTH_BOUNDS, SENSITIVITY_LENGTH_BOUNDS
WIDE_LENGTH_SCALE = 1.0
PRIMARY_LENGTH_BOUNDS = (0.01, 100.0)
SENSITIVITY_LENGTH_UPPER = 1000.0
HYBRID_MODELS = ("M2", "M2W", "M3")
# Trend prior variance (intercept and every slope) and the fixed fallback residual sd.
# frozen: week9_phase1_7::PHYSICS_PRIOR_VARIANCE (= week9_phase1_9::PRIOR_VARIANCE);
# week9_phase1_7::fit_additive fallback kernel residual_variance=0.35**2
PHYSICS_PRIOR_VARIANCE = 25.0
FALLBACK_RESIDUAL_SD = 0.35


# --- fixed physics mean + residual GPC (M2 / M2W / M3) ------------------------


def _length_bounds(model: str, upper: float | None) -> tuple[float, float]:
    require(model in HYBRID_MODELS, f"unknown residual model {model}")
    lower, default_upper = LENGTH_SCALE_BOUNDS if model == "M2" else PRIMARY_LENGTH_BOUNDS
    return float(lower), float(default_upper if upper is None else upper)


def residual_kernel(model: str, upper: float | None = None, fixed: bool = False) -> Any:
    """``ConstantKernel(0.09, (0.05^2, 1)) * Matern(nu=1.5)`` residual of the fixed-mean GPC.

    ``M2``: scalar length 1.5, bounds (0.25, 4.0).  ``M2W``: scalar length 1.0,
    bounds (0.01, upper).  ``M3``: ARD ``ones(4)``, bounds (0.01, upper).
    ``upper`` defaults to the model's frozen upper bound (4.0 / 100.0);
    ``fixed=True`` freezes both amplitude and lengths.
    frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::residual_kernel (M2W, M3);
    week9_phase1_11_fixed_mean_discrepancy_gp.py::residual_kernel (M2)
    """
    bounds = _length_bounds(model, upper)
    if model == "M3":
        length: Any = np.ones(4, dtype=float)
    else:
        length = MATERN_LENGTH_SCALE if model == "M2" else WIDE_LENGTH_SCALE
    return ConstantKernel(INITIAL_RESIDUAL_VARIANCE, "fixed" if fixed else RESIDUAL_VARIANCE_BOUNDS) * Matern(
        length_scale=length, length_scale_bounds="fixed" if fixed else bounds, nu=1.5
    )


@dataclass
class HybridFit:
    """Frozen physics mean, the training-pool input scaler and the fitted residual GP.

    frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::HybridFit
    (``length_bounds`` replaces the archive's ``length_upper`` so M2 shares the class).
    """

    physics: PhysicsMeanFit
    x_scaler: StandardScaler
    gp: FixedMeanLaplaceGPC
    revealed_indices: np.ndarray
    model: str
    length_bounds: tuple[float, float]

    @property
    def residual_sd(self) -> float:
        return math.sqrt(float(self.gp.kernel_.k1.constant_value))

    @property
    def length_scales(self) -> np.ndarray:
        """Per-feature lengths (a scalar length is repeated four times)."""
        values = np.ravel(self.gp.kernel_.k2.length_scale).astype(float)
        return values if len(values) == 4 else np.repeat(values[0], 4)

    @property
    def length_upper(self) -> float:
        return self.length_bounds[1]


def fit_hybrid(
    x4: np.ndarray,
    logh: np.ndarray,
    labels: np.ndarray,
    revealed: Sequence[int],
    training_pool: Sequence[int],
    model: str,
    physics: PhysicsMeanFit | None = None,
    upper: float | None = None,
) -> HybridFit:
    """Fit ``M2`` / ``M2W`` / ``M3`` on the revealed rows with a fixed h-only logistic mean.

    The input scaler is fitted on the whole outer training pool (not the revealed
    rows); ``physics`` defaults to ``fit_physics_mean`` on the revealed rows and
    may be shared between models (Phase 1.13 fits it once per budget).
    frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::fit_hybrid;
    week9_phase1_11_fixed_mean_discrepancy_gp.py::fit_fixed_mean (M2)
    """
    revealed_array = np.asarray(revealed, dtype=int)
    x4 = np.asarray(x4, dtype=float)
    logh = np.asarray(logh, dtype=float)
    if physics is None:
        physics = fit_physics_mean(logh, labels, revealed_array)
    scaler = StandardScaler().fit(x4[np.asarray(training_pool, dtype=int)])
    x_train = scaler.transform(x4[revealed_array])
    mean_train = physics.latent(logh[revealed_array])
    gp = FixedMeanLaplaceGPC(residual_kernel(model, upper), optimize=True).fit(
        x_train, np.asarray(labels)[revealed_array], mean_train
    )
    return HybridFit(physics, scaler, gp, revealed_array, model, _length_bounds(model, upper))


def components(fit: HybridFit, x4: np.ndarray, logh: np.ndarray) -> dict[str, np.ndarray]:
    """Physics latent, residual latent (``final - physics``), final latent, variance and P(keyhole).

    frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::components
    """
    transformed = fit.x_scaler.transform(np.asarray(x4, dtype=float))
    phys = fit.physics.latent(np.asarray(logh, dtype=float))
    final, var = fit.gp.latent_mean_and_variance(transformed, phys)
    probability = fit.gp.predict_proba(transformed, phys)[:, 1]
    return {
        "physics_latent": phys,
        "residual_latent": final - phys,
        "final_latent": final,
        "latent_variance": var,
        "probability": probability,
    }


def fit_diagnostic(fit: HybridFit) -> dict[str, Any]:
    """Residual sd, per-feature lengths, bound hits (``atol`` 5e-4) and optimizer diagnostics.

    frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::fit_diagnostic
    """
    d = fit.gp.diagnostics_
    lengths = fit.length_scales
    lower = np.isclose(lengths, fit.length_bounds[0], atol=BOUND_ATOL, rtol=0)
    upper = np.isclose(lengths, fit.length_bounds[1], atol=BOUND_ATOL, rtol=0)
    sd_lower = bool(np.isclose(fit.residual_sd, RESIDUAL_SD_BOUNDS[0], atol=BOUND_ATOL, rtol=0))
    sd_upper = bool(np.isclose(fit.residual_sd, RESIDUAL_SD_BOUNDS[1], atol=BOUND_ATOL, rtol=0))
    row: dict[str, Any] = {
        "residual_sd": fit.residual_sd,
        "residual_sd_lower_bound_hit": sd_lower,
        "residual_sd_upper_bound_hit": sd_upper,
        "residual_sd_any_bound_hit": sd_lower or sd_upper,
        "l_P": float(lengths[0]),
        "l_VX": float(lengths[1]),
        "l_LS": float(lengths[2]),
        "l_ST": float(lengths[3]),
        "anisotropy_ratio": float(lengths.max() / lengths.min()),
        "any_length_lower_bound_hit": bool(lower.any()),
        "any_length_upper_bound_hit": bool(upper.any()),
        "any_length_bound_hit": bool(lower.any() or upper.any()),
        "optimizer_converged": d.optimizer_converged,
        "optimizer_message": d.optimizer_message,
        "optimizer_iterations": d.optimizer_iterations,
        "optimizer_evaluations": d.optimizer_evaluations,
        "posterior_iterations": d.posterior_iterations,
        "fallback_status": d.fallback_status,
        "objective_value": d.objective_value,
        "length_upper_bound": fit.length_upper,
    }
    for i, name in enumerate(FEATURES):
        row[f"l_{name}_lower_bound_hit"] = bool(lower[i])
        row[f"l_{name}_upper_bound_hit"] = bool(upper[i])
    return row


# --- trend + residual additive GPC (physics ridge / generic trend) ------------


def matern32(xa: np.ndarray, xb: np.ndarray, length_scale: float = MATERN_LENGTH_SCALE) -> np.ndarray:
    """Unit-amplitude Matern-3/2 cross-covariance ``(1 + r) exp(-r)``, ``r = sqrt(3) |a - b| / l``.

    frozen: week9_phase1_7_physics_ridge_residual_gp.py::matern32
    """
    xa = np.asarray(xa, dtype=float)
    xb = np.asarray(xb, dtype=float)
    squared = np.maximum(np.sum(xa**2, axis=1)[:, None] + np.sum(xb**2, axis=1)[None, :] - 2.0 * xa @ xb.T, 0.0)
    radius = np.sqrt(squared) / float(length_scale)
    root3 = math.sqrt(3.0)
    return (1.0 + root3 * radius) * np.exp(-root3 * radius)


class TrendResidualKernel(Kernel):
    """``s2 (1 + t . t') + v Matern32(|z - z'| / l)`` on inputs ``[z (4 columns) | t (n_trend columns)]``.

    Hyperparameters (sklearn theta order): ``length_scale`` then
    ``residual_variance``; ``trend_prior_variance`` ``s2`` and ``n_trend`` are
    fixed.  ``n_trend=1`` is the physics-ridge kernel, ``n_trend=4`` the
    generic-trend control; the algebra is identical up to the design matrix.
    frozen: week9_phase1_7_physics_ridge_residual_gp.py::PhysicsRidgeResidualKernel;
    week9_phase1_9_physics_specificity_control.py::GenericTrendResidualKernel
    """

    def __init__(
        self,
        residual_variance: float = INITIAL_RESIDUAL_VARIANCE,
        length_scale: float = MATERN_LENGTH_SCALE,
        residual_variance_bounds: tuple[float, float] = RESIDUAL_VARIANCE_BOUNDS,
        length_scale_bounds: tuple[float, float] = LENGTH_SCALE_BOUNDS,
        trend_prior_variance: float = PHYSICS_PRIOR_VARIANCE,
        n_trend: int = 1,
    ) -> None:
        self.residual_variance = residual_variance
        self.length_scale = length_scale
        self.residual_variance_bounds = residual_variance_bounds
        self.length_scale_bounds = length_scale_bounds
        self.trend_prior_variance = trend_prior_variance
        self.n_trend = n_trend

    @property
    def hyperparameter_residual_variance(self) -> Hyperparameter:
        return Hyperparameter("residual_variance", "numeric", self.residual_variance_bounds)

    @property
    def hyperparameter_length_scale(self) -> Hyperparameter:
        return Hyperparameter("length_scale", "numeric", self.length_scale_bounds)

    def __call__(self, X: np.ndarray, Y: np.ndarray | None = None, eval_gradient: bool = False):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        Y_is_none = Y is None
        Y = X if Y_is_none else np.atleast_2d(np.asarray(Y, dtype=float))
        width = 4 + int(self.n_trend)
        require(X.shape[1] == width and Y.shape[1] == width, f"trend+residual kernel expects [z4, {self.n_trend} trend columns]")
        x4, trend_x = X[:, :4], X[:, 4:]
        y4, trend_y = Y[:, :4], Y[:, 4:]
        squared = np.maximum(np.sum(x4**2, axis=1)[:, None] + np.sum(y4**2, axis=1)[None, :] - 2.0 * x4 @ y4.T, 0.0)
        scaled = math.sqrt(3.0) * np.sqrt(squared) / float(self.length_scale)
        residual_base = (1.0 + scaled) * np.exp(-scaled)  # evaluation order is frozen (bitwise parity)
        residual = float(self.residual_variance) * residual_base
        trend = float(self.trend_prior_variance) * (1.0 + trend_x @ trend_y.T)
        covariance = trend + residual
        if not eval_gradient:
            return covariance
        if not Y_is_none:
            raise ValueError("Gradient can only be evaluated when Y is None")
        grad_length = float(self.residual_variance) * scaled**2 * np.exp(-scaled)
        return covariance, np.stack([grad_length, residual], axis=2)

    def diag(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(np.asarray(X, dtype=float))
        return float(self.trend_prior_variance) * (1.0 + np.sum(X[:, 4:] ** 2, axis=1)) + float(self.residual_variance)

    def is_stationary(self) -> bool:
        return False

    def __repr__(self) -> str:
        return (
            "TrendResidualKernel("
            f"residual_sd={math.sqrt(float(self.residual_variance)):.4g}, "
            f"length_scale={float(self.length_scale):.4g}, "
            f"trend_prior_sd={math.sqrt(float(self.trend_prior_variance)):.4g}, "
            f"n_trend={int(self.n_trend)})"
        )


@dataclass
class AdditiveFit:
    """Fitted sklearn GPC with the training-pool scalers for the 4D inputs and the trend columns.

    frozen: week9_phase1_7_physics_ridge_residual_gp.py::AdditiveFit
    (``trend_scaler`` is the archive's ``h_scaler``); week9_phase1_9::GenericFit
    """

    model: GaussianProcessClassifier
    x_scaler: StandardScaler
    trend_scaler: StandardScaler
    revealed_indices: np.ndarray
    x_train_transformed: np.ndarray
    y_train: np.ndarray
    warnings: str
    fit_status: str

    @property
    def kernel(self) -> TrendResidualKernel:
        return self.model.kernel_

    @property
    def residual_sd(self) -> float:
        return math.sqrt(float(self.kernel.residual_variance))

    @property
    def length_scale(self) -> float:
        return float(self.kernel.length_scale)


def _trend_matrix(trend: np.ndarray) -> np.ndarray:
    values = np.asarray(trend, dtype=float)
    return values.reshape(-1, 1) if values.ndim == 1 else values


def generic_trend_matrix(x4: np.ndarray) -> np.ndarray:
    """``[log P, log VX, log LS, ST]`` from the raw ``(P, VX, LS, ST)`` columns.

    frozen: week9_phase1_9_physics_specificity_control.py::generic_trend_matrix
    """
    x = np.asarray(x4, dtype=float)
    require((x[:, 0] > 0).all() and (x[:, 1] > 0).all() and (x[:, 2] > 0).all(), "log inputs must be positive")
    return np.column_stack([np.log(x[:, 0]), np.log(x[:, 1]), np.log(x[:, 2]), x[:, 3]])


def transform_additive_inputs(
    x4: np.ndarray, trend: np.ndarray, x_scaler: StandardScaler, trend_scaler: StandardScaler
) -> np.ndarray:
    """``[x_scaler(x4) | trend_scaler(trend)]``; a 1-D ``trend`` is one column.

    frozen: week9_phase1_7_physics_ridge_residual_gp.py::transform_additive_inputs;
    week9_phase1_9::transform_generic_inputs
    """
    return np.column_stack([x_scaler.transform(np.asarray(x4, dtype=float)), trend_scaler.transform(_trend_matrix(trend))])


def fit_additive(
    x4: np.ndarray,
    trend: np.ndarray,
    labels: np.ndarray,
    revealed: Sequence[int],
    training_pool: Sequence[int],
    seed: int,
    residual_sd_upper: float = RESIDUAL_SD_BOUNDS[1],
) -> AdditiveFit:
    """Laplace GPC with ``TrendResidualKernel`` (L-BFGS-B, 0 restarts, 100 mode iterations).

    Scalers are fitted on the training pool, the model on the revealed rows.
    ``trend`` is ``log h`` (physics ridge) or a ``(n, k)`` design matrix.  On
    ``LinAlgError`` / ``ValueError`` / ``FloatingPointError`` the fallback is a
    fixed kernel with residual sd 0.35 and length 1.5.  ``residual_sd_upper``
    replaces the residual-sd cap (Phase 1.8 sensitivity); ``seed`` only feeds
    sklearn's ``random_state`` (inert without restarts).
    frozen: week9_phase1_7_physics_ridge_residual_gp.py::fit_additive;
    week9_phase1_9::fit_generic; week9_phase1_8::fit_additive_with_bound
    """
    revealed_array = np.asarray(revealed, dtype=int)
    pool = np.asarray(training_pool, dtype=int)
    x4 = np.asarray(x4, dtype=float)
    trend = _trend_matrix(trend)
    labels = np.asarray(labels)
    x_scaler = StandardScaler().fit(x4[pool])
    trend_scaler = StandardScaler().fit(trend[pool])
    transformed = transform_additive_inputs(x4[revealed_array], trend[revealed_array], x_scaler, trend_scaler)
    n_trend = trend.shape[1]
    kernel = TrendResidualKernel(
        residual_variance_bounds=(RESIDUAL_SD_BOUNDS[0] ** 2, float(residual_sd_upper) ** 2), n_trend=n_trend
    )
    model = GaussianProcessClassifier(
        kernel=kernel,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=0,
        max_iter_predict=100,
        warm_start=False,
        random_state=int(seed),
    )
    fit_status = "optimized_additive_laplace"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            model.fit(transformed, labels[revealed_array])
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            fit_status = "fixed_additive_laplace_fallback"
            model = GaussianProcessClassifier(
                kernel=TrendResidualKernel(
                    residual_variance=FALLBACK_RESIDUAL_SD**2, length_scale=MATERN_LENGTH_SCALE, n_trend=n_trend
                ),
                optimizer=None,
                n_restarts_optimizer=0,
                max_iter_predict=100,
                random_state=int(seed),
            )
            model.fit(transformed, labels[revealed_array])
    warning_text = " | ".join(str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning))
    return AdditiveFit(
        model, x_scaler, trend_scaler, revealed_array, transformed, labels[revealed_array].astype(int), warning_text, fit_status
    )


def fit_generic(
    x4: np.ndarray, labels: np.ndarray, revealed: Sequence[int], training_pool: Sequence[int], seed: int
) -> AdditiveFit:
    """Generic-trend control: ``fit_additive`` with ``[log P, log VX, log LS, ST]`` as the trend.

    frozen: week9_phase1_9_physics_specificity_control.py::fit_generic
    """
    return fit_additive(x4, generic_trend_matrix(x4), labels, revealed, training_pool, seed)


def additive_components(fit: AdditiveFit, x4: np.ndarray, trend: np.ndarray) -> dict[str, Any]:
    """Split the Laplace latent mean into trend and residual parts.

    With ``alpha = y - pi`` at the mode: ``beta_0 = s2 sum(alpha)``,
    ``beta = s2 T_train' alpha``, ``trend = beta_0 + T beta``,
    ``residual = v Matern32(X_train, X)' alpha``.  Returns ``trend_latent``,
    ``residual_latent``, ``combined_latent``, ``latent_variance``,
    ``probability``, ``trend_probability`` (``expit`` of the trend), the scalar
    ``beta_0`` and the ``beta`` vector.  The decomposition is checked against
    sklearn's latent mean to 2e-6.
    frozen: week9_phase1_7_physics_ridge_residual_gp.py::additive_components;
    week9_phase1_9::generic_components
    """
    transformed = transform_additive_inputs(x4, trend, fit.x_scaler, fit.trend_scaler)
    alpha = fit.y_train.astype(float) - np.asarray(fit.model.base_estimator_.pi_, dtype=float)
    prior = float(fit.kernel.trend_prior_variance)
    beta_0 = prior * float(alpha.sum())
    beta = prior * (fit.x_train_transformed[:, 4:].T @ alpha)
    trend_latent = beta_0 + transformed[:, 4:] @ beta
    residual_base = matern32(fit.x_train_transformed[:, :4], transformed[:, :4], fit.length_scale)
    residual_latent = float(fit.kernel.residual_variance) * residual_base.T @ alpha
    combined_latent = trend_latent + residual_latent
    latent_mean, latent_variance = fit.model.latent_mean_and_variance(transformed)
    require(np.allclose(combined_latent, latent_mean, rtol=2e-6, atol=2e-6), "additive component decomposition mismatch")
    return {
        "trend_latent": trend_latent,
        "residual_latent": residual_latent,
        "combined_latent": combined_latent,
        "latent_variance": latent_variance,
        "probability": fit.model.predict_proba(transformed)[:, 1],
        "trend_probability": expit(trend_latent),
        "beta_0": beta_0,
        "beta": beta,
    }


def additive_diagnostic(fit: AdditiveFit) -> dict[str, Any]:
    """Fit status, kernel repr, residual sd / length, bound hits (``atol`` 5e-4) and warnings.

    frozen: week9_phase1_7_physics_ridge_residual_gp.py::fit_diagnostic_row
    (bounds are read from the fitted kernel so a changed residual-sd cap is honoured)
    """
    sd_bounds = tuple(math.sqrt(float(value)) for value in fit.kernel.residual_variance_bounds)
    length_bounds = tuple(float(value) for value in fit.kernel.length_scale_bounds)
    return {
        "fit_status": fit.fit_status,
        "kernel": repr(fit.kernel),
        "residual_sd": fit.residual_sd,
        "length_scale": fit.length_scale,
        "residual_sd_lower_bound_hit": bool(np.isclose(fit.residual_sd, sd_bounds[0], rtol=0, atol=BOUND_ATOL)),
        "residual_sd_upper_bound_hit": bool(np.isclose(fit.residual_sd, sd_bounds[1], rtol=0, atol=BOUND_ATOL)),
        "length_scale_lower_bound_hit": bool(np.isclose(fit.length_scale, length_bounds[0], rtol=0, atol=BOUND_ATOL)),
        "length_scale_upper_bound_hit": bool(np.isclose(fit.length_scale, length_bounds[1], rtol=0, atol=BOUND_ATOL)),
        "convergence_warning": bool(fit.warnings),
        "warning_text": fit.warnings,
    }
