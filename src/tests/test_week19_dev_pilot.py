"""Invariant tests for the Week 19 DEV pilot (no GP fits).

Target-extraction fixtures re-derive A and the whole-record maximum from the raw cache with an independent few-line
implementation of the pinned rules; they are skipped when the raw cache is absent.  Pipeline invariants read the
committed pilot tables.
"""
import json

import numpy as np
import pandas as pd
import pytest

import src.week19_dev_pilot as P

TAB, OUT = P.TAB, P.OUT
needs_outputs = pytest.mark.skipif(not (TAB / "fit_diagnostics.csv").exists(), reason="pilot outputs absent")


# ---------------------------------------------------------------- target contract
def test_pilot_inputs_contract():
    inp = pd.read_csv(TAB / "pilot_inputs.csv")
    cols = ["sim_id", "campaign", "partition", "P_W", "VX_m_s", "LS_radius_m", "ST_K", "has_keyhole", "whole_max_um", "A_um", "A_available", "A_failure",
            "first_valid_ms", "recording_end_ms", "derived_exit_ms", "active_cutoff_ms", "early_end", "frac_K_FCK", "frac_K_KC", "n_K_frames", "n_C_frames",
            "source_revision", "source_table_sha256"]
    assert list(inp.columns) == cols
    assert len(inp) == 541 and inp.sim_id.is_unique
    assert inp.groupby("campaign").has_keyhole.agg(["size", "sum"]).to_dict() == {"size": {"NEW": 136, "OLD": 405}, "sum": {"NEW": 124, "OLD": 73}}
    assert inp.A_um.isna().sum() == 1 and inp.loc[inp.A_um.isna(), "sim_id"].item() == P.NO_A      # null, never zero
    assert (inp.A_available == inp.A_um.notna()).all() and (inp.A_um.dropna() > 0).all()
    assert (inp.A_um.dropna() <= inp.whole_max_um[inp.A_um.notna()] + 1e-9).all()                     # A is a sub-window maximum
    assert inp.frac_K_KC.isna().sum() == 2


def _raw_targets(sim, campaign):
    from src.week19_sources import local_file
    from src.week7_phase2_sph_v2_physical_target_extraction import load_numeric
    rev = P.OLD_REV if campaign == "OLD" else P.NEW_REV
    t = np.loadtxt(local_file(rev, f"{sim}/monitor/time.dat"), ndmin=1)
    b, _ = load_numeric(local_file(rev, f"{sim}/monitor/position-bounds_melt.dat"), "position-bounds_melt.dat")
    valid = np.isfinite(b).all(1) & (np.abs(b) < 1e30).all(1) & (b[:, 1] >= b[:, 0]) & (b[:, 3] >= b[:, 2]) & (b[:, 5] >= b[:, 4])
    depth = 1e6 * np.maximum(0.0, -b[:, 4])
    whole = float(depth[valid].max())
    if len(b) != len(t):
        return whole, np.nan
    tok = {k: float(sim.split(f"_{k}-")[1].split("_")[0].replace("p", ".")) for k in ("VX", "XF", "XL")}
    cutoff = min(float(t[-1]), 0.9 * (min(tok["XF"], tok["XL"]) + 12e-6) / tok["VX"])
    return whole, float(depth[valid & (t <= cutoff)].max())


def _fixture_ids():
    rep = pd.read_csv(P.AUDIT / "tables/representative_cases.csv")
    return [P.LATE_NEG, P.NO_A, P.LATE_K_POS] + P.UNRESOLVED + rep.sim_id.tolist()


def test_target_extraction_fixtures():
    from src.week19_sources import local_file
    inp = pd.read_csv(TAB / "pilot_inputs.csv").set_index("sim_id")
    ids = _fixture_ids()
    if not local_file(P.NEW_REV, f"{ids[0]}/monitor/time.dat").exists():
        pytest.skip("raw cache absent")
    for sim in ids:
        whole, A = _raw_targets(sim, inp.loc[sim, "campaign"])
        assert abs(whole - inp.loc[sim, "whole_max_um"]) < 1e-9, sim
        if sim == P.NO_A:
            assert np.isnan(A) and np.isnan(inp.loc[sim, "A_um"])                 # bounds/time mismatch: no truncation, no value
        else:
            assert abs(A - inp.loc[sim, "A_um"]) < 1e-9, sim


# ---------------------------------------------------------------- threshold rule and bootstrap
def test_threshold_details_matches_engine_rule():
    from src.week18_engine import DepthGPR
    rng = np.random.default_rng(3)
    X = rng.uniform([300, 0.2, 4e-5, 300], [450, 1.0, 5e-5, 500], size=(30, 4))
    for overlap in (False, True):
        y = (np.arange(30) % 3 == 0).astype(int)
        d = np.where(y == 1, 150.0, 80.0) * rng.uniform(0.9, 1.1, 30)
        if overlap:
            d[0], d[1] = 60.0, 170.0                                                # y[0] = 1 (deep class) shallow, y[1] = 0 deep
        f = DepthGPR(X).fit(X, d, y)
        td = P.threshold_details(np.log(d), y)
        assert td["threshold_branch"] == ("logistic" if overlap else "midpoint")
        assert abs(td["log_u"] - f.u) < 1e-12


def test_bootstrap_weights_stratified_and_seeded():
    y = np.r_[np.ones(124, int), np.zeros(12, int)]
    W = P.boot_weights(y, draws=50)
    assert (W[0] == 1).all() and (W[1:, y == 1].sum(1) == 124).all() and (W[1:, y == 0].sum(1) == 12).all()
    assert np.array_equal(W, P.boot_weights(y, draws=50))


def test_weighted_stats_equal_row_duplication():
    rng = np.random.default_rng(1)
    n = 40
    y = (rng.random(n) < 0.6).astype(int); p = rng.random(n); q = rng.random(n) < 0.3; fold = np.arange(n) % 5; sk = (y == 1) & (rng.random(n) < 0.3)
    w = rng.integers(0, 3, n).astype(float); w[[0, 1]] = 1                        # keep both classes
    dup = np.repeat(np.arange(n), w.astype(int))
    a = P.stats_w(p, np.ones(n, bool), y, sk, q, fold, w[None, :])
    b = P.stats_w(p[dup], np.ones(len(dup), bool), y[dup], sk[dup], q[dup], fold[dup], np.ones((1, len(dup))))
    for k in ("BA", "specificity_12neg", "sensitivity_all_pos", "brier", "AUC"):
        assert np.allclose(a[k], b[k]), k
    ref = 0.5 * (np.mean(p[y == 1] >= .5) + np.mean(p[y == 0] < .5))
    assert np.isclose(P.stats_w(p, np.ones(n, bool), y, sk, q, fold, np.ones((1, n)))["BA"][0], ref)


def _mt(dBA, lo, specA, specW, specG, skA, skW, skG):
    rows = [{"arm": "", "contrast": "ACTIVE_E1_SHARED - WHOLE_E1_SHARED", "budget": 40, "metric": "BA", "estimate": dBA, "lo95": lo, "hi95": 1, "scope": "mean_over_repeats", "threshold_mode": "learned"},
            {"arm": "", "contrast": "ACTIVE_E1_SHARED - WHOLE_E1_SHARED", "budget": 40, "metric": "q20_acc", "estimate": 0.0, "lo95": -1, "hi95": 1, "scope": "mean_over_repeats", "threshold_mode": "learned"}]
    for arm, s, k in (("ACTIVE_E1_SHARED", specA, skA), ("WHOLE_E1_SHARED", specW, skW), ("G3_SHARED", specG, skG)):
        rows += [{"arm": arm, "contrast": "", "budget": 40, "metric": "specificity_12neg", "estimate": s, "lo95": 0, "hi95": 1, "scope": "mean_over_repeats", "threshold_mode": "learned"},
                 {"arm": arm, "contrast": "", "budget": 40, "metric": "sensitivity_shortK", "estimate": k, "lo95": 0, "hi95": 1, "scope": "mean_over_repeats", "threshold_mode": "learned"}]
    return pd.DataFrame(rows)


def test_decision_rule_edges():
    fd = pd.DataFrame({"budget": [40] * 30, "status": ["ok"] * 30, "optimizer_success": [True] * 30})
    ok = pd.DataFrame({"status": ["PASS"]})
    assert P.decide(_mt(0.02, 0.001, 0.5, 0.3, 0.3, 12 / 20, 13 / 20, 8 / 20), fd, ok)["verdict"] == "ADVANCE"            # loss exactly 0.05 passes
    assert P.decide(_mt(0.02, 0.001, 0.5, 0.3, 0.3, 11 / 20, 13 / 20, 8 / 20), fd, ok)["verdict"] == "NO_ADVANCE"         # loss 0.10 fails
    assert P.decide(_mt(0.02, -0.001, 0.5, 0.3, 0.3, 12 / 20, 13 / 20, 8 / 20), fd, ok)["verdict"] == "INCONCLUSIVE"      # lower bound <= 0
    assert P.decide(_mt(0.005, 0.001, 0.5, 0.3, 0.3, 12 / 20, 13 / 20, 8 / 20), fd, ok)["verdict"] == "NO_ADVANCE"        # below 0.01
    assert P.decide(_mt(0.02, 0.001, 0.25, 0.3, 0.3, 12 / 20, 13 / 20, 8 / 20), fd, ok)["verdict"] == "NO_ADVANCE"        # specificity decline
    bad = fd.copy(); bad.loc[0, "status"] = "unavailable_single_class"
    assert P.decide(_mt(0.02, 0.001, 0.5, 0.3, 0.3, 12 / 20, 13 / 20, 8 / 20), bad, ok)["verdict"] == "INCONCLUSIVE"      # B40 unavailable


# ---------------------------------------------------------------- leakage guard (stub engine, no fits)
class _Stub:
    class _GP:
        mode_fp_ = 1e-12
        log_marginal_likelihood_value_ = -1.0
        kernel_ = "stub"

        class diagnostics_:
            optimizer_converged, optimizer_message, optimizer_iterations, fallback_status = True, "ok", 1, "none"

    class _Fit:
        def __init__(self, u=None):
            self.gp, self.u = _Stub._GP(), u

    seen = []

    @classmethod
    def fit_learner(cls, learner, task, L, fixed, state):
        L = np.asarray(L)
        cls.seen.append((learner[0], (task["y"] >= 0).sum(), np.isfinite(task["depth"]).sum(), len(L)))
        assert (task["y"][L] >= 0).all() and (np.delete(task["y"], L) == -1).all()
        assert np.isnan(np.delete(task["depth"], L)).all()
        if learner[0] == "GPR_depth":
            ok = np.isfinite(task["depth"][L])
            return cls._Fit(P.threshold_details(np.log(task["depth"][L][ok]), task["y"][L][ok])["log_u"])
        return cls._Fit()

    @staticmethod
    def proba(f, X):
        return np.full(len(X), 0.7)

    @staticmethod
    def latent(f, X):
        return np.zeros(len(X)), np.ones(len(X))


def test_fit_one_masks_unpaid_rows():
    from src.week13_synthetic_al import maximin_order
    t = P.build_tasks()[0]
    t["path"] = t["pool"][maximin_order(t["X"][t["pool"]], np.random.default_rng([1820, t["repeat"], t["fold"], 2]))][:P.PATH_LEN]
    for arm in P.ARMS:
        rec, pr, oc, ok = P.fit_one(_Stub, t, arm, 16, t["path"][:16], 0)
        assert ok and rec["status"] in ("ok", "unavailable_single_class") and rec["labels_passed"] == 16
        assert len([r for r in pr if r["threshold_mode"] == "learned"]) == len(t["test"])


# ---------------------------------------------------------------- committed pipeline outputs
@needs_outputs
def test_paths_reproduce_and_are_label_blind():
    from src.week13_synthetic_al import maximin_order
    pp = pd.read_csv(TAB / "paid_paths.csv")
    for t in P.build_tasks():
        exp = t["ids"][t["pool"][maximin_order(t["X"][t["pool"]], np.random.default_rng([1820, t["repeat"], t["fold"], 2]))][:P.PATH_LEN]]
        got = pp[(pp.repeat == t["repeat"]) & (pp.fold == t["fold"])].sort_values("query_index").sim_id.to_numpy()
        assert np.array_equal(exp, got) and not set(got) & set(t["ids"][t["test"]])


@needs_outputs
def test_predictions_and_fits_invariants():
    pr = pd.read_csv(TAB / "predictions.csv"); fd = pd.read_csv(TAB / "fit_diagnostics.csv")
    g = pr.groupby(["arm", "threshold_mode", "repeat", "budget"]).sim_id
    assert (g.size() == 136).all() and (g.nunique() == 136).all()
    ok = pr[pr.prediction_status == "ok"]
    assert ok.p_keyhole.between(0, 1).all() and (ok.latent_variance > 0).all()
    assert len(fd) == 90 and (fd.groupby(["repeat", "fold", "budget"]).prefix_sha256.nunique() == 1).all()
    assert (fd.labels_passed == fd.n_paid).all()


@needs_outputs
def test_manifest_frozen_before_fits():
    man = json.loads((OUT / "pilot_manifest.json").read_text(encoding="utf-8"))
    run = json.loads((P.PROV / "p1_run.json").read_text())
    assert run["manifest_sha256_at_fit_time"] == P.sha256(OUT / "pilot_manifest.json")
    assert man["created_utc"] <= run["p1_started_utc"] and run["learner_fits"] <= 90
    assert man["data"]["dev_repeat_allowlist"] == [1, 2] and man["budgets"] == [16, 40, 80]


@needs_outputs
def test_q20_matches_week18_cache():
    if not P.Q20_CACHE.exists():
        pytest.skip("Week 18 phase 2 cache absent")
    qc = P.q20_cache_check(P.build_tasks())
    assert qc.test_rows_equal.all() and qc.q20_equal.all()


def test_descriptive_table_counts_and_labels():
    t = pd.read_csv(TAB / "descriptive_whole_vs_A_by_label.csv")
    assert (t.n_evaluated == t.n_runs_in_subset - t.n_undefined_ratio - t.n_target_missing).all()
    assert (t.n_positive + t.n_negative == t.n_evaluated).all()
    hk = t[(t.label == "has_keyhole") & (t.subset == "all") & t.cohort.str.startswith("all")]
    assert hk.groupby("campaign").n_positive.first().to_dict() == {"NEW": 124, "OLD": 73}     # benchmark labels preserved
    assert t[t.subset != "all"].exploratory.all() and not t[t.subset == "all"].exploratory.any()
