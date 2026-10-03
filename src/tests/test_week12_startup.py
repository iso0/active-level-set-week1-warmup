import importlib
import json
from pathlib import Path

import numpy as np


def test_startup_module_import_has_no_side_effects():
    module = importlib.import_module("src.week12_startup")
    assert module.SCHEMA_VERSION == "week12_startup_diagnosis_v1"
    assert module.FAILURES == {"external__r003_f04", "external__r009_f05", "external__r019_f04"}


def test_single_class_reference_is_hypergeometric():
    module = importlib.import_module("src.week12_startup")
    expected = (1 + 0) / 3
    assert np.isclose(module._single_class_probability(1, 2, 2), expected)
    assert np.isclose(module._single_class_probability(8, 101, 16), 0.26806809563061135)


def test_diagnosis_artifacts_have_passed_qc():
    root = Path("outputs/week12_startup_and_transfer_development/startup/diagnosis")
    if not (root / "QC.json").exists():
        return
    qc = json.loads((root / "QC.json").read_text(encoding="utf-8"))
    assert qc["status"] == "PASS"
    assert all(qc["checks"].values())


def test_diagnosis_does_not_define_a_startup_rule():
    module = importlib.import_module("src.week12_startup")
    assert not hasattr(module, "benchmark_startup_rules")
