"""Checkpoint acceptance safeguards of the cached-posterior decision audit (decision-audit-1.1, 2026-10-14): forced
numerical failure, probability mismatch, invalid exports, the valid unchanged case, readout and primary availability,
and the queue completion marker.  Synthetic inputs only (no study data, no fit); the last test checks written audit
outputs when they exist."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import src.jdl_v2_decision_audit as DA
import src.jdl_v2_export as VX

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "outputs" / "joint_depth_label_development" / "v2_decision_audit"
QUEUE = ROOT / "outputs" / "joint_depth_label_development" / "queue" / "QUEUE.json"
CUTOFF_ONLY = {"finite_batch": False, "posterior_mean_pi": False, "paid_fraction": True, "cutoff_0.5": True}


@pytest.fixture()
def toy():
    return DA._toy_checkpoint()


def _audit(toy, arrays=None, side=None, stored=None, **kw):
    a, s, st, expect = toy
    return DA.audit_checkpoint(a if arrays is None else arrays, s if side is None else side, st if stored is None else stored, 0.5, expect=expect, **kw)


def _copy(arrays):
    return {k: v.copy() for k, v in arrays.items()}


# ---------------------------------------------------------------------------------------------------- valid case
def test_valid_checkpoint_is_accepted_and_unchanged(toy):
    arrays = toy[0]
    rec, rows = _audit(toy)
    assert rec["status"] == DA.ST_OK and rec["parity_pass"] and all(rec["valid"].values())
    assert rec["max_abs_p_minus_stored_prediction"] <= DA.P_PARITY_TOL
    nref = len(arrays["x_ref"]); posts, w = VX.components(arrays), arrays["weights"]
    dec = DA.decisions(posts, w, nref)                               # the decision-audit-1.0 computation
    pt = DA.mixture_probability(posts, w)[nref:]
    want = {"finite_batch": dec["decision"][nref:], "posterior_mean_pi": pt >= dec["pi_mean"], "paid_fraction": pt >= 0.5, "cutoff_0.5": pt >= 0.5}
    for rule, v in want.items():
        assert np.array_equal([r[f"d_{rule}"] for r in rows], v), rule
    assert np.array_equal([r["A"] for r in rows], dec["A"][nref:]) and np.array_equal([r["B"] for r in rows], dec["B"][nref:])
    assert rec["pi_mean"] == dec["pi_mean"] and rec["numerically_accepted"]
    assert all(r["checkpoint_status"] == DA.ST_OK and r["valid_finite_batch"] for r in rows)


# ---------------------------------------------------------------------------------------------------- numerical failure
def test_forced_ladder_failure_is_excluded_from_the_qmc_rules(toy):
    def forced_stop(posts, w, nref):
        d = DA.decisions(posts, w, nref); d["numerically_accepted"] = False
        return d
    rec, rows = _audit(toy, decide=forced_stop)
    assert rec["status"] == DA.ST_STOP and rec["valid"] == CUTOFF_ONLY
    assert len(rows) == 4 and all(r["d_finite_batch"] is not None and r["valid_finite_batch"] is False for r in rows)   # attempted, kept, flagged


def test_non_psd_covariance_is_a_numerical_stop(toy):
    bad = _copy(toy[0]); cov = bad["h_cov_0"]
    cov[0, 1] = cov[1, 0] = 1.5 * np.sqrt(cov[0, 0] * cov[1, 1])     # indefinite; diagonal (hence parity) unchanged
    rec, rows = _audit(toy, arrays=bad)
    assert rec["parity_pass"] and rec["status"] == DA.ST_STOP and "FloatingPointError" in rec["reason"]
    assert rec["valid"] == CUTOFF_ONLY and all("d_finite_batch" not in r for r in rows)


def test_nonfinite_coefficients_are_flagged(toy):
    def forced_nan(posts, w, nref):
        d = DA.decisions(posts, w, nref); d["A"] = np.array(d["A"], float); d["A"][-1] = np.nan
        return d
    rec, _ = _audit(toy, decide=forced_nan)
    assert rec["status"] == DA.ST_NONFINITE and rec["valid"] == CUTOFF_ONLY


# ---------------------------------------------------------------------------------------------------- probability parity
@pytest.mark.parametrize("delta, ok", [(1e-8, False), (2 * DA.P_PARITY_TOL, False), (0.5 * DA.P_PARITY_TOL, True), (np.nan, False)])
def test_probability_parity_is_enforced_at_1e_10(toy, delta, ok):
    st = toy[2].copy()
    st.iloc[1] = np.nan if np.isnan(delta) else st.iloc[1] + delta
    rec, _ = _audit(toy, stored=st)
    assert DA.P_PARITY_TOL == 1e-10
    assert (rec["status"] == DA.ST_OK) is ok
    if not ok:
        assert rec["status"] == DA.ST_PARITY and not any(rec["valid"].values())


# ---------------------------------------------------------------------------------------------------- invalid exports
def _variants(toy):
    arrays, side, stored, _ = toy
    a1 = _copy(arrays); a1["h_mean_1"][3] = np.nan
    a2 = _copy(arrays); a2["weights"] = np.array([.6, .3])
    a3 = _copy(arrays); a3["x_eval"] = a3["x_eval"][:3]
    st = stored.copy(); st.index = list(stored.index[:3]) + ["OTHER-SIM_H-0000000000"]
    return {"nonfinite_h_mean": {"arrays": a1}, "weights_not_probability_vector": {"arrays": a2}, "inputs_not_aligned": {"arrays": a3},
            "duplicated_test_id": {"side": dict(side, test_ids=[side["test_ids"][0]] * 2 + side["test_ids"][2:])},
            "stored_ids_differ": {"stored": st}, "sidecar_metadata_differs": {"side": dict(side, fold=2)},
            "stored_not_numeric": {"stored": pd.Series(["x"] * 4, index=stored.index)}}


@pytest.mark.parametrize("name", list(_variants(DA._toy_checkpoint())))
def test_invalid_exports_enter_no_rule(toy, name):
    rec, rows = _audit(toy, **_variants(toy)[name])
    assert rec["status"] == DA.ST_INVALID and not any(rec["valid"].values()) and rows == []


def test_export_files_are_verified_against_the_frozen_index(toy, tmp_path):
    arrays, side, stored, _ = toy
    stem = DA.checkpoint_name(1, 1, 16, "V2_EP_mixture")
    sw = VX.save_export(tmp_path / f"{stem}.npz", arrays, side)
    pref = {"status": "ok", "prefix_sha256": side["prefix_sha256"], "pi_hat": 0.5}
    fits = {(1, 1, 16, "V2_EP_mixture"): dict(pref, export=sw), (1, 1, 16, "rho1_EP"): dict(pref, reused_from="V2_EP_mixture rho=1 EP component (exact; same fit)"),
            (1, 1, 16, "Binary_V2_EP"): {"status": "failed", "error": "synthetic"}}
    index = {stem: sw["file_sha256"]}
    ld = DA.load_checkpoint(1, 1, 16, "V2_EP_mixture", fits, index, tmp_path)
    assert ld["reason"] is None and DA.audit_checkpoint(ld["arrays"], ld["side"], stored, .5, expect=ld["expect"])[0]["status"] == DA.ST_OK
    ld1 = DA.load_checkpoint(1, 1, 16, "rho1_EP", fits, index, tmp_path)
    nref = len(arrays["x_ref"]); p1 = DA.mixture_probability([VX.components(arrays)[1]], [1.0])[nref:]
    assert ld1["stem"] == stem and ld1["component_rho"] == 1.0
    assert DA.audit_checkpoint(ld1["arrays"], ld1["side"], pd.Series(p1, index=side["test_ids"]), .5, expect=ld1["expect"], component_rho=1.0)[0]["status"] == DA.ST_OK
    # the mixture probability is not the rho = 1 probability: using the wrong component fails parity
    assert DA.audit_checkpoint(ld1["arrays"], ld1["side"], stored, .5, expect=ld1["expect"], component_rho=1.0)[0]["status"] == DA.ST_PARITY
    for args in ((1, 1, 16, "Binary_V2_EP", fits, index, tmp_path), (2, 1, 16, "V2_EP_mixture", fits, index, tmp_path),
                 (1, 1, 16, "V2_EP_mixture", fits, {}, tmp_path), (1, 1, 16, "V2_EP_mixture", fits, {stem: "0" * 64}, tmp_path),
                 (1, 1, 16, "V2_EP_mixture", fits, index, tmp_path / "absent")):
        ld = DA.load_checkpoint(*args)
        assert ld["reason"] and ld["arrays"] is None
        assert DA.audit_checkpoint(ld["arrays"], ld["side"], stored, .5, reason=ld["reason"])[0]["status"] == DA.ST_INVALID
    f = tmp_path / f"{stem}.npz"; f.write_bytes(f.read_bytes() + b"\0")
    assert "altered" in DA.load_checkpoint(1, 1, 16, "V2_EP_mixture", fits, index, tmp_path)["reason"]


# ---------------------------------------------------------------------------------------------------- availability
def test_one_failed_primary_checkpoint_makes_the_primary_unavailable():
    s = DA.summarize(DA._toy_records({(1, 3, 40, "V2_EP_mixture"): DA.ST_STOP}))
    ro = s["readouts"]
    assert s["audit_status"] == "PRIMARY_UNAVAILABLE" and s["exit_code"] == DA.EXIT_PRIMARY_UNAVAILABLE == 3
    assert s["primary"]["checkpoints_ok"] == 19 and s["primary"]["invalid_checkpoints"] == ["NEW__r1_f3__B40__V2_EP_mixture"]
    assert not ro["V2_EP_mixture|B40|r1|finite_batch"]["available"] and ro["V2_EP_mixture|B40|r1|finite_batch"]["valid_folds"] == 4
    assert not ro["V2_EP_mixture|B40|r1|posterior_mean_pi"]["available"]
    assert ro["V2_EP_mixture|B40|r1|cutoff_0.5"]["available"] and ro["V2_EP_mixture|B40|r2|finite_batch"]["available"]


@pytest.mark.parametrize("change, partition", [({(2, 2, 16, "V2_EP_mixture"): None}, None), ({(1, 1, 40, "V2_EP_mixture"): DA.ST_PARITY}, None),
                                               ({(2, 4, 16, "V2_EP_mixture"): DA.ST_INVALID}, None), ({(1, 5, 16, "V2_EP_mixture"): DA.ST_NONFINITE}, None),
                                               ({}, {"V2_EP_mixture": False})])
def test_missing_invalid_or_unpartitioned_primary_is_unavailable(change, partition):
    part = None if partition is None else {(a, b, r): a not in partition for a in DA.ARMS for b in (16, 40) for r in (1, 2)}
    s = DA.summarize(DA._toy_records(change), part)
    assert s["primary"]["status"] == "PRIMARY_UNAVAILABLE" and s["exit_code"] == 3


def test_duplicate_record_is_never_scored():
    recs = DA._toy_records({}); s = DA.summarize(recs + recs[:1])
    assert s["exit_code"] == 3 and s["status_counts"][DA.ST_DUPLICATE] == 1


def test_secondary_failure_keeps_a_complete_primary():
    s = DA.summarize(DA._toy_records({(2, 5, 16, "rho1_EP"): DA.ST_PARITY}))
    assert s["audit_status"] == "PRIMARY_COMPLETE_SECONDARY_UNAVAILABLE" and s["exit_code"] == 0
    assert not s["readouts"]["rho1_EP|B16|r2|cutoff_0.5"]["available"] and s["readouts"]["rho1_EP|B16|r1|cutoff_0.5"]["available"]
    assert DA.summarize(DA._toy_records({}))["audit_status"] == "COMPLETE"


def test_incomplete_audit_never_writes_the_queue_completion_marker(tmp_path):
    bad = DA.summarize(DA._toy_records({(1, 3, 40, "V2_EP_mixture"): DA.ST_STOP}))
    assert DA.finalize(bad, tmp_path / "bad") == 3
    assert (tmp_path / "bad" / DA.UNAVAILABLE_FILE).exists() and not (tmp_path / "bad" / DA.SUMMARY_FILE).exists()
    assert DA.finalize(DA.summarize(DA._toy_records({})), tmp_path / "ok") == 0 and (tmp_path / "ok" / DA.SUMMARY_FILE).exists()
    t08 = [t for t in json.loads(QUEUE.read_text(encoding="utf-8"))["tasks"] if t["id"] == "T08_DECISION_EVALUATE"]
    assert len(t08) == 1 and t08[0]["done"] == {"type": "file", "path": f"outputs/joint_depth_label_development/v2_decision_audit/{DA.SUMMARY_FILE}"}


def test_validation_gate_contains_the_safeguard_selftest():
    sg = DA.safeguard_selftest()
    failed = [k for k, v in sg["checks"].items() if not v]
    assert not failed, failed
    assert len(sg["checks"]) >= 30


# ---------------------------------------------------------------------------------------------------- written outputs
def test_written_audit_outputs_respect_availability():
    present = [f for f in (AUDIT / DA.SUMMARY_FILE, AUDIT / DA.UNAVAILABLE_FILE) if f.exists()]
    if not present:
        pytest.skip("decision audit not evaluated yet")
    assert len(present) == 1
    s = json.loads(present[0].read_text(encoding="utf-8"))
    assert s["audit_version"] == DA.AUDIT_VERSION and (s["exit_code"] == 0) == (present[0].name == DA.SUMMARY_FILE)
    mt = pd.read_csv(AUDIT / "metrics_per_repeat.csv")
    for r in mt.itertuples():
        ro = s["readouts"][DA.readout_key(r.arm, r.budget, r.repeat, r.rule)]
        assert (r.availability == "AVAILABLE") == ro["available"]
        assert np.isfinite(r.BA) == ro["available"]
    fl = pd.read_csv(AUDIT / "class_fractions_and_numerics.csv")
    assert set(fl.status) <= {DA.ST_OK, DA.ST_INVALID, DA.ST_PARITY, DA.ST_NONFINITE, DA.ST_STOP}
    assert (fl[fl.status == DA.ST_OK].max_abs_p_minus_stored_prediction <= DA.P_PARITY_TOL).all()
