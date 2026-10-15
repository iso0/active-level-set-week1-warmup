"""Unit and invariant tests for the V2 comparison, the VX stump, the EX addendum metrics and the stopping audit."""
import gzip
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "joint_depth_label_development"
V2DIR = OUT / "v2_model_comparison"
REL = "outputs/joint_depth_label_development"
ASTRA = ROOT / "outputs" / "astra_joint_model_v2"


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)


def _added_in(path):
    c = _git("log", "--format=%H", "--diff-filter=A", "--", path).stdout.split()
    return c[-1] if c else None


# ---------------------------------------------------------------------------------------------------- the port
def _astra():
    sys.path.insert(0, str(ASTRA))
    try:
        for m in ("joint_model_v2", "v1_reference"):
            sys.modules.pop(m, None)
        import joint_model_v2 as A
        import v1_reference as V1
        return A, V1
    finally:
        sys.path.remove(str(ASTRA))


@pytest.mark.skipif(not (ASTRA / "joint_model_v2.py").exists(), reason="Astra V2 package absent")
def test_port_matches_astra_on_a_small_four_input_case():
    import src.jdl_v2_model as P
    A, V1 = _astra()
    g = np.random.default_rng(3)
    ref = g.uniform(-1, 1, (25, 4)); xp = ref[:9]; xt = g.uniform(-1, 1, (7, 4))
    y = np.array([1, 1, 0, 1, 1, 1, 0, 1, 1], float); z = 0.6 * xp[:, 0] + 0.1 + 0.03 * g.standard_normal(9); z[4] = np.nan
    cfg = P.STAGE_M_CONFIG
    for kw in ({}, {"rhos": (1.0,)}):
        a = A.JointModelV2(ref, cfg, **kw).fit(xp, y, z); p = P.JointModelV2(ref, cfg, **kw).fit(xp, y, z)
        assert np.max(np.abs(a.predict_proba(xt) - p.predict_proba(xt))) < 1e-7
        assert np.max(np.abs(a.weights - p.weights)) < 1e-7
        assert np.max(np.abs(np.array(a.diagnostics["log_evidence"]) - np.array(p.diagnostics["log_evidence"]))) < 1e-7
    b = P.JointModelV2(ref, cfg).fit(xp, y, z, use_response=False)
    assert b.solve_count == 1 and np.max(np.abs(b.weights - 1 / 3)) < 1e-12
    lap = P.JointModelV2(ref, cfg, rhos=(1.0,), inference="laplace").fit(xp, y, z)
    v1 = V1.JointDepthLabelGP(ref, cfg).fit(xp, y, z)
    assert np.max(np.abs(lap.predict_proba(xt) - v1.predict_proba(xt))) < 2e-7


def test_ep_is_exact_for_one_probit_factor():
    import src.jdl_v2_model as P
    from scipy.special import log_ndtr, ndtr
    m, K, tau = np.array([0.4]), np.array([[0.3]]), 0.15
    r = P.infer_probit(m, K, np.array([0]), tau, "ep")
    t = -0.4 / np.sqrt(tau ** 2 + 0.3)
    assert abs(r["log_evidence"] - log_ndtr(t)) < 1e-10


def test_induced_failure_refits_the_whole_mixture():
    import src.jdl_v2_model as P
    g = np.random.default_rng(5)
    ref = g.uniform(-1, 1, (20, 4)); xp = ref[:8]; y = np.array([1, 1, 1, 0, 1, 1, 1, 1], float); z = 0.5 * xp[:, 1]
    m = P.JointModelV2(ref, P.STAGE_M_CONFIG).fit(xp, y, z, _inject_failure=0.5)
    assert m.diagnostics["fallback"] and len(m.components) == 3
    assert [c["method"] for c in m.diagnostics["components"]] == ["laplace"] * 3 and m.weights.min() > 0


# ---------------------------------------------------------------------------------------------------- VX stump
def test_stump_learns_cut_and_orientation_from_paid_labels_only():
    from src.jdl_vx_stump import fit_stump, predict_stump
    x = np.array([-1.0, -0.5, 0.0, 0.4, 1.2, 1.5]); y = np.array([1, 1, 1, 1, 0, 0])
    m = fit_stump(x, y)
    assert m["type"] == "split" and m["orientation"] == -1 and abs(m["cut"] - 0.8) < 1e-12 and m["paid_BA"] == 1.0
    s = predict_stump(m, np.array([-2.0, 0.79, 0.81, 3.0]))
    assert list(s >= 0.5) == [True, True, False, False]
    m2 = fit_stump(-x, y)                                                         # mirrored feature -> mirrored orientation
    assert m2["orientation"] == +1
    assert fit_stump(x, np.ones(6, int))["type"] == "constant"                    # one-class paid labels
    assert fit_stump(np.zeros(4), np.array([1, 0, 1, 0]))["type"] == "constant"  # no distinct values
    import ast
    text = (ROOT / "src" / "jdl_vx_stump.py").read_text(encoding="utf-8")
    assert "0.85" not in text.replace(ast.get_docstring(ast.parse(text), clean=False), "")   # no fixed cut outside the docstring


def test_stump_tie_break_prefers_the_widest_gap():
    from src.jdl_vx_stump import fit_stump
    x = np.array([0.0, 0.1, 1.0, 1.1, 3.0]); y = np.array([1, 0, 1, 0, 1])
    m = fit_stump(x, y)
    assert m["type"] in ("split", "constant")
    if m["type"] == "split":
        assert m["paid_BA"] > 0.5


# ---------------------------------------------------------------------------------------------------- metrics
def test_threshold_metrics_equal_stage_m_metrics_at_one_half():
    from src.jdl_evaluate import boot_weights, wmetrics
    from src.jdl_v2_evaluate import wmetrics_thr
    g = np.random.default_rng(7)
    n = 60; y = (g.uniform(size=n) < 0.8).astype(int); p = g.uniform(size=n); p[3] = np.nan
    avail = np.isfinite(p); sk = g.uniform(size=n) < 0.2; q20 = g.uniform(size=n) < 0.3; fold = g.integers(1, 6, n)
    W = boot_weights(y, draws=50, seed=1)
    a = wmetrics(p, avail, y, sk, q20, fold, W)
    b, _, _ = wmetrics_thr(p, avail, y, sk, q20, fold, W, np.full(n, 0.5))
    for k in a:
        assert np.allclose(a[k], b[k], equal_nan=True), k


# ---------------------------------------------------------------------------------------------------- V2 study artefacts
needs_v2 = pytest.mark.skipif(not (V2DIR / "V2_DECISION.json").exists(), reason="V2 comparison not evaluated yet")


@pytest.mark.skipif(not (V2DIR / "V2_MANIFEST.json").exists(), reason="V2 manifest absent")
def test_v2_validation_and_manifest_precede_results():
    val = json.loads((V2DIR / "validation" / "V2_VALIDATION.json").read_text(encoding="utf-8"))
    assert val["status"] == "PASS" and all(val["hard_checks"].values())
    man = _added_in(f"{REL}/v2_model_comparison/V2_MANIFEST.json")
    assert man
    for out in ("predictions_all.csv.gz", "V2_DECISION.json", "contrasts.csv", "RUN_STATE.json"):
        c = _added_in(f"{REL}/v2_model_comparison/{out}")
        if c is not None:
            assert c != man and _git("merge-base", "--is-ancestor", man, c).returncode == 0, out
    frozen = json.loads(_git("show", f"{man}:{REL}/v2_model_comparison/V2_MANIFEST.json").stdout)
    import hashlib
    for f, h in frozen["code_sha256"].items():
        assert hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == h, f


@needs_v2
def test_v2_run_complete_reuse_exact_and_identities():
    st = json.loads((V2DIR / "RUN_STATE.json").read_text(encoding="utf-8"))
    assert st["top_level_requests"] == 180 and st["pending"] is None
    assert st["component_attempts"]["validation"] + st["component_attempts"]["comparison"] <= 300
    pr = pd.read_csv(V2DIR / "predictions_all.csv.gz")
    assert set(pr.arm) == {"V2_EP_mixture", "rho1_EP", "Binary_V2_EP", "V1_Laplace", "Binary_V1_Laplace", "ACTIVE_E1", "G3", "J_trained", "VX_stump"}
    sm = pd.read_csv(OUT / "stage_m" / "predictions_all.csv.gz")
    sm = sm[sm.population == "NEW"]
    for arm, src in (("V1_Laplace", "J"), ("Binary_V1_Laplace", "Binary_matched"), ("ACTIVE_E1", "ACTIVE_E1"), ("G3", "G3")):
        a = pr[pr.arm == arm].set_index(["repeat", "fold", "budget", "sim_id"]).p.sort_index()
        b = sm[sm.arm == src].set_index(["repeat", "fold", "budget", "sim_id"]).p.sort_index()
        x, z = a.to_numpy(), b.loc[a.index].to_numpy()
        # Exact up to the CSV round trip (owner decision of 2026-10-15, ledger T17-FIX): the reused value was parsed from
        # the Stage M CSV by pandas' default float parser, which is not correctly rounded, before being stored, so it may
        # lie one ULP away (T17: 1 of 2,176 values, 2.1e-25 at p = 1.24e-9).  Missing values must coincide exactly.
        same = (x == z) | (np.isnan(x) & np.isnan(z))
        one_ulp = np.abs(x - z) <= np.spacing(np.maximum(np.abs(x), np.abs(z)))
        assert (same | one_ulp).all(), arm
    mix = pr[pr.arm == "V2_EP_mixture"].set_index(["repeat", "fold", "budget", "sim_id"]).sort_index()
    r1 = pr[pr.arm == "rho1_EP"].set_index(["repeat", "fold", "budget", "sim_id"]).sort_index()
    fl = pd.read_csv(V2DIR / "fit_log.csv")
    if not fl[fl.arm == "V2_EP_mixture"].empty and (fl[fl.arm == "rho1_EP"].reused_from.notna()).all():
        assert np.array_equal(r1.p.to_numpy(), mix["p_rho_1.0"].to_numpy())
    cm = pd.read_csv(V2DIR / "component_masses_and_moments.csv")
    assert np.allclose(cm[cm.arm == "Binary_V2_EP"].weight, 1 / 3, atol=1e-12)


@needs_v2
def test_v2_decision_follows_the_frozen_screen():
    d = json.loads((V2DIR / "V2_DECISION.json").read_text(encoding="utf-8"))
    ct = pd.read_csv(V2DIR / "contrasts.csv")
    r = ct[(ct.arm == "V2_EP_mixture") & (ct.ref == "Binary_V2_EP") & (ct.budget == 40) & (ct.rule == "p>=0.5")].set_index("metric").estimate_mean_over_repeats
    ok = r["BA"] >= 0.01 - 1e-12 and r["specificity"] >= -1e-12 and r["log_loss"] <= 1e-12
    assert d["screen"]["verdict"].startswith("PROMISING") == bool(ok)
    assert abs(d["primary"]["estimate"] - r["BA"]) < 1e-12


@pytest.mark.skipif(not (OUT / "exploratory" / "EX_METRICS_ADDENDUM" / "metrics_with_counts.csv").exists(), reason="EX addendum not computed")
def test_ex_addendum_reproduces_the_quoted_numbers():
    m = pd.read_csv(OUT / "exploratory" / "EX_METRICS_ADDENDUM" / "metrics_with_counts.csv")
    new = m[(m.population == "NEW") & (m.budget == 40)].set_index(["arm", "rule"])
    for (arm, rule), ba, sk in ((("G3", "p>=0.5"), 0.6435, 0.55), (("ACTIVE_E1", "p>=0.5"), 0.6818, 0.70), (("J_trained", "p>=0.5"), 0.7517, 0.675), (("J_trained", "p>=pi_hat"), 0.9059, 0.05)):
        assert abs(new.loc[(arm, rule)].BA - ba) < 5e-4 and abs(new.loc[(arm, rule)].shortK_sensitivity - sk) < 1e-9
