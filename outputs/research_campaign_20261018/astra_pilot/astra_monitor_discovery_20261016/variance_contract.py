"""Explicit GP adapter convention; standard-library arithmetic, no model fitting.

An additive WhiteKernel contributes to sklearn GPR's returned test variance.
This helper requires the caller to declare the convention and supply predictive
noise in the SAME transformed/output units as the returned standard deviation.
It cannot infer conventions or certify an arbitrary model's noise semantics.
"""
from math import isfinite, sqrt


def split_sd(returned_sd, observation_noise_variance, *, returned_kind):
    """Return (latent_sd, noise_sd) for the Predictions contract.

    returned_kind must be 'latent' or 'observation'. Only tiny floating-point
    subtraction error is clipped; an incompatible noise variance is rejected.
    alpha-only training regularization must not be silently treated as predictive
    WhiteKernel noise. Heteroscedastic adapters call this separately at each x.
    """
    s, v = float(returned_sd), float(observation_noise_variance)
    if not (isfinite(s) and isfinite(v) and s >= 0 and v >= 0):
        raise ValueError("require finite nonnegative SD and noise variance")
    if returned_kind == "latent":
        return s, sqrt(v)
    if returned_kind != "observation":
        raise ValueError("declare returned_kind as latent or observation")
    latent_variance = s*s-v
    if latent_variance < -1e-12*max(s*s, v, 1e-30):
        raise ValueError("predictive variance is smaller than declared noise variance")
    return sqrt(max(0., latent_variance)), sqrt(v)


def hand_counterexample():
    """Analytical example only: no synthetic generator, fitted GP or data score."""
    residual, latent_variance, noise_variance = 3.8, 1., 1.
    predictive_variance = latent_variance+noise_variance
    correct = residual/sqrt(predictive_variance)
    double_counted = residual/sqrt(predictive_variance+noise_variance)
    return {"residual": residual, "latent_variance": latent_variance,
            "noise_variance": noise_variance, "trigger_threshold": 2.5,
            "correct_z": correct, "double_counted_z": double_counted,
            "correct_triggers": abs(correct) >= 2.5,
            "double_counted_triggers": abs(double_counted) >= 2.5,
            "interpretation": "possible trigger difference; no claim about historical frequency or outcome"}
