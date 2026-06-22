"""Acquisition rules used in the Week 2 Branin comparison.

All functions work with the latent predictive distribution from the Week 1
GaussianProcessRegressor stand-in. The model predicts a latent mean ``mu`` and
standard deviation ``sigma``. The current believed boundary is ``mu = 0``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


METHOD_ORDER = (
    "random",
    "smallest_abs_mu",
    "straddle",
    "randomized_straddle",
    "expected_feasibility",
)


METHOD_DESCRIPTIONS = {
    "random": "Uniformly random unlabelled pool point; floor baseline.",
    "smallest_abs_mu": "Choose the point closest to the current boundary: argmin |mu|.",
    "straddle": "Choose largest 1.96*sigma - |mu|: near boundary and uncertain.",
    "randomized_straddle": (
        "Draw one beta ~ chi-square(df=2) per step and choose largest "
        "sqrt(beta)*sigma - |mu|."
    ),
    "expected_feasibility": (
        "Contour-focused expected-improvement-style score "
        "E[max((1.96*sigma)^2 - Y^2, 0)] for Y ~ Normal(mu, sigma^2)."
    ),
}


@dataclass
class AcquisitionChoice:
    """One selected pool index plus metadata useful for reproducibility."""

    index: int
    metadata: dict[str, float | int | str]


def rng_for_method(seed: int, method: str) -> np.random.Generator:
    """Create a deterministic RNG tied to a seed and method name."""
    digest = hashlib.sha256(f"{seed}:{method}:week2".encode("utf-8")).digest()
    method_offset = int.from_bytes(digest[:8], "little") % (2**32)
    return np.random.default_rng(method_offset)


def smallest_abs_mu_scores(mu: np.ndarray) -> np.ndarray:
    """Higher is better, equivalent to choosing the smallest absolute mean."""
    return -np.abs(mu)


def straddle_scores(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Classifier-straddle score: uncertain and near the current boundary."""
    return 1.96 * sigma - np.abs(mu)


def randomized_straddle_scores(
    mu: np.ndarray,
    sigma: np.ndarray,
    beta: float,
) -> np.ndarray:
    """Randomized straddle score using one beta draw for the whole step."""
    return np.sqrt(beta) * sigma - np.abs(mu)


def expected_feasibility_scores(
    mu: np.ndarray,
    sigma: np.ndarray,
    quadrature_nodes: int = 24,
) -> np.ndarray:
    """Expected feasibility for the zero contour.

    We approximate E[max(epsilon(x)^2 - Y(x)^2, 0)] with Gauss-Hermite
    quadrature, where ``Y(x)`` is Normal(mu, sigma^2) and
    ``epsilon(x) = 1.96*sigma(x)``.
    """
    mu = np.asarray(mu, dtype=float)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-12)
    epsilon = 1.96 * sigma
    nodes, weights = np.polynomial.hermite.hermgauss(quadrature_nodes)
    samples = mu[None, :] + np.sqrt(2.0) * sigma[None, :] * nodes[:, None]
    improvement = np.maximum(epsilon[None, :] ** 2 - samples**2, 0.0)
    return (weights[:, None] * improvement).sum(axis=0) / np.sqrt(np.pi)


def choose_next_index(
    method: str,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray | None,
    sigma: np.ndarray | None,
    rng: np.random.Generator,
) -> AcquisitionChoice:
    """Choose the next pool index according to one acquisition rule."""
    if method not in METHOD_ORDER:
        raise ValueError(f"Unknown acquisition method: {method}")
    if len(unlabelled_indices) == 0:
        raise ValueError("No unlabelled candidates left")

    if method == "random":
        position = int(rng.integers(len(unlabelled_indices)))
        return AcquisitionChoice(
            index=int(unlabelled_indices[position]),
            metadata={"selected_position": position},
        )

    if mu is None or sigma is None:
        raise ValueError(f"{method} requires both mu and sigma")

    if method == "smallest_abs_mu":
        scores = smallest_abs_mu_scores(mu)
        metadata: dict[str, float | int | str] = {}
    elif method == "straddle":
        scores = straddle_scores(mu, sigma)
        metadata = {}
    elif method == "randomized_straddle":
        beta = float(rng.chisquare(df=2.0))
        scores = randomized_straddle_scores(mu, sigma, beta)
        metadata = {"beta": beta}
    else:
        scores = expected_feasibility_scores(mu, sigma)
        metadata = {"quadrature_nodes": 24}

    best_position = int(np.argmax(scores))
    metadata["selected_position"] = best_position
    metadata["selected_score"] = float(scores[best_position])
    return AcquisitionChoice(index=int(unlabelled_indices[best_position]), metadata=metadata)
