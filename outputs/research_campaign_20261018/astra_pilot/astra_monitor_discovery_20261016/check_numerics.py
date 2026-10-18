"""Four tiny GP fits, available ONLY inside the coordinator-authorized pilot.

Independent dense inverse / scalar references, not scientific-score tuning.
"""
def run_reference_checks(before_fit):
    import numpy as np
    from synthetic import FixedGP
    out = []
    for n in (1, 2, 3, 4):
        x = np.array([[.1*j, .2, .4, .7] for j in range(n)])
        y = np.array([(-1.)**j*.2 for j in range(n)])
        test = np.array([[.15, .2, .4, .7], [.6, .1, .5, .2]])
        before_fit(n)
        gp = FixedGP().fit(x, y)
        m, s = gp.predict(test)
        # Independently written covariance; no call to FixedGP.kernel.
        def kernel(a, b):
            from math import dist, sqrt, exp
            r = sqrt(3)*dist(a, b)/.28
            return .8**2*(1+r)*exp(-r)
        k = np.array([[kernel(a, b) for b in x] for a in x])
        k += np.eye(n)*(.08**2+1e-10)
        cross = np.array([[kernel(a, b) for b in test] for a in x])
        inv = np.linalg.inv(k)
        reference_m = -.4+cross.T@inv@(y+.4)
        reference_v = .8**2-np.einsum("ij,ik,kj->j", cross, inv, cross)
        error = max(float(abs(m-reference_m).max()), float(abs(s*s-reference_v).max()))
        if error > 1e-9:
            raise AssertionError("independent small GP reference failed")
        out.append({"n": n, "max_absolute_error": error, "tolerance": 1e-9})
    return out
