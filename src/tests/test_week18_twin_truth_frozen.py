"""Week 18 — digital-twin truths are locked: model-code changes must not move them (see RESEARCH_LOG 2026-10-05)."""
import hashlib

import numpy as np

import src.week18_twins as W


def test_t_tobit_truth_is_the_frozen_phase2_truth():
    f = W.truth("T_TOBIT")
    assert np.allclose(f.theta, [-0.251764, -1.189419, 0.923598, 0.958547, 1.173827, 2.822081, -7.469518], atol=1e-5)
    assert abs(f.u - 110.964118) < 1e-4
    t = W.twin_task("T_TOBIT", "OLD", 324, 0)
    assert hashlib.sha1(t["y"].tobytes()).hexdigest()[:16] == "ccb5304065fceb3d"
    assert abs(float(np.nansum(np.log(t["depth"]))) - 1716.6962) < 1e-3
