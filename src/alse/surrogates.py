"""Surrogate models for level-set estimation.

Four families, all ported verbatim from the archive:

* synthetic GPR stand-in (``branin_week1.py``): ``C(1,(0.1,10)) * RBF(0.20,(0.08,1))
  + White(1e-4 fixed)``, ``alpha=1e-6``, no restarts;
* fixed synthetic GPC (``week4_06_gp_classifier_surrogate.py``): ``C(1,fixed) *
  RBF(0.25,fixed)``, optimizer off, ``max_iter_predict=100``; optional optimised
  iso/ARD variants from ``week4_07_optimized_gp_classifier_surrogate.py``;
* real-data GPR/GPC (Phase 6, ``week7_phase6_real_data_boundary_active_level_set.py``):
  ``C(1,(1e-3,1e3)) * Matern(1,(1e-2,1e2),nu=1.5)`` on standardised inputs with the
  frozen fallback chain (GPR: alpha 1e-8 -> 1e-6 -> fixed kernel; GPC: optimised ->
  fixed kernel -> LogisticRegression(C=1)) recorded in :class:`FitResult`;
* standalone GPC kernel family G0-G4 (``week9_phase1_12_gpc_kernel_adequacy.py``),
  where G0 is the Phase 6 kernel and the others swap RBF/Matern and iso/ARD.

Every stored trajectory depends on these settings; do not tidy them.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import norm
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from alse.io import require

Array = np.ndarray


# --- synthetic GPR stand-in ---------------------------------------------------


def make_gpr_standin(seed: int) -> GaussianProcessRegressor:
    """Week-1 regression stand-in for a level-set oracle on the unit square.

    frozen: branin_week1.py::make_gp
    """
    kernel = (
        ConstantKernel(1.0, (0.1, 10.0))
        # The lower bound prevents the regression stand-in from drawing a tiny
        # island around every observed label instead of a smooth regime boundary.
        * RBF(length_scale=0.20, length_scale_bounds=(0.08, 1.0))
        + WhiteKernel(noise_level=1e-4, noise_level_bounds="fixed")
    )
    return GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=False,
        n_restarts_optimizer=0,
        random_state=seed,
    )


def fit_gpr_standin(X: Array, y: Array, seed: int) -> GaussianProcessRegressor:
    """Fit :func:`make_gpr_standin` while silencing optimizer-bound warnings.

    frozen: branin_week1.py::fit_gp
    """
    gp = make_gpr_standin(seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gp.fit(X, y)
    return gp


# --- fixed synthetic GPC ------------------------------------------------------

GPC_LENGTH_SCALE = 0.25  # week4_06::GPC_LENGTH_SCALE
GPC_MAX_ITER_PREDICT = 100  # week4_06::GPC_MAX_ITER_PREDICT (also Phase 6 / Week 9 primary fits)
SYNTHETIC_CONSTANT_BOUNDS = (0.1, 10.0)  # week4_07::KERNEL_CONSTANT_BOUNDS
SYNTHETIC_LENGTH_BOUNDS = (0.03, 3.0)  # week4_07::KERNEL_LENGTH_SCALE_BOUNDS

# semantic name -> week4_07 SURROGATE_VARIANTS literal
FIXED_GPC_VARIANTS = {
    "fixed": "fixed_iso_gpc",
    "optimized_iso": "optimized_iso_gpc",
    "optimized_ard": "optimized_ard_gpc",
}


def _canonical_variant(variant: str) -> str:
    if variant in FIXED_GPC_VARIANTS:
        return FIXED_GPC_VARIANTS[variant]
    if variant in FIXED_GPC_VARIANTS.values():
        return variant
    raise ValueError(f"Unknown surrogate variant: {variant}")


def make_synthetic_gpc_kernel(variant: str = "fixed", dimension: int = 2):
    """Kernel of the synthetic GPC: fixed iso RBF(0.25) or optimised iso/ARD RBF.

    frozen: week4_06_gp_classifier_surrogate.py::make_gp_classifier (fixed),
    week4_07_optimized_gp_classifier_surrogate.py::make_base_kernel
    """
    canonical = _canonical_variant(variant)
    if canonical == "fixed_iso_gpc":
        return ConstantKernel(1.0, constant_value_bounds="fixed") * RBF(
            length_scale=GPC_LENGTH_SCALE,
            length_scale_bounds="fixed",
        )
    if canonical == "optimized_iso_gpc":
        return ConstantKernel(1.0, constant_value_bounds=SYNTHETIC_CONSTANT_BOUNDS) * RBF(
            length_scale=GPC_LENGTH_SCALE,
            length_scale_bounds=SYNTHETIC_LENGTH_BOUNDS,
        )
    return ConstantKernel(1.0, constant_value_bounds=SYNTHETIC_CONSTANT_BOUNDS) * RBF(
        length_scale=np.full(dimension, GPC_LENGTH_SCALE),
        length_scale_bounds=SYNTHETIC_LENGTH_BOUNDS,
    )


def make_fixed_gpc(
    variant: str = "fixed", seed: int = 0, dimension: int = 2, restarts: int = 0
) -> GaussianProcessClassifier:
    """Synthetic GPC: optimizer off for ``'fixed'``, L-BFGS-B for the optimised variants.

    ``random_state`` only matters with restarts; the fixed variant is seed-free.
    frozen: week4_06_gp_classifier_surrogate.py::make_gp_classifier,
    week4_07_optimized_gp_classifier_surrogate.py::fit_classifier_variant (kernel/optimizer)
    """
    canonical = _canonical_variant(variant)
    fixed = canonical == "fixed_iso_gpc"
    return GaussianProcessClassifier(
        kernel=make_synthetic_gpc_kernel(canonical, dimension),
        optimizer=None if fixed else "fmin_l_bfgs_b",
        n_restarts_optimizer=0 if fixed else restarts,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        random_state=seed,
    )


def fit_fixed_gpc(
    X: Array, y: Array, variant: str = "fixed", seed: int = 0, restarts: int = 0
) -> GaussianProcessClassifier:
    """Fit :func:`make_fixed_gpc`; both classes are required.

    frozen: week4_06_gp_classifier_surrogate.py::fit_classifier,
    week4_07_optimized_gp_classifier_surrogate.py::fit_classifier_variant
    """
    X = np.asarray(X, dtype=float)
    require(np.unique(y).size >= 2, "GaussianProcessClassifier requires both classes in the labelled set")
    gp = make_fixed_gpc(variant, seed=seed, dimension=X.shape[1], restarts=restarts)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        gp.fit(X, y)
    return gp


def predict_p_plus(model: GaussianProcessClassifier, X: Array) -> Array:
    """P(label == +1) column of ``predict_proba``.

    frozen: week4_06_gp_classifier_surrogate.py::predict_p_plus
    """
    probabilities = model.predict_proba(X)
    matches = np.flatnonzero(model.classes_ == 1.0)
    if len(matches) != 1:
        raise RuntimeError(f"Expected class +1 in classifier classes, got {model.classes_}")
    return probabilities[:, int(matches[0])]


# --- real-data GPR / GPC (Phase 6) -------------------------------------------

# frozen: week7_phase6_real_data_boundary_active_level_set.py module constants
KERNEL_CONSTANT_BOUNDS = (1e-3, 1e3)
KERNEL_LENGTH_BOUNDS = (1e-2, 1e2)
GPR_ALPHA_PRIMARY = 1e-8
GPR_ALPHA_RETRY = 1e-6
ACTIVE_OPTIMIZER_RESTARTS = 0
GPC_FALLBACK_MAX_ITER_PREDICT = 200
LOGISTIC_FALLBACK_C = 1.0
LOGISTIC_FALLBACK_MAX_ITER = 2000


@dataclass
class FitResult:
    """One fitted surrogate plus the diagnostics the experiment tables read.

    ``diagnostics`` is only filled by :func:`fit_gpc_kernel` (Week 9 kernel-family
    fields); the other fields are the Phase 6 originals.
    frozen: week7_phase6_real_data_boundary_active_level_set.py::FitResult
    """

    model: Any
    scaler: StandardScaler
    y_mean: float | None
    y_scale: float | None
    fit_status: str
    warnings: list[str]
    kernel: str
    constant_value: float | None
    length_scale: float | None
    bound_hit: bool
    alpha: float | None = None
    diagnostics: dict[str, Any] | None = None


def make_signal_kernel(kind: str = "matern32") -> Any:
    """``C(1,(1e-3,1e3)) * {Matern32 | Matern52 | RBF}(1,(1e-2,1e2))``.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::make_signal_kernel
    """
    if kind == "matern32":
        base = Matern(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS, nu=1.5)
    elif kind == "matern52":
        base = Matern(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS, nu=2.5)
    elif kind == "rbf":
        base = RBF(length_scale=1.0, length_scale_bounds=KERNEL_LENGTH_BOUNDS)
    else:
        raise ValueError(f"Unknown kernel kind: {kind}")
    return ConstantKernel(1.0, constant_value_bounds=KERNEL_CONSTANT_BOUNDS) * base


def extract_kernel_diagnostics(kernel: Any) -> tuple[float | None, float | None, bool]:
    """(constant, first length scale, bound hit within 1e-5 relative) of a fitted product kernel.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::extract_kernel_diagnostics
    """
    try:
        constant = float(kernel.k1.constant_value)
        length = float(np.ravel(kernel.k2.length_scale)[0])
        tol = 1e-5
        hit = bool(
            constant <= KERNEL_CONSTANT_BOUNDS[0] * (1 + tol)
            or constant >= KERNEL_CONSTANT_BOUNDS[1] * (1 - tol)
            or length <= KERNEL_LENGTH_BOUNDS[0] * (1 + tol)
            or length >= KERNEL_LENGTH_BOUNDS[1] * (1 - tol)
        )
        return constant, length, hit
    except (AttributeError, TypeError, ValueError):
        return None, None, False


def _scaler_for(x: Array, scaler: StandardScaler | None) -> StandardScaler:
    """The archive fits the scaler on the label-free training pool; default to ``x``."""
    return scaler if scaler is not None else StandardScaler().fit(x)


def fit_gpr(
    x: Array,
    y: Array,
    seed: int,
    *,
    scaler: StandardScaler | None = None,
    kernel_kind: str = "matern32",
    restarts: int = ACTIVE_OPTIMIZER_RESTARTS,
) -> FitResult:
    """GPR on standardised inputs and z-scored targets: alpha 1e-8, retry 1e-6, then fixed kernel.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::fit_gpr
    """
    scaler = _scaler_for(x, scaler)
    x_scaled = scaler.transform(x)
    y_mean = float(np.mean(y))
    y_scale = float(np.std(y, ddof=0))
    if not math.isfinite(y_scale) or y_scale < 1e-12:
        y_scale = 1.0
    y_scaled = (np.asarray(y, dtype=float) - y_mean) / y_scale
    caught: list[str] = []
    last_error = ""
    for alpha, status in [(GPR_ALPHA_PRIMARY, "optimized_primary"), (GPR_ALPHA_RETRY, "optimized_jitter_retry")]:
        model = GaussianProcessRegressor(
            kernel=make_signal_kernel(kernel_kind),
            alpha=alpha,
            normalize_y=False,
            optimizer="fmin_l_bfgs_b",
            n_restarts_optimizer=restarts,
            random_state=seed,
        )
        try:
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always")
                model.fit(x_scaled, y_scaled)
            caught.extend(str(record.message) for record in records)
            constant, length, hit = extract_kernel_diagnostics(model.kernel_)
            return FitResult(
                model=model,
                scaler=scaler,
                y_mean=y_mean,
                y_scale=y_scale,
                fit_status=status,
                warnings=caught,
                kernel=str(model.kernel_),
                constant_value=constant,
                length_scale=length,
                bound_hit=hit,
                alpha=alpha,
            )
        except Exception as exc:  # numerical fallback is recorded, never silent
            last_error = f"{type(exc).__name__}: {exc}"
            caught.append(last_error)

    # Fail-safe for numerical continuation: same kernel shape, optimizer disabled.
    fallback = GaussianProcessRegressor(
        kernel=make_signal_kernel(kernel_kind),
        alpha=GPR_ALPHA_RETRY,
        normalize_y=False,
        optimizer=None,
        random_state=seed,
    )
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        fallback.fit(x_scaled, y_scaled)
    caught.extend(str(record.message) for record in records)
    constant, length, hit = extract_kernel_diagnostics(fallback.kernel_)
    return FitResult(
        model=fallback,
        scaler=scaler,
        y_mean=y_mean,
        y_scale=y_scale,
        fit_status=f"fixed_kernel_fallback_after:{last_error}",
        warnings=caught,
        kernel=str(fallback.kernel_),
        constant_value=constant,
        length_scale=length,
        bound_hit=hit,
        alpha=GPR_ALPHA_RETRY,
    )


def predict_gpr(fit: FitResult, x: Array) -> tuple[Array, Array]:
    """(mu, sigma) in original target units; sigma floored at 1e-12.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::predict_gpr
    """
    mu_scaled, sigma_scaled = fit.model.predict(fit.scaler.transform(x), return_std=True)
    mu = np.asarray(mu_scaled, dtype=float) * float(fit.y_scale) + float(fit.y_mean)
    sigma = np.maximum(np.asarray(sigma_scaled, dtype=float) * float(fit.y_scale), 1e-12)
    return mu, sigma


def fit_gpc(
    x: Array,
    labels: Array,
    seed: int,
    *,
    scaler: StandardScaler | None = None,
    kernel_kind: str = "matern32",
    restarts: int = ACTIVE_OPTIMIZER_RESTARTS,
) -> FitResult:
    """Laplace GPC on standardised inputs: optimised -> fixed kernel -> LogisticRegression(C=1).

    frozen: week7_phase6_real_data_boundary_active_level_set.py::fit_gpc
    """
    scaler = _scaler_for(x, scaler)
    x_scaled = scaler.transform(x)
    caught: list[str] = []
    model = GaussianProcessClassifier(
        kernel=make_signal_kernel(kernel_kind),
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=restarts,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        warm_start=False,
        random_state=seed,
    )
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            model.fit(x_scaled, labels)
        caught.extend(str(record.message) for record in records)
        constant, length, hit = extract_kernel_diagnostics(model.kernel_)
        return FitResult(
            model=model,
            scaler=scaler,
            y_mean=None,
            y_scale=None,
            fit_status="optimized_primary",
            warnings=caught,
            kernel=str(model.kernel_),
            constant_value=constant,
            length_scale=length,
            bound_hit=hit,
        )
    except Exception as exc:
        caught.append(f"{type(exc).__name__}: {exc}")

    fixed = GaussianProcessClassifier(
        kernel=make_signal_kernel(kernel_kind),
        optimizer=None,
        max_iter_predict=GPC_FALLBACK_MAX_ITER_PREDICT,
        random_state=seed,
    )
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            fixed.fit(x_scaled, labels)
        caught.extend(str(record.message) for record in records)
        constant, length, hit = extract_kernel_diagnostics(fixed.kernel_)
        return FitResult(
            model=fixed,
            scaler=scaler,
            y_mean=None,
            y_scale=None,
            fit_status="fixed_kernel_fallback",
            warnings=caught,
            kernel=str(fixed.kernel_),
            constant_value=constant,
            length_scale=length,
            bound_hit=hit,
        )
    except Exception as exc:
        caught.append(f"{type(exc).__name__}: {exc}")

    logistic = LogisticRegression(C=LOGISTIC_FALLBACK_C, max_iter=LOGISTIC_FALLBACK_MAX_ITER, random_state=seed)
    logistic.fit(x_scaled, labels)
    return FitResult(
        model=logistic,
        scaler=scaler,
        y_mean=None,
        y_scale=None,
        fit_status="logistic_numerical_fallback",
        warnings=caught,
        kernel="NA_logistic_fallback",
        constant_value=None,
        length_scale=None,
        bound_hit=False,
    )


def predict_gpc(fit: FitResult, x: Array) -> Array:
    """P(positive class) = ``predict_proba[:, 1]`` on standardised inputs.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::predict_gpc,
    week9_phase1_12_gpc_kernel_adequacy.py::predict_positive
    """
    return np.asarray(fit.model.predict_proba(fit.scaler.transform(x))[:, 1], dtype=float)


def continuous_probability(mu: Array, sigma: Array, threshold: float) -> Array:
    """P(response > threshold) = Phi((mu - threshold) / sigma), clipped to [1e-12, 1 - 1e-12].

    frozen: week7_phase6_real_data_boundary_active_level_set.py::continuous_probability
    """
    z = (np.asarray(mu, dtype=float) - float(threshold)) / np.maximum(np.asarray(sigma, dtype=float), 1e-12)
    return np.clip(norm.cdf(z), 1e-12, 1 - 1e-12)


# --- standalone GPC kernel family G0-G4 (Week 9 Phase 1.12) -------------------

# frozen: week9_phase1_12_gpc_kernel_adequacy.py::MODEL_SPECS
GPC_KERNELS: dict[str, dict[str, Any]] = {
    "G0": {"name": "isotropic Matern-3/2", "family": "Matern", "nu": 1.5, "ard": False, "primary": False},
    "G1": {"name": "isotropic RBF", "family": "RBF", "nu": None, "ard": False, "primary": False},
    "G2": {"name": "ARD RBF", "family": "RBF", "nu": None, "ard": True, "primary": False},
    "G3": {"name": "ARD Matern-3/2", "family": "Matern", "nu": 1.5, "ard": True, "primary": True},
    "G4": {"name": "isotropic Matern-5/2", "family": "Matern", "nu": 2.5, "ard": False, "primary": False},
}
GPC_KERNEL_FEATURES = ("P", "VX", "LS", "ST")  # ARD kernels are four-dimensional
KERNEL_BOUND_RTOL = 1e-5  # week9_phase1_12::BOUND_RTOL


def make_gpc_kernel(name: str) -> Any:
    """``C(1,(1e-3,1e3)) * {RBF | Matern(nu)}`` with iso (1.0) or ARD (ones(4)) length scales, bounds (1e-2,1e2).

    frozen: week9_phase1_12_gpc_kernel_adequacy.py::make_kernel
    """
    require(name in GPC_KERNELS, f"unknown GPC model {name}")
    spec = GPC_KERNELS[name]
    length = np.ones(4, dtype=float) if spec["ard"] else 1.0
    bounds = tuple(float(x) for x in KERNEL_LENGTH_BOUNDS)
    if spec["family"] == "RBF":
        base = RBF(length_scale=length, length_scale_bounds=bounds)
    else:
        base = Matern(length_scale=length, length_scale_bounds=bounds, nu=float(spec["nu"]))
    return ConstantKernel(1.0, constant_value_bounds=tuple(float(x) for x in KERNEL_CONSTANT_BOUNDS)) * base


def _kernel_family_diagnostics(model: Any, fit_status: str, fallback_status: str, caught: list[str]) -> dict[str, Any]:
    """Week 9 Phase 1.12 per-fit diagnostic row (amplitude, per-feature lengths, bound hits).

    frozen: week9_phase1_12_gpc_kernel_adequacy.py::fit_gpc_model (diagnostics block)
    """
    base = {
        "fit_status": fit_status,
        "fallback_status": fallback_status,
        "optimizer_warning": bool(caught),
        "warning_text": " | ".join(caught),
    }
    if fit_status == "logistic_fallback":
        nan_keys = ("objective_value", "amplitude", "length_scale", "l_P", "l_VX", "l_LS", "l_ST", "anisotropy_ratio")
        false_keys = ("amplitude_lower_bound_hit", "amplitude_upper_bound_hit", "any_length_lower_bound_hit",
                      "any_length_upper_bound_hit", "any_length_bound_hit")
        return {**base, **{k: math.nan for k in nan_keys}, **{k: False for k in false_keys}}
    amplitude = float(model.kernel_.k1.constant_value)
    values = np.ravel(model.kernel_.k2.length_scale).astype(float)
    ard = len(values) == 4
    expanded = values if ard else np.repeat(values[0], 4)
    lower = np.isclose(expanded, KERNEL_LENGTH_BOUNDS[0], rtol=KERNEL_BOUND_RTOL, atol=0)
    upper = np.isclose(expanded, KERNEL_LENGTH_BOUNDS[1], rtol=KERNEL_BOUND_RTOL, atol=0)
    diag = {
        **base,
        "objective_value": float(-model.log_marginal_likelihood_value_),
        "amplitude": amplitude,
        "amplitude_lower_bound_hit": bool(np.isclose(amplitude, KERNEL_CONSTANT_BOUNDS[0], rtol=KERNEL_BOUND_RTOL, atol=0)),
        "amplitude_upper_bound_hit": bool(np.isclose(amplitude, KERNEL_CONSTANT_BOUNDS[1], rtol=KERNEL_BOUND_RTOL, atol=0)),
        "length_scale": float(values[0]) if not ard else math.nan,
        "l_P": float(expanded[0]),
        "l_VX": float(expanded[1]),
        "l_LS": float(expanded[2]),
        "l_ST": float(expanded[3]),
        "anisotropy_ratio": float(expanded.max() / expanded.min()),
        "any_length_lower_bound_hit": bool(lower.any()),
        "any_length_upper_bound_hit": bool(upper.any()),
        "any_length_bound_hit": bool(lower.any() or upper.any()),
    }
    for index, feature in enumerate(GPC_KERNEL_FEATURES):
        diag[f"l_{feature}_lower_bound_hit"] = bool(lower[index])
        diag[f"l_{feature}_upper_bound_hit"] = bool(upper[index])
    return diag


def fit_gpc_kernel(
    name: str, x: Array, labels: Array, seed: int, *, scaler: StandardScaler | None = None
) -> FitResult:
    """GPC with kernel ``name`` (G0-G4), same optimizer/fallback chain as :func:`fit_gpc`.

    ``G0`` reproduces :func:`fit_gpc` exactly. Week 9 status strings differ from the
    Phase 6 ones (``fixed_kernel_fallback`` / ``logistic_fallback``) and the per-fit
    diagnostic row is stored in ``FitResult.diagnostics``.
    frozen: week9_phase1_12_gpc_kernel_adequacy.py::fit_gpc_model
    """
    scaler = _scaler_for(x, scaler)
    x_scaled = scaler.transform(x)
    kernel = make_gpc_kernel(name)
    caught: list[str] = []
    fit_status = "optimized_primary"
    fallback_status = "none"
    model: Any = GaussianProcessClassifier(
        kernel=kernel,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=ACTIVE_OPTIMIZER_RESTARTS,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        warm_start=False,
        random_state=int(seed),
    )
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            model.fit(x_scaled, labels)
        caught = [str(item.message) for item in records]
    except Exception as exc:
        fallback_status = f"fixed_kernel_after_{type(exc).__name__}"
        fit_status = "fixed_kernel_fallback"
        model = GaussianProcessClassifier(
            kernel=kernel,
            optimizer=None,
            n_restarts_optimizer=0,
            max_iter_predict=GPC_FALLBACK_MAX_ITER_PREDICT,
            warm_start=False,
            random_state=int(seed),
        )
        try:
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always")
                model.fit(x_scaled, labels)
            caught = [str(exc), *(str(item.message) for item in records)]
        except Exception as second:
            fallback_status = f"logistic_after_{type(exc).__name__}_{type(second).__name__}"
            fit_status = "logistic_fallback"
            model = LogisticRegression(
                C=LOGISTIC_FALLBACK_C, max_iter=LOGISTIC_FALLBACK_MAX_ITER, random_state=int(seed)
            ).fit(x_scaled, labels)
            caught = [str(exc), str(second)]
    diagnostics = _kernel_family_diagnostics(model, fit_status, fallback_status, caught)
    if fit_status == "logistic_fallback":
        kernel_text, constant, length, hit = "NA_logistic_fallback", None, None, False
    else:
        kernel_text = str(model.kernel_)
        constant, length, hit = extract_kernel_diagnostics(model.kernel_)
    return FitResult(
        model=model,
        scaler=scaler,
        y_mean=None,
        y_scale=None,
        fit_status=fit_status,
        warnings=caught,
        kernel=kernel_text,
        constant_value=constant,
        length_scale=length,
        bound_hit=hit,
        diagnostics=diagnostics,
    )
