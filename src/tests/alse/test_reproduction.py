"""Reproduction gates: the thesis headline numbers, read from frozen artifacts.

Gates that need a computation (AULC of the frozen margin trajectories, split and
design manifests, the A0 path replay) live in test_metrics.py and
test_protocol.py. These check the decision artifacts the thesis cites, so a
broken archive path or a silently changed number is caught.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from alse.config import ARCHIVE_OUTPUTS, archive_file
from alse.data import load_population

pytestmark = pytest.mark.archive


def test_population_is_frozen():
    population = load_population()
    assert population.shape[0] == 405 and int(population["has_keyhole"].sum()) == 73
    assert population["partition"].value_counts().to_dict() == {"old-data-local": 178, "new-data": 164, "old-data-remote-clean": 63}


def test_phase7_preregistered_decision():
    decision = pd.read_csv(ARCHIVE_OUTPUTS / "week7_07_final_boundary_hybrid_benchmark" / "phase7_final_decision.csv")
    text = decision.to_string()
    assert "BINARY ACQUISITION PRIMARY" in text


def test_week8_5_frozen_ledger():
    ledger = pd.read_csv(ARCHIVE_OUTPUTS / "week8_5_frozen_confirmation" / "decision_ledger.csv")
    statuses = ledger.iloc[:, ledger.columns.str.contains("decision|status", case=False)].astype(str).agg(" ".join, axis=1)
    joined = " ".join(statuses)
    assert "PASS" in joined and "QUALIFY" in joined and "NOT_CONFIRMED" in joined
    numbers = ledger.select_dtypes("number").to_numpy().ravel()
    assert any(abs(v - 0.0372998) < 1e-6 for v in numbers)  # margin minus random q20 AULC


def test_h320_closure_and_physics_frontier():
    closure = json.loads(archive_file("outputs/week9_phase1_close_week8/query_saving_claim_decision.json").read_text())
    assert "NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED" in json.dumps(closure)
    m3 = pd.read_csv(ARCHIVE_OUTPUTS / "week9_phase1_13_fixed_physics_ard_discrepancy" / "model_summary.csv")
    values = m3.select_dtypes("number").to_numpy().ravel()
    assert any(abs(v - 0.8424908088235293) < 1e-9 for v in values)


def test_phase_1_18b_committed_result():
    """Phase 1.18B exists only at the archive's git HEAD; archive_file() fetches it."""
    decision = json.loads(archive_file("outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/primary_decision.json").read_text())
    assert decision["decision"] == "GLOBAL_SUR_NO_GAIN"
