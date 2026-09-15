"""Physics coordinate ``h``, the h-only logistic mean, and a fixed-mean Laplace GPC.

``h = P / sqrt(VX * LS^3)`` (units W s^1/2 m^-2; ``LS`` is the Gaussian spot
radius in metres) is the keyhole process coordinate used throughout Week 9.
``fit_physics_mean`` turns ``log h`` into a logistic latent mean from the
revealed prefix, and ``FixedMeanLaplaceGPC`` learns a 4D GP discrepancy on
top of that fixed mean with Laplace inference (GPML Algorithms 3.1/3.2/5.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import scipy.optimize
from scipy.linalg import cho_solve, cholesky, solve
from scipy.special import erf, expit
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from alse.io import require

# Gan et al. (2021) Supplementary Table 3: Ti-6Al-4V liquidus, single-material
# ST sensitivity only.  frozen: week9_phase1_5_h_physics_confirmation.py::TI64_LIQUIDUS_K
TI64_LIQUIDUS_K = 1933.0
# frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::EPS
EPS = 1e-12

# Williams-Barber five-error-function approximation of the logistic-Gaussian
# integral (the same constants sklearn's GaussianProcessClassifier uses).
# frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::WB_COEFS, WB_LAMBDAS
WB_COEFS = np.array([-1854.8214151, 3516.89893646, 221.29346712, 128.12323805, -2010.49422654])[:, None]
WB_LAMBDAS = np.array([0.41, 0.40, 0.37, 0.44, 0.39])[:, None]

# Six fixed-form process scores (name, formula, SI units); exponents are not
# tuned to data.  frozen: week9_phase1_discriminative_update.py::physical_scores
PHYSICAL_SCORES: tuple[tuple[str, str, str], ...] = (
    ("linear_energy_P_over_VX", "P / VX", "J/m"),
    ("irradiance_P_over_LS2", "P / LS²", "W/m²"),
    ("areal_P_over_VX_LS", "P / (VX·LS)", "J/m²"),
    ("volumetric_P_over_VX_LS2", "P / (VX·LS²)", "J/m³"),
    ("king_style_P_over_LS_sqrtVX", "P / (LS·√VX)", "W·s^0.5/m^1.5"),
    ("keyhole_process_score_h", "P / √(VX·LS³)", "W·s^0.5/m²"),
)


# --- h coordinate ------------------------------------------------------------


def log_h(P: np.ndarray, VX: np.ndarray, LS: np.ndarray) -> np.ndarray:
    """log(P / sqrt(VX * LS^3)) with a strict positivity check on the inputs.

    frozen: week9_phase1_7_physics_ridge_residual_gp.py::log_h
    """
    p = np.asarray(P, dtype=float)
    velocity = np.asarray(VX, dtype=float)
    radius = np.asarray(LS, dtype=float)
    require((p > 0).all() and (velocity > 0).all() and (radius > 0).all(), "h inputs must be positive")
    return np.log(p / np.sqrt(velocity * radius**3))


def h_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-row ``h_SI``, ``log_h_SI_reference`` and the Ti64 ``h/(1933 K - ST)`` variant.

    Column names follow the archived ``h_coordinates.csv``; ``experiment_name``
    and ``has_keyhole`` are carried through when present.
    frozen: week9_phase1_5_h_physics_confirmation.py::h_coordinates
    """
    p = frame.P.to_numpy(float)
    velocity = frame.VX.to_numpy(float)
    radius_m = frame.LS.to_numpy(float)
    require((p > 0).all() and (velocity > 0).all() and (radius_m > 0).all(), "h inputs must be positive")
    h = p / np.sqrt(velocity * radius_m**3)
    delta_liquidus = TI64_LIQUIDUS_K - frame.ST.to_numpy(float)
    require((delta_liquidus > 0).all(), "ST exceeds fixed liquidus reference")
    h_st = h / delta_liquidus
    columns: dict[str, Any] = {"population_row_index": frame.index.astype(int)}
    if "experiment_name" in frame:
        columns["experiment_name"] = frame.experiment_name.astype(str)
    if "has_keyhole" in frame:
        columns["manual_has_keyhole"] = frame.has_keyhole.astype(int)
    columns.update(
        {
            "h_SI": h,
            "log_h_SI_reference": np.log(h),
            "delta_T_liquidus_minus_ST_K": delta_liquidus,
            "h_over_deltaT": h_st,
            "log_h_over_deltaT": np.log(h_st),
        }
    )
    out = pd.DataFrame(columns)
    require(np.isfinite(out.select_dtypes(include=[np.number])).all().all(), "non-finite h coordinate")
    return out


def physical_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """The six fixed-form scores of ``PHYSICAL_SCORES`` as ``<name>__raw`` / ``<name>__log`` columns.

    frozen: week9_phase1_discriminative_update.py::physical_scores (values dict)
    """
    p = frame.P.to_numpy(float)
    v = frame.VX.to_numpy(float)
    radius = frame.LS.to_numpy(float)
    formulas = (
        p / v,
        p / radius**2,
        p / (v * radius),
        p / (v * radius**2),
        p / (radius * np.sqrt(v)),
        p / np.sqrt(v * radius**3),
    )
    values: dict[str, np.ndarray] = {}
    for (name, _, _), raw in zip(PHYSICAL_SCORES, formulas):
        raw = np.asarray(raw, dtype=float)
        require(np.isfinite(raw).all() and (raw > 0).all(), f"Invalid physical score {name}")
        values[f"{name}__raw"] = raw
        values[f"{name}__log"] = np.log(raw)
    return pd.DataFrame(values, index=frame.index)


# --- h-only logistic mean ----------------------------------------------------


@dataclass
class PhysicsMeanFit:
    """StandardScaler on ``log h`` plus an (almost) unpenalised logistic fit."""

    scaler: StandardScaler
    model: LogisticRegression
    revealed_indices: np.ndarray

    def latent(self, log_h: np.ndarray) -> np.ndarray:
        """Logistic decision function (latent mean) at the given ``log h`` values."""
        z = self.scaler.transform(np.asarray(log_h, dtype=float).reshape(-1, 1))
        return self.model.decision_function(z)


def fit_physics_mean(log_h: np.ndarray, labels: np.ndarray, revealed: Sequence[int], seed: int = 0) -> PhysicsMeanFit:
    """Fit the h-only logistic mean on the revealed rows (scaler + LR, C=1e6, lbfgs, 3000 iters).

    ``seed`` is forwarded to ``random_state`` (inert for lbfgs; the archive
    passed ``seed_u32('physics', seed)`` under its own root).
    frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::fit_physics_mean
    """
    indices = np.asarray(revealed, dtype=int)
    scaler = StandardScaler().fit(np.asarray(log_h)[indices, None])
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000, random_state=int(seed))
    model.fit(scaler.transform(np.asarray(log_h)[indices, None]), np.asarray(labels)[indices])
    return PhysicsMeanFit(scaler=scaler, model=model, revealed_indices=indices)


# --- fixed-mean Laplace GPC ----------------------------------------------------


@dataclass
class LaplaceDiagnostics:
    """Optimizer / posterior-mode diagnostics recorded by ``FixedMeanLaplaceGPC.fit``.

    Archive convention: with ``optimize=False`` no optimizer runs and
    ``optimizer_converged`` is ``not optimize`` (True), message
    ``"optimizer_disabled"``; after a fallback it is False with the fallback tag.
    """

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

    Latent ``f = m + g`` with ``m`` given per row and ``g ~ GP(0, k)``.  Mode
    finding, marginal likelihood and gradients follow GPML Algorithms 3.1,
    3.2 and 5.1; with ``m = 0`` the probabilities equal sklearn's
    ``GaussianProcessClassifier`` for the same kernel parameters.
    frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::FixedMeanLaplaceGPC
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
        """Fit on ``X`` with labels ``y`` in {0,1} and the fixed latent mean per training row."""
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
            optimizer_message=str(result.message)
            if result is not None
            else ("optimizer_disabled" if not self.optimize else fallback),
            optimizer_iterations=int(result.nit) if result is not None else 0,
            optimizer_evaluations=int(result.nfev) if result is not None else 0,
            posterior_iterations=int(iterations),
            fallback_status=fallback,
            objective_value=-float(lml),
        )
        return self

    def latent_mean_and_variance(self, X: np.ndarray, mean_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Laplace latent mean ``m* + K*^T (y - pi)`` and variance (floored at ``EPS``)."""
        X = np.asarray(X, dtype=float)
        mean_test = np.asarray(mean_test, dtype=float)
        K_star = self.kernel_(self.X_train_, X)
        latent_mean = mean_test + K_star.T.dot(self.y_train_ - self.pi_)
        v = solve(self.L_, self.W_sr_[:, None] * K_star)
        latent_var = self.kernel_.diag(X) - np.einsum("ij,ij->j", v, v)
        return latent_mean, np.maximum(latent_var, EPS)

    def predict_proba(self, X: np.ndarray, mean_test: np.ndarray) -> np.ndarray:
        """Williams-Barber logistic-Gaussian integral; columns ``[P(y=0), P(y=1)]``."""
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
