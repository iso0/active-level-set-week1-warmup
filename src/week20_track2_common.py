"""Numpy-only helpers shared by the Track 2 model scripts (the GPyTorch script runs in .venv, so no pandas here)."""
from __future__ import annotations

import numpy as np

UREF_LOG1P = float(np.log1p(110.9641179189907))


def sample_summaries(samples, plan, obs, centers, width):
    """samples: (S, K) latent log1p-depth trajectories of one held-out run.
    plan: bins inside the planned horizon (scheduled settings); obs: bins with observed test data.
    Returns per-sample: maximum over the planned horizon, maximum / argmax-s / time-above-u_ref (s units) over the
    observed bins.  Derived from posterior trajectories, never from the maximum of the posterior mean."""
    sp = samples[:, plan]; so = samples[:, obs]
    out = {"max_planned": sp.max(1) if sp.shape[1] else np.full(len(samples), np.nan),
           "max_observed": so.max(1) if so.shape[1] else np.full(len(samples), np.nan),
           "argmax_s_observed": centers[obs][so.argmax(1)] if so.shape[1] else np.full(len(samples), np.nan),
           "exceed_s_observed": (so > UREF_LOG1P).sum(1) * width}
    return {k: v.astype(np.float32) for k, v in out.items()}
