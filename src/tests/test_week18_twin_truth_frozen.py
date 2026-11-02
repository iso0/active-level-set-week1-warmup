"""Week 18 — digital-twin truths are locked: model-code changes must not move them (see RESEARCH_LOG 2026-10-05)."""
import hashlib

import numpy as np
from threadpoolctl import threadpool_limits

import src.week18_twins as W

# The frozen T_TOBIT truth was built with the machine's default 8 OpenBLAS threads. Its L-BFGS-B fit uses
# finite-difference gradients, so the BLAS thread count changes the summation order and the optimiser path:
# with 1 or 4 threads the same code stops at a different theta (diagnostic of 2026-11-02, central ledger FIN-TOBIT).
# The frozen reference below is unchanged; the test reproduces the freeze-time thread setting instead of
# inheriting the caller's (the campaign runners set BLAS threads = 1).
FREEZE_BLAS_THREADS = 8


def test_t_tobit_truth_is_the_frozen_phase2_truth():
    W.truth.cache_clear()
    with threadpool_limits(limits=FREEZE_BLAS_THREADS, user_api="blas"):
        f = W.truth("T_TOBIT")
        assert np.allclose(f.theta, [-0.251764, -1.189419, 0.923598, 0.958547, 1.173827, 2.822081, -7.469518], atol=1e-5)
        assert abs(f.u - 110.964118) < 1e-4
        t = W.twin_task("T_TOBIT", "OLD", 324, 0)
        assert hashlib.sha1(t["y"].tobytes()).hexdigest()[:16] == "ccb5304065fceb3d"
        assert abs(float(np.nansum(np.log(t["depth"]))) - 1716.6962) < 1e-3
    W.truth.cache_clear()
