"""Focused invariants for the Week 9 Phase 1.5 confirmation."""

from __future__ import annotations

import inspect
import json

import numpy as np
import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_5_h_physics_confirmation as phase15


def test_canonical_population_and_semantics() -> None:
    population = w85.load_population().reset_index(drop=True)
    assert len(population) == 405
    assert int(population.has_keyhole.sum()) == 73
    assert int((population.has_keyhole.astype(int) == 0).sum()) == 332
    assert population.ST.between(300.0, 400.0).all()
    assert population.LS.between(40e-6, 90e-6).all()
    source = (
        phase15.ROOT / "src" / "week6_phase3_5_regime_target_design.py"
    ).read_text(encoding="utf-8")
    assert '"spot_radius"' in source
    assert "np.isclose(laser_spot_size, spot_radius" in source
    audit = json.loads((phase15.OUTPUT / "data_and_protocol_audit.json").read_text(encoding="utf-8"))
    assert audit["LS_definition"] == "Gaussian laser spot radius r0; stored in metres"
    assert audit["ST_definition"] == "substrate temperature"


def test_h_si_calculation_and_determinism() -> None:
    sample = pd.DataFrame(
        {
            "P": [200.0],
            "VX": [0.8],
            "LS": [50e-6],
            "ST": [350.0],
            "experiment_name": ["unit-test"],
            "has_keyhole": [False],
        }
    )
    first = phase15.h_coordinates(sample)
    second = phase15.h_coordinates(sample.copy())
    expected = 200.0 / np.sqrt(0.8 * (50e-6) ** 3)
    assert np.isclose(first.loc[0, "h_SI"], expected, rtol=0, atol=1e-9)
    assert np.isclose(first.loc[0, "log_h_SI_reference"], np.log(expected), rtol=0, atol=1e-14)
    pd.testing.assert_frame_equal(first, second)
    # W / sqrt((m/s) m^3) = W s^(1/2) m^-2, so bare h is not dimensionless.
    assert expected > 0


def test_frozen_split_manifest_and_initial_design() -> None:
    population = w85.load_population().reset_index(drop=True)
    specs = w85.build_splits(population)
    distances = w85.b1_distance(population)
    assert len(specs) == 100
    for spec in specs:
        train = set(spec.train_indices)
        test = set(spec.test_indices)
        assert len(train) == 324
        assert len(test) == 81
        assert train.isdisjoint(test)
        initial = w85.initial_design(spec, population)
        assert len(initial) == 16
        assert set(initial).issubset(train)
        flags = w85.boundary_flags(spec, population, distances)
        assert int(flags["B1_q20"].sum()) == 17
        assert int(flags["B1_q30"].sum()) == 25


def test_acquisition_choosers_have_no_label_or_boundary_inputs() -> None:
    for chooser in (
        phase15.choose_h_margin,
        phase15.choose_gpc_margin,
        phase15.choose_assisted_product,
    ):
        names = {name.lower() for name in inspect.signature(chooser).parameters}
        assert not names.intersection({"labels", "hidden_labels", "test_labels", "b1", "b2", "b3"})

    candidate = np.array([9, 4, 7])
    probabilities = np.array([0.1, 0.5, 0.9])
    assert phase15.choose_h_margin(candidate, probabilities) == 4
    assert phase15.choose_gpc_margin(candidate, probabilities) == 4
    assert phase15.choose_assisted_product(candidate, probabilities, probabilities) == 4


def test_saved_active_information_flow() -> None:
    flow = pd.read_csv(phase15.OUTPUT / "active_information_flow.csv.gz")
    assert len(flow) == 27_200
    assert set(flow.arm) == {"h_margin", "gpc5_margin", "assisted_product"}
    population = w85.load_population().reset_index(drop=True)
    specs = {spec.run_id: spec for spec in w85.build_splits(population)}
    for run_id, rows in flow.groupby("run_id"):
        spec = specs[run_id]
        train, test = set(spec.train_indices), set(spec.test_indices)
        selected = set(rows.selected_population_row_index.astype(int))
        assert selected.issubset(train)
        assert selected.isdisjoint(test)
    assert not flow.test_rows_available_to_acquisition.astype(bool).any()
    assert not flow.hidden_pool_labels_available_to_acquisition.astype(bool).any()
    assert not flow.B1_B2_B3_available_to_acquisition.astype(bool).any()
    assert not flow.threshold_fitted_from_all_pool_labels.astype(bool).any()


def test_week85_baseline_reproduction_gate() -> None:
    gate = phase15.baseline_reproduction_gate()
    assert gate["status"] == "PASS"
    assert gate["outer_runs"] == 100
    assert gate["initial_design_exact_matches"] == 100
    assert gate["absolute_difference"] < 2e-5
