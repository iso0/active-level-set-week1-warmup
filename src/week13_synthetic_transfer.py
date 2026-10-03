"""Week 13 synthetic campaign-transfer study (CONTROLLED METHODOLOGICAL EVIDENCE).

Question: when does a physics-informed mean (M3 analogue) transfer worse than a
generic GP under campaign shift?  Pre-specified expectation (written before
running): with no corner deviation (A = 0) the physics models are at least as
good as the generic GP; as A grows, the physics-only trend fails first, the
amplitude-capped M3 analogue next, while a generic ARD GPC and an uncapped
M3 analogue degrade less.

All models are trained on every label of an OLD-like campaign (405 cases) and
scored on an independent NEW-like corner campaign (136 cases) plus the dense
noise-free NEW truth.  Hyperparameters are learned by the same L-BFGS Laplace
code path (src/week9_phase1_11 FixedMeanLaplaceGPC) as the historical M3; only
the fixed mean and the amplitude bounds differ between M3-capped, M3-uncapped
and G3-like.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import brentq
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src.week13_boundary_metrics import edge_metrics, gabriel_edges
from src.week13_synthetic import DenseTruth, PhysicsTrend, Scenario, labels, latent, physics_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic_transfer"
OLD_BOX = ((0, 0, 0, 0), (1, 1, 1, .5))
NEW_BOX = ((.8, 0, 0, 0), (1, 1, .2, 1))
AMPS = (0.0, 0.75, 1.5, 3.0)
SIGMA = 0.5
MODELS = {
    "H_physics_only": None,
    "M3_capped": ("physics", (0.05 ** 2, 1.0 ** 2)),
    "M3_uncapped": ("physics", (0.05 ** 2, 1e3)),
    "G3_generic": ("zero", (1e-3, 1e3)),
}


def offset_for(amp):
    u = Scenario("x", *OLD_BOX, 0, 0).sample(200000, np.random.default_rng(99))
    return float(brentq(lambda c: labels(u, Scenario("x", *OLD_BOX, c, amp)).mean() - .18, -3, 3))


def kernel(bounds):
    return ConstantKernel(0.09 if bounds[1] <= 1 else 1.0, bounds) * Matern(length_scale=np.ones(4), length_scale_bounds=(0.01, 100.0), nu=1.5)


def run_one(amp, rep, c):
    rng = np.random.default_rng([31, int(amp * 100), rep])
    sc_old = Scenario("OLD", *OLD_BOX, c, amp)
    sc_new = Scenario("NEW", *NEW_BOX, c, amp)
    uo = sc_old.sample(405, rng)
    un = sc_new.sample(136, rng)
    yo = (latent(uo, sc_old) + SIGMA * rng.standard_normal(len(uo)) > 0).astype(int)
    yn = (latent(un, sc_new) + SIGMA * rng.standard_normal(len(un)) > 0).astype(int)
    dense = DENSE.setdefault(amp, DenseTruth(sc_new, seed=5))
    scaler = StandardScaler().fit(uo)
    zo, zn, zd = scaler.transform(uo), scaler.transform(un), scaler.transform(dense.u)
    trend = PhysicsTrend().fit(physics_score(uo), yo)
    edges = gabriel_edges(StandardScaler().fit_transform(un))
    rows = []
    for name, spec in MODELS.items():
        diag = {}
        if spec is None:
            lat_n = trend.latent(physics_score(un))
            lat_d = trend.latent(physics_score(dense.u))
            p_n = 1 / (1 + np.exp(-lat_n))
        else:
            meanf, bounds = spec
            m_o = trend.latent(physics_score(uo)) if meanf == "physics" else np.zeros(len(uo))
            m_n = trend.latent(physics_score(un)) if meanf == "physics" else np.zeros(len(un))
            m_d = trend.latent(physics_score(dense.u)) if meanf == "physics" else np.zeros(len(dense.u))
            gp = p11.FixedMeanLaplaceGPC(kernel(bounds), optimize=True).fit(zo, yo, m_o)
            lat_n, _ = gp.latent_mean_and_variance(zn, m_n)
            lat_d, _ = gp.latent_mean_and_variance(zd, m_d)
            p_n = gp.predict_proba(zn, m_n)[:, 1]
            diag = {"amplitude_var": float(gp.kernel_.k1.constant_value),
                    "amp_upper_hit": bool(np.isclose(gp.kernel_.k1.constant_value, bounds[1], rtol=1e-4)),
                    **{f"ls_{k}": float(v) for k, v in zip(("P", "VX", "LS", "ST"), np.ravel(gp.kernel_.k2.length_scale))},
                    "converged": gp.diagnostics_.optimizer_converged}
        yhat = (lat_n > 0).astype(int)
        r = {"amp": amp, "rep": rep, "model": name, "new_minority_share": float(np.mean(yn == 0)),
             "old_cases_in_new_box": int(np.all((uo >= np.asarray(NEW_BOX[0])) & (uo <= np.asarray(NEW_BOX[1])), axis=1).sum()),
             "balanced_accuracy": float((np.mean(yhat[yn == 1] == 1) + np.mean(yhat[yn == 0] == 0)) / 2) if (yn == 0).any() else np.nan,
             "rare_recall": float(np.mean(yhat[yn == 0] == 0)) if (yn == 0).any() else np.nan,
             "roc_auc": float(roc_auc_score(yn, p_n)) if len(set(yn)) == 2 else np.nan,
             "accuracy": float(np.mean(yhat == yn))}
        em = edge_metrics(edges, yn, yhat)
        r.update({"BER": em["BER"], "BEF1": em["BEF1"]})
        r.update(dense.metrics((lat_d > 0).astype(int)))
        r.update(diag)
        rows.append(r)
    return rows


DENSE: dict = {}


def real_counterfactual():
    """EXPLORATORY, post-hoc: the single mechanism counterfactual on real OLD->NEW.

    Same OLD-trained M3 pipeline with the residual variance cap relaxed from 1 to 1e3.
    This is not a method proposal and is not tuned; it tests one mechanism.
    """
    from src.week12_development_common import FEATURES, load_new, load_old
    old, new = load_old(), load_new()
    xo, yo, lo = old[FEATURES].to_numpy(float), old.has_keyhole.to_numpy(int), old.log_h.to_numpy(float)
    xn, yn, ln = new[FEATURES].to_numpy(float), new.has_keyhole.to_numpy(int), new.log_h.to_numpy(float)
    phys = p11.fit_physics_mean(lo, yo, np.arange(len(old)), 0)
    sc = StandardScaler().fit(xo)
    out = {}
    for name, bounds in (("M3_capped_var_le_1", (0.05 ** 2, 1.0)), ("M3_uncapped_var_le_1e3", (0.05 ** 2, 1e3)), ("G3_like_zero_mean", (1e-3, 1e3))):
        mean_o = phys.latent(lo) if "M3" in name else np.zeros(len(lo))
        mean_n = phys.latent(ln) if "M3" in name else np.zeros(len(ln))
        k = ConstantKernel(0.09 if bounds[1] <= 1 else 1.0, bounds) * Matern(length_scale=np.ones(4), length_scale_bounds=(0.01, 100.0), nu=1.5)
        gp = p11.FixedMeanLaplaceGPC(k, optimize=True).fit(sc.transform(xo), yo, mean_o)
        lat, _ = gp.latent_mean_and_variance(sc.transform(xn), mean_n)
        p = gp.predict_proba(sc.transform(xn), mean_n)[:, 1]
        yhat = (lat > 0).astype(int)
        out[name] = {"balanced_accuracy": float((np.mean(yhat[yn == 1] == 1) + np.mean(yhat[yn == 0] == 0)) / 2),
                     "rare_recall_count": int((yhat[yn == 0] == 0).sum()), "roc_auc": float(roc_auc_score(yn, p)),
                     "amplitude_var": float(gp.kernel_.k1.constant_value),
                     "length_scales_PVXLSST": np.ravel(gp.kernel_.k2.length_scale).round(3).tolist(),
                     "converged": bool(gp.diagnostics_.optimizer_converged)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=7)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    offsets = {amp: offset_for(amp) for amp in AMPS}
    res = Parallel(n_jobs=a.jobs, verbose=5)(delayed(run_one)(amp, r, offsets[amp]) for amp in AMPS for r in range(a.reps))
    frame = pd.DataFrame([row for rows in res for row in rows])
    frame.to_csv(OUT / "transfer_results.csv", index=False)
    cols = ["balanced_accuracy", "rare_recall", "roc_auc", "BEF1", "NSD_0.1", "ASSD", "dense_balanced_accuracy", "amplitude_var", "ls_P", "ls_VX", "ls_LS", "ls_ST"]
    summary = frame.groupby(["amp", "model"])[cols].mean()
    summary.to_csv(OUT / "transfer_summary.csv")
    cf = real_counterfactual()
    (OUT / "REAL_OLD_TO_NEW_COUNTERFACTUAL_EXPLORATORY.json").write_text(json.dumps(cf, indent=2))
    (OUT / "offsets.json").write_text(json.dumps(offsets, indent=2))
    pd.set_option("display.width", 250)
    print(summary.round(3).to_string())
    print(json.dumps(cf, indent=2))


if __name__ == "__main__":
    main()
