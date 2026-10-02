"""Focused synthetic fixtures for the independent Week 11 QC checker."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).with_name("validate_external_execution.py")
SPEC = importlib.util.spec_from_file_location("week11_execution_qc", MODULE_PATH)
qc = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(qc)


def _path() -> pd.DataFrame:
    return pd.DataFrame({"query_order": range(1, 81), "row_index": range(80)})


def test_path_requires_unique_training_only_orders():
    qc._check_path_group(_path(), set(range(100)))
    duplicate = _path()
    duplicate.loc[79, "row_index"] = 78
    with pytest.raises(qc.QCError, match="repeated query"):
        qc._check_path_group(duplicate, set(range(100)))
    heldout = _path()
    heldout.loc[79, "row_index"] = 101
    with pytest.raises(qc.QCError, match="held-out"):
        qc._check_path_group(heldout, set(range(100)))


def test_prediction_group_rejects_duplicate_or_missing_test_id():
    valid = pd.DataFrame({"row_index": [80, 81, 82]})
    qc._check_prediction_group(valid, {80, 81, 82})
    duplicate = pd.DataFrame({"row_index": [80, 80, 82]})
    with pytest.raises(qc.QCError, match="exactly the held-out"):
        qc._check_prediction_group(duplicate, {80, 81, 82})


def test_completed_pairs_stop_exactly_before_failed_pair():
    splits = [{"split_id": "s1"}, {"split_id": "s2"}]
    failure = {"split_id": "s2", "arm": qc.CONTROL}
    assert qc._completed_pairs_before_failure(splits, failure) == [
        ("s1", qc.CONTROL), ("s1", qc.CHALLENGER), ("s1", qc.ATTRIBUTION)
    ]


def test_frozen_id_and_seed_bindings_reject_drift():
    qc._require_exact(["A", "B"], ["A", "B"], "ID drift")
    with pytest.raises(qc.QCError, match="ID drift"):
        qc._require_exact(["B", "A"], ["A", "B"], "ID drift")
    saved = [{"split_id": "s", "split_seed": 1102}]
    expected = [{"split_id": "s", "split_seed": 1101}]
    with pytest.raises(qc.QCError, match="seed drift"):
        qc._require_exact(saved, expected, "seed drift")


def test_candidate_prefix_stops_at_first_two_class_extension():
    frozen16 = list(range(16))
    labels = {i: 0 for i in frozen16}
    labels[10] = 1
    assert qc._candidate_start_length(frozen16, labels) == 11
    labels[10] = 0
    with pytest.raises(qc.QCError, match="both classes"):
        qc._candidate_start_length(frozen16, labels)
