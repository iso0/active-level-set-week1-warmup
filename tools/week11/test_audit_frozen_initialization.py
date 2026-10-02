"""Focused tests for the bounded post-hoc initialization audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("audit_frozen_initialization.py")
SPEC = importlib.util.spec_from_file_location("week11_initialization_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def test_exact_hypergeometric_small_population():
    assert audit.single_class_probability(2, 2, 2) == pytest.approx(1 / 3)
    assert audit.single_class_probability(0, 5, 2) == 1.0


def test_hypergeometric_rejects_impossible_sample():
    with pytest.raises(audit.AuditError, match="Invalid hypergeometric population"):
        audit.single_class_probability(2, 2, 5)


def test_distribution_is_exact_and_deterministic():
    assert audit._distribution([1, 2, 2, 3]) == {
        "minimum": 1, "median": 2.0, "maximum": 3,
        "histogram": {"1": 1, "2": 2, "3": 1},
    }
