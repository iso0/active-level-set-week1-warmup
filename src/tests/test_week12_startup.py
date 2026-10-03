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


def test_startup_next_is_label_blind_beyond_observed_prefix():
    module = importlib.import_module("src.week12_startup")
    x = np.column_stack([np.arange(12) + 10.0, np.arange(12) + 1.0,
                         np.arange(12) + 2.0, np.arange(12) + 300.0])
    train = np.arange(12)
    original = np.arange(12)
    queried = np.array([0, 1, 2, 3, 4, 5, 6, 7])
    observed = np.ones(8, dtype=int)
    for rule in module.STARTUP_RULES:
        first = module.startup_next(rule, x, train, queried, observed, original_order=original, split_id="unit")
        second = module.startup_next(rule, x, train, queried, observed, original_order=original, split_id="unit")
        assert first == second


def test_physics_strata_use_training_rows_only():
    module = importlib.import_module("src.week12_startup")
    x = np.column_stack([np.arange(10) + 10.0, np.arange(10) + 1.0,
                         np.arange(10) + 2.0, np.arange(10) + 300.0])
    train = np.arange(6)
    original = np.arange(6)
    _, first = module._physics_strata(x, train, original)
    changed = x.copy()
    changed[6:, :] = 10_000.0
    _, second = module._physics_strata(changed, train, original)
    assert first == second


def test_physics_stratified_round_robin_is_label_invariant():
    module = importlib.import_module("src.week12_startup")
    x = np.column_stack([np.exp(np.arange(10, dtype=float)), np.ones(10),
                         np.ones(10), np.arange(10, dtype=float)])
    train = np.arange(10)
    original = np.arange(10)
    _, strata = module._physics_strata(x, train, original)
    queried = [0]
    observed_a = [1]
    observed_b = [0]
    chosen_strata = []
    for step in range(6):
        a = module.startup_next("physics_stratified_geometry", x, train, queried,
                                observed_a, original_order=original, split_id="unit")
        b = module.startup_next("physics_stratified_geometry", x, train, queried,
                                observed_b, original_order=original, split_id="unit")
        assert a == b
        chosen_strata.append(strata[a])
        queried.append(a)
        observed_a.append(1 if step % 2 else 0)
        observed_b.append(0 if step % 2 else 1)
    assert chosen_strata == [0, 1, 2, 0, 1, 2]


def test_physics_stratified_exhaustion_checks_all_cyclic_strata():
    module = importlib.import_module("src.week12_startup")
    x = np.column_stack([np.exp(np.arange(5, dtype=float)), np.ones(5),
                         np.ones(5), np.arange(5, dtype=float)])
    train = np.arange(5)
    original = np.arange(5)
    queried = [0]
    observed = [1]
    while len(queried) < len(train):
        nxt = module.startup_next("physics_stratified_geometry", x, train, queried,
                                  observed, original_order=original, split_id="unit")
        assert nxt not in queried
        queried.append(nxt)
        observed.append(1)
    assert sorted(queried) == train.tolist()
