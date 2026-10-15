"""Decision-audit amendment A1 (extended QMC ladder): identical to the frozen ladder up to 2^14, adds only 2^16, and
its outputs stay labelled as an amendment next to the unchanged frozen outcome."""
import gzip
import hashlib
import json

import numpy as np
import pytest

import src.jdl_v2_decision_audit as DA
import src.jdl_v2_decision_audit_a1 as A1
import src.jdl_v2_export as VX


def _toy():
    arrays, side, stored, expect = DA._toy_checkpoint()
    return VX.components(arrays), arrays["weights"], len(arrays["x_ref"])


def test_a1_equals_the_frozen_ladder_when_2_14_accepts():
    posts, w, nref = _toy()
    d0, d1 = DA.decisions(posts, w, nref), A1.decisions_a1(posts, w, nref)
    assert d0["numerically_accepted"] and d1["numerically_accepted"] and d0["bits"] == d1["bits"] <= 14
    for k in ("A", "B", "signed_margin", "decision", "margin_2se", "ambiguous"):
        assert np.array_equal(d0[k], d1[k]), k
    assert d0["pi_mean"] == d1["pi_mean"] and A1._same(d0["history"], d1["history"])


def test_a1_adds_only_the_2_16_level(monkeypatch):
    posts, w, nref = _toy()
    monkeypatch.setattr(DA, "ACCEPT_MARGIN_CHANGE", -1.0)          # never accept: exercises the full ladder
    dz, dx = DA.decisions(posts, w, nref), A1.decisions_a1(posts, w, nref)
    assert [h["bits"] for h in dz["history"]] == [12, 14] and [h["bits"] for h in dx["history"]] == [12, 14, 16]
    assert not dz["numerically_accepted"] and not dx["numerically_accepted"] and dx["bits"] == 16
    assert A1._same(dz["history"], dx["history"][:2])


def test_a1_keeps_the_frozen_criterion_and_module():
    assert A1.LADDER_A1 == (10, 12, 14, 16) and DA.ACCEPT_MARGIN_CHANGE == 0.015 and DA.ACCEPT_PI_CHANGE == 0.003
    man = json.loads(A1.FROZEN_MANIFEST.read_text(encoding="utf-8"))
    assert hashlib.sha256((DA.ROOT / "src" / "jdl_v2_decision_audit.py").read_bytes()).hexdigest() == man["code_sha256"]["src/jdl_v2_decision_audit.py"]


def test_a1_outputs_are_labelled_next_to_the_frozen_outcome():
    if not A1.OUTCOME_A1.exists():
        pytest.skip("A1 not evaluated yet")
    out = json.loads(A1.OUTCOME_A1.read_text(encoding="utf-8"))
    assert out["label"].startswith("AMENDED") and out["frozen_outcome"]["audit_status"] == "PRIMARY_UNAVAILABLE"
    assert out["frozen_outcome"]["sha256"] == hashlib.sha256(A1.FROZEN_RESULT.read_bytes()).hexdigest()
    assert (A1.OUT_A1 / out["result_file"]).exists() and (out["exit_code"] == 0) == (out["result_file"] == DA.SUMMARY_FILE)
    recs = [json.loads(gzip.decompress(f.read_bytes()))["fit"] for f in sorted(A1.CACHE_A1.glob("NEW__*.json.gz"))]
    if recs:
        assert len(recs) == 60 and all(r["amendment"] == A1.AMENDMENT for r in recs)
        assert all(r["status"] == DA.ST_OK for r in recs if r["frozen_status"] == DA.ST_OK)     # accepted by 1.1.1 stays accepted
