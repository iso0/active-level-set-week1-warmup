"""Exact (coherent) one-step reduction of the finite-pool latent-set Bayes 0-1 risk under a
Gaussian latent posterior, via bivariate-normal orthant probabilities (Owen's T).

For candidate x and reference u with latent (m,v) and covariance c:
  t_x = m_x/sqrt(v_x), t_u = m_u/sqrt(v_u), rho = c/sqrt(v_x v_u)
  pi_x = Phi(t_x),  pi_u = Phi(t_u)
  P(Y_u=1, Y_x=1) = Phi2(t_u, t_x; rho)        (orthant probability)
  pi'_1(u) = Phi2/pi_x,   pi'_0(u) = (pi_u - Phi2)/(1 - pi_x)     [martingale-coherent]
  r_u(x) = min(pi_u,1-pi_u) - [pi_x min(pi'_1,1-pi'_1) + (1-pi_x) min(pi'_0,1-pi'_0)]
  A_XSUR(x) = sum_u r_u(x)
Theorem (leverage identity): r_u(x) = 0 unless the Bayes decision at u differs between the two
outcomes, and then 0 < r_u(x) <= min(pi_x, 1-pi_x, pi_u, 1-pi_u).
"""
import numpy as np
from scipy.special import owens_t, ndtr


def bvn_cdf(h, k, rho):
    """P(X<=h, Y<=k) for standard bivariate normal with correlation rho (vectorised, Owen 1956)."""
    h = np.asarray(h, float); k = np.asarray(k, float); rho = np.clip(np.asarray(rho, float), -0.999999, 0.999999)
    h = np.where(np.abs(h) < 1e-12, 1e-12, h); k = np.where(np.abs(k) < 1e-12, 1e-12, k)
    s = np.sqrt(1 - rho * rho)
    ah = (k - rho * h) / (h * s); ak = (h - rho * k) / (k * s)
    beta = np.where(h * k < 0, 0.5, 0.0)
    return 0.5 * (ndtr(h) + ndtr(k)) - owens_t(h, ah) - owens_t(k, ak) - beta


def acq_xsur(m_ref, v_ref, m_c, v_c, C, risk_floor=1e-6):
    """Reference points with current risk below `risk_floor` are skipped: exact up to
    sum of their risks (r_u <= min(pi_u, 1-pi_u))."""
    pi_all = ndtr(m_ref / np.sqrt(v_ref)); keep = np.minimum(pi_all, 1 - pi_all) > risk_floor
    if keep.sum() == 0:
        return np.zeros(len(m_c)), np.zeros(len(m_c), int)
    m_ref, v_ref, C = m_ref[keep], v_ref[keep], C[:, keep]
    t_u = m_ref / np.sqrt(v_ref); t_x = m_c / np.sqrt(v_c)
    pi_u = ndtr(t_u); pi_x = ndtr(t_x)
    rho = C / np.sqrt(np.outer(v_c, v_ref))
    P11 = np.clip(bvn_cdf(t_u[None, :], t_x[:, None], rho), 0, None)
    P11 = np.minimum(P11, np.minimum(pi_u[None, :], pi_x[:, None]))
    px = np.clip(pi_x, 1e-12, 1 - 1e-12)[:, None]
    pi1 = np.clip(P11 / px, 0, 1); pi0 = np.clip((pi_u[None, :] - P11) / (1 - px), 0, 1)
    cur = np.minimum(pi_u, 1 - pi_u).sum()
    exp = (px * np.minimum(pi1, 1 - pi1) + (1 - px) * np.minimum(pi0, 1 - pi0)).sum(1)
    flips = ((pi1 >= 0.5) != (pi0 >= 0.5)).sum(1)
    return cur - exp, flips


if __name__ == "__main__":
    from scipy.stats import multivariate_normal
    rng = np.random.default_rng(0); err = 0
    for _ in range(200):
        h, k, r = rng.normal(0, 2), rng.normal(0, 2), rng.uniform(-0.98, 0.98)
        ref = multivariate_normal([0, 0], [[1, r], [r, 1]]).cdf([h, k]); err = max(err, abs(ref - float(bvn_cdf(h, k, r))))
    print("max |bvn error| vs scipy:", err)
    # leverage identity check
    m_ref = rng.normal(0, 1.5, 50); v_ref = rng.uniform(0.2, 2, 50); m_c = rng.normal(0, 1.5, 20); v_c = rng.uniform(0.2, 2, 20)
    L = rng.normal(0, 1, (70, 70)); S = L @ L.T + 0.1 * np.eye(70); d = np.sqrt(np.diag(S)); R = S / np.outer(d, d)
    C = R[50:, :50] * np.sqrt(np.outer(v_c, v_ref)) * 0.9
    a, fl = acq_xsur(m_ref, v_ref, m_c, v_c, C)
    print("nonneg:", (a >= -1e-9).all(), "zero when no flips:", np.all(a[fl == 0] < 1e-9), "bound holds:", np.all(a <= fl * np.minimum(ndtr(m_c / np.sqrt(v_c)), 1 - ndtr(m_c / np.sqrt(v_c))) + 1e-9))
