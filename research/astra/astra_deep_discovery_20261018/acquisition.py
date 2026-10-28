"""Loss-linked Gaussian SUR and finite-pool baseline scores. No oracle access."""
import numpy as np
from scipy.special import ndtr, owens_t


def gaussian_error_reduction(a, rho2):
    a = np.asarray(a, float)
    r2 = np.asarray(rho2, float)
    if np.any(r2 < -1e-7) or np.any(r2 > 1+1e-7):
        raise ArithmeticError("invalid information fraction; check covariance contract")
    r2 = np.clip(r2, 0., 1.)
    ratio = np.sqrt(np.maximum(1-r2, 0)/np.maximum(r2, 1e-300))
    before = ndtr(-np.abs(a))
    gain = before-2*owens_t(np.abs(a), ratio)
    gain = np.where(r2 < 1e-15, 0., gain)
    if np.min(gain) < -1e-10:
        raise ArithmeticError("negative Gaussian value of information")
    return np.maximum(gain, 0.)


def information_fraction(posterior, mask):
    j = posterior.mean.shape[1]
    channels = [k for k in range(j) if mask & (1 << k)]
    if not channels:
        return np.zeros(posterior.cross_cov.shape[:2])
    c = posterior.cross_cov[:, :, channels]
    v = (posterior.latent_cov+posterior.noise_cov)[:, channels][:, :, channels]
    if len(channels) == 1:
        delta = c[:, :, 0]**2/np.maximum(v[:, 0, 0], 1e-12)
    else:
        inv = np.linalg.inv(v+np.eye(len(channels))[None]*1e-12)
        delta = np.einsum("rni,nij,rnj->rn", c, inv, c)
    return delta/np.maximum(posterior.ref_variance[:, None], 1e-12)


def sur_scores(posterior, *, primary_only=False):
    a = posterior.ref_mean/np.sqrt(posterior.ref_variance)
    scores = np.zeros(len(posterior.mean))
    masks = [1] if primary_only else range(len(posterior.availability_weights))
    for mask in masks:
        weight = float(sum(w for k, w in enumerate(posterior.availability_weights) if k & 1)) if primary_only else posterior.availability_weights[mask]
        if mask and weight:
            scores += weight*gaussian_error_reduction(a[:, None], information_fraction(posterior, mask)).mean(0)
    return scores


def truvar_scores(p, eta, unresolved):
    # Supplement's reopening version; beta^.5=3, delta=.1, eta shrink r=.5.
    v = p.ref_variance
    mask = unresolved
    if not mask.any():
        mask = np.ones(len(v), bool)
    while eta > 1e-6 and np.max(3*np.sqrt(v[mask])) <= 1.1*eta:
        eta *= .5
    before = np.maximum(9*v[mask], eta**2)
    after_v = v[:, None]*(1-np.clip(information_fraction(p, 1), 0, 1))
    gain = (before[:, None]-np.maximum(9*after_v[mask], eta**2)).sum(0)
    return gain, eta


def vtl_scores(p):
    # VTL / integrated latent variance reduction, same paid-channel contract.
    result = np.zeros(len(p.mean))
    for mask, weight in enumerate(p.availability_weights):
        if mask and weight:
            result += weight*(p.ref_variance[:, None]*information_fraction(p, mask)).mean(0)
    return result


def baseline_scores(p, mode):
    sd = np.sqrt(np.maximum(p.latent_cov[:, 0, 0], 1e-12))
    if mode == "maxvar":
        return sd*sd
    if mode == "straddle":
        return 1.96*sd-np.abs(p.mean[:, 0])
    if mode == "margin":
        return -np.abs(p.probability-.5)
    raise ValueError(mode)
